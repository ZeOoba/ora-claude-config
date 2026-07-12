---
name: rules
description: "All standing ORA working rules and validated preferences, merged from the former feedback_*.md files. Sectioned by domain. Current-state; incident history lives in event_log.md."
metadata: 
  node_type: memory
  type: rules
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
---

# ORA Standing Rules & Preferences

Merged 2026-06-03 from: feedback_workflow, feedback_email_outlook_only, feedback_digest_recipients,
feedback_qb_desktop, feedback_netlify_mcp, feedback_less_permission_prompts, feedback_csp_preload_onload.

---

## 1. Working style & velocity

- **Never overwrite existing configs without reading them first.** `settings.json` holds custom hooks, MCP permissions, env vars — a blind overwrite destroys months of config. Always read `settings.json`, `CLAUDE.md`, and any change-log before a write that touches them.
- **Check what already exists before installing/creating anything.** Gabriel has ~70 skills, 9 MCP connectors, a fully configured system. Source-of-truth for ORA-built skills is the Cowork OS path (git `github.com/ZeOoba/ora-skills`).
- **No fake features.** Claude Code has no `/plugin` command or marketplace. Stick to real mechanisms: skills, MCP servers, hooks, CLAUDE.md.
- **Proceed without asking on:** file creation, file moves, folder creation (within Claude-system working surfaces — see carve-out below).
- **Always ask before:** file deletion, external communications, modifying financial models, sending emails, **moving/transferring money**, **touching oxfordra.net** (edit/build/deploy — repos `website-canonical`/`oxford-site`/live Netlify site; broadened 2026-06-05 from "never deploy" to "never touch"), and **writing/moving/deleting in the non-Claude Oxford Capital OneDrive business folders** under `OneDrive - Oxford Capital Partners/` (path corrected 2026-07-09 — the prior `(1)`-suffixed path was the stale, incomplete duplicate folder per `reference_memory_scope_fragmentation.md`; reading for analysis is fine — only writes need permission; Claude-system paths like Cowork OS / Claude_Workspace / brain repo / `~/.claude` remain the free working surface). (Velocity on non-destructive; explicit confirmation on irreversible.)
- **OneDrive root business/personal scope (2026-07-09, no files moved):** before any broad search/scan of the OneDrive root for business-focused work (deal search, tenant/property lookup, accounting), consult `reference_onedrive_business_scope.md` and scope to its Business list. Never surface or reason over its Personal list for business work; treat its Ambiguous list as needing Gabriel's one-line confirmation first. A physical Business/Personal folder split was proposed 2026-07-09 (`Claude_Workspace/00_Governance/outputs/2026-07-09_OneDrive-Business-Personal-Split_Proposal_v01.md`) but not executed — this scope file makes the split usable immediately without waiting on that decision.
- **Be direct about diminishing returns.** Flag when further additions won't move the needle before building them.
- **Audit-ledger convention (2026-07-09):** before launching any setup/system audit, grep memory for a same-day or superseding `project_*-audit` entry — extend it, don't duplicate. (Motivating incident: the 2026-07-09 morning and evening audits independently re-derived overlapping findings; several evening items were already closed by the morning session.)

## 2. Email — Outlook only, no Gmail

- Gabriel uses **Outlook (Microsoft 365) only**. Never use Gmail for drafts, notifications, automation, or any email delivery.
- **Send path:** Outlook COM via PowerShell is the SOLE path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (uses authenticated desktop profile; no OAuth/tokens). **Composio fallback REMOVED 2026-06-11** (connector gone). On non-zero COM exit: retry once, then flag loudly (Notion completion row; automation-health-monitor producer-beacon check catches the silent send) — do NOT halt, never route through Composio/Rube/Gmail.
- **Rube is retired (EOL 2026-05-15) — never reference or route to it.**
- **Zapier is out of space** (since 2026-04-16) — do not recommend or design around Zapier. Use Outlook COM, Power Automate (if premium), or local PowerShell.

## 3. Digest & report recipients

- **Routing:** canonical rule → `CLAUDE.md` Email & scheduler section (supersedes the old cc-both default, re-ratified 2026-06-10). In Outlook COM, semicolon-delimit if a send legitimately has multiple recipients.

## 3b. HubSpot — current tenants ONLY (Gabriel 2026-06-11)

- HubSpot's scope at ORA is **tracking current tenants** — it is NOT a broker, deal, or general-relationship CRM.
- Broker/counterparty last-contact truth = **Outlook** (M365 search). Missing or stale broker records in HubSpot are expected, never defects to "fix."
- Do not propose HubSpot backfills, dedupes, or workflows for brokers/deals; tenant-side use (tenant-intelligence, monthly-close HubSpot items) is unchanged.

## 4. QuickBooks — Desktop only

- ORA runs **QuickBooks Desktop** (not QBO) across ~20 LLC company files.
- **Never recommend "re-auth the QuickBooks MCP."** The Intuit MCP (`52fa80c0-…`) is QBO-only and structurally incompatible — no QBO tenant exists.
- Current workflow: **QB Desktop → SharePoint export → skill parse** (monthly-close, re-operations, exception-detection). Acceptable at monthly cadence.
- Future programmatic bridge: **CData ODBC/JDBC** wrapped in a thin custom MCP. Only pursue if Gabriel needs *daily* (not monthly) cadence — ask that question first.
- If any skill/doc still says "QB MCP — requires OAuth re-auth," flag it as stale.

## 5. Netlify deploys

- **Try the Netlify MCP first** (`mcp__a66aaa4a-…__netlify-*`); on any error fall back to `npx netlify-cli` (authenticated as ggoldberg@oxfordra.net) — do not retry the MCP. Key commands: `sites:list`, `deploy`, `status`.
- oxfordra.net Site ID: `95ac0a0f-a84d-4400-b919-b8d7a8526646`.
- Do NOT recommend "reconnect the connector" as a fix — past failures were server-side, not auth.
- **Never deploy oxfordra.net without explicit request.**

## 6. Permissions — keep the allowlist current (DORMANT under §10 bypass regime, 2026-06-12)

- **Superseded while §10 is in force:** defaultMode is `bypassPermissions`, so allowlist upkeep changes nothing — do NOT proactively offer `less-permission-prompts`. Keep the allowlist intact as the fallback if the mode is ever reverted.
- (Dormant rule, kept for reversion:) `less-permission-prompts` only expands the allowlist for safe, read-only, already-used commands. **Never** add destructive operations (`rm`, `push --force`, etc.) without explicit approval.

## 7a. Confidentiality — egress surfaces & staging (verified 2026-06-11)

- **Egress surfaces (hook-blocked, fail-closed):** `Claude_Workspace/00_Governance/outputs/` is classified mirror/build output — the confidentiality guard BLOCKS confidential-deal terms there (proven in production twice on 2026-06-11: the audit report draft and the Cowork port artifact). Treat all outward-mirroring `outputs/` trees, the site repos, Notion external pages, and email the same.
- **Sanctioned staging for confidential-deal artifacts until closing:** `~/.claude/_confidential-staging/`, UNTRACKED files only — the canonical home for active deal-bound working files (put new ones here directly, not loose at the `~/.claude` root). `~/.claude` is a git repo pushing to `github.com/ZeOoba/ora-claude-config` (PRIVATE) — anything git-ADDED reaches an off-machine remote. The fail-closed `.gitignore` (`/*` default-deny) ignores the whole `_confidential-staging/` subtree, so files land untracked by default; never `git add` a file carrying a deal name. `session-context.md` (untracked, root) remains the sanctioned roster home. (Loose deal-bound `*.md` at the root still works but fires check-8 `[MISSING]` noise every run — use the subfolder.)
- **Enforcement:** `maintenance/doctrine-integrity-probe.py` check 8 scans CLAUDE.md + every git-tracked `*.md` + untracked root `*.md` for active confidential terms (index-only reporting). Surfaced via a git pre-push blocking gate (`hooks/git-prepush-doctrine-gate.py`, in-band) plus the daily `ora-doctrine-integrity-guard` scheduled task (push-independent backstop, alarms via Notion Ops Hub + best-effort email; corrected 2026-07-08 — the prior weekly eos-health-report email mechanism was retired, see event_log). The `_confidential-staging/` subtree is exempt from the untracked scan (narrow to that one dir; `CONFIDENTIAL_STAGING_DIRNAME` in the probe) — but only for UNTRACKED files: a git-tracked file there is still scanned. The session-context exemption auto-revokes if that file is ever git-tracked.
- **Owner-ratified repo exception (2026-06-14):** `oxford-command-center` (PRIVATE single-owner, `ZeOoba/oxford-command-center`) MAY hold active confidential deal terms in committed source (e.g. `src/data/seed-deals.ts`) — Gabriel's standing decision; the repo's pre-push scan was removed (PR #32). The egress guard + the rules above STILL bar deal terms from the public site, the `/dist/` mirror, Notion, Outlook, and every OTHER repo/surface. Audits / probes must NOT flag committed terms in THIS repo as a finding. (The egress guard never blocked internal repo writes/pushes anyway — see `~/.claude/hooks/confidentiality-guard.py`.)

## 7b. Declassification / reclassification file checklist (2026-07-09; amended 2026-07-12)

No checklist existed for this before 2026-07-09; the E. Fulton declassification
touched 4 files ad hoc and missed `session-context.md` (caught and fixed
out-of-band — see `event_log.md`). When a confidential deal's status changes
(declassified, or re-classified confidential), update ALL of:

- `hooks/confidential-terms.json` — flip the deal's `active` flag.
- `session-context.md` — update the roster line (Hard Invariant 3's sanctioned
  untracked roster home).
- `memory/event_log.md` — append the dated decision via
  `python ~/.claude/maintenance/append-event-log.py` (§9: never Edit-anchor the
  log header — one structural writer at a time).
- `memory/projects.md` — update the deal's entry/status.
- `memory/MEMORY.md` — only if the deal's index-entry description text changes.
- `memory/firm.md` — only if firm-level facts changed (e.g. portfolio
  composition).
- `CLAUDE.md` (master `~/.claude/CLAUDE.md`) and every ported copy — Cowork
  Settings user-preferences text (not file-backed; requires a manual paste by
  Gabriel), `Obsidian BrainVault/CLAUDE.md`, and any other surface-specific
  copy — remove the belt-and-suspenders deal-name reference outright. Added
  2026-07-12 after a second miss: the original 2026-07-09 pass never touched
  these, so `~/.claude/CLAUDE.md`'s Invariant 3 and the Obsidian vault's
  confidentiality rule both still named E. Fulton by name a full 3 days later —
  caught by a Cowork session running the (unrelated) post-legal-hold
  consolidation task. Gabriel's call (2026-07-12): just delete the stale
  reference each time — do NOT replace it with standing "never name an active
  confidential deal in this file" policy language; that's Hard Invariant 3's
  job at the roster level, not a per-file rule to maintain.

Doc-only enforcement (decided 2026-07-09): declassification is rare enough
that a lightweight automated check isn't warranted yet — revisit if a future
declassification misses this checklist despite the Hard Invariant 3 pointer.

## 7. Website / CSP (oxfordra.net)

- **Do NOT use the `<link rel="preload" as="style" onload="this.rel='stylesheet'">` CSS pattern.** Use plain `<link rel="stylesheet">`. The tightened CSP (no `'unsafe-inline'` in script-src) silently breaks inline `on*=` handlers, so the preload never swaps and styles never load.
- When tightening CSP on a static site, audit for `onload=`/`onerror=`/any `on*=` inline handlers — they fail silently. FOUC savings aren't worth the fragility. If FOUC avoidance is critical: inline the full stylesheet, OR add `'unsafe-hashes' 'sha256-<hash>'`, OR move swap logic into an external hashed script.
- Style guide: EB Garamond / DM Sans / IBM Plex Mono; `#1B2A4A` / `#C9A96E` / `#F5F3EF` (Parchment corrected 2026-06-11 — `#F5F0E8` was wrong; verified against `--parchment` in website-canonical CSS).

## 8. Parked-task chips — claim-lock before executing (race-proofing, 2026-06-11)

- **Why:** a parked chip can launch on two surfaces (Code + Cowork) and double-run — proven by the GitHub purge chip executing twice concurrently; benign only because both runs converged on the same end state.
- **Step 0 of every chip runbook:** check `C:\Users\Owner\.claude\chip-claims.log` (untracked — the fail-closed .gitignore keeps it off the remote). If a `CLAIMED` line for the same chip title is **< 60 min old** with no matching `DONE`/`ABORTED`, ABORT and report the prior claim instead of executing. Otherwise append `<ISO-8601 local> | CLAIMED | <chip title> | <surface/session-id>`, and on exit append the matching `| DONE` (or `| ABORTED <reason>`) line.
- **Authoring rule:** any session creating a chip via `spawn_task` must embed this step 0 verbatim in the chip prompt — the spawned session starts cold and cannot recall this rule on its own.
- **Verification-phrasing conventions for purge/state-check runbooks:** an object-gone check on GitHub returns **404 OR 422** ("No commit found" = object missing from an existing repo; 404 = the repo itself is missing) — expect either. Phrase git preconditions **structurally** ("main has `X` as root commit"), never count-based ("single commit") — clean commits legitimately accumulate on top of a baseline.

## 9. Automation budget & event-log concurrency (2026-06-11)

- **AUTOMATION BUDGET (re-ratified 2026-07-09, expires 2026-10-07):** new scheduled tasks/monitoring layers still need a real P0-critical (or otherwise clearly load-bearing) justification — the bar against low-value automation sprawl stays. The **one-in-one-out retirement requirement is DROPPED** as of this re-ratification (Gabriel's decision) — a new automation no longer requires killing an existing task to add it. Original rationale for the now-dropped clause: the 2026-06-11 audit found 36 archived tasks from 2 months of churn.
- **EVENT-LOG CONCURRENCY:** entries are appended ONLY via `python ~/.claude/maintenance/append-event-log.py` (atomic, newest-first) — never Edit-anchor the log header (3 header-anchor collisions on 2026-06-11). One structural writer at a time. Retirement entries that should auto-ratify probe drops must contain the literal token RATIFIED plus the exact task ids.

## 10. Permission regime — bypass + structural gates (Gabriel-directed 2026-06-12)

- **defaultMode is `bypassPermissions`** in both `~/.claude/settings.json` and the OneDrive project `.claude/settings.json` — Gabriel's standing directive: the system acts without approval prompts; the only human gates are money movement, external email, and oxfordra.net changes. Do NOT "fix" this back to default/acceptEdits; the project-level key is load-bearing (project overrides user, and every CC scheduled task runs with that cwd).
- **The three gates are enforced by `~/.claude/hooks/ora-autonomy-gate.py`** (PreToolUse, first in chain), NOT by permission prompts: COM sends to non-`@oxfordra.net` recipients blocked · Edit/Write into `website-canonical`/any `oxford-site` tree blocked · Netlify production deploys blocked. Money has no tool path (doctrine-only, invariant 1). The 3 Netlify updater MCP tools sit in user-settings deny rules (deny survives bypass).
- **Override protocol:** ONLY after Gabriel's explicit in-turn confirmation, `touch` the named sentinel in `~/.claude/hooks/overrides/` (`allow-external-send` / `allow-website-change`); valid 60 min from mtime. Scheduled/headless sessions must NEVER self-create a sentinel — flag and stop instead.
- **Before requesting a sentinel:** quote the hook's actual block condition and the exact blocked command in the request. Reads of the site tree pass the gate untouched — a "blocked read" means the command carried a write indicator (`>`, `cp `, `rm `, …), so fix the command instead of overriding (2026-07-09; see memory `feedback_autonomy_gate_blocks_writes_not_reads.md`).
- **`less-permission-prompts` allowlist upkeep (§6) is now moot under bypass** — keep the allowlist intact anyway as the fallback if the mode is ever reverted.

## 11. Edit-tool / bash-mount sync verification on large diffs (2026-07-08)

- **On large diffs, the Edit tool's write and the bash-mounted view of the same file can diverge** — a Windows-side Read after an Edit can show the change landed while the bash-side file (same path, mounted view) still shows stale length/content, or vice versa. Hit twice in one Cowork deal session building v03 model deliverables, costing real time chasing a "the edit didn't take" false alarm.
- **How to apply:** past a certain diff size (large multi-section rewrites, not small single-line edits), don't trust the Windows-side Read alone to confirm a write landed — cross-check the bash-side file directly (`wc -l`, `stat`, or a targeted `grep` for the new content) after the Edit. If the two views disagree, re-read both before deciding which is authoritative; don't assume either side is automatically correct.

## 12. Governance-ledger writes — append-only via helper script (2026-07-10)

- **Never add a new section to a governance ledger (`Claude_Workspace\00_Governance\outputs\*ledger*.md`, e.g. `2026-06-10_fleet-disposition-ledger.md`) with a general-purpose overwrite-mode write.** Second incident of this exact failure mode: a prior session used the wrong write mode and overwrote `2026-06-10_fleet-disposition-ledger.md`, wiping §1–§7 down to just the newly-added §8. Recovery required an OneDrive Version History restore — and finding the right version required first discovering the file's canonical copy is synced under **egoldberg@oxfordra.net**'s OneDrive account, not Gabriel's own (`(1)`-suffixed local folder) — see `reference_memory_scope_fragmentation.md`.
- **Route every ledger append through `Claude_Workspace\00_Governance\Scripts\Append-Ledger.ps1`** (`powershell -NoProfile -ExecutionPolicy Bypass -File Append-Ledger.ps1 -LedgerPath <path> -TextFile <new-section.md>`). It refuses any path outside `00_Governance\...\outputs\*ledger*.md`, refuses a nonexistent target (ledgers are created once by normal write, then only appended to), snapshots the pre-append file to a sibling `archive\` folder by default (never-delete canon), and appends via `Add-Content` only — there is no code path in it that can overwrite.
- **How to apply:** when a skill/task/session needs to add a new dated section to any governance ledger, use the helper instead of Edit/Write in overwrite mode. If the helper is unavailable on the current surface (e.g. a non-Code session without shell access), fall back to an explicit append-mode operation and double-check the resulting line count grew rather than shrank before moving on.


## 13. Recovery/cleanup briefs — state-freshness header + re-verify before acting (2026-07-10)

- **Why:** the 2026-07-05→07-10 fleet-loss recovery repeatedly produced briefs/docs written against registry state that a parallel session had already changed. The 2026-07-10 cleanup session found 3 of its 8 instructed steps stale on arrival (tasks already deleted, content already promoted, tasks already re-enabled) — and one step's instructed action (an OneDrive recycle-bin recovery) would have RISKED REGRESSION had it been executed as written, because a verified-current restoration had superseded the "lost" file the day before.
- **Authoring rule:** any recovery/cleanup brief, handoff prompt, or multi-step remediation doc MUST carry a header line: `STATE AS OF <ISO-8601 timestamp> — re-verify registry/filesystem ground truth per step before acting; treat every step as a hypothesis, not a fact.` Chip prompts and scheduled-task remediation SKILL.mds count as briefs for this purpose.
- **Executing rule:** on receiving such a brief (with or without the header), verify each step's premise against the live source of record (`list_scheduled_tasks`, filesystem, event_log.md) BEFORE mutating anything. If the premise no longer holds, record "already done / superseded — verified" and move on; never execute a stale instruction because the brief says so. This is the scheduler-registry analogue of the git single-writer doctrine (event_log 2026-07-08 near-miss #1) applied to instructions instead of writes.
