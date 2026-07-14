#!/usr/bin/env python3
"""Tests for memory-index-guard.py (PreToolUse, added 2026-07-14).

Drives the real hook as a subprocess with real PreToolUse payloads against a temp
MEMORY.md (via ORA_MEMORY_INDEX), so the live index is never touched.

deny  == stdout carries permissionDecision "deny"
allow == empty stdout (the hook stays silent)

Stdlib only; Windows (`python`).
"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "memory-index-guard.py"))

SHORT = "- [A](a.md) - short hook\n"
LONG = "- [B](b.md) - " + ("x" * 200) + "\n"          # 200-char hook, way over the 150 cap
OTHER_FILE = "C:/Users/Owner/.claude/CLAUDE.md"       # a path the guard must ignore

failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


def run(payload, index_text):
    """Run the hook against a temp index. Returns (denied: bool, reason: str)."""
    with tempfile.TemporaryDirectory() as d:
        idx = os.path.join(d, "MEMORY.md")
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write(index_text)
        # Point the payload at the temp index unless the test overrode file_path.
        payload.setdefault("tool_input", {}).setdefault("file_path", idx)
        env = dict(os.environ, ORA_MEMORY_INDEX=idx)
        r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                           capture_output=True, text=True, env=env)
        out = (r.stdout or "").strip()
        if not out:
            return False, ""
        try:
            data = json.loads(out)
        except ValueError:
            return False, ""
        hso = data.get("hookSpecificOutput", {})
        return hso.get("permissionDecision") == "deny", hso.get("permissionDecisionReason", "")


# 1. THE POINT OF THE HOOK: a Write that introduces an over-length hook is denied.
denied, reason = run({"tool_name": "Write", "tool_input": {"content": SHORT + LONG}}, SHORT)
check("Write adding an over-length hook -> DENY", denied)
check("deny reason names the cap and points to the linked file", "150" in reason and "one-line" in reason.lower())

# 2. A Write with only compliant hooks passes.
denied, _ = run({"tool_name": "Write", "tool_input": {"content": SHORT + SHORT}}, SHORT)
check("Write with compliant hooks -> allow", not denied)

# 3. An Edit that introduces an over-length hook is denied.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": SHORT, "new_string": LONG}}, SHORT)
check("Edit introducing an over-length hook -> DENY", denied)

# 4. NO-LOCKOUT: if the index is ALREADY dirty, an unrelated edit that doesn't make it
#    worse must still pass. Otherwise a pre-existing violation would make the index
#    un-editable until someone ran a full consolidation first -- punishing the wrong write.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": SHORT, "new_string": "- [A](a.md) - still short\n"}},
                SHORT + LONG)
check("pre-existing violation + unrelated edit -> allow (no lockout)", not denied)

# 5. NO-LOCKOUT: an edit that REDUCES the violations (a consolidation pass) must pass.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": LONG, "new_string": SHORT}}, SHORT + LONG)
check("consolidation edit that fixes a violation -> allow", not denied)

# 6. Other files are none of this hook's business.
denied, _ = run({"tool_name": "Write",
                 "tool_input": {"file_path": OTHER_FILE, "content": LONG}}, SHORT)
check("write to a non-MEMORY.md file -> allow", not denied)

# 7. Blockquote pointer lines at the top of MEMORY.md are not index entries.
denied, _ = run({"tool_name": "Write",
                 "tool_input": {"content": "> " + ("x" * 300) + "\n" + SHORT}}, SHORT)
check("long blockquote line is not an index entry -> allow", not denied)

# 8. FAIL-OPEN: garbage stdin must never block a tool call.
r = subprocess.run([sys.executable, HOOK], input="not json at all",
                   capture_output=True, text=True)
check("malformed stdin -> silent allow, exit 0", r.returncode == 0 and not (r.stdout or "").strip())

# 9. FAIL-OPEN: an unsimulatable edit shape (ambiguous old_string) allows rather than guesses.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": "nope-not-present", "new_string": LONG}}, SHORT)
check("unsimulatable edit shape -> allow (fail open)", not denied)

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - memory-index-guard denies new bloat, never locks the index")
sys.exit(0)
