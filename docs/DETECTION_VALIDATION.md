# Reading and sermon detection: Linux validation

Validated on 7 October 2026 against three locally cached service recordings. Analysis used temporary job directories without their saved manual reviews. The existing sources, reviews, completed videos and original transcript caches were preserved. These results assess the Linux source changes; they do not validate a new Windows installer.

## What failed and what changed

The old detector required a reading phrase and a Bible reference within a few transcript segments. YouTube captions sometimes split the book, chapter and verse range across cues, abbreviate “verse” as “vers”, or omit the spoken reading announcement altogether. A missing closing cue also discarded an otherwise usable passage. A broad song pattern could mistake discussion of congregational singing inside a sermon for its ending.

The detector now:

- Joins nearby caption fragments for references and understands spoken compound numbers and numbered books.
- Associates a detached verse range with a nearby chapter reference, but requires an ordered match to the locally stored Bible before accepting a bare reference as a reading candidate.
- Corroborates short explicitly announced readings with at least three distinct ordered verse matches. A chapter reference without a range still needs four distinct matches. Speech recognition and translation differences can leave individual verses unmatched.
- Retains a reader's brief passage announcement when it immediately precedes matched Scripture, with 0.7 seconds of headroom. Longer host introductions remain outside the proposed cut. The rule uses a 30-second proximity bound, not a particular speaker or recording.
- Distinguishes an actual closing invitation from an incidental sentence about singing, and uses a closing prayer or speaker handoff to trim the end.
- Keeps supported passage/start evidence when the ending remains uncertain. Only unresolved information needs operator attention.
- Applies saved operator corrections before clamping chapter boundaries to the final interval. Sections outside the cut are removed; unknown reading/sermon transitions stay unknown rather than receiving an invented timestamp.

Where captions omit important evidence, a separate, bounded local speech check examines up to three short excerpts. It uses the established phase-aware voice channel and faster-whisper `small.en`, beam size 5, word timestamps and a 500 ms VAD silence setting. Each candidate excerpt is at most 150 seconds; the end check uses 120 seconds. Original captions remain cached separately. The refined cache records the checked windows, model, settings, source identity and cache fingerprint.

Titles still require an explicit spoken/on-screen title or an operator-supplied description. Service dates still require recording/title evidence or an operator correction; upload dates are not substituted.

## Real-recording results

Seconds are measured from the original service recording. Start/end below are proposed unreviewed cuts, not changes to the operator's existing saved cuts.

| Service | Transcript evidence | Passage | Start | End | Remaining issue |
|---|---|---|---:|---:|---|
| 6 September 2026 | Original captions alone | Acts 2:42–47 | 2067.939 | 3733.839 | Ending approximate; explicit title unavailable |
| 6 September 2026 | Captions plus targeted local speech checks | Acts 2:42–47 | 2045.190 | 3728.629 | Explicit title unavailable |
| 20 September 2026 | Original captions | Romans 1:8–17 | 2641.379 | 4983.100 | Explicit title unavailable |
| 4 October 2026 | Cached local speech transcript | Romans 2:1–16 | 2300.850 | 4574.120 | Explicit title unavailable |

For 6 September, local speech recovered the reader's announcement and the prayer's final “Amen”, both missing from the useful caption evidence. The proposed end leaves 0.5 seconds after the prayer and precedes the following song invitation. The saved manual interval was 2042–3730 seconds; the candidate falls about 3.2 seconds later at the start and 1.4 seconds earlier at the end. Listen to these margins before confirming a new cut.

For 20 September, the new start intentionally includes the reader's brief announcement, about 24.6 seconds before the saved first-verse cut. Its ending agrees with the saved cut. For 4 October, both cut points are within 0.15 seconds of the saved manual values.

For the refined 6 September evaluation, the local checks covered 1947.600–2097.600, 2359.839–2509.839 and 3643.839–3763.839 seconds. The original caption cache was unchanged. The local evidence and full evaluation JSON remain in the ignored experiment directory rather than the source repository.

## Regression checks and limits

Analysis tests cover fragmented references, spoken compound numbers, detached ranges that need Scripture corroboration, an actual recovered announcement superseding a bare reference, misleading sermon sentences about singing, preservation of known passage/start when an end is missing, reader announcements versus longer introductions, and “keep the passage open” not becoming a second reading. Additional checks verify that saved review fields remain authoritative, section endpoints and chapter offsets agree with an overridden cut, and unknown transitions remain unset. Public-domain local Bible text supplies the synthetic reading fixtures; real service transcripts are not committed as tests.

The detector remains conservative. Its “supported” label means the lexical rules found corroborating evidence; it is not a statistically calibrated confidence percentage. Repeated readings, very short readings, poor speech recognition, translation differences, unusual handoffs and unannounced endings can still need review. These three recordings do not establish accuracy across all services. Check the proposed edges in the source player before confirming uncertain cuts, and retain manual review as the final authority.
