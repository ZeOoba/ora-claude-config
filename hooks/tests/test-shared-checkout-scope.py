"""Tests for shared-checkout-guard.py's PATH-SCOPED hygiene nudge (2026-09-10).

WHY THIS EXISTS: the nudge fired on every Edit into a shared checkout and reported
REPO-WIDE dirt -- "the .claude MAIN checkout has 97 uncommitted change(s) that may be
another session's WIP" -- with no regard for whether the file under the cursor was one
of them. Gabriel flagged it as advisory noise, and the diagnosis is sharper than
"too chatty": the message was WORD-FOR-WORD IDENTICAL in the one case that genuinely
matters (your file is itself uncommitted, so your edit lands on someone's WIP) and in
the overwhelmingly common case that carries no such hazard at all. A warning that reads
the same when it is true and when it is false is not a warning.

So these cases assert the SPLIT, not the wording:
  1-2. edited file IS dirty        -> named as the hazard it is
  3-4. edited file is NOT dirty    -> labelled repo background, and does NOT assert a
                                      co-mingling risk it cannot support
  5.   attribution narrows with the scope (a session that touched an UNRELATED dirty
       file must not be named when you edit a different dirty file)
  6.   the dedupe fingerprint carries the in/out bit -- otherwise the transition from
       background to real collision inside one unchanged dirty set is swallowed by the
       marker written for the weaker message
  7.   the commit-hygiene advice survives in BOTH branches (the half that was always
       true), and neither branch ever denies

Kept in its own file rather than appended to test-shared-checkout-guard.py: that file
is inside another live session's declared claim paths as of this change.

Stdlib only. ASCII-only. Self-contained (creates its own temp git repos).
"""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import gitfixture  # noqa: E402

# See test-shared-checkout-guard.py: git sets these when this runs inside the real
# pre-push chain, and they would silently redirect every git call below at the OUTER
# repo instead of the temp fixture.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS, "shared-checkout-guard.py")

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def run_hook(session_id, file_path, repos, sessions_dir):
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = os.pathsep.join(repos)
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_dir
    env["ORA_FLEET_SESSIONS_DIR"] = "C:/does/not/exist_scs_sessions_dir"
    # Claim files must not leak in from the live tree: this suite is about the DIRT
    # nudge, and a real active-work claim on a fixture path would add same-file
    # collision text to the output and make these assertions machine-dependent.
    env["ORA_ACTIVE_WORK_DIR"] = os.path.join(sessions_dir, "no-claims")
    p = subprocess.run([sys.executable, HOOK],
                       input=json.dumps({"session_id": session_id,
                                         "tool_input": {"file_path": file_path}}),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def message_of(out):
    """The warning text, or "" when the hook stayed silent."""
    if not out.strip():
        return ""
    try:
        return json.loads(out).get("systemMessage") or ""
    except Exception:
        return ""


def dirty_repo(files):
    """A main checkout with `files` (relative paths) present but uncommitted."""
    d = gitfixture.blank_repo(prefix="scs-main-")
    for rel in files:
        full = os.path.join(d, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write("uncommitted content\n")
    return d


def sessions_tmp():
    return tempfile.mkdtemp(prefix="scs-sess-")


def record_touched(sessions_dir, sid, paths):
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "touched-files.txt"), "w", encoding="utf-8") as fh:
        for p in paths:
            fh.write("%s\t%.6f\n" % (os.path.normcase(os.path.abspath(p)), time.time()))


# ===================================================================================
# 1-2. The edited file IS in the dirty set
# ===================================================================================
print("== 1-2. edited file is itself uncommitted ==")
repo = dirty_repo(["wip.py", "other-a.txt", "other-b.txt"])
target = os.path.join(repo, "wip.py")
rc, out = run_hook("s1", target, [repo], sessions_tmp())
msg = message_of(out)
check("still exits 0 (warn-only)", rc, 0)
check("warns", bool(msg), True)
check("names the file as the hazard", "wip.py is ITSELF one of the" in msg, True)
check("still reports the repo-wide count for context", "3 uncommitted" in msg, True)
check("does NOT mislabel it as background", "NOT among them" in msg, False)


# ===================================================================================
# 3-4. The edited file is NOT in the dirty set
# ===================================================================================
print("== 3-4. edited file is clean, repo is dirty ==")
repo = dirty_repo(["other-a.txt", "other-b.txt"])
target = os.path.join(repo, "server", "clean.ts")
rc, out = run_hook("s2", target, [repo], sessions_tmp())
msg = message_of(out)
check("still exits 0", rc, 0)
check("still says something (the repo IS dirty)", bool(msg), True)
check("labels it repo background", "NOT among them" in msg, True)
check("does not assert a hazard on this file",
      "is ITSELF one of the" in msg, False)
# The old wording -- unconditional and identical in both branches -- is what made the
# hook noise. Its absence here IS the fix.
check("drops the unconditional co-mingling assertion",
      "risks co-mingling their hunks" in msg, False)


# ===================================================================================
# 5. Attribution narrows with the scope
# ===================================================================================
print("== 5. attribution is scoped to the edited file ==")
repo = dirty_repo(["mine.py", "theirs.py"])
sess = sessions_tmp()
# Another session is live and has touched a DIFFERENT dirty file. Repo-wide, it would
# be named; scoped to mine.py it must not be, because it says nothing about my file.
state = os.path.join(sess, "session-state.json")
with open(state, "w", encoding="utf-8") as fh:
    json.dump({"sessions": {"otherses": {"status": "working", "cwd": repo,
                                         "lastAt": "t"}}}, fh)
os.environ["ORA_FLEET_STATE"] = state
record_touched(sess, "otherses", [os.path.join(repo, "theirs.py")])

rc, out = run_hook("s3", os.path.join(repo, "mine.py"), [repo], sess)
msg = message_of(out)
check("edited-file branch fired", "mine.py is ITSELF one of the" in msg, True)
check("the unrelated session is NOT named as touching my file",
      "otherses"[:8] in msg, False)

rc, out = run_hook("s3b", os.path.join(repo, "theirs.py"), [repo], sess)
msg = message_of(out)
check("...but IS named when I edit the file it actually touched",
      "otherses"[:8] in msg, True)
os.environ.pop("ORA_FLEET_STATE", None)


# ===================================================================================
# 6. The dedupe fingerprint carries the in/out bit
# ===================================================================================
print("== 6. clean-file warning does not swallow the dirty-file one ==")
repo = dirty_repo(["wip.py", "other.txt"])
sess = sessions_tmp()
# Same session, same UNCHANGED dirty set: first a clean file, then a dirty one.
_, out1 = run_hook("s4", os.path.join(repo, "server", "clean.ts"), [repo], sess)
_, out2 = run_hook("s4", os.path.join(repo, "wip.py"), [repo], sess)
check("background warning delivered first", "NOT among them" in message_of(out1), True)
check("the sharper warning still gets through",
      "wip.py is ITSELF one of the" in message_of(out2), True)
# ...and the ordinary dedupe still holds within one branch.
_, out3 = run_hook("s4", os.path.join(repo, "wip.py"), [repo], sess)
check("repeat of the same branch is still deduped", message_of(out3), "")


# ===================================================================================
# 7. Commit hygiene survives in both branches; neither ever denies
# ===================================================================================
print("== 7. commit-hygiene advice + warn-only invariant ==")
repo = dirty_repo(["wip.py", "other.txt"])
_, out_in = run_hook("s5", os.path.join(repo, "wip.py"), [repo], sessions_tmp())
_, out_out = run_hook("s6", os.path.join(repo, "clean.ts"), [repo], sessions_tmp())
for label, o in (("dirty-file", out_in), ("clean-file", out_out)):
    m = message_of(o)
    check(label + ": warns against a blanket add", "git add -A" in m, True)
    check(label + ": still points at an isolated worktree", "worktree" in m, True)
    check(label + ": never denies", "deny" in o, False)
    check(label + ": reaches the MODEL via additionalContext",
          bool((json.loads(o).get("hookSpecificOutput") or {}).get(
              "additionalContext")), True)

# A CLEAN repo stays completely silent in both branches -- unchanged contract.
clean = gitfixture.blank_repo(prefix="scs-clean-")
rc, out = run_hook("s7", os.path.join(clean, "x.ts"), [clean], sessions_tmp())
check("clean repo stays silent", out.strip(), "")


# ===================================================================================
# 8. UNTRACKED DIRECTORY collapse (independent-review finding, 2026-09-10). `git
#    status --porcelain` reports a whole untracked directory as ONE line -- `?? dir/`
#    -- never one line per file beneath it. A plain membership test against
#    _status_paths()'s output therefore misses every file under such a directory and
#    asserted "is NOT among them" for a file that plainly was uncommitted -- a false
#    assertion in exactly the direction this whole change was meant to fix.
# ===================================================================================
print("== 8. edited file lives under an UNTRACKED DIRECTORY ==")
repo = gitfixture.blank_repo(prefix="scs-dir-")
os.makedirs(os.path.join(repo, "newdir"))
with open(os.path.join(repo, "newdir", "a.py"), "w", encoding="utf-8") as fh:
    fh.write("new file under an untracked dir\n")
with open(os.path.join(repo, "root-dirty.txt"), "w", encoding="utf-8") as fh:
    fh.write("root-level uncommitted file\n")

rc, out = run_hook("s8", os.path.join(repo, "newdir", "a.py"), [repo], sessions_tmp())
msg = message_of(out)
check("file under an untracked dir IS recognized as dirty",
      "a.py is ITSELF one of the" in msg, True)
check("must NOT be mislabeled as background",
      "is NOT among them" in msg, False)

# A file that merely shares a NAME PREFIX with a dirty entry (not a real containment)
# must not be swept in by a loose prefix check.
repo2 = gitfixture.blank_repo(prefix="scs-prefix-")
with open(os.path.join(repo2, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("dirty\n")
with open(os.path.join(repo2, "a.py.bak"), "w", encoding="utf-8") as fh:
    fh.write("a DIFFERENT, clean-relative-to-a.py file that merely shares a prefix\n")
# a.py.bak is itself untracked too, so make it the ONLY thing NOT being asked about --
# check the other direction: editing a.py.bak while only a.py (not a.py.bak) is
# "dirty" would be a false positive from a naive startswith(dirty_prefix) check with
# no separator boundary. Use a fresh repo where a.py is dirty and a.py.bak is clean
# (committed) to isolate this.
repo3 = gitfixture.blank_repo(prefix="scs-prefix2-")
with open(os.path.join(repo3, "a.py.bak"), "w", encoding="utf-8") as fh:
    fh.write("committed content\n")
subprocess.run(["git", "-C", repo3, "add", "a.py.bak"], capture_output=True)
subprocess.run(["git", "-C", repo3, "commit", "-m", "seed"], capture_output=True)
with open(os.path.join(repo3, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("newly dirty, unrelated to a.py.bak\n")
rc, out = run_hook("s9", os.path.join(repo3, "a.py.bak"), [repo3], sessions_tmp())
check("a same-prefix FILE (not a directory) is not swept in as a false positive",
      "is ITSELF one of the" in message_of(out), False)


print("")
print("%d/%d checks passed" % (sum(1 for r in results if r), len(results)))
sys.exit(0 if all(results) else 1)
