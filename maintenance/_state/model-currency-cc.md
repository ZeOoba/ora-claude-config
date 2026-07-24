# CC/MCP Scheduled-Task Model-Currency Log

Append-only. Written by ora-task-integrity-guard STEP 2.5 (informational; never alarms on its own).
Classification key: CURRENT = tag matches standard · STALE = tag present but mismatched · UNTAGGED = no tag · UNVERIFIABLE = tag literally reads UNVERIFIABLE (expected baseline for this fleet per 2026-07-08 finding; not fixable via recreate).

2026-07-09 — 10 tasks: 8 MODEL-UNVERIFIABLE, 2 MODEL-UNTAGGED, 0 MODEL-STALE, 0 MODEL-CURRENT, standard=claude-sonnet-5
2026-07-10 — 14 tasks: 11 MODEL-UNVERIFIABLE, 3 MODEL-UNTAGGED, 0 MODEL-STALE, 0 MODEL-CURRENT, standard=claude-sonnet-5
2026-07-11 — 18 tasks: 12 MODEL-UNVERIFIABLE, 6 MODEL-UNTAGGED, 0 MODEL-CURRENT, 0 MODEL-STALE, standard=claude-sonnet-5
2026-07-12 — 18 tasks: 12 MODEL-UNVERIFIABLE, 6 MODEL-UNTAGGED, 0 MODEL-CURRENT, 0 MODEL-STALE, standard=claude-sonnet-5
2026-07-13 — 19 tasks: 18 MODEL-UNVERIFIABLE, 1 MODEL-CURRENT (ora-cc-schematic-refresh=claude-sonnet-5), 0 MODEL-STALE, 0 MODEL-UNTAGGED, standard=claude-sonnet-5
2026-07-14 — 20 tasks: 18 MODEL-UNVERIFIABLE, 1 MODEL-CURRENT (ora-cc-schematic-refresh=claude-sonnet-5), 0 MODEL-STALE, 1 MODEL-UNTAGGED (canary-model-check-temp, disabled one-time), standard=claude-sonnet-5
2026-07-15 — 21 tasks: 19 MODEL-UNVERIFIABLE, 1 MODEL-CURRENT (ora-cc-schematic-refresh=claude-sonnet-5), 0 MODEL-STALE, 1 MODEL-UNTAGGED (canary-model-check-temp, disabled one-time), standard=claude-sonnet-5
2026-07-17 — 24 tasks: 19 MODEL-UNVERIFIABLE, 2 MODEL-CURRENT (ora-cc-schematic-refresh + ora-am-brief = claude-sonnet-5), 0 MODEL-STALE, 3 MODEL-UNTAGGED (ora-setup-review-closeout-recheck enabled one-time; heartbeat-beacon-recovery-check + heartbeat-check-backup-verify disabled one-time), standard=claude-sonnet-5
2026-07-19 — 23 tasks: 19 MODEL-UNVERIFIABLE, 2 MODEL-CURRENT (ora-cc-schematic-refresh + ora-am-brief = claude-sonnet-5), 0 MODEL-STALE, 2 MODEL-UNTAGGED (ora-deal-command-board + ora-deal-aging-sla), standard=claude-sonnet-5
2026-07-21 — 27 tasks: CURRENT=2, STALE=0, UNTAGGED=5, UNVERIFIABLE=20, standard=claude-sonnet-5
2026-07-22 — 29 tasks: CURRENT=2, STALE=0, UNTAGGED=7, UNVERIFIABLE=20, standard=claude-sonnet-5
2026-07-24 — 28 tasks: MODEL-CURRENT 2, MODEL-STALE 1 (ora-site-exposure-probe: claude-opus-4-8), MODEL-UNTAGGED 4 (check-dirty-files-session-pr, ora-appsec-sweep, ora-tenant-hubspot-reconciliation, ora-override-sweep-dryrun-check), MODEL-UNVERIFIABLE 21, standard=claude-sonnet-5

## CLASSIFICATION KEY REVISED 2026-07-24 (ora-task-integrity-guard v1.7)
The original key above (CURRENT = tag matches standard / STALE = tag present but mismatched) was the
LAMS match-the-standard test mis-applied to this fleet. CC/MCP is server-pinned and NOT settable, so an
id mismatch is not actionable and must not be graded "stale" (reference_scheduled_task_model_standard.md,
"CC/MCP fleet — model is NOT settable, but IS observable": the CC/MCP check is tag-presence +
observation-freshness). Prior dated lines are left byte-intact per append-only; read every pre-07-24
"STALE" / "CURRENT" count under the OLD key. New key, effective 2026-07-24:
  OBSERVED = real model id, checked/set on or after reference_model_release_checklist.md's
             "Current lineup as of <date>" line — the BEST state; a non-Sonnet id here is the
             documented #48976 server-pin outcome, not a defect
  OBSERVATION-STALE = real model id, but checked/set predates that lineup date -> re-observe, never recreate
  UNVERIFIABLE = tag literally reads UNVERIFIABLE (expected baseline; not fixable via recreate)
  UNTAGGED = no tag at all (the only real coverage gap)

2026-07-24 (CORRECTED, supersedes the 2026-07-24 line above) — 28 tasks: MODEL-OBSERVED 3 (ora-am-brief=claude-sonnet-5 set 07-16; ora-cc-schematic-refresh=claude-sonnet-5 checked 07-16; ora-site-exposure-probe=claude-opus-4-8 checked 07-22 via live-run transcript canary — reclassified from MODEL-STALE, no action), MODEL-OBSERVATION-STALE 0, MODEL-UNVERIFIABLE 21, MODEL-UNTAGGED 4 (check-dirty-files-session-pr [disabled], ora-appsec-sweep [intentional Fable pin per CLAUDE.md security floor — tag it, do not flip], ora-tenant-hubspot-reconciliation, ora-override-sweep-dryrun-check [one-time]), lineup-anchor=2026-07-10, LAMS standard (not applied to this fleet)=claude-sonnet-5

2026-07-24 (2nd correction, same day) — ora-appsec-sweep moved MODEL-UNTAGGED -> MODEL-OBSERVED via transcript canary on its 2026-07-22 17:38Z run (session 4b66d74c): main loop = claude-opus-4-8 x163 + claude-sonnet-5 x86, ZERO claude-fable-5. Its frontmatter `model: fable` is INERT on CC/MCP (first direct evidence that frontmatter model: is not read for this fleet). Revised 07-24 counts: MODEL-OBSERVED 4, MODEL-OBSERVATION-STALE 0, MODEL-UNVERIFIABLE 21, MODEL-UNTAGGED 3 (check-dirty-files-session-pr [disabled], ora-tenant-hubspot-reconciliation, ora-override-sweep-dryrun-check [one-time]). NOTE: prior 07-22/07-24 lines called appsec an "intentional Fable pin" — that was a conflation of declared intent with actual firing model; see reference_scheduled_task_model_standard.md CORRECTION 2026-07-24. GOVERNANCE GAP (Gabriel's call): this security-gate task runs below CLAUDE.md's never-below-Fable floor, no in-registry fix exists.

2026-07-24 (3rd correction, same day — precision fix) — ora-appsec-sweep's tag narrowed to [MODEL: claude-opus-4-8]. The earlier "claude-opus-4-8 + claude-sonnet-5" reading aggregated the WHOLE session 4b66d74c; that session began as the scheduled fire (17:38:32Z, all 163 msgs opus) and later went INTERACTIVE when Gabriel ran /model at 19:54:12Z (the 86 sonnet msgs). Only the pre-first-human-turn portion is fleet evidence. CANARY METHOD RULE: always cut the transcript at the first human-authored turn before counting models. Classification unchanged (MODEL-OBSERVED); counts unchanged (OBSERVED 4 / OBSERVATION-STALE 0 / UNVERIFIABLE 21 / UNTAGGED 3).

2026-07-24 (13:05 ET catch-up run) — 30 tasks: MODEL-OBSERVED 4 (ora-am-brief=claude-sonnet-5 set 07-16; ora-cc-schematic-refresh=claude-sonnet-5 checked 07-16; ora-site-exposure-probe=claude-opus-4-8 checked 07-22; ora-appsec-sweep=claude-opus-4-8 checked 07-24), MODEL-OBSERVATION-STALE 1 (ora-511-industrial-fallout-check — tag [MODEL: claude-sonnet-5] carries NO checked/set date, so observation freshness is unassertable; re-observe at next supervised touch, never a recreate cycle), MODEL-UNVERIFIABLE 21, MODEL-UNTAGGED 4 (check-dirty-files-session-pr [disabled/paused], ora-tenant-hubspot-reconciliation, ora-override-sweep-dryrun-check [one-time 07-26], check-shared-checkout-settled-140pm [one-time 07-24, newly registered today]), lineup-anchor=2026-07-10, LAMS standard (NOT applied to this fleet)=claude-sonnet-5. Task count 28 -> 30 since the 12:22 ET run: two one-time tasks registered by other sessions today (ora-511-industrial-fallout-check, check-shared-checkout-settled-140pm) — both counted here, neither an alarm.

2026-07-24 (SUPERSEDES the 13:05 line above — new scope doctrine applied) — 26 in-scope tasks: MODEL-OBSERVED 4, MODEL-OBSERVATION-STALE 0, MODEL-UNVERIFIABLE 22, MODEL-UNTAGGED 0; 4 exempt (3 one-time / 1 paused), lineup-anchor=2026-07-10, LAMS standard (NOT applied to this fleet)=claude-sonnet-5. REAL COVERAGE GAPS: 0. Changes: (a) ora-tenant-hubspot-reconciliation tagged [UNVERIFIABLE | checked 2026-07-24] — it was the ONLY genuinely in-scope untagged task; (b) ora-override-sweep-dryrun-check, check-shared-checkout-settled-140pm, ora-511-industrial-fallout-check (one-time) and check-dirty-files-session-pr (disabled) reclassified UNTAGGED -> MODEL-N/A per reference_scheduled_task_model_standard.md "Tag scope & required fields" (ratified 2026-07-24); (c) ora-511's undated tag now formally OBSERVATION-STALE-class but moot, since one-time CC/MCP tasks are exempt. CLASSIFIER HARDENING same day: take the LAST bracketed MODEL match in a description, never the first — this guard's own v1.8 changelog quoted an example tag and a first-match read graded the guard itself UNDATED while its real trailing tag was intact.
