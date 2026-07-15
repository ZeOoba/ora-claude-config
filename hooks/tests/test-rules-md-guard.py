#!/usr/bin/env python3
"""Tests for rules-md-guard.py (PreToolUse, added 2026-07-14).

Drives the real hook as a subprocess with real PreToolUse payloads against a temp
rules.md (via ORA_RULES_MD), so the live file is never touched.

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
    os.path.dirname(os.path.abspath(__file__)), "..", "rules-md-guard.py"))

CLEAN = "## 1. Working style\n\n- some standing rule, no date.\n"
DATED_NEW = CLEAN + "\n## 14. New rule (2026-07-15)\n\n- content\n"
OTHER_FILE = "C:/Users/Owner/.claude/CLAUDE.md"

failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


def run(payload, rules_text):
    """Run the hook against a temp rules.md. Returns (denied: bool, reason: str)."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rules.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(rules_text)
        payload.setdefault("tool_input", {}).setdefault("file_path", p)
        env = dict(os.environ, ORA_RULES_MD=p)
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


# 1. THE POINT OF THE HOOK: a Write introducing a new dated header is denied.
denied, reason = run({"tool_name": "Write", "tool_input": {"content": DATED_NEW}}, CLEAN)
check("Write adding a dated header -> DENY", denied)
check("deny reason names memory-policy.md sec 2 and event_log.md",
      "memory-policy" in reason and "event_log.md" in reason)

# 2. A Write with only dateless headers passes.
denied, _ = run({"tool_name": "Write",
                 "tool_input": {"content": CLEAN + "\n## 14. Another dateless rule\n"}}, CLEAN)
check("Write with only dateless headers -> allow", not denied)

# 3. An Edit that introduces a dated header is denied.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": CLEAN, "new_string": DATED_NEW}}, CLEAN)
check("Edit introducing a dated header -> DENY", denied)

# 4. NO-LOCKOUT: if the file ALREADY has a dated header, an unrelated edit that
#    doesn't add another one must still pass -- a pre-existing violation (or a
#    consolidation-in-progress state) must never brick the file.
ALREADY_DATED = CLEAN + "\n## 9. Old rule (2026-06-01)\n\n- content\n"
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": "some standing rule, no date.",
                                "new_string": "some standing rule, no date, tweaked."}},
                ALREADY_DATED)
check("pre-existing dated header + unrelated edit -> allow (no lockout)", not denied)

# 5. NO-LOCKOUT: an edit that REMOVES a dated header (a consolidation pass) must pass.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": "## 9. Old rule (2026-06-01)",
                                "new_string": "## 9. Old rule"}},
                ALREADY_DATED)
check("consolidation edit removing a dated header -> allow", not denied)

# 6. Other files are none of this hook's business.
denied, _ = run({"tool_name": "Write",
                 "tool_input": {"file_path": OTHER_FILE, "content": DATED_NEW}}, CLEAN)
check("write to a non-rules.md file -> allow", not denied)

# 7. A date appearing in prose (not a header line) is not flagged.
PROSE_DATE = CLEAN + "\n- Gabriel decided this on 2026-07-14, see event_log.md.\n"
denied, _ = run({"tool_name": "Write", "tool_input": {"content": PROSE_DATE}}, CLEAN)
check("date in prose body text (not a header) -> allow", not denied)

# 8. FAIL-OPEN: garbage stdin must never block a tool call.
r = subprocess.run([sys.executable, HOOK], input="not json at all",
                   capture_output=True, text=True)
check("malformed stdin -> silent allow, exit 0", r.returncode == 0 and not (r.stdout or "").strip())

# 9. FAIL-OPEN: an unsimulatable edit shape (ambiguous old_string) allows rather than guesses.
denied, _ = run({"tool_name": "Edit",
                 "tool_input": {"old_string": "nope-not-present", "new_string": DATED_NEW}}, CLEAN)
check("unsimulatable edit shape -> allow (fail open)", not denied)

# 10. A ### (h3) dated header is caught too, not just ##.
H3_DATED = CLEAN + "\n### 14a. Sub-rule (2026-07-15)\n\n- content\n"
denied, _ = run({"tool_name": "Write", "tool_input": {"content": H3_DATED}}, CLEAN)
check("### h3 dated header -> DENY", denied)

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - rules-md-guard denies new dated header walls, never locks the file")
sys.exit(0)
