---
name: reference_lean_ram_toolkit
description: "ORA lean-RAM toolkit — commands, slash commands, shortcuts, and the auto-park RAM watchdog. Built 2026-06-05 for the 5.7 GB box; RETUNED 2026-07-09 for the 32 GB machine (~24 GB working ceiling). Also covers the 2026-07-11 terminal/IDE rebuild (pwsh 7, Nerd Font, starship, Windows Terminal, VS Code) — see the dated sections for what survives vs superseded."
metadata: 
  node_type: memory
  type: reference
  originSessionId: fc2b8c61-e442-45dd-bcf1-f5b08b075d11
---

# Lean-RAM Toolkit (battlestation, 5.7 GB)

> **Why this exists:** the workstation has only **5.7 GB total RAM** and chronically runs ~0.2–0.7 GB free. Root cause = the Claude **desktop app** (Electron): a fixed **~1.3 GB shell** (renderer+main+gpu+utils) **+ ~130 MB per open Code session**. With 5–8 concurrent GUI sessions that is the whole machine. The fix is structural: run heavy/parallel work as **lean CLI sessions (~150 MB)** and shed the GUI. MCP/skill/cache tuning is rounding error by comparison.

## Hard facts (measured 2026-06-05)
- Electron shell ≈ 1.3 GB, only reclaimed by closing **all** GUI sessions.
- Each GUI Code session = its own `claude-code\…\claude.exe` child, ~45–170 MB, tagged with `--resume <session-id>` in its command line.
- Standalone CLI `claude.exe` (`C:\Users\Owner\.local\bin\claude.exe`) runs **independent of the desktop app**; resumes any session via `claude --continue` / `claude --resume <id>`.
- Current session id is exposed as env `CLAUDE_CODE_SESSION_ID` and in the hook stdin `session_id`.
- CLI sessions carry excel + context7 + skills + superpowers, **NOT** Outlook (composio lives only in the desktop config) — send mail in the GUI or via the Outlook COM script.

## PowerShell profile commands  (profile: `OneDrive…\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`)
Pure-ASCII only inside profile code (PS 5.1 reads .ps1 as ANSI; em-dashes/smart-quotes break parsing).
- `ram` — free-RAM + Claude-process snapshot
- `sessions` — list GUI Code sessions (PID, MB, session id, idle)
- `ora` — open a lean CLI session in the ORA workspace (GUI stays up)
- `heavy` — quit the whole GUI (~1.3 GB) → fresh lean CLI
- `handoff` — quit the whole GUI → resume the **latest** conversation in a lean CLI
- `handoff-solo <id>` — move **one** session to lean CLI: kills only that session's own GUI process (~130 MB), never the shell or others; resumes it standalone
- `clear-disk` — reclaim npm `_cacache` + non-core `_npx` dirs (**preserves** the Outlook/`mcp-remote` bridge). Guard: refuses unless GUI fully quit.

## Slash commands  (`~/.claude/commands/*.md`) — one-click inside Claude
Each spawns a **detached** standalone terminal (survives the GUI closing):
- `/ram` — inline RAM snapshot (safe)
- `/solo` — move THIS session to lean CLI, **leave the GUI + other sessions running** (uses `CLAUDE_CODE_SESSION_ID`)
- `/handoff` — quit whole GUI, resume this conversation lean
- `/heavy` — quit whole GUI, fresh lean CLI
- `/cleardisk` — quit GUI then clear-disk

## Desktop shortcuts  (`…\Documents\Desktop`)
- "Claude Handoff to CLI" → `handoff` · "Claude Lean CLI (fresh)" → `heavy`. **Correction 2026-07-11:** taskbar pinning is NOT categorically blocked — a prior session's note here was wrong (or only true of the old COM/verb-based pinning APIs, which Microsoft did retire). Real mouse-driven right-click → "Pin to taskbar" via computer-use worked fine for Windows Terminal. See the 2026-07-11 taskbar-pinning section below for the one real gotcha (frontmost-app focus, not the pin action itself).

## Auto-park RAM watchdog  (PostToolUse hook, in `~/.claude/settings.json`)
- Wrapper `~/.claude/hooks/ram-watchdog.sh` (bash, 60 s throttle) → `~/.claude/hooks/ram-guard.ps1` (logic).
- Tiers (tunable at top of `ram-guard.ps1`): **WARN_MB=300** (warn + offer /solo, no action) · **CRIT_MB=200** (auto-park the most-idle OTHER session) · **MIN_IDLE=300 s** (eligibility).
- Park = kill that idle session's process (~130 MB); session file persists, fully resumable. Never the current session (excluded by stdin `session_id`) or the shell. Falls back to warn if nothing safely idle or self can't be identified.
- **Activation:** new hooks need `/hooks` opened once (or restart) to load in an already-running session.

## Config changes banked (settings.json / .claude.json)
- `fred` MCP removed from `.claude.json` (≈80–120 MB). `chrome-devtools-mcp@chrome-devtools-plugins` plugin **disabled** (3 node procs gone).
- `skillOverrides`: 19 non-ORA skills `off`, 25 `user-invocable-only`. `autoCompactEnabled:true`, `cleanupPeriodDays:14`, `skillListingMaxDescChars:1536`.
- Deleted (regenerable): chrome-devtools vendored `node_modules` (~356 MB), `launch-preview-8111ca383298` (~121 MB) + `…-6e9e2b27502d` (~9 MB), telemetry queue, stale superpowers 5.0.7 cache.
- **GOTCHA:** the desktop app rewrites `claude_desktop_config.json` AND `~/.claude.json` while running — external edits to those get clobbered within seconds. Edit them only with the app fully quit. (`settings.json` and profile/commands/hooks are NOT clobbered.)

## Scheduled maintenance
- Windows Task **"ORA Nightly Disk Clean"** → `~/.claude/maintenance/ora-nightly-disk.ps1` (adaptive: always `npm cache clean`; full `_npx` clean only when GUI is down). Log: `~/.claude/maintenance/ora-nightly-disk.log`. **Recurring DAILY 04:00** (WakeToRun + StartWhenAvailable); set 2026-06-05.

## Agent fan-out concurrency (observed 2026-06-13)
- A **5-wide concurrent opus fan-out** (Workflow `parallel()` adversarial review, 5 lenses + synthesis) **hit a server-side rate limit** ("Server is temporarily limiting requests · Rate limited") and ALL agents failed — a false-clean result. Re-running the same review as **2 concurrent opus Agents** succeeded cleanly.
- **Calibration for this box:** cap adversarial/review fan-outs at **~2–3 concurrent opus agents**; for larger sweeps, batch or run sequentially. This is a request-burst limit (not RAM), but it compounds the existing CLAUDE.md guidance ("/ram before fan-outs, concurrency modest, 5.7 GB ceiling"). Prefer a few sequential Agent calls over a wide `parallel()`/Workflow fan-out here.

## Honest ceiling
5.7 GB is undersized for desktop-app + 4–5 concurrent agent sessions. Tooling buys headroom and automates cleanup; durable fix is behavioral (fewer concurrent GUI sessions) or hardware (more RAM). `[SPECULATIVE]` weekly fights = hardware ceiling, not config.

## 2026-07-09 — new 32GB machine (LAPTOP-CSHSCBE6, ASUS Zenbook S14): split what survives from what's superseded
This whole toolkit was built for the 5.7 GB box. On the new machine (32GB total, ~4.7GB free observed at idle — still not enormous, but an order of magnitude more headroom):
- **Superseded (RAM-driven):** the heavy/handoff/solo/clear-disk premise (reclaim ~1.3GB by quitting the GUI) is now marginal — that's ~4% of total RAM, not a meaningful constraint. The RAM watchdog's WARN_MB=300/CRIT_MB=200 thresholds are likewise under 1% of total and effectively inert (see settings.json audit finding, 2026-07-09).
- **Survives unchanged (NOT RAM-driven):** the "Agent fan-out concurrency" cap above (~2-3 concurrent opus agents for adversarial/review fan-outs) is a **request-burst rate-limit**, explicitly confirmed in that section's own text ("This is a request-burst limit (not RAM)"). More RAM does not relax it — do not widen fan-outs on this machine on the assumption that 32GB fixes it; prefer sequential/batched Agent calls for wide adversarial reviews exactly as before.
- Do not delete this file's RAM-specific guidance — if this profile is ever synced back to a genuinely RAM-constrained box, it's still correct there.

## 2026-07-09 (evening) — ratified re-tune executed (RAM_POSTURE=RETUNE-32GB, ~24 GB working ceiling)
Gabriel ratified the 32 GB posture via the setup-audit remediation MCQ; the doctrine surfaces were updated this session. Old → new values (event-logged same day):
- `hooks/ram-guard.ps1`: `WARN_MB` 300 → **2048** · `CRIT_MB` 200 → **1024** (`MIN_IDLE` 900 unchanged). The watchdog is meaningful again instead of effectively inert.
- EOS spec §9 parallelism: `Workflow`/parallel concurrency "≤ a few" → **≤ 8** (tool self-cap `min(16, cores−2)` still binds); machine line now reads 32 GB physical / ~24 GB working ceiling.
- **UNCHANGED:** the ~2–3 concurrent-opus adversarial/review fan-out cap (request-burst rate limit, not RAM — see the section above). Footprint discipline also stays: no standing RAM-heavy services (Docker etc.) without justification.
- Mirrors updated: `docs/system-inventory.md` hardware section, `daily-setup-audit-prompt.md` + plugin `ora-setup-self-audit` footprint lines, `commands/ram.md` baseline note, `tech.md` machine constraints, `00_system_of_record.md` §hardware line. Gabriel's User Preferences 5.7 GB line is his manual edit — flagged, not touched.

## 2026-07-11 — closed a real post-migration gap: pwsh 7 + Nerd Font were never actually installed
The profile's own header claims "Works in PowerShell 7 (pwsh) and Windows PowerShell 5.1" and the banner/prompt use Nerd Font codepoints (`0xF07B` folder, `0xE0A0` powerline branch) — but on LAPTOP-CSHSCBE6 neither **pwsh** nor any Nerd Font was actually installed (the `~/.claude` wholesale-copy migration only carries what's under `~/.claude`; PowerShell/Windows Terminal/fonts live outside it and were never reinstalled). Practical effect pre-fix: the banner rendered with tofu/missing glyphs, and anything assuming `pwsh` on PATH would have silently fallen back to Windows PowerShell 5.1 or failed.
- **Fixed:** installed PowerShell 7 (`winget Microsoft.PowerShell`, exposed via MSIX alias at `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` — NOT under `Program Files\PowerShell\7\`, that path doesn't exist for the Store/winget install) and JetBrainsMono Nerd Font (`winget DEVCOM.JetBrainsMonoNerdFont`, family name **"JetBrainsMono NFM"** for terminal use — the Mono variant, not plain "JetBrainsMono NF").
- Windows Terminal (`%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`) repointed `defaultProfile` to a new explicit pwsh-7 profile, set `profiles.defaults.font.face` = "JetBrainsMono NFM" + `colorScheme` = "One Half Dark" globally. Verified the profile loads clean and the banner renders under the new pwsh.
- **starship** was installed (`winget Starship.Starship`) and, in a same-day follow-up, **wired into both `$PROFILE`s** (pwsh 7 + WinPS 5.1) — appended right after `Show-Banner`, so the static banner still prints once at shell start but starship's `function prompt` now overrides the old custom folder/git-branch prompt for per-command rendering. Config: `C:\Users\Owner\.config\starship.toml`. **Gotcha:** freshly-spawned `pwsh`/`powershell.exe` processes from a stale parent shell don't see winget's PATH update, so `starship` alone in the init line threw `CommandNotFoundException` — fixed by hardcoding the full path (`Invoke-Expression (&"C:\Program Files\starship\bin\starship.exe" init powershell)`) instead of relying on PATH.
- **pwsh-7 profile parity fix:** the ORA lean-CLI toolkit (`ram`/`ora`/`heavy`/`handoff`/`sessions`/`clear-disk`) only ever existed in the WindowsPowerShell 5.1 profile (§ above) — never ported to the pwsh 7 profile because pwsh wasn't installed until 2026-07-11. Since pwsh 7 is now the Windows Terminal default, the full toolkit was copied into the pwsh 7 profile too so switching shells doesn't silently drop those commands. Keep both profiles in sync going forward when editing either.
- **VS Code reinstalled 2026-07-11:** `winget Microsoft.VisualStudioCode`. Extensions did **not** need reinstalling — `C:\Users\Owner\.vscode\extensions\` (45 extensions incl. `anthropic.claude-code`) survived the migration independently of the `~/.claude` wholesale copy (unclear mechanism — this path is outside `~/.claude` entirely, so the "migration only copied `~/.claude`" assumption from the 2026-07-09 setup audit is not universally true; some non-`.claude` folders partially carried over while others, like `AppData\Roaming\Code\User\settings.json` and Windows Terminal's settings, did not). VS Code auto-detected the pre-existing extensions folder on first launch with zero reinstalls. New `settings.json` created from scratch (theme **"SynthWave '84"** — chosen because its neon green/cyan/magenta palette exact-matches the RGB values hardcoded in the PowerShell banner above, a strong signal it was the original paired theme; alternatives `Dracula Theme` / `Tokyo Night` are also installed if wrong), material icon theme, JetBrainsMono NFM font, prettier/ruff format-on-save, integrated terminal defaulted to pwsh 7 + the Nerd Font.
- **Path gotcha (for future sessions):** `$PROFILE` for both PS5.1 and pwsh 7 resolves under `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\...` — Windows has KFM-redirected "Documents" into the business OneDrive. Checking the bare `%USERPROFILE%\Documents\...` (no OneDrive segment) finds nothing and wrongly looks like the profile doesn't exist. Same applies to `Documents\Desktop` shortcuts referenced above.

## 2026-07-11 (later) — taskbar pinning via computer-use + a GitHub Copilot near-miss
Closed out the terminal rebuild by pinning both apps to the taskbar via the `computer-use` MCP (real mouse clicks, not COM/verb automation).
- **Windows Terminal:** pinned cleanly — `request_access(["Terminal"])` (click-tier only, but that's enough), `open_application`, right-click its taskbar icon, click "Pin to taskbar" in the jump list. One clean pass.
- **VS Code:** pinning itself is the same mechanic, but it failed repeatedly and for a real reason worth remembering: **the permission-tier "frontmost application" check is keyed to whichever app currently has OS focus, not whichever app is under the click coordinates.** With VS Code (click-tier: left-click only, no right-click) focused, right-clicking its *taskbar* icon still errors as a VS Code right-click, not a shell action — even though the pixel is on the taskbar. Fix: left-click empty desktop first (shifts focus to the shell, which needs a `request_access(["File Explorer"])` grant — full tier) so the frontmost app is shell, THEN right-click the taskbar icon.
- **Real near-miss:** mid-troubleshoot, a click intended for "Pin to taskbar" landed instead on VS Code's first-run "Sign in to use GitHub Copilot" dialog (which kept resurfacing/stealing focus) and triggered a live GitHub OAuth device-code flow (code `47AB-6040` was issued). **No account action completed** — every prompt was clicked Cancel/No immediately and the flow ended in "Sign-in failed," confirmed via the toast text before moving on. Lesson: when an unrelated first-run/onboarding modal from a just-installed app keeps grabbing focus during unrelated taskbar/window automation, stop and let the human dismiss it rather than continuing to click blind near it — the risk isn't the pin, it's whatever dialog happens to be sitting under the coordinates. VS Code's taskbar pin was finished manually by Gabriel instead of forcing it through.

## 2026-07-11 (later still) — Claude-Code-specific performance pass, all 5 items done
Gabriel asked what would make Claude Code itself perform better given this setup; five items were identified and all implemented same session:
1. **Banner-pollution fix (both `$PROFILE`s):** `Show-Banner` was unconditional — any non-interactive/redirected invocation (Desktop Commander's teed PowerShell, or any future `pwsh`/`powershell` call missing `-NoProfile`) got the ANSI banner mixed into captured stdout. This was already a documented pain point — `ora-weekly-hygiene/SKILL.md` §Block B explicitly works around "the Desktop Commander shell... prints a banner and SWALLOWS the script's stdout" by teeing to a file instead of trusting console capture. Fixed by wrapping the call: `if (-not [Console]::IsOutputRedirected) { Show-Banner }`. Verified: running the profile through this Bash tool (which redirects stdout) now shows no banner while `ram`/`prompt` (starship) still work; a real interactive terminal still gets the banner. Existing real automation (`send-via-outlook.ps1`, `ram-guard.ps1`) was independently grepped and confirmed already `-NoProfile`-safe — no live breakage existed, this closed a latent trap.
2. **OneDrive Files-On-Demand pinned for `Claude_Workspace`:** same SKILL.md documents `Operation not permitted` errors from cloud-only placeholders. Ran `attrib +P -U "...\Claude_Workspace" /S /D` (via a temp .bat — Git Bash mangles `cmd.exe /c`/`attrib` argument quoting directly, use a script file) to force full local hydration + pin. Folder is 1.5 GB — scoped to `Claude_Workspace` only, not the whole (much larger) OneDrive business root, to avoid an unprompted multi-GB download. Verified via `attrib` output showing the `P` flag on the folder. Extending to other project folders is a manual follow-up if wanted.
3. **VS Code `files.watcherExclude` + `search.exclude` added** (`node_modules`, `.git/objects`, `dist`, `build`, `.next`, temp/lock-file patterns) — previously unset, meaning VS Code's watcher and OneDrive's sync engine were both polling the same tree with zero exclusions.
4. **VS Code `files.autoSave: "afterDelay"` (1000ms)** — added to avoid the stale-buffer conflict prompt when Claude Code edits a file that's also open (unsaved) in the VS Code UI.
5. **Claude Code statusLine configured** via the built-in `statusline-setup` agent. Script: `C:\Users\Owner\.claude\statusline-command.py` (Python, not PowerShell — deliberately avoids the profile-pollution risk in item 1). Shows model display name, git branch (via `git --no-optional-locks`, 2s timeout, omitted outside a repo), context-window used %, Claude.ai 5-hour rate-limit used % (color-coded green/yellow/red), session cost, and net lines changed. Registered in `settings.json` → `statusLine`.
- **Any future statusline changes should go through the `statusline-setup` agent again**, not ad hoc edits to the script/settings.json.

## 2026-07-11 (final) — statusline verification found the agent's schema claim was wrong; corrected with real captured data
Asked to "check the statusline in a fresh session." A genuinely fresh `claude` session showed only the bare model name ("Sonnet 5", no `ctx`/`5h` segments) — looked broken but wasn't: `context_window.used_percentage` is `null` at zero usage and `rate_limits` only populates after the first API response, so there was nothing else to show yet. Confirmed by temporarily logging raw stdin to a debug file and launching one more fresh session (`wt.exe -p "PowerShell 7" pwsh -NoExit -Command claude`, captured payload read back via Bash — no computer-use needed for this part).
- **Real captured payload contradicted what the `statusline-setup` agent asserted.** It claimed `total_cost_usd` / lines-added-removed / duration fields don't exist in the current schema. The actual captured JSON has all of them: `"cost":{"total_cost_usd":0,"total_duration_ms":...,"total_api_duration_ms":...,"total_lines_added":0,"total_lines_removed":0}`. **Lesson: even a purpose-built schema-aware subagent's claim about a live API/stdin schema is worth spot-verifying against a real captured payload before trusting it into a config file** — it doesn't have shell access in this harness and was going on the documentation it was given, which was stale here.
- Script updated to add the cost (`$X.XX`) and net-lines-changed (`+N/-M`, green/red, omitted when both zero) segments using the verified real field names. Debug-logging code was temporary and has been removed. Tested against both a zero-usage payload (`Sonnet 5 | $0.00`) and a realistic-usage payload (`Sonnet 5 | ctx 5% | 5h 18% | $0.84 | +37/-12`) — both render correctly.
- **This session left 2 throwaway `claude.exe` processes running** (spawned via `wt.exe` purely to capture the real stdin payload) among the ~24 already running on this machine (this user runs a real concurrent-session fleet — see the toolkit's own `ram`/`sessions` commands above). Could not safely identify which 2 PIDs were the throwaway ones from `Get-CimInstance`/`tasklist` alone (timestamps clustered too closely with other legitimate sessions) — did **not** guess-kill any process. Left for Gabriel to close the 2 new terminal windows manually. If this recurs, tag spawned-for-verification sessions somehow (e.g., a distinguishing `--append-system-prompt` marker or a unique starting cwd) so they can be found and cleaned up programmatically afterward instead.
