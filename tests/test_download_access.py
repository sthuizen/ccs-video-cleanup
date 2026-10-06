import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ccs.acquire import acquire


class DownloadAccess(unittest.TestCase):
    def test_sign_in_block_does_not_immediately_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ccs.acquire.command', side_effect=RuntimeError("ERROR: Sign in to confirm you're not a bot")) as command:
                with self.assertRaisesRegex(RuntimeError, 'Download access to firefox'):
                    acquire(Path(tmp), 'https://www.youtube.com/watch?v=c4qtGGSgBQI')
                self.assertEqual(command.call_count, 1)

    def test_caption_rate_limit_retries_without_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ccs.acquire.command', side_effect=[RuntimeError('ERROR: Unable to download video subtitles: HTTP Error 429'), None]) as command:
                acquire(Path(tmp), 'https://www.youtube.com/watch?v=c4qtGGSgBQI', 'firefox')
                retry = command.call_args.args[0]
                self.assertNotIn('--write-subs', retry)
                self.assertNotIn('--write-auto-subs', retry)
                self.assertIn('--cookies-from-browser', retry)

    def test_video_rate_limit_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ccs.acquire.command', side_effect=RuntimeError('ERROR: HTTP Error 429')) as command:
                with self.assertRaisesRegex(RuntimeError, 'wait before retrying'):
                    acquire(Path(tmp), 'https://www.youtube.com/watch?v=c4qtGGSgBQI')
                self.assertEqual(command.call_count, 1)
