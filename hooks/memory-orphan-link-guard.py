"""MEMORY.md orphan-index-link COMMIT-time guard -- PreToolUse hook for Bash.

THE DEFECT THIS PREVENTS. memory-integrity-probe.py reports "orphan index link IN GIT":
HEAD's MEMORY.md links a memory file that HEAD's TREE does not contain, so anyone cloning
the repo gets a broken pointer. It fired with 5 such links on 2026-07-24 (probe exit 1),
and the root cause is structural, not careless: MEMORY.md is a single shared file that many
sessions append to, while each session's memory BODY file is its own new untracked file.
Whoever commits MEMORY.md sweeps up everyone's index lines -- including lines whose bodies
that committer never had staged. See reference_event_log_uncommitted_backlog.md (no single
committer) and shared-checkout-cofile-patch-hazard.md.

WHY COMMIT TIME AND NOT WRITE TIME. At write time the body file is sitting right there on
disk, so a write-time check sees nothing wrong -- the orphan only comes into existence when
MEMORY.md is committed WITHOUT the body. hooks/memory-index-guard.py already owns the
write-time rule (the 150-char hook cap) and is deliberately left alone here; this guard owns
the distinct commit-time rule. Same file, two different failure modes, two separate guards.

WHAT IT CHECKS. When a Bash command is a `git commit` that would include MEMORY.md, every
relative markdown link in the version of MEMORY.md that git is about to commit must resolve
to a path that is either already in HEAD or staged in this same commit. If any does not, the
commit is denied with the exact `git add` line that fixes it.

Reads the version git will ACTUALLY commit:
  * `git commit -- <pathspec>` re-reads the WORKING TREE (see
    feedback_pathspec_commit_discards_index_splice.md), so we read the working tree.
  * a plain staged `git commit` commits the INDEX, so we read `git show :<path>`.
Getting this wrong in the lenient direction only ever means missing a block, never a false
one -- but it is cheap to get right, so we do.

DELIBERATELY NOT AN AUTO-COMMITTER. The obvious framing is "auto-commit the body when
MEMORY.md is written." That would be actively dangerous in this checkout: HEAD moved six
times during the 2026-07-24 session from concurrent sessions, and an unattended `git add`
would sweep another session's in-flight work into a commit it never reviewed -- the exact
hazard recorded in the backlog-janitor note. Blocking is safe; committing on someone's
behalf is not.

SAFETY INVARIANT: the entire body is wrapped in try/except and exits 0 (ALLOW) on ANY error
-- unparseable stdin, no git, detached repo, unreadable file, weird command shape. A bug here
must never block a commit and must never lock Gabriel out of his own memory index
(cf. feedback_confidentiality_guard_selfdeadlock.md, where a fail-CLOSED guard bricked
Write/Edit/Bash machine-wide). Fail-open is also the ratified default for cross-session
coordination guards -- feedback_fail_open_over_mutex_for_fleet_gates.md.

Stdlib only. ASCII-only. Windows.
"""

import json
import os
import re
import shlex
import subprocess
import sys

DEFAULT_MEMORY_INDEX = (
    "C:/Users/Owner/.claude/projects/"
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md")

# Markdown link whose target is a relative .md path: [Title](some_file.md) or (some_file.md#anchor).
# Skips absolute URLs (http:, https:, mailto:) and wiki-style [[links]], which are not paths.
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?!\w+:)([^)\s#]+\.md)(?:#[^)\s]*)?\s*\)")

# Git global options that take their value as a SEPARATE following token. These must be
# skipped WITH their value when looking for the subcommand, or `git -c user.name=x commit`
# reads as subcommand "user.name=x" and the guard silently never fires.
GIT_VALUE_OPTS = frozenset((
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
))


def target_index():
    return os.environ.get("ORA_MEMORY_INDEX") or DEFAULT_MEMORY_INDEX


def _git(repo, *args):
    """Run git, returning stdout or None. Never raises."""
    try:
        p = subprocess.run(
            ("git",) + args, cwd=repo, capture_output=True, timeout=15)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def _segment_git_parts(seg):
    """(subcommand, [args after it]) if this segment invokes git, else (None, []).

    Tokenized rather than regexed on purpose: the subcommand is the first token after
    `git` that is not an option (or an option's separate value). A substring match would
    wrongly fire on `git log --grep=commit`, because `commit` sits on a word boundary
    inside that token.
    """
    try:
        toks = seg.split()
    except Exception:
        return None, []
    # Find the git executable token (allows `/usr/bin/git`, `git.exe`, and a leading
    # `sudo`/`env`-style prefix that we simply scan past).
    gi = None
    for i, t in enumerate(toks):
        base = t.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if base in ("git", "git.exe"):
            gi = i
            break
    if gi is None:
        return None, []
    i = gi + 1
    while i < len(toks):
        t = toks[i]
        if t in GIT_VALUE_OPTS:
            i += 2          # skip the option AND its separate value
            continue
        if t.startswith("-"):
            i += 1          # `--foo`, `--foo=bar`, `-p` -- self-contained
            continue
        return t, toks[i + 1:]  # first non-option token IS the subcommand
    return None, []


def _segment_is_git_commit(seg):
    """True if this single command segment invokes `git commit`."""
    return _segment_git_parts(seg)[0] == "commit"


# ---------------------------------------------------------------------------------
# PreToolUse TIMING (2026-07-24). This hook runs BEFORE the command does, so reading
# the index alone judges a state the command is about to change. For a COMPOUND
# command that produced two opposite failures, both verified against the live guard:
#   * FALSE NEGATIVE -- `git add MEMORY.md && git commit`: unstaged at hook time, so the
#     guard returned "not our business" and the orphan links landed. A straight BYPASS.
#   * FALSE POSITIVE -- `git restore --staged MEMORY.md && git commit`: staged at hook
#     time, so a commit that would NOT have included it was blocked.
# Same class as the config-write-guard compound-add blind spot. Fix: walk the command's
# segments in order and simulate whether MEMORY.md ends up in the commit.
# ---------------------------------------------------------------------------------
_STAGE_ALL_FLAGS = {"-A", "--all", "-u", "--update"}


def _mentions_path(args, rel):
    """True if any arg names MEMORY.md -- repo-relative, absolute, or bare basename."""
    base = rel.rsplit("/", 1)[-1]
    for a in args:
        a2 = a.strip("\"'").replace("\\", "/")
        if a2 == rel or a2.endswith("/" + rel) or a2 == base or a2.endswith("/" + base):
            return True
    return False


def _commit_would_include(cmd, rel, staged_now):
    """(included, from_worktree) -- does MEMORY.md end up in this commit, and does its
    content come from the working tree (because the command stages it) or the index?

    Deliberately errs toward INCLUDED: a wrong 'included' costs a spurious block that a
    human can inspect, while a wrong 'excluded' silently lands the orphan this guard
    exists to stop.

    PATHSPEC EXCLUSIVITY (2026-07-24). `git commit -- <pathspec>` is EXCLUSIVE by git's
    own semantics -- verified directly: `git add A.md B.md; git commit -- A.md` commits
    ONLY A.md, leaving B.md staged and untouched even though it WAS staged at commit
    time; `git commit -a -- A.md` is a hard git error ("fatal: paths ... with -a does
    not make sense") and never commits at all. So once a `commit` segment carries a
    `--` pathspec, whether `rel` is one of the named paths is the ONLY question -- any
    staged_now state or earlier add/-a in this same command is moot, because the
    pathspec is what git actually honors. Concretely: in a shared checkout, another
    session's unrelated `git add` can leave MEMORY.md sitting staged in the index;
    without this carve-out a plain `git commit -- unrelated/file.md`, which cannot
    possibly touch MEMORY.md, was DENIED anyway.

    QUOTE-AWARE `--` DETECTION (2026-07-24, REFUTE pass on the carve-out above). The
    rest of this file tokenizes segments with a naive `.split()`, which is fine for
    finding a subcommand name but is NOT safe for spotting a pathspec separator: an
    ORDINARY commit message containing a standalone " -- " (e.g. "fix -- bug", "notes
    -- see PR") naive-splits into its OWN "--" token, which a first version of this
    carve-out trusted as a real pathspec -- reopening the exact bypass the 2026-07-24
    12:54 fix closed, just behind different bait. Verified live: `git add MEMORY.md &&
    git commit -m "fix -- bug"` and `git commit -am "fix -- bug"` both got ALLOW under
    that version. Only a `shlex`-tokenized (quote-aware) standalone `--` is trusted here;
    one embedded inside a quoted argument is invisible to shlex and correctly ignored.
    """
    staged, from_worktree = staged_now, False
    for seg in re.split(r"(?:&&|\|\||;|\|)", cmd):
        sub, args = _segment_git_parts(seg.strip())
        if sub is None:
            continue
        if sub == "add":
            bulk = any(a in _STAGE_ALL_FLAGS for a in args) or \
                any(a.strip("\"'") == "." for a in args)
            if bulk or _mentions_path(args, rel):
                staged, from_worktree = True, True
        elif sub == "restore" and "--staged" in args:
            paths = [a for a in args if not a.startswith("-")]
            if not paths or _mentions_path(args, rel):
                staged, from_worktree = False, False
        elif sub == "reset":
            paths = [a for a in args if not a.startswith("-") and a != "HEAD"]
            if not paths or _mentions_path(args, rel):
                staged, from_worktree = False, False
        elif sub == "commit":
            pathspec = None
            try:
                quoted = shlex.split(seg)
            except ValueError:
                quoted = None  # unbalanced quoting -- do not trust a pathspec read here
            if quoted is not None and "--" in quoted:
                pathspec = quoted[quoted.index("--") + 1:]
            if pathspec is not None:
                included_here = _mentions_path(pathspec, rel)
                staged, from_worktree = included_here, included_here
                continue
            # `-a` / `--all` stages every tracked modified file, including MEMORY.md --
            # so it re-includes a file an earlier segment just unstaged.
            if any(a in ("-a", "--all") or
                   (a.startswith("-") and not a.startswith("--") and "a" in a[1:])
                   for a in args):
                staged, from_worktree = True, True
    return staged, from_worktree


def _is_git_commit(cmd):
    """True if the command line invokes `git commit`. Ignores commands that merely
    MENTION it -- e.g. an echo of advice text, or `git log --grep=commit`."""
    if not isinstance(cmd, str) or "commit" not in cmd:
        return False
    # Split on shell separators so `cd x && git commit -m y` still matches, while a
    # quoted mention inside a single argument does not get its own segment.
    for seg in re.split(r"(?:&&|\|\||;|\|)", cmd):
        if _segment_is_git_commit(seg.strip()):
            return True
    return False


def _has_pathspec(cmd):
    """True if a `--` pathspec separator is present, which makes git commit the WORKING
    TREE for those paths rather than the index."""
    return re.search(r"\s--\s", cmd) is not None


def _staged_paths(repo):
    out = _git(repo, "diff", "--cached", "--name-only")
    if out is None:
        return None
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def _in_head(repo, relpath):
    return _git(repo, "cat-file", "-e", "HEAD:" + relpath) is not None


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    if payload.get("tool_name") != "Bash":
        return
    cmd = (payload.get("tool_input") or {}).get("command")
    if not _is_git_commit(cmd):
        return

    index_abs = os.path.abspath(target_index())
    if not os.path.isfile(index_abs):
        return

    repo_dir = os.path.dirname(index_abs)
    toplevel = _git(repo_dir, "rev-parse", "--show-toplevel")
    if not toplevel:
        return  # not a git repo -- nothing to guard
    repo = toplevel.strip()

    # Repo-relative path of MEMORY.md, forward-slashed the way git reports paths.
    rel_index = os.path.relpath(index_abs, repo).replace(os.sep, "/")

    staged = _staged_paths(repo)
    if staged is None:
        return

    # Would this commit include MEMORY.md at all? Simulated from the command's segments,
    # NOT read straight off the pre-command index -- see _commit_would_include.
    included, from_worktree = _commit_would_include(cmd, rel_index, rel_index in staged)
    if not included:
        return  # MEMORY.md not part of this commit -- not our business

    if _has_pathspec(cmd) or from_worktree:
        # A pathspec commit takes the WORKING TREE, and so does anything the command
        # stages itself.
        try:
            with open(index_abs, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception:
            return
    else:
        content = _git(repo, "show", ":" + rel_index)
        if content is None:
            return

    # If the version being committed is byte-identical to HEAD's, this commit lands no
    # new index lines -- any orphan in it is pre-existing, and blocking here would be a
    # permanent deadlock rather than a guard. (Reachable via `git add -A` when MEMORY.md
    # happens to be unmodified.)
    head_content = _git(repo, "show", "HEAD:" + rel_index)
    if head_content is not None and head_content == content:
        return

    mem_dir = os.path.dirname(rel_index)
    missing = []
    seen = set()
    for target in LINK_RE.findall(content):
        if target in seen:
            continue
        seen.add(target)
        rel_target = (mem_dir + "/" + target) if mem_dir else target
        rel_target = os.path.normpath(rel_target).replace(os.sep, "/")
        if rel_target in staged:
            continue
        if _in_head(repo, rel_target):
            continue
        missing.append(rel_target)

    if not missing:
        return

    on_disk = [m for m in missing if os.path.isfile(os.path.join(repo, m))]
    absent = [m for m in missing if m not in on_disk]

    parts = [
        "MEMORY.md orphan-index-link guard: this commit would land %d index link(s) whose "
        "body file is neither in HEAD nor staged. A clone would get a broken pointer, and "
        "memory-integrity-probe.py would exit 1 on the next run." % len(missing)
    ]
    if on_disk:
        parts.append(
            "\nPresent on disk but NOT staged -- stage the bodies in the SAME commit:\n"
            "  git add %s" % " ".join('"%s"' % m for m in on_disk))
    if absent:
        parts.append(
            "\nNot on disk at all (typo, rename, or a body never written):\n" +
            "\n".join("  - " + m for m in absent))
    parts.append(
        "\nBody before index, always. If these bodies belong to ANOTHER session, do not "
        "stage them -- commit your own body files first and leave that session's index "
        "line uncommitted for it to land.")

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "".join(parts),
        }
    }
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a bug must never block a commit
    sys.exit(0)
