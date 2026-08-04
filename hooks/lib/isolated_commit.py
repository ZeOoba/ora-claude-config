#!/usr/bin/env python3
"""Stage an exact-text-replacement hunk into the git INDEX only, leaving any
OTHER uncommitted changes to the same file untouched in the working tree.

WHY (2026-08-04, open-items-tracker.md OI-061/OI-072 session): that tracker file
collides constantly -- multiple sessions land corrections to it in the same
evening, and a plain `git add <file> && git commit` sweeps up whatever ELSE is
sitting uncommitted in the working copy, silently committing another session's
in-progress edit under your name (or, worse, before it's ready). The fix used by
hand three times in one session: diff HEAD's committed version against
HEAD-with-your-change-applied, and `git apply --cached` just that diff -- the
working tree (and everyone else's uncommitted edits in it) is never touched. This
module mechanizes that, replacing a manual sed-based path-retargeting step that
is the single easiest part of the technique to get subtly wrong under time
pressure.

HOW the header-path trick works: `git apply` expects a patch whose header paths
already read "a/<repo-relative-path>" / "b/<repo-relative-path>" (with the
default -p1). Rather than diffing two arbitrarily-named temp files and then
string-replacing their paths in the resulting patch text, this builds the diff
from two temp files that are ALREADY NAMED "a/<rel_path>" and "b/<rel_path>"
(relative to a scratch cwd) -- so the header paths come out correct straight out
of `git diff --no-index`, with no post-processing and nothing to get wrong.

HARDENED after independent review (2026-08-04, claude-fable-5) found this module's
FIRST version had two real silent-failure modes, both now closed:
  * `repo_root` not the actual toplevel -> `git apply` resolves patch paths
    relative to cwd and silently drops paths outside it, so "stage, then
    commit" could stage NOTHING while printing success. Fixed by resolving
    `--show-toplevel` up front and, belt-and-braces, verifying post-apply that
    the index actually changed to `new_content`.
  * Another session's edit already STAGED (not just working-tree-dirty) for
    the same file was silently merged into the patch if its context happened
    to overlap, because nothing checked the index against `ref` first. Fixed
    by requiring the index entry for `rel_path` to exactly equal `ref`'s
    content before touching anything.
The same review also found the original comment claiming git blobs are
"always \\n-normalized internally" was flatly wrong -- git stores whatever
bytes were committed, so a CRLF-committed file kept CRLF, and a naive
text-mode read/write pair silently rewrote its line endings. Fixed by reading
`git show` output as raw bytes and decoding without universal-newline
translation, so the reconstructed content matches the blob byte-for-byte.

Stdlib only. Windows (`python`).
"""
import os
import shutil
import subprocess
import sys
import tempfile

# Scrubbed in both this module's and worktree_cleanup_check.py's _run(): git
# exports these to hook subprocesses, and this module lives under hooks/lib.
# An inherited GIT_DIR would silently redirect every git call here at whatever
# repo that variable names instead of `repo_root` -- same hazard documented in
# hooks/tests/*.py's identical scrub, just at the library layer instead of the
# test layer (2026-08-04 independent review, minor note 3).
_GIT_ENV_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_PREFIX")


def _clean_env():
    env = dict(os.environ)
    for v in _GIT_ENV_VARS:
        env.pop(v, None)
    return env


def _run(args, cwd=None):
    # encoding="utf-8" is NOT optional here: text=True alone defaults to the
    # OS locale codepage (cp1252 on this Windows machine), which cannot decode
    # this repo's actual UTF-8 prose (em dashes, curly quotes are everywhere in
    # open-items-tracker.md, the primary target of this module). Found live:
    # a cp1252 decode failure crashed the reader thread and silently left
    # p.stdout as None rather than raising into this function, so the FIRST
    # symptom was an unrelated-looking AttributeError three calls downstream --
    # errors="strict" (the default) is kept deliberately so a genuine encoding
    # mismatch still fails loudly instead of silently mangling bytes.
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", env=_clean_env())


def _toplevel(repo_root):
    """The actual repo toplevel for `repo_root`. `git apply` resolves patch
    paths relative to the CURRENT DIRECTORY, and when that directory is a
    subdirectory of the repo, silently ignores (does not error on) any
    patched path outside it -- so calling from anywhere but the toplevel can
    stage nothing while every git command still exits 0. Normalizing here,
    once, up front, is cheaper and more robust than trying to path-adjust
    every subsequent call."""
    p = _run(["git", "rev-parse", "--show-toplevel"], cwd=repo_root)
    if p.returncode != 0:
        raise RuntimeError("isolated_commit: %s is not inside a git repo -- %s" % (
            repo_root, (p.stderr or "").strip()[:300]))
    # git always reports the toplevel with forward slashes, even on Windows;
    # os.path.normpath restores the native separator so later os.path.join
    # calls behave the same as everywhere else in this module.
    return os.path.normpath(p.stdout.strip())


def _show_bytes(repo_root, ref, rel_path):
    """Raw bytes of `rel_path` at `ref`, exactly as stored in the git object
    -- NOT decoded through a text-mode pipe, which would apply universal-
    newline translation and silently turn a CRLF-committed blob's \\r\\n into
    bare \\n. Raises if the ref or path does not resolve."""
    p = subprocess.run(["git", "show", "%s:%s" % (ref, rel_path)],
                       cwd=repo_root, capture_output=True, env=_clean_env())
    if p.returncode != 0:
        raise RuntimeError("isolated_commit: cannot read %s:%s -- %s" % (
            ref, rel_path, (p.stderr or b"").decode("utf-8", "replace").strip()[:300]))
    return p.stdout


def _show(repo_root, ref, rel_path):
    """Content of `rel_path` at `ref`, exactly as committed (line endings
    preserved -- see `_show_bytes`). Silently treating a missing file as
    empty content would let a caller "isolate" a hunk against nothing and
    stage a patch that adds the file wholesale instead of the intended
    targeted edit -- `_show_bytes` already raises for that."""
    return _show_bytes(repo_root, ref, rel_path).decode("utf-8")


def build_replacement(base_content, old_text, new_text):
    """The new file content, plus a sanity check that `old_text` appears
    EXACTLY once. Two or zero matches both raise: two means the replacement
    is ambiguous (which occurrence?), zero means the caller's old_text no
    longer matches -- e.g. the file moved on since it was last read -- and
    silently no-op'ing would report success while staging nothing.
    old_text == new_text is also rejected explicitly (rather than left to
    fail confusingly three steps later inside `git diff --no-index`, whose
    "no difference" case looks identical to a real failure from the outside)."""
    if old_text == new_text:
        raise ValueError("isolated_commit: old_text and new_text are identical "
                         "-- nothing to replace")
    count = base_content.count(old_text)
    if count != 1:
        raise ValueError(
            "isolated_commit: old_text found %d times in the target, expected "
            "exactly 1" % count)
    return base_content.replace(old_text, new_text, 1)


def _assert_index_matches_ref(repo_root, ref, rel_path):
    """Refuse to proceed if the CURRENT INDEX for `rel_path` differs from
    `ref`'s content -- i.e. something is already staged for this file (most
    plausibly another session's in-progress `git add`, mid-edit, in this same
    shared checkout). Applying a patch built against `ref` on top of a
    DIFFERENT staged base can succeed (context lines may still match nearby)
    while silently merging that other content into the result -- caught by
    independent review, reproduced live. `git show :<path>` reads the INDEX
    (no ref prefix); comparing byte-for-byte against `_show_bytes(ref, ...)`
    catches even a whitespace-only staged difference."""
    p = subprocess.run(["git", "show", ":%s" % rel_path], cwd=repo_root,
                       capture_output=True, env=_clean_env())
    if p.returncode != 0:
        raise RuntimeError(
            "isolated_commit: cannot read the INDEX version of %s -- %s "
            "(is it tracked and staged as expected?)" % (
                rel_path, (p.stderr or b"").decode("utf-8", "replace").strip()[:300]))
    index_bytes = p.stdout
    ref_bytes = _show_bytes(repo_root, ref, rel_path)
    if index_bytes != ref_bytes:
        raise RuntimeError(
            "isolated_commit: refusing to stage -- the INDEX for %s already "
            "differs from %s. Something else is already staged for this file "
            "(possibly another session's in-progress `git add`); layering a "
            "patch on top of it risks silently sweeping that content into "
            "your commit. Resolve or unstage it first." % (rel_path, ref))


def _assert_no_other_staged_changes(repo_root, ref, rel_path, allow_other_staged_paths):
    """Refuse to proceed if any path OTHER than `rel_path` is staged relative
    to `ref` -- e.g. another session ran `git add other.md` before this call.

    WHY (delta review, 2026-08-04, C3 -- found AFTER `_assert_index_matches_ref`
    was believed to close this class): that check only guards `rel_path`
    itself. Reproduced live: another session stages `other.md`; this function's
    caller stages an isolated hunk in `doc.md`; both succeed with no warning;
    the documented finish step (`git commit`) then commits BOTH files under
    the caller's message, silently sweeping the other session's in-progress
    work in -- the exact harm this module's own WHY paragraph names, via a
    different path than the one already guarded. `git commit -- rel_path`
    is NOT a safe workaround to suggest instead: a pathspec commit takes
    WORKING-TREE content for that path, not the isolated INDEX content this
    module just staged, so it would not even commit the intended change.

    `allow_other_staged_paths=True` is the explicit, named opt-out for a
    caller that is deliberately staging several files before one commit and
    therefore already owns the whole staged set -- never a silent default.

    Compares staged paths against HEAD, NOT `ref` (final delta review, minor
    note 1): when `ref` is an older commit, diffing the index against `ref`
    lists every file touched by commits BETWEEN `ref` and HEAD too, even
    though those are already committed, not staged -- a false positive that
    misattributes ordinary history to "another session's in-progress `git
    add`". "What's actually staged right now" is always index-vs-HEAD,
    independent of which ref this call happens to be reading content from.

    -c core.quotepath=false (final delta review, minor note 2): without it, a
    non-ASCII path in `--name-only` output is octal-quoted
    ("\\317\\200.md"), which would never equal the literal `rel_path` and
    could self-refuse on its own target file."""
    if allow_other_staged_paths:
        return
    p = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--cached",
                        "--name-only", "HEAD"],
                       cwd=repo_root, capture_output=True, env=_clean_env())
    if p.returncode != 0:
        raise RuntimeError(
            "isolated_commit: could not enumerate staged paths -- %s" %
            (p.stderr or b"").decode("utf-8", "replace").strip()[:300])
    staged_paths = {line.strip() for line in
                    p.stdout.decode("utf-8", "replace").splitlines() if line.strip()}
    others = staged_paths - {rel_path}
    if others:
        raise RuntimeError(
            "isolated_commit: refusing to stage -- %d other path(s) are ALSO "
            "staged relative to %s: %s. Committing now would sweep them in "
            "under your message too (possibly another session's in-progress "
            "`git add`). Pass allow_other_staged_paths=True only if you "
            "deliberately intend to commit that whole staged set." % (
                len(others), ref, ", ".join(sorted(others))[:300]))


def stage_isolated_replacement(repo_root, rel_path, old_text, new_text, ref="HEAD",
                               allow_other_staged_paths=False):
    """Stage, into the INDEX ONLY, the change that turns `ref`'s committed
    version of `rel_path` from `old_text` to `new_text` (exactly one
    occurrence). Any uncommitted working-tree changes to this file -- from
    this session or another -- are left exactly as they were; only a `git
    commit` (run separately, by the caller) turns this into a real commit.

    Preconditions enforced before anything is written: the INDEX for
    `rel_path` must already exactly match `ref` (see `_assert_index_matches_ref`),
    NO OTHER path may already be staged relative to `ref` unless the caller
    explicitly passes `allow_other_staged_paths=True` (see
    `_assert_no_other_staged_changes` -- otherwise a subsequent `git commit`
    would sweep that other file in too), and after applying, the INDEX must
    actually equal `new_content` (belt and braces against `repo_root`/cwd
    path-resolution surprises -- see `_toplevel`'s docstring). Raises
    ValueError (bad old_text match) or RuntimeError (a precondition or git
    command failed) on failure. Never touches the working tree either way.
    """
    repo_root = _toplevel(repo_root)
    rel_path_norm = rel_path.replace("\\", "/")
    _assert_index_matches_ref(repo_root, ref, rel_path_norm)
    _assert_no_other_staged_changes(repo_root, ref, rel_path_norm, allow_other_staged_paths)
    base_content = _show(repo_root, ref, rel_path_norm)
    new_content = build_replacement(base_content, old_text, new_text)

    scratch = tempfile.mkdtemp(prefix="isolated-commit-")
    try:
        a_path = os.path.join(scratch, "a", rel_path_norm)
        b_path = os.path.join(scratch, "b", rel_path_norm)
        os.makedirs(os.path.dirname(a_path), exist_ok=True)
        os.makedirs(os.path.dirname(b_path), exist_ok=True)
        # newline="": write exactly the characters in base_content/new_content
        # (already exact-byte-preserved by `_show`/`_show_bytes` -- CRLF stays
        # CRLF, LF stays LF) with NO further translation, so the resulting
        # patch's context matches the INDEX's stored bytes exactly regardless
        # of this file's line-ending convention.
        with open(a_path, "w", encoding="utf-8", newline="") as f:
            f.write(base_content)
        with open(b_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)

        # --src-prefix=/--dst-prefix= MUST be empty: --no-index prepends its own
        # "a/"/"b/" by default, which would double up with the "a/"/"b/" already
        # baked into a_path/b_path's names (diff --git a/a/<rel> b/b/<rel> --
        # caught by this module's own test, not assumed).
        #
        # -c core.autocrlf=false is NOT optional: `git diff --no-index` consults
        # the GLOBAL core.autocrlf setting even though `scratch` is not inside
        # any git repo, and on a machine with autocrlf=true (this one) it
        # silently strips \r from the generated hunks -- so a_path/b_path's
        # carefully byte-preserved CRLF content produces an LF-only patch,
        # which then either fails `git apply --cached` outright (context
        # mismatch against the real CRLF index) or, worse, could succeed and
        # silently rewrite the file's line endings.
        #
        # Captured as RAW BYTES, not via `_run()` (text=True): text=True's
        # universal-newline translation happens on the READ side of the pipe
        # too, not just decoding -- so even with the autocrlf fix above, a
        # text-mode capture of this subprocess's stdout would ITSELF silently
        # convert \r\n to \n before the patch ever reaches disk. Both of these
        # were caught live while writing this module's own CRLF regression
        # test, in sequence -- fixing the first (autocrlf) was not sufficient
        # on its own, which is exactly why the test exists rather than trusting
        # the fix by inspection.
        diff = subprocess.run(
            ["git", "-c", "core.autocrlf=false", "diff", "--no-index",
            "--src-prefix=", "--dst-prefix=", "--",
            "a/%s" % rel_path_norm, "b/%s" % rel_path_norm],
            cwd=scratch, capture_output=True, env=_clean_env())
        # --no-index exits 1 for "found a difference" (expected -- that's the
        # whole point) and 0 only for "no difference", which cannot happen
        # here since build_replacement() already required old_text != new
        # content. Any OTHER exit code means something actually went wrong.
        if diff.returncode not in (0, 1) or not diff.stdout.strip():
            raise RuntimeError("isolated_commit: git diff --no-index failed -- %s" %
                               (diff.stderr or b"").decode("utf-8", "replace").strip()[:300])
        patch_path = os.path.join(scratch, "patch.diff")
        with open(patch_path, "wb") as f:
            f.write(diff.stdout)

        check = _run(["git", "apply", "--cached", "--check", patch_path], cwd=repo_root)
        if check.returncode != 0:
            raise RuntimeError(
                "isolated_commit: patch does not apply cleanly to the index -- "
                "the file likely changed since `ref` (%s). git says: %s" % (
                    ref, (check.stderr or "").strip()[:500]))
        apply_ = _run(["git", "apply", "--cached", patch_path], cwd=repo_root)
        if apply_.returncode != 0:
            raise RuntimeError("isolated_commit: git apply --cached failed -- %s" %
                               (apply_.stderr or "").strip()[:500])

        # Post-apply verification (independent review, C1): confirm the INDEX
        # actually changed to `new_content` rather than trusting exit codes
        # alone. Every command above can legitimately exit 0 while having
        # touched nothing if `repo_root` were still wrong for some reason
        # `_toplevel` did not anticipate -- this is the backstop.
        staged_bytes = subprocess.run(
            ["git", "show", ":%s" % rel_path_norm], cwd=repo_root,
            capture_output=True, env=_clean_env()).stdout
        if staged_bytes.decode("utf-8", "replace") != new_content:
            raise RuntimeError(
                "isolated_commit: git apply --cached reported success, but the "
                "INDEX does not actually contain the expected new content -- "
                "refusing to report success. Do not run `git commit`; the "
                "index may be in an unexpected state.")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    import argparse  # lazy: CLI-only, matches claim_work.py's convention
    p = argparse.ArgumentParser(
        description="Stage an exact old-text -> new-text replacement into the "
                     "git index only, without touching other uncommitted "
                     "changes to the same file. Run `git commit` yourself "
                     "afterward -- this only stages.")
    p.add_argument("rel_path", help="Repo-relative path to the file")
    p.add_argument("--old", required=True,
                   help="Path to a file containing the exact old text (read "
                        "byte-for-byte, no newline translation, so its line "
                        "endings must match the target file's)")
    p.add_argument("--new", required=True,
                   help="Path to a file containing the exact new text (same "
                        "byte-for-byte rule as --old)")
    p.add_argument("--repo-root", default=".", help="Repo root (default: cwd)")
    p.add_argument("--ref", default="HEAD", help="Ref to diff against (default: HEAD)")
    p.add_argument("--allow-other-staged", action="store_true",
                   help="Allow proceeding even if paths OTHER than rel_path are "
                        "already staged relative to --ref. Default refuses (delta "
                        "review, C3): the documented finish step is `git commit`, "
                        "which would sweep any other staged file in under your "
                        "message too. Only pass this if you deliberately intend "
                        "to commit that whole staged set.")
    args = p.parse_args()

    # newline="": read --old/--new exactly as written, matching the
    # byte-for-byte discipline the library now uses throughout -- a text-mode
    # read here would silently normalize CRLF in the caller's own files,
    # reintroducing the class of bug this module was just hardened against.
    with open(args.old, encoding="utf-8", newline="") as f:
        old_text = f.read()
    with open(args.new, encoding="utf-8", newline="") as f:
        new_text = f.read()

    try:
        stage_isolated_replacement(os.path.abspath(args.repo_root), args.rel_path,
                                   old_text, new_text, ref=args.ref,
                                   allow_other_staged_paths=args.allow_other_staged)
    # UnicodeDecodeError added (delta review): `_show`'s strict utf-8 decode of a
    # non-UTF-8 blob previously escaped this catch and surfaced as a raw
    # traceback instead of the clean ERROR: path every other failure mode uses.
    except (ValueError, RuntimeError, UnicodeDecodeError) as e:
        print("ERROR: %s" % e)
        return 1
    print("Staged isolated replacement in %s (against %s). Working tree "
          "untouched -- run `git commit` to finish." % (args.rel_path, args.ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
