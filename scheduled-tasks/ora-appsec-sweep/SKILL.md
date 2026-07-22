---
name: ora-appsec-sweep
description: General application-security sweep of ora-pm (live tenant portal, Stripe ACH) and oxford-command-center — secret scan (working tree + full git history), lockfile CVE audit, AR-ledger/balance-display schema review, tenant-portal auth/injection pass, and OWASP-LLM checks scoped to ORA's actual agent surfaces (hooks, MCP connectors, scheduled-task registries). REPORT-ONLY: findings go to Notion Ops Hub + open-items-tracker.md; never rotates, never pushes, never auto-fixes. Reads suppressions.md before reporting. Dispatches the per-repo review to the security-auditor agent (Fable-pinned). v1.1 (2026-07-22: dispatch-to-agent simplification + fixed a duplicate-YAML-frontmatter defect that predated this version; see STATUS note). v1.0 registered 2026-07-20 (Plan 4b/4a) after a manual, Gabriel-supervised first run (2026-07-19).
model: fable
---

<!--
  STATUS: v1.1, 2026-07-22. Executed the FUTURE SIMPLIFICATION below: this task
  now dispatches the per-repo review to the `security-auditor` agent (see the
  PER-REPO REVIEW section replacing the old inline CHECKS section) instead of
  duplicating its checklist. ORA-specific scope that is NOT in security-auditor's
  generic Review Scope — full git-history secret scanning (+ the fresh-clone
  cross-check), the AR-ledger fan-out/divide-by-100 lens, and the ORA-scoped
  scheduled-task/SKILL.md/MCP-connector OWASP-LLM items — is retained as explicit
  deltas in the dispatch prompt, not silently dropped. The pinned-SHA worktree
  protocol, suppression-file gate, and reporting canon (Notion/OI-tracker/email)
  are unchanged — those live in the orchestrating STEPS below, not in the agent.
  Also fixed in this version: the file previously carried two duplicate YAML
  frontmatter blocks (a mechanical defect, same class as the one flagged on
  `ora-skill-text-audit\SKILL.md` per memory reference_scheduled_task_model_standard.md)
  — only the second, redundant block declared `model: fable`. Merged to one
  block; CC/MCP scheduled-task model is server-pinned at registration rather
  than read live from this file's frontmatter (memory: same file), so this was
  a cleanliness fix, not evidence the Fable pin had actually been failing —
  memory's 2026-07-22 re-check independently confirmed the fleet's pin as
  correct-as-is before this edit.

  PRIOR STATUS (v1.0, REGISTERED 2026-07-20, Plan 4b): Cherry-picked `security-auditor`
  agent + `security-and-hardening` skill (Plan 4a) landed 2026-07-18, same
  session that drafted this file — both installed and verified present at
  ~/.claude/agents/security-auditor.md and ~/.claude/skills/security-and-hardening/.

  FIRST RUN: completed 2026-07-19, manual and Gabriel-supervised per the
  FIRST-RUN NOTE below. It found OI-015 (alleged E. Fulton deal-terms
  residual in ora-pm git history) and separately surfaced dependency-CVE
  findings that were fixed and landed on oxford-command-center main the
  same evening. OI-015 was triaged directly with Gabriel 2026-07-19: closed
  as verified-clean (a fresh clone showed the reachable history is genuinely
  clean; the original finding was a stale local git-object-cache artifact,
  not a real leak). A real, separate residual was confirmed and spun off as
  OI-022 (the same historical blob is still retrievable via GitHub's Git
  Data API through a GitHub-internal `refs/pull/2/head` ref — no self-service
  fix exists; a GitHub Support request is drafted but not yet submitted,
  Gabriel's action, tracked in open-items-tracker.md). NOTE: OI-022 is still
  OPEN — until the Support ticket resolves, this sweep's local-checkout
  history scan (not a fresh clone) may re-surface the same blob. No
  suppression entry has been added for it — only Gabriel adds suppressions,
  and this needs his explicit call on scope/wording first.

  MODEL PIN: `model: fable` in frontmatter is deliberate and load-bearing.
  This task reviews security-gate-adjacent and payment-facing code
  (CLAUDE.md floor: confidential/financial/governor and security-gate code
  never below Fable). Never let this task inherit the caller's model. This
  applies to the `security-auditor` dispatch too — the Agent call in the
  PER-REPO REVIEW section below MUST pass `model: 'fable'` explicitly, never
  omit it and rely on inheritance (CLAUDE.md dispatch invariant).
-->

ORA AppSec Sweep — recurring application-security review of the two production ORA codebases. Self-contained; you start fresh with no memory of prior runs. Surface: Claude Code (CC/MCP fleet). This is a READ-ONLY review task.

## REPORT-ONLY PROTOCOL (ABSOLUTE — READ FIRST)

THIS TASK NEVER FIXES ANYTHING. IT ONLY REPORTS.

- NEVER ROTATE CREDENTIALS. A live-credential finding is reported and escalated, never remediated in-run.
- NEVER PUSH. NEVER COMMIT. NEVER STAGE. NEVER EDIT ANY FILE IN EITHER REPO.
- NEVER OPEN GITHUB ISSUES OR PULL REQUESTS.
- NEVER AUTO-FIX — no `npm audit fix`, no dependency bumps, no config edits, no history rewrites, no `git filter-repo`, ever.
- NEVER DELETE OR REWRITE GIT HISTORY, even when the finding is a secret IN that history.
- The ONLY writes this task performs: (1) a Notion Ops Hub completion row, (2) appended finding entries in `open-items-tracker.md`, (3) its own scratch/report files under the session scratchpad, (4) the disposable pinned-SHA worktrees it creates and removes for scanning.
- LIVE-CREDENTIAL ESCALATION: if any finding is plausibly a LIVE credential (a key/token/password that could work right now — Stripe keys, Graph secrets, DB connection strings, PATs), send a SAME-DAY escalation email to Gabriel per the email step below, marked URGENT in the subject. Do NOT test the credential against any live service. Do NOT rotate it. Rotation is Gabriel's call and Gabriel's action.

Rationale: this org has already had (a) a confidential-terms leak reach an external remote via `.env.example` in ora-pm, and (b) an owner-ratified decision (B1) to deliberately KEEP certain sensitive content in a private repo. An auto-remediating sweep would have destroyed evidence in case (a) and violated a ratified decision in case (b). Report-only is a design decision, not a limitation.

## PURPOSE

`ora-pm` runs a live tenant portal with Stripe ACH payments and has a documented defect history: a CRITICAL AR-ledger cartesian fan-out bug, a confidential-terms leak via `.env.example` that reached an external remote, and (fixed 2026-07-18, commits `f47bbe0`/`f196337`/`43f0b76`) a tenant-balance divide-by-100 display bug. `oxford-command-center` houses financial-decision code already covered weekly by `ora-financial-code-integrity-sweep` (adversarial correctness review) — but neither repo has recurring general appsec coverage: secrets, CVEs, injection, auth, agent-surface hardening. This sweep closes that gap. It complements, never duplicates, the financial-code integrity sweep: that task asks "is the math right?"; this one asks "is the surface attackable?".

## REPOS & PINNED-SHA PROTOCOL

Targets:
- `C:\Users\Owner\ora-pm` (remote `ZeOoba/ora-pm`) — live tenant portal, Stripe ACH, AR ledger.
- `C:\Users\Owner\oxford-command-center` — warehouse/scoring/NOI/capital-config platform.

NEVER scan the live working tree. Both checkouts are shared, single-writer surfaces that another session may be mid-edit in (see CLAUDE.md shared-checkout doctrine). Instead, per repo:

1. Pin the SHA: `git -C <repo> rev-parse HEAD` → record it. Every finding in the report cites this SHA — findings are meaningless without a stable ref.
2. Create a disposable detached read-only worktree OUTSIDE the repo:
   `git -C <repo> worktree add --detach "C:\Users\Owner\AppData\Local\Temp\claude\appsec-sweep\<repo-name>-<sha7>" <sha>`
   Do NOT junction or copy `node_modules` into it (worktree junction hazard — see memory `reference_worktree_node_modules_junction_hazard.md`). Lockfile-based audits do not need an install.
3. Run all working-tree checks against the worktree; run all history checks (`git log -p`, etc.) with `git -C <repo>` — history reads don't touch the working tree and are safe against the shared checkout.
4. On completion, remove the worktree: `git -C <repo> worktree remove "<worktree path>"` (no `--force`; if removal fails because of a stray file, report it in the Notion row and leave it — never force-remove).
5. Check `git worktree list` first — if a worktree for this sweep already exists (crashed prior run), reuse or remove it cleanly before creating another.

## SUPPRESSIONS (MANDATORY PRE-STEP)

Before reporting ANY finding, read `C:\Users\Owner\.claude\scheduled-tasks\ora-appsec-sweep\suppressions.md` (committed alongside this file). Every candidate finding is checked against it; a suppressed item is dropped silently — not reported, not "mentioned for completeness", not re-litigated. The suppression file exists because a prior sweep-like process re-flagging an owner-ratified decision wastes Gabriel's time and erodes trust in the sweep. If a finding is a NEAR match to a suppression but not exact (e.g., a NEW file containing deal terms, not the ratified one), report it and note the adjacent suppression.

Only Gabriel adds suppressions. This task NEVER writes to suppressions.md.

## PER-REPO REVIEW — dispatch to `security-auditor`

For EACH pinned-SHA worktree, invoke the Agent tool once:

```
Agent({
  description: "Security audit — <repo-name> @ <sha7>",
  subagent_type: "security-auditor",
  model: "fable",                 // ALWAYS explicit — never omit (see MODEL PIN note above)
  run_in_background: false,       // this task runs the two repos sequentially, not in parallel (see NOTES: RAM)
  prompt: <the template below, with <worktree-path>/<sha>/<repo-name> filled in>
})
```

`security-auditor`'s own Review Scope (input handling, auth/authz + IDOR, data protection, infra/CORS/headers,
third-party/webhook-signature integrations, AI/LLM features) already covers checks (d) and most of (e) — do not
re-paste that checklist into the prompt, it is redundant with the agent's own system prompt. Instead, the
dispatch prompt below carries ONLY what the agent would not otherwise think to check: ORA's specific defect
history, the full-git-history secret scan (its default scope is code review, not git-history archaeology), and
the ORA-scoped agent-surface items its generic "AI/LLM Features" section doesn't enumerate by name.

**Dispatch prompt template** (severity scale CRITICAL / HIGH / MEDIUM / LOW / INFO — matches the agent's own):

> Security audit of `<repo-name>` at the pinned worktree `<worktree-path>` (git SHA `<sha>`). This is a disposable
> read-only worktree, not the live checkout — findings should cite the SHA, not "current HEAD". Run your standard
> Review Scope, PLUS the following ORA-specific items your default scope does not cover:
>
> 1. **Full git-history secret scan**, not just the working tree: `git -C <repo> log -p --all` piped through
>    credential patterns (`password|passwd|secret|api[_-]?key|token|private[_-]?key|BEGIN (RSA|EC|OPENSSH)
>    PRIVATE KEY|sk_live|sk_test|pk_live|whsec_|client_secret|connectionstring|AKIA[0-9A-Z]{16}`). A secret
>    deleted in a later commit is STILL a finding — report the introducing commit and whether it ever reached
>    `origin`. A candidate hit may be a stale LOCAL dangling/unreachable object rather than genuinely reachable
>    from `origin` — cross-check via a fresh bare clone (`git clone --bare <remote-url>` to a scratch temp dir,
>    same log/grep against that clone) before reporting it as a live remote-history finding (see OI-015/OI-022,
>    the 2026-07-19 incident that motivated this cross-check). `.env.example` must contain ONLY placeholders.
> 2. **AR-ledger / balance-display lens** (ora-pm; apply the security-relevant half only in oxford-command-center's
>    `server/warehouse/migrations/**` — math correctness there belongs to `ora-financial-code-integrity-sweep`,
>    do not duplicate it): this class of bug already shipped twice (cartesian fan-out; divide-by-100). Flag
>    missing uniqueness/FK constraints permitting duplicate ledger rows; joins between charges/payments lacking
>    a key that guarantees 1:1 or intentional aggregation; money stored ambiguously (cents vs dollars unprovable
>    from name/comment/type). Trace balance display end-to-end once (DB → API → portal render) — every unit
>    conversion (`/100`, `*100`, `toFixed`, currency formatting) must appear exactly once; two conversions or
>    zero is a finding.
> 3. **ORA-scoped OWASP-LLM agent-surface items** beyond your generic AI/LLM section: (a) any committed
>    scheduled-task/SKILL.md/workflow file in-repo that grants broader tool permissions than its job needs,
>    contains an external send path other than the ratified Outlook COM script, or routes output anywhere other
>    than the ggoldberg-only canon; (b) any committed MCP server config adding new connectors or widening scopes;
>    (c) `hooks/**` or committed `.claude/` config for override/auth/exit-code changes — a hook failing open
>    where doctrine says fail closed, a weakened override check, an inverted exit-code convention (PreToolUse vs
>    git-hook conventions are OPPOSITE — memory `reference_pretooluse_vs_git_hook_exit_codes.md`); flag any
>    committed change to security-gate hook logic at minimum HIGH.
> 4. **Dependency CVEs**: `npm audit --json` in this worktree (lockfile-based, no install needed). NEVER run
>    `npm audit fix` or any remediation — report only, with fix version if available. Triage by reachability:
>    runtime dependency on a served path outranks dev-only tooling.
>
> Report EVERY finding (do not pre-filter for relevance to Gabriel — the orchestrating task filters against a
> suppression list after you return). Use your standard Output Format (severity counts + per-finding Location /
> Description / Impact / Recommendation). Report-only: never rotate credentials, push, commit, or open issues/PRs.

The orchestrating STEPS below (suppression filtering, Notion row, open-items-tracker, escalation email, worktree
cleanup) are unchanged by this dispatch — they operate on whatever the agent returns exactly as they did on the
old inline checks' output.

## STEPS

1. PRE-FLIGHT: confirm both repos exist and git works in each. If either fails, write a Notion completion row noting the failure for that repo, continue with the other if possible, and never fabricate a result.
2. Read `suppressions.md` (path above). If it is missing or unreadable, STOP the reporting phase and record a TOOLING ERROR — running without suppressions guarantees re-flagging ratified decisions.
3. Pin SHAs and create the two detached worktrees per the protocol above.
4. Dispatch the `security-auditor` agent per repo per the PER-REPO REVIEW section above. Collect candidate findings from its returned report: repo, pinned SHA, severity, file/commit location, description, evidence, and its recommendation (NOT executed).
5. Filter through suppressions. Drop exact matches; annotate near-matches.
6. NOTION COMPLETION ROW (ALWAYS): write a row to the Ops Hub (Notion collection `32b6ecd8`) recording: date, both pinned SHAs, per-repo finding counts by severity (the agent's own Critical/High/Medium/Low/Info summary — note which ORA-specific delta item or built-in Review Scope section each finding traces to, for traceability, but don't force it back into the old five-letter (a)–(e) shape), result line (CLEAN / N FINDINGS (worst: X) / TOOLING ERROR / PARTIAL — what didn't run), and suppression count applied. A partial sweep is not the same claim as a full one — say what ran and what didn't (e.g. the agent errored before finishing one repo, or `npm audit` failed).
7. OPEN-ITEMS TRACKER: append each MEDIUM+ finding as an item to `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\open-items-tracker.md` following its existing item format (it is the canonical punch-list; do not restate items that already exist there — check for duplicates from prior runs first, matching on repo+file+check).
8. EMAIL (ONLY on CRITICAL/HIGH findings OR a tooling failure — never on a clean or low-only week): send via Outlook COM — the SOLE send path:
   `powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -Body "<body>"`
   TO ggoldberg@oxfordra.net ONLY (never cc Eric; never ze@). Subject: "ORA AppSec Sweep — N finding(s) ([worst severity])" or "... — URGENT: possible live credential" or "... — TOOLING ERROR". Body: per-finding block (repo · SHA · check · file/commit · severity · evidence · suggested next step). On a non-zero exit from the send script: retry ONCE; if it still fails, flag loudly in the Notion row and continue — do NOT halt.
9. CLEANUP: remove both worktrees per the protocol. Verify with `git worktree list`.
10. NEVER FABRICATE. If a check could not run, the report says so; an unrun check is never reported as clean.

## FIRST-RUN NOTE — COMPLETED

First run occurred 2026-07-19, manual and Gabriel-supervised as required before registration. It surfaced OI-015 and dependency-CVE findings; OI-015 was triaged directly with Gabriel the same day (closed as verified-clean, real residual spun off as OI-022 — see STATUS note at top). Cron registered 2026-07-20 per the proposed cadence below. Proposed cadence: weekly, offset from the Monday 1:30 PM financial-code sweep to avoid RAM contention — now running Wednesday 1:30 PM ET.

## NOTES

- Complements `ora-financial-code-integrity-sweep` (correctness of financial math, oxford-command-center only, Workflow-based refuters). No overlap by design: where a finding is a MATH defect in financial-decision code, note it and defer to that sweep's next run rather than duplicating the adversarial review.
- Single-writer discipline: this task reads the shared checkouts' git history via `git -C` and does all file-level work in its own disposable worktrees. It never mutates either working tree.
- RAM: workstation ceiling ~5.7 GB. Run the two repos SEQUENTIALLY, not in parallel; `git log -p --all` on a large repo is memory-hungry — stream it through the pattern match, never load it whole.
- Methodology: the per-repo review is delegated to the `security-auditor` agent (threat-model-first, STRIDE at trust boundaries, the audit-triage reachability tree, "if a secret is ever committed, rotate it — deleting the line is not enough" (rotation = Gabriel, not this task), and its own OWASP-LLM 2025 mapping) plus the ORA-specific deltas in the PER-REPO REVIEW dispatch prompt above. v1.0's inline checklist was itself adapted from the vetted `security-and-hardening` skill (agent-skills-main, reviewed clean 2026-07-18) — see STATUS note for the v1.0→v1.1 simplification history.