---
name: prompt-embedded-current-state-prose
description: "Hand-written \"current state\" claims baked into prompts/workflows (shas, finding counts, ratification state, already-done lists) rot — give them a runtime refresh mechanism, a live-artifact pointer, or a dated curated-@ tag plus a VERIFY instruction"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 506c87f0-3030-45f0-9886-9bd1de4311db
---

Never state repo/world state as a timeless fact inside a prompt, workflow script, or SKILL.md.

**Why:** proven twice on 2026-07-16 — cc-audit-army's baked `BASELINE = origin/main @ 823574d` fell 192 commits behind (auditors were told a stale sha was "the authoritative current state" and re-reported landed work as gaps), and cc-eval-plan-premortem.js hardcoded a "37-finding audit" count plus an "un-ratified" governor-ruleset claim that aged out when RCT v03 ratified 2026-07-14.

**How to apply** — pick one per claim, strongest first:
1. **Runtime refresh**: derive the claim when the prompt is built (cc-audit-army's fail-closed `cc-refresh` scout; generic-mode Orient).
2. **Live-artifact pointer**: tell the agent to read the authoritative file instead of asserting its contents (cc-eval-plan-premortem now defers to `<wt>/_run/AUDIT-REPORT.md` for count + baseline).
3. **Dated tag + verify**: `curated @ <date/sha>` plus an explicit "VERIFY before trusting" instruction — the model is `~/.claude/prompts/command-center-autonomous-review-v2.md`'s "Known reality as of authoring (VERIFY, do not trust blindly)" style.

Sweep heuristic: grep workflows/prompts/scheduled-task SKILL.mds for 7-hex shas, hardcoded counts, "un-ratified"/"currently"/"already done". Related: [[workflows-dir-single-writer-gap]].
