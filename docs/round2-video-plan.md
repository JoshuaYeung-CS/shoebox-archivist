# Round 2 video plan (only if selected as a finalist)

Rules: public YouTube, 3 minutes or less, English narration or full English subtitles, recorded on the assigned UGREEN AI NAS during the assigned test day, showing the core workflow, key capabilities and actual results. No third-party music or trademarks other than UGREEN's.

## Test data to prepare before the test day

- About 60 scans of my own prints (fronts and backs), with dates I already know: some with camera date imprints, some with handwritten backs, some with lab stamps, one from before 1970, one ambiguous imprint such as 5 6 '87, and a few with no clues.
- Name two or three people groups in Photos on the NAS before recording.
- A written answer key (file name, true date) to score the run.
- Back up the ledger notes, stories and a screen recording before the day ends; the NAS is reset.

## Shot list (about 2:50)

| Time | Shot | Narration focus |
|---|---|---|
| 0:00 to 0:15 | Photos timeline showing scans stuck at the scan date | The problem |
| 0:15 to 0:35 | Typing "Organize the scans in Shoebox 2" and confirming folder and mode | Trigger and inputs |
| 0:35 to 1:20 | The Archive Plan: albums, evidence lines, confidence levels, questions | Evidence ladder, on-device OCR and vision, named people |
| 1:20 to 1:40 | Answering one question and approving | The user stays in control |
| 1:40 to 2:15 | Approval prompts, then albums appearing in Photos, a story note opened, file dates sorted | Real results, with album identifiers from the report |
| 2:15 to 2:35 | Rerun shows "nothing new"; "undo the last shoebox run" restores file dates | Idempotency and undo |
| 2:35 to 2:50 | Score against the answer key; privacy summary | Results and NAS fit |

## Checks before submitting Round 2

- Re-run `tools/lint_package.py`; the final ZIP must still pass the kit checker.
- Update the Skill with anything learned on the NAS (how `create-album` accepts photos, indexing delay, timeline order after `chtimes`) and record changes in the README.
- Final ZIP and YouTube link due Tue Dec 1, 2:45 am ET (Nov 30, 11:45 pm PT).
