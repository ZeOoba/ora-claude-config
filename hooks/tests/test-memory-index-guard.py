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

# 10-16. DESKTOP COMMANDER COVERAGE (added 2026-07-14): several scheduled tasks are
# approved to write memory files through Desktop Commander's write_file/edit_block MCP
# tools instead of native Edit/Write/MultiEdit -- a distinct tool_input shape (write_file
# uses "path" not "file_path"; edit_block has no "replace_all", it has
# "expected_replacements"). A same-day regression (MEMORY.md line 85, 170 chars) reached
# disk despite this guard supposedly being live, because the guard only recognized native
# tool calls. These cases close that gap for both known tool-name prefixes.
DC_WRITE_FILE_NAMES = [
    "mcp__Desktop_Commander__write_file",
    "mcp__plugin_desktop-commander_desktop-commander__write_file",
]
DC_EDIT_BLOCK_NAMES = [
    "mcp__Desktop_Commander__edit_block",
    "mcp__plugin_desktop-commander_desktop-commander__edit_block",
]

for name in DC_WRITE_FILE_NAMES:
    # 10. write_file in (default) rewrite mode introducing an over-length hook -> DENY.
    denied, _ = run({"tool_name": name, "tool_input": {"path": "PLACEHOLDER", "content": SHORT + LONG}}, SHORT)
    check("%s rewrite adding an over-length hook -> DENY" % name, denied)

    # 11. write_file in append mode: the "content" param is only the appended chunk, not
    # the full file -- simulate() must concatenate onto current_text, not replace it.
    denied, _ = run({"tool_name": name,
                     "tool_input": {"path": "PLACEHOLDER", "content": LONG, "mode": "append"}}, SHORT)
    check("%s append introducing an over-length hook -> DENY" % name, denied)

    denied, _ = run({"tool_name": name,
                     "tool_input": {"path": "PLACEHOLDER", "content": SHORT, "mode": "append"}}, SHORT)
    check("%s append with a compliant hook -> allow" % name, not denied)

    # 12. Non-string content (Excel 2D-array mode) can't be simulated as index text -> allow.
    denied, _ = run({"tool_name": name,
                     "tool_input": {"path": "PLACEHOLDER", "content": [["a", "b"]]}}, SHORT)
    check("%s non-string content -> allow (fail open)" % name, not denied)

for name in DC_EDIT_BLOCK_NAMES:
    # 13. edit_block's native field names (file_path/old_string/new_string) introducing
    # an over-length hook -> DENY, same as the native Edit tool.
    denied, _ = run({"tool_name": name,
                     "tool_input": {"old_string": SHORT, "new_string": LONG}}, SHORT)
    check("%s introducing an over-length hook -> DENY" % name, denied)

    # 14. expected_replacements != 1 means simulating a single replace() would be a guess
    # about how many replacements Desktop Commander will actually make -> fail open.
    denied, _ = run({"tool_name": name,
                     "tool_input": {"old_string": SHORT, "new_string": LONG, "expected_replacements": 2}},
                    SHORT + SHORT)
    check("%s with expected_replacements=2 -> allow (fail open, ambiguous count)" % name, not denied)

    # 15. Excel/Word range mode (no old_string/new_string, uses "range"/"content" instead)
    # isn't text-length-simulatable -> allow.
    denied, _ = run({"tool_name": name,
                     "tool_input": {"range": "Sheet1!A1:B2", "content": [["x", "y"]]}}, SHORT)
    check("%s Excel/Word range mode -> allow (fail open, not text)" % name, not denied)

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - memory-index-guard denies new bloat, never locks the index")
sys.exit(0)
