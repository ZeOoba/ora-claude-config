---
name: ora-notion-retention
description: Daily Notion retention sweep — trashes stale auto-generated report pages to prevent UI slowdown
---

Execute the ora-notion-retention skill defined at:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Cowork OS\Claude\Scheduled\ora-notion-retention\SKILL.md

Read that file in full, then follow its 7-step EXECUTION SEQUENCE exactly:

1. COMPUTE CUTOFFS — today minus retention_days for each title prefix in the retention table.
2. SCAN + MATCH — notion-search each prefix, parse date from title, queue pages older than cutoff. Skip pages tagged ✅ Resolved / ✅ Clean / [KEEP] / [PIN] / [ARCHIVE]. Skip pages edited in last 48 hours.
3. DETECT SAME-DAY DUPLICATES — keep newest, queue rest.
4. SAFETY GATE — if queue > 50 items: STOP, create "Retention Sweep — Manual Review Required — {date}" alert page, email ggoldberg@oxfordra.net, do NOT auto-trash. If queue = 0: exit silently.
5. EXECUTE TRASH — create staging page `🗑️ Retention Sweep — {YYYY-MM-DD}` under Oxford Real Assets — Operations Hub (parent 32b6ecd89e5981f2b329df3fd0e25062), move queued pages underneath via notion-move-pages (max 100/batch), then trash the staging page.
6. LOG — append to outputs/retention-log.md: `{YYYY-MM-DD} | swept {count} pages | {prefix}:{n}, ...`
7. NOTIFICATION — only if sweep > 20 pages, email ggoldberg@oxfordra.net with per-prefix breakdown.

PRESERVE LIST (never trash): Quarterly Review, Monthly Close, HubSpot CRM Audit, Covenant Watch, IC Memo, Deal Sourcing Log, pages tagged `keep` or `pinned`, pages referenced from Cowork OS Master Index (32b6ecd89e5981a9a566e3ed1b1c9a9e).

Tools required: notion-search, notion-fetch, notion-create-pages, notion-move-pages, notion-update-page, notion-update-data-source.

On MCP failure: exit gracefully, retry tomorrow. Do not page overnight.