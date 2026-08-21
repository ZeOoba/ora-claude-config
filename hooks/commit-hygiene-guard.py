"""Commit-hygiene guard -- PreToolUse hook, matcher: Bash. WARN-ONLY.

Two independent commit-time checks, both closing gaps found live on 2026-08-09.

--- GAP A: BRANCH IDENTITY -------------------------------------------------------
A session verified `git status` and `git log -1` immediately before committing (exactly
what the shared-checkout single-writer rule prescribes), and STILL committed onto another
session's feature branch: between the check and the commit, a concurrent session ran
`git checkout` in the shared main checkout and moved HEAD's BRANCH out from under it. The
commit landed on `feat/model-canary-probe-step25`, stacked on three unrelated commits, and
had to be recovered by cherry-picking to main from a temporary worktree.

Why no existing guard caught it:
  * shared-checkout-guard.py is PreToolUse on Edit|Write|MultiEdit -- it never sees Bash,
    so a `git commit` is structurally invisible to it.
  * commit-provenance-guard.py DOES run on Bash commits, but it reasons about WHICH FILES
    the commit sweeps up (provenance), not about WHICH BRANCH receives them.
  * The dirty-file fingerprint is orthogonal: the branch can change while the dirty set
    does not, and vice versa. No amount of file-level checking surfaces branch identity.
So this states the destination branch at the one moment it matters, and says so louder
when the branch CHANGED since this session's last observed commit in that repo.

--- GAP B: MEMORY `modified:` STAMP ----------------------------------------------
Memory files carry a `modified:` frontmatter timestamp. The Claude Code HARNESS maintains
it when the harness itself writes a `node_type: memory` file through Edit/Write -- there is
no ORA hook doing this, which is exactly why it is easy to get wrong. A script/Bash write
(a Python splice, sed, a generated file) edits the same file without going through that
path, so the body changes and the stamp does not. Observed twice in one session:
people.md was fully rewritten but still claimed `modified: 2026-08-05`, and projects.md
shipped in 570dd6f still claiming 2026-08-03.

A stale stamp is not cosmetic: `modified:` is what a reader (and the staleness probes) use
to decide whether a memory file can be trusted, so a rewritten-but-stale-stamped file reads
as older -- and therefore less authoritative -- than it is. That is the same
inferred-vs-verified failure the memory doctrine exists to prevent.

Detection is deliberately at COMMIT time, not write time: at write time a script has no
obligation to stamp anything and there is nothing yet to compare against; at commit time
git gives us both versions for free, and a purely mechanical question -- "the content
changed; did the stamp move?" -- answers it with no heuristics.

SAFETY INVARIANT: warn-only, fail-open BY CONSTRUCTION. permissionDecision is ALWAYS
"allow"; it is never "deny"/"ask". The whole body is wrapped in try/except and exits 0 on
ANY error. A bug here must never block a commit -- cf. feedback_confidentiality_guard_selfdeadlock.md,
where a fail-CLOSED guard bricked Write/Edit/Bash machine-wide. Delivery uses
hookSpecificOutput.additionalContext because it is the only PreToolUse field that is both
model-visible and non-blocking (the lesson shared-checkout-guard.py records in its own
DELIVERY note: systemMessage alone reaches the user but never the model).

PRECISION POSTURE (REVISED 2026-08-09 after independent review -- the first draft's
rationale was WRONG and is recorded here because the correction is the load-bearing part).

The first draft argued detection could stay naive because "this one only ever prints, so
the worst outcome of a crafted command is a missing advisory line, not a bypassed gate."
Independent review refuted that empirically: with repo resolution taken from the payload
cwd alone, `git -C <repoA> commit` executed from a cwd inside repoB printed
"this commit will land on `feat/decoy`" -- repoB's branch -- while the commit really landed
on repoA's main. That is not a missing line; it is a CONFIDENTLY WRONG one, delivered at
the precise moment Gap A exists to protect, and it is the same failure class
shared-checkout-guard.py recorded on 2026-07-24: "a confidently WRONG name is worse than
no name" -- it sends the reader to reconcile against the wrong thing.

So the posture is now: a wrong advisory is worse than a missing one, and BOTH are worse
than the cost of resolving the command properly. This file therefore resolves the target
repo the way the command actually will (`cd` segments and `git -C`), and picks index vs
working tree by how the commit actually stages (`-a`/`--all`, or a preceding `git add` in
the same command line). Quote-aware tokenization with punctuation_chars=True also means a
glued `git add -A&&git commit` is segmented correctly rather than silently missed.

It still does NOT need memory-orphan-link-guard.py's full adversarial tearing defence:
that guard BLOCKS, so a crafted command that fools it bypasses a gate. This one only ever
prints, so a crafted command costs an advisory. The difference is that ORDINARY commands
must be right -- which is what the review showed the first draft got wrong.

--- GAP C: UNSCOPED STAGE (added 2026-08-21, usage-report remediation) ----------------
A bare `-a`/`--all`, or a sweep `git add -A`/`add .`/`add --all`/`add -u`, with no
explicit `-- <pathspec>` on the commit itself, stages whatever else happens to be dirty
in the working tree -- including the SAME session's own forgotten or unrelated local
edits, not just another session's (commit-provenance-guard.py already blocks that
cross-session case; this is the narrower, same-session hygiene gap it does not cover).

Deliberately WARN-only, not a new blocking gate: this repo already tried blocking-by-
syntax for git flags once and the lesson held -- a wrong or over-broad BLOCK on an
ordinary command is worse than a missed advisory, and BLOCKING a bare `-a`/`add -A`
would also be pure redundant friction on top of the cross-session case
commit-provenance-guard.py already enforces. So this reuses the exact same detection
`analyze()` already computes for stages_all/has_add (extended to also capture whether
an `add` segment's own args are a SWEEP form) and only ever prints.

Silent whenever the commit carries an explicit `-- <pathspec>` (already scoped, however
it got staged) or when `add` named explicit paths with no sweep flag.

ACCEPTED GAPS (independent review, 2026-08-21):
a separate-token `-m "-a"` (the value, not glued -- `git commit -m "-a"`) is misread by
the PRE-EXISTING `_cluster_stages_all` scan (same root cause as round-2 finding m8, which
only fixed the GLUED case) and now surfaces as a visible wrong UNSCOPED advisory instead
of a silent one -- noise-direction, never silence, never blocks; tolerated rather than
fixed here to avoid touching `_cluster_stages_all`'s pre-existing, independently-scoped
behavior in the course of adding an unrelated advisory. (`git add -- -u`, a file literally
named `-u`, was ALSO on this list originally -- Qodo's PR #142 review found the sweep scan
didn't stop at add's own `--`, and the fix for that [see add_has_own_pathspec above]
resolved this case as a side effect; removed from this list rather than left stale.)

Silence-direction, from the SAME PR #142 review round: `cd sub && git add -A && cd .. &&
git commit -m x` -- same repo, but the sweep is recorded against the resolved `repo/sub`
target while the commit resolves against `repo`, so `_norm_target()`'s literal path
comparison doesn't match them even though `git add -A` from a subdirectory sweeps the
WHOLE repo, not just `sub`. Fixing this needs `analyze()` to know the actual git toplevel,
which would mean adding git calls to a function deliberately kept git-free; tolerated
under this file's single-operator-cooperative threat model, same as the other gaps here.

Stdlib only. ASCII-only. Windows (`python`).
"""

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys

MEM_RE = re.compile(r"(?:^|/)memory/.+\.md$", re.IGNORECASE)
MODIFIED_RE = re.compile(r"^\s*modified:\s*(\S+)\s*$", re.MULTILINE)
# Global `git` options that take a separate value argument; the subcommand is whatever
# follows them. Anything starting with "-" that is not in this set is assumed valueless.
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"


# Characters that separate shell statements. `\n` is INCLUDED and is the whole point of
# the 2026-08-09 round-2 fix: shlex keeps newline in `whitespace` by default, so a bare
# newline never ends a segment and `git add -A\ngit commit -m x` parsed as ONE segment
# headed by `git add`, swallowing the commit -- silent. Multi-line Bash blocks are an
# ordinary shape here. `(`/`)` are included too, which incidentally makes a subshell
# `(git commit -m x)` visible. memory-orphan-link-guard.py reached the same settings by
# the same route; this is a deliberate port, not a coincidence.
SEP_CHARS = "();<>|&\n"


def _tokens(cmd):
    """Best-effort tokenization. shlex first (handles quoting); on failure fall back to a
    naive split rather than giving up, since a missing warning is this guard's only real
    failure mode."""
    try:
        return shlex.split(cmd, posix=True)
    except Exception:
        try:
            return cmd.split()
        except Exception:
            return []


def _segments(cmd):
    """[[token,...], ...] -- the command split into shell segments, quote-aware.

    punctuation_chars=True makes shlex emit `&&`/`||`/`;`/`|` as their OWN tokens even when
    glued to a word (`git add -A&&git commit`), which a plain shlex.split() silently welds
    into one token -- the regression memory-orphan-link-guard.py records in its Round B
    note. Splitting on those operator tokens then gives real segments, so `cd X && git
    commit` is two segments rather than one soup, and a `git` appearing as an ARGUMENT to
    another program (`echo git commit ...`) is no longer at a segment head.

    Falls back to a single naive segment on any tokenizer error: degrading to the old
    behavior is strictly better than going silent.
    """
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=SEP_CHARS)
        lex.whitespace_split = True
        # A newline must act as a SEPARATOR, not as whitespace, or multi-line blocks
        # collapse into one segment (round-2 finding M4).
        lex.whitespace = lex.whitespace.replace("\n", "")
        # `#` must NOT start a comment: `echo done # note\ngit commit` would otherwise eat
        # the rest of the line INCLUDING the newline, hiding the commit entirely.
        lex.commenters = ""
        toks = list(lex)
    except Exception:
        toks = _tokens(cmd)
    segs, cur = [], []
    for t in toks:
        if t and all(c in SEP_CHARS for c in t):
            # A pure-punctuation token (`&&`, `;`, `\n`, `|`, `(`, `)`) ends the segment.
            # Quoted newlines never reach here: they stay INSIDE their token, which is why
            # the heredoc `-m "$(cat <<'EOF' ... EOF)"` idiom still parses as one commit.
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def _strip_prefixes(seg):
    """Drop env assignments and sudo/command wrappers from a segment head, so
    `GIT_DIR=x sudo git commit` still presents `git` as the head token."""
    i = 0
    while i < len(seg):
        t = seg[i]
        if "=" in t and not t.startswith("-") and "/" not in t.split("=")[0]:
            i += 1
            continue
        if os.path.basename(t).lower() in ("sudo", "command", "env", "nice", "time",
                                           "then", "do", "else", "elif", "{", "!"):
            i += 1
            continue
        break
    return seg[i:]


def _git_subcommand(seg):
    """(subcommand, dash_C_value, rest_tokens) for a segment whose head is `git`,
    else (None, None, []). Skips global options exactly as is_git_commit did, and
    additionally CAPTURES `-C <path>` -- the value that decides which repo the command
    actually operates on (review finding M2)."""
    seg = _strip_prefixes(seg)
    if not seg:
        return None, None, []
    if os.path.basename(seg[0]).lower() not in ("git", "git.exe"):
        return None, None, []
    dash_c = None
    j = 1
    while j < len(seg):
        tok = seg[j]
        if not tok.startswith("-"):
            break
        if tok == "-C" and j + 1 < len(seg):
            dash_c = seg[j + 1]
            j += 2
            continue
        if tok in GIT_OPTS_WITH_VALUE:
            j += 2
            continue
        if "=" in tok:
            j += 1
            continue
        j += 1
    if j >= len(seg):
        return None, dash_c, []
    return seg[j], dash_c, seg[j + 1:]


# Short options that CONSUME the rest of the token as their value. Everything after one of
# these inside a cluster is data, not flags.
_VALUE_LETTERS = "mCcFt"


def _cluster_stages_all(arg):
    """True when `arg` is a commit flag that makes the commit stage tracked files itself.

    Value-aware (round-2 finding m8): the first draft asked `"a" in arg[1:]`, so
    `git commit -m"add feature X"` -- a GLUED message value containing the letter a --
    read as `-a` and made the guard read the WORKING TREE for a commit that will actually
    land the index. That is a false positive whose message asserts the file is being
    committed when it is not, which the module docstring's own posture ("a wrong advisory
    is worse than a missing one") rules out. Now the scan stops at the first value-taking
    letter: `-am` still qualifies (a precedes m), `-madd...` does not.
    """
    if not isinstance(arg, str) or not arg.startswith("-") or arg == "--":
        return False
    if arg == "--all":
        return True
    if arg.startswith("--"):
        return False
    for ch in arg[1:]:
        if ch == "a":
            return True
        if ch in _VALUE_LETTERS:
            return False
    return False


def _norm_target(p):
    """Comparable form of a resolved repo-target path string -- same precision level as
    the rest of this file's `-C`/`cd` resolution (a literal path comparison, not a real
    git-toplevel resolution, which analyze() does not have the git calls to do). Good
    enough for this file's single-operator-cooperative-fleet threat model; see the
    module's own ACCEPTED GAPS note."""
    return os.path.normcase(os.path.normpath(p))


def analyze(cmd, payload_cwd):
    """Resolve what this command line will actually do, or None when it is not a commit.

    Returns dict with exactly these keys: `repo_dir` (resolved against `cd` segments and a
    relative `git -C`), `stages_all`, `pathspec` (list), `has_add`, `sweep_add`. Closes
    review findings M1 (cd-compound), M2 (`git -C`), M3 (`git add && commit` / `commit -am`).
    """
    cwd = payload_cwd
    found = None
    has_add = False
    # GAP C sweep tracking, keyed by resolved repo target (independent review, PR #142):
    # a sweep `add` in ONE repo must not taint a `commit` in a DIFFERENT one
    # (`git -C repo1 add -A && git -C repo2 commit -m x`) -- a bare boolean can't tell
    # the two apart, so this records the resolved target every sweep add actually
    # touched, and each commit only consults entries matching ITS OWN resolved target.
    sweep_add_targets = set()
    for seg in _segments(cmd):
        stripped = _strip_prefixes(seg)
        # Track `cd <path>` so a later segment's repo resolves where the shell will be
        # (M1): `cd C:/repo && git commit` must resolve against C:/repo, not the payload cwd.
        if stripped and os.path.basename(stripped[0]).lower() == "cd" and len(stripped) > 1:
            target = os.path.expanduser(stripped[1])
            cwd = target if os.path.isabs(target) else os.path.join(cwd, target)
            continue
        sub, dash_c, rest = _git_subcommand(seg)
        if sub is None:
            continue
        if sub == "add":
            has_add = True
            # GAP C: does THIS add's own arg list contain a sweep token, UNSCOPED by a
            # pathspec? Unlike has_add (deliberately unrestricted, see the REVERT note
            # just below), this one only asks about the tokens actually passed to add --
            # `git add plain.txt` must stay silent while `git add -A`/`add .`/
            # `add --all`/`add -u` must not. Same token set pending_add_paths() in
            # hooks/lib/git_commit_parse.py already treats as "wants everything", kept
            # in sync deliberately rather than imported: this file has its own
            # independent tokenizer (see module docstring), so importing one function
            # from the other would still leave two segment-parsing implementations to
            # keep behavior-equivalent.
            #
            # SCOPED BY THE ADD'S OWN PATHSPEC (independent review, PR #142): git's `-A`/
            # `--all` means "the whole tree" only when NO pathspec is given to add itself
            # -- `git add -A -- plain.txt` is scoped to plain.txt, not a sweep, the same
            # way an explicit `-- <pathspec>` already scopes a commit elsewhere in this
            # function. Only the tokens BEFORE add's own `--` are eligible sweep tokens;
            # a `--` followed by at least one real path means this add is scoped and
            # never counts as a sweep, regardless of which flags precede it.
            add_flags = rest
            add_has_own_pathspec = False
            if "--" in rest:
                _idx = rest.index("--")
                add_flags = rest[:_idx]
                add_has_own_pathspec = bool([p for p in rest[_idx + 1:] if p])
            if not add_has_own_pathspec and any(
                    t in ("-A", "--all", "--no-ignore-removal", "-u", "--update", ".")
                    for t in add_flags):
                if dash_c:
                    add_target = dash_c if os.path.isabs(dash_c) else os.path.join(cwd, dash_c)
                else:
                    add_target = cwd
                sweep_add_targets.add(_norm_target(add_target))
            # DELIBERATELY NOT path-restricted (round-3 finding M5 -- this is a REVERT).
            #
            # Round 2 raised a MINOR false positive: `git add plain.txt && git commit`
            # warns about an unrelated dirty memory file the commit will not include. The
            # round-3 fix captured the add's named paths and restricted candidates to them.
            # That overcorrection created FOUR false-negative paths, all verified:
            #   * `git add memory/*.md && git commit` -- the shell expands the glob, the
            #     guard sees the literal `memory/*.md`, matches nothing, SILENT. A glob add
            #     aimed straight at the memory directory killed exactly the warning Gap B
            #     exists for.
            #   * `git add <unrelated> && git commit -am x` -- `-a` stages the memory file
            #     anyway, but the add-path restriction still applied. SILENT.
            #   * `git add -A && git add plain.txt && git commit` -- the empty-list sentinel
            #     conflated "unrestricted" with "nothing captured yet". SILENT.
            #   * a trailing `# ... -- ...` comment parsed as a pathspec. SILENT.
            # Every approximation error landed in the SUPPRESS direction, which inverts this
            # hook's stated cost asymmetry (a missed warning is the real failure; a spurious
            # one is noise). The original FP was explicitly filed as non-blocking. So the
            # restriction is removed rather than patched: reasoning about what a command
            # will stage, from tokens alone, before it runs, is not reliably decidable, and
            # a guess that fails silent is worse than the noise it replaced.
            continue
        if sub != "commit":
            continue
        # Drop a trailing shell comment BEFORE looking for `--` (round-3 finding M5.2):
        # `lex.commenters = ""` is required for the newline fix, so `# cleanup -- see notes`
        # survives as ordinary tokens and its `--` was read as a real pathspec separator --
        # restricting the commit to nonexistent paths and going silent. bash starts a
        # comment only at WORD START, so testing startswith("#") matches bash and leaves a
        # mid-word `#` (e.g. `file#1`, glued inside its own token) alone.
        # QUOTE-BLINDNESS (round-4 finding M6): shlex has already REMOVED the quotes by the
        # time we see a token, so a legitimate message `-m "#123 fix"` arrives as a token
        # starting with `#` and was truncated as if it were a comment. Both directions were
        # observed: `git commit -m "#123 fix" -a` lost its `-a` and went silent (a missed
        # warning), and `git commit -m "#123 fix" -- plain.txt` lost its real `--` and warned
        # about a file the pathspec excludes (a wrong advisory). Requiring the token to
        # contain NO WHITESPACE separates them: a real comment tokenizes to a bare `#` (or
        # `#word`), while a quoted message that merely begins with `#` almost always
        # contains a space and survives.
        # RESIDUAL, accepted: a single-word message like `-m "#123"` followed by more flags
        # still truncates. Vanishingly rare, and it fails toward silence rather than a wrong
        # advisory.
        for _i, _t in enumerate(rest):
            if _t.startswith("#") and not any(c.isspace() for c in _t):
                rest = rest[:_i]
                break
        pathspec = []
        if "--" in rest:
            pathspec = [p for p in rest[rest.index("--") + 1:] if p]
        stages_all = any(_cluster_stages_all(a) for a in rest)
        # A relative `-C` is resolved against the SHELL's cwd, not the hook process's
        # (round-2 finding m9): `git -C repo commit` from the parent dir was silent
        # because os.path.isdir("repo") ran in the hook's own working directory.
        if dash_c:
            target = dash_c if os.path.isabs(dash_c) else os.path.join(cwd, dash_c)
        else:
            target = cwd
        found = {
            "repo_dir": target,
            "stages_all": bool(stages_all),
            "pathspec": pathspec,
            # Snapshotted HERE, not after the whole loop (independent review,
            # 2026-08-21): sweep_add/has_add otherwise stay position-blind and would
            # credit a commit with a sweep `add` that only happens AFTER it in the same
            # compound command (`git commit -m x && git add -A` has not yet added
            # anything at the time this commit runs) -- a wrong advisory, exactly what
            # this module's own PRECISION POSTURE forbids. Matches "later commit wins":
            # each commit's snapshot reflects only sweep/add activity seen SO FAR.
            #
            # ALSO repo-scoped (independent review, PR #142, Qodo finding): a sweep add
            # only taints THIS commit if it targeted the SAME resolved repo -- otherwise
            # `git -C repo1 add -A && git -C repo2 commit -m x` would wrongly warn about
            # repo2's commit over repo1's sweep.
            "sweep_add": _norm_target(target) in sweep_add_targets,
            "has_add": has_add,
        }
        # keep scanning: a LATER commit segment wins, matching execution order
    if found is None:
        return None
    return found


def is_git_commit(cmd):
    """True when `cmd` invokes `git commit`.

    Requires the SUBCOMMAND position to be `commit` -- i.e. the first non-option token
    after a `git`, skipping global options and their values. This is what keeps
    `git log --grep commit` and `echo commit && git status` from matching, without needing
    a full shell parser.
    """
    # Cheap pre-filter before tokenizing. This hook is on the Bash hot path (every command
    # in every session), and shlex is the expensive part; a command with no literal
    # "commit" substring can never satisfy the subcommand test below, so the overwhelmingly
    # common case pays a substring scan instead of a full tokenize. Behavior-preserving by
    # construction: the check below requires an exact `commit` TOKEN, which implies the
    # substring.
    if "commit" not in cmd:
        return False
    # Segment-aware, sharing _segments/_git_subcommand with analyze() rather than
    # re-implementing option parsing (the first draft duplicated it, and the duplicate
    # used the NON-punctuation tokenizer -- so `git add -A&&git commit` welded into one
    # token, is_git_commit returned False, and main() early-returned before the
    # segmentation fix downstream could ever run). One parser, one behavior.
    for seg in _segments(cmd):
        sub, _dash_c, _rest = _git_subcommand(seg)
        if sub == "commit":
            return True
    return False


def _git(repo, *args, **kw):
    """Run git, returning stdout or None on ANY failure. `text_ok` allows binary-ish
    content through with replacement rather than raising."""
    try:
        # encoding="utf-8" is REQUIRED on Windows, not a nicety: with text=True alone,
        # subprocess decodes via the LOCALE codec (cp1252 here), so git's UTF-8 path bytes
        # for a non-ASCII filename are mangled before any matching happens -- the later
        # `git show HEAD:<path>` then fails on the corrupted path and the file is silently
        # skipped. Pairs with core.quotePath=false below: quotePath fixes git's escaping,
        # this fixes our decoding, and BOTH are needed to see such a path at all.
        proc = subprocess.run(("git", "-C", repo) + args, capture_output=True,
                              text=True, timeout=8, encoding="utf-8", errors="replace")
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def repo_root(cwd):
    out = _git(cwd, "rev-parse", "--show-toplevel")
    return out.strip() if out and out.strip() else None


def current_branch(repo):
    out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if not out:
        return None
    b = out.strip()
    return b or None


def _modified_value(text):
    if not text:
        return None
    m = MODIFIED_RE.search(text)
    return m.group(1) if m else None


def stale_stamp_files(repo, use_worktree=False, pathspec=None):
    """Already-tracked memory files whose CONTENT changed while `modified:` did not.

    --diff-filter=M restricts this to modifications: an added file has no HEAD version to
    compare against, and a deletion has no stamp to check. A file with no `modified:` field
    in HEAD is skipped -- it is not a stamped memory file and this rule does not apply.

    `use_worktree` selects WHICH version git will actually commit -- the working tree for a
    pathspec commit, for `commit -a/--all`, and for a `git add ... && git commit` compound
    (review finding M3: PreToolUse runs BEFORE the command, so the `add` has not happened
    yet and the index is still empty -- checking `--cached` there is a straight bypass, the
    same false negative memory-orphan-link-guard.py documents); the index for a plain
    already-staged commit.

    `pathspec`, when non-empty, additionally RESTRICTS candidates to files the commit
    actually names (review finding m2): warning about a dirty memory file that this
    pathspec commit will not touch implies it is being committed when it is not.

    `-c core.quotePath=false` is REQUIRED, not cosmetic: by default git renders a non-ASCII
    path as an escaped, DOUBLE-QUOTED string ("na\\303\\257ve.md"), which fails the
    `.md$` match and silently drops the file -- a false negative, this guard's only real
    failure mode, on exactly the filenames least likely to be noticed.
    """
    if use_worktree:
        names = _git(repo, "-c", "core.quotePath=false", "diff", "HEAD",
                     "--name-only", "--diff-filter=M")
    else:
        names = _git(repo, "-c", "core.quotePath=false", "diff", "--cached",
                     "--name-only", "--diff-filter=M")
    if not names:
        return []
    wanted = None
    if pathspec:
        wanted = [p.replace("\\", "/").strip("./") for p in pathspec]
    out = []
    for rel in names.splitlines():
        rel = rel.strip()
        if not rel or not MEM_RE.search(rel.replace("\\", "/")):
            continue
        if wanted is not None:
            norm = rel.replace("\\", "/")
            # A pathspec entry may name the file or a containing directory.
            if not any(norm == w or norm.startswith(w.rstrip("/") + "/") for w in wanted):
                continue
        head_txt = _git(repo, "show", "HEAD:" + rel)
        if use_worktree:
            try:
                with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                    new_txt = fh.read()
            except Exception:
                continue
        else:
            new_txt = _git(repo, "show", ":" + rel)
        old_v = _modified_value(head_txt)
        new_v = _modified_value(new_txt)
        if old_v is None or new_v is None:
            continue  # not a stamped memory file -> rule does not apply
        if old_v == new_v:
            out.append((rel, old_v))
    return out


def _branch_marker(sessions_dir, session_id, repo):
    """Keyed on a HASH OF THE FULL NORMALIZED REPO PATH, not its basename (review finding
    m7): two different checkouts that merely share a directory name -- e.g. a repo and its
    linked worktree, both named `commit-hygiene-guard` -- would otherwise share one marker
    and manufacture a false "BRANCH CHANGED" every time you alternated between them."""
    full = os.path.normcase(os.path.abspath(repo))
    key = hashlib.sha256(full.encode("utf-8", "replace")).hexdigest()[:16]
    return os.path.join(sessions_dir, session_id, "last-commit-branch-" + key)


def _read_prev_branch(marker):
    try:
        with open(marker, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip() or None
    except Exception:
        return None


def _write_branch(marker, branch):
    # utf-8, NOT ascii+replace (review finding m1): a non-ASCII branch name written with
    # errors="replace" is stored mangled (`feat/na?ve`), so the next comparison against the
    # real name never matches and EVERY subsequent commit reports a spurious BRANCH CHANGED
    # -- the alarm that cries wolf until it is ignored.
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(branch)
    except Exception:
        pass  # best-effort: a lost marker costs change-detection, not the branch line


def _safe(text):
    """Collapse to one printable line before it reaches MODEL-VISIBLE additionalContext.

    Branch names and file paths are attacker-influencable in principle (a crafted branch or
    a file named `... ignore previous instructions ...`), and shared-checkout-guard.py's
    H1/H2 findings establish the house standard of sanitizing such spans even when locally
    authored. Cheap, so applied rather than argued about."""
    s = str(text or "")
    s = "".join(c if (c.isprintable() and c not in "\r\n\t") else " " for c in s)
    s = " ".join(s.split())
    if len(s) > 160:
        s = s[:160].rstrip() + "...(truncated)"
    return s or "(unknown)"


def build_message(branch, prev_branch, stale, unscoped=False):
    parts = []
    if branch:
        if prev_branch and prev_branch != branch:
            parts.append(
                "BRANCH CHANGED since your last commit in this repo: you are now on `%s`, "
                "not `%s`. In a shared checkout another session can `git checkout` between "
                "your pre-commit check and this commit -- re-confirm this is the branch you "
                "intend before proceeding." % (_safe(branch), _safe(prev_branch)))
        else:
            parts.append("BRANCH: this commit will land on `%s`." % _safe(branch))
    if stale:
        listed = "; ".join("%s (still `modified: %s`)" % (_safe(p), _safe(v))
                           for p, v in stale[:4])
        more = "" if len(stale) <= 4 else " and %d more" % (len(stale) - 4)
        parts.append(
            "STALE MEMORY STAMP: %d memory file(s) changed content but their `modified:` "
            "frontmatter did NOT move: %s%s. The harness only stamps `modified:` when IT "
            "writes the file via Edit/Write -- a script/Bash write (python splice, sed, "
            "generated file) bypasses it. Hand-set `modified:` before committing, or the "
            "file will read as older, and therefore less trustworthy, than it is."
            % (len(stale), listed, more))
    if unscoped:
        parts.append(
            "UNSCOPED STAGE: this command uses `-a`/`--all`, or a bare `add -A`/`add .`/"
            "`add --all`/`add -u`, with no explicit `-- <pathspec>` on the commit itself -- "
            "it will stage whatever else is dirty in the working tree, including your own "
            "forgotten or unrelated local changes. Prefer `git commit -- <paths>` matching "
            "what you meant to stage, or hooks/lib/isolated_commit.py for a single-file, "
            "index-only stage.")
    return "\n\n".join(parts)


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not isinstance(cmd, str) or not cmd.strip():
        return
    if not is_git_commit(cmd):
        return

    cwd = payload.get("cwd") or os.getcwd()
    if not isinstance(cwd, str):
        return
    plan = analyze(cmd, cwd)
    if plan is None:
        return
    target = plan["repo_dir"]
    if not isinstance(target, str) or not os.path.isdir(target):
        return
    repo = repo_root(target)
    if not repo:
        return  # not a git repo -> nothing to say

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"
    sessions_dir = os.environ.get("COMMIT_HYGIENE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR

    branch = current_branch(repo)
    marker = _branch_marker(sessions_dir, session_id, repo)
    prev = _read_prev_branch(marker)
    # The committed content comes from the working tree whenever the commit stages for
    # itself (-a/--all), names a pathspec, or is preceded by a `git add` in the SAME
    # command line (which has not run yet at PreToolUse time).
    use_wt = bool(plan["pathspec"]) or plan["stages_all"] or plan["has_add"]
    # ONLY an explicit `git commit -- <pathspec>` restricts candidates. Inferring a
    # restriction from a preceding `git add` was tried and reverted -- see the M5 note in
    # analyze(): every inference error failed silent, which is the one direction this hook
    # must not fail in.
    stale = stale_stamp_files(repo, use_worktree=use_wt, pathspec=plan["pathspec"])
    # UNSCOPED only when the commit itself carries no explicit pathspec: a `-- <paths>`
    # commit is already scoped to exactly those paths regardless of how staging happened.
    unscoped = (plan["stages_all"] or plan["sweep_add"]) and not plan["pathspec"]

    msg = build_message(branch, prev, stale, unscoped=unscoped)
    if not msg:
        return
    _emit(msg)
    # Recorded only AFTER delivery, mirroring shared-checkout-guard's _commit_marker
    # ordering lesson: if the marker were written first and delivery then raised, the
    # change would be deduped away forever and never re-reported.
    if branch:
        _write_branch(marker, branch)


def _emit(msg):
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",   # NEVER deny -- see SAFETY INVARIANT
            "additionalContext": msg,
        },
    }))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a commit
    sys.exit(0)
