# Local source-checkout installation

Open **Christ Church Video Cleanup** from the applications menu, or run `./open-cleanup`. The maintained operator instructions are the [user guide](USER_GUIDE.md) and the [Linux illustrated PDF](../output/pdf/CCS-Video-Cleanup-Linux-Guide.pdf). For the application-only installer, use the [packaging guide](../packaging/README.md); its data lives separately from this checkout.

The source installation retains downloads, samples, transcripts, OCR, plans and exports in `jobs/<video-id>/`. Cached sources are reused. New downloads default to the highest available resolution; the app lets you choose lower resolutions. It never upscales a cached source. Browser previews are lighter encodes; **Download full-quality sermon** provides `finished.mp4`.

Choose YouTube video, Spotify podcast audio, or both. Listen to the three preset tests or tweak and retest before export. Video adds a five-second church intro. Podcast MP3 uses the same selected conditioning, without intro silence. Finished outputs omit inferred player chapter labels. Nothing is published automatically.

Speech recognition, OCR and audio enhancement run locally. Stereo phase is checked before mono conversion to protect opposed-channel sources. Balanced cleanup uses the approved hall profile: DeepFilterNet3 capped at 20 dB, gentle filtering and constant gain targeting -20 LUFS, with peak protection. Tuning and validation details are in [Audio tuning](AUDIO_TUNING.md).

## Command line

```bash
./ccs-cleanup run 'https://www.youtube.com/watch?v=VIDEO_ID'
./ccs-cleanup analyze '/absolute/path/service.mp4'
./ccs-cleanup review 'URL' --start '00:38:00' --end '01:18:00' \
  --date '2026-10-04' --passage 'Romans 2:1–16' \
  --title 'Your sermon title' --confirm
./ccs-cleanup render 'URL'
```

Use your own dates and timestamps. CLI render creates a video with the saved audio profile; the browser provides destination choice and the sample comparison workflow. `render --no-stabilize` is available for steady sources. Preserve cached analysis and corrections when revisiting a service.

The source server is `ccs-video-cleanup.service`; its independent tray is installed by `tools/install_tray.py`. Closing the browser keeps work running. The tray shows current task/progress and offers **Quit and stop services**. A fresh launch does not select an old service. Packaged installations use separate service names; do not run both servers on port 8765.
