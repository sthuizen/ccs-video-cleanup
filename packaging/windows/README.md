# Windows church-use installer

This folder builds a Windows 10/11 x64 installer on Linux using NSIS. The application, embedded CPython 3.13.16, pip bootstrap wheel, Bible text and church-authorized branding are included. Specialist Python packages, FFmpeg/Deno and the speech model are prepared automatically on first launch. No system Python installation or cloud AI account is needed.

## Church operator instructions

Download the Windows `setup.exe` from the private repository release and run it. The wizard installs for the signed-in user, creates a desktop shortcut and adds **Christ Church Video Cleanup** to the Start menu. Open that shortcut. First launch displays a browser setup page with progress and retry controls. Keep the computer awake and online until the app opens.

Use a 64-bit Intel/AMD Windows PC. ARM and 32-bit Windows are not supported by this installer. A modern CPU, 8 GB RAM and several GB free for tools/models are recommended; video jobs need additional space. Setup may take several minutes depending on internet speed. Processing time depends on the recording and CPU. If native AI libraries need Microsoft's Visual C++ components, setup downloads the official installer, checks its Microsoft signature and asks Windows to install it. Approve the Windows administrator prompt, or ask your computer administrator to help. This is a one-time system prerequisite; the app itself installs for the current user.

Windows downloads start without browser cookies by default, so Firefox is optional. If YouTube requests verification, install/open Firefox, sign into YouTube there and enter `firefox` under **Download access**. Firefox is preferable to Chromium browser-cookie extraction on current Windows.

After setup, paste the completed YouTube service URL, choose **Prepare sermon**, review uncertain fields and create the finished video. The church logo appears in the app and intro card. See [the operator guide](../../docs/USER_GUIDE.md). Closing the browser leaves processing running. Reopening the shortcut reconnects to the existing server. The app starts when opened; it does not install a Windows system service or run automatically at login.

The Windows app is local at `http://127.0.0.1:8765`. It does not publish videos. The browser preview and full-quality download remain distinct. Source, recognition evidence, manual details and finished media are retained locally.

## Locations and maintenance

- App/runtime: `%LOCALAPPDATA%\Programs\CCSVideoCleanup` by default.
- Videos, evidence, downloaded tools and models: `%LOCALAPPDATA%\CCSVideoCleanup`.
- Logs: `setup.log` for preparation and `server.log` for the local server; stage logs remain inside individual jobs.
- Dependency inventory and model/media notices: `third-party-notices` in the data folder.

Start menu shortcuts open the data folder and setup log. Back up `jobs` and referenced local input videos before maintenance. The uninstaller preserves the separate data folder. Finish processing before updating or uninstalling; an active processing lock prevents interruption. Install a newer release to change pinned dependencies or downloader versions. Jobs/models are preserved when setup refreshes private Python libraries.

Command-line example from PowerShell, using the default install path:

```powershell
$app = "$env:LOCALAPPDATA\Programs\CCSVideoCleanup"
& "$app\runtime\python.exe" "$app\app\windows\launcher.py" --cli analyze 'C:\Videos\service.mp4'
& "$app\runtime\python.exe" "$app\app\windows\launcher.py" --cli run 'https://www.youtube.com/watch?v=VIDEO_ID'
```

The usual `review` and `render` CLI flags apply. `--setup` retries preparation; `--shutdown` closes an idle server and refuses an active job. The CLI and desktop use the same cross-process lock and data folder. Do not delete lock files to bypass running work.

## Installer trust and dependencies

The installer is not Authenticode signed unless the church supplies an appropriate signing certificate. Windows may display an unknown-publisher/SmartScreen prompt. Verify the release checksum and origin; do not disable Windows protection globally. A signed distribution is a future improvement, not something a Linux build alone can claim.

Embedded CPython retains its `LICENSE.txt`; the pip wheel retains its licence. First-run Python dependencies are pinned with hashes in `requirements.lock`, with binary wheels only. The historical RapidOCR wrapper is installed separately without dependencies and with its Python metadata override; native dependencies are not exempted from compatibility checks. Its functional compatibility must be demonstrated by actual OCR in target Windows tests.

FFmpeg is downloaded directly from a named upstream BtbN build and verified against its SHA-256. It is not redistributed inside this installer. The source URL and checksum are in `downloads.json`; downloaded upstream docs/notices are retained. Upstream release retention may eventually remove an asset; then publish a new tested app version with an updated manifest rather than bypassing verification. Python dependency wheel licences stay in the private package directory. Model licence/card notices and a resolved inventory are saved separately.

Microsoft's runtime is also downloaded directly and signature-checked, rather than redistributed inside the installer. See [Microsoft's download and runtime guidance](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

The logo is included for the church's requested use. This does not grant unrelated public redistribution rights. Keep the repository private and see [application rights](../../RIGHTS.md). Windows evaluation images and VM disks are testing tools, not application release attachments.

## Build on Linux

Requires Python with Pillow and an NSIS compiler. The raw logo remains outside Git; download the church-use `church-logo.png` asset from the private Windows release and place it at `assets/church-logo.png` (or pass its path with `--logo`):

```bash
python3 packaging/windows/build.py --logo assets/church-logo.png
```

If NSIS is extracted locally, set `NSISDIR` to its `usr/share/nsis` folder and pass `--makensis PATH`. The builder verifies/downloads the embedded Python and pip assets, stages source and branding under ignored `.tools/windows/build`, and writes an installer/checksum under ignored `dist`. It neither installs the app nor touches the production server.

To update dependencies, compile `requirements.in` for Windows x64/Python 3.13 with hash generation, retain RapidOCR's separate lock and test on actual Windows. Bump all installer/launcher version fields together. Record first-run setup, real OCR, offline speech-model inference, synthetic opposed-stereo render, chapters, preview audio, paths with spaces/non-ASCII, duplicate launch, update/uninstall behavior and retained data. Linux tests alone do not prove Windows compatibility.
