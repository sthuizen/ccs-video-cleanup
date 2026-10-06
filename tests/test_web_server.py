import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from ccs.common import write_json,read_json

class WebServer(unittest.TestCase):
    def test_utf8_metadata_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'details.json'
            value={'title':'God’s mercy — café','passage':'Romans 2:1–16'}
            write_json(path,value)
            self.assertEqual(read_json(path),value)
            self.assertIn('—'.encode('utf-8'),path.read_bytes())

    def test_health_logo_and_linux_shutdown_guard(self):
        from ccs.common import ROOT
        with tempfile.TemporaryDirectory() as temporary:
            data=Path(temporary);logo=data/'church-logo.png';logo.write_bytes(b'fixture-logo')
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env=os.environ.copy();env.update(CCS_DATA_DIR=str(data),CCS_LOGO=str(logo),CCS_APP_ID='test-instance')
            env.pop('CCS_WINDOWS_LAUNCHER',None)
            import PIL
            dependencies=str(Path(PIL.__file__).parent.parent)
            entry='import sys; sys.path.insert(0,'+repr(dependencies)+'); from ccs.cli import main; main()'
            server=subprocess.Popen([sys.executable,'-c',entry,'serve','--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                url=f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url+'/api/health',timeout=.2) as response:health=json.load(response)
                        break
                    except OSError:time.sleep(.05)
                else:self.fail('Server did not start')
                self.assertEqual(health['instance'],'test-instance')
                with urllib.request.urlopen(url+'/logo.png') as response:self.assertEqual(response.read(),logo.read_bytes())
                request=urllib.request.Request(url+'/api/shutdown',data=b'{"instance":"test-instance"}',headers={'Content-Type':'application/json','X-CCS-Request':'1'})
                with self.assertRaises(urllib.error.HTTPError) as failure:urllib.request.urlopen(request)
                self.assertEqual(failure.exception.code,400)
                self.assertIsNone(server.poll())
            finally:server.terminate();server.wait(timeout=10)
