# Commit-Provenance Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block a `git commit` that would sweep up another live session's uncommitted work, without ever wedging the fleet.

**Architecture:** Two small stdlib-only hooks. An append-only PostToolUse *recorder* writes per-session touched-file provenance to `hooks/sessions/<sid>/touched-files.txt`. A PreToolUse Bash *guard* fires only on `git commit`, computes the candidate file set, and blocks (exit 2 + stderr) only when a candidate appears in ANOTHER session's touched-set AND liveness affirmatively reports that session open AND its set is within a 6h TTL. Two affirmative signals means fail-open by construction; no lock is held, so deadlock is structurally impossible.

**Tech Stack:** Python 3.13 stdlib only (`json`, `os`, `re`, `sys`, `time`, `shlex`, `subprocess`). Windows. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md`

## Global Constraints

- **Stdlib only. ASCII-only source. Windows (`python`).** Matches every existing hook.
- **Fail open, always.** `main()` wrapped in `try/except`; ANY internal error → print nothing, `sys.exit(0)` (ALLOW). Only `SystemExit` propagates (the one real block). Copy `registry-write-guard.py`'s `__main__` idiom verbatim.
- **Exactly ONE block path** (guard only): exit 2 + stderr. Exit 2 is the only PreToolUse channel that reaches the model, and it blocks — that pairing is intended here. Verified 2026-07-16.
- **Two affirmative signals required to block.** Missing/stale/unreadable liveness or touched-set = "no information" = ALLOW. This honours `hooks/lib/session_liveness.py`'s explicit "ENRICHMENT ONLY, never a hard gate" contract.
- **Self-recognition is structural:** only `other_sid != my_sid` sets are consulted.
- **TTL default 6 hours** (`SESSION_PRUNE_H = 6` in `fleet-session-hook.py`).
- **Env seams (tests only, never required in prod):** `COMMIT_PROVENANCE_SESSIONS_DIR`, `COMMIT_PROVENANCE_TTL_H`, plus the existing `ORA_FLEET_STATE` consumed by `session_liveness`.
- **Python path:** `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe`
- **Run tests from** `C:/Users/Owner/.claude/hooks/tests`.
- **The recorder must be append-only** — never read-modify-write. That race is precisely what `session_liveness`'s docstring warns about.

## File Structure

| File | Responsibility |
|---|---|
| `hooks/commit-provenance-recorder.py` | CREATE. PostToolUse. Append one absolute normcase path per write to this session's touched-files.txt. Nothing else. |
| `hooks/tests/test-commit-provenance-recorder.py` | CREATE. 4 cases. |
| `hooks/commit-provenance-guard.py` | CREATE. PreToolUse/Bash. Detect `git commit`, resolve repo, compute candidates, intersect vs live others, block or allow. |
| `hooks/tests/test-commit-provenance-guard.py` | CREATE. 12 cases. |
| `settings.json` | MODIFY. Register recorder (PostToolUse) + guard (PreToolUse/Bash). |

**Single-writer warning:** `~/.claude` is a shared checkout with ~8 concurrent sessions. Before each commit run `git status --short` and stage **only** the exact paths named in that task's commit step. Never `git add -A`. If a file you did not touch appears modified, leave it.

---

### Task 1: Recorder

**Files:**
- Create: `C:/Users/Owner/.claude/hooks/commit-provenance-recorder.py`
- Test: `C:/Users/Owner/.claude/hooks/tests/test-commit-provenance-recorder.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the on-disk contract `hooks/sessions/<session_id>/touched-files.txt` — one `os.path.normcase(os.path.abspath(p))` path per line, UTF-8, append-only, duplicates permitted. Task 3's guard reads exactly this.

- [ ] **Step 1: Write the failing test**

Create `hooks/tests/test-commit-provenance-recorder.py`:

```python
"""Tests for commit-provenance-recorder.py PostToolUse hook.

Run: python test-commit-provenance-recorder.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs).
Append-only / fail-open: the recorder NEVER blocks and never rewrites the file.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "commit-provenance-recorder.py")


def run_hook(stdin_text, sessions_dir):
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK], input=stdin_text,
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def sessions_tmp():
    return tempfile.mkdtemp(prefix="cpr-sess-")


def read_touched(sessions_dir, sid):
    p = os.path.join(sessions_dir, sid, "touched-files.txt")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def test_edit_payload_records_file_path():
    sess = sessions_tmp()
    target = "C:/Users/Owner/.claude/some/file.md"
    payload = json.dumps({"session_id": "s1", "tool_input": {"file_path": target}})
    rc, out, err = run_hook(payload, sess)
    assert rc == 0, "recorder must never block, got %s (%s)" % (rc, err)
    got = read_touched(sess, "s1")
    assert got == [os.path.normcase(os.path.abspath(target))], "got %r" % got
    print("PASS test_edit_payload_records_file_path")


def test_desktop_commander_payload_uses_path_field():
    """DC's write_file uses 'path', not 'file_path' -- the same gap
    registry-write-guard.py and memory-index-guard.py both had to close."""
    sess = sessions_tmp()
    target = "C:/Users/Owner/.claude/other/file.md"
    payload = json.dumps({"session_id": "s2", "tool_input": {"path": target}})
    rc, out, err = run_hook(payload, sess)
    assert rc == 0
    got = read_touched(sess, "s2")
    assert got == [os.path.normcase(os.path.abspath(target))], "got %r" % got
    print("PASS test_desktop_commander_payload_uses_path_field")


def test_repeated_writes_append_not_overwrite():
    """Append-only: no read-modify-write, so no race. Duplicates are expected
    and are deduped by the READER, not the writer."""
    sess = sessions_tmp()
    a = "C:/Users/Owner/.claude/a.md"
    b = "C:/Users/Owner/.claude/b.md"
    for t in (a, b, a):
        run_hook(json.dumps({"session_id": "s3", "tool_input": {"file_path": t}}), sess)
    got = read_touched(sess, "s3")
    assert len(got) == 3, "append-only must keep all 3 lines, got %r" % got
    assert os.path.normcase(os.path.abspath(b)) in got, "got %r" % got
    print("PASS test_repeated_writes_append_not_overwrite")


def test_malformed_stdin_fails_open():
    sess = sessions_tmp()
    rc, out, err = run_hook("not json", sess)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    print("PASS test_malformed_stdin_fails_open")


def test_missing_path_is_noop():
    sess = sessions_tmp()
    rc, out, err = run_hook(json.dumps({"session_id": "s4", "tool_input": {}}), sess)
    assert rc == 0
    assert read_touched(sess, "s4") == [], "no path -> nothing recorded"
    print("PASS test_missing_path_is_noop")


if __name__ == "__main__":
    test_edit_payload_records_file_path()
    test_desktop_commander_payload_uses_path_field()
    test_repeated_writes_append_not_overwrite()
    test_malformed_stdin_fails_open()
    test_missing_path_is_noop()
    print("ALL COMMIT-PROVENANCE-RECORDER TESTS PASS")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-recorder.py
```
Expected: FAIL. The hook file does not exist yet, so `subprocess.run` returns a non-zero rc and the first assert trips with `recorder must never block, got 2 (... can't open file ... No such file or directory)`.

- [ ] **Step 3: Write minimal implementation**

Create `hooks/commit-provenance-recorder.py`:

```python
"""Commit-provenance recorder -- PostToolUse hook for Edit|Write|MultiEdit plus
Desktop Commander's write_file/edit_block (both the mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ prefixes).

Records WHAT THIS SESSION EDITED so that commit-provenance-guard.py (PreToolUse,
Bash) can recognise another live session's work and refuse to sweep it into a
commit. Half of a two-part guard; useless alone. Full rationale:
docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

Writes one absolute, normcase-normalised path per line to
  hooks/sessions/<session_id>/touched-files.txt

APPEND-ONLY BY DESIGN. It never reads the file back and never rewrites it, so
concurrent sessions cannot race here -- deliberately unlike
fleet-session-hook.py's unlocked load-mutate-replace cycle, which its own
session_liveness.py docstring flags as "a real, accepted, bounded race under
concurrent writers". Duplicate lines are EXPECTED and are deduped by the reader.

SAFETY INVARIANT: this hook has no opinions and no failure mode. It never blocks
anything (PostToolUse cannot), and the whole body is wrapped in try/except -- on
ANY error it exits 0 silently. A bug here degrades the guard to "no information",
which the guard treats as ALLOW.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"
TOUCHED_BASENAME = "touched-files.txt"


def sessions_dir():
    return os.environ.get("COMMIT_PROVENANCE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def norm(path):
    """The canonical on-disk form. The guard MUST normalise identically."""
    return os.path.normcase(os.path.abspath(path))


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    # Desktop Commander's write_file uses "path"; edit_block and native Edit use
    # "file_path" -- same fallback registry-write-guard.py settled on.
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(file_path, str) or not file_path:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return

    sess_dir = os.path.join(sessions_dir(), session_id)
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, TOUCHED_BASENAME), "a", encoding="utf-8") as fh:
        fh.write(norm(file_path) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a recorder bug must never affect a tool call
    sys.exit(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-recorder.py
```
Expected: 5 PASS lines then `ALL COMMIT-PROVENANCE-RECORDER TESTS PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Owner/.claude
git status --short   # confirm ONLY these two paths are yours; never `git add -A`
git add hooks/commit-provenance-recorder.py hooks/tests/test-commit-provenance-recorder.py
git commit -m "feat(hooks): add commit-provenance recorder (append-only touched-file log)"
```

---

### Task 2: Guard skeleton — detects `git commit`, blocks nothing

**Files:**
- Create: `C:/Users/Owner/.claude/hooks/commit-provenance-guard.py`
- Test: `C:/Users/Owner/.claude/hooks/tests/test-commit-provenance-guard.py`

**Interfaces:**
- Consumes: Task 1's `touched-files.txt` contract (not yet read in this task).
- Produces, for Task 3:
  - `sessions_dir() -> str`
  - `ttl_h() -> float`
  - `norm(path: str) -> str`
  - `is_git_commit(cmd: str) -> bool`
  - `repo_root(cmd: str, cwd: str) -> str | None`
  - `candidate_paths(repo: str, cmd: str) -> set[str] | None` (absolute normcase)

Deliverable: a guard that correctly identifies `git commit` invocations and their candidate files, and **always allows**. Independently reviewable — a reviewer can reject the parsing without judging the block logic.

- [ ] **Step 1: Write the failing test**

Create `hooks/tests/test-commit-provenance-guard.py`:

```python
"""Tests for commit-provenance-guard.py PreToolUse hook (matcher: Bash).

Run: python test-commit-provenance-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp git repos).
Fail-open BY CONSTRUCTION: blocking needs TWO affirmative signals (a foreign
touched-set hit AND affirmative liveness). Anything else -> allow.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "commit-provenance-guard.py")


def run_hook(cmd, cwd, sessions_dir, session_id="me", fleet_state=None, ttl_h=None):
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_dir
    if ttl_h is not None:
        env["COMMIT_PROVENANCE_TTL_H"] = str(ttl_h)
    env["ORA_FLEET_STATE"] = fleet_state or "C:/does/not/exist_cpg.json"
    payload = json.dumps({
        "session_id": session_id, "cwd": cwd,
        "tool_input": {"command": cmd},
    })
    proc = subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def make_repo():
    d = tempfile.mkdtemp(prefix="cpg-repo-")
    _git(["init", "-q"], d)
    _git(["config", "user.email", "t@t.t"], d)
    _git(["config", "user.name", "t"], d)
    return d


def write_and_stage(repo, name, text="x"):
    p = os.path.join(repo, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    _git(["add", name], repo)
    return os.path.normcase(os.path.abspath(p))


def sessions_tmp():
    return tempfile.mkdtemp(prefix="cpg-sess-")


def seed_touched(sessions_dir, sid, paths, age_h=0):
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "touched-files.txt")
    with open(p, "w", encoding="utf-8") as fh:
        for x in paths:
            fh.write(x + "\n")
    if age_h:
        old = time.time() - age_h * 3600
        os.utime(p, (old, old))
    return p


def fleet_state_with(sids):
    fd, path = tempfile.mkstemp(suffix="_fleet.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"sessions": {s: {"status": "working", "cwd": "x", "lastAt": "t"}
                                for s in sids}}, fh)
    return path


# ---------- Task 2 cases: detection + always-allow ----------

def test_non_git_command_silent():
    repo = make_repo()
    rc, out, err = run_hook("ls -la", repo, sessions_tmp())
    assert rc == 0, "non-git must allow, got %s" % rc
    assert out == "" and err == "", "must be silent, got %r / %r" % (out, err)
    print("PASS test_non_git_command_silent")


def test_git_commit_with_no_foreign_files_allows():
    repo = make_repo()
    write_and_stage(repo, "mine.txt")
    rc, out, err = run_hook('git commit -m "x"', repo, sessions_tmp())
    assert rc == 0, "no foreign files -> allow, got %s (%s)" % (rc, err)
    print("PASS test_git_commit_with_no_foreign_files_allows")


def test_malformed_stdin_fails_open():
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_tmp()
    proc = subprocess.run([sys.executable, HOOK], input="not json",
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
    print("PASS test_malformed_stdin_fails_open")


def test_cwd_not_a_repo_allows():
    d = tempfile.mkdtemp(prefix="cpg-norepo-")
    rc, out, err = run_hook('git commit -m "x"', d, sessions_tmp())
    assert rc == 0, "not a git repo -> allow, got %s" % rc
    print("PASS test_cwd_not_a_repo_allows")


def test_dry_run_allows():
    """--dry-run fixes no provenance, so it is never blocked."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit --dry-run -m "x"', repo, sess, fleet_state=fs)
    assert rc == 0, "--dry-run must always allow, got %s (%s)" % (rc, err)
    print("PASS test_dry_run_allows")


if __name__ == "__main__":
    test_non_git_command_silent()
    test_git_commit_with_no_foreign_files_allows()
    test_malformed_stdin_fails_open()
    test_cwd_not_a_repo_allows()
    test_dry_run_allows()
    print("ALL COMMIT-PROVENANCE-GUARD TESTS PASS")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-guard.py
```
Expected: FAIL on `test_non_git_command_silent` — the hook file does not exist, so rc is non-zero (`can't open file`).

- [ ] **Step 3: Write minimal implementation**

Create `hooks/commit-provenance-guard.py`:

```python
"""Commit-provenance guard -- PreToolUse hook, matcher: Bash.

BLOCKS a `git commit` that would sweep up ANOTHER LIVE SESSION's uncommitted
work. Companion to commit-provenance-recorder.py (PostToolUse), which supplies
the per-session touched-file provenance this guard reads.

WHY: on 2026-07-16 one session hit four concurrency events in an hour; THREE were
Bash git operations, invisible to any Edit|Write hook. The worst: a staged
MEMORY.md edit was swept into another session's commit inside the ~30s window
between this session's `git add` and its `git commit`. shared-checkout-guard.py
warns at EDIT time and is advisory; this guard enforces at COMMIT time, the one
chokepoint where provenance is fixed. Full rationale + rejected alternatives:
docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

SAFETY INVARIANT -- fail-open BY CONSTRUCTION, not by exception handling. It
blocks only on TWO affirmative signals: (a) a candidate file appears in another
session's touched-set, AND (b) session_liveness affirmatively reports that
session open, AND that set is within TTL. Missing/stale/unreadable data yields
"no information" -> ALLOW. This honours session_liveness.py's explicit contract
("ENRICHMENT ONLY, never a hard gate ... treat a read failure, or a stale/empty
result, the same as 'no information'"). NO LOCK IS EVER HELD, so a crashed
session cannot wedge the fleet -- the deadlock class does not exist here.

Deliberately narrow (precision over recall, same philosophy as
registry-write-guard.py): it does NOT catch foreign files written by a script
rather than the Edit tool. That accepted false negative is what makes the guard
survivable -- the naive "block anything I did not touch" design would have
blocked 31ac61d, a legitimate script-generated commit.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import re
import shlex
import subprocess
import sys

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"
DEFAULT_TTL_H = 6.0  # matches fleet-session-hook.py's SESSION_PRUNE_H = 6

# `git ... commit` within one shell segment (no |, ;, & between them).
GIT_COMMIT_RE = re.compile(r"\bgit\b[^|;&]*\bcommit\b")
GIT_C_RE = re.compile(r"""\bgit\b\s+-C\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))""")
CD_RE = re.compile(r"""\bcd\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))\s*&&""")


def sessions_dir():
    return os.environ.get("COMMIT_PROVENANCE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def ttl_h():
    try:
        return float(os.environ.get("COMMIT_PROVENANCE_TTL_H") or DEFAULT_TTL_H)
    except Exception:
        return DEFAULT_TTL_H


def norm(path):
    """MUST match commit-provenance-recorder.py's norm() exactly."""
    return os.path.normcase(os.path.abspath(path))


def _first_group(m):
    return next((g for g in m.groups() if g), None) if m else None


def is_git_commit(cmd):
    if not isinstance(cmd, str) or not cmd:
        return False
    if "--dry-run" in cmd:
        return False  # fixes no provenance
    return bool(GIT_COMMIT_RE.search(cmd))


def _git_lines(repo, args):
    try:
        proc = subprocess.run(["git", "-C", repo] + args,
                              capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def repo_root(cmd, cwd):
    """`git -C <p>` wins, else a leading `cd <p> &&`, else the payload cwd."""
    d = _first_group(GIT_C_RE.search(cmd)) or _first_group(CD_RE.search(cmd)) or cwd
    if not d:
        return None
    out = _git_lines(d, ["rev-parse", "--show-toplevel"])
    return out[0] if out else None


def _has_all_flag(cmd):
    """True for `-a`, `-am`, `--all`. False for `-m` and `--amend`
    (`^-[a-zA-Z]+$` cannot match a double-dash flag)."""
    try:
        tokens = shlex.split(cmd)
    except Exception:
        tokens = cmd.split()
    for t in tokens:
        if t == "--all":
            return True
        if re.match(r"^-[a-zA-Z]+$", t) and "a" in t:
            return True
    return False


def candidate_paths(repo, cmd):
    """Absolute normcase paths this commit would capture, or None if unknown."""
    # Explicit `-- <pathspec>` narrows the commit. This branch is load-bearing:
    # the block message tells the user to use a pathspec, so it MUST work.
    m = re.search(r"\s--\s+(.+)$", cmd)
    if m:
        try:
            given = shlex.split(m.group(1))
        except Exception:
            given = m.group(1).split()
        return {norm(os.path.join(repo, p)) for p in given if p}

    staged = _git_lines(repo, ["diff", "--cached", "--name-only"])
    if staged is None:
        return None
    rel = set(staged)
    if _has_all_flag(cmd):
        tracked = _git_lines(repo, ["diff", "--name-only"]) or []
        rel |= set(tracked)
    return {norm(os.path.join(repo, p)) for p in rel}


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    cmd = tool_input.get("command")
    if not is_git_commit(cmd):
        return  # fast path: not a commit -> no git calls at all

    repo = repo_root(cmd, payload.get("cwd") or "")
    if not repo:
        return  # not a repo we can resolve -> allow
    cands = candidate_paths(repo, cmd)
    if not cands:
        return  # nothing to commit, or unknown -> allow
    # Task 3 adds the foreign-hit check here.
    return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # fail open: any internal error must never block a tool call
    sys.exit(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-guard.py
```
Expected: 5 PASS lines then `ALL COMMIT-PROVENANCE-GUARD TESTS PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Owner/.claude
git status --short
git add hooks/commit-provenance-guard.py hooks/tests/test-commit-provenance-guard.py
git commit -m "feat(hooks): commit-provenance guard skeleton (detect git commit + candidate set)"
```

---

### Task 3: Guard blocks a foreign-file commit

**Files:**
- Modify: `C:/Users/Owner/.claude/hooks/commit-provenance-guard.py` (add `foreign_hits()`; extend `main()`)
- Modify: `C:/Users/Owner/.claude/hooks/tests/test-commit-provenance-guard.py` (add 7 cases)

**Interfaces:**
- Consumes: Task 2's `sessions_dir()`, `ttl_h()`, `norm()`, `candidate_paths()`; Task 1's `touched-files.txt`; `hooks/lib/session_liveness.other_active_sessions(my_sid) -> list[dict]` with `sid` and `status` keys.
- Produces: the terminal behaviour. No further tasks depend on new symbols.

- [ ] **Step 1: Write the failing tests**

Append to `hooks/tests/test-commit-provenance-guard.py`, immediately BEFORE the `if __name__ == "__main__":` block:

```python
# ---------- Task 3 cases: the block predicate ----------

def test_foreign_file_from_live_session_blocks():
    """THE case this guard exists for -- 2026-07-16's 4da5d26 sweep."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, "must BLOCK a foreign-file commit, got %s (%s)" % (rc, err)
    assert "theirs.txt" in err, "stderr must name the file, got %r" % err
    assert "other" in err, "stderr must name the owning session, got %r" % err
    print("PASS test_foreign_file_from_live_session_blocks")


def test_foreign_file_but_session_not_live_allows():
    """Liveness contract: no affirmative 'open' signal -> no information -> allow."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    rc, out, err = run_hook('git commit -m "x"', repo, sess,
                            fleet_state="C:/does/not/exist_cpg.json")
    assert rc == 0, "dead/unknown session must not block, got %s (%s)" % (rc, err)
    print("PASS test_foreign_file_but_session_not_live_allows")


def test_foreign_touched_set_older_than_ttl_allows():
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign], age_h=99)
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 0, "stale touched-set must not block, got %s (%s)" % (rc, err)
    print("PASS test_foreign_touched_set_older_than_ttl_allows")


def test_explicit_pathspec_excluding_foreign_allows():
    """The remediation the block message recommends MUST actually work."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    write_and_stage(repo, "mine.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x" -- mine.txt', repo, sess, fleet_state=fs)
    assert rc == 0, "pathspec excluding the foreign file must allow, got %s (%s)" % (rc, err)
    print("PASS test_explicit_pathspec_excluding_foreign_allows")


def test_override_sentinel_allows():
    """The deliberate 'land the orphaned backlog' janitor workflow (c0272bb)."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    d = os.path.join(sess, "me")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "allow-foreign-commit"), "w", encoding="ascii") as fh:
        fh.write("landing backlog")
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 0, "override sentinel must allow, got %s (%s)" % (rc, err)
    print("PASS test_override_sentinel_allows")


def test_own_touched_set_never_blocks_self():
    """Self-recognition is structural: only other_sid != my_sid is consulted."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    sess = sessions_tmp()
    seed_touched(sess, "me", [mine])
    fs = fleet_state_with(["me"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, session_id="me", fleet_state=fs)
    assert rc == 0, "a session must never block itself, got %s (%s)" % (rc, err)
    print("PASS test_own_touched_set_never_blocks_self")


def test_commit_dash_a_picks_up_foreign_tracked_modification():
    repo = make_repo()
    p = os.path.join(repo, "theirs.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1")
    _git(["add", "theirs.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- their uncommitted edit")   # tracked-modified, NOT staged
    foreign = os.path.normcase(os.path.abspath(p))
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -am "x"', repo, sess, fleet_state=fs)
    assert rc == 2, "-a must capture tracked-modified foreign files, got %s (%s)" % (rc, err)
    print("PASS test_commit_dash_a_picks_up_foreign_tracked_modification")
```

And replace the `__main__` block with:

```python
if __name__ == "__main__":
    test_non_git_command_silent()
    test_git_commit_with_no_foreign_files_allows()
    test_malformed_stdin_fails_open()
    test_cwd_not_a_repo_allows()
    test_dry_run_allows()
    test_foreign_file_from_live_session_blocks()
    test_foreign_file_but_session_not_live_allows()
    test_foreign_touched_set_older_than_ttl_allows()
    test_explicit_pathspec_excluding_foreign_allows()
    test_override_sentinel_allows()
    test_own_touched_set_never_blocks_self()
    test_commit_dash_a_picks_up_foreign_tracked_modification()
    print("ALL COMMIT-PROVENANCE-GUARD TESTS PASS")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-guard.py
```
Expected: the 5 Task-2 cases PASS, then FAIL on `test_foreign_file_from_live_session_blocks` with `must BLOCK a foreign-file commit, got 0` — the guard currently always allows.

- [ ] **Step 3: Write the implementation**

In `hooks/commit-provenance-guard.py`, add `time` to the imports:

```python
import time
```

Add the liveness import directly below the existing imports:

```python
LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
from session_liveness import other_active_sessions  # noqa: E402
```

Add `TOUCHED_BASENAME` next to the other constants:

```python
TOUCHED_BASENAME = "touched-files.txt"
OVERRIDE_BASENAME = "allow-foreign-commit"
```

Add this function above `main()`:

```python
def foreign_hits(candidates, my_sid):
    """[(path, other_sid, status)] for candidates owned by ANOTHER LIVE session.

    Requires TWO affirmative signals per hit: the other session is affirmatively
    reported open by session_liveness, AND its touched-set is within TTL. Any
    read failure, missing file, or stale set is treated as NO INFORMATION and
    yields no hit -- never a block. This is session_liveness.py's documented
    contract, and it is what makes this guard fail-open by construction.
    """
    try:
        live = other_active_sessions(my_sid) or []
    except Exception:
        return []  # no information -> allow
    if not live:
        return []
    cutoff = time.time() - ttl_h() * 3600.0
    base = sessions_dir()
    hits = []
    for entry in live:
        sid = (entry or {}).get("sid")
        if not sid or sid == my_sid:
            continue
        path = os.path.join(base, sid, TOUCHED_BASENAME)
        try:
            if not os.path.exists(path) or os.path.getmtime(path) < cutoff:
                continue
            with open(path, encoding="utf-8") as fh:
                touched = {ln.strip() for ln in fh if ln.strip()}  # dedupe on read
        except Exception:
            continue  # unreadable -> no information -> no hit
        for p in sorted(candidates & touched):
            hits.append((p, sid, (entry.get("status") or "")))
    return hits
```

Replace the `# Task 3 adds the foreign-hit check here.` / `return` lines at the end of `main()` with:

```python
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    # Deliberate backlog-landing (the c0272bb janitor workflow) stays possible.
    if os.path.exists(os.path.join(sessions_dir(), session_id, OVERRIDE_BASENAME)):
        return

    hits = foreign_hits(cands, session_id)
    if not hits:
        return

    shown = hits[:5]
    detail = "\n".join(
        "  - %s  (edited by session %s%s)"
        % (os.path.basename(p), sid[:8], (" -- " + st) if st else "")
        for p, sid, st in shown
    )
    more = "" if len(hits) <= 5 else "\n  ... and %d more" % (len(hits) - 5)
    reason = (
        "This `git commit` would capture %d file(s) that ANOTHER LIVE SESSION "
        "edited:\n%s%s\n\n"
        "Committing them here attributes their work to you and can strand or "
        "clobber it (2026-07-16: a staged edit was swept into another session's "
        "commit inside a 30s window). Two ways forward:\n"
        "  1. Commit only your own files with an explicit pathspec:\n"
        "     git commit -m \"...\" -- <your/file> <your/other-file>\n"
        "  2. If you are DELIBERATELY landing another session's orphaned work, "
        "declare it:\n"
        "     touch \"%s\"\n"
        % (len(hits), detail, more,
           os.path.join(sessions_dir(), session_id, OVERRIDE_BASENAME).replace("\\", "/"))
    )
    sys.stderr.write("BLOCKED (commit-provenance-guard): " + reason + "\n")
    sys.exit(2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" test-commit-provenance-guard.py
```
Expected: 12 PASS lines then `ALL COMMIT-PROVENANCE-GUARD TESTS PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Owner/.claude
git status --short
git add hooks/commit-provenance-guard.py hooks/tests/test-commit-provenance-guard.py
git commit -m "feat(hooks): block commits that would sweep another live session's work"
```

---

### Task 4: Register both hooks; prove no regressions

**Files:**
- Modify: `C:/Users/Owner/.claude/settings.json`

**Interfaces:**
- Consumes: Tasks 1-3's two hook files.
- Produces: live enforcement.

- [ ] **Step 1: Register the recorder (PostToolUse)**

In `settings.json`, inside `hooks.PostToolUse`, append this entry. Match the Desktop Commander alias coverage `registry-write-guard.py` already uses:

```json
{
  "matcher": "Edit|Write|MultiEdit|mcp__Desktop_Commander__write_file|mcp__Desktop_Commander__edit_block|mcp__plugin_desktop-commander_desktop-commander__write_file|mcp__plugin_desktop-commander_desktop-commander__edit_block",
  "hooks": [
    {
      "type": "command",
      "command": "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \"C:/Users/Owner/.claude/hooks/commit-provenance-recorder.py\""
    }
  ]
}
```

- [ ] **Step 2: Register the guard (PreToolUse)**

In `settings.json`, inside `hooks.PreToolUse`, append:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \"C:/Users/Owner/.claude/hooks/commit-provenance-guard.py\""
    }
  ]
}
```

Order does not matter: all matching PreToolUse hooks run and a deny wins (verified live 2026-07-16 — `shared-checkout-guard` returned `allow` while `registry-write-guard` still blocked a registry write).

- [ ] **Step 3: Verify settings.json is still valid JSON and both are registered**

Run:
```bash
cd /c/Users/Owner/.claude && "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" -c "
import json,io
s=json.load(io.open('settings.json',encoding='utf-8'))
names=[h.get('command','') for evt in ('PreToolUse','PostToolUse') for it in s['hooks'][evt] for h in it.get('hooks',[])]
print('recorder registered:', any('commit-provenance-recorder' in n for n in names))
print('guard registered   :', any('commit-provenance-guard' in n for n in names))
"
```
Expected:
```
recorder registered: True
guard registered   : True
```
If `json.load` raises, the edit broke the file — fix before continuing. `settings.json` is blast-radius.

- [ ] **Step 4: Full no-regression gate (all 20 test files)**

Run:
```bash
cd /c/Users/Owner/.claude/hooks/tests
PY="C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe"
pass=0; fail=0
for t in test-*.py; do
  if "$PY" "$t" >/dev/null 2>&1; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL $t"; fi
done
echo "passed=$pass failed=$fail"
```
Expected: `passed=20 failed=0` (the 18 pre-existing files plus the 2 new ones). Any FAIL is a regression — fix before committing.

- [ ] **Step 5: Live smoke test — a real block, then a real allow**

Run:
```bash
cd /c/Users/Owner/.claude
SID=$(ls -t hooks/sessions | head -1)   # this session's dir
echo "--- simulate: another live session owns a file we are about to commit ---"
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" -c "
import json,os,sys
sys.path.insert(0,'C:/Users/Owner/.claude/hooks/lib')
from session_liveness import other_active_sessions
o=other_active_sessions('$SID')
print('other live sessions:', [(x['sid'][:8], x.get('status')) for x in o][:3] or 'NONE -> smoke test cannot fire; skip step 5')
"
```
If at least one other session is live, seed its touched-set with a file you have staged and confirm `git commit` is blocked with the guard's message, then confirm `git commit -m "x" -- <your-file>` is allowed. If no other session is live, note that the live smoke test was skipped and rely on the 12 unit cases. **Do not fake liveness state in the real fleet mirror to force the test.**

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Owner/.claude
git status --short
git add settings.json
git commit -m "feat(hooks): register commit-provenance recorder + guard"
```

---

## Self-Review

**Spec coverage:** §4a recorder → Task 1. §4b + §5 predicate → Tasks 2-3. §6 command detection (`git -C`, `cd &&`, `--dry-run`) → Task 2 `is_git_commit`/`repo_root`. §7 candidate set (staged / `-a` / pathspec) → Task 2 `candidate_paths`, tested in Task 3 cases 6 + 12. §8 override → Task 3. §9 all 12 guard + 4 recorder cases → Tasks 1-3 (recorder has 5: the spec's 4 plus `missing_path_is_noop`). §11.3 registration → Task 4. §11.4 suite + smoke → Task 4 steps 4-5.

**Gap found and closed:** spec §11.5 (memory note + guard-liveness roster) is NOT covered by a task — it is post-merge documentation, not implementation. Do it after Task 4 lands; `doctrine-integrity-probe.py`'s guard-liveness check reads 6 guards today and will not see these two until added.

**Placeholder scan:** none. Every code step contains complete, runnable code.

**Type consistency:** `norm()` is defined identically in both files (Task 1 / Task 2) — this is the load-bearing contract; if they diverge, every comparison silently misses and the guard becomes a no-op. `sessions_dir()`, `ttl_h()`, `TOUCHED_BASENAME` consistent across both. `other_active_sessions(my_sid)` returns dicts keyed `sid`/`status`, matching `test-shared-checkout-guard.py`'s existing usage of the same function.
