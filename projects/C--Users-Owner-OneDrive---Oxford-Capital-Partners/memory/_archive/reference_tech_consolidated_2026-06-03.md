---
name: Tech Stack & Reference Locations
description: Where things live — file paths, system configs, key integrations
type: reference
originSessionId: 7a2d65d8-0426-4732-9939-712f86b5976f
---
**Skills library (nominal user path):** `C:/Users/Owner/.claude/skills/` — contains a small local skill set (ic-memo-builder, playwright-skill, prompt-factory, redline-analyzer, webapp-testing, workflow-audit, + a few loose .md files). NOT where the `anthropic-skills:*` ORA skill library lives.

**Skills library (authoritative ORA — Cowork OS project-scoped, read by Claude Code):** `C:/Users/Owner/OneDrive - Oxford Capital Partners (1)/Cowork OS/.claude/skills/` — OneDrive-synced. **Git-tracked** (self-contained repo, remote `https://github.com/ZeOoba/ora-skills.git`, branch `main`, init'd 2026-04-16). As of 2026-04-28 contains 13 skills: acquisition-underwriting, cap-rate-snapshot, deal-screen, deploy-site, document-assembly, lease-abstraction-pipeline, lease-renewal-pipeline, market-comp-analyzer, monthly-close, psa-reconciliation, tenant-email, cowork-settings, README. **Source of truth.**

**Skills library (AppData runtime cache — Claude Code agent mode):** `C:/Users/Owner/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/<outer-UUID>/<inner-UUID>/skills/`. Contains all 41 `anthropic-skills:*` entries. UUIDs as of 2026-04-16: outer `583f08bc-0123-4111-8158-8fe3d927e350` (created 2026-02-21, stable ~2 months), inner `a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3` (session-coupled, may rotate). Check drift via `bash ~/.claude/check-uuid-drift.sh` — baseline at `~/.claude/uuid-baseline.json`.

**Cowork Desktop (claude.ai Electron wrapper) skill source — DIFFERENT from above:** Runtime path inside sandbox is `/sessions/<session-name>/mnt/.claude/skills/` — cloud-hosted, not on local disk. Local AppData edits do NOT propagate to Cowork Desktop. Discovered during 2026-04-16 smoke test when Cowork Desktop showed pre-hardening skill versions (document-assembly v1.0, lease-abstraction-pipeline v1.1) despite correct local AppData install. To update Cowork Desktop, re-upload SKILL.md files via claude.ai's skills UI.

**Skill audit/install convention:** Dual-write Cowork OS + AppData. Backups at `C:/Users/Owner/.claude/backups/skill-audit-YYYYMMDD-HHMMSS/` + `cowork-skills-YYYYMMDD-HHMMSS/` + per-file `.backup-<stamp>` sidecars. Gabriel's rule: do NOT auto-create Cowork OS skill directories that don't already exist — that's a promote decision, separate from an install pass (Priority 2 explicitly authorizes creation when promoting).
**Scheduled tasks (canonical registry — re-verified 2026-06-01):** `C:/Users/Owner/AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/local-agent-mode-sessions/a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3/583f08bc-0123-4111-8158-8fe3d927e350/scheduled-tasks.json` — **43 tasks (40 enabled, 3 disabled)**, runs landing daily (last write 2026-05-31 22:15). The 3 disabled: `hard-delete-zapier-trial-reminder`, `ora-quarterly-cron-restore-20260521`, `ora-connector-recovery-ratification-check`. This is the registry the Cowork firing-runtime actually executes.
  - **Split-brain RESOLVED 2026-05-31, re-confirmed 2026-06-01:** `claude-code-sessions/.../scheduled-tasks.json` is now EMPTIED (`"scheduledTasks": []`, only leftover `recordedSkips` for ora-email-queue-pm) — NOT the old "2-task fragment". The `scheduled-tasks` MCP reads this empty file, so `list_scheduled_tasks` correctly returns **0** (verified live 2026-06-01). The legacy folder `C:/Users/Owner/.claude/scheduled-tasks/` was archived.
  - **The MCP CANNOT be re-pointed by config** — its path is product-determined (Claude Code → `claude-code-sessions/…`; Cowork firing-runtime → `local-agent-mode-sessions/…`; same session UUIDs, different product folder). Forcing it (junction/copy) would re-introduce the double-execution split-brain. DO NOT do this. **Read fleet health from the LAMS registry directly or the daily `ora-cc-implementation-verifier` email (07:45 ET) — NOT the MCP's 0.**
  - **2026-06-02:** Added task **`ora-notion-daily-digest`** (cron `0 17 * * *` = 17:00 ET) — end-of-day digest of everything created/edited in Notion that day (Deal Pipeline / Tenants / Knowledge Base / Ops Hub / catch-all), HTML email to ggoldberg+egoldberg. SKILL.md at `…\Documents\Claude\Scheduled\ora-notion-daily-digest\SKILL.md`; send path send-via-outlook.ps1 → composio-ora fallback. Registry edited DIRECTLY (the `scheduled-tasks` MCP writes the wrong/empty registry, so do NOT use it to add tasks). Live registry actually held **42** tasks before this add (the "43" verified 2026-06-01 was already slightly stale), now 43. Registry backup: `scheduled-tasks.json.bak-20260602-notion-digest`.
  - **2026-06-02:** Added task **`ora-dashboard-refresh`** (cron `0 7,13 * * *` = 07:00 & 13:00 ET) — refreshes the ORA Command Center web dashboard: runs `ora-dashboard/extract-all.ps1` (Excel COM → data JSONs), re-pulls Notion pipeline + HubSpot (E. Fulton filtered), redeploys via `npx wrangler pages deploy` (deploy step auto-skips until Cloudflare login is configured). SKILL.md at `…\Documents\Claude\Scheduled\ora-dashboard-refresh\SKILL.md`. Now **44 tasks**. Backup: `scheduled-tasks.json.bak-20260602-dashrefresh`. See [[project_active]] item 5.
**Global CLAUDE.md:** `C:/Users/Owner/.claude/CLAUDE.md`
**Setup reference:** `C:/Users/Owner/.claude/ORA_SetupReference.md`
**Global settings:** `C:/Users/Owner/.claude/settings.json`
**Project settings:** `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-/settings.json`
**Memory:** `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-/memory/`
**ORA root (canonical):** `C:/Users/Owner/OneDrive - Oxford Capital Partners (1)/ORA/` (6 project folders + Briefs + _reference)
**ORA archive:** `C:/Users/Owner/ORA_pre_consolidation/` (pre-merge snapshot from 2026-04-09, safe to delete)

**oxfordra.net canonical repo (verified 2026-05-31):** `C:/Users/Owner/website-canonical/` — git, remote `https://github.com/ZeOoba/Website.git`. This is the `OXFORDRA_REPO` env value. (The old `Cowork OS/oxford-site/` path is GONE.)
**oxfordra.net deploy copy:** `C:/Users/Owner/oxford-site/` (clean, no git)
**Netlify Site ID:** 95ac0a0f-a84d-4400-b919-b8d7a8526646

**MCP Connectors active:**
- Notion (c5f4869f) — knowledge base, ops hub, deal tracking
- HubSpot (a3e380ce) — CRM, lease pipeline, tenant tracking
- Microsoft/Outlook (c0ea3c01) — email, calendar, SharePoint
- QuickBooks (52fa80c0) — Intuit QBO REST API. **NOT USABLE for ORA** (ORA is QB Desktop). No OAuth re-auth will fix this. See `feedback_qb_desktop.md`. Future bridge: CData ODBC/JDBC → custom MCP (not yet built).
- Netlify (a66aaa4a) — site deploys
- PDF tools — read/display PDFs
- Desktop Commander — file ops
- Claude Preview — browser preview
- Apify — web scraping

**composio-ora MCP (Claude Desktop local server, fixed + scoped 2026-05-28):** `npx mcp-remote` bridge to the Composio server `82451fc0-e919-4971-9603-228bee9a344d` (name `claude-desktop-connector`). Config in `AppData/Roaming/Claude/claude_desktop_config.json`; working snippet backed up at `~/.claude/backups/composio-ora-working-config.json`. API key `ak_kopREDACTED` (in the config `env` block).
- **Auth = `x-api-key` header ONLY** (Bearer → 401; OAuth browser sign-in is blocked at the Composio org level for ggoldberg — `"contact your organization admin"`, do NOT retry OAuth). URL must include the `/mcp` suffix (bare URL 307-redirects).
- **Scoped to Outlook ACTION tools only (18), down from 733.** Dropped Notion + HubSpot toolkits — they fully duplicate the native Notion (c5f4869f) and HubSpot (a3e380ce) connectors. Kept Outlook because the native Microsoft connector (c0ea3c01) is **read/search only** — Composio adds the writes: send/reply/draft/forward email, add attachment, move msg, create/update/delete calendar event, accept/decline invite, create/update contact.
- **Scoping lives server-side** via Composio API: `PATCH https://backend.composio.dev/api/v3/mcp/{id}` (note: `/mcp/{id}`, NOT `/mcp/servers/{id}` which 404s; list is at `/mcp/servers`) with body `{"toolkits":[...],"allowed_tools":[...]}`. Header `x-api-key`. Server-side config is immune to Desktop file-clobbering.
- **GOTCHA — tool slugs:** the catalog `/api/v3/tools?toolkit_slug=outlook` returns double-prefixed `slug`s (`OUTLOOK_OUTLOOK_SEND_EMAIL`) that the LIVE MCP does NOT recognize. The real live tool names are single-prefix (`OUTLOOK_SEND_EMAIL`). To get true names, expose the full toolkit (`allowed_tools:[]`) and read `tools/list`.
- **GOTCHA — Windows `&` in URL breaks the spawn (THE bug that kept it failing):** Claude Desktop on Windows spawns `npx` through `cmd.exe`, which splits the command at `&`. A URL like `...?include_composio_helper_actions=true&user_id=ggoldberg` gets truncated at the `&`, so `mcp-remote` loses `user_id` AND every arg after it (incl. `--header`), then falls back to (failing) OAuth → "Server disconnected / Could not attach." FIX: use a SINGLE query param so there's no `&` — drop `include_composio_helper_actions=true`, keep `?user_id=ggoldberg`. Also INLINE the API key in `--header x-api-key:ak_...` rather than `${COMPOSIO_API_KEY}` (cmd doesn't expand `${}`; mcp-remote's own substitution works but inlining is bulletproof). Symptom in `AppData/Roaming/Claude/logs/mcp-server-composio-ora.log`: `'user_id' is not recognized as an internal or external command` + `EADDRINUSE`.
- **GOTCHA — Claude Desktop clobbers `claude_desktop_config.json`:** it rewrites the file from its in-memory copy on lifecycle events (esp. after opening the Local MCP servers settings UI), reverting manual edits. To make an edit stick: FULLY quit Desktop (tray → Exit), THEN edit the file, THEN relaunch (Desktop loads the file fresh at startup). Editing while it runs gets overwritten.
- If "Server disconnected": check for a stale hung `mcp-remote` node process holding the callback-port lock in `~/.mcp-auth/mcp-remote-*/` and kill it.

**PM Platforms (no MCP connector yet):**
- Yardi → MD/Baltimore portfolio
- AppFolio → Columbus OH
- Rent Manager → Indianapolis + Kansas City

**Rube MCP (d6315173) — SHUT DOWN (EOL 2026-05-15; removed from all configs 2026-05-31):**
- Fully retired. **Composio** (`composio-ora`, server `82451fc0`) is the sole automation/connector bridge for Outlook writes; native Notion/HubSpot/Netlify MCPs cover the rest. Do NOT reference or route to Rube anywhere — allowlists and CLAUDE.md scrubbed 2026-05-31.
- Recipe archive (historical only): `ORA/Migrations/2026-04-15_Rube_Export/rube-export-2026-04-15.json`

**Notion Database IDs (archived 2026-04-15, still valid):**
- Deal Sourcing Log: `9a6ae21985a34621899cc757fd062f8b`
- Acquisition Pipeline Tracker: `bcfe4a037e614ac1a0bbc44174fa138b`
- Broker Relationships: `48e43778b1f24b168f3c0bf18f8642e9`
- Tenant Database: `b12f4cfda9954755834164​35ae8173b4`
- Property Register: `19a61fc921ed42d7a0dbaa730d9a9683`
- CapEx & Maintenance Log: `5dfcc3ad532e4e5fbf8d512e2b69e317`
- Operations Hub (parent page): `32b6ecd89e5981f2b329df3fd0e25062`

**Zapier:** Out of space / NOT used (per operating rules). Integrations run via native Notion/HubSpot/Netlify MCPs + Composio for Outlook writes. **KEEP CONNECTED — do NOT remove in cleanup passes (verified 2026-06-02).** "Out of space" = capacity-capped, not retired; it's a tool Gabriel returns to when account space frees (cross-platform glue: QB→HubSpot, email→Notion). No live automation depends on it (LAMS registry checked), so removal is harmless *but* forces an unnecessary reconnect/re-auth later.
**Connectors removed 2026-06-02:** Microsoft Learn (claude.ai connector — use ⋮ → Remove, not Disconnect, which fails server-side), Google Drive (superseded by ms365/SharePoint), stray `searchapi` HTTP MCP (was in `.claude.json` C:/WINDOWS/system32 project). Already-gone earlier: Rube, QBO, Adobe, Gmail, Google Calendar.
**Working directory:** `C:/Users/Owner/OneDrive - Oxford Capital Partners (1)/`
**Deals folder:** `C:/Users/Owner/OneDrive - Oxford Capital Partners (1)/Cowork OS/`
