"""Time-bound + exactness tests for the shared linear shlex (hooks/lib/linear_shlex.py) as
used by commit-hygiene-guard.py and memory-orphan-link-guard.py (2026-09-21).

WHY. Both guards sit in the dispatcher's in-process BASH chain and both tokenize the WHOLE
command with stdlib shlex as soon as the text contains the substring "commit" -- NOT only
for `git commit`: `echo commit; <blob>` is enough. stdlib shlex builds each token with
`self.token += ch` (one full string copy per char), so ONE long token (a base64 blob, a
minified one-liner) is O(len^2): measured 512KB ~ 10-12s PER PASS, and the guards make
2-4 passes (commit-hygiene: is_git_commit + analyze + the _tokens fallback; memory-orphan:
_is_git_commit + _resolve_target_repo + one _commit_would_include per index). The
dispatcher has no per-guard timeout, so every guard behind them stalls. config-write-guard
already got the fix (PR #245); this pins the same fix, shared, in the two remaining guards.

This file pins:
  * LIB    -- hooks/lib/linear_shlex.py exists, config-write-guard uses the SAME class.
  * EXACT  -- seeded differential fuzz + bounded exhaustive enumeration of the shared class
              against stdlib shlex under EACH guard's exact constructor arguments, tokens AND
              exception type+message (both guards branch on the exception), plus the real
              guard entry points against the ORIGINAL stdlib code copied verbatim below.
  * TIME   -- time.thread_time GROWTH RATIO (4x input must cost < 7x: linear ~4x, quadratic
              ~16x). Absolute bounds flake under load, so the absolute cap is loose.
  * WALL   -- process-boundary wall clock through the real guards on a 512KB command.
  * SAFE   -- a huge commit command still gets the guard's verdict (advisory / deny).
  * DEGRADE-- with the lib module missing each guard stays live on the stdlib class.

Run: python test-linear-shlex-commit-guards.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(HOOKS_DIR, "lib")
sys.path.insert(0, LIB_DIR)

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def _load(filename, modname):
    spec = importlib.util.spec_from_file_location(
        modname, os.path.join(HOOKS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    import linear_shlex as LS  # noqa: E402
except Exception:
    LS = None

CH = _load("commit-hygiene-guard.py", "chg_linear_under_test")
MO = _load("memory-orphan-link-guard.py", "mol_linear_under_test")
CWG = _load("config-write-guard.py", "cwg_linear_shared_under_test")


# ---- ORACLES: the ORIGINAL stdlib-shlex code, copied verbatim (never imported from the
# code under test). commit-hygiene-guard._tokens/_segments and memory-orphan-link-guard.
# _tokenize_segments as on origin/main before this change.
def raw_ch_tokens(cmd):
    try:
        return shlex.split(cmd, posix=True)
    except Exception:
        try:
            return cmd.split()
        except Exception:
            return []


def raw_ch_segments(cmd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=CH.SEP_CHARS)
        lex.whitespace_split = True
        lex.whitespace = lex.whitespace.replace("\n", "")
        lex.commenters = ""
        toks = list(lex)
    except Exception:
        toks = raw_ch_tokens(cmd)
    segs, cur = [], []
    for t in toks:
        if t and all(c in CH.SEP_CHARS for c in t):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def raw_mo_segments(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="".join(MO._FULL_PUNCTUATION_CHARS))
    lex.whitespace_split = True
    lex.whitespace = lex.whitespace.replace("\n", "")
    lex.commenters = ""
    try:
        toks = list(lex)
    except ValueError:
        return None
    segs, cur = [], []
    for tok in toks:
        pure = tok and all(c in MO._FULL_PUNCTUATION_CHARS for c in tok)
        sep = pure and any(c in MO._SEGMENT_OP_CHARS for c in tok)
        if sep:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        segs.append(cur)
    return segs


# ------------------------------------------------- each guard's EXACT constructor recipe
def _ch_segments_cfg(cls, text):
    lex = cls(text, posix=True, punctuation_chars=CH.SEP_CHARS)
    lex.whitespace_split = True
    lex.whitespace = lex.whitespace.replace("\n", "")
    lex.commenters = ""
    return list(lex)


def _ch_split_cfg(cls, text):
    lex = cls(text, posix=True)              # what shlex.split(text, posix=True) builds
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def _mo_cfg(cls, text):
    lex = cls(text, posix=True, punctuation_chars="".join(MO._FULL_PUNCTUATION_CHARS))
    lex.whitespace_split = True
    lex.whitespace = lex.whitespace.replace("\n", "")
    lex.commenters = ""
    return list(lex)


CONFIGS = (("commit-hygiene _segments", _ch_segments_cfg),
           ("commit-hygiene _tokens (shlex.split)", _ch_split_cfg),
           ("memory-orphan _tokenize_segments", _mo_cfg))


def _result(cfg, cls, text):
    try:
        out = cfg(cls, text)
    except Exception as e:
        return ("EXC", type(e).__name__, str(e))
    # TokenBuf.__eq__ makes a leaked TokenBuf compare EQUAL to its string, so equality alone
    # cannot see one: pin the exact type of every emitted token too.
    if any(type(tok) is not str for tok in out):
        return ("BADTYPE", [type(tok).__name__ for tok in out])
    return out


TOKENS = ["a", "b", "git", "commit", "-m", "-a", " ", "  ", "\t", "\n", "\n\n", "'", "\"",
          "\\", "\\\\", "(", ")", ";", "|", "||", "&", "&&", "<", ">", ">>", "2>&1", "#",
          "# c\n", "~", "-", ".", "/", "=", "*", "?", "$", "`", "{", "}", "C:\\x", "\u00a0",
          "\u00e9", "1", "'a b'", "\"c d\"", "\\'", "\\\"", "\\ ", "$(", ")", "<<'EOF'\n",
          "EOF\n", "-m \"x\ny\"", ";(", "&(", ");"]


def _rand_from(rng, toks, lo, hi):
    return "".join(rng.choice(toks) for _ in range(rng.randint(lo, hi)))


# ---------------------------------------------------------------------------- LIB
def test_lib_module_and_sharing():
    check("hooks/lib/linear_shlex.py is importable with the shared API",
          LS is not None and hasattr(LS, "LinearShlex") and hasattr(LS, "TokenBuf")
          and hasattr(LS, "shlex_class") and hasattr(LS, "split")
          and LS.SHLEX_LINEAR_MIN_CHARS == 12288,
          "missing lib module or API")
    if LS is None:
        return
    check("shlex_class: stdlib at/below the threshold, LinearShlex above it",
          LS.shlex_class("a" * 12288) is shlex.shlex
          and LS.shlex_class("a" * 12289) is LS.LinearShlex)
    check("config-write-guard uses the SHARED class (one implementation, no drift)",
          CWG._LinearShlex is LS.LinearShlex and CWG._TokenBuf is LS.TokenBuf
          and CWG._SHLEX_LINEAR_MIN_CHARS == LS.SHLEX_LINEAR_MIN_CHARS)
    check("commit-hygiene-guard resolves the shared lib class",
          getattr(CH, "_shlex_class", None) is LS.shlex_class)
    check("memory-orphan-link-guard resolves the shared lib class",
          getattr(MO, "_shlex_class", None) is LS.shlex_class)


# ---------------------------------------------------------------------------- EXACT
def test_linear_class_exactness_per_guard_config():
    if LS is None:
        check("linear class exactness (lib missing)", False, "no linear_shlex module")
        return
    rng = random.Random(20260921)
    n = 20000
    for label, cfg in CONFIGS:
        bad, ok, exc = [], 0, 0
        for _ in range(n):
            s = _rand_from(rng, TOKENS, 0, 16)
            want = _result(cfg, shlex.shlex, s)
            got = _result(cfg, LS.LinearShlex, s)
            if isinstance(want, tuple):
                exc += 1
            else:
                ok += 1
            if want != got:
                bad.append((s, want, got))
            if len(bad) >= 5:
                break
        check("LinearShlex == stdlib (tokens, or exception type+message), %s: %d fuzz "
              "(%d parsed, %d raised)" % (label, n, ok, exc), not bad, ascii(bad[:2]))
        check("fuzz not vacuous, %s (>=8000 parsed, >=1000 raised)" % label,
              ok >= 8000 and exc >= 1000, "parsed=%d raised=%d" % (ok, exc))


def test_linear_class_exhaustive_small_alphabet():
    if LS is None:
        check("linear class exhaustive (lib missing)", False, "no linear_shlex module")
        return
    alphabet = ["a", " ", "'", "\"", "\\", ";", "\n", "#", "&", "("]
    strings = [""]
    frontier = [""]
    for _ in range(5):
        frontier = [s + c for s in frontier for c in alphabet]
        strings.extend(frontier)
    for label, cfg in CONFIGS:
        bad = []
        for s in strings:
            if _result(cfg, shlex.shlex, s) != _result(cfg, LS.LinearShlex, s):
                bad.append(s)
                if len(bad) >= 3:
                    break
        check("LinearShlex == stdlib EXHAUSTIVE (%d strings <=5 over a %d-char alphabet), %s"
              % (len(strings), len(alphabet), label), not bad, ascii(bad))


FILLERS = (lambda n: "a" * n,
           lambda n: "'" + "a" * n + "'",
           lambda n: "\"" + "a b\n" * (n // 4) + "\"",
           lambda n: "\\a" * (n // 2),
           lambda n: "'a'\"b\"" * (n // 5),
           lambda n: "a" * n + "'",              # unbalanced: exception path, linear class
           lambda n: "\"" + "a" * n)             # unbalanced double quote


def test_guard_entry_points_match_original_across_the_threshold():
    rng = random.Random(20260922)
    bad = []
    runs = 0
    for _ in range(240):
        pre = _rand_from(rng, TOKENS, 0, 6)
        post = _rand_from(rng, TOKENS, 0, 6)
        filler = rng.choice(FILLERS)(rng.randint(12250, 14000))
        text = rng.choice(("git commit -m ", "echo commit; ", "git add -A && git commit ",
                           "")) + pre + filler + post
        runs += 1
        if not all(type(tok) is str for seg in CH._segments(text) for tok in seg):
            bad.append(("CH._segments token type", len(text)))
        if CH._segments(text) != raw_ch_segments(text):
            bad.append(("CH._segments", len(text)))
        if CH._tokens(text) != raw_ch_tokens(text):
            bad.append(("CH._tokens", len(text)))
        if MO._tokenize_segments(text) != raw_mo_segments(text):
            bad.append(("MO._tokenize_segments", len(text)))
        if len(bad) >= 5:
            break
    check("real guard tokenizers == ORIGINAL stdlib code on %d texts straddling/above the "
          "12288-char threshold" % runs, not bad, ascii(bad[:3]))
    # below the threshold the stdlib class must be used untouched
    small = "git add -A&&git commit -m 'x y'\ngit status"
    check("below the threshold the answer is unchanged (commit-hygiene)",
          CH._segments(small) == raw_ch_segments(small) == [
              ["git", "add", "-A"], ["git", "commit", "-m", "x y"], ["git", "status"]])
    check("below the threshold the answer is unchanged (memory-orphan)",
          MO._tokenize_segments(small) == raw_mo_segments(small))
    for label, fn, raw in (("CH._segments", CH._segments, raw_ch_segments),
                           ("MO._tokenize_segments", MO._tokenize_segments, raw_mo_segments)):
        for text in ("", "  ", "'unclosed", "git commit -m '" + "a" * 13000,
                     "echo " + "x" * 13000 + " 'q r' \"s t\" \\u ; a | b"):
            check("%s == original on edge input (%d chars)" % (label, len(text)),
                  fn(text) == raw(text))


# ---------------------------------------------------------------------------- TIME
def cpu(fn, *args):
    t0 = time.thread_time()
    r = fn(*args)
    return time.thread_time() - t0, r


def _growth(label, fn, mk, abs_cap=6.0):
    small, big = mk(131072), mk(524288)
    dt_s, _ = cpu(fn, small)
    dt_b, _ = cpu(fn, big)
    check("%s scales linearly: 128KB %.3fs, 512KB %.3fs" % (label, dt_s, dt_b),
          dt_b < 7 * dt_s + 0.1 and dt_b < abs_cap)


SHAPES = (("one long token", lambda n: "git commit -m " + "a" * n),
          ("non-git command mentioning commit", lambda n: "echo commit; echo " + "a" * n),
          ("glued quoted fragments", lambda n: "git commit -m " + "'a'\"b\"" * (n // 5)),
          ("unbalanced quote (exception + fallback passes)",
           lambda n: "git commit -m '" + "a" * n))


def test_commit_hygiene_cpu_growth():
    for shape, mk in SHAPES:
        _growth("commit-hygiene _segments (%s)" % shape, CH._segments, mk)
    _growth("commit-hygiene _tokens (%s)" % SHAPES[0][0], CH._tokens, SHAPES[0][1])
    _growth("commit-hygiene is_git_commit (%s)" % SHAPES[1][0], CH.is_git_commit, SHAPES[1][1])
    _growth("commit-hygiene analyze (%s)" % SHAPES[0][0],
            lambda c: CH.analyze(c, "C:/x"), SHAPES[0][1])


def test_memory_orphan_cpu_growth():
    for shape, mk in SHAPES:
        _growth("memory-orphan _tokenize_segments (%s)" % shape, MO._tokenize_segments, mk)
    _growth("memory-orphan _is_git_commit (%s)" % SHAPES[1][0], MO._is_git_commit,
            SHAPES[1][1])
    _growth("memory-orphan _commit_would_include (%s)" % SHAPES[0][0],
            lambda c: MO._commit_would_include(c, "memory/MEMORY.md", False), SHAPES[0][1])


# ---------------------------------------------------------------------------- WALL
WALL_BOUND = 5.0


def _run_guard(script, payload, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    t0 = time.monotonic()
    proc = subprocess.run([sys.executable, script], input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, timeout=300)
    return (time.monotonic() - t0, proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", repo] + list(args),
                   check=True, capture_output=True)


def _make_repo(orphan=False):
    repo = tempfile.mkdtemp(prefix="lscg-repo-")
    _git(repo, "init", "-q")
    os.makedirs(os.path.join(repo, "memory"))
    idx = os.path.join(repo, "memory", "MEMORY.md")
    with open(idx, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# index\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    if orphan:
        with open(idx, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("- [Ghost](ghost_body.md) - never written\n")
        _git(repo, "add", "memory/MEMORY.md")
    return repo, idx


def _bash(cmd, cwd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd,
            "session_id": "lscg-session-0123456789"}


def test_real_guards_finish_in_bounded_wall_time():
    repo, idx = _make_repo()
    sess = tempfile.mkdtemp(prefix="lscg-sess-")
    ch = os.path.join(HOOKS_DIR, "commit-hygiene-guard.py")
    mo = os.path.join(HOOKS_DIR, "memory-orphan-link-guard.py")
    ch_env = {"COMMIT_HYGIENE_SESSIONS_DIR": sess}
    mo_env = {"ORA_MEMORY_INDEX": idx}
    for label, cmd in (("git commit -m <512KB token>", "git commit -am " + "a" * 524288),
                       ("echo commit; <512KB token>", "echo commit; echo " + "a" * 524288)):
        dt, rc, _out, err = _run_guard(ch, _bash(cmd, repo), ch_env)
        check("commit-hygiene-guard wall-clock bound (%s): %.2fs rc=%s" % (label, dt, rc),
              rc == 0 and dt < WALL_BOUND, err[:160])
        dt, rc, _out, err = _run_guard(mo, _bash(cmd, repo), mo_env)
        check("memory-orphan-link-guard wall-clock bound (%s): %.2fs rc=%s" % (label, dt, rc),
              rc == 0 and dt < WALL_BOUND, err[:160])


# ---------------------------------------------------------------------------- SAFE
def test_huge_commit_commands_still_get_their_verdict():
    blob = "a" * 262144
    repo, idx = _make_repo(orphan=True)
    sess = tempfile.mkdtemp(prefix="lscg-sess2-")
    dt, rc, out, err = _run_guard(os.path.join(HOOKS_DIR, "memory-orphan-link-guard.py"),
                                  _bash('git commit -m "%s"' % blob, repo),
                                  {"ORA_MEMORY_INDEX": idx})
    check("memory-orphan-link-guard still DENIES an orphan index link behind a 256KB "
          "message: %.2fs" % dt,
          rc == 0 and '"permissionDecision": "deny"' in out and "ghost_body.md" in out
          and dt < WALL_BOUND, (out + err)[:200])
    repo2, _idx2 = _make_repo()
    dt, rc, out, err = _run_guard(os.path.join(HOOKS_DIR, "commit-hygiene-guard.py"),
                                  _bash('git commit -am "%s"' % blob, repo2),
                                  {"COMMIT_HYGIENE_SESSIONS_DIR": sess})
    check("commit-hygiene-guard still emits its BRANCH + UNSCOPED advisory behind a 256KB "
          "message: %.2fs" % dt,
          rc == 0 and "BRANCH" in out and "UNSCOPED STAGE" in out and dt < WALL_BOUND,
          (out + err)[:200])


# ---------------------------------------------------------------------------- DEGRADE
def test_guards_stay_live_when_the_lib_module_is_missing():
    # Process boundary: a guard copied ALONE beside an empty lib/ (a partial deploy: the
    # guard landed before the lib on the shared checkout) must still do its job on the
    # stdlib class -- never go inert, never crash.
    stage = tempfile.mkdtemp(prefix="lscg-partial-")
    os.makedirs(os.path.join(stage, "lib"))
    for name in ("commit-hygiene-guard.py", "memory-orphan-link-guard.py"):
        shutil.copy(os.path.join(HOOKS_DIR, name), os.path.join(stage, name))
    repo, idx = _make_repo(orphan=True)
    sess = tempfile.mkdtemp(prefix="lscg-sess3-")
    dt, rc, out, err = _run_guard(os.path.join(stage, "commit-hygiene-guard.py"),
                                  _bash("git commit -am x", repo),
                                  {"COMMIT_HYGIENE_SESSIONS_DIR": sess})
    check("commit-hygiene-guard (lib missing) still advises: rc=%s" % rc,
          rc == 0 and "BRANCH" in out, (out + err)[:200])
    dt, rc, out, err = _run_guard(os.path.join(stage, "memory-orphan-link-guard.py"),
                                  _bash("git commit -m x", repo), {"ORA_MEMORY_INDEX": idx})
    check("memory-orphan-link-guard (lib missing) still DENIES an orphan: rc=%s" % rc,
          rc == 0 and '"permissionDecision": "deny"' in out, (out + err)[:200])
    # In-process: blocking the import must leave the SAME tokenizer answers (stdlib class).
    saved = sys.modules.get("linear_shlex")
    sys.modules["linear_shlex"] = None          # `import linear_shlex` now raises ImportError
    try:
        ch = _load("commit-hygiene-guard.py", "chg_nolib")
        mo = _load("memory-orphan-link-guard.py", "mol_nolib")
        cwg = _load("config-write-guard.py", "cwg_nolib")
    finally:
        if saved is None:
            sys.modules.pop("linear_shlex", None)
        else:
            sys.modules["linear_shlex"] = saved
    big = "git commit -m " + "a" * 13000 + " ; git add -A"
    check("commit-hygiene-guard (lib blocked) tokenizes identically via stdlib AND the "
          "stdlib fallbacks engaged",
          ch._segments(big) == raw_ch_segments(big)
          and ch.is_git_commit(big) is True
          and ch._shlex_class(big) is shlex.shlex and ch._shlex_split is shlex.split)
    check("memory-orphan-link-guard (lib blocked) tokenizes identically via stdlib AND the "
          "stdlib fallback engaged",
          mo._tokenize_segments(big) == raw_mo_segments(big)
          and mo._is_git_commit(big) is True and mo._shlex_class(big) is shlex.shlex)
    check("config-write-guard (lib blocked) falls back to stdlib shlex and still tokenizes",
          cwg._LinearShlex is shlex.shlex
          and cwg._tokenize("echo " + "x" * 13000 + " > out.txt", True)
          == ["echo", "x" * 13000, ">", "out.txt"])


if __name__ == "__main__":
    test_lib_module_and_sharing()
    test_linear_class_exactness_per_guard_config()
    test_linear_class_exhaustive_small_alphabet()
    test_guard_entry_points_match_original_across_the_threshold()
    test_guards_stay_live_when_the_lib_module_is_missing()
    test_huge_commit_commands_still_get_their_verdict()
    test_commit_hygiene_cpu_growth()
    test_memory_orphan_cpu_growth()
    test_real_guards_finish_in_bounded_wall_time()
    if _failures:
        print("\n%d FAILURE(S):\n  %s" % (len(_failures), "\n  ".join(_failures)))
        sys.exit(1)
    print("\nALL linear-shlex-commit-guards tests passed.")
    sys.exit(0)
