import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from ccs.common import ROOT, read_json
from ccs.analyze import analyze, refs, reading_candidates, CLOSE, clamp_sections
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
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith(('ROM 2:1 ','ROM 2:2 ','ROM 2:3 ','ROM 2:4 ','ROM 2:5 ')):selected.append(line.split(' ',2)[2])
        segments=[{'start':10+i*30,'end':20+i*30,'text':t} for i,t in enumerate(selected)]
        result=infer_reading('Romans 2',segments,0)
        self.assertEqual(result['passage'],'Romans 2:1–5')
        self.assertEqual(result['confidence'],'supported')
    def bible_segments(self, code, chapter, numbers, start=100):
        path=ROOT/'assets/bible/engwebp_vpl.txt'
        if not path.exists():self.skipTest('Bible dataset not installed')
        wanted={f'{code} {chapter}:{n}' for n in numbers}
        selected=[line.split(' ',2)[2] for line in path.read_text(encoding='utf-8').splitlines() if ' '.join(line.split(' ',2)[:2]) in wanted]
        return [{'start':start+i*15,'end':start+10+i*15,'text':text} for i,text in enumerate(selected)]

    def test_fragmented_caption_reference(self):
        self.assertEqual(refs('Our reading is from Romans chapter 1 vers 8 to 17'),['Romans 1:8–17'])
        segments=[{'start':60,'end':65,'text':'Our reading today is from Romans chapter'},
                  {'start':64,'end':70,'text':'1 vers 8 to 17. Church Bibles page 1128.'}]
        candidate=reading_candidates(segments)[0]
        self.assertEqual(candidate['passages'],['Romans 1:8–17'])

    def test_reference_and_detached_range_need_ordered_scripture(self):
        announcement=[{'start':20,'end':25,'text':'It is there in Acts chapter two.'},
                      {'start':75,'end':80,'text':'42-47, page 194.'}]
        self.assertEqual(reading_candidates(announcement),[])
        reading=self.bible_segments('ACT',2,[42,44,47])
        candidate=reading_candidates(announcement+reading)[0]
        self.assertEqual(candidate['passages'],['Acts 2:42–47'])
        self.assertEqual(candidate['alignment']['confidence'],'supported')
        self.assertEqual(candidate['alignment']['reading_ends'],reading[-1]['end'])
        self.assertIsNone(infer_reading('Acts 2',reading,20))

    def test_recovered_announcement_replaces_bare_reference(self):
        segments=[{'start':20,'end':25,'text':'It is there in Acts chapter two.'},
                  {'start':75,'end':80,'text':'Our reading is Acts chapter two verses forty two to forty seven.'}]
        candidate=reading_candidates(segments+self.bible_segments('ACT',2,[42,44,47]))[0]
        self.assertEqual(candidate['kind'],'announcement')
        self.assertEqual(candidate['time'],75)

    def test_sermon_illustration_is_not_closing_hymn(self):
        self.assertIsNone(CLOSE.search('You see, singing together involves much more than praise.'))
        self.assertIsNotNone(CLOSE.search("We're going to sing next, reflecting on the cross."))

    def test_passage_survives_unresolved_ending(self):
        segments=[{'start':60,'end':65,'text':'Our reading today is from Romans chapter two.'}]
        segments+=self.bible_segments('ROM',2,[1,2,3,4,5])
        with tempfile.TemporaryDirectory() as directory:
            job=Path(directory)
            (job/'source.info.json').write_text('{"title":"Service 4 October 2026"}',encoding='utf-8')
            with patch('ccs.analyze.probe',return_value={'format':{'duration':'3000'}}),patch('ccs.analyze.status'):
                plan=analyze(job,job/'source.mp4',{'segments':segments},[])
        self.assertEqual(plan['passage'],'Romans 2:1–5')
        self.assertIsNotNone(plan['start'])
        self.assertIsNone(plan['end'])
        self.assertTrue(any('sermon ending' in issue for issue in plan['issues']))

    def test_compound_spoken_numbers(self):
        self.assertEqual(refs('Acts chapter two verses forty two to forty seven'),['Acts 2:42–47'])
        self.assertEqual(refs('First Corinthians chapter two verses twenty-one through twenty-three'),['1 Corinthians 2:21–23'])

    def test_reader_introduction_preserved_but_long_host_lead_in_excluded(self):
        reading=self.bible_segments('ROM',2,[1,2,3,4,5],start=100)
        for announcement_time,expected in ((80,79.3),(50,99.3)):
            segments=[{'start':announcement_time,'end':announcement_time+5,'text':'Our reading is from Romans chapter two.'}]+reading
            segments += [{'start':1000,'end':1005,'text':'Let us pray.'},
                         {'start':1010,'end':1020,'text':'In the name of Jesus. Amen.'},
                         {'start':1025,'end':1030,'text':"We are going to sing our final hymn."}]
            with tempfile.TemporaryDirectory() as directory:
                job=Path(directory)
                (job/'source.info.json').write_text('{"title":"Service 4 October 2026"}',encoding='utf-8')
                with patch('ccs.analyze.probe',return_value={'format':{'duration':'3000'}}),patch('ccs.analyze.status'):
                    plan=analyze(job,job/'source.mp4',{'segments':segments},[])
            self.assertAlmostEqual(plan['start'],expected)
            self.assertAlmostEqual(plan['end'],1020.5)

    def test_reviewed_cut_clamps_sections_and_points(self):
        plan={'start':130,'end':500,'sections':[
            {'name':'Bible reading','start':100,'end':160},
            {'name':'Sermon','start':160,'end':1000},
            {'name':'Closing prayer','start':1000,'end':1020}],
            'sermon_points':[{'name':'Earlier','start':120},{'name':'Within cut','start':300},{'name':'Later','start':600}]}
        clamp_sections(plan)
        self.assertEqual(plan['sections'],[{'name':'Bible reading','start':130,'end':160},{'name':'Sermon','start':160,'end':500}])
        self.assertEqual([point['start'] for point in plan['sermon_points']],[300])
        chapter_offsets=[5+section['start']-plan['start'] for section in plan['sections']]
        self.assertEqual(chapter_offsets,[5,35])
        plan['start']=200
        clamp_sections(plan)
        self.assertEqual(plan['sections'],[{'name':'Sermon','start':200,'end':500}])

    def test_saved_review_controls_cut_and_chapters(self):
        segments=[{'start':60,'end':65,'text':'Our reading today is from Romans chapter two.'}]
        segments+=self.bible_segments('ROM',2,[1,2,3,4,5])
        segments += [{'start':1000,'end':1005,'text':'Let us pray.'},
                     {'start':1010,'end':1020,'text':'In the name of Jesus. Amen.'},
                     {'start':1025,'end':1030,'text':'We are going to sing our final hymn.'}]
        review={'start':130,'end':500,'passage':'Romans 2:1–5','title':'Operator title','date':'2026-10-04','confirmed':True}
        with tempfile.TemporaryDirectory() as directory:
            job=Path(directory)
            (job/'source.info.json').write_text('{"title":"Service 4 October 2026"}',encoding='utf-8')
            (job/'review.json').write_text(json.dumps(review),encoding='utf-8')
            with patch('ccs.analyze.probe',return_value={'format':{'duration':'3000'}}),patch('ccs.analyze.status'):
                plan=analyze(job,job/'source.mp4',{'segments':segments},[])
        for field,value in review.items():self.assertEqual(plan[field],value)
        self.assertEqual(plan['sections'][0]['start'],130)
        self.assertEqual(plan['sections'][-1]['end'],500)
        self.assertEqual([5+section['start']-plan['start'] for section in plan['sections']],[5,45])
        self.assertTrue(all(130<=section['start']<section['end']<=500 for section in plan['sections']))

    def test_unknown_transition_is_not_invented_by_cut_clamping(self):
        plan={'start':130,'end':500,'sections':[
            {'name':'Bible reading','start':None,'end':None},
            {'name':'Sermon and closing prayer','start':None,'end':None}]}
        clamp_sections(plan)
        self.assertEqual(plan['sections'][0]['start'],130)
        self.assertIsNone(plan['sections'][0]['end'])
        self.assertIsNone(plan['sections'][1]['start'])
        self.assertEqual(plan['sections'][1]['end'],500)

    def test_keep_open_after_reader_is_not_second_reading(self):
        segments=[{'start':60,'end':65,'text':'Our reading today is from Romans chapter two.'}]
        segments+=self.bible_segments('ROM',2,[1,2,3,4,5])
        segments.append({'start':185,'end':190,'text':'If you could keep that open to Romans chapter two.'})
        self.assertEqual(len(reading_candidates(segments)),1)

if __name__=='__main__':unittest.main()
