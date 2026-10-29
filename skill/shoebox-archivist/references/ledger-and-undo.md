# Ledger and undo

The ledger makes the Skill safe to run twice and possible to reverse. It is a Markdown note saved next to the scans through the knowledge expert. Each save creates a new note whose name starts with `shoebox-ledger` and ends with the run date and time, so an earlier ledger is never overwritten.

## When it is written

1. **8a, before any change.** Status `planned` for every approved print, with the old modified time from step 1.
2. **8g, after the changes.** Status `applied`, `skipped` or `failed` for every print, with the real results returned by the experts.

If the 8a save does not return `completed`, the run stops before any change. If a run stops between 8a and 8g, the 8a ledger still holds every old value, so undo works.

## Format

A short header followed by one table.

Header lines:

- Run: date and time the run started
- Folder: the source folder exactly as confirmed
- Mode: apply
- Batch: first and last file in this batch, and how many remain
- File dates: on or off
- Story folder: as confirmed

Table columns:

| Column | Content |
|---|---|
| File | Path as returned by the inventory |
| Status | planned, applied, skipped or failed |
| Date | Approved date and level |
| Evidence | Short evidence summary |
| Album | Album name, and the album identifier once created |
| Old modified time | From step 1 |
| New modified time | Timestamp set, or kept |
| Tag | Shoebox date unknown, if added |
| Story | Story file path, for the first print of each album |
| Note | Error text or reason for skipping |

## Resume rules (step 1)

- Read only the newest ledger in the folder.
- `applied` prints are left out of the new batch and counted as done.
- `planned` and `failed` prints are dated again from scratch; the old ledger values are not trusted for anything except the old modified time.
- An album identifier in the ledger is checked again in step 8b before reuse; if the album no longer exists, the user is told and asked whether to create it again.
- If a file in the ledger is no longer in the folder, it is reported as missing and left alone.

## Undo

Undo reverses the newest run that has an 8g ledger, or an 8a ledger if the run stopped early.

1. Read the ledger with the step 1 delegation.
2. Show the user what will be restored: files whose modified time will go back, files whose tag will be removed, and albums that must be removed by hand.
3. After a yes, restore the old modified times with the file expert (same delegation as 8d, using the old values as the approved list).
4. Remove the Shoebox date unknown tag from the files the ledger shows it was added to (file expert, `tag-delete-file`).
5. List the albums the run created, by name and identifier, and tell the user to remove them in Photos if wanted. No catalog Action deletes albums, so the Skill does not.
6. Story notes stay; tell the user where they are.
7. Save a new ledger that records the undo result.

Undo never deletes photos or story notes and never touches files that are not in the ledger.
