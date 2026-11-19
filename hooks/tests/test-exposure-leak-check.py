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
for p in ("maintenance/_archive/2026-09-22_checkout-sync/" + MEM + "/people.md",
          MEM + "/People.md", MEM + "/USER.MD", MEM.replace("/", "\\") + "\\people.md",
          "maintenance/_archive/x/maintenance/_state/deal-stage-snapshot.json"):
    expect("exposure path (archive/case/backslash): %s" % p[-40:], elc.is_exposure_path(p))
expect("archive memory copy counts as memory",
       elc.is_memory_path("maintenance/_archive/x/" + MEM + "/notes.md"))
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
EN = chr(0x2013)
for label, ph in (("dashes", "202-555-0143"), ("parens", "(614) 555-0199 x117"),
                  ("dots", "312.555.0110"), ("+1", "+1 415 555 0187"),
                  ("E.164", "tel:+12025550143"), ("glued ext", "202-555-0143x12"),
                  ("underscore before", "cell_202-555-0143"), ("en dash", "202" + EN + "555" + EN + "0143"),
                  ("slash", "202/555-0143"), ("double space", "(202)  555-0143"),
                  ("spaced parens", "( 202 ) 555 - 0143")):
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
# --- path parsing ---------------------------------------------------------------------------
quoted = "\n".join([C1, "", "    msg", "", 'diff --git "a/%s/caf\\303\\251.md" "b/%s/caf\\303\\251.md"' % (MEM, MEM),
                    'new file mode 100644', '--- /dev/null', '+++ "b/%s/caf\\303\\251.md"' % MEM,
                    "@@ -0,0 +1 @@", "+call 202-555-0143"]) + "\n"
expect("C-quoted non-ASCII memory path still caught, path decoded",
       elc.scan_diff(quoted) == [(MEM + "/caf" + chr(0xE9) + ".md", "phone-in-memory")],
       elc.scan_diff(quoted))
bdir = "\n".join([C1, "", "    msg", "", "diff --git a/%s/a b/x.md b/%s/a b/x.md" % (MEM, MEM),
                  "--- a/%s/a b/x.md\t" % MEM, "+++ b/%s/a b/x.md\t" % MEM,
                  "@@ -1 +1 @@", "+call 202-555-0143"]) + "\n"
expect("directory ending in ' b' parsed from +++ line",
       elc.scan_diff(bdir) == [(MEM + "/a b/x.md", "phone-in-memory")], elc.scan_diff(bdir))
expect("git log args pin prefixes, quoting, textconv, text, cc and root",
       all(a in elc.GIT_LOG_ARGS for a in ("--src-prefix=a/", "--dst-prefix=b/", "--no-textconv",
                                            "--no-ext-diff", "core.quotePath=false", "--text",
                                            "--cc", "--root")))
expect("reconciler tmp-write sidecar is an exposure path",
       elc.is_exposure_path("maintenance/_state/deal-stage-snapshot.json.tmp-write"))

# extra phone formats (merge gate round 1)
NB = chr(0xA0)
for label, ph in (("+1(area) no sep", "+1(202)555-0143"), ("1(area) sp", "1(202) 555-0143"),
                  ("+1(area) sp", "+1(202) 555-0143"), ("nbsp", "202" + NB + "555" + NB + "0143")):
    expect("phone (%s) in memory blocks" % label,
           elc.scan_diff(diff(MEM + "/f.md", ["call " + ph])) == [(MEM + "/f.md", "phone-in-memory")])
# false-positive guards (each boundary must hold)
for label, txt in (("leading digit", "9202-555-0143"), ("trailing digit", "202-555-01439"),
                   ("exchange 1xx", "202-155-0143")):
    expect("no phone false positive: %s" % label, elc.scan_diff(diff(MEM + "/x.md", [txt])) == [],
           elc.scan_diff(diff(MEM + "/x.md", [txt])))

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
expect("mixed-case keys in .json block",
       elc.scan_diff(diff("x.json", ['"Deal": "a",', '"STAGE": "b"'])) == [("x.json", "pipeline-shape")])
expect(".jsonl one-line record blocks",
       elc.scan_diff(diff("s.jsonl", ['{"id": 1, "deal": "a", "stage": "b"}'])) == [("s.jsonl", "pipeline-shape")])
two = diff("p.json", ['{"p1": {"deal": "a",']) + diff("p.json", ['"stage": "b"}}']).replace(C1, "commit " + "b" * 40)
expect("deal and stage added in two commits of one push block",
       elc.scan_diff(two) == [("p.json", "pipeline-shape")], elc.scan_diff(two))

# --- rule 4: debt figures -----------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="exp-leak-")
try:
    loan = {"_meta": {"version": 1}, "loans": [
        {"id": "L1", "original_principal": 1111111.0, "balloon_payment": 987654.32,
         "appraisal": {"value": 2222222}, "anchor": {"principal": 3333333.0},
         "schedule": [["2026-01-01", 4444444.0]]},
        {"id": "L2", "original_principal": 50000.0}]}
    lt = os.path.join(tmp, "loan-terms.json")
    with open(lt, "w") as f:
        json.dump(loan, f)
    deny = os.path.join(tmp, "deny.json")
    with open(deny, "w") as f:
        json.dump({"strings": ["LN-000123456"]}, f)
    missing = os.path.join(tmp, "nope.json")

    def _w(obj, _c=[0]):
        _c[0] += 1
        p = os.path.join(tmp, "src%d.json" % _c[0])
        with open(p, "w") as f:
            json.dump(obj, f)
        return p
    fake_home = os.path.join(tmp, "home")
    os.mkdir(fake_home)

    n = elc.load_needles(loan_terms_path=lt, denylist_path=deny)
    for want in ("1,111,111", "1111111", "987,654.32", "987654.32", "2,222,222", "LN-000123456",
                 "3,333,333", "4444444", "1,111,111.00"):
        expect("needle built: %s" % want, want in n)
    expect("sub-floor figure skipped", "50000" not in n and "50,000" not in n)
    for label, txt in (("comma form", "balance $1,111,111 at 4%"), ("bare form", "bal=1111111"),
                       ("cents", "balloon 987,654.32"), ("loan no.", "loan LN-000123456"),
                       ("zero cents", "$1,111,111.00 due"), ("one-dp zero", "1111111.0"),
                       ("anchor balance", "bal 3,333,333")):
        expect("debt figure (%s) blocks anywhere" % label,
               elc.scan_diff(diff("docs/x.md", [txt]), n) == [("docs/x.md", "debt-figure")])
    n2 = elc.load_needles(loan_terms_path=_w({"loans": [{"original_principal": 1111111.55}]}))
    for label, txt in (("truncated whole $", "bal $1,111,111"), ("truncated bare", "bal 1111111"),
                       ("rounded", "bal 1,111,112"), ("cents", "bal 1,111,111.55")):
        expect("figure with cents, written as %s, blocks" % label,
               elc.scan_diff(diff("docs/x.md", [txt]), n2) == [("docs/x.md", "debt-figure")])
    nd = elc.load_needles(loan_terms_path=lt, denylist_path=_w({"strings": ["ab", "LN-000123456"]}))
    expect("denylist entries under 4 chars are ignored",
           elc.scan_diff(diff("docs/x.md", ["about this"]), nd) == [])
    for label, txt in (("longer number", "11111110"), ("decimal tail", "1111111.5"),
                       ("group tail", "1,111,111,000"), ("leading digit", "21111111")):
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
    sub = os.path.join(tmp, "gitrepo")
    subprocess.run(["git", "init", "-q", sub], capture_output=True)
    expect("no sources -> None (skip)", elc.load_needles(start_dir=sub) is None)
    try:
        elc.load_needles(start_dir=os.path.join(tmp, "not-a-repo-dir-xyz"))
        expect("unresolvable repo root -> error", False)
    except elc.ExposureSourceError:
        expect("unresolvable repo root -> error", True)
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
    # host config that rewrites diff headers / hides content must not blind the scan
    for k, v in (("diff.noprefix", "true"), ("diff.srcPrefix", "x/"), ("diff.dstPrefix", "y/"),
                 ("core.quotePath", "true"), ("diff.mangle.textconv", "true")):
        sh(["git", "config", k, v], repo)
    with open(os.path.join(repo, ".git", "info", "attributes"), "w") as f:
        f.write("*.md diff=mangle\n")
    r = push_scan()
    expect("e2e: noprefix/srcPrefix/textconv config cannot hide the re-add",
           r.returncode == 1 and "exposure-path" in r.stderr, r.stderr[:400])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)

    # archive-snapshot copy and case variant: blocked
    arch = os.path.join(repo, "maintenance", "_archive", "2026-12-01_sync", *MEM.split("/"))
    os.makedirs(arch)
    with open(os.path.join(arch, "people.md"), "w") as f:
        f.write("- Broker B\n")
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "People.md"), "w") as f:
        f.write("- Broker C\n")
    sh(["git", "add", "-f", "-A"], repo)
    sh(["git", "commit", "-qm", "archive copy"], repo)
    r = push_scan()
    expect("e2e: archive copy blocked", r.returncode == 1 and "_archive" in r.stderr, r.stderr[:400])
    expect("e2e: case-variant People.md blocked", "People.md -> exposure-path" in r.stderr,
           r.stderr[:600])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)

    # copy of an already-public non-memory file into memory: the phone must still be seen
    with open(os.path.join(repo, "notes.txt"), "w") as f:
        f.write("vendor 202-555-0143\nline two\nline three\n")
    sh(["git", "add", "notes.txt"], repo)
    sh(["git", "commit", "-qm", "notes"], repo)
    advance()
    with open(os.path.join(repo, "notes.txt"), "a") as f:
        f.write("line four\n")
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    shutil.copy(os.path.join(repo, "notes.txt"), os.path.join(repo, MEM, "contacts.md"))
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "copy into memory"], repo)
    r = push_scan()
    expect("e2e: phone copied into memory is caught (no rename/copy detection)",
           r.returncode == 1 and "phone-in-memory" in r.stderr, r.stderr[:400])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)
    expect("git log args disable rename detection", "--no-renames" in elc.GIT_LOG_ARGS
           and "-M" not in elc.GIT_LOG_ARGS and "-C" not in elc.GIT_LOG_ARGS)

    # rename-with-edit into memory (catches a dropped --no-renames end to end)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    sh(["git", "mv", "notes.txt", MEM + "/moved.md"], repo)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "moved.md"), "a") as f:
        f.write("line five\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "rename into memory"], repo)
    r = push_scan()
    expect("e2e: rename-with-edit into memory is caught",
           r.returncode == 1 and "moved.md -> phone-in-memory" in r.stderr, r.stderr[:400])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)

    # NUL byte in a re-added exposure file (catches a dropped --text)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "people.md"), "wb") as f:
        f.write(b"- Broker D\x00 202-555-0143\n")
    sh(["git", "add", "-f", MEM + "/people.md"], repo)
    sh(["git", "commit", "-qm", "binary-looking people"], repo)
    r = push_scan()
    expect("e2e: NUL-byte people.md re-add blocked", r.returncode == 1
           and "people.md -> exposure-path" in r.stderr, r.stderr[:400])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)

    # phone introduced only by a merge's conflict resolution (catches a dropped --cc)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "m.md"), "w") as f:
        f.write("base\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "m base"], repo)
    advance()
    sh(["git", "checkout", "-qb", "side"], repo)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "m.md"), "w") as f:
        f.write("side\n")
    sh(["git", "commit", "-qam", "side"], repo)
    sh(["git", "checkout", "-q", "main"], repo)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "m.md"), "w") as f:
        f.write("ours\n")
    sh(["git", "commit", "-qam", "ours"], repo)
    sh(["git", "merge", "-q", "side"], repo)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "m.md"), "w") as f:
        f.write("resolved, call 202-555-0143\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "resolve"], repo)
    # push only the merge on top of a remote that already has both parents
    sh(["git", "push", "-q", "--no-verify", "origin", "HEAD~1:refs/heads/ours", "side:refs/heads/side"], repo)
    sh(["git", "fetch", "-q", "origin"], repo)
    head = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    base = sh(["git", "rev-parse", "HEAD~1"], repo).stdout.strip()
    env = {k: v for k, v in os.environ.items() if k not in strip}
    env.update(HOME=fake_home, USERPROFILE=fake_home)
    r = subprocess.run([sys.executable, scan_copy, "origin", origin], cwd=repo,
                       input="refs/heads/ours %s refs/heads/ours %s\n" % (head, base),
                       capture_output=True, text=True, env=env)
    expect("e2e: phone added only in a conflict resolution is caught",
           r.returncode == 1 and "m.md -> phone-in-memory" in r.stderr, r.stderr[:400])
    sh(["git", "reset", "-q", "--hard", "origin/main"], repo)
    sh(["git", "branch", "-qD", "side"], repo)

    # orphan root commit with log.showRoot=false (catches a dropped --root)
    sh(["git", "config", "log.showRoot", "false"], repo)
    sh(["git", "checkout", "-q", "--orphan", "leak"], repo)
    sh(["git", "rm", "-rqf", "--cached", "."], repo)
    os.makedirs(os.path.join(repo, MEM), exist_ok=True)
    with open(os.path.join(repo, MEM, "people.md"), "w") as f:
        f.write("- Broker E\n")
    sh(["git", "add", "-f", MEM + "/people.md"], repo)
    sh(["git", "commit", "-qm", "orphan"], repo)
    head = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    r = subprocess.run([sys.executable, scan_copy, "origin", origin], cwd=repo,
                       input="refs/heads/leak %s refs/heads/leak %s\n" % (head, "0" * 40),
                       capture_output=True, text=True, env=env)
    expect("e2e: orphan root commit scanned despite log.showRoot=false",
           r.returncode == 1 and "people.md -> exposure-path" in r.stderr, r.stderr[:400])
    sh(["git", "checkout", "-qf", "main"], repo)
    sh(["git", "config", "--unset", "log.showRoot"], repo)
    sh(["git", "clean", "-qfd"], repo)

    # the exposure pass's own `git log` failing must block (fail closed)
    import io
    sspec = importlib.util.spec_from_file_location("scan_mod", scan_copy)
    smod = importlib.util.module_from_spec(sspec)
    sspec.loader.exec_module(smod)
    real_run = smod.subprocess.run

    def failing_run(args, *a, **k):
        if isinstance(args, list) and "--no-renames" in args:
            return subprocess.CompletedProcess(args, 128, b"", b"boom")
        return real_run(args, *a, **k)
    with open(os.path.join(repo, "ok.md"), "w") as f:
        f.write("harmless\n")
    sh(["git", "add", "ok.md"], repo)
    sh(["git", "commit", "-qm", "ok"], repo)
    head = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    base = sh(["git", "rev-parse", "origin/main"], repo).stdout.strip()
    saved = (os.getcwd(), sys.stdin, sys.stderr, dict(os.environ))
    try:
        os.chdir(repo)
        os.environ.update(HOME=fake_home, USERPROFILE=fake_home)
        for k in strip:
            os.environ.pop(k, None)
        sys.stdin = io.StringIO("refs/heads/main %s refs/heads/main %s\n" % (head, base))
        sys.stderr = io.StringIO()
        smod.subprocess.run = failing_run
        rc = smod.main()
        err = sys.stderr.getvalue()
    finally:
        smod.subprocess.run = real_run
        os.chdir(saved[0])
        sys.stdin, sys.stderr = saved[1], saved[2]
        os.environ.clear()
        os.environ.update(saved[3])
    expect("e2e: failed exposure git log blocks the push", rc == 1
           and "cannot check for pipeline, PII or debt data" in err, err[:400])
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
