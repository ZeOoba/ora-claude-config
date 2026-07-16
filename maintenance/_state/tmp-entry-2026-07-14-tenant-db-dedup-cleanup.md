## 2026-07-14 — Retired stale ora-tenant-db-dedup-remediation LAMS one-time task (Cowork-side cleanup, closes 2026-07-12 loop)

Retired the `ora-tenant-db-dedup-remediation` one-time scheduled task via the supervised
`delete_scheduled_task` MCP tool (never the Scheduled-sidebar trash icon, which is
folder-destructive and can break a same-id task on the other fleet). It was created
2026-07-12 15:38 ET as a same-day hedge — fire once at 2026-07-13 08:00 ET to run the Notion
Tenant DB dedup remediation, in case an earlier Notion API quota block ("used all of your
plan's free data source queries") was still live at hedge time.

The hedge was never needed: an interactive session executed the full remediation live later
that same evening, 2026-07-12, archiving 124 of 296 rows across categories A/B/D — hours
before the task's scheduled slot. The task never fired (confirmed enabled:false, no
lastRunAt) and sat expired and orphaned. A later 2026-07-12 session already flagged it here
as a dead entry needing "supervised Cowork-side cleanup" — that cleanup did not happen until
now, 2 days later. This entry closes that loop: the underlying remediation was already
confirmed executed, not missed.

Per Hard Invariant 6, archived rather than deleted: moved the task folder from
`OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-tenant-db-dedup-remediation\`
to a new `_archive_2026-07-14_stale-cleanup\` folder (matching the existing
`_archive_2026-06-11_orphans` convention). `efulton-post-legalhold-consolidation` was
deliberately left untouched in this pass — separate, sensitive, needs Gabriel's explicit
sign-off first.

