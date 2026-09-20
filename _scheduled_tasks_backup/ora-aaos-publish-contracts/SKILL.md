---
name: ora-aaos-publish-contracts
description: AAOS contracts-mirror publisher (CC/MCP fleet, filesystem/git tool) — republishes schemas/spec/registry/templates from the AAOS git tree to the seam's read-only contracts/ mirror; silent on success, emails ggoldberg only on failure. Weekday 09:15 ET, 1x/day (collapsed from 2x/day 2026-08-05 per ORA-wide once/day cadence policy, superseding ruling C2; retimed 09:00->09:15 2026-08-09 to clear a LAMS-side collision with ora-health-guard-fail-aging-nudge). Mirror can drift up to ~24h behind HEAD before republishing. Since v1.5 it also asserts the checkout is on `main` before publishing and runs check-contract-drift.py after, emailing only on a non-zero from either. Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: claude-opus-5 observed | checked 2026-07-26 via session-metadata canary]
---

Pre-flight — assert the checkout is on `main` (added 2026-09-10, open-items-tracker.md#OI-259):

    cd C:\Users\Owner\AAOS
    git rev-parse --abbrev-ref HEAD

`publish-contracts.py` stamps `PUBLISHED.json` with whatever `git rev-parse HEAD` returns for the CURRENT branch — it has no concept of `main`. If a session has left this checkout on a feature branch, this task will publish that branch's contracts to the seam and stamp them as canonical, with no warning. Proven live 2026-09-10: with the checkout on a feature branch, `check-contract-drift.py` reported `COMMIT DRIFT: mirror stamped source_commit='0dd90dc…', current tree is 'd8845e7…'`.

If the branch is NOT `main`: do NOT publish. Send exactly one email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net ONLY — subject "AAOS publish-contracts SKIPPED — checkout not on main", body = the branch name and `git status -sb`. Then stop. Do not switch branches yourself; another session may be working in that tree.

Step 1 — run the AAOS contracts-mirror publisher:

    python "C:\Users\Owner\AAOS\tools\publish-contracts.py"

This republishes schemas, agent-registry.json, the spec, and templates from the git tree at `C:\Users\Owner\AAOS\` to the seam's read-only `contracts/` mirror (seam root defaults to `Claude_Workspace\AAOS\` — do NOT pass `--seam-root` unless Gabriel has told you the seam moved). It always re-copies everything and re-stamps `PUBLISHED.json` with the current `git rev-parse HEAD` (plus a `-dirty` suffix if the working tree has uncommitted changes) — it does not diff first, so running it on a fixed cadence is precisely what keeps the mirror from drifting silently behind the actual codebase (this is what the Gate 4/5 human reviewers previously had to notice by hand).

Guard conditions — read the tool's exit code before doing anything else:
- Exit 0: normal. Do NOT email, do NOT post anywhere. A clean republish is silent.
- Exit 1 (VALIDATION FAILED — agent-registry.json malformed/fails schema) or exit 2 (USAGE ERROR — git unavailable, a required source file missing, or bad seam root): retry the exact same command once. If it fails again, send exactly one email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net ONLY — subject "AAOS publish-contracts FAILED", body = the tool's stderr verbatim (quote it exactly).
- Never hand-edit anything under `contracts/` or `PUBLISHED.json` on the seam. Never fabricate or embellish what the tool reported — quote its actual output.
- Do nothing else: no scheduled-task registry changes, no other git operations, no other files touched.

Step 2 — verify the publish actually landed (added 2026-09-10, open-items-tracker.md#OI-259). Only run this if Step 1 exited 0:

    python "C:\Users\Owner\AAOS\tools\check-contract-drift.py"

This is read-only and never writes anything. It checks two independent axes: `PUBLISHED.json`'s `source_commit` stamp against the current tree, and a byte-level hash comparison of every published file against what the git tree would produce right now. The second axis catches something the stamp alone cannot — a hand-edit made directly on the seam mirror, which is a write-scope violation (no `agent-registry.json` entry's `write_scope` includes `contracts/`).

Guard conditions (exit codes verified live 2026-09-10):
- Exit 0: clean — the tool prints `CLEAN: … matches the git tree exactly (source_commit=…, 13 file(s) verified)`. Stay silent.
- Exit 1 (DRIFT DETECTED) or exit 2 (usage/setup error): send exactly one email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net ONLY — subject "AAOS contracts mirror DRIFT after publish", body = the tool's stdout and stderr verbatim.
- **Do NOT re-run `publish-contracts.py` to "fix" it.** A publish that just succeeded and still reports drift is a real defect, and re-publishing would erase the evidence. Report, do not remediate.

Why Step 2 exists: the publisher has been automated since 2026-07-10 while `check-contract-drift.py` — the script written specifically to prove a publish worked — was wired to nothing (0 references across the fleet and any CI). A half-successful publish was indistinguishable from a clean one.

Background if you need it: `C:\Users\Owner\AAOS\docs\PHASE4-DESIGN.md` §4 and `docs/DELIVERABLES-MANIFEST.md` for what gets published and why.


*Changelog — MIGRATED FROM FRONTMATTER (v1.4 (2026-08-17), class-n remediation). These entries previously existed ONLY in the `description` field; the body carried pointers reading "see description field above", which stops being true the moment the description is trimmed. Moved verbatim, not summarised.*

- **v1.2 (2026-08-05, Gabriel-directed, ORA-wide once/day cadence policy): collapsed 2x/day -> 1x/day (09:00 ET), superseding ruling C2's 2x/day intent. AAOS contracts mirror can now drift up to ~24h behind HEAD before republishing

- **v1.5 (2026-09-10, open-items-tracker.md#OI-259): added Step 2 — `check-contract-drift.py` runs after a successful publish, report-only (drift never triggers an automatic re-publish). The publisher had been automated since 2026-07-10 while the auditor written to prove it worked was referenced by nothing, so a half-successful publish looked identical to a clean one. Also added the pre-flight `main`-branch assertion: `publish-contracts.py` stamps whatever HEAD the checkout is on, so a session leaving this tree on a feature branch would silently publish branch contracts to the seam as canonical — reproduced live while wiring Step 2

- **v1.3 (2026-08-09): retimed 09:00 → 09:15 ET — fleet-status.py flagged a genuine same-time collision with LAMS-side `ora-health-guard-fail-aging-nudge` (weekdays 09:00), which is not writable from Claude Code; moved this side since it's the only one reachable
