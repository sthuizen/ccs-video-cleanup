import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ccs import exports
from ccs.audio_review import identity, DEFAULTS, settings
from ccs.common import BIN,command,write_json,read_json,probe

class Exports(unittest.TestCase):
    def test_destination_validation(self):
        self.assertEqual(exports.destinations(),['youtube'])
        self.assertEqual(exports.destinations(['spotify','youtube']),['youtube','spotify'])
        for value in ([],['unknown'],'spotify',{}):
            with self.assertRaises(ValueError):exports.destinations(value)

    def test_podcast_only_uses_chosen_conditioning_and_no_video_intro(self):
        with tempfile.TemporaryDirectory(prefix='ccs-podcast-test-') as tmp:
            job=Path(tmp)
            command([BIN/'ffmpeg','-y','-f','lavfi','-i','testsrc2=size=160x90:rate=25:duration=5',
                '-f','lavfi','-i','sine=frequency=400:sample_rate=48000:duration=5',
                '-filter_complex','[1:a]asplit=2[l][r];[r]volume=-1[inv];[l][inv]amerge=inputs=2[a]',
                '-map','0:v','-map','[a]','-c:v','libx264','-c:a','pcm_s16le',job/'source.mkv'],job,'fixture')
            write_json(job/'source-path.json',{'path':str(job/'source.mkv')})
            plan=dict(start=.5,end=4.5,duration=5,title='Mercy',date='2026-10-11',passage='Romans 2',confirmed=True,issues=[])
            write_json(job/'plan.json',plan)
            chosen={**DEFAULTS,'suppression':0,'loudness':-18,'clarity':1,'compression':1.5}
            write_json(job/'audio-choice.json',dict(selection=identity(job,plan),parameters=chosen))
            with patch('ccs.exports.render') as video:exports.create(job,['spotify']);video.assert_not_called()
            self.assertFalse((job/'finished.mp4').exists())
            self.assertEqual(read_json(job/'status.json')['stage'],'Finished')
            self.assertEqual(read_json(job/'export-settings.json')['outputs'],['spotify'])
            validation=read_json(job/'podcast-validation.json')
            self.assertEqual(validation['audio_profile'],settings(chosen))
            self.assertLess(abs(validation['duration']-4),.1)
            self.assertLess(validation['audio_true_peak_db'],-.5)
            self.assertGreater(validation['audio_lufs'],-40,'Opposed channels must not cancel speech')
            self.assertLess(abs(validation['audio_lufs']-chosen['loudness']),1.5,'Chosen normalization must also be applied to the podcast')
            stream=probe(job/'podcast.mp3')['streams'][0]
            self.assertEqual((stream['codec_name'],stream['channels'],stream['sample_rate']),('mp3',1,'48000'))
            self.assertTrue(exports.podcast_ready(job,plan))
            self.assertFalse(exports.podcast_ready(job,{**plan,'title':'Changed title'}))
            write_json(job/'audio-choice.json',dict(selection=identity(job,plan),parameters={**chosen,'clarity':2}))
            self.assertFalse(exports.podcast_ready(job,plan),'Changed conditioning must hide stale podcast')

    def test_both_and_video_only_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp);write_json(job/'plan.json',dict(start=0,end=5,duration=5,title='Title',passage='Romans 2',date='2026-10-11',confirmed=True))
            with patch('ccs.exports.render') as video,patch('ccs.exports.podcast') as audio:
                exports.create(job,['youtube','spotify'],False)
                video.assert_called_once_with(job,False,finish=False);audio.assert_called_once()
            with patch('ccs.exports.render') as video,patch('ccs.exports.podcast') as audio:
                exports.create(job)
                video.assert_called_once();audio.assert_not_called()
