---
name: ora-appsec-sweep
description: General application-security sweep of ora-pm (live tenant portal, Stripe ACH) and oxford-command-center — secret scan (working tree + full git history), lockfile CVE audit, AR-ledger/balance-display schema review, tenant-portal auth/injection pass, and OWASP-LLM checks scoped to ORA's actual agent surfaces (hooks, MCP connectors, scheduled-task registries). Weekly, Wednesdays. REPORT-ONLY: findings go to Notion Ops Hub + open-items-tracker.md; never rotates, never pushes, never auto-fixes. Reads suppressions.md before reporting. Dispatches the per-repo review to the security-auditor agent, which carries the never-below-Fable model floor (this task's own frontmatter model:fable pin is NOT honored on CC/MCP — server-pin, issue #48976); a post-hoc dispatch-integrity gate probes subagent transcripts after the run and emails a MODEL-FLOOR BREACH alarm only on a drop below Opus (an Opus fallback is ruled COMPLIANT, OI-052 closed). Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: UNVERIFIABLE | checked 2026-10-30]
model: opus
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

  MODEL PIN — CLAIM CORRECTED 2026-07-24, THE FRONTMATTER PIN IS NOT IN EFFECT.
  `model: opus` in frontmatter is deliberate INTENT, and this task does review
  security-gate-adjacent and payment-facing code (CLAUDE.md floor:
  confidential/financial/governor and security-gate code never below Opus 5.5).
  But a transcript canary on this task's own 2026-07-22 17:38 UTC scheduled run
  (session 4b66d74c-b948-49c1-8f8d-883d821e7aa3, whose first timestamp matches
  the registry's lastRunAt to within 2s) shows the scheduled portion fired on
  **claude-opus-4-8 — all 163 assistant messages from 17:38:32Z up to the first
  human turn, with zero claude-fable-5**. (That session later became interactive:
  Gabriel ran `/model` at 19:54:12Z and the subsequent 86 messages are
  claude-sonnet-5. Those are a deliberate human switch, NOT scheduled-task
  behaviour — do not read them as fleet evidence.) CC/MCP scheduled tasks are server-pinned at
  registration and do NOT read this file's frontmatter `model:` field, so the
  v1.1 STATUS note's inference ("a cleanliness fix, not evidence the Fable pin
  had actually been failing") is now disproven: the pin was, and is, inert.
  ==> RESOLVED 2026-07-24, Gabriel-ratified: **Option C — the floor is carried by
  the `security-auditor` Agent dispatch, not by this task's own model.** The
  orchestrator runs at the server-pinned tier (observed opus-4-8); the actual
  security judgment runs at Fable inside the subagent, which is a real, honored
  mechanism. Rejected alternatives: (A) accept-and-document alone — leaves the
  judgment itself below the floor; (B) migrate to LAMS where the frontmatter pin
  IS enforceable — but LAMS has no local COM/shell, which this sweep's
  full-git-history scanning depends on, so it trades a model-tier gap for a
  capability gap. (A) stands only as the INTERIM position until the dispatch is
  proven live on the 2026-07-29 fire.
  Because the pin now lives entirely in the dispatch, a silent dispatch failure
  would breach the floor invisibly — see the DISPATCH INTEGRITY GATE in the
  PER-REPO REVIEW section, which is mandatory and alarms on failure.
  Do NOT "fix" this by deleting the frontmatter pin (it records intent and costs
  nothing) and do NOT flip anything to Sonnet.
  The `security-auditor` dispatch is a SEPARATE mechanism and its pin IS
  honored — the Agent call in the PER-REPO REVIEW section below MUST keep
  passing `model: 'opus'` explicitly, never omitting it and relying on
  inheritance (CLAUDE.md dispatch invariant).
  DISPATCH NOT YET EXERCISED (resolved 2026-07-24, no defect): the 2026-07-22
  run made ZERO Agent/Task calls and wrote zero subagent transcripts. That is
  NOT a skipped dispatch — v1.1, which introduced the dispatch, was authored
  DURING that same session (the run's own Edit calls to this file are visible
  in its transcript), so the fire executed the v1.0 inline-CHECKS spec, which
  had no dispatch to make. The `security-auditor` dispatch has therefore never
  actually run; its first real opportunity is the next scheduled fire. Treat
  that fire as the dispatch's first live test and verify a subagent transcript
  is produced — do not assume the path works until it has.
-->

ORA AppSec Sweep — recurring application-security review of the two production ORA codebases. Self-contained; you start fresh with no memory of prior runs. Surface: Claude Code (CC/MCP fleet). This is a READ-ONLY review task.

## REPORT-ONLY PROTOCOL (ABSOLUTE — READ FIRST)

THIS TASK NEVER FIXES ANYTHING. IT ONLY REPORTS.

- NEVER ROTATE CREDENTIALS. A live-credential finding is reported and escalated, never remediated in-run.
- NEVER PUSH. NEVER COMMIT. NEVER STAGE. NEVER EDIT ANY FILE IN EITHER REPO. The one exception to NEVER COMMIT and NEVER STAGE is outside both scanned repos: step 7c lands this run's own `open-items-tracker.md` rows in `~/.claude` through `maintenance/commit-own-edit.py`. Never run `git add`/`git commit` yourself.
- NEVER OPEN GITHUB ISSUES OR PULL REQUESTS.
- NEVER AUTO-FIX — no `npm audit fix`, no dependency bumps, no config edits, no history rewrites, no `git filter-repo`, ever.
- NEVER DELETE OR REWRITE GIT HISTORY, even when the finding is a secret IN that history.
- The ONLY writes this task performs: (1) a Notion Ops Hub completion row, (2) appended finding entries in `open-items-tracker.md`, (3) its own scratch/report files under the session scratchpad, (4) the disposable pinned-SHA worktrees it creates and removes for scanning, (5) the step-7 landing: the `--begin` baseline record `commit-own-edit.py` keeps beside this session's provenance, and the one tracker commit it makes.
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
  model: "opus",                  // ALWAYS explicit — never omit (see MODEL PIN note above)
  run_in_background: false,       // this task runs the two repos sequentially, not in parallel (see NOTES: RAM)
  prompt: <the template below, with <worktree-path>/<sha>/<repo-name> filled in>
})
```

### DISPATCH INTEGRITY GATE (MANDATORY — added 2026-07-24, Gabriel-ratified Option C)

The Opus 5.5 pin (`opus` alias; Fable retired 2026-10-05) on this task now lives ENTIRELY in the Agent call above. The orchestrating session
itself runs on the CC/MCP server-pinned model (observed `claude-opus-4-8`, 2026-07-24 canary) — the
frontmatter `model: opus` is inert. So if this dispatch silently fails to happen, the security
judgment quietly drops to the orchestrator's model and the CLAUDE.md never-below-Opus-5.5 floor is
breached with no visible signal. That is exactly the failure this gate exists to prevent.

After EACH per-repo Agent call, assert ALL of the following before using its output:
1. The Agent call actually returned a subagent result. A `null`/empty return (user skip, terminal
   API error after retries, agent type unresolvable) is a FAILURE, not "no findings."
2. The findings you report for that repo came FROM the subagent. **You must NEVER substitute your
   own inline review for a failed dispatch** — inline review is precisely the v1.0 behaviour this
   design replaced, and it runs below the floor.
3. `model: "opus"` was passed explicitly on the call (never omitted, never inherited).

Assertions 1–3 are SPAWN-TIME checks — they confirm the dispatch happened and was pinned. They are
structurally blind to a mid-run FALLBACK, where a subagent begins on `claude-fable-5` and then drops
to the orchestrator's model partway through, with that tier producing the actual findings report
(observed on BOTH the 2026-07-31 fire — fable → opus-5 — and the 2026-08-12 fire — fable → opus-4-8).
Gabriel RULED 2026-08-14 that a mid-run fallback to an OPUS tier was COMPLIANT, and closed OI-052. On
2026-10-05 the floor itself became Opus 5.5 (Fable retired from dispatch), so the post-hoc assertion now
enforces `claude-opus-5-5` exactly: a fallback to opus-5 or opus-4-8 now TRIPS it (tightened from the
2026-08-14 opus-4-8 floor). It still catches a total dispatch failure:

4. **(POST-HOC — run ONCE after BOTH repos' dispatches, not per-repo)** Every subagent held at least
   the OPUS 5.5 floor for its full run, not merely at spawn. Run:
   `python ~/.claude/maintenance/check-dispatch-model-floor.py --session $CLAUDE_CODE_SESSION_ID --floor claude-opus-5-5`
   Exit 0 = every subagent held Opus-or-above end-to-end; exit 1 = at least one subagent ran BELOW Opus
   (sonnet / haiku / unknown id); exit 2 = the transcripts could not be read (verified-null — treat as
   a gate failure, NEVER a pass; an unverifiable floor is not a held floor). Quote the probe's per-agent
   table verbatim in the completion report either way.

If assertion 1, 2, or 3 fails for a repo: do NOT silently continue. Mark that repo's section
`DISPATCH FAILED — FINDINGS NOT PRODUCED AT THE REQUIRED MODEL FLOOR`, omit any inline substitute
findings, and email ggoldberg@oxfordra.net (subject prefix `⚠️ ORA AppSec Sweep — DISPATCH FAILURE`)
via the standard Outlook COM path, in addition to the normal reporting. A dispatch failure is a
first-class alarm even when the sweep finds nothing.

If assertion 4 fails (probe exit 1 or 2): this is DIFFERENT from a dispatch failure — the findings
ARE from the real subagent and remain usable (do NOT discard them and do NOT substitute inline
review). Under the OPUS 5.5 floor, exit 1 means a subagent ran BELOW claude-opus-5-5 (opus-5 / opus-4-8 /
sonnet / haiku / unknown); a Fable run is above the floor and does not trip this. Exit 2 means the floor could not be verified. Either way, record a
`MODEL-FLOOR BREACH (OI-052)` line in the completion report AND email ggoldberg@oxfordra.net (subject
prefix `⚠️ ORA AppSec Sweep — MODEL-FLOOR BREACH`) via the standard Outlook COM path, with the probe's
output pasted in. Because only a run below Opus 5.5 trips it, a firing under the Opus 5.5
floor is RARE and a REAL signal — a genuine drop below Opus, or an unreadable transcript — not routine
noise. Do NOT "fix" a firing by loosening the floor below Opus or deleting the assertion.

**FIRST LIVE TEST — the 2026-07-29 fire.** This dispatch has never actually executed: the 2026-07-22
run made zero Agent calls because v1.1 (which introduced the dispatch) was authored during that very
session, so the fire ran the v1.0 inline spec. On the next run, explicitly confirm a subagent
transcript was produced (`~/.claude/projects/<project>/<session-id>/subagents/*.jsonl` non-empty) and
state that confirmation in the completion report. Until that has been observed once, treat the
Fable-via-dispatch path as UNPROVEN and say so in the report rather than assuming it worked.

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
6. NOTION COMPLETION ROW (ALWAYS): Compute the run date once at run start (`date '+%A %Y-%m-%d'`; date part in every date slot, weekday only where one is named) and reuse that exact value in every title, subject and body. If a Notion create returns no page ID (e.g. a grace-period/quota notice), search by the exact title before any retry — a match created at/after the create call is this run's page; never blind-retry a create. Quota errors → `notion-quota-fallback` skill. Write a row to the Ops Hub (Notion parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`, full UUID) recording: date, both pinned SHAs, per-repo finding counts by severity (the agent's own Critical/High/Medium/Low/Info summary — note which ORA-specific delta item or built-in Review Scope section each finding traces to, for traceability, but don't force it back into the old five-letter (a)–(e) shape), result line (CLEAN / N FINDINGS (worst: X) / TOOLING ERROR / PARTIAL — what didn't run), and suppression count applied. A partial sweep is not the same claim as a full one — say what ran and what didn't (e.g. the agent errored before finishing one repo, or `npm audit` failed).
7. OPEN-ITEMS TRACKER: append each MEDIUM+ finding as an item to `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\open-items-tracker.md` following its existing item format (it is the canonical punch-list; do not restate items that already exist there — check for duplicates from prior runs first, matching on repo+file+check). When there is nothing new to append, skip 7a–7c. Run the 7a and 7c commands each as its own Bash call, not chained with anything else.
   a. BEGIN, after the duplicate check and before the first tracker edit: `python "C:\Users\Owner\.claude\maintenance\commit-own-edit.py" --begin --path "C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\open-items-tracker.md"`. It records whether the tracker already held someone else's uncommitted content. Whatever it reports (BEGUN, DIRTY_AT_BEGIN or ERROR), carry on with 7b.
   b. EDIT TOOL ONLY: make every tracker edit with the Edit tool, never Bash, sed or a script. The Edit tool's touch record is the only proof of authorship the landing step accepts; a script-written row reads as unowned and stays uncommitted. In the same pass, make sure the frontmatter `modified:` shows this run's UTC time (update it with the Edit tool if it still shows an older one).
   c. LAND after the last edit: `python "C:\Users\Owner\.claude\maintenance\commit-own-edit.py" --path "C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\open-items-tracker.md" --message "memory(open-items): ora-appsec-sweep <run date> files OI-NNN..OI-MMM"`. It waits until the file has been quiet for 15 s, then commits the tracker only when preflight-shared-checkout.py proves this run is the only live recorded owner of what changed. It can take up to about 90 s, so give this Bash call a 600000 ms timeout. Run it once; never retry it, never run `git` yourself. Add its first output line (`COMMIT-OWN-EDIT <STATUS> -- ...`) to the step-6 Notion page and to the run summary.
      - COMMITTED or NOTHING_TO_COMMIT (exit 0): done.
      - LEFT_FOR_SWEEP (exit 1): another writer, claim or lock was in the way. The rows stay uncommitted for ora-memory-commit-sweep (Fridays 19:00). Not a failure by itself; the recorded line keeps a repeat visible.
      - ERROR (exit 2), UNDONE or COMMITTED_UNVERIFIED (exit 3), or no `RESULT_JSON=` line: a tooling failure for step 8. Quote the output line in the email.
8. EMAIL (ONLY on CRITICAL/HIGH findings OR a tooling failure, including a step-7c ERROR, UNDONE or COMMITTED_UNVERIFIED — never on a clean or low-only week): send via Outlook COM — the SOLE send path:
   `powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -Body "<body>"`
   TO ggoldberg@oxfordra.net ONLY (never cc Eric; never ze@). Subject: "ORA AppSec Sweep — N finding(s) ([worst severity])" or "... — URGENT: possible live credential" or "... — TOOLING ERROR". Body: per-finding block (repo · SHA · check · file/commit · severity · evidence · suggested next step). On exit 2 or 4 from the send script: retry ONCE; if it still fails, flag loudly in the Notion row and continue — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the failure record named above, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
9. CLEANUP: remove both worktrees per the protocol. Verify with `git worktree list`.
10. NEVER FABRICATE. If a check could not run, the report says so; an unrun check is never reported as clean.

## FIRST-RUN NOTE — COMPLETED

First run occurred 2026-07-19, manual and Gabriel-supervised as required before registration. It surfaced OI-015 and dependency-CVE findings; OI-015 was triaged directly with Gabriel the same day (closed as verified-clean, real residual spun off as OI-022 — see STATUS note at top). Cron registered 2026-07-20 per the proposed cadence below. Proposed cadence: weekly, offset from the Monday 1:30 PM financial-code sweep to avoid RAM contention — now running Wednesday 1:30 PM ET.

## NOTES

- Complements `ora-financial-code-integrity-sweep` (correctness of financial math, oxford-command-center only, Workflow-based refuters). No overlap by design: where a finding is a MATH defect in financial-decision code, note it and defer to that sweep's next run rather than duplicating the adversarial review.
- Single-writer discipline: this task reads the shared checkouts' git history via `git -C` and does all file-level work in its own disposable worktrees. It never mutates either working tree.
- RAM: workstation ceiling ~5.7 GB. Run the two repos SEQUENTIALLY, not in parallel; `git log -p --all` on a large repo is memory-hungry — stream it through the pattern match, never load it whole.
- Methodology: the per-repo review is delegated to the `security-auditor` agent (threat-model-first, STRIDE at trust boundaries, the audit-triage reachability tree, "if a secret is ever committed, rotate it — deleting the line is not enough" (rotation = Gabriel, not this task), and its own OWASP-LLM 2025 mapping) plus the ORA-specific deltas in the PER-REPO REVIEW dispatch prompt above. v1.0's inline checklist was itself adapted from the vetted `security-and-hardening` skill (agent-skills-main, reviewed clean 2026-07-18) — see STATUS note for the v1.0→v1.1 simplification history.


*Changelog — MIGRATED FROM FRONTMATTER (v1.7 (2026-08-17), class-n remediation). These entries previously existed ONLY in the `description` field; the body carried pointers reading "see description field above", which stops being true the moment the description is trimmed. Moved verbatim, not summarised.*

- **v1.2 (2026-07-24: MODEL PIN claim corrected — a transcript canary on the 2026-07-22 run DISPROVED the assumption that this task runs on Fable; see MODEL PIN note. Documentation only, no procedural change)

- **v1.3 (2026-07-24: Gabriel ratified Option C — the never-below-Fable floor is carried by the security-auditor Agent dispatch, not this task's own model; adds a MANDATORY DISPATCH INTEGRITY GATE that alarms rather than silently falling back to inline review, since inline review runs at the orchestrator's below-floor model)

- **v1.4 (2026-08-03, Gabriel-directed re-canary): model re-observed off the 2026-08-01T01:06Z scheduled fire, session local_0a029d90 — claude-opus-5 across all 93 scheduled-portion assistant messages. Supersedes the 07-24 claude-opus-4-8 finding, which predated the 2026-07-26 Opus 5 lineup rollout. That session DID continue interactively (human turn late in the run), i.e. exactly the case where get_session's single model field is untrustworthy — so the authoritative transcript-cut method was used and the interactive tail was excluded; here both methods happened to agree. The frontmatter model: fable pin is STILL not honored on CC/MCP (server-pin, Claude Code issue #48976) — unchanged finding, and the reason the Fable floor rides on the security-auditor Agent dispatch rather than this task

- **v1.5 (2026-08-12: added a fourth, POST-HOC DISPATCH INTEGRITY GATE assertion — a model-floor probe (maintenance/check-dispatch-model-floor.py) that reads the subagent transcripts after the run and alarms via a `⚠️ MODEL-FLOOR BREACH` email if any subagent fell back below the Fable floor mid-run; closes the OI-052 blind spot that assertions 1–3, being spawn-time only, cannot see. Report-only; findings from a fallen-back subagent stay usable, the breach is just made visible)

- **v1.6 (2026-08-14, Gabriel ruling): OI-052 CLOSED — a mid-run fallback to an OPUS tier is ruled COMPLIANT with never-below-Fable (Opus is still top-tier). The post-hoc gate assertion now enforces an OPUS floor (`--floor claude-opus-4-8`), so the routine fable→opus fallback no longer alarms; only a drop BELOW Opus (sonnet/haiku/unknown id) or an unreadable transcript trips the `⚠️ MODEL-FLOOR BREACH` email

- **v1.8 (2026-11-05, Gabriel chose option 1 of 3):** step 7 now lands its own tracker rows. It records a `--begin` baseline before the first edit, writes with the Edit tool only, and lands with `maintenance/commit-own-edit.py`. That helper commits the tracker only when preflight-shared-checkout.py proves this run is the only live recorded owner of what changed; otherwise it leaves the rows for ora-memory-commit-sweep. Before this, the rows waited for the weekly sweep and the tracker read CONTESTED to every other writer in the meantime: the 2026-11-04 rows OI-389..395 blocked another session until they were committed by hand as `e8b708c6`. NEVER COMMIT gains that one exception, outside both scanned repos. Deliberately NOT done: the register-scheduled-task step 3c `sched-open-items-tracker` claim. The preflight reads every claim with a flat 120-minute TTL, so a leftover claim would hold the tracker CONTESTED for other writers for up to two hours after a run, the very state this change removes. claim_work.py also refuses the release after a claim has displaced an expired one.