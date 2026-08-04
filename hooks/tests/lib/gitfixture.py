#!/usr/bin/env python3
"""Shared throwaway-git-repo fixture for the hook/maintenance test suites.

WHY (open-items-tracker.md#OI-061): 13 test files each hand-rolled their own repo
fixture at ~5 process spawns per repo (`git init` + 2x `git config` + `git add` +
`git commit`). Measured 2026-08-03: test-eos-review-gate.py alone paid 365 of its 559
spawns there (73 runtime make_repo() calls), running 44-67s idle but 141.7s under real
multi-session load -- i.e. OVER the pre-push gate's 90s per-file budget. The
second-worst file sat at 51% of budget with nothing pathological about it, so this was
a wall the next growing file would hit too.

HOW: build each distinct repo shape ONCE per test process, then `shutil.copytree` it
per call. A git repo is self-contained -- the object store, refs and config all live
under .git/ and `git init` writes no absolute paths into them -- so a copied repo is
functionally identical to a freshly-inited one, at zero subprocess cost. First call for
a given shape pays the ~5 spawns; every later call pays none.

DELIBERATELY SMALL. This is the verification layer for security gates: 13 test files
depending on one fixture makes that fixture a single point of failure, and a fixture
that silently produced a subtly different repo (missing user config, different default
branch, no initial commit) would let tests pass while no longer exercising what they
claim. So: no cleverness, no lazy-deleting, no shared mutable state between callers,
and every invariant asserted in test-gitfixture.py. If you need a new repo shape, add
a named function -- do not add flags to an existing one.

CONTRACT: every returned path is a fresh directory the caller owns and may mutate
freely; callers are responsible for cleanup exactly as they were before (most of these
suites intentionally leak into %TEMP% and let the OS reap it).
"""
import os
import shutil
import subprocess
import tempfile

__all__ = ["blank_repo", "repo_with_commit", "git", "spawn_count", "reset_cache",
           "DEFAULT_IDENTITY"]

# (user.email, user.name) baked into a template's local config. NOT a house style to
# normalise on: the suites using this fixture legitimately differ -- "t@t.t" here,
# "t@example.invalid" and "t@t" elsewhere -- and author identity lands in commit
# metadata, so silently rewriting a caller's identity is exactly the kind of
# looks-right-but-differs change this module exists to avoid. Pass what your original
# hand-rolled fixture passed; it is part of the cache key so two identities never share
# a template. (open-items-tracker.md#OI-072)
DEFAULT_IDENTITY = ("t@t.t", "t")

# Template cache: shape-key -> path of the pristine template repo for that shape.
_TEMPLATES = {}
# Number of real subprocesses this module has spawned; asserted by its own test so a
# regression back to per-call spawning is caught mechanically, not by eye.
_SPAWNS = 0


def _run(args, cwd=None):
    global _SPAWNS
    _SPAWNS += 1
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(repo, *args):
    """Run a git command in `repo`. Mirrors the per-file `git()` helpers it replaces."""
    return _run(["git", "-C", repo] + list(args))


def spawn_count():
    """Subprocesses spawned by this module so far this process."""
    return _SPAWNS


def _must(proc, what):
    """Fail LOUDLY and locally if a template-build git command failed.

    Without this a failing git (missing binary, full disk, leaked GIT_* env) yields a
    silently broken template, and the damage surfaces later as unrelated-looking
    assertion failures in whichever suite happens to use that shape -- fail-closed, so
    no gate can be bypassed, but the diagnosis points at the wrong file. The hand-rolled
    fixtures this replaces asserted on their git calls; keep that.
    """
    if proc.returncode != 0:
        raise RuntimeError("gitfixture: template build failed at %s: %s"
                           % (what, (proc.stderr or proc.stdout or "").strip()[:300]))
    return proc


def _build_template(key, files, message, newline, encoding, identity):
    """Create the pristine template for a shape. Called at most once per shape."""
    email, name = identity
    tpl = tempfile.mkdtemp(prefix="gitfixture-tpl-")
    _must(_run(["git", "init", "-q", tpl]), "init")
    _must(git(tpl, "config", "user.email", email), "config user.email")
    _must(git(tpl, "config", "user.name", name), "config user.name")
    if files:
        for rel, text in files.items():
            path = os.path.join(tpl, rel)
            parent = os.path.dirname(path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            with open(path, "w", encoding=encoding, newline=newline) as fh:
                fh.write(text)
        _must(git(tpl, "add", "-A"), "add")
        _must(git(tpl, "commit", "-q", "-m", message), "commit")
    # Cached only on success -- a failed build must not poison later calls.
    _TEMPLATES[key] = tpl
    return tpl


def _clone_template(key, files, message, prefix, newline, encoding, identity, dest):
    tpl = (_TEMPLATES.get(key) or
           _build_template(key, files, message, newline, encoding, identity))
    if dest is None:
        dest = tempfile.mkdtemp(prefix=prefix)
    # dest already exists (mkdtemp, or the caller's own dir); copytree needs it absent
    # or dirs_exist_ok. Materialising INTO a caller's dir keeps that caller's own
    # lifetime management -- e.g. a `with tempfile.TemporaryDirectory() as d:` block
    # that auto-deletes -- which returning a fresh path would silently break.
    shutil.copytree(tpl, dest, dirs_exist_ok=True)
    return dest


def blank_repo(prefix="gitfixture-blank-", identity=DEFAULT_IDENTITY, dest=None):
    """An initialised repo with user config and NO commits (git init + 2x config).

    `identity` is (user.email, user.name) and is part of the cache key -- see
    repo_with_commit's docstring for why it must mirror the caller's original.
    `dest`, if given, materialises the repo INTO that existing directory and returns
    it, instead of creating a new temp dir.
    """
    return _clone_template(("__blank__", identity), None, None, prefix,
                           "\n", "utf-8", identity, dest)


def repo_with_commit(files=None, message="init", prefix="gitfixture-repo-",
                     newline="\n", encoding="utf-8", identity=DEFAULT_IDENTITY,
                     dest=None):
    """An initialised repo with `files` committed. Default: one README.md.

    `newline` is passed straight to open() and MUST match what the caller's original
    hand-rolled fixture used, because it changes the committed bytes: "\\n" writes
    literal LF (what a fixture with an explicit newline="\\n" produced), while None
    applies Python's default translation, i.e. CRLF on Windows. Getting this wrong
    yields a repo that looks right but whose files differ byte-for-byte from what the
    test used to assert against -- the exact silent-difference failure this module's
    docstring warns about. It is part of the cache key for the same reason.

    `encoding` likewise mirrors the caller's original. It matters less for bytes (every
    current fixture string is ASCII) than for FAIL-FAST behaviour: a caller whose
    hand-rolled fixture used encoding="ascii" got a UnicodeEncodeError the moment
    someone added a smart quote to a fixture string, and silently committing UTF-8
    instead would lose that signal. Pass what the original passed. Also in the key.
    """
    if files is None:
        files = {"README.md": "hello\n"}
    key = repr((tuple(sorted(files.items())), message, newline, encoding, identity))
    return _clone_template(key, files, message, prefix, newline, encoding,
                           identity, dest)


def reset_cache():
    """Drop cached templates (test-only; forces the next call to rebuild)."""
    _TEMPLATES.clear()
