"""Run via the installed launcher (--module windows.verify) on Windows."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import unittest


def verify():
    assert os.name=='nt','This check must run on actual Windows.'
    from ccs.common import DATA_ROOT,MODELS,BIN,LOGO,probe,command,write_json,read_json
    from ccs.render import card,render
    from rapidocr_onnxruntime import RapidOCR
    from faster_whisper import WhisperModel
    from windows.launcher import APP,INSTALL,VERSION,URL,IDENTITY
    output=DATA_ROOT/'verification';output.mkdir(exist_ok=True)
    plan={'title':'God judges fairly','passage':'Romans 2:1–16','date':'2026-10-04','start':1,'end':7,'duration':8,'issues':[],'confirmed':True,'sections':[{'name':'Bible reading','start':1,'end':3},{'name':'Sermon','start':3,'end':7}]}
    card(output,plan,1280,720)
    text=' '.join(line[1] for line in RapidOCR()(str(output/'intro.png'))[0] or [])
    assert 'God judges fairly' in text,text
    assert LOGO.is_file()
    model=WhisperModel('small.en',device='cpu',compute_type='int8',download_root=str(MODELS),local_files_only=True)
    speech=Path(os.environ['CCS_TEST_SPEECH'])
    segments,info=model.transcribe(str(speech),language='en',beam_size=3)
    transcript=' '.join(s.text for s in segments)
    assert 'church' in transcript.casefold() and 'romans' in transcript.casefold(),transcript
    with tempfile.TemporaryDirectory(prefix='CCS test café ') as temporary:
        job=Path(temporary)
        command([BIN/'ffmpeg','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=25:duration=8','-f','lavfi','-i','sine=frequency=200:sample_rate=48000:duration=8','-filter_complex','[1:a]asplit=2[l][r];[r]volume=-1[inv];[l][inv]amerge=inputs=2[a]','-map','0:v','-map','[a]','-c:v','libx264','-c:a','pcm_s16le',job/'source.mkv'],job,'fixture')
        write_json(job/'source-path.json',{'path':str(job/'source.mkv')});write_json(job/'plan.json',plan)
        render(job)
        assert read_json(job/'validation.json')['audio_channels']==1
        assert read_json(job/'audio-channel-analysis.json')['correlation']<-.99
        assert len(probe(job/'finished.mp4')['chapters'])==3
        import shutil
        for name in ('finished.mp4','intro.png','validation.json','preview-validation.json','audio-channel-analysis.json'):
            shutil.copy2(job/name,output/name)
    launcher=APP/'windows/launcher.py'
    subprocess.run([str(INSTALL/'runtime/pythonw.exe'),str(launcher),'--open'],check=True)
    for _ in range(100):
        try:
            with urllib.request.urlopen(URL+'/api/health',timeout=2) as response:health=json.load(response)
            if health.get('instance')==IDENTITY:break
        except OSError:pass
        time.sleep(.2)
    else:raise RuntimeError('Windows launcher failed to start the web server.')
    with urllib.request.urlopen(URL+'/logo.png') as response:
        assert hashlib.sha256(response.read()).digest()==hashlib.sha256(LOGO.read_bytes()).digest()
    with urllib.request.urlopen(URL+'/api/jobs') as response:json.load(response)
    marker=DATA_ROOT/'setup.json';before=marker.stat().st_mtime_ns
    subprocess.run([sys.executable,str(launcher),'--setup'],check=True)
    assert marker.stat().st_mtime_ns==before
    # A second desktop launch must reconnect without creating a second server.
    subprocess.run([str(INSTALL/'runtime/pythonw.exe'),str(launcher),'--open'],check=True)
    from ccs.locking import file_lock
    with file_lock(DATA_ROOT/'.tools/pipeline.lock'):
        result=subprocess.run([sys.executable,str(launcher),'--shutdown'])
        assert result.returncode==2,'Shutdown interrupted a held processing lock.'
    with urllib.request.urlopen(URL+'/api/health') as response:assert json.load(response)['instance']==IDENTITY
    report={'version':VERSION,'windows':sys.getwindowsversion()._asdict() if hasattr(sys.getwindowsversion(),'_asdict') else list(sys.getwindowsversion()),'python':sys.version,'real_ocr':text,'offline_speech_inference':transcript,'church_logo_sha256':hashlib.sha256(LOGO.read_bytes()).hexdigest(),'synthetic_render_opposed_stereo':True,'non_ascii_paths':True,'chapters':True,'web_ui_logo_jobs_api':True,'repeat_setup_reused':True,'duplicate_launch':True,'active_render_shutdown_refused':True}
    (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':verify()
