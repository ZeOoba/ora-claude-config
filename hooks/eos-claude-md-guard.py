"""Engineering OS CLAUDE.md edit-time doctrine guard -- PreToolUse hook for
Edit|Write|MultiEdit.

Simulates the post-edit content of CLAUDE.md (without writing it) and runs
doctrine-integrity-probe.py's check_size_and_dates() against the simulated
text. On a hard-fail (size budget or bare date), DENIES the edit via the
same permissionDecision:deny mechanism eos-plan-gate.py already uses -- the
violating state never lands on disk. This surfaces what was previously only
caught at `git push` time (git-prepush-doctrine-gate.py), hours later.

There is no local precedent for a blocking PostToolUse hook in this repo
(every existing PostToolUse hook is fail-open by design) -- this is
deliberately PreToolUse, reusing eos-plan-gate.py's proven deny mechanism
instead of inventing a new one.

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error --
bad stdin, missing field, unreadable file, an edit shape we can't simulate --
it prints nothing and exits 0 (ALLOW). A bug must NEVER block a tool call.

Stdlib only. ASCII-only. Windows (`python`).
"""

import importlib.util
import json
import os
import sys

MAINTENANCE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maintenance"))
DEFAULT_CLAUDE_MD = "C:/Users/Owner/.claude/CLAUDE.md"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def is_claude_md(file_path):
    target = os.environ.get("EOS_CLAUDE_MD") or DEFAULT_CLAUDE_MD
    return _norm(file_path) == _norm(target)


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
            return None  # ambiguous/no match -- let the real Edit tool handle its own error
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


def _load_probe():
    probe_path = os.path.join(MAINTENANCE_DIR, "doctrine-integrity-probe.py")
    spec = importlib.util.spec_from_file_location("doctrine_integrity_probe", probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_stdin_text():
    """Decode stdin explicitly as UTF-8, off the raw buffer -- never trust
    sys.stdin's own text-mode encoding. A hook spawned directly by the
    harness (as opposed to a POSIX-locale shell) can get sys.stdin.encoding
    resolved to the Windows ANSI codepage instead of UTF-8 -- confirmed live
    2026-07-17: a harness-spawned process logged sys.stdin.encoding ==
    'cp1252' and silently mangled a payload's em-dash into 3-character
    mojibake before json.loads ever ran. CLAUDE.md's own prose is full of
    non-ASCII punctuation (em-dashes, arrows, >=/<=, middle dots), so almost
    any real old_string trips this: current_text.count(old) drops to 0,
    simulate_edit() returns None, and the hook fails open -- exactly how a
    bare ISO date landed in CLAUDE.md undenied. Reading the raw bytes and
    decoding them ourselves makes this independent of whatever codepage the
    parent process happened to inherit."""
    return sys.stdin.buffer.read().decode("utf-8")


def main():
    payload = json.loads(_read_stdin_text())
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    if not is_claude_md(file_path):
        return

    target = os.environ.get("EOS_CLAUDE_MD") or DEFAULT_CLAUDE_MD
    try:
        with open(target, "r", encoding="utf-8") as fh:
            current_text = fh.read()
    except Exception:
        return  # can't read current content -- fail open

    simulated = simulate_edit(tool_name, tool_input, current_text)
    if simulated is None:
        return  # couldn't simulate this shape -- fail open

    probe = _load_probe()
    violations = probe.check_size_and_dates(simulated)
    if not violations:
        return

    reason = (
        "Engineering OS doctrine check: this edit would leave CLAUDE.md in "
        "violation --\n- " + "\n- ".join(violations) +
        "\nFix before this edit lands (checks 5/6 of doctrine-integrity-probe.py; "
        "same hard-fail the pre-push gate enforces, surfaced now instead of at push)."
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
