# ORA Machine Migration Runbook — new computer (week of 2026-06-15)

Written 2026-06-11 (Phase A of the setup-remediation sprint; audit grade 72/100).
Execute on the NEW machine as Phase B, one section at a time, in order. Re-verify every
fact against live state first — this doc is as-of 2026-06-11. Full sprint context:
`Claude_Workspace/00_Governance/outputs/2026-06-11_claude-setup-audit-rev2-grade-72.md`.

## B0. Decisions already made (Gabriel, 2026-06-11)
- **Username: pin `Owner`.** Create the Windows profile as a LOCAL account named `Owner`
  at OOBE so the profile dir is exactly `C:\Users\Owner` (Microsoft-account setup
  auto-derives folder names — do it deliberately, attach the MS account after).
  WHY: 15+ load-bearing hardcoded paths — all 9 hook commands in settings.json, the
  integrity-guard engine paths, send-via-outlook.ps1's log path, SKILL.md output paths.
  If the profile dir differs, EVERY hook fails at first session.
- **Backup remote: `ZeOoba/ora-claude-config` (PRIVATE).** Created + pushed 2026-06-11;
  history PURGED to a single term-free commit the same evening (the initial push had
  carried pre-scrub history — 48 term occurrences in old diffs; caught by
  doctrine-integrity-probe check 8, remediated via branch swap, Gabriel-approved).
  Confidential terms are scrubbed from all tracked files (verified 0 hits across the
  full live terms list). NEVER commit a deal term to it; the guard test suite derives
  its fixtures from the untracked terms file. **STANDING RULE: any pre-push
  confidentiality gate must scan `git log -p --all` (full history), not just the
  tree — a clean HEAD does not mean a clean push.** The pre-purge history lives on
  LOCAL-ONLY branch `archive/pre-purge-20260611` — NEVER push it; exclude it from any
  future remote (it does not migrate via clone; if migrating by disk copy, leave it).

## B1. Provision (in order)
1. Windows local account `Owner` → verify `echo %USERPROFILE%` = `C:\Users\Owner`.
2. Sign into OneDrive → WAIT for FULL hydration of
   `OneDrive - Oxford Capital Partners (1)` — verify `Documents\Claude\Scheduled\` and
   `Claude_Workspace\` are real files, not placeholder stubs (right-click → Always keep
   on this device for both).
3. Install: Claude Desktop, Claude Code, Python 3.x (on PATH — hooks require it),
   Node + npm, git, gh CLI, netlify CLI, Outlook desktop (M365 profile for
   ggoldberg@oxfordra.net — the COM send path needs a configured profile).
4. `git clone https://github.com/ZeOoba/ora-claude-config.git C:\Users\Owner\.claude`
   (gh auth login as ZeOoba first).
5. Place SECRETS from the out-of-band transfer (USB/local only — NEVER via git,
   OneDrive, or email):
   - `C:\Users\Owner\.claude\.credentials.json` (15,750 B as of 6/11)
   - `C:\Users\Owner\.claude\hooks\confidential-terms.json` (1,428 B)
   - `C:\Users\Owner\.claude\scheduled-tasks\_shared\anthropic-key.dat` (326 B)
   - `C:\Users\Owner\.claude\scheduled-tasks\_shared\netlify-token.dat` (262 B)
   (Sweep on 6/11 confirmed: no other .env*/.dat secrets exist under ~/.claude.)
   NOTE: `scheduled-tasks/` is NOT git-tracked — copy the whole
   `C:\Users\Owner\.claude\scheduled-tasks\` tree (SKILL.mds + _shared + engines)
   from the old machine in the same out-of-band transfer.
6. Reinstall plugins per `~/.claude/plugins/installed_plugins.json` (firecrawl,
   superpowers, frontend-design, andrej-karpathy-skills; chrome-devtools stays
   disabled). Marketplaces: claude-plugins-official, chrome-devtools-plugins,
   anthropic-agent-skills, karpathy-skills.
7. Re-auth connectors: claude.ai login (Notion, HubSpot, M365, Netlify connectors are
   account-side — verify each in a session), gh CLI, netlify CLI. Verified gotchas:
   QBO MCP stays dead (Desktop-only doctrine); Zapier stays connected, never routed.

## B2. Scheduled fleets (registries are machine-local AppData — they do NOT migrate)
1. FIRST: open the Desktop app, run `list_scheduled_tasks` on BOTH surfaces (a Code
   session sees the CC store only; a Cowork session sees LAMS). If tasks synced with
   the account, VERIFY real fires instead of re-registering.
2. If empty (expected): re-register every live task via `create_scheduled_task` in a
   supervised session ON THE TARGET SURFACE, one approval per task. JSON-splice is
   PROHIBITED (proven registered-but-unscheduled 2026-06-09). The authoritative
   roster (ids + crons) is the GENERATED block in `~/.claude/session-context.md`.
3. Catch-up doctrine: a cron fires at its time ONLY if the app is open then; otherwise
   tasks burst at next app-open (the global-limit "skips" are that burst hitting the
   dispatcher cap). Keep the Desktop app open with Keep Awake ON on the new machine.
   Tasks that MUST hit their clock → Phase C cloud-routine memo, not a desktop cron.
4. Windows Task Scheduler (the third scheduler): re-create via schtasks per the file
   headers — `maintenance/fleet-deadman.ps1` (daily 07:30) and
   `maintenance/ora-nightly-disk.ps1`.

## B3. Burn-in (48h) — all with command-output evidence
- [ ] Heartbeat updates Notion page 35c6ecd8 at 05:50 + 17:50; GitHub
      `ZeOoba/ora-cowork-watchdog` green. The migration gap WILL trip the 16h alarm
      once — treat as a LIVE TEST of the dead-man chain: confirm the alert reaches
      Gabriel, then clear.
- [ ] `python hooks/tests/test-confidentiality-guard.py` → ALL PASS (630 as of 6/11)
      BEFORE any egress-capable automation runs. (Fail-closed: if confidential-terms
      .json is missing the guard BLOCKS all egress — placing it is step B1.5.)
- [ ] `python maintenance/registry-membership-probe.py` → exit 0, roster regenerated.
- [ ] `python maintenance/test-registry-membership-probe.py` → 15/15.
- [ ] doctrine-integrity / governor-drift / memory-integrity probes → exit 0.
- [ ] One COM test send to ggoldberg@oxfordra.net — ONLY with Gabriel's explicit
      per-send confirmation; verify `_shared/send-log.txt` writes.
- [ ] ora-am-brief produces + publishes end-to-end; lane-telemetry.jsonl appending.
- [ ] `ora-task-integrity-guard` (CC, 12:45) fires and prints GUARD OK cc=N lams=N.

## B4. Old machine decommission
ONLY after every B3 box is checked AND on Gabriel's explicit go. Before wipe: export
anything unsynced (check `git -C ~/.claude status`, OneDrive sync state, Obsidian
vault, `C:\Users\Owner\ora-skills`, `website-canonical`, `oxford-command-center`,
`ora-pm`, `ora-financials-work` — push/copy each). The GitHub watchdog survives the
wipe (cloud-side); `fleet-deadman.ps1` does not (local schtasks — recreated in B2.4).

## Known holds & residuals (carry into Phase C)
- 5 folders held pending Gabriel's ratification (named by skill docs, in NO registry):
  ora-annual-budget-kickoff, ora-year-end-review, ora-lender-covenant-tracker,
  ora-cash-position-snapshot, ora-heartbeat-chain-verify-20260611.
- LAMS registry still holds disabled entries (scheduled-task-integrity-guard,
  ora-lams-fire-test-20260610, ora-heartbeat-chain-verify-20260611) — remove via the
  Cowork UI when convenient; until then their folders cannot be archived (the guard
  restores them — observed live 2026-06-11).
- Guard gap (PROPOSED, data fix for Gabriel): squeezed multi-word identifiers (e.g.
  a no-space form of a 2-word counterparty name) evade the substring matcher — add
  no-space forms to each deal's `always` array in confidential-terms.json.
- county-parcel-screen is git-UNTRACKED (embeds counterparty names in its never-call
  machinery) — local-only; needs a sanitized backup path (externalize the names to an
  untracked data file, then re-track).
- am-brief mirror-fallback references the retired ora-connector-preflight-guard
  producer (absent mirror = expected; no-mirror branch handles it).
