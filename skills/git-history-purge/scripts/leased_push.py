"""Force-push a history rewrite, checking the whole chain backup -> rewrite -> remote first.

  python -I leased_push.py <mirror.git> <work.git> <remote-url> [--batch N] [--dry-run]
                          [--delete-removed]

<mirror.git> is the untouched backup; <work.git> is filter-repo run on a fresh clone of it
(filter-repo leaves <work.git>/filter-repo/ref-map: old SHA, new SHA, ref; a second
filter-repo pass on the same copy keeps the original "old" SHAs).

Before anything is pushed, all three links are checked:
  rewrite  - every ref in ref-map must have been rewritten FROM the backup's SHA. A stale
             work.git (made from a backup that has since been re-fetched) -> exit 2.
  remote   - each ref is classified against `git ls-remote`:
               done   remote already has the rewritten SHA (an earlier run pushed it): skipped
               push   remote still has the backup's SHA (or neither has the ref)
               moved  anything else: someone pushed after the backup; also any branch or tag
                      on the remote that the backup does not have (created after it)
             Any moved ref -> nothing pushed, exit 3. Fetch it into the backup, move work.git
             aside, re-clone and re-run filter-repo, then run this again.
  deleted  - refs in the backup that the rewrite removed (every commit on them was purged)
             still hold the old data on the remote. Without --delete-removed: exit 4,
             nothing pushed. With it: each is deleted, leased against the backup's SHA.

Every lease is against the BACKUP's SHA, never against what the remote shows at push time.
Refspecs carry NO "+": a "+" forces past its own lease. All refs except refs/heads/main go
in batches of --batch (default 40; hundreds of lease arguments exceed the Windows
command-line limit); the default branch (--main-ref, default refs/heads/main) is pushed
ALONE, last, and only if nothing else was rejected.

Exit: 0 everything pushed or already done; 1 a rejection or main held (rerun after fixing:
finished refs are skipped); 2 bad arguments, unreadable repo, failed ls-remote, missing or
stale ref-map; 3 remote moved since backup; 4 refs deleted by the rewrite (see above).
"""
import argparse
import os
import subprocess
import sys

ZERO = "0" * 40


def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def local_refs(repo):
    r = sh(["git", "-C", repo, "for-each-ref", "--format=%(objectname) %(refname)", "refs/heads", "refs/tags"])
    if r.returncode:
        return None
    return {ref: sha for sha, ref in (l.split(" ", 1) for l in r.stdout.splitlines() if l)}


def read_ref_map(work):
    path = os.path.join(work, "filter-repo", "ref-map")
    try:
        with open(path, encoding="utf-8") as fh:
            rows = [l.split() for l in fh.read().splitlines()[1:] if l.strip()]
    except OSError:
        return None
    return {ref: (old, new) for old, new, ref in rows}


def push(work, url, refs, leases, dry_run, flags, rejected, label):
    """One `git push` of refs (each "src:dst" with a lease); tallies porcelain flags."""
    print("%s: %s" % (label, " ".join(dst for _, dst in refs)))
    args = ["git", "-C", work, "push", "--porcelain", "--no-verify"]
    if dry_run:
        args.append("--dry-run")
    args.append(url)
    args += ["--force-with-lease=%s:%s" % (dst, leases[dst]) for _, dst in refs]
    args += ["%s:%s" % (src, dst) for src, dst in refs]
    p = sh(args)
    seen = False
    for l in p.stdout.splitlines():
        if "\t" in l and l[:1] in "+-*= !":
            seen = True
            f = l.split("\t")[0].strip() or " "
            flags[f] = flags.get(f, 0) + 1
            if f == "!":
                rejected.append(l)
    if p.returncode and not seen:
        rejected.append("%s failed: %s" % (label, p.stderr.strip()[-300:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mirror")
    ap.add_argument("work")
    ap.add_argument("url")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delete-removed", action="store_true")
    ap.add_argument("--main-ref", default="refs/heads/main",
                    help="the default branch: pushed alone, last, only if nothing else was rejected")
    a = ap.parse_args()

    backup, work = local_refs(a.mirror), local_refs(a.work)
    if not backup or work is None:
        print("cannot read refs from %s" % (a.mirror if not backup else a.work))
        return 2
    ref_map = read_ref_map(a.work)
    if ref_map is None:
        print("no filter-repo/ref-map in %s: it must be a filter-repo run on a fresh clone of the backup" % a.work)
        return 2
    stale = sorted(ref for ref, (old, _) in ref_map.items() if ref in backup and old != backup[ref])
    if stale:
        for ref in stale:
            print("STALE " + ref)
        print("the rewrite was not made from this backup: move work.git aside, re-clone the backup, re-run filter-repo")
        return 2

    r = sh(["git", "ls-remote", a.url, "refs/heads/*", "refs/tags/*"])
    if r.returncode:
        print("ls-remote failed: %s" % r.stderr.strip()[-300:])
        return 2
    remote = {ref: sha for sha, ref in (l.split("\t") for l in r.stdout.splitlines()
                                        if l and not l.endswith("^{}"))}

    done, todo, moved = [], [], []
    for ref, new in work.items():
        cur, old = remote.get(ref), backup.get(ref)
        if cur == new:
            done.append(ref)
        elif cur == old:
            todo.append(ref)
        else:
            moved.append(ref)
    removed = sorted(ref for ref in backup if ref not in work)
    to_delete = [ref for ref in removed if remote.get(ref) == backup[ref]]
    moved += [ref for ref in removed if remote.get(ref) not in (None, backup[ref])]
    # The backup is a mirror: a branch or tag on the remote that it does not have was
    # created after the backup, and may carry pre-purge history. Treat it as moved.
    moved += sorted(set(remote) - set(work) - set(backup))
    print("refs: %d to push, %d already done, %d moved since backup, %d deleted by the rewrite "
          "(%d still on remote)" % (len(todo), len(done), len(moved), len(removed), len(to_delete)))
    if moved:
        for ref in sorted(moved):
            print("MOVED " + ref)
        print("nothing pushed: fetch the moved refs into the backup, redo the rewrite, run again")
        return 3
    if to_delete and not a.delete_removed:
        for ref in to_delete:
            print("DELETED-BY-REWRITE " + ref)
        print("nothing pushed: these remote refs still hold purged data; re-run with --delete-removed")
        return 4

    hook = os.environ.get("LEASED_PUSH_TEST_BEFORE_PUSH")   # test seam: a Python script run between check and push
    if hook:
        subprocess.run([sys.executable, "-I", hook], check=True)

    leases = {ref: backup.get(ref, "") for ref in todo}
    leases.update({ref: backup[ref] for ref in to_delete})
    others = [(ref, ref) for ref in todo if ref != a.main_ref] + [("", ref) for ref in to_delete]
    flags, rejected, held = {}, [], []
    for i in range(0, len(others), a.batch):
        push(a.work, a.url, others[i:i + a.batch], leases, a.dry_run, flags, rejected, "batch %d" % (i // a.batch + 1))
    if a.main_ref in todo:
        if rejected:
            held.append(a.main_ref)
        else:
            push(a.work, a.url, [(a.main_ref, a.main_ref)], leases, a.dry_run, flags, rejected, "main")
    print("flags: %s" % " ".join("%s=%d" % kv for kv in sorted(flags.items())))
    for l in rejected:
        print("REJECTED " + l)
    for ref in held:
        print("HELD %s (pushed only when every other ref succeeded)" % ref)
    print("rejected: %d; held: %d; deleted: %d" % (len(rejected), len(held), flags.get("-", 0)))
    return 1 if (rejected or held) else 0


if __name__ == "__main__":
    sys.exit(main())
