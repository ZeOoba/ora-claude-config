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

EOS_REVIEW_MODELS MUST be set in settings.json's top-level "env" block to reach
this hook -- confirmed 2026-09-07 (incident: commit 4c5d441 on
build/git-probe-dedup) that setting it inline on the gated Bash command's own
shell (e.g. `EOS_REVIEW_MODELS=... python -c ... && git commit ...`) does NOT
work: this hook is spawned by the harness as its own PreToolUse process, not as
a child of the command it gates, so a shell-local assignment on that command
line is invisible to it. settings.json's env block, by contrast, is written
into every subprocess Claude Code spawns, hook processes included. TREAT THIS
AS A TEMPORARY BRIDGE, not the fix: unlike OVERRIDE_TIER_ARGS below (single-use,
30-min TTL), a settings.json env override is unbounded -- it silently widens
this fail-closed gate for every commit in every session until someone removes
it. Prefer sweeping REVIEWER_MODEL_LADDER itself (reference_model_release_
checklist.md item 9) and pull the env override once that lands.

A self-reported model id can carry a trailing context-window tag (e.g.
"claude-opus-5[1m]"); `_bare_model()` strips it before every ladder/env
comparison so that formatting alone never refuses a genuine top-tier reviewer.

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
  --cmd "<exact git commit invocation>" (2026-07-26, either subcommand):
      scope --key/--record to ONLY what that specific commit would land,
      identically to how main() will gate it -- required for a PATHSPEC-
      SCOPED commit (`git commit ... -- <path>`) in a busy shared checkout:
      without --cmd, --key/--record score every at-risk path anywhere in the
      working tree, which can never match main()'s narrower per-commit key
      whenever another session has unrelated risk files staged/modified/
      untracked elsewhere. See scope_for_cmd()'s docstring.

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
        is_git_commit, pathspec_arg_paths, pending_add_paths, repo_root,
        tokenize_cmd_segments, _segment_git_subcommand_and_args,
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
REVIEWER_MODEL_LADDER = ("claude-fable-5-1", "claude-opus-5")

# A self-reported model id can carry a trailing context-window tag, e.g.
# "claude-opus-5[1m]" -- same hazard maintenance/model-canary-probe.py's
# bare_model() exists to strip. An exact-match comparison against the ladder
# would otherwise refuse a genuine top-tier reviewer over formatting alone,
# recreating the exact 2026-09-07 incident this ladder update fixes. Applied
# once at --record intake (the artifact always stores the bare id) and again
# on read, in case an older artifact was written before this normalization
# existed.
_MODEL_SUFFIX_RE = re.compile(r"\[[^\]]*\]$")

# Splits an EOS_REVIEW_MODELS list on commas that are NOT inside an unclosed
# "[...]" tag, so a comma-bearing context-window tag (theoretical -- no real
# tag in this fleet's data has ever carried one, per 2026-09-08 review) can't
# get shredded into two garbage tokens by a naive raw.split(","). See
# accepted_models()'s comment for the fuller reasoning (findings 2+4).
_MODEL_LIST_SPLIT_RE = re.compile(r",(?![^\[]*\])")


def _bare_model(mid):
    """Strip surrounding whitespace, then a trailing [...] suffix. Strips
    INSIDE this function (not left to callers) so every call site gets the
    same normalization for free -- an independent review (2026-09-08) found
    this file's original callers stripped inconsistently (accepted_models()
    did, cli_record()/valid_review() didn't), which meant a reviewer id with
    trailing whitespace instead of a suffix could still be wrongly refused.
    Matches maintenance/model-canary-probe.py's bare_model(), which already
    strips before its own regex sub."""
    if not isinstance(mid, str):
        return mid
    return _MODEL_SUFFIX_RE.sub("", mid.strip())

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
    observed real-world trigger.

    UPDATE (2026-09-07, git-probe-dedup follow-up): this `-c
    core.quotepath=false` flag is exactly what turned a THEORETICAL non-ASCII
    gap into a real, always-live one -- it makes THIS call site the one
    git_lines() caller in the whole module that is exposed to raw non-UTF-8
    stdout bytes regardless of repo/global quotepath config, and until
    git_commit_parse.git_lines() gained encoding="utf-8", errors="replace"
    (via delegating to git_probe_common.git()), a non-ASCII path here did NOT
    degrade to the fallback described above -- it crashed the whole hook with
    an unhandled AttributeError (`None.splitlines()`), caught only by
    __main__'s blanket `except Exception: pass`, i.e. a silent ALLOW of the
    entire commit. See git_lines()'s own docstring for the verified mechanism
    and hooks/tests/test-eos-review-gate.py's
    test_index_realcase_path_survives_non_ascii_under_quotepath_false for the
    regression proof. The fallback-not-crash claim above is accurate again as
    of that fix."""
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
        # DIRECTORY-PATHSPEC EXPANSION (2026-07-26, REFUTE F1/F2 fix): must
        # mirror candidate_paths' own pathspec_arg_paths() expansion exactly.
        # Without this, a directory pathspec's expanded FILES (from
        # risk_files/candidate_paths) would not appear in this set at all --
        # _origin_content_digest would then treat them as index-sourced
        # instead of worktree-sourced, missing the same re-reads-the-
        # working-tree behavior this function exists to capture.
        for p in commit_args[idx + 1:]:
            if not p:
                continue
            for abs_path in pathspec_arg_paths(repo, p):
                rel = _rel(repo, abs_path)
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


def scope_for_cmd(repo, cmd):
    """(rels, digest_fn) for the exact bytes a specific `git commit` invocation
    `cmd` would land -- the SAME computation main() uses to decide whether to
    block. Single source of truth for both call sites (2026-07-26 fix): before
    this, --key/--record used _worktree_risk_rels (every at-risk path in the
    WHOLE working tree) while main() used this narrower, cmd-scoped
    computation. For a pathspec-scoped commit (`git commit ... -- <path>`) in
    a busy shared checkout with OTHER risk files staged/modified/untracked
    elsewhere, those two scopes differ -- so a review recorded via --record
    keyed over the wider set could never validate against main()'s narrower
    key for that same commit. The operator's only paths forward were
    unstaging the foreign files or burning the single-use override token,
    for a commit that was already correctly scoped and needed neither.
    Passing this cmd to --key/--record now produces a key GUARANTEED to
    match what main() will check for that exact invocation."""
    rels = risk_files(repo, cmd)
    worktree_sourced = _worktree_sourced_rels(repo, cmd)
    digest_fn = lambda r: _origin_content_digest(repo, cmd, r, worktree_sourced)  # noqa: E731
    return rels, digest_fn


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
        # _bare_model here too -- an operator pastes EOS_REVIEW_MODELS straight
        # from a self-reported id (the exact scenario the docstring points them
        # at), and a suffixed value on this side must not wedge the gate the
        # same way an unnormalized --model would (see _bare_model's callers).
        #
        # Split BEFORE normalizing, but bracket-aware (2026-09-08 independent
        # review, findings 2+4): a plain `raw.split(",")` has two bugs. (a) A
        # bracket-only entry (e.g. "claude-opus-5,[1m]") passes the `v.strip()`
        # truthiness check on the RAW token, then _bare_model() reduces it to
        # "" -- an empty string that still ends up IN the accepted tuple, so a
        # reviewer_model of "" would validate: a genuine fail-OPEN hole in a
        # fail-closed gate. (b) a comma inside a real tag ("claude-opus-5[1m,
        # 200k]") splits mid-tag into two garbage tokens that match nothing --
        # fail-closed, not a bypass, but it can wedge a genuinely valid id.
        # _MODEL_LIST_SPLIT_RE splits only on a comma NOT inside an unclosed
        # "[...]"; filtering on the truthiness of the NORMALIZED value (not
        # the raw token) closes (a).
        vals = tuple(
            m for m in (_bare_model(v) for v in _MODEL_LIST_SPLIT_RE.split(raw))
            if m
        )
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
    if _bare_model(data.get("reviewer_model")) not in accepted_models():
        return None
    return data


# ---------------------------------------------------------------------------
# messaging
# ---------------------------------------------------------------------------

def message_shape_hint(cmd):
    """OI-122. PURE DIAGNOSTIC: reads already-computed parse state and returns
    advisory TEXT ONLY. It can never change which paths this gate blocks on --
    callers append it to the message and nothing else.

    tokenize_cmd_segments() attaches a trailing `-- <pathspec>` correctly for a
    single-line `-m` and for the fleet-sanctioned heredoc-fed multi-line form.
    A DIRECTLY-QUOTED multi-line `-m "a<newline>b"` is not a recognized
    construct, so per-line tokenization strands the pathspec in a disconnected
    segment, find_commit_segment() never sees it, and scope falls back to the
    no-pathspec set (staged + pending-add + `-a`-modified). In a busy shared
    checkout that surfaces as a false BLOCK on ANOTHER session's staged files.

    Why this is a message fix and not a tokenizer fix: rounds 2 and 3 of
    tokenize_cmd_segments both tried to track quote state across arbitrary
    content, and both shipped false ALLOWs -- a decoy `-- <path>` leaking as
    the real pathspec, a real commit hidden behind a decoy `--dry-run`, plus
    O(n^2) blowup (see git_commit_parse.py:327-376). Fail-CLOSED friction with
    an accurate message beats fail-OPEN silence. Do not reopen that.

    DETECTION (review finding F2): the signal is a bare `--` token STRANDED in
    a tokenized segment that is not a command invocation of its own -- i.e. the
    wreckage of a broken message -- NOT a regex over raw command text. Regexing
    raw text also matched `--` used as ASCII punctuation inside a heredoc body,
    and a legitimately chained `git log ... -- <path>`, firing confidently-wrong
    advice on commits that parsed and scoped perfectly well.

    Segments are classified with git_commit_parse's own
    _segment_git_subcommand_and_args rather than a bare `s[0] != "git"` test,
    so an env-assignment prefix (`GIT_PAGER=cat git log ... -- <path>`) is not
    mistaken for wreckage (review finding N2).

    ACCEPTED RESIDUALS, both minor and both self-correcting because the worst
    case is one wasted read of an advisory paragraph:
      - N1: a chained NON-git command carrying a legitimate bare `--`
        (`npm test -- --grep auth`, `kubectl exec ... --`) alongside a
        no-pathspec commit still trips this. Classifying arbitrary commands is
        out of scope for a diagnostic.
      - N3: if a stranded message line happens to BEGIN with the word "git",
        that segment classifies as a git invocation and the hint stays silent
        on a real case. Fails toward silence, matching this function's stance.

    Recomputes find_commit_segment/tokenize_cmd_segments rather than reusing
    earlier results; both are pure and deterministic over `cmd`. Returns ""
    whenever it cannot be confident, so the default is silence, never a
    misleading claim."""
    if not isinstance(cmd, str) or "\n" not in cmd:
        return ""  # single-line commands attach their pathspec fine
    commit_args = find_commit_segment(cmd)
    if commit_args is not None and "--" in commit_args:
        return ""  # pathspec recovered -- nothing to explain
    if not [s for s in tokenize_cmd_segments(cmd)
            if s and "--" in s and _segment_git_subcommand_and_args(s) is None]:
        return ""  # no stranded pathspec wreckage -- say nothing
    return (
        "\nIF THIS COMMIT WAS MEANT TO BE PATHSPEC-SCOPED, READ THIS FIRST -- "
        "the paths above may not be yours. This command carries a `--` "
        "pathspec separator, but its `-m` message is a directly-quoted "
        "multi-line string, which this parser cannot attach a pathspec "
        "through. The pathspec was stranded, so scope fell back to the "
        "no-pathspec set (staged + pending-add + `-a`-modified) -- in a shared "
        "checkout that can include another session's staged files, which your "
        "commit would not actually land.\n"
        "  Re-run with a SINGLE-LINE `-m`, or a heredoc-fed message -- both "
        "attach the pathspec correctly. The heredoc terminator must sit at "
        "column 0, so copy the following EXACTLY, without adding indentation:\n"
        "\n"
        "git commit -m \"$(cat <<'EOF'\n"
        "<title>\n"
        "\n"
        "<body>\n"
        "EOF\n"
        ")\" -- <path>\n"
        "\n"
        "  Do NOT mint an override token for this. Do NOT record a review "
        "verdict over the fallback set either: the artifact is keyed to those "
        "paths and their digests, so a later plain `git commit` from THIS "
        "session that sweeps the same files would validate against it and "
        "land them unreviewed.\n"
    )


def build_message(repo, rels, session_id, key, artifact_state, shape_hint=""):
    listing = "\n".join(
        "  - %s   [%s]" % (r, risk_reason(r)) for r in rels[:8])
    more = "" if len(rels) <= 8 else "\n  ... and %d more" % (len(rels) - 8)
    hook = os.path.abspath(__file__).replace("\\", "/")
    # PRINT A COMMAND THE OTHER GATE PERMITS (2026-08-12, hit live). Spelling this
    # with os.path.abspath(__file__) puts the LIVE <root>/hooks/ path into the
    # command the operator is told to run. config-write-guard matches "write
    # indicator + governance-path marker anywhere in the command", and ">" matches
    # inside an ASCII arrow -- which review prose is full of ("199/204 -> 204/204")
    # -- so following this gate's own instructions verbatim was BLOCKED by that
    # guard, whose only named exit was minting a 60-minute, multi-use,
    # governance-WIDE token to permit one artifact write. Same class as the
    # `--model ` -> "del " deadlock tool_call_paths.py word-anchored on 2026-08-03:
    # a false positive that forces a strictly broader privilege is a security
    # regression, not caution.
    #
    # A repo-relative spelling carries no governance marker at all (the markers are
    # root-prefixed), so it is not gated even with arrows in --notes -- and
    # sessions_dir() is absolute, so the artifact still lands in the live tree.
    # Only offered when the repo actually carries its own copy, which is exactly the
    # ~/.claude case where the block bites; every other repo keeps the absolute
    # path, and the NOTE below is what keeps that form usable.
    #
    # KNOWN, AND FAIL-CLOSED: the relative form runs the REPO's copy, which in a
    # gate-development worktree may be mid-edit or divergent. A broken copy errors
    # visibly; a divergent one writes a mis-keyed artifact and the live gate KEEPS
    # BLOCKING. Neither is an evasion path -- a session that wanted to forge a
    # verdict could always write the artifact JSON directly (see this module's
    # HONEST LIMIT). The cost is operator confusion, in the one scenario where the
    # operator is editing this gate anyway.
    own_copy = os.path.join(repo or "", "hooks", "eos-review-gate.py")
    if repo and os.path.isfile(own_copy):
        invocation = "python hooks/eos-review-gate.py"
    else:
        invocation = 'python "%s"' % hook
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
        "  2. Record its verdict (run it from the repo root, as spelled):\n"
        "     %s --record --verdict approved --model <pinned-id> "
        "--notes \"<what was reviewed and found>\"\n"
        "     (`--key` prints the exact key + path list to hand the reviewer.)\n"
        "     TIP: pass --notes-file <path> instead of --notes to keep the prose "
        "OUT of the command text entirely -- that is the clean exit when the notes "
        "themselves would trip config-write-guard (an ASCII arrow, or describing a "
        "review that involved rm -rf). Write the notes to a scratch file, then "
        "point --notes-file at it.\n"
        "     NOTE: an ASCII arrow in --notes (\"199/204 -> 204/204\") reads as a "
        "`>` redirect to config-write-guard; combined with an absolute hooks/ path "
        "that BLOCKS, and minting allow-config-write for it would grant far more "
        "than this one artifact write needs. Use the spelling above verbatim, or "
        "write 'to' instead of the arrow.\n"
        "     If this commit is PATHSPEC-SCOPED (`git commit ... -- <path>`), "
        "pass `--cmd \"<the exact git commit invocation>\"` to both --key and "
        "--record so the review scopes to only what THIS commit lands -- "
        "otherwise, in a busy shared checkout, other sessions' unrelated "
        "staged/modified/untracked risk files get scored into the key too and "
        "it will never match.\n"
        "  3. The artifact is keyed to this exact content. Edit any of these "
        "files afterward and it stops matching -- re-review, do not re-record.\n\n"
        "If Gabriel has approved landing this UNREVIEWED, write a single-use "
        "override token:\n%s\n"
        "Current review state: %s\n%s"
        % (len(rels), "no matching review artifact", listing, more,
           ", ".join(accepted_models()), invocation,
           override_tokens.describe_token(session_id, tier),
           artifact_state, shape_hint)
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

def _resolve_notes(argv):
    """Review notes from `--notes-file <path>` if given, else `--notes <text>`.

    WHY --notes-file EXISTS (2026-08-16). config-write-guard blocks on
    "write indicator + governance-path marker anywhere in the command text", and
    a --record invocation necessarily names a live hooks/ path. So the NOTES
    THEMSELVES can block the recording: describing a security review that
    involved `rm -rf`, or writing an ASCII arrow (which reads as a `>`
    redirect), trips the guard. That is a self-inflicted deadlock unique to
    security work that documents itself -- the more precisely you describe what
    you reviewed, the more likely you cannot record it.

    The guard's matcher is deliberately NOT narrowable (see
    feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md), and minting a
    governance-wide token to record an artifact is strictly worse than the
    problem. Moving the prose OUT of the command line removes the trigger
    without touching the guard at all: the command then contains only a path.

    --notes-file wins when both are supplied, and a read failure is FATAL rather
    than silently falling back to an empty string -- a review artifact whose
    notes vanished is worse than one that failed loudly."""
    path = _arg(argv, "--notes-file")
    if path:
        # utf-8-sig, not utf-8: this box is PowerShell-primary, where `>` and
        # Out-File default to UTF-16LE and Set-Content can emit a UTF-8 BOM.
        # A BOM is NOT whitespace, so U+FEFF survived .strip() straight into the
        # artifact's notes. UTF-16 still raises -- loudly and by design -- but
        # the error now says what to do about it.
        try:
            with open(path, encoding="utf-8-sig") as fh:
                return fh.read().strip()
        except UnicodeDecodeError as e:
            raise SystemExit(
                "eos-review-gate: --notes-file %s is not UTF-8 (%s). PowerShell's "
                "`>` and Out-File default to UTF-16LE -- rewrite it with "
                "`Set-Content -Encoding utf8` or a UTF-8 heredoc and retry."
                % (path, e))
    return _arg(argv, "--notes") or ""


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


# Every CLI flag this tool actually reads. Deliberately NOT a list of every
# "--x" string in this file: --cached/--name-only/--others/--exclude-standard/
# --verify/--path/--stdin are arguments this script passes to `git`, not flags
# it accepts. Keep this set in sync when adding a CLI flag; `_flagset_is_consistent()`
# asserts it against the real `_arg(argv, ...)` call sites.
_VALUE_FLAGS = ("--repo", "--session", "--cmd", "--model", "--verdict",
                "--notes", "--notes-file")
_BOOL_FLAGS = ("--key", "--record")
KNOWN_CLI_FLAGS = frozenset(_VALUE_FLAGS + _BOOL_FLAGS)

# Stamped into every artifact so version skew is visible AFTER the fact too.
# OI-181's incident was undiagnosable from the artifact alone: an empty `notes`
# field looks identical whether the reviewer wrote nothing or the tool silently
# dropped it. Bump this when the CLI contract changes.
__version__ = "2026.08.16"


def _flagset_is_consistent():
    """Assert KNOWN_CLI_FLAGS still covers every flag `_arg(argv, ...)` reads.

    Guards against this fix causing the very failure it prevents: if someone
    adds a CLI flag and forgets this set, `reject_unknown_flags` would reject a
    LEGITIMATE flag. That fails loudly rather than silently, so it is not a
    security hole -- but it is a confusing break, and it is cheap to catch.
    Returns the missing flags, empty when consistent."""
    try:
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
    except OSError:
        return ()  # cannot read own source -> no information -> stay quiet
    read_flags = set(re.findall(r'_arg\(argv,\s*"(--[a-z-]+)"', src))
    return tuple(sorted(read_flags - KNOWN_CLI_FLAGS))


def reject_unknown_flags(argv):
    """Fail LOUDLY on a flag this copy does not understand (OI-181).

    WHY THIS EXISTS. `_arg` is a positional `argv.index()` scan, not argparse,
    so an unrecognised flag is silently ignored. That is harmless for a typo but
    not here: on 2026-08-16 a worktree copy predating `--notes-file` was handed
    `--notes-file <path>`, ignored it, and recorded an APPROVED review artifact
    with `notes: ""` -- exit 0, no warning. `notes` is not part of the artifact
    key, so the gate still PASSED and the commit landed. The audit trail for a
    blast-radius change vanished at exactly the moment it was being created.

    Version skew is the norm, not the exception, because config-write-guard
    explicitly routes callers to a WORKTREE copy of this tool (the live path is
    blocked as a governance write). Any worktree branched before a flag was
    added will silently discard it. Rejecting unknown flags converts that whole
    class -- every future flag, not just --notes-file -- into a loud failure.

    Scope is deliberately the CLI path only. `main()` (the hook path) never
    reads argv, and since 2026-08-16 this module is imported and run IN-PROCESS
    by pretooluse-dispatcher.py, where `sys.argv` belongs to the DISPATCHER
    (e.g. `--chain bash`). Validating there would block every Bash call."""
    unknown, i = [], 0
    while i < len(argv):
        tok = argv[i]
        if tok in _VALUE_FLAGS:
            i += 2  # skip the VALUE, which may legitimately begin with "--"
            continue
        if tok in _BOOL_FLAGS:
            i += 1
            continue
        if tok.startswith("--"):
            unknown.append(tok)
        i += 1
    if unknown:
        raise SystemExit(
            "eos-review-gate: unrecognised flag(s): %s\n"
            "This copy of the tool accepts: %s\n"
            "Refusing to record rather than silently discarding them -- that is "
            "how a review artifact ends up with empty notes (OI-181).\n"
            "MOST LIKELY CAUSE: this copy is STALE. config-write-guard routes "
            "you to a worktree copy, and a worktree branched before the flag "
            "was added does not have it. Check the live copy at "
            "~/.claude/hooks/eos-review-gate.py, or rebase this worktree."
            % (", ".join(unknown), " ".join(sorted(KNOWN_CLI_FLAGS))))


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
    """(root, session_id, rels, digest_fn) for the --key/--record CLI.

    CMD-SCOPING (2026-07-26 fix): if `--cmd "<git commit ...>"` is given, rels
    and digest_fn come from scope_for_cmd -- the exact same computation main()
    will use to gate THAT invocation, so the resulting key is guaranteed to
    validate against it. Without --cmd, falls back to the original behaviour
    (_worktree_risk_rels: every at-risk path anywhere in the working tree,
    plain working-tree-byte digest) -- still correct for an operator who has
    not yet decided their exact commit invocation, or intends a plain
    `git commit` covering everything currently staged."""
    repo = _arg(argv, "--repo") or os.getcwd()
    root = repo_root("", repo)
    if not root:
        sys.stderr.write("eos-review-gate: not a git repo: %s\n" % repo)
        return None, None, None, None
    session_id = (_arg(argv, "--session")
                  or os.environ.get("CLAUDE_CODE_SESSION_ID") or "")
    if not override_tokens.SESSION_ID_RE.match(session_id):
        sys.stderr.write(
            "eos-review-gate: no usable session id (set CLAUDE_CODE_SESSION_ID "
            "or pass --session); a review artifact cannot be addressed.\n")
        return None, None, None, None
    cmd = _arg(argv, "--cmd")
    if cmd:
        rels, digest_fn = scope_for_cmd(root, cmd)
    else:
        rels = _worktree_risk_rels(root)
        digest_fn = None
    return root, session_id, rels, digest_fn


def cli_key(argv):
    root, session_id, rels, digest_fn = _cli_context(argv)
    if root is None:
        return 1
    sys.stdout.write(json.dumps({
        "repo": root.replace("\\", "/"),
        "paths": rels,
        "reasons": {r: risk_reason(r) for r in rels},
        "key": review_key(root, rels, digest_fn) if rels else "",
    }, indent=2))
    return 0


def cli_record(argv):
    root, session_id, rels, digest_fn = _cli_context(argv)
    if root is None:
        return 1
    if not rels:
        sys.stderr.write(
            "eos-review-gate: nothing at risk in the working tree -- there is no "
            "blast-radius diff to review, so no artifact is needed or written.\n")
        return 1
    model = _bare_model(_arg(argv, "--model"))
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
    key = review_key(root, rels, digest_fn)
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
        "notes": _resolve_notes(argv),
        "ts": int(time.time()),
        "tool_version": __version__,
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

    # Origin-aware, cmd-scoped rels + digest (see module docstring's PROVENANCE
    # FIX / M1, and scope_for_cmd's own docstring for the 2026-07-26 CLI-parity
    # fix): the key must reflect whatever bytes THIS specific commit invocation
    # actually lands per path -- index for a plainly-staged path, working tree
    # for one sourced via -a/pending-add/explicit pathspec -- and nothing else.
    rels, digest_fn = scope_for_cmd(repo, cmd)
    if not rels:
        return  # nothing blast-radius in this commit -> allow silently

    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""

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
                            artifact_state_note(session_id, key),
                            message_shape_hint(cmd))
    if mode == "warn":
        sys.stderr.write("WARNING (eos-review-gate, warn mode -- not blocking): "
                         + message + "\n")
        return
    sys.stderr.write("BLOCKED (eos-review-gate): " + message + "\n")
    sys.exit(2)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--key" in argv or "--record" in argv:
        # OI-181: reject flags this copy does not understand BEFORE doing any
        # work. Silently ignoring one is how an approved review artifact ends up
        # with empty notes. CLI path only -- main() never reads argv, and the
        # dispatcher runs this module in-process under ITS own sys.argv.
        _missing = _flagset_is_consistent()
        if _missing:
            sys.stderr.write(
                "eos-review-gate: WARNING -- KNOWN_CLI_FLAGS is out of date; "
                "_arg() reads %s but the set does not list them. Add them, or "
                "valid invocations will be rejected.\n" % ", ".join(_missing))
        reject_unknown_flags(argv)
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
