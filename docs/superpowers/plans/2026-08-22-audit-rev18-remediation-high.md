# Automation Audit Rev 18 Remediation — High Urgency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Inline execution, checkpoint after each task.

**Goal:** Close the two high-urgency findings from ORA Automation Audit Revision 18 (https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7) — event_log.md's 35-day-unrolled 1.42MB file with no size-based rollover trigger.

**Architecture:** Both tasks operate on `~/.claude/maintenance/` tooling and `~/.claude/projects/.../memory/event_log.md`. Task 1 runs the existing, tested `rollover-event-log.py` (concurrency-safe by design — atomic, mtime-guarded). Task 2 adds a size-threshold check to `append-event-log.py`'s existing backlog-warning path, mirroring its existing warning style rather than introducing new alerting infrastructure.

**Tech Stack:** Python 3, no new dependencies.

## Global Constraints

- `memory/` is a shared checkout, git-tracked, currently has uncommitted work from another session in flight (event_log.md +78 lines since last commit 2026-08-22 13:08:26; several unrelated memory reference files show as deleted by another session). Do not touch those unrelated deletions or the other session's uncommitted append content — commit only files this plan explicitly changes.
- `append-event-log.py`'s own docstring (lines 10-13): "only ONE session at a time should do structural edits (consolidation, rollover) to the log." This plan is that structural edit — do not run it if another rollover is detected in progress (check for a `.rollover-lock` or similar before running; if none exists, proceed).
- MEMORY.md itself is NOT touched by this plan (deferred — actively contended by a concurrent session's deletions right now; see Automation Audit Rev 18 finding R18-1, partially addressed already this session via a targeted compaction).
- Never use `git add -A` in this checkout — stage only the exact files this plan modifies.

---

### Task 1: Run the existing event_log.md rollover

**Files:**
- Modify (via script, not direct edit): `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\event_log.md`
- Create (via script): a new file under `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\_archive\` (exact name emitted by the script)
- Reference: `C:\Users\Owner\.claude\maintenance\rollover-event-log.py` (read-only, not modified this task)

**Interfaces:**
- Consumes: nothing from a prior task (first task in this plan)
- Produces: a rolled-over `event_log.md` (recent entries only) + one new archive file; later tasks in this plan don't depend on the output

- [ ] **Step 1: Verify current state before running**

Run: check the live byte size and date range are still what Revision 18 measured (findings decay — re-verify before acting, per standing guidance).

```bash
python -c "import pathlib; p=pathlib.Path(r'C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\event_log.md'); print(p.stat().st_size)"
```
Expected: a number close to 1,420,000 (± normal daily growth). If it has already rolled over (dramatically smaller, e.g. <500,000), STOP — someone else already did this; do not re-run.

- [ ] **Step 2: Run the rollover script in dry-run/check mode if it supports one**

```bash
python C:\Users\Owner\.claude\maintenance\rollover-event-log.py --help
```
Expected: usage text. Note whether a `--dry-run` or `--check` flag exists; if so, run it first and read the output before proceeding to Step 3.

- [ ] **Step 3: Run the rollover for real**

```bash
python C:\Users\Owner\.claude\maintenance\rollover-event-log.py
```
Expected: exit 0, output naming the new archive file path and the resulting event_log.md size (should land well under 400KB, consistent with the 3 historical archived chunks — 303,844B / 401,121B / 135,280B).

- [ ] **Step 4: Verify the other session's uncommitted append survived**

```bash
git -C C:\Users\Owner\.claude log -1 --format=%H -- "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md"
```
Then diff the current file's tail against what was uncommitted before Step 3 (the 78-line addition noted in Global Constraints) — confirm those entries are still present in the post-rollover event_log.md (rollover should only remove OLD entries, never recent ones). If the recent entries are missing, STOP and do not commit — investigate before proceeding.

- [ ] **Step 5: Commit only the rollover's own output**

```bash
git -C C:\Users\Owner\.claude add "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md" "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/_archive/<new-archive-filename>"
git -C C:\Users\Owner\.claude commit -m "chore(event_log): rollover 2026-08-22 - 35 days unrolled, 1.42MB (Automation Audit R18-2)"
```
Do NOT add the other unrelated modified/deleted files from `git status` — those belong to another session.

---

### Task 2: Add a size-threshold trigger to the backlog warning

**Files:**
- Modify: `C:\Users\Owner\.claude\maintenance\append-event-log.py`

**Interfaces:**
- Consumes: nothing from Task 1 (independent change, same file family)
- Produces: a `warn_if_uncommitted_backlog`-style size check other tooling doesn't currently depend on (this is additive)

- [ ] **Step 1: Locate the existing backlog-warning function**

```bash
grep -n "warn_if_uncommitted_backlog\|def warn" C:\Users\Owner\.claude\maintenance\append-event-log.py
```
Read the function in full via the Read tool before editing — match its existing warning style (print format, exit behavior) exactly rather than inventing a new one.

- [ ] **Step 2: Add a size check alongside the existing count check**

Add a check that reads `event_log.md`'s current byte size after append, and prints the same class of warning line the function already uses when it exceeds ~400,000 bytes (the historical archive-chunk ceiling) — reusing the existing warning's format string and severity, not a new mechanism. Read the actual function signature and warning text first; the added check must call `os.path.getsize()` on the resolved log path already used elsewhere in the file (do not hardcode a second path).

- [ ] **Step 3: Verify the check fires correctly**

```bash
python -c "
import sys
sys.path.insert(0, r'C:\Users\Owner\.claude\maintenance')
import append_event_log as m
# call the size-check function directly with a size above threshold and confirm it returns/prints the warning
"
```
Adjust to whatever the actual function/module structure turns out to be after Step 1's read — confirm the new check triggers on a size above 400,000 and stays silent below it (test both branches).

- [ ] **Step 4: Confirm no regression on the existing count-based warning**

Run the script's own test suite if one exists:
```bash
find C:\Users\Owner\.claude\maintenance -iname "*test*append*event*"
```
If a test file exists, run it and confirm it still passes. If none exists, do a manual smoke test: append a trivial entry via the normal `--entry-file` path and confirm exit 0 with no unrelated errors.

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\Owner\.claude add maintenance/append-event-log.py
git -C C:\Users\Owner\.claude commit -m "feat(append-event-log): add size-threshold warning alongside existing backlog-count check (Automation Audit R18-2)"
```
