# ORA Scheduled-Tasks Starter Pack (HISTORICAL — written for the 2026-06-06 rebuild)

> **⚠ SUPERSEDED 2026-06-10/11 (dual-fleet doctrine):** the "LAMS is orphaned" framing below
> is WRONG as of 2026-06-10 — LAMS (`local-agent-mode-sessions` registry) is Cowork's ACTIVE
> store (4 live recurring tasks); the CC/MCP store holds 14. `fleet-deadman.ps1` was re-pointed
> dual-fleet (v3, 2026-06-10). Email send is COM-only since 2026-06-11 (Composio removed — any
> Composio mention below is historical). Current truth: session-context.md + memory tech.md §3
> + the fleet disposition ledger. This file is retained as a rebuild-procedure reference only.

The old 29-task LAMS fleet was believed orphaned at rebuild time (the app's Scheduled-tasks panel showed zero). The
underlying `SKILL.md` files are INTACT on disk, so each rebuilt task just points at its
existing skill — no logic re-pasted, all recipients/Notion IDs/send paths preserved.

**How to add each:** Claude Desktop → Scheduled tasks → **New task** → paste the Prompt →
set the Schedule (times are ET) → keep **Keep awake = ON** (these run only while the PC is awake).

**Order to add:** 1 (brief) → 4 (self-audit) → 2 (deal scan) → 3 (ledger) → 5 (health guard, recommended).
Stagger the times exactly as given so two tasks never fire in the same minute.

---

## 1 — ORA Morning Brief   ·   Daily, 06:10 AM ET
```
Run the ORA Morning Brief. Open and follow this skill file EXACTLY as written — it is the authoritative, self-contained spec; do not improvise:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-am-brief\SKILL.md
Execute all applicable blocks in order (A Rate Prefetch → B Daily Brief 9-section report → C Inbox Pre-Brief → D Cash Snapshot), branching by today's ET day-of-week per the file's cadence table. Use the recipients, Notion page IDs, and Outlook send path named in the file (send-via-outlook.ps1 PRIMARY → mcp__composio-ora__OUTLOOK_SEND_EMAIL fallback). Daily Brief → ggoldberg + egoldberg; Inbox/Cash → ggoldberg only. Do NOT email anyone not named in the file. Do NOT modify settings.json, ~/.claude config, hooks, or any memory file.
```

## 2 — ORA Deal-Sourcing Scan   ·   Weekly, Tuesday 07:20 AM ET
```
Run the ORA weekly on-market deal-sourcing scan. Open and follow this skill file EXACTLY:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-deal-sourcing-scan\SKILL.md
Scan the nine target-market clusters for new/re-listed/price-cut industrial-flex listings, screen against the ORA buy-box, score with the Ranking-workbook weights, DEDUPE against the Notion Deal Sourcing Log (data source 9a6ae219) and Acquisition Pipeline (bcfe4a03) before writing, then email a ranked digest from ggoldberg@oxfordra.net to ggoldberg + egoldberg via mcp__composio-ora__OUTLOOK_SEND_EMAIL. Report only verifiable listings with a working URL — never fabricate a listing/price/NOI; mark estimates [EST]. Do not contact any broker. Do not duplicate the off-market distress monitor's work.
```

## 3 — ORA Evening Ledger   ·   Daily, 06:00 PM ET
```
Run the ORA Evening Ledger. Open and follow this skill file EXACTLY:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-pm-ledger\SKILL.md
Execute the three blocks in order (A Notion Daily Digest → B Outbox QC Sweep [weekdays] → C EOD Action Ledger), branching by ET day-of-week per the file. Use the send paths/recipients in the file (Digest & EOD → ggoldberg + egoldberg; Outbox QC → ggoldberg only; send-via-outlook.ps1 PRIMARY → composio-ora fallback). Block C's autonomy is bounded by its HARD GUARDRAILS in the file: no counterparty send, no production deploy, no money movement, no system-of-record mutation. Do NOT modify settings.json, ~/.claude config, hooks, or memory files.
```

## 4 — ORA Setup Self-Audit (daily health routine)   ·   Daily, 06:30 AM ET
```
Run the ORA daily setup self-optimization routine. Open and follow this prompt file EXACTLY:
C:\Users\Owner\.claude\daily-setup-audit-prompt.md
Run all probes using the FULL python interpreter path (bare `python` is not on PATH in scheduled sessions):
  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/setup-self-audit.py
  ...then fleet-status.py, doctrine-integrity-probe.py, governor-drift-probe.py, memory-integrity-probe.py the same way.
Triage findings SCREEN/WATCH/PASS. EMIT a dated digest (YYYY-MM-DD_setup-self-audit.md) to the canonical outputs folder. Per the ORA guard doctrine (I6): do NOT modify settings.json, hooks, CLAUDE.md, memory files, or the scheduler registry — list anything requiring those as PROPOSED actions in the digest for Gabriel to approve. If verdict is CRITICAL, also draft (do not auto-send) an alert email to ggoldberg@oxfordra.net. Mondays only: also run the cutting-edge radar (read-only WebFetch of hesreallyhim/awesome-claude-code + anthropics/claude-plugins-official) and append a 3-5 line shortlist.
```

## 5 — ORA Health Guard (recommended 5th — produces the 05:25 mirror the Morning Brief falls back to)   ·   Daily, 05:15 AM ET
```
Run the ORA Health Guard. Open and follow this skill file EXACTLY:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-health-guard\SKILL.md
Execute blocks in order A (scheduled-task SKILL.md integrity self-heal — add-only, never delete) → B (connector pre-flight + morning mirror email, MUST go out before the 06:10 Morning Brief) → C (probe suite: fleet-status + governor-drift + memory-integrity + confidentiality self-test) into ONE [ORA] Health Guard status email to ggoldberg@oxfordra.net only. Use the full python path C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe. HARD LINE per the file: this task EMITS reports/proposals only — it must NOT write settings.json, hooks, CLAUDE.md, memory files, or the scheduler registry; report drift with a proposed fix, do not apply it.
```

---

### Notes
- **Times are de-conflicted:** 05:15 (health) · 06:00 (ledger PM) · 06:10 (brief) · 06:30 (self-audit) · 07:20 Tue (deal scan). No two share a minute.
- **All send paths preserved** from the original skills: `send-via-outlook.ps1` PRIMARY → `composio-ora` fallback. After the Composio key rotation, confirm one task's email lands before trusting the fleet.
- **`fleet-deadman.ps1` re-point:** the Windows watchdog still reads the OLD orphaned registry. Once these new tasks run, that registry stays frozen → false alarms. Re-point or disable it once we confirm where the new UI stores run-state (or rely on the GitHub Actions `ora-cowork-watchdog`).
- **Not rebuilt (deliberately):** the ~24 lower-value/never-ran tasks from the old fleet (quarterly/annual/one-offs). Add them back only if/when needed — this lean 5 covers daily acquisition velocity + ops + self-optimization.
