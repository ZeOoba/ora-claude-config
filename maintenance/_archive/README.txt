ORA maintenance/_archive — retired scripts (never deleted, per the "move to /archive/, never delete" invariant)

register-eos-health-task.ps1
eos-health-report.ps1
  Superseded 2026-07-08 by the `ora-doctrine-integrity-guard` CC/MCP scheduled task
  (~/.claude/scheduled-tasks/ora-doctrine-integrity-guard/SKILL.md).

  Why retired: these two scripts implemented the legacy "ORA EOS Health" weekly report
  via a RAW Windows Task Scheduler entry (Register-ScheduledTask), which bypassed this
  system's documented dual-fleet scheduler doctrine (CC/MCP `claude-code-sessions` +
  LAMS/Cowork `local-agent-mode-sessions`; see memory/tech.md sec 3). The "ORA EOS Health"
  Windows task was confirmed NOT registered (Get-ScheduledTask returned nothing) at the
  time of replacement — the mechanism was already dead.

  What was preserved: the useful payload — running doctrine-integrity-probe.py and
  surfacing eos-telemetry-rollup.py's lane-compliance rollup — now runs daily under the
  doctrine-driven guard task above, which ALSO runs governor-drift-probe.py (previously
  unwired anywhere) and writes the shared _state/doctrine-status.json.

  eos-telemetry-rollup.py was NOT retired — it is reused verbatim by the new guard task
  at its original path (~/.claude/maintenance/eos-telemetry-rollup.py). Do not archive it.

  These two files are archived VERBATIM (content unmodified) — relocation only.
