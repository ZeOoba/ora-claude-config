---
name: reference-acquisition-pipeline-uniform-stamp-2026-08-16
description: "Acquisition Pipeline flipped to uniform-stamp 2026-08-16; detector BUILT the same day — the '⏰ Action Overdue' trap and why the bulk-field guard could not have caught it"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 681975eb-43c2-4411-8b0c-14015927e5b8
  modified: 2026-08-16T21:12:58.839Z
---

On **2026-08-16** the Notion **Acquisition Pipeline Tracker** (data source `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) was found showing the **uniform-stamp tell** — all 20 rows carrying one identical `last_edited_time` of `2026-08-13`. It was a **downgrade, not a freeze** (unlike the Tenant DB, the column is still advancing), but it left the source judged on a single unverifiable signal.

**`acquisition_pipeline_snapshot_diff.py` was built the same session. All six §A.1 database sources now have a snapshot-diff detector.** 62 selftest assertions; live baseline of 20 rows; same-day re-pull 0/0/0.

## The trap, and why it nearly shipped

The schema has THREE formula fields. One is calendar-derived and had to be excluded:

- **`⏰ Action Overdue`** — `if(prop("Next Action Date") < now(), "OVERDUE " + format(dateBetween(now(), ...,"days")) + "d", "")`. It **ticks** (`OVERDUE 4d`→`5d` daily) *and* **band-flips** (`""`→`OVERDUE 1d`). Two rows were already overdue at build time, so the detector would have been broken on day one.

**The natural template would have shipped the defect.** `deal_sourcing_snapshot_diff.py` shares this database's endpoint form (`/v1/data_sources/{id}/query` @ `2025-09-03`) and its `TIME_DERIVED_FIELDS` is EMPTY. Only reading each formula's expression live caught the difference — see [[reference_lease_date_detector_defects_2026-07-24]] for the 267/298 incident that made this discipline mandatory.

**⚠ The bulk-field guard is NOT a backstop here.** Measured on real data: only **3 of 20 rows drift per day = 15%**, far below the 50% `BULK_FIELD_RATIO`, and the guard verifiably stayed silent in the differential control. On a ~20-row table where only rows with a `Next Action Date` can drift, the guard is *structurally incapable* of firing on this field. Do not rely on it to catch a missed exclusion on small tables.

**Two formulas are deliberately KEPT** (exclude by NAME, never by TYPE): `Price Per SF`, and **`Replacement Cost Ratio` — governor-adjacent**, the RCT basis denominator behind ORA's ~35–40%-of-replacement discipline (populated on 13 of 20 rows; see [[project_replacement_cost_benchmark_unratified]] and [[reference_notion_pipeline_tracker_stale_governor_fields]]). A type-based exclusion would have blinded the detector to it, exactly as it would have blinded Property Register to `LTV`.

**Field-name codepoints were verified**: `0x23F0` + space + `Action Overdue`, with **no U+FE0F variation selector** — so the `"⏰ Action Overdue"` literal matches exactly. Worth re-checking if the exclusion ever appears to stop working.

## ⚠ These scripts are gitignored — force-add or they go unbacked

`~/.claude/.gitignore:61` carries `/scheduled-tasks/*/*`, so **nothing inside a task folder is tracked by default**. The five detector scripts and `SKILL.md` are tracked only because they were force-added. A new script in a task folder is silently excluded from the private backup repo (`ZeOoba/ora-claude-config`) until someone runs:

```
git add -f scheduled-tasks/ora-pm-ledger/<new-file>.py
```

This is very likely the same class as `ora-task-integrity-guard`'s recurring "UNBACKED file" finding (it fired again 2026-08-16).

**Landed and backed up: [PR #134](https://github.com/ZeOoba/ora-claude-config/pull/134), merged 2026-08-16 (merge commit `60f84d9`).** Merged content verified byte-identical to the live running copies of both the script and `SKILL.md`.

⚠ **Branching gotcha worth carrying.** `~/.claude` is routinely parked on some *other* session's feature branch, not `main` — at the time it sat on `feat/model-canary-probe-step25`, **17 commits ahead of `origin/main`**, only one of them mine. A worktree cut from `HEAD` inherits all of that, so a PR opened from it sweeps other sessions' unmerged work into your review. **Cut the worktree branch from `origin/main` and cherry-pick, or check `git rev-list --count origin/main..HEAD` before opening the PR.** Verify the cherry-picked file is byte-identical to what was reviewed — the `eos-review-gate` artifact is keyed to content, so any divergence silently invalidates the approval. See [[feedback_auto_review_blast_radius_gate]].
