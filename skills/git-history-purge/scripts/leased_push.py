"""Force-push every rewritten branch and tag with a per-ref lease, in batches, main last.

  python -I leased_push.py <work.git> <remote-url> [--batch N] [--dry-run]
                          [--snapshot-only | --use-snapshot]

Leases come from a snapshot of the REMOTE (`git ls-remote`) taken just before pushing and saved
to <work.git>/../remote-snapshot.txt. A ref the remote does not have gets an empty lease (must
not exist). Batches of --batch refs (default 40) keep the command line under the Windows limit.
Prints per-batch ref names and a final tally of porcelain flags. Exit 0 only if nothing was
rejected; on any rejection the push is PARTIAL: fix the cause, then run again WITHOUT
--use-snapshot so the leases are re-taken from the remote's current state.
--snapshot-only  write the snapshot and stop.   --use-snapshot  reuse the saved snapshot.
"""
import argparse
import os
import subprocess
import sys


def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("url")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--snapshot-only", action="store_true")
    g.add_argument("--use-snapshot", action="store_true")
    a = ap.parse_args()
    snap_path = os.path.join(os.path.dirname(os.path.abspath(a.work)), "remote-snapshot.txt")

    if a.use_snapshot:
        lines = open(snap_path, encoding="utf-8").read().splitlines()
    else:
        r = sh(["git", "ls-remote", a.url, "refs/heads/*", "refs/tags/*"])
        if r.returncode:
            print(r.stderr)
            return 2
        lines = [l for l in r.stdout.splitlines() if not l.endswith("^{}")]
        with open(snap_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    snap = {ref: sha for sha, ref in (l.split("\t") for l in lines if l)}
    print("remote snapshot: %d refs -> %s" % (len(snap), snap_path))
    if a.snapshot_only:
        return 0

    refs = sh(["git", "-C", a.work, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags"]).stdout.split()
    refs.sort(key=lambda r: r == "refs/heads/main")
    missing = sorted(set(snap) - set(refs))
    if missing:
        print("remote refs absent from the rewrite (left untouched): %d" % len(missing))
    flags, rejected = {}, []
    for i in range(0, len(refs), a.batch):
        chunk = refs[i:i + a.batch]
        print("batch %d: %s" % (i // a.batch + 1, " ".join(chunk)))
        args = ["git", "-C", a.work, "push", "--porcelain", "--no-verify"]
        if a.dry_run:
            args.append("--dry-run")
        args.append(a.url)
        args += ["--force-with-lease=%s:%s" % (r, snap.get(r, "")) for r in chunk]
        # NO "+" prefix: a "+" refspec forces the ref and silently overrides its lease
        # (test_ref_moved_after_snapshot_is_rejected_and_exit_nonzero proves this).
        args += ["%s:%s" % (r, r) for r in chunk]
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
    print("rejected: %d" % len(rejected))
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
