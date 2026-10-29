# Why Shoebox Archivist

Three candidate ideas were checked against what the Uliya Skill Kit 0.7.3 actually exposes. The deciding source is the kit's machine-readable catalog, `data/capability-catalog.json` (catalog version 2.0.0, 9 CLIs, 7 domains), together with `docs/skill-development-standard.md`, which says to "use only capabilities present in the catalog" and to state a step as unsupported when no capability matches.

## What the catalog offers for each idea

| Need | Shoebox Archivist | Receipt-to-Ledger | Shoot Culler |
|---|---|---|---|
| Find the files | `ug-filesystem` `find` / `ls` (file-agent) | same | same |
| Read text in images | `ug-photo` `vision-ocr` (photo-agent) | `ug-document` `extract` with `schema=receipt` (document-agent) | not needed |
| Understand the picture | `ug-photo` `vision-vlm` with a prompt | not needed | `vision-vlm` can describe, but nothing scores sharpness or closed eyes |
| Metadata | `ug-photo` `meta` (EXIF) | `ug-document` `metadata` | `ug-photo` `meta` |
| People | `ug-photo` `figure-albums`, `search-picture --figure-uuid` (existing UGOS people index) | not needed | not needed |
| Build the result | `ug-photo` `create-album` (workflow approval) | `ug-filesystem` `mkdir` / `cpmv`, `ug-filemgr` `tag-add-file` | `ug-filemgr` `tag-add-file` for "reject" |
| Write a document | `ug-document` `writing` (`task=draft`, `content`), `ug-knowledge` `save-text` | `ug-knowledge` `save-text` | `ug-knowledge` `save-text` |
| Fix dates | `ug-filesystem` `chtimes` (gateway approval, `mtime >= 0`) | not needed | not needed |
| Watch a folder | not needed | **no trigger or watch capability anywhere in the catalog** | not needed |

## Decision

**Shoebox Archivist (Bring Memories to Life track).** Every step maps to a catalog Action owned by a registered expert, and it uses the parts of the NAS that make it an AI NAS rather than storage: on-device OCR, the vision model, the people index the NAS already maintains, and Photos albums. Its core value, turning clues locked in pixels into dates with evidence, is not something the kit's own examples or scenarios do.

Gaps found and designed around (each is stated in the Skill and the PDF):

- No Action writes EXIF dates. The Skill names albums by the recovered date and, optionally, sets the file modified time with `chtimes`. Whether UGOS Photos orders scans by that time is pending NAS validation.
- `chtimes` takes integers of zero or more, so prints from before 1970 keep their file date; they are still dated and grouped.
- No Action deletes albums, so undo restores file times and tags and lists the albums for the user to remove by hand.
- No Action creates people groups or clusters faces on demand; the Skill reads only groups the user already named. This also keeps it clear of the biometric identification area that the SkillHub Content Submission and Publication Standards single out for stricter review.
- Every Action's `permissions`, `prerequisites` and `errorCodes` are recorded as `knowledgeStatus: unknown` in the catalog, so the Skill handles states generically and lists this as a risk.

## Rejected ideas

**Receipt-to-Ledger (Automate Your Workflow).** Fully supported, but it is almost exactly the catalog's own built-in scenario for contracts and invoices (`find` then `extract` then `tag-add-file` then `mkdir` then `cpmv`), and `kit/references/examples/contract-invoice-audit.md` covers the same ground. `ug-document extract` already ships a `receipt` schema, so the Skill would add little of its own, which scores poorly on Innovation & Differentiation. The "watches a scans folder" part has no capability at all; it would have to run on request.

**Shoot Culler (Unleash Your Creativity).** The central step, picking the sharpest non-blinking frame per burst, has no matching Action. No CLI scores image quality, focus, or eye state; `vision-vlm` returns free-text descriptions, and the closest structured option, `file-workflow start --by image_resolution`, sorts by resolution, not sharpness. The Standard says a step without a capability must be declared unsupported, which would leave the Skill without its core.

## Kit files read

- `SKILL.md`, `docs/skill-development-standard.md`
- `references/`: `skill-format.md`, `expert-orchestration.md`, `cli-usage-rules.md`, `safety-and-approval.md`, `completion-and-errors.md`, `runtime-authoring-lessons.md`, `capability-query.md`, `cli-capabilities.md`, `check-workflow.md`, `init-workflow.md`, `help.md`, and all seven `examples/`
- `assets/skill-template/SKILL.template.md`
- `data/capability-catalog.json`, `schemas/*.schema.json`
- `scripts/check-lib.mjs` and `scripts/check-skill.mjs` (the static checker; its rules are mirrored in `tools/lint_package.py`)

Three places where the kit's own text and its checker disagree, and the checker was followed:

- The template heading `# Expert orchestration` fails the checker, which requires `# Orchestration` or `# Workflow`.
- The template and the kit `SKILL.md` show evidence lines as `- <cli> -> <agent>` under `# Capability evidence`; the checker only accepts `` - `cli` → `agent` `` under `# Generation-time capability evidence`.
- The Starter Kit web page recommends a `README.md` in the Skill folder, but the checker and the Official Rules allow only `SKILL.md` and `references/`, so the README lives in this repo instead.
