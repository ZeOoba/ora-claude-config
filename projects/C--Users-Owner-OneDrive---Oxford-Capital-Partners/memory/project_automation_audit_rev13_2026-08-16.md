---
name: project-automation-audit-rev13-2026-08-16
description: "Automation Audit Rev 13 + Schematic rev 2026-08-16a — FRED connector dead, skill-mirror drift recurred, MEMORY.md ~1 week from its hard ceiling"
metadata: 
  node_type: memory
  type: project
  originSessionId: 65a7fd4c-89ba-4dde-b8d0-a3a0c736cae4
  modified: 2026-08-17T01:47:20.550Z
---

Revision 13 of the [ORA Automation Audit](https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7) and rev `2026-08-16a` of the [Claude Code — System Schematic](https://claude.ai/code/artifact/4ad3530d-f84f-4def-a472-d16ef107e74c), both 2026-08-16, Gabriel-invoked in one pass via [[ora-setup-audit-skill]].

**⛔ PARTIALLY SUPERSEDED same day — see [[project_r13_verification_2026-08-16]].** A live re-check found item 1 (FRED dead) and item 3 (skill-mirror drift) no longer reproduce — both closed between this memory's authorship and the re-check, cause unconfirmed. Item 2's MEMORY.md figure was also overstated (actual 20,443 B / ~9 days runway, not 22,207 B / ~7) and its CLAUDE.md "1,841 words / nine words of headroom" claim does not reconcile with a live `wc -w` (1,706, git-clean) — treat that specific figure as wrong, though the county-sales-monitor tie-break gap it cites is real. Items 4/5 (passed-deal-tracker duplicate, collision retimes) held up and are unaffected.

**Scope split, so a future session doesn't re-run the wrong half:** Revision 12 (same day, earlier) ran thread 1 (plugins & connectors) in full — Rev 13 deliberately does NOT re-litigate it. Rev 13 ran threads 2 (fleet), 3 (skill catalog) and 4 (token gates), which Rev 12 explicitly left unmeasured.

**Three things to verify before trusting anything downstream:**

1. **The FRED MCP connector is DEAD** and nothing alerts on it. `uv run --with mcp` resolves the newest `mcp` package each launch, and FastMCP moved out of `mcp.server.fastmcp` — so `~/.claude/mcp-servers/fred/server.py:26` raises `ModuleNotFoundError` and the server exposes no tools. Macro/rate-strip pulls silently fall back to web search. **No probe in this stack checks MCP connector liveness** (`setup-self-audit.py` checks re-auth, which is different). Not fixed — needs a pinned dependency plus, durably, a liveness check.

2. **MEMORY.md is close to a HARD ceiling, and it is not the CLAUDE.md kind of gate.** 22,207 B at probe time, 22,488 B twenty-five minutes later (another session), against a **24,400 B Read-tool limit** — past which the index cannot be loaded at all. ~3.1 KB/week ⇒ roughly a week. Levers are archival (with inbound-ref repair) or splitting the index; prose trimming is measured to buy nothing. Needs Gabriel's call. Related: CLAUDE.md is 1,841 words against a 1,850 FAIL gate — nine words — and that is already blocking a routine tie-break addition for `county-sales-monitor`. See [[reference_claude_md_word_budget_is_a_floor]].

3. **The stale-skill-mirror defect RECURRED** (Rev 10's R10-1). `~/.claude/skills/ora-setup-audit` is v1.3; `~/ora-skills` is v1.4. This session loaded the v1.3 mirror, so the finding is self-demonstrating. **The structural point:** v1.4's fix was Step 0, "a self-check for a stale loaded copy" — a guard inside the guarded file, which cannot fire when that file is the stale one. `setup-self-audit.py`'s `check_skill_mirror_drift()` DID fire correctly; detection works, remediation never routes.

**⛔ `ora-passed-deal-tracker` dual registration is DELIBERATE — do not "clean it up".** It is registered on both fleets, same id, same cron `30 6 15 * *`, both enabled. The CC task's own registry `description` records why: **"Moved from LAMS/Cowork to CC/MCP 2026-08-15 (Gabriel-directed workflow-optimization item T3-12): the LAMS surface has no path to the Outlook COM send script, confirmed failing live 2026-08-15."** So **CC is the intended survivor and LAMS is the leftover** — Rev 13's first published recommendation ("keep LAMS, retire CC") was BACKWARDS and is retracted in the artifact. The CC copy reads NEVER-RUN only because it is monthly-on-the-15th and was registered on the 16th (`nextRunAt` 2026-09-15), not because it is broken. A live session ("Make passed-deal-tracker guard live in ~/.claude checkout") was mid-migration on it at the time of this pass.

**Two process lessons from that miss:** (1) a scheduled task's registry `description` field carries decisive provenance and must be read before recommending any retire — I recommended before reading it; (2) `fleet-status.py` renders a cross-fleet duplicate as a "same-time collision" group containing a single task name, making two very different conditions indistinguishable — worth fixing in the probe.

**Green, and worth recording:** `memory-integrity-probe.py` returned **exit 0 — first green on record** (264/264, 1:1 reconcile, zero orphans) after five straight EXIT 1. `doctrine-integrity` warnings 7→2 with the 180 skill-scan IO errors cleared. `governor-drift` exit 0 / 1,035 files. `confidentiality-guard` 131/131, sixth green. Throttle skips 147→50 in 24h, third consecutive decline.

**Schematic note:** rev `2026-08-16a` re-audited the structural sections instead of carrying them forward, and four had drifted badly — plugin surface 15 sources → 2 marketplaces, skills ~185 → ~103, hook bindings 24 → 31, custom subagents 6 → 8. That drift accumulated across the runs that carried those sections forward, which is the cost of the carry-forward default. Both caps (4 title entries, keep-2 per node) held; the 08-11a entry was condensed retroactively per spec.

**Nothing was executed.** All six findings are investigation-only, pending Gabriel.
