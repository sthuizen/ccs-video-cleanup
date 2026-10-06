import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from ccs.locking import file_lock, LockBusy

class FileLock(unittest.TestCase):
    def test_competing_process_and_release(self):
        with tempfile.TemporaryDirectory(prefix='ccs-lock-') as temporary:
            path=Path(temporary)/'nested'/'pipeline.lock'
            script='from ccs.locking import file_lock,LockBusy; import sys\ntry:\n with file_lock(sys.argv[1]): pass\nexcept LockBusy: sys.exit(7)'
            # Embedded Windows Python uses its explicit app path; normal source tests use cwd.
            with file_lock(path):
                result=subprocess.run([sys.executable,'-c',script,str(path)],capture_output=True)
                self.assertEqual(result.returncode,7,result.stderr.decode(errors='replace'))
            result=subprocess.run([sys.executable,'-c',script,str(path)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))

    def test_exception_releases_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'lock'
            with self.assertRaises(RuntimeError):
                with file_lock(path):raise RuntimeError('test failure')
            with file_lock(path):pass
