---
name: reference_plugin_cleanup_scope_cache_vs_marketplaces
description: "The 2026-08-05 plugin cleanup only cleaned plugins/cache/ — plugins/marketplaces/ is a separate tree with its own orphans, ~23MB missed"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f91bfd95-26da-4fd2-9c5a-275814c22796
  modified: 2026-08-14T12:39:19.635Z
---

`~/.claude/plugins/` has (at least) two independent trees that can each carry orphaned content after a plugin is uninstalled or a marketplace is dropped: `plugins/cache/` (per-plugin installed content) and `plugins/marketplaces/` (full marketplace repo clones, e.g. `chrome-devtools-plugins`, `claude-code-plugins`, `karpathy-skills`). Uninstalling a plugin does not remove its marketplace clone, and a cleanup pass scoped to one tree will not touch the other.

The 2026-08-05 ratified cleanup (see [ORA Automation Audit](project_automation_audit_rev7_2026-08-13.md)) uninstalled 4 dead plugins and archived their `plugins/cache/` residue (~23MB: document-skills, obsidian, karpathy caches, moved to `_archive/`) — but never touched `plugins/marketplaces/`. The 2026-08-13 investigation found a *second*, coincidentally similar-sized ~23MB of dead weight there: `chrome-devtools-plugins` (10.3 MB, not in `extraKnownMarketplaces`, zero installed plugins) and `claude-code-plugins` (12.28 MB, same). Neither was in scope for the 08-05 pass and neither has been cleaned as of this writing.

**Why:** the two trees look like they'd be swept by the same cleanup, but they're structurally separate and nothing cross-checks them against each other.

**How to apply:** any future plugin/marketplace cleanup pass should explicitly check BOTH `plugins/cache/` and `plugins/marketplaces/` against `installed_plugins.json` / `settings.json`'s `extraKnownMarketplaces` — don't assume a prior cleanup covered both just because it covered one. See [[reference_skilloverrides_inert_for_plugin_skills]] for the related, previously-discovered plugin-skill-resolver gotcha from the same audit lineage.

**Update 2026-08-14 (Revision 8):** the 08-13 cleanup above archived (moved to `_archive/`) `chrome-devtools-plugins`/`claude-code-plugins` rather than deregistering them, and both were re-registered in `plugins/known_marketplaces.json` within hours — `chrome-devtools-plugins` regrew to ~1.8GB. **Archiving the folder is not sufficient; it must be deregistered with `claude plugin marketplace remove <name>`** (confirm current state first with `claude plugin marketplace list`) — that's the only action that removes both the on-disk clone AND the registry entry that lets it get re-cloned. Fixed properly this way 2026-08-14, ~1.8GB reclaimed.
