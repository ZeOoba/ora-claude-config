---
name: ora-aaos-publish-contracts
description: AAOS contracts-mirror publisher (CC/MCP fleet, filesystem/git tool) — republishes schemas/spec/registry/templates from the AAOS git tree to the seam's read-only contracts/ mirror; silent on success, emails ggoldberg only on failure. Weekday 09:15 ET, 1x/day (collapsed from 2x/day 2026-08-05 per ORA-wide once/day cadence policy, superseding ruling C2; retimed 09:00->09:15 2026-08-09 to clear a LAMS-side collision with ora-health-guard-fail-aging-nudge). Mirror can drift up to ~24h behind HEAD before republishing. Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: claude-opus-5 observed | checked 2026-07-26 via session-metadata canary]
---

Run the AAOS contracts-mirror publisher:

    python "C:\Users\Owner\AAOS\tools\publish-contracts.py"

This republishes schemas, agent-registry.json, the spec, and templates from the git tree at `C:\Users\Owner\AAOS\` to the seam's read-only `contracts/` mirror (seam root defaults to `Claude_Workspace\AAOS\` — do NOT pass `--seam-root` unless Gabriel has told you the seam moved). It always re-copies everything and re-stamps `PUBLISHED.json` with the current `git rev-parse HEAD` (plus a `-dirty` suffix if the working tree has uncommitted changes) — it does not diff first, so running it on a fixed cadence is precisely what keeps the mirror from drifting silently behind the actual codebase (this is what the Gate 4/5 human reviewers previously had to notice by hand).

Guard conditions — read the tool's exit code before doing anything else:
- Exit 0: normal. Do NOT email, do NOT post anywhere. A clean republish is silent.
- Exit 1 (VALIDATION FAILED — agent-registry.json malformed/fails schema) or exit 2 (USAGE ERROR — git unavailable, a required source file missing, or bad seam root): retry the exact same command once. If it fails again, send exactly one email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net ONLY — subject "AAOS publish-contracts FAILED", body = the tool's stderr verbatim (quote it exactly).
- Never hand-edit anything under `contracts/` or `PUBLISHED.json` on the seam. Never fabricate or embellish what the tool reported — quote its actual output.
- Do nothing else: no scheduled-task registry changes, no other git operations, no other files touched. This task's entire job is one command and, conditionally, one email.

Background if you need it: `C:\Users\Owner\AAOS\docs\PHASE4-DESIGN.md` §4 and `docs/DELIVERABLES-MANIFEST.md` for what gets published and why.


*Changelog — MIGRATED FROM FRONTMATTER (v1.4 (2026-08-17), class-n remediation). These entries previously existed ONLY in the `description` field; the body carried pointers reading "see description field above", which stops being true the moment the description is trimmed. Moved verbatim, not summarised.*

- **v1.2 (2026-08-05, Gabriel-directed, ORA-wide once/day cadence policy): collapsed 2x/day -> 1x/day (09:00 ET), superseding ruling C2's 2x/day intent. AAOS contracts mirror can now drift up to ~24h behind HEAD before republishing

- **v1.3 (2026-08-09): retimed 09:00 → 09:15 ET — fleet-status.py flagged a genuine same-time collision with LAMS-side `ora-health-guard-fail-aging-nudge` (weekdays 09:00), which is not writable from Claude Code; moved this side since it's the only one reachable
