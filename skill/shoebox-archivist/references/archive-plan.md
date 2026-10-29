# Archive plan

The Archive Plan is the only checkpoint before anything is written. It must let the user check every proposed date in seconds and change anything in plain words.

## Format

Show the plan as one message in this order.

**1. Summary line.** Folder, images found, images in this batch, and how many prints landed at each confidence level. Example: "Scans from the blue shoebox: 142 images, 71 prints (71 backs paired). Day 18, Month 9, Year 27, Decade 12, Undated 5."

**2. Proposed albums.** One block per album:

| Field | Content |
|---|---|
| Album | Proposed name, for example 1974-08 Lake Tahoe |
| Date | The proposed date and its level |
| Evidence | Each item on its own line, strongest first, with the source: imprint text, back caption verbatim, lab stamp, metadata, hint, era estimate |
| People | Named people found, or "none named" |
| Prints | File names, with "back paired" where a back was matched |
| File dates | New modified time per print, or "kept (before 1970)" or "kept (Decade only)", shown only if file dates are on |

**3. Questions.** Numbered, one line each, with the two candidate answers where there are two. Examples: day or month order of an imprint, a back that could belong to two fronts, a caption that disagrees with an imprint by a year.

**4. Not dated.** Prints with Unknown confidence, prints that could not be read, unpaired backs, and duplicate copies, each with the reason.

**5. What will change if approved.** A plain list with counts: albums to create, prints to add, stories to draft, file dates to change (only if on), files to tag "Shoebox date unknown", and the ledger note to save. Say that nothing is deleted, moved or renamed.

**6. How to answer.** One short line listing the replies below.

## Replies the user can give

| Reply | Effect |
|---|---|
| approve all | Apply every album and change in the plan |
| approve albums 1, 3 and 4 | Apply only those; others stay in the ledger as planned |
| rename album 2 to Grandpa retirement party | Change the proposed name |
| set the date of scan-0417 to June 1979 | Replace the date with the user date; the evidence list records "set by user" |
| move scan-0420 to album 3 | Change the grouping |
| answer 1: day first | Resolve a numbered question |
| file dates on, or file dates off | Change the option |
| cancel | Stop; nothing is written |

Any edit produces a revised plan that is shown again in full or as a clear diff. Writes start only after a yes to the latest plan.

## Rules

- Never hide a low-confidence date inside an album with high-confidence ones without its own level label.
- Never present an era estimate as a fact.
- Long plans: show the albums first and put prints over 20 per album behind a count with an offer to list them.
- In plan mode, offer to save the plan as a note. That save is a write and needs approval.
