"""MEMORY.md index-hook write-time guard -- PreToolUse hook for Edit|Write|MultiEdit plus
Desktop Commander's write_file/edit_block (both the mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ tool-name prefixes -- both exist live in
this stack). Several scheduled tasks are approved to write memory files through Desktop
Commander instead of native Edit/Write/MultiEdit; a same-day regression (MEMORY.md line 85,
170 chars) reached disk because the guard only recognized native tool calls. Extended
2026-07-14 to close that gap -- see hooks/tests/test-memory-index-guard.py cases 10-16.

memory-policy.md sec 3 says each MEMORY.md index entry is "a one-line description";
doctrine-integrity-probe.py check 9 operationalizes that as a 150-char cap on the HOOK
text (the description after the link) and WARNs when an entry blows past it.

That detection was purely retrospective, so the count grew ~1/day (6 -> 14 -> 15 across
three daily probe runs) and needed a manual consolidation pass on 2026-07-14 to clear.
This hook closes the loop at the point of the write: an over-length hook never lands on
disk in the first place, so the daily probe has nothing to accumulate.

Deliberately mirrors eos-claude-md-guard.py (same PreToolUse deny mechanism, same
simulate-then-check shape) rather than inventing a new pattern. It imports the CAP and
the ENTRY REGEX from doctrine-integrity-probe.py so the write-time rule and the audit-time
rule cannot drift apart -- change the cap in one place and both move.

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error -- bad stdin,
missing field, unreadable file, an unimportable probe, an edit shape we can't simulate --
it prints nothing and exits 0 (ALLOW). A bug here must NEVER block a tool call, and it
must never be able to lock Gabriel out of editing his own memory index (cf.
feedback_confidentiality_guard_selfdeadlock.md -- a fail-CLOSED guard bricked Write/Edit/
Bash machine-wide; this one fails OPEN by construction).

Stdlib only. ASCII-only. Windows (`python`).
"""

import importlib.util
import json
import os
import sys

MAINTENANCE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maintenance"))
DEFAULT_MEMORY_INDEX = (
    "C:/Users/Owner/.claude/projects/"
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md")

# Tool-call shape knowledge (which tool names write files, and under which path arg)
# is SHARED via hooks/lib/tool_call_paths.py (2026-07-18) -- this guard and
# registry-write-guard.py each independently rediscovered the same Desktop Commander
# blind spot on 2026-07-14, which is exactly the drift a shared normalization layer
# prevents. The fallback below preserves this guard's pre-refactor parsing verbatim,
# so a broken/missing lib degrades to the OLD behavior, never to a new hole -- and
# this guard's fail-open posture is unchanged either way.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
try:
    from tool_call_paths import (  # noqa: E402
        DC_EDIT_BLOCK_NAMES, DC_WRITE_FILE_NAMES, primary_write_path)
except Exception:
    DC_WRITE_FILE_NAMES = frozenset((
        "mcp__Desktop_Commander__write_file",
        "mcp__plugin_desktop-commander_desktop-commander__write_file",
    ))
    DC_EDIT_BLOCK_NAMES = frozenset((
        "mcp__Desktop_Commander__edit_block",
        "mcp__plugin_desktop-commander_desktop-commander__edit_block",
    ))

    def primary_write_path(tool_name, tool_input):
        # pre-refactor parsing, verbatim: generic file_path-or-path for any tool
        p = tool_input.get("file_path") or tool_input.get("path")
        return p if isinstance(p, str) and p else None


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def target_index():
    return os.environ.get("ORA_MEMORY_INDEX") or DEFAULT_MEMORY_INDEX


def is_memory_index(file_path):
    return _norm(file_path) == _norm(target_index())


def simulate_edit(tool_name, tool_input, current_text):
    """Return the post-edit text WITHOUT writing anything, or None if the tool/input
    shape can't be simulated (caller must then fail open)."""
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

    if tool_name in DC_WRITE_FILE_NAMES:
        # Desktop Commander's write_file uses "path"/"content"/"mode", not Write's
        # "file_path"/"content". In append mode, "content" is only the appended chunk --
        # simulating it as the full new file (like rewrite) would be wrong.
        content = tool_input.get("content")
        if not isinstance(content, str):
            return None  # e.g. Excel 2D-array content -- not text, can't simulate
        if tool_input.get("mode") == "append":
            return current_text + content
        return content  # "rewrite" (the schema default)

    if tool_name in DC_EDIT_BLOCK_NAMES:
        # edit_block shares Edit's field names (file_path/old_string/new_string) but has
        # no "replace_all" -- it has "expected_replacements" (default 1). A count other
        # than 1 means simulating a single replace() would be guessing how many
        # replacements Desktop Commander will actually make, so fail open instead.
        old = tool_input.get("old_string")
        new = tool_input.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str) or old == "":
            return None  # Excel/Word range mode (range/content, no old_string) etc.
        if tool_input.get("expected_replacements", 1) != 1:
            return None
        if current_text.count(old) != 1:
            return None
        return current_text.replace(old, new, 1)

    return None


def _load_probe():
    probe_path = os.path.join(MAINTENANCE_DIR, "doctrine-integrity-probe.py")
    spec = importlib.util.spec_from_file_location("doctrine_integrity_probe", probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def over_length_hooks(text, entry_re, maxlen):
    """[(line_no, hook_len, hook_preview), ...] for index entries whose hook exceeds maxlen.

    Same measurement as doctrine-integrity-probe.py check 9: the hook is the text AFTER
    the markdown link, not the whole bullet.
    """
    over = []
    for ln_no, ln in enumerate(text.splitlines(), 1):
        m = entry_re.match(ln)
        if not m:
            continue
        hook = ln[m.end():].strip()
        if len(hook) > maxlen:
            over.append((ln_no, len(hook), hook[:60]))
    return over


def _read_stdin_text():
    """Decode stdin explicitly as UTF-8, off the raw buffer -- never trust
    sys.stdin's own text-mode encoding. A hook spawned directly by the
    harness (as opposed to a POSIX-locale shell) can get sys.stdin.encoding
    resolved to the Windows ANSI codepage instead of UTF-8 -- confirmed live
    in eos-claude-md-guard.py (2026-07-17): a harness-spawned process logged
    sys.stdin.encoding == 'cp1252' and silently mangled a payload's em-dash
    into 3-character mojibake before json.loads ever ran. MEMORY.md's own
    prose is full of non-ASCII punctuation, so almost any real old_string
    trips this: current_text.count(old) drops to 0, simulate_edit() returns
    None, and the hook fails open. Reading the raw bytes and decoding them
    ourselves makes this independent of whatever codepage the parent
    process happened to inherit."""
    return sys.stdin.buffer.read().decode("utf-8")


def main():
    payload = json.loads(_read_stdin_text())
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    # Path extraction is the shared layer's job (tool_call_paths.primary_write_path):
    # it knows Desktop Commander's write_file uses "path" (not "file_path"), that
    # edit_block matches native Edit's field names, and keeps the legacy generic
    # fallback for any other tool name -- behavior-preserving by contract.
    file_path = primary_write_path(tool_name, tool_input)
    if file_path is None:
        return
    if not is_memory_index(file_path):
        return

    try:
        with open(target_index(), "r", encoding="utf-8") as fh:
            current_text = fh.read()
    except Exception:
        return  # can't read current content -- fail open

    simulated = simulate_edit(tool_name, tool_input, current_text)
    if simulated is None:
        return  # couldn't simulate this shape -- fail open

    probe = _load_probe()
    entry_re = probe.MEMORY_INDEX_ENTRY_RE
    maxlen = probe.MEMORY_INDEX_HOOK_MAXLEN

    # Only block hooks THIS edit introduces or worsens. Pre-existing over-length entries
    # are the daily probe's business -- denying an unrelated edit because the file was
    # already dirty would punish the wrong write and make the index un-editable until
    # someone ran a full consolidation first.
    before = {ln for ln, _, _ in over_length_hooks(current_text, entry_re, maxlen)}
    after = over_length_hooks(simulated, entry_re, maxlen)
    if len(after) <= len(before):
        return

    lines = "\n".join(
        "- line %d: %d chars (cap %d) -- starts \"%s...\"" % (ln, n, maxlen, prev)
        for ln, n, prev in after)
    reason = (
        "MEMORY.md index-hook cap: this edit would add an index entry whose hook "
        "description exceeds %d chars --\n%s\n"
        "memory-policy.md sec 3: the index holds ONE-LINE POINTERS, not content. Put the "
        "detail in the linked memory file and leave a short hook here. (Same rule "
        "doctrine-integrity-probe.py check 9 audits daily -- enforced now so it can't "
        "accumulate.)" % (maxlen, lines))
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
