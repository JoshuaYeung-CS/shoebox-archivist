# Privacy and permissions

Family photos are some of the most personal files on a NAS. This Skill is designed so that they stay there and the user stays in control of every change.

## What is read

- Image files inside the one folder the user confirms, up to three folder levels deep. Nothing outside it.
- Their metadata, recognised text and a two-sentence description, produced by the NAS photo expert.
- The names of people groups the user already named in Photos, and which of these images are in them.
- Earlier shoebox-ledger notes in the same folder.

## Where data goes

- All processing is done by the registered NAS experts. The parent Skill passes only real results between them.
- The Skill asks the photo expert to use the NAS default on-device model and never names an external model or service. It makes no network calls and sends nothing off the NAS.
- Story drafts are produced by the NAS document expert from the facts supplied, with no output file; only approved text is saved, by the knowledge expert.
- If the NAS owner has configured the platform to use a third-party model, that is a platform setting outside this Skill; the Skill does not change it.

## People

- Only people groups that the user has already created and named in Photos are used, and only to say who appears in a print and to name them in a story.
- The Skill never names, guesses, compares or searches for unknown faces, never creates people groups, and reports unnamed groups only as a count.
- The Skill is not meant for identifying anyone; it is a personal archiving tool for the owner of the photos.

## What changes, and the approval each change needs

Approval values are those recorded in the kit capability catalog. Every change happens only after the user says yes to the Archive Plan, and then the platform asks again where the catalog requires it.

| Change | Expert | Catalog approval | When |
|---|---|---|---|
| Save the run ledger note | knowledge-agent | workflow | 8a and 8g |
| Create albums | photo-agent | workflow | 8c |
| Set file modified times | file-agent | gateway | 8d, only if the user turned it on |
| Create the Shoebox date unknown tag | file-agent | gateway | 8e, only if it does not exist |
| Add or remove that tag on files | file-agent | conditional | 8e and undo |
| Draft story text (no file written) | document-agent | gateway | 8f |
| Create the story folder | file-agent | gateway | 8f, only if missing |
| Save story notes | knowledge-agent | workflow | 8f |

Never done: deleting, moving or renaming photos, editing pixels or EXIF, sharing albums, creating shared folders, or any change outside the confirmed folder and the albums listed in the plan.

## Data left behind

- Albums the user approved.
- Story notes in the story folder.
- Ledger notes in the source folder. They contain file paths, dates, captions and album names, and nothing else. The user may delete them; the Skill then cannot resume or undo that run.

## Credentials

The Skill contains no credentials, keys or account details and never asks for any.
