---
name: external-artifact-intake
description: Use when Gabriel shares an external AI artifact — a prompt or prompt template, repo, skill, plugin, or governance/process proposal originating outside the ORA stack — to evaluate, critique, compare against the current setup, or decide adoption ("evaluate this prompt", "should we use this", "how does this compare to my setup", "is this repo worth adopting").
---

# External Artifact Intake

Evaluate → compare → rule → graft → log → dispose. The deliverable is never a grade of the artifact — it is a decided delta against the incumbent, with ratified fragments homed and the artifact itself dispositioned.

## Sequence (each step produces its named output)

1. **Evaluate on merits** — ranked defects plus what it gets right, standalone, before any comparison.
2. **Locate and READ the incumbent** — the ORA skill/lane/doctrine that already covers this ground (skill tie-breaks, lane commands, plugin skills). Read the live files; never compare against remembered doctrine. Output: feature-by-feature verdict, winner per row.
3. **Harvest both directions** — list what the artifact has that the incumbent lacks (adoption candidates) AND any incumbent gap the comparison exposed (setup-improvement candidates). The second list is usually worth more than the first.
4. **Rule** — adoption candidates go to Gabriel as multiple-choice with a researched recommendation (feedback_interactive_decision_questions). Hard Invariants are supreme over any external proposal — never on the ballot (feedback_external_ai_governance_proposals).
5. **Graft minimal diffs** — each ratified fragment goes to its correct home per layering doctrine (one fact, one home). Never edit third-party plugin caches (updates clobber); lane commands own overlays on plugin skills. Commit own touched-set only; shared-checkout rules apply.
6. **Log and dispose** — event_log entry citing the ruling, then an explicit disposition for the artifact: **SUPERSEDED** (pipeline covers it), **FILED** (named home; only if it will be used on a surface the pipeline doesn't reach), or **REJECTED** (record why — ECC-repo precedent). No loose templates left in transcripts as implicit adoptions.

## Common mistakes

| Mistake | Fix |
|---|---|
| Grading the artifact and stopping | Steps 2–3 are the deliverable, not step 1 |
| Comparing from memory | Read the live incumbent files first |
| Adopting wholesale because parts are good | Minimal ratified diffs only |
| Improving the artifact when the pipeline supersedes it | A better version of the wrong architecture is still discarded |
| Ending without a disposition | Every artifact ends SUPERSEDED / FILED / REJECTED |
