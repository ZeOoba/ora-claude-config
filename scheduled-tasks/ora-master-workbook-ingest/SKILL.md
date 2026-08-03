---
name: ora-master-workbook-ingest
description: Weekly Monday 05:45 ET producer — re-ingests the live ORA Master Workbook (cell-accurate local read-only extraction, 49 tabs), refreshes the Notion Portfolio Intelligence Dashboard, writes a dated Portfolio Metrics snapshot, maintains the Open Workbook Corrections register, updates DSOR freshness state. Keeps the canonical data mirror within 7-day freshness for downstream consumers. Conditional email to ggoldberg only on failure/material drift/insurance escalation. v1.3 2026-08-03 (read-only openpyxl promoted to PRIMARY read path; mandatory tie-out battery incl. rent-roll→NOI gross income; STEP 4e corrections register; STEP 6(b) already-escalated carve-out). [MODEL: UNVERIFIABLE | checked 2026-07-08]
output_contract:
  version: 1
  blocks:
    - id: block-portfolio-metrics-snapshot
      artifact:
        type: notion_page
        title_pattern: "Portfolio Metrics Snapshot — {DATE} (Master Workbook ingest)"
        parent_id: 3386ecd8-9e59-8166-af49-da066dc7ca14
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon]
      skip_condition: "STEP 2 NO-OP GUARD: if the workbook's lastModifiedDateTime is unchanged since the last recorded ingest, the run logs a one-line no-op to Ops Hub and STOPS before STEP 4 — no new snapshot page is written that week. A missing snapshot on a given Monday is not automatically a failure; cross-check the DSOR page (3706ecd8-9e59-813a-b4c7-ecbc2c213fa8) §5/§6 and the Ops Hub for a same-day no-op log line before alarming."
      on_missing_severity: warn
      is_primary_health_signal: true
      notes: "Parent (Knowledge Base) id verified against SKILL.md STEP 4b text. Downgraded to warn, not alarm, because of the documented no-op skip path above — this is a known, accepted limitation of this contract, not an oversight."
    - id: block-portfolio-dashboard-refresh
      artifact:
        type: notion_page
        page_id: 3396ecd8-9e59-819c-a598-e55dc5581504
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon]
      skip_condition: "Same STEP 2 no-op guard as block-portfolio-metrics-snapshot — the dashboard's 'Last refreshed' line only advances on a non-no-op run."
      on_missing_severity: info
      is_primary_health_signal: false
      notes: "Secondary/redundant signal to the dated snapshot page above; kept at info severity given the same no-op ambiguity."
---

PROVENANCE: v1.1 registered 2026-05-30. CC/MCP registry destroyed by the 2026-07-05 app reinstall; restored 2026-07-07 as a thin pointer-stub redirecting to a "corrected" OneDrive spec file. That OneDrive file was itself deleted during the 2026-07-08 fleet reconciliation (not archived — collateral damage from an unrelated cleanup pass; see `~/.claude/_confidential-staging/2026-07-08_LAMS-fleet-recovery/2026-07-08_LAMS-fleet-audit_v01.md`, which covers the LAMS fleet only and does not mention this break), leaving the stub pointing at nothing ahead of the 2026-07-13 05:45 fire. **v1.2 (this file) makes the spec fully self-contained** to eliminate the redirect-to-an-external-file pattern that has now caused two consecutive breakages. Do not reintroduce a pointer to an external spec file for this task.

Run the ORA Master Workbook ingest. You are a senior financial-systems operator for Oxford Realty Advisors. Each run starts fresh with no memory; everything you need is below. Follow the ORA Institutional Style Guide v1.0+.

OBJECTIVE
Refresh the Notion mirror of firm data from the LIVE Master Workbook so downstream consumers (cash-position monitoring, inbox briefs, dashboards, live artifacts) read data no more than ~7 days stale. The workbook — not Notion — is the system of record. This task is READ-ONLY against the Master Workbook itself — it never writes to the workbook, only to its Notion mirror.

CANONICAL POINTER
Read the DSOR page first: Notion page 3706ecd8-9e59-813a-b4c7-ecbc2c213fa8 ("ORA Data Source of Record (DSOR) — Master Workbook"). It defines read order, IDs, and the freshness rule. If anything below conflicts with that page, the page wins.

STEP 1 — READ THE LIVE WORKBOOK (system of record)
READ-PATH ORDER (revised 2026-08-03 — Desktop Commander demoted after failing to connect on two consecutive runs, 07-27 and 08-03; the openpyxl path carried both runs cleanly and is structurally incapable of writing):
  PRIMARY — **local read-only openpyxl extraction.** `openpyxl.load_workbook(path, data_only=True, read_only=True)`, iterate `ws.iter_rows(values_only=True)`, NEVER call `.save()`. This is the preferred path because it cannot mutate the workbook even on an error path, it does not depend on an MCP server being up, and it returns exact cell values with no truncation. Two caveats you must respect: (i) `data_only=True` returns Excel's **cached** values, so a cell Excel has never calculated comes back `None` rather than a number — if a whole column reads `None`, suspect a non-recalculated workbook and say so rather than reporting zeros; (ii) to read a FORMULA (e.g. when diagnosing a defect for the corrections register) you must load a second time with `data_only=False`. See 1c — read-only openpyxl is endorsed; openpyxl **writes** remain banned.
  EQUAL-ALTERNATIVE — Desktop Commander local read (`mcp__Desktop_Commander__read_file` with `sheet=<tab name>`, optional `range="Sheet!A1:Z99"`; returns exact JSON 2D arrays). Equally cell-accurate. Use it when the MCP is connected and you prefer it; do not spend the run trying to revive it if it is not.
  LAST RESORT — the M365 connector render described under SECONDARY below. Truncating; flag anything past the cutoff as MISSING.
  Whichever path you use, state it in the DSOR §6 change-log line and on the Dashboard header.
The workbook is OneDrive-synced on Gabriel-Laptop at:
  C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx
  (2026-07-17: `eric spreadsheets\` is in the OneDrive Business/Personal split's Ambiguous bucket — deliberately NOT moved, still at OneDrive root — do not prepend `Business\` to this path. Verified 2026-07-07/08 — do NOT use a "(1)"-suffix variant; that path is stale/ENOENT. If a future OneDrive re-sync reintroduces a "(1)" or "(2)" suffix folder — a known OneDrive collision artifact — re-verify with get_file_info before relying on either path.)
  1. Freshness: capture the file's `modified` timestamp (= workbook lastModifiedDateTime) and the sheet list. Any of these work — use whichever is available: `mcp__excel__get_workbook_metadata` (returns both `modified` and `sheets` in one call), a local `stat` on the path, or `mcp__Desktop_Commander__get_file_info`. Confirm the `sheets` array (**should be 50 tabs**: 35 model sheets + the 15-tab EXPORT layer = 13 EXPORT_* data tabs + EXPORT_Index + EXPORT_README. History: this line asserted 34 until 2026-07-16, then 49 until 2026-08-03. **The 49 was wrong** — counted live via Excel COM `Workbooks.Sheets.Count` on 2026-08-03 and cross-checked with openpyxl: 50, of which 9 are hidden (Claude Log, AMFee_Combined, the six loan-detail sheets, 99_Archive_Log). The 2026-08-03 ingest reported "49 tabs confirmed" because it echoed this line's expected value instead of counting — **COUNT the array, do not pattern-match it to the number written here**. A count below 50 means tabs are genuinely missing; a count above 50 means the model grew — report it, do not "restore" any earlier figure). If the path is missing (sync gap), fall back to SECONDARY and flag it.
  1b. The EXPORT layer is the machine-readable read path and is the intended source for any flat, one-row-per-record consumer. Per its own `EXPORT_README`: every cell is a LIVE FORMULA pulling from the model sheets (e.g. `='Master Tenant Rent Roll'!A81`), so it always reflects the last recalculation — there is no refresh step. `EXPORT_RentRoll` (137 tenant rows; `Property · Tenant Name · Unit · Company · Sq Ft · Monthly Rent · Rent/SF · Lease Start · Lease End · Escalation Date · Escalation % · Status · Vacant · Annual Rent`) is the designated source for the planned Notion Tenant-DB mirror — see `Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`. **NEVER write to an EXPORT_* tab** — every cell is a formula; a write destroys the link. Write only to the source model sheet.
  1c. **WRITING to this workbook (any task, any reason): use Excel COM, never openpyxl.** (This bans openpyxl *writes* only — read-only openpyxl is the PRIMARY read path above, and is safe precisely because it never saves.) openpyxl warns "Conditional Formatting extension is not supported and will be removed" on save — a lossy round-trip on Eric's model — and `data_only=True` + save flattens every formula in all 51 tabs to static values. Also: the workbook is OneDrive-hosted, so Excel **AutoSave can persist a cell before an error path can roll it back** — a COM exception (e.g. the transient `RPC_E_CALL_REJECTED` seen 2026-07-16) does NOT mean the write was undone. Back up first, then diff against the backup to establish ground truth. This task is READ-ONLY against the workbook regardless; this note exists so a future writer does not learn it the hard way.
  1d. **COM WRITE PROTOCOL — every rule below was learned by breaking it on 2026-08-03. Follow all six.**
      (i) **NEVER save on a failure path.** Set a `$success` flag, save only when it is true, and make teardown `$wb.Close($success)`. On 2026-08-03 a `finally { $wb.Close($true) }` persisted a HALF-APPLIED multi-sheet change: the Northwood loan was left in both the external and internal books and `00_Home!D7` published **$20,355,291**, inflated by exactly $2.8M, until it was spotted and completed. A partial financial-model write that saves is worse than one that fails loudly.
      (ii) **Probe the target before a structural edit.** `EXPORT_*` sheets are `ProtectContents = True` AND hold ListObjects — a plain `Rows.Insert()` fails on both counts. Add rows via `ListObject.ListRows.Add(pos)`, unprotecting first and re-protecting after. Check `ProtectContents` / `ListObjects.Count` up front rather than discovering it mid-transaction.
      (iii) **Attach to a running Excel; never open a second instance against the same file.** `GetActiveObject('Excel.Application')` first, `New-Object` only if that throws. A second instance takes a read-only copy and silently discards the save — a strong candidate for how earlier "fixes that didn't stick" were lost.
      (iv) **Leave the user's session as you found it.** Track separately whether YOU opened the instance and whether YOU opened the workbook. Close only the workbook you opened; `Quit()` only an instance you created. Never quit an Excel that has the user's own files in it.
      (v) **A row insert/delete on a shared sheet is not local.** `Assumptions` is referenced across the model — a single inserted row there shifts every downstream reference and named range (Excel re-points them, but VERIFY). After any structural change run a workbook-wide error sweep (`UsedRange.SpecialCells(xlCellTypeFormulas, 16)` per sheet) and confirm zero error cells before saving.
      (vi) **Hand-enumerated formulas do not extend.** Before inserting a loan/entity row, grep the sheet for expressions like `=(H5+H6)-(H7)` that name cells individually instead of a range — they shift but never widen, silently dropping the new row from that metric. `Portfolio Summary — Internal!C16` was exactly this. The same class caused four separate defects in one day (`Cash Balances!A2`, `Loan Index` internal total, both EXPORT mirrors).
  2. Read each SoR tab cell-accurately via the PRIMARY path above. Read the FULL tab. Do NOT rely on the SharePoint text render — it hard-truncates at ~100K chars and silently drops External Loans Summary / Portfolio Summary — Internal / Loan Index / Cash Data.
  KEY CELLS to lock: External Loans Summary — borrower total, lender block (negative = capital deployed), and the "Portfolio LTV" cell (net external debt ÷ Oxford value, distinct from 00_Home gross LTV). Portfolio Summary — Internal — per-loan Current Balance + PORTFOLIO TOTALS + top-concentration. Cash Data — the as-of date is MAX(header date row), NOT the Cash Balances summary A2 label. Cash Balances' embedded historical table also lags the current column by ~2 periods (diagnosed 2026-07-08 — newest balances get pasted into an existing older-dated row instead of a newly appended one; a `..._pre-A2fix_2026-06-09.xlsx` backup in `Documents\Claude\_backups` shows a prior fix attempt that didn't stick). Property NOI — portfolio totals row. Assumptions — all rates.
SECONDARY (fallback only) — Microsoft 365 connector read_resource with URI:
  file:///b!fogSrIGhzUeBSf98j4jg7JBJQDYJDw5Og7B2gKTH8HDkm61VkL_ZQYZmGfTNXL9f/01ABKEESVJPJNG6AC7F5DKUNFUHRCN5AUM
  Saved to a file with offset/limit paging — read fully in chunks; capture lastModifiedDateTime via sharepoint_search "Master Excel Template Company Wide Oxford". WARNING: this render truncates at ~100K chars; treat any tab past the cutoff as MISSING — flag it, do NOT silently reconstruct or carry forward.
Source-of-truth tabs: 00_Home, Property NOI, Master Tenant Rent Roll, Cash Balances, Cash Data, Loan Index, External Loans Summary, Portfolio Summary — Internal, Insurance Renewals, Assumptions, Monthly Checklist (added 2026-07-16 — the 31/59-item close checklist lives as an in-workbook sheet, not a separate file; `ora-pm-ledger`'s EOD Ledger already reads it live daily, this weekly ingest should carry it into the Notion mirror too).

STEP 2 — NO-OP GUARD
Fetch DSOR page §5. If the workbook lastModifiedDateTime is unchanged since the last recorded ingest, log a one-line no-op to the Operations Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062) and STOP — do not rewrite the dashboard or send email.

STEP 3 — EXTRACT CANONICAL METRICS
From the SoR tabs compute, at minimum: portfolio SF / value / NOI / DSCR / LTV / cap rate / equity / CoC (Oxford share and 100%); rent roll totals (tenant count, annualized & monthly rent, weighted $/SF, top tenant, top-5 concentration, WALT); external borrower & lender debt (balances, rates, maturities), internal loan book and concentration; cash by entity and total; insurance policy status counts and expirations (track per-policy status across runs — see STEP 6 escalation rule); lease-expiration windows. Reconcile to 00_Home headline figures (QC gate — note any variance > tolerance).

MANDATORY TIE-OUTS (run all of these; report each as PASS with the figure, or as a QC exception with the variance — a tie-out you did not run is a QC exception, never silence):
  T1. Portfolio Value = Σ Property NOI "Oxford Value" column.
  T2. 00_Home Total Debt = External Loans Summary borrower total + Portfolio Summary — Internal PORTFOLIO TOTALS.
  T3. 00_Home "Portfolio LTV" = external borrower total ÷ Portfolio Value (GROSS-external definition) AND External Loans Summary's own "Portfolio LTV" = net external position ÷ Portfolio Value (NET-external definition). These are two different cells with two different definitions — never conflate them, and always label which one you are quoting.
  T4. DSCR = Σ Oxford NOI ÷ Σ Debt Service, and cap rate = Σ Oxford NOI ÷ Portfolio Value.
  T5. **RENT ROLL → PROPERTY NOI GROSS INCOME (added 2026-08-03; verified exact to the cent on that run).** For each property, multiply its Master Tenant Rent Roll Annual Rent subtotal by that property's Oxford ownership share (Assumptions tab — 50% for 9050 Red Branch, 1900 N Broadway, 3883, Fenton, Restoration Church; 100% otherwise), then sum. The result must equal Property NOI's "Gross Income (Oxford)" total **exactly**. Note the Sepich Portfolio row aggregates five rent-roll properties (Banwick, Morrison, Zettler, 4595 E. 5th, 4601 E. 5th) into one Property NOI line — group accordingly.
      *Why this one earns its place:* it makes drift attribution mechanical instead of inferential. When portfolio value or NOI moves materially, T5 tells you immediately whether the cause is leasing (rent roll moved, tie-out still holds) or a valuation/cap-rate/expense change (rent roll flat, NOI moved anyway). On 2026-08-03 it converted a bare "value −$980,408" into "value fell because contractual rent fell $59,735 and most values are formula-driven as NOI ÷ cap" — a reportable cause rather than a guess.
  T6. Cash total = Σ entity balances for the newest Cash Data column.
  Where a tie-out fails because of a KNOWN open workbook defect, do not re-derive it from scratch — check the Open Workbook Corrections register (STEP 4e) first and reconcile against the corrected figures recorded there.

STEP 4 — REFRESH THE MIRROR (do NOT create duplicate databases)
a. Update the Portfolio Intelligence Dashboard (Notion page 3396ecd8-9e59-819c-a598-e55dc5581504): replace the metric tables and set the "Last refreshed" line to today with the workbook lastModifiedDateTime cited.
b. Write a dated archive page "Portfolio Metrics Snapshot — [date] (Master Workbook ingest)" under the Knowledge Base (3386ecd8-9e59-8166-af49-da066dc7ca14), same structure as prior snapshots.
c. If the ora-master-dashboard / ora-cash-position artifacts exist, refresh their numbers. Reliable channel: mcp__Desktop_Commander__edit_block in place on the artifact index.html (e.g. C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Artifacts\<id>\index.html — no "(1)" suffix; verified 2026-07-08, that directory currently has no artifacts, so this step is a no-op) — the cowork Edit tool is blocked there (outside connected folders) and mcp__cowork__update_artifact requires a full faithful HTML reproduction. Patch the `const D = {…}` data object + header "As of" stamp.
d. Update DSOR page 3706ecd8-9e59-813a-b4c7-ecbc2c213fa8 §5 "Current state" with the new workbook lastModifiedDateTime and today's ingest date; append a §6 change-log line.
e. [added 2026-08-03] Maintain the **Open Workbook Corrections register** — Notion page 3b16ecd8-9e59-8153-8c9e-f264e301b3ca, under the Operations Hub. This is the aging ledger for workbook defects that only Eric or Gabriel can fix (this task is READ-ONLY against the workbook, and Hard Invariant 4 blocks it from touching the model). It exists so a correction's AGE lives in one durable place instead of being re-narrated as prose in every weekly email.
   For each OPEN row: re-check it against the live workbook this run, then update `Runs open`, `Age (days)`, and add/refresh a `Last verified` note. **Verify — do not assume it is still open.** A row you did not actually re-check is an unverified null, not a confirmed-open item; say which ones you checked.
   If a correction is now fixed in the workbook, MOVE the row to the Resolved section with the run date that confirmed it. Never delete a row — the register is append-and-move-only, so the history of how long each defect ran stays legible.
   If this run finds a NEW defect requiring a workbook edit, add a row (next WBC-### id) plus a Detail & proposed fixes subsection: the offending cell, the current formula or value, the root cause, and a concrete proposed fix. Diagnose the root cause before filing — read the actual formula with `data_only=False` rather than describing the symptom. A row whose detail is only a symptom is worth far less to Eric than one carrying the formula and the replacement.
   Then reference the register (by link, one-line status each) in the Dashboard's QC Exceptions section and in the STEP 6 email — do NOT restate each correction's full detail in the email. The register holds the detail; the email holds only what changed.

STEP 5 — PUBLICATION GUARD
For each Notion write, capture pages[0].id; retry once on failure; verify by title search. Apply the shared _shared\PUBLICATION_GUARD.md pattern if present.

STEP 6 — CONDITIONAL NOTIFICATION
Email if any of:
  (a) any Notion publication failed after retry, or
  (b) a QC reconciliation variance > tolerance — SUBJECT TO THE ALREADY-ESCALATED CARVE-OUT BELOW, or
  (c) the workbook lastModifiedDateTime is itself > 14 days old (upstream not being updated), or
  (d) [added 2026-07-08] any Insurance Renewals policy has appeared in EXPIRED status for 3+ consecutive ingest runs (compare this run's expired policy list against the last 2 DSOR/Ops-Hub change-log entries by Policy #/RowID). As of 2026-07-07's run this condition is ALREADY MET for INS-FVC-PCKG, INS-FVC-BCL, INS-ETCPOA-PCKG, INS-ETCPOA-BCL, INS-1100RARIG-PCKG, INS-1100RARIG-BCL (expired since ≤2026-06-09, 4+ consecutive runs) and INS-3883LIVINGSTON-PCKG, INS-3883LIVINGSTON-BCL (expired since 2026-06-11, 3 consecutive runs as of 2026-06-22/07-07) — the next run that reaches this step should include these in the alert even if (a)-(c) are otherwise clean. Do not re-alert on the same policy every subsequent run once it has fired once under this rule — track "already escalated" via a note in the Ops Hub log line and only re-fire if newly crossing the 3-run threshold or after a gap.
ALREADY-ESCALATED CARVE-OUT FOR (b) [added 2026-08-03 — ports the hygiene rule that (d) has had since 2026-07-08; before this, suppressing a repeat QC alert depended entirely on the operator's judgment, and the 2026-08-03 run had to reason it out from first principles]:
  A QC exception that is (i) unchanged in substance since the last run, AND (ii) already reported to Gabriel in a prior run's alert, AND (iii) recorded as an OPEN row in the Open Workbook Corrections register (STEP 4e) does **NOT**, on its own, trigger an email. It is carried in the register and stated in the Dashboard's QC Exceptions section instead.
  Such an exception DOES appear in the email — as a one-line reminder with its age and a link to the register, never a re-narration — whenever an email is being sent for some other reason.
  It RE-FIRES on its own merit only when one of these is true:
    • it materially changes (the figure, the affected cells, or the corrected values move);
    • it crosses the **4-run / 28-day aging threshold** measured from first flagging — an aging re-fire, so a correction can never go quiet forever just because it is old news. Re-arm the counter after each aging re-fire, and record in the register that it fired;
    • it was previously reported RESOLVED and has regressed.
  Rationale, so a future run does not "helpfully" undo this: re-alarming Gabriel weekly about a decision he has already made trains him to ignore the alert channel, which is the failure mode this whole notification step exists to avoid. Silence on an aging defect is the opposite failure. The register plus the aging threshold is what buys both.
  This carve-out governs (b) ONLY. Conditions (a) and (c) always fire — a publication failure and a stale upstream workbook are never "old news."

Route via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (write the body to a temp file via Desktop Commander `write_file`, then `-BodyFile`; Composio removed 2026-06-11, no fallback connector exists — on a non-zero COM exit retry once, then flag, do not halt). `-To "ggoldberg@oxfordra.net"` ONLY (no egoldberg cc — routing canon: only the Daily Brief cc's Eric). Subject on failure/escalation: "[ALERT] ora-master-workbook-ingest — [reason] — [date]". Do NOT use the legacy Rube namespace. On a clean run with no escalation, post a one-line success log to the Operations Hub only — no email.

Output format and tone per ORA Institutional Style Guide v1.0+.