# ORA Linux server -- secrets manifest

Every secret the server needs, where it lives, and how it travels.
**Transport rule (runbook B1.5): out-of-band ONLY -- direct scp/USB between
Gabriel's own machines. NEVER via git, OneDrive, email, or chat.**
None of these files is ever tracked by git; the pre-push confidential scan
(fail-closed) backstops mistakes, but do not rely on it.

| Secret | Lives at (server) | How it travels | Breaks without it | Verify (verify-setup.sh line) |
|---|---|---|---|---|
| Claude credentials | `~/.claude/.credentials.json` | scp from desktop `C:/Users/Owner/.claude/.credentials.json`, or skip and run `claude` login on the server | headless Claude Code sessions (`claude -p`) | `claude auth (-p smoke)` |
| Confidential terms list | `~/.claude/hooks/confidential-terms.json` | scp from desktop (1,428 B per runbook B1.5) | FAIL-CLOSED: confidentiality guard + pre-push scan brick sessions/pushes; hooks test suite SKIPs its guard suite | `confidential-terms.json` |
| Anthropic key (scheduled-task lane) | `~/.claude/scheduled-tasks/_shared/anthropic-key.dat` | scp from desktop (dir is git-UNTRACKED -- copy the whole `scheduled-tasks/` tree) | any re-homed scheduled task that reads the .dat key | (not checked -- desktop-lane residue; copy only if those tasks re-home) |
| Netlify token (scheduled-task lane) | `~/.claude/scheduled-tasks/_shared/netlify-token.dat` | scp from desktop, same tree as above | deploy-site skill lane | (not checked -- same as above) |
| Server env file | `~/.config/ora/ora.env` (mode 600) | created by provision.sh from `secrets.env.example`; values typed/pasted in over ssh | every systemd unit (EnvironmentFile), full gate, runner job env | `ora.env mode 600` + `ora.env defines *` |
| NOTION_TOKEN | inside `ora.env` | pasted from the Notion integration admin page (same token the GitHub watchdog secret uses) | ora-heartbeat.service -> watchdog 16h alarm trips | `ora.env defines NOTION_TOKEN` (presence only) |
| ANTHROPIC_API_KEY (optional) | inside `ora.env` (commented by default) | Anthropic console | nothing, if `claude` login is used instead | `claude auth (-p smoke)` |
| FRED_API_KEY (optional) | inside `ora.env` (commented by default) | fred.stlouisfed.org account page | FRED macro tool + regional dynamics enrichment (gate unaffected) | (not checked -- optional) |
| GitHub runner registration token | consumed once by `install-runner.sh` (never stored) | minted at <https://github.com/ZeOoba/oxford-command-center/settings/actions/runners/new?arch=x64&os=linux>, expires ~1h | runner cannot register; existing runner unaffected | `GitHub runner service` |
| Runner job env | `~/actions-runner-occ/.env` (mode 600) | written by `install-runner.sh` from ora.env (contains corpus PATHS, not tokens -- still treat as sensitive) | full-gate workflow jobs lose WORKBOOK_PATH/FINANCIALS_DIR | `GitHub runner service` |
| rclone OneDrive token cache | `~/.config/rclone/rclone.conf` | created in place by the one-time `rclone config` device-code flow (M365 sign-in as ggoldberg@oxfordra.net) | ora-data-sync.service (hourly corpus pull) | `workbook file` + `financials corpus` (staleness shows up here) |
| Git push auth (SSH key or PAT) | `~/.ssh/id_ed25519` (or credential helper) | generated ON the server (`ssh-keygen -t ed25519`), public key added at <https://github.com/settings/keys> -- private key never travels | clones in provision.sh, vault-backup push, config-repo pulls | `BrainVault pushable` |

Notes:
- `ora.env` is the ONLY file here that provision.sh creates; everything else
  is a deliberate manual placement -- that is what makes them secrets.
- The two `.dat` files are Windows scheduled-task-lane residue: copy them only
  when/if those lanes re-home to the server; absence breaks nothing listed in
  server/units/.
- Rotation: revoking the Notion token, the runner (Settings -> Actions ->
  Runners -> Remove), or the rclone app grant (M365 My Sign-Ins) kills the
  corresponding lane only; nothing else on the box shares those credentials.
