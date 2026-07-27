---
name: project-fred-key-exposure-2026-07-24
description: "CLOSED 2026-07-26 — FRED API key exposed in 21 cleartext local files (found by setup-self-audit's secret scan), rotated by Gabriel same-day, all 21 copies now resolved. Durable lesson: FRED MCP is stdio-transport and spawns fresh per session, so no fleet-wide restart is ever needed to pick up a rotated key."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-26T17:09:20.698Z
---

**CLOSED 2026-07-26.** Found 2026-07-24 by the newly-extended `setup-self-audit` secret
scan: the live FRED API key (fingerprint `sha256(key)[:12]` = `0f63fcc0868f`) sat in
cleartext in 21 files — 4 `SKILL.md` copies (1 local backup + 3 OneDrive archive copies of
the retired `ora-debt-maturity-snapshot` task, root cause: key hardcoded into a URL query
string instead of `{{FRED_API_KEY}}`), 5 `.claude.json.backup.*` copies, and 12 append-only
session-transcript/`audit.jsonl` echoes. Never in git history (never pushed).

Gabriel rotated the key same-day (new fingerprint `3cfc85efb07f`); old key independently
confirmed dead (`HTTP 400`), new key confirmed live (`HTTP 200`). Deliberately did NOT
scrub-then-rotate — scrubbing first would have (a) been incomplete (OneDrive cloud version
history + append-only transcripts can't be redacted) and (b) turned the tracking probe
green while a live key was still exposed, the exact false-assurance failure this scan
exists to prevent.

**Residual, closed 2026-07-26:** the 4 `SKILL.md` copies are scrubbed (3 already were; the
4th done this session, verified via fingerprint match, never re-printing the raw key). The
5 `.claude.json.backup.*` copies needed no action — it's a rolling window capped at 5, and
every file present by 07-26 already postdated the rotation. Transcripts/`audit.jsonl` are
intentionally left to age out (append-only, can't be redacted anyway).

**Durable lesson:** the original "restart Claude Desktop to reload the FRED MCP" framing
was wrong — `~/.claude.json`'s `fred` entry is `"type": "stdio"`, spawned per-session via
`uv run`, with `FRED_API_KEY` read from the *current* config at each spawn. A stdio MCP
server is never a shared long-running daemon; every new session (including every scheduled
task, which is a fresh spawn per firing, not a persistent process) already gets the current
key automatically. Confirmed empirically 2026-07-26: a session born from `ora-health-guard`'s
own post-rotation fire called `fred_latest`/`fred_series_info` successfully with no auth
error. Apply this lesson generally — don't assume an MCP credential rotation needs an app
restart without first checking whether the server is stdio (per-session) vs a networked
daemon a session merely connects to.
