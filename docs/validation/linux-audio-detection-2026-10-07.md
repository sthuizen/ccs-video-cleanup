# Linux audio and detection validation — 7 October 2026

The original Linux installation was updated and all three real recordings regenerated. **50 Python tests passed**, including installed-model processing, opposed-stereo handling, complete synthetic rendering, master audio alignment, preview integrity, setup checksum failure and caption refinement. Four existing browser-interface checks also passed. This record does not validate a new Windows or Debian installer. Human listening confirmation remains pending.

## Complete real outputs

| Service | Passage | Retained manual cut (source seconds) | Finished duration | LUFS | True peak | Full decode |
|---|---|---|---:|---:|---:|---|
| 2026-09-06 | Acts 2: 42-47 | 2042.0–3730.0 | 1693.021 s | -20.26 | -1.90 dBTP | Passed |
| 2026-09-20 | Romans 1:8–17 | 2665.94–4983.1 | 2322.221 s | -20.40 | -1.41 dBTP | Passed |
| 2026-10-04 | Romans 2:1–16 | 2301.0–4574.0 | 2278.021 s | -20.49 | -1.48 dBTP | Passed |

Every output has mono AAC audio and its five-second church intro. All three intro frames were visually inspected. The master encodes enhanced PCM once with exact initial silence; it does not re-encode the sermon AAC across the intro join. Full decoding and encoded true-peak measurements cover each entire finished file.

Original source identity (path, byte size, modification timestamp), manual cuts, original transcript, review and source-info JSON remain unchanged. H.264 packet counts and aggregate SHA256 of each sermon video payload match the previous output exactly: audio-only regeneration reused the stabilized video. Previous complete outputs and metadata remain under each local job’s `previous-output/` directory. Recordings, transcripts, model binaries and raw experiment logs are excluded from Git.

## Final master comparisons

These measurements use excerpts decoded from the **actual complete finished outputs**, not only experimental WAV files. Voice RMS is matched to -28 dBFS and processing delay is removed before applying common source masks. Negative differences mean less background energy.

| Service / source start | Sample | Background mask | New minus previous | Previous/new delay |
|---|---:|---|---:|---|
| 2026-09-06 / 2600 s | 60 s | quiet-frame proxy, 9.00 s | -13.39 dB | 47.4/1.2 ms |
| 2026-09-20 / 3000 s | 90 s | quiet-frame proxy, 13.50 s | -11.89 dB | 46.3/0.0 ms |
| 2026-10-04 / 2600 s | 90 s | word-gap quiet frames, 13.74 s | -6.80 dB | 46.3/0.0 ms |
| 2026-10-04 / 4510 s | 60 s | word-gap quiet frames, 9.27 s | -4.01 dB | 46.3/0.0 ms |

For caption-only sources, masks use the lowest 15% of source 10 ms RMS frames; voice matching uses the highest 40%. For the October source, masks use gaps longer than 0.5 seconds between cached words, excluding 150 ms at each edge; voice uses word centres. The background column additionally restricts either mask to source frames below -40 dBFS. The September 6 result is near the digital floor and must not be interpreted as equivalent audible crowd-noise removal. October’s louder laughter is excluded by this background threshold and can remain strongly audible. Using all October word-gap frames, including louder crowd sounds, the sermon pause energy is 1.16 dB higher and the prayer 0.25 dB lower than before; this makes the limitation explicit. These are energy proxies, not separation quality or listening scores.

## Passage and boundaries

Independent analysis without saved reviews recovered Acts 2:42–47, Romans 1:8–17 and Romans 2:1–16. Automatic reading/end evidence is recorded in the companion JSON. The September 20 start includes the reader’s announcement about 24.6 seconds before the existing first-verse cut. Missing September 6 caption evidence was repaired by bounded local checks on original phase-safe audio. See [detection evidence and limits](../DETECTION_VALIDATION.md). Your manual cuts continue to control these finished outputs. Unknown reading/sermon transitions remain unset.

## Reproduce and evaluate

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/compare_audio.py wrFPGvIIEWk --start 2600 --seconds 60
.venv/bin/python tools/compare_audio.py --start 3000 --seconds 90 -- -jFmoQpDCac
.venv/bin/python tools/compare_audio.py c4qtGGSgBQI --start 2600 --seconds 90
.venv/bin/python tools/compare_audio.py c4qtGGSgBQI --start 4510 --seconds 60
```

After a completed render with preserved previous output, this utility writes aligned, voice-matched original/previous/new MP3 clips, masks/measurements and a local `audio-review.html` page. Open `/files/JOB_ID/audio-review.html` on the loopback app to compare them and play the source around detected edges. Use one listening volume, especially for quiet prayer and final syllables. The MP3s are audition aids; `finished.mp4` remains the master.

The selected profile is DeepFilterNet3 with 20 dB maximum suppression, gentle FFT suppression/soft expansion, constant gain targeting -20 LUFS and a limiter without makeup. The verified tool and model work locally. The current service was restarted only after production processing and tests finished. The existing manual interface remains available. See [research, primary sources and limitations](../AUDIO_RESEARCH.md) and [machine-readable results](linux-audio-detection-2026-10-07.json).
