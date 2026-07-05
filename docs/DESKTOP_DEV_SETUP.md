# ORA Desktop Dev Setup -- oxford-command-center

Purpose and scope: this is the DEV-PROJECT bring-up subset only -- it gets a Windows
desktop ready to run and develop `oxford-command-center` and confirms Claude Code runs
there. It deliberately defers everything about provisioning a brand-new machine
(Python for hooks, gh CLI, netlify CLI, Outlook COM profile, secrets placement, OneDrive
hydration, scheduled-fleet re-registration) to `docs/MIGRATION_RUNBOOK.md` sections
**B1 Provision** and **B3 Burn-in**. Read this doc for the project dev loop; read that
doc for the fuller machine migration.

The automation is `maintenance/setup-desktop-windows.ps1`. It is verify-first and
idempotent (re-running on a healthy box is a fast no-op), LOUD (every step is checked
and reported, nothing is silently swallowed), and conservative (never installs/upgrades
Claude Code, never deletes anything, never overwrites a config, never starts the dev
server unless you ask it to, never kills a process it did not launch).

## Prerequisites

- Windows 10 or 11, local profile `Owner` so `%USERPROFILE%` resolves to
  `C:\Users\Owner` (pinned -- many hardcoded paths in this repo depend on it; see
  `docs/MIGRATION_RUNBOOK.md` B0 if you are setting up a fresh machine).
- The repo already cloned at `C:\Users\Owner\oxford-command-center`. If it is not
  there yet, the script will FAIL loudly with the exact clone command rather than
  clone it for you:
  ```
  git clone https://github.com/ZeOoba/oxford-command-center.git C:\Users\Owner\oxford-command-center
  ```
  Private-repo auth is out of scope here -- see `docs/MIGRATION_RUNBOOK.md` for GCM/PAT
  setup.
- Claude Code already installed. The script never installs, upgrades, or otherwise
  touches it; it only verifies.

## Exact launch line

Run from an ordinary (non-elevated) `powershell.exe` window unless you specifically
need one of the elevated remediations below:

```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\maintenance\setup-desktop-windows.ps1
```

This script ships with the `ora-claude-config` repo, which clones to `C:\Users\Owner\.claude`
(see `docs/MIGRATION_RUNBOOK.md` B1), so it lives under `.claude\maintenance\` -- NOT inside
the project it sets up. The project it targets is a separate tree, passed via `-ProjectPath`
(default `C:\Users\Owner\oxford-command-center`). The script locates its own log via
`$PSScriptRoot`, so it runs correctly from wherever the repo was cloned.

Note: `-ExecutionPolicy Bypass` applies to this one process only and cannot override a
domain/GPO `MachinePolicy` set to `Restricted` or `AllSigned` -- if the script refuses
to run even with `Bypass`, that is a policy set above the user scope and needs an
administrator to adjust the machine policy; this script cannot self-fix it (and by
design never calls `Set-ExecutionPolicy` at any scope).

## Parameter reference

| Parameter | Default | When to use |
|---|---|---|
| `-ProjectPath` | `C:\Users\Owner\oxford-command-center` | Override only if the repo genuinely lives elsewhere. |
| `-SkipInstall` | off | Verify-only mode: probes and reports everything, runs zero winget installs and zero `npm install`/`npm ci` (still runs the read-only checks). Use for a quick health check on a box you don't want to change. |
| `-WhatIfInstall` | off | Logs the exact `winget install` command line it would run for Node/Git instead of executing it. Use to preview what an install would do. |
| `-StartDevServer` | off | Only when set, the script launches `npm run dev` for a bounded health check against `http://localhost:8911` (Brain Server) and `http://localhost:5273` (web), then **always** stops what it launched. Use after a clean install to confirm the app actually comes up end-to-end. |
| `-BrainPort` | 8911 | Pre-flighted always; only polled under `-StartDevServer`. |
| `-WebPort` | 5273 | Same as above. |
| `-HealthTimeoutSec` | 60 | Bound on the `-StartDevServer` health poll before it WARNs (never a hard failure). |
| `-LogPath` | sibling `setup-desktop-windows.log` next to the script | Override if you want the log elsewhere. Always appended to, never truncated. |

Typical usage:
- First run on a new checkout: no flags (installs what's missing, runs the gate smoke
  test).
- Quick recheck without touching anything: `-SkipInstall`.
- Confirm the app actually serves traffic: add `-StartDevServer` once deps are known
  good.

## What the script checks, step by step

1. **Preamble** -- elevation, PowerShell version/edition, execution policy, free
   memory, free disk on the project drive (WARN under 3 GB).
2. **Winget** -- detect only; absence degrades install steps to verify-only, never a
   hard failure by itself.
3. **Node** -- three-way: skip if `>=20` already satisfies the floor; install via
   winget only if node is completely absent (and no live `node.exe` process is
   holding the binary); WARN (never silently upgrade) if a `<20` install is present,
   since it may be intentionally pinned for another app. Version is parsed and cast to
   `[version]` for a numeric compare (never a string sort). Also checks for PATH
   shadowing (multiple `node` resolutions), `npm -v`, and `process.arch`.
4. **Git** -- detected by running the binary (`git --version`), not by `winget list`
   (which misses GitHub Desktop/scoop/WSL/MSI installs). Installs via winget only if
   missing or older than 2.40. WARN, not hard-fail, if unresolved -- `npm install`
   does not need git, but `npm run gate` and repo operations do.
5. **PATH refresh** -- rereads the Machine + User PATH into the running session
   in-process after any install (never touches the registry).
6. **Git config hygiene** -- read-before-write, `--global` scope only (never
   `--system`, to avoid needing admin): `core.longpaths=true` if unset,
   `core.autocrlf=false` only if currently unset or `true` (an explicit `input`/`false`
   is left alone), `credential.helper=manager` only if empty and a GCM binary is
   found on disk. Also checks (and, if elevated, sets) the machine-wide
   `HKLM\...\FileSystem\LongPathsEnabled` registry value.
7. **Project locate** (HARD prerequisite) -- the project directory and its
   `package.json` must both exist. WARNs loudly if the resolved path is under a
   OneDrive-synced folder (dehydration can corrupt `node_modules`), if the directory
   exists but is not a git work tree, or if `origin` does not point at the expected
   `ZeOoba` owner. Never clones, never deletes, never rewrites the remote.
8. **`.claude\settings.json` read-only guard** -- hashes the file, scans for
   unresolved merge-conflict markers, and confirms it parses as JSON. The file is
   never written, reformatted, or round-tripped -- only read. A missing file is a
   WARN (`git checkout -- .claude/settings.json` restores it); a corrupt file
   is a HARD FAIL.
9. **`package.json` parse** -- reads `engines.node` for an informational comparison
   and enumerates which of `dev` / `gate` / `ensure-deps` scripts actually exist, so
   later steps only invoke scripts that are really there (missing scripts are a SKIP
   row, never a failure).
10. **Dependencies** -- gated on `npm ls --depth=0` exiting 0, not on whether
    `node_modules` merely exists (a half-finished nightly disk-clean can leave a
    folder present but broken). If inconsistent and a `gate` script exists, runs
    `npm run gate`, which triggers `ensure-deps.mjs`'s self-heal. Otherwise runs
    `npm ci` (if `package-lock.json` exists) or `npm install`, falling back from
    `npm ci` to `npm install` on an `EUSAGE` lock mismatch, and retrying once on
    `EPERM`/`EBUSY` (a common Defender file-lock signature). Every npm exit code is
    judged by the integer `$LASTEXITCODE`, never by `$?` (which npm does not set
    meaningfully across a pipeline).
11. **Gate smoke test** -- runs `npm run gate` if it exists and step 10 did not
    already run it, exercising `ensure-deps.mjs` end-to-end.
12. **Port pre-flight** -- reports whether `8911`/`5273` are already listening and by
    which PID/process name. Never kills a foreign holder; an occupied port is a WARN
    and disables `-StartDevServer` for that port.
13. **Claude Code verify** -- resolves the binary (PATH, then `~/.local/bin`, then the
    npm-shim location), checks for PATH shadowing via `where.exe` (never the bare
    `where`, which is the `Where-Object` alias), runs `claude --version` in a
    background job with a ~20s timeout (an auto-updater, EDR, or proxy can otherwise
    hang it indefinitely), and checks for `%USERPROFILE%\.claude.json` as an
    authentication signal. Never installs, upgrades, or calls `claude doctor` (that is
    an interactive TUI -- see below). Immediately after, re-hashes
    `.claude\settings.json` and FAILs loudly if it changed at all during the run.
14. **Optional dev health check** -- only under `-StartDevServer`, and only if both
    ports were free in step 12: launches `npm run dev` (via `cmd.exe` so the redirected
    child can resolve the `npm.cmd` shim), polls both URLs until both answer or the
    timeout elapses, and **always** stops the process tree it launched (`taskkill /T`
    on the captured root PID) and re-verifies both ports are free again in a `finally`
    block, even on error. A timeout is a WARN, never a hard failure.
15. **Summary** -- a PASS/WARN/FAIL table to the console and the log, plus tallies
    and the exit code.

## What the script does NOT do (and why)

- Never installs, upgrades, or otherwise touches Claude Code -- it is assumed already
  installed; this script only verifies it.
- Never starts the dev server unless `-StartDevServer` is explicitly passed, and
  always stops what it started (and re-verifies the ports it took are free again).
- Never writes to `.claude\settings.json` (or any other config) -- read-only, hash
  checked before and after.
- Never deletes anything (archive to `/archive/` if something ever must be displaced).
- Never disables TLS verification (no `strict-ssl false`, no `sslVerify false`).
- Never changes the PowerShell execution policy at any scope.
- Never persists a registry PATH edit (only the in-process `$env:Path` is rebuilt).
- Never kills a process it did not itself launch.
- Never re-clones into an existing project directory.

## Reading the summary and the log

The console prints a `Step | Status | Detail` table at the end of the run; the same
table (plus every timestamped step line) is appended to
`maintenance\setup-desktop-windows.log` (or wherever `-LogPath` points). The log is
append-only -- it is never truncated, so history accumulates across runs.

Exit code is **1** only for one of three hard-prerequisite failures:
- Node `>=20` could not be resolved even after an install attempt (this includes a
  present-but-`<20` Node that was deliberately not auto-upgraded).
- The project directory or its `package.json` is missing.
- `.claude\settings.json` is corrupt, contains conflict markers, or its hash changed
  during the run (proof the script -- or something else running concurrently --
  mutated it).

Every other problem -- winget missing, non-admin long-paths, proxy/TLS interception,
occupied ports, git missing or too old, multiple Node/Git/Claude installs on PATH, a
dev-health timeout, missing Claude auth, low disk space, a OneDrive-located checkout --
is a **WARN** with an exact remediation string in the Detail column, and the run still
exits **0**.

## Elevation guidance

Three things benefit from an elevated (Run as Administrator) session; everything else
in this script works fine without admin:

- `winget install ... --scope machine` (Node/Git). Non-admin falls back automatically
  to `--scope user` -- fine for a single-user dev box.
- `git config --system` (this script never attempts this -- it only ever writes
  `--global`, specifically to avoid requiring admin).
- `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled`. Without admin,
  the script only reports the current value and prints the exact elevated command:
  ```
  New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWord -Force
  ```
  A reboot may be needed afterward for this to fully apply everywhere.

A non-admin run is the normal case and is fully supported; only run elevated if you
specifically need one of the three items above. The script never forces a reboot.

## Manual health checks reserved for humans

- **`claude doctor`** -- an interactive TUI. Never called by the script (it would
  hang a non-interactive run). Run it yourself in a terminal if Claude Code diagnostics
  are needed beyond what step 13 reports.
- **`npm run dev`** -- run it yourself to watch Brain Server come up at
  `http://localhost:8911` and web at `http://localhost:5273` in real time, and press
  Ctrl+C to stop it. The script's own `-StartDevServer` path automates a bounded
  version of this same check for a one-shot verification, then tears it down.

## Common WARNs and their fixes

| WARN | Fix |
|---|---|
| winget missing | Install "App Installer" from the Microsoft Store, or grab a release from `github.com/microsoft/winget-cli`. See `docs/MIGRATION_RUNBOOK.md` B1. |
| Node/Git installed but still unresolved | PATH is stale in this shell. Open a new `powershell.exe` window (or reboot), then re-run -- the script is idempotent and will just confirm success. |
| Multiple Node/Git/Claude installs on PATH | Likely nvm-windows/fnm or a duplicate MSI/scoop install. The WARN names which one currently wins; reorder PATH or uninstall the shadowed copy deliberately. |
| Node present but `<20` | Not auto-upgraded because it may be pinned for another app. If safe to upgrade: `winget install --id OpenJS.NodeJS.LTS -e`. Note this is still a hard-fail exit (1) until Node `>=20` resolves. |
| `LongPathsEnabled` not 1, non-admin | Run the elevated `New-ItemProperty` command above from an admin PowerShell, then reboot. |
| `core.autocrlf` churn | The script only ever sets `false` when the value was unset or `true`; an explicit `input`/`false` is left alone. If you're seeing line-ending churn, check whether `.gitattributes` disagrees with your global config -- the script will not touch the working tree to "fix" this. |
| Occupied port 8911/5273 | Something else (or a leftover process) is already listening. The script reports the owning PID/name but never kills it; `-StartDevServer` will skip health-checking that port until it's free. |
| Low disk space (<3 GB) | Free up space before installing -- see `maintenance/ora-nightly-disk.ps1` for the routine cleanup this box already runs. |
| Missing `%USERPROFILE%\.claude.json` | Claude Code may be unauthenticated. Run `claude` once interactively to log in. |

## Corporate-network remediation (report-only)

The script does not attempt to fix a corporate proxy or TLS-intercepting root
certificate -- it can only surface the signature (an `npm install` failure containing
`SELF_SIGNED_CERT_IN_CHAIN` or `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, or a stalled
`winget`/`claude --version` call). Remediation:
- Proxy: set `HTTP_PROXY`/`HTTPS_PROXY`, `npm config set proxy`/`https-proxy`, and
  `winget --proxy` as needed for your network.
- TLS interception: point `NODE_EXTRA_CA_CERTS` (or npm's `cafile`) and git's
  `http.sslCAInfo` at the corporate root CA PEM.
- **Never** set `npm config set strict-ssl false` or `git config http.sslVerify false`
  to work around this -- that disables certificate validation entirely.

Full detail: `docs/MIGRATION_RUNBOOK.md`.

## OneDrive caution

Keep `oxford-command-center` at a plain-profile path (e.g.
`C:\Users\Owner\oxford-command-center`), **outside** any
`OneDrive - Oxford Capital Partners (1)` folder. A OneDrive-synced checkout can
dehydrate files mid-session and corrupt `node_modules` or lock files under active
development. Step 7 (`ProjectLocate`) WARNs if the resolved path contains `OneDrive`.

## Idempotency and safety statement

Re-running this script is always safe: every step detects current state before
acting and skips anything already satisfied. If a nightly disk-clean or other process
partially wipes `node_modules` mid-session, `npm run gate` (triggering
`ensure-deps.mjs`) self-heals it on the next run. The script proves to itself that it
never mutated `.claude\settings.json` by hashing the file before (step 8) and after
(step 13) the run and FAILing loudly if the hash ever differs.

## Cross-references

- `docs/MIGRATION_RUNBOOK.md` -- full machine migration: Python for hooks, gh CLI,
  netlify CLI, Outlook COM profile, secrets placement, OneDrive hydration, and
  scheduled-fleet re-registration (sections B1 Provision, B3 Burn-in). This dev-setup
  script is strictly the project-bring-up subset of that larger process.
- `maintenance/ora-nightly-disk.ps1` -- the scheduled disk-reclaim routine this box
  already runs; relevant if the Preamble step WARNs about low free disk.
