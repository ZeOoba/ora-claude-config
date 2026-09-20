---
name: feedback-subagent-double-completion-and-legit-agreement
description: "One background Agent can emit TWO completion notifications with different answers; identical answers from DIFFERENT agents are genuine agreement, not a defect"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0534d11d-1d76-48ff-937d-8cd86b31ce19
  modified: 2026-09-12T22:45:56.135Z
---

When fanning out background subagents and harvesting their JSON results, wait for ALL agents before finalizing any slot. A single task-id can notify twice with different final blocks. 2026-09-12 eval-harness poll: Hamilton r3 sent Combined 15.0, then 11.0.

- **Differing blocks from one task-id** = failed sample. Never keep the first or the last.
- **Identical answers from different task-ids are NOT evidence of mis-attribution.** Coarse integer judgments agree legitimately (Port Sheldon r2/r3 = 29, E Fulton r2/r3 = 55 in the same run).
- A draft rule that failed on cross-agent identity was withdrawn. It missed the real failure and would have cut two scored deals to n=1.

**Why:** a recorder that takes the first notification per slot silently keeps whichever answer arrived first. Nothing looked wrong until the second notice came in.

**How to apply:** any harvest of parallel Agent results (eval harness, verified-deal-recon, audits). Canonical rule: `ora-skills/acquisition-underwriting-eval-harness/SKILL.md` Step 1.5 and Data-quality finding 5 (PR ZeOoba/ora-skills#54). Related: [[feedback_agent_model_pin_not_held_end_to_end]].
