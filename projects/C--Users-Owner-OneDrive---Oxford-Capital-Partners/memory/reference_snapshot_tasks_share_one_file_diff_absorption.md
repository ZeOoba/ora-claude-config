---
name: reference-snapshot-tasks-share-one-file-diff-absorption
description: "ora-lease-snapshot-refresh and ora-cc-snapshot-refresh write the SAME tracked data/snapshots/portfolio.json — whichever runs after the workbook moves captures the diff and commits; the other then finds the file already matching HEAD and correctly commits nothing. A long commit gap is expected behavior, not a broken task."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e0f8485e-e687-437e-8cfa-2b85164df03d
  modified: 2026-08-12T21:00:30.414Z
---

Both `ora-lease-snapshot-refresh` (weekday `40 7 * * 1-5`) and `ora-cc-snapshot-refresh` (weekly `15 6 * * 1`) regenerate and commit the **same** git-tracked file, `data/snapshots/portfolio.json` in `oxford-command-center`. Both run the same material-change gate, which ignores `meta.generatedAt` and restores the file rather than committing timestamp-only churn.

The consequence is not obvious and gets misread as a fault: **whichever task runs after real workbook movement absorbs the entire diff.** It commits; the sibling's next fire then regenerates a file already identical to `HEAD`, sees an empty `$MATERIAL`, restores, and commits nothing — exactly as designed.

**Observed directly, 2026-08-11:** the CC task ran 22:39Z (a ~36h-late catch-up of its Monday slot) and committed `0b5b36e` at 22:41:56Z, carrying the `asOf` 2026-08-06 → 2026-08-10 movement. The lease task fired **3m41s later** at 22:45:37Z, found the file already current, and produced no commit. The next lease fire (2026-08-12) likewise found nothing material.

**What this means in practice**

- A multi-day gap between `Auto-refresh: lease snapshot` commits is **not** evidence the task is broken, blocked, or skipping. Check whether the sibling committed in the interval before treating it as a defect.
- It also means a task's own auto-push may never exercise: no commit → the whole Auto-push section is skipped. Through 2026-08-12 neither task had auto-pushed a commit of its own making; both pushes to date were manual.
- Diagnose from the sibling's commits and the run transcripts, never from one task's commit history alone. Registry `lastRunAt` holds only the **latest** run, so "did it fire on day N" is usually unanswerable from the registry after the fact — use the session transcripts (`scheduledTaskId` identifies them).

Guards that also live on this file and can independently suppress a commit: the section-shrink guard, the deals-degradation stdout scan (see [[reference-portfolio-json-notion-seed-fallback-regression]]), and the anomaly floor plus `checkSnapshot` write refusal (see [[reference_parseleases_vacancy_block_phantom_leases_2026-08-03]]). Rule out absorption first — it is by far the most common reason for "no commit."
