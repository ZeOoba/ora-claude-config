#!/usr/bin/env python3
"""preflight-shared-checkout.py -- read-only SINGLE-WRITER gate: "is it safe
for ME to start editing these paths, in this shared checkout, right now?"

WHY (found 2026-09-10, by scanning the last 20 sessions' Bash usage): CLAUDE.md
and the session-context block both mandate a preflight before touching a shared
checkout (~/.claude, ora-skills, website-canonical, oxford-command-center) --
"run `git log --oneline -1` + `git status`; if HEAD is newer than session-start
or uncommitted changes are not yours, STOP". That trio was typed by hand 181
times across 13 of the last 20 sessions, never twice the same way. Three
problems, all structural rather than anybody's carelessness:

  * The "is HEAD newer than session-start?" half was compared BY EYE against a
    sha nobody had written down. An eyeballed gate is not a gate.
  * `git status` in ~/.claude routinely returns 70-100 dirty files belonging to
    a dozen other sessions. Scanning that by hand for the two that overlap MY
    paths is exactly the reading task a person skips at 4pm.
  * The claims side (hooks/lib/claim_work.py) was a SEPARATE command that the
    hand-typed versions usually just left out, so a live claim on the very
    paths being edited went unseen.

This composes the three into one verdict with one exit code. It is the
pre-EDIT gate; the existing tools answer neighbouring questions and are
deliberately not duplicated here:

  * dirty-file-owner-report.py -- "whose WIP is this dirty file?" (attribution,
    after the fact, whole-repo).
  * cross-repo-wip-scan.py     -- "how long has the backlog been aging?"
                                  (periodic, whole-repo, unattended).
  * checkout-merge-forward.py  -- "fix the branch drift" (a corrector).
  * verify-push.py             -- "did the push actually land?" (post-push).

DESIGN STANCES carried over from those tools, each earned by a past failure:

  1. Every distinguishable finding gets its OWN exit code. A moved HEAD, an
     overlapping dirty file and a competing claim have different remedies;
     collapsing them into one generic "STOP" is how a session talks itself past
     the one that mattered.
  2. Not-requested is NOT unmeasurable. Omitting --since means the caller
     declined the HEAD check -- reported, still CLEAR. A claims directory we
     TRIED and failed to read is INDETERMINATE, and never green.
  3. Overlap is decided on PATH SEGMENTS, not string prefixes, in BOTH
     directions: a claim on `agents/` covers a request for `agents/foo.md`, and
     `agents/` never contests `agents-archive/`.
  4. The verdict survives a pipe. Piping a gate into `tail` masks its exit code
     -- the defect behind a past false "push succeeded" claim (memory:
     feedback_piped_gate_exit_masking) -- so a RESULT_JSON= line is printed on
     every outcome.
  5. READ-ONLY. It runs `rev-parse` and `status` and reads claim JSON. It never
     claims, commits, stashes, checks out or resets. It reports; you decide.

STALE OWNERS (added 2026-09-12): a recorded touch older than the path's last
commit is reported as STALE, not silently counted as a live owner. That ended
the false STOP from July-era touches on long-committed files, which looked
identical to a live conflict and cost an investigation each time. A file
whose only other owners are stale is still CONTESTED, labelled STALE-ONLY with
the exact remedy. A partial commit (isolated_commit.py lands one hunk, leaves
the rest) post-dates the touch while foreign hunks stay dirty, so nothing but
the caller's own `git diff HEAD -- <path>` can clear it: `--accept-stale PATH`.
The real fix (per-touch blob hashes in commit-provenance-recorder.py, so a
stale verdict can be proven) touches hooks/** and is tracked separately.

ACCEPTED LIMITATION: "mine" means mine among RECORDED touches. Provenance is
written by the Edit/Write tool hook, so another session's edit made through
Bash (sed, a redirect, a script) never appears, and a file I once touched can
read as mine alone. The same applies to two spelling cases provenance cannot
reconcile: a foreign touch recorded through a FILE symlink (different
basename, and creating one needs a privilege sessions do not hold), and one
recorded under a directory that was later renamed or removed. Junction and
8.3 directory/file spellings ARE reconciled (see _owners). Same
precision-over-recall tradeoff as
commit-provenance-guard.py; the claims check and HEAD check are the backstops.

LOCAL-ONLY ADVISORY (added 2026-09-12): when the checkout is NOT on its
canonical branch, report which scope paths are committed on this branch but
absent from `origin/<canonical>` (falling back to local `<canonical>`), plus how
many commits are unpushed to the upstream. Found when a CLEAR preflight let a
session edit the OI-249 merge-forward scripts assuming they would ship with
main -- they existed only on the checkout's never-pushed feature branch.
Advisory only: it never changes the exit code (the contract below is
test-pinned), and an unresolvable canonical ref is reported as "could not
check" with local_only_paths=null, never as an empty (clean) list. No fetch --
a stale origin ref can under-report, same limitation as cross-repo-wip-scan.

PATH CONTAINMENT (added 2026-09-12): every --paths entry must belong to the
--repo checkout, decided on its realpath AND on git's own answer for which
toplevel owns it. Reproduced in the PR #196 review: from ~/.claude, a file
dirty in ora-skills was CONTESTED with --repo ~/ora-skills but CLEAR with
--repo ~/.claude, because a path in another checkout is simply absent from
this one's dirty set. The git-owner half also catches a nested checkout
(~/.claude/.claude/worktrees/<name> is string-inside ~/.claude). A path whose
owner cannot be established counts as outside: a path that was never
evaluated is never CLEAR. Repository-selecting env (GIT_DIR, GIT_WORK_TREE,
...) is scrubbed from every git call, and Win32 verbatim-prefix spellings
are normalized.
Repositories selected only through those env vars (a bare "dotfiles" repo)
are therefore unsupported and read NOT_A_REPO -- closed, not open.
A DIRECTORY scope that CONTAINS a linked worktree of this repo is checked
too: each is listed in nested_checkouts_excluded with its dirty_count; a
dirty (or unreadable) one is CONTESTED, since its work never appears in this
checkout's status and a sweep over the parent would take it; a clean one is
only counted. That includes the CALLER's own dirty worktree -- nested
entries have no per-file attribution, so --accept-stale cannot clear one;
narrow the scope instead. If the worktree list itself fails under a directory scope, the
verdict is INDETERMINATE. Not enumerated (unbounded walk): independent clones,
and worktrees of OTHER repos, inside ignored directories under the scope --
name a path inside one and it IS caught (exit 5).

MOVED OUT OF SCOPE (added 2026-09-13): HEAD moving since --since is a STOP
only when a moved commit touches the scope. The "re-read what you are about to
edit" remedy has nothing to re-read when every moved commit is elsewhere, and
in ~/.claude, where a dozen sessions commit an hour, the blanket STOP held up a
one-file cherry-pick over an unrelated docs commit. The move is still reported
(head_moved true, a WARNING line) and only ever clears to the NEXT finding in
precedence, never past CONTESTED. The in-scope set is a
`git diff --name-only --no-renames <since> HEAD` over :(literal,icase)
pathspecs, so a
rename that carries a scope file away still counts, and a scope spelled in a
different case still matches. head_moved_in_scope is that list, [] when
measured clean, and null when unmeasurable: --since does not resolve, is not an
ancestor of HEAD (reset, rebase, branch switch: the diff would not describe
what happened to the checkout), or git fails. null keeps HEAD_MOVED.
The WARNING line names the moved range as <since>..<head>. Pathspecs are
:(literal,icase), matching _last_commit_time. BY DESIGN the diff compares end
states only: churn inside the range that nets out -- a scope file changed and
reverted, a merge into scope later reverted, a file created and deleted within
since..HEAD -- reads as nothing-in-scope (CLEAR), because the scope content at
HEAD equals the content at --since and there is nothing new to re-read.

STALE UNTRACKED KNOWN BLOB (added 2026-09-13): observed live the same day,
scheduled-tasks/ora-ground-truth-auditor/SKILL.md returned CONTESTED because an
UNTRACKED copy sat in the tree with "[no live recorded owner]" -- yet its
`git hash-object` was byte-identical to a blob already committed at that same
path. Nothing in such a file is unsaved work. An in-scope foreign dirty entry
is classified STALE_UNTRACKED_KNOWN_BLOB only when ALL hold: it is untracked
(`??`, never a modified tracked file -- a tracked file reverted to an older
blob is still a modification of HEAD); it has no live recorded owner and no
recorded touch by ANY session inside the --ttl-minutes window (default 2h; an
unknown or non-numeric touch time counts as inside), and provenance was read
COMPLETELY -- a missing sessions dir (provenance_available false) or any
session touched-files.txt that exists but cannot be read (counted in the new
RESULT_JSON key provenance_partial) disables the classification entirely, since
an empty owner map is then not evidence of no touch (review #208); no other
session's live claim overlaps it; and its blob appears, as either side of a change, in
`git log --exclude=refs/stash --all --no-renames --raw -n 200 -- :(literal)<path>`
(same path only; a stash is live WIP, not history).
At most 50 such files are hashed per run; the rest stay CONTESTED. Each is
listed in the RESULT_JSON key stale_untracked_known_blob ({path, blob,
commits}) and ALSO stays in dirty_overlap_foreign (with known_blob /
known_blob_commits added), so a consumer reading only the old keys still
sees dirt. The verdict is STALE_UNTRACKED_KNOWN_BLOB with exit 0 and a WARNING
ONLY when every contesting item is of that kind; any other foreign dirt, a
dirty nested worktree, or a competing claim keeps CONTESTED (exit 1), and it
never outranks HEAD_MOVED or INDETERMINATE.

Usage:
    python maintenance/preflight-shared-checkout.py --paths P [P ...]
        [--repo PATH]        checkout to inspect (default: cwd)
        [--since SHA]        session-start sha; full or short. Omit to skip
                             the HEAD check (it is then reported "not checked")
        [--session ID]       my session id (default: $CLAUDE_CODE_SESSION_ID)
        [--claims-dir DIR]   default: <repo>/hooks/active-work, else
                             ~/.claude/hooks/active-work
        [--ttl-minutes N]    claim TTL, default 120 (matches claim_work.py)
        [--canonical BRANCH] branch the checkout should track, default main
                             (local-only advisory only)
        [--json]             machine-readable only, nothing else on stdout

    --paths accepts files or directories, absolute or relative to --repo, and
    all of them must be inside that one checkout (else exit 5).

Exit codes:
    0  CLEAR          nothing contests these paths -- go ahead
    0  STALE_UNTRACKED_KNOWN_BLOB
                      go ahead WITH CARE: the only contesting items are
                      untracked copies of blobs already committed at those
                      paths (see STALE UNTRACKED KNOWN BLOB); a WARNING names
                      the matching commit(s)
    1  CONTESTED      an overlapping dirty file, or another session's live claim
    2  NOT_A_REPO     --repo is not a git checkout, or git is unavailable
    3  HEAD_MOVED     --since given, HEAD is not that commit, and the move
                      touched the scope -- or that could not be established
                      (see MOVED OUT OF SCOPE)
    4  INDETERMINATE  a fact could not be established (claims unreadable) --
                      uncertain, never treated as clean
    5  OUT_OF_REPO    a --paths entry is not in the --repo checkout, so it was
                      never evaluated (out_of_repo_paths names each one and the
                      checkout that owns it)

Precedence when several apply: NOT_A_REPO > OUT_OF_REPO > HEAD_MOVED >
CONTESTED > INDETERMINATE > STALE_UNTRACKED_KNOWN_BLOB > CLEAR. A HEAD move
that touched no scope path sets nothing and falls through. All findings are reported regardless of
which one sets the exit code. OUT_OF_REPO outranks the rest because --since and
the dirty set then describe the wrong checkout.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

EXIT_CLEAR = 0
EXIT_CONTESTED = 1
EXIT_NOT_A_REPO = 2
EXIT_HEAD_MOVED = 3
EXIT_INDETERMINATE = 4
EXIT_OUT_OF_REPO = 5

DEFAULT_TTL_MINUTES = 120  # matches claim_work.py's 2h window


# --------------------------------------------------------------------------
# path overlap -- segment-wise, both directions
# --------------------------------------------------------------------------
def _unverbatim(p):
    """Drop a Win32 verbatim prefix. realpath keeps `\\\\?\\C:\\...` as-is, and
    git never prints one, so an in-repo path spelled that way compared
    unequal to its own toplevel (review finding, 2026-09-12)."""
    if p.startswith("\\\\?\\UNC\\"):
        return "\\\\" + p[8:]
    if p.startswith("\\\\?\\"):
        return p[4:]
    return p


def _real(p):
    return os.path.realpath(_unverbatim(os.path.abspath(p)))


def _norm(p):
    """Absolute, case-folded, forward-slashed, no trailing separator.

    Case-folding is correct on Windows (the only host this runs on) and is also
    what claim_work.py already writes into its `paths`, so the two agree.
    """
    # realpath: a junction or an 8.3 short name (C:\Users\OWNER~1\...) is a
    # different spelling of the same directory. git reports the long real
    # path, so comparing spellings as strings made every overlap miss.
    p = _unverbatim(_real(p)).replace("\\", "/").rstrip("/")
    return p.lower()


def _overlaps(a, b):
    """True when a and b name the same path, or one CONTAINS the other.

    Segment-wise on purpose: `.../agents` must not match `.../agents-archive`,
    which a bare startswith() would.
    """
    a, b = _norm(a), _norm(b)
    if a == b:
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def _any_overlap(path, scope):
    return any(_overlaps(path, s) for s in scope)


def _inside(path, root):
    """Segment-wise: `root` itself or anything under it, never `root2/`."""
    p, r = _norm(path), _norm(root)
    return p == r or p.startswith(r + "/")


# --------------------------------------------------------------------------
# git facts
# --------------------------------------------------------------------------
_GIT_REPO_ENV = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_PREFIX", "GIT_OBJECT_DIRECTORY", "GIT_CEILING_DIRECTORIES",
                 "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_NAMESPACE"}


def _git(repo, *args, **kw):
    """Never raises: a missing git binary or a timeout comes back as a failed
    call (rc 127), so NOT_A_REPO / the advisory's error paths handle it instead
    of a traceback exiting 1 -- which reads as CONTESTED and prints no
    RESULT_JSON. --no-optional-locks keeps `git status` from taking index.lock
    under a concurrent session's add/commit (this tool must stay read-only).
    Repository-selecting variables are scrubbed: an inherited GIT_DIR /
    GIT_WORK_TREE (a git hook, a wrapper) outranks -C, and pointed every fact
    -- toplevel, status, owner -- at whatever checkout the caller came from."""
    env = {k: v for k, v in os.environ.items() if k.upper() not in _GIT_REPO_ENV}
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", repo] + list(args),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=kw.get("timeout", 30), env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(["git"] + list(args), 127, "", str(exc))


def _head_sha(repo):
    proc = _git(repo, "rev-parse", "HEAD")
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _moved_in_scope(repo, since, scope):
    """Scope paths changed between --since and HEAD: repo-relative, forward-slash,
    sorted. [] means measured and nothing in scope moved; None means it could not
    be established, and None must keep HEAD_MOVED (see MOVED OUT OF SCOPE)."""
    if not scope:
        return None
    base = _git(repo, "rev-parse", "--verify", "--quiet", since + "^{commit}")
    if base.returncode != 0 or not base.stdout.strip():
        return None
    base_sha = base.stdout.strip()
    if _git(repo, "merge-base", "--is-ancestor", base_sha, "HEAD").returncode != 0:
        return None
    # :(literal,icase), the same magic _last_commit_time uses. literal: a scope
    # entry is a path, not a pattern -- without it `agents/[draft].md` is also
    # a glob that matches `agents/d.md`, so the in-scope list would name files
    # the caller never scoped. icase: git can record a path in a different case
    # than the file on disk (and than the caller's --paths, which _real()
    # canonicalizes to disk case); NTFS treats them as one file, so must we.
    # Directory entries and "." still match everything beneath them.
    specs = [":(literal,icase)" + os.path.relpath(p, repo).replace("\\", "/") for p in scope]
    diff = _git(repo, "-c", "core.quotepath=off", "diff", "--name-only",
                "--no-renames", "-z", base_sha, "HEAD", "--", *specs)
    if diff.returncode != 0:
        return None
    return sorted(p for p in diff.stdout.split("\0") if p)


def _own_toplevel(path):
    """realpath of the git toplevel that owns `path`, or None when it sits in
    no work tree (or git cannot say). A path that does not exist yet -- a file
    about to be created, in a directory about to be created -- is answered by
    its nearest existing ancestor directory."""
    d = path
    while not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    proc = _git(d, "rev-parse", "--show-toplevel")
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return _real(proc.stdout.strip())


def _outside_repo(scope, repo):
    """Scope entries this checkout cannot speak for. Each carries
    `suggested_repo` (the checkout that owns it, None when unknown) and
    `reason`: other_checkout | no_checkout (git named no owner: not in a work
    tree, inside .git/, or git failed) | unrecognised_spelling (git says
    --repo owns it but the spelling does not resolve under it).

    Two conditions, both required to count as inside: the realpath sits under
    the toplevel, AND git names that same toplevel as the path's owner. The
    second catches a path inside a nested checkout --
    ~/.claude/.claude/worktrees/<name> is string-inside ~/.claude, but
    ~/.claude's `git status` never lists its dirt, so evaluating it there is
    the same wrong-repo false CLEAR. Failing to establish the owner is
    outside, never inside."""
    out = []
    for p in scope:
        own = _own_toplevel(p)
        same_owner = own is not None and _norm(own) == _norm(repo)
        if _inside(p, repo) and same_owner:
            continue
        if same_owner:
            # Never hint "re-run with --repo X" when X is what was passed.
            out.append({"path": p, "suggested_repo": None, "reason": "unrecognised_spelling"})
        else:
            out.append({"path": p, "suggested_repo": own,
                        "reason": "other_checkout" if own else "no_checkout"})
    return out


def _nested_checkouts(repo, scope):
    """Linked worktrees of this repo that sit UNDER a directory scope entry.
    Their dirt never appears in this checkout's `git status` (review finding,
    2026-09-12: `--paths .` in a repo holding .claude/worktrees read CLEAR
    while those worktrees held uncommitted work). main() status-checks each
    one: dirty contests, clean is only counted. Returns None when git cannot
    list worktrees (unmeasured, not empty). Independent clones and other
    repos' worktrees are not enumerated -- see PATH CONTAINMENT."""
    proc = _git(repo, "worktree", "list", "--porcelain")
    if proc.returncode != 0:
        return None
    found = []
    for line in proc.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        wt = _real(line[len("worktree "):].strip())
        if _norm(wt) == _norm(repo) or not os.path.isdir(wt):
            continue
        under = [s for s in scope if _inside(wt, s) and _norm(wt) != _norm(s)]
        if under:
            found.append({"path": wt, "under_scope":
                          [os.path.relpath(s, repo).replace("\\", "/") for s in under]})
    return found


def _dirty_paths(repo, untracked=None):
    """Absolute paths of everything `git status --porcelain` reports. When a
    set is passed as `untracked`, the '??' entries are also added to it.

    Includes untracked files -- a stranger's brand-new file in my scope is
    exactly as much of a co-mingling hazard as a modified one. For a rename
    ("R  old -> new") both sides are returned: either may be in my scope.

    NUL-delimited (-z) on purpose: plain porcelain C-quotes non-ASCII names
    ("agents/caf\\303\\251.md"), and a quote-strip left the octal escapes in
    place, so such a file never matched its scope and the gate read CLEAR.
    Under -z paths are verbatim, and a rename entry is followed by its
    source path as a separate NUL field.
    """
    proc = _git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    if proc.returncode != 0:
        return None
    out = []
    fields = proc.stdout.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        paths = [path]
        if "R" in code or "C" in code:
            if i < len(fields) and fields[i]:
                paths.append(fields[i])
            i += 1
        for part in paths:
            full = os.path.join(repo, part.replace("/", os.sep))
            out.append(full)
            if untracked is not None and code == "??":
                untracked.add(full)
    return out


KNOWN_BLOB_MAX_CANDIDATES = 50   # untracked in-scope files hashed per run
KNOWN_BLOB_MAX_COMMITS = 200     # history entries scanned per path


def _known_blob(repo, rel):
    """(blob, [commit, ...]) when the working copy of untracked `rel` hashes to
    a blob recorded AT THAT PATH in `git log --all` history (as either side of
    a change, so a later deletion commit counts too), else None. Bounded to
    KNOWN_BLOB_MAX_COMMITS entries; any git failure is None (stays CONTESTED)."""
    ho = _git(repo, "hash-object", "--", rel)
    blob = (ho.stdout or "").strip().lower()
    if ho.returncode != 0 or not blob:
        return None
    # refs/stash excluded: a `stash -u` holds live WIP, not committed history.
    lg = _git(repo, "-c", "core.quotepath=off", "log", "--exclude=refs/stash", "--all",
              "--no-renames",
              "--raw", "--no-abbrev", "--format=%H", "-n", str(KNOWN_BLOB_MAX_COMMITS),
              "--", ":(literal)" + rel)
    if lg.returncode != 0:
        return None
    commits, current = [], None
    for line in lg.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            current = line
            continue
        meta = line.split("\t", 1)[0].split()
        # ":<mode> <mode> <old> <new> <status>"
        if current and len(meta) >= 4 and blob in (meta[2].lower(), meta[3].lower()):
            if current not in commits:
                commits.append(current)
    return (blob, commits) if commits else None


def _local_only(repo, scope, canonical):
    """Advisory branch-identity facts. Returns a dict:
    current_branch, off_canonical, canonical_ref, canonical_ref_error,
    local_only_paths (None when unmeasurable), unpushed_commits (None when
    there is no upstream)."""
    info = {"current_branch": None, "off_canonical": None, "canonical_ref": None,
            "canonical_ref_error": None, "local_only_paths": None,
            "unpushed_commits": None}
    proc = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode != 0:
        info["canonical_ref_error"] = "cannot resolve current branch"
        return info
    current = proc.stdout.strip()
    info["current_branch"] = current
    info["off_canonical"] = current != canonical

    proc = _git(repo, "rev-list", "--count", "@{u}..HEAD")
    if proc.returncode == 0 and proc.stdout.strip().isdigit():
        info["unpushed_commits"] = int(proc.stdout.strip())

    if not info["off_canonical"]:
        info["local_only_paths"] = []
        return info

    for ref in ("origin/%s" % canonical, canonical):
        if _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0:
            info["canonical_ref"] = ref
            break
    else:
        info["canonical_ref_error"] = ("neither origin/%s nor %s resolves locally"
                                       % (canonical, canonical))
        return info

    rels = []
    for p in scope:
        if not _norm(p).startswith(_norm(repo) + "/") and _norm(p) != _norm(repo):
            continue  # outside this checkout
        rel = os.path.relpath(p, repo).replace("\\", "/")
        rels.append("" if rel == "." else rel)
    if not rels:
        info["local_only_paths"] = []
        return info

    def _tree_files(ref):
        proc = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", *[r or "." for r in rels])
        return None if proc.returncode != 0 else set(proc.stdout.splitlines())

    here = _tree_files("HEAD")
    there = _tree_files(info["canonical_ref"])
    if here is None or there is None:
        info["canonical_ref_error"] = "git ls-tree failed"
        return info
    info["local_only_paths"] = sorted(here - there)
    return info


# --------------------------------------------------------------------------
# claims -- read the on-disk JSON contract directly
# --------------------------------------------------------------------------
def _default_sessions_dir():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        os.pardir, "hooks", "lib"))
        from commit_provenance import sessions_dir  # noqa: E402
        return sessions_dir()
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".claude", "hooks",
                            "sessions")


def _scan_provenance(sessions_dir):
    """(index, skipped). index is {normcase(path): {session_id:
    last_touch_epoch | None}} from every session's touched-files.txt, or None
    when the directory itself cannot be listed. None == old-format line with
    no timestamp (unknown touch time). skipped counts session touched-files.txt
    entries that EXIST but could not be read (not a regular file, or OSError):
    their touches are unknown, so the index is partial (review #208) --
    reported as provenance_partial, and it disables known-blob classification.

    Same source commit-provenance-recorder.py writes and
    dirty-file-owner-report.py reads -- deliberately not a second tracking
    mechanism. Read directly (one tab-separated line per touch) rather than
    importing read_touched(), so a mid-write hooks/lib does not take the
    preflight down with it.
    """
    if not os.path.isdir(sessions_dir):
        return None, 0
    index, skipped = {}, 0
    try:
        names = os.listdir(sessions_dir)
    except OSError:
        return None, 0
    # Keys are stored raw, as the Edit hook saw them (possibly a junction or
    # 8.3 spelling); _owners() reconciles spellings at lookup time.
    for sid in names:
        tf = os.path.join(sessions_dir, sid, "touched-files.txt")
        if not os.path.isfile(tf):
            if os.path.lexists(tf):
                skipped += 1  # present but not a readable regular file
            continue
        try:
            with open(tf, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parts = line.rstrip("\r\n").split("\t", 1)
                    path = parts[0].strip()
                    if not path:
                        continue
                    try:
                        ts = float(parts[1]) if len(parts) > 1 and parts[1].strip() else None
                    except ValueError:
                        ts = None
                    _merge_touch(index.setdefault(os.path.normcase(path), {}), sid, ts)
        except OSError:
            # one unreadable session is not a reason to fail the scan, but it
            # is a reason not to treat the scan as complete
            skipped += 1
            continue
    return index, skipped


def _merge_touch(owners, sid, ts):
    """Keep each session's LATEST touch. An unknown (None) time wins: it can
    never be proven older than a commit, so it must never be discounted."""
    if sid in owners and (owners[sid] is None or ts is None):
        owners[sid] = None
    else:
        owners[sid] = ts if sid not in owners else max(owners[sid], ts)


def _merge_owners(into, other):
    for sid, ts in other.items():
        _merge_touch(into, sid, ts)


def _owners(path, prov_index):
    """{session_id: last_touch_epoch | None} known to have touched `path`.
    Empty == nobody recorded it, which is NOT the same as 'nobody touched
    it'."""
    if prov_index is None:
        return {}
    # A foreign touch recorded under a junction/8.3 spelling never equals the
    # realpath key, so the file read as mine alone (CLEAR). Match every
    # recorded key with the same basename by resolving ITS directory. Only a
    # handful of dirty-in-scope files are looked up, so resolving at lookup
    # time is cheap, where resolving all ~20k recorded lines at index time
    # took minutes.
    target = os.path.normcase(os.path.realpath(path))
    base = os.path.basename(target)
    owners = {}
    _merge_owners(owners, prov_index.get(target, {}))
    for key, sids in prov_index.items():
        if key == target:
            continue
        kbase = os.path.basename(key)
        if kbase != base:
            # An 8.3 FILE name (AVERYV~1.TXT) never shares the basename;
            # resolve the whole key, but only for '~' names that still exist.
            if "~" in kbase and os.path.exists(key):
                try:
                    if os.path.normcase(os.path.realpath(key)) == target:
                        _merge_owners(owners, sids)
                except (OSError, ValueError):
                    pass
            continue
        d = os.path.dirname(key)
        if d not in _DIR_REAL:
            # A directory that no longer exists cannot be another spelling of
            # a live file's directory, and realpath on it is the slow case.
            try:
                _DIR_REAL[d] = (os.path.normcase(os.path.realpath(d))
                                if os.path.isdir(d) else None)
            except (OSError, ValueError):
                _DIR_REAL[d] = None
        if _DIR_REAL[d] and os.path.join(_DIR_REAL[d], base) == target:
            _merge_owners(owners, sids)
    return owners


def _stale_note(entry):
    """Human-readable tail naming stale owners, so a discount is visible
    rather than silent -- and, for a stale-only file, the exact remedy."""
    stale = entry.get("stale_owners") or []
    if not stale:
        return ""
    names = ", ".join(s[:8] for s in stale)
    if entry.get("stale_only"):
        return ("  STALE-ONLY other owner(s) %s: their touch predates the last commit,"
                " but a partial commit can leave their hunks dirty. Check"
                " `git diff HEAD -- %s` holds only your hunks, then re-run with"
                " --accept-stale %s" % (names, entry["path"], entry["path"]))
    if entry.get("stale_accepted"):
        return "  (stale owner(s) %s accepted via --accept-stale)" % names
    return "  (+%d stale, committed since their touch: %s)" % (len(stale), names)


def _known_note(entry):
    """Tail for an untracked foreign file whose bytes are already committed."""
    commits = entry.get("known_blob_commits")
    if not commits:
        return ""
    shown = ", ".join(c[:12] for c in commits[:3])
    more = " +%d more" % (len(commits) - 3) if len(commits) > 3 else ""
    return ("  WARNING: STALE_UNTRACKED_KNOWN_BLOB -- untracked, byte-identical to"
            " blob %s committed at this path in %s%s" % (entry["known_blob"][:12], shown, more))


def _last_commit_time(repo, rel):
    """Epoch of the newest commit touching `rel`, or None (never committed, or
    git could not answer). `:(literal,icase)` for the same reason as
    commit-provenance-guard.py last_commit_time(): provenance keys are
    lowercased, and a plain pathspec silently misses any path with uppercase."""
    proc = _git(repo, "log", "-1", "--format=%ct", "--", ":(literal,icase)" + rel)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        return None
    try:
        return float(out.splitlines()[0])
    except ValueError:
        return None


def _split_stale(owners, commit_ts):
    """(live, stale) session-id sets. A touch is STALE when its time is KNOWN
    and the path's last commit is at or after it -- the file was committed
    after that session touched it. That does NOT prove all of its content is
    in git: a partial commit can land one hunk and leave the rest dirty, so
    the caller never auto-clears on stale alone (see --accept-stale). Same
    timestamp rule as commit-provenance-guard.py already_committed_since().
    Unknown touch time, or a never-committed path, stays live."""
    if commit_ts is None:
        return set(owners), set()
    stale = {sid for sid, ts in owners.items() if ts is not None and commit_ts >= ts}
    return set(owners) - stale, stale


_DIR_REAL = {}  # per-run cache for _owners(): recorded dir -> normcase(realpath) | None


def _default_claims_dir(repo):
    # Same override claim_work.py honors -- otherwise the two can read
    # different directories and a live claim goes unseen.
    env = os.environ.get("ORA_ACTIVE_WORK_DIR")
    if env:
        return env
    local = os.path.join(repo, "hooks", "active-work")
    if os.path.isdir(local):
        return local
    return os.path.join(os.path.expanduser("~"), ".claude", "hooks",
                        "active-work")


def _read_claims(claims_dir, ttl_minutes):
    """Returns (claims, unreadable). Never raises on a bad file -- a claim we
    cannot parse is an UNKNOWN we must surface, not one we may skip.

    Reads the JSON files directly rather than importing claim_work.py: that
    module is itself frequently under concurrent edit in this checkout, and a
    preflight must not fail because the thing it inspects is mid-write.
    """
    claims, unreadable = [], []
    if not os.path.isdir(claims_dir):
        return None, [claims_dir]
    cutoff = datetime.now() - timedelta(minutes=ttl_minutes)
    try:
        names = sorted(os.listdir(claims_dir))
    except OSError as exc:
        return None, ["%s (%s)" % (claims_dir, exc)]
    for name in names:
        if not name.endswith(".json"):
            continue
        full = os.path.join(claims_dir, name)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError) as exc:
            unreadable.append("%s (%s)" % (name, exc))
            continue
        if not isinstance(rec, dict):
            unreadable.append("%s (not a JSON object)" % name)
            continue
        raw = rec.get("claimed_at") or ""
        try:
            when = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            unreadable.append("%s (unparseable claimed_at %r)" % (name, raw))
            continue
        claims.append({
            "slug": rec.get("title") or name[:-5],
            "session_id": rec.get("session_id") or "",
            "description": rec.get("description") or "",
            "claimed_at": when.strftime("%Y-%m-%dT%H:%M:%S"),
            "expired": when < cutoff,
            "paths": [p for p in (rec.get("paths") or []) if isinstance(p, str)],
        })
    return claims, unreadable


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Single-writer preflight for a shared git checkout.")
    ap.add_argument("--paths", nargs="+", required=True,
                    help="files/dirs you are about to edit (abs or rel to --repo)")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--since", default=None,
                    help="session-start sha; omit to skip the HEAD check")
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    ap.add_argument("--claims-dir", default=None)
    ap.add_argument("--sessions-dir", default=None,
                    help="commit-provenance sessions dir (attribution)")
    ap.add_argument("--ttl-minutes", type=int, default=DEFAULT_TTL_MINUTES)
    ap.add_argument("--accept-stale", nargs="+", default=None, metavar="PATH",
                    help="after checking `git diff HEAD -- PATH` holds only your "
                         "own hunks, accept a file whose only other owners are stale")
    ap.add_argument("--canonical", default="main",
                    help="branch this checkout should track (local-only advisory)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = _unverbatim(os.path.abspath(args.repo))
    out = []          # human-readable lines, suppressed under --json
    def say(line=""):
        out.append(line)

    # --- fact 0: is this even a checkout? -------------------------------
    head = _head_sha(repo) if os.path.isdir(repo) else None
    if head is None:
        report = {"verdict": "NOT_A_REPO", "repo": repo,
                  "detail": "not a git checkout, or git unavailable"}
        _emit(report, ["NOT A GIT CHECKOUT: %s" % repo], args.json)
        return EXIT_NOT_A_REPO

    # Relative --paths resolve against the directory the caller named, but
    # every git-reported path is relative to the TOPLEVEL. Joining porcelain
    # output onto a subdirectory --repo (the cwd default when run from
    # maintenance/) matched nothing and read CLEAR -- so after scope is
    # resolved, `repo` becomes the toplevel for every other fact.
    # Both scope and repo go through realpath so every later relpath/overlap
    # compares one spelling (see _norm).
    # expanduser first: Windows PowerShell 5.1 passes `~` through unexpanded, and
    # "~/x" joined under the repo named a directory called "~" -- evaluated
    # nothing, read CLEAR.
    scope = [_real(os.path.join(repo, p) if not os.path.isabs(p) else p)
             for p in (os.path.expanduser(q) for q in args.paths)]
    top = _git(repo, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and top.stdout.strip():
        repo = _real(top.stdout.strip())
    else:
        repo = _real(repo)

    # --- fact 0b: does every scope path belong to THIS checkout? --------
    # A path in another checkout is absent from this one's dirty set by
    # construction, so it read CLEAR however contested it really was.
    out_of_repo = _outside_repo(scope, repo)
    outside = {o["path"] for o in out_of_repo}
    nested = _nested_checkouts(repo, [p for p in scope if p not in outside])

    # --- fact 1: has HEAD moved since session start? --------------------
    # A blank or very short --since prefix-matches almost any HEAD and would
    # report "unchanged". Under 7 hex chars the fact cannot be established.
    head_moved, since_error = None, None
    if args.since is not None:
        since = args.since.strip().lower()
        if len(since) < 7 or any(ch not in "0123456789abcdef" for ch in since):
            since_error = "--since %r is not a sha of at least 7 hex chars" % args.since
        else:
            head_moved = not (head.lower().startswith(since)
                              or since.startswith(head.lower()))
    # --- fact 1b: did the move touch my scope? --------------------------
    head_moved_in_scope = None
    if head_moved:
        head_moved_in_scope = _moved_in_scope(
            repo, since, [p for p in scope if p not in outside])

    # --- fact 2: dirty files overlapping my scope -----------------------
    untracked = set()
    dirty = _dirty_paths(repo, untracked)
    if dirty is None:
        report = {"verdict": "NOT_A_REPO", "repo": repo,
                  "detail": "git status failed"}
        _emit(report, ["git status failed in %s" % repo], args.json)
        return EXIT_NOT_A_REPO
    # Attribute each overlapping dirty file. "Not yours" is the doctrine's
    # actual test -- flagging my OWN in-progress edit would make the gate fire
    # on every re-run, which is how gates get bypassed. A file with no recorded
    # owner, or one ALSO touched by someone else, stays foreign: unknown and
    # shared are both hazards, only "provably mine alone" is exempt.
    sessions_dir = args.sessions_dir or _default_sessions_dir()
    prov_index, prov_skipped = _scan_provenance(sessions_dir)
    mine = (args.session or "").lower()
    accepted_stale = {
        _norm(p if os.path.isabs(p) else os.path.join(args.repo, p))
        for p in (os.path.expanduser(q) for q in (args.accept_stale or []))}

    dirty_overlap_mine, dirty_overlap_foreign = [], []
    for p in dirty:
        if not _any_overlap(p, scope):
            continue
        rel = os.path.relpath(p, repo).replace("\\", "/")
        touches = _owners(p, prov_index)
        # Stale-owner discount (2026-09-12): a touch the path's last commit
        # already post-dates is history. Two false STOPs in one session came
        # from July / 09-09 touches on files committed since. Discounting only
        # ever REMOVES a session from `live`; an empty `live` still reads
        # foreign below, so history can never turn "unknown" into "mine".
        live, stale = _split_stale(
            touches, _last_commit_time(repo, rel) if touches else None)
        # Exact id match: an 8-char prefix of a SHORT --session ('b') made
        # every 'b...' session's file read as mine.
        only_mine = bool(live) and bool(mine) and all(
            o.lower() == mine for o in live)
        entry = {"path": rel, "owners": sorted(live), "stale_owners": sorted(stale)}
        if p in untracked:
            entry["_untracked"] = True
            entry["_touches"] = touches
        if only_mine and stale:
            # NOT auto-cleared (independent review 2026-09-12): a PARTIAL
            # commit -- hooks/lib/isolated_commit.py lands one hunk and leaves
            # the rest -- post-dates the other session's touch while its
            # remaining hunk is still dirty. Only the caller can check the
            # diff, so it stays CONTESTED until they say so via --accept-stale.
            if _norm(os.path.join(repo, rel)) in accepted_stale:
                entry["stale_accepted"] = True
            else:
                entry["stale_only"] = True
                only_mine = False
        (dirty_overlap_mine if only_mine else dirty_overlap_foreign).append(entry)
    # Nested worktrees under a directory scope (review round 2): a DIRTY one
    # contests -- its work is invisible to this checkout's status, and a sweep
    # over the parent (archive, cleanup) would take it. A CLEAN one has nothing
    # to protect and stays advisory, so the STOP is always satisfiable. Its
    # files are not attributed per-file (another checkout's provenance), and
    # an unreadable status is unknown, which contests like any unknown owner.
    for n in nested or []:
        nd = _dirty_paths(n["path"])
        n["dirty_count"] = None if nd is None else len(nd)
        if nd is None or nd:
            dirty_overlap_foreign.append({
                "path": os.path.relpath(n["path"], repo).replace("\\", "/"),
                "owners": [], "stale_owners": [],
                "nested_checkout": n["path"], "nested_dirty_count": n["dirty_count"]})
    dirty_overlap_mine.sort(key=lambda d: d["path"])
    # Nested entries first: they carry the only --repo hint, and must not be
    # pushed past the 20-line human cap by per-file entries.
    dirty_overlap_foreign.sort(key=lambda d: (not d.get("nested_checkout"), d["path"]))

    # --- fact 3: other sessions' live claims overlapping my scope -------
    claims_dir = args.claims_dir or _default_claims_dir(repo)
    claims, unreadable = _read_claims(claims_dir, args.ttl_minutes)

    competing, expired_overlap = [], []
    if claims is not None:
        for c in claims:
            if not any(_any_overlap(p, scope) for p in c["paths"]):
                continue
            if c["session_id"] and mine and c["session_id"].lower() == mine:
                continue  # my own claim (exact id; see ownership note above)
            (expired_overlap if c["expired"] else competing).append(c)

    # --- fact 4: untracked foreign copies of already-committed blobs ------
    # (see STALE UNTRACKED KNOWN BLOB). Only untracked, per-file, foreign
    # entries with no recorded owner inside the TTL window (an unknown touch
    # time counts as inside it) and no other session's live claim on the path.
    # Bounded: at most KNOWN_BLOB_MAX_CANDIDATES files are hashed; the rest
    # stay plain CONTESTED.
    # FAIL CLOSED (review #208): "no touch inside the window" is only evidence
    # when provenance was fully read. A missing/unlistable sessions dir, or any
    # session file that exists but could not be read, leaves the touch set
    # unknown -- an empty owner map there proves nothing, so classify nothing.
    provenance_complete = prov_index is not None and prov_skipped == 0
    touch_cutoff = time.time() - args.ttl_minutes * 60
    known_blob = []
    candidates = 0
    for d in dirty_overlap_foreign:
        is_untracked = d.pop("_untracked", False)
        touches = d.pop("_touches", {})
        if not provenance_complete:
            continue
        if not is_untracked or d.get("nested_checkout") or d["owners"]:
            continue
        # `not ts < cutoff` also catches a NaN timestamp (never provably old)
        if any(ts is None or not ts < touch_cutoff for ts in touches.values()):
            continue
        full = os.path.join(repo, d["path"].replace("/", os.sep))
        # Unreadable claims: classify anyway -- INDETERMINATE outranks the
        # known-blob verdict, so the unknown still cannot read as go.
        if any(any(_overlaps(cp, full) for cp in c["paths"]) for c in competing):
            continue
        if candidates >= KNOWN_BLOB_MAX_CANDIDATES:
            continue
        candidates += 1
        found = _known_blob(repo, d["path"])
        if found is None:
            continue
        d["known_blob"] = found[0]
        d["known_blob_commits"] = found[1]
        known_blob.append({"path": d["path"], "blob": found[0], "commits": found[1]})
    for d in dirty_overlap_mine:
        d.pop("_untracked", None)
        d.pop("_touches", None)

    # --- advisory: is this work landing only on a non-canonical branch? ---
    branch_info = _local_only(repo, [p for p in scope if p not in outside],
                              args.canonical)

    # --- verdict --------------------------------------------------------
    # A directory scope whose worktrees could not be listed may hide dirty
    # nested work: unmeasured, never clean. (File scopes cannot contain one.)
    nested_unmeasured = nested is None and any(
        os.path.isdir(p) for p in scope if p not in outside)
    indeterminate = (claims is None or bool(unreadable) or bool(since_error)
                     or nested_unmeasured)
    known_paths = {k["path"] for k in known_blob}
    known_only = (bool(dirty_overlap_foreign) and not competing
                  and all(d["path"] in known_paths and not d.get("nested_checkout")
                          for d in dirty_overlap_foreign))
    contested = (bool(dirty_overlap_foreign) or bool(competing)) and not known_only

    if out_of_repo:
        verdict, code = "OUT_OF_REPO", EXIT_OUT_OF_REPO
    elif head_moved and head_moved_in_scope != []:
        verdict, code = "HEAD_MOVED", EXIT_HEAD_MOVED
    elif contested:
        verdict, code = "CONTESTED", EXIT_CONTESTED
    elif indeterminate:
        verdict, code = "INDETERMINATE", EXIT_INDETERMINATE
    elif known_only:
        verdict, code = "STALE_UNTRACKED_KNOWN_BLOB", EXIT_CLEAR
    else:
        verdict, code = "CLEAR", EXIT_CLEAR

    report = {
        "verdict": verdict,
        "repo": repo,
        "head": head,
        "since": args.since,
        "head_moved": head_moved,          # null == not checked / uncheckable
        # only meaningful when head_moved: [] == measured, nothing in scope moved;
        # null == not measured (or HEAD did not move)
        "head_moved_in_scope": head_moved_in_scope,
        "since_error": since_error,
        "scope": [os.path.relpath(p, repo).replace("\\", "/")
                  if p not in outside else p for p in scope],
        "out_of_repo_paths": out_of_repo,
        "nested_checkouts_excluded": nested,   # null == could not enumerate
        "dirty_overlap_foreign": dirty_overlap_foreign,
        "dirty_overlap_mine": dirty_overlap_mine,
        # untracked foreign copies byte-identical to a blob committed at the
        # same path; they are ALSO listed in dirty_overlap_foreign
        "stale_untracked_known_blob": known_blob,
        "dirty_total": len(dirty),
        "sessions_dir": sessions_dir,
        "provenance_available": prov_index is not None,
        # count of session touched-files.txt that exist but could not be read;
        # > 0 means attribution is partial and known-blob classification is off
        "provenance_partial": prov_skipped,
        "competing_claims": competing,
        "expired_claims_overlapping": expired_overlap,
        "claims_dir": claims_dir,
        "claims_unreadable": unreadable,
        "canonical": args.canonical,
    }
    report.update(branch_info)

    # --- human-readable ------------------------------------------------
    say("PREFLIGHT %s -- %s" % (verdict, repo))
    say("  scope        : %s" % ", ".join(report["scope"]))
    if out_of_repo:
        say("  OUT-OF-REPO  : %d scope path(s) are not in this checkout -- nothing"
            " below was checked for them:" % len(out_of_repo))
        for o in out_of_repo:
            if o["suggested_repo"]:
                say("      %s   -> belongs to %s; re-run with --repo \"%s\""
                    % (o["path"], o["suggested_repo"], o["suggested_repo"]))
            elif o["reason"] == "unrecognised_spelling":
                say("      %s   -> git places it in this checkout but the spelling does"
                    " not resolve under it; pass it relative to --repo" % o["path"])
            else:
                say("      %s   -> git names no owning checkout (not in a work tree,"
                    " inside .git/, or git failed)" % o["path"])
    if nested_unmeasured:
        say("  NOT COVERED ?: could not list this repo's worktrees -- any nested"
            " under the directory scope went unexamined (INDETERMINATE)")
    clean_nested = [n for n in nested or [] if n.get("dirty_count") == 0]
    if clean_nested:
        say("  NOT COVERED  : %d clean nested worktree(s) under the scope (no"
            " uncommitted files; see nested_checkouts_excluded)" % len(clean_nested))
    if since_error:
        say("  HEAD         : %s  NOT CHECKED -- %s" % (head[:12], since_error))
    elif head_moved is None:
        say("  HEAD         : %s  (--since not given: not checked)" % head[:12])
    elif head_moved and head_moved_in_scope == []:
        say("  HEAD         : %s  WARNING: MOVED %s..%s -- no moved commit touches"
            " the scope, so this does not stop you; re-read anything OUTSIDE the"
            " scope you rely on" % (head[:12], since[:12], head[:12]))
    elif head_moved and head_moved_in_scope:
        say("  HEAD         : %s  MOVED since %s, touching %d scope path(s):"
            % (head[:12], args.since, len(head_moved_in_scope)))
        for p in head_moved_in_scope[:20]:
            say("      %s" % p)
        if len(head_moved_in_scope) > 20:
            say("      ... and %d more" % (len(head_moved_in_scope) - 20))
    elif head_moved:
        say("  HEAD         : %s  MOVED since %s (whether it touched the scope could"
            " not be established -- --since unresolvable or not an ancestor of HEAD)"
            % (head[:12], args.since))
    else:
        say("  HEAD         : %s  unchanged since session start" % head[:12])
    if dirty_overlap_foreign:
        n_nested = sum(1 for d in dirty_overlap_foreign if d.get("nested_checkout"))
        say("  NOT-YOURS dirty in scope (%d of %d dirty file(s) in repo%s):"
            % (len(dirty_overlap_foreign) - n_nested, len(dirty),
               " + %d dirty nested worktree(s)" % n_nested if n_nested else ""))
        for d in dirty_overlap_foreign[:20]:
            if d.get("nested_checkout"):
                cnt = d["nested_dirty_count"]
                if cnt is None:
                    say("      %s   [nested worktree, git status UNREADABLE -- repair or"
                        " prune it (`git worktree repair` / `prune`), or narrow the scope]"
                        % d["path"])
                else:
                    say("      %s   [nested worktree, %d uncommitted file(s) -- not in this"
                        " checkout's status; commit it, narrow the scope, or run with"
                        " --repo \"%s\"]" % (d["path"], cnt, d["nested_checkout"]))
                continue
            who = ", ".join(o[:8] for o in d["owners"]) or "no live recorded owner"
            say("      %s   [%s]%s%s" % (d["path"], who, _stale_note(d), _known_note(d)))
        if len(dirty_overlap_foreign) > 20:
            say("      ... and %d more" % (len(dirty_overlap_foreign) - 20))
    else:
        say("  not-yours dirty in scope: none (%d dirty elsewhere in repo)"
            % len(dirty))
    if dirty_overlap_mine:
        say("  (your own uncommitted edits in scope, not contesting: %s)"
            % ", ".join(d["path"] + _stale_note(d) for d in dirty_overlap_mine[:10]))
    if prov_index is None:
        say("  CAVEAT: provenance unavailable (%s) -- nothing can be proven"
            " yours, so every overlap is treated as not-yours." % sessions_dir)
    elif prov_skipped:
        say("  CAVEAT: provenance PARTIAL -- %d session touched-files.txt could not be"
            " read (%s); untracked known-blob files are not exempted." % (prov_skipped,
                                                                         sessions_dir))
    if competing:
        say("  COMPETING CLAIMS:")
        for c in competing:
            say("      %s  session %s  (%s)  -- %s"
                % (c["slug"], (c["session_id"] or "?")[:8], c["claimed_at"],
                   c["description"][:70]))
    else:
        say("  competing claims: none")
    for c in expired_overlap:
        say("  (expired claim ignored: %s  session %s  %s)"
            % (c["slug"], (c["session_id"] or "?")[:8], c["claimed_at"]))
    for u in unreadable:
        say("  UNREADABLE claim: %s" % u)
    if claims is None:
        say("  claims could not be read at all -- verdict is INDETERMINATE")
    if branch_info["off_canonical"]:
        unpushed = branch_info["unpushed_commits"]
        push_note = ("no upstream" if unpushed is None
                     else "%d unpushed commit(s)" % unpushed)
        if branch_info["local_only_paths"] is None:
            say("  LOCAL-ONLY ?  : on '%s', not '%s' -- could not check what exists on"
                " %s: %s (%s)" % (branch_info["current_branch"], args.canonical,
                                  args.canonical, branch_info["canonical_ref_error"],
                                  push_note))
        elif branch_info["local_only_paths"]:
            lop = branch_info["local_only_paths"]
            say("  LOCAL-ONLY   : on '%s', not '%s' (%s). %d scope path(s) exist on this"
                " branch but NOT on %s -- edits here land only on this branch:"
                % (branch_info["current_branch"], args.canonical, push_note, len(lop),
                   branch_info["canonical_ref"]))
            for p in lop[:20]:
                say("      %s" % p)
            if len(lop) > 20:
                say("      ... and %d more" % (len(lop) - 20))
        else:
            say("  branch       : on '%s', not '%s' (%s); no scope path is committed only"
                " on this branch vs %s"
                % (branch_info["current_branch"], args.canonical, push_note,
                   branch_info["canonical_ref"]))
    say()
    say({
        "CLEAR": "  -> go ahead.",
        "STALE_UNTRACKED_KNOWN_BLOB": "  -> go ahead, WITH CARE: every contesting file"
                                      " is an untracked copy of a blob already in git"
                                      " history at that path (listed above). Nothing in"
                                      " it is unsaved work; archive it when convenient.",
        "CONTESTED": "  -> STOP. Reconcile with the other session, or scope"
                     " into an isolated worktree.",
        "HEAD_MOVED": "  -> STOP. Re-read the files you are about to edit;"
                      " the checkout advanced under you.",
        "INDETERMINATE": "  -> uncertain, not clean. Establish the missing"
                         " fact before editing.",
        "NOT_A_REPO": "  -> not a checkout.",
        "OUT_OF_REPO": "  -> STOP. Paths outside --repo were never evaluated. Run"
                       " once per checkout, with the --repo that owns them.",
    }[verdict])

    _emit(report, out, args.json)
    return code


def _emit(report, lines, as_json):
    if as_json:
        sys.stdout.write(json.dumps(report, indent=1) + "\n")
        return
    for line in lines:
        sys.stdout.write(line + "\n")
    # Always last, always one line: survives being piped into `tail`.
    sys.stdout.write("RESULT_JSON=" + json.dumps(report) + "\n")


def _utf8_stdout():
    """A piped Windows stdout is cp1252: an emoji file name in the human lines
    raised UnicodeEncodeError, exiting 1 with no RESULT_JSON. json.dumps is
    ASCII-escaped already; only the human lines need this."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


if __name__ == "__main__":
    _utf8_stdout()
    sys.exit(main())
