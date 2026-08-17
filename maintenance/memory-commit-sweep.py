#!/usr/bin/env python3
"""ORA memory/ commit-cadence sweep. REPORT-AND-ACT — this is not a probe; it commits.

WHY THIS EXISTS: memory/ is git-tracked but has no write gate (unlike event_log.md's
append-event-log.py: mtime-guard + atomic-replace + spool-on-lock). Sessions edit memory
files directly via Edit/Write and separately git add/commit, or don't. With 5-6 concurrent
sessions this produces the 32f3065 failure class -- a session commits a MEMORY.md pointer
to a new file without git-add-ing the file itself, so the pointer is broken for every
reader but the authoring machine. memory-integrity-probe.py's head_orphans() check
DETECTS this; this script closes the gap it detects, on a cadence, instead of the file
sitting orphaned until someone happens to run the probe and then hand-fixes it (as
happened live 2026-08-16, twice in 3 days after the first instance on 2026-08-14 --
see reference_memory_dir_not_in_single_writer_list_2026-08-14.md).

SAFETY MODEL (all deliberate, not incidental):
  - Scoped to the memory/ directory ONLY. Every git call runs with cwd=MEM and pathspec
    "." or explicit relative filenames -- never a bare `-A` at the repo root, so this can
    never stage/commit hooks/, settings.json, or any sibling path mid-edit by another
    session (the blast-radius list in CLAUDE.md).
  - QUIET-WINDOW, not "commit everything dirty": a changed path is only swept once its
    mtime is at least QUIET_SECONDS old. A file another session is still actively
    mid-edit on (e.g. writing file A, about to write file B as one logical change 5s
    later) is left for the NEXT cycle, not grabbed mid-transaction. This mirrors
    dirty-tree-triage's two-pass mtime-settlement heuristic, simplified for an unattended
    cadence rather than an interactive investigation.
  - Deletions and renames are never auto-swept -- reported and left for a human. A file
    disappearing from memory/ is rare and consequential (Hard invariant 6: never delete,
    move to /archive/); blind auto-commit of a delete this script did not originate is
    exactly the kind of silent, hard-to-reverse action the operating rules single out.
  - Staged-set verification: after `git add`, the script re-reads what is actually staged
    and aborts the commit (no `git commit` call at all) if it does not exactly match what
    it intended to add. This is the guard against racing a concurrent `git add` from
    another process sharing the same index (see feedback_git_index_is_shared_state.md /
    reference_event_log_partial_commit_splice.md) -- on mismatch this script does NOT
    reset or unstage anything (that could interfere with the other process); it just skips
    committing this cycle and reports. The next cycle retries from a clean read.
  - Index-lock aware: if .git/index.lock exists in the repo root, skip the whole cycle
    (exit 1, non-fatal) rather than wait-and-hope or force through it.
  - No pushes, no branch switches, no rebase/reset/checkout of anything. Commits land on
    whatever branch is currently checked out -- purely additive.
  - No empty commits: if nothing is staged after `git add`, or the staged diff is empty,
    the script exits 0 with nothing further.

Exit 0 = committed, or nothing needed committing this cycle. Exit 1 = skipped (lock
contention or staged-set race) -- transient, retry next cycle. Exit 2 = cannot operate
(not a git repo, MEM missing) -- a probe/sweep that cannot look must not invent findings.
"""
import os, re, sys, glob, subprocess, time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")
MEM = os.environ.get("ORA_MEMORY_DIR") or os.path.join(
    HOME, ".claude", "projects",
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")

QUIET_SECONDS = 120  # a changed path must be untouched this long before the sweep takes it

STATUS_RE = re.compile(r"^(..)\s+(.+)$")


def _git(mem_dir, *args, timeout=30):
    """Run git with cwd=mem_dir. Returns (stdout, returncode) -- returncode None on
    subprocess failure (git missing, timeout). Never raises."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=mem_dir, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except Exception as e:
        return str(e), None
    return r.stdout, r.returncode


def _repo_root(mem_dir):
    out, rc = _git(mem_dir, "rev-parse", "--show-toplevel")
    return out.strip() if rc == 0 else None


def _index_locked(mem_dir):
    root = _repo_root(mem_dir)
    if not root:
        return False
    return os.path.isfile(os.path.join(root, ".git", "index.lock"))


def _parse_status(porcelain):
    """porcelain `git status --porcelain` lines -> [(code, path), ...]. Pure."""
    out = []
    for line in porcelain.splitlines():
        m = STATUS_RE.match(line)
        if not m:
            continue
        code, path = m.group(1), m.group(2)
        # renames report as "old -> new"; keep the raw path token, callers filter on code.
        out.append((code, path))
    return out


def _resolve(path_str, mem_dir, repo_root):
    """A path string from git status/diff output -> absolute filesystem path.

    NOT assumable: whether git reports these paths relative to CWD or relative to the
    repo root is version/config dependent (status.relativePaths; `git diff --name-only`
    has its own convention). Confirmed live on this environment (git 2.55.0, Windows):
    `git -C <mem_dir> status --porcelain -- .` returns REPO-ROOT-relative paths even
    though cwd=mem_dir -- e.g. "projects/.../memory/INDEX_reference.md", not
    "INDEX_reference.md". A script that assumed cwd-relative and fed that string
    straight to `git add` (with cwd=mem_dir) would look for a nonexistent nested path
    and silently no-op forever -- exactly the kind of self-defeating bug this sweep
    exists to prevent elsewhere. Try both joins, prefer whichever exists on disk (the
    ground truth); if neither exists (path already gone -- a delete), prefer the
    repo-root join since that is the confirmed convention here. Always returns an
    absolute path, which sidesteps the ambiguity for every downstream git call: git
    accepts absolute pathspecs regardless of cwd.
    """
    root_join = os.path.normpath(os.path.join(repo_root, path_str)) if repo_root else None
    cwd_join = os.path.normpath(os.path.join(mem_dir, path_str))
    if root_join and os.path.exists(root_join):
        return root_join
    if os.path.exists(cwd_join):
        return cwd_join
    return root_join or cwd_join


def classify(entries, mem_dir, repo_root, now, quiet_seconds):
    """[(code, path)] -> dict of buckets, values are ABSOLUTE paths (raw path string for
    review entries, since a rename's "old -> new" token isn't a single resolvable path).
    Pure apart from stat() for mtimes.

    settled:   untracked/modified, mtime old enough -> safe to sweep this cycle
    recent:    untracked/modified, mtime too fresh -> leave for next cycle
    review:    delete/rename present -> never auto-swept, always reported
    """
    settled, recent, review = [], [], []
    for code, path in entries:
        if "D" in code or "R" in code or "->" in path:
            review.append(path)
            continue
        full = _resolve(path, mem_dir, repo_root)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            review.append(path)  # vanished between status and stat -- don't guess
            continue
        if (now - mtime) >= quiet_seconds:
            settled.append(full)
        else:
            recent.append(full)
    return {"settled": sorted(settled), "recent": sorted(recent), "review": sorted(review)}


def build_message(name_status, mem_dir, repo_root):
    """`git diff --cached --name-status` output -> commit message. Displays paths
    relative to mem_dir for readability (e.g. "reference_x.md", not the full
    repo-relative or absolute form)."""
    added, modified = [], []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        code, path = parts
        display = os.path.relpath(_resolve(path, mem_dir, repo_root), mem_dir)
        (added if code.startswith("A") else modified).append(display)
    lines = ["memory: automated sync checkpoint (%d new, %d modified)"
             % (len(added), len(modified)), ""]
    for p in sorted(added):
        lines.append("new: " + p)
    for p in sorted(modified):
        lines.append("mod: " + p)
    lines += ["", "Unattended memory-commit-sweep.py run. Mechanical checkpoint only -- "
              "no content judgment applied. Closes the head_orphans() gap "
              "(committed-pointer-to-uncommitted-content) that "
              "memory-integrity-probe.py detects but does not fix."]
    return "\n".join(lines)


def run_sweep(mem_dir=None, quiet_seconds=QUIET_SECONDS, now=None):
    """Does the real work. Returns a result dict; never raises, never prints, never
    calls sys.exit -- so tests can call it directly against a fixture repo."""
    mem_dir = mem_dir or MEM
    now = now if now is not None else time.time()
    result = {"exit_code": 0, "committed": False, "committed_files": [],
              "skipped_recent": [], "skipped_review": [], "message": ""}

    if not os.path.isdir(mem_dir):
        result["exit_code"] = 2
        result["message"] = "memory dir not found: %s" % mem_dir
        return result

    root = _repo_root(mem_dir)
    if not root:
        result["exit_code"] = 2
        result["message"] = "%s is not inside a git work tree" % mem_dir
        return result

    if _index_locked(mem_dir):
        result["exit_code"] = 1
        result["message"] = "skipped -- .git/index.lock present (another git operation in progress)"
        return result

    out, rc = _git(mem_dir, "status", "--porcelain", "--untracked-files=all", "--", ".")
    if rc != 0:
        result["exit_code"] = 2
        result["message"] = "git status failed: %s" % out
        return result

    entries = _parse_status(out)
    if not entries:
        result["message"] = "clean -- nothing to sweep"
        return result

    buckets = classify(entries, mem_dir, root, now, quiet_seconds)
    result["skipped_recent"] = [os.path.relpath(p, mem_dir) for p in buckets["recent"]]
    result["skipped_review"] = buckets["review"]

    if not buckets["settled"]:
        result["message"] = "nothing settled this cycle (%d too-recent, %d needs-review)" % (
            len(buckets["recent"]), len(buckets["review"]))
        return result

    # Absolute paths -- sidesteps the cwd-vs-repo-root-relative ambiguity documented on
    # _resolve(). git accepts absolute pathspecs regardless of cwd.
    out, rc = _git(mem_dir, "add", "--", *buckets["settled"])
    if rc != 0:
        result["exit_code"] = 1
        result["message"] = "git add failed, skipping this cycle: %s" % out
        return result

    staged_out, rc = _git(mem_dir, "diff", "--cached", "--name-only")
    if rc != 0:
        result["exit_code"] = 1
        result["message"] = "could not verify staged set, skipping this cycle: %s" % staged_out
        return result
    staged = {_resolve(p, mem_dir, root) for p in staged_out.splitlines()}
    intended = set(buckets["settled"])
    if staged != intended:
        # Do NOT unstage/reset -- another process may own the extra entries. Leave the
        # index as-is and retry next cycle.
        result["exit_code"] = 1
        result["message"] = ("staged set != intended set (concurrent git add?) -- not "
                              "committing. extra=%r missing=%r" % (
                                  sorted(staged - intended), sorted(intended - staged)))
        return result

    name_status, rc = _git(mem_dir, "diff", "--cached", "--name-status")
    if rc != 0 or not name_status.strip():
        result["message"] = "nothing actually staged after add -- no-op"
        return result

    msg = build_message(name_status, mem_dir, root)
    out, rc = _git(mem_dir, "commit", "-m", msg)
    if rc != 0:
        result["exit_code"] = 2
        result["message"] = "git commit failed: %s" % out
        return result

    result["committed"] = True
    result["committed_files"] = sorted(os.path.relpath(p, mem_dir) for p in intended)
    result["message"] = "committed %d file(s)" % len(intended)
    return result


def main():
    result = run_sweep()
    print("MEMORY COMMIT SWEEP: %s" % result["message"])
    if result["skipped_recent"]:
        print("  too recent this cycle (%ds quiet window): %s" % (
            QUIET_SECONDS, ", ".join(result["skipped_recent"])))
    if result["skipped_review"]:
        print("  needs human review (delete/rename, never auto-swept): %s" % (
            ", ".join(result["skipped_review"])))
    if result["committed"]:
        for f in result["committed_files"]:
            print("  + " + f)
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
