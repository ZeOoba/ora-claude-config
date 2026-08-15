---
name: ora-claude-setup-audit
description: Monthly wrapper — invokes the ora-setup-audit skill (formerly claude-setup-audit; platform rejects "claude" in skill names) — formal, evidence-grounded audit of skills/plugins/connectors/hooks/scheduled-task fleet, keep/fix/combine/delete verdicts — and continues the ORA Automation Audit artifact. Never executes fixes itself — investigation only. [MODEL: claude-sonnet-5 | set 2026-08-13]
---

Monthly ORA setup audit (CC/MCP fleet). This task is a THIN WRAPPER — it does not contain any audit logic of its own.

1. Invoke the `ora-setup-audit` skill (via the Skill tool, skill name `ora-setup-audit` — formerly `claude-setup-audit`, renamed 2026-08-13 because the platform rejects skill names containing "claude"; canonical source C:\Users\Owner\ora-skills\ora-setup-audit\SKILL.md, also mirrored at C:\Users\Owner\.claude\skills\ora-setup-audit\ and installed on the Cowork surface as anthropic-skills:ora-setup-audit). Do not re-derive, duplicate, or "improve" its audit logic in this task — follow its own Standard Workflow unmodified: locate the existing "ORA Automation Audit" artifact via Artifact action:list first (never start a parallel one), run its four threads (plugins & connectors, scheduled-task fleet, skill catalog redundancy, token-bloat sources), cross-verify any conflicting claims against a live file read, and apply its Guardrails section (never-flag allowlist, rarity-is-neutral framing, evidence-honesty — no invocation telemetry exists anywhere in this stack, every prune/delete verdict must be evidence-inferred and state what was checked).

2. Synthesize into a new rev-band on the existing Automation Audit artifact per the skill's own format (keep/fix/combine/delete/ask/dead chips, cited evidence) and publish via Artifact passing the existing url — never create a parallel artifact.

3. Write exactly one project-memory pointer entry per the skill's own Outputs section (findings + what's pending Gabriel's call; do not duplicate the artifact's content into memory).

4. Do NOT execute any fix/delete/combine verdict in this pass — this is an unattended scheduled run, so "explicitly asked to fix it now" can never be true here. Investigation and verdict table only, exactly as the skill's own step 5 requires.

5. Do not email. This task's only outputs are the updated Artifact and the one memory pointer entry.

6. Never fabricate a finding, a verdict, or evidence the ora-setup-audit skill's own threads did not themselves produce. If the Skill tool invocation fails outright, or the Automation Audit artifact can't be located, report that failure via a memory note instead of silently skipping the run or inventing a fresh artifact.