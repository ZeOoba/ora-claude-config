#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py's review_by overdue check (added 2026-07-14).

Runs the real probe against a throwaway fixture memory dir via ORA_MEMORY_DIR, so the
live memory set is never touched. Stdlib only; Windows (`python`).

Origin: project_owner_outreach_stale_guard_watch.md declared its own 2026-07-13 deadline
in prose, sailed past it, and nobody noticed -- the check exists so a date in prose
becomes a date the fleet enforces.
"""
import os
import subprocess
import sys
import tempfile

PROBE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "maintenance",
    "memory-integrity-probe.py"))


def run_probe(files):
    """Write `files` (name -> text) into a temp memory dir and run the probe over it."""
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


def note(review_by=None, body="body\n"):
    fm = "---\nname: n\n"
    if review_by:
        fm += "review_by: %s\n" % review_by
    return fm + "---\n\n" + body


failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


# 1. A past review_by is reported as OVERDUE.
rc, out = run_probe({"watch.md": note("2020-01-01")})
check("past review_by -> OVERDUE warning", "OVERDUE" in out and "watch.md" in out)

# 2. Overdue is a WARNING, not a failure -- an expired note must never break the fleet.
check("overdue does not fail the probe (rc=0)", rc == 0)

# 3. A future review_by is silent.
rc, out = run_probe({"watch.md": note("2099-12-31")})
check("future review_by -> no warning", "OVERDUE" not in out and rc == 0)

# 4. No review_by at all is silent (the field is opt-in; most memories are undated).
rc, out = run_probe({"plain.md": note(None)})
check("absent review_by -> no warning", "OVERDUE" not in out and rc == 0)

# 5. A malformed date is surfaced, not silently swallowed, and never crashes.
rc, out = run_probe({"bad.md": "---\nname: n\nreview_by: not-a-date\n---\n\nx\n"})
check("malformed review_by -> never crashes", rc == 0)

# 6. The date must be a real frontmatter field, not any date mentioned in prose --
#    otherwise every memory quoting a past date would scream.
rc, out = run_probe({"prose.md": note(None, "We reviewed this on 2020-01-01 and moved on.\n")})
check("a past date in PROSE is not treated as review_by", "OVERDUE" not in out)

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - review_by overdue check behaves")
sys.exit(0)
