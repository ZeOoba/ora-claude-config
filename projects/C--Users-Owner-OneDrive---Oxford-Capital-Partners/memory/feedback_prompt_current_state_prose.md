---
name: prompt-embedded-current-state-prose
description: "Hand-written \"current state\" claims baked into prompts/workflows AND into live data fields (shas, finding counts, ratification state, already-done lists, aging anchors and elapsed-day counts) rot — give them a runtime refresh mechanism, a live-artifact pointer, or a dated curated-@ tag plus a VERIFY instruction"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 506c87f0-3030-45f0-9886-9bd1de4311db
  modified: 2026-08-03T19:15:08.360Z
---

Never state repo/world state as a timeless fact inside a prompt, workflow script, or SKILL.md.

**Why:** proven twice on 2026-07-16 — cc-audit-army's baked `BASELINE = origin/main @ 823574d` fell 192 commits behind (auditors were told a stale sha was "the authoritative current state" and re-reported landed work as gaps), and cc-eval-plan-premortem.js hardcoded a "37-finding audit" count plus an "un-ratified" governor-ruleset claim that aged out when RCT v03 ratified 2026-07-14.

**How to apply** — pick one per claim, strongest first:
1. **Runtime refresh**: derive the claim when the prompt is built (cc-audit-army's fail-closed `cc-refresh` scout; generic-mode Orient).
2. **Live-artifact pointer**: tell the agent to read the authoritative file instead of asserting its contents (cc-eval-plan-premortem now defers to `<wt>/_run/AUDIT-REPORT.md` for count + baseline).
3. **Dated tag + verify**: `curated @ <date/sha>` plus an explicit "VERIFY before trusting" instruction — the model is `~/.claude/prompts/command-center-autonomous-review-v2.md`'s "Known reality as of authoring (VERIFY, do not trust blindly)" style.

**The same rule binds live DATA fields, not just prompts (extended 2026-08-03, per Gabriel).** A Notion `Next Action` on 754 Old State Route 74 carried not just a posture claim but a computed one — *"Counterparty-aging clock runs from 2026-07-23 (counsel class, 7-business-day threshold; 1 bd elapsed as of 07-24 — inside SLA)."* Correct the instant it was written; by 2026-08-03 it had drifted to **exactly 7 business days, sitting precisely on the ratified counsel threshold**, while the live Outlook thread showed the real last outbound was 07-31 (1 bd) *and* that seller's counsel had already answered. Anyone reading the field literally — a human, the weekly `ora-deal-command-board`, or a downstream skill — would have manufactured a breach on a deal that was not merely inside SLA but no longer an outbound-aging item at all.

**Gabriel's ruling, 2026-08-03: an aging anchor belongs in a computed field or nowhere.** Applied that day: the arithmetic clause was stripped from the 754 row and replaced with a non-decaying *rule* ("aging is computed from the live Outlook thread by ora-deal-aging-sla; no elapsed-day count or threshold verdict is to be recorded in this field"). A rule carries no state, so it cannot rot. `Last Activity`, `Stage`, `PSA Status`, and `LOI Status` were deliberately left untouched — stripping decayed arithmetic is not the same act as reconciling a posture field, which would destroy divergence evidence and reset the staleness clock (see `ora-deal-aging-sla` guardrails).

**How to apply when WRITING a deal/tenant record:** state the observable event and its date ("PSA sent to Patterson 2026-07-23 14:51 UTC") — never the derived quantity ("1 bd elapsed", "inside SLA", "31 days stale"). Derived figures belong to whatever recomputes them at read time. Any skill that stamps `Next Action` (`deal-execution`, `loi-generation`, `acquisition-underwriting`, `psa-reconciliation`) is in scope; propagating this into their SKILL.md text is an open follow-up requiring the `ora-skills` single-writer claim.

**The consuming side of the same rule: a handoff document states INTENT, not completion (added 2026-08-03).** The rule above is written for the author. The reader needs the mirror of it, because a cross-surface handoff is the single most state-dense prose ORA produces — file tables, commit-message drafts, "before you commit" cleanup lists, expected command output. The 2026-08-01 Cowork→Code handoff for `deal-execution` v1.3 opened with a modified/new file table and a §2 "three cleanup items" block; by the time a Code session read it, §2 (fixture cleanup), §3 (the commit), and §4's packaging had **all already been done** — `1567da7` was on `main` and `_staging/` held both `.skill` files. Nothing in the document was dishonest; it described the state at authoring, and the world moved. The same session then made the inverse error inside one turn: it read `_staging/PENDING_REIMPORT.md`, saw two pending lines, and reported the install as not-yet-done — when Gabriel's Save-skill click had landed two minutes earlier and only the hand-cleared ledger lagged (see [[docx-verification-windows-gap]]'s sibling case in [[reference_skill_reimport_sync_lag]]).

**How to apply as a reader:** before executing any handoff, plan, or prior-session summary, re-derive its claimed starting state — `git log -1` / `git status` for "committed", the artifact on disk for "packaged", the authoritative runtime signal for "installed" — and treat every step as *conditionally* pending. This costs one batch of read-only checks and converts "already-done" from a silent redo into a stated finding. Pre-flight failure analysis already names `already-done` as a failure mode; this is the concrete instance. A handoff author can halve the cost by writing steps as verify-then-act ("confirm `git log -1` is not yet `<subject>`, then commit") rather than as imperatives.

Sweep heuristic: grep workflows/prompts/scheduled-task SKILL.mds for 7-hex shas, hardcoded counts, "un-ratified"/"currently"/"already done" — and grep Notion long-text fields for "clock runs from", "bd elapsed", "days stale", "as of <date>". Related: [[workflows-dir-single-writer-gap]].
