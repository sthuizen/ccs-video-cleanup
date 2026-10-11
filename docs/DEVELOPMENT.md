# Development and release guide

[Home](../README.md) · [Architecture](ARCHITECTURE.md) · [Contribution notes](../CONTRIBUTING.md)

## Get the source

Sign into GitHub with access to the private repository, then:

```bash
git clone https://github.com/thenailedone/ccs-video-cleanup.git
cd ccs-video-cleanup
git switch -c your-change
```

`main` is current source/documentation. `v1.0.0` is a recovered historical snapshot; `v1.4.0` identifies the current release source. See [version provenance](VERSION_HISTORY.md). Release binaries are separate attachments and are not included by cloning. Bible text and provenance are tracked; the logo, toolchains and model caches are not.

## Run a development copy

The original `python3 setup.py` bootstraps a local installation, downloads tools/models and registers the original desktop/service. **It also changes user-level launch/service files.** Read it and [the local-install guide](LOCAL_INSTALL.md) before using it on a computer already running production. Prefer a separate user account or disposable environment for a full bootstrap.

For an existing package installation, its initialized user venv can run this checkout while APT supplies tools. Put all test jobs in a fresh directory; do not point a developer server at production jobs. Example from the checkout:

```bash
export CCS_DATA_DIR="$(mktemp -d)"
export CCS_BIN_DIR=/usr/bin
export CCS_YTDLP="${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup/venv/bin/yt-dlp"
export CCS_MODEL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup/models/whisper"
"${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup/venv/bin/python" -m ccs.cli serve --port 8766
```

Confirm the model path against `packaging/launch` and your actual installation. Stop the development process with Ctrl-C. Delete the temporary jobs only when finished. The source wrapper `./ccs-cleanup` assumes a source-local `.venv`; the package launcher executes installed app code, not your checkout.

## Tests

For the original configured workspace, after substantive pipeline edits:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

For a package-equipped development checkout, use the same user-venv Python shown above, with isolated `CCS_DATA_DIR` and `/usr/bin` tool path. Tests use a short synthetic source; never replace those inputs with private production recordings. They include opposed stereo, full rendering/validation, review logic and cached-work behavior.

The browser logic checks require Deno and read only the source HTML:

```bash
deno run --allow-read tests/download_access.js
deno run --allow-read tests/preview_display.js
deno run --allow-read tests/progress_display.js
deno run --allow-read tests/review_precision.js
deno run --allow-read tests/audio_workflow.js
deno run --allow-read tests/service_selection.js
deno run --allow-read tests/resolution_selection.js
deno run --allow-read tests/library_controls.js
deno run --allow-read tests/export_choices.js
```

In a source-local installation use `.tools/bin/deno`; in a packaged one use the Deno installed in its venv if not on PATH. Do not restart a production render to test unrelated documentation or UI changes.

## Build an application-only package

On a Debian-family build machine with Python 3 and `dpkg-deb`:

```bash
python3 packaging/build_deb.py --version 1.4.0
```

Use a new version for new content. The builder writes a `.deb` and SHA-256 checksum into ignored `dist/`; it does not install the package, need model caches or alter a running server. Version 1.1's design excludes third-party binaries/wheels/models and branding. Keep that boundary intact. The preserved original 1.1.0 artifact is authoritative; rebuilds are not promised to be bit-identical because packaging timestamps/documentation can differ.

## Verify a release

Install the candidate through APT in each intended target distro, then run setup as a normal user. Confirm standard Python libraries come from `/usr/lib/python3/dist-packages`. Exercise OCR, offline Whisper loading, repeated setup, web/API and a complete synthetic render with opposed stereo, absence of player chapters, mono audio and preview validation. `packaging/verify_installed.py` provides installed-environment smoke checks; it must be run with that installation's Python and appropriate app/data/model paths. It does not replace the media test or a real desktop launch check.

The archived 1.1 evidence used proot Ubuntu 24.04/Python 3.12 and Debian 13/Python 3.13 with a shared host kernel. A future desktop release should additionally test menu launch, login startup and service lifecycle on actual target desktops. Record what was and was not tested honestly.

Before publishing a new private release:

1. Run appropriate Python/browser checks and target-install tests.
2. Review staged files. No videos, job evidence, cookies, credentials, logo, models or environments belong in Git.
3. Record artifact byte sizes/checksums, test environments and limitations; update documentation and version history.
4. Commit and tag the tested source. Create a draft GitHub Release, attach the installer/checksum/validation and verify uploads before publishing.
5. Download/check the new attachment or compare GitHub's asset SHA-256 digest with the local file. Retain earlier releases; do not replace historical installer bytes.

[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) associate binary attachments with Git tags and also provide source archives. Keep the repository private. No release process here grants public distribution rights to the application or archived bundled components.

## Windows development

The [Windows builder and guide](../packaging/windows/README.md) explain the Linux NSIS build. The embedded runtime and pip wheel have pinned SHA-256 values; Python dependencies use Windows x64 hash locks. Download the authorized raw logo from the private Windows release and supply it locally because the raw branding file is excluded from Git. Keep VM images, installers, models and lab credentials under ignored `.tools`/`dist` folders.

Run source regression tests on Linux, then use actual Windows for native import, OCR, offline speech inference and FFmpeg rendering. `packaging/windows/verify.py` runs via the installed launcher with `--module windows.verify` and `CCS_TEST_SPEECH` pointing to a synthetic English WAV. It checks a path containing spaces and non-ASCII characters, the opposed-stereo case, absence of player chapters, logo/health endpoints, repeated setup, duplicate launch and refusal to shut down during processing. Follow this with the Python suite and Deno UI checks, plus actual installer update/uninstall/reinstall and shortcut tests. A successful Linux build alone is insufficient.

No Windows VM or evaluation OS is distributed. Source tags, installer/checksum assets and sanitized test reports belong together in the private release. Do not claim Authenticode signing unless a real trusted certificate was used.

Version 1.4.0 builders include the platform PDF guides, so first run `tools/build_user_guides.py` after updating the screenshot fixtures. New UI checks also cover `audio_workflow`, `service_selection`, `resolution_selection`, `library_controls` and `export_choices`. Windows tray feedback uses `/api/tray`; the server starts its native WinForms tray in a kill-on-close Windows job object. Linux packaged tray is a separate GTK user unit. See the 1.4.0 validation record for actual tested scope.
