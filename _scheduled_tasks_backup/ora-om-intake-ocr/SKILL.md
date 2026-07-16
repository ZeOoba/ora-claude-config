---
name: ora-om-intake-ocr
description: Weekly OM intake pass — detect new PDFs in Investment Candidates folder, OCR image-only scans, gate-screen new candidates (Buy Box Stage 0), extract structured fields via Brain server, report. Wednesdays 6:15 AM ET. v1.2 (2026-06-15). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

# ORA OM Intake & OCR Pass (weekly)

Folder: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026`

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
       -Method Post -Form $form -TimeoutSec 60
  if ($r.ok -and $r.fieldCount -gt 0) { $extractedFields = $r.fields }
} catch { $extractedFields = $null }
```

If extraction succeeds (ok=true, fieldCount > 0): store fields for Step 4.
If Brain server is unavailable (connection refused / timeout / any error): skip silently —
log "Brain offline — no field extraction" in the candidate note. Never block gate-logging on
extraction failure.

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