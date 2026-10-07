import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ccs.transcribe import refinement_windows, merge_refinement, split_gaps, refine_transcript


class TranscriptionRefinement(unittest.TestCase):
    def test_missing_book_still_checks_a_clear_reading_announcement(self):
        transcript = {'method': 'youtube-captions', 'segments': [
            {'start': 100, 'end': 106, 'text': 'Our reading this morning is on page 194'},
            {'start': 112, 'end': 118, 'text': 'They devoted themselves to the apostles teaching'}]}
        windows = refinement_windows(transcript, {'duration': 1000, 'start': None,
                                                  'end': None, 'passage': None})
        self.assertEqual(windows, [(70., 220.)])

    def test_title_and_date_do_not_trigger_audio(self):
        transcript = {'method': 'youtube-captions', 'segments': [{'start': 1977, 'end': 1985, 'text': 'Acts chapter 2'}]}
        plan = {'duration': 5000, 'start': 2068, 'end': 3730, 'passage': 'Acts 2:42–47',
                'issues': ['No explicit sermon title found', 'No service date found']}
        self.assertEqual(refinement_windows(transcript, plan), [])
        plan['evidence'] = {'passage': {'requires_local_verification': True}}
        self.assertEqual(refinement_windows(transcript, plan), [(1947.0, 2097.0)])

    def test_checks_are_bounded_and_prioritize_reading(self):
        segments = [{'start': x, 'end': x+5, 'text': 'Romans chapter one'} for x in (1000, 1500, 2000, 2500, 3000)]
        segments.append({'start': 2490, 'end': 2495, 'text': 'Our reading today'})
        windows = refinement_windows({'method': 'youtube-captions', 'segments': segments},
                                     {'duration': 5000, 'start': None, 'end': None, 'passage': None})
        self.assertEqual(len(windows), 3)
        self.assertTrue(any(a <= 2490 and b >= 2505 for a,b in windows))
        self.assertLessEqual(sum(b-a for a, b in windows), 450)

    def test_merge_keeps_outside_caption_and_absolute_offsets(self):
        segments = [{'start': 90, 'end': 98, 'text': 'before'}, {'start': 99, 'end': 105, 'text': 'garbled'},
                    {'start': 130, 'end': 135, 'text': 'after'}]
        recovered = [{'start': 102.5, 'end': 110, 'text': 'Our reading is Acts chapter two'}]
        merged = merge_refinement(segments, [(100, 120)], recovered)
        self.assertEqual([s['text'] for s in merged], ['before', recovered[0]['text'], 'after'])
        self.assertEqual(merged[1]['start'], 102.5)
        self.assertEqual(segments[1]['text'], 'garbled')

    def test_ending_check_and_early_reading_share_budget(self):
        transcript = {'method': 'youtube-captions', 'segments': [
            {'start': 30, 'end': 40, 'text': 'Our reading from Acts chapter two'},
            {'start': 1500, 'end': 1510, 'text': 'Romans chapter one'},
            {'start': 2000, 'end': 2010, 'text': 'Romans chapter two'}]}
        plan = {'duration': 5000, 'start': 45, 'end': 4900, 'passage': 'Acts 2',
                'issues': ['The sermon ending is approximate. Confirm the last words before the closing song.']}
        windows = refinement_windows(transcript, plan)
        self.assertIn((0, 150), windows)
        self.assertIn((4810, 4930), windows)
        self.assertLessEqual(len(windows), 3)
        self.assertLessEqual(sum(b-a for a, b in windows), 450)

    def test_split_preserves_verification_provenance(self):
        segment = {'start': 10, 'end': 50, 'text': 'Amen Thank you', 'source': 'local-check',
                   'words': [{'start': 10, 'end': 11, 'word': ' Amen'}, {'start': 49, 'end': 50, 'word': ' Thank you'}]}
        parts = split_gaps([segment])
        self.assertEqual([(s['start'], s['end']) for s in parts], [(10, 11), (49, 50)])
        self.assertTrue(all(s['source'] == 'local-check' for s in parts))

    def test_local_offsets_cache_and_original_preserved(self):
        transcript = {'method': 'youtube-captions', 'segments': [{'start': 100, 'end': 105, 'text': 'Acts chapter two'}]}
        plan = {'duration': 1000, 'start': None, 'end': None, 'passage': None}
        word = SimpleNamespace(start=2, end=3, word=' Our reading')
        segment = SimpleNamespace(start=2, end=3, text=' Our reading', words=[word])
        model = SimpleNamespace(transcribe=lambda *args, **kwargs: (iter([segment]), None))
        fake_module = SimpleNamespace(WhisperModel=lambda *args, **kwargs: model)
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory); video = job/'source.mp4'; video.write_bytes(b'synthetic source')
            original = job/'transcript.json'; original.write_text('original cached transcript', encoding='utf-8')
            with patch.dict('sys.modules', {'faster_whisper': fake_module}), patch('ccs.render.mono_filter', return_value='pan=mono|c0=c0'), patch('ccs.transcribe.command') as command, patch('ccs.transcribe.status'):
                result = refine_transcript(job, video, transcript, plan)
                self.assertEqual(result['segments'][0]['start'], 72)
                self.assertEqual(result['verified_windows'], [[70.0, 220.0]])
                self.assertEqual(refine_transcript(job, video, transcript, plan), result)
                self.assertEqual(command.call_count, 1)
                video.write_bytes(b'changed source length')
                refine_transcript(job, video, transcript, plan)
                self.assertEqual(command.call_count, 2)
            self.assertEqual(original.read_text(encoding='utf-8'), 'original cached transcript')
