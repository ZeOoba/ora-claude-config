---
name: project-automation-audit-rev12-2026-08-16
description: "Automation Audit Rev 12 (2026-08-16) — both Revision 9 data-quality items refuted as false findings; capex-budgeting was never republished and the \"orphaned\" plugin registration was a category error"
metadata: 
  node_type: memory
  type: project
  originSessionId: 16c5371f-037c-41a7-907c-504cc9671b5b
  modified: 2026-08-16T18:27:43.849Z
---

Gabriel-invoked targeted pass against the Rev 9/10 open tail. Artifact: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7 (Revision 12). Investigation-only — nothing executed.

**Both Rev 9 data-quality items were false findings, not open work.** Three things a future session needs before trusting older revisions' prose on this:

1. **`capex-budgeting` was never republished.** The "live today with a 2026-08-12 update" reading came from the *repo* copy — `ora-skills` commit `d03fe62`, an editorial v1.1 bump that tombstoned dangling `maintenance-analytics` refs. A repo commit/mtime says nothing about store publication state. Live listing shows exactly 6 of the 7 skills migrated in `19c63c4` absent and 1 (`submarket-spatial-analysis`) present — precisely Rev 5's record. Rev 5 was right all along. This is the drift `ora-skill-store-drift-check` exists to catch.

2. **Never test an `@inline` plugin's liveness against `enabledPlugins`.** `@inline` = cloud skill-store plugin; those *never* appear in `enabledPlugins`, which holds only marketplace-sourced plugins. `anthropic-skills@inline` (usageCount 175, fired today) is absent from it too. The `ora-operations-extensions:submarket-spatial-analysis` entry is a correct frozen log record from 2026-06-22, weeks before the bundle's retirement (`2f4f831`, 08-05); `.claude.json` usage maps are never garbage-collected. Rev 10 reached the right verdict for partly the wrong reason. See [[reference-settings-json-enabledplugins-skilloverrides-attribution-2026-08]].

3. **The artifact's `skillOverrides` "STILL LIVE" table is moot.** All 39 plugin-prefixed keys were removed 2026-08-05 in commit `165fff3` (56 keys/39 prefixed → 17/0), confirmed by bisecting `settings.json` across 20 commits. The *root cause* — plugin-sourced skills hit `if(e.type==="prompt" || e.source==="plugin") return "on"` before the override map is read — remains valid doctrine. Residual left unchased on Gabriel's call: 8 of the 17 survivors target an uninstalled Cloudflare plugin (dead by absence); the 9 `user-invocable-only` keys can't be adjudicated from disk.

**Also confirmed closed:** the `ora-operations-extensions` retirement (committed, tree clean — the "still uncommitted" note is stale), and R10-3/the 1.8 GB re-clone. `plugins/` tree is now 9.7 MB total with only 2 marketplaces, both supplying installed plugins; no regrowth since 2026-08-14 18:38. Honesty caveat recorded in the artifact: that mtime predates `c70cd4a`, so the stop cannot be attributed to that commit.

Related: [[reference-memory-dir-not-in-single-writer-list-2026-08-14]], [[feedback-verified-null-vs-inferred-null]].
