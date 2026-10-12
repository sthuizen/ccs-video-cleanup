# Ubuntu / Debian installer

Version 1.4 is an application-only amd64 package targeting Ubuntu 24.04 LTS and Debian
13. Older releases do not provide all required Python/PyAV versions. Other
releases need compatible binary wheels and separate validation. APT
installs standard dependencies; the user's first-run setup downloads specialist
AI packages, the downloader, Deno, speech model and verified native speech enhancer. Internet access is required
for installation/setup and YouTube downloads. Speech recognition and OCR then
run locally without cloud AI, API keys or subscriptions.

## Install

Ubuntu needs the `universe` repository enabled. From the installer folder:

```bash
sudo apt install ./ccs-video-cleanup_1.4.1_amd64.deb
ccs-video-cleanup setup
```

Run setup as your normal desktop user, without sudo. It displays progress,
verifies the distribution FFmpeg's filters and loads the OCR/speech models.
Allow several minutes and roughly 1–2 GB for user tools and models, plus APT
libraries and your video jobs. Interrupted setup can be rerun; model downloads
remain cached. If a binary wheel is unavailable for your Python version,
setup fails with the pip error instead of silently compiling dependencies.

Open **Christ Church Video Cleanup** from the applications menu. A terminal
shows initial setup progress if setup has not been completed, then the browser
opens. Desktop launch starts services for the current session. Login startup
is off by default; select **Start automatically at login** in the tray menu
to enable it, or clear the checkmark to disable it. Changing this preference
leaves current processing running. Without user systemd, the launcher starts a background server.
Closing the browser does not stop video processing.

The logo is not distributed. Intros use the church name as text by default.
To add a logo you have permission to use:

```bash
ccs-video-cleanup setup --logo /path/to/logo.png
```

Application files are in `/usr/lib/ccs-video-cleanup`. Videos, models and the
private environment are in `~/.local/share/ccs-video-cleanup/`, or under your
`XDG_DATA_HOME`. Licence notices and an installed Python inventory are in
`third-party-notices/`. See [THIRD_PARTY.md](THIRD_PARTY.md).
CLI: `ccs-video-cleanup run 'URL'`; the existing review/render flags work.

## Updates

APT updates the standard dependencies. Update YouTube support without replacing
models or reinstalling AI tools:

```bash
ccs-video-cleanup setup --update-downloader
```

If a distribution upgrade changes Python's major/minor version, rerun setup;
the user environment must be recreated for that interpreter. Successful setup
records its Python version. Errors appear in the setup terminal; a successful
marker is only saved after imports, media filters and models have been checked.

## Switching from the original local installation

Only one service should use port 8765. Finish any active job, then:

```bash
systemctl --user disable --now ccs-video-cleanup.service
```

Original project jobs and models remain untouched. Copy required job folders
into the packaged app's `jobs/` folder if needed. An authorised logo can be
imported from the original project's `assets/church-logo.png` using the command
above. Its old desktop file is `~/.local/share/applications/ccs-video-cleanup.desktop`;
the package installs the distinct `ccs-video-cleanup-packaged.desktop`.

If upgrading the bundled 1.0 prototype, finish processing and stop its packaged
service before installing 1.1. User jobs stay in the same data directory:

```bash
systemctl --user stop ccs-video-cleanup-packaged-tray.service ccs-video-cleanup-packaged.service
sudo apt install ./ccs-video-cleanup_1.4.1_amd64.deb
ccs-video-cleanup setup
```

## Remove

```bash
systemctl --user disable --now ccs-video-cleanup-packaged-tray.service ccs-video-cleanup-packaged.service
sudo apt remove ccs-video-cleanup
```

Removal preserves videos, evidence and downloaded user tools. Without systemd,
stop the launcher's background server first. Delete the user data directory
only when you no longer need its contents.

## Rebuild

```bash
python3 packaging/build_deb.py --version 1.4.1
```

Requires `dpkg-deb`; no local venv, binary toolchain or model cache is needed.
The builder creates `dist/*.deb` and a SHA-256 checksum without installing it
or touching the running app. Before releasing changes, run the repository's
unit tests and verify the package/setup in the target distributions, including
an actual synthetic video render and offline model loading.

## Version 1.4.1 startup controls

Launch and setup no longer enable login startup. The tray checkbox controls both
the server and tray user units. On the first tray launch after upgrading from
1.4.0, the old implicit startup enablement is cleared without stopping current
work. Open the updated app once after installation to apply that migration;
then select **Start automatically at login** if wanted. The saved preference
is retained across subsequent launches and upgrades. See [validation](../docs/validation/v1.4.1.md).

## Version 1.4 audio and review

The native DeepFilterNet3 enhancer is downloaded directly from upstream, verified and installed in the user data directory. The approved settings match the original Linux installation: 20 dB maximum suppression, gentle filtering and constant gain targeting -20 LUFS. First setup requires internet; enhancement then runs locally. Improved caption checks, passage/boundary evidence and manual review are included. Player chapter labels are disabled. Install the new package and rerun `ccs-video-cleanup setup` as your desktop user, with processing idle; jobs and model caches are retained.

## Desktop tray and guide

The .deb includes the Linux tray script, orange icon, GTK/Ayatana dependencies and a separate user-service unit. Desktop launch starts both services. Closing the browser leaves work running. Tray quit stops the server and its workers; active work asks for confirmation. The packaged tray requires user systemd and a compatible desktop indicator host; some GNOME desktops need their usual AppIndicator extension enabled. Non-systemd fallback starts the web server without a managed tray.

The installed PDF is `/usr/share/doc/ccs-video-cleanup/CCS-Video-Cleanup-Linux-Guide.pdf`. [Read it online](../output/pdf/CCS-Video-Cleanup-Linux-Guide.pdf). Guided audio tests, resolution choice, confirmed deletion and YouTube/Spotify exports are included. Finish work and quit the tray before upgrading.
