#!/usr/bin/env python3
"""Tests for dirty-file-owner-report.py -- the read-only "who owns each dirty
file" reporter (2026-08-12 close-out automation candidate; see
project_primary_checkout_main_move_blocked_2026-08-12.md).

Black-box, subprocess-driven against synthetic fixtures (own throwaway git
repo, own sessions dir with hand-written touched-files.txt, own claims dir
with hand-written claim JSON) -- matching the house convention (see
hooks/tests/test-shared-checkout-guard.py, maintenance/test-fleet-status.py).
No mocking of time: claim fixtures use claim_work.write_claim's own `now=`
param so ages are computed the same way the module under test computes them.

Run: python test-dirty-file-owner-report.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs + repo).
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "dirty-file-owner-report.py")
LIB_DIR = os.path.join(os.path.dirname(HERE), "hooks", "lib")
sys.path.insert(0, LIB_DIR)
import claim_work  # noqa: E402  (used to write fixture claims via the real module)

PY = sys.executable

# This process may inherit git worktree/index env vars from whatever invoked
# it (see hooks/tests/test-shared-checkout-guard.py's identical scrub) --
# strip them so subprocess git calls against the throwaway fixture repo below
# operate on THAT repo, not whatever outer checkout this test runs inside.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

_failures = []


def check(name, got, want):
    ok = got == want
    if ok:
        print("PASS " + name)
    else:
        print("FAIL " + name + "   (got %r, want %r)" % (got, want))
        _failures.append(name)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, text=True)


def make_repo():
    d = tempfile.mkdtemp(prefix="dfor-repo-")
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")
    with open(os.path.join(d, "README.md"), "w") as fh:
        fh.write("hello\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")
    return d


def dirty(repo, rel, content="wip\n"):
    path = os.path.join(repo, rel)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w") as fh:
        fh.write(content)
    return path


def record_touched(sessions_dir, sid, paths, ts=None):
    """Write sid's provenance touched-set exactly as commit-provenance-recorder.py
    does -- normcase(abspath(path))\\t<epoch> per line."""
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    when = ts if ts is not None else time.time()
    with open(os.path.join(d, "touched-files.txt"), "w", encoding="utf-8") as fh:
        for p in paths:
            fh.write("%s\t%.6f\n" % (os.path.normcase(os.path.abspath(p)), when))


def run_report(repo, sessions_dir, claims_dir, extra_args=None, env_extra=None):
    args = [PY, SCRIPT, "--repo", repo, "--sessions-dir", sessions_dir,
            "--claims-dir", claims_dir, "--json"]
    if extra_args:
        args += extra_args
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
    return proc.returncode, proc.stdout, proc.stderr


def by_path(report, rel):
    for f in report["files"]:
        if f["path"].replace("\\", "/") == rel.replace("\\", "/"):
            return f
    return None


# ===================================================================================
# BASIC: provenance attributes a dirty file to the touching session
# ===================================================================================
print("== BASIC: provenance attribution ==")
repo = make_repo()
sessions_dir = tempfile.mkdtemp(prefix="dfor-sess-")
claims_dir = tempfile.mkdtemp(prefix="dfor-claims-")

f1 = dirty(repo, "owned-by-a.txt")
f2 = dirty(repo, "untouched.txt")
record_touched(sessions_dir, "session-aaaaaaaa", [f1])

rc, out, err = run_report(repo, sessions_dir, claims_dir)
check("exit 0", (rc, err), (0, err))
report = json.loads(out)
check("total dirty files == 2", report["total_dirty"], 2)
a = by_path(report, "owned-by-a.txt")
check("owned-by-a.txt attributed to session-aaaaaaaa",
      a and a["owner"], "session-aaaaaaaa")
u = by_path(report, "untouched.txt")
check("untouched.txt has no owner", u and u["owner"], None)
check("sources all report available",
      report["sources"], {"provenance_available": True, "liveness_available": True,
                           "claims_available": True})


# ===================================================================================
# MULTI-SESSION: most-recent touch wins as owner; both hits recorded
# ===================================================================================
print()
print("== MULTI-SESSION: most recent provenance touch is the owner ==")
repo2 = make_repo()
sessions_dir2 = tempfile.mkdtemp(prefix="dfor-sess2-")
claims_dir2 = tempfile.mkdtemp(prefix="dfor-claims2-")
shared = dirty(repo2, "shared.txt")
now = time.time()
record_touched(sessions_dir2, "session-old0000", [shared], ts=now - 3600)
record_touched(sessions_dir2, "session-new0000", [shared], ts=now - 60)

rc, out, err = run_report(repo2, sessions_dir2, claims_dir2)
check("exit 0 (multi-session)", (rc, err), (0, err))
report2 = json.loads(out)
s = by_path(report2, "shared.txt")
check("owner is the MORE RECENT toucher", s["owner"], "session-new0000")
check("both sessions recorded in provenance list",
      sorted(p["session_id"] for p in s["provenance"]),
      ["session-new0000", "session-old0000"])


# ===================================================================================
# CLAIM-ONLY: no provenance, but a live claim's --paths covers the file
# ===================================================================================
print()
print("== CLAIM-ONLY: claim-declared path attributes with no provenance ==")
repo3 = make_repo()
sessions_dir3 = tempfile.mkdtemp(prefix="dfor-sess3-")
claims_dir3 = tempfile.mkdtemp(prefix="dfor-claims3-")
claimed = dirty(repo3, "claimed-only.txt")
claim_work.write_claim("some-slug", "session-claim001", "working on it",
                        base_dir=claims_dir3, paths=[claimed])

rc, out, err = run_report(repo3, sessions_dir3, claims_dir3)
check("exit 0 (claim-only)", (rc, err), (0, err))
report3 = json.loads(out)
c = by_path(report3, "claimed-only.txt")
check("owner comes from the claim when no provenance exists",
      c["owner"], "session-claim001")
check("claim slug recorded on the file entry",
      c["claims"][0]["slug"] if c["claims"] else None, "some-slug")


# ===================================================================================
# UNATTRIBUTED: neither provenance nor claim covers the file
# ===================================================================================
print()
print("== UNATTRIBUTED: no evidence at all ==")
repo4 = make_repo()
sessions_dir4 = tempfile.mkdtemp(prefix="dfor-sess4-")
claims_dir4 = tempfile.mkdtemp(prefix="dfor-claims4-")
dirty(repo4, "mystery.txt")

rc, out, err = run_report(repo4, sessions_dir4, claims_dir4)
report4 = json.loads(out)
m = by_path(report4, "mystery.txt")
check("unattributed file has owner None", m["owner"], None)
# also check the human-readable path renders an UNATTRIBUTED section
proc = subprocess.run([PY, SCRIPT, "--repo", repo4, "--sessions-dir", sessions_dir4,
                        "--claims-dir", claims_dir4],
                       capture_output=True, text=True, timeout=30)
check("text report names the file under UNATTRIBUTED",
      ("mystery.txt" in proc.stdout, "UNATTRIBUTED" in proc.stdout), (True, True))


# ===================================================================================
# RENAME: a porcelain rename line attributes the NEW path
# ===================================================================================
print()
print("== RENAME: attribution follows the new path, not the old one ==")
repo5 = make_repo()
sessions_dir5 = tempfile.mkdtemp(prefix="dfor-sess5-")
claims_dir5 = tempfile.mkdtemp(prefix="dfor-claims5-")
orig = os.path.join(repo5, "README.md")
renamed = os.path.join(repo5, "RENAMED.md")
git(repo5, "mv", "README.md", "RENAMED.md")
record_touched(sessions_dir5, "session-renamer", [renamed])

rc, out, err = run_report(repo5, sessions_dir5, claims_dir5)
report5 = json.loads(out)
check("exit 0 (rename)", (rc, err), (0, err))
r = by_path(report5, "RENAMED.md")
check("renamed file attributed via its NEW path",
      r and r["owner"], "session-renamer")
check("old path is not separately listed",
      by_path(report5, "README.md"), None)


# ===================================================================================
# DEGRADED SOURCE: a missing sessions directory is reported as UNAVAILABLE,
# not silently folded into a clean "0 attributed"
# ===================================================================================
print()
print("== DEGRADED: missing sessions dir is a caveat, not a silent zero ==")
repo6 = make_repo()
dirty(repo6, "orphan.txt")
missing_sessions_dir = os.path.join(tempfile.mkdtemp(prefix="dfor-sess6-"), "does-not-exist")
claims_dir6 = tempfile.mkdtemp(prefix="dfor-claims6-")

rc, out, err = run_report(repo6, missing_sessions_dir, claims_dir6)
report6 = json.loads(out)
check("exit 0 even with a missing sessions dir", (rc, err), (0, err))
check("provenance_available is False for a missing sessions dir",
      report6["sources"]["provenance_available"], False)
proc6 = subprocess.run([PY, SCRIPT, "--repo", repo6, "--sessions-dir", missing_sessions_dir,
                         "--claims-dir", claims_dir6],
                        capture_output=True, text=True, timeout=30)
check("text report surfaces a CAVEAT line for the missing source",
      ("CAVEAT" in proc6.stdout, "UNAVAILABLE" in proc6.stdout), (True, True))


# ===================================================================================
# CLEAN REPO: nothing dirty -> total 0, no crash
# ===================================================================================
print()
print("== CLEAN: a clean checkout reports zero dirty files ==")
repo7 = make_repo()
sessions_dir7 = tempfile.mkdtemp(prefix="dfor-sess7-")
claims_dir7 = tempfile.mkdtemp(prefix="dfor-claims7-")
rc, out, err = run_report(repo7, sessions_dir7, claims_dir7)
report7 = json.loads(out)
check("exit 0 (clean repo)", (rc, err), (0, err))
check("total_dirty == 0 on a clean repo", report7["total_dirty"], 0)


# ===================================================================================
# BAD REPO: not a git checkout at all -> exit 2, no traceback
# ===================================================================================
print()
print("== BAD REPO: a non-git directory exits 2 with a clear stderr message ==")
not_a_repo = tempfile.mkdtemp(prefix="dfor-notrepo-")
sessions_dir8 = tempfile.mkdtemp(prefix="dfor-sess8-")
claims_dir8 = tempfile.mkdtemp(prefix="dfor-claims8-")
rc, out, err = run_report(not_a_repo, sessions_dir8, claims_dir8)
check("exit 2 for a non-git directory", rc, 2)
check("stderr names the failure", "[ACTION]" in err, True)
check("stdout is empty on failure (no partial/garbled report)", out.strip(), "")


# ===================================================================================
# CLAIM TTL: an expired claim (beyond --ttl-minutes) does not attribute
# ===================================================================================
print()
print("== CLAIM TTL: a claim older than --ttl-minutes is not used for attribution ==")
repo9 = make_repo()
sessions_dir9 = tempfile.mkdtemp(prefix="dfor-sess9-")
claims_dir9 = tempfile.mkdtemp(prefix="dfor-claims9-")
old_claim_file = dirty(repo9, "old-claim.txt")
# 200 days: older than the explicit 120-MINUTE override tested below, but
# still inside the report's own ~365-day (525600-minute) default TTL.
old_now = datetime.datetime.now() - datetime.timedelta(days=200)
claim_work.write_claim("ancient-slug", "session-ancient", "long done",
                        base_dir=claims_dir9, paths=[old_claim_file], now=old_now)

rc, out, err = run_report(repo9, sessions_dir9, claims_dir9,
                           extra_args=["--ttl-minutes", "120"])
report9 = json.loads(out)
oc = by_path(report9, "old-claim.txt")
check("a claim older than --ttl-minutes does not attribute the file",
      oc["owner"], None)
# ...but the same claim IS honored under this report's own generous default TTL
rc, out, err = run_report(repo9, sessions_dir9, claims_dir9)
report9b = json.loads(out)
oc2 = by_path(report9b, "old-claim.txt")
check("the default (report-scoped) TTL is wide enough to still see it",
      oc2["owner"], "session-ancient")


print()
if _failures:
    print("FAILURES: %d" % len(_failures))
    for f in _failures:
        print("  - " + f)
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
