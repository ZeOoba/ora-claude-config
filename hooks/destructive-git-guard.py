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
             "--negotiation-tip", "--cleanup", "--refmap", "--negotiation-restrict",
             "--negotiation-include"},
    "rebase": {"--onto", "-s", "--strategy", "-X", "--strategy-option", "-x", "--exec",
               "-C", "--whitespace", "--empty"},
    "cherry-pick": {"-m", "--mainline", "-s", "--strategy", "-X", "--strategy-option",
                    "--cleanup"},
    "revert": {"-m", "--mainline", "-s", "--strategy", "-X", "--strategy-option",
               "--cleanup"},
    "read-tree": {"--prefix", "--index-output"},
}
_STOP_OPS = {"--abort", "--continue", "--quit", "--skip", "--edit-todo", "--show-current-patch"}


def _parse_args(sub, args, every=None):
    """(positionals, post_dashdash, {option: value}, flags) for one invocation. A bare "-"
    is the previous branch (@{-1}); options that take a value consume it. `vals` keeps the
    LAST value of a repeated option; pass a dict as `every` to also collect all of them."""
    vopts = _VALUE_OPTS.get(sub, set())

    def put(k, v):
        vals[k] = v
        if every is not None:
            every.setdefault(k, []).append(v)

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
                put(k, v)
            elif k in vopts and i + 1 < len(pre):
                put(k, pre[i + 1])
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
                        put(k, a[j + 1:])
                    elif i + 1 < len(pre):
                        put(k, pre[i + 1])
                        i += 1
                    break
        else:
            pos.append(a)
        i += 1
    return pos, post, vals, flags


_REBASE_TRUE = {"true", "1", "yes", "on", "merges", "m", "interactive", "i", "preserve", "p"}
# A pathspec that names every path in the repo, whatever the command's directory.
_ALL_PATHS = [":/"]
_UNRESOLVED = object()
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _strip_refspec(name):
    """`refs/heads/X` / `refs/tags/X` -> X, `refs/remotes/R/X` -> R/X (how a ref is named
    for rev-parse)."""
    for p in ("refs/heads/", "refs/tags/", "refs/remotes/"):
        if name.startswith(p):
            return name[len(p):]
    return name


def _is_network_url(url):
    """True for a URL git reaches over the network (https://, ssh://, git@host:path);
    False for a local path, `file://` or `.` -- whose refs can hold ANY old history."""
    u = (url or "").strip()
    if not u or u.startswith("file://"):
        return False
    if "://" in u:
        return True
    return bool(re.match(r"^[^/\\:]+:", u)) and not re.match(r"^[A-Za-z]:", u)


def _norm_key(key):
    """git config key normalization: section and variable are case-insensitive, a
    subsection (branch name) is not."""
    parts = key.split(".")
    if len(parts) >= 3:
        return ".".join([parts[0].lower()] + parts[1:-1] + [parts[-1].lower()])
    return key.lower()


def segment_config(seg):
    """{normalized key: value} from `git -c k=v` options in this segment; None when the
    segment sets git config through the environment (GIT_CONFIG_*, --config-env), which
    this guard does not model -- callers then assume the worst case."""
    out = {}
    i = 0
    while i < len(seg) and _ENV_ASSIGN.match(seg[i]):
        if seg[i].upper().startswith("GIT_CONFIG"):
            return None
        i += 1
    if i >= len(seg) or seg[i] != "git":
        return out
    i += 1
    while i < len(seg) and seg[i].startswith("-"):
        t = seg[i]
        if t.startswith("--config-env"):
            return None
        if t == "-c" and i + 1 < len(seg):
            k, eq, v = seg[i + 1].partition("=")
            out[_norm_key(k)] = v if eq else "true"
            i += 2
        elif t in ("-C", "--git-dir", "--work-tree", "--namespace"):
            i += 2
        else:
            i += 1
    return out


class _Repo(object):
    """Read-only git probes for one claude-home repo, with this segment's `-c` overrides
    (None = config set through the environment: unknown)."""

    def __init__(self, root, overrides):
        self.root = root
        self.overrides = overrides

    def config(self, key):
        if self.overrides and _norm_key(key) in self.overrides:
            return self.overrides[_norm_key(key)]
        v = _git(self.root, "config", "--get", key)
        return v[0] if v else None

    def branch(self):
        b = _git(self.root, "symbolic-ref", "--short", "-q", "HEAD")
        return b[0] if b else None

    def is_commit(self, ref):
        return bool(_git(self.root, "rev-parse", "--verify", "-q", ref + "^{commit}"))

    def is_treeish(self, ref):
        return bool(_git(self.root, "rev-parse", "--verify", "-q", ref + "^{tree}"))

    def upstream_name(self):
        u = _git(self.root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        return u[0] if u else None

    def remote_is_local(self, name):
        """A configured remote (or a URL/path given in its place) that is NOT a network
        remote. Since the 2026-11-20 history purge no network remote (GitHub) carries
        memory, so its remote-tracking refs are judged as they stand before a fetch; a
        LOCAL remote can serve any old branch, so what it fetches is unknowable."""
        if name == ".":
            return True
        url = self.config("remote.%s.url" % name)
        return not _is_network_url(url if url is not None else name)

    def dwim_remote_refs(self, name):
        """`git checkout|switch <name>` with no local <name>: git creates it from
        refs/remotes/<remote>/<name> (--guess, the default)."""
        out = []
        for full in (_git(self.root, "for-each-ref", "--format=%(refname)",
                          "refs/remotes/*/" + name) or []):
            parts = full.split("/")
            if len(parts) >= 4 and full == "refs/remotes/%s/%s" % (parts[2], name):
                out.append(full[len("refs/remotes/"):])
        return out


def _ref_candidates(name):
    """Every full ref name git's revision rules may resolve `name` to (gitrevisions(7):
    <name>, refs/<name>, refs/tags/<name>, refs/heads/<name>, refs/remotes/<name>,
    refs/remotes/<name>/HEAD). Matching fetch state against ALL of them covers every
    spelling of a ref (`imp/x`, `heads/imp/x`, `refs/heads/imp/x`, `remotes/r/x`) at once,
    instead of normalizing spellings one by one (merge gate N1-N3)."""
    if name.startswith("refs/"):
        return [name]
    return [name, "refs/" + name, "refs/tags/" + name, "refs/heads/" + name,
            "refs/remotes/" + name, "refs/remotes/%s/HEAD" % name]


def _full_dst(dst):
    """A fetch refspec destination as full ref name(s). git DWIMs a bare destination to a
    branch or a tag (by the source's type): cover both."""
    if dst.startswith("refs/"):
        return [dst]
    return ["refs/heads/" + dst, "refs/tags/" + dst]


def fetch_effects(repo, sub, args, state):
    """Fold one `git fetch` / `git pull` segment into `state`, the record of what later
    segments of the same command must treat as re-pointed (OI-409):
      unresolved -- FULL ref names (and FETCH_HEAD) whose post-fetch value is unknowable;
      prefixes   -- FULL ref-name prefixes re-pointed wholesale: every remote-tracking ref
                    of a LOCAL remote (`refs/remotes/self/`), or a glob destination;
      aliases    -- FETCH_HEAD and network refspec destinations (full names) -> the
                    remote-tracking ref they will equal, judged pre-fetch."""
    pos, post, _vals, flags = _parse_args(sub, list(args))
    pos = pos + post  # fetch/pull take no pathspecs: words after `--` are remote + refspecs
    state["unresolved"].add("FETCH_HEAD")
    if flags & {"--all", "--multiple"}:
        # --all: every remote. --multiple: each word is a remote OR a remote group; a name
        # that is not a configured remote (a group, a path) cannot be ruled out -- local.
        for r in (_git(repo.root, "remote") or []) if ("--all" in flags or not pos) else []:
            if repo.remote_is_local(r):
                state["prefixes"].add("refs/remotes/%s/" % r)
                state["local"] = True
        for r in pos if "--all" not in flags else []:
            if repo.config("remote.%s.url" % r) is None or repo.remote_is_local(r):
                state["prefixes"].add("refs/remotes/%s/" % r)
                state["local"] = True
        return
    br = repo.branch()
    remote = pos[0] if pos else (repo.config("branch.%s.remote" % br) if br else None)
    remote = remote or "origin"
    specs = pos[1:]

    def mark_dsts():
        for spec in specs:
            if ":" in spec:
                dst = spec.lstrip("+").split(":", 1)[1]
                if "*" in dst:
                    # A glob destination (`refs/remotes/gh/*`) re-points every ref under
                    # its prefix: track the prefix, not the literal pattern.
                    state["prefixes"].update(_full_dst(dst.split("*", 1)[0]))
                elif dst:
                    state["unresolved"].update(_full_dst(dst))

    if remote == "." or repo.remote_is_local(remote):
        # A LOCAL fetch can re-point any ref, under any spelling git accepts (prefixes,
        # globs, `heads/`, `^0`, `~0`, `^{commit}`...): matching names one form at a time
        # never converged (merge gate N1-N4). After one, every later write target in the
        # same command is unknowable; the prefixes/unresolved below are kept as detail.
        state["local"] = True
        if remote != "." and repo.config("remote.%s.url" % remote) is not None:
            state["prefixes"].add("refs/remotes/%s/" % remote)
        mark_dsts()
        return
    if sub == "pull":
        return
    configured = repo.config("remote.%s.url" % remote) is not None

    def tracking(src):
        if src.startswith("refs/tags/"):
            return src[len("refs/tags/"):]
        return "%s/%s" % (remote, _strip_refspec(src)) if configured else _UNRESOLVED

    first = None
    i = 0
    while i < len(specs):
        spec = specs[i]
        i += 1
        if spec == "tag" and i < len(specs):
            src, dst = "refs/tags/" + specs[i], None
            i += 1
        else:
            src, _c, dst = spec.lstrip("+").partition(":")
        t = tracking(src) if src else _UNRESOLVED
        if first is None:
            first = t
        if dst:
            for full in _full_dst(dst):
                state["aliases"][full] = t
    if first is None:
        up = repo.upstream_name()
        bremote = repo.config("branch.%s.remote" % br) if br else None
        first = up if (up and bremote == remote) else _UNRESOLVED
    state["aliases"]["FETCH_HEAD"] = first
    state["unresolved"].discard("FETCH_HEAD")


# Pull options this guard can classify with certainty: flags without a value, and the
# value options it consumes. Anything else on a pull command line (an abbreviation other
# than of --rebase/--no-rebase, -S/-j with attached values, options added by a newer git)
# makes the rebase mode UNKNOWN, and the pull is checked as both merge and rebase. Matching
# more spellings one by one never converged (pre-commit review R4/R5).
_PULL_PLAIN_FLAGS = {"-q", "--quiet", "-v", "--verbose", "-n", "--stat", "--no-stat",
                     "--ff", "--no-ff", "--ff-only", "--commit", "--no-commit", "--edit",
                     "--no-edit", "--squash", "--no-squash", "--autostash", "--no-autostash",
                     "--verify", "--no-verify", "--tags", "--no-tags", "--prune", "-p",
                     "--progress", "--no-progress", "--log", "--no-log", "--signoff",
                     "--no-signoff", "--allow-unrelated-histories", "--set-upstream"}
_PULL_SHORT_PLAIN = {"q", "v", "n", "p"}


def _pull_rebase_flag(args):
    """'tree' (rebase) / 'merge' from the LAST of `--rebase[=v]`, `-r[v]` and `--no-rebase`
    on a pull command line, as git reads them (merge gate R3-01: any `--no-rebase` used to
    win); None when none is given; 'unknown' when any option cannot be classified with
    certainty -- callers then check both modes."""
    vopts = _VALUE_OPTS.get("pull", set())
    pre, _post = _split_dashdash(list(args))
    false_words = ("", "false", "no", "off", "0")

    def is_abbrev(name, full, shortest):
        # git accepts any unique prefix of a long option; `--reb`/`--no-reb` are the
        # shortest unambiguous ones for pull (`--re`/`--no-re` are ambiguous and fail).
        return len(name) >= len(shortest) and full.startswith(name)

    last, i = None, 0
    while i < len(pre):
        a = pre[i]
        name, eq, val = a.partition("=")
        if not a.startswith("-") or a == "-":
            pass  # positional
        elif a.startswith("--") and is_abbrev(name, "--no-rebase", "--no-reb") and not eq:
            last = "merge"
        elif a.startswith("--") and is_abbrev(name, "--rebase", "--reb"):
            # `--rebase` alone = true; `--rebase=` (empty) and false words = merge.
            last = "merge" if (eq and val.strip().lower() in false_words) else "tree"
        elif a.startswith("--"):
            if name in vopts:
                if not eq:
                    i += 1  # its value is the next word
            elif name not in _PULL_PLAIN_FLAGS or eq:
                return "unknown"
        else:
            for j in range(1, len(a)):
                c = a[j]
                if c == "r":
                    # `-r` takes an OPTIONAL attached value: the rest of the cluster.
                    rest = a[j + 1:].strip().lower()
                    last = "merge" if (rest and rest in false_words) else "tree"
                    break
                if "-" + c in vopts:
                    if j + 1 == len(a):
                        i += 1  # value is the next word
                    break  # the rest of the cluster is the value
                if c not in _PULL_SHORT_PLAIN:
                    return "unknown"
        i += 1
    return last


def memory_plans(sub, args, repo, fetched=None):
    """[(mode, ref, paths)] -- what this command would write into the worktree.
    'tree':   the worktree becomes ref's tree;            'paths': ref's content for paths;
    'merge':  ref's changes since the merge-base merge in; 'commit': a commit/range applies
              (paths carries the mainline parent number for `-m N`, else None);
    'unresolved': a target that cannot be known NOW -- it comes from a local remote, or
              from a fetch earlier in this same command -- so nothing can be verified.
    `repo` is a _Repo; `fetched` is the fetch_effects state of earlier segments, or None
    when no fetch precedes this segment."""
    every = {}
    pos, post, vals, flags = _parse_args(sub, list(args), every)
    if flags & _STOP_OPS:
        return []

    def target(ref, mode, paths=None, fetchable=True, tree=False):
        """One plan for `ref`, or None (not a ref: git fails or reads it as a path)."""
        ev = ref
        if fetched is not None:
            if fetched.get("local"):
                return ("unresolved", ref, None)
            # Match on the ref's BASE name: `FETCH_HEAD^0`, `x~2`, `t^{commit}` and `x:path`
            # name the same re-pointed ref (merge gate N4).
            if ref.startswith(("@{u}", "@{upstream}")):
                base = "@{u}"
                suffix = ref[len("@{upstream}" if ref.startswith("@{upstream}") else "@{u}"):]
            else:
                base = re.split(r"[~^:]|@\{", ref, 1)[0] or ref
                suffix = ref[len(base):]
            cands = _ref_candidates(base)
            al = next((fetched["aliases"][c] for c in cands if c in fetched["aliases"]), None)
            if al is _UNRESOLVED:
                return ("unresolved", ref, None)
            if al:
                ev = al + suffix
                base = al
                cands = _ref_candidates(al)
            if base in ("@{u}", "@{upstream}"):
                up = repo.upstream_name()
                cands = _ref_candidates(up) if up else []
            if any(c in fetched["unresolved"]
                   or any(c.startswith(p) for p in fetched["prefixes"]) for c in cands):
                return ("unresolved", ref, None)
        if repo.is_treeish(ev) if tree else repo.is_commit(ev):
            return (mode, ev, paths)
        if fetched is not None and fetchable:
            return ("unresolved", ref, None)
        return None

    def switch_target(ref, guess):
        p = target(ref, "tree", fetchable=False)
        if p or not guess:
            return [p] if p else []
        # --guess (the default): no local <ref>, so git creates it from
        # refs/remotes/*/<ref> and writes that tree.
        guessed = repo.dwim_remote_refs(ref)
        if not guessed and fetched is not None and (
                fetched["prefixes"]
                or any(n.endswith("/" + ref) for n in fetched["unresolved"])):
            # A fetch from a LOCAL remote earlier in this command may create
            # refs/remotes/<remote>/<ref> (its own namespace, or a `src:dst` into another
            # remote's), which DWIM would then check out.
            return [("unresolved", ref, None)]
        return [q for q in (target(r, "tree", fetchable=False) for r in guessed) if q]

    def plans(items):
        return [p for p in items if p]

    if sub == "checkout":
        # A new-branch option's value is a NAME; the start point is the next positional.
        if post or "--pathspec-from-file" in flags:
            if not pos:
                return []
            return plans([target(pos[0], "paths", post or _ALL_PATHS, fetchable=False,
                                 tree=True)])
        if not pos:
            return []
        if len(pos) == 1:
            guess = not (flags & {"--no-guess", "-b", "-B", "--orphan", "--detach"})
            return switch_target(pos[0], guess)
        # `checkout <tree-ish> <paths>`; a non-tree-ish first word means paths from index.
        return plans([target(pos[0], "paths", pos[1:], fetchable=False, tree=True)])
    if sub == "switch":
        guess = len(pos) == 1 and not (flags & {"--no-guess", "-c", "-C", "--create",
                                                "--force-create", "--orphan", "-d",
                                                "--detach"})
        out = []
        for r in pos:
            out.extend(switch_target(r, guess))
        return out
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
        return plans([target(src, "paths", paths, fetchable=False, tree=True)])
    if sub == "merge":
        # `-s ours` keeps HEAD's tree exactly: nothing is written.
        strategies = every.get("-s", []) + every.get("--strategy", [])
        if strategies and all(x == "ours" for x in strategies):
            return []
        # Bare `git merge` merges the upstream (merge.defaultToUpstream, on by default).
        return plans([target(r, "merge") for r in (pos or ["@{u}"])])
    if sub == "pull":
        pos = pos + post  # no pathspecs: words after `--` are remote + refspecs
        br = repo.branch()
        implicit = len(pos) <= 1
        remote = pos[0] if pos else (repo.config("branch.%s.remote" % br) if br else None)
        if remote is None:
            return []  # no upstream: git refuses the pull
        if implicit:
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
                elif remote == ".":
                    refs.append(_strip_refspec(src))  # `pull . <branch>`: a local branch
                else:
                    refs.append("%s/%s" % (remote, _strip_refspec(src)))
        last = _pull_rebase_flag(args)
        if last == "unknown":
            modes = ["merge", "tree"]
        elif last is not None:
            modes = [last]
        elif repo.overrides is None:
            modes = ["merge", "tree"]  # config set through the environment: assume either
        else:
            setting = repo.config("branch.%s.rebase" % br) if br else None
            if setting is None:
                setting = repo.config("pull.rebase")
            modes = ["tree"] if (setting or "").strip().lower() in _REBASE_TRUE else ["merge"]
        # A LOCAL remote can serve any old branch: what the pull fetches is unknowable.
        # A network remote (no memory since the purge) is judged by its remote-tracking
        # ref before the fetch; a target that does not resolve yet is unknowable too.
        local_remote = remote != "." and repo.remote_is_local(remote)
        out = []
        for r in refs:
            if local_remote:
                out.append(("unresolved", "%s %s" % (remote, r), None))
                continue
            if not repo.is_commit(r):
                if not implicit:
                    out.append(("unresolved", r, None))
                continue
            # A rebase onto an ancestor of HEAD is usually a no-op, but NOT skipped: HEAD can
            # move between this probe and the command (another session's switch), and many
            # options force a real rebase (merge gate R2-09). A false block here is safe.
            for mode in modes:
                out.append((mode, r, None))
        return out
    if sub == "rebase":
        refs = ([vals["--onto"]] if "--onto" in vals else []) + pos[:2]
        if not refs and "--root" not in flags:
            refs = ["@{u}"]  # bare `git rebase` rebases onto the upstream (fork-point)
        # No "ancestor of HEAD = no-op" skip: see the pull branch above (R2-09).
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
        return plans([target(r, "tree", tree=True) for r in pos])
    return []


_EMPTY_TREE = {"sha1": "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
               "sha256": "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321"}


def memory_hazard(repo, sub, args, fetches=None, overrides=None):
    """Lines naming what this command would write into the local-only memory folder, when
    `repo` is the claude-home repo and local memory exists. [] otherwise or on any doubt
    that is not affirmative evidence (fail-open, like the rest of this guard) -- except a
    target whose content cannot be known before the command runs (a local remote, or a
    fetch earlier in the same command), which cannot be checked at all while local memory
    is at stake (OI-409). `fetches` lists the (sub, args) of earlier fetch/pull segments;
    `overrides` is this segment's `git -c` config (None = set through the environment)."""
    if sub not in MEMORY_SUBS:
        return []
    top = _git(repo, "rev-parse", "--show-toplevel")
    if not top or not _is_claude_home_repo(top[0]):
        return []
    root = top[0]
    if not os.path.isdir(os.path.join(root, *MEMORY_REL.split("/"))):
        return []
    rp = _Repo(root, overrides)
    fetched = None
    for fsub, fargs in (fetches or []):
        fetched = fetched or {"unresolved": set(), "prefixes": set(), "aliases": {},
                              "local": False}
        fetch_effects(_Repo(root, {}), fsub, fargs, fetched)

    mem = MEMORY_REL + "/"
    # When HEAD does not track memory, a change that only DELETES memory writes nothing
    # into the worktree (OI-409 LOW: false block). For a revert the direction flips: a
    # reverted ADDITION is the deletion.
    head_tracks = bool(_git(root, "ls-tree", "--name-only", "HEAD", "--", mem))
    keep = [] if head_tracks else ["--diff-filter=%s" % ("a" if sub == "revert" else "d")]
    out = []
    for mode, ref, paths in memory_plans(sub, args, rp, fetched):
        if mode == "unresolved":
            out.append("%s target %s cannot be known before the command runs (a local "
                       "remote, or a fetch earlier in this command), so it cannot be checked "
                       "for old copies of %s/ -- fetch on its own first, then re-run the %s "
                       "against the fetched ref" % (sub, ref, MEMORY_REL, sub))
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


_PS_ENV_RE = re.compile(r"\$(?:\{env:([A-Za-z_][A-Za-z0-9_()]*)\}|env:([A-Za-z_][A-Za-z0-9_]*))", re.I)
_PS_HOME_RE = re.compile(r"^\$home(?=$|[\\/])", re.I)


def _ps_expand(p):
    """PowerShell `$env:NAME` / `${env:NAME}` / a leading `$HOME` -> their values. An unset
    variable is left as-is, so the path does not resolve (no information)."""
    p = _PS_HOME_RE.sub(lambda m: os.path.expanduser("~").replace("\\", "/"), p)
    return _PS_ENV_RE.sub(lambda m: os.environ.get(m.group(1) or m.group(2), m.group(0)), p)


def _resolve_dir(p, here, dialect="bash"):
    """Real directory for a `cd`/`-C` argument, or None when it cannot be resolved.
    Handles ~, $VARS and Git Bash /c/... paths (PowerShell: also $env:NAME and $HOME).
    None means NO INFORMATION: callers
    must stop probing rather than fall back to a stale directory (REFUTE HIGH: an
    unresolved `cd /c/...` used to probe the OLD cwd and block on ITS state)."""
    if not p:
        return None
    if dialect == "powershell":
        # PowerShell expands only $env:/$HOME/~ here; it reads `/c/x` as `C:\c\x` and
        # leaves %VAR% alone (REFUTE round 3, M1).
        p = os.path.expanduser(_ps_expand(p))
    else:
        p = os.path.expandvars(os.path.expanduser(p))
        if len(p) >= 2 and p[0] == "/" and p[1].isalpha() and (len(p) == 2 or p[2] == "/"):
            p = p[1].upper() + ":/" + p[3:]
    if not os.path.isabs(p):
        if here is None:
            return None  # relative to an unknown directory -> no information
        p = os.path.join(here, p)
    # An ABSOLUTE target resolves even when `here` is unknown (REFUTE round 2, N1: after a
    # popd the guard used to skip `git -C <abs dirty> reset --hard` entirely).
    return p if os.path.isdir(p) else None


def _git_c_dir(seg):
    """Value of `git -C <dir>` in this segment, if any."""
    for i, t in enumerate(seg[:-1]):
        if t == "-C":
            return seg[i + 1]
        if t not in ("git",) and not t.startswith("-") and "=" not in t:
            break
    return None


# PowerShell location changers (names are case-insensitive): Set-Location and its aliases,
# Push-Location and its alias. Pop-Location / popd return to a location this parser does
# not track -> no information.
_PS_CD_NAMES = {"cd", "chdir", "sl", "set-location", "pushd", "push-location"}
_PS_POP_NAMES = {"popd", "pop-location"}
_PS_CD_PATH_PARAMS = {"-path", "-literalpath", "-lp", "-pspath"}
_PS_CD_VALUE_PARAMS = {"-stackname"}
_PS_DASHES = "\u2013\u2014\u2015"  # en dash, em dash, horizontal bar: PowerShell parameter dashes
_BASH_CD_BUILTINS = {"cd", "pushd", "popd"}


# Set-/Push-/Pop-Location parameters: full name -> canonical, and the aliases PowerShell
# matches EXACTLY (an alias is never prefix-matched). Includes the common parameters
# (REFUTE round 3, I3: `Set-Location -ErrorAction Stop <dir>` is a real move).
_PS_PARAM_NAMES = {
    "path": "path", "literalpath": "literalpath", "pspath": "literalpath",
    "passthru": "passthru", "stackname": "stackname",
    "erroraction": "erroraction", "warningaction": "warningaction",
    "informationaction": "informationaction", "progressaction": "progressaction",
    "errorvariable": "errorvariable", "warningvariable": "warningvariable",
    "informationvariable": "informationvariable", "outvariable": "outvariable",
    "outbuffer": "outbuffer", "pipelinevariable": "pipelinevariable",
    "verbose": "verbose", "debug": "debug", "whatif": "whatif", "confirm": "confirm",
}
_PS_PARAM_ALIASES = {
    "lp": "literalpath", "ea": "erroraction", "wa": "warningaction",
    "infa": "informationaction", "proga": "progressaction", "ev": "errorvariable",
    "wv": "warningvariable", "iv": "informationvariable", "ov": "outvariable",
    "ob": "outbuffer", "pv": "pipelinevariable", "vb": "verbose", "db": "debug",
    "wi": "whatif", "cf": "confirm",
}
_PS_PATH_PARAMS = {"path", "literalpath"}
_PS_SWITCH_PARAMS = {"passthru", "verbose", "debug", "whatif", "confirm"}


def _ps_param(token):
    """Canonical parameter for `-Tok` / `-Tok:value` (PowerShell accepts an unambiguous
    prefix of a full name; aliases match exactly), "?" when unknown or ambiguous, None
    when the token is not a parameter at all."""
    if not token.startswith("-") or token in ("-", "+"):
        return None
    name = token[1:].split(":", 1)[0].lower()
    if not name:
        return None
    if name in _PS_PARAM_ALIASES:
        return _PS_PARAM_ALIASES[name]
    if name in _PS_PARAM_NAMES:
        return _PS_PARAM_NAMES[name]
    hits = {canon for full, canon in _PS_PARAM_NAMES.items() if full.startswith(name)}
    return hits.pop() if len(hits) == 1 else "?"


def _cd_target(seg, dialect, mixed=False):
    """Location effect of `seg`: (None, None) when it is not a location command, else:
      ("cd", dir)    -- a move to `dir` (a str)
      ("push", dir)  -- save the current location(s), then move to `dir`
      ("pop", None)  -- return to the last saved location(s)
      ("stay", None) -- a location command with no usable target (bare push, PS7 `cd -`,
                        an unknown/ambiguous parameter ...): nothing to add

    The caller decides what a move MEANS (see _findings_one): only a bash `cd` replaces
    the probed directory; every other move only ADDS one. mixed=True (the tool's shell is
    unknown, the command is also read as PowerShell): the bash reading follows pushd/popd,
    which are real bash builtins, and ignores PowerShell-only names exactly as HEAD did."""
    head = seg[0]
    if dialect != "powershell":
        if head == "cd":
            return "cd", (seg[1] if len(seg) >= 2 else "~")
        if mixed:
            if head == "pushd":
                rest = seg[1:]
                # `pushd -n`, `pushd +N/-N` and a bare `pushd` do not change the directory.
                if not rest or any(x == "-n" or x[:1] in "+-" for x in rest):
                    return "stay", None
                return "push", rest[0]
            if head == "popd":
                return "pop", None
        return None, None
    name = head.lower()
    if name not in _PS_CD_NAMES and name not in _PS_POP_NAMES:
        return None, None
    args = [("-" + x[1:]) if x[:1] in _PS_DASHES else x for x in seg[1:]]
    target = None
    k = 0
    while k < len(args):
        x = args[k]
        if x == "--":  # end of parameters: the next word is positional
            if target is None and k + 1 < len(args):
                target = args[k + 1]
            break
        pname = _ps_param(x)
        if pname is None:
            if x in ("-", "+"):
                return "stay", None  # PS7 location history: not modelled
            if target is None:
                target = x
            k += 1
            continue
        if pname == "?":
            return "stay", None  # unknown/ambiguous parameter
        inline = x.split(":", 1)[1] if ":" in x else None
        if pname in _PS_SWITCH_PARAMS:
            k += 1
            continue
        if pname in _PS_PATH_PARAMS:
            if inline:
                target = inline
                k += 1
            else:  # `-Path <dir>` and `-Path: <dir>`
                if k + 1 < len(args):
                    target = args[k + 1]
                k += 2
            continue
        k += 1 if inline else 2  # a value-taking parameter (-StackName s, -ErrorAction Stop)
    if name in _PS_POP_NAMES:
        return "pop", None
    if target is None:
        return "stay", None  # bare Push-Location stays; bare Set-Location: PS5 stays, PS7 home
    return ("push" if name in ("pushd", "push-location") else "cd"), target


def findings(cmd, cwd, dialects=("bash",)):
    """Hits from reading `cmd` in each dialect, de-duplicated. A non-Bash tool is read both
    ways (git_commit_parse.shell_dialects) and EITHER reading's affirmative evidence counts;
    each reading is still fail-open on its own.

    ORDER (REFUTE rounds 7-9, timeout fail-open): the union-only location tracking costs
    (#location changes x #git commands) probes; if a reading runs past the hook timeout
    the guard fails OPEN. So PASS 0 is the EXACT old reading -- bash rules, mixed=False,
    legacy=True: only `cd` moves, one directory, and once that directory is unknown it
    STAYS unknown and the scan stops, as the old guard's did (round 9: resolving later
    absolute targets there let 1500 `-C` probes after a bad `cd` take 70 s) -- so it finds
    the old guard's hits at the old guard's cost, and a hit there returns at once.
    Every block the old guard made is therefore made in the old time. Only when pass 0
    finds nothing do the wider readings run (bash with pushd/popd, then PowerShell); a
    timeout there can only lose NEW coverage, never an old block.
    RESIDUAL: when pass 0 blocks, hits only a wider reading would add are not listed in
    the block message (the decision is the same; the message is not exhaustive)."""
    out = []
    seen = set()

    def add(hits):
        for hit in hits:
            key = (hit[0], hit[1])
            if key not in seen:
                seen.add(key)
                out.append(hit)

    if "bash" in dialects:
        add(_findings_one(cmd, cwd, "bash", mixed=False, legacy=True))
        if out or len(dialects) == 1:
            return out
    for dialect in sorted(dialects, key=lambda d: d != "bash"):
        if out:
            break
        for hit in _findings_one(cmd, cwd, dialect, mixed=len(dialects) > 1):
            key = (hit[0], hit[1])
            if key not in seen:
                seen.add(key)
                out.append(hit)
    return out


def _union(a, b):
    return a + [x for x in b if x not in a]


def _findings_one(cmd, cwd, dialect, mixed=False, legacy=False):
    try:
        return _findings_one_unguarded(cmd, cwd, dialect, mixed, legacy)
    except Exception:
        return []  # fail open for THIS reading only; the other reading still counts


def _findings_one_unguarded(cmd, cwd, dialect, mixed, legacy=False):
    """Location tracking keeps a LIST of candidate directories; a git command is probed in
    every one of them.

    THE RULE (REFUTE round 4, after four rounds in which every case-by-case attempt to
    FOLLOW a PowerShell location change produced new false allows -- conditional moves after
    `&&`/`||`, parameter-binding errors, untracked pushes, `$` and wildcard targets, Win32
    trailing-dot/space normalisation): only a bash `cd` REPLACES the candidates, exactly as
    at HEAD. Every other location change -- every PowerShell one (Set-Location and aliases,
    including `cd` in the PowerShell reading), push, pop, and the bash reading's pushd/popd --
    only ADDS candidates. HEAD ignored all of those, so this reading's candidates are always
    a superset of HEAD's single directory: it cannot probe less than HEAD did, by
    construction rather than by enumeration.

    COST (deliberate): `Set-Location <clean>; git reset --hard` from a DIRTY cwd still blocks,
    exactly as at HEAD. `git -C <dir> ...` resolves to exactly one directory and is the way
    through; the block message already says so.

    legacy=True (findings() pass 0 only): once the candidate list is empty -- the old
    guard's "directory unknown" -- stop, exactly as the old guard did; the absolute-target
    resolution after an unknown directory (round 2, N1) is left to the wider readings. The
    Bash tool runs only pass 0, so its decisions are the old guard's."""
    out = []
    if dialect == "powershell":
        segs = _parse.tokenize_cmd_segments(cmd, dialect="powershell")
    else:
        segs = _parse.tokenize_cmd_segments(cmd, dialect=dialect)
    heres = [cwd]
    stack = []    # candidate lists saved by pushes; a pop adds the saved list back
    fetches = []  # (sub, args) of fetch/pull segments earlier in this command (OI-409)

    def resolve_all(target, bases):
        new = []
        for base in bases or [None]:
            r = _resolve_dir(target, base, dialect)
            if r is not None and r not in new:
                new.append(r)
        return new

    for seg in segs:
        if legacy and not heres:
            break  # the old guard's unknown directory is sticky: nothing more is probed
        if not seg:
            continue
        kind, target = _cd_target(seg, dialect, mixed)
        if kind:
            if dialect != "powershell" and seg[0] == "cd":
                heres = resolve_all(target, heres)  # HEAD semantics: unresolvable -> nothing
            elif kind in ("cd", "push"):
                if kind == "push":
                    stack.append(list(heres))
                heres = _union(heres, resolve_all(target, heres))
            elif kind == "pop":
                heres = _union(heres, stack.pop() if stack else [])
            continue
        sa = _parse._segment_git_subcommand_and_args(seg)
        if not sa:
            continue
        sub, args = sa
        if sub == "fetch":
            fetches.append((sub, list(args)))
            continue
        words = [a for a in args if not a.startswith("-")] if sub == "remote" else []
        if words and words[0] == "update":
            # `git remote [-v] update [<remote|group>...]` fetches them all (merge gate N5,
            # N7): the subcommand is the first non-option word.
            names = words[1:]
            fetches.append(("fetch", ["--multiple"] + names if names else ["--all"]))
            continue
        cdir = _git_c_dir(seg)
        wheres = []
        for base in heres or [None]:
            w = _resolve_dir(cdir, base, dialect) if cdir else base
            if w is not None and w not in wheres:
                wheres.append(w)  # unresolvable directory -> no information for that base
        c = classify(sub, list(args))
        for where in wheres:
            try:
                mem = memory_hazard(where, sub, list(args), list(fetches),
                                    segment_config(seg))
            except Exception:
                mem = []
            if mem:
                out.append((" ".join(["git", sub] + list(args))[:200], where, mem))
            if not c:
                continue
            try:
                lost = at_risk(where, c[0], c[1])
            except Exception:
                lost = None
            if lost:
                out.append((" ".join(["git", sub] + list(args))[:200], where, lost))
        # The old guard skipped a segment whose directory did not resolve BEFORE recording
        # its pull; pass 0 must too (REFUTE round 10: recording 600 unresolvable `-C x pull`s
        # made every later claude-home probe replay them all -- 60 s, a fail-open).
        if sub == "pull" and (wheres or not legacy):
            fetches.append((sub, list(args)))
    return out


def _safe(text):
    return "".join(ch for ch in str(text) if ch == " " or ch.isprintable())[:400]


# SHELL-TOOL SCOPE (cross-repo audit 2026-11-23, HIGH): PowerShell, Desktop Commander
# start_process / interact_with_process, the terminal panel's run_in_terminal and Windows-MCP
# PowerShell run git just
# like Bash, so this guard judges all of them (dispatcher chain "shell"). The command line is
# read through tool_call_paths.shell_text (interact_with_process carries it in `input`). If that
# lib cannot load, the scope degrades to the previous Bash-only behaviour, never wider.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
    from tool_call_paths import is_git_shell_tool as _is_shell_tool, shell_text as _shell_text  # noqa: E402
except Exception:  # noqa: BLE001
    sys.stderr.write("WARNING (%s, DEGRADED): tool_call_paths did not load -- this guard is "
                     "judging Bash ONLY; PowerShell / Desktop Commander / terminal git is "
                     "UNGUARDED until the lib is fixed.\n" % os.path.basename(__file__))
    def _is_shell_tool(tool_name):
        return tool_name == "Bash"

    def _shell_text(tool_name, tool_input):
        return tool_input.get("command") if isinstance(tool_input, dict) else None


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not _is_shell_tool(payload.get("tool_name")):
        return 0
    cmd = _shell_text(payload.get("tool_name"), payload.get("tool_input") or {}) or ""
    if not cmd or _parse is None:
        return 0
    if not any(w in cmd for w in ("checkout", "restore", "switch", "reset", "clean",
                                   "merge", "pull", "rebase", "cherry-pick", "revert",
                                   "read-tree")):
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    try:
        dialects = _parse.shell_dialects(payload.get("tool_name"))
    except Exception:
        dialects = ("bash",)  # an older parse lib: the previous behaviour, never narrower
    hits = findings(cmd, cwd, dialects)
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
