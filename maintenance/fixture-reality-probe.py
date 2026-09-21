#!/usr/bin/env python3
"""ORA fixture-reality probe. REPORT-ONLY -- never edits, fixes or rewrites
anything.

WHAT IT CATCHES
---------------
A hand-authored test fixture is an ASSERTION ABOUT THE OUTSIDE WORLD, not a
fact about it. When a hook or parser matches on a tool name, an event name or
a payload field name, the fixture can encode the SAME wrong name the code
uses. Both agree, both are wrong, the test passes green forever, and the
production branch never once fires.

Founding incident (memory: feedback_fixture_shaped_tests_certify_dead_
branches.md, 2026-07-24):
    hooks/eos-telemetry.py        counted subagent dispatch with tname == "Task"
    hooks/tests/test-eos-telemetry.py  built its fixture with "name": "Task"
                                       and asserted task_dispatched is True
The real tool name is "Agent". Across the local transcripts "Task" appeared
as a tool name 0 times and "Agent" 672 times. The signal reported 0.0% across
679 sessions and eos-telemetry-rollup.py surfaced it EVERY DAY as the
"most-frequently-missing signal" -- a measurement artifact read as a behavior
finding, for months.

METHOD
------
 1. Parse every code file under CODE_ROOTS with `ast` (never a regex over
    Python source -- a regex produces false positives that cannot be
    defended) and extract every string literal used as a NAME PREDICATE:
      * equality/inequality against a name-slot expression
        (tool_name == "X", tname != "X", payload["tool_name"] == "X",
         payload.get("hook_event_name") == "X", evt.event == "X")
      * membership in a name set, inline or bound to a module-level constant
        (tool_name in {"Edit", "Write"};  WRITE_TOOLS = (...); t in WRITE_TOOLS)
      * dict literals keyed by a name slot ({"tool_name": "X"})
      * keyword arguments named for a slot (f(tool_name="X"))
    `.startswith(...)` arguments are DELIBERATELY NOT extracted: a prefix
    predicate is exact-by-design at a different granularity, and extracting
    its argument would flag every legitimate prefix match.
 2. Stream the REAL corpus (~/.claude/projects/**/*.jsonl -- hundreds of
    transcripts, hundreds of MB; streamed line by line, never loaded whole)
    and build the OBSERVED NAME VOCABULARY per slot. Matching is therefore
    EXACT by construction -- set membership, never prefix or substring. The
    founding incident's write-up warns about exactly this: TaskCreate /
    TaskUpdate / TaskList / TaskGet / TaskOutput / TaskStop are todo tools,
    not dispatch, and widening "Task" to reach them would have "fixed" the
    metric while leaving it just as wrong.
 3. Report every literal with ZERO occurrences in its slot, with the file and
    line asserting on it, the top of what that slot ACTUALLY emits (this is
    what surfaces "Agent x672" beside a dead "Task"), and any lexical
    near-miss siblings -- ADVISORY ONLY. Note that the founding incident's
    true sibling, Agent, is NOT lexically near Task: the absence of a
    near-miss proves nothing, and a near-miss is never a licence to widen a
    match.
 4. Cross-check TEST_ROOTS. A zero-occurrence literal that a fixture ALSO
    uses is CONFIRMED fixture-shaped -- code and test agreeing on a name
    reality has never emitted. That pairing is the high-confidence finding;
    a bare zero-occurrence literal in code alone is weaker and is ranked, not
    presented flat.
 5. Separately read telemetry/lane-telemetry.jsonl and flag any boolean
    signal at EXACTLY 0.0% or 100.0% over a meaningful sample as a SUSPECTED
    BROKEN EMITTER. That is the tell the founding incident left behind: real
    behavior is rarely absolute.

FALSE-POSITIVE GUARDS (legitimate zero-occurrence literals exist)
-----------------------------------------------------------------
  * UNMEASURED SLOTS. If a slot's observed vocabulary is below
    MIN_SLOT_VOCAB distinct names, the corpus cannot speak to that slot and
    NOTHING in it is asserted. This is the big one: transcripts record tool
    names but NOT hook payloads, so hook_event_name is normally unmeasurable
    and every "PreToolUse"/"PostToolUse" literal in hooks/ would otherwise
    read as dead. Suppressed literals are disclosed as caveats, never
    silently dropped.
  * THE GENERIC `name` SLOT IS NOT ASSERTABLE FROM CODE. It is the most
    overloaded key in this repo (git refs, file names, scheduled-task ids)
    while the corpus's `name` vocabulary is only the tool/agent/MCP name
    space -- 7 false positives on the first live run, and it could never have
    produced a true one. Fixture matching keeps every slot, because the
    founding incident's own fixture keyed the tool name as "name".
  * MCP-SCOPED NAMES (mcp__server__tool) are capped at LOW: a connector this
    user has simply never invoked is not a defect.
  * CROSS-SLOT PRESENCE. A literal absent from its own slot but present in
    another is capped at MEDIUM -- likelier an over-narrow slot inference by
    this probe than a dead branch in the code.
  * EXPLICIT MARKER. `# fixture-reality-probe: expected-absent <reason>` on,
    or within MARKER_LOOKBACK lines above, the predicate suppresses it WITH
    THE REASON RECORDED -- an auditable escape hatch for newly added tool
    names not yet exercised, defensive branches for tools this user has
    never invoked, and deprecated names kept for back-compat.
  * ALLOWLIST (see ALLOWLIST below) for the same classes, keyed by literal.
  * SELF AND TOOLING. This probe, its own tests, and the sibling probes that
    deliberately quote wrong values in order to detect them, are skipped --
    the same self_path/skip_names convention as governor-drift-probe.py.
  * SHAPE. Only identifier-shaped literals in a recognised name slot are ever
    considered.

EXIT CODES (this guard FAILS OPEN, like every ORA guard)
--------------------------------------------------------
  0 = clean, OR degraded/unknown/unreadable with a stated caveat
  1 = at least one CONFIRMED fixture-shaped predicate (code + test agree on a
      name reality has never emitted). NOTHING ELSE exits non-zero -- a
      suspected broken emitter is reported, never gated on, because
      "suspected" is not "proven".
An unexpected internal error also exits 0, after printing [ACTION]: a probe
that blocks on its own bug gates nothing useful. The tradeoff is that a
crashed probe reads as clean, so every run prints a machine-checkable
evidence line (corpus.files / corpus.measured) a caller can assert on.

USAGE
-----
  python fixture-reality-probe.py                 # live scan, human report
  python fixture-reality-probe.py --quiet         # print only on a finding
  python fixture-reality-probe.py --json          # machine-readable report
  python fixture-reality-probe.py --corpus=DIR --code-roots=A,B \
      --test-roots=C --telemetry=PATH             # fixture-driven (tests)
  python fixture-reality-probe.py --max-corpus-files=N   # bounded sample run

RECOMMENDED CADENCE: weekly, alongside doctrine-integrity-probe.py. NOT
registered as a scheduled task by this change -- registration goes only
through the supervised create_scheduled_task MCP tool.
"""
import ast
import json
import os
import re
import sys

# Output may pass through a Windows cp1252 pipe. Force UTF-8 with replacement
# so the probe never dies on its own output (governor-drift-probe.py I5), and
# keep every string this file emits ASCII-only (repo convention: an unattended
# PowerShell run decodes child stdout as IBM437 -- see
# reference_powershell_git_show_corrupts_nonascii.md).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")

DEFAULT_CODE_ROOTS = [
    os.path.join(CLAUDE, "hooks"),
    os.path.join(CLAUDE, "hooks", "lib"),
    os.path.join(CLAUDE, "maintenance"),
]
DEFAULT_TEST_ROOTS = [
    os.path.join(CLAUDE, "hooks", "tests"),
    os.path.join(CLAUDE, "maintenance", "_tests"),
    os.path.join(CLAUDE, "maintenance", "tests"),
]
DEFAULT_CORPUS = os.path.join(CLAUDE, "projects")
DEFAULT_TELEMETRY = os.path.join(CLAUDE, "telemetry", "lane-telemetry.jsonl")

# --- tuning constants (every threshold here is a false-positive guard) ------

# A slot the corpus cannot speak to is UNMEASURED, never "absent". Ten distinct
# observed names is the floor at which "this name never appears" starts to mean
# something. The live tool-name slot carries dozens; hook_event_name carries
# zero (transcripts do not record hook payloads) and is correctly suppressed.
MIN_SLOT_VOCAB = 10

# A 0%/100% boolean needs a real denominator before it is worth reporting.
MIN_TELEMETRY_SAMPLE = 30

# How far above a predicate an `expected-absent` marker comment may sit.
MARKER_LOOKBACK = 2
MARKER = "fixture-reality-probe: expected-absent"

# Reported per finding: what the slot ACTUALLY emits, most frequent first.
SLOT_TOP_N = 8
NEAR_MISS_N = 3
MAX_NEAR_MISS_EDITS = 2

NAME_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:\-]{1,79}$")

# Name slots. The key is the slot; the value is the set of identifier/key
# spellings that bind an expression to it.
TOOL_HINTS = frozenset((
    "tool_name", "toolname", "tool", "tname", "tool_use_name", "toolnames",
    "tool_names", "tools", "tn",
))
EVENT_HINTS = frozenset((
    "hook_event_name", "hook_event", "event_name", "eventname", "event",
    "evt", "events", "event_names",
))
GENERIC_HINTS = frozenset(("name", "names"))

SLOT_TOOL = "tool_name"
SLOT_EVENT = "hook_event_name"
SLOT_NAME = "name"
SLOT_ORDER = (SLOT_TOOL, SLOT_EVENT, SLOT_NAME)

# Slots a CODE predicate may be asserted against. The generic `name` slot is
# deliberately NOT one of them (2026-09-10, first live run): `name` is the most
# overloaded key in this repo -- git refs ("HEAD"), file names ("MEMORY.md",
# "event_log.md", "open-items-tracker.md", "SKILL.md"), scheduled-task ids
# ("ora-mcp-liveness-probe"), memory-file slugs -- while the corpus's "name"
# vocabulary is ONLY the tool/agent/MCP name space. Asserting one against the
# other produced 7 false positives on the first live run and could never have
# produced a true one. Precision over recall, the same stance the sibling
# probes take. The FIXTURE side keeps every slot: the founding incident's own
# fixture keyed the tool name as "name", not "tool_name", so narrowing the code
# side must not narrow fixture matching (test 12b pins this).
CODE_ASSERTABLE_SLOTS = frozenset((SLOT_TOOL, SLOT_EVENT))

# Literals that are legitimately absent, with the reason on record. Keep this
# short and justified -- the marker comment is the preferred escape hatch
# because it lives next to the code it excuses. Everything here is still
# PRINTED every run, under SUPPRESSED, so an exclusion can never go quiet.
ALLOWLIST = {
    # 2026-09-10, verified by raw corpus grep (0 hits in 1,630 transcripts /
    # 1.19 GB, alongside Agent x1079 and TaskCreate x195 in the same pass):
    "MultiEdit": (
        "DEPRECATED HARNESS TOOL kept for back-compat. Not in the current tool "
        "roster and 0 occurrences in the corpus, but hooks/ still list it in "
        "EDIT_TOOLS/write-tool sets so an older transcript or a re-introduced "
        "tool stays covered. The fixtures asserting on it "
        "(test-eos-claude-md-guard.py, test-write-guard-coverage.py) therefore "
        "certify branches that cannot fire TODAY -- that is intended breadth, "
        "not a dead predicate. Re-rule if MultiEdit is ever dropped from the "
        "hooks themselves."),
    "NotebookEdit": (
        "LIVE HARNESS TOOL THIS USER HAS NEVER INVOKED (0 occurrences; it is "
        "in the current roster). The write/confidentiality guards must cover "
        "it BEFORE the first notebook edit, not after, so its defensive branch "
        "and the fixtures in test-ora-autonomy-gate.py are correct. This is "
        "the textbook legitimate zero-occurrence literal."),
}

# Files that deliberately quote wrong names in order to detect or restore them
# (same self_path/skip_names convention as governor-drift-probe.py).
SKIP_BASENAMES = frozenset((
    "fixture-reality-probe.py",
    "test_fixture_reality_probe.py",
    "governor-drift-probe.py",
    "restore-skill-governor.py",
    "doctrine-integrity-probe.py",
))

TEST_FILE_RE = re.compile(r"^test[-_].*\.py$", re.I)


def ascii_safe(s):
    """ASCII-only output, per the repo convention (see module docstring)."""
    try:
        return str(s).encode("ascii", "replace").decode("ascii")
    except Exception:
        return "<unprintable>"


# ---------------------------------------------------------------------------
# AST extraction
# ---------------------------------------------------------------------------

class Literal(object):
    __slots__ = ("value", "slot", "path", "line", "context")

    def __init__(self, value, slot, path, line, context):
        self.value = value
        self.slot = slot
        self.path = path
        self.line = line
        self.context = context

    def key(self):
        return (self.value, self.slot)


def slot_for_hint(hint):
    if hint is None:
        return None
    h = hint.lower()
    if h in TOOL_HINTS:
        return SLOT_TOOL
    if h in EVENT_HINTS:
        return SLOT_EVENT
    if h in GENERIC_HINTS:
        return SLOT_NAME
    return None


def hint_of(node):
    """The identifier/key that binds an expression to a name slot, or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            return sl.value
        return None
    if isinstance(node, ast.Call):
        # payload.get("tool_name") / payload.get("tool_name", "")
        fn = node.func
        if (isinstance(fn, ast.Attribute) and fn.attr in ("get", "pop")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            return node.args[0].value
        return None
    if isinstance(node, ast.BoolOp):
        # `payload.get("tool_name") or ""` -- the real eos-telemetry shape
        for v in node.values:
            h = hint_of(v)
            if h:
                return h
        return None
    return None


def const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def str_elements(node):
    """String constants of a set/list/tuple/frozenset(...) literal."""
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        out = []
        for e in node.elts:
            v = const_str(e)
            if v is not None:
                out.append(v)
        return out
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("frozenset", "set", "tuple", "list")
            and len(node.args) == 1):
        return str_elements(node.args[0])
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.Add)):
        return str_elements(node.left) + str_elements(node.right)
    return []


def collect_name_collections(tree):
    """Module-level constants holding a set/tuple/list of names, keyed by the
    variable name, so `tool_name in WRITE_TOOLS` resolves to its members."""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        vals = str_elements(node.value)
        if not vals:
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                out.setdefault(t.id, []).extend(vals)
    return out


def extract_literals(path, source):
    """Every name-slot string literal in one Python source, with line numbers.

    Raises SyntaxError on unparseable input -- the caller turns that into a
    caveat, never a crash and never a finding.
    """
    tree = ast.parse(source, filename=path)
    collections = collect_name_collections(tree)
    found = []

    def add(value, slot, line, context):
        if value is None or slot is None:
            return
        if not NAME_SHAPE.match(value):
            return
        found.append(Literal(value, slot, path, line, context))

    for node in ast.walk(tree):
        # --- equality / membership predicates -----------------------------
        if isinstance(node, ast.Compare):
            operands = [node.left] + list(node.comparators)
            for op, right in zip(node.ops, node.comparators):
                left = operands[operands.index(right) - 1]
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    for a, b in ((left, right), (right, left)):
                        slot = slot_for_hint(hint_of(a))
                        v = const_str(b)
                        if slot and v is not None:
                            add(v, slot, getattr(node, "lineno", 0), "compare")
                elif isinstance(op, (ast.In, ast.NotIn)):
                    slot = slot_for_hint(hint_of(left))
                    if not slot:
                        continue
                    vals = str_elements(right)
                    if not vals and isinstance(right, ast.Name):
                        vals = collections.get(right.id, [])
                    for v in vals:
                        add(v, slot, getattr(node, "lineno", 0), "membership")
        # --- dict literals keyed by a name slot ---------------------------
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                kk = const_str(k) if k is not None else None
                slot = slot_for_hint(kk)
                vv = const_str(v)
                if slot and vv is not None:
                    add(vv, slot, getattr(v, "lineno",
                                          getattr(node, "lineno", 0)), "dict")
        # --- keyword arguments named for a slot ---------------------------
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                slot = slot_for_hint(kw.arg)
                vv = const_str(kw.value)
                if slot and vv is not None:
                    add(vv, slot, getattr(kw.value, "lineno",
                                          getattr(node, "lineno", 0)),
                        "keyword")
    return found


def marker_lines(source):
    """{line_no: reason} for every `expected-absent` marker comment."""
    out = {}
    for i, raw in enumerate(source.splitlines(), 1):
        idx = raw.find(MARKER)
        if idx >= 0:
            out[i] = raw[idx + len(MARKER):].strip(" :-\t") or "(no reason given)"
    return out


def marker_for(markers, line):
    for delta in range(0, MARKER_LOOKBACK + 1):
        if (line - delta) in markers:
            return markers[line - delta]
    return None


# ---------------------------------------------------------------------------
# file discovery
# ---------------------------------------------------------------------------

def is_test_file(path):
    return bool(TEST_FILE_RE.match(os.path.basename(path)))


def iter_py(roots, want_tests, exclude_dirs=()):
    """Python sources under `roots`. Deduplicated: DEFAULT_CODE_ROOTS lists
    hooks/ and hooks/lib/ separately (hooks/lib is inside hooks/), and the
    same file must not be scanned -- or reported -- twice."""
    seen = set()
    excl = set(os.path.abspath(d).lower().rstrip("\\/") for d in exclude_dirs)
    out = []
    for root in roots:
        if os.path.isfile(root):
            cands = [root]
        elif os.path.isdir(root):
            cands = []
            for dirpath, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs
                           if d not in ("__pycache__", ".git", "node_modules",
                                        "_archive", "_applied")]
                for f in files:
                    if f.endswith(".py"):
                        cands.append(os.path.join(dirpath, f))
        else:
            continue
        for p in cands:
            ap = os.path.abspath(p)
            low = ap.lower()
            if any(low.startswith(d + os.sep) or low == d for d in excl):
                continue
            if ap in seen:
                continue
            if os.path.basename(p) in SKIP_BASENAMES:
                continue
            if is_test_file(p) != want_tests:
                continue
            seen.add(ap)
            out.append(ap)
    return sorted(out)


# ---------------------------------------------------------------------------
# corpus scan -- streamed, never loaded whole
# ---------------------------------------------------------------------------

# `"type": "tool_use", "id": "toolu_...", "name": "Bash"` and the reverse key
# order. Bounded lookahead so a long line cannot pair a tool_use marker with an
# unrelated "name" field far away.
R_TOOL_USE_A = re.compile(
    r'"type"\s*:\s*"tool_use".{0,300}?"name"\s*:\s*"([^"\\]{1,120})"', re.S)
R_TOOL_USE_B = re.compile(
    r'"name"\s*:\s*"([^"\\]{1,120})".{0,300}?"type"\s*:\s*"tool_use"', re.S)
R_TOOL_NAME = re.compile(r'"tool_name"\s*:\s*"([^"\\]{1,120})"')
R_HOOK_EVENT = re.compile(r'"hook_event_name"\s*:\s*"([^"\\]{1,120})"')
R_ANY_NAME = re.compile(r'"name"\s*:\s*"([^"\\]{1,120})"')


def iter_corpus_files(corpus_root, max_files=None):
    if os.path.isfile(corpus_root):
        return [corpus_root]
    out = []
    if not os.path.isdir(corpus_root):
        return out
    for dirpath, dirs, files in os.walk(corpus_root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f.endswith(".jsonl"):
                out.append(os.path.join(dirpath, f))
    out.sort()
    if max_files:
        out = out[:max_files]
    return out


def scan_corpus(corpus_root, max_files=None):
    """One streaming pass -> the observed name vocabulary, per slot.

    Returns (vocab, stats, caveats). vocab[slot] is {name: count}. Exact set
    membership against this vocabulary IS the matching rule -- there is no
    prefix or substring path anywhere in this probe.
    """
    vocab = {SLOT_TOOL: {}, SLOT_EVENT: {}, SLOT_NAME: {}}
    stats = {"files": 0, "lines": 0, "bytes": 0, "unreadable": 0,
             "malformed_lines": 0, "measured": False}
    caveats = []
    files = iter_corpus_files(corpus_root, max_files)
    if not files:
        caveats.append(
            "corpus UNREADABLE or EMPTY at %s -- no name was asserted against "
            "reality this run (fail open)." % ascii_safe(corpus_root))
        return vocab, stats, caveats

    def bump(slot, name):
        d = vocab[slot]
        d[name] = d.get(name, 0) + 1

    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                stats["files"] += 1
                for line in fh:
                    stats["lines"] += 1
                    stats["bytes"] += len(line)
                    if '"name"' not in line and '"tool_name"' not in line \
                            and '"hook_event_name"' not in line:
                        continue
                    # A line that is not a JSON object is malformed for our
                    # purposes; we still scan it for names rather than
                    # discarding data, but we count it so the report is honest.
                    stripped = line.strip()
                    if not (stripped.startswith("{") and stripped.endswith("}")):
                        stats["malformed_lines"] += 1
                    if '"tool_use"' in line:
                        for m in R_TOOL_USE_A.finditer(line):
                            bump(SLOT_TOOL, m.group(1))
                        for m in R_TOOL_USE_B.finditer(line):
                            bump(SLOT_TOOL, m.group(1))
                    for m in R_TOOL_NAME.finditer(line):
                        bump(SLOT_TOOL, m.group(1))
                    for m in R_HOOK_EVENT.finditer(line):
                        bump(SLOT_EVENT, m.group(1))
                    for m in R_ANY_NAME.finditer(line):
                        bump(SLOT_NAME, m.group(1))
        except Exception as exc:
            stats["unreadable"] += 1
            caveats.append("corpus file unreadable (fail open, not asserted): "
                           "%s -- %s" % (ascii_safe(path), ascii_safe(exc)))

    # The generic `name` slot is a superset of the tool-name slot: a tool name
    # IS a "name" field. Union them so a tool literal checked against the
    # generic slot is never called absent on a technicality.
    for n, c in vocab[SLOT_TOOL].items():
        vocab[SLOT_NAME][n] = max(vocab[SLOT_NAME].get(n, 0), c)

    stats["measured"] = any(vocab[s] for s in SLOT_ORDER)
    if not stats["measured"]:
        caveats.append(
            "corpus at %s yielded ZERO names across %d file(s) -- nothing was "
            "asserted (fail open)." % (ascii_safe(corpus_root), stats["files"]))
    if stats["unreadable"]:
        caveats.append("%d corpus file(s) unreadable -- coverage is partial."
                       % stats["unreadable"])
    return vocab, stats, caveats


# ---------------------------------------------------------------------------
# near-miss siblings -- ADVISORY ONLY
# ---------------------------------------------------------------------------

def edit_distance_le(a, b, limit):
    if abs(len(a) - len(b)) > limit:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (0 if ca == cb else 1)))
        if min(cur) > limit:
            return False
        prev = cur
    return prev[-1] <= limit


def near_misses(literal, vocab_slot):
    """Lexically similar names that DO occur. Advisory: the founding
    incident's true sibling (Task -> Agent) is not lexically near at all, so an
    empty list here proves nothing, and a listed near-miss is never a licence
    to widen a match to a prefix or substring."""
    low = literal.lower()
    scored = []
    for name, count in vocab_slot.items():
        if name == literal:
            continue
        nl = name.lower()
        if nl == low:
            rank = 0
        elif nl.startswith(low) or low.startswith(nl):
            rank = 1
        elif low in nl or nl in low:
            rank = 2
        elif edit_distance_le(low, nl, MAX_NEAR_MISS_EDITS):
            rank = 3
        else:
            continue
        scored.append((rank, -count, name))
    scored.sort()
    return [n for _r, _c, n in scored[:NEAR_MISS_N]]


# ---------------------------------------------------------------------------
# telemetry: the 0% / 100% tell
# ---------------------------------------------------------------------------

def scan_telemetry(path):
    """Boolean signal rates. A signal at EXACTLY 0.0% or 100.0% over a
    meaningful sample is a SUSPECTED BROKEN EMITTER -- reported, never gated
    on. Real behavior is rarely absolute."""
    out = {"path": path, "records": 0, "malformed_lines": 0, "signals": []}
    caveats = []
    if not os.path.isfile(path):
        caveats.append("telemetry file absent at %s -- emitter check SKIPPED, "
                       "not asserted (fail open)." % ascii_safe(path))
        return out, caveats
    tallies = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    out["malformed_lines"] += 1
                    continue
                if not isinstance(rec, dict):
                    out["malformed_lines"] += 1
                    continue
                out["records"] += 1
                for k, v in rec.items():
                    if isinstance(v, bool):
                        t, n = tallies.get(k, (0, 0))
                        tallies[k] = (t + (1 if v else 0), n + 1)
    except Exception as exc:
        caveats.append("telemetry unreadable (fail open, not asserted): %s"
                       % ascii_safe(exc))
        return out, caveats

    for name in sorted(tallies):
        true_n, n = tallies[name]
        pct = round(100.0 * true_n / n, 1) if n else None
        absolute = n > 0 and (true_n == 0 or true_n == n)
        flagged = bool(absolute and n >= MIN_TELEMETRY_SAMPLE)
        out["signals"].append({
            "signal": name, "true": true_n, "n": n, "pct": pct,
            "flagged": flagged,
            "note": ("SUSPECTED BROKEN EMITTER: exactly %s%% over %d records -- "
                     "treat as a measurement artifact until the predicate is "
                     "verified against real captured data, NOT as a behavior "
                     "finding" % (("0.0" if true_n == 0 else "100.0"), n))
                    if flagged else
                    ("absolute but sample %d < %d -- not asserted"
                     % (n, MIN_TELEMETRY_SAMPLE)) if absolute else "",
        })
    if out["malformed_lines"]:
        caveats.append("%d malformed telemetry line(s) skipped."
                       % out["malformed_lines"])
    return out, caveats


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def load_literals(paths, want_tests):
    """(literals, caveats) -- an unparseable file is a caveat, never a crash."""
    lits, caveats = [], []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except Exception as exc:
            caveats.append("source unreadable (not asserted): %s -- %s"
                           % (ascii_safe(p), ascii_safe(exc)))
            continue
        try:
            found = extract_literals(p, src)
        except SyntaxError as exc:
            caveats.append("source unparseable, SKIPPED (not asserted): %s -- %s"
                           % (ascii_safe(p), ascii_safe(exc)))
            continue
        except Exception as exc:
            caveats.append("source could not be analysed (not asserted): "
                           "%s -- %s" % (ascii_safe(p), ascii_safe(exc)))
            continue
        markers = marker_lines(src)
        for lit in found:
            lit.context = (lit.context, marker_for(markers, lit.line))
        lits.extend(found)
    return lits, caveats


def analyse(code_lits, test_lits, vocab, corpus_stats):
    """Rank every zero-occurrence literal. Returns (findings, suppressed,
    caveats)."""
    findings, suppressed, caveats = [], [], []

    measured_slots = set(s for s in SLOT_ORDER
                         if len(vocab[s]) >= MIN_SLOT_VOCAB)
    unmeasured_counts = {}
    unassertable_counts = {}

    # what a fixture asserts on: literal -> [(file, line, slot)]
    fixture_index = {}
    for lit in test_lits:
        fixture_index.setdefault(lit.value, []).append(lit)

    # which (file, slot) pairs have at least one literal reality DOES emit --
    # proof the file's branch on that slot is live, which makes a dead sibling
    # in the same file materially more suspicious.
    live_file_slots = set()
    for lit in code_lits:
        if lit.slot in measured_slots and lit.value in vocab[lit.slot]:
            live_file_slots.add((lit.path, lit.slot))

    grouped = {}
    for lit in code_lits:
        grouped.setdefault(lit.key(), []).append(lit)

    for (value, slot), sites in sorted(grouped.items()):
        marker = next((s.context[1] for s in sites if s.context[1]), None)
        if marker:
            suppressed.append({
                "literal": value, "slot": slot, "reason": "marker: " + marker,
                "sites": [{"file": s.path, "line": s.line} for s in sites]})
            continue
        if value in ALLOWLIST:
            suppressed.append({
                "literal": value, "slot": slot,
                "reason": "allowlist: " + ALLOWLIST[value],
                "sites": [{"file": s.path, "line": s.line} for s in sites]})
            continue
        if slot not in CODE_ASSERTABLE_SLOTS:
            unassertable_counts[slot] = unassertable_counts.get(slot, 0) + 1
            continue
        if slot not in measured_slots:
            unmeasured_counts[slot] = unmeasured_counts.get(slot, 0) + 1
            continue
        if value in vocab[slot]:
            continue

        # --- absent from a measured slot: rank it ---
        other_slot = next((s for s in SLOT_ORDER
                           if s != slot and s in measured_slots
                           and value in vocab[s]), None)
        fixtures = [f for f in fixture_index.get(value, [])
                    if f.slot == slot or f.slot == SLOT_NAME
                    or slot == SLOT_NAME]
        if fixtures:
            confidence = "CONFIRMED"
            why = ("code and fixture agree on a name the corpus has NEVER "
                   "emitted -- the test certifies a dead branch")
        elif value.startswith("mcp__"):
            confidence = "LOW"
            why = ("MCP-scoped name: a connector this user has never invoked "
                   "is not a defect")
        elif other_slot:
            confidence = "MEDIUM"
            why = ("absent from the %s slot but present as %s -- likelier an "
                   "over-narrow slot inference by this probe than a dead "
                   "branch" % (slot, other_slot))
        elif (sites[0].path, slot) in live_file_slots:
            confidence = "HIGH"
            why = ("sibling literals in the same file DO occur, so this slot "
                   "is demonstrably live here and this name alone is dead")
        else:
            confidence = "MEDIUM"
            why = ("zero occurrences, but no live sibling in the same file to "
                   "prove the slot fires here at all")

        findings.append({
            "literal": value,
            "slot": slot,
            "confidence": confidence,
            "why": why,
            "code": [{"file": s.path, "line": s.line, "context": s.context[0]}
                     for s in sorted(sites, key=lambda x: (x.path, x.line))],
            "fixtures": [{"file": f.path, "line": f.line, "slot": f.slot}
                         for f in sorted(fixtures,
                                         key=lambda x: (x.path, x.line))],
            "near_misses": near_misses(value, vocab[slot]),
            "observed_slot_top": sorted(vocab[slot].items(),
                                        key=lambda kv: (-kv[1], kv[0]))[:SLOT_TOP_N],
            "slot_vocab_size": len(vocab[slot]),
        })

    rank = {"CONFIRMED": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: (rank.get(f["confidence"], 9), f["slot"],
                                 f["literal"]))

    for slot in SLOT_ORDER:
        n = unassertable_counts.get(slot, 0)
        if n:
            caveats.append(
                "slot '%s' is NOT ASSERTABLE from code (the generic name slot "
                "is overloaded here -- git refs, file names, task ids -- while "
                "the corpus's name vocabulary is only the tool/agent/MCP name "
                "space) -- %d code literal(s) in that slot were NOT asserted. "
                "See CODE_ASSERTABLE_SLOTS." % (slot, n))
    for slot in SLOT_ORDER:
        n = unmeasured_counts.get(slot, 0)
        if n:
            caveats.append(
                "slot '%s' UNMEASURED (thin vocabulary: %d distinct name(s) "
                "observed, floor %d) -- %d code literal(s) in that slot were "
                "NOT asserted. Transcripts record tool names, not hook "
                "payloads, so this is expected for hook_event_name."
                % (slot, len(vocab[slot]), MIN_SLOT_VOCAB, n))
    return findings, suppressed, caveats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv):
    opts = {"quiet": False, "json": False, "corpus": DEFAULT_CORPUS,
            "code_roots": DEFAULT_CODE_ROOTS, "test_roots": DEFAULT_TEST_ROOTS,
            "telemetry": DEFAULT_TELEMETRY, "max_corpus_files": None}
    for a in argv:
        if a == "--quiet":
            opts["quiet"] = True
        elif a == "--json":
            opts["json"] = True
        elif a.startswith("--corpus="):
            opts["corpus"] = a.split("=", 1)[1]
        elif a.startswith("--code-roots="):
            opts["code_roots"] = [p for p in a.split("=", 1)[1].split(",") if p]
        elif a.startswith("--test-roots="):
            opts["test_roots"] = [p for p in a.split("=", 1)[1].split(",") if p]
        elif a.startswith("--telemetry="):
            opts["telemetry"] = a.split("=", 1)[1]
        elif a.startswith("--max-corpus-files="):
            try:
                opts["max_corpus_files"] = int(a.split("=", 1)[1])
            except ValueError:
                print("[ACTION] --max-corpus-files needs an integer: %s"
                      % ascii_safe(a))
                return None
        elif a in ("-h", "--help"):
            print(__doc__)
            return None
        else:
            # A typo'd flag must never be silently ignored by a probe whose
            # whole point is that silence is the failure mode.
            print("[ACTION] unknown option: %s (known: --quiet --json "
                  "--corpus= --code-roots= --test-roots= --telemetry= "
                  "--max-corpus-files=)" % ascii_safe(a))
            return None
    return opts


def build_report(opts):
    caveats = []
    vocab, corpus_stats, c1 = scan_corpus(opts["corpus"],
                                          opts["max_corpus_files"])
    caveats.extend(c1)

    test_paths = iter_py(opts["test_roots"], want_tests=True)
    code_paths = iter_py(opts["code_roots"], want_tests=False,
                         exclude_dirs=opts["test_roots"])
    code_lits, c2 = load_literals(code_paths, want_tests=False)
    test_lits, c3 = load_literals(test_paths, want_tests=True)
    caveats.extend(c2)
    caveats.extend(c3)

    if corpus_stats["measured"]:
        findings, suppressed, c4 = analyse(code_lits, test_lits, vocab,
                                           corpus_stats)
        caveats.extend(c4)
    else:
        findings, suppressed = [], []
        caveats.append("no findings asserted: the corpus could not be "
                       "measured, so absence cannot be distinguished from "
                       "ignorance.")

    telemetry, c5 = scan_telemetry(opts["telemetry"])
    caveats.extend(c5)

    confirmed = [f for f in findings if f["confidence"] == "CONFIRMED"]
    return {
        "probe": "fixture-reality-probe",
        "corpus": {
            "root": opts["corpus"],
            "files": corpus_stats["files"],
            "lines": corpus_stats["lines"],
            "bytes": corpus_stats["bytes"],
            "malformed_lines": corpus_stats["malformed_lines"],
            "unreadable": corpus_stats["unreadable"],
            "measured": corpus_stats["measured"],
            "vocab_sizes": dict((s, len(vocab[s])) for s in SLOT_ORDER),
        },
        "scanned": {
            "code_files": len(code_paths),
            "code_literals": len(code_lits),
            "test_files": len(test_paths),
            "test_literals": len(test_lits),
        },
        "findings": findings,
        "suppressed": suppressed,
        "telemetry": telemetry,
        "caveats": caveats,
        "exit": 1 if confirmed else 0,
    }


def print_human(rep, quiet):
    conf = [f for f in rep["findings"] if f["confidence"] == "CONFIRMED"]
    flagged = [s for s in rep["telemetry"]["signals"] if s["flagged"]]
    if quiet and not conf and not flagged:
        return
    c = rep["corpus"]
    print("fixture-reality-probe -- REPORT ONLY, nothing was modified.")
    print("  corpus: %d file(s), %d line(s), %.1f MB, measured=%s "
          "(vocab: tool=%d event=%d name=%d)"
          % (c["files"], c["lines"], c["bytes"] / 1048576.0, c["measured"],
             c["vocab_sizes"][SLOT_TOOL], c["vocab_sizes"][SLOT_EVENT],
             c["vocab_sizes"][SLOT_NAME]))
    s = rep["scanned"]
    print("  scanned: %d code file(s) -> %d name predicate(s); %d test file(s) "
          "-> %d fixture literal(s)"
          % (s["code_files"], s["code_literals"], s["test_files"],
             s["test_literals"]))

    if rep["findings"]:
        print("\nZERO-OCCURRENCE NAME PREDICATES (%d), ranked:"
              % len(rep["findings"]))
        for f in rep["findings"]:
            print("  [%s] %r in slot %s -- %s"
                  % (f["confidence"], ascii_safe(f["literal"]), f["slot"],
                     f["why"]))
            for site in f["code"]:
                print("        code    %s:%d (%s)"
                      % (ascii_safe(site["file"]), site["line"],
                         site["context"]))
            for site in f["fixtures"]:
                print("        FIXTURE %s:%d (slot %s) <-- agrees with the code"
                      % (ascii_safe(site["file"]), site["line"], site["slot"]))
            if f["near_misses"]:
                print("        near-miss (ADVISORY, never widen a match): %s"
                      % ascii_safe(", ".join(f["near_misses"])))
            top = ", ".join("%s x%d" % (ascii_safe(n), k)
                            for n, k in f["observed_slot_top"])
            print("        slot really emits: %s" % top)
    else:
        print("\nZERO-OCCURRENCE NAME PREDICATES: none.")

    if rep["suppressed"]:
        print("\nSUPPRESSED (%d) -- excluded WITH a reason on record:"
              % len(rep["suppressed"]))
        for s2 in rep["suppressed"]:
            print("  %r (%s): %s"
                  % (ascii_safe(s2["literal"]), s2["slot"],
                     ascii_safe(s2["reason"])))

    t = rep["telemetry"]
    print("\nTELEMETRY EMITTER CHECK (%d record(s) at %s):"
          % (t["records"], ascii_safe(t["path"])))
    if flagged:
        for s2 in flagged:
            print("  [SUSPECTED BROKEN EMITTER] %s = %s%% (%d/%d) -- %s"
                  % (s2["signal"], s2["pct"], s2["true"], s2["n"],
                     s2["note"]))
        print("  (report-only: a suspected emitter never fails this probe)")
    else:
        rates = ", ".join("%s %s%%" % (s2["signal"], s2["pct"])
                          for s2 in t["signals"])
        print("  no signal at exactly 0.0%% or 100.0%% over >= %d records. %s"
              % (MIN_TELEMETRY_SAMPLE, rates or "(no boolean signals)"))

    if rep["caveats"]:
        print("\nCAVEATS (%d) -- what this run did NOT assert:"
              % len(rep["caveats"]))
        for cv in rep["caveats"]:
            print("  - %s" % ascii_safe(cv))

    if conf:
        print("\nCONFIRMED FIXTURE-SHAPED PREDICATE(S): %d. A test is "
              "certifying a dead branch." % len(conf))
    else:
        print("\nOK -- no CONFIRMED fixture-shaped predicate.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = parse_args(argv)
    if opts is None:
        return 0
    try:
        rep = build_report(opts)
    except Exception as exc:                      # fail open, loudly
        print("[ACTION] fixture-reality-probe failed internally and asserted "
              "NOTHING: %s" % ascii_safe(exc))
        return 0
    if opts["json"]:
        print(json.dumps(rep, indent=2, sort_keys=False, default=str))
    else:
        print_human(rep, opts["quiet"])
    return rep["exit"]


if __name__ == "__main__":
    sys.exit(main())
