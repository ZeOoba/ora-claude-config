# Audit Follow-Up Hook Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close five gaps found in the 2026-07-09 Claude Code setup audit: no local signal for CLAUDE.md doctrine violations until push, a mis-measured MEMORY.md index threshold, a missing declassification checklist, guesswork-based session coordination, and a shared-checkout guard that can't tell self from other or re-arm after the first warning.

**Architecture:** Extend the existing, already-tested `doctrine-integrity-probe.py` with a pure, reusable check function and a `--quick` CLI mode; add one new PreToolUse hook that simulates edits in memory and denies via the same mechanism `eos-plan-gate.py` already uses; add one new stdlib-only shared library that turns an existing (but currently unconsumed) session-activity mirror into a fail-open liveness signal; extend `shared-checkout-guard.py` to consume it. One documentation-only change (rules.md + CLAUDE.md pointer).

**Tech Stack:** Python 3 (stdlib only — `json`, `os`, `re`, `sys`, `subprocess`, `hashlib`, `importlib.util`, `tempfile` in tests). Windows. Claude Code hooks (`PreToolUse`/`PostToolUse` via `settings.json`). No new dependencies.

## Global Constraints

- Stdlib only, ASCII-only console output, Windows (`python`) — every existing hook in this repo follows this; do not deviate.
- Every hook's entire body is wrapped in `try/except: pass` then `sys.exit(0)` in `__main__` — "a bug must NEVER block a tool call" is the repo's standing safety invariant for every hook file. New code follows this exactly.
- Test runner convention in this repo is **not** pytest: each `test-*.py` file is a standalone script with top-level `test_*()` functions, each doing its own `assert` + `print("PASS ...")`, invoked from a bottom `if __name__ == "__main__":` block that calls them all in sequence and prints one final summary line. New test files match this exactly — do not introduce pytest.
- Hook test files live in `hooks/tests/test-<hookname>.py` (confirmed the real convention — `hooks/test-ora-autonomy-gate.py` at the flat level is a documented one-off "throwaway adversarial harness", not the pattern to copy). `maintenance/` scripts have their tests directly alongside them as `maintenance/test-<scriptname>.py` (no subdirectory).
- `~/.claude` is a live single-writer git repo with pre-existing uncommitted changes from the same audit this plan follows up on (verified unrelated/non-conflicting to every file this plan touches). Each task ends with its own commit of only the files that task changed — never a broad `git add -A`.
- CLAUDE.md is currently 1,779 words (`WORD_BUDGET_WARN=1700`, `WORD_BUDGET_FAIL=1850` in `maintenance/doctrine-integrity-probe.py`) — already in WARN range. Task 3 adds ~4 words (Guards: line) and Task 4 adds ~5 words (Invariant 3 pointer): both small, verified-safe additions (headroom to FAIL is 71 words) — no trim required, but each task that touches CLAUDE.md ends with a live word-count check as an explicit step, not an assumption.

---

### Task 1: `check_size_and_dates()` + `--quick` mode in doctrine-integrity-probe.py

**Files:**
- Modify: `C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`
- Test: `C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`

**Interfaces:**
- Produces: `check_size_and_dates(text: str) -> list[str]` (module-level function in `doctrine-integrity-probe.py`) — returns a list of violation message strings (empty = clean); covers only checks 5 (word budget) and 6's CLAUDE.md-dates sub-check (not the session-context tombstone-aging sub-check, which reads a different file). Also produces the `--quick` CLI flag: `python doctrine-integrity-probe.py --quick [path]` prints `QUICK-CHECK OK` and exits 0 if clean, or prints each violation prefixed `[MISSING]` and exits 1 otherwise — skipping every other check (1-4, 7-11) entirely.
- Consumes: nothing new (uses existing `WORD_BUDGET_FAIL`, `bare_dates()` already in the file).

- [ ] **Step 1: Write the failing tests**

Add to `C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`, inserting these four new functions right before `def main():`:

```python
def test_quick_mode_clean_passes():
    """--quick against the real (clean) CLAUDE.md -> exit 0."""
    r = run_probe(["--quick"])
    assert r.returncode == 0, (
        "expected exit 0 for --quick against real CLAUDE.md, got %d\n%s"
        % (r.returncode, r.stdout))
    assert "QUICK-CHECK OK" in r.stdout, "expected the quick-check OK line:\n%s" % r.stdout
    print("  PASS test_quick_mode_clean_passes")


def test_quick_mode_size_budget_fails():
    """--quick on an over-budget fixture -> exit 1, reports size budget only
    (no skills/leak/guard-liveness output -- proves --quick skips those checks)."""
    path = _write_fixture(_v21_base() + ("word " * 1900) + "\n")
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 1, (
            "expected exit 1 for over-budget --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "size budget exceeded" in r.stdout, (
            "expected size-budget violation:\n%s" % r.stdout)
        assert "Skills referenced" not in r.stdout, (
            "--quick must skip the skills scan:\n%s" % r.stdout)
        assert "Guard liveness" not in r.stdout, (
            "--quick must skip guard-liveness:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_size_budget_fails (fails, and skips slow checks)")


def test_quick_mode_bare_date_fails():
    """--quick on a fixture with a bare date -> exit 1, reports it; slug dates exempt."""
    path = _write_fixture(_v21_base() + "- ratified 2026-06-10, do not unify\n")
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 1, (
            "expected exit 1 for bare-date --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "bare date 2026-06-10" in r.stdout, (
            "expected the specific bare-date violation:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_bare_date_fails")


def test_quick_mode_clean_fixture_passes():
    """--quick on a clean v2.1 fixture -> exit 0."""
    path = _write_fixture(_v21_base())
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 0, (
            "expected exit 0 for clean --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_clean_fixture_passes")
```

Also add the four calls into `main()`'s call sequence, right after `test_guard_liveness_fixture_orphan_and_override_excluded()` and before `print("ALL DOCTRINE-PROBE TESTS PASS")`:

```python
    test_quick_mode_clean_passes()
    test_quick_mode_size_budget_fails()
    test_quick_mode_bare_date_fails()
    test_quick_mode_clean_fixture_passes()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`
Expected: the four new tests fail (or the whole run errors) because `--quick` is not yet a recognized option — `parse_args` currently exits 1 with `[MISSING] unknown option: --quick`.

- [ ] **Step 3: Implement `check_size_and_dates()` and `--quick`**

In `C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`, insert this new function immediately after the existing `bare_dates()` function (which ends right before `def word_stream(text):`):

```python
def check_size_and_dates(text):
    """CLAUDE.md hard-fail violations only (checks 5+6's MISSING-tier findings):
    size budget and bare ISO dates. Pure function -- no I/O, no printing, no
    side effects on the module-level 'missing'/WARN_COUNT state main() uses.
    Returns a list of violation message strings (empty = clean).

    Deliberately NOT reused by main()'s own checks 5/6 (which keep their
    existing inline print/warn/missing.append flow untouched) -- main()'s path
    is exercised by test_size_budget_fail/test_dated_annotation_fails and must
    stay byte-for-byte unchanged; this is intentionally the small amount of
    accepted duplication with bare_dates()/WORD_BUDGET_FAIL that buys that
    guarantee, not an oversight.

    Does NOT include check 6's session-context tombstone-aging sub-check
    (WARN-only, reads session-context.md, not CLAUDE.md -- out of scope for a
    per-edit CLAUDE.md check).
    """
    violations = []
    words = len(text.split())
    if words > WORD_BUDGET_FAIL:
        violations.append(
            "size budget exceeded: %d > %d words (one-in-one-out gate breached -- "
            "trim an equivalent amount elsewhere in this same change; move a rule "
            "down a layer)" % (words, WORD_BUDGET_FAIL))
    for ln_no, d in bare_dates(text):
        violations.append(
            "bare date %s at line %d (dated history belongs in event_log.md)"
            % (d, ln_no))
    return violations
```

In `parse_args(argv)`, change:
```python
        elif a.startswith("--terms="):
            overrides["terms"] = Path(a.split("=", 1)[1])
        elif a.startswith("--"):
            # A typo'd flag must not silently become the CLAUDE.md path (which
            # would also disable live-mode scanning). Fail loud.
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms=)" % ascii_safe(a))
            sys.exit(1)
```
to:
```python
        elif a.startswith("--terms="):
            overrides["terms"] = Path(a.split("=", 1)[1])
        elif a == "--quick":
            overrides["quick"] = True
        elif a.startswith("--"):
            # A typo'd flag must not silently become the CLAUDE.md path (which
            # would also disable live-mode scanning). Fail loud.
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms= --quick)" % ascii_safe(a))
            sys.exit(1)
```

In `main()`, change:
```python
    try:
        text = claude_md.read_text(encoding="utf-8")
    except Exception as e:
        print("[MISSING] cannot read CLAUDE.md (%s): %s" % (claude_md, e))
        sys.exit(1)

    section = extract_section(text)
```
to:
```python
    try:
        text = claude_md.read_text(encoding="utf-8")
    except Exception as e:
        print("[MISSING] cannot read CLAUDE.md (%s): %s" % (claude_md, e))
        sys.exit(1)

    if overrides.get("quick"):
        violations = check_size_and_dates(text)
        if violations:
            print("DOCTRINE QUICK-CHECK -- source: %s" % claude_md)
            for v in violations:
                print("  [MISSING] " + v)
            print("QUICK-CHECK DRIFT: %d violation(s)" % len(violations))
            sys.exit(1)
        print("QUICK-CHECK OK -- %s within word budget, no bare dates" % claude_md)
        sys.exit(0)

    section = extract_section(text)
```

Also update the module docstring's "Optional argv[1] = path..." paragraph (near the top of the file) by appending one sentence: `" --quick runs only checks 5+6 (size budget, bare dates) against the given/default path and skips everything else -- fast enough to run on every CLAUDE.md edit."`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`
Expected: `ALL DOCTRINE-PROBE TESTS PASS` (all pre-existing tests still pass — proves the full/live-mode path is unchanged — plus the four new `--quick` tests).

- [ ] **Step 5: Commit**

```bash
git add maintenance/doctrine-integrity-probe.py maintenance/test-doctrine-integrity-probe.py
git commit -m "feat(doctrine-probe): add check_size_and_dates() + --quick mode"
```

---

### Task 2: MEMORY.md index-entry check measures only the hook text

**Files:**
- Modify: `C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`
- Test: `C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`

**Interfaces:**
- Consumes: nothing from Task 1 (independent fix, same file — run after Task 1 only to avoid a merge conflict on one file, not a logical dependency).
- Produces: `MEMORY_INDEX_HOOK_MAXLEN` (renamed from `MEMORY_INDEX_LINE_MAXLEN`, same default 150), and a new `--memory-index=PATH` CLI override (mirrors the existing `--session-context=`/`--rules=`/`--terms=` pattern) so check 9 becomes testable against a fixture instead of only the live `MEMORY.md`.

- [ ] **Step 1: Write the failing tests**

Add to `C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`, right before `def main():` (after Task 1's four new tests):

```python
def test_memory_index_long_title_short_hook_no_warn():
    """Regression fix: a long title/filename must NOT trip the check when the
    hook (description after the link) is short -- the bug this fix corrects."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    long_title = "A" * 140
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [%s](some-very-long-filename-that-eats-the-budget.md) -- ok\n" % long_title)
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, (
            "expected exit 0 (WARN-only check), got %d\n%s" % (r.returncode, r.stdout))
        assert "index entry at line 1" not in r.stdout, (
            "a long title with a short hook must NOT warn (regression):\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_long_title_short_hook_no_warn")


def test_memory_index_long_hook_warns():
    """A genuinely long HOOK description (past the link) still warns."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    long_hook = "word " * 40  # well over 150 chars
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [Short Title](file.md) -- %s\n" % long_hook)
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, "index check is WARN-only, got %d\n%s" % (r.returncode, r.stdout)
        assert "index entry at line 1" in r.stdout, (
            "a genuinely long hook must still warn:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_long_hook_warns")


def test_memory_index_hookless_entry_no_warn():
    """An entry with no ' -- hook' at all (just a bare link) must not warn or crash."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [Title](file.md)\n")
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, "hookless entry must not fail, got %d\n%s" % (r.returncode, r.stdout)
        assert "index entry at line 1" not in r.stdout, (
            "a hookless entry must not warn:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_hookless_entry_no_warn")
```

Add the three calls into `main()`'s call sequence, right after Task 1's four `test_quick_mode_*()` calls:

```python
    test_memory_index_long_title_short_hook_no_warn()
    test_memory_index_long_hook_warns()
    test_memory_index_hookless_entry_no_warn()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`
Expected: fails — `--memory-index=` is not yet a recognized option (`[MISSING] unknown option`).

- [ ] **Step 3: Implement the fix**

In `C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`, rename the constant (near the other check-9 constants):
```python
MEMORY_INDEX_LINE_MAXLEN = 150
```
to:
```python
MEMORY_INDEX_HOOK_MAXLEN = 150
```

In `parse_args(argv)`, add a new branch (after the `--quick` branch added in Task 1):
```python
        elif a == "--quick":
            overrides["quick"] = True
        elif a.startswith("--memory-index="):
            overrides["memory_index"] = Path(a.split("=", 1)[1])
        elif a.startswith("--"):
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms= --quick --memory-index=)" % ascii_safe(a))
            sys.exit(1)
```

Replace check 9's body:
```python
    mem_text, mem_err = read_optional(MEMORY_INDEX_MD)
    if mem_text is None:
        warn("MEMORY.md index-entry check skipped: %s" % ascii_safe(mem_err))
    else:
        over = []
        for ln_no, ln in enumerate(mem_text.splitlines(), 1):
            if MEMORY_INDEX_ENTRY_RE.match(ln):
                length = len(ln.strip())
                if length > MEMORY_INDEX_LINE_MAXLEN:
                    over.append((ln_no, length))
        print("MEMORY.md index entries over %d chars: %d "
              "(memory-policy sec 3: entries are 'a one-line description')"
              % (MEMORY_INDEX_LINE_MAXLEN, len(over)))
        for ln_no, length in over:
            warn("MEMORY.md index entry at line %d is %d chars (> %d) -- collapse to "
                 "a one-line pointer; detail belongs in the linked file"
                 % (ln_no, length, MEMORY_INDEX_LINE_MAXLEN))
```
with:
```python
    mem_path = overrides.get("memory_index", MEMORY_INDEX_MD)
    mem_text, mem_err = read_optional(mem_path)
    if mem_text is None:
        warn("MEMORY.md index-entry check skipped: %s" % ascii_safe(mem_err))
    else:
        over = []
        for ln_no, ln in enumerate(mem_text.splitlines(), 1):
            m = MEMORY_INDEX_ENTRY_RE.match(ln)
            if m:
                hook_text = ln[m.end():].strip()
                length = len(hook_text)
                if length > MEMORY_INDEX_HOOK_MAXLEN:
                    over.append((ln_no, length))
        print("MEMORY.md index entries with a hook description over %d chars: %d "
              "(memory-policy sec 3: entries are 'a one-line description')"
              % (MEMORY_INDEX_HOOK_MAXLEN, len(over)))
        for ln_no, length in over:
            warn("MEMORY.md index entry at line %d has a %d-char hook description "
                 "(> %d) -- collapse to a one-line pointer; detail belongs in the "
                 "linked file" % (ln_no, length, MEMORY_INDEX_HOOK_MAXLEN))
```

Also update check 9's docstring comment block above `MEMORY_INDEX_MD = ...` to note the fix: append a sentence noting the measurement is now the hook-text-only span, not the whole bulleted line, and that the constant was renamed accordingly.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py`
Expected: `ALL DOCTRINE-PROBE TESTS PASS`.

- [ ] **Step 5: Commit**

```bash
git add maintenance/doctrine-integrity-probe.py maintenance/test-doctrine-integrity-probe.py
git commit -m "fix(doctrine-probe): MEMORY.md index check measures hook text only, not the whole line"
```

---

### Task 3: `hooks/eos-claude-md-guard.py` — PreToolUse simulate-and-deny hook

**Files:**
- Create: `C:/Users/Owner/.claude/hooks/eos-claude-md-guard.py`
- Test: `C:/Users/Owner/.claude/hooks/tests/test-eos-claude-md-guard.py`
- Modify: `C:/Users/Owner/.claude/settings.json`
- Modify: `C:/Users/Owner/.claude/CLAUDE.md` (Guards: line, Engineering OS section)

**Interfaces:**
- Consumes: `check_size_and_dates(text) -> list[str]` from `maintenance/doctrine-integrity-probe.py` (Task 1), loaded via `importlib.util` (the module's hyphenated filename makes a normal `import` impossible).
- Produces: nothing further consumed by later tasks (Tasks 5/6 are independent of this one).

- [ ] **Step 1: Write the failing tests**

Create `C:/Users/Owner/.claude/hooks/tests/test-eos-claude-md-guard.py`:

```python
"""Tests for eos-claude-md-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-eos-claude-md-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp CLAUDE.md fixtures).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-claude-md-guard.py")

BASE = "## Engineering OS\nsome doctrine text\n"


def run_hook(payload, claude_md_path):
    env = dict(os.environ)
    env["EOS_CLAUDE_MD"] = claude_md_path
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_claude_md(content):
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def test_non_claude_md_path_silent():
    path = make_claude_md(BASE)
    try:
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": "C:/other/file.md", "content": "x"}},
            path,
        )
        assert rc == 0 and out.strip() == "", "non-CLAUDE.md path must be silent, got %r/%r" % (rc, out)
    finally:
        os.remove(path)
    print("PASS test_non_claude_md_path_silent")


def test_write_clean_allows():
    path = make_claude_md(BASE)
    try:
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": BASE + "more text\n"}},
            path,
        )
        assert rc == 0, "clean Write expected exit 0, got %s (%s)" % (rc, err)
        assert "deny" not in out, "clean Write must not deny, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_clean_allows")


def test_write_over_budget_denies():
    path = make_claude_md(BASE)
    try:
        over = BASE + ("word " * 1900)
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": over}},
            path,
        )
        assert rc == 0, "hook itself always exits 0, got %s" % rc
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "over-budget Write must deny, got %r" % out)
        assert "size budget exceeded" in out, "expected size-budget reason text, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_over_budget_denies")


def test_write_bare_date_denies():
    path = make_claude_md(BASE)
    try:
        dated = BASE + "- ratified 2026-06-10, do not unify\n"
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": dated}},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "bare-date Write must deny, got %r" % out)
        assert "bare date 2026-06-10" in out, "expected bare-date reason text, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_bare_date_denies")


def test_edit_clean_result_allows():
    path = make_claude_md(BASE + "old phrase here\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "old phrase here", "new_string": "new phrase here"}},
            path,
        )
        assert rc == 0 and "deny" not in out, "clean Edit must not deny, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_edit_clean_result_allows")


def test_edit_producing_bare_date_denies():
    path = make_claude_md(BASE + "old phrase here\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "old phrase here",
                "new_string": "ratified 2026-06-10, do not unify"}},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "Edit producing a bare date must deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_edit_producing_bare_date_denies")


def test_edit_ambiguous_match_fails_open():
    path = make_claude_md(BASE + "dup\ndup\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "dup", "new_string": "2026-06-10"}},
            path,
        )
        assert rc == 0 and "deny" not in out, (
            "ambiguous (2x) old_string match must fail open, not deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_edit_ambiguous_match_fails_open")


def test_multiedit_final_result_denies():
    path = make_claude_md(BASE + "alpha\nbeta\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "MultiEdit", "tool_input": {
                "file_path": path,
                "edits": [
                    {"old_string": "alpha", "new_string": "2026-06-10"},
                    {"old_string": "beta", "new_string": "unchanged"},
                ],
            }},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "MultiEdit producing a bare date must deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_multiedit_final_result_denies")


def test_malformed_stdin_fails_open():
    path = make_claude_md(BASE)
    try:
        env = dict(os.environ)
        env["EOS_CLAUDE_MD"] = path
        proc = subprocess.run([sys.executable, HOOK], input="not json",
                              capture_output=True, text=True, env=env)
        assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
        assert "deny" not in proc.stdout, "fail-open must not deny, got %r" % proc.stdout
    finally:
        os.remove(path)
    print("PASS test_malformed_stdin_fails_open")


def test_missing_target_fails_open():
    rc, out, err = run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": "C:/does/not/exist_xyz/CLAUDE.md",
                                               "content": "word " * 1900}},
        "C:/does/not/exist_xyz/CLAUDE.md",
    )
    assert rc == 0 and "deny" not in out, "missing target must fail open, got %r" % out
    print("PASS test_missing_target_fails_open")


if __name__ == "__main__":
    test_non_claude_md_path_silent()
    test_write_clean_allows()
    test_write_over_budget_denies()
    test_write_bare_date_denies()
    test_edit_clean_result_allows()
    test_edit_producing_bare_date_denies()
    test_edit_ambiguous_match_fails_open()
    test_multiedit_final_result_denies()
    test_malformed_stdin_fails_open()
    test_missing_target_fails_open()
    print("ALL EOS-CLAUDE-MD-GUARD TESTS PASS")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-eos-claude-md-guard.py`
Expected: fails with `FileNotFoundError` / non-zero — `eos-claude-md-guard.py` does not exist yet.

- [ ] **Step 3: Implement the hook**

Create `C:/Users/Owner/.claude/hooks/eos-claude-md-guard.py`:

```python
"""Engineering OS CLAUDE.md edit-time doctrine guard -- PreToolUse hook for
Edit|Write|MultiEdit.

Simulates the post-edit content of CLAUDE.md (without writing it) and runs
doctrine-integrity-probe.py's check_size_and_dates() against the simulated
text. On a hard-fail (size budget or bare date), DENIES the edit via the
same permissionDecision:deny mechanism eos-plan-gate.py already uses -- the
violating state never lands on disk. This surfaces what was previously only
caught at `git push` time (git-prepush-doctrine-gate.py), hours later.

There is no local precedent for a blocking PostToolUse hook in this repo
(every existing PostToolUse hook is fail-open by design) -- this is
deliberately PreToolUse, reusing eos-plan-gate.py's proven deny mechanism
instead of inventing a new one.

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error --
bad stdin, missing field, unreadable file, an edit shape we can't simulate --
it prints nothing and exits 0 (ALLOW). A bug must NEVER block a tool call.

Stdlib only. ASCII-only. Windows (`python`).
"""

import importlib.util
import json
import os
import sys

MAINTENANCE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maintenance"))
DEFAULT_CLAUDE_MD = "C:/Users/Owner/.claude/CLAUDE.md"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def is_claude_md(file_path):
    target = os.environ.get("EOS_CLAUDE_MD") or DEFAULT_CLAUDE_MD
    return _norm(file_path) == _norm(target)


def simulate_edit(tool_name, tool_input, current_text):
    """Return the post-edit text WITHOUT writing anything, or None if the
    tool/input shape can't be simulated (caller must then fail open)."""
    if tool_name == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None

    if tool_name == "Edit":
        old = tool_input.get("old_string")
        new = tool_input.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str) or old == "":
            return None
        if tool_input.get("replace_all"):
            return current_text.replace(old, new)
        if current_text.count(old) != 1:
            return None  # ambiguous/no match -- let the real Edit tool handle its own error
        return current_text.replace(old, new, 1)

    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return None
        text = current_text
        for e in edits:
            if not isinstance(e, dict):
                return None
            old = e.get("old_string")
            new = e.get("new_string")
            if not isinstance(old, str) or not isinstance(new, str) or old == "":
                return None
            if e.get("replace_all"):
                text = text.replace(old, new)
            else:
                if text.count(old) != 1:
                    return None
                text = text.replace(old, new, 1)
        return text

    return None


def _load_probe():
    probe_path = os.path.join(MAINTENANCE_DIR, "doctrine-integrity-probe.py")
    spec = importlib.util.spec_from_file_location("doctrine_integrity_probe", probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    if not is_claude_md(file_path):
        return

    target = os.environ.get("EOS_CLAUDE_MD") or DEFAULT_CLAUDE_MD
    try:
        with open(target, "r", encoding="utf-8") as fh:
            current_text = fh.read()
    except Exception:
        return  # can't read current content -- fail open

    simulated = simulate_edit(tool_name, tool_input, current_text)
    if simulated is None:
        return  # couldn't simulate this shape -- fail open

    probe = _load_probe()
    violations = probe.check_size_and_dates(simulated)
    if not violations:
        return

    reason = (
        "Engineering OS doctrine check: this edit would leave CLAUDE.md in "
        "violation --\n- " + "\n- ".join(violations) +
        "\nFix before this edit lands (checks 5/6 of doctrine-integrity-probe.py; "
        "same hard-fail the pre-push gate enforces, surfaced now instead of at push)."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a bug must never block a tool call
    sys.exit(0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-eos-claude-md-guard.py`
Expected: `ALL EOS-CLAUDE-MD-GUARD TESTS PASS`.

- [ ] **Step 5: Wire into settings.json**

In `C:/Users/Owner/.claude/settings.json`, in the `"PreToolUse"` array, add a new entry immediately after the `shared-checkout-guard.py` entry (which currently reads: matcher `"Edit|Write|MultiEdit"`, command pointing at `hooks/shared-checkout-guard.py`):

```json
    {
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [
        {
          "type": "command",
          "command": "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \"C:/Users/Owner/.claude/hooks/eos-claude-md-guard.py\""
        }
      ]
    },
```
(Insert as a new array element right before the `eos-evidence-gate.py` entry that closes the `PreToolUse` array.)

Verify the file is still valid JSON:
Run: `python -c "import json; json.load(open('C:/Users/Owner/.claude/settings.json', encoding='utf-8'))"`
Expected: no output, exit 0 (parses cleanly).

- [ ] **Step 6: Register the guard in CLAUDE.md's Guards: line**

In `C:/Users/Owner/.claude/CLAUDE.md`, in the Engineering OS section's "Calibrate:" bullet, change:
```
Guards: `doctrine-integrity-probe.py` · `governor-drift-probe.py` · `git-prepush-doctrine-gate.py` · `eos-telemetry` · `eos-plan-gate` (4+ unplanned edits; override `touch hooks/sessions/<id>/override`); all fail open.
```
to:
```
Guards: `doctrine-integrity-probe.py` · `governor-drift-probe.py` · `git-prepush-doctrine-gate.py` · `eos-telemetry` · `eos-plan-gate` (4+ unplanned edits; override `touch hooks/sessions/<id>/override`) · `eos-claude-md-guard` (word-budget/bare-date, PreToolUse deny); all fail open.
```

Verify word budget and guard liveness together:
Run: `python C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`
Expected: exit 0, `OK -- all referenced commands, local files and skills resolve.`, and a line `[OK]      eos-claude-md-guard -> live invocation point found` under "Guard liveness". Also confirm the printed word count is still under 1850 (`CLAUDE.md size: N words (warn > 1700, fail > 1850)`).

- [ ] **Step 7: Commit**

```bash
git add hooks/eos-claude-md-guard.py hooks/tests/test-eos-claude-md-guard.py settings.json CLAUDE.md
git commit -m "feat(hooks): add eos-claude-md-guard.py, PreToolUse doctrine check for CLAUDE.md edits"
```

---

### Task 4: Declassification / reclassification file checklist (doc-only)

**Files:**
- Modify: `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/rules.md`
- Modify: `C:/Users/Owner/.claude/CLAUDE.md` (Hard Invariant 3)

**Interfaces:** none (documentation only, no code produced or consumed).

- [ ] **Step 1: Add the checklist to rules.md §7b**

In `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/rules.md`, insert a new section immediately after §7a's last bullet (the one starting "**Owner-ratified repo exception (2026-06-14):**") and before the `## 7. Website / CSP (oxfordra.net)` header:

```markdown

## 7b. Declassification / reclassification file checklist (2026-07-09)

No checklist existed for this before 2026-07-09; the E. Fulton declassification
touched 4 files ad hoc and missed `session-context.md` (caught and fixed
out-of-band — see `event_log.md`). When a confidential deal's status changes
(declassified, or re-classified confidential), update ALL of:

- `hooks/confidential-terms.json` — flip the deal's `active` flag.
- `session-context.md` — update the roster line (Hard Invariant 3's sanctioned
  untracked roster home).
- `memory/event_log.md` — append the dated decision via
  `python ~/.claude/maintenance/append-event-log.py` (§9: never Edit-anchor the
  log header — one structural writer at a time).
- `memory/projects.md` — update the deal's entry/status.
- `memory/MEMORY.md` — only if the deal's index-entry description text changes.
- `memory/firm.md` — only if firm-level facts changed (e.g. portfolio
  composition).

Doc-only enforcement (decided 2026-07-09): declassification is rare enough
that a lightweight automated check isn't warranted yet — revisit if a future
declassification misses this checklist despite the Hard Invariant 3 pointer.
```

- [ ] **Step 2: Add the pointer to Hard Invariant 3**

In `C:/Users/Owner/.claude/CLAUDE.md`, change Hard Invariant 3:
```
3. Active confidential deals (roster: session context / `confidential-terms.json`; hook-enforced, fail-closed on Code) never appear on any external surface until closing. The deal roster lives ONLY in those two places — never name an active confidential deal in this file (it is git-tracked to an off-machine remote). If confidential-deal state is unavailable on the current surface, verify before naming any deal externally — if unverifiable, ask.
```
to:
```
3. Active confidential deals (roster: session context / `confidential-terms.json`; hook-enforced, fail-closed on Code) never appear on any external surface until closing. The deal roster lives ONLY in those two places — never name an active confidential deal in this file (it is git-tracked to an off-machine remote). If confidential-deal state is unavailable on the current surface, verify before naming any deal externally — if unverifiable, ask. Declassification file checklist: `rules.md` §7b.
```

- [ ] **Step 3: Verify**

Run: `python C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py`
Expected: exit 0, `OK -- all referenced commands, local files and skills resolve.` Confirm the printed `CLAUDE.md size: N words` line is still under 1850 (running total after Task 3 + Task 4's small additions).

- [ ] **Step 4: Commit**

```bash
git add "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/rules.md" CLAUDE.md
git commit -m "docs: add declassification/reclassification file checklist (rules.md 7b)"
```

---

### Task 5: `hooks/lib/session_liveness.py` + widen fleet-session-hook.py's PostToolUse matcher

**Files:**
- Create: `C:/Users/Owner/.claude/hooks/lib/session_liveness.py`
- Test: `C:/Users/Owner/.claude/hooks/tests/test-session-liveness.py`
- Modify: `C:/Users/Owner/.claude/settings.json`

**Interfaces:**
- Produces: `other_active_sessions(own_sid: str, state_path: str|None = None) -> list[dict]`, each dict `{"sid": str, "status": str, "cwd": str, "lastAt": str}`. Consumed by Task 6.
- No modification to `hooks/fleet-session-hook.py` itself is needed — its `PostToolUse` branch already sets `status` generically for any tool name; only the settings.json matcher needs widening (verified: `fleet-session-hook.py`'s handling of an unrecognized `tool_name` is already a safe no-op fall-through).

- [ ] **Step 1: Write the failing tests**

Create `C:/Users/Owner/.claude/hooks/tests/test-session-liveness.py`:

```python
"""Tests for hooks/lib/session_liveness.py.

Run: python test-session-liveness.py
Stdlib only. ASCII-only. Self-contained (creates its own temp state files).
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
LIB = os.path.join(HERE, "lib")
sys.path.insert(0, LIB)
from session_liveness import other_active_sessions  # noqa: E402


def write_state(d):
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return path


def test_missing_file_fails_open():
    result = other_active_sessions("own", state_path="C:/does/not/exist_xyz.json")
    assert result == [], "missing file must return [], got %r" % result
    print("PASS test_missing_file_fails_open")


def test_malformed_json_fails_open():
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("not json")
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "malformed JSON must return [], got %r" % result
    finally:
        os.remove(path)
    print("PASS test_malformed_json_fails_open")


def test_wrong_shape_fails_open():
    path = write_state({"sessions": "not a dict"})
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "wrong-shape sessions must return [], got %r" % result
    finally:
        os.remove(path)
    print("PASS test_wrong_shape_fails_open")


def test_excludes_own_sid():
    path = write_state({"sessions": {"own": {"status": "working", "cwd": "C:/x", "lastAt": "t"}}})
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "own sid must be excluded, got %r" % result
    finally:
        os.remove(path)
    print("PASS test_excludes_own_sid")


def test_returns_other_sessions_with_fields():
    path = write_state({
        "sessions": {
            "own": {"status": "working", "cwd": "C:/mine", "lastAt": "t1"},
            "other1": {"status": "idle", "cwd": "C:/theirs", "lastAt": "t2"},
        }
    })
    try:
        result = other_active_sessions("own", state_path=path)
        assert len(result) == 1, "expected exactly 1 other session, got %r" % result
        assert result[0] == {"sid": "other1", "status": "idle", "cwd": "C:/theirs", "lastAt": "t2"}, (
            "unexpected fields: %r" % result[0])
    finally:
        os.remove(path)
    print("PASS test_returns_other_sessions_with_fields")


def test_malformed_session_entry_skipped():
    path = write_state({"sessions": {"own": {}, "bad": "not a dict", "other1": {"status": "working"}}})
    try:
        result = other_active_sessions("own", state_path=path)
        sids = [r["sid"] for r in result]
        assert sids == ["other1"], "malformed entry must be skipped, got %r" % result
    finally:
        os.remove(path)
    print("PASS test_malformed_session_entry_skipped")


if __name__ == "__main__":
    test_missing_file_fails_open()
    test_malformed_json_fails_open()
    test_wrong_shape_fails_open()
    test_excludes_own_sid()
    test_returns_other_sessions_with_fields()
    test_malformed_session_entry_skipped()
    print("ALL SESSION-LIVENESS TESTS PASS")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-session-liveness.py`
Expected: `ModuleNotFoundError: No module named 'session_liveness'` — `hooks/lib/` doesn't exist yet.

- [ ] **Step 3: Implement `session_liveness.py`**

Create the directory and file `C:/Users/Owner/.claude/hooks/lib/session_liveness.py`:

```python
"""Session liveness reader for coordination guards.

Reads the fleet-session-hook.py mirror (obsidian-fleet-mirror/session-state.json)
as a fail-open ENRICHMENT signal: a session's PRESENCE in the dict means it is
still open (fleet-session-hook.py pops a session immediately on a clean
SessionEnd; a crashed session without SessionEnd is pruned after
SESSION_PRUNE_H=6 hours by fleet-session-hook.py's own next invocation).

ENRICHMENT ONLY, never a hard gate: fleet-session-hook.py is itself
fail-open/best-effort (it may silently not run, and its save_state()
load-mutate-replace cycle is unlocked -- a real, accepted, bounded race under
concurrent writers, which is exactly the two-sessions-open scenario this
module exists to detect). A caller MUST treat a read failure, or a stale/
empty result, the same as "no information" -- never as "definitely no other
session" or "definitely another session" -- and degrade to whatever
git-status-only behavior existed before consuming this module.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os

DEFAULT_STATE = "C:/Users/Owner/.claude/obsidian-fleet-mirror/session-state.json"


def other_active_sessions(own_sid, state_path=None):
    """Sessions present in session-state.json other than own_sid.

    Honors the ORA_FLEET_STATE env var override (same variable
    fleet-session-hook.py itself reads) when state_path is not given
    explicitly, so a non-default configuration can't silently desync
    writer and reader.

    Fail-open: any read/parse error (missing file, malformed JSON, wrong
    shape) returns [] -- never raises.

    Each item: {"sid": str, "status": str, "cwd": str, "lastAt": str}.
    """
    path = state_path or os.environ.get("ORA_FLEET_STATE") or DEFAULT_STATE
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, dict):
        return []
    out = []
    for sid, s in sessions.items():
        if sid == own_sid or not isinstance(s, dict):
            continue
        out.append({
            "sid": sid,
            "status": s.get("status", "?"),
            "cwd": s.get("cwd", ""),
            "lastAt": s.get("lastAt", ""),
        })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-session-liveness.py`
Expected: `ALL SESSION-LIVENESS TESTS PASS`.

- [ ] **Step 5: Widen fleet-session-hook.py's PostToolUse matcher**

In `C:/Users/Owner/.claude/settings.json`, in the `"PostToolUse"` array, find the entry with `"matcher": "Bash|Task|TaskCreate|TaskUpdate"` (the `fleet-session-hook.py` entry, marked `"async": true`) and change its matcher to:
```json
      "matcher": "Bash|Task|TaskCreate|TaskUpdate|Edit|Write|MultiEdit",
```

Verify the file is still valid JSON:
Run: `python -c "import json; json.load(open('C:/Users/Owner/.claude/settings.json', encoding='utf-8'))"`
Expected: no output, exit 0.

- [ ] **Step 6: Commit**

```bash
git add hooks/lib/session_liveness.py hooks/tests/test-session-liveness.py settings.json
git commit -m "feat(hooks): add session_liveness.py, widen fleet-session-hook.py PostToolUse matcher to Edit/Write/MultiEdit"
```

---

### Task 6: `shared-checkout-guard.py` — session-liveness enrichment + repo-wide re-arm

**Files:**
- Modify: `C:/Users/Owner/.claude/hooks/shared-checkout-guard.py`
- Modify: `C:/Users/Owner/.claude/hooks/tests/test-shared-checkout-guard.py`

**Interfaces:**
- Consumes: `other_active_sessions(own_sid, state_path=None)` from `hooks/lib/session_liveness.py` (Task 5).

- [ ] **Step 1: Write the failing tests**

In `C:/Users/Owner/.claude/hooks/tests/test-shared-checkout-guard.py`, replace the existing `run_hook` function:
```python
def run_hook(stdin_text, repos, sessions_dir):
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = os.pathsep.join(repos)
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr
```
with (adds an optional 4th parameter; every existing call site that omits it is unaffected):
```python
def run_hook(stdin_text, repos, sessions_dir, extra_env=None):
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = os.pathsep.join(repos)
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_dir
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr
```

Then add these four new test functions right before the `if __name__ == "__main__":` block:

```python
def test_rearm_on_dirty_set_change():
    """A NEW dirty-state fingerprint after the first warning re-arms it --
    the fix for 'warns only once per session even if new external changes land'."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    _, out1, _ = run_hook(payload("s6", fp), [repo], sess)
    assert "systemMessage" in out1, "first call must warn, got %r" % out1
    with open(os.path.join(repo, "second-foreign-file.txt"), "w") as fh:
        fh.write("more WIP")
    _, out2, _ = run_hook(payload("s6", fp), [repo], sess)
    assert "systemMessage" in out2, (
        "changed dirty set must re-arm the warning, got %r" % out2)
    print("PASS test_rearm_on_dirty_set_change")


def test_same_dirty_set_stays_silent_after_warning():
    """Re-confirms the ORIGINAL dedupe intent survives the re-arm fix: an
    UNCHANGED dirty set must not re-warn on every single edit."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    _, out1, _ = run_hook(payload("s7", fp), [repo], sess)
    _, out2, _ = run_hook(payload("s7", fp), [repo], sess)
    assert "systemMessage" in out1, "first call must warn, got %r" % out1
    assert "systemMessage" not in out2, (
        "unchanged dirty set must stay silent on the second call, got %r" % out2)
    print("PASS test_same_dirty_set_stays_silent_after_warning")


def test_other_active_session_named_in_message():
    """When session_liveness reports another open session, the warning names it."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    fd, state_path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"sessions": {"other-session-99": {"status": "working", "cwd": repo, "lastAt": "t"}}}, fh)
    try:
        rc, out, err = run_hook(payload("s8", fp), [repo], sess, extra_env={"ORA_FLEET_STATE": state_path})
        assert "other-se" in out, (
            "expected the other session's (truncated) id in the warning, got %r" % out)
    finally:
        os.remove(state_path)
    print("PASS test_other_active_session_named_in_message")


def test_no_other_session_generic_message():
    """When session_liveness finds nothing (empty/missing state), the message
    stays the original generic form -- proves the enrichment degrades safely."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s9", fp), [repo], sess,
                            extra_env={"ORA_FLEET_STATE": "C:/does/not/exist_xyz.json"})
    assert "systemMessage" in out, "must still warn, got %r" % out
    assert "is open right now" not in out, (
        "no other session known -> must not fabricate a collision note, got %r" % out)
    print("PASS test_no_other_session_generic_message")
```

Add the calls to the `if __name__ == "__main__":` block, after `test_malformed_stdin_fails_open()`:
```python
    test_rearm_on_dirty_set_change()
    test_same_dirty_set_stays_silent_after_warning()
    test_other_active_session_named_in_message()
    test_no_other_session_generic_message()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-shared-checkout-guard.py`
Expected: `test_rearm_on_dirty_set_change` fails (current code dedupes forever, so `out2` has no `systemMessage`); `test_other_active_session_named_in_message` fails (no enrichment yet).

- [ ] **Step 3: Implement the fix**

Replace the full contents of `C:/Users/Owner/.claude/hooks/shared-checkout-guard.py`:

```python
"""Shared-checkout hygiene guard -- PreToolUse hook for Edit|Write|MultiEdit.

WARNS (never blocks) when you edit a file in a shared-checkout repo's MAIN
checkout while that tree is dirty -- i.e., it holds uncommitted/untracked work
that may be another session's WIP. The nudge: claim an isolated worktree and
verify `git status` before committing, so you don't co-mingle another writer's
hunks (the contaminated-checkout hazard). Silent when you are already in a
linked worktree, when the tree is clean, or when the file is outside the shared
repos. Re-arms per repo whenever the repo-wide dirty-file set CHANGES (a
fingerprint of `git status --porcelain`, not just once-ever per session) --
so a second collision after the first warning is no longer silently swallowed.
When another Claude Code session is currently open (per
hooks/lib/session_liveness.py, itself a fail-open enrichment signal), the
warning names it specifically.

SAFETY INVARIANT: warn-only. It NEVER denies a tool call, and the whole body is
wrapped in try/except -- on ANY error it prints nothing and exits 0 (ALLOW).
A bug here must never block or slow an edit.

Stdlib only. ASCII-only. Windows (`python`).
"""

import hashlib
import json
import os
import subprocess
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
from session_liveness import other_active_sessions  # noqa: E402

DEFAULT_REPOS = [
    "C:/Users/Owner/oxford-command-center",
    "C:/Users/Owner/ora-skills",
    "C:/Users/Owner/.claude",
]
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def shared_repos():
    raw = os.environ.get("SHARED_CHECKOUT_REPOS")
    if raw:
        return [r for r in raw.split(os.pathsep) if r.strip()]
    return DEFAULT_REPOS


def find_repo(file_path, repos):
    fp = _norm(file_path)
    for r in repos:
        rn = _norm(r)
        if fp == rn or fp.startswith(rn + os.sep):
            return r
    return None


def is_linked_worktree(repo):
    # A linked worktree's .git is a FILE (gitdir pointer); a main checkout's is a DIR.
    return os.path.isfile(os.path.join(repo, ".git"))


def is_main_checkout(repo):
    return os.path.isdir(os.path.join(repo, ".git"))


def git_status_lines(repo):
    # Non-empty `git status --porcelain` lines for repo, or None on ANY
    # error (fail-open -> caller treats None as "nothing to warn about").
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def status_fingerprint(lines):
    # Stable hash of the repo-wide dirty-file set, used to re-arm the
    # per-session warning when the dirty set changes (not just once-ever).
    joined = "\n".join(sorted(lines))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    repo = find_repo(file_path, shared_repos())
    if repo is None:
        return  # fast path: not a shared-checkout repo -> no git call at all

    if is_linked_worktree(repo):
        return  # already isolated -- good, stay silent
    if not is_main_checkout(repo):
        return  # not a git checkout we recognize -- fail-open

    lines = git_status_lines(repo)
    if not lines:
        return  # clean, or git error -- nothing to nudge about

    fp = status_fingerprint(lines)

    sessions_dir = os.environ.get("SHARED_CHECKOUT_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)
    repo_key = os.path.basename(repo.rstrip("/\\")) or "repo"
    marker = os.path.join(sess_dir, "shared-checkout-warned-" + repo_key)

    prev_fp = None
    if os.path.exists(marker):
        try:
            with open(marker, "r", encoding="ascii") as fh:
                prev_fp = fh.read().strip()
        except Exception:
            prev_fp = None
    if prev_fp == fp:
        return  # same dirty-set already warned about this session -- stay silent

    try:
        os.makedirs(sess_dir, exist_ok=True)
        with open(marker, "w", encoding="ascii") as fh:
            fh.write(fp)
    except Exception:
        pass  # marker is best-effort; still warn

    n = len(lines)
    others = other_active_sessions(session_id)
    if others:
        who = others[0]["sid"][:8]
        status = others[0].get("status") or ""
        collision_note = (" Session `" + who + "` is open right now" +
                          (" (" + status + ")" if status else "") +
                          " -- likely the source of this WIP.")
    else:
        collision_note = ""

    msg = (
        "Shared-checkout hygiene: the " + repo_key + " MAIN checkout has " + str(n) +
        " uncommitted change(s) that may be another session's WIP." + collision_note +
        " Editing here risks co-mingling their hunks. Consider an isolated worktree "
        "(npm run worktree / EnterWorktree) and verify `git status` before committing."
    )
    # Non-blocking warning: `systemMessage` surfaces to the user; stderr is a fallback.
    sys.stdout.write(json.dumps({"systemMessage": msg}))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a tool call
    sys.exit(0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python C:/Users/Owner/.claude/hooks/tests/test-shared-checkout-guard.py`
Expected: `ALL SHARED-CHECKOUT-GUARD TESTS PASS` (all pre-existing tests plus the 4 new ones).

- [ ] **Step 5: Commit**

```bash
git add hooks/shared-checkout-guard.py hooks/tests/test-shared-checkout-guard.py
git commit -m "feat(hooks): shared-checkout-guard re-arms on dirty-set change, names the other active session"
```

---

## Final verification (after all 6 tasks)

- [ ] Run every touched test file in sequence and confirm all pass:
```bash
python C:/Users/Owner/.claude/maintenance/test-doctrine-integrity-probe.py
python C:/Users/Owner/.claude/hooks/tests/test-eos-claude-md-guard.py
python C:/Users/Owner/.claude/hooks/tests/test-session-liveness.py
python C:/Users/Owner/.claude/hooks/tests/test-shared-checkout-guard.py
```
- [ ] `python -c "import json; json.load(open('C:/Users/Owner/.claude/settings.json', encoding='utf-8'))"` — settings.json still valid JSON.
- [ ] `python C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py` — exit 0, no `[MISSING]`, `eos-claude-md-guard` shows `[OK] ... live invocation point found` under Guard liveness.
- [ ] `git -C C:/Users/Owner/.claude log --oneline -6` — confirms the 6 task commits landed, and `git status` shows no unexpected changes beyond this plan's scope (the pre-existing audit diff from before this plan started is untouched).
