import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ccs import audio_setup


class EnhancerSetup(unittest.TestCase):
    def test_bad_download_preserves_existing_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'bin/deep-filter'; target.parent.mkdir()
            target.write_bytes(b'previous tool')
            with patch('ccs.audio_setup.platform.system',return_value='Linux'), patch('ccs.audio_setup.platform.machine',return_value='x86_64'), patch('ccs.audio_setup.urllib.request.urlopen',return_value=io.BytesIO(b'bad download')):
                with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):
                    audio_setup.install(target.parent)
            self.assertEqual(target.read_bytes(),b'previous tool')

    def test_verified_tool_repairs_notices_without_downloading_again(self):
        content=b'synthetic verified tool'
        digest=hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'bin/deep-filter'; target.parent.mkdir()
            target.write_bytes(content)
            with patch('ccs.audio_setup.platform.system',return_value='Linux'), patch('ccs.audio_setup.platform.machine',return_value='x86_64'), patch('ccs.audio_setup.SHA256',digest), patch('ccs.audio_setup.urllib.request.urlopen',side_effect=lambda url,**kwargs:io.BytesIO(b'license notice')) as fetch:
                self.assertEqual(audio_setup.install(target.parent),target)
                self.assertEqual(fetch.call_count,2)
                self.assertTrue(all('/LICENSE-' in call.args[0] for call in fetch.call_args_list))
                self.assertEqual(audio_setup.install(target.parent),target)
                self.assertEqual(fetch.call_count,2)
            self.assertEqual(target.read_bytes(),content)
            self.assertTrue(target.stat().st_mode & 0o100)


if __name__=='__main__':unittest.main()
