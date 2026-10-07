"""Verified, user-local Linux speech enhancer; no audio leaves the computer."""
import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import tempfile
import urllib.request

VERSION = '0.5.6'
URL = 'https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl'
SHA256 = '70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da'

def install(directory):
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('This speech-enhancer setup has been validated for Linux x86-64 only.')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    target = directory/'deep-filter'
    verified = False
    if target.is_file():
        with target.open('rb') as stream:
            verified = hashlib.file_digest(stream, 'sha256').hexdigest() == SHA256
    notices = directory.parent/'third-party-notices'; notices.mkdir(exist_ok=True)
    names = ('LICENSE-MIT', 'LICENSE-APACHE')
    if verified and all((notices/f'DeepFilterNet-{name}.txt').is_file() for name in names):
        target.chmod(0o755)
        return target
    with tempfile.TemporaryDirectory(prefix='.enhancer-', dir=directory) as tmp:
        staged = Path(tmp)/'deep-filter'
        if not verified:
            with urllib.request.urlopen(URL, timeout=60) as response, staged.open('wb') as out:
                shutil.copyfileobj(response, out)
            with staged.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != SHA256:
                    raise RuntimeError('Speech enhancer checksum mismatch; existing tool was preserved.')
        for name in names:
            address = f'https://raw.githubusercontent.com/Rikorose/DeepFilterNet/v{VERSION}/{name}'
            with urllib.request.urlopen(address, timeout=60) as response:
                (notices/f'DeepFilterNet-{name}.txt').write_bytes(response.read())
        if not verified: staged.replace(target)
        target.chmod(0o755)
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent.parent/'.tools/bin')
    args = parser.parse_args()
    print(install(args.directory))
