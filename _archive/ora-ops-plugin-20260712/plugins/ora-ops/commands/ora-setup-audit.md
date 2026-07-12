---
description: ORA daily setup self-optimization routine — runs the maintenance probe suite via the full python path, triages SCREEN/WATCH/PASS, and emits a dated digest. Paste as a Claude Desktop scheduled-task prompt (daily 06:30 ET) or run interactively.
disable-model-invocation: true
---

Run the ORA daily setup self-optimization routine. Open and follow this prompt file EXACTLY:
C:\Users\Owner\.claude\daily-setup-audit-prompt.md
Run all probes using the FULL python interpreter path (bare `python` is not on PATH in scheduled sessions):
  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/setup-self-audit.py
  ...then fleet-status.py, doctrine-integrity-probe.py, governor-drift-probe.py, memory-integrity-probe.py the same way.
Triage findings SCREEN/WATCH/PASS. EMIT a dated digest (YYYY-MM-DD_setup-self-audit.md) to the canonical outputs folder. Per the ORA guard doctrine (I6): do NOT modify settings.json, hooks, CLAUDE.md, memory files, or the scheduler registry — list anything requiring those as PROPOSED actions in the digest for Gabriel to approve. If verdict is CRITICAL, also draft (do not auto-send) an alert email to ggoldberg@oxfordra.net. Mondays only: also run the cutting-edge radar (read-only WebFetch of hesreallyhim/awesome-claude-code + anthropics/claude-plugins-official) and append a 3-5 line shortlist.
