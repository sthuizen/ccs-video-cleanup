# Christ Church Southampton video workflow

This workspace contains an installed local sermon-preparation app. When the user supplies a service URL to process, use `./ccs-cleanup run 'URL'`. Read `README.md` for operation. Prefer this pipeline over rebuilding the workflow or using remote AI services.

The desktop app is at http://127.0.0.1:8765 and is launched as **Christ Church Video Cleanup**. The user service is `ccs-video-cleanup.service`. Downloads, analysis evidence and media are kept in `jobs/<video-id>/`.

For routine work:

1. Run the pipeline and allow the download, cached local speech recognition and local OCR to finish. Poll `status.json` or the running shell session with reasonable intervals.
2. Read `plan.json`. Strong evidence permits automatic rendering. If an issue needs clarification, inspect its evidence and only the relevant transcript timestamps or frames. Ask only for the unresolved fields; do not ask the user to re-confirm clear dates, passages or boundaries.
3. Store supplied corrections with `./ccs-cleanup review 'URL' --title '…' --confirm` (other review flags cover timestamps, date and passage). Then use `./ccs-cleanup render 'URL'`. Preserve the source and cached analysis. Intro changes reuse the already processed sermon.
4. Inspect `validation.json` and the intro frame before reporting a finished result. Deliver `finished.mp4` and concise source/cut information. Do not publish or upload unless the user requests it.

Speech recognition and OCR run locally. No cloud AI API is configured. Use language-model reasoning sparingly, for ambiguity only, rather than re-analyzing a whole clear sermon. Never invent an official sermon title or substitute upload dates for service dates. If the user wants a descriptive title, derive it from the recorded words and distinguish it from an explicitly stated title.

The 4 October 2026 source has opposed stereo channels. Keep the automatic channel phase check before transcription and mono conversion; direct `-ac 1` mixing can cancel the speech. Audio cleaning and video stabilization use FFmpeg and require no AI.

For pipeline edits, run `.venv/bin/python -m unittest discover -s tests -v` after substantive changes. The media test uses a temporary synthetic source; the shared pipeline lock prevents concurrent production renders. Do not restart a render to make unrelated documentation/UI changes.
