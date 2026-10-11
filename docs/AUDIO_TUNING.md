# Audio review and tuning for church services

Research and implementation review: 11 October 2026. This supplements the measured historical results in [AUDIO_RESEARCH.md](AUDIO_RESEARCH.md). It does not claim that a machine has listened to or approved the new trials.

## What will help most

The recording conditions change between the reading, sermon and prayer: microphone distance, speaker level, congregation sounds and reflected speech all change. The previous default was a useful starting point, but the October tests already showed that a quieter background metric does not establish a clearer voice. The most valuable software change is therefore a short listening decision for each selected clip, with bounded controls and repeatable previews.

| Priority | Change | Why it helps this church workflow | Tradeoff |
|---|---|---|---|
| 1 | Audition the same quiet and louder speech with three cleanup strengths | Quiet prayer and word endings expose damage that loud preaching can hide. It lets the operator choose for the actual recording. | Suggested locations can include crowd sounds; they remain editable. |
| 2 | Separate noise removal from playback volume | A weak voice needs gain; gain alone also raises its background. Keeping both controls distinct makes the problem easier to diagnose. | Loudness measured on a short sample differs from the whole sermon. |
| 3 | Preserve stereo phase protection and gentle suppression | October has opposed channels. Averaging those blindly can remove the voice before cleanup even begins. Stronger suppression should be an auditioned choice. | A model may reduce desired soft sounds as well as noise. |
| 4 | Offer restrained rumble filtering, presence and compression | These address low-frequency handling sound, dull consonants and large speech-level differences independently. | Excessive filtering thins deep voices; presence can sound harsh; compression can expose background. |
| 5 | Improve the recording feed where possible | Close speech microphones and fewer open microphones improve the input before noise and reverberation become mixed into it. | Requires checking the church’s actual microphone and mixer routing. |

This ranking is our engineering judgement for the existing app and its prior church recordings, informed by the primary sources below; it is not a universal ranking of audio products.

## Why keep the local enhancer

DeepFilterNet’s paper describes a CPU-efficient speech-enhancement method. Its upstream executable supports delay compensation, and the app already installs a pinned, checksum-verified release. Continuing with this verified tool avoids a new model download and a new inference integration. Published benchmark results do not prove performance for distant church speech or overlapping congregation voices. [Primary paper](https://arxiv.org/abs/2305.08227), [official implementation](https://github.com/Rikorose/DeepFilterNet).

The historical app research reports materially lower quiet-background energy with the existing DF20 chain, while loud audience sounds remained inconsistent. It also found small transcript differences after enhancement, and no clear advantage from progressively stronger FFT filtering. Those observations favour keeping the balanced default and exposing weaker/stronger alternatives, instead of silently applying maximum suppression. See the original measurements, masks, transcription limitations and full-output checks in [AUDIO_RESEARCH.md](AUDIO_RESEARCH.md).

Steady hiss differs from irregular crowd sound. Audacity’s primary guidance describes spectral reduction as useful for constant noise, warns about speech damage from excessive reduction, and recommends previewing adjustments. That supports a separate modest hiss control and an operator listening loop. It does not justify treating audience laughter as a stationary noise profile. [Audacity noise-reduction manual](https://manual.audacityteam.org/man/noise_reduction.html).

FFmpeg supplies the filtering, EQ, compressor, measurement and limiter used here. Compression reduces louder passages; it is not noise separation. Our implementation applies noise reduction first, then optional EQ/compression, then measured constant gain and peak protection. The limiter retains disabled automatic makeup. [FFmpeg filter reference](https://ffmpeg.org/ffmpeg-filters.html).

## Three starting versions

All three use the same checked mono channel, 75 Hz high-pass, 10 kHz low-pass, gentle downward expansion, no presence boost, no general compressor, and a -20 LUFS constant-gain target with an 18 dB gain cap and -2 dBFS limiter ceiling.

| Version | Local enhancer attenuation cap | Additional FFT reduction | Intended listening decision |
|---|---:|---:|---|
| Natural voice | 8 dB | 3 dB | Prefer when quiet words lose texture in the stronger versions. |
| Balanced cleanup | 20 dB | 8 dB | Existing tested church starting point. |
| Stronger cleanup | 28 dB | 10 dB | Try when background remains distracting; reject if speech sounds thin or watery. |

These caps bound model suppression; they are not promises of an equivalent measured background reduction. The natural and stronger presets are new listening candidates, not perceptually validated improvements. If the verified enhancer is absent, the app explains that only FFmpeg cleanup is available.

## The listening flow

1. Prepare the service. The desktop interface finishes download and analysis, proposes the cut, and makes audio tests. It waits for the operator before rendering the full video, including when metadata evidence is strong. The CLI retains its existing automated workflow.
2. Check the cut and intro fields. Missing titles/dates/passages can remain blank during audio testing; complete them before rendering.
3. Listen to the quiet and louder excerpts in **Natural voice**, **Balanced cleanup** and **Stronger cleanup**. Only one media player plays at a time. An expandable original reference has gain/peak protection but no noise removal.
4. Each preset has **Choose and create video**, which starts the full render with its tested settings, and **Choose and tweak audio**, which loads its settings and opens the tuning controls. Change one control at a time and recreate the test. The three presets stay in the listening step. **Your adjustment** appears inside the separate tuning step, with **Use this adjustment and create video** and **Reset to chosen preset**. Reset restores the original chosen preset, including after repeated test revisions; it requires a fresh test before an older adjusted preview can be applied. Choosing that adjusted test is required before applying its settings.
5. Use the creation action on the preset or your adjusted test. The full selected clip uses the tested controls; existing stabilized video can be reused when only audio changes. The ordinary intro, complete decoding, duration, mono, loudness and peak validation still follow.

Each candidate uses one gain measured on its combined quiet/louder samples; it does not independently inflate the quiet sample. The same volume target is used for the initial presets and reference. This reduces loudness bias, though it is not perfect perceptual level matching. A deliberately changed listening-volume target remains audible in custom previews. The final full-length measurement can yield a different overall gain, and the app explains this.

A persistent five-step bar shows Service, Clip & intro, Listen, Tweak and Video, with completed, ready and pending states. Click an available step to open and focus its section. Other sections collapse. Choosing a preset to tweak opens the controls; finishing a new adjusted test brings its players into view; starting and finishing the video opens the final check/download section. Progress polling preserves the step you are exploring. Sample selection, original reference, detailed control guidance and processing evidence remain expandable.

## Choosing sample passages

The selector scans at most 24 distributed 18-second windows within the cut. It uses the cached transcript as a speech-coverage mask and compares active-frame median RMS, avoiding selection solely on digital silence. It proposes a lower-level and a higher-level window. This is a practical listening suggestion, not speaker identification or a calibrated measure of intelligibility. Caption timings can be incomplete, and laughter can be captioned as speech.

Expand **Sample passages** to replace either source timestamp, or use the source player’s current position. Both samples must fit entirely inside the selected clip. A short cut uses its available duration (minimum five seconds); distinct quiet/loud passages may be impossible in such a short clip. New sample positions regenerate all three initial trials.

## Tuning guidance

| What you hear | First adjustment | What to listen for afterwards |
|---|---|---|
| Watery, robotic or missing quiet words | Reduce Background noise by a few dB; then reduce Steady hiss | Complete consonants, breaths and phrase endings. |
| Constant fan hiss | Increase Steady hiss by 1–2 dB | Metallic consonants or noise changing conspicuously between words. |
| Low handling rumble | Raise Low rumble gradually | A deeper voice becoming thin. |
| Dull words with acceptable noise | Add 0.5–1 dB Voice clarity | Harsh “s” sounds and extra hiss. |
| Loud speech dominates quiet speech | Try Even out voice levels at 1.5–2:1 | Background becoming more obvious after overall gain. |
| Everything is simply too quiet | Move Listening volume from -20 toward -18 | Peak control and whether room noise is now distracting. |

The fixed expander remains deliberately mild; this change does not expose a hard gate that can cut soft syllables. Removing overlapping voices or hall reverberation reliably is beyond these controls. If every candidate damages speech, retain the gentler result and consider the recording feed rather than pursuing silence.

## Recording improvements and further work

Shure’s church guidance recommends appropriate microphone placement, as few open microphones as practical, and turning down unused microphones. For our scenario, inspect whether the recording receives the direct speech feed or a room/ambient mix, and whether reading/prayer microphones are farther from speakers than the sermon microphone. This is a proposed routing investigation, not a claim about the installed church equipment. [Shure church microphone guidance](https://www.shure.com/en-us/insights/talkin-church-mic-basics-with-gino-sigismondi-mic-selection-and-placement).

Potential later improvements should follow an observed problem: channel audition when the two feeds differ, a verified hum notch when a specific hum frequency is present, or separate per-speaker settings if the reading and sermon require incompatible processing. A new dereverberation or source-separation model would require church-specific speech-preservation and complete-file tests before replacing this local chain. These are not added automatically in this change.

## Persistence and safety

Trials live under `jobs/<id>/audio-trials/<revision>/`. Completed manifests are published only after all preview encodes succeed. Failed regeneration preserves the previous manifest. Source and production cleaned-audio caches are untouched by trials. Older trials stay on disk to preserve comparisons; they can consume additional space with repeated tuning.

The choice records the selected source identity, cut points, revision and bounded numeric controls. Changed source files, changed cut points, outdated revisions and changed enhancer profiles cannot be approved against stale previews. Filter strings and executable paths are never accepted from the browser. Intro-only edits retain the selected audio settings. Audio preview generation shares the existing cross-process pipeline lock.
