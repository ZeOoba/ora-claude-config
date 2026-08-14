---
name: run-once-guard-is-block-sentinel-not-run-once-guard-ps1
description: "The fleet's run-once/double-fire guard already exists as _shared/block-sentinel.py (Python, exit 10/11/12) — it is NOT run-once-guard.ps1, and specs written from memory keep describing a PowerShell version that was never built"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0c822226-ba45-4abd-891f-49ca84a7b30d
  modified: 2026-08-11T22:02:34.940Z
---

The CC/MCP scheduled-task **run-once / double-fire entry guard already exists** and has since 2026-08-09 (PRs #39, #40, merged to `origin/main`). Verify before building — it has now been re-specced from scratch at least once (2026-08-11) as if absent.

**What actually exists**, all in `C:\Users\Owner\.claude\scheduled-tasks\_shared\`:

| File | Role |
|---|---|
| `block-sentinel.py` | the guard — per-block, per-ET-date claim-then-complete |
| `outlook-sent-probe.ps1` | independent Layer 2 — Sent Items probe before any COM send |
| `test-block-sentinel.py` | 22 test functions (`grep -c 'def test_'` — the event_log's "23" is wrong) |
| `README-DOUBLE-FIRE-GUARD.md` | the canonical contract |

**The surface differs from how it gets re-specced.** A spec written from memory tends to describe a `run-once-guard.ps1`; that file does not exist and never did. The real contract:

| Re-specced as | Actually is |
|---|---|
| `run-once-guard.ps1` (PowerShell) | `block-sentinel.py` (**Python**) |
| exit 3 = complete, 4 = in-progress | **exit 10** = SKIP_ALREADY_COMPLETE, **11** = STAND_DOWN_IN_PROGRESS, **12** = REFUSED (non-owner) |
| `-Action Claim/Complete/Release` | `claim` / `complete` / `fail` (+ `--force`, `--adopt`) |
| `_state\run-once\<taskId>.json` | `_state\<taskId>-block-completion.json` |

`fail` is the Release verb — it clears a claim immediately so a retry need not wait out the TTL. Exit codes are deliberately 10+ to stay distinct from `send-via-outlook.ps1`'s 0–4, so **do not renumber them to 3/4** to match a spec; that reintroduces exactly the conflation the numbering avoids.

Wiring as of 2026-08-11: `ora-am-brief` (blockA–D), `ora-deal-aging-sla` (main), `ora-open-sessions-board` (main, TTL 45), `ora-monday-sync` (main, LAMS), `ora-health-guard` (blockA/B/C, TTL 45). ~22 email-sending CC tasks remain unwired — that is a deliberate backlog, not an oversight.

Related: [[feedback-absence-claims-need-verification-before-building]], [[feedback-verify-before-repeating-session-claims]], [[feedback-prompt-current-state-prose]].
