#!/usr/bin/env python3
"""live-branch-drift-probe.py -- read-only: "which blast-radius files in this
LIVE checkout are behind (or diverged from) origin/main, and what would a
naive one-file sync break?"

WHY (observed 2026-09-13): the primary checkout ~/.claude sat on a long-lived
feature branch (feat/model-canary-probe-step25) 137 commits behind origin/main.
Three push blockers in one day were fixes ALREADY MERGED to main but absent
from the live branch, each rediscovered the hard way:

  1. hooks/tests/test-git-prepush-doctrine-gate-worktree.py was stale.
  2. scheduled-tasks/ora-ground-truth-auditor/SKILL.md existed only as a
     stale UNTRACKED copy, while main tracks a guarded version.
  3. hooks/tests/test-eos-review-gate.py had been synced to main but its
     module under test, hooks/lib/git_commit_parse.py, had not -- and main's
     version imports a NEW module, hooks/lib/git_probe_common.py, missing from
     the branch entirely. A naive one-file sync breaks imports in 4 fail-open
     guard hooks (which then silently skip).

All three were knowable in advance from three trees: working tree, HEAD, base.
This probe reports them before a push does.

Neighbouring tools, deliberately not duplicated:
  * preflight-shared-checkout.py -- "may I edit these paths now?" (its
    LOCAL-ONLY advisory is the mirror image: on-branch-but-not-on-main).
  * checkout-merge-forward.py    -- the corrector for branch drift.
  * check-branch-point.py        -- is a branch cut from a fresh base?

CLASSES (only in-scope paths whose HEAD blob differs from base are examined;
paths identical to base are skipped):
  BEHIND_BASE             changed on base since merge-base, unchanged on HEAD,
                          working tree clean. Includes a deletion on base
                          (flag DELETED_ON_BASE).
  DIVERGED                changed on both sides since merge-base (flag
                          WORKTREE_DIRTY when the working tree is also dirty).
  BASE_ONLY               tracked on base (added or changed there since
                          merge-base), absent from HEAD. Sub-flag
                          UNTRACKED_STALE when an untracked working-tree file
                          sits at that path; `untracked` records whether its
                          blob matches base or ANY historical blob at that path
                          (base and HEAD history).
  LOCAL_DIRTY_OVER_BEHIND a BEHIND_BASE path whose working tree is dirty --
                          foreign WIP; report only. worktree_matches_base
                          distinguishes a hand-sync from real WIP.
Changes made only on HEAD are local work, counted as local_ahead_count, never
drift.

HINTS:
  sync_requires  for a behind .py (any class), its BASE version's module-level
                 imports (ast; into try/if/with, not into def/class) are
                 resolved against hooks/lib and maintenance/_shared; each such
                 sibling that is BASE_ONLY must land in the same sync.
                 also_behind lists siblings that are themselves behind.
  coupling       a test under hooks/tests or maintenance/_tests and its
                 module(s) -- by naming convention and by the test's imports
                 (anywhere in the file) -- in DIFFERENT states, e.g. test
                 SYNCED but module BEHIND_BASE.

DESIGN STANCES:
  * READ-ONLY. The only write is `git fetch` (skip with --no-fetch). Every git
    call runs with --no-optional-locks and a scrubbed GIT_DIR/GIT_WORK_TREE
    env; hash-object is never given -w.
  * Fetch FAILS OPEN: offline or slow (timeout-bounded) is a WARNING and the
    probe runs on the last-fetched ref -- a stale base under-reports drift, it
    never invents it.
  * Batched: up to three `ls-tree -r`, one `status`, one `hash-object
    --stdin-paths`, one `cat-file --batch`, one `log --raw` -- never one
    subprocess per file.
  * The verdict survives a pipe: RESULT_JSON= is always the last line.

Usage:
    python maintenance/live-branch-drift-probe.py
        [--repo PATH]   checkout to inspect (default: ~/.claude)
        [--base REF]    default: origin/main
        [--no-fetch]    skip `git fetch <remote> <branch>`
        [--json]        machine-readable only

Exit codes:
    0  NO_DRIFT   nothing in scope is behind base
    1  DRIFT      at least one drift entry (see RESULT_JSON drift[])
    2  ERROR      not a checkout, git unavailable, base unresolvable, or a
                  tree could not be read
"""
import argparse
import ast
import json
import os
import subprocess
import sys
import time

EXIT_NO_DRIFT = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2

# The blast-radius scope. `**` = any depth (at least one segment below);
# `*` = exactly one path segment. Everything else is literal and root-anchored.
SCOPE_GLOBS = (
    "hooks/**",
    "maintenance/_tests/**",
    "maintenance/*.py",
    "scheduled-tasks/*/SKILL.md",
    "settings.json",
    "CLAUDE.md",
    "agents/**",
)

# Where "sibling module" imports resolve (the sys.path entries hooks and
# maintenance scripts insert for themselves).
SIBLING_MODULE_DIRS = ("hooks/lib", "maintenance/_shared")
TEST_DIRS = ("hooks/tests/", "maintenance/_tests/")

FETCH_TIMEOUT_S = 45
GIT_TIMEOUT_S = 60

C_BEHIND = "BEHIND_BASE"
C_DIVERGED = "DIVERGED"
C_BASE_ONLY = "BASE_ONLY"
C_DIRTY_BEHIND = "LOCAL_DIRTY_OVER_BEHIND"
CLASS_ORDER = (C_DIRTY_BEHIND, C_BASE_ONLY, C_DIVERGED, C_BEHIND)
BEHIND_CLASSES = (C_BEHIND, C_DIVERGED, C_DIRTY_BEHIND)


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------
def _match_segments(pat, segs):
    if not pat:
        return not segs
    head = pat[0]
    if head == "**":
        # ** consumes at least one segment
        return any(_match_segments(pat[1:], segs[i:]) for i in range(1, len(segs) + 1))
    if not segs:
        return False
    if head == "*":
        return bool(segs[0]) and _match_segments(pat[1:], segs[1:])
    if "*" in head:                     # one-segment wildcard, e.g. *.py
        pre, _, post = head.partition("*")
        seg = segs[0]
        return (len(seg) >= len(pre) + len(post) and seg.startswith(pre)
                and seg.endswith(post) and _match_segments(pat[1:], segs[1:]))
    return head == segs[0] and _match_segments(pat[1:], segs[1:])


_SCOPE_PATTERNS = tuple(tuple(gl.split("/")) for gl in SCOPE_GLOBS)


def in_scope(path):
    segs = path.replace("\\", "/").split("/")
    return any(_match_segments(p, segs) for p in _SCOPE_PATTERNS)


def _scope_pathspecs():
    """Top-level pathspecs covering SCOPE_GLOBS, to bound `git status`."""
    return sorted({gl.split("/")[0] for gl in SCOPE_GLOBS})


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------
_GIT_REPO_ENV = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_PREFIX", "GIT_OBJECT_DIRECTORY", "GIT_CEILING_DIRECTORIES",
                 "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_NAMESPACE"}


def _env():
    env = {k: v for k, v in os.environ.items() if k.upper() not in _GIT_REPO_ENV}
    env["GIT_TERMINAL_PROMPT"] = "0"   # an auth prompt must never hang a probe
    env.setdefault("GCM_INTERACTIVE", "never")
    return env


def git(repo, *args, stdin=None, timeout=GIT_TIMEOUT_S, binary=False):
    """Never raises: failures come back as rc 127 so the caller reports ERROR
    with a RESULT_JSON line instead of a traceback."""
    cmd = ["git", "--no-optional-locks", "-C", repo] + list(args)
    try:
        if binary:
            return subprocess.run(cmd, input=stdin, capture_output=True,
                                  timeout=timeout, env=_env())
        return subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, env=_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        empty = b"" if binary else ""
        return subprocess.CompletedProcess(cmd, 127, empty, str(exc))


class ProbeError(Exception):
    pass


def _ok(proc, what):
    if proc.returncode != 0:
        err = proc.stderr
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        raise ProbeError("%s failed: %s" % (what, (err or "").strip()[:300]))
    return proc.stdout


def _rev(repo, ref):
    proc = git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def ls_tree(repo, sha):
    """{path: blob_sha} for every blob in the commit's tree."""
    out = _ok(git(repo, "ls-tree", "-r", "-z", "--full-tree", sha), "ls-tree %s" % sha[:12])
    tree = {}
    for rec in out.split("\0"):
        if not rec or "\t" not in rec:
            continue
        meta, path = rec.split("\t", 1)
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            tree[path] = parts[2]
    return tree


def dirty_tracked(repo):
    """Tracked in-scope-dir paths with staged or unstaged changes (untracked
    files are detected per BASE_ONLY path on disk instead -- that also sees
    an ignored stale copy, which `status` would hide)."""
    proc = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=no",
               "--", *_scope_pathspecs())
    out = _ok(proc, "git status")
    dirty = set()
    fields = out.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if code in ("??", "!!"):
            continue
        dirty.add(path)
        if "R" in code or "C" in code:
            if i < len(fields) and fields[i]:
                dirty.add(fields[i])
            i += 1
    return dirty


def hash_worktree(repo, paths):
    """{path: blob_sha} for existing working-tree files (no -w: never writes)."""
    paths = [p for p in paths if os.path.isfile(os.path.join(repo, p))]
    if not paths:
        return {}
    proc = git(repo, "hash-object", "--stdin-paths", stdin="\n".join(paths) + "\n")
    shas = _ok(proc, "hash-object").split()
    if len(shas) != len(paths):
        raise ProbeError("hash-object returned %d hashes for %d paths" % (len(shas), len(paths)))
    return dict(zip(paths, shas))


def cat_blobs(repo, shas):
    """{sha: bytes} via one `cat-file --batch`."""
    shas = sorted(set(shas))
    if not shas:
        return {}
    proc = git(repo, "cat-file", "--batch", stdin=("\n".join(shas) + "\n").encode("ascii"),
               binary=True)
    data = _ok(proc, "cat-file --batch")
    out, pos = {}, 0
    for _ in shas:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        header = data[pos:nl].decode("ascii", "replace").split()
        pos = nl + 1
        if len(header) < 3 or header[1] == "missing":
            continue
        size = int(header[2])
        out[header[0]] = data[pos:pos + size]
        pos += size + 1
    return out


def historical_blobs(repo, refs, paths):
    """{path: set(blob_sha)} for every version of `paths` in the history of refs."""
    hist = {p: set() for p in paths}
    if not paths:
        return hist
    proc = git(repo, "log", "--format=", "--raw", "--no-abbrev", "--no-renames",
               *refs, "--", *paths)
    for line in _ok(proc, "git log --raw").splitlines():
        if not line.startswith(":") or "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 4 and path in hist:
            for sha in (parts[2], parts[3]):
                if sha.strip("0"):
                    hist[path].add(sha)
    return hist


def do_fetch(repo, base):
    info = {"attempted": False, "ok": None, "remote": None, "branch": None, "detail": None}
    remotes = git(repo, "remote")
    names = set(remotes.stdout.split()) if remotes.returncode == 0 else set()
    remote, _, branch = base.partition("/")
    if not branch or remote not in names:
        info["detail"] = "base %r is not a <remote>/<branch> ref; nothing to fetch" % base
        return info
    info.update(attempted=True, remote=remote, branch=branch)
    # No explicit refspec: `git fetch <remote> <branch>` updates
    # refs/remotes/<remote>/<branch> through the configured refspec.
    proc = git(repo, "fetch", "--quiet", "--no-tags", remote, branch, timeout=FETCH_TIMEOUT_S)
    info["ok"] = proc.returncode == 0
    if not info["ok"]:
        info["detail"] = (proc.stderr or "").strip()[:300] or "rc %d" % proc.returncode
    return info


# --------------------------------------------------------------------------
# python import analysis
# --------------------------------------------------------------------------
def _import_names(tree, full):
    """Candidate short module names imported by `tree`.

    full=False: module-level statements only, descending into if/try/with
    bodies (guarded imports) but never into def/class. full=True: anywhere
    (tests import the module under test inside test functions)."""
    names = set()

    def add(dotted):
        segs = [s for s in (dotted or "").split(".") if s]
        if not segs:
            return
        names.add(segs[0])
        if segs[0] == "lib" and len(segs) > 1:
            names.add(segs[1])

    def visit(node):
        if isinstance(node, ast.Import):
            for a in node.names:
                add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            add(node.module)
            if node.module == "lib":
                for a in node.names:
                    names.add(a.name)

    if full:
        for node in ast.walk(tree):
            visit(node)
        return names

    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        visit(node)
        for field in ("body", "orelse", "finalbody", "handlers"):
            stack.extend(getattr(node, field, None) or [])
    return names


def parse_imports(src_bytes, full):
    """(names:set, error:str|None). Never raises."""
    try:
        tree = ast.parse(src_bytes)
    except (SyntaxError, ValueError) as exc:
        return set(), "%s: %s" % (type(exc).__name__, exc)
    return _import_names(tree, full), None


def sibling_paths(name, trees):
    """Repo paths a short module name resolves to under SIBLING_MODULE_DIRS,
    restricted to paths present in any of `trees`."""
    out = []
    for d in SIBLING_MODULE_DIRS:
        for cand in ("%s/%s.py" % (d, name), "%s/%s/__init__.py" % (d, name)):
            if any(cand in t for t in trees):
                out.append(cand)
    return out


def is_test(path):
    return (path.startswith(TEST_DIRS) and path.endswith(".py")
            and os.path.basename(path).startswith("test"))


def named_counterparts(test_path):
    """Module paths a test is conventionally named after."""
    stem = os.path.basename(test_path)[:-3][4:].lstrip("-_")
    if not stem:
        return []
    dash, under = stem.replace("_", "-"), stem.replace("-", "_")
    if test_path.startswith("hooks/tests/"):
        return ["hooks/%s.py" % dash, "hooks/%s.py" % under,
                "hooks/lib/%s.py" % under, "hooks/lib/%s.py" % dash]
    return ["maintenance/%s.py" % dash, "maintenance/%s.py" % under,
            "maintenance/_shared/%s.py" % under]


# --------------------------------------------------------------------------
# core
# --------------------------------------------------------------------------
def probe(repo, base, fetch):
    t0 = time.time()
    report = {"verdict": None, "repo": repo, "base": base, "scope_globs": list(SCOPE_GLOBS),
              "warnings": [], "fetch": {"attempted": False, "ok": None, "detail": "--no-fetch"}}

    top = git(repo, "rev-parse", "--show-toplevel") if os.path.isdir(repo) else None
    if top is None or top.returncode != 0 or not top.stdout.strip():
        raise ProbeError("not a git checkout (or git unavailable): %s" % repo)
    repo = os.path.normpath(top.stdout.strip())
    report["repo"] = repo

    if fetch:
        f = report["fetch"] = do_fetch(repo, base)
        if f["attempted"] and not f["ok"]:
            report["warnings"].append(
                "fetch %s %s failed (offline?) -- using last-fetched %s, which may"
                " under-report drift: %s" % (f["remote"], f["branch"], base, f["detail"]))

    head = _rev(repo, "HEAD")
    if head is None:
        raise ProbeError("HEAD does not resolve in %s" % repo)
    base_sha = _rev(repo, base)
    if base_sha is None:
        raise ProbeError("base ref %r does not resolve in %s" % (base, repo))
    br = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    mb_proc = git(repo, "merge-base", head, base_sha)
    mb = mb_proc.stdout.strip() if mb_proc.returncode == 0 and mb_proc.stdout.strip() else None
    counts = git(repo, "rev-list", "--left-right", "--count", "%s...%s" % (head, base_sha))
    ahead = behind = None
    if counts.returncode == 0 and len(counts.stdout.split()) == 2:
        ahead, behind = (int(x) for x in counts.stdout.split())
    report.update(head=head, head_branch=br.stdout.strip() if br.returncode == 0 else None,
                  base_sha=base_sha, merge_base=mb, commits_ahead=ahead,
                  commits_behind=behind)
    if mb is None:
        report["warnings"].append("no merge-base between HEAD and %s: every differing"
                                  " path is treated as changed on both sides" % base)

    head_t = ls_tree(repo, head)
    base_t = head_t if base_sha == head else ls_tree(repo, base_sha)
    if mb is None:
        mb_t = {}
    elif mb == head:
        mb_t = head_t
    elif mb == base_sha:
        mb_t = base_t
    else:
        mb_t = ls_tree(repo, mb)
    dirty = dirty_tracked(repo)

    drift, local_ahead = {}, 0
    for path in sorted(set(head_t) | set(base_t)):
        if not in_scope(path):
            continue
        h, b = head_t.get(path), base_t.get(path)
        if h == b:
            continue
        m = mb_t.get(path)
        on_base, on_head = (True, True) if mb is None else (b != m, h != m)
        if not on_base:
            local_ahead += 1            # only HEAD moved: local work, not drift
            continue
        entry = {"path": path, "class": None, "flags": []}
        if h is None:
            entry["class"] = C_BASE_ONLY
            if m is not None:
                entry["flags"].append("DELETED_ON_HEAD")
            if os.path.isfile(os.path.join(repo, path)):
                entry["flags"].append("UNTRACKED_STALE")
        elif on_head:
            entry["class"] = C_DIVERGED
            if path in dirty:
                entry["flags"].append("WORKTREE_DIRTY")
        else:
            entry["class"] = C_DIRTY_BEHIND if path in dirty else C_BEHIND
            if b is None:
                entry["flags"].append("DELETED_ON_BASE")
        drift[path] = entry

    # --- working-tree blobs: dirty-over-behind + untracked-stale ----------
    wt_paths = [p for p, e in drift.items()
                if e["class"] == C_DIRTY_BEHIND or "UNTRACKED_STALE" in e["flags"]]
    wt = hash_worktree(repo, wt_paths)
    stale = [p for p in wt_paths if "UNTRACKED_STALE" in drift[p]["flags"]]
    hist = historical_blobs(repo, [base_sha, head], stale)
    for p in wt_paths:
        e, blob = drift[p], wt.get(p)
        if e["class"] == C_DIRTY_BEHIND:
            e["worktree_matches_base"] = blob is not None and blob == base_t.get(p)
        else:
            e["untracked"] = {"blob": blob,
                              "matches_base": blob is not None and blob == base_t.get(p),
                              "matches_historical_blob": blob is not None and blob in hist[p]}

    def state_of(path):
        """Class of ANY path, in scope or not: a sibling module a behind file
        imports (maintenance/_shared/**) can sit outside SCOPE_GLOBS and still
        be required by the sync."""
        if path in drift:
            return drift[path]["class"]
        h, b = head_t.get(path), base_t.get(path)
        if h is None and b is None:
            return "ABSENT"
        if h == b:
            return "SYNCED"
        m = mb_t.get(path)
        if mb is not None and b == m:
            return "LOCAL_AHEAD"
        if h is None:
            return C_BASE_ONLY
        if mb is None or h != m:
            return C_DIVERGED
        return C_DIRTY_BEHIND if path in dirty else C_BEHIND

    # --- dependency + coupling hints (one cat-file for every blob needed) --
    py_drift = [p for p in drift if p.endswith(".py") and base_t.get(p)]
    need_coupling = any(p.endswith(".py") and p.startswith(("hooks/", "maintenance/"))
                        for p in drift)
    tests_all = sorted(p for p in base_t if is_test(p)) if need_coupling else []
    blobs = cat_blobs(repo, [base_t[p] for p in py_drift] + [base_t[p] for p in tests_all])
    trees = (base_t, head_t)

    for p in py_drift:
        e = drift[p]
        src = blobs.get(base_t[p])
        if src is None:
            names, err = set(), "base blob unreadable"
        else:
            names, err = parse_imports(src, full=False)
        req, also = set(), set()
        for n in names:
            for sib in sibling_paths(n, (base_t,)):
                if sib == p:
                    continue
                st = state_of(sib)
                if st == C_BASE_ONLY:
                    req.add(sib)
                elif st in BEHIND_CLASSES:
                    also.add(sib)
        e["sync_requires"] = sorted(req)
        e["also_behind"] = sorted(also)
        if err:
            e["import_parse_error"] = err

    if need_coupling:
        test_mods = {}
        for t in tests_all:
            mods = {c for c in named_counterparts(t) if any(c in tr for tr in trees)}
            names, _err = parse_imports(blobs.get(base_t[t], b""), full=True)
            for n in names:
                mods.update(sibling_paths(n, trees))
            mods.discard(t)
            test_mods[t] = mods
        for p, e in drift.items():
            if not p.endswith(".py"):
                continue
            coupling = []
            if is_test(p):
                mods = test_mods.get(p)
                if mods is None:     # test absent from base
                    mods = {c for c in named_counterparts(p) if any(c in tr for tr in trees)}
                for mpath in sorted(mods):
                    st = state_of(mpath)
                    if st not in ("ABSENT", e["class"]):
                        coupling.append({"counterpart": mpath, "relation": "module", "state": st})
            elif p.startswith(("hooks/", "maintenance/")):
                for t in tests_all:
                    if p in test_mods[t]:
                        st = state_of(t)
                        if st not in ("ABSENT", e["class"]):
                            coupling.append({"counterpart": t, "relation": "test", "state": st})
            if coupling:
                e["coupling"] = coupling

    entries = sorted(drift.values(), key=lambda d: (CLASS_ORDER.index(d["class"]), d["path"]))
    class_counts = {c: 0 for c in CLASS_ORDER}
    for d in entries:
        class_counts[d["class"]] += 1
    report.update(drift=entries, counts=class_counts, local_ahead_count=local_ahead,
                  verdict="DRIFT" if entries else "NO_DRIFT",
                  elapsed_s=round(time.time() - t0, 2))
    return report


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def human(report):
    out = []
    say = out.append
    say("LIVE-BRANCH DRIFT %s -- %s" % (report["verdict"], report.get("repo")))
    if report["verdict"] == "ERROR":
        say("  error: %s" % report.get("error"))
        return out
    say("  HEAD   : %s @ %s  (%s ahead / %s behind %s)"
        % (report.get("head_branch"), (report.get("head") or "")[:12],
           report.get("commits_ahead"), report.get("commits_behind"), report["base"]))
    say("  base   : %s @ %s   merge-base %s"
        % (report["base"], (report.get("base_sha") or "")[:12],
           (report.get("merge_base") or "NONE")[:12]))
    f = report["fetch"]
    if not f["attempted"]:
        say("  fetch  : not attempted (%s)" % f.get("detail"))
    else:
        say("  fetch  : %s %s -> %s" % (f["remote"], f["branch"], "ok" if f["ok"] else "FAILED"))
    for w in report["warnings"]:
        say("  WARNING: %s" % w)
    for cls in CLASS_ORDER:
        rows = [d for d in report["drift"] if d["class"] == cls]
        if not rows:
            continue
        say("")
        say("  %s (%d):" % (cls, len(rows)))
        for d in rows:
            tail = "  [%s]" % ", ".join(d["flags"]) if d["flags"] else ""
            if "worktree_matches_base" in d:
                tail += ("  (working tree already matches base)" if d["worktree_matches_base"]
                         else "  (foreign WIP -- report only)")
            u = d.get("untracked")
            if u:
                tail += "  (untracked copy: %s)" % (
                    "matches base" if u["matches_base"] else
                    "matches an older version" if u["matches_historical_blob"] else
                    "matches no known version")
            say("      %s%s" % (d["path"], tail))
            if d.get("sync_requires"):
                say("          sync requires: %s" % ", ".join(d["sync_requires"]))
            if d.get("also_behind"):
                say("          imports also behind: %s" % ", ".join(d["also_behind"]))
            if d.get("import_parse_error"):
                say("          (base imports not parsed: %s)" % d["import_parse_error"][:80])
            me = "test" if is_test(d["path"]) else "module"
            for c in d.get("coupling", []):
                st = "synced" if c["state"] == "SYNCED" else c["state"]
                say("          coupling: %s %s but %s %s -- %s"
                    % (c["relation"], st, me, d["class"], c["counterpart"]))
    say("")
    say("  summary: %s; local-ahead (not drift): %d; %.2fs"
        % (", ".join("%s=%d" % (c, n) for c, n in report["counts"].items()),
           report["local_ahead_count"], report.get("elapsed_s") or 0))
    if report["verdict"] == "DRIFT":
        say("  -> drift found. Sync each path together with its 'sync requires' modules"
            " and coupled tests/modules (checkout-merge-forward.py, or a worktree).")
    else:
        say("  -> no blast-radius drift against %s." % report["base"])
    return out


def emit(report, as_json):
    if as_json:
        sys.stdout.write(json.dumps(report, indent=1) + "\n")
        return
    for line in human(report):
        sys.stdout.write(line + "\n")
    sys.stdout.write("RESULT_JSON=" + json.dumps(report) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read-only live-branch vs base blast-radius drift probe.")
    ap.add_argument("--repo", default=os.path.join(os.path.expanduser("~"), ".claude"))
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    repo = os.path.abspath(os.path.expanduser(args.repo))
    try:
        report = probe(repo, args.base, fetch=not args.no_fetch)
    except ProbeError as exc:
        report = {"verdict": "ERROR", "repo": repo, "base": args.base, "error": str(exc),
                  "scope_globs": list(SCOPE_GLOBS)}
        emit(report, args.json)
        return EXIT_ERROR
    emit(report, args.json)
    return EXIT_DRIFT if report["verdict"] == "DRIFT" else EXIT_NO_DRIFT


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


if __name__ == "__main__":
    _utf8_stdout()
    sys.exit(main())
