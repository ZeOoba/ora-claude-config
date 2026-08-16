---
name: project-automation-audit-rev11-2026-08-16
description: "Automation Audit Revision 11 — narrow follow-up (README diagram + 7-file gitignore churn fix), both executed same-pass"
metadata: 
  node_type: memory
  type: project
  originSessionId: 68a5d5ac-c5a8-4f84-a15e-2f03f545ae99
  modified: 2026-08-16T17:36:13.523Z
---

Revision 11 of the "ORA Automation Audit" artifact (https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7), 2026-08-16 — a narrow scoped follow-up via [[ora-setup-audit-skill]], NOT a fresh full four-thread pass (Revision 10, 2026-08-14, is still the last complete one; its KPIs — plugin footprint, skill counts, fleet health, token-bloat gates — were carried forward unmeasured here).

**Trigger:** surfaced while fixing a broken Mermaid diagram in `ora-claude-config`'s own README in an unrelated session (the diagram-review session, not this one's usual scope).

**R11-1 — FIXED.** README's architecture diagram showed `MAINT` (`maintenance/`) with zero edges, implying it's outside the hook/session wiring. Verified false: `hooks/git-prepush-doctrine-gate.py` directly launches `maintenance/doctrine-integrity-probe.py` as part of the pre-push chain. Added `HOOKS --> MAINT` plus a caption citation. Re-rendered standalone via `mermaid-cli` to confirm no syntax regression. Commit `615a6e2`.

**R11-2 — FIXED.** 7 `maintenance/_state/` files (`fleet-roster.md`, `model-canary.json`, `model-currency-cc.md`, `registry-membership.json`, `task-content-ledger.json`(`.lock`), `wake-cause.json`) were tracked with no external reader, causing chronic single-writer commit noise — directly observed: committing R11-1 required isolating it from 13 unrelated dirty files. Applied the same external-reader test the repo's own `.gitignore` already uses for `phantom-dispatch.json` vs. `health-guard-beacon.json`: grepped `fleet-deadman.yml` + both sibling repos (`oxford-command-center`, `ora-pm`), zero external/CI readers found for all 7. `health-guard-beacon.json` checked and correctly excluded — keeps its dead-man-reader exemption. The one candidate counterargument (losing audit trail for a postmortem) didn't hold: the cited precedent ([[am_cluster_late_wake_root_cause]]) was reconstructed entirely from Windows Event Log + Claude Desktop's own logs, never from these files' git history. Added `.gitignore` entries + `git rm --cached` (working-tree copies untouched). Commits `615a6e2` (untracking landed here by a staging accident, documented in-commit) + `2fa2678` (the `.gitignore` formalization).

**Push friction (not a finding, a process note):** the initial `git merge` on the live `~/.claude` checkout tripped `config-write-guard`'s blast-radius gate (write-verb + `~/.claude` path marker) even though the merge touched no hooks/settings/CLAUDE.md content. Resolved via the hook's own preferred path — an isolated worktree (`git worktree add -b <tmp> <path> HEAD`, merge there, push `tmp:feat/model-canary-probe-step25`, then remove the worktree) — rather than minting an override token for a non-edit. Also hit one real concurrent-push rejection (another session landed a memory-integrity fix, `86f864d`/`67686b0`, mid-session) — reconciled with a clean no-conflict merge, not a force-push.

**Landed on:** `feat/model-canary-probe-step25` (this repo's standing integration branch, same accumulate-then-batch-PR pattern as PRs #105/#115/#116/#119). NOT yet PR'd to `main` as of this entry — ask Gabriel before opening another PR so soon after #119.

**Artifact housekeeping:** Revision 7's rev-band rolled off to `ora-automation-audit-history.md` per the 4-entry cap (Step 4a) to make room for Revision 11 — the artifact's own durable-source discipline held.

**Not done, pending Gabriel:** PR-to-main for this batch (see above).
