#!/usr/bin/env python3
"""Tests for maintenance/merge-forward-unblock.py (dirty-tree-triage, 2026-09-17).

WHY THIS EXISTS: `ora-checkout-merge-forward` has been BLOCKED_DIRTY_OVERLAP since
2026-09-14 on 5 local paths that are all SUPERSEDED copies of content already on
origin/main -- 4 untracked `maintenance/headless/*` drafts (09-10, pre-review) and
`maintenance/_state/fleet-heartbeat.json` (differs from origin/main by a 7-second `ts`).

The unblock cannot be a sequence of hand-run commands, for two independent reasons:

  1. THREE live Windows Task Scheduler tasks (`ORA Headless - integrity-guard`,
     `- stranded-spec`, `- mirror-drift`) execute the LOCAL
     `maintenance/headless/run-check.py`. Moving the drafts out breaks all three
     until a merge lands main's reviewed copies, so archive and merge must be one
     step -- and if the merge does NOT land, the drafts must come BACK.
  2. `git merge` refuses on an untracked file that would be overwritten EVEN WHEN
     the local file is byte-identical to the incoming one (verified against a
     scratch repo, git 2.55.0.windows.2 -- there is no content comparison in that
     check). So "make them match main" is not an alternative to moving them.

Run: python maintenance/_tests/test_merge_forward_unblock.py   (exit 0 = pass)
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAINT = os.path.dirname(HERE)
MODULE_PATH = os.path.join(MAINT, "merge-forward-unblock.py")

_failures = []
_tmpdirs = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        _failures.append(name)


def load_module():
    spec = importlib.util.spec_from_file_location("merge_forward_unblock", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def mktmp(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    _tmpdirs.append(d)
    return d


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def make_repo():
    """A clone whose origin/main carries the reviewed headless files + a newer
    heartbeat, and whose local branch is behind and dirty exactly like the real
    checkout: 2 untracked superseded drafts + 1 tracked ts-only-stale state file."""
    origin = mktmp("mfu-origin-")
    git(origin, "init", "-q", "--bare", "-b", "main")
    seed = mktmp("mfu-seed-")
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "t@t")
    git(seed, "config", "user.name", "t")
    write(os.path.join(seed, "README.md"), "seed\n")
    write(os.path.join(seed, "maintenance/_state/fleet-heartbeat.json"),
          json.dumps({"ts": "2026-09-14T13:58:13Z", "fleets": {"cc": 38}}, indent=1) + "\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "base")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "origin", "main")

    clone = mktmp("mfu-clone-")
    shutil.rmtree(clone)
    subprocess.run(["git", "clone", "-q", origin, clone], capture_output=True, text=True)
    git(clone, "config", "user.email", "t@t")
    git(clone, "config", "user.name", "t")
    git(clone, "checkout", "-q", "-b", "feat/live")

    # origin/main advances: adds the reviewed drafts, rewrites the heartbeat.
    write(os.path.join(seed, "maintenance/headless/run-check.py"), "# reviewed\nX = 2\n")
    write(os.path.join(seed, "maintenance/headless/lib.py"), "# reviewed lib\nY = 2\n")
    write(os.path.join(seed, "maintenance/_state/fleet-heartbeat.json"),
          json.dumps({"ts": "2026-09-14T13:58:20Z", "fleets": {"cc": 38}}, indent=1) + "\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "upstream: reviewed headless + heartbeat refresh")
    git(seed, "push", "-q", "origin", "main")
    git(clone, "fetch", "-q", "origin", "main")

    # Local state: superseded untracked drafts + ts-only-stale tracked heartbeat.
    write(os.path.join(clone, "maintenance/headless/run-check.py"), "# draft\nX = 1\n")
    write(os.path.join(clone, "maintenance/headless/lib.py"), "# draft lib\nY = 1\n")
    write(os.path.join(clone, "maintenance/_state/fleet-heartbeat.json"),
          json.dumps({"ts": "2026-09-99T00:00:00Z", "fleets": {"cc": 38}}, indent=1) + "\n")
    return clone


UNTRACKED = ["maintenance/headless/run-check.py", "maintenance/headless/lib.py"]
RESTORE = ["maintenance/_state/fleet-heartbeat.json"]


def merged_sync(repo):
    """Stand-in for checkout_merge_forward.sync() that performs the REAL merge, so
    a green happy-path test proves the unblock actually unblocks git."""
    rc, out, err = git(repo, "merge", "--no-commit", "--no-ff", "origin/main")
    raw = "\n".join(x for x in (err, out) if x)
    if rc == 0:
        git(repo, "commit", "-q", "--no-edit")
        return {"status": "MERGED", "detail": "merged", "blocked_paths": None}
    if "would be overwritten by merge" in raw or "would lose untracked files" in raw:
        return {"status": "BLOCKED_DIRTY_OVERLAP", "detail": raw, "blocked_paths": ["?"]}
    git(repo, "merge", "--abort")
    return {"status": "BLOCKED_CONFLICT", "detail": raw, "blocked_paths": None}


def blocked_sync(repo):
    return {"status": "BLOCKED_DIRTY_OVERLAP", "detail": "still blocked by something else",
            "blocked_paths": ["other/file.txt"]}


# --------------------------------------------------------------------------


def test_refuses_when_index_is_not_empty():
    """A shared checkout's index can hold ANOTHER session's staged work (this test
    exists because that happened for real during this script's own development)."""
    print("\ntest_refuses_when_index_is_not_empty")
    mod = load_module()
    repo = make_repo()
    write(os.path.join(repo, "someone-else.txt"), "their work\n")
    git(repo, "add", "someone-else.txt")
    r = mod.unblock(repo, UNTRACKED, RESTORE, sync_fn=merged_sync)
    check("status is REFUSED", r["status"] == "REFUSED", "got %r" % r["status"])
    check("reason names the index", "index" in (r.get("detail") or "").lower(),
          "got %r" % r.get("detail"))
    check("draft left in place", os.path.exists(os.path.join(repo, UNTRACKED[0])))
    check("nothing archived", not r.get("archived"))


def test_refuses_when_an_untracked_path_is_not_on_the_canonical_ref():
    """The whole premise is 'superseded': if origin/main does not carry the file,
    archiving it loses the only copy and the merge would not have been blocked by it."""
    print("\ntest_refuses_when_an_untracked_path_is_not_on_the_canonical_ref")
    mod = load_module()
    repo = make_repo()
    write(os.path.join(repo, "maintenance/headless/only-local.py"), "unique work\n")
    r = mod.unblock(repo, UNTRACKED + ["maintenance/headless/only-local.py"],
                    RESTORE, sync_fn=merged_sync)
    check("status is REFUSED", r["status"] == "REFUSED", "got %r" % r["status"])
    check("reason names the path", "only-local.py" in (r.get("detail") or ""),
          "got %r" % r.get("detail"))
    check("the unique file still exists",
          os.path.exists(os.path.join(repo, "maintenance/headless/only-local.py")))
    check("the superseded drafts were NOT archived either (all-or-nothing)",
          os.path.exists(os.path.join(repo, UNTRACKED[0])))


def test_refuses_when_a_restore_path_differs_beyond_the_ignored_keys():
    """Restoring discards local content, so it is allowed ONLY when the difference
    from the canonical ref is confined to machine-written keys (here: ts)."""
    print("\ntest_refuses_when_a_restore_path_differs_beyond_the_ignored_keys")
    mod = load_module()
    repo = make_repo()
    write(os.path.join(repo, RESTORE[0]),
          json.dumps({"ts": "2026-09-99T00:00:00Z", "fleets": {"cc": 99}}, indent=1) + "\n")
    r = mod.unblock(repo, UNTRACKED, RESTORE, sync_fn=merged_sync)
    check("status is REFUSED", r["status"] == "REFUSED", "got %r" % r["status"])
    check("reason names the file", "fleet-heartbeat" in (r.get("detail") or ""),
          "got %r" % r.get("detail"))
    check("local content untouched",
          json.loads(read(os.path.join(repo, RESTORE[0])))["fleets"]["cc"] == 99)


def test_happy_path_archives_restores_and_the_merge_actually_lands():
    print("\ntest_happy_path_archives_restores_and_the_merge_actually_lands")
    mod = load_module()
    repo = make_repo()
    before = git(repo, "rev-parse", "HEAD")[1]
    r = mod.unblock(repo, UNTRACKED, RESTORE, sync_fn=merged_sync)
    check("status is MERGED", r["status"] == "MERGED", "got %r %r" % (r["status"], r.get("detail")))
    check("HEAD advanced", git(repo, "rev-parse", "HEAD")[1] != before)
    check("2 drafts archived", len(r.get("archived") or []) == 2,
          "got %r" % (r.get("archived"),))
    adir = os.path.join(repo, r["archive_dir"])
    check("archived draft content preserved",
          "# draft" in read(os.path.join(adir, os.path.basename(UNTRACKED[0]))))
    check("heartbeat backup kept in the archive",
          any("fleet-heartbeat" in f for f in os.listdir(adir)), "%r" % os.listdir(adir))
    check("merge brought main's reviewed copy to the live path",
          "# reviewed" in read(os.path.join(repo, UNTRACKED[0])))
    check("the path is now TRACKED, so the headless tasks keep working",
          git(repo, "ls-files", "--error-unmatch", UNTRACKED[0])[0] == 0)
    check("working tree clean for the restore path",
          git(repo, "status", "--porcelain=v1", "--", RESTORE[0])[1] == "",
          "got %r" % git(repo, "status", "--porcelain=v1", "--", RESTORE[0])[1])
    check("not rolled back", r.get("rolled_back") is False)


def test_rolls_back_when_the_merge_does_not_land():
    """The blocker set can grow between planning and merging (other sessions keep
    writing). If the merge does not land, the drafts MUST return: three live Windows
    tasks execute the local run-check.py."""
    print("\ntest_rolls_back_when_the_merge_does_not_land")
    mod = load_module()
    repo = make_repo()
    original = read(os.path.join(repo, UNTRACKED[0]))
    r = mod.unblock(repo, UNTRACKED, RESTORE, sync_fn=blocked_sync)
    check("status echoes the sync verdict", r["status"] == "BLOCKED_DIRTY_OVERLAP",
          "got %r" % r["status"])
    check("rolled_back is True", r.get("rolled_back") is True)
    check("draft is back at its live path", os.path.exists(os.path.join(repo, UNTRACKED[0])))
    check("draft content is byte-identical to before",
          read(os.path.join(repo, UNTRACKED[0])) == original)
    check("second draft is back too", os.path.exists(os.path.join(repo, UNTRACKED[1])))
    check("draft is untracked again, as it was",
          git(repo, "ls-files", "--error-unmatch", UNTRACKED[0])[0] != 0)
    check("restored heartbeat rolled back to the local copy",
          json.loads(read(os.path.join(repo, RESTORE[0])))["ts"] == "2026-09-99T00:00:00Z",
          "got %r" % read(os.path.join(repo, RESTORE[0])))


def test_error_with_merge_head_present_does_not_claim_restore():
    """sync ERROR with MERGE_HEAD present (M51 CAS-failure paths leave the merge in
    progress): the blockers must NOT be put back over the merge, and the report must say
    so; rolled_back stays False."""
    print("\ntest_error_with_merge_head_present_does_not_claim_restore")
    mod = load_module()
    repo = make_repo()

    def stuck_sync(r):
        head = git(r, "rev-parse", "HEAD")[1]
        with open(os.path.join(r, ".git", "MERGE_HEAD"), "w") as fh:
            fh.write(head + "\n")
        return {"status": "ERROR", "detail": "staged-set safe commit failed",
                "merge_aborted": False}
    r = mod.unblock(repo, UNTRACKED, RESTORE, sync_fn=stuck_sync)
    check("status is ERROR", r["status"] == "ERROR", repr(r["status"]))
    check("rolled_back stays False", r.get("rolled_back") is False)
    check("detail says LEFT MID-MERGE", "LEFT MID-MERGE" in (r.get("detail") or ""), repr(r.get("detail")))
    check("detail says blockers NOT restored", "NOT restored" in (r.get("detail") or ""))
    check("detail names the archive dir", (r.get("archive_dir") or "?") in (r.get("detail") or ""))
    check("drafts were not copied back over the merge",
          not os.path.exists(os.path.join(repo, UNTRACKED[0])))


def main():
    for t in (test_refuses_when_index_is_not_empty,
              test_refuses_when_an_untracked_path_is_not_on_the_canonical_ref,
              test_refuses_when_a_restore_path_differs_beyond_the_ignored_keys,
              test_happy_path_archives_restores_and_the_merge_actually_lands,
              test_rolls_back_when_the_merge_does_not_land,
              test_error_with_merge_head_present_does_not_claim_restore):
        try:
            t()
        except Exception as e:  # noqa: BLE001 -- a crashing test is a failing test
            check(t.__name__ + " [raised]", False, "%s: %s" % (type(e).__name__, e))
    for d in _tmpdirs:
        shutil.rmtree(d, ignore_errors=True)
    if _failures:
        print("\n%d FAILURE(S):" % len(_failures))
        for f in _failures:
            print("  - %s" % f)
        return 1
    print("\nALL merge-forward-unblock TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
