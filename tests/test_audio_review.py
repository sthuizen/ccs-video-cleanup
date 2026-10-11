"""Preview provenance, phase safety, tuning and render handoff."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import subprocess
from ccs import audio, audio_review as review
from ccs.common import BIN, command, read_json, write_json
from ccs.render import render

class AudioReview(unittest.TestCase):
    def test_parameters_reject_nonfinite_unknown_and_out_of_range(self):
        for p in ({'filter':'volume=100'},{'suppression':float('nan')},{'compression':5},{'loudness':True},{'clarity':'2'}):
            with self.assertRaises(ValueError): review.parameters(p)
        self.assertEqual(review.parameters({})['suppression'],20)

    def test_samples_must_fit_current_selection(self):
        plan=dict(start=10,end=60)
        self.assertEqual(review.validate_samples(plan,['00:00:10',42])[1]['start'],42)
        for samples in ([9,42],[10,43],[float('nan'),42],[10]):
            with self.assertRaises(ValueError): review.validate_samples(plan,samples)

    def test_preview_tuning_provenance_and_actual_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=Path(tmp)
            command([BIN/'ffmpeg','-y','-f','lavfi','-i','testsrc2=size=160x90:rate=10:duration=12',
                '-f','lavfi','-i','aevalsrc=0.015*sin(2*PI*180*t)*(1+2*gte(t\\,6))| -0.015*sin(2*PI*180*t)*(1+2*gte(t\\,6)):s=48000:d=12',
                '-c:v','libx264','-c:a','pcm_s16le',j/'source.mkv'],j,'fixture')
            write_json(j/'source-path.json',{'path':str(j/'source.mkv')})
            plan=dict(start=0,end=12,duration=12,title='Test',date='2026-10-04',passage='Romans 2')
            # Tests exercise the real FFmpeg chain without requiring optional neural inference.
            base=dict(version=2,filter=audio.FILTER,target_lufs=-20,maximum_gain_db=18,limiter_peak_dbfs=-2,method='ffmpeg-gentle-speech-cleanup')
            with patch.object(audio,'profile',return_value=base):
                first=review.create(j,plan,[0,0])
                self.assertEqual(len(first['trials']),3)
                self.assertLess(read_json(j/'audio-trials'/first['revision']/'audio-channel-analysis.json')['correlation'],-.99)
                self.assertFalse((j/'cleaned-audio.wav').exists())
                wave=j/first['trials'][0]['clips'][0]
                signal=np.frombuffer(subprocess.check_output([str(BIN/'ffmpeg'),'-v','error','-i',str(wave),'-f','f32le','-']),'<f4')
                self.assertGreater(np.sqrt(np.mean(signal**2)),.001,'Opposed channels must retain their speech')
                self.assertAlmostEqual(len(signal)/48000,12,delta=.05)
                params={**review.DEFAULTS,'clarity':2,'compression':1.5,'hiss':0}
                second=review.create(j,plan,[0,0],params)
                self.assertEqual(len(second['trials']),4)
                self.assertEqual(second['trials'][:3],first['trials'])
                self.assertTrue(wave.is_file())
                for revision,selection in ((first['revision'],plan),(second['revision'],{**plan,'end':11})):
                    with self.assertRaises(ValueError): review.choose(j,selection,revision,'balanced')
                self.assertFalse((j/'audio-choice.json').exists())
                configured=review.choose(j,plan,second['revision'],'custom')
                self.assertEqual(review.selected_profile(j,plan),configured)
                self.assertEqual(review.selected_profile(j,{**plan,'end':11}),base)
                write_json(j/'plan.json',plan)
                render(j,False)
                rendered=read_json(j/'media-settings.json')
                self.assertEqual(read_json(j/'validation.json')['full_decode'],'passed')
                self.assertEqual(read_json(j/'validation.json')['audio_profile'],configured)
                self.assertEqual(rendered['audio_profile'],configured)
                self.assertIn('acompressor',read_json(j/'audio-settings.json')['key']['profile']['filter'])
                source=j/'source.mkv';source.touch()
                with self.assertRaises(ValueError): review.choose(j,plan,second['revision'],'custom')

    def test_failed_preview_preserves_previous_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=Path(tmp); (j/'source.mp4').write_bytes(b'fake source')
            write_json(j/'audio-trials.json',{'revision':'completed'})
            with patch('ccs.render.mono_filter',side_effect=RuntimeError('decoder failed')):
                with self.assertRaises(RuntimeError): review.create(j,dict(start=0,end=30),[0,10])
            self.assertEqual(read_json(j/'audio-trials.json'),{'revision':'completed'})

if __name__=='__main__': unittest.main()
