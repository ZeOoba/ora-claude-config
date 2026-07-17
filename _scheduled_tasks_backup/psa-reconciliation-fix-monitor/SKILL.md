---
name: psa-reconciliation-fix-monitor
description: EOD 2026-07-17 checkpoint: verify psa-reconciliation description fix packaged + installed, and the 3 systematization fixes landed; flag loudly if outstanding.
---

You are running a one-time status monitor for Gabriel Goldberg (Oxford Realty Advisors). Goal: confirm the psa-reconciliation skill fix + related systematization work is DONE by end of day 2026-07-17, and flag it loudly if not. This is a READ-ONLY status check — do NOT edit, package, install, commit, or send anything. Report findings to this session's completion notification only (no email, no external send).

Background: yesterday psa-reconciliation could not be packaged because its frontmatter `description` was 1274 chars, over the 1024-char platform import limit, so it was the only 1 of 10 skills NOT installed. A Code-surface prompt was handed off titled `2026-07-16_psa-reconciliation-fix-and-systematization_CodePrompt_v01.md` covering: (Task 1) trim the description below 1024 and commit; (Task 2) a shared frontmatter validator behind a new `tools/hooks/pre-commit`; (Task 3) a "raw sync -> provisional -> always reimport" doctrine edit to `ora-skill-store-drift-check` plus a REIMPORT-PENDING vs IN-SYNC distinction.

Use the Desktop Commander MCP (start a PowerShell process via start_process; if its tools are deferred, load them with ToolSearch query "select:mcp__plugin_desktop-commander_desktop-commander__start_process,mcp__plugin_desktop-commander_desktop-commander__interact_with_process,mcp__plugin_desktop-commander_desktop-commander__read_process_output" first). If Desktop Commander is unavailable, say so and stop rather than guessing.

Run these checks against the live filesystem:

1. DESCRIPTION FIXED — authoritative oracle is the packager. Run: `Set-Location 'C:\Users\Owner\ora-skills'; python tools\package_skills.py "$env:TEMP" psa-reconciliation; $LASTEXITCODE`. Exit 0 with `description N/1024 OK` = description trimmed and packageable. Non-zero (still "description is 1274/exceeds 1024") = NOT fixed. Then delete the throwaway `$env:TEMP\psa-reconciliation.skill`.

2. INSTALLED / CACHE-SYNCED — compare the repo copy `C:\Users\Owner\ora-skills\psa-reconciliation\SKILL.md` against the runtime cache copy `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\583f08bc-0123-4111-8158-8fe3d927e350\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\skills\psa-reconciliation\SKILL.md`. Normalize line endings before declaring a diff (replace CRLF with LF, trim trailing whitespace per line and at file end) and SHA256-compare the normalized text — a raw-only mismatch on identical content is NOT drift. Match = cache is current.

3. INSTALL LOGGED — search `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\event_log.md` for a psa-reconciliation Save-skill install entry dated 2026-07-17 (a confirmed click, not just a commit).

4. SYSTEMATIZATION — check whether `C:\Users\Owner\ora-skills\tools\hooks\pre-commit` exists (Task 2), and grep `ora-skill-store-drift-check`'s SKILL.md for a "provisional"/"REIMPORT-PENDING" raw-sync rule (Task 3). Report each as landed / not landed. These are secondary to the psa-reconciliation install.

VERDICT:
- If checks 1+2 pass AND (3 logged OR cache clearly synced), report "DONE" concisely, and note the systematization status.
- If ANY of 1/2/3 is still outstanding, report "OUTSTANDING — psa-reconciliation not yet fixed/installed as of EOD 2026-07-17" with a one-line-per-item breakdown of exactly what is missing and the single next action (e.g., "description still 1274 chars — run Task 1 of the Code prompt"). Make the outstanding verdict prominent.
Keep the whole report under ~12 lines.