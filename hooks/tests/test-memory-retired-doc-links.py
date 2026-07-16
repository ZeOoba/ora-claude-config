#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py's retired/archived-doc link check.

Runs the real probe against a throwaway fixture memory dir via ORA_MEMORY_DIR, so the
live memory set is never touched. Stdlib only; Windows (`python`).

Origin: 2026-07-15 the probe began failing on reference_newyorkfed_api_403_hosted_fetch.md
because its body links [..](feedback_webfetch_markdown_false_negatives.md) -- a LIVE,
present, indexed memory file -- yet RETIRED_DOCS carries a bare "feedback_" prefix meant
only for the 7 retired feedback_*_merged-into-rules_2026-06-03.md docs. The over-broad
prefix false-positived on the live feedback_* family. Fix: guard on presence -- a link to
a file that still exists in the root memory set is never a retired-doc violation.
"""
import os
import subprocess
import sys
import tempfile

PROBE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "maintenance",
    "memory-integrity-probe.py"))


def run_probe(files):
    """Write `files` (name -> text) into a temp memory dir and run the probe over it.

    Every file is listed in the generated index so index reconciliation stays clean
    and the only thing under test is the retired-doc link check.
    """
    with tempfile.TemporaryDirectory() as d:
        index = "# Index\n\n" + "".join(
            "- [%s](%s) - hook\n" % (n, n) for n in files if n != "MEMORY.md")
        with open(os.path.join(d, "MEMORY.md"), "w", encoding="utf-8") as fh:
            fh.write(index)
        for name, text in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        env = dict(os.environ, ORA_MEMORY_DIR=d)
        r = subprocess.run([sys.executable, PROBE], capture_output=True, text=True, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")


failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


# 1. THE regression: a body link to a LIVE feedback_* file (present in the dir) is NOT
#    flagged as a retired-doc link, even though it shares the "feedback_" retired prefix.
rc, out = run_probe({
    "reference_x.md": "See also [W](feedback_webfetch_markdown_false_negatives.md) for more.\n",
    "feedback_webfetch_markdown_false_negatives.md": "live note\n",
})
check("live feedback_* body link -> not flagged (rc=0)",
      rc == 0 and "retired/archived" not in out)

# 2. A body link to a genuinely-retired doc that is ABSENT from the set IS still flagged.
rc, out = run_probe({
    "reference_y.md": "Old pointer: [T](reference_tech.md) should be tech.md now.\n",
})
check("absent retired-doc body link -> flagged (rc=1)",
      rc == 1 and "reference_tech.md" in out and "retired/archived" in out)

# 3. A body link to an absent retired feedback merged-doc IS flagged (the prefix still
#    does its real job when the target is genuinely gone).
rc, out = run_probe({
    "reference_z.md": "Merged away: [Q](feedback_qb_desktop_merged-into-rules_2026-06-03.md).\n",
})
check("absent retired feedback merged-doc link -> flagged (rc=1)",
      rc == 1 and "feedback_qb_desktop_merged-into-rules_2026-06-03.md" in out)

# 4. A retired-doc name appearing only inside MEMORY.md is not treated as a violation
#    (the index is deliberately skipped by the check).
rc, out = run_probe({
    "plain.md": "nothing to see\n",
})
# plain.md is present + indexed; no retired links anywhere -> clean.
check("no retired links anywhere -> clean (rc=0)",
      rc == 0 and "retired/archived" not in out)

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - retired-doc link check no longer false-positives on live feedback_*")
sys.exit(0)
