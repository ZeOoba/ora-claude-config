---
name: skilloverrides-inert-for-plugin-skills
description: "settings.json skillOverrides is silently ignored for every plugin-sourced skill (local AND @inline store) — 39 of ORA's 56 entries are dead keys"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d9a44dff-a92c-4636-be3e-27d746c44edc
  modified: 2026-08-05T21:04:47.777Z
---

**`skillOverrides` in `~/.claude/settings.json` has NO effect on plugin-sourced skills.** Verified 2026-08-05 against the shipped `claude.exe` resolver and a live session listing.

Two guard clauses return `"on"` before the override map is consulted:

```js
function BOe(e){
  if(e.type!=="prompt" || e.source==="plugin") return "on";   // plugin skills exit HERE
  let n = r?.[e.name] ?? r?.[e.unqualifiedName] ?? "on";      // never reached
}
// /skills picker path:
if(e.source==="plugin") return {value:"on", source:"plugin"};
```

The listing builder also skips them outright: `if(gi.type!=="prompt" || gi.loadedFrom!=="skills" && gi.loadedFrom!=="commands_DEPRECATED") continue;`

**Scope — this covers essentially everything ORA has tried to turn off.** 39 of 56 entries are namespaced plugin keys and are inert. Confirmed live-in-listing despite `"off"`: 6 `fa0fa64bdc96:` (docx/pdf/pptx/xlsx/mcp-builder/claude-api), 6 `ora-operations-extensions:`, 3 `anthropic-skills:` (skill-creator/personal-portfolio/setup-cowork), `andrej-karpathy-skills:karpathy-guidelines`, 2 `cowork-plugin-management:`, 4 moot `chrome-devtools-mcp:`. **Cloud skill-store plugins register as `@inline` in `.claude.json` and are `source==="plugin"` too** — so `anthropic-skills:` and `ora-operations-extensions:` are equally unreachable.

Key format is NOT the problem — the lookup accepts both `plugin:skill` and the unqualified name. The `source==="plugin"` early return is.

**Levers that actually work:** `enabledPlugins: false` / uninstall (local plugins) · unpublishing from the skill store (`@inline`) · `disableBundledSkills` or `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1` (bundled set only).

**Why this matters beyond the wasted keys:** settings.json asserts a suppression state that does not exist, and at least one audit (Automation Fleet Audit rev 1, 2026-08-05) reasoned from it — treating the stock document-skills duplication as already solved. Retiring the local `ora-operations-extensions` plugin manifest for the same reason also failed: the repo manifest was never what served those skills. See [[feedback_verify_before_repeating_session_claims]] and [[feedback_absence_claims_need_verification_before_building]].

**Verification method that settles it in one step:** compare the session's own skill listing against the `"off"` keys. If an `"off"` skill is listed, the override is inert. Do not infer suppression from the presence of a settings entry.

Related: [[reference_skill_surfaces]] · [[reference_skill_store_drift_check_false_positives]] · [[reference_skill_reimport_sync_lag]]
