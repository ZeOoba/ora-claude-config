#!/usr/bin/env python3
"""Tests for hooks/lib/exposure_leak_check.py and its wiring into git-prepush-confidential-scan.py.

Run: python hooks/tests/test-exposure-leak-check.py   (exit 0 = all pass)
Pure stdlib. ASCII-only output (Windows cp1252 console).

Every value here is SYNTHETIC (555-01xx phone numbers, 1,111,111-style figures, made-up deal
names). Real contacts and loan figures live only in gitignored files on Gabriel's machine and
must never appear in this public repo, test fixtures included. The debt-figure source is passed
through env overrides, so the tests run the same on the dev box and in CI.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
LIB = os.path.join(HOOKS, "lib", "exposure_leak_check.py")

spec = importlib.util.spec_from_file_location("exposure_leak_check", LIB)
elc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elc)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


MEM = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory"
C1 = "commit " + "a" * 40


def diff(path, added, removed=(), header=""):
    lines = [C1, "Author: t <t@example.com>", "", "    msg", "",
             "diff --git a/%s b/%s" % (path, path)]
    if header:
        lines.append(header)
    lines += ["--- a/%s" % path, "+++ b/%s" % path, "@@ -1,1 +1,1 @@"]
    lines += ["-" + r for r in removed] + ["+" + a for a in added]
    return "\n".join(lines) + "\n"


# --- path matching ------------------------------------------------------------------------
for p in ("maintenance/_state/deal-stage-snapshot.json", MEM + "/people.md", MEM + "/user.md",
          MEM + "/tenant_alpha_default_2026-01-01.md",
          MEM + "/_archive/user_gabriel_consolidated_2026-06-03.md"):
    expect("exposure path: %s" % p.rsplit("/", 1)[-1], elc.is_exposure_path(p))
for p in (MEM + "/people_index.md", MEM + "/_archive/user_ze_retired_2026-04-21.md",
          "maintenance/_state/other.json", "docs/people.md"):
    expect("not an exposure path: %s" % p, not elc.is_exposure_path(p))
expect("memory subdir counts as memory", elc.is_memory_path(MEM + "/_archive/x.md"))
expect("non-memory path", not elc.is_memory_path("docs/x.md"))

# --- rule 1: exposure path ----------------------------------------------------------------
expect("adding to people.md blocks",
       elc.scan_diff(diff(MEM + "/people.md", ["- Broker A"])) == [(MEM + "/people.md", "exposure-path")])
expect("deleting people.md passes (removed lines only)",
       elc.scan_diff(diff(MEM + "/people.md", [], ["- Broker A"], "deleted file mode 100644")) == [])
ren = "\n".join([C1, "", "    msg", "", "diff --git a/x.json b/maintenance/_state/deal-stage-snapshot.json",
                 "similarity index 100%", "rename from x.json",
                 "rename to maintenance/_state/deal-stage-snapshot.json"]) + "\n"
expect("100% rename onto an exposure path blocks",
       elc.scan_diff(ren) == [("maintenance/_state/deal-stage-snapshot.json", "exposure-path")])

# --- rule 2: phone in memory --------------------------------------------------------------
for label, ph in (("dashes", "202-555-0143"), ("parens", "(614) 555-0199 x117"),
                  ("dots", "312.555.0110"), ("+1", "+1 415 555 0187")):
    expect("phone (%s) in memory blocks" % label,
           elc.scan_diff(diff(MEM + "/feedback_x.md", ["call " + ph])) == [(MEM + "/feedback_x.md", "phone-in-memory")])
expect("phone outside memory passes", elc.scan_diff(diff("docs/x.md", ["call 202-555-0143"])) == [])
for label, txt in (("date", "2026-11-18"), ("bare 10 digits", "id 2025550143"),
                   ("version", "v1.250.3000"), ("sha-ish", "abc 123-4567"),
                   ("decimal", "1,250.0000"), ("removed", None)):
    if txt is None:
        d = diff(MEM + "/x.md", [], ["call 202-555-0143"])
    else:
        d = diff(MEM + "/x.md", [txt])
    expect("no phone false positive: %s" % label, elc.scan_diff(d) == [], elc.scan_diff(d))
expect("allowlisted public office line passes",
       elc.scan_diff(diff(MEM + "/x.md", ["recorder (614) 525-3930"])) == [])
expect("public line does not mask a private one on the same line",
       elc.scan_diff(diff(MEM + "/x.md", ["recorder (614) 525-3930 or 202-555-0143"]))
       == [(MEM + "/x.md", "phone-in-memory")])
expect("placeholder passes", elc.scan_diff(diff(MEM + "/x.md", ["[phone: see contacts.local.md]"])) == [])

# --- rule 3: pipeline shape ---------------------------------------------------------------
snap = ['{', '  "abc": {', '    "deal": "Alpha Flex Park",', '    "stage": "Candidate"', '  }', '}']
expect("deal+stage json shape blocks",
       elc.scan_diff(diff("maintenance/_state/other.json", snap)) == [("maintenance/_state/other.json", "pipeline-shape")])
expect("stage-only json passes", elc.scan_diff(diff("x.json", ['"stage": "build"'])) == [])
expect("deal+stage in a .md passes (shape rule is json only)",
       elc.scan_diff(diff("docs/x.md", ['"deal": "a"', '"stage": "b"'])) == [])

# --- rule 4: debt figures -----------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="exp-leak-")
try:
    loan = {"_meta": {"version": 1}, "loans": [
        {"id": "L1", "original_principal": 1111111.0, "balloon_payment": 987654.32,
         "appraisal": {"value": 2222222}},
        {"id": "L2", "original_principal": 50000.0}]}
    lt = os.path.join(tmp, "loan-terms.json")
    with open(lt, "w") as f:
        json.dump(loan, f)
    deny = os.path.join(tmp, "deny.json")
    with open(deny, "w") as f:
        json.dump({"strings": ["LN-000123456"]}, f)
    missing = os.path.join(tmp, "nope.json")
    fake_home = os.path.join(tmp, "home")
    os.mkdir(fake_home)

    n = elc.load_needles(loan_terms_path=lt, denylist_path=deny)
    for want in ("1,111,111", "1111111", "987,654.32", "987654.32", "2,222,222", "LN-000123456"):
        expect("needle built: %s" % want, want in n)
    expect("sub-floor figure skipped", "50000" not in n and "50,000" not in n)
    for label, txt in (("comma form", "balance $1,111,111 at 4%"), ("bare form", "bal=1111111"),
                       ("cents", "balloon 987,654.32"), ("loan no.", "loan LN-000123456")):
        expect("debt figure (%s) blocks anywhere" % label,
               elc.scan_diff(diff("docs/x.md", [txt]), n) == [("docs/x.md", "debt-figure")])
    for label, txt in (("longer number", "11111110"), ("decimal tail", "1111111.5"),
                       ("group tail", "1,111,111,000")):
        expect("no debt false positive: %s" % label, elc.scan_diff(diff("docs/x.md", [txt]), n) == [],
               elc.scan_diff(diff("docs/x.md", [txt]), n))
    msg = "\n".join([C1, "", "    land 1,111,111 refi", ""]) + "\n"
    expect("debt figure in commit message blocks",
           elc.scan_diff(msg, n) == [("<commit message aaaaaaaa>", "debt-figure")])

    # fail modes
    old_env = dict(os.environ)
    os.environ.pop("ORA_LOAN_TERMS_PATH", None)
    os.environ.pop("ORA_EXPOSURE_DENYLIST", None)
    os.environ["HOME"] = os.environ["USERPROFILE"] = fake_home
    expect("no sources -> None (skip)", elc.load_needles(start_dir=tmp) is None)
    os.environ["ORA_LOAN_TERMS_PATH"] = missing
    try:
        elc.load_needles(start_dir=tmp)
        expect("env path set but missing -> error", False)
    except elc.ExposureSourceError:
        expect("env path set but missing -> error", True)
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w") as f:
        f.write("{not json")
    for label, path in (("unparseable", bad),):
        try:
            elc.load_needles(loan_terms_path=path)
            expect("%s source -> error" % label, False)
        except elc.ExposureSourceError:
            expect("%s source -> error" % label, True)
    empty = os.path.join(tmp, "empty.json")
    with open(empty, "w") as f:
        json.dump({"loans": [{"original_principal": 10}]}, f)
    try:
        elc.load_needles(loan_terms_path=empty)
        expect("no-needle source -> error", False)
    except elc.ExposureSourceError:
        expect("no-needle source -> error", True)
    os.environ.clear()
    os.environ.update(old_env)

    # --- wiring: the real pre-push scan blocks ---------------------------------------------
    def sh(args, cwd, env=None):
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)

    origin = os.path.join(tmp, "origin.git")
    repo = os.path.join(tmp, "repo")
    sh(["git", "init", "-q", "--bare", origin], tmp)
    sh(["git", "init", "-q", "-b", "main", repo], tmp)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        sh(["git", "config", k, v], repo)
    os.makedirs(os.path.join(repo, MEM))
    with open(os.path.join(repo, MEM, "people.md"), "w") as f:
        f.write("- Broker A, 202-555-0143\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "seed"], repo)
    sh(["git", "remote", "add", "origin", origin], repo)
    sh(["git", "push", "-q", "--no-verify", "origin", "main"], repo)
    sh(["git", "fetch", "-q", "origin"], repo)

    hooks_copy = os.path.join(tmp, "hooks")
    shutil.copytree(HOOKS, hooks_copy, ignore=shutil.ignore_patterns("tests", "_state", "sessions",
                                                                      "active-work", "*.jsonl*"))
    with open(os.path.join(hooks_copy, "confidential-terms.json"), "w") as f:
        json.dump({}, f)
    scan_copy = os.path.join(hooks_copy, "git-prepush-confidential-scan.py")
    strip = ("ORA_RCT_TABLE_PATH", "ORA_RCT_LEAK_DENYLIST", "ORA_LOAN_TERMS_PATH",
             "ORA_EXPOSURE_DENYLIST")

    def push_scan(loan_env=None):
        base = sh(["git", "rev-parse", "origin/main"], repo).stdout.strip()
        head = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        env = {k: v for k, v in os.environ.items() if k not in strip}
        env.update(HOME=fake_home, USERPROFILE=fake_home)
        if loan_env:
            env["ORA_LOAN_TERMS_PATH"] = loan_env
        return subprocess.run([sys.executable, scan_copy, "origin", origin], cwd=repo,
                              input="refs/heads/main %s refs/heads/main %s\n" % (head, base),
                              capture_output=True, text=True, env=env)

    def advance():
        sh(["git", "push", "-q", "--no-verify", "origin", "HEAD:main"], repo)
        sh(["git", "fetch", "-q", "origin"], repo)

    # untrack (the fix itself): allowed
    sh(["git", "rm", "-q", "--cached", MEM + "/people.md"], repo)
    sh(["git", "commit", "-qm", "untrack people"], repo)
    r = push_scan()
    expect("e2e: untracking push passes", r.returncode == 0, r.stderr[:400])
    expect("e2e: debt rule skip announced", "debt-figure rule skipped" in r.stderr, r.stderr[:400])
    advance()

    # re-adding people.md: blocked, value not echoed
    sh(["git", "add", "-f", MEM + "/people.md"], repo)
    sh(["git", "commit", "-qm", "re-add"], repo)
    r = push_scan()
    expect("e2e: re-adding people.md blocks", r.returncode == 1 and "exposure-path" in r.stderr,
           r.stderr[:400])
    expect("e2e: phone value not echoed", "555-0143" not in r.stderr)
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)

    # debt figure in a new file: blocked with a loan-terms source
    with open(os.path.join(repo, "note.md"), "w") as f:
        f.write("refi balance 1,111,111\n")
    sh(["git", "add", "note.md"], repo)
    sh(["git", "commit", "-qm", "note"], repo)
    r = push_scan(lt)
    expect("e2e: debt figure blocks", r.returncode == 1 and "debt-figure" in r.stderr, r.stderr[:400])
    expect("e2e: figure not echoed", "1,111,111" not in r.stderr)
    r = push_scan(missing)
    expect("e2e: configured-but-missing loan source blocks", r.returncode == 1
           and "unusable" in r.stderr, r.stderr[:400])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

failed = [l for ok, l in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
