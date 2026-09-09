---
name: ora-routine-pause-resume-2026-09-11
description: One-time resume: re-enable all 36 CC/MCP scheduled tasks paused 2026-09-07 per Gabriel's instruction, plus ora-checkout-merge-forward (registered 2026-09-09, disabled to match the standing pause rather than fire mid-pause). [MODEL: claude-sonnet-5 | set 2026-09-09]
---

This is the resume half of a bounded pause Gabriel requested 2026-09-07 ("pause all routines until Friday at 4:01 PM"). It fires once, then auto-disables itself.

NOTE (added 2026-09-09): `ora-checkout-merge-forward` was registered AFTER this pause began (OI-249 candidate a). It defaulted to `enabled: true` on creation and was immediately flipped back to `false` to match the standing pause rather than fire mid-pause on its own daily cadence — added to the list below as item 37 so it comes back online with everything else, rather than sitting silently paused forever with nothing pointing at it.

STEP 0 — before touching anything, call list_scheduled_tasks and confirm none of the 37 ids below have been separately retired in the meantime by reading C:\Users\Owner\.claude\maintenance\_state\retire-pending.json. If any id in the list below now appears in that file's "pending" array, SKIP re-enabling that one id only, note it in the summary, and proceed with the rest — do not silently re-enable a task whose retirement was ratified after this pause was set.

STEP 1 — for each of the following 37 task ids, call update_scheduled_task(taskId, enabled: true) — enabled ONLY, no other field (do not touch description/prompt/cron — re-enabling is not an observation, so do NOT bump any [MODEL:] checked/set date on these tasks). After every 6 calls, write a progress marker:
python C:\Users\Owner\.claude\maintenance\task-progress-marker.py write --task-id ora-routine-pause-resume-2026-09-11 --step <N> --of 37 --note "re-enabled through <last-task-id>"

Task ids (all currently enabled:false, paused 2026-09-07):
1. ora-master-workbook-ingest
2. ora-financial-code-integrity-sweep
3. ora-monthly-portfolio-briefing
4. ora-health-guard
5. ora-task-integrity-guard
6. ora-weekly-hygiene
7. ora-deal-sourcing-scan
8. ora-pm-ledger
9. ora-doctrine-integrity-guard
10. ora-open-sessions-board
11. ora-command-center-mirror-drift-check
12. ora-site-exposure-probe
13. ora-aaos-expire-leases
14. ora-aaos-publish-contracts
15. ora-model-release-watch
16. ora-calibration-snapshot
17. ora-entry-market-scan
18. ora-cc-schematic-refresh
19. ora-sofr-direct-prefetch
20. ora-broker-touch-cadence
21. ora-am-brief
22. ora-deal-command-board
23. ora-deal-aging-sla
24. ora-appsec-sweep
25. ora-tenant-hubspot-reconciliation
26. ora-cc-snapshot-refresh
27. ora-lease-snapshot-refresh
28. ora-psa-drift-watch
29. ora-claude-setup-audit
30. ora-acquisition-underwriting-eval-harness
31. ora-county-sales-monitor
32. ora-passed-deal-tracker
33. ora-memory-commit-sweep
34. ora-ar-feed-sweep
35. ora-pm-daily-crons
36. ora-pm-monthly-billing
37. ora-checkout-merge-forward

STEP 2 — call list_scheduled_tasks once more and confirm all 37 (minus any carved out in STEP 0) now show enabled:true. Paste that confirmation and a one-line summary (count re-enabled, any carve-outs with reason) into the completion notification. Do not email anyone — this is an internal fleet-state action, not a Gabriel-facing report; ggoldberg-only routing doesn't apply because nothing is being sent externally or by mail.

STEP 3 — this task then auto-disables (fireAt one-time semantics); no further action needed.