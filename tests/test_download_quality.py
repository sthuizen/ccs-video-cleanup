import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp import YoutubeDL, parse_options
from ccs.acquire import acquire


class DownloadQuality(unittest.TestCase):
    def select(self, formats):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ccs.acquire.command') as command:
                acquire(Path(tmp), 'https://www.youtube.com/watch?v=c4qtGGSgBQI')
            args = [str(x) for x in command.call_args.args[0][1:]]
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

    def test_bitrate_takes_priority_over_resolution_and_codec(self):
        formats = [self.video('high-bitrate', 720, 5000),
                   self.video('high-resolution', 2160, 3000, 'av01'),
                   self.audio('audio', 256)]
        self.assertEqual(self.select(formats), 'high-bitrate+audio')

    def test_combined_stream_fallback(self):
        formats = [dict(format_id='combined', ext='mp4', url='https://example.com/combined',
                        vcodec='avc1', acodec='mp4a', height=2160, vbr=6000, abr=256)]
        self.assertEqual(self.select(formats), 'combined')
