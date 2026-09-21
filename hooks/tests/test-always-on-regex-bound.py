"""Time-bound + exactness tests for the two ALWAYS-ON quadratic patterns found in the
PR #234 review follow-up (2026-09-20):

  1. tool_call_paths.GIT_MUTATE_RE   (\\bgit\\b[^|;&\\n]*?\\b(verb)\\b) -- retried at every
     `git` and each attempt rescans the segment: O(n^2). Feeds shell_may_write(),
     which config-write-guard.py and workbook-write-guard.py call on every Bash call.
  2. the `<<WORD ... \\n WORD` heredoc-body stripper duplicated in config-write-guard.py
     and lint-config-guard.py -- every UNCLOSED `<<WORD` marker rescans to end of
     input: O(markers * n).

These run on EVERY Bash call regardless of hooks/lib health, and the dispatcher runs
guards in-process with no per-guard timeout, so one slow pattern stalls every guard
behind it. The fix must be EXACT (no decision changes), so this file pins both halves:

  * TIME  -- time.thread_time (CPU of THIS thread: robust to a loaded machine) on the
             real compiled patterns / real guard functions, plus a process-boundary
             wall-clock bound through each real guard.
  * EXACT -- seeded differential fuzz of the shipped implementation against the RAW
             ORIGINAL pattern (copied verbatim below, never imported from the code
             under test) on inputs small enough for the raw pattern to finish.

Run: python test-always-on-regex-bound.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

import tool_call_paths as tcp  # noqa: E402

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


CWG = _load("config-write-guard.py", "cwg_under_test")
LCG = _load("lint-config-guard.py", "lcg_under_test")

# ---- ORACLES: the ORIGINAL patterns, verbatim from origin/main 524cc14. ----------
RAW_GIT_MUTATE_RE = re.compile(
    r"\bgit\b[^|;&\n]*?\b(checkout|restore|reset|apply|stash|merge|rebase|"
    r"cherry-pick|clean|revert|pull|switch)\b", re.IGNORECASE)

RAW_HEREDOC_RE = re.compile(
    r"<<-?\s*['\"]?([a-zA-Z0-9_]+)['\"]?[^\n]*\n"
    r".*?\n"
    r"[ \t]*\1(?=[ \t\r\n]|$)",
    re.DOTALL,
)


def raw_strip_heredoc_bodies(text):
    def _blank(m):
        opening_line = m.group(0).split("\n", 1)[0] + "\n"
        return opening_line + " <heredoc-body> \n" + m.group(1)
    return RAW_HEREDOC_RE.sub(_blank, text)


def cpu(fn, *args):
    t0 = time.thread_time()
    out = fn(*args)
    return time.thread_time() - t0, out


# ------------------------------------------------------------------ time bounds
# Measured on origin/main 524cc14 (this machine, 2026-09-20/21; spread is load):
# GIT_MUTATE_RE at 16KB 1.2-3.9s, 32KB 11-15s, 64KB 46-60s; heredoc unclosed-marker
# scan 2000 markers/14KB ~1s, 5000/37KB ~7s, 8000/63KB 15-20s. The fixed code is a few
# milliseconds at 64KB, so 0.5s is ~100x its cost (load-proof). Discrimination comes
# from the LARGER shapes (64KB git chains, 5000+ markers, the long-word shape, all
# 10-60s on unfixed code); the smallest shapes (16KB git, 2000 markers) are only ~2x
# above the bound on unfixed code and exist as cheap regression canaries, not as the
# proof. Reverting either fix, or loosening the bound below ~10s, fails the suite.
CPU_BOUND = 0.5

GIT_SHAPES = {
    "git-chain-16KB": "git" + " git" * 4000 + " x",
    "git-chain-64KB": "git" + " git" * 16000 + " x",
    "git-flag-chain-64KB": "git" + " -c git=git" * 5800 + " x",
    "git-dash-chain-64KB": "git" + " --git" * 12800 + " x",
    "git-many-segments-64KB": "git x;" * 10800,
    "git-no-verb-then-late-verb-64KB": "git " * 16000 + "; git checkout",
}


def test_git_mutate_re_cpu_bound():
    for name, s in GIT_SHAPES.items():
        dt, _ = cpu(tcp.GIT_MUTATE_RE.search, s)
        check("GIT_MUTATE_RE cpu bound (%s, %d chars): %.3fs" % (name, len(s), dt),
              dt < CPU_BOUND)


def test_shell_may_write_cpu_bound():
    # The real entry point both write-guards call. Whole function, not just the
    # pattern: another quadratic pattern behind GIT_MUTATE_RE would surface here.
    for name, s in GIT_SHAPES.items():
        dt, _ = cpu(tcp.shell_may_write, s)
        check("shell_may_write cpu bound (%s, %d chars): %.3fs" % (name, len(s), dt),
              dt < CPU_BOUND)


def _unclosed_distinct(n):
    return "".join("<<A%d\n" % i for i in range(n))


def _unclosed_same(n):
    return "<<EOF\n" * n


def _unclosed_one_line(n):
    return " ".join("<<A%d" % i for i in range(n))


def _closers_for_other_words(n):
    # openers never match a closer (closers are other words), lots of closer lines
    return "".join("<<A%d\nbody\nB%d\n" % (i, i) for i in range(n))


def _long_word_many_closer_lengths():
    # Adversary for a prefix-scanning implementation: each opener has a long word
    # and the input holds closers of many distinct lengths, none equal to a prefix.
    opener_word = "Z" * 300
    parts = ["<<%s\n" % opener_word for _ in range(120)]
    parts += ["\n%s\n" % ("Y" * k) for k in range(1, 200)]
    return "".join(parts)


HEREDOC_SHAPES = {
    "unclosed-distinct-2000": _unclosed_distinct(2000),
    "unclosed-distinct-5000": _unclosed_distinct(5000),
    "unclosed-same-word-5000": _unclosed_same(5000),
    "unclosed-one-line-10000": _unclosed_one_line(10000),
    "closers-are-other-words-3000": _closers_for_other_words(3000),
    "long-word-many-closer-lengths": _long_word_many_closer_lengths(),
}

HEREDOC_FUNCS = {
    "config-write-guard": CWG._strip_heredoc_bodies,
    "lint-config-guard": LCG._strip_heredoc_bodies,
}


def test_heredoc_strip_cpu_bound():
    for gname, fn in HEREDOC_FUNCS.items():
        for name, s in HEREDOC_SHAPES.items():
            dt, _ = cpu(fn, s)
            check("%s _strip_heredoc_bodies cpu bound (%s, %d chars): %.3fs"
                  % (gname, name, len(s), dt), dt < CPU_BOUND)


# ------------------------------------------------------------------- exactness
GIT_TOKENS = [
    "git", "git", "git", "GIT", "Git", "gitx", "xgit", "git-", "-git", "git.",
    "checkout", "restore", "reset", "apply", "stash", "merge", "rebase",
    "cherry-pick", "cherry", "pick", "clean", "revert", "pull", "switch",
    "CHECKOUT", "Reset", "checkoutx", "xcheckout", "reset_", "_reset",
    " ", " ", " ", "  ", "\t", "\n", "\r", ";", "&", "|", "&&", "||", "-", "/",
    ".", "\"", "'", "x", "-C", "~/.claude", "\u017f", "\u212a", "\u00e9", "1",
    "restore-", "-restore", "ta\u0308",
]


def _rand_from(rng, toks, lo, hi):
    return "".join(rng.choice(toks) for _ in range(rng.randint(lo, hi)))


def test_git_mutate_exactness_handwritten():
    cases = [
        "git checkout main", "git  checkout", "GIT CHECKOUT", "git-checkout",
        "git\ncheckout", "git|checkout", "git;checkout", "git&checkout",
        "git x checkout", "git x; checkout", "git x\n checkout", "gitcheckout",
        "xgit checkout", "git checkoutx", "git xcheckout", "git cherry-pick",
        "git cherry", "git pick", "git -C ~/.claude checkout main -- hooks/",
        "git log", "git status; git reset --hard", "echo git; checkout",
        "git", "", "checkout git", "git\rcheckout", "git\tcheckout",
        "git.checkout", "git/checkout", "git_checkout", "git 9checkout",
        "git \u017fwitch", "git \u212ait", "git reset_", "git _reset",
        "git " * 50 + "restore", "git " * 50 + "restorex",
    ]
    for c in cases:
        want = bool(RAW_GIT_MUTATE_RE.search(c))
        got = bool(tcp.GIT_MUTATE_RE.search(c))
        check("GIT_MUTATE_RE equals raw on %s" % ascii(c[:40]), want == got,
              "raw=%s new=%s" % (want, got))


def _git_template(rng):
    """Structured case: git, args, then (maybe) a verb, with separators/word-boundary
    perturbations -- raises the positive rate far above what free token soup gives."""
    def seg():
        return _rand_from(rng, GIT_TOKENS, 0, 5)
    verb = rng.choice(["checkout", "restore", "reset", "apply", "stash", "merge",
                       "rebase", "cherry-pick", "clean", "revert", "pull",
                       "switch", "CHECKOUT", "checkoutx", "xreset", "log"])
    sep = rng.choice([" ", " ", "  ", "\t", "-", "/", ";", "&", "|", "\n", "\r",
                      " -C x ", " -- ", "_", "."])
    return (seg() + rng.choice(["git", "GIT", "gitx", "xgit"]) + sep + seg()
            + rng.choice(["", " ", ";", "\n", " git "]) + seg() + verb
            + rng.choice(["", " ", "x", "_", "-", ";"]) + seg())


def test_git_mutate_exactness_fuzz():
    rng = random.Random(20260920)
    bad = []
    hits = 0
    n = 80000
    for i in range(n):
        s = _rand_from(rng, GIT_TOKENS, 0, 14) if i % 2 else _git_template(rng)
        want = bool(RAW_GIT_MUTATE_RE.search(s))
        hits += want
        if want != bool(tcp.GIT_MUTATE_RE.search(s)):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("GIT_MUTATE_RE == raw pattern on %d seeded fuzz inputs (%d positive)"
          % (n, hits), not bad, ascii(bad[:3]))
    # the fuzz must exercise both outcomes plentifully or it proves nothing
    check("GIT_MUTATE fuzz is not vacuous (>=5000 positives and >=20000 negatives)",
          hits >= 5000 and n - hits >= 20000, "positives=%d/%d" % (hits, n))


HD_TOKENS = [
    "<<", "<<", "<<-", "<<<", "<", "-", "EOF", "EOF", "EOFX", "EO", "E", "eof",
    "A", "AB", "B", "x", "_", "9", "'", "\"", " ", " ", "\t", "\r", "\n", "\n",
    "\n", "\n\n", ";", ">", "> f.txt", "cat ", "body", "\r\n", "\u2028", "\x0b",
    "\u00a0", "\u00e9", "-", "EOF\n", "\nEOF", "\nEOF\n", " EOF", "\tEOF",
]


def test_heredoc_strip_exactness_handwritten():
    cases = [
        "cat <<EOF > f\nbody mentions hooks/x\nEOF\n",
        "cat <<'EOF'\nbody\nEOF",
        "cat <<\"EOF\"\nbody\nEOF\n",
        "cat <<-EOF\n\tbody\n\tEOF\n",
        "cat <<EOFX\nbody\nEOF\n",            # group-1 prefix backtracking quirk
        "cat <<EOF\nEOF\n",                    # empty body without blank line
        "cat <<EOF\n\nEOF\n",
        "cat <<EOF\nbody\nEOF;\n",             # closer followed by ; -> no close
        "cat <<EOF\nbody\nEOF \n",
        "cat <<EOF\nbody\r\nEOF\r\n",
        "cat <<\nEOF\nbody\nEOF\n",            # \s* crossing a newline
        "cat <<   \n\n  EOF\nbody\nEOF\n",
        "a <<A\nx\nA\nb <<B\ny\nB\nc",
        "a <<A\nx\nA\nb <<A\ny\nA\nc",
        "a <<A\n<<B\nx\nB\nA\n",
        "cat <<<EOF\nx\nEOF\n",
        "cat <<< 'here string'\n",
        "<<A\n<<A\n<<A\nA",
        "<<AB\nx\nA\n<<A\ny\nAB\n",
        "<<A\nx\nAB\nA",
        "<<EOF\nbody\n  EOF",
        "<<EOF\nbody\n\tEOF\n",
        "no heredoc at all", "", "<<", "<<\n", "<<EOF", "<<EOF\n",
        "x <<E\n" * 6 + "E\n",
        "<<E\n" + "\nE\n" * 3,
        "<<a1\nbody\na1\n<<a2 more args here\nbody\na2\ntail",
        "cat <<EOF\nbody\nEOF\nEOF\n",
        "cat <<E\nx\nE\n<<E\ny\nE",
        "<<\u00e9\nx\n\u00e9\n",
        "<<E\u00e9\nx\nE\n",
    ]
    for c in cases:
        want = raw_strip_heredoc_bodies(c)
        for gname, fn in HEREDOC_FUNCS.items():
            got = fn(c)
            check("%s strip equals raw on %s" % (gname, ascii(c[:36])), want == got,
                  "raw=%s new=%s" % (ascii(want), ascii(got)))
        check("tcp.strip_heredoc_bodies equals raw on %s" % ascii(c[:36]),
              want == tcp.strip_heredoc_bodies(c))


def _heredoc_template(rng):
    """Structured heredoc: opener (dash/ws/quote/word variants), rest-of-line, body,
    then a closer that is exact / prefix / extension / indented / mis-terminated."""
    word = rng.choice(["EOF", "EOF", "E", "A", "AB", "EOFX", "a1", "_", "9"])
    closer = rng.choice([word, word, word, word[:-1] or "Q", word + "X", word.lower(),
                         " " + word, "\t" + word, word + ";", word + " ", word + "\r"])
    opener = ("<<" + rng.choice(["", "-", "", " ", "\n", "  \n ", "\u2028"])
              + rng.choice(["", "'", "\""]) + word + rng.choice(["", "'", "\""]))
    return (_rand_from(rng, HD_TOKENS, 0, 3) + opener
            + rng.choice(["", " > f", " x y", ";"]) + rng.choice(["\n", "\r\n", "\n\n"])
            + rng.choice(["", "body", "\n", "a\nb", "<<E\n"]) + rng.choice(["\n", "\n\n"])
            + closer + rng.choice(["", "\n", " ", "\r\n", "x",
                                   "\n" + _rand_from(rng, HD_TOKENS, 0, 6)]))


def test_heredoc_strip_exactness_fuzz():
    rng = random.Random(20260921)
    n = 60000
    bad = {}
    changed = 0
    for i in range(n):
        s = _rand_from(rng, HD_TOKENS, 0, 16) if i % 2 else _heredoc_template(rng)
        want = raw_strip_heredoc_bodies(s)
        changed += (want != s)
        for gname, fn in HEREDOC_FUNCS.items():
            if fn(s) != want and gname not in bad:
                bad[gname] = s
    check("heredoc strip == raw pattern on %d seeded fuzz inputs (%d rewritten)"
          % (n, changed), not bad, ascii(bad))
    check("heredoc fuzz is not vacuous (>=10000 rewritten and >=10000 untouched)",
          changed >= 10000 and n - changed >= 10000, "rewritten=%d/%d" % (changed, n))


# ------------------------------------------------ process-boundary wall-clock
# Wall clock through the REAL guards. Loose on purpose (loaded machine, 6 sessions):
# the linear implementation finishes in ~0.5s including interpreter start, the raw
# patterns take 15-60s on these payloads.
WALL_BOUND = 8.0


def _run_guard(hook, payload, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    t0 = time.monotonic()
    proc = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, hook)],
                          input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, timeout=120)
    return (time.monotonic() - t0, proc.returncode,
            proc.stderr.decode("utf-8", "replace"))


def _bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd},
            "session_id": "test-session-0123456789abcdef"}


def test_guards_finish_in_bounded_wall_time():
    sess = tempfile.mkdtemp(prefix="aorb-sess-")
    root = tempfile.mkdtemp(prefix="aorb-root-")
    log = os.path.join(tempfile.mkdtemp(prefix="aorb-log-"), "chip-claims.log")
    base_env = {"ORA_OVERRIDE_SESSIONS_DIR": sess}
    wb = "Master Excel Template Company Wide -- Oxford.xlsx"
    git_cmd = "git" + " git" * 16000 + " x"         # 64KB, raw 46-60s (32KB was ~9s: too close to the bound)
    # A redirect first, so shell_may_write() is True and lint-config-guard actually
    # reaches its heredoc stripper (it only classifies write-shaped commands).
    hd_cmd = "echo x > out.txt" + chr(10) + _unclosed_distinct(8000)   # ~62KB, raw ~15-20s
    rigs = [
        ("config-write-guard.py", "git-chain", git_cmd,
         dict(base_env, ORA_CONFIG_GUARD_ROOT=root, ORA_CHIP_CLAIMS_LOG=log)),
        ("config-write-guard.py", "unclosed-heredocs", hd_cmd,
         dict(base_env, ORA_CONFIG_GUARD_ROOT=root, ORA_CHIP_CLAIMS_LOG=log)),
        ("lint-config-guard.py", "unclosed-heredocs", hd_cmd,
         dict(base_env, ORA_LINT_CONFIG_GUARD_ROOT=root)),
        # workbook guard only reaches shell_may_write when the command NAMES the
        # workbook, so name it.
        ("workbook-write-guard.py", "git-chain", git_cmd + " " + wb,
         dict(base_env, ORA_WORKBOOK_GUARD_NAME=wb)),
    ]
    for hook, shape, cmd, env in rigs:
        dt, rc, err = _run_guard(hook, _bash(cmd), env)
        check("%s wall-clock bound (%s, %d chars): %.2fs rc=%s"
              % (hook, shape, len(cmd), dt, rc), dt < WALL_BOUND, err[:160])


if __name__ == "__main__":
    test_git_mutate_re_cpu_bound()
    test_shell_may_write_cpu_bound()
    test_heredoc_strip_cpu_bound()
    test_git_mutate_exactness_handwritten()
    test_git_mutate_exactness_fuzz()
    test_heredoc_strip_exactness_handwritten()
    test_heredoc_strip_exactness_fuzz()
    test_guards_finish_in_bounded_wall_time()
    if _failures:
        print("\n%d FAILURE(S):\n  %s" % (len(_failures), "\n  ".join(_failures)))
        sys.exit(1)
    print("\nALL always-on-regex-bound tests passed.")
    sys.exit(0)
