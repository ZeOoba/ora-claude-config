"""Destructive-git guard -- PreToolUse hook, matcher: Bash (via pretooluse-dispatcher).

BLOCKS a git command that would DISCARD uncommitted work, but only when there is
work to lose:
  * `git checkout -- <p>` / `git checkout <p>` -> unstaged edits in <p>
  * `git checkout <tree-ish> [--] <p>`, `git checkout -f|--force`
                                        -> any dirty tracked file among the targets
  * `git restore <p>` (worktree side; `--staged` alone only touches the index)
  * `git switch -f|--force|--discard-changes`
  * `git reset --hard`                  -> any dirty tracked file
  * `git clean -f` (not `-n`)           -> anything `git clean -n` would remove
    (ignored paths are exempt as build output, EXCEPT in the claude-home config repo and
    for any ignored path whose name is sensitive -- see _protected_ignored, audit M01)
  * `git checkout|switch <commit>` / `git reset --hard|--keep|--merge <commit>` in the
    claude-home repo onto a commit that still TRACKS the local-only memory folder
    -> the local memory files (see memory_hazard, PR 476). OI-409 widened it to every
    form that writes an old tree, path or diff (clustered short flags, glob/magic
    pathspecs, `-m N` and `X^!` picks, bare merge/rebase, config-driven pull rebases,
    refs/heads|tags pull specs) and BLOCKS a pull/fetch-then-merge target that only
    resolves after the fetch -- the one place this guard is not fail-open, because it
    applies only while local memory exists and nothing about the target is knowable.

WHY (2026-09-22, /insights remediation): a stray `git checkout --` reverted reviewed
correctness fixes mid-session and they had to be rewritten. CLAUDE.md invariant 6
("never delete") covers files, not uncommitted edits; this closes that gap in
enforcement rather than prose.

SAFETY INVARIANT -- fail-open BY CONSTRUCTION. Blocks only on affirmative evidence:
the command parses to one of the forms above AND a timeout-bounded git probe in the
resolved directory shows something that would be lost. Unparseable command, missing
parse lib, not a repo, git error or timeout -> "no information" -> ALLOW.

BLOCKING CONTRACT: main() calls sys.exit(2) directly -- the dispatcher runs guards
in-process and reads rc only from SystemExit (see worktree-isolation-guard.py C1).

OVERRIDE: allow-destructive-git, 60 min, multi-use.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
GUARD_NAME = "destructive-git-guard"
OVERRIDE_BASENAME = "allow-destructive-git"
GIT_TIMEOUT = 8
# AUDIT M01 (2026-11-12). `git clean -fdX/-fdx` used to pass whenever every path it would
# remove was git-ignored ("build output"). In the claude-home repo (~/.claude) the .gitignore is
# DEFAULT-DENY, so the ignored set IS the live untracked state: hooks/confidential-terms.json
# (the fail-closed egress roster), .credentials.json, session state. There, no ignored path is
# exempt. Everywhere else an ignored path whose NAME matches the sensitive-file regex (same as
# sensitive-file-guard.py) or is the roster file is never treated as build output either.
SENSITIVE_IGNORED_RE = re.compile(r"(credentials|\.env|password|confidential-terms)", re.I)

_parse = None
_override_tokens = None
try:
    sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
    import git_commit_parse as _parse
except Exception:
    _parse = None
try:
    import override_tokens as _override_tokens
except Exception:
    _override_tokens = None


def _git(repo, *args):
    env = dict(os.environ)
    for v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
              "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
        env.pop(v, None)
    r = subprocess.run(("git",) + args, cwd=repo, capture_output=True,
                       encoding="utf-8", errors="replace", env=env, timeout=GIT_TIMEOUT)
    if r.returncode != 0:
        return None
    return [ln for ln in (r.stdout or "").splitlines() if ln.strip()]


def _short_flags(args):
    """Letters from short-flag clusters (`-fdx` -> {f,d,x}), stopping at `--`."""
    out = set()
    for a in args:
        if a == "--":
            break
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            out.update(a[1:])
    return out


def _split_dashdash(args):
    if "--" in args:
        i = args.index("--")
        return args[:i], args[i + 1:]
    return args, []


def classify(sub, args):
    """(kind, pathspecs) for a destructive invocation, else None.
    kind: 'tracked' (any dirty tracked file in pathspecs is lost), 'worktree' (only
    unstaged edits are lost -- restore from index), 'checkout-pos' (refs/paths resolved
    in at_risk) or 'clean'."""
    pre, post = _split_dashdash(args)
    longs = set(a for a in pre if a.startswith("--"))
    shorts = _short_flags(args)
    positional = [a for a in pre if not a.startswith("-")]
    if sub == "checkout":
        if "-b" in pre or "-B" in pre or "--orphan" in longs:
            return None
        if "f" in shorts or "--force" in longs:
            return ("tracked", [])
        if post:
            # `checkout -- p` restores from the INDEX (only worktree edits are lost);
            # `checkout <tree-ish> -- p` overwrites index AND worktree.
            return ("tracked" if positional else "worktree", post)
        if positional:
            # No `--`: each positional is a ref or a path -- resolved against the repo
            # in at_risk (REFUTE MED: `git checkout <file>` was missed).
            return ("checkout-pos", positional)
        return None
    if sub == "restore":
        staged = "--staged" in longs or "S" in shorts
        worktree = "--worktree" in longs or "W" in shorts
        if staged and not worktree:
            return None
        paths = post or positional
        if not paths:
            return None
        has_source = ("--source" in longs or "s" in shorts
                      or any(a.startswith("--source=") for a in pre))
        return ("tracked" if (has_source or staged) else "worktree", paths)
    if sub == "switch":
        if "f" in shorts or longs & {"--force", "--discard-changes"}:
            return ("tracked", [])
        return None
    if sub == "reset":
        if "--hard" in longs:
            return ("tracked", [])
        return None
    if sub == "clean":
        if "n" in shorts or "--dry-run" in longs:
            return None
        if "f" in shorts or "--force" in longs:
            return ("clean", args)
        return None
    return None


def at_risk(repo, kind, spec):
    """Lines describing what would be lost, [] if nothing, None if unknown."""
    if kind == "checkout-pos":
        refs, paths = [], []
        for a in spec:
            is_ref = _git(repo, "rev-parse", "--verify", "-q", a + "^{commit}") is not None
            if is_ref and not paths:
                refs.append(a)
            elif os.path.exists(os.path.join(repo, a)):
                paths.append(a)
        if not paths:
            return []  # a plain branch switch -- git itself refuses to clobber
        kind, spec = ("tracked" if refs else "worktree"), paths
    if kind in ("tracked", "worktree"):
        cmd = ["status", "--porcelain", "--untracked-files=no"]
        if spec:
            cmd += ["--"] + spec
        lines = _git(repo, *cmd)
        if lines is None or kind == "tracked":
            return lines
        # Restoring worktree FROM THE INDEX loses only unstaged edits: porcelain
        # column 2 (REFUTE MED: a staged-only change false-blocked).
        return [ln for ln in lines if len(ln) > 1 and ln[1] != " "]
    # clean: dry-run the same flags with force stripped.
    dry = []
    for a in spec:
        if a == "--force":
            continue
        if a.startswith("-") and not a.startswith("--") and "f" in a[1:]:
            rest = a[1:].replace("f", "")
            if rest:
                dry.append("-" + rest)
            continue
        dry.append(a)
    lines = _git(repo, "clean", "-n", *dry)
    if not lines:
        return lines
    # Ignored files (build output, node_modules, logs) are not uncommitted work: drop
    # them so routine `clean -fdx/-fdX` passes (review MED-2, 2026-09-22) -- EXCEPT in the
    # default-deny claude-home repo, where every ignored path is live state (audit M01).
    if _is_claude_home_repo(repo):
        return lines
    prefix = "Would remove "
    paths = [ln[len(prefix):] for ln in lines if ln.startswith(prefix)]
    try:
        # -z: NUL-separated both ways. Newline-separated stdin gets CRLF-translated on
        # Windows and git then matches "build.log\r" -- nothing is ever ignored.
        r = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"],
                           cwd=repo, input="\0".join(p.rstrip("/") for p in paths) + "\0",
                           capture_output=True, encoding="utf-8", errors="replace",
                           timeout=GIT_TIMEOUT)
        if r.returncode not in (0, 1):
            return lines
        ignored = set(x for x in (r.stdout or "").split("\0") if x)
    except Exception:
        return lines
    return [ln for ln in lines
            if not (ln.startswith(prefix) and ln[len(prefix):].rstrip("/") in ignored
                    and not _protected_ignored(ln[len(prefix):]))]


# PR 476 (2026-11-20): the memory folder is LOCAL-ONLY (gitignored, untracked) in the
# claude-home repo, but every commit before the untrack still TRACKS it. Moving the live
# checkout onto such a commit makes git overwrite the ignored memory files with that old
# snapshot (ignored files are expendable to git), and moving forward again DELETES them
# (tracked there, untracked here). No status probe sees it: nothing is "dirty".
MEMORY_REL = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory"


MEMORY_SUBS = ("checkout", "switch", "reset", "restore", "merge", "pull", "rebase",
               "cherry-pick", "revert", "read-tree")
# Options whose VALUE is a separate argument (so it is not mistaken for a ref or path).
_VALUE_OPTS = {
    "checkout": {"-b", "-B", "--orphan", "--conflict", "--pathspec-from-file"},
    "switch": {"-c", "-C", "--create", "--force-create", "--orphan", "--conflict"},
    "restore": {"-s", "--source", "--conflict", "--pathspec-from-file"},
    "fetch": {"--depth", "--deepen", "--shallow-since", "--shallow-exclude", "-o",
              "--server-option", "--upload-pack", "--negotiation-tip", "-j", "--jobs",
              "--refmap", "--recurse-submodules-default", "--submodule-prefix"},
    "merge": {"-m", "-s", "--strategy", "-X", "--strategy-option", "-F", "--file",
              "--into-name", "--cleanup"},
    "pull": {"-s", "--strategy", "-X", "--strategy-option", "--depth", "--deepen",
             "--shallow-since", "--shallow-exclude", "-o", "--server-option", "--upload-pack",
             "--negotiation-tip", "--cleanup"},
    "rebase": {"--onto", "-s", "--strategy", "-X", "--strategy-option", "-x", "--exec",
               "-C", "--whitespace", "--empty"},
    "cherry-pick": {"-m", "--mainline", "-s", "--strategy", "-X", "--strategy-option",
                    "--cleanup"},
    "revert": {"-m", "--mainline", "-s", "--strategy", "-X", "--strategy-option",
               "--cleanup"},
    "read-tree": {"--prefix", "--index-output"},
}
_STOP_OPS = {"--abort", "--continue", "--quit", "--skip", "--edit-todo", "--show-current-patch"}


def _parse_args(sub, args):
    """(positionals, post_dashdash, {option: value}, flags) for one invocation. A bare "-"
    is the previous branch (@{-1}); options that take a value consume it."""
    vopts = _VALUE_OPTS.get(sub, set())
    pre, post = _split_dashdash(args)
    pos, vals, flags = [], {}, set()
    i = 0
    while i < len(pre):
        a = pre[i]
        if a == "-":
            pos.append("@{-1}")
        elif a.startswith("--"):
            k, eq, v = a.partition("=")
            flags.add(k)
            if eq:
                vals[k] = v
            elif k in vopts and i + 1 < len(pre):
                vals[k] = pre[i + 1]
                i += 1
        elif a.startswith("-") and len(a) > 1:
            # A short-flag CLUSTER: walk every letter. The first value-taking letter takes
            # the rest of the cluster as its value, or the next argument (OI-409: `-qb x
            # old` and `-qs old` used to hide the option behind the leading `-q`).
            for j in range(1, len(a)):
                k = "-" + a[j]
                flags.add(k)
                if k in vopts:
                    if j + 1 < len(a):
                        vals[k] = a[j + 1:]
                    elif i + 1 < len(pre):
                        vals[k] = pre[i + 1]
                        i += 1
                    break
        else:
            pos.append(a)
        i += 1
    return pos, post, vals, flags


_REBASE_TRUE = {"true", "1", "yes", "on", "merges", "m", "interactive", "i", "preserve", "p"}
# A pathspec that names every path in the repo, whatever the command's directory.
_ALL_PATHS = [":/"]


def _strip_refspec(name):
    """`refs/heads/X` / `refs/tags/X` -> X (how a fetched branch or tag is named locally)."""
    for p in ("refs/heads/", "refs/tags/"):
        if name.startswith(p):
            return name[len(p):]
    return name


def fetch_targets(args):
    """Names a `git fetch` in an earlier segment of the same command may (re)point, so a
    later merge/rebase/reset of them reads PRE-fetch state: FETCH_HEAD plus every refspec
    destination."""
    pos, _post, _vals, _flags = _parse_args("fetch", list(args))
    out = {"FETCH_HEAD"}
    for spec in pos[1:]:
        if ":" in spec:
            dst = spec.lstrip("+").split(":", 1)[1]
            if dst:
                out.update((dst, _strip_refspec(dst)))
    return out


def memory_plans(sub, args, is_commit, config=None, fetched=None):
    """[(mode, ref, paths)] -- what this command would write into the worktree.
    'tree':   the worktree becomes ref's tree;            'paths': ref's content for paths;
    'merge':  ref's changes since the merge-base merge in; 'commit': a commit/range applies
              (paths carries the mainline parent number for `-m N`, else None);
    'unresolved': a target that cannot be resolved NOW but will exist once a fetch in this
              same command (or the pull itself) has run -- nothing can be verified.
    `is_commit(ref)` resolves refs against the repo; `config(key)` reads git config (None
    when unset); `fetched` is the set of names an earlier fetch in this command re-points,
    or None when no fetch precedes this segment."""
    pos, post, vals, flags = _parse_args(sub, list(args))
    if flags & _STOP_OPS:
        return []
    cfg = config or (lambda key: None)

    def target(ref, mode, paths=None, fetchable=True):
        """One plan for `ref`, or None. After a fetch in this command, a ref it re-points
        (or, for fetchable targets, any unresolvable ref) is 'unresolved'."""
        if fetched is not None and (ref in fetched or _strip_refspec(ref) in fetched):
            return ("unresolved", ref, None)
        if is_commit(ref):
            return (mode, ref, paths)
        if fetched is not None and fetchable:
            return ("unresolved", ref, None)
        return None

    def plans(items):
        return [p for p in items if p]

    if sub == "checkout":
        # A new-branch option's value is a NAME; the start point is the next positional.
        from_file = "--pathspec-from-file" in flags
        if post or from_file:
            if not pos:
                return []
            return plans([target(pos[0], "paths", post or _ALL_PATHS, fetchable=False)])
        if not pos:
            return []
        if len(pos) == 1:
            return plans([target(pos[0], "tree", fetchable=False)])
        if not is_commit(pos[0]):
            return []  # paths restored from the index
        return [("paths", pos[0], pos[1:])]
    if sub == "switch":
        return plans([target(r, "tree", fetchable=False) for r in pos])
    if sub == "reset":
        if post or not flags & {"--hard", "--keep", "--merge"}:
            return []
        return plans([target(r, "tree") for r in pos])
    if sub == "restore":
        src = vals.get("--source") or vals.get("-s")
        staged_only = bool(flags & {"--staged", "-S"}) and not flags & {"--worktree", "-W"}
        # `--pathspec-from-file`: the paths are in a file this guard does not read -- all.
        paths = _ALL_PATHS if "--pathspec-from-file" in flags else (post or pos)
        if not src or staged_only or not paths:
            return []
        return plans([target(src, "paths", paths, fetchable=False)])
    if sub == "merge":
        # Bare `git merge` merges the upstream (merge.defaultToUpstream, on by default).
        return plans([target(r, "merge") for r in (pos or ["@{u}"])])
    if sub == "pull":
        if len(pos) <= 1:
            refs = ["@{u}"]
        else:
            refs, specs, i = [], pos[1:], 0
            while i < len(specs):
                spec = specs[i]
                i += 1
                if spec == "tag" and i < len(specs):
                    refs.append(specs[i])  # `pull <remote> tag <name>`
                    i += 1
                    continue
                src = spec.lstrip("+").split(":", 1)[0]
                if not src:
                    refs.append("@{u}")
                elif src.startswith("refs/tags/"):
                    refs.append(src[len("refs/tags/"):])
                elif pos[0] == ".":
                    refs.append(_strip_refspec(src))  # `pull . <branch>`: a local branch
                else:
                    refs.append("%s/%s" % (pos[0], _strip_refspec(src)))
        rebase_opt = vals.get("--rebase")
        if "--no-rebase" in flags or (rebase_opt or "").lower() in ("false", "no", "off", "0"):
            rebase = False
        elif "--rebase" in flags or "-r" in flags:
            rebase = True
        else:
            branch = cfg("@branch")
            setting = (cfg("branch.%s.rebase" % branch) if branch else None)
            if setting is None:
                setting = cfg("pull.rebase")
            rebase = (setting or "").strip().lower() in _REBASE_TRUE
        mode = "tree" if rebase else "merge"
        # The pull fetches first: a target that cannot be resolved NOW (a refs/heads or tag
        # spec, a path remote, an unfetched branch) is only known after the fetch -- with
        # local memory present that is not an "allow" (OI-409).
        return [(mode, r, None) if is_commit(r) else ("unresolved", r, None) for r in refs]
    if sub == "rebase":
        refs = ([vals["--onto"]] if "--onto" in vals else []) + pos[:2]
        if not refs and "--root" not in flags:
            refs = ["@{u}"]  # bare `git rebase` rebases onto the upstream
        return plans([target(r, "tree") for r in refs])
    if sub in ("cherry-pick", "revert"):
        mainline = vals.get("-m") or vals.get("--mainline")
        mainline = mainline if (mainline or "").isdigit() else None
        if any(r.startswith("^") for r in pos):
            # `A ^B` / `^B A`: one revision walk, like a range.
            return [("commit", " ".join(pos), mainline)]
        out = []
        for r in pos:
            if ".." in r or r.endswith(("^!", "^@")) or "^-" in r:
                out.append(("commit", r, mainline))
            else:
                p = target(r, "commit", mainline)
                if p:
                    out.append(p)
        return out
    if sub == "read-tree":
        if "-u" not in flags or "--prefix" in flags:
            return []
        return plans([target(r, "tree") for r in pos])
    return []


_EMPTY_TREE = {"sha1": "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
               "sha256": "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321"}


def memory_hazard(repo, sub, args, fetched=None):
    """Lines naming what this command would write into the local-only memory folder, when
    `repo` is the claude-home repo and local memory exists. [] otherwise or on any doubt
    that is not affirmative evidence (fail-open, like the rest of this guard) -- except a
    target that only exists after a fetch in the same command, which cannot be checked at
    all while local memory is at stake (OI-409)."""
    if sub not in MEMORY_SUBS:
        return []
    top = _git(repo, "rev-parse", "--show-toplevel")
    if not top or not _is_claude_home_repo(top[0]):
        return []
    root = top[0]
    if not os.path.isdir(os.path.join(root, *MEMORY_REL.split("/"))):
        return []

    def is_commit(ref):
        return bool(_git(root, "rev-parse", "--verify", "-q", ref + "^{commit}"))

    def config(key):
        if key == "@branch":
            b = _git(root, "symbolic-ref", "--short", "-q", "HEAD")
            return b[0] if b else None
        v = _git(root, "config", "--get", key)
        return v[0] if v else None

    mem = MEMORY_REL + "/"
    # When HEAD does not track memory, a change that only DELETES memory writes nothing
    # into the worktree (OI-409 LOW: false block). For a revert the direction flips: a
    # reverted ADDITION is the deletion.
    head_tracks = bool(_git(root, "ls-tree", "--name-only", "HEAD", "--", mem))
    keep = [] if head_tracks else ["--diff-filter=%s" % ("a" if sub == "revert" else "d")]
    out = []
    for mode, ref, paths in memory_plans(sub, args, is_commit, config, fetched):
        if mode == "unresolved":
            out.append("%s target %s cannot be resolved until the fetch in this command has "
                       "run, so it cannot be checked for old copies of %s/ -- fetch first, "
                       "then re-run the %s on its own" % (sub, ref, MEMORY_REL, sub))
            continue
        if mode == "tree":
            hit = _git(root, "ls-tree", "--name-only", ref, "--", mem)
        elif mode == "paths":
            # Full pathspec rules (globs, magic, directory-relative), exactly as git reads
            # them from the command's own directory: everything in `ref` matching them.
            fmt = _git(root, "rev-parse", "--show-object-format") or ["sha1"]
            empty = _EMPTY_TREE.get(fmt[0], _EMPTY_TREE["sha1"])
            hit = [x for x in (_git(repo, "-c", "core.quotepath=off", "diff", "--name-only",
                                    "--no-renames", empty, ref, "--", *paths) or [])
                   if x.startswith(mem)]
        elif mode == "merge":
            base = _git(root, "merge-base", "HEAD", ref)
            hit = (_git(root, "diff", "--name-only", "--no-renames", *(keep + [base[0], ref,
                                                                              "--", mem]))
                   if base else None)
        elif " " in ref or ".." in ref or ref.endswith(("^!", "^@")) or "^-" in ref:
            # A range: every commit in it applies in turn, so an edit later reverted in the
            # same range still writes memory -- per-commit log, never the net diff.
            hit = _git(root, "log", "--format=%H", *(["-m"] if paths else []),
                       *(keep + ref.split() + ["--", mem]))
        elif paths:
            # `-m N` of a merge: the change applied is the diff against parent N.
            hit = _git(root, "diff", "--name-only", "--no-renames",
                       *(keep + ["%s^%s" % (ref, paths), ref, "--", mem]))
        else:
            hit = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root",
                       *(keep + [ref, "--", mem]))
        if hit:
            out.append("%s %s would write %d path(s) under %s/ into the worktree -- that "
                       "overwrites the local-only memory with an old copy (and a later move "
                       "or abort deletes them)" % (sub, ref, len(hit), MEMORY_REL))
    return out


def _norm(p):
    return os.path.normcase(os.path.realpath(p)).rstrip("\\/")


def _is_claude_home_repo(repo):
    """True when `repo`'s worktree root is the claude-home config repo: ~/.claude, or the
    tree this hook layer is installed in. Unknown -> True only if `repo` itself is one of
    them (the cheap, no-git comparison), so a git failure never widens the exemption."""
    homes = set()
    try:
        homes.add(_norm(os.path.join(os.path.expanduser("~"), ".claude")))
    except Exception:
        pass
    try:
        homes.add(_norm(os.path.dirname(HOOKS_DIR)))
    except Exception:
        pass
    top = _git(repo, "rev-parse", "--show-toplevel")
    cands = [repo] + (top[:1] if top else [])
    for c in cands:
        try:
            if _norm(c) in homes:
                return True
        except Exception:
            continue
    return False


def _protected_ignored(path):
    """An ignored path that `git clean -X/-x` must NOT be allowed to drop silently."""
    return bool(SENSITIVE_IGNORED_RE.search(os.path.basename(path.rstrip("/")) or path))


def _resolve_dir(p, here):
    """Real directory for a `cd`/`-C` argument, or None when it cannot be resolved.
    Handles ~, $VARS and Git Bash /c/... paths. None means NO INFORMATION: callers
    must stop probing rather than fall back to a stale directory (REFUTE HIGH: an
    unresolved `cd /c/...` used to probe the OLD cwd and block on ITS state)."""
    if not p or here is None:
        return None
    p = os.path.expandvars(os.path.expanduser(p))
    if len(p) >= 2 and p[0] == "/" and p[1].isalpha() and (len(p) == 2 or p[2] == "/"):
        p = p[1].upper() + ":/" + p[3:]
    if not os.path.isabs(p):
        p = os.path.join(here, p)
    return p if os.path.isdir(p) else None


def _git_c_dir(seg):
    """Value of `git -C <dir>` in this segment, if any."""
    for i, t in enumerate(seg[:-1]):
        if t == "-C":
            return seg[i + 1]
        if t not in ("git",) and not t.startswith("-") and "=" not in t:
            break
    return None


def findings(cmd, cwd):
    out = []
    try:
        segs = _parse.tokenize_cmd_segments(cmd)
    except Exception:
        return out
    here = cwd
    fetched = None  # names a fetch earlier in this command re-points (OI-409)
    for seg in segs:
        if not seg:
            continue
        if seg[0] == "cd":
            here = _resolve_dir(seg[1] if len(seg) >= 2 else "~", here)
            continue
        sa = _parse._segment_git_subcommand_and_args(seg)
        if not sa:
            continue
        sub, args = sa
        if sub in ("fetch", "pull"):
            try:
                names = fetch_targets(args) if sub == "fetch" else {"FETCH_HEAD"}
            except Exception:
                names = {"FETCH_HEAD"}
            fetched = (fetched or set()) | names
            if sub == "fetch":
                continue
        cdir = _git_c_dir(seg)
        where = _resolve_dir(cdir, here) if cdir else here
        if where is None:
            continue  # unresolvable directory -> no information -> allow
        try:
            mem = memory_hazard(where, sub, list(args), fetched)
        except Exception:
            mem = []
        if mem:
            out.append((" ".join(["git", sub] + list(args))[:200], where, mem))
        c = classify(sub, list(args))
        if not c:
            continue
        try:
            lost = at_risk(where, c[0], c[1])
        except Exception:
            lost = None
        if lost:
            out.append((" ".join(["git", sub] + list(args))[:200], where, lost))
    return out


def _safe(text):
    return "".join(ch for ch in str(text) if ch == " " or ch.isprintable())[:400]


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd or _parse is None:
        return 0
    if not any(w in cmd for w in ("checkout", "restore", "switch", "reset", "clean",
                                   "merge", "pull", "rebase", "cherry-pick", "revert",
                                   "read-tree")):
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    hits = findings(cmd, cwd)
    if not hits:
        return 0

    session_id = payload.get("session_id") or ""
    if _override_tokens is not None:
        try:
            tier = _override_tokens.Tier(OVERRIDE_BASENAME, "destructive-git", 3600)
            if _override_tokens.token_grants(session_id, tier) is not None:
                return 0
        except Exception:
            pass

    token = os.path.join(
        _override_tokens.sessions_root() if _override_tokens else "<sessions>",
        session_id or "<session>", "overrides", OVERRIDE_BASENAME).replace("\\", "/")
    parts = []
    for c, where, lost in hits:
        shown = "; ".join(_safe(x) for x in lost[:6])
        more = "" if len(lost) <= 6 else " (+%d more)" % (len(lost) - 6)
        parts.append("  cmd:  %s\n  repo: %s\n  would discard: %s%s"
                     % (_safe(c), _safe(where), shown, more))
    reason = (
        "this command would DISCARD uncommitted work.\n%s\n"
        "  Uncommitted edits may be another session's or your own reviewed fixes.\n"
        "  NOTE: a bare command is probed in the SESSION cwd, not a directory you `cd`-ed\n"
        "  to in an earlier call. If that repo is wrong, re-run as `git -C <dir> ...` or\n"
        "  `cd <dir> && ...` in the same call.\n"
        "  Do this instead: commit or set aside first (a WIP commit, or\n"
        "  `git stash push -u -m <unique-tag>` then apply by SHA), or narrow the pathspec.\n"
        "  If Gabriel has approved discarding it, write this override and retry:\n"
        "    path: %s\n    valid: 60 min, multi-use\n"
        "    content:\n      scope: destructive-git\n      session: %s\n"
        "      reason: <why Gabriel approved this>"
        % ("\n".join(parts), token, session_id or "<session>"))
    sys.stderr.write("BLOCKED (%s): %s\n" % (GUARD_NAME, reason))
    sys.exit(2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
