---
name: autonomy-gate-blocks-writes-not-reads
description: "ora-autonomy-gate blocks only WRITES into the site tree — a \"blocked read\" means the command carried a write indicator; read the hook before invoking the override protocol"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ac8cd07a-65a5-4241-b6a5-8fc60c23a6ad
---

A session (scheduled-origin, 2026-07-09) reported that `ora-autonomy-gate.py` "fires on any shell command scoped into the website-canonical tree" and stopped, requesting the `allow-website-change` override sentinel for a mere branch read. That claim was wrong: GATE 2b blocks a Bash command only when a site-path marker (`website-canonical`/`oxford-site`) co-occurs with a write indicator (`>`, `cp `, `mv `, `rm `, `tee `, `set-content`, …). Reads and preview deploys pass untouched — the hook's own docstring says so. The session's block was almost certainly the `2>&1` false-positive fixed the same day (bare-`>` matching, see hook comment dated 2026-07-09).

**Why:** Acting on the propagated claim would have opened an unnecessary 60-minute site-write override window under Hard Invariant 2 — with Gabriel's blessing, but for an action that never needed it.

**How to apply:** When any session (including a prior one of your own) reports a hook block, read the hook source and the exact blocked command before invoking an override protocol. For website-canonical reads, just avoid write-indicator substrings and stdout redirects in the command text. Sibling lesson to [[verify-subagent-safe-claims]] — verify "blocked" claims as skeptically as "safe" claims.

Related fact found during the same verification: branch `logo-svg-fix` (1452b3b, 2026-04-26 "Replace blurry PNG logo with inline SVG") is fully merged into main — stale, not a pending fix.
