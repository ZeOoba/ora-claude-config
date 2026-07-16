---
name: ""
metadata: 
  node_type: memory
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
---

**Status: PROPOSAL ONLY.** Nothing in `session-env\` has been touched. This is a policy design for Gabriel's approval; the pruning script itself is a separate follow-up once the policy below is signed off.

## 1. What `session-env\` is (empirically confirmed 2026-07-09)

- 763 directories, UUID-named, dated 2026-07-05 22:09 through today (2026-07-09), growing ~150–350/day (7/6: 83, 7/7: 101, 7/8: 352, 7/9: 222 and counting). At this rate it reaches ~50–100K dirs/year if left alone.
- Every sampled directory is **completely empty** — confirmed via `find` (no nested files) and PowerShell `Get-ChildItem -Force` (zero items, not even hidden/system files) on three independent samples. Zero disk cost per directory beyond the NTFS directory-entry/MFT overhead; the risk here is filesystem clutter and enumeration slowdown for any tool that globs `.claude\**` (backup scripts, doctrine probes), not storage.
- No reference to `session-env` exists anywhere in `settings.json`, hooks, or any other tracked config (`grep -r` returned zero hits). It is therefore almost certainly created by the Claude Code / claude-desktop application binary itself — not by any ORA skill, hook, or scheduled task — most likely a per-session (or per-process) scratch/working-dir stub the app creates but was never wired to clean up.
- **It is the sibling of `hooks\sessions\`**, keyed by the identical sessionId namespace. Confirmed directly: UUID `006ecde9-8f07-4a02-8e6b-5927591bda0d` exists in both `session-env\` (empty) and `hooks\sessions\` (containing real EOS plan-gate marker files: `gate-green`, `plan-approved`, `shared-checkout-warned-oxford-command-center`). `hooks\sessions\` is the EOS plan-gate override directory referenced in the Engineering OS spec; `session-env\` is a distinct, content-free directory under the same per-session UUID.

## 2. Live-session dependency check — real, not hypothetical

Cross-referenced all 9 currently-running Claude Code processes (`C:\Users\Owner\.claude\sessions\*.json`, PID-keyed, verified live via `Get-Process`) against `session-env\`:

**All 9 of 9 active sessionIds have an exact-match directory in `session-env\`**, with directory mtimes tracking recent activity (e.g. this session, `a744d8cf-2abe-4151-98ea-2bd224723db2`, mtime updates through the live conversation). This proves the directories are NOT purely disposable-on-creation — a currently-open session's directory persists and is live-referenced for the session's duration.

**Conclusion: a pure age-cutoff with no cross-check is not safe.** The safety net has to be the same one `sessions\*.json` already provides for the process registry: cross-reference sessionIds, not just mtime, before deleting.

The corollary also holds: the ~750+ directories with NO matching entry in the current 9-row `sessions\*.json` are, by definition, orphaned from sessions that have already ended (the PID registry is small and evidently self-cleans on process exit — only 8 entries versus 763 in session-env). Given the extreme creation cadence (a new dir roughly every 30–90 seconds during active hours, sometimes seconds apart — far higher than "one per top-level interactive session"), most of these 750+ are very likely per-tool-invocation or per-subagent scratch dirs from completed work, not just ended top-level sessions.

## 3. Precedent: the retired ora-session-pruner vs. the live hooks\sessions\ age-gate

Two different precedents exist, and they point in different directions for this artifact class:

**a) Retired `ora-session-pruner`** (`C:\Users\Owner\.claude\_scheduled_tasks_backup\ora-session-pruner\SKILL.md`, last revised 2026-05-25, confirmed retired — present only in the backup folder, not in the active `scheduled-tasks\` registry): targeted **Cowork session records** (a completely different location: `local-agent-mode-sessions\...\local_<id>\`), not this directory. Its model: 14-day age threshold AND title must match a scheduled-task-derived name AND state ≠ running, then **surface a candidate list to Gabriel by email — never auto-delete**. The manual-approval requirement was justified because those sessions hold real conversation content and named, non-automation work sessions had to be excluded by name-matching.

That justification **does not transfer to `session-env\`**: these directories are proven empty placeholders with no content of any kind, not named work products. Requiring manual per-item approval for an empty stub folder is disproportionate.

**b) The directly-applicable precedent is `ora-nightly-disk.ps1` step 4** (`C:\Users\Owner\.claude\maintenance\ora-nightly-disk.ps1`), which **already safely prunes the sibling `hooks\sessions\` directory today**, using exactly the mechanism this proposal needs:
```
# hooks/sessions/ prune -- delete EOS marker dirs not modified in 30+ days.
# A 30-day age gate can never select a live session (its dir is touched within seconds of now).
$cut = (Get-Date).AddDays(-30)
Get-ChildItem $sessDir -Directory | Where-Object { $_.LastWriteTime -lt $cut } | Remove-Item -Recurse -Force
```
This is the right logic (age-gate as the primary safety mechanism, on the reasoning that a live session's directory is touched continuously) — but two caveats surfaced during this investigation, both relevant to the new script:
- **The reasoning needs a belt-and-suspenders companion here**, not blind trust: `session-env\`'s creation cadence is 30–100x higher than `hooks\sessions\`'s, and it is a brand-new prune target with zero burn-in history, unlike `hooks\sessions\` which has been running for weeks. Cross-checking live sessionIds directly (§2) costs nothing and removes the single point of failure the "touched continuously" assumption represents.
- **The existing step 4 itself appears to have stopped firing**: `hooks\sessions\` still contains a directory dated 2026-06-05 (34 days old, well past its own 30-day cutoff), and `ora-nightly-disk.log`'s last entry is 2026-06-24 — 15 days stale as of today (2026-07-09). Before wiring a new step into this script, **verify the scheduled task that invokes it is still actually registered and firing** — otherwise the new session-env step inherits the same silent-non-execution failure mode.

## 4. Proposed policy

**Retention window:** delete a `session-env\<uuid>` directory only when **all** of the following hold:
1. `<uuid>` does not appear as the `sessionId` value in any `*.json` file currently in `C:\Users\Owner\.claude\sessions\` (the live PID registry — re-read fresh at run time, not cached).
2. The directory's `LastWriteTime` is **more than 72 hours (3 days)** in the past.
3. The directory's `LastWriteTime` is **not within the last 24 hours**, applied as an independent floor even if check 1 already passed — covers clock skew and the race where a brand-new session hasn't yet been PID-registered when the sweep runs.

A 3-day window (vs. `hooks\sessions\`'s 30 days) is deliberately tighter, proportionate to session-env's much higher creation rate and its role as a pure disposable scratch artifact rather than a state marker with any downstream reader.

**Implementation approach:**
- Add as a new step (step 5) in the existing `C:\Users\Owner\.claude\maintenance\ora-nightly-disk.ps1`, following its established pattern exactly (same log file, same `Log()` helper, same `-ErrorAction SilentlyContinue` posture, same "only act above a threshold" style already used for `send-log.txt` rotation and the `hooks\sessions\` step). Do not create a new standalone script — this is the same maintenance rhythm, same file, same nightly schedule slot.
- **Before adding the step, verify the scheduled task driving `ora-nightly-disk.ps1` is still actually firing** (per the 15-day-stale-log finding in §3b). If it isn't, fix that registration gap first — otherwise the new logic ships inert, same as the existing step 4 apparently is right now.
- Run in **log-only / dry-run mode for a burn-in period** (recommend 1–2 weeks: log every directory that WOULD be deleted and why, delete nothing) before flipping to live deletion. This is a lighter-weight version of the pruner's "surface, don't act" caution, calibrated to the lower stakes of an empty-directory target — full unattended automation after burn-in is appropriate here in a way it wasn't for named Cowork sessions with real content.
- Log format: mirror the existing log's timestamped-line style; each deletion line should record the uuid, its LastWriteTime, and confirmation that it was absent from `sessions\*.json` at sweep time.

**Explicit safety checks the script must perform, in order, before removing anything:**
1. Re-read `C:\Users\Owner\.claude\sessions\*.json` fresh at run time and build the live-sessionId set.
2. Skip (never delete) any `session-env\` directory whose name is in that set.
3. Skip any directory with `LastWriteTime` newer than 24 hours ago, regardless of check 2's result.
4. Only delete directories older than 72 hours AND absent from the live-sessionId set.
5. Confirm via `find`/`Get-ChildItem -Force` immediately before deletion that the directory is still empty (defensive re-check in case the app has since started writing real content into these dirs in a future version) — abort that single directory (log + skip, don't fail the whole sweep) if it is non-empty.
6. Log every deletion and every skip-for-safety with its reason; never delete silently.
7. During the burn-in period, perform steps 1–5 and log the would-delete list without calling `Remove-Item`.

**Open items requiring Gabriel's sign-off before implementation:**
- Confirm the 72-hour / 24-hour thresholds (vs. e.g. a flat 7-day window matching more conservative norms elsewhere in the fleet).
- Confirm folding this into `ora-nightly-disk.ps1` (recommended) vs. a standalone script.
- Confirm the burn-in (log-only) period length before live deletion is enabled.
- Separately: the discovery that `ora-nightly-disk.ps1`'s own `hooks\sessions\` step 4 appears to have stopped firing 15+ days ago is itself worth a quick registration check, independent of this proposal.
