---
name: piped-gate-exit-masking
description: "NEVER pipe a gate/test command (`npm run gate:ci | tail`) when its exit code is the evidence — bash reports the LAST pipe stage's code, so tail's 0 masks a red gate; redirect to a file and echo $? instead"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 506c87f0-3030-45f0-9886-9bd1de4311db
---

`npm run gate:ci 2>&1 | tail -25` exits 0 whenever `tail` succeeds — the gate's real failure code is discarded (bash default, no pipefail; Claude's Bash tool doesn't set pipefail).

**Why:** proven 2026-07-16 on oxford-command-center: a "gate:ci exit 0" background run actually contained a TS6133 typecheck failure (caught only by remote CI) and later a full typecheck failure with 8 errors — two wasted push/CI cycles and a false "verified" claim, on the same day the doctrine says evidence-before-done.

**How to apply:** for any command whose exit code is the verification evidence (gate, gate:ci, test, typecheck, lint):
```
cmd > "<scratchpad>/out.txt" 2>&1; echo "EXIT: $?"
```
then grep the file for detail. Piping to `tail`/`grep`/`head` is fine only for quick LOOKS where you will not cite the exit code as evidence. Also verify the summary line content (e.g. vitest "Test Files N passed") — never claim green from the exit code of a pipeline.

**Recurred 2026-09-10** (Gabriel, on his own smoke test): `preflight-shared-checkout.py` piped through `grep` printed `exit=0` over a **CONTESTED** verdict. Not a new mechanism — the same one, surviving because the countermeasure was only ever written down here. ORA's checks now print a machine-readable `RESULT_JSON={...}` as their LAST line specifically so a piped caller can still recover the verdict (`preflight-shared-checkout.py`, `verify-push.py`, `cross-repo-wip-scan.py`, `check-open-items-duplicate-ids.py`, the pm-ledger diffs) — when a tool offers one, read the verdict from that line. Promoted to a standing rule the same day: [[rules.md §26]]. Related: [[command-center-gate-vs-gate-ci-divergence]].
