---
name: feedback-verify-subagent-safe-claims
description: "Before executing any subagent/workflow's 'safe-now' classification (esp. file moves/archives), independently re-verify against live state — greps for code references miss operational-doctrine references (a file named in rules.md prose, not in a script)."
metadata:
  node_type: memory
  type: feedback
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
---

A workflow's discovery agents are good at surfacing candidates and bad at knowing which "obviously safe" files are secretly load-bearing, because they typically only grep for code/script references — not references embedded in prose documentation that a human (or a future session) is expected to read and act on.

**What happened (2026-07-09):** a 9-agent Claude Code setup audit proposed archiving ~40 files/dirs as "safe-now" (reversible, Claude-owned, no live dependency found). Before executing, direct re-verification caught two of these as actually load-bearing:
- `chip-claims.log` — the audit's grep found no *script* referencing it, but `rules.md` §8 names this exact path as the live claim-lock file the parked-task-chip protocol reads/appends to on every run. Archiving it would have silently reset every in-flight claim.
- `daily-setup-audit-prompt.md` — flagged safe scratch; it's actually the canonical prompt a live plugin command (`ora-ops:ora-setup-audit`) opens by exact hardcoded path every day at 06:30. Moving it would have broken the daily audit routine.
- Separately, a claimed finding ("12 of 17 `backups/` subfolders are completely empty") was flat-out wrong on direct inspection — all 15 subfolders contained real files (1–304 each). Acted on the disproven claim by skipping that action entirely, rather than either blindly trusting or blindly distrusting the workflow's report.

**Why:** subagents did real work (282 tool calls across 9 agents in this case) and were right on the vast majority of findings — the failure mode isn't laziness, it's that a grep-for-references check has a narrower blast-radius model than "is this named anywhere a human would go looking," and workflows can also just be wrong about a factual check (the empty-folders claim).

**How to apply:** treat a subagent's "safe/verified" tag as a strong prior, not a green light. Before executing any batch of file moves, deletions, or config edits a workflow proposed:
1. Spot-check the specific claim that makes something "safe" (existence, emptiness, no-references) directly yourself — don't just re-trust the same grep pattern the agent used.
2. Grep for the target filename/path across rules.md, CLAUDE.md, and any skill/command file that might reference it by exact path in prose — not just scripts/hooks.
3. If a claim doesn't hold up (like the empty-backups one), don't just skip silently — surface the correction to the user so trust calibrates on real evidence, not on the subagent's confidence.
This is generically applicable to any Workflow-tool run whose output includes a "safe to auto-apply" bucket, not specific to this audit.
