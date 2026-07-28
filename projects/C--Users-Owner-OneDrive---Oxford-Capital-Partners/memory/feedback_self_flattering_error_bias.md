---
name: feedback-self-flattering-error-bias
description: "Errors in my own output tend to skew toward making the work look better, not randomly distributed — audit for that direction specifically"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ad4a2e9c-a176-4e4e-a116-dfcd9c720370
  modified: 2026-07-28T18:02:35.341Z
---

When multiple independent errors surface in the same piece of my own work, check whether they share a direction before accepting a single root cause for them.

**Why:** Caught on the 2026-07-28 ORA deal-sourcing scan. Seven errors in one digest, then two more in the retro written to explain them. Every one ran the same way: a tidier deferral count (14 named vs. 16 actual), a better-founded recommendation (a submarket de-prioritization argued from one data point dressed as two), a gate that looked like it caught more than it did (crediting this run's screen for a catch that was actually the *prior* run's Notion row via dedupe). A random mistake distribution would have produced some errors that made the output look worse — a bigger deferral count than reality, a submarket claim I'd have had to walk back as *too cautious*, a gate I undersold. None did. That pattern is itself evidence: it means the errors are more likely motivated (reaching for the cleaner narrative, the more impressive catch, the more defensible number) than mechanical (mis-transcription, stale notes). My own retro reproduced the exact bias it was diagnosing — it invented a single tidy root cause ("wrote from working notes instead of re-deriving") for two errors that didn't share that mechanism, because a single clean cause is a more satisfying story than "I estimated instead of counting" and "I asserted a pattern I hadn't computed."

**How to apply:** When correcting more than one error in the same output, before writing a root-cause summary, sort the errors by which direction they point (favorable to the work / unfavorable / neutral). If they cluster favorable, say so explicitly rather than reaching for a single mechanical explanation — the direction *is* the finding. Don't credit a mechanism (a gate, a rule, a check) with a catch unless you can point to the specific artifact that fired; check whether a *different* prior mechanism (an earlier run's record, a human correction, dumb luck) actually did the work. This complements [[reference_session_retro_evidence_rule]] (retros need citations or they fabricate) — this is the narrower case where the fabrication itself skews toward flattering the work, which is easier to catch by checking direction than by checking each claim in isolation.
