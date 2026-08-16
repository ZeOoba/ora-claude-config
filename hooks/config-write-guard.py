"""Governance-layer hard write-gate + chip claim-lock -- PreToolUse hook.

WHY (2026-07-18, write-guard architecture hardening, Plan 5). Before this hook,
hooks/**, settings.json and CLAUDE.md had NO hard write-gate -- only soft heuristics
(eos-plan-gate.py's 4-edit threshold, eos-claude-md-guard.py's word-budget check).
One bad edit to confidentiality-guard.py or ora-autonomy-gate.py could silently
disable the entire governance layer. This gate makes that edit LOUD: it requires
Gabriel's explicit in-turn confirmation, expressed through the EXISTING session-
scoped override-token mechanism (hooks/lib/override_tokens.py -- the retired flat
mtime-only sentinel stays dead; see that module's docstring for the four defects
that killed it).

WHAT IT GATES (token tier allow-config-write, scope config-write, 60 min, multi-use):
  * <root>/hooks/**            EXCEPT hooks/sessions/**, hooks/state/**, and
                               hooks/active-work/** (SELF-DEADLOCK DEFENSE: the
                               override token itself lives at
                               hooks/sessions/<sid>/overrides/ -- gating it would
                               make the gate unsatisfiable; hooks/state/ is a
                               runtime breadcrumb dir, not governance code;
                               hooks/active-work/ is claim_work.py's claim-broadcast
                               file (2026-07-26 fix) -- CLAUDE.md's own "claim ad-hoc
                               hook work before starting" doctrine was unsatisfiable
                               without this, since the claim write itself named
                               hooks/ and tripped this same gate)
  * <root>/settings.json, <root>/settings.local.json
  * <root>/CLAUDE.md
  * either fleet's scheduled-task registry backing file (defense-in-depth on top of
    registry-write-guard.py's unconditional block)
  <root> is the LIVE checkout (C:/Users/Owner/.claude) ONLY. Worktree copies
  (<root>/.claude/worktrees/**) are deliberately NOT gated: isolated-worktree
  development is the sanctioned path for hook work, a worktree copy is inert until
  merged, and the merge itself is a loud, review-visible act (see REFUTE notes in
  the 2026-07-18 build report for the residual-risk argument).

CLAIM-LOCK (rules.md sec 8, chip-claims.log): writes to <root>/handoffs/** and
<root>/workflows/** additionally require this session to HOLD an open chip claim --
a CLAIMED line naming this session, no later DONE/ABORTED for the same title, and a
CLAIMED-or-HEARTBEAT line fresher than 60 min (the documented staleness convention).

FAIL-OPEN + TTL, per the RATIFIED doctrine (feedback_fail_open_over_mutex_for_fleet_
gates, Gabriel 2026-07-16): the claim-lock ALLOWS when chip-claims.log is missing,
unreadable, malformed, or when the payload carries no session_id -- a fresh worktree
or clone (the log is untracked) must never be bricked, and absence of information is
never license to block a coordination gate. Contrast the confidentiality-guard
self-deadlock (feedback_confidentiality_guard_selfdeadlock.md): a fail-CLOSED guard
with a malformed input once bricked Write/Edit/Bash machine-wide. The TOKEN gate, by
contrast, blocks on a POSITIVE governance-path match without a token -- that is the
gate's entire point -- but any INTERNAL error in this hook still fails open (whole
body wrapped, exit 0), so a bug here can never brick a session.

EXIT CODES (reference_pretooluse_vs_git_hook_exit_codes.md -- PreToolUse family):
exit 0 = allow; exit 2 + stderr = block. NEVER exit 1 (non-blocking error: the tool
call would PROCEED, silently disabling the gate).

SHELL COVERAGE, honestly stated: Bash / DC start_process / DC interact_with_process
are matched by normalized-text markers (write indicator + governance-path marker
anywhere in the command -- the same breadth-over-precision tradeoff ora-autonomy-
gate.py Gate 2b makes deliberately; do NOT narrow it, see
feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md). Value indirection
($var, concatenation, Get-Content) remains the documented structural ceiling of
text-matching, exactly as it is for the autonomy gate.

TEST SEAMS (env vars -- TEST ONLY, never set in settings.json/scheduled tasks;
setting them in production would redirect a security gate to attacker-chosen paths,
same caveat as OVERRIDE_DIR / ORA_OVERRIDE_SESSIONS_DIR):
  ORA_CONFIG_GUARD_ROOT, ORA_CHIP_CLAIMS_LOG, and the lib's
  ORA_OVERRIDE_SESSIONS_DIR.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

DEFAULT_ROOT = r"C:\Users\Owner\.claude"

# The token contract is the SHARED one (override_tokens.py) -- do not reinvent.
# Import posture mirrors ora-autonomy-gate.py exactly (and for the same reason --
# see reference_pretooluse_vs_git_hook_exit_codes.md): letting an ImportError
# propagate would exit 1, which is NON-blocking, silently disabling this gate; a
# sys.exit(2) at import time would brick every tool call. So degrade to "no
# override exists": ungated writes still pass, every gated write blocks.
try:
    from override_tokens import Tier, describe_token, token_grants  # noqa: E402
    TOKEN_CONTRACT_LOADED = True
except Exception:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        def __init__(self, name, scope, ttl, single_use=False,
                     requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None):
        return None  # no validator -> no grant, ever

    def describe_token(session_id, tier):
        return ("  <hooks/lib/override_tokens.py could not be imported -- no "
                "override can be honored; fix the module, do not mint a token>\n")

# Tool-call shape knowledge is the shared normalization layer's job. Same degrade
# logic; without it we cannot see write targets, so nothing matches and the gate is
# inert -- but that is identical to this hook not existing (soft-heuristic status
# quo), never a NEW hole, and the coverage meta-test pins the lib's presence.
try:
    from tool_call_paths import (  # noqa: E402
        GIT_MUTATE_RE, is_shell_tool, normalize_text, recursive_delete,
        resolve_path, shell_analysis, write_targets)
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False

CONFIG_WRITE = Tier("allow-config-write", "config-write", 3600)
DESTRUCTIVE_DELETE = Tier("allow-destructive-delete", "destructive-delete", 1800)

# ------------------------------------------------- recursive tree delete (2026-08-16)
# WHY THIS CONSUMER EXISTS. tool_call_paths.recursive_delete() shipped 2026-08-14
# (PR #112) as a path-independent detector and then sat with ZERO callers -- it
# read as shipped in every changelog while `rm -rf ~/Documents/deals` stayed as
# unguarded as the day it was filed. This is the consumer that makes it real.
#
# SCOPE IS THE WHOLE DESIGN. Blocking every recursive delete would be a
# false-positive disaster across ~14.7k Bash calls: `rm -rf node_modules` and
# `rm -rf build` are routine and safe. So this blocks exactly two classes, both
# of which destroy things that are NOT reproducible:
#   1. CATASTROPHIC SCOPE -- a bare `.`, `/`, `~`, `$HOME`, `*`, or a drive root.
#      No legitimate agent-initiated use, and the blast radius is unbounded.
#   2. BUSINESS-DATA SURFACES -- anything resolving under the user's real document
#      stores (OneDrive business folders, Documents, Desktop). Hard Invariant 5
#      already requires permission to delete there, and Invariant 6 says never
#      delete at all -- move to /archive/. This makes both mechanical.
# Everything else -- relative paths, build artifacts, temp, scratchpad, worktrees
# -- is ALLOWED, deliberately. A guard people route around protects nothing.
_CATASTROPHIC_DELETE = frozenset((
    ".", "..", "/", "\\", "*", "~", "$HOME", "${HOME}", "%USERPROFILE%",
    "./", ".\\", "/*", "~/", "~/*", "$HOME/*",
))

# Reproducible build/ephemeral output. Named explicitly so a business-data rule
# can never accidentally swallow the routine case.
_EPHEMERAL_DELETE_NAMES = frozenset((
    "node_modules", "build", "dist", ".cache", "__pycache__", ".pytest_cache",
    "target", ".venv", "venv", ".next", ".turbo", "coverage", ".mypy_cache",
    ".ruff_cache", ".parcel-cache", "out", ".nyc_output", "tmp", "temp",
))

# Business-data roots, matched on the RESOLVED path so `~`, a relative walk-up,
# and a junction all land in the same place.
_PROTECTED_DATA_MARKERS = (
    os.sep + "onedrive",  # every OneDrive root, business folders included
    os.sep + "documents", os.sep + "desktop",
)

# Working areas that live UNDER a protected root but are agent working surface,
# not business data. CLAUDE.md Hard Invariant 5 names these explicitly as free
# working surface: "~/.claude, Claude_Workspace, Cowork OS, brain repo".
_DATA_EXEMPT_MARKERS = (
    os.sep + "claude_workspace" + os.sep, os.sep + "cowork os" + os.sep,
    os.sep + ".claude" + os.sep, os.sep + ".claude-worktrees" + os.sep,
    os.sep + "node_modules" + os.sep, os.sep + "appdata" + os.sep,
)


def _delete_verdict(target):
    """(reason, detail) if this recursive-delete target must be blocked, else None.

    Conservative: an unrecognized relative path returns None (allow). The two
    blocked classes are the ones where the loss is not reproducible.

    ORDERING IS LOAD-BEARING. The protected-store test runs BEFORE the ephemeral
    allowance, not after. With the checks the other way round, any business
    folder whose leaf name happened to collide with a build-artifact name --
    `.../Deals/Target`, `.../Insurance/coverage`, `~/Documents/out` -- was
    silently unprotected, because the leaf matched first and returned allow
    (independent review 2026-08-16, MAJOR 2). Reproducibility is a property of
    WHERE a directory lives, not of what it is called."""
    raw = (target or "").strip().strip("\"'")
    if not raw:
        return None
    # `x/*` deletes exactly what `x` does. Normalize the glob tail off before any
    # equivalence test, else `./*` and `${HOME}/*` slip past the literal set
    # (independent review 2026-08-16, MAJOR 3). The `.?` covers the DOTGLOB
    # spelling: `~/.*` wipes every hidden entry in the profile -- ~/.ssh,
    # ~/.gitconfig, and ~/.claude, the governance layer itself -- and was allowed
    # while `~/*` blocked (re-review 2026-08-16, MAJOR C).
    bare = re.sub(r"[\\/]\.?\*+$", "", raw.strip())
    bare = bare.rstrip("/\\") or raw
    if raw in _CATASTROPHIC_DELETE or bare in _CATASTROPHIC_DELETE:
        return ("catastrophic scope",
                "%r names an unbounded tree (cwd, filesystem or home root)" % raw)
    if re.match(r"^[A-Za-z]:[\\/]*$", bare):
        return ("catastrophic scope", "%r is a drive root" % raw)

    expanded = os.path.expandvars(os.path.expanduser(bare))
    if not os.path.isabs(expanded):
        # Relative to an unknown cwd -- not statically decidable. Documented
        # structural ceiling: `cd <data dir> && rm -rf ./X` is not caught here.
        return None
    resolved = resolve_path(expanded)
    low = resolved.lower().rstrip("\\/")

    # ANCESTOR DELETE. A substring test alone let `rm -rf C:/Users/Owner` through
    # -- it contains no protected marker itself, yet destroys Documents, Desktop,
    # OneDrive and ~/.claude wholesale, while `rm -rf ~` (the same tree, spelled
    # differently) blocked. Anything at or above the profile root is catastrophic
    # (independent review 2026-08-16, MAJOR 4).
    profile = resolve_path(os.path.expanduser("~")).lower().rstrip("\\/")
    if profile and (low == profile or profile.startswith(low + os.sep)):
        return ("catastrophic scope",
                "%r is at or above the user profile root (%s)" % (raw, resolved))

    if any(m in low for m in _DATA_EXEMPT_MARKERS):
        return None
    if any(m in low for m in _PROTECTED_DATA_MARKERS):
        return ("business-data surface",
                "%r resolves into a protected document store (%s)" % (raw, resolved))
    if os.path.basename(low) in _EPHEMERAL_DELETE_NAMES:
        return None  # reproducible build output OUTSIDE any protected store
    return None

CLAIM_TTL_SECONDS = 3600  # rules.md sec 8: <60 min old = active claim/heartbeat
REGISTRY_BASENAME = "scheduled-tasks.json"
CC_SEGMENT = "claude-code-sessions"
LAMS_SEGMENT = "local-agent-mode-sessions"


def guard_root():
    return os.environ.get("ORA_CONFIG_GUARD_ROOT") or DEFAULT_ROOT


def claims_log_path():
    return os.environ.get("ORA_CHIP_CLAIMS_LOG") or \
        os.path.join(guard_root(), "chip-claims.log")


def _norm(p):
    """Forward-slash, lower-cased, junction-resolved absolute form for matching.

    REFUTE 2026-07-22: Win32's CreateFile silently strips trailing '.'/' '
    characters from a path's FINAL component -- "CLAUDE.md." and "CLAUDE.md"
    are the SAME file on disk, but os.path.realpath() does not replicate that
    stripping, so a raw comparison sees them as different paths. Confirmed
    this already bypassed the live hook for a plain structured Write call
    (file_path="<root>/CLAUDE.md.") -- pre-existing, not introduced by any
    single call site, so fixed once here for every caller (classify_path's
    structured file-tool targets AND _shell_absolute_hits' shell-text
    tokens)."""
    try:
        resolved = os.path.realpath(p)
    except (OSError, ValueError):
        resolved = os.path.abspath(p)
    normalized = resolved.replace("\\", "/").lower().rstrip("/")
    head, sep, tail = normalized.rpartition("/")
    stripped_tail = tail.rstrip(". ")
    if stripped_tail and stripped_tail != tail:
        normalized = head + sep + stripped_tail
    return normalized


# ------------------------------------------------------------------ path classifiers
def _classify(norm_path, root):
    """('governance', label) | ('claim', label) | None for a normalized path."""
    hooks_root = root + "/hooks"
    if norm_path == hooks_root or norm_path.startswith(hooks_root + "/"):
        rel = norm_path[len(hooks_root):]
        if rel.startswith("/sessions/") or rel == "/sessions" \
                or rel.startswith("/state/") or rel == "/state" \
                or rel.startswith("/active-work/") or rel == "/active-work":
            return None  # exempt: token/runtime state/claim-broadcast -- self-deadlock defense
        return ("governance", "hooks/** (live governance code)")
    for base, label in (("settings.json", "settings.json"),
                        ("settings.local.json", "settings.local.json"),
                        ("claude.md", "CLAUDE.md")):
        if norm_path == root + "/" + base:
            return ("governance", label)
    parts = norm_path.split("/")
    if parts and parts[-1] == REGISTRY_BASENAME and \
            (CC_SEGMENT in parts or LAMS_SEGMENT in parts):
        return ("governance", "scheduled-task registry (%s)" %
                (CC_SEGMENT if CC_SEGMENT in parts else LAMS_SEGMENT))
    for sub, label in (("/handoffs", "handoffs/**"), ("/workflows", "workflows/**")):
        base = root + sub
        if norm_path == base or norm_path.startswith(base + "/"):
            return ("claim", label)
    return None


def classify_path(raw_path):
    return _classify(_norm(raw_path), _norm(guard_root()))


# ------------------------------------------------------------------ shell classifiers
# Markers matched ANYWHERE in a normalized (NFKC + Cf/Mn-stripped, lowercased,
# forward-slashed) command that also carries a write indicator. Exempt markers are
# blanked FIRST so a token write into hooks/sessions/ never trips the hooks marker.
# Breadth over precision: a false positive costs a retry; a false negative silently
# edits the governance layer.
def _shell_marker_sets():
    root = _norm(guard_root())
    # The generic ".claude"/"~/.claude" spellings are ALWAYS armed, not only when
    # the root is the live default: a command can reach the live tree via tilde or
    # relative form regardless of what the (test-seam) root is, and the seam must
    # not weaken the matcher it is trying to test. Breadth over precision.
    generic_roots = {root, "~/.claude", ".claude"}
    exempt, governance, claim = [], [], []
    for g in generic_roots:
        exempt += [g + "/hooks/sessions", g + "/hooks/state", g + "/hooks/active-work"]
        governance += [(g + "/hooks", "hooks/**"),
                       (g + "/settings.json", "settings.json"),
                       (g + "/settings.local.json", "settings.local.json"),
                       (g + "/claude.md", "CLAUDE.md")]
        claim += [(g + "/handoffs", "handoffs/**"),
                  (g + "/workflows", "workflows/**")]
    # worktree trees are exempt (see module docstring) -- blank them before the
    # governance markers can see their .../hooks/... segments
    exempt = [g + "/worktrees" for g in generic_roots] + exempt
    return exempt, governance, claim


def _blank_exempt(text, exempt_markers):
    """Blank the ENTIRE whitespace-delimited token containing an exempt marker, so
    an exempted path (a worktree tree, a hooks/sessions token write) contributes
    NOTHING to later marker/root matching -- not even its root prefix."""
    for marker in exempt_markers:
        text = re.sub(r"\S*" + re.escape(marker) + r"\S*", " <exempt> ", text)
    return text


# BUG (2026-07-21, reproduced in the oxford-command-center worktree
# fix-refute-workflow-em-dash): marker matching was a bare `marker in text`
# substring check with no token-boundary awareness and no notion of "this
# occurrence sits inside a provably-different absolute path." Two live
# consequences: (1) the bare ".claude" root-mention matched as a text-prefix of
# the unrelated ".claude-worktrees" directory (this environment's actual
# repo-local worktree naming convention -- dash-joined, NOT the nested
# "<root>/worktrees" form already exempted); (2) a generic ".claude/workflows"
# marker fired on a fully drive-qualified absolute path under a DIFFERENT
# repo's own .claude/workflows/, which cannot resolve to the live root under
# any shell cwd. Both are fixed by the same helper below.
_PATH_WORD_RE = re.compile(r"[\w.-]")
# CODE REVIEW FINDING (2026-07-22): the excluded-character set stopped only at
# whitespace/quotes/<>/| -- not at the shell sequencing/substitution/grouping
# metacharacters (; & ` $ ( )) that ALSO terminate an unquoted token in both
# POSIX shells and cmd.exe. `cp x.py <root>/CLAUDE.md;echo pwned` glued a
# trailing shell construct directly onto the token, producing a corrupted
# path that failed _classify's EXACT-EQUALITY check for the single-file
# targets (settings.json/settings.local.json/CLAUDE.md) while _marker_matches
# skipped it on the assumption the absolute-token path already handled it --
# neither path fired. Confirmed a genuine regression (the original
# bare-substring matcher was not fooled by this, since ";echo" doesn't change
# whether "claude.md" is a substring of the corrupted string).
_ABS_PATH_TOKEN_RE = re.compile(r"[a-z]:/[^\s\"'<>|;&`$()]*")


def _boundary_ok(text, start, end):
    """True if `text[start:end]` is not glued to more path-word characters on
    either side (so ".claude" does not match inside ".claude-worktrees")."""
    before_ok = start == 0 or not _PATH_WORD_RE.match(text[start - 1])
    after_ok = end == len(text) or not _PATH_WORD_RE.match(text[end])
    return before_ok and after_ok


def _absolute_token_containing(text, idx):
    """The maximal drive-qualified absolute path token overlapping index `idx`,
    or None if `idx` is not inside one (e.g. a bare relative or tilde form)."""
    for m in _ABS_PATH_TOKEN_RE.finditer(text):
        if m.start() <= idx < m.end():
            return m.group(0)
    return None


def _shell_absolute_hits(text, root):
    """Classify every drive-qualified absolute path token in `text` through
    the SAME real-path resolution used for structured file-tool targets
    (_norm + _classify) -- os.path.realpath, not a hand-rolled string-prefix
    comparison. REFUTE 2026-07-21 (adversarial pass): an earlier version of
    this fix compared token PREFIXES as strings, which a lexical '..' segment
    defeats -- `<root>/nonexistent_dir/../hooks/evil.py` is a different
    STRING than `<root>/hooks/evil.py` but the same live file (Windows/cmd
    collapses '..' with no existence check on the intermediate segment,
    live-proven by redirect). Reusing _norm()/_classify() sidesteps that
    class of bug entirely: realpath() does the same collapsing the OS does,
    so a token that lexically resolves onto the live root is caught, and a
    token that genuinely resolves under a different root (an unrelated
    repo's own .claude/workflows/) is correctly cleared -- exactly the
    behavior already trusted for every native Write/Edit/DC file-tool call."""
    hits = []
    for m in _ABS_PATH_TOKEN_RE.finditer(text):
        cls = _classify(_norm(m.group(0)), root)
        if cls:
            hits.append(cls)
    return hits


def _marker_matches(text, marker):
    """True if some BOUNDARY-CORRECT occurrence of `marker` exists in `text`
    that is NOT inside a drive-qualified absolute path token (those are
    classified separately and more accurately by _shell_absolute_hits). A
    bare-relative or tilde-form occurrence is genuinely ambiguous -- it
    depends on an unknown shell cwd -- and stays armed (breadth over
    precision). A glued-substring occurrence (fails the boundary check, e.g.
    ".claude" inside ".claude-worktrees") is not a real occurrence."""
    start = 0
    while True:
        idx = text.find(marker, start)
        if idx == -1:
            return False
        end = idx + len(marker)
        start = idx + 1
        if not _boundary_ok(text, idx, end):
            continue
        if _absolute_token_containing(text, idx) is not None:
            continue  # handled by _shell_absolute_hits instead
        return True


# BUG (2026-07-21, same session): classify_shell scanned an ENTIRE heredoc body
# for markers, even though a heredoc body is DATA being written into a file
# (e.g. a commit message authored via `cat <<'EOF' > msg.txt`), not a path any
# command argument names. A commit message that merely MENTIONED hooks/** in
# prose tripped the governance marker. The body is blanked before marker
# scanning; the opening line (which carries any real `> target` redirect) and
# everything after the closing delimiter are left untouched, so a heredoc
# actually used to write INTO a governance path is still caught via its
# redirect target.
_HEREDOC_RE = re.compile(
    r"<<-?\s*['\"]?([a-zA-Z0-9_]+)['\"]?[^\n]*\n"  # opening line, through \n
    r".*?\n"                                        # body (non-greedy)
    r"[ \t]*\1(?=[ \t\r\n]|$)",                     # closing delimiter line
    re.DOTALL,
)


def _strip_heredoc_bodies(text):
    def _blank(m):
        opening_line = m.group(0).split("\n", 1)[0] + "\n"
        return opening_line + " <heredoc-body> \n" + m.group(1)
    return _HEREDOC_RE.sub(_blank, text)


# --- quoting/escaping normalization (2026-08-05) -----------------------------
# Two live bypasses closed here, both previously documented as open in
# memory/reference_config_write_guard_quote_split_gap.md and deliberately left
# unfixed because a full shell tokenizer was judged too large a change:
#
#   1. QUOTE-SPLIT.  `cp x.json "<root>"/hooks/evil.py` -- the quote characters
#      break what the OS sees as one contiguous path into fragments, so
#      _ABS_PATH_TOKEN_RE never matches a drive-qualified token and the lexical
#      markers never see a contiguous ".claude/hooks" either. The shell strips
#      the quotes before the FS ever sees the path.
#   2. CARET-ESCAPE.  `echo x > <root>/CLA^UDE.md` -- in cmd.exe `^` escapes the
#      next character and is removed at parse time, so `CLAUDE.md` reaches the
#      filesystem while the matcher only ever sees `CLA^UDE.md`.
#
# THE APPROACH IS UNION-ONLY, DELIBERATELY.  Rather than tokenizing (which risks
# *losing* detections when the tokenizer disagrees with the real shell -- the
# exact failure mode that produced the 2026-08-03 security regression, where a
# boundary fix un-flagged real composite writers like `robocopy /MIR`), each
# normalization produces an ADDITIONAL variant of the command text and every
# variant is scanned. A variant can only ever ADD a hit, never remove one, so no
# previously-caught command can become allowed by this change. The cost is the
# opposite risk -- over-blocking -- which the negative controls in the
# differential battery exist to bound.
#
# Variants are deduped, so the overwhelmingly common case (a command containing
# neither a quote nor a caret) collapses to exactly one scan and pays nothing.
_CARET_ESCAPE_RE = re.compile(r"\^(.)", re.DOTALL)


def _decaret(text):
    """cmd.exe caret-escape removal: `^X` -> `X` (and `^^` -> a literal `^`)."""
    return _CARET_ESCAPE_RE.sub(r"\1", text)


def _dequote(text):
    """Drop quote CHARACTERS only, preserving every other character including
    whitespace -- so two genuinely separate quoted arguments stay separated by
    their space and cannot be glued into one spurious governance-looking path."""
    return text.replace('"', "").replace("'", "")


def _shell_variants(text):
    """Deduped normalization variants of a shell command, each defeating one
    quoting/escaping trick. Order is irrelevant (hits are unioned)."""
    variants = []
    for candidate in (text, _dequote(text), _decaret(text),
                      _decaret(_dequote(text))):
        if candidate not in variants:
            variants.append(candidate)
    return variants


def _classify_shell_variant(text, live_root, governance, claim):
    """(governance_hit_or_None, claim_hit_or_None) for ONE normalized variant.

    This is the pre-2026-08-05 classify_shell body, unchanged in substance and
    with its original precedence intact; it is factored out so every variant can
    be scanned with identical logic."""
    # Every drive-qualified absolute path token gets classified through the
    # real-path resolver first -- more accurate than lexical marker matching
    # for anything absolute (handles '..', clears a genuinely different root).
    abs_hits = _shell_absolute_hits(text, live_root)
    gov = next((h for h in abs_hits if h[0] == "governance"), None)
    if gov is None:
        for marker, label in governance:
            if _marker_matches(text, marker):
                gov = ("governance", label)
                break
    if gov is None and REGISTRY_BASENAME in text and (
            CC_SEGMENT in text or LAMS_SEGMENT in text):
        gov = ("governance", "scheduled-task registry")
    # file-rewriting git aimed anywhere at the live checkout (REFUTE 2026-07-18:
    # `git -C ~/.claude checkout main -- hooks/` rewrote the live hook layer with
    # neither a classic write verb nor a contiguous ".claude/hooks" marker in its
    # text -- live-proven). Read-only git passes; `git -C ~/.claude checkout -b
    # feature` false-positives and costs a retry/token -- breadth over precision.
    # (Absolute-path forms of this same case are already caught above via
    # abs_hits -- this is the coarser "root mentioned anywhere, split across
    # unrelated arguments" signal for forms like `-C ~/.claude ... hooks/`.)
    if gov is None:
        root_mentions = (live_root, "~/.claude", ".claude")
        if GIT_MUTATE_RE.search(text) and any(
                _marker_matches(text, r) for r in root_mentions):
            gov = ("governance",
                   "file-rewriting git command referencing the live "
                   "~/.claude checkout")
    clm = next((h for h in abs_hits if h[0] == "claim"), None)
    if clm is None:
        for marker, label in claim:
            if _marker_matches(text, marker):
                clm = ("claim", label)
                break
    return gov, clm


def classify_shell(command):
    """('governance'|'claim', label) for a write-shaped shell command naming a
    protected path, else None.

    Scans every quoting/escaping variant (see _shell_variants). Governance
    precedence is preserved ACROSS variants: a governance hit found in any
    variant outranks a claim hit found in any other, matching the original
    single-pass ordering."""
    if not TOOL_PATHS_LOADED:
        return None
    base = normalize_text(command).replace("\\", "/").lower()
    base = _strip_heredoc_bodies(base)
    exempt, governance, claim = _shell_marker_sets()
    live_root = _norm(guard_root())

    first_claim = None
    for variant in _shell_variants(base):
        text = _blank_exempt(variant, exempt)
        gov, clm = _classify_shell_variant(text, live_root, governance, claim)
        if gov:
            return gov
        if clm and first_claim is None:
            first_claim = clm
    return first_claim


# ------------------------------------------------------------------ claim-lock
def _parse_ts(ts):
    try:
        dt = datetime.fromisoformat(ts.strip())
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt
    except Exception:
        return None


def session_holds_open_claim(session_id, log_path):
    """True: session holds a fresh open claim. False: log is readable and shows no
    such claim. None: log missing/unreadable/malformed or no session_id -- the
    caller must FAIL OPEN on None (ratified fail-open + TTL doctrine)."""
    if not isinstance(session_id, str) or len(session_id) < 8:
        return None
    try:
        if not os.path.isfile(log_path):
            return None
        with open(log_path, "r", encoding="utf-8", errors="strict") as fh:
            raw = fh.read()
    except Exception:
        return None
    ids = (session_id.lower(), session_id.lower()[:8])
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue  # tolerate a stray malformed line without failing the parse
        status = parts[1].split()[0].upper() if parts[1] else ""
        who = "|".join(parts[3:]).lower()
        entries.append((parts[0], status, parts[2], who))
    if not entries:
        return None  # nothing parseable at all -> treat as malformed -> fail open
    now = datetime.now(timezone.utc).astimezone()
    open_titles = {}
    for ts, status, title, who in entries:  # file order == append order
        mine = any(s in who for s in ids)
        if status in ("CLAIMED", "HEARTBEAT"):
            if mine:
                open_titles[title] = ts
        elif status in ("DONE", "ABORTED"):
            open_titles.pop(title, None)  # closed by anyone, incl. another session
    for title, ts in open_titles.items():
        dt = _parse_ts(ts)
        if dt is None:
            return True  # unparseable timestamp on MY claim -> fail toward open
        if now - dt <= timedelta(seconds=CLAIM_TTL_SECONDS):
            return True
    return False


# ------------------------------------------------------------------ blocks
def _block_governance(label, detail, session_id):
    sys.stderr.write(
        "BLOCKED (config-write-guard): write to the live governance layer -- %s\n"
        "  target: %s\n"
        "A single unreviewed edit here can silently disable the whole hook/gate "
        "layer, so this write requires Gabriel's explicit in-turn confirmation "
        "(token tier allow-config-write).\n"
        "IF THIS WAS A READ, NOT A WRITE (added 2026-07-24): do NOT mint a token. "
        "This matcher is 'write indicator + governance-path marker anywhere in the "
        "command', breadth over precision and deliberately NOT narrowed (see "
        "feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md) -- so an "
        "interpreter one-liner such as `python -c \"...\"` that merely NAMES a "
        "governance path reads as write-shaped even when it only reads, because a "
        "script's actual behavior is not statically decidable. Minting "
        "allow-config-write to satisfy a read would grant 60 min of multi-use WRITE "
        "access to the entire governance layer -- strictly worse than the read you "
        "wanted. Instead use the Read/Grep/Glob tools (never gated), or run the read "
        "without naming the governance tree in the command text.\n"
        # ADDED 2026-08-12. The two exits above cover "it was a read" and "it is a
        # real edit"; neither fits the case that keeps firing in practice --
        # INVOKING a governance CLI whose writes land in paths this guard already
        # exempts. eos-review-gate's own block text hands the operator
        # `eos-review-gate.py --record ... --notes "<prose>"`, and review prose
        # routinely carries an ASCII arrow, so the sanctioned way to clear the
        # review gate is blocked here -- with minting a governance-WIDE token as
        # the only named exit. That is the same "false positive forces a strictly
        # broader privilege" regression tool_call_paths.py's 2026-08-03 word
        # anchoring was written to kill (it fixed the `--model ` -> "del " half of
        # this identical deadlock; the ">" half is not fixable in the matcher --
        # `echo x ->f` is a real redirect -- so it is fixed here, in the guidance).
        "IF THIS WAS A GOVERNANCE-TOOL INVOCATION, NOT AN EDIT (added 2026-08-12): "
        "do NOT mint a token either. The write indicator is often PROSE rather than "
        "a verb -- '>' matches inside an ASCII arrow, so "
        "`eos-review-gate.py --record ... --notes \"199/204 -> 204/204\"` reads as a "
        "redirect while the live script path supplies the governance marker (the "
        "arrow stays armed on purpose: `echo x ->f` IS a real redirect that "
        "truncates f). The matcher also reads the WHOLE command, so a governance "
        "path paired with an unrelated write (`...; rm -f <scratch file>`) trips it "
        "-- split them into separate calls. Governance CLIs (eos-review-gate.py "
        "--record, lib/claim_work.py claim|release|renew) resolve their write "
        "targets absolutely, into hooks/sessions/ and hooks/active-work/ -- both "
        "EXEMPT here, as is hooks/state/ -- so re-run the "
        "command against a WORKTREE checkout's copy of the tool (worktree paths are "
        "exempt, and the tool still writes to the live tree), or reword the "
        "argument carrying the indicator.\n"
        "Preferred path for a REAL edit: do this work in an isolated worktree "
        "(git worktree add .claude/worktrees/<name>) and land it via review -- "
        "worktree copies are not gated.\n"
        "If Gabriel has just approved a LIVE edit, write this override token and "
        "retry:\n%s"
        % (label, detail, describe_token(session_id, CONFIG_WRITE)))
    sys.exit(2)


def _block_claim(label, detail, session_id, log_path):
    sys.stderr.write(
        "BLOCKED (config-write-guard): write to a claim-locked coordination path -- "
        "%s\n"
        "  target: %s\n"
        "This session holds no open chip claim (rules.md sec 8). Before writing to "
        "registry/handoff/shared-doctrine paths, claim the work: append\n"
        "  <ISO-8601 local> | CLAIMED | <chip title> | <surface>/%s\n"
        "to %s (and a matching DONE/ABORTED line on exit; HEARTBEAT every 30-45 min "
        "for long runs), then retry. If another session's CLAIMED line for the same "
        "work is <60 min old, ABORT and report the prior claim instead.\n"
        % (label, detail, (session_id or "<session>")[:8], log_path))
    sys.exit(2)


def _block_destructive_delete(reason, detail, command, session_id):
    sys.stderr.write(
        "BLOCKED (config-write-guard): recursive tree deletion -- %s\n"
        "  target: %s\n"
        "  command: %s\n"
        "Recursion is the destructive property here, not the path -- `rm -r x` "
        "destroys the tree just as thoroughly as `rm -rf x`, and nothing about "
        "this is recoverable through the Recycle Bin.\n"
        "ORA doctrine already answers this: Hard Invariant 6 says NEVER delete -- "
        "move to /archive/ -- and Hard Invariant 5 requires Gabriel's permission "
        "before any write/move/delete in the OneDrive business folders. Prefer "
        "`mv <target> <archive dir>/` over deleting; it is reversible and it keeps "
        "the audit trail.\n"
        "NOT BLOCKED, so you do not need a token for these: reproducible build "
        "output (node_modules, build, dist, .cache, __pycache__, target, .venv), "
        "anything relative to the repo you are in, scratchpad paths, and worktree "
        "checkouts. If you meant one of those, name it directly instead of a bare "
        "`.` or an absolute walk into the document store.\n"
        "If Gabriel has explicitly approved THIS deletion in-turn, write this "
        "override token and retry:\n%s"
        % (reason, detail, (command or "").strip()[:200],
           describe_token(session_id, DESTRUCTIVE_DELETE)))
    sys.exit(2)


# ------------------------------------------------------------------ main
def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""
    if not isinstance(tool_input, dict) or not TOOL_PATHS_LOADED:
        return  # nothing inspectable / no shape knowledge -> status quo, allow

    hits = []  # (kind, label, detail)
    targets = write_targets(tool_name, tool_input)
    for target in targets:
        cls = classify_path(target.raw_path)
        if cls:
            hits.append((cls[0], cls[1],
                         "%s (%s via %s)" % (target.raw_path, target.operation,
                                             tool_name)))
    if not targets and not is_shell_tool(tool_name):
        # GENERIC PATH-FIELD SCAN (REFUTE 2026-07-18): a routed tool the shape
        # registry does not model (an Excel MCP writer, a future connector's file
        # tool) must not sail through just because nobody taught the registry its
        # schema. Deny-by-default on path-shaped input fields, same direction as
        # ora-autonomy-gate check_mcp's Round 3 fix: any string field that LOOKS
        # like a path aimed at the governance layer gates the call.
        for field in ("file_path", "path", "filepath", "notebook_path",
                      "output_path", "source", "destination", "target", "dest"):
            raw = tool_input.get(field)
            if isinstance(raw, str) and raw:
                cls = classify_path(raw)
                if cls:
                    hits.append((cls[0], cls[1],
                                 "%s (field '%s' via %s)"
                                 % (raw, field, tool_name)))
    if is_shell_tool(tool_name):
        analysis = shell_analysis(tool_name, tool_input)
        if analysis is not None and analysis.may_write:
            cls = classify_shell(analysis.command)
            if cls:
                hits.append((cls[0], cls[1],
                             "shell command via %s: %s"
                             % (tool_name, analysis.command.strip()[:200])))
            # else: write-shaped but naming no protected path -- statically
            # unresolvable (value indirection etc.). Documented structural
            # ceiling, same as ora-autonomy-gate.py's HONEST LIMIT: allow.

        # RECURSIVE TREE DELETE (2026-08-16). Checked SEPARATELY from the
        # may_write branch above, and deliberately so: recursive_delete() carries
        # no path condition, which is the whole reason it exists -- the classes it
        # catches (`rm -rf .`, a walk into the document store) are destructive
        # because of what they DO, not where the governance tree happens to be.
        # Gating it behind may_write + a governance marker would reproduce exactly
        # the hole it was written to close.
        delete = recursive_delete(analysis.command) if analysis is not None else None
        if delete is not None:
            for target in delete.targets:
                verdict = _delete_verdict(target)
                if verdict is not None:
                    if token_grants(session_id, DESTRUCTIVE_DELETE) is None:
                        _block_destructive_delete(verdict[0], verdict[1],
                                                  delete.command, session_id)
                    break  # token granted -> allowed

    governance_hits = [h for h in hits if h[0] == "governance"]
    claim_hits = [h for h in hits if h[0] == "claim"]

    if governance_hits:
        kind, label, detail = governance_hits[0]
        # token_grants consumes single-use tokens, but this tier is multi-use, so
        # evaluating it exactly once per blocked-or-allowed call is safe.
        if token_grants(session_id, CONFIG_WRITE) is None:
            _block_governance(label, detail, session_id)
        return  # token granted -> allowed; claim-lock does not also apply

    if claim_hits:
        held = session_holds_open_claim(session_id, claims_log_path())
        if held is False:
            kind, label, detail = claim_hits[0]
            _block_claim(label, detail, session_id, claims_log_path())
        # True -> claim held; None -> fail open (missing/malformed log or no
        # session identity). Both allow.


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # FAIL OPEN: an internal bug must never block a tool call
    sys.exit(0)
