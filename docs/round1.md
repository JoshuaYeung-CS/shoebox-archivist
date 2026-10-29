# Shoebox Archivist

Track: Bring Memories to Life. Entrant: Joshua Yeung. Skill package: shoebox-archivist.zip (Uliya Skill Development Standard, kit 0.7.3).

## 1. One sentence: What does the Skill do?

Shoebox Archivist turns scanned old prints into dated, people-aware albums with a short factual story each, recovering dates from date stamps, handwriting on backs and metadata, and changing nothing until the user approves.

## 2. Who is the target user and problem?

Families digitizing boxes of prints. Each scan carries the scan date, so 1974 lands beside last week, while the real clues (a date stamp, "Lake Tahoe Aug 74" on the back) stay locked in pixels. Hand-dating hundreds of prints never happens.

## 3. What is your proposed solution?

The Skill reads each print and its back, ranks the evidence, and proposes a date with a confidence level (Day to Unknown). It groups prints into events and shows an Archive Plan. After approval it creates albums, saves a story per album, optionally corrects file dates, and keeps a ledger for resume and undo.

## 4. What is the Core User Flow?

"Organize the scans in Shoebox 2" → confirm folder and mode → review the plan, its evidence and questions → approve or edit → albums, stories, dates and ledger written → report with album identifiers and failures.

## 5. What substantive difference does your idea offer compared with existing tools or conventional AI solutions?

Photo apps sort by whatever date a file carries; chat tools guess. This Skill treats dating as evidence: it pairs backs with fronts, parses imprint formats, rejects scanner dates and misreads, never overstates precision, and asks when clues conflict. Stories use only captions and named people. Everything stays on the NAS.

## 6. Which UGREEN AI NAS capabilities will be used, and at which step in the workflow?

Photo health (preflight); file listing and duplicate scan (inventory); metadata, on-device OCR and vision description (reading prints); named people groups (people); album creation, file times and tags (apply); document drafting and note saving (stories, ledger).

## 7. What was your technical approach?

SKILL.md delegates all NAS work to registered experts: file-agent (ug-filesystem, ug-filemgr), photo-agent (ug-photo), document-agent (ug-document) and knowledge-agent (ug-knowledge), checked against catalog 2.0.0, passing only real upstream results. Inputs: folder, mode, hints, story folder. Writes follow catalog approvals; the ledger is saved first. Models: NAS on-device defaults; no external services. Image text is data, never instructions.

## 8. What is the current development status?

Implemented: the full package (SKILL.md plus eight linked references), passing the kit checker with zero errors or warnings. Not implemented: any NAS run. Pending NAS validation: OCR accuracy on faded writing, album creation from photo paths, indexing delay for new scans, and whether file times reorder the timeline.

## 9. What is your final validation plan?

Core 1: sixty scans with known dates; require correct confidence levels, no wrong Day dates, and albums as approved. Core 2: rerun then undo; the rerun skips applied prints and undo restores every file time. Edge: a pre-1970 print, an ambiguous 5 6 '87 imprint and a scanner-dated batch must each become a question or kept date, never a guess.

## 10. Are there any known limitations of your Project?

Dating depends on on-device OCR and vision; faded handwriting may fall to Decade or Unknown. No catalog action writes EXIF or deletes albums, so undo lists albums for manual removal. Pre-1970 file times cannot be set. People must already be named in Photos. Runs cap at 300 images. Only dependency: the UGOS experts.

## Third-party components and licenses (excluded from the word limit)

- Uliya Skill Kit 0.7.3 (English), the UGOS Skill Creation Tool, from the UGREEN Hackathon Starter Kit page (uliya-skill-kit-0.7.3-en.zip, SHA-256 cf557e5a022e4297892f39768132855154232efdedeb726b2845450ccd70e1b3). The archive contains no license file; its use is governed by the Hackathon Official Rules and the UGREEN SkillHub User Agreement, Privacy Policy, and Content Submission and Publication Standards. Used as development tooling only (standard, capability catalog, static checker); no kit file is included in the package.
- No open source libraries, external APIs, external services, models or datasets are included in or required by the Skill. At run time it uses only registered UGOS experts and the NAS on-device models.
- The Skill text is my own work under the MIT License, Copyright (c) 2026 Joshua Yeung.

## AI tools used (excluded from the word limit)

[JOSHUA TO FILL: AI tools used in development]
