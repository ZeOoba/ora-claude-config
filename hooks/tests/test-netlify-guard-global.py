"""Tests for hooks/bin/netlify-guard-global.js -- the machine-wide backstop for Hard
Invariant 2 (production Netlify deploys need per-deploy authorization).

Run: python test-netlify-guard-global.py
Stdlib + node only. ASCII-only. Every guard run sets NETLIFY_GUARD_DRY_RUN=1, so the real
netlify-cli is NEVER invoked and no deploy can happen. No override token is minted in the
real sessions dir: the authorized path is exercised with a stub validator in a temp copy
of the guard.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HERE, "bin", "netlify-guard-global.js")
VALIDATOR = os.path.join(HERE, "lib", "check_website_deploy.py")
PYTHON_EXE = "C:\\Users\\Owner\\AppData\\Local\\Programs\\Python\\Python313\\python.exe"

SESSION = "cccccccc-9999-8888-7777-666666666666"
PROD = ["deploy", "--prod"]
PREVIEW = ["deploy"]

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + " :: " + detail)
        FAILS.append(name)


def clean_env():
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("NODE_") and k.upper() != "ORA_OVERRIDE_SESSIONS_DIR"}
    env["NETLIFY_GUARD_DRY_RUN"] = "1"
    env["CLAUDE_CODE_SESSION_ID"] = SESSION
    return env


def run_guard(args, extra_env=None, guard=GUARD):
    env = clean_env()
    env.update(extra_env or {})
    p = subprocess.run(["node", guard] + args, env=env, capture_output=True, text=True)
    return p.returncode, p.stderr


def mint_token_dir(parent):
    d = tempfile.mkdtemp(prefix="ngg-sess-", dir=parent)
    od = os.path.join(d, SESSION, "overrides")
    os.makedirs(od)
    with open(os.path.join(od, "allow-website-deploy"), "w", encoding="ascii") as fh:
        fh.write("scope: website-deploy\nsession: %s\nreason: test token\n" % SESSION)
    return d


def stub_guard(tmp, stub_body):
    """Temp copy of the guard whose CHECK_SCRIPT is a stub validator."""
    stub = os.path.join(tmp, "stub_validator.py")
    with open(stub, "w", encoding="ascii") as fh:
        fh.write(stub_body)
    src = open(GUARD, encoding="utf8").read()
    new, n = re.subn(r'const CHECK_SCRIPT = ".*";',
                     lambda m: "const CHECK_SCRIPT = %s;" % ('"' + stub.replace("\\", "\\\\") + '"'),
                     src, count=1)
    assert n == 1, "CHECK_SCRIPT line not found"
    copy = os.path.join(tmp, "guard-copy.js")
    with open(copy, "w", encoding="utf8") as fh:
        fh.write(new)
    return copy


def main():
    tmp = tempfile.mkdtemp(prefix="ngg-test-")
    try:
        # --- 1. NODE_OPTIONS preload that forges the validator --------------------------
        evil = os.path.join(tmp, "evil.js")
        with open(evil, "w", encoding="ascii") as fh:
            fh.write('const cp = require("child_process");\n'
                     'cp.execFileSync = () => "forged allow";\n')
        evil_arg = evil.replace("\\", "/")
        cnf = os.path.join(tmp, "empty.cnf")  # valid, so node starts and the guard gets to run
        with open(cnf, "w", encoding="ascii") as fh:
            fh.write("# empty openssl config\n")
        cnf_arg = cnf.replace("\\", "/")
        for label, extra in [
            ("--require", {"NODE_OPTIONS": "--require " + evil_arg}),
            ("-r", {"NODE_OPTIONS": "-r " + evil_arg}),
            ("--require=", {"NODE_OPTIONS": "--require=" + evil_arg}),
            ("--import", {"NODE_OPTIONS": "--import file:///" + evil_arg}),
            ("lowercase key", {"node_options": "--require " + evil_arg}),
            ("quoted flag", {"NODE_OPTIONS": '"--require" ' + evil_arg}),
            ("quoted flag+value", {"NODE_OPTIONS": '"--require" "' + evil_arg + '"'}),
            ("quoted --require=", {"NODE_OPTIONS": '"--require=' + evil_arg + '"'}),
            ("--openssl-config", {"NODE_OPTIONS": "--openssl-config=" + cnf_arg}),
        ]:
            rc, err = run_guard(PROD, extra)
            check("preload %s denied on prod path" % label, rc == 5 and "forged" not in err and "authorized" not in err,
                  "rc=%s err=%s" % (rc, err))
            rc, err = run_guard(PREVIEW, extra)
            check("preload %s denied on non-prod path" % label, rc == 5, "rc=%s err=%s" % (rc, err))

        # Benign NODE_OPTIONS: allowed for non-prod, refused on the prod path.
        rc, err = run_guard(PREVIEW, {"NODE_OPTIONS": "--max-old-space-size=256"})
        check("benign NODE_OPTIONS allowed for non-prod", rc == 0 and "DRY RUN" in err, "rc=%s err=%s" % (rc, err))
        rc, err = run_guard(PROD, {"NODE_OPTIONS": "--max-old-space-size=256"})
        check("any NODE_OPTIONS refused on prod path", rc == 5 and "NODE_OPTIONS" in err, "rc=%s err=%s" % (rc, err))

        for var, val in (("NODE_PATH", tmp), ("NODE_REPL_EXTERNAL_MODULE", tmp),
                         ("NODE_V8_COVERAGE", tmp), ("OPENSSL_CONF", cnf_arg)):
            rc, err = run_guard(PREVIEW, {var: val})
            check("%s denied" % var, rc == 5 and var in err, "rc=%s err=%s" % (rc, err))

        # Any node execArgv (direct `node --flag guard.js`) is refused, incl. flags the
        # denylist does not know by name.
        # (--watch is deliberately NOT exercised: node would respawn its child tree.)
        cfg = os.path.join(tmp, "node.json")
        with open(cfg, "w", encoding="ascii") as fh:
            fh.write("{}\n")
        for flag in ("--experimental-config-file=" + cfg.replace("\\", "/"), "--no-warnings"):
            p = subprocess.run(["node", flag, GUARD] + PROD, env=clean_env(), capture_output=True, text=True)
            check("execArgv %s denied" % flag.split("=")[0],
                  p.returncode == 5 and "started with flags" in p.stderr,
                  "rc=%s err=%s" % (p.returncode, p.stderr[:300]))

        # Control: a clean env reaches the DRY RUN line for non-prod.
        rc, err = run_guard(PREVIEW)
        check("clean env non-prod reaches dry run", rc == 0 and "DRY RUN" in err, "rc=%s err=%s" % (rc, err))

        # --- 2. ORA_OVERRIDE_SESSIONS_DIR in every casing is ignored by the validator ----
        sess = mint_token_dir(tmp)
        # Control: the minted token IS valid when the seam is honoured (direct validator run).
        env = {"SystemRoot": os.environ.get("SystemRoot", ""), "ORA_OVERRIDE_SESSIONS_DIR": sess}
        p = subprocess.run([PYTHON_EXE, "-I", "-S", VALIDATOR, "--session", SESSION],
                           env=env, capture_output=True, text=True)
        check("control: minted token valid via seam", p.returncode == 0, "rc=%s %s%s" % (p.returncode, p.stdout, p.stderr))
        for key in ("ORA_OVERRIDE_SESSIONS_DIR", "ora_override_sessions_dir", "Ora_Override_Sessions_Dir"):
            rc, err = run_guard(PROD, {key: sess})
            check("seam %s cannot self-authorize" % key, rc == 5 and "DENIED" in err, "rc=%s err=%s" % (rc, err))
        # The real validator launches under -I -S (a denial message, not an import crash).
        rc, err = run_guard(PROD)
        check("real validator runs under -I -S and denies untokened session",
              rc == 5 and "DENIED" in err and "Traceback" not in err, "rc=%s err=%s" % (rc, err))

        # --- 3. Authorized path still works, with -I -S and an allowlisted env -----------
        stub = (
            "import sys, os\n"
            "if not (sys.flags.isolated and sys.flags.no_site):\n"
            "    sys.stderr.write('not isolated/no_site'); sys.exit(1)\n"
            "bad = [k for k in os.environ if k.upper().startswith(('ORA_', 'PYTHON', 'CLAUDE_', 'NODE_', 'NETLIFY'))]\n"
            "if bad:\n"
            "    sys.stderr.write('leaked: %s' % bad); sys.exit(1)\n"
            "if '--session' not in sys.argv:\n"
            "    sys.stderr.write('no session arg'); sys.exit(1)\n"
            "print('stub ok')\n"
        )
        copy = stub_guard(tmp, stub)
        rc, err = run_guard(PROD, {"PYTHONPATH": tmp, "ORA_OVERRIDE_SESSIONS_DIR": sess, "FOO": "bar"}, guard=copy)
        check("authorized path: exit 0 with allowlisted env", rc == 0 and "authorized prod deploy" in err and "DRY RUN" in err,
              "rc=%s err=%s" % (rc, err))
        deny_stub = "import sys\nsys.stderr.write('no token'); sys.exit(2)\n"
        rc, err = run_guard(PROD, guard=stub_guard(tmp, deny_stub))
        check("validator non-zero exit -> DENIED exit 5", rc == 5 and "DENIED" in err, "rc=%s err=%s" % (rc, err))
        rc, err = run_guard(PROD, {"CLAUDE_CODE_SESSION_ID": ""}, guard=copy)
        check("no session id -> exit 5", rc == 5, "rc=%s err=%s" % (rc, err))

        # --- 3b. Spellings node accepts that a naive regex misses (unit-level: the value is
        # set inside the probe process, since node would act on it at startup otherwise).
        probe = os.path.join(tmp, "probe.js")
        with open(probe, "w", encoding="ascii") as fh:
            fh.write('const g = require("%s"); process.env.NODE_OPTIONS = process.env.PROBE_VAL;'
                     'process.stdout.write(String(g.preloadProblem(false)));' % GUARD.replace("\\", "/"))

        def probe_run(val):
            env = clean_env()
            env["PROBE_VAL"] = val
            return subprocess.run(["node", probe], env=env, capture_output=True, text=True)

        for label, val in [("backslash escape", '"--requ\ire" m.js'), ("underscore", "--experimental_loader=m.js"),
                           ("underscore openssl", "--openssl_config=m.cnf"), ("snapshot-blob", "--snapshot-blob m.blob"),
                           ("quoted snapshot-blob", '"--snapshot-blob" "m.blob"')]:
            p = probe_run(val)
            check("flag spelling caught: " + label, p.returncode == 0 and p.stdout != "null",
                  "rc=%s out=%s err=%s" % (p.returncode, p.stdout, p.stderr[:200]))
        p = probe_run("--max-old-space-size=256")
        check("benign flag not flagged by preloadProblem(false)", p.stdout == "null", p.stdout + p.stderr[:200])

        # The shims clear the startup-time vectors the guard cannot see. Text check for the
        # Windows flavours; the sh shim is GENERATED and RUN against a stand-in guard, with
        # lower/mixed-case keys (Git Bash env names are case-sensitive, node.exe's are not).
        patcher_path = os.path.join(HERE, "..", "maintenance", "patch-global-netlify-shim.js")
        patcher = open(patcher_path, encoding="utf8").read()
        check("shim templates clear vars (cmd/ps1)",
              'set "NODE_OPTIONS=" & set "OPENSSL_CONF="' in patcher
              and "Remove-Item Env:NODE_OPTIONS, Env:OPENSSL_CONF" in patcher)
        bash = shutil.which("bash")
        if bash is None:
            print("SKIP sh shim runtime test (no bash on PATH)")
        else:
            stand_in = os.path.join(tmp, "standin-guard.js")
            with open(stand_in, "w", encoding="ascii") as fh:
                fh.write('const e = process.env; const hit = Object.keys(e).filter(k => /^(node_options|openssl_conf)$/i.test(k));'
                         'process.stdout.write("GUARD-RAN leaked=" + JSON.stringify(hit) + " argv=" + JSON.stringify(process.argv.slice(2)));'
                         'process.exit(7);')
            gen = subprocess.run(["node", "-e", 'process.stdout.write(require(process.argv[1]).shimContent("netlify", process.argv[2]))',
                                  patcher_path, stand_in.replace("\\", "/")], capture_output=True, text=True)
            shim = os.path.join(tmp, "shim-netlify")
            with open(shim, "w", encoding="ascii", newline="\n") as fh:
                fh.write(gen.stdout)
            # Second field = extra hostile env that defeats a loop built on env/cut/grep.
            sabotage = [{}, {"BASH_FUNC_grep%%": "() { :; }"}, {"BASH_FUNC_cut%%": "() { :; }"},
                        {"BASH_FUNC_env%%": "() { :; }"}, {"BASH_FUNC_compgen%%": "() { :; }"},
                        {"GREP_OPTIONS": "-v"}]
            cases = [(k, x) for k in ("NODE_OPTIONS", "node_options", "Node_Options", "OPENSSL_CONF", "openssl_conf")
                     for x in sabotage]
            for key, extra in cases:
                env = clean_env()
                env[key] = "--max-old-space-size=256"
                env.update(extra)
                p = subprocess.run([bash, shim, "deploy", "a b"], env=env, capture_output=True, text=True)
                check("sh shim clears %s before node starts %s" % (key, sorted(extra) or ""),
                      p.returncode == 7 and "leaked=[]" in p.stdout and '["deploy","a b"]' in p.stdout,
                      "rc=%s out=%s err=%s" % (p.returncode, p.stdout, p.stderr[:200]))

        # --- 4. validatorEnv unit: allowlist, case-insensitive ---------------------------
        js = ('const g = require(%s); process.stdout.write(JSON.stringify(Object.keys(g.validatorEnv()).sort()));'
              % ('"' + GUARD.replace("\\", "/") + '"'))
        env = {"SystemRoot": "C:\\Windows", "PATH": "p", "Temp": "t", "PYTHONPATH": "x", "PYTHONSTARTUP": "y",
               "ora_override_sessions_dir": "z", "CLAUDE_CODE_SESSION_ID": "s", "NODE_OPTIONS_X": "q"}
        p = subprocess.run(["node", "-e", js], env=env, capture_output=True, text=True)
        keys = p.stdout
        check("validatorEnv keeps only allowlisted keys",
              p.returncode == 0 and all(k in keys for k in ("SystemRoot", "PATH", "Temp"))
              and not any(k in keys for k in ("PYTHON", "ora_override", "CLAUDE_CODE", "NODE_OPTIONS_X")),
              "rc=%s out=%s err=%s" % (p.returncode, keys, p.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if FAILS:
        print("\n%d FAILED: %s" % (len(FAILS), ", ".join(FAILS)))
        sys.exit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    main()
