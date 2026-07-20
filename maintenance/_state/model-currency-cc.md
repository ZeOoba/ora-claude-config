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
