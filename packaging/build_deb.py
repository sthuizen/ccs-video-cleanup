#!/usr/bin/env python3
"""Bundle the installed, cached application without downloading at install time."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
INSTALL = '/opt/ccs-video-cleanup'


def write(path, content, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755 if executable else 0o644)


def build(version, output):
    if platform.machine() != 'x86_64':
        raise SystemExit('This bundled build supports amd64 only.')
    subprocess.run(['dpkg', '--validate-version', version], check=True)
    output.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    with tempfile.TemporaryDirectory(prefix='.ccs-deb-', dir=output) as temporary:
        stage = Path(temporary)
        app = stage / INSTALL.lstrip('/')
        app.mkdir(parents=True)
        for directory in ('ccs', 'assets'):
            shutil.copytree(ROOT / directory, app / directory, ignore=ignore)
        # Keep relative cache links, but refuse links to files outside the model bundle.
        for link in (ROOT / '.models').rglob('*'):
            if link.is_symlink() and (link.readlink().is_absolute() or not link.resolve().is_relative_to((ROOT / '.models').resolve())):
                raise RuntimeError(f'Nonportable model cache link: {link}')
        shutil.copytree(ROOT / '.models', app / '.models', symlinks=True, ignore=ignore)
        python_root = (ROOT / '.venv/bin/python').resolve().parent.parent
        shutil.copytree(python_root, app / 'python', symlinks=True, ignore=ignore)
        shutil.copytree(ROOT / '.venv/lib/python3.12/site-packages',
                        app / '.venv/lib/python3.12/site-packages', ignore=ignore)
        for name in ('ffmpeg', 'ffprobe', 'deno'):
            target = app / '.tools/bin' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / '.tools/bin' / name, target)
        write(app / '.venv/bin/python', '''#!/bin/sh
set -eu
app=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
export PYTHONPATH="$app:$app/.venv/lib/python3.12/site-packages"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
exec "$app/python/bin/python3.12" "$@"
''', True)
        write(app / '.venv/bin/yt-dlp', '''#!/bin/sh
set -eu
exec "$(dirname -- "$0")/python" -m yt_dlp "$@"
''', True)
        shutil.copy2(ROOT / 'ccs-cleanup', app / 'ccs-cleanup')
        write(app / 'launch', '''#!/bin/sh
set -eu
app=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export CCS_DATA_DIR="${CCS_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup}"
mkdir -p "$CCS_DATA_DIR/jobs" "$CCS_DATA_DIR/.tools"
if [ "${1:-}" = "--open" ]; then
    # Activate the packaged user unit without overwriting a local installation's unit.
    if command -v systemctl >/dev/null 2>&1 && systemctl --user cat ccs-video-cleanup-packaged.service >/dev/null 2>&1; then
        systemctl --user enable --now ccs-video-cleanup-packaged.service
    else
        if ! "$app/.venv/bin/python" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/api/jobs", timeout=2)' >/dev/null 2>&1; then
            nohup "$app/launch" serve > "$CCS_DATA_DIR/server.log" 2>&1 < /dev/null &
        fi
    fi
    n=0
    until "$app/.venv/bin/python" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/api/jobs", timeout=2)' >/dev/null 2>&1; do
        n=$((n + 1))
        [ "$n" -lt 15 ] || { echo 'The local server did not start.' >&2; exit 1; }
        sleep 1
    done
    exec xdg-open http://127.0.0.1:8765
fi
exec "$app/ccs-cleanup" "$@"
''', True)
        write(stage / 'usr/bin/ccs-video-cleanup', f'#!/bin/sh\nexec {INSTALL}/launch "$@"\n', True)
        write(stage / 'usr/share/applications/ccs-video-cleanup-packaged.desktop', '''[Desktop Entry]
Version=1.0
Type=Application
Name=Christ Church Video Cleanup
Comment=Prepare a sermon from a YouTube service
Exec=ccs-video-cleanup --open
Icon=video-x-generic
Terminal=false
Categories=AudioVideo;Video;
''')
        write(stage / 'usr/lib/systemd/user/ccs-video-cleanup-packaged.service', f'''[Unit]
Description=Christ Church Video Cleanup local interface (Debian package)

[Service]
Type=simple
ExecStart={INSTALL}/launch serve
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
''')
        docs = stage / 'usr/share/doc/ccs-video-cleanup'
        shutil.copytree(ROOT / 'packaging', docs / 'packaging', ignore=ignore)
        shutil.copy2(ROOT / 'README.md', docs / 'README.md')
        freeze = subprocess.check_output([str(ROOT / '.tools/bin/uv'), 'pip', 'freeze',
                                          '--python', str(ROOT / '.venv/bin/python')], text=True)
        write(docs / 'python-dependencies.txt', freeze)
        write(docs / 'bundle-notice.txt', 'This package bundles the installed application and third-party runtimes.\n'
              'Python and Python dependencies retain their upstream licenses in python/ and site-packages/.\n'
              'The bundled BtbN FFmpeg build is GPL; release metadata is in tool-releases/.\n'
              'The church logo is included for use with the Christ Church Southampton workflow.\n')
        shutil.copy2(ROOT / '.tools/ffmpeg-master-latest-linux64-gpl/LICENSE.txt', docs / 'FFmpeg-LICENSE.txt')
        for release in (ROOT / '.tools').glob('*-release.json'):
            target = docs / 'tool-releases' / release.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(release, target)
        # Smoke-test from the staging path, ensuring no original absolute paths are needed.
        env = dict(os.environ, CCS_DATA_DIR=str(stage / 'smoke-data'), HF_HUB_OFFLINE='1')
        subprocess.run([str(app / 'launch'), '--help'], env=env, check=True)
        subprocess.run([str(app / '.venv/bin/python'), '-c',
                        "from faster_whisper import WhisperModel; from rapidocr_onnxruntime import RapidOCR; "
                        "from ccs.common import ROOT; "
                        "WhisperModel('small.en', device='cpu', compute_type='int8', "
                        "download_root=str(ROOT/'.models/whisper'), local_files_only=True); RapidOCR(); "
                        "print('Bundled speech and OCR models loaded offline')"], env=env, check=True)
        # Check all bundled ELF objects, including dlopen libraries, for missing dependencies.
        library_dirs = sorted({str(p.parent) for p in app.rglob('*.so*') if p.is_file()})
        audit_env = dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(library_dirs))
        max_glibc = (2, 17)
        max_glibcxx = (3, 4, 0)
        import re
        for path in app.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open('rb') as handle:
                if handle.read(4) != b'\x7fELF':
                    continue
            versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True)
            for elf_version in re.findall(r'Name: GLIBC_(\d+\.\d+)', versions):
                max_glibc = max(max_glibc, tuple(map(int, elf_version.split('.'))))
            for elf_version in re.findall(r'Name: GLIBCXX_(\d+\.\d+\.\d+)', versions):
                max_glibcxx = max(max_glibcxx, tuple(map(int, elf_version.split('.'))))
            deps = subprocess.run(['ldd', str(path)], text=True, capture_output=True, env=audit_env)
            if 'not found' in deps.stdout:
                raise RuntimeError(f'Unresolved library in {path}: {deps.stdout}')
        subprocess.run([str(app / '.venv/bin/python'), '-m', 'unittest', 'discover',
                        '-s', str(ROOT / 'tests'), '-v'], env=env, check=True)
        shutil.rmtree(stage / 'smoke-data')
        glibc = '.'.join(map(str, max_glibc))
        # Declare system libraries; large media/AI dependencies are already bundled.
        if max_glibcxx > (3, 4, 30):
            raise RuntimeError(f'libstdc++ requirement too new: {max_glibcxx}')
        depends = f'libc6 (>= {glibc}), libstdc++6 (>= 12), libgcc-s1, libatomic1, zlib1g, libgl1, libglib2.0-0 | libglib2.0-0t64, libxcb1, libx11-6, libxau6, libxdmcp6, xdg-utils, ca-certificates, fonts-dejavu-core'
        installed_size = sum(p.stat().st_size for p in app.rglob('*') if p.is_file()) // 1024
        write(stage / 'DEBIAN/control', f'''Package: ccs-video-cleanup
Version: {version}
Architecture: amd64
Maintainer: Christ Church Video Cleanup local packaging <noreply@localhost>
Section: video
Priority: optional
Depends: {depends}
Recommends: firefox | firefox-esr, systemd
Installed-Size: {installed_size}
Description: Local Christ Church Southampton sermon video preparation
 Bundled Python, FFmpeg, Deno, local speech recognition and OCR models.
 No cloud AI services or model downloads are required after installation.
''')
        # Build with predictable ownership, without root access or install scripts.
        package = output / f'ccs-video-cleanup_{version}_amd64.deb'
        subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '-z3', '--threads-max=2',
                        '--build', str(stage), str(package)], check=True)
        digest = hashlib.file_digest(package.open('rb'), 'sha256').hexdigest()
        write(package.with_suffix('.deb.sha256'), f'{digest}  {package.name}\n')
        print(f'Built {package} ({package.stat().st_size / 1024**2:.1f} MiB), requires glibc >= {glibc}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='1.0.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.version, args.output.resolve())
