---
name: reference-portfolio-json-generatedat-commit-churn
description: "portfolio.json's generatedAt timestamp makes every lease-snapshot run look dirty; RESOLVED 2026-07-27 by a material-change gate that ignores that field"
metadata: 
  node_type: memory
  type: project
  originSessionId: 45297343-39e2-4a3e-b735-e02e65d053ac
  modified: 2026-07-28T00:16:14.658Z
---

`data/snapshots/portfolio.json` (oxford-command-center) carries a `meta.generatedAt` ISO timestamp that `scripts/lease-snapshot-drift-check.ts` rewrites on **every** run. Since the file became git-tracked on 2026-07-27 (Gabriel directive), `git status --short data/snapshots/portfolio.json` is therefore never empty after a run — the original `ora-lease-snapshot-refresh` auto-commit rule's "byte-identical → skip" short-circuit was unreachable, so all three weekday fires committed. Observed on the 19:00 run of 2026-07-27: exit 0, no drift, 138 leases, sole diff line `generatedAt`. That run's commit is `b0a55e6` — left in history deliberately (a revert would mean destructive git on a shared checkout for one cosmetic commit).

**RESOLVED 2026-07-27** — Gabriel chose the compare-excluding-`generatedAt` option over changing the artifact schema. `~/.claude/scheduled-tasks/ora-lease-snapshot-refresh/SKILL.md` now runs a material-change gate before committing:

```bash
MATERIAL=$(git diff -U0 -- data/snapshots/portfolio.json | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[+-][[:space:]]*"generatedAt":')
```

Empty → `git restore` the file, no commit. Non-empty → commit as before. Verified live in both directions before shipping: a timestamp-only regeneration produced empty `$MATERIAL`, and a deliberately perturbed `leaseEnd` produced the expected `+`/`-` pair.

**Why:** at `0 7,13,19 * * 1-5` the old behavior generated ~15 timestamp-only commits/week on `main`, burying the commits that represent real lease movement — and left the alternative (skip the commit, leave the file dirty) polluting a shared checkout that other sessions rebase over.

**How to apply:** a non-empty `git status` on this file is *not* evidence lease data changed — always diff past `meta.generatedAt`. Branch on the variable's **contents**, never `&&`-chain the pipeline: `grep` exits 1 on no-match, so exit-code logic inverts the verdict ([[feedback_piped_gate_exit_masking]], [[feedback_bash_chain_short_circuit_hides_skip]]). Note the drift reporter only speaks up for new/removed/date-changed leases, so a rent or SF correction now surfaces as an Exit 0 that commits — that combination is informative, not anomalous. Same trap applies to any other producer that stamps a generation time into a tracked artifact. Related: [[reference_autocrlf_defeats_content_hash_gates]], [[project_master_workbook_no_single_writer_2026-07-24]], [[reference_cc_scheduler_filepath_mechanism]].
