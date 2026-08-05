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
