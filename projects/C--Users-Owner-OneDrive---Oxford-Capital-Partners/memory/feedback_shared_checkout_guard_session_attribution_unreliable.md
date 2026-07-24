---
name: feedback_shared_checkout_guard_session_attribution_unreliable
description: "shared-checkout-guard's \"session X is open right now (working)\" attribution can name a session with no trace in any registry — verify via list_sessions + session-env mtime before treating it as a live blocker"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0d9560cc-b5e5-4b44-bd5c-e7af834db249
  modified: 2026-07-24T16:36:36.283Z
---

On 2026-07-19, editing `~/.claude/projects/.../memory/MEMORY.md` (a covered path in `shared-checkout-guard.py`'s `DEFAULT_REPOS`), the guard twice fired a warning naming session `eda91426-76a8-493b-9111-eb4250c3f6c7` as "open right now (working)" — before and after the edit, unchanged. Direct verification found no evidence this session was live:
- Not present in `list_sessions` (active or `include_archived: true`).
- Its `session-env` directory existed but was empty and untouched for ~4 hours at check time.
- The actual uncommitted `MEMORY.md` diff the guard was reacting to had an mtime (2026-07-18 17:42) that predated the session-env directory's own creation (2026-07-19 11:23) — the flagged session couldn't have produced the WIP it was being blamed for.
- `git status --short` on `~/.claude` returned an identical 27-entry file set before and after the edit, with no changes attributable to another actor during the check window.

Proceeded with the edit given this evidence; no conflict materialized.

**Why:** the guard's session-attribution heuristic (whatever produces the "session X is open" name) is not the same signal as `list_sessions`/session-env activity, and can name a stale or already-terminated session. This is the same category as [[feedback_verify_wip_settled_via_mtime]] (isRunning isn't per-file) and [[feedback_verify_probe_findings_before_acting]] (a probe finding is a hypothesis, not a verdict) — a hook's claim of "this session is doing it" needs the same ground-truthing as a claim of "this file changed."

**How to apply:** when `shared-checkout-guard.py` (or any hook) names a specific session ID as the source of contention on a shared `~/.claude` path, don't take the attribution at face value even if it repeats unchanged across calls. Cross-check: (1) `list_sessions`/`get_session` for that ID, (2) the named session's `session-env/<id>/` directory mtime relative to now, (3) the actual conflicted file's own mtime relative to the named session's start time. If none of the three corroborate a live actor, the attribution is likely stale and it's reasonable to proceed with an additive, targeted edit rather than isolating/waiting indefinitely. This doesn't relax the underlying single-writer doctrine ([[reference_concurrent_session_duplicate_hardening_work]]) — it's specifically about not trusting an unverified session-ID label from the guard itself.

## ROOT-CAUSED AND FIXED 2026-07-24 (Gabriel-approved live hook edit)

Fourth instance, then the actual cause. During the 2026-07-24 `ora-deal-aging-sla` run the guard named session `99aea6a4` across ~8 consecutive warnings; that session had been `idle` since 10:35:01 and had **no provenance dir under `hooks/sessions/` at all**, so it demonstrably made none of the 10:51 commits that were the real contention.

**Root cause (read at `shared-checkout-guard.py`, pre-fix):** the attribution was `others[0]` — literally the FIRST element of `session_liveness.other_active_sessions()`, an arbitrary index into a dict — asserted as *"likely the source of this WIP."* There was never any link between the named session and the dirty files. With ELEVEN sessions concurrently registered that day, the name was close to a coin flip. All four instances above are the same one-line defect, not four separate stale-data flukes.

**Fix:** `_attribute_wip()` now names a session ONLY when that session's own recorded touched-set (`commit_provenance.read_touched`, the same data `commit-provenance-guard.py` consumes) intersects the paths from `git status --porcelain`. With no such evidence it reports the count of open sessions and calls the WIP **UNATTRIBUTED**, telling the reader to check `git log -1`/`git status` themselves. Degrades honestly: missing/unreadable provenance, a bogus sessions dir, or a failed import all yield "unattributed" rather than a guess. Verified by an adversarial REFUTE pass (uninvolved sessions cannot be blamed under any input shape incl. `[{}]`/`[None]`; malformed porcelain lines cannot raise; the warn-only invariant is intact).

**Test suite realigned 2026-07-24 (branch `fix/scg-attribution-test`, commit b599432).** The fix left `test-shared-checkout-guard.py` stale — its `test_other_active_session_named_in_message` still asserted the *pre-fix* contract (an open session must be named), so the suite failed at `~/.claude` HEAD. The guard was right, the test was not: the test file's last touch predates the guard rewrite. Replaced with three tests pinning the evidence-based contract (liveness alone -> UNATTRIBUTED and NOT named · intersecting touched-set -> named · non-intersecting provenance -> UNATTRIBUTED), the middle one mutation-verified so the naming branch isn't certified dead ([[feedback_fixture_shaped_tests_certify_dead_branches]]). **If you see this test fail again, check you're not on a pre-b599432 tree before re-diagnosing the guard.**

**What still applies from below:** if the guard now DOES name a session, that is evidence-backed and worth reconciling with — but it is still enrichment, not proof, and the verification habits below remain correct. What no longer applies: treating a *named* session as noise by default. An UNATTRIBUTED message is now the honest signal that nobody's provenance matches, which is itself informative (e.g. a script-generated or externally-made change, which the recorder never sees).

**Third instance (2026-07-21):** the guard named session `a039bb1f-a6df-44e4-9ba4-b2a8f160a2a9` as the source of ~30 uncommitted changes in `~/.claude` (including a genuine `event_log.md` content-loss incident — 6 entries missing vs. HEAD, restored separately). `get_session`/`list_sessions` didn't even return this ID (not `local_`-prefixed, so outside that tool's registry) — had to find it by grepping `session-env/` and `projects/<project>/*.jsonl` for the short ID directly. Once found: it's the `ora-aaos-expire-leases` scheduled-task run, transcript is a single turn (one `Bash` call to `AAOS\tools\expire-leases.py`), last activity 09:47 ET — ~2h48m stale at check time, not live. The script itself has zero references to `event_log.md` or the memory directory. Conclusively not the culprit for the file-content loss it was blamed for. Reinforces: verify via the session's actual transcript content (what tools did it call, on what files), not just recency — a session can be both "idle, not actually running" AND "provably never touched the flagged file," two independent reasons the attribution can be wrong.
