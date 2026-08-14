---
name: reference-skill-reimport-sync-lag
description: "Claude Desktop's SkillsPlugin serves skill content from a shared local store updated by a periodic background sync (visible in main.log), not live from the ora-skills base directory on save — \"Save skill\" registers the update remotely but local propagation lags up to ~10 min behind"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5a7bfdba-a5f3-4109-b86d-6ba15088d55e
  modified: 2026-08-03T18:55:26.507Z
---

**Where served content actually comes from:** for a locally-installed skill (e.g. `exception-detection`), the Skill tool's "Base directory" (`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\<profile-guid>\<id-guid>\skills\<skill-name>\SKILL.md`) is a **single shared store reused across every session/agent spawned from that app instance** — not a per-session copy. Confirmed via `AppData\Roaming\Claude\logs\main.log`: repeated `[CCD] Using skills plugin at: <identical path>` lines across separate, unrelated session starts throughout a day.

**Why a reimport can still read stale for a while:** content in that shared directory only updates via a periodic `[SkillsPlugin] Starting skills sync` → `Found N enabled skills` → `Delta: X to download, Y to remove` → `Sync complete` cycle in `main.log`. Observed cadence: roughly every 2–10 minutes (event-driven with an idle-poll fallback, not a fixed timer). Clicking "Save skill" registers the updated package to a remote skill store immediately, but the **local file — and therefore what the Skill tool actually serves — doesn't change until the next sync tick downloads it**. Live-verified 2026-07-21: a sync at 13:08:51 showed `Delta: 0` (update not yet visible remotely); the next sync at 13:11:46 showed `Delta: 1 to download`, completing at 13:11:47 — matching the target SKILL.md's `CreationTime`/`LastWriteTime` to the second. Any session/agent invocation of the Skill tool before that sync tick fires sees the old content, **regardless of how "fresh" the session is** (a brand-new Agent spawn started before the tick reads the same not-yet-updated shared file everyone else does). This is an async propagation race, not an in-memory cache that ignores disk changes outright — the served content genuinely does come from that on-disk file, just not always the current version of it.

**Systemic implication:** `ora-skills/_staging/PENDING_REIMPORT.md` clearing (via `pending_reimport.py clear`) on a "Save skill" click is **not proof the update is live** — it only confirms the reimport/registration step ran, not that the sync-to-local-disk step has completed. Testing a skill update within the sync-tick window (up to ~10 min, occasionally faster) after clicking "Save skill" risks a false "the reimport didn't take" read across the entire skill library, not just this one instance.

**Correct verification procedure before trusting a "stale" reading:**
1. Grep `AppData\Roaming\Claude\logs\main.log` for `SkillsPlugin` entries timestamped after the "Save skill" click.
2. Confirm a `Starting skills sync` → `Delta: N to download` (N ≥ 1) → `Sync complete: N downloaded` sequence exists after that click.
3. Cross-check the target skill's `SKILL.md` file `LastWriteTime`/`CreationTime` in the shared skills-plugin directory matches that sync's completion timestamp.
4. Only then re-invoke the Skill tool and treat its content as authoritative. No app restart is required — the sync runs continuously in the background across the app's lifetime, not gated on session or app restart.

No standalone "force resync now" command was found during this investigation — if one exists in the app UI, it wasn't identified; the practical workaround is simply waiting for/confirming the next natural sync tick via the log.

See [event_log.md](event_log.md) 2026-07-21 entry for the specific `exception-detection` v1.1→v1.2 case this was diagnosed from.

---

## 2026-08-03 UPDATE — mirror *content* stopped being evidence of installation

**What changed after this memory was first written.** `ora-skills`'s pre-commit hook gained **Check 4** on 2026-07-26 (`tools/sync_appdata_mirror.py`, invoked as `--check-staged`): on every commit it copies each staged skill's shipped files into whichever AppData runtime-cache mirror(s) already hold that skill. It is additive-only and never blocks the commit. The copy preserves the *source* mtimes, so the mirror ends up holding content-identical files that look like a normal install.

**Consequence — the obvious verification is now non-discriminating.** "Confirm the mirror contains all N files" and even "confirm mirror SHA-256 == repo SHA-256" both return PASS immediately after the commit, *before anyone clicks Save skill*. A ship plan that verifies installation that way is verifying nothing (see [feedback_verified_null_vs_inferred_null.md](feedback_verified_null_vs_inferred_null.md)). Hash-vs-repo still answers **what** content is there; it cannot answer **whether an install happened**.

**What still discriminates, strongest first:**
1. **`main.log` sync sequence with a non-zero delta** — the primary evidence, and the procedure already given above. A Save-skill click produces `Triggered sync (5s delay)` → `Starting skills sync` → `Delta: N to download` (N ≥ 1) → `Sync complete: N downloaded`. The hook's file copy produces no `SkillsPlugin` log activity at all, so a non-zero delta cannot be manufactured by Check 4.
2. **mtime delta against a baseline captured before the click** — usable when the log is unavailable, and it should match the sync's completion timestamp to the second.

**Live case, 2026-08-03 (deal-execution v1.3 + legal-intelligence v1.2).** Commit `1567da7` fired Check 4 and wrote 3+1 content-identical v1.3/v1.2 files into the mirror carrying 08-01 source mtimes — a file-count check would have passed a full day before the click. The click at 14:51:03 produced `Delta: 2 to download` → `Sync complete: 2 downloaded, 0 failed` at 14:51:09, and all four mirror files were rewritten at exactly 14:51:09. The follow-up sync at 14:51:13 showed `Delta: 0`, i.e. propagation complete. Both discriminators agreed; hash-vs-repo then confirmed the content. Detail: [event_log.md](event_log.md) 2026-08-03 entry.

**Standing implication for any future skill ship:** capture a pre-click mirror baseline (or plan to read `main.log`) *before* committing, because the commit itself contaminates the mirror. Also note Check 4 means a commit alone writes to the runtime cache — relevant to any ship run under a "no runtime-cache write" constraint.
