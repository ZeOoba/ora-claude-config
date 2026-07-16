---
name: reference_composio_ora_config_historical
description: "Archived 2026-07-12 (monthly memory consolidation) from tech.md — detailed composio-ora config/gotchas. Composio-Outlook was REMOVED 2026-06-11 and has no live config; this block is retained only as historical troubleshooting record in case a future Outlook-write connector needs analogous config. Do NOT treat any content below as current — composio-ora does not exist."
metadata:
  node_type: memory
  type: archive
---

# composio-ora (Outlook writes) — config + gotchas [ARCHIVED, connector removed 2026-06-11]

Moved verbatim from `tech.md` §4 during the 2026-07-12 monthly consolidation pass — content was accurate as of the connector's active period but stale/dead weight in the live tech reference now that Composio was removed 2026-06-11 (per CLAUDE.md: "never reference it"). Kept here only for historical troubleshooting lineage.

- `npx mcp-remote` bridge; config in `AppData/Roaming/Claude/claude_desktop_config.json`; working snippet backed up at `~/.claude/backups/composio-ora-working-config.json`.
- **Auth = `x-api-key` header ONLY** (Bearer→401; OAuth blocked at Composio org level — do NOT retry). URL must include `/mcp` suffix.
- **Scoped to 18 Outlook ACTION tools** (send/reply/draft/forward, attachments, calendar create/update/delete, accept/decline, contacts) — the native MS connector is read-only; Composio adds the writes. Notion/HubSpot toolkits dropped (native connectors cover them). Scoping is server-side: `PATCH https://backend.composio.dev/api/v3/mcp/{id}` with `x-api-key`.
- **Live tool names are single-prefix** (`OUTLOOK_SEND_EMAIL`), not the catalog's double-prefixed slugs.
- **Windows `&`-in-URL bug:** cmd.exe splits the npx command at `&`, dropping args → OAuth fallback → "Server disconnected." FIX: single query param (`?user_id=ggoldberg`, drop `include_composio_helper_actions`), inline the api-key in `--header x-api-key:ak_…`.
- **Desktop clobbers `claude_desktop_config.json`** on lifecycle events — fully quit Desktop, edit, relaunch. If "Server disconnected," kill stale `mcp-remote` node procs holding `~/.mcp-auth/` port locks.
