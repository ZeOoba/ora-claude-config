---
name: ora-aaos-publish-contracts
description: AAOS contracts-mirror publisher (CC/MCP fleet, filesystem/git tool) — republishes schemas/spec/registry/templates from the AAOS git tree to the seam's read-only contracts/ mirror on a 2x-daily cadence (09:00 / 15:00 ET) so it never drifts silently behind HEAD; silent on success, emails ggoldberg only on failure. v1.1 2026-07-16: cadence halved 3×→2×/day per Fleet Ledger v2 ruling C2. v1.0 2026-07-10 (cadence changed hourly→3x/day 2026-07-10). [MODEL: claude-opus-5 observed | checked 2026-07-26 via session-metadata canary]
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