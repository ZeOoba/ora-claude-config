---
name: file-reconciliation
description: Two modes for reconciling files against a canonical location. Mode A (dedupe) hash-diffs a candidate directory tree against a canonical one, bucketing every file as identical/new/conflicting/near-dupe, and archives the safe bucket only — never auto-overwrites. Mode B (version conflict) resolves multiple non-identical copies of the same nominal document (leases, estoppels, addenda) by extracting and diffing DOCX/XLSX text content, preferring the executed/signed PDF as source of truth over whichever draft has the newest file hash. Use when the user mentions: dedupe a folder, reconcile OneDrive folders, hash-diff directories, clean up duplicate files, which copy is correct, document version conflict, resolve lease/estoppel discrepancy, or migrating/consolidating a stray file tree into a canonical one. v1.0
license: ORA Internal
---

# File Reconciliation

Two related problems that were previously solved by hand-rewriting the same Bash and DOCX-extraction logic from scratch, repeatedly, in a single session: reconciling a whole duplicate/orphaned directory tree against a canonical one (Mode A), and resolving conflicting copies of one specific document (Mode B). Both ship with a real script in `scripts/` rather than prose alone, since the prior ad hoc versions were rewritten 4+ times in one session for Mode A and at least twice for Mode B's DOCX extraction.

## Scope

Mode A: whole-tree dedup — a stray/legacy folder (an old OneDrive copy, a migration export) needs merging into a canonical location.
Mode B: single-document conflict — multiple non-identical copies of what should be one document exist, and it's unclear which is authoritative.

## Triggers

Mode A: "dedupe this folder", "reconcile [folder] against [canonical]", "clean up this duplicate file tree", "merge this OneDrive folder into the real one".
Mode B: "these leases don't match", "which version of [document] is right", "resolve this document conflict", "these estoppels have different content".

## Inputs

Mode A: candidate directory path, canonical directory path.
Mode B: 2+ file paths (or a folder containing the suspected-conflicting copies) for the same nominal document, and — if available — the executed/signed PDF (if one of the copies is a signed PDF, it wins by default per the Standard Workflow below).

## Standard Workflows

### Mode A — Directory reconciliation

1. Run `python scripts/hash_diff_buckets.py <candidate_dir> <canonical_dir> --report <report.md>` (report-only, no files touched). This buckets every candidate file:
   - **IDENTICAL** — byte-identical to a canonical file already. Safe to archive-only.
   - **NEW** — no same-named file anywhere in canonical. Needs a destination decision, no overwrite risk.
   - **CONFLICT** — exactly one same-named canonical file exists with different content. Route to Mode B if these are meaningful documents (leases, estoppels, financial models); otherwise needs a one-off human call.
   - **NEAR-DUPE** — multiple same-named canonical files exist. Ambiguous; needs a human decision.
2. Present the bucket counts and the CONFLICT/NEAR-DUPE items specifically to Gabriel — these are the ones that can silently misfile a real discrepancy if auto-resolved. NEW items also need an explicit destination unless a confident single-candidate mapping is obvious (same relative subpath structure).
3. Only after explicit confirmation, re-run with `--apply` to archive the IDENTICAL bucket (moved to `--archive-dir`, default `<candidate_dir>/_archived`, with a `manifest.tsv` line per file — never deleted outright, per the never-delete rule). CONFLICT and NEAR-DUPE are never auto-applied by the script, by design.
4. For NEW files with a confident destination, copy (don't move) into canonical, then archive the candidate-side original the same way as IDENTICAL — keeping the manifest as the audit trail.
5. Log the reconciliation (source, canonical, bucket counts, any CONFLICT resolutions) to `event_log.md` if this was a business-file consolidation rather than a personal/Claude-system cleanup.

### Mode B — Document version conflict resolution

1. If one of the conflicting copies is an **executed/signed PDF**, it is the presumptive source of truth — do not let a draft `.docx`/`.doc` with a newer file-modification hash override it. A hash-based "most recent wins" heuristic has produced wrong conclusions before (a lease escalation-clause mismatch and a mislabeled estoppel for the wrong property were both only caught by checking the actual signed PDF).
2. For DOCX copies, extract text with `python scripts/docx_extract_text.py file.docx` (single file) or `python scripts/docx_extract_text.py file_a.docx file_b.docx` (unified diff between two). For XLSX copies, use the `excel` MCP's read tools or `openpyxl` directly — no bespoke script needed there, the existing tooling covers it.
3. Read the diff for a **substantive** difference (a changed clause, a different party name, a different unit/property reference) versus a cosmetic one (formatting, a signature-block-only difference, boilerplate). Only substantive differences need escalating.
4. If no executed PDF exists among the copies and the DOCX/XLSX diff shows a substantive conflict, present it to Gabriel via `AskUserQuestion` rather than guessing — do not pick "the one that looks more complete" or "the newest" as a silent default.
5. Once resolved, archive the superseded copy/copies (never delete) with a manifest note explaining which was kept and why, and log to `event_log.md` if this touches an active property/tenant record.

## Outputs

- Mode A: `hash_diff_report.md` (or caller-specified path), `manifest.tsv` in the archive directory, `event_log.md` entry for business-file consolidations.
- Mode B: extracted-text diff output, resolution decision + rationale, archived superseded copies with manifest note.

## Boundaries

- Never auto-resolve a CONFLICT or NEAR-DUPE bucket item, or a Mode B substantive diff, without explicit human confirmation.
- Never delete — archive only, with a manifest line, per the standing never-delete rule.
- Writing to a non-Claude-system business OneDrive folder (moving/archiving files) requires the same permission as any other write to that tree — confirm scope before running `--apply` on business data, not just Claude-system cleanup.
- This skill does not touch financial models or governor constants even if one shows up in a CONFLICT bucket — flag those for the standard modeling-change permission gate rather than resolving as a routine document conflict.

## Dependencies

- `excel` MCP (Mode B, XLSX conflicts)
- `conversation-archival` / `event_log.md` (logging business-file resolutions)

## Changelog

- v1.0 (2026-07-11): initial. Combines two candidates (`duplicate-file-reconciliation`, `document-version-reconciliation`) surfaced by a workflow-audit session that found the underlying hash-diff-bucket-archive and DOCX-extraction logic hand-rewritten 4+ times and 2+ times respectively in a single prior session. Ships `scripts/hash_diff_buckets.py` and `scripts/docx_extract_text.py` rather than prose-only instructions, to actually remove the repeated-authoring cost.
