non_fleet_task_sweep -- retired, source already gone before this archive was made.

Found 2026-09-09 (ora-setup-audit quick pass): only the compiled __pycache__
(non_fleet_task_sweep.cpython-313.pyc, dated 2026-08-04) and a matching
non-fleet-task-sweep.log (also last written 2026-08-04) existed under
~/.claude/maintenance -- no non_fleet_task_sweep.py source file anywhere on
disk, not even in an _archive/ dir (checked). Nothing currently invokes it:
no scheduled task, hook, or settings.json reference. The 36-day-stale log
this produced was previously being misread as a "stopped writer" -- it never
stopped, its producer was deleted first (source removal predates Hard
Invariant 6's "archive, never delete" -- can't undo, only stop it from
re-tripping every future stale-writer sweep). Archived here rather than left
in place so future audits don't re-flag it. Do not resurrect without first
writing a real non_fleet_task_sweep.py -- these two files alone document
nothing about what the check was supposed to do beyond its name.
