import unittest
from ccs.common import ROOT, read_json
from ccs.analyze import analyze, refs
from ccs.transcribe import split_gaps
from ccs.scripture import infer_reading
class Analysis(unittest.TestCase):
    def test_reading_announcement(self):
        self.assertEqual(refs('We are in Romans, beginning of chapter two.'),['Romans 2'])
    def test_word_gap_preserves_handoff(self):
        s=[{'start':1,'end':20,'text':'Amen thank you','words':[{'start':1,'end':2,'word':' Amen'},{'start':18,'end':19,'word':' thank'},{'start':19,'end':20,'word':' you'}]}]
        parts=split_gaps(s)
        self.assertEqual(parts[0]['end'],2)
        self.assertEqual(parts[1]['start'],18)
    def test_local_verse_range(self):
        path=ROOT/'assets/bible/engwebp_vpl.txt'
        if not path.exists():self.skipTest('Bible dataset not installed')
        selected=[]
        for line in path.read_text().splitlines():
            if line.startswith(('ROM 2:1 ','ROM 2:2 ','ROM 2:3 ','ROM 2:4 ','ROM 2:5 ')):selected.append(line.split(' ',2)[2])
        segments=[{'start':10+i*30,'end':20+i*30,'text':t} for i,t in enumerate(selected)]
        result=infer_reading('Romans 2',segments,0)
        self.assertEqual(result['passage'],'Romans 2:1–5')
        self.assertEqual(result['confidence'],'supported')
if __name__=='__main__':unittest.main()
