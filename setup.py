#!/usr/bin/env python3
"""Recreate the user-local Linux toolchain; no administrator access or API keys."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, tarfile, urllib.request, zipfile
ROOT=Path(__file__).resolve().parent
TOOLS=ROOT/'.tools'; BIN=TOOLS/'bin'; BIN.mkdir(parents=True,exist_ok=True)
def fetch(url,path):
    print('Downloading',url,flush=True)
    urllib.request.urlretrieve(url,path)
def release(repo,choose):
    req=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers={'User-Agent':'CCS-video-cleanup'})
    data=json.load(urllib.request.urlopen(req))
    asset=next(a for a in data['assets'] if choose(a['name']))
    path=TOOLS/asset['name']; fetch(asset['browser_download_url'],path)
    digest=asset.get('digest')
    if digest and digest.startswith('sha256:'):
        if hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=digest[7:]: raise RuntimeError('Download checksum mismatch')
    (TOOLS/(repo.split('/')[-1]+'-release.json')).write_text(json.dumps({'tag':data['tag_name'],'url':asset['browser_download_url'],'digest':digest},indent=2))
    return path
if not (BIN/'uv').exists():
    archive=release('astral-sh/uv',lambda n:n=='uv-x86_64-unknown-linux-gnu.tar.gz')
    with tarfile.open(archive) as t:t.extractall(TOOLS,filter='data')
    shutil.copy2(TOOLS/'uv-x86_64-unknown-linux-gnu/uv',BIN/'uv')
if not (BIN/'ffmpeg').exists():
    archive=release('BtbN/FFmpeg-Builds',lambda n:'linux64-gpl' in n and 'shared' not in n and n.endswith('.tar.xz'))
    with tarfile.open(archive) as t:t.extractall(TOOLS,filter='data')
    for path in TOOLS.glob('ffmpeg-*/bin/ff*'):shutil.copy2(path,BIN/path.name)
if not (BIN/'deno').exists():
    archive=release('denoland/deno',lambda n:n=='deno-x86_64-unknown-linux-gnu.zip')
    with zipfile.ZipFile(archive) as z:z.extract('deno',BIN)
    (BIN/'deno').chmod(0o755)
subprocess.run([BIN/'uv','venv','--python','3.12',ROOT/'.venv'],check=True) if not (ROOT/'.venv/bin/python').exists() else None
subprocess.run([BIN/'uv','pip','install','--python',ROOT/'.venv/bin/python','-r',ROOT/'requirements.txt'],check=True)
# The enhancer and its embedded model are obtained directly from the verified
# upstream release; subsequent audio processing is entirely local.
subprocess.run([ROOT/'.venv/bin/python','-m','ccs.audio_setup','--directory',BIN],cwd=ROOT,check=True)
# Warm the speech model cache now, so weekly runs require no model downloads.
subprocess.run([ROOT/'.venv/bin/python','-c',"from faster_whisper import WhisperModel; WhisperModel('small.en',device='cpu',compute_type='int8',download_root="+repr(str(ROOT/'.models/whisper'))+")"],check=True)
logo=ROOT/'assets/church-logo.png'; logo.parent.mkdir(exist_ok=True)
if not logo.exists(): fetch('https://s3.amazonaws.com/media.cloversites.com/8b/8bfdf5ac-6353-4ef7-af75-69d9fdaa93b2/site-images/6524df0b-c1f5-4d8b-b848-6402e37dc5b0@2x.png',logo)
bible=ROOT/'assets/bible/engwebp_vpl.txt'
if not bible.exists():
    archive=ROOT/'assets/web-bible.zip'
    fetch('https://ebible.org/Scriptures/engwebp_vpl.zip',archive)
    with zipfile.ZipFile(archive) as z:
        z.extract('engwebp_vpl.txt',ROOT/'assets/bible')
        z.extract('engwebp_about.htm',ROOT/'assets/bible')
local=Path.home()/'.local/bin';local.mkdir(parents=True,exist_ok=True)
link=local/'ccs-cleanup'
if link.is_symlink(): link.unlink()
if not link.exists(): link.symlink_to(ROOT/'ccs-cleanup')
apps=Path.home()/'.local/share/applications'; apps.mkdir(parents=True,exist_ok=True)
(apps/'ccs-video-cleanup.desktop').write_text('[Desktop Entry]\nVersion=1.0\nType=Application\nName=Christ Church Video Cleanup\nComment=Prepare a sermon from a YouTube service\nExec="'+str(ROOT/'open-cleanup')+'"\nPath='+str(ROOT)+'\nIcon=video-x-generic\nTerminal=false\nCategories=AudioVideo;Video;\n')
units=Path.home()/'.config/systemd/user'; units.mkdir(parents=True,exist_ok=True)
(units/'ccs-video-cleanup.service').write_text('[Unit]\nDescription=Christ Church Video Cleanup local interface\n\n[Service]\nType=simple\nWorkingDirectory='+str(ROOT)+'\nExecStart="'+str(ROOT/'ccs-cleanup')+'" serve\nRestart=on-failure\nRestartSec=3\n\n[Install]\nWantedBy=default.target\n')
if shutil.which('systemctl'):
    subprocess.run(['systemctl','--user','daemon-reload'],check=False)
    subprocess.run(['systemctl','--user','start','ccs-video-cleanup.service'],check=False)
print('Installed. Open Christ Church Video Cleanup from your applications menu.')
