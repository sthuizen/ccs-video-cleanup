#!/usr/bin/env python3
"""Run with the installed user venv in an isolated target distribution."""
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

from ccs.common import DATA_ROOT, MODELS
from ccs.render import card
from faster_whisper import WhisperModel
from rapidocr_onnxruntime import RapidOCR


def verify():
    libraries={name:importlib.import_module(name).__file__ for name in ('numpy','scipy','PIL','cv2','av')}
    assert all(path.startswith('/usr/lib/python3/dist-packages/') for path in libraries.values()), libraries
    WhisperModel('small.en',device='cpu',compute_type='int8',download_root=str(MODELS),local_files_only=True)
    with tempfile.TemporaryDirectory(prefix='ccs-installed-check-') as temporary:
        job=Path(temporary)
        card(job,{'title':'God judges fairly','passage':'Romans 2:1–16','date':'2026-10-04'},1280,720)
        lines,_=RapidOCR()(str(job/'intro.png'))
        text=' '.join(line[1] for line in lines or [])
        assert 'God judges fairly' in text,text
        if os.environ.get('CCS_VERIFY_OUTPUT'):
            output=Path(os.environ['CCS_VERIFY_OUTPUT']);output.mkdir(parents=True,exist_ok=True)
            import shutil
            shutil.copy2(job/'intro.png',output/'intro.png')
    marker=DATA_ROOT/'setup.json';before=marker.stat().st_mtime_ns
    subprocess.run(['/usr/bin/ccs-video-cleanup','setup'],check=True)
    assert before==marker.stat().st_mtime_ns,'Repeated setup unexpectedly rebuilt tools'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=subprocess.Popen(['/usr/bin/ccs-video-cleanup','serve','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        for attempt in range(50):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/jobs',timeout=1) as response:json.load(response)
                break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Installed web server failed to start')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=2) as response:
            assert b'<html' in response.read().lower()
    finally:
        server.terminate();server.wait(timeout=5)
    report={'system_libraries':libraries,'offline_speech_model':True,'ocr_inference':True,'repeat_setup_reused':True,'web_ui_and_jobs_api':True}
    print(json.dumps(report,indent=2))
    if os.environ.get('CCS_VERIFY_OUTPUT'):
        (Path(os.environ['CCS_VERIFY_OUTPUT'])/'verification.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':verify()
