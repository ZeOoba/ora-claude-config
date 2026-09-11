# Headless checks — burn-in and cutover runbook

Status as of 2026-09-10: **parallel burn-in, nothing retired.** Gabriel's ruling.
The in-fleet twins keep running. Do not retire anything until the exit criteria below are met.

## Why this file exists

Cutover is deliberately unfinished, and an unfinished cutover with no written finish
condition is how a system ends up permanently running two of everything — or worse, how
somebody retires the in-fleet twin early and discovers the headless copy never covered the
half they cared about. The exclusions in `run-check.py` are real: the headless
`integrity-guard` is a **subset** of `ora-task-integrity-guard`, not a replacement.

## What is running in parallel

| Headless (Windows Task Scheduler) | In-fleet twin (CC/MCP) | Overlap |
|---|---|---|
| `ORA Headless - integrity-guard` (daily 07:20) | `ora-task-integrity-guard` (`5 7 * * *`) | **Partial** — see exclusions |
| `ORA Headless - mirror-drift` (weekdays 10:55) | `ora-command-center-mirror-drift-check` (weekday 10:40) | Near-full — both key on `mirror-run-classify.ps1`'s verdict |
| `ORA Headless - stranded-spec` (daily 07:20) | (a step inside `ora-task-integrity-guard`) | Full for that step |
| `ORA Headless - freshness` (daily 07:50) | none — new capability | n/a |

### Exclusions that block a straight integrity-guard retirement

The headless `integrity-guard` does **NOT** do these, and they only exist in the in-fleet task:

1. **SKILL.md self-healing** — content-hash restore of a missing SKILL.md from a surviving
   canonical/mirror copy. Judgement work, deliberately left in-fleet.
2. **Registry-membership drift** — `registry-membership-probe.py` is excluded because it
   takes no flags and rewrites `session-context.md` + `fleet-roster.md` on every run
   (see that file's own header warning). Unattended rewriting of shared context is a hazard.
3. **Unbacked non-SKILL.md files, id collisions, incomplete STEP 0.5 writes** — all in-fleet.

**Therefore: `ora-task-integrity-guard` cannot be retired at all on current scope.** Burn-in
for that pair is about confirming the headless subset agrees where they overlap, not about
replacing it. Retiring it would silently drop 1–3 above.

## Exit criteria — all must hold before retiring any twin

1. **≥ 10 firing days** of both copies (weekday-only checks: 10 weekdays).
2. **Zero unexplained disagreements.** Compare the headless findings file against the
   in-fleet task's Notion row / email for the same day:
   `~/.claude/maintenance/_state/headless-findings/<check>-latest.json`
   A disagreement is only "explained" if you can name the cause in writing (different
   sampling time, a pause, a known exclusion). "Probably timing" is not an explanation.
3. **At least one real non-clean event** observed and correctly paged by the headless copy.
   A pair that has only ever agreed on `CLEAN` has not been tested — silence is what both
   look like when they are broken. If no natural failure occurs, force one (stub the
   classifier path, confirm it pages, revert).
4. **The headless copy's scope is a superset** of what you are retiring. For
   `integrity-guard` today it is not — see above.

## Retire order — differs by fleet, and getting it wrong resurrects the task

**CC/MCP (all three twins here are CC):**
1. `delete_scheduled_task(<id>)` **FIRST** — registry row only, leaves the folder.
2. **Then** archive the folder to `scheduled-tasks/_archive_<date>_retired/`.

Reversing this resurrects the task: `guard.ps1:157` enumerates on id + filePath **without
filtering `enabled`**, so an archived-but-still-registered folder gets restored daily.
(Proven 2026-08-09.)

**LAMS/Cowork:** archive first. **Never** use the Scheduled-sidebar delete/trash icon — it is
folder-destructive and can break a same-id task on the *other* fleet.

**Neither fleet:** never hand-edit registry JSON. Registration and retirement go through the
supervised MCP tools only (`register-scheduled-task` skill, v2.3+ single-writer rule — check
`_state/registry-membership.log` for concurrent activity first).

**PAUSE ≠ RETIRE.** If you only want to stop a twin temporarily, use
`update_scheduled_task(enabled:false)` and record the resume, the way the 2026-09-07 bounded
pause did with `ora-routine-pause-resume-2026-09-11`.

## Uninstalling the headless side instead

If the headless experiment is abandoned, the whole footprint is four Windows tasks and one
directory — nothing in either fleet registry is touched:

```
schtasks /Delete /TN "ORA Headless - integrity-guard" /F
schtasks /Delete /TN "ORA Headless - stranded-spec" /F
schtasks /Delete /TN "ORA Headless - mirror-drift" /F
schtasks /Delete /TN "ORA Headless - freshness" /F
```

Then remove `~/.claude/maintenance/headless/` and
`~/.claude/maintenance/_state/headless-findings/`. Nothing else depends on them.

## Open decision (2026-09-10)

The wrappers run their underlying deterministic scripts directly rather than
`claude -p`, because `claude -p` cannot authenticate on this machine (expired OAuth,
verified live — see `ora_headless_lib.py`'s header). If a genuine LLM-headless path is ever
wanted it needs a Desktop re-auth or a provisioned `ANTHROPIC_API_KEY`. Nothing here
depends on that decision.
