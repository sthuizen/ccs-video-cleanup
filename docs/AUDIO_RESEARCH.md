# Speech enhancement in a large church hall

Research and local experiments conducted on 7 October 2026. The goal is to reduce distracting room noise while preserving a natural speaker and avoiding the former increase in background sound during quiet periods. This document distinguishes signal measurements from listening judgments. The recording and original analysis caches remain intact.

## Why the former audio could sound noisier

The previous chain applied FFT suppression, presence EQ, compression and two-pass `loudnorm` toward -18 LUFS. At matched speaker level, existing finished audio increased quiet-frame energy by approximately 1.7 dB (Romans 1) and 2.9 dB (Acts) relative to the previous cleaning stage before normalization; it still reduced that energy relative to the original source. A nominal `linear=true` does not guarantee constant gain: FFmpeg falls back to dynamic normalization if its true-peak or loudness-range requirements cannot be met. The three stored source measurements were approximately -28.6, -29.9 and -34.1 LUFS with much louder isolated peaks. Achieving -18 LUFS therefore needed substantial gain and often dynamic processing. Raising quiet periods makes room sound and congregation noise more audible. Reducing the volume of an entire recording is not evidence of successful noise removal.

The revised playback stage measures loudness, chooses one gain for the entire selection, caps increases at 18 dB, and limits excessive peaks without automatic makeup gain. It targets -20 LUFS, though a cap or limiting can leave the result quieter. There is no time-varying upward normalization. The limiter has compensated lookahead; it can reduce nearby sound after an exceptional peak, but never boosts a quiet pause. Final AAC/true-peak validation is still necessary because a sample limiter is not an encoded-output true-peak guarantee.

The three source recordings also have substantially opposed stereo channels. The existing phase check and channel selection must precede processing; simple stereo-to-mono averaging could cancel the intended voice.

## Selected processing

The Linux version can use an independently downloaded, verified native DeepFilterNet3 executable. It runs entirely locally and embeds its model; it requires no cloud service, Python neural runtime or audio upload. The model attenuation limit is 20 dB. A gentle FFmpeg stage follows:

```
highpass=f=75,lowpass=f=10000,afftdn=nf=-40:nr=8:tn=1:gs=8,
agate=threshold=0.004:ratio=1.5:range=0.5:attack=10:release=300:knee=4:detection=rms
```

The line break above is for reading; the actual filter string is continuous. The high/low-pass filters reduce rumble and unnecessary high-frequency content. FFT suppression addresses persistent noise, while neural enhancement also addresses some changing background sounds. The downward expander has a soft knee, modest ratio, 300 ms release and maximum 6 dB attenuation. It is deliberately gentler than a hard silence gate. Presence boost and general compression have been removed.

If the neural tool is absent, the same gentle FFmpeg stage remains available. It was less effective on the recording with the clearest nonstationary background noise. The method and exact tool hash are saved in the job's audio settings; adding or replacing the tool changes the cache identity.

Audio extraction includes context before and after the chosen section. At 48 kHz the FFT filter delayed these test signals by approximately 25 ms; this delay is removed. Native `deep-filter -D` compensates its own lookahead but returned approximately 30 ms less audio than input. Extra tail context and exact final trimming prevent the last syllables being replaced by padded silence. The requested output duration is preserved. Successful processing is cached only after all stages complete; failed work preserves the previous cache.

## Experiments and actual measurements

Four real-source excerpts were tested: the 4 October Romans 2 sermon (2600–2690 seconds), its quieter closing prayer (4510–4575), the 6 September Acts sermon (2600–2690), and the 20 September Romans 1 sermon (3000–3090). All used the phase-safe source channel at 48 kHz. Variants included the previous cleaning chain, the existing completed video, gentler FFT suppression, twelve expander settings, native DeepFilterNet3 at 12/20/full attenuation, current Xiph RNNoise, and DeepFilterNet20 plus the gentle FFT/expander chain.

Every comparison matched the main speaker RMS. The FFT-only variants were aligned by 25 ms and RNNoise by 10 ms before applying the source masks. Correlation measured approximately 46.3 ms delay in the existing finished video: FFT delay plus approximately 21.3 ms from the AAC intro join. Its masks use that measured delay. Ignoring this delay produced misleading pause measurements. The following values are the change in pause or quiet-frame energy relative to the source, at matched speaker level. Negative values indicate less energy.

| Processing | Romans 2 sermon | Romans 2 prayer | Acts quiet-frame proxy | Romans 1 quiet-frame proxy |
|---|---:|---:|---:|---:|
| Existing completed video | -4.35 dB | +0.08 dB | -4.90 dB | -5.36 dB |
| Previous cleaning, before playback normalization | -2.24 dB | -0.10 dB | -7.81 dB | -7.05 dB |
| Gentle FFT plus soft expander | +0.01 dB | -0.15 dB | -14.35 dB | -9.00 dB |
| DeepFilterNet, 12 dB cap | 0.00 dB | -0.02 dB | +5.48 dB | -7.94 dB |
| DeepFilterNet, 20 dB cap | 0.00 dB | -0.02 dB | +4.21 dB | -10.76 dB |
| DeepFilterNet20 plus gentle FFT/expander | +0.02 dB | -0.09 dB | -14.46 dB | -17.87 dB |
| Current RNNoise | +0.06 dB | -0.01 dB | -26.76 dB | -20.27 dB |

These numbers describe the experimental chain before final playback gain and encoding. They do not replace a comparison of the final rendered output.

Romans 2 has local word timestamps: speech masks cover word centres; pause masks cover gaps longer than 0.5 seconds with 150 ms margins. A pause can still contain audience laughter, voices or reflected sermon sound. The other recordings have overlapping captions without word timestamps, so their proxies use the source's highest 40% and lowest 15% of 10 ms RMS frames. Acts has nearly digitally silent frames: its apparently very large RNNoise improvement is therefore not evidence of equivalent audible congregation-noise removal. There is no clean reference recording, so a valid reference-based SI-SDR, PESQ or STOI score cannot be reported.

The clear useful result is reduced low-level background on the Romans 1 recording. The selected chain reduced its quiet-frame proxy by 17.9 dB while retaining the main voice. The model did not substantially reduce speech-like audience noise or reverberant voice in the October sermon/prayer. Stronger settings would not automatically fix that limitation.

## Actual encoded audio-stage benchmark

The revised `ccs.audio.prepare` was also exercised on the four source excerpts, including contextual extraction, the installed verified model, compensated FFT, measured constant gain and limiter. During candidate selection, the audio was AAC encoded, joined to a five-second silent intro, and AAC encoded again to reproduce the former renderer's audio stages. The final renderer now copies the joined video and encodes cached cleaned PCM once, with exact five-second initial silence; it avoids this unnecessary second lossy audio generation. This is an excerpt-level integration benchmark; it does not substitute for checking the complete final videos, whose selected-section loudness measurements can choose a different gain. The historical double-encoded benchmark retained approximately 21.3 ms join delay; correlation aligns both old and new audio before comparison. The final single-encode renderer avoids that join delay; final whole-video validation should take precedence over these candidate-selection excerpts.

| Excerpt | New minus existing finished pause energy, matched speaker |
|---|---:|
| Romans 1 | **-12.40 dB** |
| Acts near-digital-floor proxy | -9.48 dB |
| Romans 2 sermon | +1.55 dB |
| Romans 2 prayer | +0.25 dB |

The aggregate pause result is strongly improved for Romans 1, but hides a different result for quieter October background. In the October sermon, only 1.03 seconds of energetic pause frames account for **99.3% of all pause energy**; these include congregation laughter after a spoken joke. In the prayer, 0.12 seconds of energetic frames account for 94.3%. Aggregate RMS therefore describes those brief transients much more than the remaining quiet room sound. Both classes matter and are reported separately.

### Quiet room background versus energetic pauses

For the word-timestamped October excerpts, apply the same original-source pause mask, then separate frames below **-40 dBFS RMS** from more energetic frames. This is a stated source-level classification, not proof that every selected frame is pure noise. It selects 13.99 seconds of quiet sermon gaps and 9.22 seconds of quiet prayer gaps. Comparing decoded encoded outputs after measured delay alignment and speaker matching gives:

| Variant | Sermon quiet background change versus source | Prayer quiet background change versus source |
|---|---:|---:|
| Existing finished video | +1.50 dB | +0.17 dB |
| DeepFilterNet20 chain, target -20 | -5.46 dB | -4.63 dB |
| DeepFilterNet12 chain, target -20 | -4.93 dB | -4.29 dB |
| DeepFilterNet12 chain, target -18 | -4.56 dB | -3.81 dB |

Thus the selected **DF20/-20 candidate lowers October quiet background by 6.96 dB in the sermon and 4.80 dB in the prayer versus the old output**, at matched speaker level. The experimental DF12/-20 candidate gives 6.43/4.46 dB. For Romans 1, DF20 improves the quiet-frame proxy by 12.40 dB versus old output; DF12 gives 11.19 dB. These excerpt benchmarks include the revised playback chain and double AAC encoding, though full-section loudness/gain may differ.

The conclusion is robust to reasonable classification changes: using a -45 dBFS source pause cutoff gives 7.29/7.31 dB lower sermon/prayer background for DF12/-20 versus old output; -35 dBFS gives 4.64/3.19 dB. Changing the cutoff includes different amounts of reflected voice and congregation transients, so the exact number is not a universal score.

DF12/-20 retains somewhat more loud congregation laughter relative to the main voice: the sermon loud-pause change is approximately -2.78 dB versus source, compared with -4.43 dB in the old output. It does not claim to isolate one human voice from all other human voices. Quieter room background is materially reduced; removing crowd responses entirely is a different and less reliable task.

### Additional settings tested

Six stronger spectral candidates tested DF12/20, FFT floors -30/-40, reductions 8/10/12 dB, gain smoothing0/8, 10/11 kHz low-pass, and a soft expander. Stronger FFT settings did not improve October aggregate separation. Restoring the former EQ and downward compressor slightly reduced the loud-pause metric, but worsened quiet-background reduction. A louder constant target (-18/-19 versus -20) also limited louder congregation transients more, while giving slightly less quiet-background reduction. These results support keeping the gentle chain without presence boost or general compression. The fixed default is the tested 20 dB neural cap; the 12 dB alternative remains an experiment because it did not demonstrate a clear speech-preservation advantage after the full chain. Do not chase a lower aggregate laughter score by progressively clipping or suppressing the speaker.

No human listening is claimed. Original and revised material should remain available for matched-level operator comparison; measurement alone does not establish natural sound.

## Speech preservation and speed

Local faster-whisper `small.en`, CPU int8, beam size 5, VAD enabled, and independent segment conditioning screened both the 65-second prayer and 90-second Romans 1 excerpt. All variants retained the overall spoken message. Compared with recognition of the original audio, normalized word disagreement was:

| Variant | Prayer: 131 source-recognized words | Romans 1: 285 source-recognized words |
|---|---:|---:|
| Previous cleaning | 0.76% | Not tested |
| DeepFilterNet12 | 1.53% | Not tested |
| DeepFilterNet20 | 6.11% | 4.56% |
| DeepFilterNet20 plus gentle FFT/expander | 6.11% | 4.56% |
| DeepFilterNet12 chain, constant -20 target, double AAC encoding | 6.11% | 6.67% |
| DeepFilterNet20 chain, constant -20 target, double AAC encoding | 6.11% | 7.37% |
| Current RNNoise | 7.63% | 7.37% |

The complete encoded DF12 chain did not retain the lower disagreement measured for DF12 alone: both encoded targets -18/-20 gave 6.11%, equal to the DF20 chain. The eight prayer edits concern excerpt-edge wording, "May we"/"Maybe", "gonna"/"going to", one inserted "from", and "of our"/"by"; the overall message remains. The encoding-matched Romans 1 comparison similarly gives 6.67% for DF12 and 7.37% for DF20, a small difference without gross message loss. Therefore lower model attenuation is a conservative bound, not a demonstrated perfect-transcription improvement. The selected default retains DF20/-20 because its background reduction is stronger and no clear perceptual speech-loss advantage was established for DF12 after the full chain. This is transcript disagreement, **not word-error rate against human ground truth**. Differences include function words, repetitions, excerpt-edge words, and corrections to errors in the original recognition. It screens gross speech loss but cannot prove natural sound or perfect intelligibility. Passage/boundary analysis continues using original phase-safe audio rather than depending on the enhanced listening output.

On the Ryzen 5 7640U Linux laptop, the native DeepFilterNet executable took approximately 4.7–10.5 seconds for 65–90 seconds of audio, including model initialization: roughly 0.07–0.12 of playback time. Compiled current RNNoise took approximately 1.3–1.4 seconds for 90 seconds. RNNoise was somewhat stronger on one proxy, but required a separate native integration/build; DeepFilterNet supplies an official standalone executable and showed less recognition disagreement in these samples. Neither model won on every recording.

No human listening judgment is claimed. The operator should compare matched-level original/existing/new audio, especially quiet words, syllable endings, breaths, laughter, rustling and the transitions into pauses. Less energy alone can mean removed speech, and a barely audible digital floor should not drive the choice.

## Long-file encoding robustness

The first complete revised Romans 1 render exposed an AAC decode/re-encode stall near 36:15 in the old intro/sermon audio concatenation path. An independent audio-only whole-concat reproduction froze at the same timestamp, ruling out video copying as the cause. Encoding an isolated 20-second excerpt from that region completed normally, so a short successful sample did not establish full-file reliability. Extremely small float samples were observed, but that observation alone does not prove a denormal-number root cause. Whole-concat S32 sample-format conversion completed the same file in approximately 50 seconds; adding a -200 dB DC floor with `adenorm` did not resolve the stall. Short synthetic speech followed by extremely tiny sine waves also encoded normally. These observations support a numerical/state-dependent failure path but do not identify the exact internal codec defect.

The final master now obtains audio directly from the cleaned PCM cache, applies the measured constant gain and limiter, adds exact five-second initial silence, and performs one AAC encode while copying the concatenated video. This removes the unnecessary AAC decode/re-encode failure path, reduces generation loss, and removes the extra audio join delay. Original source, previous finished output and stabilized video are preserved. Complete-file decode, duration, mono and true-peak checks remain mandatory; a short successful encoding is insufficient validation.

## Signal-level regression checks

The final single-encode masters for all three recordings passed complete decoding, duration, mono and true-peak checks. Comparing those actual masters at matched voice level gives 11.89 dB less quiet-frame energy on September 20, and 6.80/4.01 dB less low-level background in the October sermon/prayer. Louder October word-gap sounds are not similarly reduced: including them gives +1.16/-0.25 dB versus the previous output. The September 6 quiet proxy falls 13.39 dB but is near the digital floor. These complete-output results take precedence over the historical double-encode excerpt benchmark. See the [full validation record, masks and reproduction commands](validation/linux-audio-detection-2026-10-07.md).

`tests/test_audio.py` uses temporary synthetic sources, with no church media and no network requirement. Its checks cover:

- Identical gain through separated quiet and speaking intervals, even after a large peak; no upward pause pumping.
- Peak-limiter operation, preserved duration and compensated lookahead.
- Gain cap, attenuation of an already loud recording, and rejection of silent/invalid loudness.
- Soft voiced harmonics and an active syllable at the end of a cut; no delayed-tail truncation.
- Cache reuse and failed processing preserving existing audio without a success marker.
- Rejection of an altered default enhancer binary before execution.
- An optional locally installed model integration check for exact duration, finite output, retained tail context and no network access.

The optional model test skips when the tool is absent. These checks do not establish perceptual quality or validate every hall microphone configuration.

## Reproducing the comparison

1. Retain the original source and choose short excerpts with speech, a genuinely quiet pause, crowd transients and quieter prayer. Run the established stereo phase check before any mono conversion.
2. Decode the selected safe channel to 48 kHz mono WAV with adequate leading/trailing context. Keep a source reference and apply each candidate independently.
3. Determine each variant's algorithmic delay by correlation on a shared voiced interval; align before selecting common speech/pause masks.
4. Use identical masks for each variant. Compare pause energy after matching speech RMS, and report the mask definition. Avoid relying on near-digital-silence quantiles.
5. Render the actual playback chain, including its gain, limiter and AAC encode. Check output duration, decoded/true peaks and all boundaries. Compare this output with the previous completed output at matched speech level.
6. Transcribe short weak-speech samples locally as a gross-loss screen; audition the audio yourself before treating the settings as confirmed.

## Download, integrity and licensing

The tested release is DeepFilterNet **v0.5.6**. Verbose runtime output confirms its embedded model is **DeepFilterNet3**; historical README text describing an older default does not describe this binary. The tested Linux x64 musl download is:

[Official native Linux release asset](https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl)

SHA256: `70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da`.

The setup command downloads it directly from upstream, verifies its pinned checksum, and retains license notices. The default installed executable is checked again before use. A specifically configured custom executable is an operator override whose hash is recorded; it is not claimed to be the verified upstream build. The Linux setup is validated for x86-64 only. This work does not change the released Windows installer; upstream Windows availability is not a substitute for Windows testing.

DeepFilterNet code is dual licensed under MIT or Apache-2.0, with copyright Hendrik Schröter (2021); the corresponding notices must accompany redistribution. The app currently downloads the official artifact rather than republishing it in its installer. Audit transitive native dependency notices before any future bundling. Xiph RNNoise is BSD-3-Clause; the tested source commit was `70f1d256acd4b34a572f999a05c87bf00b67730d`, with its official checksum-verified model download. Current RNNoise model assets are not interchangeable with arbitrary historical `.rnnn` models used by FFmpeg's `arnndn` filter.

## Recording improvements that processing cannot replace

A large hall creates reflected sound while audience voices, laughter and rustling can overlap the speaker. A general speech denoiser has no guaranteed way to distinguish the intended speaker from another human voice. Reverberation contains delayed copies of desired speech; removing it aggressively can remove syllables as well.

A close microphone and dedicated speech feed offer the largest reliable improvement. For a seated speaker, place a headworn capsule close to the corner of the mouth, or use a properly positioned close handheld/podium microphone. Keep unused microphones closed and avoid mixing ambient congregation microphones into the sermon recording feed. Exact placement depends on the equipment and hall; identify the existing routing before changing hardware. Processing can improve available material, but a clear close-mic recording remains the better input.

## Primary sources

- [FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html): FFT suppression, external-model speech denoising, expansion, loudness normalization and limiter behavior.
- [Official DeepFilterNet repository](https://github.com/Rikorose/DeepFilterNet), [v0.5.6 releases](https://github.com/Rikorose/DeepFilterNet/releases/tag/v0.5.6), [MIT license](https://github.com/Rikorose/DeepFilterNet/blob/v0.5.6/LICENSE-MIT), [Apache license](https://github.com/Rikorose/DeepFilterNet/blob/v0.5.6/LICENSE-APACHE).
- [DeepFilterNet3 primary paper](https://arxiv.org/abs/2305.08227): full-band CPU speech enhancement; published benchmarks do not guarantee church-specific results.
- [Official Xiph RNNoise source](https://github.com/xiph/rnnoise): 48 kHz mono processing example, model provenance and BSD license.
- [Shure: critical distance and microphone placement](https://service.shure.com/articles/en_US/Knowledge/critical-distance-and-microphone-placement) and [Shure: house-of-worship audio systems](https://www.shure.com/en-US/docs/education/house-of-worship-audio-systems): direct-to-room sound ratio, microphone distance and unused microphone noise.
