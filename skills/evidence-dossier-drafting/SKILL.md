---
name: evidence-dossier-drafting
description: Multi-agent drafting pipeline that prevents plausible-but-wrong output - compile a numbered facts dossier (F-ids) from verified evidence, require every drafted claim to cite an F-id inline, then have an adversarial refuter kill uncited or mis-cited claims before anything publishes. Use when orchestrating 2+ subagent drafters producing documents, artifacts, reports, or memos whose factual claims must be verifiable (artifact refreshes, audit reports, closeout matrices, IC-adjacent summaries). Not needed for single-agent prose or pure-opinion content.
---

# Evidence-Dossier Drafting (F-id pipeline)

Proven 2026-07-18 (architecture-refresh): 3 parallel drafters + 1 refuter over a 29-fact
dossier; the refuter killed 10 real defects pre-publish. The mechanism converts "the
drafter writes plausibly" from a risk into a checkable property.

## Pipeline

1. **VERIFY** — collect facts with read-only agents. Every fact must carry its evidence:
   the exact command run + relevant output lines. A claim without a command is a
   hypothesis, not a fact (probe findings included).
2. **COMPILE the dossier** — single writer. One file, numbered facts:
   `- **F-01** <claim>. (<evidence command / source>, <collector>)`
   Rules: unique F-ids · ≤ ~15 KB (fits every subagent brief without context bloat —
   reference bulky evidence by file path, never inline) · durable path (e.g.
   `00_Governance/outputs/YYYY-MM-DD_<Topic>_FactsDossier_v01.md`), NOT a session
   scratchpad — downstream sessions must be able to re-open it.
3. **DRAFT in parallel** — each drafter gets: the dossier path, its own frozen input
   baseline, ONE disjoint output file, and the citation rule verbatim:
   "Every factual sentence you add or change must cite an F-id inline (`[F-07]`).
   Invent nothing beyond the dossier and your baseline. The refuter kills uncited
   claims." Also include: "Do NOT spawn subagents" and the model pin.
4. **REFUTE** — one agent, highest tier available (reviewer ≥ implementer), briefed to
   REFUTE not confirm. Minimum kill-checks:
   (a) cross-draft contradictions (same fact stated two ways);
   (b) citation audit — spot-check ≥10 citations per draft against the dossier text;
       uncited or mis-cited changed claims die;
   (c) ruling/constraint violations (list the ratified decisions that must not be
       re-litigated);
   (d) known-stale claims (corrections the dossier already supersedes);
   (e) temporal truth — any "done" claim verified against live state NOW; not-yet-true
       actions get reworded to ruled/pending;
   (f) output↔target mapping (right file → right destination; a swap is the worst
       silent failure).
   Verdicts: PASS / PASS-with-edits (refuter applies them in place) / FAIL → re-brief
   the drafter once, then halt and report.
5. **PUBLISH from the orchestrator only** — read each passed draft in full first;
   subagents never touch external surfaces.

## Failure modes this exists to stop

- Drafter invents a precise-sounding number with no artifact behind it
  (memory: `feedback_workflow_synthesis_ungrounded_specifics`).
- Draft asserts an action as done that is only planned — sequence real-world side
  effects BEFORE publish, or the refuter rewords them to pending.
- Facts rot between plan and execution — stamp the dossier with STATE-AS-OF and have
  executors re-verify load-bearing facts past ~48h.

Related: `superpowers:requesting-code-review` (code analogue) ·
`feedback_refute_pass_proactive_default` (refute-by-default doctrine).
