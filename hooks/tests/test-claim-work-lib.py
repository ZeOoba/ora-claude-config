"""Standalone test for hooks/lib/claim_work.py. Drives the module directly (write/read/
release round-trip, TTL expiry, malformed-file fail-open) AND via its CLI subprocess
entry point, matching the house convention (see test-fleet-session-hook.py).
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
SCRIPT = os.path.join(os.path.dirname(HERE), "lib", "claim_work.py")
PY = sys.executable

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def load_module():
    spec = importlib.util.spec_from_file_location("claim_work_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(args, base_dir, session_id="cli-session-001"):
    env = dict(os.environ, ORA_ACTIVE_WORK_DIR=base_dir, CLAUDE_CODE_SESSION_ID=session_id)
    p = subprocess.run([PY, SCRIPT] + args, capture_output=True, env=env, timeout=30)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


cw = load_module()

# ===================================================================================
# BASIC: write_claim / read_active_claims round-trip
# ===================================================================================
print("== BASIC: write then read a claim ==")
root = tempfile.mkdtemp(prefix="claim-basic-")
path = cw.write_claim("hooks-override-auth", "sess-aaa", "hardening override token",
                       base_dir=root)
check("claim file created", os.path.isfile(path), True)
claims = cw.read_active_claims(base_dir=root)
check("one claim read back", len(claims), 1)
check("slug recovered", claims[0]["slug"], "hooks-override-auth")
check("session_id recovered", claims[0]["session_id"], "sess-aaa")
check("description recovered", claims[0]["description"], "hardening override token")
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# TTL: a claim older than ttl_minutes is dropped; one within it is kept
# ===================================================================================
print()
print("== TTL: expired claims are filtered out, live ones are kept ==")
root = tempfile.mkdtemp(prefix="claim-ttl-")
now = datetime.datetime(2026, 7, 25, 12, 0, 0)
old = now - datetime.timedelta(minutes=200)   # older than 120-min default TTL
fresh = now - datetime.timedelta(minutes=10)  # within it
cw.write_claim("stale-slug", "sess-old", "old work", base_dir=root, now=old)
cw.write_claim("fresh-slug", "sess-new", "fresh work", base_dir=root, now=fresh)
claims = cw.read_active_claims(base_dir=root, now=now)
slugs = sorted(c["slug"] for c in claims)
check("only the fresh claim survives the default 120-min TTL", slugs, ["fresh-slug"])
claims_wide = cw.read_active_claims(base_dir=root, ttl_minutes=300, now=now)
slugs_wide = sorted(c["slug"] for c in claims_wide)
check("both survive a wider TTL window", slugs_wide, ["fresh-slug", "stale-slug"])
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# RELEASE: release_claim removes the file; read_active_claims no longer sees it
# ===================================================================================
print()
print("== RELEASE: a released claim disappears from read_active_claims ==")
root = tempfile.mkdtemp(prefix="claim-release-")
cw.write_claim("temp-slug", "sess-bbb", "temp work", base_dir=root)
check("claim visible before release", len(cw.read_active_claims(base_dir=root)), 1)
ok = cw.release_claim("temp-slug", base_dir=root)
check("release_claim reports success", ok, True)
check("claim gone after release", len(cw.read_active_claims(base_dir=root)), 0)
ok2 = cw.release_claim("never-claimed-slug", base_dir=root)
check("releasing a nonexistent claim reports failure, not an exception", ok2, False)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# ROBUSTNESS: malformed file / missing directory / non-dict payload never crash
# ===================================================================================
print()
print("== ROBUSTNESS: malformed claim data is skipped, never raises ==")
root = tempfile.mkdtemp(prefix="claim-robust-")
os.makedirs(root, exist_ok=True)
with open(os.path.join(root, "corrupt.json"), "w", encoding="utf-8") as f:
    f.write("{not valid json")
with open(os.path.join(root, "notadict.json"), "w", encoding="utf-8") as f:
    json.dump(["a", "list", "not", "a", "dict"], f)
with open(os.path.join(root, "no-claimed-at.json"), "w", encoding="utf-8") as f:
    json.dump({"session_id": "x", "description": "missing timestamp"}, f)
cw.write_claim("valid-slug", "sess-ccc", "the only good one", base_dir=root)
claims = cw.read_active_claims(base_dir=root)
check("only the valid claim survives three malformed siblings",
      [c["slug"] for c in claims], ["valid-slug"])
shutil.rmtree(root, ignore_errors=True)

root2 = tempfile.mkdtemp(prefix="claim-nodir-")
shutil.rmtree(root2, ignore_errors=True)  # directory never created
claims_nodir = cw.read_active_claims(base_dir=root2)
check("missing claims directory returns [] rather than raising", claims_nodir, [])

# ===================================================================================
# FILENAME SAFETY: a slug with path-hostile characters can't escape the claims dir
# ===================================================================================
print()
print("== FILENAME SAFETY: hostile slug is sanitized, not a path escape ==")
root = tempfile.mkdtemp(prefix="claim-safety-")
hostile = "../../evil"
path = cw.write_claim(hostile, "sess-ddd", "path traversal attempt", base_dir=root)
check("sanitized path stays inside the claims dir",
      os.path.normpath(path).startswith(os.path.normpath(root)), True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# CLI: claim / list / release subcommands via subprocess, matching hook invocation
# ===================================================================================
print()
print("== CLI: claim, list, release round-trip via subprocess ==")
root = tempfile.mkdtemp(prefix="claim-cli-")
code, out, err = run_cli(["claim", "open-items-tracker", "appending OI-041"], root,
                          session_id="cli-sess-xyz12345")
check("claim subcommand exits 0", code, 0)
check("claim confirmation mentions the slug", "open-items-tracker" in out, True)
check("claim file landed on disk", os.path.isfile(os.path.join(root, "open-items-tracker.json")), True)

code, out, err = run_cli(["list"], root)
check("list subcommand exits 0", code, 0)
check("list output mentions the claimed slug", "open-items-tracker" in out, True)

code, out, err = run_cli(["release", "open-items-tracker"], root)
check("release subcommand exits 0", code, 0)
check("claim file removed after release",
      os.path.isfile(os.path.join(root, "open-items-tracker.json")), False)

code, out, err = run_cli(["list"], root)
check("list after release reports no active claims", "No active claims" in out, True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# RENEW (2026-08-04, OI-072 handoff near-miss): bump claimed_at on a claim THIS
# session already holds, without needing to re-supply title/paths/cwd.
# ===================================================================================
print()
print("== RENEW: bumping an own claim's timestamp, direct calls ==")
root = tempfile.mkdtemp(prefix="claim-renew-")
now = datetime.datetime(2026, 8, 4, 12, 0, 0)
old = now - datetime.timedelta(minutes=30)
cw.write_claim("repo-housekeeping", "sess-mine", "task 1", base_dir=root, now=old,
               paths=["a/b.py"])
orig_paths = cw.read_active_claims(base_dir=root, now=now)[0]["paths"]

pre = cw.renew_claim("repo-housekeeping", "sess-mine", base_dir=root, now=now)
check("renew_claim returns the pre-renewal claim", pre["description"], "task 1")
claims = cw.read_active_claims(base_dir=root, now=now)
check("renewed claim's age resets to ~0", round(claims[0]["age_minutes"], 3), 0.0)
check("renewed claim keeps its description when none given",
      claims[0]["description"], "task 1")
check("renewed claim keeps its (already-normalized) paths",
      claims[0]["paths"], orig_paths)

cw.renew_claim("repo-housekeeping", "sess-mine", description="task 2", base_dir=root,
               now=now)
claims = cw.read_active_claims(base_dir=root, now=now)
check("renew with a new description replaces it",
      claims[0]["description"], "task 2")

miss = cw.renew_claim("never-claimed", "sess-mine", base_dir=root, now=now)
check("renewing a slug with no live claim returns None", miss, None)

foreign = cw.renew_claim("repo-housekeeping", "sess-someone-else", base_dir=root, now=now)
check("renewing a DIFFERENT session's claim returns None (no takeover)", foreign, None)
claims = cw.read_active_claims(base_dir=root, now=now)
check("...and leaves the original claim's session_id untouched",
      claims[0]["session_id"], "sess-mine")
shutil.rmtree(root, ignore_errors=True)

print()
print("== FIND_CLAIM: single-slug lookup ==")
root = tempfile.mkdtemp(prefix="claim-find-")
cw.write_claim("hooks-override-auth", "sess-x", "hardening", base_dir=root)
found = cw.find_claim("hooks-override-auth", base_dir=root)
check("find_claim locates a live claim", found["session_id"], "sess-x")
check("find_claim returns None for an unclaimed slug",
      cw.find_claim("nope", base_dir=root), None)
shutil.rmtree(root, ignore_errors=True)

# Regression (2026-08-04 independent review, confidence 95): find_claim() originally
# compared the caller's RAW slug against read_active_claims()'s already-SANITIZED
# "slug" field (the on-disk filename stem). Every documented slug happens to already be
# filename-safe, so this passed every test above while being silently dead for any slug
# containing a character _safe_filename() maps to "_" -- exactly the "free-form,
# agent-supplied strings" the module's own docstring says slugs are.
print()
print("== FIND_CLAIM / RENEW / WARNING: a slug with a space (non-filename-safe) ==")
root = tempfile.mkdtemp(prefix="claim-nonalnum-")
SPACEY = "OI-072 cleanup"
cw.write_claim(SPACEY, "sess-mine", "task 1", base_dir=root)
spacey_found = cw.find_claim(SPACEY, base_dir=root)
check("find_claim locates a live claim under a spacey slug", spacey_found is not None, True)
check("...and it's the right one",
      (spacey_found or {}).get("session_id"), "sess-mine")
renewed = cw.renew_claim(SPACEY, "sess-mine", base_dir=root)
check("renew_claim succeeds on a spacey slug", renewed is not None, True)
shutil.rmtree(root, ignore_errors=True)

root = tempfile.mkdtemp(prefix="claim-nonalnum-cli-")
code, out, err = run_cli(["claim", SPACEY, "task 1"], root, session_id="cli-owner-spacey")
check("CLI claim on a spacey slug exits 0", code, 0)
code, out, err = run_cli(["renew", SPACEY], root, session_id="cli-owner-spacey")
check("CLI renew on a spacey slug exits 0 (not a dead-on-arrival 'no claim found')",
      code, 0)
code, out, err = run_cli(["claim", SPACEY, "different work"], root,
                         session_id="cli-intruder-spacey")
check("CLI claim-over on a spacey slug still exits 0 (fail-open)", code, 0)
check("...and DOES print the collision WARNING (previously silent for this slug)",
      "WARNING" in out, True)
shutil.rmtree(root, ignore_errors=True)

print()
print("== CLI: renew round-trip, and the ownership refusal ==")
root = tempfile.mkdtemp(prefix="claim-renew-cli-")
code, out, err = run_cli(["claim", "repo-housekeeping", "task 1"], root,
                          session_id="cli-owner-001")
check("initial claim exits 0", code, 0)

code, out, err = run_cli(["renew", "repo-housekeeping"], root, session_id="cli-owner-001")
check("renew (own claim) exits 0", code, 0)
check("renew confirmation mentions the slug", "repo-housekeeping" in out, True)
check("renew confirmation says 'Renewed'", "Renewed" in out, True)

code, out, err = run_cli(["renew", "repo-housekeeping", "--description", "task 2"],
                          root, session_id="cli-owner-001")
check("renew with --description exits 0", code, 0)
claims = cw.read_active_claims(base_dir=root)
check("renew --description updated the stored description",
      claims[0]["description"], "task 2")

code, out, err = run_cli(["renew", "repo-housekeeping"], root, session_id="cli-intruder")
check("renew by a DIFFERENT session exits nonzero", code != 0, True)
check("renew-by-stranger explains it's held by someone else",
      "different session" in out, True)

code, out, err = run_cli(["renew", "never-claimed-anywhere"], root,
                          session_id="cli-owner-001")
check("renew of an unclaimed slug exits nonzero", code != 0, True)
check("renew-of-nothing suggests 'claim' instead", "use 'claim'" in out, True)
shutil.rmtree(root, ignore_errors=True)

print()
print("== CLI: claim WARNS (not blocks) when overwriting a different live session ==")
root = tempfile.mkdtemp(prefix="claim-warn-cli-")
code, out, err = run_cli(["claim", "repo-housekeeping", "original work"], root,
                          session_id="cli-first-owner")
check("first claim exits 0", code, 0)

code, out, err = run_cli(["claim", "repo-housekeeping", "different work"], root,
                          session_id="cli-second-owner")
check("overwriting claim from a different session still exits 0 (fail-open)", code, 0)
check("...but prints a WARNING naming the collision", "WARNING" in out, True)
check("...mentioning the prior session's description", "original work" in out, True)
claims = cw.read_active_claims(base_dir=root)
check("the overwrite did land (fail-open, not fail-closed)",
      claims[0]["session_id"], "cli-second-owner")

code, out, err = run_cli(["claim", "repo-housekeeping", "still my work"], root,
                          session_id="cli-second-owner")
check("re-claiming one's OWN slug prints no collision warning", "WARNING" in out, False)
shutil.rmtree(root, ignore_errors=True)

print()
print("RESULT: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
