"""Standalone test for shared-checkout-guard.py's SELF-RENEWAL side effect.

WHY THIS EXISTS (2026-08-04): claim_work.py's `renew` CLI subcommand (added the same
day) only helps a claim stay accurate if a session remembers to call it -- and the
incident that motivated building `renew` in the first place was exactly a session NOT
remembering: a claim's `claimed_at` sat untouched while the claiming session moved on to
a second task under the same slug, and a reader (another session) misjudged the
resulting stale timestamp as "abandoned" and reclaimed the slug. Manual habit-adoption
recreates the same failure mode it exists to fix.

This closes the gap WITHOUT requiring the agent to remember anything: shared-checkout-
guard.py (already PreToolUse-bound on every Edit/Write/MultiEdit, already importing
claim_work.py for the file-collision check test-claim-file-collision.py covers) now also
bumps `claimed_at` on any LIVE claim the CALLING session already holds, whenever that
session edits a file inside one of the claim-relevant shared repos and the claim has
gone stale past a threshold (CLAIM_RENEW_AFTER_MINUTES, default 20). This is a
categorically SAFER automation than auto-CLAIMING would be (deliberately rejected in
claim_work.py's own docstring: "classifying non-trivial hook work from a single tool
call has too high a false positive/negative rate") -- renewing an ALREADY-OWNED claim
requires no judgment call about whether new work is claim-worthy, only "does this
session already hold a live claim, and is it still editing."

Rate-limiting is free: a renewal resets a claim's age to ~0, so the age-threshold gate
itself blocks further writes until the threshold elapses again -- no separate rate-limit
state needed, and this is asserted directly below (a claim younger than the threshold is
NOT rewritten).

Critically, this must fire even when the rest of the hook's own logic would otherwise
early-return silently (clean repo, or editing inside an already-isolated linked
worktree) -- isolated-worktree editing is this codebase's OWN mandated workflow for
hooks/** work, so if self-renewal only fired on the warn path, it would almost never
fire for well-behaved sessions, which is precisely backwards.

Drives claim_work.py directly and shared-checkout-guard.py as a subprocess over stdin,
matching the house convention (test-claim-work-lib.py, test-claim-file-collision.py).
"""
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
CLAIM_LIB = os.path.join(HOOKS, "lib", "claim_work.py")
GUARD = os.path.join(HOOKS, "shared-checkout-guard.py")
PY = sys.executable

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def load_claim_work():
    spec = importlib.util.spec_from_file_location("claim_work_srn", CLAIM_LIB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cw = load_claim_work()


def run_guard(file_path, session_id, claims_dir, repo, renew_after=None,
             sessions_dir=None):
    env = dict(os.environ,
               SHARED_CHECKOUT_SESSIONS_DIR=sessions_dir or tempfile.mkdtemp(prefix="srn-sess-"),
               ORA_ACTIVE_WORK_DIR=claims_dir,
               SHARED_CHECKOUT_REPOS=repo,
               ORA_FLEET_SESSIONS_DIR="C:/does/not/exist_srn_sessions_dir")
    if renew_after is not None:
        env["CLAIM_RENEW_AFTER_MINUTES"] = str(renew_after)
    payload = json.dumps({"session_id": session_id,
                          "tool_input": {"file_path": file_path}})
    p = subprocess.run([PY, GUARD], input=payload.encode("utf-8"),
                       capture_output=True, env=env, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def make_repo():
    """A real git checkout with a CLEAN status -- the case this feature must still
    fire on, since a clean repo is exactly where the rest of the hook's own logic
    silently early-returns with nothing to warn about."""
    d = tempfile.mkdtemp(prefix="srn-repo-")
    subprocess.run(["git", "init", "-q", d], capture_output=True, timeout=30)
    f = os.path.join(d, "SKILL.md")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("spec\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True, timeout=30)
    subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], capture_output=True, timeout=30)
    return d, f


def raw_claimed_at(claims_dir, slug):
    """The exact stored claimed_at STRING, read directly off disk -- NOT
    age_minutes (which is recomputed against real wall-clock time on every read,
    so it alone cannot distinguish 'was rewritten a moment ago' from 'was never
    touched and is coincidentally still fresh'). Comparing this string
    before/after a guard invocation is the only way to prove a write did or
    did not happen."""
    path = cw.claim_path(slug, claims_dir)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["claimed_at"]


# ===================================================================================
# A claim OLDER than the threshold gets renewed by an edit inside the claimed repo,
# even though the repo is clean and the rest of the hook has nothing to warn about.
# ===================================================================================
print("== SELF-RENEW: a stale own-claim is bumped by an edit in a clean repo ==")
repo, target = make_repo()
claims = tempfile.mkdtemp(prefix="srn-claims-a-")
old = datetime.datetime.now() - datetime.timedelta(minutes=5)
cw.write_claim("repo-housekeeping", "renew-me-01", "task 1", base_dir=claims, now=old)
before = raw_claimed_at(claims, "repo-housekeeping")

code, out, err = run_guard(target, "renew-me-01", claims, repo, renew_after=1)
check("guard still exits 0", code, 0)
after = raw_claimed_at(claims, "repo-housekeeping")
check("a stale own-claim's claimed_at changes (was renewed)", after != before, True)
age_after = cw.read_active_claims(base_dir=claims)[0]["age_minutes"]
check("...and its age drops back near zero", age_after < 1.0, True)
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

# ===================================================================================
# A claim YOUNGER than the threshold must NOT be rewritten -- this IS the rate limit
# (no separate throttle state; the age gate itself blocks further writes).
# ===================================================================================
print()
print("== SELF-RENEW: a fresh own-claim (under threshold) is left untouched ==")
repo, target = make_repo()
claims = tempfile.mkdtemp(prefix="srn-claims-b-")
cw.write_claim("repo-housekeeping", "renew-me-02", "task 1", base_dir=claims)
before = raw_claimed_at(claims, "repo-housekeeping")

code, out, err = run_guard(target, "renew-me-02", claims, repo, renew_after=20)
after = raw_claimed_at(claims, "repo-housekeeping")
check("a fresh own-claim's claimed_at is unchanged (no needless write)",
      after, before)
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

# ===================================================================================
# A DIFFERENT session's stale claim must NEVER be touched -- only the calling
# session's OWN claim(s) are eligible. This is not a takeover mechanism.
# ===================================================================================
print()
print("== SELF-RENEW: a different session's stale claim is never touched ==")
repo, target = make_repo()
claims = tempfile.mkdtemp(prefix="srn-claims-c-")
old = datetime.datetime.now() - datetime.timedelta(minutes=5)
cw.write_claim("repo-housekeeping", "someone-else-03", "their work",
               base_dir=claims, now=old)
before = raw_claimed_at(claims, "repo-housekeeping")

code, out, err = run_guard(target, "not-the-owner-03", claims, repo, renew_after=1)
after = raw_claimed_at(claims, "repo-housekeeping")
check("a different session's claim is never renewed on someone else's edit",
      after, before)
claims_after = cw.read_active_claims(base_dir=claims)
check("...and it still belongs to the original session",
      claims_after[0]["session_id"], "someone-else-03")
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

# ===================================================================================
# MULTIPLE own claims (different slugs) all get renewed by one edit.
# ===================================================================================
print()
print("== SELF-RENEW: all of the session's own stale claims are bumped, not just one ==")
repo, target = make_repo()
claims = tempfile.mkdtemp(prefix="srn-claims-d-")
old = datetime.datetime.now() - datetime.timedelta(minutes=5)
cw.write_claim("repo-housekeeping", "multi-me-04", "task A", base_dir=claims, now=old)
cw.write_claim("hooks-override-auth", "multi-me-04", "task B", base_dir=claims, now=old)
code, out, err = run_guard(target, "multi-me-04", claims, repo, renew_after=1)
ages = {c["slug"]: c["age_minutes"] for c in cw.read_active_claims(base_dir=claims)}
check("both of this session's own claims were renewed",
      all(a < 1.0 for a in ages.values()), True)
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

# ===================================================================================
# CRITICAL: self-renewal must fire even inside an ALREADY-ISOLATED linked worktree --
# the exact case where the rest of the hook's own logic silently does nothing at all
# (is_linked_worktree() early return), and precisely the workflow this codebase
# mandates for hooks/** work. If self-renewal only fired on the warn path, it would
# almost never fire for a well-behaved session.
# ===================================================================================
print()
print("== SELF-RENEW: fires inside an isolated linked worktree, not just the main checkout ==")
main_repo, _ = make_repo()
wt_dir = os.path.join(main_repo, "worktrees", "isolated-wt")
subprocess.run(["git", "-C", main_repo, "worktree", "add", wt_dir, "-b", "srn-test-branch"],
               capture_output=True, timeout=30)
wt_file = os.path.join(wt_dir, "SKILL.md")
claims = tempfile.mkdtemp(prefix="srn-claims-e-")
old = datetime.datetime.now() - datetime.timedelta(minutes=5)
cw.write_claim("repo-housekeeping", "wt-me-05", "task 1", base_dir=claims, now=old)
before = raw_claimed_at(claims, "repo-housekeeping")

code, out, err = run_guard(wt_file, "wt-me-05", claims, main_repo, renew_after=1)
check("editing inside a linked worktree exits 0 and stays silent (no warning)",
      (code, out.strip()), (0, ""))
after = raw_claimed_at(claims, "repo-housekeeping")
check("...but the claim was STILL renewed", after != before, True)
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(main_repo, ignore_errors=True)

# ===================================================================================
# Self-renewal must be entirely skipped for a file OUTSIDE any claim-relevant repo --
# no claim_work read at all, matching the existing fast-path philosophy. Cheapest way
# to assert "was skipped" here: a claim that WOULD be eligible (same session, stale)
# stays untouched when the edited file is unrelated to any configured shared repo.
# ===================================================================================
print()
print("== SELF-RENEW: skipped entirely for files outside any shared/claimed repo ==")
outside_dir = tempfile.mkdtemp(prefix="srn-outside-")
outside_file = os.path.join(outside_dir, "unrelated.md")
with open(outside_file, "w", encoding="utf-8") as fh:
    fh.write("x\n")
claims = tempfile.mkdtemp(prefix="srn-claims-f-")
old = datetime.datetime.now() - datetime.timedelta(minutes=5)
cw.write_claim("repo-housekeeping", "outside-me-06", "task 1", base_dir=claims, now=old)
before = raw_claimed_at(claims, "repo-housekeeping")
# repo="" -> SHARED_CHECKOUT_REPOS empty -> find_repo() can never match anything
code, out, err = run_guard(outside_file, "outside-me-06", claims, repo="", renew_after=1)
after = raw_claimed_at(claims, "repo-housekeeping")
check("editing a file outside every configured repo leaves the claim untouched",
      after, before)
shutil.rmtree(claims, ignore_errors=True)
shutil.rmtree(outside_dir, ignore_errors=True)

# ===================================================================================
# Fail-open: an unreadable/missing claims dir must not break the edit or raise.
# ===================================================================================
print()
print("== SELF-RENEW: fail-open on a missing claims dir ==")
repo, target = make_repo()
code, out, err = run_guard(target, "whoever-07",
                           os.path.join(tempfile.mkdtemp(prefix="srn-g-"), "does-not-exist"),
                           repo, renew_after=1)
check("missing claims dir still exits 0", code, 0)
check("...with no traceback on stderr", "Traceback" in err, False)
shutil.rmtree(repo, ignore_errors=True)

print()
print("RESULT: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
