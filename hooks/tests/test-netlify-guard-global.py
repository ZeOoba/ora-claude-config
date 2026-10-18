"""Regression tests for hooks/bin/netlify-guard-global.js (Hard Invariant 2 wrapper:
production netlify deploys need a single-use override token) and for the `ntl` alias
shims emitted by maintenance/patch-global-netlify-shim.js.

Run: python test-netlify-guard-global.py
Stdlib only + node. ASCII-only. Self-contained.

Safety: the guard is only ever driven with NETLIFY_GUARD_DRY_RUN=1, so the real
netlify-cli is never executed. Fake tokens are minted only inside a TemporaryDirectory.
Argv strings that would read as a production deploy are built from fragments.

Override seams (for mutation checks only; unset in normal runs):
  NGG_TEST_GUARD    path of an alternate guard copy to test instead of the real one
  NGG_TEST_PATCHER  path of an alternate patcher copy

If node is not installed the suite prints the `CANNOT RUN:` sentinel (ENV-SKIP for the
pre-push hook-tests gate) and exits 2.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)
GUARD = os.environ.get("NGG_TEST_GUARD") or os.path.join(HERE, "bin", "netlify-guard-global.js")
PATCHER = os.environ.get("NGG_TEST_PATCHER") or os.path.join(
    REPO, "maintenance", "patch-global-netlify-shim.js")
CHECK = os.path.join(HERE, "lib", "check_website_deploy.py")

NODE = shutil.which("node")
if not NODE:
    print("CANNOT RUN: node is not on PATH")
    sys.exit(2)

# Fragments, so no literal production-deploy command text appears in this file.
D = "".join(["dep", "loy"])
PR = "--" + "".join(["pro", "d"])
SHORT = "-" + "p"

FAKE_SESSION = "11111111-2222-3333-4444-555555555555"


def prod(*a):
    return (list(a), "prod")


def notprod(*a):
    return (list(a), "not prod")


CASES = [
    # --- deploy: production forms
    prod(D, PR),
    prod(D, SHORT),
    prod(D, "-Op"),
    prod(D, "-pO"),
    prod(D, "-p=true"),
    prod(D, PR + "=true"),
    prod(D, PR + "-if-unlocked"),
    prod(D, PR.upper()),
    prod(D, "--trigger"),
    prod(D, "--trigger=1"),
    prod(D, "-ap"),
    prod("--debug", D, "--build", PR),
    prod(D.capitalize(), PR),
    prod(D, "--dir", "dist", SHORT),
    prod("--auth", "t", D, SHORT),
    prod(D, "-s", "app", SHORT),
    prod(D, "-m", "msg", SHORT),
    # --- api: non-allowlisted methods are production
    prod("api", "restoreSiteDeploy"),
    prod("api", "rollbackSiteDeploy"),
    prod("api", "createSiteDeploy"),
    prod("api", "updateSite"),
    prod("api", "lockDeploy"),
    prod("API", "unlockDeploy"),
    prod("--auth", "t", "api", "deleteSite"),
    prod("api", "disableSite"),
    prod("api", "createDnsRecord", "--data", "{}"),
    # --- deploy: NOT production
    notprod(D, "-sapp"),
    notprod(D, "-s", "app"),
    notprod(D, "-dp"),
    notprod(D, "-mp"),
    notprod(D, "-Odp"),
    notprod(D),
    notprod(D, "--alias", "main"),
    notprod(D, "--draft"),
    notprod(D, "-m", "p"),
    notprod(D, "-P"),
    # --- api: read-only allowlist
    notprod("api", "getSite"),
    notprod("api", "listSites"),
    notprod("api", "listSiteDeploys"),
    notprod("api", "getSiteDeploy"),
    notprod("api", "--list"),
    notprod("api", "getSite", "--data", "{\"site_id\":\"x\"}"),
    # --- other subcommands
    notprod("status"),
    notprod("sites:list"),
    notprod("env:list"),
    notprod("logs"),
    notprod("dev", "-p", "8888"),
    notprod("serve", "-p", "8888"),
    notprod("link", "--name", "app"),
    notprod("build", "--context", "production"),
    notprod("blobs:set"),
]

NODE_DRIVER = (
    "const g=require(process.argv[1]);"
    "const cases=JSON.parse(process.argv[2]);"
    "process.stdout.write(JSON.stringify(cases.map(a=>g.isProdInvocation(a)?'prod':'not prod')));"
)


def clean_env():
    env = {}
    for k, v in os.environ.items():
        if k.upper() in ("CLAUDE_CODE_SESSION_ID", "ORA_OVERRIDE_SESSIONS_DIR", "PYTHON",
                         "NETLIFY_GUARD_DRY_RUN", "NGG_TEST_GUARD", "NGG_TEST_PATCHER"):
            continue
        env[k] = v
    return env


def test_detection_matrix():
    assert len(CASES) >= 40, "matrix must hold at least 40 cases, has %d" % len(CASES)
    argvs = [c[0] for c in CASES]
    proc = subprocess.run([NODE, "-e", NODE_DRIVER, GUARD, json.dumps(argvs)],
                          capture_output=True, text=True, timeout=60, env=clean_env())
    assert proc.returncode == 0, "node driver failed: %s" % proc.stderr
    got = json.loads(proc.stdout)
    bad = []
    for (argv, want), have in zip(CASES, got):
        if want != have:
            bad.append("%r expected %s got %s" % (argv, want, have))
    assert not bad, "detection mismatches:\n  " + "\n  ".join(bad)
    print("PASS test_detection_matrix (%d cases)" % len(CASES))


def mint(sessions_dir, session_id):
    d = os.path.join(sessions_dir, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "allow-website-deploy")
    with open(path, "w", encoding="ascii") as fh:
        fh.write("scope: website-deploy\nsession: %s\nreason: self-minted regression test\n"
                 % session_id)
    return path


def run_guard(argv, env):
    env = dict(env)
    env["NETLIFY_GUARD_DRY_RUN"] = "1"
    return subprocess.run([NODE, GUARD] + argv, capture_output=True, text=True,
                          timeout=60, env=env)


def test_positive_control_token_would_authorize_validator():
    # Proves the minted token layout is valid: without the scrub it WOULD authorize, so
    # the scrub tests below fail for the right reason. Uses the branch's own validator
    # against the temp dir only.
    with tempfile.TemporaryDirectory(prefix="ngg-sess-") as tmp:
        mint(tmp, FAKE_SESSION)
        env = clean_env()
        env["ORA_OVERRIDE_SESSIONS_DIR"] = tmp
        p = subprocess.run([sys.executable, "-I", CHECK, "--session", FAKE_SESSION],
                           capture_output=True, text=True, timeout=60, env=env)
        assert p.returncode == 0, "control token must validate (rc %s): %s" % (p.returncode, p.stderr)
    print("PASS test_positive_control_token_would_authorize_validator")


def _scrub_case(env_name):
    with tempfile.TemporaryDirectory(prefix="ngg-sess-") as tmp:
        token = mint(tmp, FAKE_SESSION)
        env = clean_env()
        env["CLAUDE_CODE_SESSION_ID"] = FAKE_SESSION
        env[env_name] = tmp
        p = run_guard([D, PR], env)
        assert p.returncode == 5, "%s self-minted token must be denied: rc %s stderr %s" % (
            env_name, p.returncode, p.stderr)
        assert "DENIED" in p.stderr, "expected DENIED message, got: %s" % p.stderr
        assert "DRY RUN" not in p.stderr, "must not reach the CLI: %s" % p.stderr
        assert os.path.isfile(token), "temp token must be untouched (never validated)"


def test_env_scrub_exact_case():
    _scrub_case("ORA_OVERRIDE_SESSIONS_DIR")
    print("PASS test_env_scrub_exact_case")


def test_env_scrub_lower_case():
    _scrub_case("ora_override_sessions_dir")
    print("PASS test_env_scrub_lower_case")


def test_env_scrub_mixed_case():
    _scrub_case("Ora_Override_Sessions_Dir")
    print("PASS test_env_scrub_mixed_case")


def test_python_env_does_not_authorize():
    for val in ("true", "cmd.exe"):
        with tempfile.TemporaryDirectory(prefix="ngg-sess-") as tmp:
            mint(tmp, FAKE_SESSION)
            env = clean_env()
            env["CLAUDE_CODE_SESSION_ID"] = FAKE_SESSION
            env["PYTHON"] = val
            env["ORA_OVERRIDE_SESSIONS_DIR"] = tmp
            p = run_guard([D, SHORT], env)
            assert p.returncode == 5, "PYTHON=%s must not authorize: rc %s stderr %s" % (
                val, p.returncode, p.stderr)
            assert "DENIED" in p.stderr, "expected DENIED, got: %s" % p.stderr
    print("PASS test_python_env_does_not_authorize")


def test_no_session_id_denies():
    p = run_guard([D, PR], clean_env())
    assert p.returncode == 5, "no session id must exit 5, got %s (%s)" % (p.returncode, p.stderr)
    assert "no CLAUDE_CODE_SESSION_ID" in p.stderr, p.stderr
    assert "DRY RUN" not in p.stderr
    print("PASS test_no_session_id_denies")


def test_non_prod_passes_through_dry_run():
    p = run_guard(["status"], clean_env())
    assert p.returncode == 0, "non-prod must pass: rc %s (%s)" % (p.returncode, p.stderr)
    assert "DRY RUN" in p.stderr, p.stderr
    print("PASS test_non_prod_passes_through_dry_run")


NODE_SHIM_DRIVER = (
    "const {shimContent}=require(process.argv[1]);const G=process.argv[2];"
    "const out={};for(const n of ['netlify.cmd','netlify','netlify.ps1','ntl.cmd','ntl','ntl.ps1'])"
    "out[n]=shimContent(n,G);process.stdout.write(JSON.stringify(out));"
)


def test_ntl_shims_match_netlify_shims():
    guard_path = "C:\\fake\\hooks\\bin\\netlify-guard-global.js"
    p = subprocess.run([NODE, "-e", NODE_SHIM_DRIVER, PATCHER, guard_path],
                       capture_output=True, text=True, timeout=60, env=clean_env())
    assert p.returncode == 0, "patcher must be requirable without running main(): %s" % p.stderr
    shims = json.loads(p.stdout)
    for a, b in (("netlify.cmd", "ntl.cmd"), ("netlify", "ntl"), ("netlify.ps1", "ntl.ps1")):
        assert shims[a] == shims[b], "%s shim must equal %s shim" % (b, a)
        assert guard_path in shims[b], "%s must contain the guard path" % b
        assert guard_path in shims[a], "%s must contain the guard path" % a
    print("PASS test_ntl_shims_match_netlify_shims")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("ALL NETLIFY-GUARD-GLOBAL TESTS PASS (%d tests, %d matrix cases)" % (len(tests), len(CASES)))
