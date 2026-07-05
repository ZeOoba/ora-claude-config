# ORA Linux server provisioning kit

Turns a fresh Ubuntu 24.04 box into the always-on half of the two-tier
estate: the engineering fleet (oxford-command-center dev + full gate +
self-hosted GitHub runner) and the clock-critical headless jobs (Notion
heartbeat, BrainVault backup, telemetry rollup, data sync). The Windows
desktop keeps Cowork/LAMS, the Outlook COM send lane, OneDrive, and the
Obsidian UI -- nothing here touches those.

Everything in this directory is idempotent: re-run any script after a
partial failure.

## Order of operations

| # | Step | Command |
|---|------|---------|
| 1 | Provision | `bash server/provision.sh` (as the login user; it uses sudo where needed) |
| 2 | Secrets | fill `~/.config/ora/ora.env`; place the out-of-band files -- see `SECRETS-MANIFEST.md` |
| 3 | Data | `rclone config` once, then `bash ~/.claude/server/rclone-sync.sh` -- or push from Windows with `desktop-push-data.ps1` (pick ONE transport) |
| 4 | Verify | `bash ~/.claude/server/verify-setup.sh` -- repeat until zero FAILs |
| 5 | Enable timers | `systemctl --user enable --now ora-heartbeat.timer ora-vault-backup.timer ora-telemetry-rollup.timer ora-full-gate.timer ora-data-sync.timer` |
| 6 | Runner | mint token, then `RUNNER_TOKEN=<t> bash ~/.claude/server/install-runner.sh` |

Timers are deliberately NOT enabled by provision (step 5 is human-gated on
step 4 passing). The GitHub Actions watchdog (ZeOoba/ora-cowork-watchdog)
stays where it is -- it is the off-box monitor for the heartbeat this server
now produces. Disable the old Windows-side producers (LAMS heartbeat task,
18:00 vault-backup schtask) only AFTER their server twins have fired
successfully once -- two writers is a worse failure than a day of overlap.

## What is in here

- `provision.sh` -- one-shot setup (apt, TZ, fnm/Node 22, Claude Code,
  repos, data dirs, ora.env seed, pre-push shims, npm install, user units)
- `verify-setup.sh` -- read-only burn-in smoke test (PASS/FAIL/WARN table)
- `install-runner.sh` -- self-hosted Actions runner (labels
  `self-hosted,linux,ora-data`) for the full data-bound gate
- `heartbeat.py` + `units/ora-heartbeat.*` -- Notion heartbeat producer
- `units/` -- systemd --user units (all `Type=oneshot`, all timers
  `Persistent=true`, env from `~/.config/ora/ora.env`)
- `rclone-sync.sh` / `desktop-push-data.ps1` -- the two data transports
- `run-full-gate.sh` -- gate wrapper (SKIPs cleanly when data absent)
- `secrets.env.example` -> `~/.config/ora/ora.env`; `SECRETS-MANIFEST.md`

## Irreducible manual actions

| Action | Why it cannot be scripted | Exact step |
|---|---|---|
| Fill `~/.config/ora/ora.env` | secrets never travel via git | `nano ~/.config/ora/ora.env && chmod 600 ~/.config/ora/ora.env` |
| Place `confidential-terms.json` | untracked by design (fail-closed guard data) | from desktop: `scp C:/Users/Owner/.claude/hooks/confidential-terms.json <user>@<server>:.claude/hooks/` |
| Claude auth | interactive device-code login to Gabriel's account | run `claude`, log in; or copy `.credentials.json` (manifest row 1) |
| GitHub auth for clones/push | key must be minted and authorized by a human | `ssh-keygen -t ed25519` then add the `.pub` at <https://github.com/settings/keys> |
| rclone OneDrive grant | M365 device-code consent as ggoldberg@oxfordra.net | `rclone config` (remote name `onedrive-oxford`, type `onedrive`); see rclone-sync.sh header |
| Runner registration token | minted per-repo by GitHub, expires ~1h | <https://github.com/ZeOoba/oxford-command-center/settings/actions/runners/new?arch=x64&os=linux> |
| Enable timers | human-gated on verify-setup passing (burn-in doctrine) | step 5 command above |
| Firewall | network policy is operator-owned | ufw block printed at the end of provision.sh |
| Timezone (if provision could not sudo) | timers fire in local time; cadence is ET | `sudo timedatectl set-timezone America/New_York` |
