---
name: project-fred-key-exposure-2026-07-24
description: "REMEDIATED 2026-07-24 — FRED API key rotated by Gabriel and independently verified (old key HTTP 400 dead, new key HTTP 200 live). The 21 cleartext local copies now hold a dead credential. Residual: restart to reload the MCP env, then scrub at leisure."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T16:51:53.873Z
---

**REMEDIATED 2026-07-24.** Gabriel rotated the key at the FRED console same-day. Verified
independently (not taken on the note's word): live HTTP call with the **old** key
(fingerprint `0f63fcc0868f`) → `HTTP 400 api_key is not registered` (dead); same call with
the **new** key from `~/.claude.json` (fingerprint `3cfc85efb07f`) → `HTTP 200` (live). The
21 cleartext copies below now hold a worthless credential — no further urgency, but they
still need scrubbing (queued, not done — see Residual below).

Found 2026-07-24 by the newly-extended `setup-self-audit` secret scan (see
[[reference-probe-scan-sets]]); invisible to every scheduled check before that change.

## What was found

The **currently-live** FRED API key (fingerprint `0f63fcc0868f`, 32 chars — verified by
hashing against the live config, never by printing either value) in **21 files**:

| Class | Files | Note |
|---|---|---|
| `backups/.claude.json.backup.*` | 5 | backups of the legitimate key home |
| `backups/scheduled-skills-…/ora-debt-maturity-snapshot__SKILL.md` | 1 (3 occurrences) | what the scan flagged |
| OneDrive `_archive_*_retired/ora-debt-maturity-snapshot/SKILL.md` | 3 | Claude_Workspace + Documents/Claude |
| session transcripts / `tool-results` / `subagents` `.jsonl` | 9 | key echoed into past conversation logs |
| LAMS `audit.jsonl` (AppData) | 3 | Cowork audit logs |

**Not in git history: `git log --all -S <key>` over `~/.claude` returns 0 commits, and 0
tracked files contain it.** So it has never been pushed to `ZeOoba/ora-claude-config`.
Exposure is local-disk only. This also means the new pre-push credential gate will not
block pushes of `~/.claude` on account of this key.

Root cause: the key was hardcoded into a URL query string
(`…/fred/series/observations?…&api_key=<key>&file_type=json`) in the
`ora-debt-maturity-snapshot` SKILL.md. The live copy was scrubbed earlier; the archived
and backup copies were not, and the key then propagated into session transcripts.
Same incident class `scrub-before-optin.py`'s docstring already documents.

## Why the 21 copies weren't scrubbed before rotation — deliberate, held

1. **Rotation was the only real remediation.** Scrubbing cannot be made complete: the
   OneDrive copies have **cloud version history** that a local redaction does not touch,
   and session transcripts are append-only logs. Scrubbing first would have left a live
   key in places nobody could enumerate.
2. **Scrubbing first would have destroyed the reminder.** The daily `[ACTION]`
   health-guard email was the tracking mechanism. Redacting the flagged file turns the
   probe green while the credential is still valid — the exact false-assurance failure
   this whole line of work exists to prevent.

## Residual — not yet done

1. **Restart Claude Desktop / reload the FRED MCP.** The running `mcp-servers/fred`
   process read `FRED_API_KEY` into its env at startup and is still holding the **old**
   (now-dead) key — a live call through the MCP tool returns the same `HTTP 400` as the
   raw old-key test above. `~/.claude.json` has the new key; the process just hasn't
   re-read it. Live FRED-dependent scheduled tasks: `ora-health-guard` (05:15),
   `ora-am-brief` (06:00), `ora-sofr-direct-prefetch` (10:10 M–F),
   `ora-deal-sourcing-scan` — restart before 05:15 tomorrow or they fail.
2. **Scrub the 21 cleartext copies of the dead key** (4 `SKILL.md` copies + 5
   `.claude.json.backup.*` — transcripts and `audit.jsonl` are append-only, leave those to
   age out). Only a cleanliness item now, not a security exposure. Full re-scan 2026-07-24
   confirms the count and class breakdown exactly matches the original finding (39,912
   files scanned across all 4 roots, 21 hits / 108 occurrences, none in a tracked or
   committed path) — nothing new appeared and nothing was missed the first time.

Do **not** scrub `~/.claude.json` — it is the legitimate key home and now holds the
correct live key. Note the memory's original list of "legitimate key homes" incorrectly
included `claude_desktop_config.json`; verified 2026-07-24 the key was never there.

Related: [[reference-probe-scan-sets]], [[reference_quickbooks_financials]] (secrets index
lives in `tech.md`).
