"""Regression test for snapshot-validate.py v1.1 severity split.

Fixtures are synthetic and live in TEMP — never inside _state-history (the
ora-skill-store-drift-check HARD RULE bars staging scratch inside a store).
Reproduces both live defect classes plus the 2026-08-14 false-invalid case.
"""
import json, os, subprocess, sys, tempfile

PY = sys.executable
# Resolve next to this test so a worktree tests its own copy, not the live one.
VAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "snapshot-validate.py")
D = os.path.join(tempfile.gettempdir(), "ora_snapval_test", "fixtures")
os.makedirs(D, exist_ok=True)

def row(tid, cron="0 9 * * 1-5"):
    return {"taskId": tid, "enabled": True, "cronExpression": cron,
            "lastRunAt": "2026-08-14T13:00:00.000Z"}

def doc(n, date="2026-08-13", start=0):
    return {"snapshotDate": date, "capturedAtUtc": date + "T15:20:00Z",
            "source": "synthetic fixture", "tasks": [row("t%02d" % i)
                                                     for i in range(start, start + n)]}

def write(name, text):
    p = os.path.join(D, name)
    open(p, "w", encoding="utf-8").write(text)
    return p

# --- fixtures -------------------------------------------------------------
good30 = write("2026-08-13.lams.json", json.dumps(doc(30), indent=1))
good28 = write("2026-08-14.lams.json", json.dumps(doc(28, "2026-08-14"), indent=1))

# 2026-08-12 defect class: a COMPLETE document, then more rows appended after
# the close. 30 taskId occurrences; does not parse.
whole = json.dumps(doc(15), indent=1)
tail = ",\n" + ",\n".join(json.dumps(row("t%02d" % i)) for i in range(15, 30)) + "\n]\n}"
parsefail = write("2026-08-10.lams.json", whole + tail)

# 2026-08-11 defect class: truncated AND every row missing its schedule key.
noschedule = write("2026-08-09.lams.json", json.dumps(
    {"snapshotDate": "2026-08-09", "capturedAtUtc": "2026-08-09T15:20:00Z",
     "source": "synthetic fixture",
     "tasks": [{"taskId": "t%02d" % i, "enabled": True} for i in range(16)]}, indent=1))

# clean truncation: well-formed rows, just far too few. Count is the ONLY signal.
clean_trunc = write("2026-08-08.lams.json", json.dumps(doc(14, "2026-08-08"), indent=1))

# ora-automation-health-monitor (CC) writes .ahm-cc.json / .ahm-lams.json beside the
# integrity guard's .cc.json and the frozen .lams.json. Dated NEWER than every sibling
# so a glob that cross-matched would pick them and fail case 7 / case 10.
ahm_cc = write("2026-08-20.ahm-cc.json", json.dumps(doc(40, "2026-08-20"), indent=1))
ahm_lams = write("2026-08-20.ahm-lams.json", json.dumps(doc(29, "2026-08-20"), indent=1))
ahm_lams_bad = write("2026-08-21.ahm-lams.json", whole + tail)
gcc = write("2026-08-19.cc.json", json.dumps(doc(22, "2026-08-19"), indent=1))

def run(*args):
    r = subprocess.run([PY, VAL] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout

FAILURES = []

def check(label, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + ("" if cond else "  <- " + detail))
    if not cond:
        FAILURES.append(label)

print("\n1. THE 2026-08-14 CASE - valid file, fleet legitimately shrank 30 -> 28")
code, out = run("--path", good30, "--expect-count", "28")
check("exit 0 (was 1 in v1.0)", code == 0, "exit=%d" % code)
check("SNAPSHOT OK emitted", "SNAPSHOT OK" in out)
check("ROSTER-DELTA advisory emitted", "[ADVISORY] ROSTER-DELTA" in out)
check("no [ACTION] raised", "[ACTION]" not in out, out)

print("\n2. STRUCTURE STILL RULES - parse failure is still fatal")
code, out = run("--path", parsefail, "--expect-count", "30")
check("exit 1", code == 1, "exit=%d" % code)
check("PARSE-FAIL named", "PARSE-FAIL" in out)
check("count-would-have-passed note retained", "COUNT check" in out)

print("\n3. STRUCTURE STILL RULES - rows with no schedule key are still fatal")
code, out = run("--path", noschedule, "--expect-count", "16")
check("exit 1 even with count MATCHING", code == 1, "exit=%d" % code)
check("ROW-NO-SCHEDULE named", "ROW-NO-SCHEDULE" in out)

print("\n4. CLEAN TRUNCATION - count is the only signal; large delta still fatal")
code, out = run("--path", clean_trunc, "--expect-count", "28")
check("exit 1", code == 1, "exit=%d" % code)
check("COUNT-MISMATCH-LARGE named", "COUNT-MISMATCH-LARGE" in out)

print("\n5. TOLERANCE BOUNDARY - expected 27 -> tol max(3, 3) = 3")
code, out = run("--path", good30, "--expect-count", "27")  # delta +3, at tolerance
check("delta +3 advises", code == 0 and "ROSTER-DELTA" in out, "exit=%d" % code)
code, out = run("--path", good30, "--expect-count", "26")  # delta +4, over tolerance
check("delta +4 fails", code == 1 and "COUNT-MISMATCH-LARGE" in out, "exit=%d" % code)

print("\n6. --strict-count restores v1.0 behaviour for callers that want it")
code, out = run("--path", good30, "--expect-count", "28", "--strict-count")
check("exit 1 under --strict-count", code == 1, "exit=%d" % code)
check("COUNT-MISMATCH named", "COUNT-MISMATCH " in out)

print("\n7. LATENT BUG - --newest-valid on the day the count moves")
code, out = run("--dir", D, "--fleet", "lams", "--newest-valid", "--expect-count", "28")
check("finds a baseline (v1.0 returned NO-VALID-BASELINE)", code == 0, out)
check("picks newest STRUCTURALLY valid file", "2026-08-14.lams.json" in out, out)
check("no NO-VALID-BASELINE", "NO-VALID-BASELINE" not in out)

print("\n8. CONTROL - exact match stays silent")
code, out = run("--path", good28, "--expect-count", "28")
check("exit 0", code == 0)
check("no advisory when counts agree", "ROSTER-DELTA" not in out)

print("\n9. VALIDATOR CANNOT MASQUERADE AS CLEAN")
code, out = run("--path", os.path.join(D, "does-not-exist.json"), "--expect-count", "28")
check("missing file is non-zero", code != 0, "exit=%d" % code)

print("\n10. AHM SUFFIXES - each fleet name selects only its own producer's files")
code, out = run("--dir", D, "--fleet", "ahm-cc", "--newest-valid")
check("ahm-cc accepted", code == 0, out)
check("ahm-cc picks .ahm-cc.json", "2026-08-20.ahm-cc.json" in out, out)
code, out = run("--dir", D, "--fleet", "ahm-lams", "--newest-valid")
check("ahm-lams skips the newer unparseable file", "2026-08-20.ahm-lams.json" in out, out)
code, out = run("--dir", D, "--fleet", "cc", "--newest-valid")
check("cc never selects .ahm-cc.json", code == 0 and "2026-08-19.cc.json" in out, out)
code, out = run("--dir", D, "--fleet", "lams", "--newest-valid")
check("lams never selects .ahm-lams.json", "ahm-lams" not in out, out)

print("\n" + ("ALL PASS" if not FAILURES else "FAILURES: " + ", ".join(FAILURES)))
sys.exit(1 if FAILURES else 0)
