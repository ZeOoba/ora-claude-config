---
name: ora-passed-deal-tracker
description: Monthly sweep (15th, 06:30 ET) — detect trades of passed/flagged deals; log clearing price vs ORA walk to calibrate RCT + P(exec) bands (Buy Box v1.1-E-iii). Read-only calibration evidence gathering — never auto-adjusts governor weights/bands. Moved from LAMS/Cowork to CC/MCP 2026-08-15 (Gabriel-directed workflow-optimization item T3-12): the LAMS surface has no path to the Outlook COM send script, confirmed failing live 2026-08-15 ("SEND FAILURE — no COM access", ora-pm-ledger). [MODEL: UNVERIFIABLE | checked 2026-10-08]
---

# ORA Passed-Deal Tracker (monthly — Buy Box v1.1-E-iii)

RESTORATION NOTE: Moved 2026-08-15 from the LAMS/Cowork fleet to CC/MCP (Gabriel-directed workflow-optimization item T3-12) — the LAMS surface cannot reach `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Windows-host Outlook COM script), and this task's own Step 7 requires it. Confirmed failing live 2026-08-15: ora-pm-ledger's run flagged "SEND FAILURE — ora-passed-deal-tracker — Email summary could NOT be sent — no COM access." Content otherwise unchanged from the LAMS original (restored 2026-07-07 after the 2026-07-05 machine migration). This task still only LOGS calibration evidence to Notion; it never adjusts Buy Box weights or bands itself. The LAMS twin (`OneDrive — Oxford Capital Partners\Documents\Claude\Scheduled\ora-passed-deal-tracker\`) must be disabled/retired from a Cowork session to avoid a duplicate run on the 15th — that surface is not reachable from this CC/MCP registration.

## Step 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-08-16; run before Step 1)

**This task is registered and ENABLED on BOTH fleets at the identical cron `30 6 15 * *`.** The CC/MCP copy (this file) was registered 2026-08-15 21:00 ET — its `lastRunAt: null` is benign, the registration simply landed ~14.5h after that day's 06:30 ET slot. The LAMS/Cowork twin (`OneDrive — Oxford Capital Partners\Documents\Claude\Scheduled\ora-passed-deal-tracker\SKILL.md`) is still `enabled: true`, `lastRunAt 2026-08-15T18:28:04.621Z`, `lastScheduledFor 2026-08-15T10:30:00.000Z`. The LAMS→CC move (`event_log.md`, 2026-08-15, item T3-12) was never completed, so **2026-09-15 is the first date on which both fleets fire this sweep** — and the documented fleet-wide catch-up burst can fire this copy twice on its own besides. Run this guard as the first action of the run:

```
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-passed-deal-tracker --block main --run-id <session run_id> --ttl-min 30
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

   **2b — DUPLICATE-EXCLUSION FILTER (added 2026-09-19, Gabriel-directed).** Apply
   `AND Exclude from Calibration is unchecked (treat null as false)` to EVERY arm of
   the watch list above (Status/Verdict arm, flag-notes arm and 2a). Rows retired as
   duplicates carry that checkbox plus `Duplicate Of` (plain `app.notion.com/<id>`
   text naming the canonical row); status `Dead` alone did NOT remove them, which is
   how the three `3849 N Richardt Ave` rows all entered the 2026-09-19 read-back. SQL
   form: `coalesce("Exclude from Calibration",'__NO__') <> '__YES__'` (verified
   2026-09-19: 146 rows without the clause, 123 with it, the 23 flagged rows
   dropped). Canonical rows stay unflagged and stay on the list. The address-match
   and QUESTIONS-FOR-GABRIEL instruction above remains the backstop for any duplicate
   not yet flagged — never count two rows as two losses. Do not clear or set the
   checkbox from this task; flagging is Gabriel-directed or `deal-retirement` step 3a.

   **2c — DILIGENCE-EXIT arm (added 2026-09-19, Gabriel-directed).** Additionally
   include every row where `LOI Outcome = TERMINATED-DILIGENCE`. These are deals ORA
   bid on or put under contract and then exited **on its own diligence findings** —
   title, environmental, physical inspection, financing, seller default. This is a
   THIRD question, distinct from both arms above: a pass tests the screen, a loss
   tests the bid, a diligence exit tests **diligence-stage discovery and the P(exec)
   band**. Rows on this arm get the Step 4e treatment and are **excluded from 4b** —
   there is no competitor and no clearing price, so 4b's comparison has no operand.

   `TERMINATED-DILIGENCE` is mutually exclusive with 2a's `{LOST, PENDING,
   WINNER-BUSTED}` by construction: one row, one `LOI Outcome`. **A row that is
   plainly a diligence exit but still carries `LOST` or `PENDING` is NOT re-tagged by
   this task** — writing the arm key is a lifecycle write, owned by `deal-retirement`
   or Gabriel. Report it under QUESTIONS FOR GABRIEL as a mis-keyed row, naming the
   field and the value it should hold, and hold it out of 4b for that sweep (4b's own
   exclusion clause covers this). 2b's `Exclude from Calibration` filter applies to
   this arm exactly as to the others.
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

   **3b — RE-MARKETED PASSES (added 2026-09-22).** For every watch-list row (after the
   duplicate-address merge), search the Outlook inbox with `outlook_email_search`
   over the trailing 35 days, once for the street address (street number + street
   name) and once for the property name if the row has one. Never open links.
   - Ignore ORA's own mail: any @oxfordra.net sender AND the Exchange
     legacy-DN form (`/O=EXCHANGELABS/…/CN=…GGOLDBERG`) — ORA's own digests
     (Daily Brief, sourcing scans, this task's prior runs) quote these
     addresses and were the majority of raw hits in the 2026-09-22 dry run.
     Also ignore `notifications@github.com`. Real hits are broker blasts and
     listing-alert senders (e.g. `@crexi.com`, `@loopnet.com`).
   - A hit requires the street number AND street name in subject or body; a
     name-only or partial match is **UNCONFIRMED** (listed, never escalated).
   - Extract an asking price only if stated as a dollar figure tied to the
     property; otherwise price = unknown (listing alerts usually omit it —
     report the sender + date so Gabriel can check the listing himself).
   - Walk threshold = `Walk Price`; if blank, `ORA Max Defensible Price`
     (LOI-stage rows only). Last known ask = `Asking Price`; if blank,
     `Ask at First Sighting`. Never back-compute either.
   - Classify: **INSIDE-WALK** if ask ≤ walk threshold (confirmed hits only) ·
     **PRICE-CUT x%** if ask < last known ask · else **RE-MARKETED**.
   - Any INSIDE-WALK forces the email path even when zero trades were found.
   - Read-only: no Notion writes, no outreach drafts. A row with no walk
     threshold can be PRICE-CUT or RE-MARKETED, never INSIDE-WALK.
   - Dry run 2026-09-22 (validation): 8720 Robbins Rd (PASS 2026-07-14,
     Walk $1,054,066) → Crexi alerts 2026-08-30 and 2026-09-16, no price →
     RE-MARKETED. 808 Rhoads / 6150 Avery / 1255 N Winchester → only ORA
     self-mail or >35 days → no hit.
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

   **4b EXCLUSION — diligence exits never run through this classifier (added
   2026-09-19).** A row with `LOI Outcome = TERMINATED-DILIGENCE` is out of scope for
   4b entirely: skip it here and run Step 4e instead. R1–R6 all pivot on a competitor's
   `Winning Price`, and there is no competitor — running them would produce a
   permanent, unfillable `UNCLASSIFIED` on a row that is not unclassifiable, only
   differently classified, and would pollute the QUESTIONS FOR GABRIEL block every
   month with a question that has no answer.

   **The same exclusion applies to a row still mis-keyed `LOST` or `PENDING`** where
   the evidence shows ORA itself terminated on its own diligence finding with no
   competing bidder and no clearing price — hold it out of 4b for this sweep, run 4e's
   analysis on it, and report the mis-keyed field under QUESTIONS FOR GABRIEL. Do not
   re-tag `LOI Outcome` from this task (2c). Live example as of 2026-09-19: `E Fulton
   St Portfolio` (`37a6ecd8-9e59-8156-912e-dd9680cb1660`) — executed PSA $4.0M
   4/21/2026, ORA terminated 7/9/2026 on the AEI Phase II environmental finding, no
   competing bidder; routed to `LOST` on 2026-09-19 before this arm existed.

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

   **4d — PASSED-DEAL RE-CHECK scan (added 2026-09-19, Gabriel-directed; additive and
   read-only).** ORA's passed-deal watch-date convention puts a re-engagement trigger for
   a deal it never bid on in the Sourcing Log row's `Notes / Flags`, as one line
   `RE-CHECK: YYYY-MM-DD - <trigger>` (`~/ora-skills/deal-retirement/SKILL.md` Killed Deal
   Retirement step 3d, v1.4). The `Re-Engagement Flag` / `Re-Engagement Tickler Date` pair
   is NOT used for these — it stays scoped to 4c's WINNER-BUSTED arm — so this scan is the
   only thing that surfaces them.

   Over the Step 2 watch list already in hand, scan each row's `Notes / Flags` for lines
   matching `RE-CHECK:` and parse the ISO date that follows. Report any whose date is
   **already past or falls within the next 30 days**, one line each:
   deal · date · trigger text verbatim · days until/overdue.

   - **Read-only.** Do not tick `Re-Engagement Flag`, do not set a tickler date, do not
     write a `Loss Class`, and do not contact anyone — a `RE-CHECK` deal was never bid on,
     so none of 4b's classifier applies to it. Outbound contact is Gabriel's call.
   - **A malformed or unparseable `RE-CHECK:` line is reported verbatim under QUESTIONS FOR
     GABRIEL, never silently dropped and never date-guessed.**
   - **Scope limit, stated so it is not mistaken for coverage:** this scan changes nothing
     about when this task sends. Since 2026-11-05 every sweep takes the Step 7 email path
     anyway, because Step 5b's back-test block (or its WARN line) promotes it; see the last
     Step 6 exception. A due `RE-CHECK` list therefore rides that email's PASSED-DEAL
     RE-CHECKS DUE section and the Ops Hub post. A due `RE-CHECK` line on its own still
     promotes nothing.

   **4e — DILIGENCE-EXIT classifier (added 2026-09-19, Gabriel-directed). Requires NO
   competitor price.** For every row that arrived via the Step 2c arm, produce the block
   below. Nothing here compares ORA against another bidder, because there was none.

   Record, in order — a field that cannot be sourced is written `UNK`, never inferred:

   1. **Exit cause** — exactly one of `environmental` · `title` · `physical-inspection` ·
      `financing` · `seller-default` · `other`. `other` requires a one-clause description.
      Two contributing causes → name the one that independently justified termination and
      list the second in the evidence citation; never write two causes.
   2. **Stage of discovery** — `psa_exec` (PSA execution date), `discovered` (date the
      finding first landed in a document ORA holds — the report date, not the date it was
      read), `terminated` (termination notice date), and the two derived integers
      `days_to_discovery` and `days_to_termination`, both measured from `psa_exec`. The
      gap between them is the decision latency and is reported, not judged.
   3. **Price at exit vs walk price** — contract price in force at termination, the `Walk
      Price` on the row, and the delta in $ and %. Both figures are read as recorded at
      the time; **the walk price is never recomputed now** — the same hindsight-bias
      prohibition that governs `ORA Max Defensible Price` in 4b applies here verbatim.
   4. **Would it have been caught earlier — THIS IS THE CALIBRATION OUTPUT.** Answer both
      halves separately, against the row's own contemporaneous fields (`DD-Critical
      Status`, `Edge Findings`, `Score Components`, `Gate Review`), not against what is
      known now:
      - **Pre-LOI screen:** was the risk visible, and did the screen price it? Three
        outcomes only — `SCREEN-CAUGHT-AND-PRICED` · `SCREEN-SAW-BUT-DID-NOT-PRICE` ·
        `SCREEN-BLIND`.
      - **DD checklist:** did the checklist item that found it exist, and did it run on
        time? `DD-CHECKLIST-CAUGHT-IT` · `DD-CHECKLIST-ITEM-MISSING` · `DD-RAN-LATE`.
      A finding the screen listed as an open unknown and the DD then confirmed is a
      process **working**, not a defect — say so plainly. Only `SCREEN-BLIND` or
      `DD-CHECKLIST-ITEM-MISSING` is a gap.
   5. **Carry-forward** — does the cause map to (a) a proposed **pre-LOI screen gate**,
      (b) a proposed **DD-checklist item**, (c) **both**, or (d) **neither** (a genuine
      one-off or a market risk that is priced, not gated)? State the proposed gate or
      item in one line. **PROPOSAL ONLY.** It goes to the December back-test with every
      other recommendation this task produces (Step 5) — this task never edits a
      checklist, a screen gate, a Buy Box weight, or a P(exec) band.
   6. **P(exec) reconciliation** — the `P(exec) %` recorded on the row at LOI/PSA time
      against the realized outcome (`NON-EXECUTION`, always, on this arm). Report the
      pair. Do **not** adjust the band, do not propose a new band number, and do not
      recompute the recorded value. The standing rule is unchanged: bands move ONLY at
      the December back-test with Gabriel's explicit sign-off.

   **Notion writes on this arm — read-only apart from the same logging the other arms
   already do.** Write exactly ONE field: `Loss Evidence`, as a single line in this fixed
   format, so it stays greppable without a new column:

   ```
   DILIGENCE-EXIT | cause=<...> | psa_exec=<ISO> | discovered=<ISO> | terminated=<ISO> |
   days_to_discovery=<n> | days_to_termination=<n> | price_at_exit=<$> | walk=<$> |
   delta_vs_walk=<$ / %> | p_exec_at_loi=<%> | realized=NON-EXECUTION |
   caught_earlier=<screen-verdict> / <dd-verdict> | carry_forward=<...> | src=<citation>
   ```

   Write it on ONE physical line. **A `src=` citation is mandatory** — source document,
   Notion row, or named report plus date. No citation ⇒ write nothing to Notion and put
   the row in QUESTIONS FOR GABRIEL, exactly as 4b downgrades an uncited classification.

   **Citation form — avoid a bare `*.md` filename token in `src=` (added 2026-09-19 from
   the Stage 1 apply).** Notion's rich-text editor auto-links a bare filename such as
   `deal-decision-ledger.md` into a hyperlink on write. The visible text is unchanged, so
   the fixed format and a `WHERE Loss Evidence LIKE 'DILIGENCE-EXIT |%'` grep both still
   hold, and the existing E Fulton line is **not** to be rewritten (re-writing the
   property re-triggers the same auto-link). For new rows, prefer a citation with no bare
   `*.md` token — e.g. `memory/deal-decision-ledger (2026-07-09 row)`. If this format is
   ever machine-parsed rather than grepped, this becomes mandatory rather than preferred.

   **Never written by this arm:** `Loss Class` (a diligence exit is not a loss — leaving
   it blank also keeps the Step 7 sample-size denominator honest, since that count is
   defined over `Loss Class`), `Winning Price`, `Winning Price Confidence`, `Winner
   Entity`, `Winner Type`, `Winner Close Date`, `Days LOI to Close`, `Winner Implied
   Basis`, `Re-Engagement Flag`, `Re-Engagement Tickler Date`, `Exclude from
   Calibration`, `LOI Outcome`, `Status`, and every governor/Buy Box file. A
   diligence-exit row stays ON the calibration list; it is different evidence, not
   excluded evidence.

## Calibration use
5. Each logged trade calibrates two things (report, do not auto-adjust — this is a HARD RULE, not a suggestion):
   - RCT: implied $/SF vs RCT v02 point ± band for that market (flag if outside band);
   - P(exec) bands: did deals in each seller-signal band trade near ORA's walk?
   Tabulate cumulative evidence; recommendations go to the back-test (Step 5b below).
   Weights and bands move ONLY with Gabriel's explicit sign-off, never from this task.
   Never write to any governor constant or Buy Box weight/band file directly from this
   task.

   **"The December back-test" (named in Steps 4b and 4e and in other specs) means Step
   5b's 2026-12-15 run, reviewed with Gabriel** (added 2026-11-05). Until then the phrase
   pointed at `~/ora-skills/annual-cycle/SKILL.md`, which never carried a back-test step and
   moved its year-in-review to late February (annual-cycle v1.2, 2026-10-30), so every
   recommendation routed there had no destination.

5b. **SOURCING BACK-TEST (monthly; added 2026-11-05, Gabriel in-turn "Monthly back-test
   block").** Report-only: it reads eight read-only exports and computes calibration
   evidence. It never writes Notion, a weight, a band, a gate or a doctrine file, and never
   sets a Verdict or Loss Class. Run it on every sweep, after Step 4 and before Step 6/7. The
   engine is `C:/Users/Owner/.claude/maintenance/funnel-backtest.py`; its docstring holds the
   eight queries verbatim (`QUERY_A` once per partition value, `QUERY_B`, `QUERY_P`,
   `QUERY_N`). Copy them from there, never from memory.
   (i) Make the folder `C:/Users/Owner/AppData/Local/Temp/ora-backtest-YYYY-MM-DD/`, where
   YYYY-MM-DD is the run date's date part only (the same date the Step 7 subject uses; never
   the weekday). Run each query with `notion-query-data-sources` against
   `collection://9a6ae219-85a3-4621-899c-c757fd062f8b`, and write each RESPONSE OBJECT
   verbatim (Write tool, UTF-8, keeping its `has_more` key) into that folder:
   `a_t1.json`, `a_t2.json`, `a_pass.json`, `a_killed.json`, `a_none.json` (QUERY_A with
   params `["T1 PURSUE"]`, `["T2 WATCH"]`, `["PASS"]`, `["KILLED"]`, `["(none)"]`),
   `b_t1rows.json` (QUERY_B), `p_pexec.json` (QUERY_P) and `n_count.json` (QUERY_N, the
   log's total row count, which the engine reconciles against the five partitions). Do not
   edit, merge, drop or reorder anything. If a query errors (quota, schema), stop 5b and
   record one WARN line naming the query and the error; never re-run a query to get it right.
   (ii) Run, from that folder:

   ```bash
   cd C:/Users/Owner/AppData/Local/Temp/ora-backtest-YYYY-MM-DD
   python C:/Users/Owner/.claude/maintenance/funnel-backtest.py --rows a_t1.json --rows a_t2.json --rows a_pass.json --rows a_killed.json --rows a_none.json --t1-rows b_t1rows.json --pexec-rows p_pexec.json --expect-rows n_count.json --out-md backtest.md
   ```

   Exit 0: `backtest.md` goes verbatim into the Step 7 email as its SOURCING BACK-TEST
   section and onto the Ops Hub post. Exit 2: record one WARN line quoting its `[FATAL]` line
   verbatim; never hand-fix an input file and re-run.
   (iii) Any change the block prompts (a gate, a weight, a band, a doctrine edit) is a
   proposal for Gabriel, listed under QUESTIONS FOR GABRIEL, never an action.

   **Repo path, not a skill name (2026-08-05):** `annual-cycle` was unpublished
   from the skill store (audit-driven fleet cleanup — usageCount 1 lifetime), so
   it is no longer Claude-invocable by name. The workflow itself is unchanged and
   the repo directory is untouched; read the SKILL.md directly rather than
   expecting the model to discover it by name.

## Output
6. If zero trades detected: one-line "no trades" note to Ops Hub; NO email, unless an exception below promotes the sweep to Step 7. Since 2026-11-05 one always does (Step 5b's back-test block or its WARN line; see the last exception), so this no-email branch now applies only when Step 5b did not run at all. **Ops Hub create (this note and Step 7's block):** if the create returns a grace/quota notice or no page ID, look for it — `notion-fetch` the Ops Hub parent (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`, full UUID) for an exact-title child, then search by the exact title (search lags: a miss alone is not proof) — a match created at/after the create call is this run's page, use it (its id is the `--notion-page-id`); never blind-retry a create (it produced a duplicate). After a grace/quota notice with no match, do not retry: the create is UNVERIFIED — close with `complete` (no `--notion-page-id`), stating UNVERIFIED in the run summary and the email body — never `fail`, which would release the claim and invite a duplicate create on the next fire. Quota errors → `notion-quota-fallback` skill. **If Step 4d
   found any passed-deal `RE-CHECK:` line due or overdue, carry that list on the Ops Hub
   note** (added 2026-09-19) — it is the only surface this branch writes, and a due
   re-check that lands nowhere is the same silent-loss failure 4d was added to close.
   **Carry any Step 4e DILIGENCE-EXIT block on that same Ops Hub note** (added
   2026-09-19), one line per row, same rule.

   **The send gate is NOT widened by 4e. Stated explicitly so a later reader does not
   "fix" it:** a diligence exit is a post-mortem on a decision ORA already made and
   already acted on — it carries no live clock. Exactly two conditions promote a zero-trades
   sweep to the Step 7 email path: 4c's overdue re-engagement tickler, and (since
   2026-11-05) Step 5b's back-test block or WARN line. A 4e block on its own never does.

   **Exception (added 2026-08-16): an overdue re-engagement tickler still emails.**
   Before taking this branch, check for Sourcing Log rows where
   `Re-Engagement Flag` is ticked and `Re-Engagement Tickler Date` has passed. A
   bust-and-re-engage window is time-sensitive and does not depend on a new trade
   being detected, so if any such row exists, take the Step 7 path instead and
   report it — otherwise the one output with a live clock is the one output that
   silently never sends. Zero trades AND zero overdue ticklers → this branch, unless the
   next exception applies.

   **Exception (added 2026-11-05, Gabriel in-turn "Monthly back-test block"): a Step 5b
   block or WARN line also takes the Step 7 path,** so the back-test reaches Gabriel by
   email every month even when nothing traded. Step 5b produces one or the other on every
   sweep, so in practice every sweep now emails; this branch's Ops Hub rules carry over to the
   Step 7 post unchanged. On a zero-trades sweep, Step 7's email opens with
   `No trades detected this sweep.` in place of the trades block. This is the one deliberate
   widening of the send gate. 4e still does not widen it.

   **Close the entry guard on this path too.** This is the easy one to miss: the zero-trades branch sends nothing, so there is no send step to hang the terminal call off, and a run that ends here still holds the claim it took at Step 0. Once the Ops Hub note lands:

   ```
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-passed-deal-tracker --block main --run-id <run_id> --notion-page-id <Ops Hub note page id>
   ```

   No `--email-sent-at` on this path — no email was sent, and stamping one would misreport the artifact. A zero-trades sweep is a completed sweep, so `complete` is correct here, not `fail`.

7. If trades detected: post block to Notion Ops Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062` — always the FULL UUID; the 8-char prefix `32b6ecd8` also matches the retired "Cowork OS — Master Index" page `32b6ecd8-9e59-81a9-a566-e3ed1b1c9a9e`, which is where the 2026-10-13 sweep landed by mistake) and email summary via
   the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`
   (Composio removed 2026-06-11 — no fallback connector exists; on COM exit 2 or 4
   retry once, then flag, do not halt; on exit 5 or 6 do NOT retry and never resend (send state unknown — the message MAY have gone out), flag loudly in the run summary and the failure record named above)
   FROM ggoldberg@oxfordra.net TO ggoldberg@oxfordra.net ONLY (no egoldberg cc —
   routing canon: only the Daily Brief retains that exception),
   ending with a "QUESTIONS FOR GABRIEL" block for any unverifiable trades.

   **"LOI POST-MORTEMS" section (added 2026-08-16).** If any Step 2a row resolved
   this sweep, add a section with ONE line per newly-resolved outcome:
   deal · ORA offer · winning price (confidence) · winner type · Loss Class ·
   evidence citation. Also list any row whose `Re-Engagement Tickler Date` has
   passed with `Re-Engagement Flag` still ticked. **If nothing resolved, print
   nothing** — no "no post-mortems this month" filler, no synthetic content.

   **"SOURCING BACK-TEST" section (added 2026-11-05).** Step 5b's `backtest.md` verbatim,
   or its WARN line. Always printed, every month: it is the calibration record that the
   scan doctrine's evidence tags and P(exec) bands are judged against. Do not summarize,
   re-round or re-label its numbers.

   **RE-MARKETED PASSES** — table: Property · Flag · Ask · Last ask · Max Defensible ·
   Broker/sender · Email date. Omit the section when there are no hits; UNCONFIRMED
   hits are listed in a sub-table.

   **"PASSED-DEAL RE-CHECKS DUE" section (added 2026-09-19).** If Step 4d found any
   `RE-CHECK:` line already past or due within 30 days, add a section listing one line per
   row: deal · date · trigger verbatim · days until/overdue. Same rule as above — **if
   nothing is due, print nothing.** These are not post-mortems and must not be folded into
   that section or counted toward its sample-size banner: a `RE-CHECK` deal was never bid
   on and carries no `Loss Class`.

   **"DILIGENCE EXITS" section (added 2026-09-19).** If Step 4e produced any block this
   sweep, add a section with ONE line per row:
   deal · exit cause · days PSA→discovery / PSA→termination · price at exit vs walk ($ and
   %) · P(exec) at LOI → realized · screen verdict / DD verdict · carry-forward · citation.
   **If nothing was produced, print nothing** — no filler, no "no diligence exits this
   month."

   **This section is separate from LOI POST-MORTEMS and must not be merged into it, and
   its rows must NOT be counted in that section's `INSUFFICIENT SAMPLE (n=X)` banner.**
   That banner counts classified *losses* — rows carrying a `Loss Class` other than
   UNCLASSIFIED — and a diligence exit carries no `Loss Class` at all (4e). Folding these
   rows in would inflate the ledger's apparent sample toward the 10–15 threshold with
   evidence about a different question, which is the precise failure the banner exists to
   prevent. If a diligence-exit count is ever wanted in the digest, it is its own separate
   count with its own label.

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
   run date (`YYYY-MM-DD` — the run date computed once at run start with `date '+%A %Y-%m-%d'`, date part only, reused verbatim in the subject, the 7a probe and the Ops Hub note), e.g.
   "ORA Passed-Deal Tracker — Monthly Sweep — 2026-08-15". Never use the nominal "15th"
   schedule date from this task's own description/cron, and never carry forward a prior
   run's date. Recurring/automated report subjects are never exempt from this — a subject
   dateline differing from the actual send date by more than 1 day is a MEDIUM defect
   under Check I and will keep recurring on every nominal-date run until this is fixed at
   the source (here) rather than caught downstream.

   **7a — Layer 2 pre-send probe. Run this immediately before the `send-via-outlook.ps1` call, not earlier.** It asks the mail store itself whether this month's summary is already sent, which is the backstop for Layer 1 — whose state file lives on OneDrive and can be rolled back or briefly unavailable to a sync conflict:

   ```
   powershell -ExecutionPolicy Bypass -File C:/Users/Owner/.claude/scheduled-tasks/_shared/outlook-sent-probe.ps1 -SubjectFile "<temp .txt>"
   ```

   Probe the **full dated subject** — `ORA Passed-Deal Tracker — Monthly Sweep — YYYY-MM-DD`, using the same run date the subject rule above fixes. The full string is correct here, and this is a deliberate departure from `ora-am-brief` Block C and `ora-deal-aging-sla`, which must probe a shortened dated stem: those subjects carry live counts or a run-composed headline in the tail that legitimately differ between two fires of the same day, so the full string would fail to match the earlier send and wave the duplicate through. **This** subject carries no counts and no run-composed text — it is fully determined by the send date — so it is stable across fires and safe to match on whole. Matching is substring and normalization-tolerant (dash family folded to `-`, non-ASCII dropped, casefolded), so the em-dash form written here still matches a plain-hyphen message in the store.

   **Always `-SubjectFile`, never a literal `-Subject`** — the em-dashes in this subject are mangled in transit on the command line.

   | Exit | Meaning | This task does |
   |---|---|---|
   | **0** | `NOT_SENT` | Proceed with the send. |
   | **10** | `ALREADY_SENT` | **Do NOT send.** Log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS` with the matched `sentOn` from the probe's JSON, record a **NORMAL skip** — and still record COMPLETE at 7b so Layer 1 re-converges with reality. |
   | **1** | `PROBE_ERROR` | **Fail open — send anyway**, and record the probe gap on the Notion page. Layer 1 already said PROCEED; suppressing a real monthly report because a probe broke is worse than a duplicate. |

   On the exit-10 path, pass the probe's matched `sentOn` as `--email-sent-at`, **not the current time** — the mail went out on the earlier fire, and stamping now misdates the artifact. If this run never held a claim (the state-file-lost path), say so explicitly by adding `--adopt`; without it `complete` is refused with exit 12 and nothing is written.

   **7b — close the entry guard** once the Ops Hub block and the send have both resolved:

   ```
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-passed-deal-tracker --block main --run-id <run_id> --notion-page-id <Ops Hub page id> --email-sent-at <ISO8601>
   ```

   Every field is required; a short form exits 2 and the run silently never records COMPLETE.
8. Never fabricate prices — unverified trades are listed as UNCONFIRMED with source link.

## Guard close-out
9. **On abort, record it — never leave the claim `IN_PROGRESS`:**

   ```
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-passed-deal-tracker --block main --run-id <run_id> --error "<what broke>"
   ```

   A dangling `IN_PROGRESS` is the state to avoid. It is invisible on the day it happens — the outputs may even have shipped — but the next fire past the 30-minute TTL reads the stale claim as a crashed run and regenerates everything. Before finishing, if this run claimed at Step 0, confirm it ended in `complete` or `fail`; `block-sentinel.py status --task ora-passed-deal-tracker --block main` is read-only and creates nothing.

10. **Run summary — emit one line, always.** State whether the sweep ran or was skipped, the guard token if any, the Notion artifact, and the send result. Surface any `stateFileError` or `"persisted": false` from the sentinel's JSON **verbatim** on that line: the guard fails open, so a degraded Layer 1 looks exactly like a normal run and those two fields are the only early warning. Shape:

    ```
    ora-passed-deal-tracker · SKIPPED (guard: BLOCK_MAIN_ALREADY_COMPLETE_TODAY) · artifact <page id> posted <time> ET by run <prior runId> · email already in Sent Items <sentOn> · NORMAL
    ```

    **A guard skip is a NORMAL skip, not a miss.** `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, `BLOCK_MAIN_IN_PROGRESS_ELSEWHERE`, and `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS` all mean the artifact for that ET date exists and was produced by the earlier fire — say so and cite it. `ora-health-guard` and `automation-health-monitor` read this summary; classing a correctly-suppressed duplicate as a failure trains a false alarm into the fleet and invites someone to "fix" it by removing the guard.