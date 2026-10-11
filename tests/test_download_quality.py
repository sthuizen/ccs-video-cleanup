import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp import YoutubeDL, parse_options
from ccs.acquire import acquire


class DownloadQuality(unittest.TestCase):
    def select(self, formats, height=None):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ccs.acquire.command') as command:
                acquire(Path(tmp), 'https://www.youtube.com/watch?v=c4qtGGSgBQI',video_height=height)
            full = [str(x) for x in command.call_args.args[0]]
            args = full[full.index('--no-playlist'):]
            opts = parse_options(args).ydl_opts
            opts['quiet'] = True
            with YoutubeDL(opts) as downloader:
                result = downloader.process_ie_result(
                    {'id': 'quality-test', 'title': 'Quality test', 'formats': formats},
                    download=False,
                )
            return result['format_id']

    def video(self, name, height, bitrate, codec='avc1'):
        return dict(format_id=name, ext='mp4', url='https://example.com/' + name,
                    vcodec=codec, acodec='none', height=height, vbr=bitrate)

    def audio(self, name, bitrate, codec='mp4a'):
        return dict(format_id=name, ext='m4a', url='https://example.com/' + name,
                    vcodec='none', acodec=codec, abr=bitrate)

    def test_uncapped_video_and_highest_audio_bitrate(self):
        formats = [self.video('1080', 1080, 2000), self.video('2160', 2160, 6000),
                   self.audio('opus', 128, 'opus'), self.audio('aac', 256)]
        self.assertEqual(self.select(formats), '2160+aac')

    def test_resolution_takes_priority_over_bitrate(self):
        formats = [self.video('high-bitrate', 720, 5000),
                   self.video('high-resolution', 2160, 3000, 'av01'),
                   self.audio('audio', 256)]
        self.assertEqual(self.select(formats), 'high-resolution+audio')

    def test_combined_stream_fallback(self):
        formats = [dict(format_id='combined', ext='mp4', url='https://example.com/combined',
                        vcodec='avc1', acodec='mp4a', height=2160, vbr=6000, abr=256)]
        self.assertEqual(self.select(formats), 'combined')

    def test_selected_resolution_keeps_best_audio(self):
        formats=[self.video('720',720,2000),self.video('1080',1080,4000),self.audio('best',256),self.audio('small',64)]
        self.assertEqual(self.select(formats,720),'720+best')

    def test_dimensions_never_upscale(self):
        from ccs.render import output_dimensions
        self.assertEqual(output_dimensions(1920,1080,720),(1280,720))
        self.assertEqual(output_dimensions(1280,720,1080),(1280,720))

    def test_cached_resolutions_are_unique_and_fit_saved_source(self):
        from ccs.acquire import available_resolutions, resolution
        from ccs.common import write_json
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp);(job/'source.mp4').touch()
            write_json(job/'source.info.json',dict(height=720,formats=[self.video('720',720,1000),self.video('duplicate',720,2000),self.video('480',480,500),self.video('1080',1080,4000)]))
            with patch('ccs.acquire.job_for',return_value=(job,'https://www.youtube.com/watch?v=c4qtGGSgBQI')):
                result=available_resolutions('url')
            self.assertEqual(result['resolutions'],[720,480]);self.assertTrue(result['cached'])
        for bad in [True,-1,720.5,'720;echo']:
            with self.assertRaises(ValueError):resolution(bad)
