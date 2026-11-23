"""Force-push every rewritten branch and tag, each leased against the PRE-REWRITE backup.

  python -I leased_push.py <mirror.git> <work.git> <remote-url> [--batch N] [--dry-run]

<mirror.git> is the untouched backup the rewrite was made from; <work.git> is the rewrite.
Every ref is leased against the SHA it had in <mirror.git>, never against what the remote
shows at push time: a commit pushed after the backup is not in the rewrite, and a lease
taken from the remote would silently overwrite it.

Before pushing, each ref of <work.git> is classified against `git ls-remote`:
  done   - remote already has the rewritten SHA (an earlier run pushed it): skipped
  push   - remote still has the backup's SHA (or neither has the ref): pushed
  moved  - remote has anything else: someone pushed after the backup
If ANY ref is "moved", nothing is pushed (exit 3): re-fetch that ref into the backup,
re-run the rewrite for it, then run this again.
Refs are pushed in batches of --batch (default 40; hundreds of lease arguments in one push
exceed the Windows command-line limit), refs/heads/main last, and main is held back if any
earlier ref was rejected. Refspecs carry NO "+": a "+" forces past its own lease.

Exit: 0 all pushed or already done; 1 a rejection or held main (partial: fix the cause,
run again - finished refs are skipped); 2 bad arguments or repo; 3 remote moved since backup.
"""
import argparse
import os
import shlex
import subprocess
import sys


def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def local_refs(repo):
    r = sh(["git", "-C", repo, "for-each-ref", "--format=%(objectname) %(refname)", "refs/heads", "refs/tags"])
    if r.returncode:
        return None
    return {ref: sha for sha, ref in (l.split(" ", 1) for l in r.stdout.splitlines() if l)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mirror")
    ap.add_argument("work")
    ap.add_argument("url")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    backup, work = local_refs(a.mirror), local_refs(a.work)
    if not backup or not work:
        print("cannot read refs from %s" % (a.mirror if not backup else a.work))
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
    untouched = sorted(set(remote) - set(work))
    print("refs: %d to push, %d already done, %d moved since backup, %d remote-only left untouched"
          % (len(todo), len(done), len(moved), len(untouched)))
    if moved:
        for ref in sorted(moved):
            print("MOVED " + ref)
        print("nothing pushed: re-fetch the moved refs into the backup and re-run the rewrite for them")
        return 3

    hook = os.environ.get("LEASED_PUSH_TEST_BEFORE_PUSH")   # test seam: runs between check and push
    if hook:
        subprocess.run(shlex.split(hook, posix=False), check=True)

    todo.sort(key=lambda ref: ref == "refs/heads/main")
    flags, rejected, held = {}, [], []
    for i in range(0, len(todo), a.batch):
        chunk = todo[i:i + a.batch]
        if "refs/heads/main" in chunk and rejected:
            held.append("refs/heads/main")
            chunk = [ref for ref in chunk if ref != "refs/heads/main"]
            if not chunk:
                break
        print("batch %d: %s" % (i // a.batch + 1, " ".join(chunk)))
        args = ["git", "-C", a.work, "push", "--porcelain", "--no-verify"]
        if a.dry_run:
            args.append("--dry-run")
        args.append(a.url)
        args += ["--force-with-lease=%s:%s" % (ref, backup.get(ref, "")) for ref in chunk]
        args += ["%s:%s" % (ref, ref) for ref in chunk]
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
            rejected.append("batch %d failed: %s" % (i // a.batch + 1, p.stderr.strip()[-300:]))
    print("flags: %s" % " ".join("%s=%d" % kv for kv in sorted(flags.items())))
    for l in rejected:
        print("REJECTED " + l)
    for ref in held:
        print("HELD %s (pushed only when every other ref succeeded)" % ref)
    print("rejected: %d; held: %d" % (len(rejected), len(held)))
    return 1 if (rejected or held) else 0


if __name__ == "__main__":
    sys.exit(main())
