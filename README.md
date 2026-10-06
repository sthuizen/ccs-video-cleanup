# Christ Church Video Cleanup

Open **Christ Church Video Cleanup** from the applications menu, or run `./open-cleanup`. Paste a YouTube service URL and choose **Prepare sermon**.

The original download stays in `jobs/<video-id>/source.mp4`. Browser playback uses a separate 720p H.264 preview with the original finished audio copied intact. The download always uses the full-quality `finished.mp4`. The separate output is `finished.mp4`, with a five-second intro followed by the Bible reading and sermon. Chapter markers identify the reading, sermon, closing prayer and clearly signposted points. Nothing is uploaded or published.

New downloads select the highest reported video and audio bitrates available, with no resolution cap. Separate streams are merged without re-encoding the source. Existing downloaded sources remain cached. See the [yt-dlp format sorting documentation](https://github.com/yt-dlp/yt-dlp#sorting-formats) for the bitrate selection rules.

The app downloads with yt-dlp, uses English captions if available, otherwise transcribes locally with faster-whisper small.en on the CPU. Local OCR looks for slides; lexical matching against a cached public-domain Bible helps identify the verse range without an AI model. Conventional FFmpeg processing handles noise reduction, speech EQ, compression, mono conversion, loudness normalization and two-pass camera stabilization. The church logo is cached from the official website.

The app checks stereo phase before mixing: opposed channels would cancel the voice, so it selects one instead. This is needed for the supplied 4 October 2026 service. Normalization targets -18 LUFS and -1.5 dB true peak before AAC encoding. The supplied service measured -18.2 LUFS and -1.1 dB true peak after encoding. Stabilization uses a modest 3% zoom and limited correction so camera shake is reduced without large framing changes. Noise reduction cannot remove every cough, voice or room reflection without damaging the sermon.

If date, passage, title or cut points are unclear, the app shows its evidence and asks for the missing information. It does not invent titles, use the upload date as the sermon date, or guess a cut when evidence is weak. Play near the suggested reading and ending, edit the relevant fields and choose **Save details and create video**. When verse matching succeeds, the start is just before the first verse; otherwise the reading announcement is used as a candidate. the end should be after the sermon/closing prayer and before the closing-song introduction.

Downloaded files, transcripts and OCR are reused on repeat runs. There are no cloud AI calls, API keys or subscriptions. Speech recognition and OCR use cached local models. Processing time depends on service length and CPU load; downloading and the initial transcript can take several minutes. A single service is processed at a time. Each step shows an elapsed timer, measured percentage and approximate time remaining when available; completed steps retain their durations. Downloads show progress for the current file because video, audio and captions transfer separately. Setup and brief analysis show an indeterminate indicator until measurable work starts. Estimates adjust to the observed processing speed.

## Command line

```bash
./ccs-cleanup run 'https://www.youtube.com/watch?v=VIDEO_ID'
./ccs-cleanup analyze '/absolute/path/service.mp4'
./ccs-cleanup review 'URL' --start '00:38:00' --end '01:18:00' \
  --date '2026-10-04' --passage 'Romans 2:1–16' \
  --title 'Your sermon title' --confirm
./ccs-cleanup render 'URL'
```

The times above are examples. Use the timestamps for your own video. `render --no-stabilize` is available for sources that already look steady. Local files work through the command line.

The app defaults to Firefox download access and remembers changes to this setting in each browser. Keep YouTube signed in within Firefox; cookies are read locally on each download. Clear the field if you prefer anonymous downloads. If YouTube requests sign-in, use `firefox` in the download-access field or add `--cookies-from-browser firefox` to `run`. Cookies are read by yt-dlp locally; they are not copied into reports. Download failures and expired URLs are retained in the job logs. Live services must finish before clipping.

## Installation and maintenance

Tools are already installed in this folder's `.tools/bin` and `.venv`; Python 3.12 is managed by uv. No sudo is required. To recreate installation on x86-64 Linux, run `python3 setup.py`. The installer downloads official uv, Deno and BtbN FFmpeg releases and installs pinned Python dependencies. Model files are cached in `.models/whisper`.

YouTube changes frequently. If downloads stop working, update yt-dlp using:

```bash
.tools/bin/uv pip install --python .venv/bin/python --upgrade 'yt-dlp[default]'
```

A user systemd service runs the loopback-only web server at `http://127.0.0.1:8765`; it keeps running so a browser close does not stop a render. Closing the app window closes only the browser. The service starts when you log in; reopening the launcher also starts it if needed. Stop it with `systemctl --user stop ccs-video-cleanup.service`, or prevent login startup with `systemctl --user disable ccs-video-cleanup.service`. Partial processing stages can be restarted with **Prepare sermon**. Only successfully completed transcript/OCR caches are reused. Outputs are fully decoded and checked for mono audio and expected duration before the job is marked finished.

Tests: `.venv/bin/python -m unittest discover -s tests -v`. Tests include a full short render of opposed stereo audio with stabilization and an intro card.

Space: an 84-minute 720p service may use around 1–3 GB including source, PCM analysis audio, intermediate encode and final MP4. Files are retained for review and recovery. You can remove a completed job folder when you no longer need its files.

## Debian / Ubuntu package

A bundled amd64 `.deb` installer and rebuild instructions are described in [packaging/README.md](packaging/README.md). It includes the local models and media tools; APT supplies the declared system libraries. The packaged application keeps job data in your home directory.
