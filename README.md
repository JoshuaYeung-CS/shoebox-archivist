# Shoebox Archivist

A UGOS Skill for UGREEN AI NAS that turns a folder of scanned old prints into dated, people-aware photo albums with a short factual story for each album. Entry for the UGREEN Hackathon 2026 on AI NAS, Round 1, track **Bring Memories to Life**.

Scanned prints carry the day they were scanned. Shoebox Archivist reads the clues that place them in time (camera date imprints, handwriting and lab stamps on the backs, metadata, visual era cues) through the NAS photo experts, proposes a date for every print with its evidence and a confidence level, groups prints into events and shows an Archive Plan. Only after the user approves does it create albums, save story notes, optionally correct file dates and tag undated prints, keeping a ledger so the run can be resumed or undone.

## What is in this repo

| Path | What it is |
|---|---|
| [skill/shoebox-archivist/SKILL.md](skill/shoebox-archivist/SKILL.md) | The Skill entry point (the only required file) |
| [skill/shoebox-archivist/references/](skill/shoebox-archivist/references/) | Eight linked Markdown references: date evidence, archive plan, story rules, ledger and undo, states and edge cases, privacy and permissions, examples, disclosure |
| [tools/lint_package.py](tools/lint_package.py) | Package lint and ZIP builder (outside the ZIP) |
| [tools/build_pdf.py](tools/build_pdf.py) | Builds the Round 1 proposal PDF from [docs/round1.md](docs/round1.md) |
| [tests/](tests/) | pytest suite for the lint and the PDF |
| [docs/why-this-idea.md](docs/why-this-idea.md) | Why this idea, against the kit's real capabilities |
| [docs/round2-video-plan.md](docs/round2-video-plan.md) | Plan for the Round 2 demo video |

`dist/` (the built ZIP and PDF), `vendor-kit/` (the downloaded kit) and `.venv/` are not committed.

## Quick start

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Optional but recommended: the kit, so the lint also runs UGREEN's own checker (needs Node.js)
mkdir -p vendor-kit && curl -L -o vendor-kit/uliya-skill-kit-0.7.3-en.zip \
  "https://cdn.shopify.com/s/files/1/0630/9416/1602/files/uliya-skill-kit-0.7.3-en.zip?v=1790578898"
shasum -a 256 vendor-kit/uliya-skill-kit-0.7.3-en.zip   # cf557e5a022e4297892f39768132855154232efdedeb726b2845450ccd70e1b3
unzip -q vendor-kit/uliya-skill-kit-0.7.3-en.zip -d vendor-kit/extracted

.venv/bin/python tools/lint_package.py    # lints, builds dist/shoebox-archivist.zip, runs the kit checker
.venv/bin/python tools/build_pdf.py       # builds dist/round1.pdf, checks the word and size limits
.venv/bin/python -m pytest -q
```

## How it meets the Round 1 requirements

| Requirement (Official Rules) | Where it is met |
|---|---|
| Built with the UGREEN Skill Developer Package, follows the Uliya Skill Development Standard | Every CLI and expert mapping comes from the kit catalog 2.0.0; the package passes the kit's own checker with status `static-pass` and zero warnings |
| Uses supported UGOS CLI capabilities through registered expert agents | `ug-filesystem`, `ug-filemgr` → `file-agent`; `ug-photo` → `photo-agent`; `ug-document` → `document-agent`; `ug-knowledge` → `knowledge-agent`; the Skill only delegates |
| No scripts, runtimes, manifests, executables | The ZIP holds 9 Markdown files only; the lint rejects anything else |
| SKILL.md with name (2 to 64, lowercase hyphenated) and description (1,024 characters or less) | `shoebox-archivist`; description is about 590 characters |
| SKILL.md covers goal, inputs, CLI capabilities, orchestration, completion and failure | Sections Goal, Required input, Generation-time capability evidence, Orchestration, Completion and failure |
| References under `references/`, each linked from SKILL.md | All eight linked; the lint fails on an unlinked one |
| ZIP and package 10 MB or less, 1 MB per file, 100 files or less | About 20 KB, 9 files |
| Disclosure of third-party components, licenses, principal functionality and tools used | [references/disclosure.md](skill/shoebox-archivist/references/disclosure.md) |
| PDF of 500 words or less answering the ten questions, 1 MB or less | `dist/round1.pdf`, word count checked by the build and the tests |

## Validation

`tools/lint_package.py` checks the Official Rules limits and re-implements the rules of the kit's static checker (`scripts/check-lib.mjs`), then builds a deterministic ZIP with one top-level `shoebox-archivist/` folder and runs the kit checker on both the source folder and a fresh extraction of the ZIP when Node.js and the kit are present. It also reports any open `[JOSHUA TO FILL]` blank as a warning.

Places where the kit's template and its checker disagree are listed in [docs/why-this-idea.md](docs/why-this-idea.md); the Skill follows the checker.

## Tech stack

Markdown for the Skill. Python 3.11, pytest, reportlab and pypdf for the repo tooling only. Node.js only to run the kit's checker.

## License

MIT, Copyright (c) 2026 Joshua Yeung, for the files in this repo. The Uliya Skill Kit is UGREEN's and is not included.
