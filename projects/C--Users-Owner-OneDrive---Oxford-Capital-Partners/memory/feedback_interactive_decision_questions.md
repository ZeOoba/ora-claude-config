---
name: feedback-interactive-decision-questions
description: "Every decision/ruling needed from Gabriel must be posed as an interactive multiple-choice question with a researched recommendation (standing rule, 2026-07-18)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 02323ec2-31bf-44dc-9acb-7eb5beea7aa3
---

Standing rule (Gabriel directive, 2026-07-18): whenever a session needs a decision, ruling, or approval from Gabriel — G-batches, contested items, scope choices, keep/retire calls — present it as an **interactive multiple-choice question** (AskUserQuestion tool on surfaces that support it) with a **deeply researched recommendation** for every question.

**Why:** faster ruling loop and no free-text back-and-forth; formalizes the ratified ledger-v2 governance pattern ("Claude drafts with evidence; Gabriel rules contested rows only") into the interaction layer itself.

**How to apply:**
- Use AskUserQuestion; put the recommended option FIRST with "(Recommended)" appended to its label; give each option a one-line tradeoff description.
- Batch related decisions into one call (max 4 questions/call; chain calls if more).
- On surfaces without the interactive tool (Cowork/chat), emulate with lettered options + an explicit "Recommended: (x) — why" line.
- Hard-invariant confirmations (external sends, deploys, money, governor changes) may be CARRIED by this format, but the selection itself is the explicit in-turn confirmation — never pre-select or assume.
- This does not expand WHEN to ask (autonomy rules unchanged — one-pass completion, pause only for material ambiguity/invariants); it governs HOW to ask when a pause is warranted.

Related: [[rules]] §10 permission regime · ledger-v2 pattern in [[project-claude-setup-audit-2026-07-16]].
