"""Standalone test for the EXPIRED-CLAIM CLOBBER defect in hooks/lib/claim_work.py.

WHY THIS EXISTS (2026-09-10, Gabriel-reported, hit live): a `claim` from a different
session destroyed session c2673895's `repo-housekeeping` claim at exit 0, with no
REFUSED line and nothing for `restore` to put back -- it had to be hand-reinstated by
rewriting the JSON.

The 2026-08-09 refusal gate looked like it already covered this. It does not, and the
reason is a ONE-LINE blind spot rather than a policy gap:

    existing = find_claim(args.slug)      # <- TTL-FILTERED

find_claim() is a thin wrapper over read_active_claims(), which SKIPS any claim past
its TTL (120 min default, 30 for `sched-`), future-dated, or carrying an unparseable
`claimed_at`. Such a claim file is still ON DISK and still the slug's only record --
but to `claim` it reads as "no claim here at all", so BOTH protections miss it:

  * the refusal gate never fires (nothing to collide with), and -- the load-bearing
    half --
  * `prior_claim` is never recorded, because that expression is also keyed on
    `existing`. The file is overwritten and the displaced session's description,
    paths, host id and timestamp are gone. `restore` then correctly reports "nothing
    to restore", because nothing was ever recorded.

So the defect is NOT "expired claims should block" -- they must not; fail-open on
expiry is ratified doctrine (a crashed session must never wedge a slug). The defect is
that displacement was SILENT and IRRECOVERABLE. The fix is Gabriel's second option:
record a superseded entry on EVERY displacement, expired ones included, and say so at
the point of displacement.

Same blind spot, same fix, in `restore`: its own `current = find_claim(...)` meant a
restore over an expired claim destroyed it with no record either.

REGRESSION HALF: the live-claim refusal, the --force takeover and the
carry-forward-your-own-prior_claim behaviours must all be unchanged. Cases 6-9 pin
them here so this file fails if the fix widened into a policy change.

Drives the claim_work.py CLI as a subprocess (exit codes are half the contract),
matching test-claim-work-lib.py's convention.
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
SCRIPT = os.path.join(HOOKS, "lib", "claim_work.py")
PY = sys.executable

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def load_module():
    spec = importlib.util.spec_from_file_location("claim_work_clobber", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(args, base_dir, session_id="cli-session-001", host_session_id=None):
    env = dict(os.environ, ORA_ACTIVE_WORK_DIR=base_dir,
               CLAUDE_CODE_SESSION_ID=session_id)
    env.pop("CLAUDE_CODE_HOST_SESSION_ID", None)
    if host_session_id is not None:
        env["CLAUDE_CODE_HOST_SESSION_ID"] = host_session_id
    p = subprocess.run([PY, SCRIPT] + args, capture_output=True, env=env, timeout=30)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def age_claim(base_dir, slug, minutes):
    """Backdate `slug`'s claimed_at by `minutes` -- the ONLY way to make a claim
    expire without sleeping through a 120-minute TTL."""
    path = os.path.join(base_dir, slug + ".json")
    with open(path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    d["claimed_at"] = (datetime.datetime.now() -
                       datetime.timedelta(minutes=minutes)).strftime(
                           "%Y-%m-%dT%H:%M:%S")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return d["claimed_at"]


def read_file(base_dir, slug):
    with open(os.path.join(base_dir, slug + ".json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


cw = load_module()


# ===================================================================================
# 1. THE DEFECT: a plain `claim` over an EXPIRED foreign claim must still record it
# ===================================================================================
print("== 1. plain claim over an EXPIRED foreign claim ==")
root = tempfile.mkdtemp(prefix="claim-clobber-1-")
cw.write_claim("repo-housekeeping", "sess-AAA", "land 9 agents/ files",
               paths=[os.path.join(root, "agents")], base_dir=root,
               host_session_id="local_aaaa")
was = age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 60)

rc, out, _ = run_cli(["claim", "repo-housekeeping", "unrelated cleanup",
                      "--paths", os.path.join(root, "docs")],
                     root, session_id="sess-BBB")
# Fail-OPEN on expiry is deliberate: an expired claim must never deny the slug.
check("expired claim does NOT block (exit 0)", rc, 0)
check("displacement is announced, not silent", "EXPIRED" in out, True)
check("output points at restore", "restore repo-housekeeping" in out, True)

d = read_file(root, "repo-housekeeping")
check("slug now held by the new session", d["session_id"], "sess-BBB")
check("displaced claim recorded in prior_claim", "prior_claim" in d, True)
check("prior_claim names the displaced session",
      (d.get("prior_claim") or {}).get("session_id"), "sess-AAA")
check("prior_claim keeps the displaced description",
      (d.get("prior_claim") or {}).get("description"), "land 9 agents/ files")
check("prior_claim keeps the displaced timestamp verbatim",
      (d.get("prior_claim") or {}).get("claimed_at"), was)
check("prior_claim keeps the displaced host id",
      (d.get("prior_claim") or {}).get("host_session_id"), "local_aaaa")
check("prior_claim keeps the displaced paths",
      bool((d.get("prior_claim") or {}).get("paths")), True)
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 2. ... and `restore` can actually put it back (the recovery half)
# ===================================================================================
print("== 2. restore recovers a claim displaced without --force ==")
root = tempfile.mkdtemp(prefix="claim-clobber-2-")
cw.write_claim("repo-housekeeping", "sess-AAA", "land 9 agents/ files",
               paths=[os.path.join(root, "agents")], base_dir=root)
age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 60)
run_cli(["claim", "repo-housekeeping", "unrelated cleanup"], root,
        session_id="sess-BBB")

rc, out, _ = run_cli(["restore", "repo-housekeeping"], root, session_id="sess-BBB")
check("restore succeeds (exit 0)", rc, 0)
d = read_file(root, "repo-housekeeping")
check("slug handed back to the displaced session", d["session_id"], "sess-AAA")
check("restored description is the displaced one", d["description"],
      "land 9 agents/ files")
check("restore consumed the undo record", "prior_claim" in d, False)
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 3. A claim with an UNPARSEABLE claimed_at is invisible to find_claim() too
# ===================================================================================
print("== 3. claim over a file with an unparseable claimed_at ==")
root = tempfile.mkdtemp(prefix="claim-clobber-3-")
cw.write_claim("hooks-override-auth", "sess-AAA", "gate hardening", base_dir=root)
path = os.path.join(root, "hooks-override-auth.json")
with open(path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)
raw["claimed_at"] = "not-a-timestamp"
with open(path, "w", encoding="utf-8") as fh:
    json.dump(raw, fh)

rc, out, _ = run_cli(["claim", "hooks-override-auth", "other work"], root,
                     session_id="sess-BBB")
check("unparseable-timestamp claim does not block", rc, 0)
d = read_file(root, "hooks-override-auth")
check("unparseable-timestamp claim is still preserved",
      (d.get("prior_claim") or {}).get("session_id"), "sess-AAA")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 4. A FUTURE-dated claim is skipped by read_active_claims() as well
# ===================================================================================
print("== 4. claim over a FUTURE-dated claim ==")
root = tempfile.mkdtemp(prefix="claim-clobber-4-")
cw.write_claim("repo-housekeeping", "sess-AAA", "clock-skewed claim", base_dir=root)
age_claim(root, "repo-housekeeping", -240)  # 4 hours in the FUTURE
rc, out, _ = run_cli(["claim", "repo-housekeeping", "other work"], root,
                     session_id="sess-BBB")
check("future-dated claim does not block", rc, 0)
d = read_file(root, "repo-housekeeping")
check("future-dated claim is still preserved",
      (d.get("prior_claim") or {}).get("session_id"), "sess-AAA")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 5. `restore` over an EXPIRED claim preserves it in turn (same blind spot)
# ===================================================================================
print("== 5. restore over an expired third-party claim ==")
root = tempfile.mkdtemp(prefix="claim-clobber-5-")
# A forces over B, so the file carries a restorable prior_claim naming B...
cw.write_claim("repo-housekeeping", "sess-BBB", "B's work", base_dir=root)
run_cli(["claim", "repo-housekeeping", "A's takeover", "--force"], root,
        session_id="sess-AAA")
check("setup: A holds it, B is restorable",
      (read_file(root, "repo-housekeeping").get("prior_claim") or {}).get(
          "session_id"), "sess-BBB")
# ... then A's claim ages out, and someone runs restore.
age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 60)
rc, out, _ = run_cli(["restore", "repo-housekeeping"], root, session_id="sess-CCC")
check("restore over an expired claim is not blocked", rc, 0)
d = read_file(root, "repo-housekeeping")
check("B is back", d["session_id"], "sess-BBB")
check("A's displaced claim is preserved in turn",
      (d.get("prior_claim") or {}).get("session_id"), "sess-AAA")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 6. REGRESSION: a LIVE foreign claim is still REFUSED, and still writes nothing
# ===================================================================================
print("== 6. REGRESSION: live foreign claim still refused ==")
root = tempfile.mkdtemp(prefix="claim-clobber-6-")
cw.write_claim("repo-housekeeping", "sess-AAA", "live work",
               paths=[os.path.join(root, "a.py")], base_dir=root)
rc, out, _ = run_cli(["claim", "repo-housekeeping", "mine",
                      "--paths", os.path.join(root, "b.py")],
                     root, session_id="sess-BBB")
check("live claim refused (exit 3)", rc, cw.EXIT_CLAIM_REFUSED)
check("refusal says REFUSED", "REFUSED" in out, True)
check("disjoint paths still do NOT downgrade the refusal",
      "do NOT overlap" in out, True)
check("nothing was written", read_file(root, "repo-housekeeping")["session_id"],
      "sess-AAA")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 7. REGRESSION: --force over a LIVE claim still preserves + reports the takeover
# ===================================================================================
print("== 7. REGRESSION: --force over a live claim ==")
root = tempfile.mkdtemp(prefix="claim-clobber-7-")
cw.write_claim("repo-housekeeping", "sess-AAA", "live work", base_dir=root)
rc, out, _ = run_cli(["claim", "repo-housekeeping", "mine", "--force"], root,
                     session_id="sess-BBB")
check("force succeeds", rc, 0)
check("force still labelled a TAKEOVER", "FORCED TAKEOVER" in out, True)
check("forced takeover still preserves the displaced claim",
      (read_file(root, "repo-housekeeping").get("prior_claim") or {}).get(
          "session_id"), "sess-AAA")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 8. REGRESSION: re-claiming YOUR OWN expired claim is not a displacement
# ===================================================================================
print("== 8. REGRESSION: re-claiming your own expired claim ==")
root = tempfile.mkdtemp(prefix="claim-clobber-8-")
# Own claim, expired, carrying a prior_claim from an earlier takeover.
cw.write_claim("repo-housekeeping", "sess-BBB", "earlier work", base_dir=root)
run_cli(["claim", "repo-housekeeping", "took it over", "--force"], root,
        session_id="sess-AAA")
age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 60)
rc, out, _ = run_cli(["claim", "repo-housekeeping", "still me, updated desc"], root,
                     session_id="sess-AAA")
check("own expired re-claim succeeds", rc, 0)
check("own expired re-claim is NOT reported as a displacement",
      "EXPIRED" in out, False)
d = read_file(root, "repo-housekeeping")
check("own re-claim does not record ITSELF as prior",
      (d.get("prior_claim") or {}).get("session_id"), "sess-BBB")
check("description updated", d["description"], "still me, updated desc")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 9. REGRESSION: a fresh slug with no claim file at all stays quiet
# ===================================================================================
print("== 9. REGRESSION: brand-new slug ==")
root = tempfile.mkdtemp(prefix="claim-clobber-9-")
rc, out, _ = run_cli(["claim", "brand-new-slug", "first claim"], root,
                     session_id="sess-AAA")
check("fresh claim succeeds", rc, 0)
check("fresh claim reports no displacement", "EXPIRED" in out, False)
check("fresh claim has no prior_claim",
      "prior_claim" in read_file(root, "brand-new-slug"), False)
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 10. read_stale_claim(): the helper's own contract
# ===================================================================================
print("== 10. read_stale_claim() contract ==")
root = tempfile.mkdtemp(prefix="claim-clobber-10-")
check("no file -> None", cw.read_stale_claim("nope", base_dir=root), None)
cw.write_claim("repo-housekeeping", "sess-AAA", "live", base_dir=root)
check("LIVE claim -> None (find_claim already sees it)",
      cw.read_stale_claim("repo-housekeeping", base_dir=root), None)
age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 1)
stale = cw.read_stale_claim("repo-housekeeping", base_dir=root)
check("expired claim -> a view", (stale or {}).get("session_id"), "sess-AAA")
check("view carries an age", isinstance((stale or {}).get("age_minutes"), float),
      True)
# A `sched-` claim expires at the SHORTER TTL, so the helper must honour it too --
# otherwise an unattended claim between 30 and 120 minutes old is live to neither
# reader and clobberable again.
cw.write_claim("sched-nightly", "sess-CCC", "unattended", base_dir=root)
age_claim(root, "sched-nightly", cw.SCHED_TTL_MINUTES + 5)
check("sched- claim uses the SHORT ttl",
      (cw.read_stale_claim("sched-nightly", base_dir=root) or {}).get(
          "session_id"), "sess-CCC")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 11. `release` names the ACTUAL cause of a displacement, not always "--force"
#     (independent-review finding, 2026-09-10: an expired displacement is now the
#     COMMON case that leaves a prior_claim behind, and `release`'s refusal used to
#     blame "your '--force' takeover" for it -- false, and misleading about what
#     actually happened and why --force is not the fix.)
# ===================================================================================
print("== 11. release names the real displacement cause ==")
root = tempfile.mkdtemp(prefix="claim-clobber-11-")
cw.write_claim("repo-housekeeping", "sess-AAA", "A's work", base_dir=root)
age_claim(root, "repo-housekeeping", cw.DEFAULT_TTL_MINUTES + 60)
run_cli(["claim", "repo-housekeeping", "B's work"], root, session_id="sess-BBB")
rc, out, _ = run_cli(["release", "repo-housekeeping"], root, session_id="sess-BBB")
check("release refuses (the record is still there to protect)", rc,
      cw.EXIT_CLAIM_REFUSED)
check("...but does NOT blame --force for an expired displacement",
      "--force' takeover displaced" in out, False)
check("...and names the real cause instead", "EXPIRED" in out, True)
check("...and still points at restore (this one names a real session)",
      "restore repo-housekeeping" in out, True)
d = read_file(root, "repo-housekeeping")
check("nothing was deleted", d["session_id"], "sess-BBB")
check("prior_claim survives the refused release", "prior_claim" in d, True)

# The genuine --force case must still read as a --force takeover.
root2 = tempfile.mkdtemp(prefix="claim-clobber-11b-")
cw.write_claim("repo-housekeeping", "sess-AAA", "A's live work", base_dir=root2)
run_cli(["claim", "repo-housekeeping", "B forces", "--force"], root2,
        session_id="sess-BBB")
rc, out, _ = run_cli(["release", "repo-housekeeping"], root2, session_id="sess-BBB")
check("genuine --force takeover: release still names it correctly",
      "--force' takeover displaced" in out, True)
shutil.rmtree(root, ignore_errors=True)
shutil.rmtree(root2, ignore_errors=True)


# ===================================================================================
# 12. An expired displacement over an UNATTRIBUTABLE claim never advertises a
#     'restore' that will refuse it (independent-review finding, 2026-09-10)
# ===================================================================================
print("== 12. expired + unattributable displacement gives honest recovery advice ==")
root = tempfile.mkdtemp(prefix="claim-clobber-12-")
path = os.path.join(root, "repo-housekeeping.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump({"session_id": "?", "description": "legacy claim, no session",
               "title": "repo-housekeeping", "cwd": "", "paths": [],
               "claimed_at": (datetime.datetime.now() -
                              datetime.timedelta(
                                  minutes=cw.DEFAULT_TTL_MINUTES + 60)
                              ).strftime("%Y-%m-%dT%H:%M:%S")}, fh)
rc, out, _ = run_cli(["claim", "repo-housekeeping", "new work"], root,
                     session_id="sess-CCC")
check("expired+unattributable displacement does not block", rc, 0)
check("does NOT advertise a restore that will refuse", "restore repo-housekeeping"
      in out, False)
check("says why: no session to restore it to", "manual recovery" in out, True)
d = read_file(root, "repo-housekeeping")
check("the legacy metadata is preserved anyway",
      (d.get("prior_claim") or {}).get("description"), "legacy claim, no session")
rc2, out2, _ = run_cli(["restore", "repo-housekeeping"], root, session_id="sess-CCC")
check("...and restore does in fact refuse it, confirming the advice was honest",
      rc2, 1)
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 13. read_prior_claim_reason() contract
# ===================================================================================
print("== 13. read_prior_claim_reason() contract ==")
root = tempfile.mkdtemp(prefix="claim-clobber-13-")
check("no file -> ''", cw.read_prior_claim_reason("nope", base_dir=root), "")
cw.write_claim("s", "sess-AAA", "live", base_dir=root)
check("no displacement recorded -> ''",
      cw.read_prior_claim_reason("s", base_dir=root), "")
run_cli(["claim", "s", "forced", "--force"], root, session_id="sess-BBB")
check("--force takeover -> 'force'", cw.read_prior_claim_reason("s", base_dir=root),
      "force")
shutil.rmtree(root, ignore_errors=True)


# ===================================================================================
# 14. renew_claim() carries `prior_claim_reason` forward, same as `prior_claim`
#     (independent-review finding, 2026-09-10: renew_claim() re-read `prior_claim`
#     from disk on every renewal but not its sibling `prior_claim_reason`, so
#     shared-checkout-guard.py's ~20-minute self-renewal erased the reason on the
#     very next cycle -- release's refusal then fell back to the generic wording
#     ("a claim it displaced") instead of the correct, specific one.)
# ===================================================================================
print("== 14. renew_claim() carries prior_claim_reason forward ==")
root = tempfile.mkdtemp(prefix="claim-clobber-14-")
cw.write_claim("s", "sess-AAA", "live", base_dir=root)
run_cli(["claim", "s", "forced", "--force"], root, session_id="sess-BBB")
check("precondition: reason is 'force' right after the takeover",
      cw.read_prior_claim_reason("s", base_dir=root), "force")
cw.renew_claim("s", "sess-BBB", base_dir=root)
check("reason survives a renewal", cw.read_prior_claim_reason("s", base_dir=root),
      "force")
rc, out, _ = run_cli(["release", "s"], root, session_id="sess-BBB")
check("release still names the real cause after a renewal",
      "--force' takeover displaced" in out, True)
shutil.rmtree(root, ignore_errors=True)


print("")
print("%d/%d checks passed" % (sum(1 for r in results if r), len(results)))
sys.exit(0 if all(results) else 1)
