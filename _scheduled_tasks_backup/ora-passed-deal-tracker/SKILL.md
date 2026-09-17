---
name: ora-passed-deal-tracker
description: Monthly sweep (15th, 06:30 ET) — detect trades of passed/flagged deals; log clearing price vs ORA walk to calibrate RCT + P(exec) bands (Buy Box v1.1-E-iii). Read-only calibration evidence gathering — never auto-adjusts governor weights/bands. Moved from LAMS/Cowork to CC/MCP 2026-08-15 (Gabriel-directed workflow-optimization item T3-12): the LAMS surface has no path to the Outlook COM send script, confirmed failing live 2026-08-15 ("SEND FAILURE — no COM access", ora-pm-ledger). [MODEL: claude-sonnet-5 | set 2026-08-15]
---

# ORA Passed-Deal Tracker (monthly — Buy Box v1.1-E-iii)

RESTORATION NOTE: Moved 2026-08-15 from the LAMS/Cowork fleet to CC/MCP (Gabriel-directed workflow-optimization item T3-12) — the LAMS surface cannot reach `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Windows-host Outlook COM script), and this task's own Step 7 requires it. Confirmed failing live 2026-08-15: ora-pm-ledger's run flagged "SEND FAILURE — ora-passed-deal-tracker — Email summary could NOT be sent — no COM access." Content otherwise unchanged from the LAMS original (restored 2026-07-07 after the 2026-07-05 machine migration). This task still only LOGS calibration evidence to Notion; it never adjusts Buy Box weights or bands itself. The LAMS twin (`OneDrive — Oxford Capital Partners\Documents\Claude\Scheduled\ora-passed-deal-tracker\`) must be disabled/retired from a Cowork session to avoid a duplicate run on the 15th — that surface is not reachable from this CC/MCP registration.

## Step 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-08-16; run before Step 1)

**This task is registered and ENABLED on BOTH fleets at the identical cron `30 6 15 * *`.** The CC/MCP copy (this file) was registered 2026-08-15 21:00 ET — its `lastRunAt: null` is benign, the registration simply landed ~14.5h after that day's 06:30 ET slot. The LAMS/Cowork twin (`OneDrive — Oxford Capital Partners\Documents\Claude\Scheduled\ora-passed-deal-tracker\SKILL.md`) is still `enabled: true`, `lastRunAt 2026-08-15T18:28:04.621Z`, `lastScheduledFor 2026-08-15T10:30:00.000Z`. The LAMS→CC move (`event_log.md`, 2026-08-15, item T3-12) was never completed, so **2026-09-15 is the first date on which both fleets fire this sweep** — and the documented fleet-wide catch-up burst can fire this copy twice on its own besides. Run this guard as the first action of the run:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-passed-deal-tracker --block main --run-id <session run_id> --ttl-min 30
```

Write it on ONE line — `^` is a cmd.exe continuation and hard-fails in both shells this host offers. This is a single-block task: the block id is `main` throughout (which the helper renders as `BLOCK_MAIN_*` tokens), and its state file is its own — `Claude_Workspace\_state\ora-passed-deal-tracker-block-completion.json`, keyed per task, so it cannot collide with `ora-am-brief`'s.

| Exit | Decision | This task does |
|---|---|---|
| **0** | `PROCEED` | Claimed. Continue to Step 1. |
| **10** | `SKIP_ALREADY_COMPLETE` | This month's sweep already completed. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, **skip the entire task** — no Notion write, no email — and report a **NORMAL skip** citing the earlier run's Notion artifact. |
| **11** | `STAND_DOWN_IN_PROGRESS` | Another fire claimed this run less than the TTL ago and is live right now. Stand down identically: log `BLOCK_MAIN_IN_PROGRESS_ELSEWHERE`, report a **NORMAL skip**. |
| **any other** | tooling failure | **FAIL OPEN — run the task normally**, and put the exit code and stderr **verbatim** in the run summary. Exit 2 is a malformed command (usually a missing `--task`); 9009/127 is a missing interpreter. Never read any of these as "already done". |

**A broken guard must never suppress the run.** This is a *monthly* task, so a wrongly-suppressed fire costs a full month of calibration evidence — strictly worse than the duplicate Notion row the guard exists to prevent. Fail-open is not a courtesy fallback here; it is the required behavior, and the only trace of a degraded Layer 1 is the `stateFileError` / `"persisted": false` fields you are required to surface at Step 10.

**Ownership — a claim at exit 0 means you MUST terminate the claim.** A run that claimed successfully must end in `complete` (Step 6 **or** Step 7, whichever output path it took) or in `fail` (Step 9). A run that stood down at exit 10 or 11 owns nothing and calls **NEITHER**: `fail` from a stood-down run would release the *live* run's claim and let a third fire start mid-generation, and a fabricated `complete` would silently suppress every later fire that ET date. Non-owner calls are refused with exit 12 and nothing is written. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

**`--force` is human-directed only — a scheduled fire must never pass it.** It overrides a `COMPLETE` record for a deliberate in-session re-run. A forced re-run must bypass **both** layers or it cannot re-send: Layer 2 would still find the earlier message in Sent Items, so the run would re-publish Notion and silently skip the mail. Pass `-Force` to `outlook-sent-probe.ps1` at Step 7a as well.

**Scope limit — this guard does NOT dedupe the LAMS twin, and does not close T3-12.** Layer 1's state file is keyed per *task*, not per fleet, and both fleets resolve the same OneDrive path — so cross-fleet dedup works by construction, but only for a fleet whose SKILL.md actually calls `claim`. The LAMS copy does not, and Layer 2 cannot cover it either: that surface has no Outlook COM path, which is the very reason T3-12 moved this task here (consistent with the 2026-08-15 LAMS run, which advanced `lastRunAt` but left no durable artifact — the newest `Passed-Deal Tracker` Notion page is still 2026-07-15 and `_shared/send-log.txt` has no entry for it that day). What this guard honestly protects against is **this** copy firing twice. Retiring the twin needs a Cowork-side `enabled:false` toggle and remains a separate open follow-up. Cheap interim mitigation if that slips past 2026-09-15: paste this same Step 0 into the LAMS copy — the shared state file will then dedupe the two fleets against each other. **Do not "fix" a double-fire by retiming this task's cron**; the burst is documented fleet-wide behavior and the guard belongs here.

## Steps
1. Read memory `acquisition-buy-box-v1` (space 0ef6698a-7103-4045-be6c-03fd76352016). If memory is unreachable in this unattended session, note it as a coverage gap and proceed with the Notion-sourced watch list only — do not fabricate the memory content.
2. Build the watch list from Notion Deal Sourcing Log
   (collection://9a6ae219-85a3-4621-899c-c757fd062f8b): Status in
   {Passed, Dead, Screened} OR Verdict in {PASS, KILLED} OR notes contain
   GATE-FLAGGED / FLOOR-FLAGGED — i.e., everything ORA saw and did not buy.

   **2a — LOST-AT-LOI arm (added 2026-08-16, P3 lost-deal ledger).** Additionally
   include every row where `LOI Outcome` in {LOST, PENDING, WINNER-BUSTED}. These
   are deals ORA actually bid on, and they are a DIFFERENT question from an
   ordinary pass: a pass tests the screen, a loss tests the bid. Rows on this arm
   get the Step 4b structured treatment, not just the prose log.

   **Do NOT gate this arm on the Acquisition Pipeline Tracker's `LOI Status`
   field — it is unreliable and disagrees with the Sourcing Log** (verified
   2026-08-16: `1333 Research Road` reads `Not Submitted` in the Pipeline Tracker
   while its Sourcing Log row reads `LOI Submitted`; `511 Industrial Mile Road`
   reads `Submitted` with no LOI Expiration Date). Same failure shape as the
   known-bad HubSpot `closedate` field. The Sourcing Log's `LOI Outcome` is the
   only field this task may branch on.

   **Watch for duplicate rows.** The Sourcing Log carries more than one row for
   at least one deal (`511 Industrial Mile Road` — `3446ecd8…` Status=Reviewing
   and `37c6ecd8…` Status=Dead, differing broker names, same address and SF).
   Match on normalized address, not on row identity, and never count two rows as
   two losses. Surface any newly-detected duplicate in the QUESTIONS FOR GABRIEL
   block rather than silently merging.
3. For each (batch by market): check for a sale/trade since last run via
   (a) the **County Sales Comps** Notion database FIRST — see below — then
   (b) `CoStar Exports\` folder under `Investment Candidates -- 2026\`
   (Gabriel drops exports; Excel preferred), then (c) web search
   (county auditor transfer records, Crexi/LoopNet sold listings, press).
   NO broker outreach — data gaps go to Gabriel as structured questions.

   **3a — query County Sales Comps before searching (added 2026-08-16).** The
   `county-sales-monitor` skill already accumulates recorded industrial sales into
   a Notion comps database on its own monthly cycle (304 transactions at launch).
   Read the data source id from `~/.claude/skills/county-sales-monitor/SKILL.md`
   rather than hardcoding it here. Querying it is cheaper and cleaner than
   re-searching the web for a deed this fleet already recorded, and it yields a
   `RECORDED-DEED` confidence rather than a press-release inference.

   Join on normalized street address, plus parcel id where the row carries one.
   Match guards, all mandatory:
   - **Date sanity** — the sale must post-date `LOI Sent Date` (or `First Sighted`
     if no LOI), and fall within ~24 months of it.
   - **Price sanity** — winning price within 0.3x–3.0x of the last known ask.
     Outside that band, flag; do not match.
   - **NONARMS rows NEVER auto-classify.** county-sales-monitor already flags
     non-arms-length/nominal transfers. A seller re-titling their own LLC looks
     identical to a sale to a new buyer from the outside. Inherit the flag and
     route the row to QUESTIONS FOR GABRIEL.
   - **Ambiguity is a null, not a guess.** Two candidate parcels, address variants,
     suite splits → `Winning Price Confidence = UNCONFIRMED` and surface it. Never
     silently pick the closer match.

   **Coverage is partial and must be stated, not implied.** The comps DB covers
   Franklin OH, Baltimore Co MD, and Polk IA only (Tier A). That is real coverage
   for Columbus, partial for Maryland (Baltimore Co ≠ Salisbury/Easton/Cambridge),
   and ZERO for Indianapolis, Cincinnati, Kansas City, Madison, Grand Rapids,
   Richmond, and Louisville — those fall through to (b)/(c) as before. **Missouri
   and Kansas are non-disclosure states: consideration is never published, so a
   Kansas City winning price can only ever be BROKER-RELAYED or UNCONFIRMED, and
   never RECORDED-DEED.** Say which channel produced each price. Do not expand
   county-sales-monitor's county coverage from this task — that is that skill's
   own documented next phase.
4. On a detected trade, log to the deal's Notion row ("Exception Outcome" if an
   exception, else "Notes / Flags"): clearing price, date, buyer if public, and
   CLEARING PRICE vs ORA WALK delta ($ and %). Also append one line to the
   Exception Register tab logic if the deal was an exception.

   **4b — LOST-AT-LOI rows: write STRUCTURED fields, not prose (added 2026-08-16).**
   For any watch-list row that arrived via the Step 2a arm, the free-text log above
   is not sufficient — it is unqueryable, which is the whole defect this arm exists
   to fix. Populate the Block B properties on the Deal Sourcing Log row:
   `LOI Outcome` · `Winning Price` · `Winning Price Confidence` · `Winner Entity`
   (grantee exactly as recorded) · `Winner Type` · `Winner Close Date` ·
   `Days LOI to Close` · `Winner Implied Basis (% RCT LOW)` (winning price +2%
   closing ÷ RCT v03 LOW for that market) · `Loss Class` · `Loss Evidence`.

   `Delta vs ORA Offer $` and `Delta vs ORA Offer %` are formulas — do not write them.

   **Then run the classifier.** Two orthogonal questions, then a label. Compare the
   `Winning Price` to `ORA Max Defensible Price` — the price at which the deal first
   breached a Stage 1 floor, **fixed at LOI time and never recomputed now**;
   recomputing it at outcome time is hindsight bias and is prohibited.

   | Rule | Condition | Loss Class |
   |---|---|---|
   | R1 | Winning > Max Defensible | **BASIS-DISCIPLINE** — matching required breaching a ratified floor. Losing was the strategy working. **No action.** |
   | R2 | Winning ≤ ORA Offer Price | **EXECUTION** — winner paid the same or less and still won. Speed/certainty/credibility loss. The only terms-free execution proof available. |
   | R3 | Offer < Winning ≤ Max Defensible, gap ≤ 5% of offer | **PRICE-MARGINAL** — inside noise. Break toward EXECUTION only on hard terms evidence; else UNCLASSIFIED. |
   | R4 | Offer < Winning ≤ Max Defensible, gap > 5% | **BASIS-ELECTIVE** — ORA could have paid it and chose not to stretch. A judgment call for the back-test, not a defect. |
   | R5 | Winner Type ∈ {Owner-User, 1031 Buyer} AND Winning > Max Defensible + 10% | **NON-COMPARABLE BUYER** (subclass of BASIS-DISCIPLINE) — an owner-user prices imputed rent and SBA leverage; a 1031 buyer prices a deadline. Never winnable. A sourcing lesson at most, never a bidding one. |
   | R6 | Winner's contract terminates / property returns to market | **WINNER-BUSTED** — discipline vindicated AND a re-engagement trigger (see 4c). |

   **`ORA Max Defensible Price` blank ⇒ `Loss Class = UNCLASSIFIED`. Always.** Without
   it neither Q1 nor the R3/R4 split can be evaluated, and a label asserted without it
   is fabricated. Say so in `Loss Evidence` and put the row in QUESTIONS FOR GABRIEL.
   The same applies where `Walk Price` and `ORA Offer Price` contradict each other
   (live example: `511 Industrial Mile Road` carries Walk $930,000 against a
   $1,450,000 LOI — those cannot both be right, so that row is held UNCLASSIFIED).

   **`Loss Evidence` is mandatory and must carry a citation** — source document,
   Notion row, deed reference, or named broker plus date. A classification with no
   source line is invalid; downgrade it to UNCLASSIFIED rather than shipping it.

   **This task NEVER proposes a higher offer, never recomputes a walk price, and
   never recommends bidding more.** BASIS-DISCIPLINE is a SUCCESS label. The one
   pro-action output permitted is the 4c re-engagement flag, which is a patience
   play, not a bid escalation. Weights and bands still move only at the December
   back-test with Gabriel's sign-off (Step 5 hard rule — unchanged).

   **4c — WINNER-BUSTED re-engagement (Gabriel-ratified 2026-08-16: flag + tickler).**
   When a winner's contract busts, set `LOI Outcome = WINNER-BUSTED`,
   `Loss Class = WINNER-BUSTED`, tick `Re-Engagement Flag`, and set
   `Re-Engagement Tickler Date` to a concrete follow-up date. Report it in the email.
   Do **not** draft or send the re-engagement mail — outbound counterparty contact
   needs Gabriel's in-turn confirmation. This generalizes the pattern Gabriel already
   built by hand for `511 Industrial Mile Road`, where a dedicated one-time task
   (`ora-511-industrial-fallout-check`, firing 2026-08-21) asks the broker whether the
   competing contract survived DD and financing. A row whose tickler date has passed
   with the flag still set is itself reportable — `808 Rhoads Avenue` sat 50+ days.

## Calibration use
5. Each logged trade calibrates two things (report, do not auto-adjust — this is a HARD RULE, not a suggestion):
   - RCT: implied $/SF vs RCT v02 point ± band for that market (flag if outside band);
   - P(exec) bands: did deals in each seller-signal band trade near ORA's walk?
   Tabulate cumulative evidence; recommendations go to the December back-test, run
   from `~/ora-skills/annual-cycle/SKILL.md` — weights and bands move ONLY there,
   and only with Gabriel's explicit sign-off. Do not duplicate the back-test in
   this task, and never write to any governor constant or Buy Box weight/band
   file directly from this task.

   **Repo path, not a skill name (2026-08-05):** `annual-cycle` was unpublished
   from the skill store (audit-driven fleet cleanup — usageCount 1 lifetime), so
   it is no longer Claude-invocable by name. The workflow itself is unchanged and
   the repo directory is untouched; read the SKILL.md directly rather than
   expecting the model to discover it by name.

## Output
6. If zero trades detected: one-line "no trades" note to Ops Hub; NO email.

   **Exception (added 2026-08-16): an overdue re-engagement tickler still emails.**
   Before taking this branch, check for Sourcing Log rows where
   `Re-Engagement Flag` is ticked and `Re-Engagement Tickler Date` has passed. A
   bust-and-re-engage window is time-sensitive and does not depend on a new trade
   being detected, so if any such row exists, take the Step 7 path instead and
   report it — otherwise the one output with a live clock is the one output that
   silently never sends. Zero trades AND zero overdue ticklers → this branch.

   **Close the entry guard on this path too.** This is the easy one to miss: the zero-trades branch sends nothing, so there is no send step to hang the terminal call off, and a run that ends here still holds the claim it took at Step 0. Once the Ops Hub note lands:

   ```
   python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-passed-deal-tracker --block main --run-id <run_id> --notion-page-id <Ops Hub note page id>
   ```

   No `--email-sent-at` on this path — no email was sent, and stamping one would misreport the artifact. A zero-trades sweep is a completed sweep, so `complete` is correct here, not `fail`.

7. If trades detected: post block to Notion Ops Hub (32b6ecd8) and email summary via
   the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`
   (Composio removed 2026-06-11 — no fallback connector exists; on a non-zero COM exit
   retry once, then flag, do not halt)
   FROM ggoldberg@oxfordra.net TO ggoldberg@oxfordra.net ONLY (no egoldberg cc —
   routing canon: only the Daily Brief retains that exception),
   ending with a "QUESTIONS FOR GABRIEL" block for any unverifiable trades.

   **"LOI POST-MORTEMS" section (added 2026-08-16).** If any Step 2a row resolved
   this sweep, add a section with ONE line per newly-resolved outcome:
   deal · ORA offer · winning price (confidence) · winner type · Loss Class ·
   evidence citation. Also list any row whose `Re-Engagement Tickler Date` has
   passed with `Re-Engagement Flag` still ticked. **If nothing resolved, print
   nothing** — no "no post-mortems this month" filler, no synthetic content.

   **MANDATORY sample-size banner.** While the count of rows with a `Loss Class`
   other than UNCLASSIFIED is **under 10**, every LOI POST-MORTEMS section must
   open with, verbatim:

   ```
   INSUFFICIENT SAMPLE (n=X) — per-deal lessons only; no trend claim.
   ```

   This is not decoration. At ORA's velocity (~5–12 LOIs/yr, ~3–8 losses)
   distinguishing a 70/30 basis-vs-execution split from a 30/70 needs ≈10–15
   classified losses — 18–36 months of accumulation. As of 2026-08-16 the
   classified count is **1**. Individual rows are actionable immediately (one
   confirmed R2 loss justifies fixing the proof-of-funds package on its own);
   *distributional* claims are not, and must not be made. This ledger is
   supposed to be boring for its first year.
   **Subject line (added 2026-07-21 — pm-ledger Check I, Frozen-Date Subject):** use the
   date this email is actually sent (`YYYY-MM-DD`, today's real date at send time), e.g.
   "ORA Passed-Deal Tracker — Monthly Sweep — 2026-08-15". Never use the nominal "15th"
   schedule date from this task's own description/cron, and never carry forward a prior
   run's date. Recurring/automated report subjects are never exempt from this — a subject
   dateline differing from the actual send date by more than 1 day is a MEDIUM defect
   under Check I and will keep recurring on every nominal-date run until this is fixed at
   the source (here) rather than caught downstream.

   **7a — Layer 2 pre-send probe. Run this immediately before the `send-via-outlook.ps1` call, not earlier.** It asks the mail store itself whether this month's summary is already sent, which is the backstop for Layer 1 — whose state file lives on OneDrive and can be rolled back or briefly unavailable to a sync conflict:

   ```
   powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt>"
   ```

   Probe the **full dated subject** — `ORA Passed-Deal Tracker — Monthly Sweep — YYYY-MM-DD`, using the same real send date the subject rule above fixes. The full string is correct here, and this is a deliberate departure from `ora-am-brief` Block C and `ora-deal-aging-sla`, which must probe a shortened dated stem: those subjects carry live counts or a run-composed headline in the tail that legitimately differ between two fires of the same day, so the full string would fail to match the earlier send and wave the duplicate through. **This** subject carries no counts and no run-composed text — it is fully determined by the send date — so it is stable across fires and safe to match on whole. Matching is substring and normalization-tolerant (dash family folded to `-`, non-ASCII dropped, casefolded), so the em-dash form written here still matches a plain-hyphen message in the store.

   **Always `-SubjectFile`, never a literal `-Subject`** — the em-dashes in this subject are mangled in transit on the command line.

   | Exit | Meaning | This task does |
   |---|---|---|
   | **0** | `NOT_SENT` | Proceed with the send. |
   | **10** | `ALREADY_SENT` | **Do NOT send.** Log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS` with the matched `sentOn` from the probe's JSON, record a **NORMAL skip** — and still record COMPLETE at 7b so Layer 1 re-converges with reality. |
   | **1** | `PROBE_ERROR` | **Fail open — send anyway**, and record the probe gap on the Notion page. Layer 1 already said PROCEED; suppressing a real monthly report because a probe broke is worse than a duplicate. |

   On the exit-10 path, pass the probe's matched `sentOn` as `--email-sent-at`, **not the current time** — the mail went out on the earlier fire, and stamping now misdates the artifact. If this run never held a claim (the state-file-lost path), say so explicitly by adding `--adopt`; without it `complete` is refused with exit 12 and nothing is written.

   **7b — close the entry guard** once the Ops Hub block and the send have both resolved:

   ```
   python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-passed-deal-tracker --block main --run-id <run_id> --notion-page-id <Ops Hub page id> --email-sent-at <ISO8601>
   ```

   Every field is required; a short form exits 2 and the run silently never records COMPLETE.
8. Never fabricate prices — unverified trades are listed as UNCONFIRMED with source link.

## Guard close-out
9. **On abort, record it — never leave the claim `IN_PROGRESS`:**

   ```
   python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-passed-deal-tracker --block main --run-id <run_id> --error "<what broke>"
   ```

   A dangling `IN_PROGRESS` is the state to avoid. It is invisible on the day it happens — the outputs may even have shipped — but the next fire past the 30-minute TTL reads the stale claim as a crashed run and regenerates everything. Before finishing, if this run claimed at Step 0, confirm it ended in `complete` or `fail`; `block-sentinel.py status --task ora-passed-deal-tracker --block main` is read-only and creates nothing.

10. **Run summary — emit one line, always.** State whether the sweep ran or was skipped, the guard token if any, the Notion artifact, and the send result. Surface any `stateFileError` or `"persisted": false` from the sentinel's JSON **verbatim** on that line: the guard fails open, so a degraded Layer 1 looks exactly like a normal run and those two fields are the only early warning. Shape:

    ```
    ora-passed-deal-tracker · SKIPPED (guard: BLOCK_MAIN_ALREADY_COMPLETE_TODAY) · artifact <page id> posted <time> ET by run <prior runId> · email already in Sent Items <sentOn> · NORMAL
    ```

    **A guard skip is a NORMAL skip, not a miss.** `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, `BLOCK_MAIN_IN_PROGRESS_ELSEWHERE`, and `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS` all mean the artifact for that ET date exists and was produced by the earlier fire — say so and cite it. `ora-health-guard` and `automation-health-monitor` read this summary; classing a correctly-suppressed duplicate as a failure trains a false alarm into the fleet and invites someone to "fix" it by removing the guard.