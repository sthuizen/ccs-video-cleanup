# Dependencies and redistribution

Version 1.1 replaces the bundled-runtime prototype. The `.deb` contains the
application's Python/HTML source, installer scripts and a public-domain Bible.
It contains no third-party executable, Python wheel, speech/OCR model or logo.

## Distribution dependencies

APT installs Python, FFmpeg/ffprobe, Pillow, NumPy, SciPy, OpenCV, PyAV, fonts,
CA certificates and xdg-utils. Their licence notices and sources are supplied
through the distribution packages, not repackaged into this installer.
Use your distribution's security/update mechanism for these components.

## Independently downloaded user dependencies

`ccs-video-cleanup setup` creates a venv with access to APT's Python libraries.
It downloads faster-whisper 1.2.1, RapidOCR 1.4.4 and their remaining dependencies
from PyPI. RapidOCR is installed without its PyPI OpenCV wheel because the
APT cv2 implementation supplies that functionality. This avoids duplicate
OpenCV/Qt/FFmpeg wheel libraries. The pinned RapidOCR 1.4.4 wrapper declares
Python <3.13 in its historical metadata; this one pure-Python package is
installed with that restriction overridden on Debian 13. Its actual OCR is
tested with both Python 3.12 and 3.13; native dependency interpreter restrictions
are not overridden. Other Python versions require separate validation. PyAV, NumPy, SciPy and Pillow are constrained
to the APT versions and are not replaced in the user environment.

The downloader is fetched from PyPI with its default and Deno dependencies;
this avoids relying on an outdated distribution yt-dlp or requiring backports.
All downloads are performed as the desktop user, not by a root package script.
The venv retains upstream wheel licence files. A resolved dependency inventory,
Whisper model card and additional licence notices are saved under
`~/.local/share/ccs-video-cleanup/third-party-notices/`.

Relevant upstream terms and sources:

- faster-whisper: MIT — https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE
- CTranslate2: MIT — https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE
- Whisper model (converted small.en): MIT model card — https://huggingface.co/Systran/faster-whisper-small.en
- Whisper code and model weights: MIT — https://github.com/openai/whisper/blob/main/LICENSE
- RapidOCR wrapper: Apache-2.0 — https://github.com/RapidAI/RapidOCR/blob/main/LICENSE
- OCR model provenance: packaged PaddleOCR models — https://github.com/PaddlePaddle/PaddleOCR
- ONNX Runtime: MIT — https://github.com/microsoft/onnxruntime/blob/main/LICENSE
- Deno: MIT and third-party notices — https://github.com/denoland/deno/blob/main/LICENSE.md
- yt-dlp: Unlicense and dependency terms — https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- World English Bible Protestant Edition: public domain — https://ebible.org/engwebp/copyright.htm

The current Linux source setup additionally obtains the official DeepFilterNet
v0.5.6 x86-64 musl executable directly from its upstream release. It embeds the
DeepFilterNet3 model. The URL and SHA-256 are pinned in `ccs/audio_setup.py`;
the executable is checked again before use and is installed under the user's
data `.tools/bin`, with MIT/Apache-2.0 notices under `.tools/third-party-notices`.
It is not bundled in the `.deb`. Published 1.1.0/1.2.0 installers are unchanged.
See [research, exact artifact and licensing limits](../docs/AUDIO_RESEARCH.md).

These are references, not a certification of every transitive dependency's
redistribution requirements. If distributing an offline bundle later, review
all exact wheel contents, bundled native libraries and model artefacts, retain
notices, and provide corresponding source where applicable. In particular,
FFmpeg and native libraries in Python wheels can have GPL/LGPL obligations;
copying just a top-level Python project's licence is insufficient.

## Branding

The package excludes the church logo. By default an intro uses the church's
name as text. Users may supply an image they are authorised to use with
`ccs-video-cleanup setup --logo /path/to/logo.png`. This does not grant anyone
rights to redistribute that image. This package does not assign a new licence
to the church's name, branding or application source.
