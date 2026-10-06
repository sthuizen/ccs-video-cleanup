import unittest, tempfile
from pathlib import Path
from ccs.analyze import refs, dates
from ccs.common import seconds, write_json, read_json, command, BIN
from ccs.render import mono_filter, validate, render
class Rules(unittest.TestCase):
    def test_spoken_reference(self):
        self.assertEqual(refs('Romans chapter two verses one to sixteen'),['Romans 2:1–16'])
        self.assertEqual(refs('second Corinthians chapter five verse twenty one'),['2 Corinthians 5:21'])
        self.assertEqual(refs('Romans 2:1-16'),['Romans 2:1–16'])
    def test_service_date(self):
        self.assertEqual(dates('11:15am Sunday Gathering - 4th October 2026'),['2026-10-04'])
        self.assertEqual(dates('31st February 2026'),[])
    def test_invalid_cut(self):
        with self.assertRaises(ValueError): validate(dict(start=10,end=5,duration=20,title='A',date='2026-10-04',passage='Romans 2'))
        self.assertEqual(seconds('01:02:03'),3723)
class Media(unittest.TestCase):
    def test_opposed_stereo_and_full_render(self):
        with tempfile.TemporaryDirectory(prefix='ccs-test-') as tmp:
            j=Path(tmp)
            command([BIN/'ffmpeg','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=25:duration=8','-f','lavfi','-i','sine=frequency=200:sample_rate=48000:duration=8','-filter_complex','[1:a]asplit=2[l][r];[r]volume=-1[inv];[l][inv]amerge=inputs=2[a]','-map','0:v','-map','[a]','-c:v','libx264','-c:a','pcm_s16le',j/'source.mkv'],j,'fixture')
            write_json(j/'source-path.json',{'path':str(j/'source.mkv')})
            self.assertIn('c0=c',mono_filter(j,j/'source.mkv',0,8))
            self.assertLess(read_json(j/'audio-channel-analysis.json')['correlation'],-.99)
            write_json(j/'plan.json',dict(start=1,end=7,duration=8,title='God judges fairly',passage='Romans 2:1–16',date='2026-10-04',issues=[],confirmed=True,sections=[{'name':'Bible reading','start':1,'end':3},{'name':'Sermon','start':3,'end':7}]))
            render(j)
            self.assertEqual(read_json(j/'validation.json')['audio_channels'],1)
            self.assertTrue((j/'finished.mp4').is_file())
            from ccs.common import probe
            chapters=probe(j/'finished.mp4')['chapters']
            self.assertEqual([c['tags']['title'] for c in chapters],['Intro','Bible reading','Sermon'])
            self.assertLessEqual(float(chapters[-1]['end_time']),11.1)
            from ccs.preview import ready
            self.assertTrue(ready(j))
            preview=probe(j/'preview.mp4')
            pv=next(s for s in preview['streams'] if s['codec_type']=='video')
            self.assertEqual((pv['width'],pv['height']),(640,360))
            self.assertEqual(pv['profile'],'Constrained Baseline')
            import json, subprocess
            def audio_packets(path):
                return json.loads(subprocess.check_output([str(BIN/'ffprobe'),'-v','error','-select_streams','a:0','-show_packets','-show_data_hash','sha256','-show_entries','packet=pts_time,data_hash','-of','json',str(path)]))['packets']
            master=audio_packets(j/'finished.mp4'); lighter=audio_packets(j/'preview.mp4')
            self.assertEqual([p['data_hash'] for p in master],[p['data_hash'] for p in lighter])
            self.assertLess(abs(float(master[1]['pts_time'])-float(lighter[1]['pts_time'])),.001)
            (j/'finished.mp4').touch()
            self.assertFalse(ready(j))
if __name__=='__main__': unittest.main()
