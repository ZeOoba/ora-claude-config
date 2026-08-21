---
name: reference_settings_json_enabledplugins_skilloverrides_attribution_2026-08
description: "settings.json's enabledPlugins (14→7 keys) and skillOverrides (44→17 entries) collapses are fully git-attributed, contra the 2026-08-09 schematic refresh's \"attribution not investigated\" note"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c7e2e2fe-cbb2-4612-a29c-664b2a5ec9bc
  modified: 2026-08-14T19:07:49.940Z
---

The 2026-08-09 `ora-cc-schematic-refresh` run found `enabledPlugins` collapsed from 14 keys/12 true to 7 keys/7 true, and `skillOverrides` fell 44 → 17 entries, and reported both as **"Attribution not investigated — flagged as an open question rather than guessed at."** They were not actually unknown — `settings.json` is git-tracked at `C:\Users\Owner\.claude` (backed to `ZeOoba/ora-claude-config`), and `git log -p -- settings.json` answers both in two prior commits, both Gabriel-authored:

**`a0e95bf`** (2026-07-28 22:28:14 -0400, "config: dedupe skills, remove dead plugins; log usage-audit follow-ups") — dropped `firecrawl@claude-plugins-official`, `frontend-design@claude-plugins-official`, `coderabbit@claude-plugins-official`, `claude-api@anthropic-agent-skills` from `enabledPlugins`, plus 7 orphaned firecrawl/claude-api `skillOverrides` entries. Commit message: "drop 7 orphaned firecrawl/claude-api skillOverrides left dead after Gabriel uninstalled firecrawl via the app UI (coderabbit was uninstalled the same way)."

**`165fff3`** (2026-08-05 17:28:02 -0400, "chore(env): purge inert skillOverrides, fix HubSpot doctrine line, teach probe about GUARD_CHAIN") — dropped `andrej-karpathy-skills@karpathy-skills`, `document-skills@anthropic-agent-skills`, `obsidian@obsidian-skills` from `enabledPlugins`, and removed 38 more inert `skillOverrides` entries (55→17 at that point; a later independent count landed on 44→17, the two commits' deltas overlap rather than being purely additive — the numbers are still fully explained, just not from a single commit). Root cause given in the commit body: the shipped resolver (`BOe()`) returns "on" for any plugin-sourced skill before the override map is consulted, so every plugin-keyed override entry was inert by construction — confirmed empirically, all 19 keys marked "off" were live in a session started after settings.json was last written. The commit also explicitly notes it is preserving "another session's uncommitted removal of andrej-karpathy-skills from skillOverrides + enabledPlugins... same direction of work."

**Net: both structural changes are deliberate, Gabriel-ratified-in-turn, and root-caused in the commit bodies — not an unattributed drift.** The gap was procedural: the schematic-refresh producer diffs `settings.json` against its own prior snapshot but never checks `git log` before reporting a change as unattributed. Fixed 2026-08-09: `ora-cc-schematic-refresh/SKILL.md` now instructs a `git log -p -- settings.json` check before calling any structural settings.json change unattributed. See [[reference_config_write_guard_bash_read_shaped_false_positive]] for a related settings.json/hooks investigation from the same period.

---

## 2026-08-14 update — when the change is NOT in git, the Desktop log is the source of record

`git log -p -- settings.json` (the v1.2 rule) answers only for *committed* changes. On 2026-08-14 `enabledPlugins`
went 7 keys/7 true → **5 keys/3 true/2 false** with the change sitting **uncommitted in the working tree**, so the
git-log-first check correctly came back empty. That is not "unattributed" — it means you look somewhere else.

**Source of record for uncommitted plugin changes: `%APPDATA%\Claude\logs\main.log`.** Four discrete events, all found there:

| When | Change | Log marker |
|---|---|---|
| 2026-08-13 19:43:54 | `hookify` removed | `[marketplaceFileOps] Removed "..."` |
| 2026-08-13 19:44:00 | `claude-code-setup` removed | `[marketplaceFileOps] Removed "..."` |
| 2026-08-13 19:44:23 | `claude-md-management` → false | `[LocalPluginsWriter] Set plugin enabled=false in settings: ...` |
| 2026-08-14 12:46:36 | `code-review` → false | *(no Desktop line — done from a Claude Code session)* |

The first three are one **29-second interactive burst in the app UI** (corroborated by `installed_plugins.json`
mtime 19:44:00) — a human, not automation. The fourth was a deliberate doctrine call: `CLAUDE.md` was written
99 seconds later (12:48:15) adding *"`code-review:code-review` plugin retired 08-14 (collided with native
`/code-review`, strictly narrower)"*. **Pair a settings.json mtime with CLAUDE.md's mtime** — a doctrine edit
within a couple of minutes usually identifies the actor and the reason.

**⛔ `[PluginsFetcher] fetchPluginEnabledState: N overrides` is NOT a tracer for `enabledPlugins`.** It tracks the
5 *local* plugins and read a flat `5` continuously from 2026-08-13 00:00 onward — including while settings.json
still held 7 keys. Using it as a change detector produces a confident wrong answer. The mutation markers are
`[LocalPluginsWriter]` and `[marketplaceFileOps]`, and both are rare (1 and 2 hits respectively in a 5MB log).

**No automation writes this key.** The only ORA script referencing `enabledPlugins`,
`maintenance/skill-override-efficacy-probe.py`, is read-and-print only. Don't hunt for a rogue hook.

Also: don't report a fast-moving figure from two samples. The 08-14a schematic pass first called this "moving hour
to hour" on the strength of an 08:35 reading (5/4/1) vs a 12:48 reading (5/3/2); those were simply the states
either side of the fourth event, and the file has been unwritten since 12:46:36. Corrected in the artifact and
`event_log.md` the same day. See [[feedback_verified_null_vs_inferred_null]].

**Operationalized 2026-08-14 — don't re-derive this, and don't re-duplicate it either.**
`~/.claude/scheduled-tasks/ora-cc-schematic-refresh/SKILL.md`'s cross-check (b) needs this ladder at
unattended runtime, when the SKILL.md prompt is the only text guaranteed to be read — a memory file that
is merely indexed is the wrong home for a rule a task must execute blind. v1.6 (commit `a9ed8ac`) first
solved that by inlining the whole ladder, which fixed the execution gap but recreated the duplication
this file exists to avoid (CLAUDE.md's "one fact, one home"). Corrected same day in commit `09c03da`
(branch `fix/schematic-node-cap-v15`): the SKILL.md now carries an **imperative Read of this file's
absolute path** plus "do not duplicate its content here" — the pattern already in use at
`ora-task-integrity-guard` step 2.5 for the model-currency standard — and inlines only the two points
where a wrong guess publishes a false claim (the `fetchPluginEnabledState` decoy, and not calling two
samples "churn"). **This file is the single source of truth for the ladder; the SKILL.md is a pointer,
not a second copy.**
