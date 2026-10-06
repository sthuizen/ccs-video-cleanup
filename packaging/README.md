# Ubuntu / Debian installer

The `.deb` bundles this version's Python 3.12 runtime, pinned installed Python
packages, FFmpeg with stabilization, Deno, Whisper small.en and OCR models,
church logo and cached Bible. It contains no videos, browser cookies, job
history or credentials. Model setup does not require internet access.

This build is for amd64 (64-bit Intel/AMD), not ARM. Its control file declares
the minimum glibc version measured from the bundled binaries, plus the system
libraries, fonts and desktop URL opener required by the application. APT
installs these system dependencies from your distribution's repositories.
Use a desktop Ubuntu/Debian installation with a browser. Downloading YouTube
videos still requires internet access.

## Install

In the folder containing the `.deb`:

```bash
sudo apt install ./ccs-video-cleanup_1.0.0_amd64.deb
```

Open **Christ Church Video Cleanup** from the applications menu. The first
launch starts and enables the packaged user service, which then starts at login.
Without a working user systemd session the launcher starts a background server.
Closing the browser does not stop processing.

Application files are in `/opt/ccs-video-cleanup`. Videos, evidence and caches
are in `~/.local/share/ccs-video-cleanup/jobs/` (or under `$XDG_DATA_HOME`).
CLI: `ccs-video-cleanup run 'URL'`; all existing review/render flags work.

## Existing local installation

Use only one server on port 8765. Before switching from the project-based
installation, finish any running job, then stop and disable its service:

```bash
systemctl --user disable --now ccs-video-cleanup.service
```

Its data remains in the original project's `jobs/` folder. To carry it over,
copy the required job folders into the packaged app's jobs folder. The old
user-local launcher may still appear in the menu; its desktop file is
`~/.local/share/applications/ccs-video-cleanup.desktop`. The packaged desktop
file has the distinct name `ccs-video-cleanup-packaged.desktop`.

## Stop / remove

```bash
systemctl --user disable --now ccs-video-cleanup-packaged.service
sudo apt remove ccs-video-cleanup
```

Keep your videos and job data; removal does not delete them. For a launcher
started without systemd, stop its background server before removing the app.

## Rebuild

From a working local installation with cached models and tools:

```bash
python3 packaging/build_deb.py --version 1.0.0
```

Requires `dpkg-deb`, `readelf` and `ldd`. The builder copies the installed
runtime, checks shared-library requirements, loads speech/OCR offline, runs
all tests with the relocated runtime and renders a temporary synthetic video.
It creates `dist/*.deb` and a SHA-256 checksum. It does not install the package,
restart the live service, or touch production videos. Bundled dependencies
are a snapshot; rebuild with a new version number after updates. The bundled
FFmpeg GPL license, release metadata and Python dependency inventory are in
`/usr/share/doc/ccs-video-cleanup/`.
