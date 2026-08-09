---
name: reference_settings_json_enabledplugins_skilloverrides_attribution_2026-08
description: "settings.json's enabledPlugins (14→7 keys) and skillOverrides (44→17 entries) collapses are fully git-attributed, contra the 2026-08-09 schematic refresh's \"attribution not investigated\" note"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c7e2e2fe-cbb2-4612-a29c-664b2a5ec9bc
  modified: 2026-08-09T13:44:59.296Z
---

The 2026-08-09 `ora-cc-schematic-refresh` run found `enabledPlugins` collapsed from 14 keys/12 true to 7 keys/7 true, and `skillOverrides` fell 44 → 17 entries, and reported both as **"Attribution not investigated — flagged as an open question rather than guessed at."** They were not actually unknown — `settings.json` is git-tracked at `C:\Users\Owner\.claude` (backed to `ZeOoba/ora-claude-config`), and `git log -p -- settings.json` answers both in two prior commits, both Gabriel-authored:

**`a0e95bf`** (2026-07-28 22:28:14 -0400, "config: dedupe skills, remove dead plugins; log usage-audit follow-ups") — dropped `firecrawl@claude-plugins-official`, `frontend-design@claude-plugins-official`, `coderabbit@claude-plugins-official`, `claude-api@anthropic-agent-skills` from `enabledPlugins`, plus 7 orphaned firecrawl/claude-api `skillOverrides` entries. Commit message: "drop 7 orphaned firecrawl/claude-api skillOverrides left dead after Gabriel uninstalled firecrawl via the app UI (coderabbit was uninstalled the same way)."

**`165fff3`** (2026-08-05 17:28:02 -0400, "chore(env): purge inert skillOverrides, fix HubSpot doctrine line, teach probe about GUARD_CHAIN") — dropped `andrej-karpathy-skills@karpathy-skills`, `document-skills@anthropic-agent-skills`, `obsidian@obsidian-skills` from `enabledPlugins`, and removed 38 more inert `skillOverrides` entries (55→17 at that point; a later independent count landed on 44→17, the two commits' deltas overlap rather than being purely additive — the numbers are still fully explained, just not from a single commit). Root cause given in the commit body: the shipped resolver (`BOe()`) returns "on" for any plugin-sourced skill before the override map is consulted, so every plugin-keyed override entry was inert by construction — confirmed empirically, all 19 keys marked "off" were live in a session started after settings.json was last written. The commit also explicitly notes it is preserving "another session's uncommitted removal of andrej-karpathy-skills from skillOverrides + enabledPlugins... same direction of work."

**Net: both structural changes are deliberate, Gabriel-ratified-in-turn, and root-caused in the commit bodies — not an unattributed drift.** The gap was procedural: the schematic-refresh producer diffs `settings.json` against its own prior snapshot but never checks `git log` before reporting a change as unattributed. Fixed 2026-08-09: `ora-cc-schematic-refresh/SKILL.md` now instructs a `git log -p -- settings.json` check before calling any structural settings.json change unattributed. See [[reference_config_write_guard_bash_read_shaped_false_positive]] for a related settings.json/hooks investigation from the same period.
