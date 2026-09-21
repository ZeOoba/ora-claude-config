"""Time-bound + exactness tests for the SECOND batch of always-on quadratics found by the
independent review of test-always-on-regex-bound.py's change (2026-09-21).

Every Bash call runs shell_may_write() (config-write-guard, workbook-write-guard,
lint-config-guard, ora-autonomy-gate ...) and config-write-guard's recursive_delete()
and token layer. The dispatcher runs guards in-process with no per-guard timeout, so one
slow pattern stalls every guard behind it. Shapes fixed here (all measured O(n^2)):

  1. tool_call_paths._FD_DUP_RE / _NULL_REDIRECT_RE / _RD_FD_DUP_RE -- a bare leading
     `\\d*` retried from every offset of a digit run.  `echo ` + "1"*64KB ~ 25s.
  2. tool_call_paths._OPEN_SAFE_ARGS_RE -- lazy `[^,]*?` next to `\\s*`: `open(a` +
     spaces + `b)`.  32KB ~ 10s.
  3. tool_call_paths._RECURSIVE_FLAG_RE / _FORCE_FLAG_RE -- two adjacent stars over one
     class: `rm -rrrr...x`.  40KB ~ 13s.
  4. tool_call_paths.recursive_delete's per-`rm` rescans: `rm x rm x ... -rf y` (k rm's
     cost O(k*n), 24KB ~ 20s) and the O(n) recount per stripped `)`/`}` (`rm -rf )))..`)
     and the list-membership dedupe of distinct operands.
  5. config-write-guard.py / lint-config-guard.py `_blank_exempt` -- `\\S*marker\\S*`
     re-scanned to the token end from every offset of a token that lacks the marker:
     `echo <one 16KB token> > out.txt` ~10s in config-write-guard.

  6. config-write-guard.py `_INTERIOR_DOT_RE` -- two stars over one class: `echo x` +
     "."*N + ` > out.txt`.  40KB ~ 15s.
  7. config-write-guard.py's stdlib shlex tokenizer -- `self.token += ch` is a full copy
     per char, so ONE long token is O(len^2) memcpy (512KB: 6.3s per pass, 3 passes).

The fixes are EXACT (linear rewrites) except recursive_delete's per-segment rm bound,
which fails toward BLOCK (see _RD_MAX_CANDIDATES_PER_SEGMENT). This file pins:

  * TIME  -- time.thread_time (CPU of THIS thread: robust to a loaded machine) on the real
             functions, on payloads sized so the UNFIXED code needs >= ~10s, plus a
             process-boundary wall-clock bound through each real guard.
  * EXACT -- seeded differential fuzz of the shipped code against the RAW ORIGINALS
             (copied verbatim below, never imported from the code under test).
  * SAFE  -- a huge command that really targets a governance path is still blocked; the
             rm bound blocks (never allows) past its limit.

Run: python test-always-on-linear-redirect-exempt.py
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


CWG = _load("config-write-guard.py", "cwg_linear_under_test")
LCG = _load("lint-config-guard.py", "lcg_linear_under_test")

# ---- ORACLES: the ORIGINAL code, verbatim from origin/main 07b879b. -------------
RAW_FD_DUP_RE = re.compile(r"\d*>&\d*|&>{1,2}")
RAW_NULL_REDIRECT_RE = re.compile(r"\d*>\s*(?:/dev/null|nul)\b", re.IGNORECASE)
RAW_RD_FD_DUP_RE = re.compile(r"\d*[<>]&\d*-?|&>{1,2}")
RAW_OPEN_SAFE_ARGS_RE = re.compile(r"^\s*[^,]*?\s*(?:,\s*['\"]r[bt]?['\"]\s*)?$")
_RM_SHORT_OPTS = "rfidv"
RAW_RECURSIVE_FLAG_RE = re.compile(
    r"(?<![\w-])--recursive(?![\w-])"
    r"|(?<![\w-])-[%s]*r[%s]*(?![\w-])" % (_RM_SHORT_OPTS, _RM_SHORT_OPTS),
    re.IGNORECASE)
RAW_FORCE_FLAG_RE = re.compile(
    r"(?<![\w-])--force(?![\w-])"
    r"|(?<![\w-])-[%s]*f[%s]*(?![\w-])" % (_RM_SHORT_OPTS, _RM_SHORT_OPTS),
    re.IGNORECASE)


def raw_open_may_write(lowered):
    if "open(" not in lowered:
        return False
    calls = list(tcp._OPEN_CALL_RE.finditer(lowered))
    if len(calls) != lowered.count("open("):
        return True
    return any(not RAW_OPEN_SAFE_ARGS_RE.match(m.group(1)) for m in calls)


def raw_delete_targets(rest):
    pieces, spans = [], []
    for m in tcp._ARG_TOKEN_RE.finditer(rest):
        token = m.group(0)
        if pieces and spans[-1] == m.start():
            pieces[-1] += token
        else:
            pieces.append(token)
            spans.append(0)
        spans[-1] = m.end()

    targets = []
    skip_next = False
    for token in pieces:
        if skip_next:
            skip_next = False
            continue
        if tcp._REDIRECT_TOKEN_RE.match(token):
            if tcp._BARE_REDIRECT_RE.match(token):
                skip_next = True
            continue
        if token.startswith("-"):
            continue
        token = token.replace("\"", "").replace("'", "")
        for close, open_ in ((")", "("), ("}", "{")):
            while (token.endswith(close)
                   and token.count(close) > token.count(open_)):
                token = token[:-1]
        while token.endswith("`") and token.count("`") % 2 == 1:
            token = token[:-1]
        if token:
            targets.append(token)
    return targets


def raw_recursive_delete(command):
    if not isinstance(command, str) or not command:
        return None
    text = tcp.normalize_text(command)
    text = tcp._IFS_TOKEN_RE.sub(" ", text)
    text = tcp._SPACED_FD_DUP_RE.sub(r"\1&", text)
    text = RAW_RD_FD_DUP_RE.sub(" ", text)
    targets, force = [], False
    hit = False
    for segment in tcp._SEGMENT_SPLIT_RE.split(text):
        for m in tcp._RM_VERB_RE.finditer(segment):
            rest = segment[m.end():]
            if not RAW_RECURSIVE_FLAG_RE.search(rest):
                continue
            if not tcp._in_command_position(segment[:m.start()]):
                continue
            hit = True
            force = force or bool(RAW_FORCE_FLAG_RE.search(rest))
            for t in raw_delete_targets(rest):
                if t not in targets:
                    targets.append(t)
    if not hit:
        return None
    return tcp.RecursiveDelete(text, True, force, targets)


def raw_blank_exempt_cwg(text, exempt_markers):
    for marker in exempt_markers:
        text = re.sub(r"\S*" + re.escape(marker) + r"\S*", " <exempt> ", text)
    return text


def raw_blank_exempt_lcg(text, marker):
    return re.sub(r"\S*" + re.escape(marker) + r"\S*", " <exempt> ", text)


RAW_INTERIOR_DOT_RE = re.compile(r"(?<=[^\s/.\\])[.\s]*\.[.\s]*(?=[/\\])")


RAW_ABS_PATH_TOKEN_RE = re.compile(r"[a-z]:/[^\s\"'<>|;&`$()]*")
RAW_ATTACHED_PATH_RE = re.compile(r"[\w.:$~\\/-]*[\\/]$")
RAW_TAR_EXTRACT_RE = re.compile(r"^-[A-Za-z]*x[A-Za-z]*$")


def raw_marker_matches(text, marker):
    """CWG._marker_matches verbatim, with the per-occurrence finditer restart."""
    start = 0
    while True:
        idx = text.find(marker, start)
        if idx == -1:
            return False
        end = idx + len(marker)
        start = idx + 1
        if not CWG._boundary_ok(text, idx, end):
            continue
        tok = None
        for m in RAW_ABS_PATH_TOKEN_RE.finditer(text):
            if m.start() <= idx < m.end():
                tok = m.group(0)
                break
        if tok is not None:
            continue
        return True


def raw_tokenize(text, escape):
    import shlex
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        if not escape:
            lex.escape = ""
        return list(lex)
    except Exception:
        return None


def cpu(fn, *args):
    t0 = time.thread_time()
    out = fn(*args)
    return time.thread_time() - t0, out


# ------------------------------------------------------------------ time bounds
# Measured on origin/main 07b879b (this machine, 2026-09-21; spread is load): see the
# per-shape numbers in the module docstring. The fixed code is a few milliseconds on
# every payload below, so 0.5s is ~100x its cost (load-proof); every payload is sized so
# the unfixed code needs >= ~10s (or, where noted, >= 2s), i.e. >= 4x the bound.
CPU_BOUND = 0.5


def _digits(n):
    return "echo " + "1" * n


def _open_spaces(n):
    return "open(a" + " " * n + "b)"


def _open_spaces_comma(n):
    return "open(a" + " " * n + ",'r' x)"


def _rm_flag_run(n):
    return "rm -" + "r" * n + "x"


def _rm_force_run(n):
    return "rm -r -" + "f" * n + "x"


def _rm_many_then_flag(n):
    return "rm x " * (n // 5) + " -rf y"


def _rm_hit_many(n):
    return "find . " + "-exec rm -rf {} + " * (n // 19)


def _rm_close_run(n):
    return "rm -rf " + ")" * n


def _rm_brace_run(n):
    return "rm -rf " + "}" * n


def _rm_distinct_targets(n):
    return "rm -rf " + " ".join("a%d" % i for i in range(n // 7))


def _long_token_redirect(n):
    return "echo " + "a" * n + " > out.txt"


TCP_CPU_CASES = [
    # (label, function, payload)
    ("FD_DUP_RE.sub digits 64KB", lambda s: tcp._FD_DUP_RE.sub(" ", s), _digits(65536)),
    ("NULL_REDIRECT_RE.sub digits 64KB",
     lambda s: tcp._NULL_REDIRECT_RE.sub(" ", s), _digits(65536)),
    ("RD_FD_DUP_RE.sub digits 64KB",
     lambda s: tcp._RD_FD_DUP_RE.sub(" ", s), _digits(65536)),
    ("shell_may_write digits 64KB", tcp.shell_may_write, _digits(65536)),
    ("shell_may_write digits-then-gt 64KB", tcp.shell_may_write, "1" * 65536 + ">"),
    ("recursive_delete digits 64KB", tcp.recursive_delete, _digits(65536)),
    ("shell_may_write open(spaces) 32KB", tcp.shell_may_write, _open_spaces(32768)),
    ("shell_may_write open(spaces,mode) 32KB", tcp.shell_may_write,
     _open_spaces_comma(32768)),
    ("recursive_delete rm -rrr..x 40KB", tcp.recursive_delete, _rm_flag_run(40000)),
    ("recursive_delete rm -r -fff..x 40KB", tcp.recursive_delete, _rm_force_run(40000)),
    ("recursive_delete rm x rm x .. -rf 24KB", tcp.recursive_delete,
     _rm_many_then_flag(24000)),
    ("recursive_delete -exec rm -rf {} + x N 24KB", tcp.recursive_delete,
     _rm_hit_many(24000)),
    ("recursive_delete rm -rf ))).. 128KB", tcp.recursive_delete, _rm_close_run(131072)),
    ("recursive_delete rm -rf }}}.. 128KB", tcp.recursive_delete, _rm_brace_run(131072)),
    ("recursive_delete 28K distinct operands (200KB)", tcp.recursive_delete,
     _rm_distinct_targets(200000)),
]


def test_tcp_cpu_bounds():
    for label, fn, payload in TCP_CPU_CASES:
        dt, _ = cpu(fn, payload)
        check("cpu bound (%s): %.3fs" % (label, dt), dt < CPU_BOUND)


def test_interior_dot_and_shlex_cpu_bounds():
    dt, _ = cpu(CWG._strip_interior_component_dots, "x" + "." * 40000)
    check("config-write-guard _strip_interior_component_dots cpu bound (x + 40000 dots): "
          "%.3fs" % dt, dt < CPU_BOUND)
    dt, _ = cpu(CWG._strip_interior_component_dots, "x" + ". " * 20000)
    check("config-write-guard _strip_interior_component_dots cpu bound (x + 20000 '. '): "
          "%.3fs" % dt, dt < CPU_BOUND)
    # shlex costs ~1us per char even when linear, so an absolute bound tight enough to
    # catch the quadratic flakes under load. Use the GROWTH instead: 4x the input must
    # cost < 7x (linear ~4x, quadratic ~16x; stdlib shlex measured 6.3s at 512KB), plus
    # a loose absolute cap.
    shapes = (("one long token", lambda n: "echo " + "a" * n + " > out.txt"),
              ("glued quoted fragments",
               lambda n: "echo " + "'a'\"b\"" * (n // 5) + " > out.txt"))
    for label, mk in shapes:
        small, big = mk(131072), mk(524288)
        dt_s, toks = cpu(CWG._tokenize, small, True)
        dt_b, toks_b = cpu(CWG._tokenize, big, True)
        check("config-write-guard _tokenize scales linearly (%s): 128KB %.3fs, 512KB %.3fs"
              % (label, dt_s, dt_b),
              toks is not None and toks_b is not None
              and dt_b < 7 * dt_s + 0.1 and dt_b < 3.0)
    dt_s, _ = cpu(CWG._shlex_passes, "echo " + "a" * 131072 + " > out.txt")
    dt_b, _ = cpu(CWG._shlex_passes, "echo " + "a" * 524288 + " > out.txt")
    check("config-write-guard _shlex_passes scales linearly (3 passes): 128KB %.3fs, "
          "512KB %.3fs" % (dt_s, dt_b), dt_b < 7 * dt_s + 0.1 and dt_b < 6.0)


def test_review_round_cpu_bounds():
    # M1: `_in_command_position` -> _ATTACHED_PATH_RE on a long word run before rm -r
    for label, cmd in (("word run then rm -r 32KB", "a" * 32768 + " rm -r x"),
                       ("16 candidates each behind a 2KB word run",
                        ("rm -r " + "a" * 2000 + " ") * 16),
                       ("word run of path chars then rm -r 32KB",
                        "a.b:c~d" * 4600 + " rm -r x")):
        dt, _ = cpu(tcp.recursive_delete, cmd)
        check("recursive_delete cpu bound (%s): %.3fs" % (label, dt), dt < CPU_BOUND)
    # M2: tar -xxxx...x! (two stars over one class)
    dt, _ = cpu(CWG.classify_shell, "tar -" + "x" * 32768 + "! f", True)
    check("config-write-guard classify_shell cpu bound (tar -xxx..x! 32KB): %.3fs" % dt,
          dt < CPU_BOUND)
    # M3: a marker that recurs inside drive-qualified tokens
    dt, _ = cpu(CWG._marker_matches, "c:/.claude/hooks " * 4000, ".claude/hooks")
    check("config-write-guard _marker_matches cpu bound (64KB of marker-in-abs-token): "
          "%.3fs" % dt, dt < CPU_BOUND)
    # (classify_shell end to end is dominated by a linear realpath cost per drive token,
    # so a growth ratio there cannot tell fixed from reverted; the direct _marker_matches
    # bound above is the discriminating check for this shape.)
    dt, _ = cpu(tcp._delete_targets, "'a'" * 170000)
    check("_delete_targets cpu bound (170000 abutting quoted fragments, 510KB): %.3fs"
          % dt, dt < CPU_BOUND)
    # m2: blank_exempt with the marker PRESENT in another token, so the `marker not in
    # text` early-out cannot hide a reverted anchored pattern.
    exempt, _gov, _claim = CWG._shell_marker_sets()
    text = "a" * 32768 + " x" + exempt[0] + "/y"
    dt, _ = cpu(CWG._blank_exempt, text, exempt)
    check("config-write-guard _blank_exempt cpu bound (32KB token + a marker elsewhere): "
          "%.3fs" % dt, dt < CPU_BOUND)
    dt, _ = cpu(LCG._blank_exempt, "a" * 65536 + " x/.claude/worktrees/y",
                ".claude/worktrees")
    check("lint-config-guard _blank_exempt cpu bound (64KB token + a marker elsewhere): "
          "%.3fs" % dt, dt < CPU_BOUND)


def test_blank_exempt_cpu_bounds():
    exempt, _gov, _claim = CWG._shell_marker_sets()
    blob = "a" * 32768
    dt, _ = cpu(CWG._blank_exempt, blob, exempt)
    check("config-write-guard _blank_exempt cpu bound (32KB token, %d markers): %.3fs"
          % (len(exempt), dt), dt < CPU_BOUND)
    dt, _ = cpu(LCG._blank_exempt, "a" * 65536, ".claude/worktrees")
    check("lint-config-guard _blank_exempt cpu bound (64KB token): %.3fs" % dt,
          dt < CPU_BOUND)
    cmd = _long_token_redirect(24576)
    dt, _ = cpu(CWG.classify_shell, cmd, True)
    check("config-write-guard classify_shell cpu bound (24KB token > out.txt): %.3fs"
          % dt, dt < CPU_BOUND)
    dt, _ = cpu(LCG.classify_shell_text, _long_token_redirect(65536))
    check("lint-config-guard classify_shell_text cpu bound (64KB token): %.3fs" % dt,
          dt < CPU_BOUND)


# ------------------------------------------------------------------- exactness
def _rand_from(rng, toks, lo, hi):
    return "".join(rng.choice(toks) for _ in range(rng.randint(lo, hi)))


FD_TOKENS = [
    "1", "2", "12", "007", "9", "\u0663", "\u0664", ">", ">", ">&", ">&", "&>", "&>>",
    "&", "<", "<&", "-", " ", " ", "\t", "\n", "/dev/null", "nul", "NUL", "Nul", "nulx",
    "/dev/nullx", "_nul", "-", "a", ">>", "2>&1", "1>&2", "0<&1", "&&", "|", ";", "x",
    "\u0130", "\u017f",
]


def _spans(pat, s):
    return [m.span() for m in pat.finditer(s)]


def _fd_pair_case(s, raw, new, label, bad):
    if (raw.sub(" ", s) != new.sub(" ", s) or _spans(raw, s) != _spans(new, s)
            or (raw.search(s) is None) != (new.search(s) is None)):
        bad.setdefault(label, s)


def test_fd_patterns_handwritten():
    cases = ["1>&23>&4", "12>&3", ">&", "&>", "&>>", "&&>", "1>&2>&3", "2>/dev/null",
             "1 > nul", "12>/dev/null 34>nul", "5>\n/dev/null", "1>NULx", "1>nul9",
             "99>&1-", "0<&1", "a1>&2", "1a>&2", "\u066312>&1", "12\u0663>&1", ">&1>&2>&3",
             "&>1>&2", "x1>&2 y", "123456789>&", "123456789 >&", ">nul>nul", "1>nul2>nul",
             "1>&2\n3>&4", "", "111", ">"]
    bad = {}
    for s in cases:
        for raw, new, label in ((RAW_FD_DUP_RE, tcp._FD_DUP_RE, "FD_DUP"),
                                (RAW_NULL_REDIRECT_RE, tcp._NULL_REDIRECT_RE, "NULL"),
                                (RAW_RD_FD_DUP_RE, tcp._RD_FD_DUP_RE, "RD_FD")):
            _fd_pair_case(s, raw, new, label, bad)
    check("fd-dup/null-redirect patterns equal raw on %d handwritten cases" % len(cases),
          not bad, ascii(bad))
    # the naive lookbehind fix `(?<!\d)\d*` is NOT exact -- pin why this one is not it.
    naive = re.compile(r"(?<!\d)\d*>&\d*|&>{1,2}")
    check("naive `(?<!\\d)\\d*` anchoring would differ on 1>&23>&4 (the reason for the "
          "optional-group form)",
          naive.sub(" ", "1>&23>&4") != RAW_FD_DUP_RE.sub(" ", "1>&23>&4"))


def test_fd_patterns_fuzz():
    rng = random.Random(20260921)
    n = 120000
    bad = {}
    hits = 0
    for _ in range(n):
        s = _rand_from(rng, FD_TOKENS, 0, 14)
        hits += bool(RAW_FD_DUP_RE.search(s)) + bool(RAW_NULL_REDIRECT_RE.search(s))
        for raw, new, label in ((RAW_FD_DUP_RE, tcp._FD_DUP_RE, "FD_DUP"),
                                (RAW_NULL_REDIRECT_RE, tcp._NULL_REDIRECT_RE, "NULL"),
                                (RAW_RD_FD_DUP_RE, tcp._RD_FD_DUP_RE, "RD_FD")):
            _fd_pair_case(s, raw, new, label, bad)
    check("fd-dup/null-redirect/RD patterns == raw (sub, finditer spans, search) on %d "
          "seeded fuzz inputs" % n, not bad, ascii(bad))
    check("fd fuzz is not vacuous (>=30000 positives)", hits >= 30000, "hits=%d" % hits)


def test_shell_may_write_end_to_end_unchanged():
    # full-function equality on redirect-heavy inputs, against a raw-pattern rebuild of
    # the function (same body, raw patterns swapped in).
    def raw_smw(command):
        lowered = tcp.normalize_text(command).lower()
        lowered = RAW_FD_DUP_RE.sub(" ", lowered)
        lowered = RAW_NULL_REDIRECT_RE.sub(" ", lowered)
        if tcp.GIT_MUTATE_RE.search(lowered):
            return True
        if raw_open_may_write(lowered):
            return True
        if tcp._BOUNDED_VERB_RE.search(lowered):
            return True
        if tcp._COMPOSITE_WRITER_RE.search(lowered):
            return True
        return any(ind in lowered for ind in tcp.UNBOUNDED_WRITE_INDICATORS)

    toks = FD_TOKENS + ["echo ", "cat ", "ls ", "cp ", "rm ", "open(", ")", "'r'", ",",
                        "p", "git ", "checkout ", "tee ", "> out.txt"]
    rng = random.Random(20260922)
    n = 60000
    bad = []
    pos = 0
    for _ in range(n):
        s = _rand_from(rng, toks, 0, 12)
        want = raw_smw(s)
        pos += want
        if want != tcp.shell_may_write(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("shell_may_write == raw-pattern rebuild on %d fuzz inputs (%d True)" % (n, pos),
          not bad, ascii(bad[:3]))
    check("shell_may_write fuzz not vacuous (>=5000 True and >=5000 False)",
          pos >= 5000 and n - pos >= 5000, "true=%d/%d" % (pos, n))


OPEN_TOKENS = ["a", "p", " ", " ", "\t", "\n", "\r", ",", ",", "'r'", "\"r\"", "'rb'",
               "'rt'", "'w'", "'r", "r'", "rb", "mode=", "=", "x", "'", "\"", "\u00a0",
               "\u2003", "\x1c", "'rbt'", "'R'"]


def test_open_args_exactness():
    rng = random.Random(20260923)
    n = 150000
    bad = []
    pos = 0
    for _ in range(n):
        s = _rand_from(rng, OPEN_TOKENS, 0, 9)
        want = RAW_OPEN_SAFE_ARGS_RE.match(s) is not None
        pos += want
        if want != tcp._open_args_safe(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("_open_args_safe == raw regex on %d fuzz arguments (%d safe)" % (n, pos),
          not bad, ascii(bad[:3]))
    check("open-args fuzz not vacuous (>=20000 safe and >=20000 unsafe)",
          pos >= 20000 and n - pos >= 20000, "safe=%d/%d" % (pos, n))
    cases = ["open(p)", "open(p,'rb')", "open(p, 'r' )", "open(p,'w')", "open(p,mode)",
             "open(p,'r','x')", "open( p ,\"rt\"\n)", "open(open(p))", "open(p) open(q",
             "x open(p,'r') y open(q,'w')", "open()", "open(,)", "open(,'r')"]
    bad = [c for c in cases if raw_open_may_write(c) != tcp._open_may_write(c)]
    check("_open_may_write == raw on handwritten cases", not bad, ascii(bad))


FLAG_TOKENS = ["-", "--", "r", "R", "f", "F", "i", "I", "d", "v", "x", "z", "recursive",
               "Recursive", "force", "FORCE", "recurs", "-r", "-rf", "-fr", "-R", "-vrf",
               " ", " ", "\t", "=", "a", "_", "\u017f", "\u0130", "\u0131", "\u212a", ".",
               "/", "'", "\"", "1", ";", "rm "]


def test_flag_exactness():
    rng = random.Random(20260924)
    n = 120000
    bad = []
    rec = frc = 0
    for _ in range(n):
        s = _rand_from(rng, FLAG_TOKENS, 0, 14)
        rec += bool(RAW_RECURSIVE_FLAG_RE.search(s))
        frc += bool(RAW_FORCE_FLAG_RE.search(s))
        last_rec, last_force = tcp._last_rm_flag_starts(s)
        if bool(RAW_RECURSIVE_FLAG_RE.search(s)) != (last_rec >= 0) \
                or bool(RAW_FORCE_FLAG_RE.search(s)) != (last_force >= 0):
            bad.append(s)
        # positional contract: for every rm verb at [b, e), "flag in s[e:]" == last >= e
        for m in tcp._RM_VERB_RE.finditer(s):
            e = m.end()
            if (RAW_RECURSIVE_FLAG_RE.search(s[e:]) is not None) != (last_rec >= e) \
                    or (RAW_FORCE_FLAG_RE.search(s[e:]) is not None) != (last_force >= e):
                bad.append(s)
        if len(bad) >= 5:
            break
    check("_last_rm_flag_starts == raw flag regexes (whole + per-rm suffix) on %d fuzz "
          "inputs (%d recursive, %d force)" % (n, rec, frc), not bad, ascii(bad[:3]))
    check("flag fuzz not vacuous (>=8000 of each)", rec >= 8000 and frc >= 8000,
          "rec=%d force=%d" % (rec, frc))


TARGET_TOKENS = ["a", "b/c", "x y", "'x y'", "\"z w\"", ")", "))", "(", "(a)", "}", "{",
                 "{}", "{a}", "`", "``", "`a`", "/", "~", ".", "*", ">", "2>", ">&",
                 "2>&1", "2>/dev/null", "> f", "< f", " ", " ", " ", "\t", "-x", "--",
                 "-", "Closing (final)", "a)b", "a}b", "$(x)", "${HOME}", "'", "\"",
                 "a'b'c", "'a'b", "\"a\"'b'"]


def test_delete_targets_exactness():
    rng = random.Random(20260925)
    n = 150000
    bad = []
    for _ in range(n):
        s = _rand_from(rng, TARGET_TOKENS, 0, 12)
        if raw_delete_targets(s) != tcp._delete_targets(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("_delete_targets == raw on %d fuzz inputs (unbalanced-tail strip)" % n,
          not bad, ascii(bad[:3]))
    for base in (")", "}", "a)", "a}", "(a))", "{a}}", "))((", "a)))"):
        for k in (0, 1, 2, 5, 40):
            s = "x " + base * k
            if raw_delete_targets(s) != tcp._delete_targets(s):
                bad.append(s)
    check("_delete_targets == raw on repeated-delimiter shapes", not bad, ascii(bad[:3]))


RD_TOKENS = ["rm ", "rm ", "rm", "-rf ", "-r ", "-R ", "-fr ", "-f ", "-v ", "-rfx ",
             "-x ", "--recursive ", "--force ", "--RECURSIVE ", "sudo ", "xargs ",
             "-exec ", "find . ", "git ", "A=1 ", "a ", "b/c ", "'x y' ", "\"z\" ",
             "> ", "2>&1 ", "2>/dev/null ", "> f ", "( ", ") ", "{} ", "` ", "$( ",
             "; ", "&& ", "| ", "\n", "/ ", "~ ", ".. ", "* ", "${IFS}", "$IFS", "1>&2 ",
             "0<&1 ", "12>&3 ", "1234567>/dev/null ", "-- ", "C:/x ", "nice -n 5 ", "time ",
             "\u017f ", "\u0130 ", "\t"]


def _rd_template(rng):
    """Structured: [separator/wrapper prefix] rm [flags] [operands/redirects] [more], which
    lifts the hit rate far above what free token soup gives."""
    pre = rng.choice(["", "", "sudo ", "xargs ", "A=1 ", "find . -exec ", "git ", "echo ",
                      "( ", "nice -n 5 ", "; ", "a ", "timeout 5 ", "$( ", "` "])
    flags = _rand_from(rng, ["-rf ", "-r ", "-R ", "-f ", "-v ", "--recursive ", "--force ",
                             "-x ", "a ", "-fr ", "-i "], 0, 3)
    ops = _rand_from(rng, RD_TOKENS, 0, 6)
    tail = rng.choice(["", "", "; rm -rf z", " && rm -r y", " | rm -f q", " -rf t"])
    return pre + "rm " + flags + ops + tail


def _rd_view(d):
    return None if d is None else (d.command, d.recursive, d.force, d.targets)


def test_recursive_delete_exactness_below_the_bound():
    rng = random.Random(20260926)
    n = 90000
    bad = []
    hits = 0
    forced = 0
    for i in range(n):
        s = _rand_from(rng, RD_TOKENS, 0, 13) if i % 3 else _rd_template(rng)
        want = _rd_view(raw_recursive_delete(s))
        hits += want is not None
        forced += bool(want and want[2])
        if want != _rd_view(tcp.recursive_delete(s)):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("recursive_delete == raw on %d fuzz commands (%d hits, %d force)"
          % (n, hits, forced), not bad, ascii(bad[:3]))
    check("recursive_delete fuzz not vacuous (>=8000 hits, >=3000 force, >=20000 None)",
          hits >= 8000 and forced >= 3000 and n - hits >= 20000,
          "hits=%d force=%d/%d" % (hits, forced, n))
    cases = ["rm -rf /", "rm -rf ~/Documents/deals", "sudo rm -rf x", "git rm -r --cached x",
             "grep rm -r .", "# rm -rf x", "find . -exec rm -rf {} +",
             "find . -exec rm -rf {} + -exec rm -rf y +", "rm -rf a; rm -rf b && rm -r c",
             "rm 2>/dev/null -rf x", "(rm -rf x)", "docker run --rm -it x",
             "rm -rf 2>&1 ~/Documents/deals", "rm -r x -f", "rm x -R", "rm --recursive --force x",
             "env A=1 rm -rf x", "xargs -0 rm -rf", "timeout 5 rm -rf x", "rmdir -r x",
             "rm -rf \"my dir\"/x", "rm -rf x) y}", "rm -rf ${IFS}/"]
    bad = [c for c in cases if _rd_view(raw_recursive_delete(c))
           != _rd_view(tcp.recursive_delete(c))]
    check("recursive_delete == raw on handwritten cases", not bad, ascii(bad))


def test_recursive_delete_bound_fails_toward_block():
    b = tcp._RD_MAX_CANDIDATES_PER_SEGMENT
    at = "rm -rf a " * b
    over = "rm -rf a " * (b + 1)
    d_at = tcp.recursive_delete(at)
    d_over = tcp.recursive_delete(over)
    check("exactly at the bound the result still equals the raw scan",
          _rd_view(d_at) == _rd_view(raw_recursive_delete(at)))
    check("past the bound the segment is reported as a recursive delete of '/'",
          d_over is not None and "/" in d_over.targets,
          ascii(_rd_view(d_over)))
    check("config-write-guard would BLOCK that overflow target (catastrophic scope)",
          CWG._delete_verdict("/") is not None)
    # the bound must never turn a previously-detected delete into None
    shapes = [_rm_many_then_flag(6000), _rm_hit_many(6000), "rm x " * 200 + " -R y",
              "sudo rm -rf a " + "rm x " * 200]
    for s in shapes:
        raw_hit = raw_recursive_delete(s) is not None
        new_hit = tcp.recursive_delete(s) is not None
        check("bound never un-flags a raw hit (%s...)" % ascii(s[:24]),
              (not raw_hit) or new_hit)
    # a bounded segment must not swallow OTHER segments: a later segment still reports
    d = tcp.recursive_delete("rm -rf a " * (b + 4) + "; rm -rf keep_me")
    check("a later segment is still scanned after an overflowing one",
          d is not None and "keep_me" in d.targets, ascii(_rd_view(d)))


BLANK_TOKENS = ["/hooks/sessions", "/hooks/state", "/hooks/active-work", "~/.claude",
                ".claude", "/worktrees", ".claude/worktrees", "c:/users/owner/.claude",
                "a", "b", "/", "x/", "\"", "'", " ", " ", "\t", "\n", "\u00a0", "\u2003",
                "\x1c", "\u3000", "-", "=", "hooks", "sessions", "<exempt>", "exempt", "1"]


def test_blank_exempt_exactness():
    real_markers, _g, _c = CWG._shell_marker_sets()
    marker_sets = [
        list(real_markers),
        ["/hooks/sessions", ".claude/worktrees", "a", "x/"],
        ["a b/hooks", "/hooks/state"],     # a whitespace marker: raw pattern preserved
        ["", "/x"],                        # empty marker: raw pattern preserved
        ["exempt", "<exempt>", "/hooks/state"],   # marker overlapping the placeholder
    ]
    rng = random.Random(20260927)
    n = 40000
    bad = {}
    changed = 0
    for i in range(n):
        s = _rand_from(rng, BLANK_TOKENS, 0, 14)
        ms = marker_sets[i % len(marker_sets)]
        want = raw_blank_exempt_cwg(s, ms)
        changed += (want != s)
        if want != CWG._blank_exempt(s, ms):
            bad.setdefault("cwg-set-%d" % (i % len(marker_sets)), s)
        for m in ms:
            if raw_blank_exempt_lcg(s, m) != LCG._blank_exempt(s, m):
                bad.setdefault("lcg[%r]" % m, s)
    check("_blank_exempt (config-write-guard + lint-config-guard) == raw on %d fuzz inputs"
          " x %d marker sets (%d rewritten)" % (n, len(marker_sets), changed),
          not bad, ascii(bad))
    check("blank-exempt fuzz not vacuous (>=10000 rewritten, >=10000 untouched)",
          changed >= 10000 and n - changed >= 10000, "rewritten=%d/%d" % (changed, n))
    cases = ["cp x C:/u/.claude/worktrees/a/b y", "echo >~/.claude/hooks/sessions/s/t",
             "a/.claude/worktrees b/.claude/worktrees", "x.claude/worktreesy", "",
             "  ", ".claude/worktrees", "\t.claude/worktrees\n"]
    bad = [c for c in cases
           if raw_blank_exempt_lcg(c, ".claude/worktrees")
           != LCG._blank_exempt(c, ".claude/worktrees")]
    check("_blank_exempt == raw on handwritten worktree cases", not bad, ascii(bad))


DOT_TOKENS = [".", ".", "..", " ", " ", "\t", "\n", "/", "\\", "a", "b", "x/", ".claude",
              "\u00a0", "\u2003", "\x1c", "-", "_", "1", "./", "../"]


def test_interior_dot_exactness():
    rng = random.Random(20260928)
    n = 150000
    bad = []
    changed = 0
    for _ in range(n):
        s = _rand_from(rng, DOT_TOKENS, 0, 14)
        want = RAW_INTERIOR_DOT_RE.sub("", s)
        changed += (want != s)
        if want != CWG._strip_interior_component_dots(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("_strip_interior_component_dots == raw regex on %d fuzz inputs (%d rewritten)"
          % (n, changed), not bad, ascii(bad[:3]))
    check("interior-dot fuzz not vacuous (>=15000 rewritten, >=15000 untouched)",
          changed >= 15000 and n - changed >= 15000, "rewritten=%d/%d" % (changed, n))
    cases = [".claude./hooks", ".claude /hooks", "./x", "../x", "a../b", "a. ./b", "a  /b",
             "a\t/b", "x.\\y", "a...", "a . . /b", " ./x", "a.", "a. \n. /b", ""]
    bad = [c for c in cases
           if RAW_INTERIOR_DOT_RE.sub("", c) != CWG._strip_interior_component_dots(c)]
    check("_strip_interior_component_dots == raw on handwritten cases", not bad, ascii(bad))


SHLEX_TOKENS = ["a", "b", "ab", " ", " ", "\t", "\n", "\r", "'", "'", "\"", "\"", "\\",
                "\\\\", "(", ")", ";", "|", "&", "&&", "<", ">", ">>", "2>&1", "#",
                "# c\n", "~", "-", ".", "/", "=", "*", "?", "$", "`", "{", "}", "C:\\x",
                "\u00a0", "\u00e9", "1", "rm", "'a b'", "\"c d\"", "\\'", "\\\"", "\\ "]


def _shlex_result(cls, text, escape):
    try:
        lex = cls(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        if not escape:
            lex.escape = ""
        return list(lex)
    except Exception as e:
        return ("EXC", type(e).__name__, str(e))


def test_linear_shlex_exactness():
    import shlex
    rng = random.Random(20260929)
    n = 60000
    bad = []
    ok = exc = 0
    for _ in range(n):
        s = _rand_from(rng, SHLEX_TOKENS, 0, 16)
        for escape in (True, False):
            want = _shlex_result(shlex.shlex, s, escape)
            got = _shlex_result(CWG._LinearShlex, s, escape)
            if isinstance(want, tuple):
                exc += 1
            else:
                ok += 1
            if want != got:
                bad.append((s, escape, want, got))
        if len(bad) >= 5:
            break
    check("_LinearShlex == stdlib shlex (tokens, or exception type+message) on %d fuzz "
          "inputs x 2 escape modes (%d parsed, %d raised)" % (n, ok, exc),
          not bad, ascii(bad[:2]))
    check("shlex fuzz not vacuous (>=30000 parsed, >=3000 raised)",
          ok >= 30000 and exc >= 3000, "parsed=%d raised=%d" % (ok, exc))
    # _tokenize (the real entry point) across the size threshold, both classes
    big = "echo " + "x" * 13000 + " 'q r' \"s t\" \\u ; a | b"
    for text in (big, big + " '", "a b c", "", "  ", "'unclosed"):
        for escape in (True, False):
            check("CWG._tokenize == raw stdlib tokenizer (%d chars, escape=%s)"
                  % (len(text), escape),
                  CWG._tokenize(text, escape) == raw_tokenize(text, escape))


ATTACH_TOKENS = ["a", "b1", "_", ".", ":", "$", "~", "-", "/", "\\", "//", "x/", "C:\\", " ",
                 "\t", "\"", "'", "(", "\u00e9", "\u0663", "\u00a0", "\u2153", "%", "*"]


def test_attached_path_exactness():
    rng = random.Random(20260930)
    n = 200000
    bad = []
    changed = 0
    for _ in range(n):
        s = " ".join(_rand_from(rng, ATTACH_TOKENS, 0, 6).split())  # as _in_command_position
        want = RAW_ATTACHED_PATH_RE.sub(" ", s)
        changed += (want != s)
        if want != tcp._strip_attached_path(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("_strip_attached_path == raw regex on %d fuzz joins (%d rewritten)"
          % (n, changed), not bad, ascii(bad[:3]))
    check("attached-path fuzz not vacuous (>=15000 rewritten)", changed >= 15000,
          "rewritten=%d" % changed)
    # end-to-end: _in_command_position with the raw regex swapped in
    def raw_icp(prefix):
        saved = tcp._strip_attached_path
        tcp._strip_attached_path = lambda j: RAW_ATTACHED_PATH_RE.sub(" ", j)
        try:
            return tcp._in_command_position(prefix)
        finally:
            tcp._strip_attached_path = saved
    rng = random.Random(20260931)
    toks = ["sudo", "env", "A=1", "-x", "-exec", "/bin/", "./", "C:\\bin\\", "x/", "5", "(",
            "$(", "`", "{", " ", " ", "a", "rm", "timeout", "nice", "-n", "/", "\\"]
    bad = []
    for _ in range(60000):
        p = _rand_from(rng, toks, 0, 7)
        if raw_icp(p) != tcp._in_command_position(p):
            bad.append(p)
            if len(bad) >= 5:
                break
    check("_in_command_position == raw-regex variant on 60000 fuzz prefixes", not bad,
          ascii(bad[:3]))


TAR_TOKENS = ["-", "--", "x", "X", "f", "v", "z", "a", "1", "!", "\n", " ", "\t", "\u00e9",
              "\u017f", "\u212a", "_", "="]


def test_tar_bundle_exactness():
    rng = random.Random(20260932)
    n = 200000
    bad = []
    pos = 0
    for i in range(n):
        if i % 2:
            s = _rand_from(rng, TAR_TOKENS, 0, 8)
        else:  # structured: dash + letters (usually with an x) + an occasional odd tail
            s = ("-" + _rand_from(rng, ["x", "x", "f", "v", "z", "X", "a"], 0, 5)
                 + rng.choice(["", "", "", "\n", "\n\n", "!", "1", "é", " "]))
        want = RAW_TAR_EXTRACT_RE.match(s) is not None
        pos += want
        if want != CWG._is_tar_extract_bundle(s):
            bad.append(s)
            if len(bad) >= 5:
                break
    check("_is_tar_extract_bundle == raw regex on %d fuzz tokens (%d match)" % (n, pos),
          not bad, ascii(bad[:3]))
    check("tar fuzz not vacuous (>=10000 match, >=10000 not)", pos >= 10000 and n - pos >= 10000,
          "match=%d/%d" % (pos, n))
    for tok, cmd in (("-xf", "tar"), ("-x\n", "tar"), ("-x\n\n", "tar"), ("--extract", "tar"),
                     ("--xx", "tar"), ("-vxf", "bsdtar"), ("-cf", "tar"), ("-xf", "cat")):
        raw = (tok in CWG._OUTPUT_FLAG_TOKENS) or (
            cmd in ("tar", "bsdtar") and (tok in ("--extract", "--get")
            or (RAW_TAR_EXTRACT_RE.match(tok) is not None and not tok.startswith("--"))))
        check("_is_output_flag(%r, %r) == raw" % (cmd, tok),
              CWG._is_output_flag(cmd, tok) == raw)


MARKER_TOKENS = ["c:/", "d:/", ".claude/hooks", ".claude", "hooks", "/", " ", " ", "\t", "\n",
                 "x", "a.b", "'", "\"", ";", "-", ".claude-", "~/.claude/hooks", "c:/x/",
                 "C:/", "\u00e9", "'hooks", "(hooks", ";hooks", "(", ")", "c:/a'", "c:/a("]


def test_marker_matches_exactness():
    rng = random.Random(20260933)
    n = 150000
    bad = []
    pos = 0
    # Markers that START with a character an absolute token cannot swallow (quote, paren,
    # semicolon) exercise the "marker begins exactly at a token's end" boundary; the real
    # markers start with `.`/`~`, which a token always swallows.
    markers = [".claude/hooks", "'hooks", "(hooks", ";hooks", "~/.claude/hooks"]
    for i in range(n):
        s = _rand_from(rng, MARKER_TOKENS, 0, 12).lower()
        marker = markers[i % len(markers)]
        want = raw_marker_matches(s, marker)
        pos += want
        if want != CWG._marker_matches(s, marker):
            bad.append((marker, s))
            if len(bad) >= 5:
                break
    check("_marker_matches == raw (per-occurrence restart) on %d fuzz texts x %d markers "
          "(%d True)" % (n, len(markers), pos), not bad, ascii(bad[:3]))
    check("marker fuzz not vacuous (>=10000 True, >=10000 False)",
          pos >= 10000 and n - pos >= 10000, "true=%d/%d" % (pos, n))


def test_prose_overflow_is_pinned_and_blocks():
    # The bound counts candidates BEFORE the command-position check (review 2026-09-21,
    # m3): prose that merely MENTIONS `rm -r` more than the bound is reported as a
    # delete of "/" (blocked unless a DESTRUCTIVE_DELETE token is minted). Pin it, and
    # pin that the same prose at or under the bound is unchanged.
    b = tcp._RD_MAX_CANDIDATES_PER_SEGMENT
    under = "echo " + "rm -r x " * b
    over = "echo " + "rm -r x " * (b + 1)
    check("prose with %d `rm -r` mentions is not a delete (as before the bound)" % b,
          tcp.recursive_delete(under) is None and raw_recursive_delete(under) is None)
    d = tcp.recursive_delete(over)
    check("prose with %d `rm -r` mentions IS reported (bounded, fails toward block)" % (b + 1),
          d is not None and "/" in d.targets and raw_recursive_delete(over) is None,
          ascii(_rd_view(d)))


def test_guards_stay_live_when_the_lib_lacks_blank_exempt_token():
    # Partial deploy (review 2026-09-21, m4): the guards import blank_exempt_token
    # SEPARATELY, so a lib without it degrades to the raw pattern instead of turning the
    # whole guard inert (TOOL_PATHS_LOADED False).
    import types
    real = sys.modules["tool_call_paths"]
    stub = types.ModuleType("tool_call_paths")
    stub.__dict__.update({k: v for k, v in real.__dict__.items()
                          if k not in ("blank_exempt_token", "__name__")})
    sys.modules["tool_call_paths"] = stub
    try:
        cwg = _load("config-write-guard.py", "cwg_stub_lib")
        lcg = _load("lint-config-guard.py", "lcg_stub_lib")
    except Exception as e:  # a guard that cannot even load without the name is the failure
        check("both guards load without blank_exempt_token in the lib", False, repr(e))
        return
    finally:
        sys.modules["tool_call_paths"] = real
    check("config-write-guard stays loaded without blank_exempt_token",
          cwg.TOOL_PATHS_LOADED is True)
    check("lint-config-guard stays loaded without blank_exempt_token",
          lcg.TOOL_PATHS_LOADED is True)
    check("fallback blank-exempt equals the raw pattern (config-write-guard)",
          cwg._blank_exempt("cp a/worktrees/b c", ["/worktrees"])
          == raw_blank_exempt_cwg("cp a/worktrees/b c", ["/worktrees"]))
    check("fallback blank-exempt equals the raw pattern (lint-config-guard)",
          lcg._blank_exempt("cp a/.claude/worktrees/b c", ".claude/worktrees")
          == raw_blank_exempt_lcg("cp a/.claude/worktrees/b c", ".claude/worktrees"))


def test_realpath_is_memoized_per_classify_shell_call():
    # Second-review MAJOR-1: realpath of a nonexistent `c:/a/a/...` is O(components x
    # length) on Python 3.13 and classify_shell resolved each drive token ~7x (3 shlex
    # passes x 4 variants). Pin (a) each distinct token is resolved ONCE per call,
    # (b) no cache outlives the call, (c) verdicts are unchanged by the memo.
    import os as _os
    calls = []
    real_rp = _os.path.realpath

    def counting(p, *a, **k):
        calls.append(p)
        return real_rp(p, *a, **k)

    toks = ["c:/zz_nonexistent_%d/x" % i for i in range(40)]
    cmd = "echo \"q\" ^ > out.txt " + " ".join(toks)
    _os.path.realpath = counting
    try:
        CWG.classify_shell(cmd, True)
        first = list(calls)
        del calls[:]
        CWG.classify_shell(cmd, True)   # a SECOND call must resolve afresh (no leak)
        second = list(calls)
    finally:
        _os.path.realpath = real_rp
    distinct = len(set(p for p in first))
    check("classify_shell resolves each distinct path once (%d realpath calls, %d distinct)"
          % (len(first), distinct), len(first) == distinct and distinct >= 40)
    check("no realpath cache survives the call (second call resolved %d paths)"
          % len(second), len(second) == len(first) and CWG._REALPATH_MEMO is None)
    ok = CWG.classify_shell("echo x > %s/hooks/y.py" % CWG._norm(CWG.guard_root()), True)
    check("verdict unchanged: a write into the protected tree is still classified",
          ok is not None and ok[0] == "governance", ascii(ok))
    # CPU: a single 32KB nonexistent path costs one realpath (OS cost); repeated per
    # variant it used to cost ~6x that. NOTE (accepted residual, see _REALPATH_MEMO in
    # config-write-guard.py): the quote/caret here sit OUTSIDE the token, so this pins the
    # exact-string memo only; other SPELLINGS of one long token (case, quote-cut,
    # caret) are still resolved separately and are deliberately not bounded here.
    path = "c:/" + "a/" * 15000
    t_single, _ = cpu(real_rp, path)
    t_cls, _ = cpu(CWG.classify_shell, "echo \"q\" ^ ls " + path, True)
    check("classify_shell on one long drive path costs ~1 realpath: %.3fs vs single %.3fs"
          % (t_cls, t_single), t_cls < 2.5 * t_single + 0.5)


WB_NAME = "master excel template company wide -- oxford.xlsx"


def _wbg():
    os.environ["ORA_WORKBOOK_GUARD_NAME"] = WB_NAME
    return _load("workbook-write-guard.py", "wbg_under_test")


def test_workbook_identifier_memo_and_bound():
    wbg = _wbg()
    dt, _ = cpu(wbg._shell_writes_workbook, "wb.save(p); " * 5400 + " " + WB_NAME)
    check("workbook-write-guard _shell_writes_workbook cpu bound (5400 save(p) calls, 64KB): "
          "%.3fs" % dt, dt < CPU_BOUND)
    dt, _ = cpu(wbg._shell_writes_workbook, "df.to_excel(w); " * 4000 + " " + WB_NAME)
    check("workbook-write-guard _shell_writes_workbook cpu bound (4000 to_excel(w), 64KB): "
          "%.3fs" % dt, dt < CPU_BOUND)
    # exactness of the memo: identical verdicts to an UNCACHED resolver, on fuzz
    raw_resolve = wbg._resolve_identifier_literal
    def uncached(lowered_text, ident, cache=None):
        return raw_resolve(lowered_text, ident, None)
    rng = random.Random(20260934)
    idents = ["p", "q", "w", "path", "x1"]
    lits = ["'other.xlsx'", "r'%s'" % WB_NAME, "'%s'" % WB_NAME, "f'x'", "'a b'", "\"%s\"" % WB_NAME]
    calls = ["wb.save(%s)", "df.to_excel(%s)", "wb.save(%s, 1)", "df.to_excel(%s, 'S')",
             "book.save(%s)", "wb.save(str(%s))", "wb.save(%s and 1)"]
    bad = []
    blocked = 0
    n = 20000
    for _ in range(n):
        parts = []
        for _k in range(rng.randint(1, 6)):
            r = rng.random()
            if r < 0.4:
                parts.append("%s = %s" % (rng.choice(idents), rng.choice(lits)))
            elif r < 0.9:
                parts.append(rng.choice(calls) % rng.choice(idents + lits))
            else:
                parts.append(rng.choice(["import openpyxl", "echo hi", "cp a b", WB_NAME]))
        if rng.random() < 0.8:
            parts.append(WB_NAME)
        text = "; ".join(parts)
        cached = wbg._shell_writes_workbook(text)
        wbg._resolve_identifier_literal = uncached
        try:
            plain = wbg._shell_writes_workbook(text)
        finally:
            wbg._resolve_identifier_literal = raw_resolve
        blocked += bool(cached[0])
        if cached != plain:
            bad.append(text)
            if len(bad) >= 5:
                break
    check("_shell_writes_workbook with the identifier memo == uncached on %d fuzz commands "
          "(%d blocked)" % (n, blocked), not bad, ascii(bad[:2]))
    check("workbook fuzz not vacuous (>=2000 blocked, >=2000 allowed)",
          blocked >= 2000 and n - blocked >= 2000, "blocked=%d/%d" % (blocked, n))
    # the bound: >64 DISTINCT resolvable identifiers fail toward block, <=64 unchanged
    m = 64  # the LITERAL bound: a regressed constant must not move the boundary with it
    check("_MAX_DISTINCT_IDENTIFIERS is exactly 64", wbg._MAX_DISTINCT_IDENTIFIERS == m)
    def cmd(k):
        return "; ".join("p%d = 'other.xlsx'; wb.save(p%d)" % (i, i) for i in range(k)) \
            + "; " + WB_NAME
    check("%d distinct resolvable identifiers still clear (unchanged)" % m,
          wbg._shell_writes_workbook(cmd(m))[0] is False)
    check("%d distinct identifiers fail toward BLOCK (bounded work)" % (m + 1),
          wbg._shell_writes_workbook(cmd(m + 1))[0] is True)


# ------------------------------------------------ process-boundary wall-clock
# Wall clock through the REAL guards. Loose on purpose (loaded machine, other sessions):
# the fixed guards finish in ~0.5s including interpreter start; the unfixed ones take
# 10s to minutes on these payloads.
WALL_BOUND = 8.0


def _run_guard(hook, payload, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    t0 = time.monotonic()
    proc = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, hook)],
                          input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, timeout=300)
    return (time.monotonic() - t0, proc.returncode,
            proc.stderr.decode("utf-8", "replace"))


def _bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd},
            "session_id": "test-session-0123456789abcdef"}


def test_guards_finish_in_bounded_wall_time():
    sess = tempfile.mkdtemp(prefix="aolre-sess-")
    root = tempfile.mkdtemp(prefix="aolre-root-")
    log = os.path.join(tempfile.mkdtemp(prefix="aolre-log-"), "chip-claims.log")
    base_env = {"ORA_OVERRIDE_SESSIONS_DIR": sess}
    wb = "Master Excel Template Company Wide -- Oxford.xlsx"
    cwg_env = dict(base_env, ORA_CONFIG_GUARD_ROOT=root, ORA_CHIP_CLAIMS_LOG=log)
    lcg_env = dict(base_env, ORA_LINT_CONFIG_GUARD_ROOT=root)
    wbg_env = dict(base_env, ORA_WORKBOOK_GUARD_NAME=wb)
    digits = _digits(65536)                         # raw ~25s+ in shell_may_write alone
    blob = _long_token_redirect(32768)               # raw ~40s in config-write-guard
    rigs = [
        ("config-write-guard.py", "digit-run", digits, cwg_env),
        ("config-write-guard.py", "long-token-redirect", blob, cwg_env),
        ("config-write-guard.py", "rm-x-many-then-flag", _rm_many_then_flag(24000), cwg_env),
        ("config-write-guard.py", "rm-flag-run", _rm_flag_run(40000), cwg_env),
        ("config-write-guard.py", "interior-dot-run", "echo x" + "." * 40000 + " > out.txt",
         cwg_env),
        ("config-write-guard.py", "one-512KB-token", _long_token_redirect(524288), cwg_env),
        ("lint-config-guard.py", "digit-run", digits, lcg_env),
        ("lint-config-guard.py", "long-token-redirect", _long_token_redirect(65536),
         lcg_env),
        ("workbook-write-guard.py", "digit-run", digits + " " + wb, wbg_env),
        ("workbook-write-guard.py", "open-spaces", _open_spaces(32768) + " " + wb, wbg_env),
    ]
    for hook, shape, cmd, env in rigs:
        dt, rc, err = _run_guard(hook, _bash(cmd), env)
        check("%s wall-clock bound (%s, %d chars): %.2fs rc=%s"
              % (hook, shape, len(cmd), dt, rc), dt < WALL_BOUND, err[:160])


def test_huge_commands_still_block_when_they_target_governance():
    # The fixes must not weaken a gate: a huge redirect INTO the protected tree is still
    # blocked, an exempt worktree token inside a huge command is still exempt, and the
    # catastrophic delete is still blocked -- each within the wall-clock bound.
    sess = tempfile.mkdtemp(prefix="aolre-sess2-")
    root = tempfile.mkdtemp(prefix="aolre-root2-")
    log = os.path.join(tempfile.mkdtemp(prefix="aolre-log2-"), "chip-claims.log")
    env = {"ORA_OVERRIDE_SESSIONS_DIR": sess, "ORA_CONFIG_GUARD_ROOT": root,
           "ORA_CHIP_CLAIMS_LOG": log}
    posix_root = root.replace("\\", "/")
    blob = "a" * 32768
    dt, rc, err = _run_guard("config-write-guard.py",
                             _bash("echo %s > %s/hooks/x.py" % (blob, posix_root)), env)
    check("config-write-guard still BLOCKS a 32KB-blob write into <root>/hooks: %.2fs rc=%s"
          % (dt, rc), rc == 2 and dt < WALL_BOUND, err[:120])
    dt, rc, err = _run_guard("config-write-guard.py",
                             _bash("echo %s > %s/worktrees/w/hooks/x.py" % (blob, posix_root)),
                             env)
    check("config-write-guard still ALLOWS the same blob into an exempt worktree: %.2fs rc=%s"
          % (dt, rc), rc == 0 and dt < WALL_BOUND, err[:120])
    dt, rc, err = _run_guard("config-write-guard.py",
                             _bash("rm x " * 4000 + " -rf y"), env)
    check("config-write-guard BLOCKS an overflowing rm-x-many command (fails toward "
          "block): %.2fs rc=%s" % (dt, rc), rc == 2 and dt < WALL_BOUND, err[:120])
    lroot = tempfile.mkdtemp(prefix="aolre-lroot-")
    lenv = {"ORA_OVERRIDE_SESSIONS_DIR": sess, "ORA_LINT_CONFIG_GUARD_ROOT": lroot}
    cmd = "echo %s > %s/oxford-command-center/eslint.config.js" % (
        blob, lroot.replace("\\", "/"))
    dt, rc, err = _run_guard("lint-config-guard.py", _bash(cmd), lenv)
    check("lint-config-guard still BLOCKS a 32KB-blob write to a protected config: "
          "%.2fs rc=%s" % (dt, rc), rc == 2 and dt < WALL_BOUND, err[:120])


if __name__ == "__main__":
    test_fd_patterns_handwritten()
    test_fd_patterns_fuzz()
    test_shell_may_write_end_to_end_unchanged()
    test_open_args_exactness()
    test_flag_exactness()
    test_delete_targets_exactness()
    test_recursive_delete_exactness_below_the_bound()
    test_recursive_delete_bound_fails_toward_block()
    test_blank_exempt_exactness()
    test_interior_dot_exactness()
    test_linear_shlex_exactness()
    test_tcp_cpu_bounds()
    test_attached_path_exactness()
    test_tar_bundle_exactness()
    test_marker_matches_exactness()
    test_prose_overflow_is_pinned_and_blocks()
    test_guards_stay_live_when_the_lib_lacks_blank_exempt_token()
    test_realpath_is_memoized_per_classify_shell_call()
    test_workbook_identifier_memo_and_bound()
    test_review_round_cpu_bounds()
    test_interior_dot_and_shlex_cpu_bounds()
    test_blank_exempt_cpu_bounds()
    test_guards_finish_in_bounded_wall_time()
    test_huge_commands_still_block_when_they_target_governance()
    if _failures:
        print("\n%d FAILURE(S):\n  %s" % (len(_failures), "\n  ".join(_failures)))
        sys.exit(1)
    print("\nALL always-on-linear-redirect-exempt tests passed.")
    sys.exit(0)
