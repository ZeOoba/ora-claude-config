# Plan: plan-gate override audit trail

**Size:** small (2 hook files + their tests). Worktree: `.claude/worktrees/eos-plan-gate-audit-trail` (branch `eos-plan-gate-audit-trail`, based off local HEAD `1d3cf27`).

## Problem
`eos-plan-gate.py` denies the 4th+ unplanned code edit and tells the session to `touch <override_path>` — a bare, 0-byte sentinel with no record of who approved skipping the plan, or why. Found via a live audit (2026-07-12): 74/187 sessions used a raw override with zero accompanying plan doc, and the file itself carries no metadata. Cross-referencing lane-telemetry showed override sessions still test/verify at a high rate (96%/74%), so this isn't a rigor crisis — but the audit trail gap is real and worth closing now that it's found.

## Fix
1. `eos-plan-gate.py`: change the denial message to ask for a one-line reason written into the override file, instead of a bare touch. No change to the core allow/deny logic (still presence-based, still fail-open) — this is a text-only, backward-compatible change. Existing override files (0 bytes) must keep working.
2. `eos-telemetry.py`: at SessionEnd, additionally check `<sessions_dir>/<session_id>/override` (new `EOS_SESSIONS_DIR` read, mirroring the constant already used in `eos-plan-gate.py`). If present, record `override_used`, `override_reason` (file content, or `null` if empty/old-style), `override_at` (file mtime as UTC ISO-8601). Wrapped in its own inner try/except so a corrupt override file can't drop the rest of the telemetry record — outer fail-open invariant unchanged.

## Tests (TDD — write first, watch fail, then implement)
- `test-eos-plan-gate.py`: new `test_denial_message_requests_reason` — 4th-edit denial reason text must mention the override path and prompt for a reason (not just "touch"). All 6 existing tests must still pass unchanged.
- `test-eos-telemetry.py`: extend `run_hook` to optionally set `EOS_SESSIONS_DIR`; add `test_override_used_surfaces_reason` (reason text round-trips), `test_override_used_no_reason_backward_compat` (0-byte file → `override_reason: null`, `override_used: true`), `test_no_override_file` (no file → all three fields false/null). All 5 existing tests must still pass unchanged.

## Out of scope
No change to who can create an override (still self-serviceable — that's an architecture question, not this fix), no change to `eos-plan-marker.py`, no enforcement/validation of reason content (stays fail-open).

## Land
Local test run (both files) green → local self-review against the diff → merge worktree branch back to `main` in `~/.claude` (fast-forward or merge commit, no force) → log to `memory/event_log.md` → remove worktree.
