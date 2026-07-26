---
name: ora-financial-code-integrity-sweep
description: Weekly (Mon 1:30 PM ET) adversarial integrity sweep of financial-decision code in oxford-command-center — runs the refute-financial-change workflow against the last 7 days of warehouse/scoring/NOI/capital-config commits; Notion completion row always, emails ggoldberg only on a real defect or tooling failure. v1.0 2026-06-13. Restored 2026-07-07. Refuter tier raised opus->fable with opus fallback per-lens, 2026-07-10 (CLAUDE.md governor/financial-code floor). Path scope rebuilt as directory globs (file-list missed the debt module) + rate-limit retry subcase 8a, 2026-07-24. [MODEL: UNVERIFIABLE | checked 2026-07-08]
---

ORA Financial-Code Integrity Sweep — weekly adversarial review of capital-allocation code. Self-contained; you start fresh with no memory of prior runs. Surface: Claude Code (CC/MCP fleet). This is a READ-ONLY review task — do not edit, stage, commit, or push anything in the repo.

(Restored 2026-07-07 after the CC/MCP registry was destroyed by a 2026-07-05 app reinstall — recovered from the 2026-06-22 fleet snapshot.)

PURPOSE: The Engineering OS mandates that any change to financial-decision code (engine math, scoring, benchmarking, NOI, anything feeding capital allocation or NOI) gets an adversarial pass — reviewers told to REFUTE the change, not bless it. A green test gate does not prove correctness on un-encountered data. This task runs that pass weekly against everything that landed in the last 7 days, so a defect a green gate missed surfaces within a week of merge.

REPO: C:\Users\Owner\oxford-command-center   (CC surface; git available via the Bash tool with PowerShell — use `powershell -NoProfile -Command "Set-Location 'C:\Users\Owner\oxford-command-center'; <git cmd>"`).

FINANCIAL-CODE PATHS (the review scope — only changes touching these matter):
  server/warehouse/**   (ALL of it — including migrations, the debt module, sync writers, and
                         the "delivery-only" route files: the 2026-07-24 sweep's root-cause
                         defect lived in debt-api.ts, a route file)
  server/macro/**, src/analytics/**, server/overlay.ts,
  src/contracts/warehouse.ts, src/contracts/macro.ts, src/contracts/debt.ts, src/contracts/loan.ts,
  src/brain/anomaly-insights.ts, src/brain/principal-digest.ts
  (2026-07-24 lesson: the previous version enumerated individual warehouse FILES; the week the
  Debt & Maturity module landed, none of its files were on the list, and a literal reading of the
  scope would have reported CLEAN while two HIGH governor false-clearance defects sat in the
  window. Directory globs, not file lists — new financial files must be in scope by default.
  This list intentionally tracks scripts/check-refute-required.ts's isFinancialSourcePath, but
  BROADER: files that script exempts as delivery-only still get swept here.)

STEPS:
1. PRE-FLIGHT: confirm the repo exists and git works. If not, write a Notion completion row noting the failure and STOP (do not fabricate a result).
2. SCOPE THE WINDOW: compute the review range. Run:
     git log --since="7 days ago" --pretty=format:"%h %ad %s" --date=short -- <financial paths above>
   and
     git diff --stat "@{7 days ago}"..HEAD -- <financial paths above>
   Capture the commit list, the changed-file list, and the diffstat.
3. GUARD — NO-CHANGE WEEK: if NO commits in the window touched the financial-code paths, do NOT run the workflow. Write a Notion completion row "CLEAN — no financial-code changes in the trailing 7 days" with the date, and STOP. Do NOT send an email on a clean week (the Notion row + ora-automation-health-monitor cover liveness).
4. RUN THE ADVERSARIAL WORKFLOW: if there ARE financial-code changes, invoke the saved refute workflow via the Workflow tool:
     Workflow({ scriptPath: "C:\\Users\\Owner\\oxford-command-center\\.claude\\workflows\\refute-financial-change.js", args: { changeSet: "<PROSE: list the commits (hash + subject), the changed files, and the diffstat from step 2. Tell the refuters to review the COMMITTED diff for the exact range with: git diff <oldest-sha>^..HEAD -- <the financial paths>. Summarize what each changed file does.>", greenContext: "These changes already passed the gate when merged. Probe the EDGES the test corpus does not exercise — a green gate does not prove correctness on unencountered data. Hunt for: governor-invariant bypass (DSCR<1.25 / LTV>0.40 ever persisted), NOI sign/double-count, basis-mixing, non-total-order comparators, null/empty-cohort/singleton gaps, atomicity holes." } })
   The workflow runs 3 fable refuters (correctness · determinism · edges), each falling back to opus per-lens if Fable is unavailable, and returns { verdicts, anyRealDefect, worstSeverityRank, succeeded, allFailed }.
5. INTERPRET: if allFailed=true, treat this as a TOOLING ERROR (every lens failed on both Fable and the opus fallback) — do NOT report CLEAN, skip to step 8. Otherwise collect every verdict where foundRealDefect=true. For each, capture lens, title, severity, concreteTrigger, detail, suggestedFix. If succeeded < 3, note the partial coverage (which lens(es) failed) in the Notion row even when the covered lenses are clean — a partial sweep is not the same claim as a full one.
6. NOTION COMPLETION ROW (ALWAYS): write a row to the Ops Hub (Notion collection 32b6ecd8) recording: date, commits reviewed (count + hashes), result (CLEAN / N DEFECTS FOUND / TOOLING ERROR / PARTIAL — N of 3 lenses), worst severity, and a one-line summary. Never fabricate — if a step failed, say so in the row.
7. EMAIL (ONLY on a real defect OR a tooling failure): send via Outlook COM — the SOLE send path:
     powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -Body "<body>"
   TO ggoldberg@oxfordra.net ONLY (never cc Eric — this is not the Daily Brief; never ze@). Subject: "ORA Financial-Code Integrity Sweep — N defect(s) found ([worst severity])" or "... — TOOLING ERROR". Body: per-defect block (file · lens · severity · concrete trigger · suggested fix) plus the reviewed commit list. On a non-zero exit from the send script: retry ONCE; if it still fails, flag loudly in the Notion completion row and continue — do NOT halt.
8. NEVER FABRICATE deal, tenant, or financial data. If the workflow cannot run (e.g. Workflow tool unavailable in this context), git is broken, or the workflow returns allFailed=true (every lens failed on both Fable and the opus fallback), record a TOOLING ERROR in the Notion row, email the error per step 7, and stop — do not invent a verdict.
   8a. RATE-LIMIT SUBCASE (added 2026-07-24 after a live occurrence: all 6 lens attempts failed
   with "You've hit your weekly limit · resets <time>"): when the per-agent failure messages show
   a usage/rate limit rather than a genuine tool breakage, record the Notion row as
   "TOOLING ERROR — RATE LIMITED (resets <stated time>)" and, instead of leaving the week
   unswept, register a ONE-TIME retry via the supervised create_scheduled_task tool (never
   registry-JSON splicing; honor the registry single-writer check in the session-start context
   first): id "ora-financial-code-integrity-sweep-retry", scheduled ~60 minutes after the stated
   reset time, prompt = "Run the ora-financial-code-integrity-sweep SKILL.md at
   C:\\Users\\Owner\\.claude\\scheduled-tasks\\ora-financial-code-integrity-sweep\\SKILL.md now;
   this is a one-time rate-limit retry — delete nothing, just execute the steps." Then email per
   step 7 with subject suffix "— RATE LIMITED, retry scheduled <time>". If create_scheduled_task
   is unavailable or the registration fails, fall back to plain step-8 TOOLING ERROR handling —
   the email still fires and the next weekly run covers the same window (its 7-day lookback
   overlaps).

NOTES:
- This is the recurring counterpart to the on-demand refute-financial-change workflow distilled from the PFI Phase 1 reviews (which caught real NOI double-count, intransitive tie-break, sign-inversion, and governor-bypass defects a green gate never surfaced).
- Single-writer discipline: this task only READS the repo. The workflow's refuter agents also only read. Never modify the working tree.
- RAM: the workstation ceiling is ~5.7 GB. The workflow caps its own concurrency; do not spawn additional parallel agents beyond it.