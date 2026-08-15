#!/usr/bin/env python3
"""
reference-backup-coverage-probe.py -- OI-153.

WHY THIS EXISTS
  Three files lost their backup in a single day (2026-08-14) and each was found
  by a different accident:

    1. scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py
       -- git-IGNORED by the 2b `/scheduled-tasks/*/*` rule. Invisible to
       `git status`. Caught next-day by task-folder-backup-completeness-probe.
    2. maintenance/_tests/test_check_dispatch_model_floor.py
       -- untracked but NOT ignored. Visible to `git status`, never added.
    3. maintenance/check-dispatch-model-floor.py
       -- the MODULE that (2) imports. Also untracked. Nothing noticed until a
       worktree checkout had the test but not its subject and the pre-push
       hook-tests gate died with FileNotFoundError.

  (3) is the dangerous shape: a TRACKED file that depends on an UNTRACKED one.
  The repo looks healthy, every gate passes locally because the untracked file
  is sitting right there in the working tree, and the breakage only appears in
  a fresh checkout -- i.e. for somebody else, or after a restore, which is
  exactly when a backup is supposed to help.

  Existing coverage does not catch it:
    - doctrine-integrity-probe Check 12 is TOP-LEVEL-DIR granularity: it flags a
      directory with zero tracked files. `maintenance/` has hundreds, so it
      passes while individual files inside are unbacked.
    - task-folder-backup-completeness-probe is scoped to scheduled-tasks/*/ and
      keys on git-IGNORED, so it sees neither (2) nor (3).

WHAT IT DOES
  For every tracked text file, extracts quoted string literals that look like a
  path to a code/config file, resolves them repo-relative, and reports any that
  EXIST on disk but are NOT tracked.

  Deliberately narrow. It does NOT flag untracked files in general -- this tree
  carries ~70 of them and most are meant to be scratch. It flags only the ones
  something tracked actually depends on, which is what makes it quiet enough to
  be worth gating on later. Measured over the live tree at authoring time: 786
  tracked text files scanned, 2 hits, both already-documented exemptions.

EXIT CODES
  0 clean -- no tracked file references an unbacked path
  1 at least one [ACTION] finding
  2 could not look (git unavailable / not a repo). Never reported as clean:
    a zero that might mean "couldn't look" is a failure, not a pass.

REPORT-ONLY FOR NOW. Not wired into the pre-push gate; promoting it to a
blocking gate is a separate, deliberate decision (see OI-153) and should follow
a few days of quiet runs, not this file's authoring.
"""

import argparse, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATE_DIR = os.path.join(HERE, "_state")
LOG = os.path.join(STATE_DIR, "reference-backup-coverage.log")
EXEMPT_FILE = os.path.join(HERE, "_shared", "reference-backup-exempt.json")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Only these carry path literals worth resolving. Extending to every extension
# would pull in prose that merely NAMES a file without depending on it.
SCAN_EXTS = (".py", ".ps1", ".json")
# A quoted literal ending in a code/config extension. Backslashes are normalized
# out of the text before matching, so the class needs no escape handling.
REF_RE = re.compile(r'["\']([A-Za-z0-9_.:\-/]+\.(?:py|ps1|json|sh))["\']')
ABS_PREFIX = "c:/users/owner/.claude/"


def load_exempt(path=EXEMPT_FILE):
    """{rel_path: reason}. Missing file is fine -- an empty exemption set is the
    strict reading, and this probe fails toward reporting, not toward silence."""
    try:
        with io.open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("  [warn] exemption list unreadable (%s) -- treating as empty" % e)
        return {}
    out = {}
    for entry in raw if isinstance(raw, list) else []:
        p = (entry or {}).get("path")
        if p:
            out[p.replace("\\", "/").lower()] = entry.get("reason", "(no reason recorded)")
    return out


def tracked_files(repo):
    r = subprocess.run(["git", "-C", repo, "ls-files"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.splitlines() if p]


def extract_refs(text):
    """Repo-relative candidate paths referenced by quoted literals in `text`.

    Deliberately excludes any absolute path OUTSIDE the repo root (AppData,
    OneDrive session stores, etc.) -- code legitimately references those (the
    scheduled-task registries, fleet snapshots) and they were never going to be
    "in the backup" in the first place, so flagging them is a false positive,
    not a finding. Widening ABS_PREFIX to catch a bare drive letter without also
    filtering out other-drive/other-root absolute paths would have reintroduced
    exactly this noise -- verified live 2026-08-14 (4 spurious hits from AppData
    paths on the first run after the ':' fix, before this filter existed).
    """
    text = text.replace("\\\\", "/").replace("\\", "/")
    out = set()
    for m in REF_RE.finditer(text):
        raw = m.group(1)
        low = raw.lower()
        if low.startswith(ABS_PREFIX):
            rel = raw[len(ABS_PREFIX):]
        elif ":" in raw:
            continue                      # an absolute path OUTSIDE the repo root
        elif "/" in raw and not raw.startswith(("http", "/")):
            rel = raw
        else:
            continue                      # bare filename: too ambiguous to resolve
        rel = rel.lstrip("./")
        if rel:
            out.add(rel)
    return out


def _is_ignored(repo, rel):
    r = subprocess.run(["git", "-C", repo, "check-ignore", "-q", "--", rel],
                       capture_output=True)
    return r.returncode == 0


def scan(repo, tracked, exempt):
    """-> (findings, scanned_count).

    findings: [(ref, referrers, status)] where status is one of:
      "exempt"    -- on the reviewed-exempt list (info, never actionable)
      "ignored"   -- untracked but git DOES ignore it: a deliberate choice was
                     made somewhere (e.g. runtime state under _state/), just not
                     this file's decision to second-guess (info, not actionable)
      "unbacked"  -- untracked AND not ignored: nobody decided. This is the
                     actual OI-153 shape -- both real 2026-08-14 incidents
                     landed here, neither was ever gitignored.
    """
    tracked_lower = {p.lower() for p in tracked}
    hits, scanned = {}, 0
    for p in sorted(tracked):
        if not p.endswith(SCAN_EXTS):
            continue
        fp = os.path.join(repo, p)
        if not os.path.isfile(fp):
            continue                      # tracked but deleted in the worktree
        scanned += 1
        try:
            text = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for rel in extract_refs(text):
            if rel.lower() in tracked_lower:
                continue
            if os.path.isfile(os.path.join(repo, rel)):
                hits.setdefault(rel, set()).add(p)
    findings = []
    for rel, referrers in sorted(hits.items()):
        if rel.lower() in exempt:
            status = "exempt"
        elif _is_ignored(repo, rel):
            status = "ignored"
        else:
            status = "unbacked"
        findings.append((rel, sorted(referrers), status))
    return findings, scanned


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    tracked = tracked_files(a.repo)
    if tracked is None:
        print("[ERROR] git ls-files failed in %s -- the check DID NOT RUN. "
              "This is not a pass." % a.repo)
        return 2

    exempt = load_exempt()
    findings, scanned = scan(a.repo, tracked, exempt)
    actionable = [f for f in findings if f[2] == "unbacked"]
    ignored = [f for f in findings if f[2] == "ignored"]
    exempted = [f for f in findings if f[2] == "exempt"]

    print("reference-backup-coverage  scanned=%d tracked-text-file(s)  "
          "referenced-but-unbacked=%d  gitignored=%d  exempt=%d"
          % (scanned, len(actionable), len(ignored), len(exempted)))
    for rel, referrers, _ in exempted:
        print("  [info] %s -- reviewed-exempt: %s" % (rel, exempt[rel.lower()]))
    for rel, referrers, _ in ignored:
        print("  [info] %s -- gitignored, presumably a deliberate runtime-state "
              "choice (referenced by %s); not second-guessed here" % (rel, referrers[0]))
    for rel, referrers, _ in actionable:
        shown = referrers[0] + (" (+%d more)" % (len(referrers) - 1)
                                if len(referrers) > 1 else "")
        print("  [ACTION] %s is referenced by TRACKED %s, is NOT tracked, and is NOT "
              "gitignored -- nobody has decided what it is. A fresh checkout gets the "
              "referrer without its dependency. Fix: `git add` it, or gitignore it "
              "explicitly, or add it to %s with a dated reason."
              % (rel, shown, os.path.relpath(EXEMPT_FILE, a.repo).replace("\\", "/")))

    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write("%s scanned=%d unbacked=%d exempt=%d%s\n"
                    % (_now(), scanned, len(actionable), len(exempted),
                       ("" if not actionable else
                        " paths=" + ",".join(r for r, _, _ in actionable))))
    except Exception as e:
        print("  [warn] could not append to %s (%s)" % (LOG, e))

    if not actionable:
        print("OK -- every path referenced by a tracked file is itself tracked.")
    return 1 if actionable else 0


def _now():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def selftest():
    import tempfile, shutil
    results = []

    def check(cond, label):
        results.append((bool(cond), label))
        print("  %s %s" % ("PASS" if cond else "FAIL", label))

    # --- extract_refs ---
    check(extract_refs('spec_from_file_location("m", "maintenance/x.py")') == {"maintenance/x.py"},
          "extract_refs: repo-relative literal")
    check(extract_refs(r'p = "C:\\Users\\Owner\\.claude\\maintenance\\y.py"') == {"maintenance/y.py"},
          "extract_refs: absolute Windows literal normalizes to repo-relative")
    check(extract_refs('open("notes.py")') == set(),
          "extract_refs: bare filename is too ambiguous to resolve, ignored")
    check(extract_refs('url = "https://x/y.json"') == set(),
          "extract_refs: URLs are not paths")
    check(extract_refs(r'p = "C:\\Users\\Owner\\AppData\\Roaming\\x.json"') == set(),
          "extract_refs: an absolute path OUTSIDE the repo root is not a repo dependency")

    # --- scan, on a throwaway repo ---
    d = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "-C", d, "init", "-q"], capture_output=True)
        os.makedirs(os.path.join(d, "maintenance"), exist_ok=True)
        io.open(os.path.join(d, "maintenance", "dep.py"), "w").write("x = 1\n")
        io.open(os.path.join(d, "maintenance", "ref.py"), "w").write(
            'load("maintenance/dep.py")\n'
            'load("maintenance/state/ledger.json")\n')
        io.open(os.path.join(d, ".gitignore"), "w").write("maintenance/state/\n")
        subprocess.run(["git", "-C", d, "add", "maintenance/ref.py", ".gitignore"],
                       capture_output=True)
        os.makedirs(os.path.join(d, "maintenance", "state"), exist_ok=True)
        io.open(os.path.join(d, "maintenance", "state", "ledger.json"), "w").write("{}\n")
        tr = tracked_files(d)
        f, n = scan(d, tr, {})
        by_rel = {rel: (referrers, status) for rel, referrers, status in f}
        check(n == 1 and by_rel.get("maintenance/dep.py", ((), None))[1] == "unbacked",
              "scan: TRACKED referrer + UNTRACKED, UN-IGNORED dependency -> 'unbacked' "
              "(the actual OI-153 shape -- nobody decided)")
        check(by_rel.get("maintenance/state/ledger.json", ((), None))[1] == "ignored",
              "scan: TRACKED referrer + UNTRACKED but GITIGNORED dependency -> 'ignored', "
              "not flagged as an action (a decision was already made, just not to track it)")
        subprocess.run(["git", "-C", d, "add", "maintenance/dep.py"], capture_output=True)
        f2, _ = scan(d, tracked_files(d), {})
        f2_actionable = [x for x in f2 if x[2] == "unbacked"]
        check(f2_actionable == [], "scan: tracking the dependency clears the finding")
        f3, _ = scan(d, tr, {"maintenance/dep.py": "reviewed 2026-08-14"})
        by_rel3 = {rel: status for rel, _, status in f3}
        check(by_rel3.get("maintenance/dep.py") == "exempt",
              "scan: an exempt path is reported as info, not as an action")
        # An untracked file nothing references must NOT be flagged -- this is the
        # property that keeps the probe quiet enough to gate on.
        io.open(os.path.join(d, "maintenance", "scratch.py"), "w").write("y = 2\n")
        f4, _ = scan(d, tracked_files(d), {})
        f4_actionable = [x for x in f4 if x[2] == "unbacked"]
        check(f4_actionable == [], "scan: an UNREFERENCED untracked file is NOT flagged (noise floor)")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    bad = [l for ok, l in results if not ok]
    print("\nSELFTEST: %s (%d/%d)" % ("PASS" if not bad else "FAIL",
                                      len(results) - len(bad), len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
