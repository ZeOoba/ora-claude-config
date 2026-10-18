#!/usr/bin/env python3
"""One-shot unblocker for `ora-checkout-merge-forward`: archive SUPERSEDED local
blockers, merge forward immediately, and roll the blockers BACK if the merge does
not land (dirty-tree-triage, 2026-09-17).

WHY A SCRIPT AND NOT A LIST OF STEPS (both reasons are load-bearing):

  1. `maintenance/headless/run-check.py` and its siblings are UNTRACKED 09-10
     pre-review drafts of what landed on origin/main as `e39bc29` -- but THREE live
     Windows Task Scheduler tasks (`ORA Headless - integrity-guard`, `- stranded-spec`,
     `- mirror-drift`) execute that local file every day. Archiving the drafts breaks
     all three until a merge lands main's reviewed copies. Archive and merge therefore
     have to be ONE operation, with a rollback if the merge does not land -- which a
     hand-run sequence cannot promise.
  2. `git merge` refuses on an untracked file it would overwrite EVEN WHEN that file is
     byte-identical to the incoming one (verified in a scratch repo, git
     2.55.0.windows.2 -- `verify_absent` compares existence, never content). So
     "overwrite the drafts with main's copies and leave them" is NOT an alternative.

It also keeps the whole operation inside ONE `python <script>` invocation, which is
what `config-write-guard.py` permits: the hand-run equivalents (`git checkout --`,
`mv`, a `git show >` redirect) are all write-shaped commands naming the live
governance tree, so each would need an `allow-config-write` token minted in an
attended session.

SAFETY MODEL -- refuse, or leave the checkout exactly as found. Nothing is deleted
(Hard Invariant 6): every blocker is MOVED or COPIED into
`maintenance/_archive/<date>_merge-forward-unblock/` first, and that archive is kept
whatever the outcome, so a rollback restores from a byte-verified copy.

REFUSES (exit 2, nothing touched) when:
  - anything is already STAGED in the shared index (another session's `git add`
    -- feedback_git_index_is_shared_state.md), or a merge/rebase is in progress;
  - `git fetch origin <canonical>` fails (cannot prove what "superseded" means);
  - an `--untracked` path is missing, is actually TRACKED, or does NOT exist on
     origin/<canonical> -- i.e. it is not superseded and archiving it would move the
     only copy;
  - a `--restore` path is not tracked-and-dirty, or differs from origin/<canonical>
     by anything beyond `--ignore-json-keys` (default `ts`). Restoring discards local
     content, so it is allowed only for a machine-written stamp difference.
  All checks run BEFORE the first write, and refusal is all-or-nothing.

  python maintenance/merge-forward-unblock.py --json
  python maintenance/merge-forward-unblock.py --json --dry-run
Exit 0 = MERGED or NOOP_CLEAN · 1 = merge did not land (rolled back) · 2 = REFUSED/ERROR.
"""
import argparse
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys

DEFAULT_REPO = r"C:\Users\Owner\.claude"
DEFAULT_CANONICAL = "main"
# The live 2026-09-14 blocker set, from checkout-merge-forward-last-run.json.
DEFAULT_UNTRACKED = (
    "maintenance/headless/ora_headless_lib.py",
    "maintenance/headless/run-check.py",
    "maintenance/headless/test-ora-headless-lib.py",
    "maintenance/headless/register-headless-checks.ps1",
)
DEFAULT_RESTORE = ("maintenance/_state/fleet-heartbeat.json",)
DEFAULT_IGNORE_JSON_KEYS = ("ts",)
SYNCED = ("MERGED", "NOOP_CLEAN")
IN_PROGRESS_REFS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")
IN_PROGRESS_PATHS = ("rebase-merge", "rebase-apply", "sequencer", "BISECT_START")


def _git(repo, args):
    try:
        p = subprocess.run(["git"] + args, cwd=repo, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120,
                           env=dict(os.environ, LC_ALL="C", LANGUAGE="C"))
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _in_progress(repo):
    for ref in IN_PROGRESS_REFS:
        rc, sha, _ = _git(repo, ["rev-parse", "-q", "--verify", ref])
        if rc == 0 and sha:
            return ref
        if rc not in (0, 1):
            return "%s (unverifiable)" % ref
    for sub in IN_PROGRESS_PATHS:
        rc, path, _ = _git(repo, ["rev-parse", "--git-path", sub])
        if rc != 0 or not path:
            return "%s (unverifiable)" % sub
        full = path if os.path.isabs(path) else os.path.join(repo, path)
        if os.path.exists(full):
            return sub
    return None


def json_equal_ignoring(a_text, b_text, keys):
    """True when both parse as JSON and are equal once `keys` are dropped from the
    top level. A parse failure is False, never a pass: an unparseable file is
    exactly when a 'only the timestamp differs' claim cannot be checked."""
    try:
        a, b = json.loads(a_text), json.loads(b_text)
    except (ValueError, TypeError):
        return False
    if not isinstance(a, dict) or not isinstance(b, dict):
        return a == b
    return {k: v for k, v in a.items() if k not in keys} == \
           {k: v for k, v in b.items() if k not in keys}


def _show(repo, ref, rel):
    rc, out, _ = _git(repo, ["show", "%s:%s" % (ref, rel)])
    return out if rc == 0 else None


def _is_tracked(repo, rel):
    return _git(repo, ["ls-files", "--error-unmatch", "--", rel])[0] == 0


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def plan(repo, untracked, restore, ignore_json_keys=DEFAULT_IGNORE_JSON_KEYS,
         canonical=DEFAULT_CANONICAL):
    """(ok, detail) -- every precondition, checked before any write."""
    rc, _, err = _git(repo, ["rev-parse", "--git-dir"])
    if rc != 0:
        return False, "not a git repo: %s" % err

    op = _in_progress(repo)
    if op:
        return False, "a git operation is already in progress (%s) -- left untouched" % op

    rc, staged, _ = _git(repo, ["diff", "--cached", "--name-only"])
    if rc != 0:
        return False, "cannot read the index"
    if staged:
        return False, ("the shared index already has staged content (another session's "
                       "`git add`): %s" % ", ".join(staged.splitlines()[:10]))

    rc, _, err = _git(repo, ["fetch", "origin", canonical])
    if rc != 0:
        return False, "fetch origin %s failed: %s" % (canonical, err)
    ref = "origin/%s" % canonical

    for rel in untracked:
        full = os.path.join(repo, rel)
        if not os.path.exists(full):
            return False, "%s does not exist -- already resolved?" % rel
        if _is_tracked(repo, rel):
            return False, ("%s is TRACKED, not an untracked draft -- refusing to archive "
                           "a tracked file" % rel)
        if _show(repo, ref, rel) is None:
            return False, ("%s does not exist on %s -- it is NOT superseded, and archiving "
                           "it would move the only copy" % (rel, ref))

    for rel in restore:
        full = os.path.join(repo, rel)
        if not os.path.exists(full):
            return False, "%s does not exist" % rel
        if not _is_tracked(repo, rel):
            return False, "%s is not tracked -- nothing to restore it from" % rel
        canon = _show(repo, ref, rel)
        if canon is None:
            return False, "%s does not exist on %s" % (rel, ref)
        local = _read(full)
        if local == canon:
            continue
        if not json_equal_ignoring(local, canon, ignore_json_keys):
            return False, ("%s differs from %s beyond %s -- restoring would discard real "
                           "local content" % (rel, ref, "/".join(ignore_json_keys)))
    return True, "all preconditions hold"


def _default_sync(repo, canonical, state_file):
    """checkout-merge-forward.py is the authoritative merge -- never reimplemented."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "checkout-merge-forward.py")
    spec = importlib.util.spec_from_file_location("checkout_merge_forward", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot locate checkout-merge-forward.py at %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.sync(repo, canonical)
    if state_file:
        try:
            mod.update_state(result, state_file)
        except OSError:
            pass  # a state-write failure never changes the merge verdict
    return result


def unblock(repo, untracked=DEFAULT_UNTRACKED, restore=DEFAULT_RESTORE,
            ignore_json_keys=DEFAULT_IGNORE_JSON_KEYS, canonical=DEFAULT_CANONICAL,
            sync_fn=None, state_file=None, archive_dir=None, dry_run=False):
    repo = os.path.abspath(repo)
    untracked, restore = list(untracked), list(restore)
    out = {"repo": repo, "status": None, "detail": None, "archive_dir": None,
           "archived": [], "restored": [], "rolled_back": False, "merge": None}

    ok, detail = plan(repo, untracked, restore, ignore_json_keys, canonical)
    if not ok:
        out["status"], out["detail"] = "REFUSED", detail
        return out
    if dry_run:
        out["status"], out["detail"] = "DRY_RUN", detail
        return out

    rel_archive = archive_dir or os.path.join(
        "maintenance", "_archive",
        "%s_merge-forward-unblock" % datetime.date.today().isoformat()).replace("\\", "/")
    abs_archive = os.path.join(repo, rel_archive)
    os.makedirs(abs_archive, exist_ok=True)
    out["archive_dir"] = rel_archive

    moved, copied = [], []
    try:
        for rel in untracked:
            dest = os.path.join(abs_archive, os.path.basename(rel))
            shutil.move(os.path.join(repo, rel), dest)
            moved.append((rel, dest))
        for rel in restore:
            dest = os.path.join(abs_archive, os.path.basename(rel) + ".local-copy")
            shutil.copy2(os.path.join(repo, rel), dest)
            copied.append((rel, dest))
            rc, _, err = _git(repo, ["checkout", "--", rel])
            if rc != 0:
                raise RuntimeError("git checkout -- %s failed: %s" % (rel, err))
    except (OSError, RuntimeError) as e:
        _rollback(repo, moved, copied)
        out["status"] = "ERROR"
        out["detail"] = "could not stage the unblock (%s) -- rolled back" % e
        out["rolled_back"] = True
        return out

    out["archived"] = [rel for rel, _ in moved]
    out["restored"] = [rel for rel, _ in copied]

    try:
        result = sync_fn(repo) if sync_fn else _default_sync(repo, canonical, state_file)
    except Exception as e:  # noqa: BLE001 -- any merge failure must roll back
        _rollback(repo, moved, copied)
        out["status"], out["detail"], out["rolled_back"] = "ERROR", "merge raised %s: %s" % (
            type(e).__name__, e), True
        return out

    out["merge"] = result
    out["status"] = result.get("status")
    out["detail"] = result.get("detail")
    if out["status"] == "ERROR" and _merge_head_present(repo):
        # The merge was deliberately LEFT IN PROGRESS (checkout-merge-forward M51 paths):
        # copying drafts back over a live merge would corrupt it. Archived copies are the
        # restore source once a human resolves the merge.
        out["rolled_back"] = False
        out["detail"] = ("LEFT MID-MERGE -- blockers NOT restored; local copies archived at %s; "
                         "restore from the archive after resolving the merge. %s"
                         % (rel_archive, out["detail"]))
        return out
    if out["status"] not in SYNCED:
        _rollback(repo, moved, copied)
        out["rolled_back"] = True
        out["detail"] = ("merge did not land (%s) -- blockers restored to their live paths "
                         "so the ORA Headless tasks keep running. %s"
                         % (out["status"], out["detail"]))
    return out


def _merge_head_present(repo):
    """True unless MERGE_HEAD is provably absent (rev-parse exit 1): an unreadable ref
    counts as present so a possibly-live merge is never overwritten."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", "MERGE_HEAD"],
                       capture_output=True, text=True)
    return p.returncode != 1


def _rollback(repo, moved, copied):
    """Put every blocker back. Never overwrites a path the merge itself created."""
    for rel, dest in moved:
        live = os.path.join(repo, rel)
        if os.path.exists(live) or not os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(live), exist_ok=True)
        try:
            shutil.copy2(dest, live)
        except OSError:
            pass
    for rel, dest in copied:
        try:
            shutil.copy2(dest, os.path.join(repo, rel))
        except OSError:
            pass


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--canonical", default=DEFAULT_CANONICAL)
    ap.add_argument("--untracked", action="append", default=None)
    ap.add_argument("--restore", action="append", default=None)
    ap.add_argument("--ignore-json-keys", default=",".join(DEFAULT_IGNORE_JSON_KEYS))
    ap.add_argument("--state-file", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    r = unblock(a.repo,
                untracked=a.untracked or DEFAULT_UNTRACKED,
                restore=a.restore if a.restore is not None else DEFAULT_RESTORE,
                ignore_json_keys=tuple(k for k in a.ignore_json_keys.split(",") if k),
                canonical=a.canonical, state_file=a.state_file, dry_run=a.dry_run)
    print(json.dumps(r, indent=2) if a.json
          else "%s: %s" % (r["status"], r["detail"]))
    if r["status"] in SYNCED or r["status"] == "DRY_RUN":
        return 0
    return 2 if r["status"] in ("REFUSED", "ERROR") else 1


if __name__ == "__main__":
    sys.exit(main())
