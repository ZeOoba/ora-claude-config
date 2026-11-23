"""Refuse any push that would carry pre-purge commits back to the remote.

  python -I old_history_guard.py commits <backup.git> <purged.git> <out-file>
      write every commit reachable from the backup's branches and tags that is NOT in the
      purged history (rewritten or dropped by the purge). Exit 1 if there are none.
  python -I old_history_guard.py check <old-commits-file> [-- <next hook command> ...]
      as a pre-push hook: read git's stdin lines "<local ref> <local sha> <remote ref> <remote sha>";
      exit 1 if any pushed commit (or any ancestor) is in the file. If a next hook command is
      given and the push is allowed, run it with the SAME stdin bytes and the hook's own
      arguments, and return its exit code - this is how to chain it in front of an existing
      pre-push hook (e.g. a confidentiality scan that also reads stdin).

Why commits, not root commits: filter-repo keeps a commit's SHA when nothing in it or its
ancestors changed, so a clean first commit survives the purge and every old branch shares it.
After a purge, local branches and worktrees still on the old history must never be pushed;
`pushurl` and per-branch pushRemote do not stop `git push origin <branch>`, a pre-push hook
does. Run `check` from inside the repo being pushed (git runs hooks there).
"""
import subprocess
import sys

ZERO = "0" * 40


def rev_list(repo, *args):
    r = subprocess.run(["git", "-C", repo, "rev-list"] + list(args), capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("rev-list failed in %s: %s" % (repo, r.stderr.strip()))
    return set(r.stdout.split())


def main(argv):
    if len(argv) == 5 and argv[1] == "commits":
        old = rev_list(argv[2], "--branches", "--tags") - rev_list(argv[3], "--branches", "--tags")
        with open(argv[4], "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(old)) + "\n")
        print("pre-purge commits recorded: %d" % len(old))
        return 0 if old else 1
    if len(argv) >= 3 and argv[1] == "check":
        nxt = argv[argv.index("--") + 1:] if "--" in argv else []
        with open(argv[2], encoding="utf-8") as fh:
            old = set(fh.read().split())
        if not old:
            print("old_history_guard: commit list is empty; refusing to guess", file=sys.stderr)
            return 1
        data = sys.stdin.buffer.read()
        bad = []
        for line in data.decode("utf-8", "replace").splitlines():
            parts = line.split()
            if len(parts) != 4 or parts[1] == ZERO:
                continue
            if rev_list(".", parts[1]) & old:
                bad.append(parts[2])
        for ref in bad:
            print("old_history_guard: refusing to push %s: it carries pre-purge history" % ref, file=sys.stderr)
        if bad:
            return 1
        if nxt:
            return subprocess.run(nxt, input=data).returncode
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
