# Troubleshooting

[Home](../README.md) · [Operator guide](USER_GUIDE.md)

| Symptom | Action |
|---|---|
| APT cannot find a dependency | Confirm amd64, Ubuntu 24.04 or Debian 13; update APT indexes. Enable Ubuntu `universe`. Older distributions need separate work rather than force-installed incompatible packages. |
| First-run setup fails | Run `ccs-video-cleanup setup` in a terminal as your normal user. Check the first relevant error, internet access and free space. Rerun after fixing it; completed model downloads remain cached. |
| “No matching distribution” from pip | Check the supported distro/Python versions. Setup requires binary wheels and deliberately does not silently compile native packages. |
| App does not open | Run `ccs-video-cleanup --open` in a terminal and inspect its output. Check the packaged service using the commands below. |
| Port 8765 already in use | The old and packaged services may both be running. Finish active processing, then stop the installation you are no longer using. See migration instructions. |
| YouTube requests sign-in or returns download errors | Sign into YouTube in Firefox and use Firefox download access. If still failing, run `ccs-video-cleanup setup --update-downloader`; retry after updating. |
| It keeps asking for passage/title/boundaries | Listen around the suggested timestamps and enter the correct details manually. Unusual service structure can exceed automatic rules. |
| Another video is processing | Wait for the existing job. CLI and desktop share a lock. Do not delete the lock file to bypass an active render. |
| Progress appears stuck | Inspect stage log timestamps and CPU/disk activity. Local recognition or video encoding can take a long time; do not launch a competing render. |
| Output framing is unsuitable | Review the master and rerender with `--no-stabilize` if stabilization is unnecessary. |
| Speech is weak after mixing stereo | Preserve the channel-phase check. Opposed channels can cancel speech under direct `-ac 1`; inspect the source and job audio evidence before changing filters. |
| Preview will not play | Check `preview-validation.json` and preview logs. Download/check `finished.mp4` separately; the browser preview is a separate encode. |
| App breaks after distribution/Python upgrade | Rerun setup. The private environment must match the new Python major/minor. Back up user data before maintenance. |

## Read service and job logs

For the package:

```bash
systemctl --user status ccs-video-cleanup-packaged.service
journalctl --user -u ccs-video-cleanup-packaged.service -n 100 --no-pager
```

For the original folder installation, replace the service name with `ccs-video-cleanup.service`. If systemd is unavailable, inspect the terminal from the launcher and the job logs. The actual user data path follows `XDG_DATA_HOME`, if set.

```bash
cat ~/.local/share/ccs-video-cleanup/jobs/VIDEO_ID/status.json
```

Look at the named stage log in that folder. Correct the reported cause, then retry **Prepare sermon** or the appropriate CLI command. Successfully completed caches are reused. A failed render is not a finished result; inspect `validation.json` and `intro.png` before accepting it.

## Reporting a problem

Use the repository's [issues](https://github.com/thenailedone/ccs-video-cleanup/issues). Include package version, distro/Python version, action, error and the smallest relevant log excerpt. Explain whether it is the package or original installation. Remove credentials, signed download URLs and sensitive transcript material. Do not attach cookies, full private recordings, home directories or model/venv archives. A short synthetic reproduction is preferable when the problem is about rendering or UI logic.

## Windows first setup and launch

Open **Setup log** from the application's Start menu folder, or expand **Setup details** in the browser. **Try setup again** resumes preparation after fixing internet access or approving the Microsoft prerequisite. Do not delete video jobs to repair tool setup. A failed hash check requires a clean retry or an updated release, never disabling verification. For a managed PC, an administrator may need to install the Microsoft Visual C++ x64 runtime.

An unknown-publisher/SmartScreen prompt is possible because the church installer is unsigned. Confirm the private release origin and checksum. Normal use does not require administrator rights. Another application occupying port 8765 prevents launch; close that conflicting application and reopen the shortcut. Check `%LOCALAPPDATA%\CCSVideoCleanup\server.log` if launch still fails.

Updates and uninstall refuse to interrupt active processing. Finish the job first. Browser closing does not stop the server; reopening the shortcut reconnects. Uninstall retains `%LOCALAPPDATA%\CCSVideoCleanup`, including jobs and models. See the [Windows guide](../packaging/windows/README.md) for command-line maintenance.

On a new Windows installation, the default browser may show its own welcome screens before the app page. Complete that browser setup; the church application does not require browser sync or a Microsoft account.

## 1.4 audio, exports and tray

- Choose a prepared service before opening its clip/audio steps. Fresh launch intentionally starts without a selection.
- Audio tests show activity in the pinned bar. After changing a slider, recreate and listen to the test before export. Reset restores the chosen preset.
- Select at least one destination. MP3 downloads appear after podcast validation; full-quality MP4 is separate from the light preview.
- Windows: check the notification area's hidden-icons overflow for the church icon. Closing the browser keeps the server running; use the tray to quit.
- Linux: the tray needs GTK/Ayatana AppIndicator and a desktop tray host. Check `systemctl --user status ccs-video-cleanup-packaged-tray.service` for the packaged app. Desktop environments without a tray host still have browser progress.
- If a cached file has a lower resolution, choose a higher resolution and prepare again to download that source. The app does not invent detail by upscaling.
- Delete controls are under **Manage saved services**, closed by default. Review, acknowledgment and a typed phrase are all required. Deleted jobs go to Trash/Recycle Bin.
