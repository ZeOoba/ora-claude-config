---
name: project-r13-verification
description: "Same-day live re-check of Automation Audit Revision 13 (R13-1..6) — 3 of 6 headline findings refuted or mismeasured, 2 confirmed, tail claims unverified"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4aca81f7-4ed4-43c0-af89-7f62545326ae
  modified: 2026-08-17T01:46:49.305Z
---

Gabriel asked to investigate Revision 13 of the "ORA Automation Audit" artifact. A live ground-truth re-check the same day found the report had already gone partly stale — evidence appended to the artifact as an "R13-VERIFICATION" bullet (same rev-band, after R13-6), not a new numbered revision.

**Refuted (do not act on these R13 chips without re-measuring first):**
- R13-1 (FRED MCP dead): live retest now succeeds — `.claude.json`'s fred entry is pinned (`--with "mcp<2"`) and the launch command exits 0, no ModuleNotFoundError. Cause of the discrepancy unestablished (13+ concurrent sessions were active in this same checkout — a concurrent fix landing between R13-1's authorship and this check is plausible but not confirmed).
- R13-2 (skill-mirror drift): `~/ora-skills/ora-setup-audit/SKILL.md` and `~/.claude/skills/ora-setup-audit/SKILL.md` are now byte-identical (both v1.4); mirror mtime postdates the repo commit, confirming a re-sync already happened.
- R13-5 (CLAUDE.md near FAIL gate): live `wc -w` reads 1,706 words (matches R13-5's own cited "Revision 10" figure, not its claimed current 1,841). Working tree is git-clean against the 2026-08-14 commit — no edit explains a higher count. The claimed "nine words of headroom" does not reconcile with any observable state. The *sub*-finding (county-sales-monitor missing from CLAUDE.md:52's Market research tie-break) is independently true and still stands.

**Overstated, direction correct:**
- R13-4 (MEMORY.md near hard ceiling): actual size is 20,443 B, not 22,207 B — ~9 days runway at the stated rate, not ~7. The archival-vs-split decision is still real and still needs Gabriel's call, just not as urgent as framed.

**Confirmed as written:**
- R13-3 + CORRECTION (ora-passed-deal-tracker duplicate, CC is the intended destination): both fleet folders still exist; CC registry description matches the quoted provenance text verbatim.
- R13-6 (collision retimes executed): live registry read confirms both crons exactly (`ora-pm-daily-crons` → `40 9 * * *`, `ora-county-sales-monitor` → `25 10 15 * *`).

**Not re-verified:** the "also measured and clean" tail (doctrine-integrity, governor-drift, confidentiality-guard, 8/8 guards) — out of scope for this pass, carried not confirmed.

**Process note:** another session (`0b2d3ebe`) was concurrently editing the same artifact file during this pass — the verification was appended additively after a forced re-read per the single-writer collision hook. Reconcile before any further structural edit to the artifact.

Why this matters generally, beyond R13: this environment currently has 13+ concurrent sessions active in the same checkout, several with merged PRs against `~/.claude`. A same-day audit finding can go stale within hours purely from other sessions' live remediation — [[feedback_verify_before_repeating_session_claims]] and [[feedback_findings_decay_recheck_before_writing]] both apply, but neither previously covered *inbound* review of someone else's just-published findings, only outbound re-assertion of one's own. Worth folding into ora-setup-audit's guardrails: a same-day R13-style claim needs re-verification before being cited as current, not just before being repeated.

Artifact: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7
