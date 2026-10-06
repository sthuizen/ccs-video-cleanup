#!/usr/bin/env python3
"""Build the Windows x64 installer on Linux with NSIS; never install the app."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/'packaging/windows/downloads.json').read_text())

def fetch(item,cache):
    target=cache/item['filename']
    if not target.exists():
        temp=target.with_suffix('.partial')
        with urllib.request.urlopen(item['url'],timeout=90) as s,temp.open('wb') as f:shutil.copyfileobj(s,f)
        temp.replace(target)
    with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=item['sha256']:raise RuntimeError('Checksum mismatch: '+item['filename'])
    return target

def build(makensis,logo):
    work=ROOT/'.tools/windows/build';payload=work/'payload';cache=ROOT/'.tools/windows/downloads'
    cache.mkdir(parents=True,exist_ok=True)
    if payload.exists():shutil.rmtree(payload)
    app=payload/'app';runtime=payload/'runtime';app.mkdir(parents=True);runtime.mkdir()
    shutil.copytree(ROOT/'ccs',app/'ccs',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'packaging/windows',app/'windows',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    html=app/'ccs/index.html'
    html.write_text(html.read_text(encoding='utf-8').replace('id="cookies" value="firefox"','id="cookies" value=""'),encoding='utf-8')
    bible=app/'assets/bible';bible.mkdir(parents=True)
    for name in ('engwebp_vpl.txt','engwebp_about.htm'):shutil.copy2(ROOT/'assets/bible'/name,bible/name)
    if not logo.is_file():raise RuntimeError('Supply the authorized church logo with --logo.')
    shutil.copy2(logo,app/'assets/church-logo.png')
    from PIL import Image
    with Image.open(logo) as image:
        # The supplied wordmark has its square church symbol on the left.
        # Use that exact symbol for small Windows icons; app/intro keep the full logo.
        logo_image=image.crop((0,0,image.height,image.height)).convert('RGBA')
        logo_image.thumbnail((256,256))
        icon=Image.new('RGBA',(256,256),(0,0,0,0))
        icon.alpha_composite(logo_image,((256-logo_image.width)//2,(256-logo_image.height)//2))
        icon.save(app/'windows/church.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    with zipfile.ZipFile(fetch(SPEC['python'],cache)) as z:z.extractall(runtime)
    # Explicit application path; neither registry Python settings nor system site-packages are used.
    (runtime/'python313._pth').write_text('python313.zip\n.\n../app\nimport site\n')
    shutil.copy2(fetch(SPEC['pip'],cache),app/'windows'/SPEC['pip']['filename'])
    for source,name in ((ROOT/'RIGHTS.md','APPLICATION-RIGHTS.md'),(ROOT/'packaging/windows/README.md','WINDOWS-INSTRUCTIONS.md')):
        shutil.copy2(source,app/'windows'/name)
    (app/'windows/QUICK-START.txt').write_text('''Christ Church Video Cleanup - Windows quick start

1. Open the Christ Church Video Cleanup desktop or Start menu shortcut.
2. On first use, keep the PC online and awake while the local tools download.
   Approve the Microsoft C++ prerequisite prompt if it appears.
3. Paste the completed YouTube service URL and choose Prepare sermon.
4. Review the date, passage, title and reading/sermon cut points when asked.
5. Save the details and create the video. Watch the intro, beginning and end.
6. Download finished.mp4 for the full-quality result.

Closing the browser does not stop processing. Reopen the shortcut to reconnect.
The app never publishes your videos. Speech recognition and OCR run locally.

If YouTube requests verification, sign into YouTube in Firefox, then enter
firefox under Download access. Wait before retrying rate-limited downloads.

Start menu: Video files and evidence opens your data; Setup log helps with setup.
Data: %LOCALAPPDATA%\\CCSVideoCleanup
Finish processing before updating or uninstalling. Uninstall keeps video data.

Complete guide: https://github.com/thenailedone/ccs-video-cleanup/blob/main/packaging/windows/README.md
(Repository access is required.)
''',encoding='utf-8')
    output=ROOT/'dist/ccs-video-cleanup_1.2.0_windows_x64_setup.exe';output.parent.mkdir(exist_ok=True)
    subprocess.run([str(makensis),'-V2',f'-DPAYLOAD={payload}',f'-DOUTPUT={output}',str(ROOT/'packaging/windows/installer.nsi')],check=True)
    with output.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    output.with_suffix('.exe.sha256').write_text(digest+'  '+output.name+'\n')
    print(json.dumps({'file':str(output),'bytes':output.stat().st_size,'sha256':digest},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--makensis',default=shutil.which('makensis'));p.add_argument('--logo',type=Path,default=ROOT/'assets/church-logo.png');a=p.parse_args()
    if not a.makensis:p.error('Install NSIS or pass --makensis')
    build(a.makensis,a.logo)
