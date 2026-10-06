#!/usr/bin/python3
"""Prepare private dependencies and local models after package installation."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

APP = Path(__file__).resolve().parent
DATA = Path(os.environ.get('CCS_DATA_DIR', str(Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'ccs-video-cleanup')))
REVISION = '1.1.0'
TOP_PACKAGES = ['faster-whisper==1.2.1']


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def prepare(logo=None, update_downloader=False):
    if os.geteuid() == 0:
        raise SystemExit('Run ccs-video-cleanup setup as your normal desktop user, without sudo.')
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA/'setup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        environment = DATA/'venv'
        python = environment/'bin/python'
        marker = DATA/'setup.json'
        try:
            record = json.loads(marker.read_text()) if marker.exists() else {}
        except (ValueError, OSError):
            record = {}
        ready = record.get('revision') == REVISION and record.get('python_minor') == list(sys.version_info[:2]) and python.exists()
        if not ready:
            print('Preparing local AI tools. Internet access is required for this one-time setup.', flush=True)
            # Recreate only an incomplete environment. Successful model downloads remain cached.
            if environment.exists(): shutil.rmtree(environment)
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
            constraints = DATA/'system-constraints.txt'
            script = "from importlib.metadata import version; print('\\n'.join(name+'=='+version(name) for name in ('numpy','Pillow','scipy','av')))"
            constraints.write_text(subprocess.check_output([str(python), '-c', script], text=True))
            pip = [python, '-m', 'pip', 'install', '--only-binary=:all:', '--constraint', constraints]
            run(pip + ['-r', APP/'requirements-ai.txt'])
            # RapidOCR's PyPI metadata asks for opencv-python. APT's python3-opencv
            # supplies cv2 instead, so install these two wrappers without duplicate wheels.
            run(pip + ['--no-deps'] + TOP_PACKAGES)
            # This pinned wrapper is pure Python. Its historical <3.13 metadata
            # excludes Debian 13; both 3.12 and 3.13 are tested with real OCR.
            # Do not override interpreter requirements for its native dependencies.
            run(pip + ['--no-deps', '--ignore-requires-python', 'rapidocr-onnxruntime==1.4.4'])
            filters = subprocess.check_output(['/usr/bin/ffmpeg','-hide_banner','-filters'], stderr=subprocess.STDOUT, text=True)
            for name in ('vidstabdetect','vidstabtransform','afftdn','loudnorm'):
                if name not in filters: raise RuntimeError(f'The distribution FFmpeg lacks {name}.')
            run([python, '-c', "import cv2, numpy, scipy, PIL, av, ctranslate2, tokenizers, onnxruntime; from rapidocr_onnxruntime import RapidOCR; RapidOCR(); print('Image, media and OCR dependencies verified')"])
            run([environment/'bin/deno', '--version'])
            # This is a model download, not a cloud inference call. Later speech runs locally.
            run([python, '-c', "import sys; from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8', download_root=sys.argv[1]); print('Speech model ready')", DATA/'models/whisper'])
            notice = DATA/'third-party-notices'
            notice.mkdir(exist_ok=True)
            # Preserve model notices alongside the downloaded model, not in the .deb.
            import urllib.request
            for filename, url in {
                'Whisper-LICENSE.txt': 'https://raw.githubusercontent.com/openai/whisper/main/LICENSE',
                'Whisper-model-card.md': 'https://huggingface.co/Systran/faster-whisper-small.en/raw/main/README.md',
                'PaddleOCR-LICENSE.txt': 'https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/LICENSE',
                'RapidOCR-LICENSE.txt': 'https://raw.githubusercontent.com/RapidAI/RapidOCR/main/LICENSE',
                'Deno-LICENSE.txt': 'https://raw.githubusercontent.com/denoland/deno/main/LICENSE.md',
            }.items():
                with urllib.request.urlopen(url, timeout=60) as response:
                    (notice/filename).write_bytes(response.read())
            with (notice/'python-dependencies.txt').open('w') as inventory:
                run([python, '-m', 'pip', 'freeze'], stdout=inventory)
            record = {'revision': REVISION, 'python_minor': list(sys.version_info[:2]), 'python': subprocess.check_output([str(python), '--version'], text=True).strip()}
            temporary=marker.with_suffix('.tmp'); temporary.write_text(json.dumps(record, indent=2)); temporary.replace(marker)
        if update_downloader:
            run([python, '-m', 'pip', 'install', '--only-binary=:all:', '--upgrade', 'yt-dlp[default,deno]'])
            with (DATA/'third-party-notices/python-dependencies.txt').open('w') as inventory:
                run([python, '-m', 'pip', 'freeze'], stdout=inventory)
        if logo:
            from PIL import Image
            source = Path(logo).expanduser().resolve()
            with Image.open(source) as image:
                target=DATA/'assets/church-logo.png'; target.parent.mkdir(exist_ok=True)
                image.convert('RGBA').save(target)
        print(f'Ready. Videos and models are stored in {DATA}', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logo', help='A church logo you have permission to use')
    parser.add_argument('--update-downloader', action='store_true')
    args=parser.parse_args()
    prepare(args.logo, args.update_downloader)
