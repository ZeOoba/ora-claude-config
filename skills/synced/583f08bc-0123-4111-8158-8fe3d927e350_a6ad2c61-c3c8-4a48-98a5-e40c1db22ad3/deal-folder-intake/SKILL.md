---
name: "deal-folder-intake"
description: "Archive an uploaded or received acquisition document package into a permanent, hash-verified Oxford Realty Advisors deal folder — structure, byte-verification, source manifest, OneDrive mirror, and memory pointer. Use when the user says: store this deal, archive this package, save these files for [property], file this broker package, set up a deal folder, keep this for the record, or uploads a multi-file acquisition package (OM, leases, tax bills, site plan, Argus/CoStar exports, models, IC memos) without asking for an underwrite. Does NOT underwrite, screen, or price — that is acquisition-underwriting; does NOT pre-screen a single target — that is verified-deal-recon. Run it AFTER an underwrite to make the package permanent, or standalone to park a package that has not been underwritten yet. v1.0 "
---

# DEAL FOLDER INTAKE — ORA acquisition package archiving

Turns a pile of uploaded deal documents into a permanent, verifiable deal folder: **structure → hash-verify → manifest → mirror → memory pointer.** Session upload folders are ephemeral; anything not archived is lost when the session ends.

## SCOPE

**This skill files. It does not analyze.**

| Request | Route |
|---|---|
| "store / archive / save this package" | **This skill** |
| "underwrite / screen / evaluate this" | `acquisition-underwriting` |
| "is this worth pursuing" (one target) | `verified-deal-recon` |
| "abstract these leases" | `lease-abstraction-pipeline` |
| "reconcile the PSA" | `psa-reconciliation` |

If the user wants both filing and analysis, **file first** (the source files are perishable), then hand off. Never let an underwrite request end without the package archived.

**Hard Invariant 3 check before anything else:** if the deal is on the active confidential roster, it is archived normally but never named on an external surface — no artifact publish, no external send. If confidential-deal state is unavailable on the current surface, verify before naming the deal outside ORA systems; if unverifiable, ask.

---

## STAGE 1 — INVENTORY AND IDENTIFY

1. List every uploaded file with size and modified date. Do not skip files you cannot parse — a proprietary binary still gets archived.
2. Establish the deal identity from the package: full street address(es), city, county, state, ZIP. The county matters — it drives the tax-record bucket.
3. **Check for an existing folder for this deal before creating anything.** Search the outputs folder and the mirror target for the address, an abbreviation, and the property name. If one exists, add to it and version the manifest (`_v02`); never create a second folder for the same asset.
4. Derive the folder name: `Property_Name_City_ST` in underscores, e.g. `Old_Alexandria_Ferry_Clinton_MD`, `3700_Kinsman_Madison_WI`. Stable for the life of the deal — closed and passed deals keep the name they were filed under.

---

## STAGE 2 — STRUCTURE

```
<Property_Name_City_ST>/
├── YYYY-MM-DD_<Property>_SourceManifest_v01.md
├── 00_Dossier/            canonical narrative, if one exists
├── 01_Broker_Package/     OM, flyer, rent roll, Argus/broker exports
├── 02_Leases_Executed/    signed leases, amendments, guaranties, estoppels
├── 03_Tax_Records/        assessment notices, tax bills, appeal filings
├── 04_Site_and_Market/    site plan, survey, title, environmental, CoStar
├── 05_ORA_Underwrite/     ORA model, IC memo, LOI, deal-terms register
└── archive/               superseded versions — never delete
```

Create every bucket even when empty; a missing bucket reads as "not received" and an empty one reads as "nothing yet." Add buckets only when a package genuinely needs one (`06_Debt/` for a loan assumption, `07_Closing/` post-PSA).

**Naming — do not unify the schemas (CLAUDE.md doctrine):**

- **Counterparty-supplied files keep their original filenames verbatim**, typos included (`Costar Reporrt ...pdf` stays misspelled). Renaming breaks every citation in the dossier, IC memo and model, and destroys the provenance link to what the broker actually sent. This overrides the deal-file naming schema, which governs documents ORA *authors*.
- **ORA-authored models** keep `ORA_[DocType]_[Property]_v[X.Y].xlsx`.
- **Session work-product** (manifest, dossier) uses `YYYY-MM-DD_[Topic]_[DocType]_v##.ext`.
- **Never delete. Move to `/archive/`.**

---

## STAGE 3 — COPY AND VERIFY (non-negotiable)

Copy, then prove the copy. An unverified archive is not an archive.

1. SHA-256 every source file and every archived file.
2. Compare **hash sets and file counts** in both directions. Report `HASH MATCH` only when both agree.
3. Any mismatch or count gap stops the run and is reported — never papered over.

**Windows MAX_PATH trap — this will bite.** Cowork session paths run ~215 characters before the deal folder even starts, so `Copy-Item` fails with `DirectoryNotFoundException` on files that plainly exist. Symptoms: the copy dies on one deep file while shallower ones succeed.

- Use `robocopy <src> <dst> /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NP` — long-path safe. Exit codes **0–7 are success** (1 = files copied); only ≥8 is failure.
- `Get-ChildItem "\\?\<path>"` silently returns **zero items** in Windows PowerShell 5.1 — it does not error, it just yields nothing, which makes a broken verification look like an empty folder. Never verify the long side that way. Hash the long path from the POSIX shell (where the session folder is mounted at a short path) and the short side in PowerShell, then compare.
- Build any multi-step PowerShell as a `.ps1` file and run it with `-File`. Inline `-Command` mangles `$_` and nested quotes.

---

## STAGE 4 — MANIFEST

One markdown file at the folder root. This is what a future session reads first.

Required sections:

1. **Header** — address, county, date, deal status in one line (verdict, ask, walk price if underwritten; `NOT YET UNDERWRITTEN` if not), and the underwrite of record.
2. **Folder structure** — the tree, so nobody guesses.
3. **File register** — a row per file: filename, bucket, *what it is and why it matters*, read/not-read status, bytes, SHA-256 prefix. "What it is" earns its place: `RET Bill_7458.pdf — PG County Tax Inquiry, acct 0959445, FY27 — the load-bearing verification` tells a future session where the deal turns. Flag any file whose content contradicts the rent roll or the OM.
4. **Sources cited but NOT held as files** — broker e-mails, GIS pulls, assessor sites, market reports, anything consulted live. This section is the one people skip and the one that costs a re-underwrite. Name each source specifically enough to re-pull.
5. **Open items** — every unresolved DD-Critical, data conflict, and unverified assertion, numbered. Include the re-engage trigger.
6. **Verification line** — "All N archived copies verified byte-identical to the files as received (SHA-256, DD Mon YYYY)."

---

## STAGE 5 — MIRROR

The Cowork outputs folder persists on the user's machine but is not the firm's document store.

- **Mirror target:** `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\Deals\<Property_Name_City_ST>`. `Claude_Workspace` is free working surface under Hard Invariant 5 — no permission needed.
- **Re-verify hashes at the destination.** A mirror is not done until it is proven.
- **Non-Claude Oxford OneDrive business folders** (`Investment Candidates -- 2026`, property folders, accounting) are **read-only without explicit permission**. If the deal's natural home is one of those, mirror to `Claude_Workspace` and *ask* before writing to the business folder. Do not assume the ask.
- Note in the manifest where the mirror lives and when it was last verified.

---

## STAGE 6 — MEMORY POINTER

The folder is worthless if the next session cannot find it.

- **Update the existing deal memory** if one exists — do not create a second. Add a "Where everything lives" paragraph: folder path, bucket-by-bucket contents, verification date, and the sources *not* held.
- If no deal memory exists, write one (`type: project`) carrying the verdict or `NOT YET UNDERWRITTEN`, the economics that decide it, and the archive pointer. Link related memories with `[[slug]]`.
- Add or update the one-line `MEMORY.md` index entry.
- Convert relative dates to absolute.

---

## STAGE 7 — QC GATE

Do not report completion until all twelve pass:

1. Every uploaded file is archived — including unparseable binaries.
2. File counts match, source vs archive vs mirror.
3. Every SHA-256 matches; the match is stated explicitly.
4. Counterparty filenames are byte-identical to what was received.
5. ORA artifacts follow the model / session-output schemas.
6. Every bucket exists; `archive/` exists.
7. No pre-existing folder for this deal was duplicated.
8. Manifest carries all six required sections.
9. Every dossier/IC-memo/model file citation resolves to a file on disk.
10. Sources-not-held section is populated (or explicitly "none").
11. Mirror verified at the destination, or its absence explained.
12. Deal memory and `MEMORY.md` index both updated.

Then present the manifest and the dossier (if any) via the file-sharing tool, and state in two sentences: what was archived, and what remains open.

---

## FAILURE MODES SEEN IN PRACTICE

- **Renaming broker files to fit a schema** — silently orphans every citation in the underwrite. Preserve originals.
- **Trusting `Copy-Item` on long paths** — partial copy, no obvious error until you count files.
- **Verifying with `Get-ChildItem "\\?\..."`** — returns zero, reads as success, proves nothing.
- **Archiving the files but not the live sources** — the GIS pull, the broker e-mail, the market report. Six weeks later nobody can reconstruct where a figure came from.
- **A second folder for the same asset** — two partial archives, neither authoritative. Always search first.
- **Treating an OCR copy as a replacement** — keep both the image-only original and the OCR copy; the original is the executed instrument.

