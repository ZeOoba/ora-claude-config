---
name: workflows-dir-single-writer-gap
description: RESOLVED 2026-07-16 (commit fa9da40) — ~/.claude/workflows is now git-TRACKED, so git-status single-writer checks see it; mtime sweep remains the catch for in-flight same-minute edits
metadata: 
  node_type: memory
  type: reference
  originSessionId: 506c87f0-3030-45f0-9886-9bd1de4311db
---

`C:\Users\Owner\.claude\workflows\` (cc-audit-army.js, cc-eval-plan-premortem.js, verified-deal-recon.js, `_tests/`) shows as `?? workflows/` in `git -C ~/.claude status` — the standard single-writer check (`git status`/`git log -1`) cannot see another session's uncommitted work on these files.

Proven 2026-07-16: two sessions concurrently edited cc-audit-army.js + `_tests/test.mjs` + README (one adding `args.forceModel`, one adding the cc-refresh scout). Git showed nothing; the collision was caught only by the Edit tool's "modified on disk since you last read it" warning and a PowerShell `LastWriteTime` sweep.

**How to apply:** before editing anything under `~/.claude/workflows`, sweep `Get-ChildItem -Recurse | Select FullName, LastWriteTime` and treat writes newer than session start that you didn't make as an active writer — re-read every file immediately before editing, keep edits additive, and re-run `node _tests/test.mjs` after. Shared mutable state there includes `_tests/cc-mode-prompts.snapshot.json` (re-snapshot procedure: [[rules]]-grade — README-cc-self-audit.md documents it). Related: [[shared-checkout-cofile-patch-hazard]].

**RESOLVED 2026-07-16:** `workflows/` (all 9 files incl. `_tests/`) tracked via `.gitignore` `!/workflows/` opt-in, commit `fa9da40`, pushed to the private ora-claude-config remote. Scrub re-verified independently pre-commit: zero confidential-terms.json hits, zero secrets; only firm-level figures already tracked via CLAUDE.md. Standard `git status` single-writer checks now see modifications AND new files there. The mtime sweep above is still worth running when git status shows a fresh modification you didn't make — it identifies WHICH files and HOW recent.
