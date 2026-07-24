"""Engineering OS review gate -- PreToolUse hook for Bash. BLOCKING.

Blocks a `git commit` that would land BLAST-RADIUS or FINANCIAL-DECISION code
with no independent code-review artifact tied to THAT SPECIFIC DIFF.

RATIFIED BY GABRIEL 2026-07-24 (scope + blocking enforcement). Rationale and the
measured cost basis live in memory/feedback_auto_review_blast_radius_gate.md:
one reviewer pass cost ~108k subagent tokens / ~6.5 min on an EIGHT-LINE diff and
found a `major` defect the implementer had missed. Worth it on risky code; pure
waste on typos and docs -- hence a scoped gate, not a universal one.

WHY A HOOK AND NOT DOCTRINE. The Engineering OS "Done" criteria ALREADY required
an independent review, and it was skipped in the very session that wrote them.
`eos-plan-gate` is what actually stopped work that day; the prose did not. This
gate is the same mechanism applied to review.

SCOPE is the risk list CLAUDE.md already defines -- no new list was invented:
  hooks/** . *.env* . *credentials* . confidential-terms.json . settings.json .
  CLAUDE.md and ~/.claude config . scheduled-task registries . CSP/headers .
  financial-constant/governor files . financial-decision code (engine math,
  scoring, benchmarking, capital-allocation/NOI).

WHAT MAKES THIS NOT THEATER: the review artifact is keyed by a CONTENT HASH of
the exact bytes THIS commit invocation would actually land for each risk file --
not just "whatever is on disk right now". Edit a reviewed file by one character
and its key changes, the artifact no longer matches, and the gate blocks again.
A review cannot be earned once and spent forever, and a review of {a.py} does
not cover a later commit of {a.py, b.py}. See test_stale_review_blocks -- that
test IS the feature.

PROVENANCE FIX (2026-07-24, independent review finding M1). "The bytes this
commit would land" is NOT always the working-tree file: a plain `git commit`
(no `-a`) commits the INDEX (whatever was `git add`ed), which can differ from a
since-further-edited working copy. The original version hashed working-tree
bytes unconditionally, so staging v1, having it reviewed, then editing to v2
WITHOUT re-staging, and running a bare `git commit` -- which lands v1 -- keyed
against v2 and let v1 land unreviewed. `_origin_content_digest` now hashes the
INDEX blob for plainly-staged paths and the WORKING TREE only for paths sourced
via `-a`/`--all` (which re-stages from the working tree), a pending `git add` in
the same compound command (which is about to stage current working-tree bytes),
or an explicit `-- pathspec` commit (which re-reads the working tree for those
paths regardless of the index -- see commit-provenance-guard.py's own
REMEDIATION-TEXT PATHSPEC GOTCHA for the precedent). Reproduced and closed by
test_index_vs_worktree_divergence_is_not_satisfied_by_worktree_review.

THE AUTO-DISPATCH CARVE-OUT (Gabriel, 2026-07-24). This gate is only satisfiable
because Gabriel granted an explicit carve-out to the standing session instruction
"Do not call the AgentTool unless the user requested it": a reviewer subagent MAY
be dispatched without asking, SOLELY to review a blast-radius / financial-decision
diff for this gate. Without that carve-out this gate would deny commits with no
permitted way to clear them -- a deadlock, not a guardrail. The carve-out is
narrow: it authorizes review dispatch, nothing else.

REVIEWER MODEL TIER. Doctrine is reviewer >= implementer, and financial/governor
code never below the top tier. Gabriel's 2026-07-24 amendment: do NOT hardcode a
single id -- "Fable might go away, just use highest intelligence available."
So this file carries a LADDER of acceptable top-tier ids rather than one constant;
a retired id degrades to the next entry instead of wedging the gate. The ladder is
a sweep target for reference_model_release_checklist.md, and EOS_REVIEW_MODELS
overrides it without a code change. Every dispatch must still PIN an explicit
`model` -- inheritance can yield an unusable id.

SAFETY INVARIANT, two-sided and deliberately asymmetric:
  - The gate's OWN machinery fails OPEN. Bad stdin, no git, unreadable repo,
    import failure, any unexpected exception -> exit 0, allow. A bug in a gate
    must never wedge the fleet.
  - A GRANT fails CLOSED. A missing, corrupt, stale, mis-keyed, cross-session, or
    under-tier artifact is not an approval. Ambiguity never resolves in the
    grant's favour -- same stance as lib/override_tokens.py.
  Concretely: "I cannot tell what this commit touches" -> allow. "I can tell it
  touches risk code and I cannot find a valid review" -> block.

ESCAPE HATCH: the shared session-scoped override-token contract
(lib/override_tokens.py), tier `allow-unreviewed-commit`, SINGLE-USE. Single-use
on purpose -- a multi-use token would let one approval cover an entire session of
unreviewed blast-radius commits, which is how the plan-gate ended up with 76 of 79
override markers empty. The token is checked ONLY after the gate has decided it
would otherwise block, because token_grants() CONSUMES: evaluating it
speculatively would burn Gabriel's approval on a commit that never needed one.

HONEST LIMIT. Same cooperative threat model as every other gate here: the session
being gated can also write its own review artifact via `--record`. This gate
raises the floor from "review silently skipped" to "review deliberately
falsified", and leaves an audit trail either way. It is not an adversarial
boundary and does not pretend to be.

A second honest limit (2026-07-24 review finding n8): a Bash call that mutates a
reviewed file AND commits it IN THE SAME COMMAND (e.g. `echo x >> hooks/g.py &&
git add -A && git commit ...`) defeats the content key by construction --
PreToolUse evaluates the command before any of it has run, so the key is
necessarily computed against pre-mutation bytes. This is the same TOCTOU class
every hook here accepts (repo_freshness.py, ora-autonomy-gate.py's text-matching
ceiling): the gate can only ever evaluate the state that exists at the moment it
fires, not the state a not-yet-executed command is about to create.

CLI (this is how the gate is actually satisfiable):
  python eos-review-gate.py --key
      -> {"key", "paths", "repo"} for the current risk diff. Give this to the
         reviewer so it reviews exactly what the gate will hash.
  python eos-review-gate.py --record --verdict approved --model <pinned-id> \
      --notes "<summary>"
      -> writes the artifact for the CURRENT key.

Stdlib only. ASCII-only. Windows (`python`).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import, same reasoning as commit-provenance-guard.py: an unguarded
# import crashes at MODULE LOAD, before main()'s fast-path check runs, so it
# would traceback on EVERY Bash call in EVERY session -- not just commits.
try:
    import override_tokens
    from git_commit_parse import (
        candidate_paths, find_commit_segment, git_lines, has_all_flag,
        is_git_commit, pending_add_paths, repo_root,
    )
    PARSE_CONTRACT_LOADED = True
except Exception:
    PARSE_CONTRACT_LOADED = False

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"
REVIEWS_SUBDIR = "reviews"

# Acceptable reviewer model ids, highest intelligence first. NOT a single
# hardcoded constant, by Gabriel's 2026-07-24 amendment -- a retired id must
# degrade to the next entry rather than make the gate unsatisfiable. Sweep target
# for reference_model_release_checklist.md.
REVIEWER_MODEL_LADDER = ("claude-fable-5", "claude-opus-4-8")

APPROVED_VERDICTS = ("approved", "pass", "no-blocking-findings")

OVERRIDE_TIER_ARGS = ("allow-unreviewed-commit", "unreviewed-blast-radius-commit",
                      30 * 60)

# ---------------------------------------------------------------------------
# risk classification -- CLAUDE.md's list, transcribed. Nothing invented here.
# ---------------------------------------------------------------------------

# Checked FIRST. A path matching any of these is never risk code, even if a risk
# rule below would otherwise match it.
_EXCLUDED_DIR_PARTS = {
    "node_modules", "__pycache__", ".git", "archive", "memory", "sessions",
    "site-packages", "dist", "build", ".venv", "venv",
}

_CONFIG_EXTS = {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}

# Financial-decision code: "engine math, scoring, benchmarking,
# capital-allocation/NOI" plus the named governor constants. Tokens are
# deliberately specific -- a bare "score"/"engine" would drag in search engines
# and UI scores, and a gate that cries wolf gets switched off.
#
# Split into two groups (2026-07-24 review finding m6, PoC 5): plain substring
# matching let the 3-letter fragment "noi" match "noise_filter.py". Long,
# already-distinctive tokens (e.g. "capital_alloc", which is a deliberate
# PREFIX match for capital_allocation.py/capital_allocator.py) stay substring --
# a boundary requirement would break that intentional prefix use. Only the
# short fragments actually prone to colliding with ordinary English/code words
# get boundary protection.
_FINANCE_TOKENS_SUBSTR = (
    "governor", "dscr", "hurdle", "cap_rate", "caprate",
    "underwrit", "valuation", "capital_config", "capital_alloc", "capital-alloc",
    "replacement_cost", "replacement-cost", "benchmark", "scoring", "waterfall",
    "amortiz",
)
# "engine" stays boundary-protected, not substring -- it is an ordinary English
# word ("search engine", "template engine", "game engine") the original design
# already avoided via delimited variants ("/engine/", "engine_", "_engine");
# folding those into a bare substring here would have reintroduced exactly the
# false-positive class the original comment above warns against.
_FINANCE_TOKENS_BOUNDARY = ("noi", "irr", "ltv", "engine")
_FINANCE_BOUNDARY_RE = re.compile(
    r"(?<![a-z0-9])(?:%s)(?![a-z0-9])"
    % "|".join(re.escape(t) for t in _FINANCE_TOKENS_BOUNDARY)
)
_FINANCE_CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java",
    ".rb", ".php", ".sql", ".json",
}


def _has_finance_token(rel):
    if any(t in rel for t in _FINANCE_TOKENS_SUBSTR):
        return True
    return bool(_FINANCE_BOUNDARY_RE.search(rel))


def risk_reason(rel):
    """Why `rel` (repo-relative, forward-slashed, lowercased) is blast-radius or
    financial-decision code -- or None if it is not."""
    parts = rel.split("/")
    base = parts[-1]
    ext = os.path.splitext(base)[1]

    if any(p in _EXCLUDED_DIR_PARTS for p in parts[:-1]):
        return None
    # Documentation is not enforcement code. CLAUDE.md is the one .md that IS
    # doctrine, and stays in scope.
    if ext == ".md" and base != "claude.md":
        return None

    if base == "claude.md":
        return "CLAUDE.md doctrine"
    # ROOT-anchored (2026-07-24 review finding M4): a bare "hooks somewhere in
    # the path" match flagged idiomatic React/Vue `src/hooks/useX.ts` as
    # enforcement code. CLAUDE.md's "hooks/**" means THIS repo's own top-level
    # hooks/ directory, not any directory that happens to be named hooks.
    if parts[0] == "hooks":
        return "hooks/** enforcement code"
    if ".env" in base:
        return "environment file"
    if "credential" in rel:
        return "credentials"
    if base == "confidential-terms.json":
        return "confidential-terms roster"
    if base in ("settings.json", "settings.local.json"):
        return "settings.json harness config"
    if "scheduled-tasks" in rel or "scheduled_tasks" in rel:
        return "scheduled-task registry"
    if base in ("_headers", "netlify.toml", "vercel.json") or base.endswith(".headers"):
        return "CSP/headers"
    if "csp" in base:
        return "CSP/headers"
    if ".claude" in parts[:-1] and ext in _CONFIG_EXTS:
        return "~/.claude config"
    if ext in _FINANCE_CODE_EXTS and _has_finance_token(rel):
        return "financial-decision / governor code"
    return None


# ---------------------------------------------------------------------------
# the review key: a content hash of exactly the risk files at stake
# ---------------------------------------------------------------------------

def _rel(repo, abs_path):
    try:
        rel = os.path.relpath(abs_path, repo)
    except ValueError:
        return None  # different drive -- not in this repo
    rel = rel.replace("\\", "/")
    if rel.startswith("../"):
        return None
    return rel.lower()


def risk_files(repo, cmd):
    """Sorted repo-relative risk paths this commit would capture.

    Returns [] when the command captures nothing risky AND when the parser could
    not determine what it captures -- both mean "nothing to gate on". That is the
    fail-open half of the safety invariant: this gate can only police what it can
    see, and every degradation in git_commit_parse biases toward fewer paths."""
    cands = candidate_paths(repo, cmd)
    if not cands:
        return []
    out = set()
    for abs_path in cands:
        rel = _rel(repo, abs_path)
        if rel and risk_reason(rel):
            out.add(rel)
    return sorted(out)


def _content_digest(repo, rel):
    """git's own blob object-id for the WORKING-TREE bytes of `rel`, or
    DELETED if the path cannot be read.

    CRLF-NORMALIZATION FIX (2026-07-24, discovered during the actual live
    merge attempt -- neither review round's test repos hit this, because
    files written directly by Python in a fresh temp repo never round-trip
    through a git CHECKOUT, so no CRLF conversion had ever fired there).
    This machine runs `core.autocrlf=true`. Hashing raw `open(path,"rb")`
    bytes meant `_content_digest` returned the CHECKED-OUT (CRLF) bytes,
    while `_index_digest` (below) returns `git show`'s NORMALIZED (LF)
    index blob -- so for a file already staged separately (a plain `git
    add` in an earlier step, then a bare `git commit`), the two digests
    differed for EVERY text file, unconditionally, regardless of whether the
    content was logically identical. That would have made the gate
    permanently unsatisfiable via --record for that entire commit shape --
    the exact "wedge the fleet" failure this gate must never cause.
    Routing through `git hash-object --stdin --path <rel>` applies the SAME
    clean-filter/autocrlf normalization git itself would apply on `git add`,
    so this now returns the identical object id `_index_digest` would see
    for logically-identical content, independent of on-disk line endings.
    Falls back to a raw sha256 read if git cannot answer (e.g. this path
    resolves outside any repo git recognizes) -- a degraded but still-total
    digest, never a crash."""
    path = os.path.join(repo, rel)
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return "DELETED"
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "hash-object", "--stdin", "--path", rel],
            input=data, capture_output=True, timeout=5)
        if proc.returncode == 0:
            out = proc.stdout.decode("ascii", "strict").strip()
            if out:
                return out
    except Exception:
        pass
    return hashlib.sha256(data).hexdigest()


def _index_realcase_path(repo, rel):
    """Resolve `rel` (repo-relative, LOWERCASED -- every rel in this module is,
    per _rel()) to its real on-disk casing as recorded in the index, or None
    if no index entry matches case-insensitively.

    CASE-SENSITIVITY FIX (2026-07-24, independent-review finding B1). `git
    show :path` -- the index-blob shorthand `_index_digest` uses -- matches
    its path argument LITERALLY, even under Windows' default
    core.ignorecase=true: that setting governs working-tree/index STAT
    lookups, not this ref-syntax path match. So `git show :claude.md` misses
    an index entry actually named `CLAUDE.md`, `_index_digest` returns None,
    and the caller's documented-safe fallback silently reverts to the
    WORKING-TREE digest -- reintroducing, for exactly this file, the bug M1
    exists to close. CLAUDE.md is the flagship risk file (a Hard Invariant),
    so this was the worst possible file for the fallback to bite.

    This is the identical bug class commit-provenance-guard.py already hit
    and fixed on 2026-07-20 for `git log -- <pathspec>` (see that file's own
    CASE-SENSITIVITY FIX note) by wrapping the pathspec as `:(literal,icase)`.
    `git ls-files`, unlike the `:path` ref-syntax shorthand, DOES honor
    pathspec magic, so the same wrapper recovers the real casing here; the
    result is then used for the actual `git show :<realcase>` blob lookup.

    `-c core.quotepath=false` (targeted re-review, same day): without it, a
    non-ASCII filename comes back C-quoted (e.g. `"hooks/caf\303\251.py"`),
    which the subsequent `git show :<that literal text>` cannot resolve --
    degrades to the documented worktree-digest fallback rather than a crash,
    but every real risk pattern in this gate (claude.md, settings.json,
    hooks/**, finance tokens) is ASCII, so this closes a gap with no
    observed real-world trigger."""
    out = git_lines(repo, ["-c", "core.quotepath=false", "ls-files", "--cached",
                           "--", ":(literal,icase)" + rel])
    return out[0] if out else None


def _index_digest(repo, rel):
    """git's own blob object-id for the STAGED (index) content of `rel`, or
    None if `rel` is not in the index (untracked, removed from the index) or
    git cannot answer.

    OBJECT-ID FORM, NOT A CONTENT HASH (2026-07-24, paired with
    _content_digest's CRLF-normalization fix): `git rev-parse :<path>`
    returns the SAME kind of value `git hash-object` computes for
    normalized working-tree content -- both are git's canonical blob oid
    for what would be stored on `git add`. Comparing two oids this way is
    correct by construction; comparing a raw sha256-of-index-bytes against a
    raw sha256-of-working-tree-bytes (the pre-fix shape) is NOT, whenever
    autocrlf normalization makes the two byte streams differ even for
    logically identical content."""
    realcase = _index_realcase_path(repo, rel)
    if realcase is None:
        return None
    out = git_lines(repo, ["rev-parse", "--verify", "-q", ":" + realcase])
    return out[0] if out else None


def _worktree_sourced_rels(repo, cmd):
    """Repo-relative (lowercased) paths that THIS commit invocation would read
    from the WORKING TREE rather than the index -- see the module docstring's
    PROVENANCE FIX note. Real git semantics, not a heuristic:
      - an explicit `-- pathspec` commit RE-READS the working tree for those
        paths regardless of what is staged (commit-provenance-guard.py's own
        documented REMEDIATION-TEXT PATHSPEC GOTCHA);
      - `-a`/`--all` re-stages every tracked-modified path from the working
        tree before committing;
      - a `git add` pending in the same compound command (not yet run at
        hook-fire time) is about to stage current working-tree bytes.
    Everything else is index-sourced: exactly what a plain `git commit` with
    nothing already covering it actually lands.
    Degrades toward the EMPTY set on any git-query failure -- see
    _origin_content_digest's fallback, which biases any resulting uncertainty
    toward MISMATCHING a previously-recorded key (more review required), never
    toward silently matching one that covered different bytes."""
    out = set()
    commit_args = find_commit_segment(cmd)
    if commit_args is None:
        return out
    if "--" in commit_args:
        idx = commit_args.index("--")
        for p in commit_args[idx + 1:]:
            if not p:
                continue
            rel = _rel(repo, os.path.join(repo, p))
            if rel:
                out.add(rel)
        return out  # pathspec form: ONLY these paths, all worktree-sourced
    if has_all_flag(commit_args):
        for p in (git_lines(repo, ["diff", "--name-only"]) or []):
            rel = _rel(repo, os.path.join(repo, p))
            if rel:
                out.add(rel)
    for abs_path in pending_add_paths(repo, cmd):
        rel = _rel(repo, abs_path)
        if rel:
            out.add(rel)
    return out


def _origin_content_digest(repo, cmd, rel, worktree_sourced):
    """sha256 of whichever bytes THIS commit invocation would actually land for
    `rel` -- the working tree for a path in `worktree_sourced`, else the index.
    Falls back to the working-tree digest when the index has no entry (a path
    that is only reachable there is, by definition, worktree-sourced) -- this
    fallback can only make the key diverge from a stale review, never cause a
    stale review to validate."""
    if rel in worktree_sourced:
        return _content_digest(repo, rel)
    digest = _index_digest(repo, rel)
    return digest if digest is not None else _content_digest(repo, rel)


def review_key(repo, rels, digest_fn=None):
    """A stable key over the exact CONTENT of the risk files under review, as
    resolved by `digest_fn(rel)` (defaults to _content_digest, i.e. plain
    working-tree bytes -- the CLI's view of "what is at risk right now").

    Keyed on content, not on a commit range: at PreToolUse time there is no
    commit to name yet, and a range would not change when the implementer keeps
    editing after the review. Content does. That is precisely the staleness
    property the gate needs -- edit one reviewed byte and the key moves."""
    if digest_fn is None:
        digest_fn = lambda r: _content_digest(repo, r)  # noqa: E731
    h = hashlib.sha256()
    for rel in rels:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(digest_fn(rel).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# the review artifact
# ---------------------------------------------------------------------------

def sessions_dir():
    return os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def accepted_models():
    raw = os.environ.get("EOS_REVIEW_MODELS")
    if raw:
        vals = tuple(v.strip() for v in raw.split(",") if v.strip())
        if vals:
            return vals
    return REVIEWER_MODEL_LADDER


def artifact_path(session_id, key):
    """Session-scoped, mirroring the override-token layout: hooks/sessions/ is
    gitignored, so an artifact cannot be swept into a commit by `git add -A` and
    cannot be re-minted at age ~0 by a fresh clone (the 2026-07-16 defect that
    self-granted a live override). Session scoping also means one session's
    review does not silently authorize another's commit -- a real constraint
    with 4+ sessions routinely running here."""
    if not override_tokens.SESSION_ID_RE.match(session_id or ""):
        return None
    return os.path.join(sessions_dir(), session_id, REVIEWS_SUBDIR, key + ".json")


def valid_review(session_id, key):
    """The artifact's fields if a valid review authorizes `key` for this session,
    else None. Every failure mode -- absent, unreadable, malformed, wrong key,
    wrong session, non-approving verdict, under-tier reviewer -- is NOT a grant."""
    path = artifact_path(session_id, key)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("key") != key:
        return None
    if data.get("session") != session_id:
        return None
    if str(data.get("verdict", "")).strip().lower() not in APPROVED_VERDICTS:
        return None
    if data.get("reviewer_model") not in accepted_models():
        return None
    return data


# ---------------------------------------------------------------------------
# messaging
# ---------------------------------------------------------------------------

def build_message(repo, rels, session_id, key, artifact_state):
    listing = "\n".join(
        "  - %s   [%s]" % (r, risk_reason(r)) for r in rels[:8])
    more = "" if len(rels) <= 8 else "\n  ... and %d more" % (len(rels) - 8)
    hook = os.path.abspath(__file__).replace("\\", "/")
    tier = override_tokens.Tier(*OVERRIDE_TIER_ARGS, single_use=True)
    return (
        "This `git commit` would land %d blast-radius / financial-decision "
        "file(s) with %s:\n%s%s\n\n"
        "Ratified by Gabriel 2026-07-24: this class of code gets an INDEPENDENT "
        "review before it lands -- an implementer re-reading their own diff does "
        "not count. One measured pass found a `major` defect in an 8-line diff.\n\n"
        "To clear this gate:\n"
        "  1. Dispatch an independent reviewer on exactly these files. Gabriel's "
        "carve-out permits dispatching it WITHOUT asking, for this purpose only. "
        "PIN the model explicitly -- one of: %s.\n"
        "  2. Record its verdict:\n"
        "     python \"%s\" --record --verdict approved --model <pinned-id> "
        "--notes \"<what was reviewed and found>\"\n"
        "     (`--key` prints the exact key + path list to hand the reviewer.)\n"
        "  3. The artifact is keyed to this exact content. Edit any of these "
        "files afterward and it stops matching -- re-review, do not re-record.\n\n"
        "If Gabriel has approved landing this UNREVIEWED, write a single-use "
        "override token:\n%s\n"
        "Current review state: %s\n"
        % (len(rels), "no matching review artifact", listing, more,
           ", ".join(accepted_models()), hook,
           override_tokens.describe_token(session_id, tier),
           artifact_state)
    )


def artifact_state_note(session_id, key):
    """Distinguish 'never reviewed' from 'reviewed, but the artifact no longer
    matches' -- the second is the common case and the confusing one."""
    path = artifact_path(session_id, key)
    if path and os.path.isfile(path):
        return "an artifact exists for this key but did not validate (verdict, " \
               "reviewer model, or session mismatch) -- see the fields above."
    base = os.path.join(sessions_dir(), session_id or "", REVIEWS_SUBDIR)
    try:
        existing = [f for f in os.listdir(base) if f.endswith(".json")]
    except OSError:
        existing = []
    if existing:
        return ("%d earlier review(s) recorded this session, none matching the "
                "current content (key %s). The files changed after they were "
                "reviewed -- that is this gate working as designed."
                % (len(existing), key[:12]))
    return "no review recorded this session (key %s)." % key[:12]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def _worktree_risk_rels(root):
    """Every currently at-risk repo-relative path -- staged, tracked-and-
    modified-but-unstaged, AND untracked. Union, not a guess at which specific
    future commit invocation the operator will type.

    UNTRACKED-FILE FIX (2026-07-24 review finding M3): the previous version
    tried two synthetic commands ("git commit", "git commit -a") to discover
    what to key on -- neither sees a brand-new, never-`git add`ed risk file,
    because staged/`-a` are both meaningless for a path with no index entry at
    all. That is precisely this fleet's own committing shape
    (`git add <paths> && git commit -q -F -`, memory-documented): a session
    creates hooks/new-guard.py and commits it in one compound call. Under the
    old logic the HOOK correctly blocked it (via pending_add_paths) while
    `--record` refused with "nothing at risk in the working tree" -- an
    unsatisfiable loop with no exit but the override token, reproducing the
    exact plan-gate failure (76/79 empty overrides) this gate exists to avoid.
    `git ls-files --others --exclude-standard` closes the gap."""
    staged = git_lines(root, ["diff", "--cached", "--name-only"]) or []
    modified = git_lines(root, ["diff", "--name-only"]) or []
    untracked = git_lines(root, ["ls-files", "--others", "--exclude-standard"]) or []
    out = set()
    for p in staged + modified + untracked:
        rel = p.replace("\\", "/").lower()
        if risk_reason(rel):
            out.add(rel)
    return sorted(out)


def _cli_context(argv):
    repo = _arg(argv, "--repo") or os.getcwd()
    root = repo_root("", repo)
    if not root:
        sys.stderr.write("eos-review-gate: not a git repo: %s\n" % repo)
        return None, None, None
    session_id = (_arg(argv, "--session")
                  or os.environ.get("CLAUDE_CODE_SESSION_ID") or "")
    if not override_tokens.SESSION_ID_RE.match(session_id):
        sys.stderr.write(
            "eos-review-gate: no usable session id (set CLAUDE_CODE_SESSION_ID "
            "or pass --session); a review artifact cannot be addressed.\n")
        return None, None, None
    rels = _worktree_risk_rels(root)
    return root, session_id, rels


def cli_key(argv):
    root, session_id, rels = _cli_context(argv)
    if root is None:
        return 1
    sys.stdout.write(json.dumps({
        "repo": root.replace("\\", "/"),
        "paths": rels,
        "reasons": {r: risk_reason(r) for r in rels},
        "key": review_key(root, rels) if rels else "",
    }, indent=2))
    return 0


def cli_record(argv):
    root, session_id, rels = _cli_context(argv)
    if root is None:
        return 1
    if not rels:
        sys.stderr.write(
            "eos-review-gate: nothing at risk in the working tree -- there is no "
            "blast-radius diff to review, so no artifact is needed or written.\n")
        return 1
    model = _arg(argv, "--model")
    if model not in accepted_models():
        sys.stderr.write(
            "eos-review-gate: reviewer model %r is not in the accepted tier "
            "(%s). Reviewer must be >= implementer; pin one explicitly.\n"
            % (model, ", ".join(accepted_models())))
        return 1
    verdict = (_arg(argv, "--verdict") or "").strip().lower()
    if verdict not in APPROVED_VERDICTS:
        sys.stderr.write(
            "eos-review-gate: verdict %r recorded as NON-approving; the gate will "
            "keep blocking. Approving verdicts: %s\n"
            % (verdict, ", ".join(APPROVED_VERDICTS)))
    key = review_key(root, rels)
    path = artifact_path(session_id, key)
    if not path:
        sys.stderr.write("eos-review-gate: session id cannot address an artifact.\n")
        return 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = {
        "key": key,
        "session": session_id,
        "verdict": verdict,
        "reviewer_model": model,
        "paths": rels,
        "repo": root.replace("\\", "/"),
        "notes": _arg(argv, "--notes") or "",
        "ts": int(time.time()),
    }
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(record, fh, indent=2)
    record["artifact_path"] = path
    sys.stdout.write(json.dumps(record, indent=2))
    return 0


# ---------------------------------------------------------------------------
# hook
# ---------------------------------------------------------------------------

def main():
    if not PARSE_CONTRACT_LOADED:
        return  # no information -> allow (see the guarded import above)

    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    cmd = tool_input.get("command")
    if not is_git_commit(cmd):
        return  # fast path: not a commit -> no git calls at all

    mode = (os.environ.get("EOS_REVIEW_GATE_MODE") or "block").strip().lower()
    if mode == "off":
        return
    if mode not in ("block", "warn"):
        mode = "block"  # a typo must never silently disable a security gate

    repo = repo_root(cmd, payload.get("cwd") or "")
    if not repo:
        return  # cannot resolve a repo -> no information -> allow

    rels = risk_files(repo, cmd)
    if not rels:
        return  # nothing blast-radius in this commit -> allow silently

    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""

    # Origin-aware digest (see module docstring's PROVENANCE FIX / M1): the key
    # must reflect whatever bytes THIS specific commit invocation actually
    # lands per path -- index for a plainly-staged path, working tree for one
    # sourced via -a/pending-add/explicit pathspec.
    worktree_sourced = _worktree_sourced_rels(repo, cmd)
    digest_fn = lambda r: _origin_content_digest(repo, cmd, r, worktree_sourced)  # noqa: E731
    key = review_key(repo, rels, digest_fn)
    if valid_review(session_id, key):
        return  # reviewed, and the review matches THIS content -> allow

    # Only in BLOCK mode is a grant actually needed, so the single-use token is
    # evaluated (and burned) ONLY here -- not in warn mode, which never blocks
    # and must never spend Gabriel's approval on a commit that didn't need one
    # (2026-07-24 review finding m7: the token was previously consumed before
    # the mode branch, so a live token silently vanished under warn mode with
    # no warning, no block, and the approval wasted).
    if mode == "block":
        tier = override_tokens.Tier(*OVERRIDE_TIER_ARGS, single_use=True)
        if override_tokens.token_grants(session_id, tier) is not None:
            sys.stderr.write(
                "eos-review-gate: proceeding UNREVIEWED on %d blast-radius "
                "file(s) under a single-use override token (consumed).\n"
                % len(rels))
            return

    message = build_message(repo, rels, session_id, key,
                            artifact_state_note(session_id, key))
    if mode == "warn":
        sys.stderr.write("WARNING (eos-review-gate, warn mode -- not blocking): "
                         + message + "\n")
        return
    sys.stderr.write("BLOCKED (eos-review-gate): " + message + "\n")
    sys.exit(2)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--key" in argv or "--record" in argv:
        try:
            sys.exit(cli_key(argv) if "--key" in argv else cli_record(argv))
        except Exception as exc:  # CLI errors are the operator's to see
            sys.stderr.write("eos-review-gate: %s\n" % exc)
            sys.exit(1)
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # fail open: a bug in this gate must never block a tool call
    sys.exit(0)
