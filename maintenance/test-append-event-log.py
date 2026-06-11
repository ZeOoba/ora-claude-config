#!/usr/bin/env python3
"""Tests for append-event-log.py — the collision-safe newest-first inserter.

Why this exists: 2026-06-11 saw three stale-anchor collisions in one day from
concurrent sessions Edit-anchoring the same event_log.md header. The helper's
pure function inserts a new '## ' entry immediately BEFORE the first existing
'## ' entry (newest-first), preserving frontmatter and intro prose.

Run: python test-append-event-log.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ael", os.path.join(HERE, "append-event-log.py"))
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


DOC = ("---\nname: event_log\n---\n\n# ORA Event Log (append-only, newest first)\n\n"
       "Intro prose line.\n\n## 2026-06-10 — older entry\n- detail\n")
ENTRY = "## 2026-06-11 — new entry\n- new detail"

out = ael.insert_newest(DOC, ENTRY)
expect("inserts before first '## '", out.index("## 2026-06-11") < out.index("## 2026-06-10"))
expect("frontmatter preserved", out.startswith("---\nname: event_log\n---"))
expect("intro prose preserved before entry",
       out.index("Intro prose line.") < out.index("## 2026-06-11"))
expect("older entry intact", "## 2026-06-10 — older entry\n- detail" in out)
expect("blank-line separation", "\n\n## 2026-06-11" in out and "new detail\n\n## 2026-06-10" in out)

# no existing entries -> append at end
no_entries = "---\nx: y\n---\n\n# ORA Event Log\n\nIntro.\n"
out2 = ael.insert_newest(no_entries, ENTRY)
expect("no entries -> appended at end", out2.rstrip().endswith("- new detail"))
expect("no entries -> intro intact", "Intro." in out2)

# idempotence of shape: inserting twice keeps both, newest first
out3 = ael.insert_newest(out, "## 2026-06-12 — newest")
expect("second insert lands first",
       out3.index("## 2026-06-12") < out3.index("## 2026-06-11") < out3.index("## 2026-06-10"))

# entry must be a dated '## ' header
try:
    ael.insert_newest(DOC, "not a header")
    expect("rejects non-'## ' entry", False)
except ValueError:
    expect("rejects non-'## ' entry", True)

# '## ' inside frontmatter or intro must not be mistaken for an entry anchor
tricky = "---\ndescription: \"## not an entry\"\n---\n\n# ORA Event Log\n\n## 2026-06-09 — real\n"
out4 = ael.insert_newest(tricky, ENTRY)
expect("frontmatter '## ' not used as anchor",
       out4.index("## 2026-06-11") > out4.index('description'))
expect("real entry still after new one", out4.index("## 2026-06-11") < out4.index("## 2026-06-09"))

passed = sum(1 for ok, _ in results if ok)
print("\nappend-event-log tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
