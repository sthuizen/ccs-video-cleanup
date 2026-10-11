# Operator guide

[Home](../README.md) · [Installation](../packaging/README.md) · [Troubleshooting](TROUBLESHOOTING.md)

## Before starting

Use a completed service rather than a live stream. Keep several gigabytes free: source, analysis audio, intermediate encodes and final video all take space, and higher-resolution recordings can be much larger. The computer must stay awake during processing. The app processes one job at a time.

Open **Christ Church Video Cleanup**. A browser close leaves the server and current processing running; reopen the app to see progress. For the package, data normally lives in `~/.local/share/ccs-video-cleanup/`; the original project installation keeps jobs in its project folder. See [maintenance](MAINTENANCE.md) before moving data between installations.

## Download and analyze

Paste the service URL and choose **Prepare sermon**. Download access defaults to Firefox on Linux and to anonymous access on Windows; your choice is remembered in that browser. If YouTube requests sign-in, sign into YouTube in Firefox on this computer and use `firefox` in the download-access field. Clear the field for anonymous downloads. Browser cookies are read locally by yt-dlp; do not export or share them to report a problem.

Paste the URL and check its available resolutions. The selector defaults to the highest; choose a lower resolution before preparing if you want a smaller video. Downloads keep the best available audio. For an already saved source, lower choices resize the finished video and preserve the original and cached analysis. Separate streams are merged without re-encoding the source. English captions are used when available; otherwise the app transcribes locally. In the app, missing or weak reading/ending evidence also triggers short local audio checks, whose results are stored separately from the original captions. OCR is performed when title/passage evidence requires it.

Percentages and estimates appear where work is measurable. Setup and brief analysis may show an indeterminate indicator. Download percentages concern the current file, because video, audio and captions can transfer separately. Estimates change with observed speed and CPU load.

## Review uncertain details

Atypical service order, announcements, imperfect captions and unclear slides can confuse the proposed reading/sermon boundaries. Correct the fields in the existing review interface when needed. Listen to the evidence around those points; there is no need to reanalyze a whole service just to supply a title.

| Field | What to enter |
|---|---|
| Start | Source timestamp just before the desired Bible reading begins, or the intended sermon start if no reading is included |
| End | Source timestamp after the sermon/closing prayer and before unwanted music or announcements |
| Date | Actual service date in `YYYY-MM-DD` form; not the YouTube upload date |
| Passage | The recorded Bible passage and verse range |
| Title | Explicitly stated sermon title, or an operator-approved descriptive title based on recorded words |

Times are measured against the original service, not the new video with its added intro. Use `HH:MM:SS` for clarity. A proposed boundary is evidence to check, not proof. Do not invent an official title. The detector includes a brief reader announcement immediately before matched Scripture; a longer host introduction or prayer is usually excluded. Saved manual cuts remain authoritative.

In the updated local app, choose **Save details and make audio tests** after checking the fields. Listen to the same quiet and louder excerpts in three versions, choose the closest result, and use **Choose and tweak audio** to adjust and recreate a test if needed. Then choose the orange **Choose and create** button for your selected destinations. The desktop app waits for this choice even when analysis is clear; the CLI retains automatic rendering. See [audio review, controls and research](AUDIO_TUNING.md). Corrections reuse the downloaded source, transcript and OCR. Intro-only changes can reuse the already processed sermon; preserve the job folder for this to work.

## Check and collect the result

Watch the intro, first spoken words and closing words. Confirm date/title/passage, intelligible audio and sensible framing. The five-second intro precedes the selected reading/sermon. Player chapter labels are disabled, so scrubbing does not display inferred reading or sermon labels.

The download is `finished.mp4`, the full-quality H.264/mono AAC master. Browser playback uses a separate preview at up to 720p, with the finished audio copied intact. Preview softness does not mean the downloaded master has been reduced to preview quality.

Automatic validation decodes the output and checks expected duration and mono audio. The renderer also measures final loudness and true peak. It cannot certify that the operator selected the correct theological passage, date or spoken boundary. Speech cleanup reduces some background noise and uses constant gain to avoid lifting quiet pauses, but cannot remove every cough or room reflection without harming speech. Listen especially to soft prayer, word endings and audience sounds. Stabilization applies modest framing changes. Source media is retained.

## Command line

The package executable is `ccs-video-cleanup`; the original project wrapper is `./ccs-cleanup`. Examples below use the package. Replace the URL and all sample details with the actual service:

```bash
ccs-video-cleanup run 'https://www.youtube.com/watch?v=VIDEO_ID'
ccs-video-cleanup analyze '/absolute/path/service.mp4'
ccs-video-cleanup review 'URL' --start '00:38:00' --end '01:18:00' \
  --date '2026-10-04' --passage 'Romans 2:1–16' \
  --title 'Operator-approved sermon title' --confirm
ccs-video-cleanup render 'URL'
ccs-video-cleanup render 'URL' --no-stabilize
```

`analyze` stops before rendering. `review --confirm` stores corrections and validates required values; follow it with `render`. `run --cookies-from-browser firefox` reads Firefox access locally. `render --no-stabilize` suits footage that already looks steady. `serve --port 8766` can start a separate loopback server, but all processes sharing a data directory still share the processing lock.

## Job evidence

Under `jobs/<video-id>/`, `source.mp4` is the original download; `transcript.json`/`.txt` and `screen-text.json` are cached evidence; `plan.json` is the proposed/current cut; `review.json` records supplied corrections; `status.json` and stage `.log` files show progress/errors. `validation.json` accompanies `finished.mp4`; `intro.png` is a quick intro check. Preserve these together for later correction. Local-file jobs retain a source-path reference: back up the referenced original too.


## Manage saved services

Open **Manage saved services** beneath the prepared-service selector. Each finished service (video or podcast) has a trash button beside its name. Review the named service and stored file size, choose **Review deletion**, tick the acknowledgment, and type **DELETE** before choosing **Move to Trash**. **Delete all saved services** includes unfinished saved jobs too and requires **DELETE ALL**. Both actions are unavailable during processing. Confirmations expire after five minutes and must be repeated if any saved files change.

Deletion moves the whole job folder (source download, analysis, samples and generated videos) to the computer’s Trash or Recycle Bin. A local source outside the app is preserved. Restore the folder to its original `jobs/` location through the desktop Trash to bring it back into the list. Space is reclaimed when you empty Trash using your desktop.

## Linux and Windows background tray

Both desktop packages have a tray controller independent of the browser. Linux uses an Ayatana indicator; Windows uses the native notification area (possibly its hidden-icons overflow). Closing browser windows leaves processing running. Its menu offers **Open Christ Church Video Cleanup**, current task, percentage (when measurable), elapsed time, estimated remaining time and **Quit and stop services**. Quit stops the local server and its download/FFmpeg worker processes, then removes the tray icon. Quitting during processing asks first; source files and saved analysis remain, but incomplete output may need to be recreated. The desktop shortcut starts the server and tray again.

The tray uses the system Python GTK bindings, the installed Ayatana indicator library and the desktop tray host. To install its user-service unit for another Linux source checkout, run `.venv/bin/python tools/install_tray.py`. The .deb includes the tray controller and dependencies; the packaged tray requires user systemd and a compatible desktop tray host. Windows uses the built-in PowerShell/WinForms notification icon and a process group to stop server children on exit.

The pinned step bar also shows the selected service’s current task and progress. On Linux the tray shows a percentage beside its icon while measurable work runs, **Working** when a percentage is unavailable, or **Review**/**Listen** when it needs input. Tray progress follows the active background job even when the browser is closed.

### YouTube and Spotify exports

Use **Where will you share this sermon?** to choose **YouTube · video**, **Spotify · podcast audio**, or both. YouTube is selected by default. Listen to the same three presets, optionally tweak and recreate the tests, then choose the tested audio to create your selected exports. Step 5 provides separate downloads.

The YouTube file is the existing full-quality MP4 with the church intro. The Spotify podcast is a mono MP3 at 48 kHz and 128 kbps, encoded directly from the same conditioned PCM and chosen volume/peak protection. It starts with the selected clip, without the video title card’s silent lead-in. Podcast-only export skips video stabilization and encoding. The app checks the entire MP3 and its duration, format and audio peaks before offering it for download. Upload the MP3 manually in Spotify for Creators; the app does not publish automatically. [Spotify’s accepted podcast file formats](https://support.spotify.com/ag/creators/article/publishing-audio-episodes/).

Illustrated guides: [Linux PDF](../output/pdf/CCS-Video-Cleanup-Linux-Guide.pdf) and [Windows PDF](../output/pdf/CCS-Video-Cleanup-Windows-Guide.pdf). Windows progress appears in the icon tooltip and right-click menu. Fresh launch shows Ready until a service is selected; active background work takes priority.
