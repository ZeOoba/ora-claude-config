---
name: reference-writing-style-platform-skill
description: "setup-writing-style / my-writing-style are real but dynamically-gated Claude/Cowork platform skills, not ora-skills artifacts — never expect them on the filesystem"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 559f4ced-2a74-48bd-a35e-416ffa9a96d6
---

`setup-writing-style` and `my-writing-style` are genuine Anthropic platform-native skills injected into the session system prompt's `<writing_style>` block — not skills authored in `ora-skills`, not `.skill` packages, not anything `package-and-stage-skill` or `ora-skill-store-drift-check` will ever find on disk.

Gating logic observed verbatim in a 2026-07-15 `ora-skill-text-audit` LAMS session's system prompt (`local_16c8ad22-61ed-4e7d-9c14-2c88620343d6.json`):
- No saved voice profile yet → only `setup-writing-style` is listed. Triggers when starting a draft the user will send as themselves: draft first, then offer in one line to learn their style.
- A profile exists → only `my-writing-style` is listed instead. Corrections/edits get offered as a save to the profile; the skill is never "rerun."

**Why:** this is conditionally rendered per-account/per-session state (has a writing-style profile been saved yet), not a file-based skill — so grepping `ora-skills`, `~/.claude`, or any plugin cache for the name will always return zero matches, correctly. That is not evidence of a dangling reference.

**How to apply:** if a future skill-text audit (or any session) flags `setup-writing-style`/`my-writing-style` as an unresolved/unverifiable reference, close it as **not a defect** — it's expected platform behavior, verifiable only by reading a live session's rendered system prompt, never by filesystem search. Resolved the 2026-07-15 `ora-skill-text-audit` MEDIUM #8 finding on this basis.
