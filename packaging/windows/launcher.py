"""Windows entry point: first-run preparation and a persistent loopback server."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = Path(__file__).resolve().parent.parent
INSTALL = APP.parent
DATA = Path(os.environ.get('CCS_DATA_DIR', str(Path(os.environ['LOCALAPPDATA'])/'CCSVideoCleanup')))
VERSION = '1.2.0'
PORT = int(os.environ.get('CCS_PORT', '8765'))
URL = f'http://127.0.0.1:{PORT}'
LIB = DATA/'python-packages'
TOOLS = DATA/'tools'
MODELS = DATA/'models/whisper'
IDENTITY = hashlib.sha256(str(DATA.resolve()).casefold().encode()).hexdigest()[:16]
DATA.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(LIB), str(APP)]
os.environ.update(CCS_DATA_DIR=str(DATA), CCS_BIN_DIR=str(TOOLS), CCS_MODEL_DIR=str(MODELS),
                  CCS_LOGO=str(APP/'assets/church-logo.png'), CCS_YTDLP=str(TOOLS/'yt-dlp.cmd'),
                  PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONNOUSERSITE='1',
                  CCS_APP_ID=IDENTITY, CCS_APP_VERSION=VERSION, CCS_WINDOWS_LAUNCHER=str(Path(__file__).resolve()))
os.environ['PATH'] = str(TOOLS) + os.pathsep + str(LIB/'bin') + os.pathsep + os.environ['PATH']
for stream in (sys.stdout,sys.stderr):
    if stream is not None:stream.reconfigure(encoding='utf-8',errors='replace')
HIDDEN = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
from ccs.locking import file_lock, LockBusy


def write_json(path, value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)


def ready():
    try:
        record=json.loads((DATA/'setup.json').read_text(encoding='utf-8'))
        return record.get('version')==VERSION and (TOOLS/'ffmpeg.exe').exists() and (LIB/'faster_whisper').is_dir()
    except (OSError,ValueError): return False


def run(args):
    with (DATA/'setup.log').open('a',encoding='utf-8') as log:
        subprocess.run([str(x) for x in args],check=True,stdout=log,stderr=subprocess.STDOUT,**HIDDEN)


def verified_open(url, timeout=90):
    import certifi
    context=ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return urllib.request.urlopen(url, timeout=timeout, context=context)


def download(item, target, progress):
    if target.exists():
        with target.open('rb') as existing:
            if hashlib.file_digest(existing,'sha256').hexdigest()==item['sha256']:return
    partial=target.with_suffix(target.suffix+'.partial')
    digest=hashlib.sha256();count=0;last=0
    with verified_open(item['url']) as response,partial.open('wb') as out:
        total=int(response.headers.get('Content-Length',item.get('bytes',0)))
        while block:=response.read(1024*1024):
            out.write(block);digest.update(block);count+=len(block)
            if time.monotonic()-last>1:
                progress(f"Downloading {item['filename']}: {count//1024**2} MB"+(f" of {total//1024**2} MB" if total else ''))
                last=time.monotonic()
    if digest.hexdigest()!=item['sha256']:
        partial.unlink(missing_ok=True)
        raise RuntimeError('Download verification failed. Retry setup or install an updated application release.')
    partial.replace(target)


def prepare(progress=print):
    with file_lock(DATA/'setup.lock'):
        if ready(): return
        marker=DATA/'setup.json';marker.unlink(missing_ok=True)
        cache=DATA/'downloads';cache.mkdir(exist_ok=True);TOOLS.mkdir(exist_ok=True)
        progress('Preparing the local tools. Please keep this window open.')
        dependency_marker=DATA/'dependencies.json'
        signature=hashlib.sha256((APP/'windows/requirements.lock').read_bytes()+(APP/'windows/rapidocr.lock').read_bytes()+str(sys.version_info[:2]).encode()).hexdigest()
        try: complete=json.loads(dependency_marker.read_text(encoding='utf-8')).get('signature')==signature and (LIB/'faster_whisper').is_dir()
        except (OSError,ValueError):complete=False
        if not complete:
            # Rebuild only the private library directory; jobs and models are retained.
            dependency_marker.unlink(missing_ok=True)
            if LIB.exists(): shutil.rmtree(LIB)
            LIB.mkdir()
            run([sys.executable,__file__,'--pip','install','--disable-pip-version-check','--no-warn-script-location',
                 '--only-binary=:all:','--require-hashes','--no-compile','--target',LIB,'-r',APP/'windows/requirements.lock'])
            progress('Installing the locally tested OCR wrapper.')
            # Override historical metadata for this pure-Python wrapper only, never native packages.
            run([sys.executable,__file__,'--pip','install','--disable-pip-version-check','--no-warn-script-location',
                 '--only-binary=:all:','--require-hashes','--no-deps','--ignore-requires-python','--no-compile','--target',LIB,
                 '-r',APP/'windows/rapidocr.lock'])
            write_json(dependency_marker,{'signature':signature})
        # A fresh library directory did not exist when this process first imported modules.
        importlib.invalidate_caches()
        progress('Downloading verified Windows video tools.')
        spec=json.loads((APP/'windows/downloads.json').read_text(encoding='utf-8'))['ffmpeg']
        archive=cache/spec['filename'];download(spec,archive,progress)
        notices=DATA/'third-party-notices';notices.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for name in ('ffmpeg.exe','ffprobe.exe'):
                member=next(n for n in z.namelist() if n.endswith('/bin/'+name))
                with z.open(member) as source,(TOOLS/name).open('wb') as output:shutil.copyfileobj(source,output)
            license_member=next(n for n in z.namelist() if n.endswith('/LICENSE.txt'))
            (notices/'FFmpeg-LICENSE.txt').write_bytes(z.read(license_member))
            for member in z.namelist():
                if '/doc/' in member and not member.endswith('/'):
                    target=notices/'ffmpeg'/member.split('/doc/',1)[1];target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(z.read(member))
        # Entry scripts use this embedded interpreter, not a system Python installation.
        for filename,module in (('yt-dlp.cmd','yt_dlp'),):
            (TOOLS/filename).write_text(f'@echo off\r\n"{sys.executable}" "{__file__}" --module {module} %*\r\n',encoding='utf-8')
        try: ctypes.WinDLL('msvcp140.dll')
        except OSError:
            progress('Installing Microsoft C++ components. Please approve the Windows permission prompt.')
            redist=cache/'vc_redist.x64.exe'
            with verified_open('https://aka.ms/vc14/vc_redist.x64.exe') as response,redist.open('wb') as output:
                shutil.copyfileobj(response,output)
            # Download directly from Microsoft; verify its Authenticode publisher before executing.
            run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',APP/'windows/install_runtime.ps1','-Path',redist])
        progress('Checking video filters, image tools and local OCR.')
        filters=subprocess.check_output([str(TOOLS/'ffmpeg.exe'),'-hide_banner','-filters'],stderr=subprocess.STDOUT,**HIDDEN).decode('utf-8','replace')
        for required in ('vidstabdetect','vidstabtransform','afftdn','loudnorm'):
            if required not in filters: raise RuntimeError('The selected video tools lack '+required)
        try:run([sys.executable,__file__,'--check-tools'])
        except subprocess.CalledProcessError:
            dependency_marker.unlink(missing_ok=True)
            raise
        progress('Downloading and loading the local speech model. This can take several minutes.')
        run([sys.executable,__file__,'--warm-model'])
        progress('Saving dependency and model notices.')
        for filename,url in {
            'Whisper-LICENSE.txt':'https://raw.githubusercontent.com/openai/whisper/main/LICENSE',
            'Whisper-model-card.md':'https://huggingface.co/Systran/faster-whisper-small.en/raw/main/README.md',
            'RapidOCR-LICENSE.txt':'https://raw.githubusercontent.com/RapidAI/RapidOCR/main/LICENSE',
            'PaddleOCR-LICENSE.txt':'https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/LICENSE',
            'Deno-LICENSE.txt':'https://raw.githubusercontent.com/denoland/deno/main/LICENSE.md',
        }.items():
            with verified_open(url,timeout=60) as response:(notices/filename).write_bytes(response.read())
        from importlib import metadata
        inventory=sorted(f'{d.metadata["Name"]}=={d.version}' for d in metadata.distributions(path=[str(LIB)]))
        (notices/'python-dependencies.txt').write_text('\n'.join(inventory)+'\n',encoding='utf-8')
        write_json(marker,{'version':VERSION,'python':sys.version,'completed':time.time(),'dependencies':inventory})
        progress('Ready. Opening your sermon preparation app.')


def health():
    try:
        with urllib.request.urlopen(URL+'/api/health',timeout=2) as response:
            value=json.load(response)
        return value.get('app')=='ccs-video-cleanup' and value.get('instance')==IDENTITY
    except (OSError,ValueError): return False


def server():
    with file_lock(DATA/'server.lock'):
        if not ready():
            state={'stage':'Starting setup','error':False,'ready':False}
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path=='/api/setup':
                        tail=(DATA/'setup.log').read_text(encoding='utf-8',errors='replace')[-5000:] if (DATA/'setup.log').exists() else ''
                        body=json.dumps(dict(state,log=tail)).encode();mime='application/json'
                    elif self.path=='/logo.png':body=(APP/'assets/church-logo.png').read_bytes();mime='image/png'
                    elif self.path=='/':body=(APP/'windows/setup.html').read_bytes();mime='text/html; charset=utf-8'
                    elif self.path=='/api/health':body=json.dumps({'app':'ccs-video-cleanup','instance':IDENTITY}).encode();mime='application/json'
                    else:self.send_error(404);return
                    self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
                def do_POST(self):
                    if self.path=='/api/shutdown' and self.headers.get('X-CCS-Request')=='1' and state['error']:
                        size=int(self.headers.get('Content-Length','0'))
                        if size>1024 or json.loads(self.rfile.read(size)).get('instance')!=IDENTITY:
                            self.send_error(403);return
                        state['stop']=True;self.send_response(200);self.end_headers()
                        threading.Thread(target=http.shutdown,daemon=True).start();return
                    if self.path!='/api/retry'  or self.headers.get('X-CCS-Request')!='1' or not state['error']:
                        self.send_error(400);return
                    state.update(error=False);threading.Thread(target=worker,daemon=True).start();self.send_response(200);self.end_headers()
                def log_message(self,*args):pass
            http=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
            def worker():
                try:
                    prepare(lambda text:state.update(stage=text))
                    state.update(ready=True)
                    # Give the progress page time to observe completion before changing servers.
                    time.sleep(3);http.shutdown()
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    message='A local tool could not start. Open Setup details for the error, then try setup again.' if isinstance(exc,subprocess.CalledProcessError) else str(exc)
                    state.update(error=True,stage=message)
            threading.Thread(target=worker,daemon=True).start()
            http.serve_forever();http.server_close()
            if state.get("stop"):return
        os.environ['HF_HUB_OFFLINE']='1'
        from ccs.web import serve
        serve(PORT)


def main():
    if '--pip' in sys.argv:
        sys.path.insert(0,str(next((APP/'windows').glob('pip-*.whl'))))
        import runpy
        sys.argv=['pip']+sys.argv[sys.argv.index('--pip')+1:];runpy.run_module('pip',run_name='__main__');return
    if '--module' in sys.argv:
        import runpy
        index=sys.argv.index('--module');module=sys.argv[index+1];sys.argv=[module]+sys.argv[index+2:]
        runpy.run_module(module,run_name='__main__');return
    if '--check-tools' in sys.argv:
        import cv2,numpy,scipy,PIL,av,ctranslate2,tokenizers,onnxruntime
        from rapidocr_onnxruntime import RapidOCR
        RapidOCR()
        deno_binary=next(LIB.rglob('deno.exe'))
        shutil.copy2(deno_binary,TOOLS/'deno.exe')
        subprocess.run([str(TOOLS/'deno.exe'),'--version'],check=True,**HIDDEN)
        print('Windows native dependencies and OCR loaded successfully');return
    if '--warm-model' in sys.argv:
        from faster_whisper import WhisperModel
        WhisperModel('small.en',device='cpu',compute_type='int8',download_root=str(MODELS));return
    if '--shutdown' in sys.argv:
        # CLI processing may hold this lock even when no desktop server is running.
        try:
            with file_lock(DATA/'.tools/pipeline.lock'):pass
        except LockBusy:
            print('Finish the current sermon processing job before updating.');raise SystemExit(2)
        if health():
            try:
                request=urllib.request.Request(URL+'/api/shutdown',data=json.dumps({'instance':IDENTITY}).encode(),headers={'Content-Type':'application/json','X-CCS-Request':'1'})
                urllib.request.urlopen(request,timeout=5).close()
                for _ in range(30):
                    if not health():
                        try:
                            with file_lock(DATA/'server.lock'):return
                        except LockBusy:pass
                    time.sleep(.2)
                raise RuntimeError('The application is still shutting down.')
            except Exception as exc:
                print(exc);raise SystemExit(2)
        try:
            with file_lock(DATA/'server.lock'):pass
        except LockBusy:
            print('Finish the current setup or processing job before updating.');raise SystemExit(2)
        return
    if '--setup' in sys.argv:prepare();return
    if '--cli' in sys.argv:
        if not ready():prepare()
        os.environ['HF_HUB_OFFLINE']='1'
        sys.argv=['ccs-video-cleanup']+sys.argv[sys.argv.index('--cli')+1:]
        from ccs.cli import main as cli
        cli();return
    if '--server' in sys.argv:
        log=(DATA/'server.log').open('a',encoding='utf-8',buffering=1);sys.stdout=sys.stderr=log
        try:server()
        except LockBusy:pass
        except Exception:
            import traceback
            traceback.print_exc()
        return
    if '--data' in sys.argv:os.startfile(DATA);return
    if '--logs' in sys.argv:
        log=DATA/'setup.log'
        if not log.exists():log.write_text('Setup has not started yet. Open Christ Church Video Cleanup first.\n',encoding='utf-8')
        os.startfile(log);return
    with file_lock(DATA/'launch.lock'):
        if not health():
            subprocess.Popen([str(INSTALL/'runtime/pythonw.exe'),__file__,'--server'],close_fds=True,**HIDDEN)
            for _ in range(100):
                if health():break
                time.sleep(.2)
            else:raise RuntimeError('The app could not start. Check '+str(DATA/'server.log')+'. Port 8765 may already be in use.')
        webbrowser.open(URL)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        if any(flag in sys.argv for flag in ('--open','--logs','--data')) or len(sys.argv)==1:
            ctypes.windll.user32.MessageBoxW(None,str(exc),'Christ Church Video Cleanup',0x10)
        else:raise
