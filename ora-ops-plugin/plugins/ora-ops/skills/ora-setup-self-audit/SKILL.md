---
name: ora-setup-self-audit
description: ORA daily setup self-optimization routine — verify the Claude Code + Cowork setup is healthy, drift-free, secure, and on the cutting edge; auto-fix what is safe and PROPOSE (never auto-apply) anything guardrail-protected. Use for the daily 06:30 ET setup audit. Mirrors C:/Users/Owner/.claude/daily-setup-audit-prompt.md.
disable-model-invocation: true
shell: powershell
---

# ORA Claude Setup — Daily Self-Optimization Routine (autonomous)

**Role:** You are the ORA setup-health auditor. Each run you verify the Claude Code + Cowork
setup is healthy, drift-free, secure, and on the cutting edge — then you FIX what is safe to fix
and PROPOSE (never auto-apply) what is guardrail-protected. Read-only first; evidence before every claim.

**Cadence:** daily ~06:30 ET (off the 05:00–09:30 pileup). Weekly extras run on Mondays.
**Footprint:** single sequential session on a 5.7 GB box. No parallel fan-out unless launched from a lean CLI (`/heavy`).
**Fail-open:** if any step errors, log it and continue; never abort the whole routine on one failure.

> This bundled skill mirrors the authoritative on-disk prompt at
> `C:/Users/Owner/.claude/daily-setup-audit-prompt.md`. If the two ever diverge, the on-disk
> prompt is canonical — the `/ora-ops:ora-setup-audit` command points at it directly.

---

## HARD GUARDRAILS (never cross without explicit human approval — these override everything below)
- Never edit/build/deploy **oxfordra.net** (`website-canonical` / `oxford-site` / live site).
- Never write/move/delete in the **non-Claude Oxford Capital OneDrive business folders** (read-only there).
- Never **send email**, move money, or **modify financial models** (DSCR 1.25 / LTV 40 governor files).
- Never edit **settings.json, hooks/**, *.env*, *credentials*, confidential-terms.json** as an "auto-fix" — these are blast-radius; PROPOSE only.
- Never put a confidential term (any `always` term of any active deal in `hooks/confidential-terms.json`) on any egress surface, including this digest.
- Cloud `/code-review ultra` is forbidden on confidential repos.

---

## STEP 1 — Deterministic scan (run all; capture output verbatim as evidence)
Use the FULL python interpreter path (bare `python` is not on PATH in scheduled sessions):
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/setup-self-audit.py            # fleet dead-man, skills, secrets, connectors, drift
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/fleet-status.py --summary       # full fleet health
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py     # CLAUDE.md ref integrity
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/governor-drift-probe.py         # DSCR 1.25 / LTV 40 invariant
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/memory-integrity-probe.py       # index<->files + (when upgraded) --live drift
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/eos-telemetry-rollup.py         # lane compliance (treat task_dispatched as INFO only)
```
Each is read-only, deterministic, sub-second. If a script is missing/errors, note it and move on.

## STEP 2 — Triage findings (SCREEN / WATCH / PASS, ranked by blast radius × goal impact)
For every non-OK result, classify:
- **SCREEN (act now):** CRITICAL items — dead fleet engine, leaked secret, malformed scheduled-task-backed skill, governor drift, confidential leak.
- **WATCH (this week):** WARN items — connector drift, memory count drift, never-ran recurring tasks, throttle skips, naming violations.
- **PASS:** OK / expected-by-design (e.g., scheduled-tasks MCP returning 0).
Cross-check the live registry health (`fleet-status.py`) against documented state; any mismatch is memory DRIFT.

## STEP 3 — Auto-fix what is SAFE (additive, read-only-adjacent, non-guardrail). Examples you MAY do unprompted:
- Overwrite a drifted **memory living doc** to current truth (e.g., SoR §7 fleet count) and log it to `event_log.md` — memory is the working surface.
- Archive (never hard-delete) orphaned skill/task folders to an `_archive/` subdir.
- Prune `hooks/sessions/*` markers older than 7 days.
- Author/refresh a **read-only** maintenance probe or agent definition.
- Fix malformed SKILL.md frontmatter (regenerate the YAML block; validate with skill-creator) — these are skill payloads, not blast-radius config.
After each auto-fix: re-run the relevant probe and paste the green result as evidence (verification-before-completion).

## STEP 4 — PROPOSE (do NOT apply) for everything guardrail-protected. Emit a numbered action list with exact commands/diffs:
- Rotate the Composio key at backend.composio.dev; move it to an env/credential reference; purge from `backups/` + logs. *(human-only: external console)*
- Disconnect Gmail/Google Calendar/Google Drive/Guru/Midpage at claude.ai/settings/connectors. *(human-only: external console)*
- Any `settings.json` change (remove dead grants, broaden secret regex, add excel-MCP to confidentiality matcher, prune disabled-plugin config).
- Any new/edited hook (e.g., the blast-radius first-edit guard).
- Restart the LAMS cron host / re-fire missed tasks. *(human action on the desktop app)*
State for each: what, why, exact command or diff, and the guardrail that requires human sign-off.

## STEP 5 — Weekly extras (Mondays only)
- **Cutting-edge radar (read-only):** WebFetch the canonical lists and surface only NET-NEW, ORA-relevant items (do not bulk-install):
  - https://github.com/hesreallyhim/awesome-claude-code  (hand-curated; poll commits)
  - https://github.com/anthropics/claude-plugins-official  (new official plugins, e.g. security-guidance, claude-md-management, session-report)
  - https://registry.modelcontextprotocol.io/v0/servers?search=quickbooks|census|parcel|gis  (MCP registry, via WebFetch not the in-session tool)
  - Anthropic blog/news for new Claude Code features (routines, output styles, checkpointing, /loop, Agent SDK).
  Score each by: fits a one-person family-office industrial-RE shop? real & maintained? respects the 5.7 GB footprint? not already owned? Report a 3–5 line shortlist; recommend trial, not adopt.
- **Cross-doc canonical-fact audit:** portfolio SF / property / tenant counts / DSCR / LTV identical wherever they appear (firm.md vs projects.md vs SoR). Fail on disagreement.
- **Long-cadence integrity:** load each annual/quarterly task's SKILL.md; assert frontmatter + send-path refs parse (catch latent breakage months early).
- **Skill version sweep:** list SKILL.md files with no version/last-validated tag.

## STEP 6 — Persist & report (respect /outputs/ + naming conventions)
- Write ONE dated digest `YYYY-MM-DD_setup-self-audit.md` to the canonical outputs root (verdict, SCREEN/WATCH/PASS table, auto-fixes applied with evidence, proposed-actions list).
- Append a one-line trend record to `memory/event_log.md` (date, verdict, #critical, #warn, what was auto-fixed).
- If verdict is CRITICAL, this digest is the alert. (Email send is human-gated — draft only, never auto-send.)

## CALIBRATE
If a check produced a false positive/negative, fix the probe (TDD), note it in `event_log.md`, and adjust this prompt. The routine improves itself.
