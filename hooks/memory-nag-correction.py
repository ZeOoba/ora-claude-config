#!/usr/bin/env python3
"""Memory-index nag correction -- PostToolUse hook for Edit|Write|MultiEdit plus
Desktop Commander's write_file/edit_block (both mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ prefixes -- both live in this stack).

WHY THIS EXISTS (2026-08-03). The Claude Code harness itself prints, after any edit to
MEMORY.md that crosses some harness-internal threshold: "The memory index at MEMORY.md
is NN.NKB, approaching the 24.4KB read limit. Compact it to under 17.1KB now: keep one
line per entry, move detail into topic files, and merge or drop stale entries." 17.1KB
(17100 bytes) was this repo's OWN size-gate constant until Gabriel recalibrated it to
21.5KB (21500 bytes) on 2026-07-31 -- measured against the live corpus, stripping every
entry's descriptive hook down to bare links still only reached 15,183 bytes, so 17.1KB
demanded deleting ~30 live pointers (17% of all memories). See the calibration comment
above MEMORY_WARN_BYTES in maintenance/memory-integrity-probe.py and
memory/reference_memory_index_size_gate_is_a_runway_marker.md (the standing answer).

The harness's own nag is not ours to edit and will keep citing 17.1KB regardless. A
session that has not seen the runway-marker memory reads the nag as authoritative and
starts deleting live index pointers to satisfy an unsatisfiable number -- reproduced
directly 2026-08-03 (a session flagged the nag as broken, itself unaware a fix already
existed). This hook makes the correction automatic: every write to MEMORY.md that
crosses the REAL ratified threshold gets an immediate, model-visible follow-up naming
the actual numbers and pointing at the standing-answer memory, via
hookSpecificOutput.additionalContext -- NOT systemMessage, which is user-visible but
invisible to the model (reference_hook_systemmessage_not_model_visible.md; the same
defect class cost hooks/shared-checkout-guard.py 168 silent firings over 7 days before
it was found 2026-07-16). Warn-only, never blocks -- this hook runs strictly after the
write already landed.

Imports MEMORY_WARN_BYTES / MEMORY_HARD_BYTES from maintenance/memory-integrity-probe.py
(mirroring memory-index-guard.py's _load_probe() pattern) rather than hardcoding its own
copies, so the write-time correction and the audit-time gate cannot drift apart. Falls
back to hardcoded copies of the SAME two ratified numbers only if the probe cannot be
imported at all, so a missing/broken probe degrades to "still correct today" rather than
silence.

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error -- bad stdin,
missing field, unreadable file, an unimportable probe -- it prints nothing and exits 0.
A bug here must never block a tool call and must never crash the harness's own turn.

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

# Tool-call shape knowledge is SHARED via hooks/lib/tool_call_paths.py (2026-07-18) --
# see memory-index-guard.py's identical rationale. The fallback preserves the legacy
# generic file_path-or-path parsing, so a broken/missing lib degrades gracefully rather
# than opening a new hole.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
try:
    from tool_call_paths import is_write_capable, primary_write_path  # noqa: E402
except Exception:
    _FALLBACK_WRITE_TOOLS = frozenset((
        "Write", "Edit", "MultiEdit",
        "mcp__Desktop_Commander__write_file",
        "mcp__plugin_desktop-commander_desktop-commander__write_file",
        "mcp__Desktop_Commander__edit_block",
        "mcp__plugin_desktop-commander_desktop-commander__edit_block",
    ))

    def is_write_capable(tool_name):
        return tool_name in _FALLBACK_WRITE_TOOLS

    def primary_write_path(tool_name, tool_input):
        p = tool_input.get("file_path") or tool_input.get("path")
        return p if isinstance(p, str) and p else None

# Same two numbers as maintenance/memory-integrity-probe.py, kept here ONLY as a
# fail-safe if that module cannot be imported at all (see _load_probe below) -- the
# import path is the source of truth; these are not a second place to update.
_FALLBACK_WARN_BYTES = 21500
_FALLBACK_HARD_BYTES = 24400


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def target_index():
    return os.environ.get("ORA_MEMORY_INDEX") or DEFAULT_MEMORY_INDEX


def is_memory_index(file_path):
    return _norm(file_path) == _norm(target_index())


def _load_probe():
    probe_path = os.path.join(MAINTENANCE_DIR, "memory-integrity-probe.py")
    spec = importlib.util.spec_from_file_location("memory_integrity_probe", probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _thresholds():
    try:
        probe = _load_probe()
        return probe.MEMORY_WARN_BYTES, probe.MEMORY_HARD_BYTES
    except Exception:
        return _FALLBACK_WARN_BYTES, _FALLBACK_HARD_BYTES


def _read_stdin_text():
    # Decode raw bytes as UTF-8 ourselves -- never trust sys.stdin's own encoding.
    # Same rationale as memory-index-guard.py's _read_stdin_text(): a harness-spawned
    # process can resolve sys.stdin.encoding to cp1252 instead of UTF-8 (confirmed
    # live, reference_windows_hook_stdin_cp1252_encoding_gap.md).
    return sys.stdin.buffer.read().decode("utf-8")


def build_message(idx_bytes, warn_bytes, hard_bytes):
    if idx_bytes > hard_bytes:
        return (
            "MEMORY.md is %d bytes, past the %d-byte Read-tool HARD limit -- it no "
            "longer fits in one Read call. This is a genuine problem (not merely the "
            "harness's stale nag): archive dead entries with inbound-ref repair, or "
            "split the index. If a \"compact to under 17.1KB\" message appeared above, "
            "its 17.1KB figure is stale and unrelated to this real limit -- see "
            "memory/reference_memory_index_size_gate_is_a_runway_marker.md." % (
                idx_bytes, hard_bytes))
    return (
        "MEMORY.md is now %d bytes. If a \"compact to under 17.1KB\" nag appeared "
        "above, ignore the 17.1KB figure -- that is the Claude Code harness's own "
        "stale, internal number, not this repo's gate, and it is not editable here. "
        "The ratified thresholds (Gabriel, 2026-07-31) are WARN %d bytes (a runway "
        "marker, not a target) and HARD %d bytes (the real Read-tool limit -- do not "
        "raise it). Do NOT delete live index pointers to satisfy the harness's nag; "
        "the levers are archival-with-ref-repair or splitting the index. See "
        "memory/reference_memory_index_size_gate_is_a_runway_marker.md." % (
            idx_bytes, warn_bytes, hard_bytes))


def emit(ctx):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ctx,
        }
    }))


def main():
    payload = json.loads(_read_stdin_text())
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if not is_write_capable(tool_name):
        return  # e.g. a Read call that happens to carry a file_path field
    file_path = primary_write_path(tool_name, tool_input)
    if file_path is None:
        return
    if not is_memory_index(file_path):
        return

    idx_bytes = os.path.getsize(target_index())
    warn_bytes, hard_bytes = _thresholds()
    if idx_bytes <= warn_bytes:
        return  # nothing to correct -- genuinely under the real gate

    emit(build_message(idx_bytes, warn_bytes, hard_bytes))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a bug here must never block a tool call
    sys.exit(0)
