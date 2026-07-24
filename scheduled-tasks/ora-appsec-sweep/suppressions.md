# ora-appsec-sweep — Suppressions

Owner-ratified findings the sweep must NEVER re-flag. Only Gabriel adds entries here; the sweep itself never writes to this file. Each entry: what the sweep would otherwise flag, why it is suppressed, who ratified it and when, and the exact scope of the suppression (near-matches outside the scope are still reported, with a note pointing at the adjacent suppression).

Source of record for S-001/S-002: memory `cc-autonomous-audit-pr28.md` (Gabriel's decisions of 2026-06-14 on the oxford-command-center autonomous audit, PR #28).

---

## S-001 — Committed confidential deal terms in oxford-command-center seed data (audit item B1)

- **What the sweep would flag:** confidential deal terms present in source at `src/data/seed-deals.ts` in `ZeOoba/oxford-command-center` (secret/sensitive-data scan, check (a); also reachable via the LLM02 sensitive-context lens in check (e)).
- **Suppression:** DO NOT FLAG. Gabriel DECIDED 2026-06-14: KEEP + EXEMPT. He chose to keep confidential deal terms in this private, single-owner repo's source. The pre-push confidentiality hook added in PR #28 was deliberately REMOVED (PR #32) and the repo exempted; no de-commit or history scrub was performed or is wanted. The `~/.claude/hooks/confidential-terms.json` EGRESS guard is unchanged and still bars deal terms from the public site, the `/dist/` mirror, Notion, and Outlook — internal repo presence is the ratified exception.
- **Scope:** deal terms in `oxford-command-center` source and its git history (including `src/data/seed-deals.ts` and the historical commits containing the same terms). NOT covered: deal terms newly appearing in `ora-pm`, in any PUBLIC or externally-served artifact, in Notion/Outlook output, or any NEW category of confidential data — those are reported, with a note referencing S-001.
- **Ratified:** Gabriel Goldberg, 2026-06-14 (memory: cc-autonomous-audit-pr28.md — "Future audits: do NOT re-flag committed deal terms in this repo as a finding — it is an owner-ratified exception.").

## S-002 — Acquisition scorecard ruleset ratification state (audit item B4)

- **What the sweep would flag:** `config/acquisition-ruleset.v1.json` in `oxford-command-center` carrying `ratification:"ratified"` as committed, agent-readable configuration governing financial decisions (check (e) agent-surface / governance-config lens might flag a committed decision-authority file for review).
- **Suppression:** DO NOT FLAG, DO NOT RE-RATIFY, DO NOT PROPOSE MODIFICATION. Gabriel ratified acquisition scorecard v1.0 in-session 2026-06-14 (PR #27); the engine is live and fail-closed. The ratified state is the intended state.
- **Scope:** the existence and ratified status of `config/acquisition-ruleset.v1.json` v1.0. NOT covered: any CHANGE to the ruleset without a new RULESET_VERSION + fresh Invariant-4 ratification — a modified ruleset carrying the old ratification stamp is a REPORTABLE finding (that is the drift S-002 exists to protect against, not permit).
- **Ratified:** Gabriel Goldberg, 2026-06-14 (memory: cc-autonomous-audit-pr28.md).

---

*No other suppressions. First-run triage (see SKILL.md FIRST-RUN NOTE) is expected to propose additions — e.g., the dispositioned historical `.env.example` leak in ora-pm once Gabriel rules on it — but they land here only with his sign-off.*
