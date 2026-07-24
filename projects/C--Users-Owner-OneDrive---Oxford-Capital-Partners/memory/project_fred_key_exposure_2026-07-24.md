---
name: project-fred-key-exposure-2026-07-24
description: "OPEN 2026-07-24 — the live FRED API key sits in cleartext in 21 local files; never committed, so not pushed. Rotation is Gabriel's action and is the only real remediation."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T16:28:40.981Z
---

**OPEN — awaiting Gabriel. Blocking action: rotate the FRED API key at the FRED console.**

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

## Why nothing has been scrubbed yet — deliberate

1. **Rotation is the only real remediation.** Scrubbing cannot be made complete: the
   OneDrive copies have **cloud version history** that a local redaction does not touch,
   and session transcripts are append-only logs. Scrubbing first would leave a live key
   in places nobody can enumerate.
2. **Scrubbing first destroys the reminder.** The daily `[ACTION]` health-guard email is
   currently the tracking mechanism. Redacting the flagged file turns the probe green
   while the credential is still valid — the exact false-assurance failure this whole
   line of work exists to prevent.

**Order: rotate at the FRED console → confirm the new key works → then scrub the durable
copies (the 4 SKILL.md copies + 5 config backups) → transcripts age out.**

Do **not** scrub `~/.claude.json` or `claude_desktop_config.json` — those are the
legitimate key homes and the FRED MCP needs them until rotation.

Related: [[reference-probe-scan-sets]], [[reference_quickbooks_financials]] (secrets index
lives in `tech.md`).
