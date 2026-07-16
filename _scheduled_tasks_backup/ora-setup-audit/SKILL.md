---
name: ora-setup-audit
description: RETIRED 2026-06-16 (strategic audit kill list): daily cadence overkill; overlaps ora-health-guard pre-session check.
---

Run the ORA daily setup self-optimization routine. Open and follow this prompt file EXACTLY — it is the authoritative spec: C:\Users\Owner\.claude\daily-setup-audit-prompt.md

Run all probes using the FULL python interpreter path (bare `python` is NOT on PATH in scheduled sessions):
  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/setup-self-audit.py
Then run, the same way, from C:/Users/Owner/.claude/maintenance/ : fleet-status.py --summary (DUAL-FLEET since 2026-06-10 — reads BOTH the claude-code-sessions and local-agent-mode-sessions registries), registry-membership-probe.py (exit 1 = a task entry silently DROPPED from a registry — treat as SCREEN/CRITICAL; this is the failure mode that left the heartbeat dark 2026-05-31..06-10), doctrine-integrity-probe.py, governor-drift-probe.py, memory-integrity-probe.py.

Triage every finding SCREEN / WATCH / PASS. EMIT one dated digest file named YYYY-MM-DD_setup-self-audit.md to the canonical outputs folder (Claude_Workspace\00_Governance\outputs\). **WRITE INCREMENTALLY (added 2026-06-11 after the 6/11 run was RAM-parked mid-run and emitted nothing):** create the digest file with its header + a "RUN IN PROGRESS" marker BEFORE running the first probe, append each probe's verdict line immediately after that probe completes, and finish by replacing the marker with the final verdict + SCREEN/WATCH/PASS table + PROPOSED-actions list. A killed run must still leave a partial digest showing how far it got.

Per the ORA guard doctrine (I6) this task is READ-ONLY / emit-only: do NOT modify settings.json, hooks, CLAUDE.md, memory files, or the scheduler registry — list anything that would require those as PROPOSED actions in the digest for Gabriel to approve. If the verdict is CRITICAL, additionally DRAFT (do NOT auto-send) an alert email to ggoldberg@oxfordra.net. On Mondays only, also run the read-only cutting-edge radar (WebFetch https://github.com/hesreallyhim/awesome-claude-code and https://github.com/anthropics/claude-plugins-official) and append a 3-5 line shortlist.

HARD GUARDRAILS: never send email, move money, modify financial models, or touch oxfordra.net. Drafts only; the human sends.