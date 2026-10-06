# Operator guide

[Home](../README.md) · [Installation](../packaging/README.md) · [Troubleshooting](TROUBLESHOOTING.md)

## Before starting

Use a completed service rather than a live stream. Keep several gigabytes free: source, analysis audio, intermediate encodes and final video all take space, and higher-resolution recordings can be much larger. The computer must stay awake during processing. The app processes one job at a time.

Open **Christ Church Video Cleanup**. A browser close leaves the server and current processing running; reopen the app to see progress. For the package, data normally lives in `~/.local/share/ccs-video-cleanup/`; the original project installation keeps jobs in its project folder. See [maintenance](MAINTENANCE.md) before moving data between installations.

## Download and analyze

Paste the service URL and choose **Prepare sermon**. Download access defaults to Firefox and is remembered in that browser. If YouTube requests sign-in, sign into YouTube in Firefox on this computer and use `firefox` in the download-access field. Clear the field for anonymous downloads. Browser cookies are read locally by yt-dlp; do not export or share them to report a problem.

Downloads select the highest reported video/audio bitrates available without a resolution cap. Separate streams are merged without re-encoding the source. English captions are used when available; otherwise the app transcribes locally. OCR is performed when title/passage evidence requires it.

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

Times are measured against the original service, not the new video with its added intro. Use `HH:MM:SS` for clarity. A proposed boundary is evidence to check, not proof. Do not invent an official title. When clear verse matching succeeds, the start is placed just before the first verse; otherwise the reading announcement can be a candidate.

Choose **Save details and create video** after checking the fields. A clearly supported plan can render automatically. Corrections reuse the downloaded source, transcript and OCR. Intro-only changes can reuse the already processed sermon; preserve the job folder for this to work.

## Check and collect the result

Watch the intro, first spoken words and closing words. Confirm date/title/passage, intelligible audio and sensible framing. The five-second intro precedes the selected reading/sermon. Chapter markers are included when supported by evidence; uncertain sermon points may have no chapter.

The download is `finished.mp4`, the full-quality H.264/mono AAC master. Browser playback uses a separate preview at up to 720p, with the finished audio copied intact. Preview softness does not mean the downloaded master has been reduced to preview quality.

Automatic validation decodes the output and checks expected duration and mono audio. It cannot certify that the operator selected the correct theological passage, date or spoken boundary. Noise reduction cannot remove every cough or room reflection without harming speech; stabilization applies modest framing changes. Source media is retained.

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
