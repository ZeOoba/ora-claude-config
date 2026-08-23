---
name: project-automation-audit-rev14-2026-08-16
description: "Automation Audit Rev 14 — independent reverification of Revision 11 (README HOOKS→MAINT edge, 7 maintenance/_state/ files untracked); both reconfirmed, zero new open items; one methodology lesson"
metadata:
  type: project
  originSessionId: 0b2d3ebe-d43f-4527-a586-50ee0cbfc5a1
  modified: 2026-08-17T01:48:47.933Z
---

Revision 14 of the [ORA Automation Audit](https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7), 2026-08-16, Gabriel-invoked via [[ora-setup-audit-skill]] to independently verify Revision 11's two already-published, already-"FIXED" findings rather than take them on trust.

**Both reconfirmed, no new open items.** R11-1 (README `HOOKS→MAINT` diagram edge) — `hooks/git-prepush-doctrine-gate.py:113,421` independently grepped, matches the diagram and caption exactly, commit `615a6e2` confirmed on `origin/main`. R11-2 (7 `maintenance/_state/` files untracked + `.gitignore` formalized) — all 7 confirmed absent from `git ls-files` at HEAD, `.gitignore:223-229` carries the entries, `health-guard-beacon.json`'s exemption held, and the external-reader grep (`fleet-deadman.yml` + `oxford-command-center` + `ora-pm`) was independently re-run from scratch, not trusted — zero matches, same result.

**One real methodology lesson, worth carrying into future audits:** the first pass here produced a false alarm. `git branch --contains 615a6e2` (local branches only, no `-r`) found no `main`, and the checked-out branch (`feat/model-canary-probe-step25`) had diverged 29 ahead / 35 behind its own `origin` tracking ref — which read as "R11's fix is stranded on an unmerged, unpushed local branch," a real durability gap if true. `git branch -r --contains` showed `origin/main` already had both commits; `origin/main`'s own tree confirmed the file state independently. **`git branch --contains` without `-r`/`-a` silently omits remote-only merges** — a trap for any future "is this commit safely landed" check run from a local clone whose branch tips lag their own remotes, which is the routine case in this actively-contended checkout, not the exception.

**Published mid-collision.** Another live session (`4aca81f7`) was concurrently editing the Revision 13 band in the same durable working-copy file (`~/.claude/artifacts/ora-automation-audit.html`) while this pass wrote Revision 14 above it. Edits were disjoint (different line ranges) and applied cleanly, but the mandatory Step 4a rev-band cap (4 inline max) was **deliberately deferred** rather than attempted as a same-pass deletion against a file another session was actively writing — 5 inline bands (14/13/12/11/10) stand temporarily. **Open: roll Revision 10 to `ora-automation-audit-history.md` on the next pass** once the collision has settled — do not let this ride past one more revision.

**Not re-measured, not carried forward as current:** plugin/marketplace footprint, skill-catalog counts, scheduled-task fleet health, and the four token-bloat gates are Revision 13's numbers, unchanged here.
