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
are read by TWO layers, unioned (2026-08-28 structural hardening; see the token-
layer section for the full rationale): (1) a shlex-based STRUCTURAL layer that
parses the command into argv tokens the way a real shell does and classifies each
reconstructed token via realpath resolution -- closing the quote-split / caret /
backslash-escape CLASS by construction instead of by per-spelling patches; and
(2) the historical normalized-text marker net (write indicator + governance-path
marker anywhere in the command -- the same breadth-over-precision tradeoff
ora-autonomy-gate.py Gate 2b makes deliberately; do NOT narrow it, see
feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md), kept whole as the
safety net for shapes tokenization cannot model. Value indirection ($var,
concatenation, Get-Content) remains the documented structural ceiling of static
text analysis, exactly as it is for the autonomy gate.

TEST SEAMS (env vars -- TEST ONLY, never set in settings.json/scheduled tasks;
setting them in production would redirect a security gate to attacker-chosen paths,
same caveat as OVERRIDE_DIR / ORA_OVERRIDE_SESSIONS_DIR):
  ORA_CONFIG_GUARD_ROOT, ORA_CHIP_CLAIMS_LOG, and the lib's
  ORA_OVERRIDE_SESSIONS_DIR.

Stdlib only. ASCII-only. Windows (`python`).
"""
import bisect
import json
import os
import posixpath
import re
import shlex
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
        GIT_MUTATE_RE, _FD_DUP_RE, _NULL_REDIRECT_RE, is_shell_tool,
        normalize_text, recursive_delete, resolve_path, shell_analysis,
        strip_heredoc_bodies, write_targets)
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False
# Imported SEPARATELY so a lib that predates blank_exempt_token (a partial deploy: the
# guards landing before the lib on the shared checkout) degrades to the raw pattern
# instead of tripping the import above and turning this whole guard inert.
try:
    from tool_call_paths import blank_exempt_token  # noqa: E402
except Exception:
    def blank_exempt_token(text, marker):
        return re.sub(r"\S*" + re.escape(marker) + r"\S*", " <exempt> ", text)

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
#
# ------------------------------------------------------------------------------
# THREAT MODEL, STATED NARROWLY ON PURPOSE (2026-08-16, after 4 review rounds).
#
# THIS IS A RAIL AGAINST ACCIDENTAL AND CARELESS DELETION. IT IS NOT AN
# ADVERSARIAL CONTROL, and must not be cited as one in any audit, review or
# design that assumes an agent cannot delete a protected tree.
#
# Four independent review rounds drove 10 real defects out of this code, and the
# fourth could not produce a single bypass a non-adversarial operator would
# plausibly type. What it COULD still produce, and what remains open by design:
#   rm -rf $'\057'                  ANSI-C quoting
#   P=~/Documents; rm -rf $P/deals  a variable holding the path
#   F=-rf; rm $F ~/Documents/deals  a variable holding the flags
#   echo <base64> | base64 -d | sh  any encode-then-execute form
# These are not oversights and they are not closable here. This guard matches
# PRE-EXPANSION COMMAND TEXT; the shell has unboundedly many spellings that
# expand to one operand, so no regex over that text can enumerate them. Each
# round closed a real idiom, but the tail is infinite and patching it further
# buys asymptotically nothing -- which is why round 4's explicit recommendation
# was to stop patching and narrow this claim instead.
#
# If the threat model genuinely includes an agent that INTENDS to delete, the
# enforcement point is a layer that observes post-expansion argv (an OS/audit
# hook), not pre-execution command text. Building that is a separate decision;
# pretending this is that is the failure mode worth preventing.
# ------------------------------------------------------------------------------
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


# TIME BOUND (2026-09-21). classify_shell() resolves each drive-qualified token with
# os.path.realpath from up to 3 shlex passes x 4 text variants (~7x per token), and on
# Python 3.13 realpath of a nonexistent `c:/a/a/a/...` costs O(components x length)
# until the 32,767-char path ceiling (`ls c:/a/a/...` 32KB: 4.4s; with a quote and a
# caret in the command 25.8s). The filesystem does not change inside one call, so
# classify_shell() memoizes realpath per path string for the duration of that call ONLY
# (this is None otherwise, so every other caller and every test sees no cache).
# KNOWN, ACCEPTED RESIDUAL (review 2026-09-21, accepted by Gabriel): the memo is keyed on
# the exact string, and the token layer and the lexical net hand _norm different
# SPELLINGS of one token (case-preserved vs lowered, quote-cut vs dequoted, caret vs
# decareted), so a long nonexistent drive path is still resolved up to ~5x, and each
# resolution is OS-cost (one 30KB path ~3.9s; two 30KB tokens with quote+caret ~36s).
# Path length is capped at 32,767 chars by the OS. Keying on a folded spelling would
# change behavior on case-sensitive directories, skipping realpath for long tokens
# would let a padded junction path evade the gate, and re-implementing realpath is too
# risky for a security gate, so this is NOT closed here. The pre-change cost was ~7x.
_REALPATH_MEMO = None


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
    memo = _REALPATH_MEMO
    if memo is not None and p in memo:
        resolved = memo[p]
    else:
        try:
            resolved = os.path.realpath(p)
        except (OSError, ValueError):
            resolved = os.path.abspath(p)
        if memo is not None:
            memo[p] = resolved
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
        text = blank_exempt_token(text, marker)
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
    either side (so ".claude" does not match inside ".claude-worktrees").

    A run of trailing `.`/space AFTER the marker is skipped before the boundary
    test: Win32 strips a path component's trailing dots/spaces, so `CLAUDE.md.`
    and `settings.json ` are the SAME file as the un-suffixed marker (REFUTE
    round 3, 2026-08-28 -- `_norm` already does this leaf-strip for drive/
    structured targets; this extends it to the raw-text marker path a tilde/
    relative token uses). A distinct sibling like `CLAUDE.md.backup` is NOT
    swept: after the dots comes `backup`, a path-word char, so the boundary
    still fails."""
    before_ok = start == 0 or not _PATH_WORD_RE.match(text[start - 1])
    # Skip only trailing DOTS here, not spaces: this runs over raw, un-tokenized
    # command text where a space is a TOKEN SEPARATOR (`git -C ~/.claude checkout
    # ...`), not part of a filename -- and a space already satisfies the
    # boundary test on its own (it is not a path-word char). Only a dot is a
    # path-word char that would otherwise glue. The per-token matcher
    # (_token_marker_at_boundary) skips dot AND space, because a space inside a
    # shlex token can only have come from quoting and is part of the name.
    after = end
    while after < len(text) and text[after] == ".":
        after += 1
    after_ok = after == len(text) or not _PATH_WORD_RE.match(text[after])
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
    spans = None  # (starts, ends) of the absolute tokens, computed once, on demand
    while True:
        idx = text.find(marker, start)
        if idx == -1:
            return False
        end = idx + len(marker)
        start = idx + 1
        if not _boundary_ok(text, idx, end):
            continue
        # TIME BOUND (2026-09-21): this used to re-run _ABS_PATH_TOKEN_RE.finditer from
        # offset 0 for EVERY occurrence (`c:/.claude/hooks ` * N: 64KB 5.2s). The
        # tokens are ordered and non-overlapping, so one scan + a bisect finds the
        # same "token overlapping idx" that _absolute_token_containing() does.
        if spans is None:
            found = [(m.start(), m.end()) for m in _ABS_PATH_TOKEN_RE.finditer(text)]
            spans = ([s for s, _e in found], [e for _s, e in found])
        pos = bisect.bisect_right(spans[0], idx) - 1
        if pos >= 0 and idx < spans[1][pos]:
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
# The scanner lives in hooks/lib/tool_call_paths.py (shared with lint-config-guard.py):
# the regex this used to be was O(markers * n) on unclosed `<<WORD` markers -- see
# the TIME BOUND note there. Output is byte-identical to the old regex.
def _strip_heredoc_bodies(text):
    return strip_heredoc_bodies(text)


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
# --- UNC admin-share / device-path normalization (2026-08-28, REFUTE round 4) -
# A UNC admin-share path spells the drive as `C$` (dollar), not `C:`, so NEITHER
# realpath detector fires -- `tool_call_paths._ABS_PATH_TOKEN_RE` and
# `_TOKEN_DRIVE_ABS_RE` both require a literal drive-colon -- and the token never
# reaches _norm/realpath, the resolver that collapses a trailing dot on the
# `.claude.` component and its 8.3 alias (`CLAUDE~1`). Rewriting the share/device
# prefix to a drive-qualified form routes every such spelling back through
# realpath, which already handles the dot and 8.3 collapse (verified live in
# round 4: the drive-qualified `C:\...\.claude.\...` form blocks). Covers, in
# both slash directions: `\\host\C$\` and `//host/C$/`; `\\?\UNC\host\C$\`;
# and the `\\?\C:\` / `\\.\C:\` device prefixes (stripped to `C:\`).
_UNC_DEVICE_UNC_RE = re.compile(
    r"[\\/]{2}[?.][\\/]unc[\\/][^\\/]+[\\/]([a-z])\$[\\/]", re.IGNORECASE)
_UNC_DEVICE_DRIVE_RE = re.compile(
    r"[\\/]{2}[?.][\\/]([a-z]:[\\/])", re.IGNORECASE)
_UNC_ADMIN_SHARE_RE = re.compile(
    r"[\\/]{2}[^\\/?.][^\\/]*[\\/]([a-z])\$[\\/]", re.IGNORECASE)


# Interior-component trailing dot/space strip: `.claude./hooks` -> `.claude/hooks`
# (Win32 strips a path component's trailing dots/spaces; REFUTE round 5,
# 2026-08-28). Only a dot/space RUN sitting immediately before a separator and
# immediately after a real component char is removed -- so `./x` (current dir)
# and `../x` (parent) are untouched (their dots are preceded by a separator or
# start, not a component char), and a genuinely distinct sibling like
# `.claudeX/hooks` is unaffected. Complements the leaf-dot handling in the two
# boundary matchers (which covers a dot at the END of a match, with no trailing
# separator).
#
# TIME BOUND (2026-09-21). This used to be one pattern,
#     (?<=[^\s/.\\])[.\s]*\.[.\s]*(?=[/\\])
# whose two stars over the SAME class are ambiguous, so a long dot/space run with no
# separator after it (`echo x` + "."*N + ` > out.txt`) cost O(N^2) -- 16KB 2.5s CPU
# through classify_shell(), x4 per doubling -- on every write-shaped Bash call.
# EXACT unrolling: the lookahead (`/` or `\`) is disjoint from [.\s], so a match must
# end at the end of the whole [.\s] run, and the lookbehind (not `.` or whitespace)
# forces the start to be the run's own first char. So a run is stripped iff it holds
# at least one `.` and is followed by a separator; one linear pattern finds the runs.
_INTERIOR_DOT_RE = re.compile(r"(?<=[^\s/.\\])[.\s]+(?=[/\\])")


def _strip_interior_component_dots(text):
    return _INTERIOR_DOT_RE.sub(
        lambda m: "" if "." in m.group() else m.group(), text)


def _normalize_unc(text):
    """Rewrite UNC admin-share and device-path prefixes to a drive-qualified
    form so the realpath resolver runs. Ordered so the device/UNC-device forms
    are handled before the bare admin-share pattern (whose host char class
    excludes `?`/`.` and so cannot eat a device prefix)."""
    text = _UNC_DEVICE_UNC_RE.sub(lambda m: m.group(1) + ":\\", text)
    text = _UNC_DEVICE_DRIVE_RE.sub(lambda m: m.group(1), text)
    text = _UNC_ADMIN_SHARE_RE.sub(lambda m: m.group(1) + ":\\", text)
    return text


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


# --- structural token layer (2026-08-28) --------------------------------------
# WHY. A root-cause audit of this file's git history (823375a -> 569ef4b ->
# 6281076 -> 7d01eff -> e39c4c -> 8a4d51d -> 1939bac -> 8ec80a2/9adcc5b) found a
# repeated "bypass found -> patch -> new bypass found" cycle: every patch closed
# ONE lexical spelling (mode-blind open(), .claude-inside-.claude-worktrees,
# heredoc bodies, quote/caret splitting) because path identification was done by
# regex/substring over RAW command text, and the shell has more spellings than
# any regex can enumerate. This layer closes the CLASS instead of the spelling:
# tokenize the command the way a real shell does (shlex), then classify each
# RECONSTRUCTED argv token through the same _norm/_classify realpath resolution
# already trusted for structured file-tool targets. `"<root>"/hoo\ks/evil.py`
# arrives here as the single token `<root>/hooks/evil.py`, exactly what the
# filesystem will see -- no quote-split, caret, or backslash-escape spelling
# survives tokenization, by construction rather than by enumeration.
#
# UNION-ONLY, like the 2026-08-05 variant scan and for the same ratified reason:
# a tokenizer that REPLACED the lexical net would lose detections wherever shlex
# disagrees with the real shell (cmd.exe grammar, ANSI-C quoting, unbalanced
# quotes -- the exact 2026-08-03 regression class). So the token layer can only
# ADD a hit or a write-shaped verdict; every command the lexical net blocked
# before is still blocked, and shlex parseability is never a precondition for
# blocking (a ValueError degrades to the lexical net, pinned by test).
#
# WHY NOT AN ALLOW-LIST OF SAFE COMMANDS. Considered and rejected: a PreToolUse
# gate that blocks every unrecognized command across ~14.7k Bash calls is the
# false-positive disaster the module docstring's "breadth over precision"
# tradeoff exists to avoid, and "a guard people route around protects nothing"
# (the recursive-delete section, above). The deny-net stays; it just stops being
# the only reader of the command.
#
# THREE PASSES, deduped: POSIX-escape (bash semantics -- `hoo\ks` == `hooks`),
# no-escape (Windows semantics -- `C:\Users\...` backslashes are separators, not
# escapes), and decaret+no-escape (cmd.exe -- `^` removed at parse time). Each
# pass can only add hits, so a pass that mangles the other platform's paths into
# garbage tokens is harmless: garbage classifies as nothing.
_TOKEN_WRITE_COMMANDS = frozenset((
    # the lexical verb set, reachable here even when escape-spelled (`c\p`)
    "cp", "copy", "mv", "move", "rm", "del", "erase", "ren", "rename",
    "rd", "rmdir", "tee", "touch", "mkdir", "dd",
    "robocopy", "xcopy", "scp", "rcp", "pscp", "rsync", "git-rm", "git-mv",
    "remove-item", "move-item", "copy-item", "rename-item",
    "set-content", "add-content", "out-file", "new-item",
    # real file writers the lexical net never covered at all (each was a
    # live-proven bypass in the 2026-08-28 RED run): install(1) copies onto its
    # target, ln -sf replaces it, truncate/shred destroy its content in place,
    # patch edits its target file in place, split/csplit create output files.
    "install", "ln", "link", "mklink", "truncate", "shred", "unlink",
    "patch", "split", "csplit",
))
# Commands that WRITE only when an output-directing flag is present; a bare
# invocation reads (to stdout / lists an archive). Gating on the flag buys real
# precision -- `curl <url>` and `tar -tf a.tar` stay reads even when the text
# mentions a governance marker -- rather than the blunt breadth of marking the
# command a writer unconditionally (adversarial 2026-08-28, class 2).
_FLAG_WRITERS = frozenset((
    "curl", "wget", "tar", "bsdtar", "unzip", "sort", "gpg", "openssl",
))
# Output-directing flags/switches, matched against a whole token. `-C`/`-d` are
# tar/unzip target-directory switches; `-o`/`-O`/`--output` families cover
# curl/wget/sort/gpg; `-out` is openssl's. A tar `-x`/`-xf`/`-xvf` bundle
# (extract) is handled separately -- it is a bundle, not a standalone flag.
_OUTPUT_FLAG_TOKENS = frozenset((
    "-o", "-O", "--output", "--remote-name", "--output-dir", "-out", "--out",
    "-C", "--directory", "-d",
))


# Interpreters whose INLINE-CODE form (`-c`, `-e`, ...) or IN-PLACE form
# (`gawk -i inplace`) executes an arbitrary, statically-undecidable body. When
# one of these names a governance path, the command is treated as write-shaped
# (fail toward block) -- not because a write verb was seen, but because the body
# COULD write and cannot be proven read-only. This is the guard's own stated
# posture (see _block_governance: "a script's actual behavior is not statically
# decidable"), made real across the interpreter family so no single writer
# method (WriteAllText, createWriteStream, Path(..).open('w'), gawk inplace) has
# to be enumerated -- closing the CLASS, not the spelling (adversarial round 2,
# 2026-08-28). A raw REPL `input` (interact_with_process) is handled the same
# way via classify_shell(undecidable=True), since its whole payload is a body.
_AWK_CMDS = frozenset(("awk", "gawk", "mawk", "nawk"))
# perl/ruby take BOTH an inline-code flag (`-e`/`-E`) and an in-place-edit flag
# (`-i`, `-i.bak`), idiomatically combined into one dash bundle (`-pe`, `-ne`,
# `-pi`, `-i.bak`). Any single-dash bundle carrying `i` or `e` is undecidable-
# write (round 3, 2026-08-28).
_PERL_CMDS = frozenset(("perl", "ruby"))
# scripted line editors: a batch/ex-mode invocation (`-c wq`, `-es`, `-s`)
# writes the named file without a shell write verb.
_EDITOR_CMDS = frozenset(("ex", "ed", "vim", "vi", "view", "nvim"))
_EDITOR_SCRIPT_FLAGS = frozenset(("-c", "-es", "-s", "--cmd", "+"))
_INTERPRETER_CMDS = frozenset((
    "python", "python2", "python3", "py", "node", "nodejs",
    "powershell", "pwsh",
)) | _AWK_CMDS | _PERL_CMDS | _EDITOR_CMDS
_INLINE_CODE_FLAGS = frozenset((
    "-c", "-e", "--eval", "--exec", "--command", "-command", "-encodedcommand",
    "-ec", "-enc", "-p", "--print",
))


def _interpreter_inline(command, rest):
    """True if `command` is an interpreter/editor invoked with an inline-code,
    in-place, or scripting flag among `rest` (its following tokens) -- an
    undecidable body that COULD write. A SCRIPT FILE argument (`python
    hooks/test.py`, `perl app.pl`) has no such flag and stays a read."""
    if command not in _INTERPRETER_CMDS:
        return False
    lowered = [t.lower() for t in rest]
    if command in _AWK_CMDS:
        return any(t in ("-i", "--in-place", "--inplace", "inplace", "in-place")
                   or t.startswith("-i") for t in lowered)
    if command in _PERL_CMDS:
        for t in lowered:
            if t in _INLINE_CODE_FLAGS:
                return True
            # single-dash bundle (not `--`) whose letters include an in-place
            # (i) or inline-eval (e): `-i`, `-i.bak`, `-pe`, `-ne`, `-pi`.
            if t.startswith("-") and not t.startswith("--"):
                if any(c in "ie" for c in t[1:].split(".")[0]):
                    return True
        return False
    if command in _EDITOR_CMDS:
        return any(t in _EDITOR_SCRIPT_FLAGS or t.startswith("+")
                   for t in lowered)
    return any(t in _INLINE_CODE_FLAGS for t in lowered)


def _is_tar_extract_bundle(tok):
    """`re.match(r"^-[A-Za-z]*x[A-Za-z]*$", tok)`, linear. The raw pattern's two
    stars over one class made `tar -xxxx...x!` O(n^2) (32KB 7.5s) on every Bash call.
    The `$` also matches just before ONE trailing newline, which is kept here."""
    if not tok.startswith("-"):
        return False
    body = tok[1:]
    if body.endswith("\n"):
        body = body[:-1]
    return "x" in body and body.isascii() and body.isalpha()


def _is_output_flag(command, tok):
    if tok in _OUTPUT_FLAG_TOKENS:
        return True
    # tar extract: a single-dash bundle containing `x` (`-x`, `-xf`, `-xvf`),
    # or the long form.
    if command in ("tar", "bsdtar"):
        if tok in ("--extract", "--get"):
            return True
        if _is_tar_extract_bundle(tok) and not tok.startswith("--"):
            return True
    return False
# Wrappers/keywords that pass command position through to the next token --
# same closed-list philosophy as tool_call_paths._EXEC_WRAPPERS.
_TOKEN_WRAPPERS = frozenset((
    "sudo", "doas", "env", "command", "builtin", "exec", "nohup", "nice",
    "ionice", "stdbuf", "setsid", "xargs", "timeout", "time", "watch", "eval",
    "if", "then", "else", "elif", "fi", "while", "until", "do", "done", "for",
))
_TOKEN_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")
_TOKEN_DURATION_RE = re.compile(r"^\d+(\.\d+)?[smhd]?$")  # `timeout 5 rm ...`
_TOKEN_DRIVE_ABS_RE = re.compile(r"^[A-Za-z]:[/\\]")
_TOKEN_BOUNDARY_PUNCT = frozenset("();<>|&{}\n")
_WRITE_REDIRECT_TOKENS = frozenset((">", ">>"))


# TIME BOUND (2026-09-21). stdlib shlex builds each token with `self.token += ch`, one
# full string copy per character: ONE long token (a base64 blob, a minified one-liner)
# is O(len^2) memcpy -- 256KB 1.5s, 512KB 6.3s per pass, and _shlex_passes() makes
# three passes on every write-shaped Bash call. hooks/lib/linear_shlex.py swaps the token
# accumulator for a list-backed buffer and changes NOTHING else (the state machine is
# still the stdlib's own, so behavior is identical by construction and pinned against
# stdlib shlex by differential fuzz). Shared with commit-hygiene-guard and
# memory-orphan-link-guard; used only past _SHLEX_LINEAR_MIN_CHARS. Imported in its own
# try/except so a partial deploy (guard landed before the lib) degrades to the stdlib
# class instead of tripping the imports above and turning this guard inert.
try:
    from linear_shlex import (  # noqa: E402
        LinearShlex as _LinearShlex, TokenBuf as _TokenBuf,
        SHLEX_LINEAR_MIN_CHARS as _SHLEX_LINEAR_MIN_CHARS)
except Exception:
    _SHLEX_LINEAR_MIN_CHARS = 12288
    _TokenBuf = None
    _LinearShlex = shlex.shlex


def _tokenize(text, escape):
    """shlex-split `text` into argv-style tokens, or None if unparseable.
    posix mode merges quoted fragments exactly as the shell does;
    punctuation_chars makes operators (;|&<>(){}) their own tokens so they can
    never glue onto a path. escape=False turns off backslash-escaping for the
    Windows-path pass."""
    try:
        lex = (_LinearShlex if len(text) > _SHLEX_LINEAR_MIN_CHARS
               else shlex.shlex)(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        if not escape:
            lex.escape = ""
        return list(lex)
    except Exception:
        return None  # unbalanced quote etc. -- the lexical net still applies


def _shlex_passes(text):
    passes = []
    for candidate, escape in ((text, True), (text, False),
                              (_decaret(text), False)):
        toks = _tokenize(candidate, escape)
        if toks and toks not in passes:
            passes.append(toks)
    return passes


# Commands that only READ/inspect a path they name. The allow-list half of the
# inversion (round 6, 2026-08-28): with these enumerated, ANY OTHER command that
# names a governance path as a bare operand fails toward write-shaped, so an
# unrecognized file-writer (certutil -decode, xxd -r, esentutl, a future tool)
# is caught by default instead of silently allowed -- ending the "add the next
# writer verb by name" treadmill for the write-DETECTION axis. Over-block is
# confined to unknown commands that ALSO name a governance path; a read here has
# the Read/Grep/Glob and worktree escapes. git mutating verbs are caught
# separately by GIT_MUTATE_RE, so git is safe to treat as a reader here.
_READER_CMDS = frozenset((
    "cat", "bat", "tac", "nl", "rev", "head", "tail", "less", "more", "most",
    "view", "grep", "egrep", "fgrep", "rg", "rga", "ag", "ack", "pcregrep",
    "ls", "dir", "tree", "find", "fd", "stat", "file", "wc", "du", "df",
    "diff", "cmp", "comm", "sdiff", "colordiff", "delta",
    "od", "hexdump", "strings", "cksum", "sum", "shasum",
    "md5sum", "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum",
    "b2sum", "cut", "column", "join", "paste", "fold", "fmt", "expand",
    "unexpand", "basename", "dirname", "realpath", "readlink", "pwd",
    "type", "which", "command", "whereis", "whatis", "man", "info", "help",
    "printf", "echo", "print", "printenv", "test", "true", "false",
    "git", "gh", "hg", "svn", "jq", "yq", "xmllint", "wc",
    "pytest", "tox", "nox", "mypy", "pyflakes", "pylint", "flake8",
    "pycodestyle", "cd", "pushd", "popd", "source", ".",
))
_SED_WRITE_CMD_RE = re.compile(r"(?:^|[;{}\s/])[wW](?:\s|$)")


def _command_base(tok):
    """The bare command name of a token: strip any leading path and a Windows
    executable extension (`/bin/rm` -> `rm`, `cp.exe` -> `cp`)."""
    base = tok.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    if base.endswith(".exe") or base.endswith(".com") or base.endswith(".bat"):
        base = base.rsplit(".", 1)[0]
    return base


def _segment_write_shaped(seg):
    """True if one command SEGMENT writes: a redirect operator, a known
    file-writing command in command position, a flag-writer WITH its output
    flag, or `sed -i`. Command position skips env-assignments and recognized
    exec-wrappers so `echo cp mv rm > x` writes via the redirect, never via the
    verb NAMES in argument position, and `git rm ...` is not `rm`."""
    if any(t in _WRITE_REDIRECT_TOKENS for t in seg):
        return True  # fd-dup/null-device forms were stripped pre-tokenize
    idx, seen_wrapper = 0, False
    command = None
    while idx < len(seg):
        tok = seg[idx]
        if _TOKEN_ENV_ASSIGN_RE.match(tok) or _TOKEN_DURATION_RE.match(tok):
            idx += 1
            continue
        base = _command_base(tok)
        if base in _TOKEN_WRAPPERS:
            seen_wrapper = True
            idx += 1
            continue
        if tok.startswith("-"):
            if seen_wrapper:
                idx += 1
                continue  # a flag OF a recognized wrapper (sudo -u, xargs -0)
            return False  # a bare flag before any command -- position invalid
        command = base
        break
    if command is None:
        return False
    if command in _TOKEN_WRITE_COMMANDS:
        return True
    rest = seg[idx + 1:]
    if command in _FLAG_WRITERS:
        return any(_is_output_flag(command, t) for t in rest)
    if command == "sed":
        # in-place (`-i`) OR a `w`/`W` write command anywhere in the script
        # (round 6, 2026-08-28: `sed 'w <path>'` overwrites <path>).
        return any(t.startswith("-i") for t in rest) \
            or any(_SED_WRITE_CMD_RE.search(t) for t in rest)
    if command in _INTERPRETER_CMDS:
        # an interpreter/editor running a SCRIPT FILE (no inline/in-place flag)
        # is a read; only an inline/in-place body is write-shaped.
        return _interpreter_inline(command, rest)
    if command in _READER_CMDS:
        return False
    # UNKNOWN command (round 6 inversion): fail toward write-shaped. This only
    # BLOCKS when the command also names a governance path (classify_shell then
    # finds it); an unknown command naming no protected path returns None ->
    # allow, so the blast radius is unknown-commands-touching-governance.
    return True


def _tokens_write_shaped(tokens):
    """True if ANY command segment in the token stream writes. Segments split on
    the control-punctuation tokens shlex emits (`;` `|` `&` `(` `)` `{` `}`)."""
    seg = []
    for tok in tokens:
        if tok and all(c in _TOKEN_BOUNDARY_PUNCT for c in tok) \
                and any(c in ";|&(){}\n" for c in tok):
            if _segment_write_shaped(seg):
                return True
            seg = []
        else:
            seg.append(tok)
    return _segment_write_shaped(seg)


def _token_marker_at_boundary(tl, marker):
    """True if `marker` occurs in token text `tl` on real path-segment
    boundaries (start-or-`/` before, `/`-or-end after) -- so `.claude/hooks`
    never matches inside `.claude-worktrees/...`."""
    start = 0
    while True:
        idx = tl.find(marker, start)
        if idx == -1:
            return False
        end = idx + len(marker)
        start = idx + 1
        before_ok = idx == 0 or tl[idx - 1] == "/"
        # Skip a trailing `.`/space run (Win32 leaf-strip, REFUTE round 3
        # 2026-08-28) before the after-boundary test, and accept a quote as a
        # boundary so a marker inside a quoted interpreter arg
        # (`'~/.claude/CLAUDE.md.'`) still resolves.
        after = end
        while after < len(tl) and tl[after] in ". ":
            after += 1
        after_ok = after == len(tl) or tl[after] in "/'\""
        if before_ok and after_ok:
            return True


def _classify_token(tok, live_root, exempt, governance, claim):
    """('governance'|'claim', label) | None for ONE reconstructed argv token.

    Drive-qualified tokens go through _norm/_classify -- realpath resolution,
    the same authority as structured Write/Edit targets, which also correctly
    CLEARS a different repo's own .claude/ tree. Tilde/relative tokens are
    cwd-ambiguous, so they match the always-armed generic markers textually
    (breadth over precision, same doctrine as the lexical net), with the exempt
    markers checked first and tilde falling back to expanduser resolution."""
    t = tok.replace("\\", "/")
    tl = t.lower().rstrip("/")
    if not tl:
        return None
    # DRIVE-QUALIFIED tokens resolve through _norm/realpath (which collapses
    # `..`) and go to _classify -- the same authority as a structured Write/Edit
    # target, and the reason the drive form is immune to the `..`-through-an-
    # exempt-prefix walk: realpath collapses the path onto the real file BEFORE
    # the exempt dirs are tested. A different repo's own .claude/ tree still
    # resolves clear.
    if _TOKEN_DRIVE_ABS_RE.match(t):
        return _classify(_norm(t), live_root)
    if "/" not in tl:
        return None  # not path-shaped (a bare `~` is not a governance path)
    # TILDE and BARE-RELATIVE tokens are cwd/seam-ambiguous, so they are NOT
    # realpath-resolved (that would bind to the real home and miss a test seam,
    # and cannot distinguish the live root in production either). They match the
    # ALWAYS-ARMED generic markers (`~/.claude/**`, `.claude/**`) textually --
    # breadth over precision, the same seam-independent mechanism the lexical
    # net uses. Collapse `.`/`..` LEXICALLY first so an exempt prefix cannot be
    # walked back up into governance (adversarial 2026-08-28, class 1):
    # `~/.claude/hooks/sessions/../evil.py` -> `~/.claude/hooks/evil.py`.
    tl = _strip_interior_component_dots(posixpath.normpath(tl))
    for marker in exempt:
        if _token_marker_at_boundary(tl, marker):
            return None
    for marker, label in governance:
        if _token_marker_at_boundary(tl, marker):
            return ("governance", label)
    for marker, label in claim:
        if _token_marker_at_boundary(tl, marker):
            return ("claim", label)
    parts = tl.split("/")
    if parts and parts[-1] == REGISTRY_BASENAME and \
            (CC_SEGMENT in parts or LAMS_SEGMENT in parts):
        return ("governance", "scheduled-task registry (%s)" %
                (CC_SEGMENT if CC_SEGMENT in parts else LAMS_SEGMENT))
    return None


def _token_layer(normalized, live_root, exempt, governance, claim):
    """(write_shaped, governance_hit_or_None, claim_hit_or_None) from the parsed
    token stream. `normalized` is heredoc-stripped, case- and backslash-
    preserving text (backslashes must reach shlex intact for escape semantics).
    fd-dup and null-device redirects are stripped first, same as
    shell_may_write(), so `2>&1` / `2>/dev/null` never read as writes."""
    text = normalized.replace("\n", " ; ")  # shlex eats newlines as whitespace
    text = _FD_DUP_RE.sub(" ", text)
    text = _NULL_REDIRECT_RE.sub(" ", text)
    write_shaped = False
    gov = clm = None
    for tokens in _shlex_passes(text):
        if not write_shaped:
            write_shaped = _tokens_write_shaped(tokens)
        for tok in tokens:
            cls = _classify_token(tok, live_root, exempt, governance, claim)
            if cls is None:
                continue
            if cls[0] == "governance":
                gov = gov or cls
            elif clm is None:
                clm = cls
    return write_shaped, gov, clm


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


def classify_shell(command, may_write=True, undecidable=False):
    """See _classify_shell_impl. Runs it with a per-call realpath memo (_REALPATH_MEMO)."""
    global _REALPATH_MEMO
    outer = _REALPATH_MEMO
    _REALPATH_MEMO = {} if outer is None else outer
    try:
        return _classify_shell_impl(command, may_write, undecidable)
    finally:
        _REALPATH_MEMO = outer


def _classify_shell_impl(command, may_write=True, undecidable=False):
    """('governance'|'claim', label) for a write-shaped shell command naming a
    protected path, else None.

    Two readers of the same command, unioned (a hit from either blocks):
      * the STRUCTURAL token layer (_token_layer) -- shlex-parsed argv tokens
        classified through realpath resolution; also contributes its own
        write-shapedness verdict, so an escape-spelled verb (`c\\p`) or a
        writer the lexical indicators never covered (install, ln -sf,
        truncate) is still seen as a write;
      * the LEXICAL variant net (see _shell_variants) -- the historical
        breadth-over-precision matcher, kept whole as the safety net for
        every shape tokenization cannot model (unbalanced quotes, cmd.exe
        grammar corners, value indirection markers).
    `may_write` is the caller's lexical shell_may_write() verdict; the command
    is treated as write-shaped if EITHER reader says so, OR `undecidable` is set
    (a raw REPL `input` payload, whose whole body is undecidable code). The token
    layer additionally flags interpreter one-liners as write-shaped. Governance
    precedence is preserved across variants and layers: a governance hit anywhere
    outranks a claim hit anywhere."""
    if not TOOL_PATHS_LOADED:
        return None
    normalized = _normalize_unc(_strip_heredoc_bodies(normalize_text(command)))
    exempt, governance, claim = _shell_marker_sets()
    live_root = _norm(guard_root())

    token_write, token_gov, token_clm = _token_layer(
        normalized, live_root, exempt, governance, claim)
    if not (may_write or token_write or undecidable):
        return None  # no reader saw a write -- reads stay ungated

    base = _strip_interior_component_dots(normalized.replace("\\", "/").lower())
    first_claim = None
    for variant in _shell_variants(base):
        text = _blank_exempt(variant, exempt)
        gov, clm = _classify_shell_variant(text, live_root, governance, claim)
        if gov:
            return gov
        if clm and first_claim is None:
            first_claim = clm
    if token_gov:
        return token_gov
    return first_claim or token_clm


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
        if analysis is not None:
            # classify_shell is consulted even when the LEXICAL may_write is
            # False: the token layer can recognize a write the raw-text
            # indicators cannot (`c\p`, install, ln -sf, truncate, an
            # interpreter one-liner -- each a live-proven 2026-08-28 bypass).
            # A raw REPL input (interact_with_process) is a wholly undecidable
            # body, so it is forced write-shaped; classify_shell still returns
            # None unless a governance PATH is present, so reads stay ungated.
            repl = "interact_with_process" in tool_name
            cls = classify_shell(analysis.command, analysis.may_write,
                                 undecidable=repl)
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
