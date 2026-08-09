---
name: reference-cron-retime-rearms-executed-slot
description: "Retiming a periodic scheduled task mid-period re-arms the CURRENT period's slot even when that slot already ran to completion, producing a duplicate fire. Confirmed 2026-08-09 on ora-entry-market-scan (monthly, cron \"45 11 1-7 * 2\"): the 08-04 slot ran to completion 11:36 local, SKILL.md v1.4 retimed 11:00->11:45 ET on 08-09, and the scheduler immediately re-fired the 08-04 slot on a day that is NOT a valid fire under either AND or OR dom/dow semantics. Distinct from the catch-up burst (app-closed) and from global_limit throttle-skips."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e047be2a-a877-4a51-8453-0636016207db
  modified: 2026-08-09T14:19:06.550Z
---

**Symptom.** A periodic task fires on a date its own cron cannot produce, shortly after its cron
expression was edited. `lastScheduledFor` still points at the ALREADY-COMPLETED prior slot while
`lastRunAt` jumps to now.

**Confirmed instance (2026-08-09, `ora-entry-market-scan`).** Registry entry read directly:

```
"cronExpression": "45 11 1-7 * 2",
"lastScheduledFor": "2026-08-04T15:45:00.000Z",
"lastRunAt":        "2026-08-09T14:06:04.418Z"
```

The 2026-08-04 slot had run to completion that day (`outputs/2026-08-04_entry-scan-{results,summary}.json`,
written 11:36 local). SKILL.md **v1.4 retimed the task 11:00 → 11:45 ET on 2026-08-09**; the scheduler
then fired the 08-04 slot again. 2026-08-09 was a **Sunday** — not day 1-7, not a Tuesday — so it is
not a valid fire under compound-cron AND semantics *or* under OR semantics
(see [[reference_fleet_status_compound_cron_and_semantics]]). The re-arm, not the cron, produced it.

**Why this is its own failure mode.** Three superficially similar things are all different:

| Mechanism | Trigger | Tell |
|---|---|---|
| **Retime re-arm** (this file) | cron edited mid-period on a slot that already ran | `lastScheduledFor` = an already-completed slot; fire date invalid for the cron |
| [[reference_fleet_throttle_skip_catchup_burst]] | Desktop app closed past several fire times | many tasks fire within seconds of app reopen; `recordedSkips` `global_limit` |
| [[reference_scheduler_lastrunat_stamped_at_dispatch]] | phantom dispatch | `lastRunAt` advances with no work product at all |

**How to apply.** Before retiming a periodic (weekly/monthly) task, check whether the current
period's slot has already executed — look for this run's output artifact, not just `lastRunAt`
(which is stamped at dispatch). If it has, expect a duplicate fire and either accept it or retime
at the start of the next period instead. Worth a pre-flight line in [[register-scheduled-task]],
whose retiming procedure does not currently mention it.

**What a duplicated run should actually do.** Do NOT blindly re-execute an expensive sweep. On the
2026-08-09 instance the correct output was a *reduced-scope* run: honour the mandatory doctrine
check (which caught a real delta — Louisville KY ratified as ORA's 10th canonical cluster 2026-08-05,
one day after the prior run, invalidating that task's off-taxonomy handling), apply the delta, and
declare in the output exactly which steps were skipped and why. A re-sweep would have restated
5-day-old listings and re-asked Gabriel questions the prior run had already raised.
See [[feedback_verified_null_vs_inferred_null]] — "not re-checked" must never be written as
"confirmed unchanged".
