"""Refuse any push that would carry pre-purge history back to the remote.

  python -I old_history_guard.py roots <backup.git> <purged-repo> <out-file>
      write the root commits of the backup that the purged history does not share
  python -I old_history_guard.py check <old-roots-file>      (as a pre-push hook)
      reads git's pre-push stdin lines "<local ref> <local sha> <remote ref> <remote sha>";
      exit 1 if any pushed commit descends from an old root

After a purge, local branches and worktrees still on the old history must never be pushed.
`pushurl` and per-branch pushRemote do not stop `git push origin <branch>`; a pre-push hook
does. Install it before pushes are re-enabled (call it from the repo's existing pre-push hook
if there is one). Run git from inside the repo being pushed (the hook's working directory).
"""
import subprocess
import sys

ZERO = "0" * 40


def roots(repo, *revs):
    r = subprocess.run(["git", "-C", repo, "rev-list", "--max-parents=0"] + list(revs),
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("cannot list roots in %s: %s" % (repo, r.stderr.strip()))
    return set(r.stdout.split())


def main(argv):
    if len(argv) == 5 and argv[1] == "roots":
        old = roots(argv[2], "--all") - roots(argv[3], "--all")
        with open(argv[4], "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(old)) + "\n")
        print("old-history roots: %d" % len(old))
        return 0
    if len(argv) == 3 and argv[1] == "check":
        with open(argv[2], encoding="utf-8") as fh:
            old = set(fh.read().split())
        if not old:
            print("old_history_guard: roots file is empty; refusing to guess", file=sys.stderr)
            return 1
        bad = []
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) != 4 or parts[1] == ZERO:
                continue
            if roots(".", parts[1]) & old:
                bad.append(parts[2])
        for ref in bad:
            print("old_history_guard: refusing to push %s: it carries pre-purge history" % ref, file=sys.stderr)
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
