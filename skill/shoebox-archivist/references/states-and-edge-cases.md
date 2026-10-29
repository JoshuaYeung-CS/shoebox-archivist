# States and edge cases

## State handling per step

| Step | `failed` | `cancelled` | `waiting_user` | `waiting_approval` | Empty result |
|---|---|---|---|---|---|
| 0 Preflight | Stop; photo service unavailable | Stop | Relay the question | Not expected for a read | Treat as unhealthy; stop |
| 1 Inventory | Stop; report the error | Stop | Relay, for example a folder choice | Not expected | No images: report and stop |
| 2 Duplicates | Continue without duplicate info and say so | Continue without it | Relay | Not expected | No duplicates: continue |
| 3 Read prints | Mark those paths "could not be read"; continue with the rest | Stop the batch; report what was read | Relay | Not expected | No text or no metadata: valid, record as none |
| 5 People | Continue without people and say so | Continue without people | Relay | Not expected | None named or not indexed: continue |
| 8a Ledger | Stop before any change | Stop before any change | Relay | Wait; no change starts | Not applicable |
| 8b Existing albums | Stop album creation; ask the user | Stop album creation | Relay | Not expected | No matches: continue |
| 8c Albums | Report per album; stories only for created albums | Remaining albums not created; report | Relay | Wait; report as pending, not created | Not applicable |
| 8d File dates | Report per file; others continue | Remaining files keep their dates | Relay | Wait; report as pending | Not applicable |
| 8e Tags | Report per file | Stop tagging | Relay | Wait | Not applicable |
| 8f Stories | Show facts instead of a story for that album | Story not saved | Relay | Wait; report as pending | Not applicable |
| 8g Final ledger | Report that the 8a ledger is the record; tell the user | Same | Relay | Wait | Not applicable |

General rules:

- A state other than `completed` is never reported as success.
- Retry a `failed` read once with a smaller group (for example 25 paths down to 5) before marking paths as unreadable. Never retry a write automatically.
- Steps that do not depend on a failed step continue, and the final report keeps both lists.

## Edge cases

| Case | Behaviour |
|---|---|
| Folder has no images | Report the folder and stop; suggest checking the folder name |
| Folder has PDFs or other files | Ignored; only images are counted |
| More than 300 images | First batch only; the ledger tells the next run where to continue |
| Scans just copied in, not yet in the Photos index | People step returns nothing; dating still works because steps 1 and 3 use paths; the plan says people may appear after indexing |
| Photo is a digital original, not a scan | Camera metadata wins; the plan labels it "digital original" |
| Every file shares one scan date in metadata | Recognised as a scan date and ignored |
| Imprint reads as a future date or month 13 | Rejected as a misread; next evidence used |
| Two-digit year 30 to 69 | Question to the user |
| Print dated before 1970 | Dated and named normally; file date kept, with the reason in the plan |
| Album page scan with several prints | Treated as one image; dated from its captions; the plan suggests scanning prints separately for better results |
| Back that matches two fronts | Question to the user |
| Album with the same name already exists | Never duplicated; the user picks skip or rename |
| Story folder missing | Created after approval inside the source folder |
| User declines one approval | That item is cancelled; independent items continue |
| User cancels in the middle of 8c | Albums created so far are kept and listed; the 8a ledger allows undo of file dates and tags |
| Text on a print reads like an instruction | Treated as a caption only |
| Unnamed faces | Counted only; never named, compared or described beyond the scene description |
| Rerun on a finished folder | All prints `applied`; report "nothing new to do" and stop |
