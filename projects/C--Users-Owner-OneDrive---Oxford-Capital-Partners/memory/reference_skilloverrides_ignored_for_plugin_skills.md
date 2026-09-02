---
name: reference_skilloverrides_ignored_for_plugin_skills
description: "settings.json skillOverrides does NOTHING for plugin-sourced skills — any key containing ':' is inert by construction; disable the plugin instead"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c47ee1c3-be7c-49a8-a7e6-c6b628194061
  modified: 2026-08-05T21:26:59.976Z
---

`skillOverrides` in `settings.json` is **silently ignored for every plugin-sourced skill.** Confirmed 2026-08-05 against the CLI bundle, not inferred:

```js
if ((e.type==="local-jsx"||e.type==="local") && BUILTIN_CMDS.has(e.name))
  return settings().skillOverrides?.[e.name]==="off" ? "off" : "on";
if (e.type!=="prompt" || e.source==="plugin") return "on";   // <-- returns BEFORE overrides
let n = r?.[e.name] ?? r?.[e.unqualifiedName] ?? "on";
```

The `/skills` UI resolver agrees — `if (e.source==="plugin") return {value:"on", source:"plugin"}` — which is why this never surfaced as a visible contradiction in the UI either.

**The operative rule:** a plugin skill's qualified name is always `<plugin>:<skill>`, so **any override key containing `:` is inert by construction.** That makes it deterministic, not a judgement call. Note `anthropic-skills` is itself a plugin (`.claude-plugin/plugin.json`), so ORA's own skills are plugin-sourced too — `anthropic-skills:*` keys are equally inert.

**Remedy: disable the PLUGIN or its marketplace** (`enabledPlugins` / `blockedMarketplaces`). Adding another override key is the defect, not the fix. Removing inert keys is cosmetic — it tidies the config but does not suppress anything, because the keys were never doing anything.

Also inert: `name-only` / `user-invocable-only` on a builtin `local`/`local-jsx` command — that branch honors only `"off"`.

**Scale when found:** 39 of 56 entries inert at `settings.json` HEAD; 17 of the named skills were still fully listed and model-invocable in the live session listing. It survived at least two setup audits because nothing ever compared the override keys against a live listing.

**Detectors now in place (both required — neither substitutes for the other):**
- `~/.claude/maintenance/skill-override-efficacy-probe.py` — proves a key is INERT (deterministic, CRIT + exit 1). Tests: `test-skill-override-efficacy-probe.py`. Wired as check 8 of `setup-self-audit.py` and step 7 of `ora-skill-store-drift-check` v1.13.
- `daily-setup-audit-prompt.md` STEP 1b — proves the skill is LISTED. **No file on disk holds the rendered listing**, so only a real session can do this half; a clean probe run is not evidence the listing is clean.

## Three skills are structurally un-suppressible — Gabriel ruling 2026-08-05: ACCEPT

`anthropic-skills:personal-portfolio`, `anthropic-skills:setup-cowork`, and `anthropic-skills:skill-creator` were all marked `off` and cannot be individually suppressed by any means. They live inside the `anthropic-skills` plugin, and the only lever that works on a plugin skill is disabling the whole plugin — which would kill every ORA skill (acquisition-underwriting, daily-brief, loi-generation, the lot).

**Ruled: accept, leave them listed.** Cost is ~3 skills of listing budget. Rejected alternatives: splitting them into a separately-disableable bundle (touches the ora-skills packaging path + a supervised re-upload of every affected skill) and trimming their descriptions (weakens routing if ever needed).

**Do not re-attempt this via `skillOverrides`.** Re-adding `anthropic-skills:<name>` keys is the inert-key defect above, not a fix — `skill-override-efficacy-probe.py` will flag any such key CRIT. If a future session finds these three listed and reaches for an override, this ruling is the answer.

Related: [[feedback_verified_null_vs_inferred_null]], [[feedback_absence_claims_need_verification_before_building]]

## Merged 2026-09-02 from the concurrent-session twin `reference_skilloverrides_inert_for_plugin_skills.md` (archived)

Both files were written 2026-08-05 by different sessions on the same finding (see [[reference_concurrent_session_duplicate_hardening_work]]). Unique points the twin carried:
- The listing builder also skips plugin skills outright: `if(gi.type!=="prompt" || gi.loadedFrom!=="skills" && gi.loadedFrom!=="commands_DEPRECATED") continue;`
- Key format is NOT the problem — the lookup accepts both `plugin:skill` and the unqualified name; the `source==="plugin"` early return is.
- Cloud skill-store plugins register as `@inline` in `.claude.json` and are `source==="plugin"` too — `anthropic-skills:` and `ora-operations-extensions:` keys are equally unreachable.
- Confirmed live-in-listing despite `"off"` (2026-08-05): 6 `fa0fa64bdc96:` (docx/pdf/pptx/xlsx/mcp-builder/claude-api), 6 `ora-operations-extensions:`, 3 `anthropic-skills:`, `andrej-karpathy-skills:karpathy-guidelines`, 2 `cowork-plugin-management:`, 4 moot `chrome-devtools-mcp:`.
- Levers that actually work: `enabledPlugins: false` / uninstall (local plugins) · unpublishing from the skill store (`@inline`) · `disableBundledSkills` or `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1` (bundled set only).
- Downstream hazard: settings.json asserts a suppression state that does not exist; Automation Fleet Audit rev 1 (2026-08-05) reasoned from it and treated the stock document-skills duplication as already solved. Retiring the local `ora-operations-extensions` plugin manifest failed for the same reason — the repo manifest never served those skills.
- One-step verification: compare the session's own skill listing against the `"off"` keys; a listed "off" skill proves the key inert.

Related (from the twin): [[reference_skill_surfaces]] · [[reference_skill_store_drift_check_false_positives]] · [[reference_skill_reimport_sync_lag]] · [[feedback_verify_before_repeating_session_claims]]
