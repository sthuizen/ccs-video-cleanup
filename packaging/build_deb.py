#!/usr/bin/env python3
"""Build a small application-only Debian package; dependencies are not bundled."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
INSTALL='/usr/lib/ccs-video-cleanup'
DEPENDS='python3 (>= 3.11), python3-venv, python3-pil (>= 9), python3-numpy (>= 1.21.6), python3-scipy, python3-opencv (>= 4.5), python3-av (>= 11), ffmpeg (>= 7:5), fonts-dejavu-core, ca-certificates, xdg-utils'


def write(path, content, executable=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content)
    path.chmod(0o755 if executable else 0o644)


def build(version, output):
    subprocess.run(['dpkg','--validate-version',version],check=True)
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ccs-deb-',dir=output) as temporary:
        stage=Path(temporary);app=stage/INSTALL.lstrip('/');app.mkdir(parents=True)
        shutil.copytree(ROOT/'ccs',app/'ccs',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        # Only the public-domain Bible is redistributed; no logo, binaries or models.
        bible=app/'assets/bible';bible.mkdir(parents=True)
        for filename in ('engwebp_vpl.txt','engwebp_about.htm'):
            shutil.copy2(ROOT/'assets/bible'/filename,bible/filename)
        for filename in ('setup_user.py','requirements-ai.txt','launch'):
            shutil.copy2(ROOT/'packaging'/filename,app/filename)
        (app/'launch').chmod(0o755)
        write(stage/'usr/bin/ccs-video-cleanup',f'#!/bin/sh\nexec {INSTALL}/launch "$@"\n',True)
        write(stage/'usr/share/applications/ccs-video-cleanup-packaged.desktop','''[Desktop Entry]
Version=1.0
Type=Application
Name=Christ Church Video Cleanup
Comment=Prepare a sermon from a YouTube service; first launch downloads local tools
Exec=ccs-video-cleanup --open
Icon=video-x-generic
Terminal=true
Categories=AudioVideo;Video;
''')
        write(stage/'usr/lib/systemd/user/ccs-video-cleanup-packaged.service',f'''[Unit]
Description=Christ Church Video Cleanup local interface

[Service]
Type=simple
ExecStart={INSTALL}/launch serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
''')
        docs=stage/'usr/share/doc/ccs-video-cleanup';docs.mkdir(parents=True)
        for filename in ('README.md','THIRD_PARTY.md'):
            shutil.copy2(ROOT/'packaging'/filename,docs/filename)
        write(docs/'copyright','''Christ Church Video Cleanup application source and installer.
Third-party executables, Python libraries, AI models and church logo are not
included in this package. Dependencies are installed independently by APT or
by the user's setup command. Their own licences continue to apply.

The included World English Bible Protestant Edition is public domain.
Original information: https://ebible.org/engwebp/copyright.htm
Publisher's information is preserved in assets/bible/engwebp_about.htm.
See THIRD_PARTY.md for dependency sources and maintenance instructions.
''')
        size=sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())//1024
        write(stage/'DEBIAN/control',f'''Package: ccs-video-cleanup
Version: {version}
Architecture: amd64
Maintainer: Christ Church Video Cleanup local packaging <noreply@localhost>
Section: video
Priority: optional
Depends: {DEPENDS}
Recommends: firefox | firefox-esr, systemd
Installed-Size: {size}
Description: Local Christ Church Southampton sermon video preparation
 Uses distribution media tools and a private user AI environment.
 First-run setup requires internet to download dependencies and local models.
''')
        package=output/f'ccs-video-cleanup_{version}_amd64.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','-z3','--build',str(stage),str(package)],check=True)
        with package.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        write(package.with_suffix('.deb.sha256'),f'{digest}  {package.name}\n')
        print(f'Built {package} ({package.stat().st_size/1024**2:.1f} MiB)')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='1.3.0')
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args();build(args.version,args.output.resolve())
