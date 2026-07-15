"""rules.md dated-header write-time guard -- PreToolUse hook for Edit|Write|MultiEdit.

memory-policy.md sec 2 says living docs (rules.md is one, per sec 1) are
"overwritten in place to reflect current truth ... do not accumulate dated
## History walls inside them" -- history goes to event_log.md instead. That
principle went unenforced until the 2026-07-14 consolidation pass found
rules.md violating it: 10 dated section headers, word count up 2030 -> 2677
(+32%) across just 3 commits (2026-07-09 to 2026-07-12). This hook closes the
loop at the point of the write, the same way memory-index-guard.py closes
MEMORY.md's index-hook-length loop: a NEW dated header never lands on disk.

Deliberately mirrors memory-index-guard.py's shape (same PreToolUse deny
mechanism, same simulate-then-check pattern, same before/after-count
no-lockout rule) rather than inventing a new one.

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error --
bad stdin, missing field, unreadable file, an edit shape we can't simulate --
it prints nothing and exits 0 (ALLOW). A bug here must NEVER block a tool call.

Scope: rules.md only, not the full living-doc set (00_system_of_record.md,
firm.md, tech.md, etc.) -- this is the one file where the problem was actually
measured this session. Extend to others only if the same pattern is confirmed
there too, not speculatively.

Native Edit/Write/MultiEdit only, not Desktop-Commander-driven -- rules.md is
a Code-surface-maintained governance file, not written by scheduled tasks the
way MEMORY.md or the registries are. Revisit if that changes.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import re
import sys

DEFAULT_RULES_MD = (
    "C:/Users/Owner/.claude/projects/"
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/rules.md")

# A markdown header (## through ######) whose line carries a YYYY-MM-DD date
# anywhere in it -- the exact pattern the 2026-07-14 consolidation removed
# 10 instances of (e.g. "## 8. Parked-task chips ... (race-proofing, 2026-06-11)").
DATED_HEADER_RE = re.compile(r'^#{2,6}\s.*\b20\d\d-\d\d-\d\d\b')


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def target_rules_md():
    return os.environ.get("ORA_RULES_MD") or DEFAULT_RULES_MD


def is_rules_md(file_path):
    return _norm(file_path) == _norm(target_rules_md())


def simulate_edit(tool_name, tool_input, current_text):
    """Return the post-edit text WITHOUT writing anything, or None if the
    tool/input shape can't be simulated (caller must then fail open)."""
    if tool_name == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None

    if tool_name == "Edit":
        old = tool_input.get("old_string")
        new = tool_input.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str) or old == "":
            return None
        if tool_input.get("replace_all"):
            return current_text.replace(old, new)
        if current_text.count(old) != 1:
            return None  # ambiguous/no match -- let the real Edit tool raise its own error
        return current_text.replace(old, new, 1)

    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return None
        text = current_text
        for e in edits:
            if not isinstance(e, dict):
                return None
            old = e.get("old_string")
            new = e.get("new_string")
            if not isinstance(old, str) or not isinstance(new, str) or old == "":
                return None
            if e.get("replace_all"):
                text = text.replace(old, new)
            else:
                if text.count(old) != 1:
                    return None
                text = text.replace(old, new, 1)
        return text

    return None


def dated_header_lines(text):
    """[(line_no, line_text), ...] for every header line carrying a YYYY-MM-DD date."""
    out = []
    for ln_no, ln in enumerate(text.splitlines(), 1):
        if DATED_HEADER_RE.match(ln):
            out.append((ln_no, ln.strip()))
    return out


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    if not is_rules_md(file_path):
        return

    try:
        with open(target_rules_md(), "r", encoding="utf-8") as fh:
            current_text = fh.read()
    except Exception:
        return  # can't read current content -- fail open

    simulated = simulate_edit(tool_name, tool_input, current_text)
    if simulated is None:
        return  # couldn't simulate this shape -- fail open

    # Only block headers THIS edit introduces or worsens. A pre-existing dated
    # header (or a consolidation pass mid-flight) never locks the file -- same
    # no-lockout rule as memory-index-guard.py.
    before = dated_header_lines(current_text)
    after = dated_header_lines(simulated)
    if len(after) <= len(before):
        return

    lines = "\n".join("- line %d: %s" % (ln, txt) for ln, txt in after)
    reason = (
        "rules.md dated-header cap: this edit would add a section header "
        "carrying a YYYY-MM-DD date --\n%s\n"
        "memory-policy.md sec 2: living docs are overwritten in place to "
        "reflect current truth; history goes to event_log.md, not a dated "
        "## History wall in the doc itself. State the rule dateless here and "
        "log the incident/reasoning to event_log.md instead (via "
        "maintenance/append-event-log.py)." % lines
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a bug must never block a tool call
    sys.exit(0)
