#!/usr/bin/env python3
"""Native git pre-push gate for ~/.claude — scans every commit genuinely NEW to the
remote, across the full diff of each (not just the tree at HEAD).

Lesson 2026-06-11 (incident, same-day remediation): the first push of this repo
carried pre-scrub commits with confidential deal terms in their diffs. A clean HEAD
does not mean a clean push. This hook runs `git log -p` over every ref range being
pushed and BLOCKS if any active always-term from hooks/confidential-terms.json
appears anywhere in that range, or any active context-term appears with one of its
anchors in the same window (one whole commit: header, message and patch; one blob view;
the full content of a file a pushed commit adds or modifies). Each window is also scanned URL-decoded (%XX and +, bounded rounds). See
_roster_entries() and scan_text() (Defect 2, 2026-11-12). Terms are never echoed — only
roster-entry indices are reported. Compressed blobs (.gz / .tgz / .zip, detected by magic bytes),
which `git log -p` shows only as "Binary files differ", are decompressed in memory and
scanned too -- see scan_compressed() (audit finding 2026-11-08).

Range computation (fixed 2026-07-25 — see rev_range()/_resolve_default_baseline()):
an EXISTING remote ref scans remote_sha..local_sha (the delta), same as always. A
BRAND-NEW remote ref (the normal case for a new branch's first push) scans
origin/<default-branch>..local_sha — commits not yet reachable from the repo's
default/trunk branch — NOT the unbounded `git log -p local_sha` this gate used
before that date, which dumped the ENTIRE history reachable from local_sha and
re-flagged commits already public on origin/main on every single first push of any
new branch (confirmed repro: a6f0689, an origin/main ancestor, re-flagged forever on
a documented placeholder API-key value in server/secrets.env.example -- not spelled
out here verbatim, since this gate scans its own source too). An
orphan branch (no merge-base with the default branch) is scanned in FULL by this same
range, because none of its history is reachable from a baseline it shares no ancestry
with — intentional, not a gap, since none of that history was ever public.

FAIL-CLOSED: terms file unreadable -> block; git log fails (e.g. unknown remote
sha — run `git fetch` first) -> block; a brand-new ref whose default-branch baseline
can't be resolved (no origin remote, nothing fetched) -> block, not a silent
full-history rescan and not a silent skip. No active terms (all deals closed) plus
no credential hits -> allow.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree
add` never checks it out into a fresh linked worktree. load_terms() falls back to
the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, shared by
every worktree of the same repo) when this checkout's own copy is missing or
unreadable. Still fail-closed if the file is unreadable in BOTH places (2026-07-12).

Install (done 2026-06-11, extended 2026-07-24; re-do after any fresh clone — see
docs/MIGRATION_RUNBOOK.md). The .git/hooks/pre-push shim is NOT version-controlled, so
it must be recreated on every fresh clone. It runs THREE tracked checks in order — the
doctrine-drift gate, then the hook-test-suite gate, then this fail-closed
confidentiality scan LAST (the first two take </dev/null so neither consumes git's ref
stdin; the final exec hands that stdin to this scan unchanged):
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (The doctrine-drift check lives in hooks/git-prepush-doctrine-gate.py, the hook-test
   check in hooks/git-prepush-hook-tests-gate.py; THIS scan's own logic is unchanged —
   the other two gates were added ahead of it, not merged into it.)

Exit 0 = allow push. Exit 1 = block (git pre-push convention).
"""
import json
import os
import re
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")
ZERO_RE = "0"

# CREDENTIAL SCAN (Gabriel ruling, 2026-07-24). Until now this gate blocked confidential
# DEAL TERMS only -- it carried zero credential patterns, so nothing stopped an API key
# reaching ZeOoba/ora-claude-config. The detection logic existed in
# maintenance/scrub-before-optin.py but only ran when a human remembered to invoke it; its
# own docstring records that the FRED key hardcoded in a retired SKILL.md was caught "only
# because that grep happened to be written that day".
#
# FAIL-CLOSED like the terms check: if the pattern module cannot be imported we block,
# because we cannot prove the push is clean. (The terms scan already fails closed on an
# unreadable terms file -- same principle, same reason.)
sys.path.insert(0, os.path.join(HOOK_DIR, "lib"))
try:
    import secret_patterns as _sp
except Exception as _e:  # pragma: no cover - exercised via the import-failure test
    _sp = None
    _SP_ERR = str(_e)

# RCT LEAK CHECK (2026-11-13, Gabriel's 2026-11-12 audit ruling: this repo stays public and the
# ratified replacement-cost table moved out of source). Blocks a push whose ADDED lines or
# commit messages carry an RCT figure, compared against a PRIVATE local copy outside the tree
# (hooks/lib/rct_leak_check.py). No private copy on this machine -> the check is skipped and
# says so; a private copy that exists but is broken -> blocked, like an unreadable terms file.
try:
    import rct_leak_check as _rct
except Exception as _e:  # pragma: no cover
    _rct = None
    _RCT_ERR = str(_e)

# EXPOSURE LEAK CHECK (2026-11-18, cross-repo audit; Gabriel ruling "untrack + guard now"):
# blocks re-publishing the untracked pipeline snapshot / PII memory files, phone numbers in
# memory, the {deal, stage} pipeline shape, and loan figures (hooks/lib/exposure_leak_check.py).
try:
    import exposure_leak_check as _exp
except Exception as _e:  # pragma: no cover
    _exp = None
    _EXP_ERR = str(_e)


def _read_json(path):
    """Parsed JSON from path, or None on any read/parse error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (same for every worktree of
    the same repo), or None on any failure -- not a git repo, git missing, etc."""
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if it can't be
    resolved or doesn't exist there. hooks/confidential-terms.json is gitignored
    (see .gitignore), so `git worktree add` never checks it out into a linked
    worktree -- this lets a linked worktree fall back to the main checkout's
    copy instead of failing closed on every push from a fresh worktree."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    # Assumes the terms file lives at <repo-root>/hooks/confidential-terms.json --
    # same layout TERMS_FILE itself relies on (HOOK_DIR is this script's own dir).
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


class RosterShapeError(Exception):
    pass


def _str_list(deal, field):
    """The deal's `field` as a list of strings, [] when absent. RAISES RosterShapeError when the
    field is present but not a list, or holds a non-string entry: a roster we cannot read
    completely cannot prove a push clean (a bare string used to be iterated per CHARACTER)."""
    value = deal.get(field)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(t, str) for t in value):
        raise RosterShapeError("%s is not a list of strings" % field)
    return value


def _roster_entries(d):
    """Scan entries for every active deal. A plain lowercase str is an `always` term; a tuple
    (term, anchors) is a `context` term that counts only when one of `anchors` co-occurs in the
    same scanned window (see scan_text). anchors == () means ANCHORLESS -> the term counts on its
    own.

    CONTEXT TERMS (Defect 2a, 2026-11-12): this gate used to read `always` only, so an active deal
    carrying only `context` / `context_requires_any` added nothing and main()'s `if terms:` skipped
    the terms scan outright -- allow-without-scan. Anchor rule mirrors confidentiality-guard.py
    find_hit(): any blank anchor leaves the group unanchored. DELIBERATE DIVERGENCE from find_hit():
    a MISSING / empty / non-list / non-string `context_requires_any` is ALSO unanchored here
    (fail-closed), where find_hit() never matches those context terms at all. Same rule as the
    ora-skills port (tools/prepush_confidential_scan.py).

    SHAPE (#497 follow-up, 2026-11-23): a non-`_` entry that is NOT a dict (a list, a string, null)
    is a deal we cannot read -- RosterShapeError, so the push blocks, instead of the old silent
    skip. WHITESPACE: every term and anchor is stripped before matching -- a padded roster string
    (" rent roll ") used to need the padding in the pushed text, which only narrowed matching."""
    out = []
    for key, deal in d.items():
        if key.startswith("_"):
            continue
        if not isinstance(deal, dict):
            raise RosterShapeError("deal entry is not an object")
        if not deal.get("active", True):
            continue
        out.extend(t.strip().lower() for t in _str_list(deal, "always") if t.strip())
        ctx = [t.strip().lower() for t in _str_list(deal, "context") if t.strip()]
        if not ctx:
            continue
        raw = deal.get("context_requires_any")
        if (isinstance(raw, list) and raw
                and all(isinstance(a, str) and a.strip() for a in raw)):
            anchors = tuple(a.strip().lower() for a in raw)
        else:
            anchors = ()  # anchorless or malformed anchors: fail closed
        out.extend((t, anchors) for t in ctx)
    return out


def load_terms():
    """Scan entries for every active deal (see _roster_entries), or None -- fail-closed -- when
    the roster is unreadable both in this checkout and (falling back) in the main worktree's copy,
    or when it parses but is malformed (RosterShapeError; no fallback for that: a malformed local
    roster is a real defect to fix, not a missing gitignored file)."""
    d = _read_json(TERMS_FILE)
    if d is None:
        fallback = _main_worktree_terms_file()
        if fallback is not None:
            d = _read_json(fallback)
    if not isinstance(d, dict):
        return None
    try:
        return _roster_entries(d)
    except RosterShapeError:
        return None


def _is_sha(s):
    return len(s) == 40 and all(c in "0123456789abcdef" for c in s.lower())


def _read_stdin(stream):
    """git writes the ref lines as UTF-8 bytes whatever the console code page; reading them
    through a cp1252 text stream garbled a non-ASCII ref name past the name scan (REFUTE
    2026-11-23 round 2, C1e). Falls back to text for a stream with no byte buffer (tests)."""
    buf = getattr(stream, "buffer", None)
    if buf is None:
        return stream.read()
    return buf.read().decode("utf-8", "replace")


def parse_pushrefs(text):
    """Pre-push stdin lines: '<local_ref> <local_sha> <remote_ref> <remote_sha>'.
    Both sha fields must be 40-hex — anything else is noise, not a ref line."""
    refs = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and _is_sha(parts[1]) and _is_sha(parts[3]):
            refs.append(tuple(parts))
    return refs


_DEFAULT_BRANCH_CANDIDATES = ("refs/remotes/origin/main", "refs/remotes/origin/master")


def _resolve_default_baseline(start_dir="."):
    """Best-effort commit-ish for the remote's default/trunk branch (e.g.
    'refs/remotes/origin/main'), used to bound the history scan on a brand-new remote
    ref. Prefers the tracked refs/remotes/origin/HEAD symref (set by a real `git
    clone` or `git remote set-head`); falls back to the common trunk names since a
    plain `git fetch` alone does not set that symref. Returns None if nothing
    resolves -- no `origin` remote, nothing fetched yet, or not a git repo at all --
    so the caller can fail closed instead of silently rescanning full history or
    silently skipping the scan.

    start_dir defaults to "." (the process's own cwd) DELIBERATELY, not HOOK_DIR --
    it must resolve against the SAME repo the `git log -p` scan itself operates on
    (which also relies on inherited cwd, not `-C`). git invokes pre-push hooks with
    cwd already at the top of the repo being pushed, so in real installs this and
    HOOK_DIR's parent are the same directory anyway -- but conflating the two is a
    live bug the moment they diverge (caught in review: it silently baselined
    against the wrong repo and produced a tautologically-passing test).

    ALWAYS fully-qualified (refs/remotes/origin/... , never the short 'origin/main').
    A short name is subject to git's ref-disambiguation order, which checks
    refs/heads/ before refs/remotes/ -- a LOCAL branch literally named 'origin/main'
    would silently shadow the real remote-tracking ref and could exclude genuinely
    new, unpushed commits from the scan (a demonstrated false negative caught in
    review). Fully-qualified refs cannot be shadowed."""
    candidates = []
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        p = None
    if p is not None and p.returncode == 0 and p.stdout.strip():
        symref_target = p.stdout.strip()
        # `git remote set-head` always yields a refs/remotes/... target, but the
        # lower-level `git symbolic-ref refs/remotes/origin/HEAD <anything>` doesn't
        # enforce that -- it would happily point this at a refs/heads/... branch,
        # which reopens exactly the shadowing class the fully-qualified-refs fix
        # above closes (caught in review). Only trust it if it's actually still
        # under refs/remotes/; otherwise fall through to the default candidates.
        if symref_target.startswith("refs/remotes/"):
            candidates.append(symref_target)
    for c in _DEFAULT_BRANCH_CANDIDATES:
        if c not in candidates:
            candidates.append(c)
    for ref in candidates:
        try:
            v = subprocess.run(
                ["git", "-C", start_dir, "rev-parse", "-q", "--verify", ref + "^{commit}"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            continue
        if v.returncode == 0 and v.stdout.strip():
            return ref
    return None


def rev_range(local_sha, remote_sha, baseline):
    """Range of commits to scan for one pushed ref.

    - Existing remote ref (remote_sha not all-zero): unchanged -- the delta,
      remote_sha..local_sha.
    - Brand-new remote ref (remote_sha all-zero, the normal case for a new branch's
      first push): bounded to baseline..local_sha, i.e. only commits NOT already
      reachable from the repo's default/trunk branch (baseline, e.g. origin/main).
      This is the 2026-07-25 fix: the old behavior returned local_sha alone (no range
      at all), which makes `git log -p` dump the ENTIRE history reachable from
      local_sha -- re-scanning commits already public on origin/main on every first
      push of any new branch.
    - Orphan branch (no merge-base with baseline at all): baseline..local_sha then
      naturally covers the branch's FULL history, because none of it is excluded by
      a baseline it shares no ancestry with. This is intentional, not a gap: an
      orphan branch's history was never reachable from the trunk, so none of it is
      "already public" and all of it must be scanned.
    - baseline is None (can't resolve the repo's default branch -- no origin remote,
      nothing fetched, not a repo): returns None to signal the caller must fail
      closed rather than silently falling back to a full-history rescan or silently
      skipping the scan.
    """
    if set(remote_sha) != {ZERO_RE}:
        return "%s..%s" % (remote_sha, local_sha)
    if baseline is None:
        return None
    return "%s..%s" % (baseline, local_sha)


# URL-ENCODED VIEWS (Defect 2b, 2026-11-12): a roster term pasted into a URL or query string --
# `Quiet%20Marsh%20Park`, `Quiet+Marsh+Park`, or double-encoded `Quiet%2520Marsh%2520Park` -- never
# matched the plain lowercase substring scan. Every window is now ALSO scanned through two decode
# chains, unquote and unquote_plus, each applied up to URL_DECODE_MAX_ROUNDS times (stopping early
# once a round changes nothing). Over-decoding can only ADD matches -- the fail-closed direction --
# so the chains are not "smart" about which round is the real one. RESIDUAL: encodings nested deeper
# than the bound, and other encodings (base64, HTML entities, \uXXXX escapes) are not decoded.
URL_DECODE_MAX_ROUNDS = 4


def _decoded_views(low):
    """YIELD lowercase views of `low` (already lowercase): itself, then each round of the unquote
    and unquote_plus chains. Decoding is skipped when there is nothing to decode.

    A GENERATOR (#497 follow-up, 2026-11-23): the old list held up to 9 full copies of the window
    at once (~10x a large blob's size in memory, with no cap). Callers consume one view at a time,
    so at most the source, the current view and the next one are alive (~3x)."""
    from urllib.parse import unquote, unquote_plus
    yield low
    if "%" not in low and "+" not in low:
        return
    for fn in (unquote, unquote_plus):
        cur = low
        for _ in range(URL_DECODE_MAX_ROUNDS):
            nxt = fn(cur).lower()  # %4D -> "M": decoded bytes can carry uppercase
            if nxt == cur:
                break
            yield nxt
            cur = nxt
        cur = nxt = None


def _entry_term(entry):
    return entry if isinstance(entry, str) else entry[0]


# CHUNKED DECODING (#497 follow-up, 2026-11-23): unquote() allocates one string object per `%`
# escape, so decoding a large escape-heavy blob in one call peaked near 10x its size, with no cap.
# The window is therefore decoded in DECODE_CHUNK slices that OVERLAP by the longest preimage any
# needle can have. One decoded char comes from at most 12 source chars in the round that produced
# it (a 4-byte UTF-8 char is four %XX escapes; the Kelvin sign U+212A, `%E2%84%AA`, even lowercases
# to ASCII 'k'), and every earlier round can triple an ASCII char (`%` -> `%25`, any char -> %XX).
# So after URL_DECODE_MAX_ROUNDS rounds a needle of length L comes from at most
# L * 12 * 3**(rounds - 1) contiguous source chars (REFUTE 2026-11-23 round 2: the first bound,
# L * 3**rounds, missed non-ASCII preimages straddling a chunk edge). lower() never shrinks a
# string, so it cannot lengthen a preimage. Every
# occurrence (raw or decoded) therefore lies wholly inside some chunk and decodes there exactly as
# in the whole text (an escape never spans more than its 3 chars). Results equal whole-window
# decoding; memory per call is bounded by the chunk, not the window.
DECODE_CHUNK = 1 << 20


def _chunks(text, needles):
    longest = max((len(n) for n in needles), default=0)
    overlap = longest * 12 * 3 ** (URL_DECODE_MAX_ROUNDS - 1) + 8
    if len(text) <= DECODE_CHUNK + overlap:
        yield text
        return
    i = 0
    while True:
        yield text[i:i + DECODE_CHUNK + overlap]
        if i + DECODE_CHUNK + overlap >= len(text):
            return
        i += DECODE_CHUNK


def _found_needles(text, needles):
    """The subset of `needles` present in ANY decoded view of `text` (see CHUNKED DECODING)."""
    left, found = set(needles), set()
    for chunk in _chunks(text, left):
        for view in _decoded_views(chunk.lower()):
            hit = set(n for n in left if n in view)
            found |= hit
            left -= hit
            if not left:
                return found
    return found


def scan_text(text, terms):
    """Sorted indices of roster entries present in ONE window of text (never the terms
    themselves). `terms` holds always-terms (str) and context entries ((term, anchors) tuples).
    A context entry needs an anchor in the SAME window; term and anchor may each match in ANY
    decoded view of it (REFUTE E: an anchor holding a literal '+' or '%' and a '+'-encoded term
    never share one view). anchors == () is ANCHORLESS: the term counts on its own (fail-closed,
    see _roster_entries)."""
    needles = set()
    for e in terms:
        needles.add(_entry_term(e))
        if not isinstance(e, str):
            needles.update(e[1])
    found = _found_needles(text, needles)
    hits = []
    for i, e in enumerate(terms):
        if _entry_term(e) not in found:
            continue
        if isinstance(e, str) or not e[1] or any(a in found for a in e[1]):
            hits.append(i)
    return hits


def mentions_term(text, terms):
    """True when `text` contains ANY roster term string in any decoded view, IGNORING anchors.
    Used to withhold a reported path: printing a path that carries a context term next to
    "confidential term(s)" discloses the term even when the path alone is not a hit (REFUTE C5b)."""
    return bool(_found_needles(text, set(_entry_term(e) for e in terms)))


# WINDOWS (Defect 2a, 2026-11-12): a context term's anchor must co-occur in the same window, and
# the whole `git log -p` output of a push is NOT one window -- an anchor in one commit and a term in
# an unrelated commit would otherwise combine. Window = ONE WHOLE COMMIT: its `commit <sha>`
# header, message and patch together (REFUTE 2026-11-23, A3: the message and the patch are
# published together, so a term in the message and its anchor in the patch -- or in a file NAME
# -- must block; the 2026-11-12 split into [message, patch] let them pass). For compressed /
# UTF-16 blobs, each text view scan_compressed() produces is a window, and so is the full
# content of every plain file a pushed commit adds or modifies (B1/B2, see scan_compressed).
# `git log` (pinned --pretty=medium) indents message lines by four spaces and prefixes every
# patch line, so a line starting with `commit <40 hex>` can only be git's own header.
_COMMIT_HEADER_RE = re.compile(r"^commit [0-9a-f]{40}", re.M)


def _log_windows(body):
    """Split `git log -p` output into windows: one per commit (header + message + patch)."""
    starts = [m.start() for m in _COMMIT_HEADER_RE.finditer(body)]
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    return [body[a:b] for a, b in zip(starts, starts[1:] + [len(body)]) if body[a:b]]


_WITHHELD = "<path withheld: contains a confidential term>"

# REF NAMES AND TAG OBJECTS (#497 follow-up, 2026-11-23): both are published by a push, and
# `git log` shows neither -- a branch named after a deal (`refs/heads/quiet-marsh-park`) and an
# annotated tag whose message names one both reached the remote unscanned.
#   * NAMES (a pushed ref name, and the `tag <name>` line inside every tag object) are matched raw,
#     with every non-alphanumeric run folded to a space (git allows , = ! and more in ref names),
#     and SQUASHED (all non-alphanumerics removed, so `QuietMarshPark` matches "Quiet Marsh Park";
#     squashed terms under 4 alphanumerics are not used). `refs/heads/` etc. is dropped first.
#   * OBJECTS: a pushed ref is peeled through every nested annotated tag; each tag object is
#     scanned through _text_views (a UTF-16 tag message is legal and git does not reject it). A tag
#     -- annotated or lightweight -- may point at a BLOB or a TREE rather than a commit; `git log`
#     shows nothing for those, so the blob (decompressed when compressed) or every blob in the
#     tree, plus the tree's paths, is scanned too (REFUTE round 2, C1a-c).
# Any git failure, or a chain deeper than TAG_MAX_DEPTH, blocks (fail-closed).
_NAME_FOLD = re.compile(r"[\W_]+", re.UNICODE)
_REF_PREFIX = re.compile(r"^refs/(?:heads|tags|remotes/[^/]+)/")
_SQUASH_MIN_ALNUM = 4
TAG_MAX_DEPTH = 16


class TagScanError(Exception):
    pass


def _squash(text):
    return _NAME_FOLD.sub("", text.lower())


def _squashed_terms(terms):
    """`terms` with every term / anchor squashed, index for index. A term that squashes to fewer
    than _SQUASH_MIN_ALNUM chars is replaced by a needle that cannot occur (it would match
    everywhere); an anchor that squashes to nothing keeps its original form."""
    never = "\x00\x00never\x00\x00"
    out = []
    for e in terms:
        t = _squash(_entry_term(e))
        t = t if len(t) >= _SQUASH_MIN_ALNUM else never
        out.append(t if isinstance(e, str) else (t, tuple(_squash(a) or a for a in e[1])))
    return out


def _name_parts(name):
    bare = _REF_PREFIX.sub("", name)
    return [name, _NAME_FOLD.sub(" ", bare)], _squash(bare)


def name_hits(name, terms):
    """Roster-entry indices a published NAME (ref or tag name) carries, in any form above."""
    views, squashed = _name_parts(name)
    hits = set(scan_text(squashed, _squashed_terms(terms)))
    for v in views:
        hits.update(scan_text(v, terms))
    return sorted(hits)


def _ref_shown(ref, terms):
    """`ref` for a block message, or a placeholder when any form of it carries a term."""
    if terms:
        views, squashed = _name_parts(ref)
        if any(mentions_term(v, terms) for v in views) \
                or mentions_term(squashed, _squashed_terms(terms)):
            return "<ref withheld: contains a confidential term>"
    return ref


def _git_out(args, cwd=None):
    p = subprocess.run(["git"] + args, capture_output=True, cwd=cwd)
    if p.returncode != 0:
        raise TagScanError("`git %s` failed" % " ".join(args[:2]))
    return p.stdout


def _blob_texts(data):
    if _is_compressed(data):
        try:
            return _decompress_texts(data, [COMPRESSED_MAX_BYTES])
        except UnscannableBlob as e:
            raise TagScanError("a tagged compressed blob could not be read (%s)" % e)
    return _text_views(data)


def pushed_object_texts(sha, cwd=None):
    """(texts, names) for what pushing `sha` publishes beyond `git log`: every annotated tag
    object on the peel chain (each _text_views view), and -- when the chain ends at a blob or a
    tree -- that content and the tree's paths. `names` are the `tag <name>` lines. Both empty for
    a plain commit. RAISES TagScanError on any git failure or an over-deep chain."""
    texts, names = [], []
    for _ in range(TAG_MAX_DEPTH):
        kind = _git_out(["cat-file", "-t", sha], cwd).decode("ascii", "replace").strip()
        if kind == "commit":
            return texts, names
        if kind == "blob":
            texts.extend(_blob_texts(_git_out(["cat-file", "blob", sha], cwd)))
            return texts, names
        if kind == "tree":
            out = _git_out(["ls-tree", "-r", "-z", "--full-tree", sha], cwd)
            entries, paths = [], []
            for rec in out.decode("utf-8", "surrogateescape").split("\0"):
                if not rec:
                    continue
                meta, _, path = rec.partition("\t")
                parts = meta.split()
                paths.append(path)
                if len(parts) == 3 and parts[1] == "blob":
                    entries.append(parts[2])
            texts.append("\n".join(paths))
            names.extend(paths)  # path names are folded / squashed like ref names (round 3)
            try:
                for _sha, data in _iter_blobs(sorted(set(entries)), cwd):
                    texts.extend(_blob_texts(data))
            except UnscannableBlob as e:
                raise TagScanError("a tagged tree could not be read (%s)" % e)
            return texts, names
        if kind != "tag":
            raise TagScanError("unexpected object type %r" % kind)
        raw = _git_out(["cat-file", "tag", sha], cwd)
        texts.extend(_text_views(raw))
        # The ASCII header dilutes a UTF-16 message below _text_views' NUL threshold (and moves
        # its BOM off byte 0), so the message body after the header is viewed on its own too.
        body = raw.split(b"\n\n", 1)[1] if b"\n\n" in raw else b""
        texts.extend(_text_views(body)[1:])
        # A signature block after the message dilutes a BOM-less UTF-16 message the same way
        # (REFUTE round 3), so the part before the first armor line is viewed on its own as well.
        if b"-----BEGIN " in body:
            texts.extend(_text_views(body.split(b"-----BEGIN ", 1)[0])[1:])
        head = raw.decode("utf-8", "ignore").split("\n\n", 1)[0].split("\n")
        first = head[0].split()
        if len(first) != 2 or first[0] != "object" or not _is_sha(first[1]):
            raise TagScanError("unparseable tag object %s" % sha[:12])
        names.extend(line[4:] for line in head if line.startswith("tag "))
        sha = first[1]
    raise TagScanError("tag chain deeper than %d" % TAG_MAX_DEPTH)


def _withhold(path, terms):
    """`path`, or a placeholder when it carries any roster term (anchors ignored, any decoded
    view). Every block message that prints a path goes through this (REFUTE 2026-11-23, C5:
    the credential / RCT / exposure reports printed term-bearing paths verbatim)."""
    return _WITHHELD if terms and mentions_term(path, terms) else path


def scan_log(body, terms):
    """Sorted roster-entry indices hit in any window of a `git log -p` body."""
    hits = set()
    for w in _log_windows(body):
        hits.update(scan_text(w, terms))
    return sorted(hits)


# --- Compressed blobs (audit finding prepush-scan-blind-to-compressed-transcripts, 2026-11-08) ---
# `git log -p` renders a .gz / .tgz / .zip as "Binary files ... differ", so a roster term or a
# credential inside a compressed session transcript or memory snapshot reached the remote with no
# scan at all. Every blob the pushed range adds or modifies is streamed ONE AT A TIME through
# `git cat-file --batch` (memory = the largest single blob) and classified BY CONTENT -- never by
# extension and never by git's binary/text flag, which a `.gitattributes` or uncommitted
# `.git/info/attributes` `diff` line can flip -- and, when it is gzip (magic bytes) or zip (magic
# bytes or zipfile.is_zipfile, which also finds a prefixed/self-extracting archive), decompressed
# in memory -- tar members inside a gzip included, nested archives to a small
# depth. Scanned for roster terms and credentials: every member's content, the raw blob as text
# (zip member names, the gzip FNAME header, a prefix or trailer around the archive), and the whole
# decompressed tar stream as text (tar member names, PAX headers, bytes after end-of-archive).
# Reports name the archive path only -- never a member name -- and withhold even the path when
# the path itself carries a term.
# FAIL-CLOSED: a compressed blob that cannot be fully read (corrupt, encrypted, past the per-blob
# size cap or member cap, nested too deep) BLOCKS, roster or not: like an unimportable pattern
# module, an unproven credential scan is a blocked push. The size cap is PER BLOB, so one large
# archive cannot switch off the scan of the others. Cost of that choice, accepted deliberately: a
# push adding an encrypted zip or a zip with an unsupported method (e.g. Deflate64) always blocks;
# the only way past is a human's `--no-verify`. Do not downgrade this to a warning.
# UTF-16 (audit E6, 2026-11-08): every decompressed member / stream is ALSO decoded as UTF-16
# when it carries a BOM or is >30% NUL bytes (see _text_views) -- utf-8-with-ignore keeps only the
# ASCII half of each UTF-16 code unit, interleaved with NULs, so a term never matched.
# MERGES (audit prepush-scan-skips-merge-commit-diffs + E6, 2026-11-08): both this blob walk and
# main()'s `git log -p` run with `--cc`, so a merge commit contributes its dense combined diff --
# the paths/hunks whose result differs from EVERY parent, i.e. exactly the content a conflict
# resolution ("evil merge") introduced. Hunks a merge takes verbatim from one parent are omitted by
# --cc on purpose: that content lives in the parent's own commit, which is either inside the pushed
# range (scanned there) or already on the remote.
# A bare (non-archived) UTF-16 file is "Binary files differ" to `git log -p` too, so the same
# blob walk scans its UTF-16 views (REFUTE 2026-11-08).
# RESIDUAL: other binary formats (PDF streams, images, xz/bz2/7z) and BOM-less UTF-16 under 30%
# NUL bytes (CJK-heavy text) or UTF-32 are not decoded; history already on the remote is not
# rescanned; zip entries absent from the central directory are not read.
GZIP_MAGIC = b"\x1f\x8b"
ZIP_MAGIC = b"PK\x03\x04"
COMPRESSED_MAX_BYTES = 256 * 1024 * 1024  # decompressed bytes per compressed blob
COMPRESSED_MAX_MEMBERS = 20000
COMPRESSED_MAX_DEPTH = 3


class UnscannableBlob(Exception):
    pass


def _range_blobs(rng, cwd=None):
    """[(path, blob_sha)] for every blob added or modified anywhere in `rng` (every commit, not
    just the tip). RAISES UnscannableBlob on a git failure (the caller blocks)."""
    # --cc: a merge commit lists the paths its resolution changed relative to EVERY parent, in
    # combined raw form (one leading ':' per parent: N+1 modes, N+1 shas, status). Without it a
    # blob introduced only by a merge resolution was never enumerated (audit E6).
    p = subprocess.run(["git", "log", "--raw", "--cc", "-z", "--no-abbrev", "--no-renames",
                        "--format=", rng], capture_output=True, cwd=cwd)
    if p.returncode != 0:
        raise UnscannableBlob("`git log --raw %s` failed" % rng)
    fields = p.stdout.decode("utf-8", "surrogateescape").split("\0")
    out, seen = [], set()
    i = 0
    while i < len(fields):
        meta = fields[i].lstrip("\n")
        if not meta.startswith(":"):
            i += 1
            continue
        path = fields[i + 1] if i + 1 < len(fields) else ""
        i += 2
        nparents = len(meta) - len(meta.lstrip(":"))
        parts = meta.lstrip(":").split()
        if len(parts) < 2 * nparents + 3:
            raise UnscannableBlob("unparseable `git log --raw` record")
        # result mode/sha are the LAST of the N+1 modes and of the N+1 shas
        new_mode, new_sha = parts[nparents], parts[2 * nparents + 1]
        if set(new_sha) == {ZERO_RE} or new_mode in ("160000", "120000"):
            continue  # deletion, submodule, symlink
        if (path, new_sha) not in seen:
            seen.add((path, new_sha))
            out.append((path, new_sha))
    return out


def _iter_blobs(shas, cwd=None):
    """Yield (sha, bytes) one blob at a time from a single `git cat-file --batch` process, so
    memory is bounded by the largest blob, not the push. RAISES UnscannableBlob on a git failure
    or a missing object."""
    if not shas:
        return
    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd)
    try:
        for sha in shas:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode("ascii", "replace").split()
            if len(header) < 3 or header[1] != "blob":
                raise UnscannableBlob("unexpected cat-file output for object %s" % sha[:12])
            size = int(header[2])
            data = proc.stdout.read(size)
            proc.stdout.read(1)  # trailing newline
            if len(data) != size:
                raise UnscannableBlob("short read for object %s" % sha[:12])
            yield sha, data
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.kill()
        proc.wait()


def _is_zip(blob):
    import io
    import zipfile
    if blob[:4] == ZIP_MAGIC:
        return True
    try:
        return zipfile.is_zipfile(io.BytesIO(blob))
    except Exception:
        return False


def _is_compressed(blob):
    return blob[:2] == GZIP_MAGIC or _is_zip(blob)


UTF16_NUL_RATIO = 0.30


def _text_views(data):
    """Text views of one decompressed buffer: utf-8 (errors ignored) always, plus UTF-16 LE and
    BE when the buffer carries a UTF-16 BOM or is more than 30% NUL bytes. Decoding both byte
    orders (rather than guessing one) costs one extra pass and cannot pick the wrong order."""
    views = [data.decode("utf-8", "ignore")]
    if not data:
        return views
    bom = data[:2] in (b"\xff\xfe", b"\xfe\xff")
    if bom or data.count(b"\x00") > UTF16_NUL_RATIO * len(data):
        body = data[2:] if bom else data
        for enc in ("utf-16-le", "utf-16-be"):
            # U+0000 -> '"' (REFUTE round 2): a NUL code unit is not whitespace, so the
            # `password assignment` value class [^\s"']{6,} ran straight through NUL padding
            # -- sc.exe-shaped `password=` + NULs + `DisplayName=` read as a 6+ char password.
            # A quote ends a value the way the NUL ends the C string; a real value stays whole.
            views.append(body.decode(enc, "ignore").replace("\x00", '"'))
    return views


def _decompress_texts(blob, budget, depth=0):
    """Every text view of a gzip / zip blob: the raw blob, each member, and a decompressed tar
    stream as a whole. `budget` is a one-item list of decompressed bytes still allowed for THIS
    blob. RAISES UnscannableBlob on anything that cannot be fully read."""
    import gzip
    import io
    import tarfile
    import zipfile
    if depth > COMPRESSED_MAX_DEPTH:
        raise UnscannableBlob("archives nested deeper than %d" % COMPRESSED_MAX_DEPTH)

    def _take(n):
        budget[0] -= n
        if budget[0] < 0:
            raise UnscannableBlob("decompressed size over the %d MB per-file scan cap"
                                  % (COMPRESSED_MAX_BYTES // (1024 * 1024)))

    def _expand(data):
        if _is_compressed(data):
            return _decompress_texts(data, budget, depth + 1)
        return _text_views(data)

    out = [blob.decode("utf-8", "ignore")]  # names, gzip FNAME, prefix / trailer bytes
    try:
        if blob[:2] == GZIP_MAGIC:
            with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
                data = gz.read(budget[0] + 1)  # bounded: a header's size can lie, the stream cannot
            _take(len(data))
            out.extend(_text_views(data))  # whole stream: tar names, PAX, trailer, UTF-16 text
            buf = io.BytesIO(data)
            if data[257:262] == b"ustar" or (len(data) >= 512 and tarfile.is_tarfile(buf)):
                buf.seek(0)
                with tarfile.open(fileobj=buf, mode="r:") as tf:
                    members = tf.getmembers()
                    if len(members) > COMPRESSED_MAX_MEMBERS:
                        raise UnscannableBlob("too many tar members")
                    for m in members:
                        if not m.isfile():
                            continue
                        fh = tf.extractfile(m)
                        if fh is None:
                            raise UnscannableBlob("unreadable tar member")
                        out.extend(_expand(fh.read()))
            elif _is_compressed(data):
                out.extend(_decompress_texts(data, budget, depth + 1))
        else:
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                infos = zf.infolist()
                if len(infos) > COMPRESSED_MAX_MEMBERS:
                    raise UnscannableBlob("too many zip members")
                for info in infos:
                    out.append(info.filename)
                    if info.is_dir():
                        continue
                    with zf.open(info) as fh:
                        mdata = fh.read(budget[0] + 1)
                    _take(len(mdata))
                    out.extend(_expand(mdata))
    except UnscannableBlob:
        raise
    except Exception as e:  # corrupt stream, encrypted zip member, truncated tar, ...
        raise UnscannableBlob(type(e).__name__)
    return out


def scan_compressed(rng, terms, cwd=None):
    """(term_hits, cred_leaks, unscannable) for every compressed blob added or modified in
    `rng`. term_hits: [(path, indices)]; cred_leaks: [(path, labels)]; unscannable:
    [reason]. Reports carry the ARCHIVE path only -- never a member name, a term, or a value --
    and a path that itself contains a term is withheld."""
    term_hits, cred_leaks, unscannable = [], [], []

    def _shown(path):
        return _withhold(path, terms)

    # FULL FILE CONTENT windows (REFUTE 2026-11-23, B1/B2): the diff scan sees only ADDED lines
    # plus 3 lines of context, so a context term added to a file in one commit (or push) and its
    # anchor added far away in a later one never shared a window -- yet the pushed file holds
    # both. Every plain blob a pushed commit adds or modifies is therefore also scanned whole,
    # for ANCHORED context entries only: always-terms and anchorless context terms are fully
    # caught by the diff scan already (any occurrence is an added line somewhere), so scanning
    # them here would only repeat those reports. Same reasoning as
    # exposure_leak_check.shape_hits (rule 3).
    # ACCEPTED COST (fail-safe, REFUTE 2026-11-23 E13/E14): this window reads the WHOLE file, so
    # a file that ALREADY holds an anchored term and its anchor on the remote blocks on ANY later
    # edit or rename of it -- and a later scrub commit in the same push does not clear it (the
    # touching commit is still in the range): remove the term or anchor in a commit of its own
    # first, or rewrite the history. The combination is already public in that case, so blocking
    # is the right direction. Not covered (residual): submodule gitlinks and Git LFS pointers
    # (no content in git). Decoding memory is bounded per chunk (see CHUNKED DECODING); the blob
    # itself is still read whole, as every scan here always has.
    anchored = set(i for i, e in enumerate(terms or ()) if not isinstance(e, str) and e[1])

    try:
        blobs = _range_blobs(rng, cwd)
        paths_by_sha = {}
        for path, sha in blobs:
            paths_by_sha.setdefault(sha, []).append(path)
        for sha, blob in _iter_blobs(sorted(paths_by_sha), cwd):
            path = paths_by_sha[sha][0]
            if not _is_compressed(blob):
                views = _text_views(blob)
                if anchored:
                    whole = [i for i in scan_text(views[0], terms) if i in anchored]
                    if whole:
                        term_hits.append(("%s [full file content]" % _shown(path), whole))
                # A bare UTF-16 file (BOM or NUL-heavy; Windows PowerShell 5.1's `>` and
                # Out-File write UTF-16LE by default) is "Binary files differ" to `git log -p`,
                # so only its UTF-16 views are scanned here -- the utf-8 view is the diff scan's
                # (REFUTE 2026-11-08, E6 residual).
                texts = views[1:]
                if not texts:
                    continue
            else:
                try:
                    texts = _decompress_texts(blob, [COMPRESSED_MAX_BYTES])
                except UnscannableBlob as e:
                    unscannable.append("%s: %s" % (_shown(path), e))
                    continue
            hits, labels = set(), set()
            for text in texts:
                if terms:
                    hits.update(scan_text(text, terms))
                if not all(_sp.is_exempt_path(p) for p in paths_by_sha[sha]):
                    labels.update(_sp.scan_text(text))
            if hits:
                term_hits.append((_shown(path), sorted(hits)))
            if labels:
                cred_leaks.append((_shown(path), sorted(labels)))
    except (UnscannableBlob, ValueError, OSError) as e:
        unscannable.append("compressed-blob enumeration failed (%s)" % e)
    return term_hits, cred_leaks, unscannable


def main():
    # Fail closed on a broken pattern module, exactly as for an unreadable terms file:
    # an unprovable push is a blocked push.
    if _sp is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): hooks/lib/secret_patterns.py "
                         "could not be imported (%s) -- cannot scan for credentials.\n"
                         % _SP_ERR)
        return 1
    terms = load_terms()
    if terms is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): confidential-terms.json "
                         "unreadable or malformed (an always / context field that is not a "
                         "list of strings) — cannot prove the push is clean.\n")
        return 1
    if _rct is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): hooks/lib/rct_leak_check.py could "
                         "not be imported (%s) -- cannot check for RCT figures.\n" % _RCT_ERR)
        return 1
    try:
        rct_needles, _rct_sources = _rct.load_needles()
    except _rct.RctSourceError as e:
        sys.stderr.write("pre-push BLOCKED (fail-closed): the private RCT table/denylist exists "
                         "but is unusable (%s) -- fix it or move it aside; an absent file skips "
                         "the check, a broken one blocks.\n" % e)
        return 1
    if rct_needles is None:
        sys.stderr.write("pre-push note: RCT leak check skipped -- no private RCT table or "
                         "denylist on this machine (~/.ora-private/rct/).\n")
    elif not _rct.table_loaded(_rct_sources):
        sys.stderr.write("pre-push WARNING: RCT leak check is running on the superseded-values "
                         "denylist ONLY -- the current private RCT table was not found, so the "
                         "current figures are not checked.\n")
    if _exp is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): hooks/lib/exposure_leak_check.py "
                         "could not be imported (%s) -- cannot check for pipeline, PII or debt "
                         "data.\n" % _EXP_ERR)
        return 1
    try:
        exp_needles = _exp.load_needles()
    except _exp.ExposureSourceError as e:
        sys.stderr.write("pre-push BLOCKED (fail-closed): a private debt-figure source exists "
                         "but is unusable (%s) -- fix it or move it aside; an absent file skips "
                         "the debt-figure rule, a broken one blocks.\n" % e)
        return 1
    if exp_needles is None:
        sys.stderr.write("pre-push note: debt-figure rule skipped -- no data/loan-terms.json or "
                         "~/.ora-private/exposure-denylist.json on this machine (path, phone and "
                         "pipeline-shape rules still run).\n")
    # NOTE: there is deliberately NO `if not terms: return 0` early exit any more. It used
    # to short-circuit the whole hook whenever no deal was active -- which is the state
    # TODAY -- so a credential scan placed after it would have been dead on arrival. The
    # two scans are independent: an empty terms list disables the TERMS check only.
    # No start_dir arg -- resolves against THIS PROCESS's cwd, same as the `git log -p`
    # scan below (which also has no explicit -C/cwd). git invokes pre-push hooks with
    # cwd at the top of the repo being pushed, so this is the repo actually being
    # scanned -- deliberately NOT HOOK_DIR, which is fixed to wherever this script
    # file happens to live and would silently diverge from the repo being pushed.
    # Always resolved against the "origin" remote -- matches every other assumption
    # in this file (confidential-terms.json fallback, install docs) that ~/.claude
    # has exactly one remote; a push to a second remote would still be scanned, just
    # bounded against origin/main rather than that remote's own trunk.
    baseline = _resolve_default_baseline()
    bad = False
    pushrefs = parse_pushrefs(_read_stdin(sys.stdin))
    # ZERO ref lines (2026-11-09, push-live-backup REFUTE round 3): a stray \r or Unicode
    # space in a shim can starve this scan's stdin, and with no ref lines it scans nothing
    # and allows. git itself runs pre-push with EMPTY stdin on an up-to-date push (verified,
    # git 2.55.0.windows.2), so this cannot fail closed unconditionally without breaking
    # every no-op push. A caller that guarantees >=1 ref opts in with
    # ORA_PREPUSH_REQUIRE_REFS=1 (push-live-backup.py; git passes the env to the hook).
    if not pushrefs and os.environ.get("ORA_PREPUSH_REQUIRE_REFS") == "1":
        sys.stderr.write("pre-push BLOCKED (fail-closed): zero ref lines on stdin while "
                         "ORA_PREPUSH_REQUIRE_REFS=1 -- the caller guaranteed a ref to push, so "
                         "the shim did not hand this scan git's ref lines.\n")
        return 1
    for local_ref, local_sha, remote_ref, remote_sha in pushrefs:
        if set(local_sha) == {ZERO_RE}:
            continue  # ref deletion — nothing new is pushed
        if terms:
            # Ref names, tag objects and tagged blobs / trees are published but never in
            # `git log` (see REF NAMES AND TAG OBJECTS). The LOCAL name is checked too, fail-safe:
            # it usually becomes a remote name, and it is printed in every message below (and
            # withheld there when it carries a term).
            n_hits = set(name_hits(remote_ref, terms)) | set(name_hits(local_ref, terms))
            if n_hits:
                sys.stderr.write("pre-push BLOCKED: the pushed REF NAME carries %d confidential "
                                 "term(s); ref names are published. Rename the branch or tag "
                                 "first. Terms are not echoed.\n" % len(n_hits))
                bad = True
            local_ref = _ref_shown(local_ref, terms)
            try:
                o_texts, o_names = pushed_object_texts(local_sha)
                t_hits = set(i for text in o_texts for i in scan_text(text, terms))
                t_hits.update(i for name in o_names for i in name_hits(name, terms))
                t_hits = sorted(t_hits)
            except TagScanError as e:
                sys.stderr.write("pre-push BLOCKED (fail-closed): the tag / tagged object pushed "
                                 "on %s could not be read (%s), so it cannot be proven free of "
                                 "confidential terms.\n" % (local_ref, e))
                bad = True
                t_hits = []
            if t_hits:
                sys.stderr.write("pre-push BLOCKED: %d confidential term(s) (indices %s) in an "
                                 "ANNOTATED TAG (message or name) or the blob / tree a tag points "
                                 "at, pushed on %s. These are published; re-create the tag "
                                 "cleanly.\n" % (len(t_hits), t_hits, local_ref))
                bad = True
        rng = rev_range(local_sha, remote_sha, baseline)
        if rng is None:
            sys.stderr.write("pre-push BLOCKED (fail-closed): %s is a brand-new remote "
                             "ref and the repo's default branch (origin/main) could not "
                             "be resolved to bound the history scan -- run `git fetch` "
                             "first.\n" % local_ref)
            bad = True
            continue
        # ONE pinned `git log` pass feeds every scanner below (terms, credentials, RCT,
        # exposure) -- audit 2026-11-23 HIGH #2. exposure_leak_check.GIT_LOG_ARGS pins:
        #   --text           a text file with one NUL byte, or a path marked `-diff` in
        #                    .gitattributes, would otherwise print "Binary files differ" and
        #                    hide a term or key;
        #   --no-textconv / --no-ext-diff   a local diff driver cannot rewrite what is shown;
        #   --root           log.showRoot=false cannot hide a root commit's diff;
        #   --no-renames     a renamed/copied file shows as a full add, not unchanged context;
        #   --cc             a merge's conflict-resolution content is scanned;
        #   --no-abbrev-commit --pretty=medium   the "commit <40hex>" header rct_leak_check
        #                    keys commit-message scanning on (REFUTE 2026-11-13, C9);
        #   fixed a/ b/ prefixes + core.quotePath=false   per-path rules see real paths.
        # It also replaces three separate full-range passes with one.
        # _log_windows() (context-term windows, Defect 2a) ALSO relies on the pinned
        # --pretty=medium layout: a `commit <40hex>` header and message lines indented four
        # spaces. A pusher's own format.pretty (e.g. %H%n%B) would leave a message line
        # `diff --git ...` unindented and let it split a term from its anchor (REFUTE F,
        # 2026-11-12), so the format must stay pinned in GIT_LOG_ARGS, never inherited.
        p = subprocess.run(["git"] + _exp.GIT_LOG_ARGS + [rng], capture_output=True)
        if p.returncode != 0:
            sys.stderr.write("pre-push BLOCKED (fail-closed): `git log -p %s` failed "
                             "for %s (unknown remote sha? run `git fetch` first) -- cannot "
                             "check for pipeline, PII or debt data, confidential terms, "
                             "credentials or RCT figures.\n" % (rng, local_ref))
            bad = True
            continue
        body = p.stdout.decode("utf-8", "ignore")
        if terms:
            hits = scan_log(body, terms)
            if hits:
                sys.stderr.write("pre-push BLOCKED: %d confidential term(s) (indices %s) "
                                 "found in the HISTORY being pushed on %s (range %s). A "
                                 "clean HEAD does not mean a clean push — purge or rebase "
                                 "the history first (see docs/MIGRATION_RUNBOOK.md).\n"
                                 % (len(hits), hits, local_ref, rng))
                bad = True
        # Credential scan over the SAME body -- per file, so a test fixture in the history
        # cannot block every push (see secret_patterns.scan_diff). Reports path + label
        # only; the matched value is never echoed into the terminal or a CI log.
        leaks = _sp.scan_diff(body)
        if leaks:
            detail = "; ".join("%s -> %s" % (_withhold(path, terms), ", ".join(labels))
                               for path, labels in leaks)
            sys.stderr.write("pre-push BLOCKED: credential-shaped string(s) in the HISTORY "
                             "being pushed on %s (range %s): %s. Values are not echoed. "
                             "Rotate the credential FIRST, then purge or rebase the "
                             "history -- a force-push alone does not un-leak it.\n"
                             % (local_ref, rng, detail))
            bad = True
        if rct_needles:
            # Same pinned body (it carries --text: REFUTE round 2, N1).
            rct_paths = _rct.scan_diff(body, rct_needles)
            if rct_paths:
                sys.stderr.write("pre-push BLOCKED: ratified RCT replacement-cost figure(s) from "
                                 "the private table ADDED on %s (range %s): %s. Figures are not "
                                 "echoed. This repo is PUBLIC: replace each with a pointer to the "
                                 "private RCT file (~/.ora-private/rct/), and reword the commit "
                                 "message if it is listed.\n"
                                 % (local_ref, rng,
                                    "; ".join(_withhold(rp, terms) for rp in rct_paths)))
                bad = True
        # Exposure rules over the same pinned body (prefixes, path quoting and textconv are
        # pinned so a host's diff.noprefix / textconv config cannot blind the path rules).
        e_hits = _exp.scan_diff(body, exp_needles)
        # Rule 3 reads file CONTENTS at every pushed commit (exposure_leak_check.shape_hits).
        try:
            e_hits = sorted(set(e_hits) | set(_exp.shape_hits(rng)))
        except _exp.ShapeScanError as e:
            sys.stderr.write("pre-push BLOCKED (fail-closed): could not read the pushed .json "
                             "files on %s (%s) -- cannot check for the pipeline-snapshot "
                             "shape.\n" % (local_ref, e))
            bad = True
            continue
        if e_hits:
            sys.stderr.write("pre-push BLOCKED: pipeline / PII / debt data ADDED on %s (range "
                             "%s): %s. Values are not echoed. This repo is PUBLIC: keep the "
                             "file untracked (gitignored), move contacts to contacts.local.md "
                             "and loan figures to data/loan-terms.json, and reword the commit "
                             "message if it is listed.\n"
                             % (local_ref, rng, "; ".join("%s -> %s" % (_withhold(h[0], terms),
                                                                         h[1]) for h in e_hits)))
            bad = True
        # Compressed and UTF-16 blobs: invisible to `git log -p` (see scan_compressed).
        c_hits, c_leaks, c_bad = scan_compressed(rng, terms)
        if c_hits:
            sys.stderr.write("pre-push BLOCKED: confidential term(s) inside COMPRESSED / UTF-16 file(s) "
                             "or a pushed file's full file content "
                             "being pushed on %s (range %s): %s. Terms are not echoed.\n"
                             % (local_ref, rng, "; ".join("%s -> indices %s" % (p, i)
                                                          for p, i in c_hits)))
            bad = True
        if c_leaks:
            sys.stderr.write("pre-push BLOCKED: credential-shaped string(s) inside COMPRESSED / UTF-16 "
                             "file(s) being pushed on %s (range %s): %s. Values are not echoed.\n"
                             % (local_ref, rng, "; ".join("%s -> %s" % (p, ", ".join(l))
                                                          for p, l in c_leaks)))
            bad = True
        if c_bad:
            # Blocks roster or not: an unproven credential scan is a blocked push, the same
            # rule as the unimportable-pattern-module branch above (review 2026-11-08).
            sys.stderr.write("pre-push BLOCKED (fail-closed): compressed file(s) in the push on "
                             "%s could not be fully read, so they cannot be proven free of "
                             "confidential terms or credentials: %s\n"
                             % (local_ref, "; ".join(c_bad)))
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
