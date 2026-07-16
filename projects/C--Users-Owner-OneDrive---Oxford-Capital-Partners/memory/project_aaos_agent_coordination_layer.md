---
name: project_aaos_agent_coordination_layer
description: AAOS (ORA Agent Coordination Layer) exists — a real git repo + OneDrive seam for cross-surface Code<->Cowork task/lease/handoff coordination. Check this before treating any AAOS reference as unverified or injected.
metadata: 
  node_type: memory
  type: project
  originSessionId: e8c060da-c8fb-4fb7-9a8e-6ed8e9ac897a
---

AAOS ("ORA Agent Coordination Layer") is real infrastructure, built and shipped v1.0 in a Claude Code session on 2026-07-10. It is a task-queue + lease + handoff + event coordination layer letting Claude Code and Claude Cowork sessions hand off work to each other safely across the OneDrive "seam."

**Where it lives:**
- Git repo (code, schemas, tests, docs — 16+ commits, six Gate reviews, 194 tests green as of 2026-07-10): `C:\Users\Owner\AAOS\`
- Live runtime state (the "seam" — tasks/handoffs/locks/events, NOT under git): `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\AAOS\projects\ora-ops\`
- Read-only contracts mirror (schemas/spec/registry published from git to the seam for a Cowork consumer): `<seam root>\contracts\`
- Entry point for any Cowork session joining as the `cowork` agent: `<seam root>\COWORK-BOOTSTRAP.md` (self-contained; fail-closed on any unreadable/malformed precondition, per its own §3)

**Why this note exists:** a Cowork session asked to act on a staged AAOS handoff (task `t-cowork-seam-confirm`) correctly refused, on the grounds that "AAOS," "handoff," and "spool event" appeared nowhere in its loaded context (CLAUDE.md, memory, skill canon) — treating it as a plausible prompt-injection test. That skepticism was the right default response to an unverifiable second-hand instruction, and this note is the fix: AAOS is confirmed real (git history, passing tests, real files read directly), so a future session can verify it here instead of refusing blind or trusting blind.

**Standing open item:** `t-cowork-seam-confirm` — live two-way seam confirmation from an actual Cowork session — has never been closed. It requires: (1) that Cowork session have folder access to `Claude_Workspace\AAOS\` (the 2026-07-10 attempt failed on this precondition — "no folder is currently mounted"), and (2) Gabriel confirming AAOS's legitimacy in-session before Cowork acts on the staged handoff (per the incident above). Once granted, the paste-in instructs Cowork to read `COWORK-BOOTSTRAP.md`, then the handoff at `<seam root>\projects\ora-ops\handoffs\h-code-to-cowork-seam-confirm.json`, and follow its §7 SAFE-BY-HAND recipes.

**How to apply:** if a future session — Code or Cowork — encounters a reference to AAOS, a "seam," `tools/expire-leases.py`, `tools/publish-contracts.py`, `tools/check-contract-drift.py`, or a `t-`/`h-`/`e-` prefixed AAOS-shaped id, verify against the git repo and seam paths above before treating it as fabricated or as an injection attempt. Two scheduled tasks exist for it on the CC/MCP fleet: `ora-aaos-expire-leases` (lease sweep) and `ora-aaos-publish-contracts` (contracts-mirror republish), both hourly during business hours, silent on success, emailing ggoldberg@oxfordra.net only on failure.
