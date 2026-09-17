---
name: ora-om-intake-ocr
description: Weekly OM intake pass (Wednesdays 06:15 AM ET) — detects new PDFs in the Investment Candidates folder, OCRs image-only scans (Tesseract-backed, winget-installed 2026-08-12; Ghostscript path blocked by non-admin session, see body Step 2), gate-screens new candidates (Buy Box Stage 0), sweeps stale seen-backlog OMs that were never gate-screened (Step 3.6), extracts structured fields via the Brain server, and reports. Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

PATH FIX (2026-07-29): the Folder: path below was missing a `\Business\` segment and pointed
to a location that does not exist on disk — confirmed via filesystem search during the
2026-07-29 run (167 PDFs found under the corrected path; 0 under the old one). That run's
manifest (`_intake\manifest.json`) had also drifted, with a stale `root` field pointing at a
dead `(1)` OneDrive conflict-copy path; that field was corrected the same run. Both fixes are
corrective only — no other logic changed.

# ORA OM Intake & OCR Pass (weekly)

Folder: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Investment Candidates -- 2026`

## Step 0 — Heartbeat (always first)
Append `{ts, event: "run-start"}` to the `runLog` array of `_intake\manifest.json`
(under the folder above; create the file if missing). On completion, append
`{ts, event: "run-complete", note: "{n} new, {m} OCR'd, {k} gate-passed"}`.
Purpose: distinguish fired-and-failed from fired-with-zero-intake.

## Step 1 — Detect new/changed PDFs
List all PDFs (recursive, skip `Random. Superceded` and any `*_OCR.pdf`).
Compare against the CANONICAL manifest at `_intake\manifest.json` inside the folder above
(path + size + mtime; the `Documents\Claude\Scheduled\` location is retired — unreachable
in unsupervised sessions).
If the manifest is ever missing: treat as empty but do NOT OCR the whole backlog —
process only files modified in the last 14 days; log the rest to the manifest as seen.

## Step 2 — Text-layer check + OCR
For each intake PDF, test for extractable text (pdftotext first 3 pages; <100 chars = image-only).
Image-only → `ocrmypdf --skip-text` to a sibling file named `<original>_OCR.pdf`.
Never modify the original. If ocrmypdf unavailable, install via pip (--break-system-packages).
Record OCR success/failure per file.
Prereqs (fixed 2026-08-12): Tesseract-OCR installed via `winget install --id UB-Mannheim.TesseractOCR`
(user-scope, no admin needed) — add `C:\Program Files\Tesseract-OCR` to PATH if a fresh session
doesn't see it (`$env:Path = 'C:\Program Files\Tesseract-OCR;' + $env:Path`). Ghostscript could
NOT be installed the same way — its Inno Setup installer requires admin elevation and the
scheduled-task session has no interactive UAC session to approve it (winget has no Ghostscript
package as of 2026-08-12; the official installer at
github.com/ArtifexSoftware/ghostpdl-downloads hangs/silently fails without a click-through).
This is a soft deviation, not a blocker: `ocrmypdf --skip-text` still completes successfully and
produces a searchable `_OCR.pdf` without Ghostscript — the optimizer just leaves a subset of
images unoptimized ("[WinError 2]... image could not be processed by the optimizer, left
unchanged, output file is still valid") for ~9% less compression. If Tesseract itself is ever
missing again, reinstall with the winget command above — do not re-attempt Ghostscript
unsupervised; flag it for Gabriel to install interactively if full optimization is ever needed.

## Step 3 — Gate-screen new OMs (Buy Box v1.0)
For each NEW property OM (not models/memos/leases), read the OCR'd copy and apply
Stage 0 gates only (product / size-price / market / physical / flood-flag / other kills)
per the acquisition-underwriting skill and the acquisition-buy-box-v1 memory.
Do NOT full-score — produce gates verdict + 3-line fact summary per property.
Data gaps: list as questions for Gabriel (per feedback-data-gap-routing memory);
NEVER draft broker outreach from this task.

## Step 3.5 — Structured field extraction (best-effort)
For each gate-passing property OM, try to extract structured fields via the Brain server
(http://localhost:8911/api/actions/om-extract). Use PowerShell:

```powershell
try {
  $pdf = Get-Item "<path-to-pdf>"
  $form = @{ file = $pdf }
  $r = Invoke-RestMethod -Uri "http://localhost:8911/api/actions/om-extract" `
       -Method Post -Form $form -Headers @{ 'X-ORA-Client' = '1' } -TimeoutSec 60
  if ($r.ok -and $r.fieldCount -gt 0) { $extractedFields = $r.fields }
} catch { $extractedFields = $null }
```

If extraction succeeds (ok=true, fieldCount > 0): store fields for Step 4.
If Brain server is unavailable (connection refused / timeout / any error): skip silently —
log "Brain offline — no field extraction" in the candidate note. Never block gate-logging on
extraction failure.

## Step 3.6 — Stale seen-backlog sweep (periodic, runs every execution)
Added 2026-08-12 after "OM  Dollar General  Cincinnati OH.pdf" was found sitting with
status="seen-backlog-2026-06-10" and no "gate" field for ~2 months — it was seeded into the
manifest in bulk on 2026-06-11 without ever being individually gate-screened, and because its
size/mtime never changed, Step 1's diff never re-surfaced it. A file only re-enters screening
today if it changes; this step catches the ones that never do.
On every run, scan the FULL manifest.files array (not just this run's new/changed set) for
entries where: (a) the filename looks like a property OM by ORA's naming convention (starts
with "OM " case-insensitive — supporting docs such as Costar reports, rent rolls, LOIs, models,
memos, and ORA-generated owner-outreach output are exempt, same as Step 3), AND (b) status
starts with "seen" (seen-backlog-* or seen-YYYY-MM-DD), AND (c) there is no "gate" key present.
For each match (oldest mtime first, cap 15 per run to bound runtime): gate-screen it now per
Step 3 (Stage 0 only), using its `_OCR.pdf` sibling if one exists, else pdftotext/live OCR.
Write a "gate" result and bump status to "gate-flagged-{date}" or "gate-passed-{date}", same as
any other gate-screened file. Gate-passing results still route through Step 4's Notion
dedup-check before writing. If more than 15 stale matches remain after the cap, log the residual
count in the run-complete runLog note so it visibly drains over consecutive weekly runs instead
of silently persisting.

## Step 4 — Log
Gate-passing new candidates → Notion Deal Sourcing Log
(collection://9a6ae219-85a3-4621-899c-c757fd062f8b) as Status=New Lead with
gates result in Notes / Flags. If Step 3.5 returned extracted fields, append an
"OM Extraction" section to Notes listing each field: value pair (e.g. "price: 1450000 |
totalSf: 17688 | yearBuilt: 1987 | clearHeightFt: 18 | inPlaceRentPsf: 5.40 | waltYears: 3.2").
Check for an existing row first; never duplicate.
Update manifest.json with all processed files.

## Step 5 — Report
Email summary via Outlook COM — C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1
(SOLE send path; Composio removed 2026-06-11 — on COM failure retry once then flag, do not halt)
from ggoldberg@oxfordra.net to ggoldberg@oxfordra.net ONLY (no egoldberg cc — per the 2026-05-15
routing directive re-ratified 2026-06-10, only the Daily Brief cc's Eric).
Subject: "OM Intake — {date}: {n} new, {m} OCR'd, {k} gate-passed".
Body: per-property gate verdicts, OCR failures, questions for Gabriel.
If zero new files: send nothing; the Step 0 run-complete entry suffices.
If the Outlook COM send is unavailable or fails after the one retry (e.g. Desktop Commander/PowerShell
not available this run), write the report to the folder as `YYYYMMDD_OM-Intake-OCR_Report_v##.md`
and note the delivery deviation in the run-complete runLog entry.

## Constraints
Autonomous; no mid-run questions. Originals immutable. Temp work in session
scratchpad only — never write temp files to the OneDrive folder. Permitted durable
writes there: `_intake\manifest.json` (canonical state), `*_OCR.pdf` siblings, and
the dated intake report when email is unavailable.


*Changelog — MIGRATED FROM FRONTMATTER (v1.5 (2026-08-17), class-n remediation). These entries previously existed ONLY in the `description` field; the body carried pointers reading "see description field above", which stops being true the moment the description is trimmed. Moved verbatim, not summarised.*

- **v1.3 (2026-07-29): corrected Folder: path (missing \Business\ segment; pointed to a nonexistent location). [MODEL: claude-sonnet-5 | set 2026-07-13]

- **v1.4 (2026-08-12): added Step 3.6 stale seen-backlog sweep (closes the gap that let "OM  Dollar General  Cincinnati OH.pdf" sit un-gated for ~2 months); OCR now Tesseract-backed (winget-installed 2026-08-12) with a Ghostscript deviation (blocked by non-admin session — see Step 2 note)

- **v1.6 (2026-09-12): Step 3.5's `om-extract` POST now sends `-Headers @{ 'X-ORA-Client' = '1' }`.** Paired with the `oxford-command-center` OI-050 fix (Host/CSRF request-boundary guard on the Brain Server), which requires this header on every non-GET request or 403s it — this task's call was the one caller the repo-scoped sweep for that fix could not see (lives outside the repo). Without this edit, extraction would have silently failed every Wednesday from 2026-09-16 onward (indistinguishable from "Brain offline" per Step 3.5's own catch-and-skip handling). No other logic changed.
