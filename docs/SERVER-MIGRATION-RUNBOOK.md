# ORA Server Migration Runbook -- Tier S (Linux local server) stand-up

Written 2026-07-05 (server-migration sprint). Companion to `docs/MIGRATION_RUNBOOK.md`
(the Windows desktop rebuild, Phase B) -- that doc governs the desktop; THIS doc governs
the new always-on Ubuntu server. Execute one section at a time, in order. Re-verify
every fact against live state first -- this doc is as-of 2026-07-05. Evidence rule
carries over unchanged: no box is checked without pasted command output.

Audit basis: hooks audit, maintenance/scheduler audit, EOS invariants audit,
oxford-command-center audit, skills/vault/watchdog audit, Claude Code docs audit
(all 2026-07-05). Where a claim below matters, the audit finding is cited inline.

---

## S0. Decisions (ratified for this migration -- mirror of B0)

- **D1. Two-tier estate.** The desktop is NOT being replaced; it is being relieved.
  - **STAYS on Windows (Tier D):** the Outlook COM send lane
    (`scheduled-tasks/_shared/send-via-outlook.ps1` + send-log.txt -- email is
    COM-only by ratified doctrine since 2026-06-11), OneDrive hydration and every
    job that reads the hydrated business tree in place, the Cowork/LAMS surface
    skills and their scheduled tasks (ora-om-intake-ocr, ora-replacement-cost-refresh,
    ora-skill-store-drift-check), the Obsidian UI + Copilot indexing, the schtasks
    trio (fleet-deadman.ps1, ora-nightly-disk.ps1, eos-health-report.ps1), and the
    CC-store LLM fleet (am-brief, pm-ledger, health-guard, setup-audit,
    deal-sourcing-scan) for v1 -- they email, and the server has no send lane (D6).
  - **MOVES to Linux (Tier S):** the engineering fleet (oxford-command-center
    development, the FULL `npm run gate` including reconcile + warehouse:verify,
    a self-hosted GitHub Actions runner) and the clock-critical headless producers
    identified by the maintenance audit's serverCandidates list: the Notion
    heartbeat producer (the single strongest must-hit-its-clock case -- the
    2026-05-31..06-10 outage was exactly "app not open"), the vault backup, and
    the telemetry rollup. Plus Claude Code headless sessions (`claude -p`) on
    server repos.
- **D2. Server username is ANY name -- the Owner pin is dead on Tier S.** B0 pinned
  the Windows profile to `Owner` because 15+ load-bearing hardcoded `C:\Users\Owner`
  paths would break otherwise. The portability work (units I1/I2) replaced every
  hardcoded profile path in hooks and `settings.json` with `~`/`os.path.expanduser`
  and self-relative resolution (`hooks/run-hook.sh` resolves the hook from its own
  directory; hook defaults resolve `~/.claude/...`). `expanduser("~/...")` resolves
  to `C:/Users/Owner` on the desktop, so the pin survives THERE without being a
  requirement HERE. WHY this matters: it removes an entire class of provision-time
  failure (wrong username = every hook dead) that the desktop runbook had to
  engineer around.
- **D3. Layout (fixed; scripts assume it).** Repos: `$HOME/oxford-command-center`,
  `$HOME/ora-skills`, `$HOME/BrainVault`. Config repo cloned AT `~/.claude`
  (exactly like the Windows runbook, B1.4). Data corpus:
  `$HOME/ora-data/eric-spreadsheets/` (Master Workbook) and
  `$HOME/ora-data/property-financials/` (32-file P&L corpus). Server env + secrets:
  `~/.config/ora/ora.env`, mode 600, NEVER inside the `~/.claude` git checkout.
  Per-doctrine secrets stay at their gitignored homes:
  `~/.claude/hooks/confidential-terms.json` and `~/.claude/.credentials.json`.
- **D4. Failure doctrine carries over UNCHANGED** (EOS hardening spec
  `docs/superpowers/specs/2026-06-05-eos-reliability-hardening-design.md` section 3):
  productivity/process gates FAIL OPEN (`hooks/run-hook.sh` -- any launcher failure
  exits 0 silently); confidentiality/egress gates FAIL CLOSED
  (`hooks/run-hook-strict.sh` -- any failure exits 2 with an ASCII stderr message).
  A migration that flips either direction is a doctrine violation, not a bug.
- **D5. Heartbeat producer moves to systemd; the GitHub watchdog does NOT move.**
  `server/heartbeat.py` on a systemd user timer PATCHes the same canonical Notion
  page (35c6ecd8-9e59-81d5-8d2c-d08002458b78, probed DIRECTLY BY ID per the v02
  doctrine -- never title-search) on the same 2x/day cadence. The
  `ZeOoba/ora-cowork-watchdog` GitHub Actions probe stays EXACTLY as-is: it is the
  off-box monitor and must never live on the box it watches. Do NOT recreate the
  Notion page if it goes missing -- restore from trash (duplicates are the v02
  failure mode).
- **D6. Email egress from the server = NONE in v1.** No SMTP, no Graph, no COM.
  Server jobs that want to notify either (a) write output the desktop lane picks up
  (queue-to-Windows: drop the rendered body under a synced/pulled path and let the
  existing COM lane send it), or (b) rely on the watchdog chain (GitHub Issue ->
  native notification). Phase 2 OPTION, not ratified: Microsoft Graph API send from
  the server -- requires explicit ratification because it would end the COM-only
  doctrine and add an egress surface the confidentiality guard must learn
  (add a token to `EGRESS_BASH` in `hooks/confidentiality-guard.py`; never replace
  the `send-via-outlook.ps1` token -- Gate 1 of `hooks/ora-autonomy-gate.py` keys
  on it and the desktop still uses it).
- **D7. Scheduler doctrine, restated for Tier S.** On the desktop, cron-class jobs
  live in app-local JSON registries that fire only while the app is open, and
  JSON-splice registration is PROHIBITED (proven registered-but-unscheduled
  2026-06-09; `docs/MIGRATION_RUNBOOK.md` B2.2). On the server, systemd user units
  REPLACE that entire class for moved jobs: units are declarative files in
  `server/units/` (version-controlled, reviewable), enabled via `systemctl --user
  enable --now`, and fire on the wall clock regardless of any app. The JSON-splice
  ban is therefore MOOT on Tier S -- there is no registry JSON to splice. The ban
  still binds on the desktop for everything that stays there.
- **D8. ASCII-only output in all hooks/tests** (Windows cp1252 console contract;
  `hooks/tests/test-engineering-router.py` asserts isascii). The same checkout
  deploys to both tiers; a Linux-side edit that emits non-ASCII breaks the desktop.
- **D9. Backward compatibility is a gate, not a goal.** The same ora-claude-config
  checkout is `~/.claude` on the Windows desktop. Windows behavior must be unchanged
  after a `git pull` there. Any server-motivated change to hooks/settings must pass
  `hooks/tests/run-all.sh` under Git Bash on the desktop too (S5 checkbox).

---

## S1. Provision

**Hardware/VM floor:** Ubuntu 24.04 LTS, x86_64, glibc (NOT Alpine/musl -- the
oxford-command-center gate compiles/loads better-sqlite3 + sqlite-vec, and prebuilt
binaries exist only for linux-x64/glibc; musl means a from-source build chain),
8 GB+ RAM (gate + runner + headless sessions concurrently), 40 GB+ disk
(corpus + node_modules + runner work dirs), always-on power/network. A VM is fine;
a laptop with a lid is not -- the whole point is wall-clock reliability.

**One command path.** Everything below is scripted; the manual sub-steps are the
numbered rows in the MANUAL ACTIONS table.

1. Create the server user (any name, D2), get SSH access.
2. GitHub auth -- CHOOSE ONE (manual action M2):
   - **Deploy keys** (least privilege): one SSH keypair per repo
     (ora-claude-config read; BrainVault read-write; oxford-command-center
     read-write if the runner pushes anything), added in each repo's Settings ->
     Deploy keys. Best for a box that should never hold account-wide credentials.
   - **`gh auth login` device flow** (simplest): one browser round-trip, account
     scope. Acceptable because the box is private and single-purpose; revoke the
     token at decommission.
3. Clone the config repo AT `~/.claude`, then run the provisioner:

   ```bash
   git clone git@github.com:ZeOoba/ora-claude-config.git "$HOME/.claude"
   bash "$HOME/.claude/server/provision.sh"
   ```

   NOTE: the LOCAL-ONLY branch `archive/pre-purge-20260611` does not travel via
   clone (good -- see `docs/MIGRATION_RUNBOOK.md` B0: NEVER push it, never copy it
   to this box).

   `server/provision.sh` is idempotent and does, in order: apt prerequisites
   (git, curl, python3, build-essential fallback for native modules), Node 20+
   (gate engines field) via the official channel, Claude Code native installer
   (`curl -fsSL https://claude.ai/install.sh | bash` -- per the Claude Code docs
   audit this is the auto-updating recommended path), `loginctl enable-linger`
   for the service user (WITHOUT this, every systemd --user timer dies at logout --
   FM-8), directory skeleton (`~/ora-data/...`, `~/.config/ora/`), repo clones
   into the D3 layout, `hooks/install-prepush.sh` against `~/.claude` and every
   confidential repo clone (per `confidential-repos.json`; clones do NOT carry
   `.git/hooks` -- B3 learned this the hard way), systemd user units copied from
   `server/units/` (NOT yet enabled -- S4 enables them deliberately), and an
   `npm ci` in `~/oxford-command-center`.
4. Claude auth -- CHOOSE ONE (manual action M4):
   - `claude setup-token` on the DESKTOP, transfer the resulting credential
     out-of-band (S2 rule) to `~/.claude/.credentials.json` -- keeps the
     subscription identity;
   - or `ANTHROPIC_API_KEY` in `~/.config/ora/ora.env` -- simpler for pure
     headless `-p` use, metered separately.
5. Provision `~/.claude/session-context.md` (referenced by the SessionStart hook;
   it is generated/untracked and a fresh clone does not have it -- the cat fails
   SILENTLY and sessions start without operational context). Copy the desktop's
   or `touch` a stub; regenerate properly post burn-in.
6. Run `bash "$HOME/.claude/server/verify-setup.sh"` -- every line must PASS.
   This is the same evidence discipline as B3: the script checks interpreter
   presence, layout dirs, secrets placement + modes, linger, unit files, corpus
   counts, and hook launcher behavior. Paste its output into the burn-in log.

**Hook execution note (from the Claude Code docs audit):** hook command strings run
via `sh -c` on Linux and Git Bash on Windows; tilde is NOT expanded in hook command
values -- the portable form used by `settings.json` (unit I2) is
`bash "$HOME/.claude/hooks/run-hook.sh" <hook.py>`, where `$HOME` is expanded by the
shell on both platforms. Do not "fix" this to `~` on either tier.

---

## S2. Secrets (out-of-band ONLY)

**STANDING RULE (unchanged from `docs/MIGRATION_RUNBOOK.md` B1.5): secrets travel by
USB/scp/local transfer only -- NEVER via git, OneDrive, or email.** The full
authoritative inventory with per-secret provenance is
`server/SECRETS-MANIFEST.md`; `server/secrets.env.example` is the template for
`~/.config/ora/ora.env`. Summary table:

| Secret | Lands at | Mode | Consumed by |
|---|---|---|---|
| confidential-terms.json | `~/.claude/hooks/confidential-terms.json` | 600 | confidentiality-guard.py, git-prepush-confidential-scan.py, test-confidentiality-guard.py |
| Claude credential | `~/.claude/.credentials.json` (or ANTHROPIC_API_KEY in ora.env) | 600 | Claude Code sessions |
| NOTION_TOKEN | `~/.config/ora/ora.env` | 600 | server/heartbeat.py |
| ANTHROPIC_API_KEY (if chosen in S1.4) | `~/.config/ora/ora.env` | 600 | headless `claude -p` units |
| GitHub deploy key(s) / gh token | `~/.ssh/` / gh keyring | 600 | vault-backup.sh, runner, clones |
| Runner registration token | consumed once by `server/install-runner.sh`, not stored | n/a | runner registration (short-lived; see S4) |

Rules that bind here:

- `~/.config/ora/ora.env` lives OUTSIDE the `~/.claude` git checkout by design --
  it can never be swept into a commit of the config repo. Keep it that way.
- **THE FAIL-CLOSED TRAP (hooks audit, highest-severity finding):**
  `hooks/confidentiality-guard.py` loads the terms file BEFORE surface
  classification and BLOCKS UNCONDITIONALLY when it is unreadable. The file is
  gitignored, so a fresh clone does not have it. Consequence: if
  `confidential-terms.json` is not in place before the FIRST Claude session on
  the server, EVERY matched Write/Edit/Bash call blocks -- the deployment is
  bricked (by design: fail-closed is the doctrine, D4). Place it in the same
  sitting as the clone, before anything else runs. `server/verify-setup.sh`
  checks presence + mode and `hooks/tests/run-all.sh` refuses a vacuous pass
  (the confidentiality suite exits 1 if the terms file is missing or has <3
  active always-terms).
- The same terms file gates pushes (`git-prepush-confidential-scan.py` is
  fail-closed on an unreadable terms file: ALL pushes block). Missing terms file
  therefore = bricked sessions AND bricked pushes. One file, two brick modes.
- NEVER create or commit a staging/fake `confidential-terms.json` inside any
  tracked tree. Test fixtures derive from the live file at runtime precisely so
  no term ever appears in a tracked test.

---

## S3. Data corpus (gate fuel)

The full gate needs two local data sets (oxford-command-center audit):
`WORKBOOK_PATH` -> `$HOME/ora-data/eric-spreadsheets/Master Excel Template Company
Wide -- Oxford.xlsx` and `FINANCIALS_DIR` -> `$HOME/ora-data/property-financials/`
(32 Excel/xlsm files). Both env vars are exported by the runner env and by
`~/.config/ora/ora.env` for interactive sessions (defaults in `server/config.ts`
point at the Windows OneDrive layout and resolve to nothing on Linux -- the env
vars are mandatory here, not optional).

**Two transport paths -- pick one, document the choice in the burn-in log:**

- **Path A -- rclone pull (server-driven, preferred):** `rclone config` with the
  OneDrive backend, ONE device-code browser auth (manual action M5), then the
  `server/rclone-sync.sh` hourly systemd timer (unit in `server/units/`) mirrors
  the two source folders into `~/ora-data/`. Token refresh is automatic
  thereafter; expiry/revocation is FM-3.
- **Path B -- desktop push (desktop-driven):** `server/desktop-push-data.ps1`
  runs on the Windows box (schtasks or manual) and pushes the two folders to the
  server over scp/rsync. No cloud auth on the server; instead the freshness
  depends on the desktop being on -- which is the exact failure class this
  migration exists to remove. Use only if rclone auth is refused.

**Verification (evidence, not vibes):**

```bash
ls "$HOME/ora-data/property-financials" | wc -l   # >= 32
cd "$HOME/oxford-command-center" && npm run reconcile
```

`reconcile` must exit 0 asserting exactly **14 properties / 137 leases / 16 cash
entities** ($0-tolerance self-totals). `warehouse:verify` must import >= 32 files
with 0 unknown-basis rows (it builds a FRESH SQLite in os.tmpdir() -- it never
touches a live DB, safe to run any time). Both scripts resolve the committed
account-mapping seed via cwd -- ALWAYS run from the repo root.

**Corpus-version coupling warning:** those counts are assertions against a
specific corpus version. When Eric's workbook gains a property/lease, the counts
change and reconcile fails -- on WHICHEVER tier has the newer corpus. During any
corpus update, sync both tiers in the same sitting and expect one red gate run in
between. A count mismatch right after a sync is FM-14, not a code bug: check file
mtimes before touching code.

---

## S4. Services + runner

1. **Enable the timers** (deliberate, after S2+S3 are green -- units were installed
   but NOT enabled in S1):

   ```bash
   systemctl --user enable --now <unit>.timer   # for each timer in server/units/
   systemctl --user list-timers                 # evidence: NEXT column populated
   ```

   The moved-job units (authoritative list = `server/units/`): heartbeat producer
   (`server/heartbeat.py`, 2x/day pinned to America/New_York so the cadence
   matches the watchdog's 16h threshold regardless of server TZ), vault backup
   (`vault-backup.sh` in the BrainVault repo, unit I6 -- pull-rebase-then-push,
   failures VISIBLE, unlike the old `2>$null` PowerShell), telemetry rollup
   (`maintenance/eos-telemetry-rollup.py` against the server's own
   `~/.claude/telemetry/lane-telemetry.jsonl`), and the rclone corpus sync
   (Path A only).
   **ORDERING RULE for the heartbeat (this is what keeps the watchdog quiet):**
   enable the server heartbeat timer and confirm one on-schedule fire BEFORE
   disabling the LAMS `ora-cowork-heartbeat` task. Double-beating for a day is
   harmless (the watchdog measures staleness, not count -- FM-7); a gap is an
   alarm. Done in this order, the migration does NOT trip the watchdog -- unlike
   the B3 desktop migration, which planned for one live-test alarm.
2. **Install the self-hosted runner:** get a registration token from
   oxford-command-center repo Settings -> Actions -> Runners -> New self-hosted
   runner (manual action M6; token is short-lived, consume immediately), then:

   ```bash
   bash "$HOME/.claude/server/install-runner.sh" <REG_TOKEN>
   ```

   which installs the runner as a service with labels `[self-hosted, linux,
   ora-data]` and an env exporting `WORKBOOK_PATH`/`FINANCIALS_DIR`.
3. **Workflow:** `.github/workflows/full-gate-selfhosted.yml` (unit I5, in
   oxford-command-center) runs the FULL gate (governance -> typecheck -> lint ->
   test -> reconcile -> warehouse:verify -> warehouse:drift) on those labels. It
   is **workflow_dispatch-only until S5 burn-in passes** -- no schedule, no
   push trigger. After burn-in, optionally add a schedule and/or make it a
   required check. The existing `ci.yml` gate:ci on ubuntu-latest stays untouched
   (it deliberately excludes the data-bound steps).
4. **Confidentiality caution (oxford-command-center audit):** the gate's log
   output prints property names and NOI matrices (`warehouse-verify` prints the
   NOI matrix). Runner logs live in GitHub Actions. Therefore: repo stays
   PRIVATE, Actions log access is restricted to the org/owner, the runner never
   serves fork PRs, and `workflow_dispatch` gating (above) keeps arbitrary-ref
   runs off the box until burn-in proves the setup. This is FM-13.
5. **Serving note:** if the oxford-command-center server process runs on this box,
   it binds `127.0.0.1` by design (CLAUDE.md section 9 -- never relax CORS/bind).
   Remote access = SSH tunnel (`ssh -L 8911:127.0.0.1:8911 <server>`), never a
   bind change. Respect `WAREHOUSE_DB` single-writer discipline (FM-5): the gate
   is safe anywhere (tmpdir), but `warehouse:backfill` and a serving process must
   not share a live DB write window.

---

## S5. Burn-in (48h) -- all with command-output evidence, mirror of B3

No cutover (S6) until EVERY box is checked. Evidence = pasted command output in
the burn-in log, same rule as B3.

- [ ] `bash ~/.claude/server/verify-setup.sh` -> ALL lines PASS.
- [ ] `bash ~/.claude/hooks/tests/run-all.sh` -> ALL PASS **including the
      confidentiality suite** (it must actually RUN -- it exits 1 and refuses if
      the terms file is absent; a run where it was skipped is NOT a pass) and the
      autonomy-gate adversarial harness. Run the same command on the DESKTOP in
      Git Bash after `git pull` -> ALL PASS there too (D9 backward-compat gate).
- [ ] **SEEDED pre-push block test** (proves the fail-closed backstop with a live
      round, without touching real terms): in a THROWAWAY clone of a guarded
      repo, `git checkout -b tmp/prepush-seed-test`; commit a file containing one
      ACTIVE always-term taken from the live `~/.claude/hooks/confidential-terms.json`
      (type it in the commit only -- never into this doc or any tracked fixture);
      `git push -u origin tmp/prepush-seed-test` -> MUST be BLOCKED by the
      pre-push scan (term reported by index, never echoed). Then delete the
      branch and the clone. A push that goes through = FM-10 live, stop
      everything and fix the shim before any other work.
- [ ] Full gate green on the server, from the repo root:
      `cd ~/oxford-command-center && npm run gate` -> exit 0, reconcile counts
      14/137/16, warehouse:verify >= 32 imports / 0 unknown-basis.
- [ ] One dispatched `full-gate-selfhosted.yml` run green (Actions -> workflow ->
      Run workflow); confirm it ran on THIS runner (labels in the run log).
- [ ] Heartbeat: Notion page 35c6ecd8 last_edited_time advances at both daily
      fires for 2 consecutive cycles; `ZeOoba/ora-cowork-watchdog` Actions stay
      green and NO `heartbeat-alert` issue opens. Cutover ordering (S4.1) is what
      makes this gap-free: server timer enabled + one confirmed fire FIRST, LAMS
      task disabled AFTER, double-beat tolerated for one day.
- [ ] Vault backup dual-writer proof: a `backup:`-prefixed commit from the SERVER
      visible on GitHub (`git log origin/main` in BrainVault shows the server
      hostname/committer), AND a subsequent DESKTOP `git pull` in the vault is
      clean (no conflict, Obsidian unaffected), AND a desktop-side edit round-trips
      back. If the old `vault-backup.ps1` is still scheduled on the desktop,
      verify it now runs the I6-fixed logic (pull-rebase before push, errors
      visible) -- the legacy `git push ... 2>$null` swallow is FM-6.
- [ ] OCC project-settings guard test: in a Claude session in
      `~/oxford-command-center`, attempt `git add -A` -> BLOCKED by the vendored
      project guard (`.claude/settings.json` + hooks, unit I5) with the
      explicit-paths message. Also attempt an edit to `architecture/status.json`
      with invalid JSON and run `npm run governance` -> the status.json
      validation added in `scripts/governance-check.ts` (unit I5) must FAIL it.
- [ ] Telemetry: `~/.claude/telemetry/lane-telemetry.jsonl` appends after a
      coding session on the server; rollup timer run exits 0.
- [ ] Hygiene sweep (hooks audit pollution class): after 48h,
      `find ~ ~/oxford-command-center -maxdepth 2 -name 'C:*'` -> EMPTY (no
      literal `C:\Users\...` directories created by mis-defaulted hooks), and
      `git -C ~/.claude status` shows no untracked garbage.
- [ ] `systemctl --user list-timers` shows every unit with a sane NEXT; zero
      failed units in `systemctl --user --failed`; reboot the box once and
      confirm timers come back WITHOUT a login (linger proof, FM-8).

---

## S6. Cutover + decommission of moved desktop tasks

ONLY after every S5 box is checked. All desktop-side disables happen in the
surface UI (Cowork UI for LAMS; Desktop app Scheduled panel for CC) -- the
JSON-splice ban (D7) still binds on the desktop. DISABLE, don't delete, for the
first week: a disabled task is a one-click rollback.

**Disable on the desktop (moved to Tier S):**

| Desktop entry | Store | Replaced by |
|---|---|---|
| ora-cowork-heartbeat (05:50 + 17:50) | LAMS | `server/heartbeat.py` systemd timer -- disable ONLY after the S5 heartbeat box is checked (ordering rule S4.1) |
| BrainVault 6 PM backup schtask (`vault-backup.ps1`) | schtasks | server vault-backup timer. IF Obsidian editing continues on the desktop (it does), do NOT disable -- instead keep it running the I6 dual-writer-safe logic. Disable only if desktop writes cease. |
| (none else in v1) | -- | -- |

**Explicitly STAYS on the desktop (do not touch):** the entire CC email fleet
(ora-am-brief, ora-pm-ledger, ora-health-guard, ora-setup-audit,
ora-deal-sourcing-scan -- D6: server has no send lane in v1), all remaining LAMS
Cowork-surface tasks (ora-om-intake-ocr, ora-replacement-cost-refresh,
ora-skill-store-drift-check), the schtasks trio (`maintenance/fleet-deadman.ps1` --
it watches the desktop fleet, which still exists; `maintenance/ora-nightly-disk.ps1`;
`maintenance/eos-health-report.ps1` -- COM send), the Outlook COM send lane itself,
OneDrive hydration, Obsidian UI/Copilot. The desktop registries keep their
baselines; expect `maintenance/registry-membership-probe.py` to flag the heartbeat
disable ONCE -- acknowledge it as the migration, refresh the `_state` snapshot.

Post-cutover follow-ups (not gates): tighten the watchdog `STALE_HOURS_THRESHOLD`
only after 2+ weeks of server heartbeat history (a deterministic producer can
justify < 16h); consider Phase-2 moves (weekly EOS health report generation
server-side with queue-to-Windows send; Graph API ratification, D6).

---

## FAILURE-MODE TABLE

"Strands data" = can this failure lose or orphan data (vs. merely stop work).

| # | Symptom | Detection | Root cause | Remediation | Strands data? |
|---|---|---|---|---|---|
| FM-1 | Every Write/Edit/Bash in a session blocks with a confidentiality-guard message; pushes also block | verify-setup.sh terms-file line; first session bricked; run-all confidentiality suite exits 1 | `~/.claude/hooks/confidential-terms.json` missing/unreadable (gitignored -- fresh clones never have it); guard is FAIL-CLOSED by doctrine D4 | Place the real terms file out-of-band (S2), mode 600; rerun verify-setup.sh | No -- blocks work, protects data |
| FM-2 | Fail-closed hooks exit 2 with ASCII stderr on every call (strict launcher); OR productivity gates silently do nothing (open launcher) | verify-setup.sh interpreter line; `hooks/tests/run-all.sh` fails; strict-guard stderr names the missing interpreter | No `python3`/`python` on PATH (or not on the PATH systemd/hook context sees) | `apt install python3` (provision.sh does); for systemd units, ensure PATH in the unit env. Note the asymmetry is BY DESIGN: strict = blocked loudly, open = silent no-op | No |
| FM-3 | Corpus files stop updating; reconcile counts drift from desktop truth or go stale silently | `systemctl --user status` on the rclone timer (failed runs in journalctl); file mtimes in `~/ora-data` older than 24h; S3 verification counts | OneDrive rclone token expired/revoked (device-code grants can be invalidated by tenant policy or password change) | Re-run the rclone device-code auth (M5); re-run S3 verification; consider Path B as stopgap | No -- OneDrive remains source of truth; risk is DECISIONS on stale data |
| FM-4 | Dispatched full-gate runs sit "Queued" forever | Actions UI shows queued job; repo Settings -> Runners shows runner Offline | Runner service dead (reboot without service install, crash, token revoked) | `systemctl status` the runner service; restart; if unregistered, re-run `server/install-runner.sh` with a fresh token (M6) | No |
| FM-5 | SQLITE_BUSY / locked-database errors; or backfill and serving process corrupt each other's view | Server logs; `npm run warehouse:drift` mismatch; gate step failures naming the live DB | SQLite WAL is single-writer: a serving process and `warehouse:backfill` sharing one `WAREHOUSE_DB` | Gate is SAFE anywhere (warehouse:verify builds in os.tmpdir(), never the live DB). Discipline: stop the server before backfill against the live DB, or point backfill at a scratch `WAREHOUSE_DB` and swap. Worktrees each set their own WAREHOUSE_DB (worktree-env.example) | YES if DDL is run against the live DB directly -- doctrine: migrations only, never delete `data/warehouse/finance.sqlite` |
| FM-6 | Vault backup push rejected (non-fast-forward) or merge conflicts; worst case: desktop backups silently dead | vault-backup.sh logs a visible error (I6); `git log origin/main` missing recent `backup:` commits; desktop pull conflicts | Two writers (desktop Obsidian + server) on one branch; legacy `vault-backup.ps1` swallowed push errors with `2>$null` (skills/vault audit) -- a failed push looked like success | I6 strategy: `git pull --rebase --autostash` BEFORE commit/push; on conflict, abort and alert, never force. Verify the desktop task runs the fixed logic. Gitignore the churning `.obsidian/copilot-index-*.json` (tracked today -- will conflict the moment two writers exist) | YES in legacy mode (unpushed desktop commits can strand invisibly) -- that is WHY the S5 dual-writer box exists |
| FM-7 | Notion heartbeat page edited 4x/day during cutover; watchdog behavior questioned | Notion page edit history; watchdog Actions logs show hours-since-edit near 0 | Server timer AND LAMS task both live (the S4.1 ordering does this deliberately for one day) | None needed -- watchdog measures staleness, not count. Disable the LAMS task after the S5 heartbeat box; a GAP is the dangerous state, not a double-beat | No |
| FM-8 | All systemd --user timers stop after SSH logout/reboot; watchdog trips ~16h later | `systemctl --user list-timers` empty when logged back in; heartbeat-alert issue opens; S5 reboot check fails | `loginctl enable-linger` never ran (user manager exits with last session) | `sudo loginctl enable-linger <user>`; provision.sh does this -- verify-setup.sh asserts it | No |
| FM-9 | `npm ci` fails building better-sqlite3/sqlite-vec; or binary loads then crashes | provision.sh / gate step 1 output; node -e "require('better-sqlite3')" | Wrong platform: musl (Alpine), non-x86_64, or Node older than engines >= 20; prebuilds are linux-x64/glibc | Use Ubuntu 24.04 x86_64 (S1 floor); Node 20+ (CI uses 24); `apt install build-essential python3` enables from-source fallback | No |
| FM-10 | A secret or deal term reaches GitHub | Pre-push hook block message (the backstop working); GitHub secret-scanning alert; doctrine-integrity probe check 8 (the alarm that caught the 2026-06-11 incident) | Secret placed inside a tracked tree, or pre-push shim missing (clones do not carry .git/hooks) | The backstop is `hooks/git-prepush-confidential-scan.py` scanning FULL history (`git log -p`) per the standing rule -- TEST IT with the S5 seeded block test. If a push lands anyway: treat as the 2026-06-11 incident -- purge history to a clean baseline, rotate the secret, verify old objects unfetchable | No (data loss no; confidentiality incident YES -- highest severity in this estate) |
| FM-11 | After a desktop `git pull` of ora-claude-config, Windows hooks stop firing or misbehave | Desktop session start errors; `hooks/tests/run-all.sh` under Git Bash goes red; deadman/registry probes flag desktop fleet issues | A server-motivated edit broke the shared contract (non-ASCII output, bash-ism in POSIX sh launcher, dropped Windows interpreter fallback, path assumption) | Revert the offending commit in ora-claude-config; the D9 gate exists precisely for this: run-all on BOTH tiers before pushing config changes | No |
| FM-12 | Heartbeat producer 401s (journalctl) OR watchdog probe fails while the page is fresh | Producer leg: `systemctl --user status` heartbeat unit, journal shows Notion API error. Probe leg: heartbeat-alert issue / red watchdog run despite fresh page | NOTION_TOKEN rotated in one place, not both -- the token now lives in TWO homes: `~/.config/ora/ora.env` (producer) and the ora-cowork-watchdog GitHub Actions secret (probe) | Rotate BOTH in the same sitting. Paste carefully: a trailing newline in the Actions secret caused an InvalidHeader failure 2026-06-11 (the probe .strip()s, but do not rely on it) | No |
| FM-13 | Property names / NOI matrices visible to unauthorized eyes via CI logs | Periodic review of Actions run visibility; repo audit log | Self-hosted runner executes warehouse-verify, which prints the NOI matrix; logs live on GitHub | Repo PRIVATE (verify, do not assume); restrict Actions log access; runner never serves fork PRs; keep full-gate workflow_dispatch-only until burn-in (S4.3) | No -- exposure risk, not loss |
| FM-14 | reconcile suddenly asserts wrong counts (not 14/137/16) on one tier only | Gate red on reconcile step with a count mismatch; corpus file mtimes differ between tiers | Corpus-version coupling (S3): workbook changed, tiers out of sync, or counts legitimately changed with portfolio changes | Check mtimes FIRST (data, not code); sync both tiers; if the portfolio really changed, update the asserted counts in the same commit as the corpus doc note | No -- but a masked version skew can quietly produce wrong analytics; treat count drift as a stop-the-line signal |

---

## MANUAL ACTIONS (irreducible -- everything else is scripted)

| # | Action | Exactly where | Est. min |
|---|---|---|---|
| M1 | Create Ubuntu 24.04 server/VM + user + SSH key access | Hypervisor/hardware console; `adduser`, `.ssh/authorized_keys` | 15 |
| M2 | GitHub auth: add deploy keys (repo Settings -> Deploy keys) OR `gh auth login` device flow in the server shell | github.com repo settings / server terminal + browser | 5 |
| M3 | Out-of-band secrets transfer: confidential-terms.json, .credentials.json (or key), populate `~/.config/ora/ora.env` from `server/secrets.env.example` per `server/SECRETS-MANIFEST.md` | scp/USB from desktop -> paths in S2 table; `chmod 600` each | 10 |
| M4 | Claude auth: `claude setup-token` on the desktop, transfer credential (or choose ANTHROPIC_API_KEY in ora.env) | Desktop terminal -> M3 transfer | 5 |
| M5 | rclone OneDrive device-code auth (Path A only, once) | `rclone config` on server + browser code entry | 5 |
| M6 | Runner registration token + install | oxford-command-center Settings -> Actions -> Runners -> New; then `bash ~/.claude/server/install-runner.sh <TOKEN>` | 5 |
| M7 | Seeded pre-push block test (S5) -- requires a human to type one live term into a throwaway commit | Server terminal, throwaway clone | 5 |
| M8 | Dispatch `full-gate-selfhosted.yml` once | GitHub Actions UI -> Run workflow | 2 |
| M9 | Cutover clicks: disable ora-cowork-heartbeat in the Cowork UI (after S5 heartbeat box); acknowledge the one registry-probe flag | Cowork Desktop UI on the Windows box | 5 |

Nine rows. If a tenth manual step appears during execution, that is a defect in
the provisioning kit -- file it against `server/provision.sh`, do not just do it
by hand silently.

---

## ROLLBACK

The migration is reversible at any point with ZERO desktop changes, because the
desktop was never modified beyond a config-repo `git pull` (which is additive and
backward-compatible by the D9 gate):

1. **Stop Tier S jobs:** `systemctl --user disable --now` every timer from
   `server/units/` (heartbeat, vault backup, telemetry rollup, rclone sync).
2. **Re-enable anything disabled in S6** (one click each: ora-cowork-heartbeat in
   the Cowork UI -- they were disabled, not deleted). Ordering mirrors S4.1 in
   reverse: re-enable the LAMS heartbeat, confirm one fire, THEN stop the server
   timer -- no watchdog gap either direction.
3. **Remove the runner:** `config.sh remove` in the runner dir (or repo Settings
   -> Runners -> Remove); leave `full-gate-selfhosted.yml` in the repo -- it is
   workflow_dispatch-only and inert without a runner.
4. **Revoke server credentials:** gh token / deploy keys, rclone grant, Notion
   token (rotate BOTH homes per FM-12 if the server copy might be compromised),
   Claude credential.
5. Desktop estate is now exactly the pre-migration estate. Repo-side changes
   (portable hooks, launchers, project settings, workflow file) are additive and
   REMAIN -- they are improvements on both tiers, not migration state. Nothing to
   revert there unless FM-11 fired, in which case revert the specific commit.

Wipe the box only after step 4 and a `git -C ~/BrainVault status` /
`git -C ~/oxford-command-center status` check for unpushed work (same discipline
as `docs/MIGRATION_RUNBOOK.md` B4).
