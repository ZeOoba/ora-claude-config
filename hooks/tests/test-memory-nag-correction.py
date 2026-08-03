#!/usr/bin/env python3
"""Tests for memory-nag-correction.py (PostToolUse, added 2026-08-03).

WHY THIS HOOK EXISTS: the Claude Code harness itself prints "The memory index at
MEMORY.md is NN.NKB, approaching the 24.4KB read limit. Compact it to under 17.1KB
now" after any edit to MEMORY.md once it grows past some harness-internal threshold.
17.1KB was this repo's OWN size-gate constant until Gabriel recalibrated it to 21.5KB
on 2026-07-31 (see maintenance/memory-integrity-probe.py's calibration comment and
memory/reference_memory_index_size_gate_is_a_runway_marker.md) -- but the harness's
own nag is not ours to edit and keeps citing the old, unsatisfiable 17.1KB figure. A
session that has not seen that memory file will read the nag as authoritative and
start deleting live index pointers to satisfy it. This hook corrects that in the
model's own context (additionalContext, not systemMessage -- see
reference_hook_systemmessage_not_model_visible.md) on every write to MEMORY.md that
crosses the REAL, ratified threshold.

Drives the real hook as a subprocess with real PostToolUse payloads against a temp
MEMORY.md (via ORA_MEMORY_INDEX), so the live index is never touched -- and every
"other file" case in this suite ALSO stays inside a tempdir (never a real path like
CLAUDE.md), so a bug in the test helper cannot corrupt anything live. It imports
MEMORY_WARN_BYTES/MEMORY_HARD_BYTES from maintenance/memory-integrity-probe.py rather
than hardcoding its own copies, so the two cannot drift apart -- tests therefore read
those constants directly rather than hardcoding 21500/24400 either.

fires  == stdout carries a non-empty hookSpecificOutput.additionalContext
silent == empty stdout (the hook stays silent)

Stdlib only; Windows (`python`).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "memory-nag-correction.py"))
PROBE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "maintenance",
    "memory-integrity-probe.py"))


def _load_probe():
    spec = importlib.util.spec_from_file_location("memory_integrity_probe", PROBE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_probe = _load_probe()
WARN_BYTES = _probe.MEMORY_WARN_BYTES
HARD_BYTES = _probe.MEMORY_HARD_BYTES

failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


def _write_padded(path, nbytes):
    """Write exactly `nbytes` bytes to `path` (ASCII filler -- byte count is what
    matters, not content)."""
    if nbytes <= 0:
        open(path, "wb").close()
        return
    open(path, "wb").write(b"x" * nbytes)


def run(tool_name, index_bytes):
    """The common case: a real MEMORY.md-equivalent file, padded to `index_bytes`,
    written and pointed at by both tool_input.file_path and ORA_MEMORY_INDEX. Always
    inside a fresh tempdir -- never a real path. Returns (additional_context, raw_stdout).

    Tests that need a MISMATCHED file_path/ORA_MEMORY_INDEX (the "wrote some other
    file" cases) build their own tempdir + subprocess call inline instead of forcing
    that shape through this helper's parameter list."""
    with tempfile.TemporaryDirectory() as d:
        idx = os.path.join(d, "MEMORY.md")
        _write_padded(idx, index_bytes)
        payload = {"tool_name": tool_name, "tool_input": {"file_path": idx}}
        env = dict(os.environ, ORA_MEMORY_INDEX=idx)
        r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                           capture_output=True, text=True, env=env)
        out = (r.stdout or "").strip()
        if not out:
            return "", out
        try:
            data = json.loads(out)
        except ValueError:
            return "", out
        hso = data.get("hookSpecificOutput", {})
        return hso.get("additionalContext", ""), out


# 1. Below WARN -> silent. Nothing to correct.
ctx, _ = run("Write", WARN_BYTES - 100)
check("size below WARN -> silent", ctx == "")

# 2. Exactly at WARN -> silent (probe's own gate is strictly-greater, mirror it).
ctx, _ = run("Write", WARN_BYTES)
check("size == WARN exactly -> silent (probe uses strict >)", ctx == "")

# 3. Just past WARN, still under HARD -> fires, names the real thresholds, and tells
#    the model to ignore the harness's 17.1KB figure.
ctx, out = run("Write", WARN_BYTES + 500)
check("size just past WARN -> fires", ctx != "")
check("mentions the real WARN threshold", str(WARN_BYTES) in ctx)
check("mentions the real HARD threshold", str(HARD_BYTES) in ctx)
check("explicitly names the stale 17.1KB harness figure", "17.1" in ctx)
check("tells the model not to delete live pointers",
      "delete" in ctx.lower() or "drop" in ctx.lower())
check("points at the standing-answer memory file",
      "reference_memory_index_size_gate_is_a_runway_marker" in ctx)
check("hookEventName is PostToolUse", '"hookEventName": "PostToolUse"' in out
      or '"hookEventName":"PostToolUse"' in out)

# 4. Past HARD -> still fires, but this is a REAL problem (Read-tool limit), not just
#    a nag to correct -- the message must say so distinctly.
ctx, _ = run("Write", HARD_BYTES + 500)
check("size past HARD -> fires", ctx != "")
check("HARD-exceeded message reads as a real problem, not just nag correction",
      "read" in ctx.lower() and ("limit" in ctx.lower() or "fit" in ctx.lower()))

# 5. A write to some OTHER file entirely (still inside the tempdir, never a real path)
#    -> silent, regardless of the REAL index's size sitting well past HARD.
with tempfile.TemporaryDirectory() as _d:
    _idx = os.path.join(_d, "MEMORY.md")
    _other = os.path.join(_d, "not-the-index.md")
    _write_padded(_idx, HARD_BYTES + 500)
    _write_padded(_other, 10)
    _payload = {"tool_name": "Write", "tool_input": {"file_path": _other}}
    _env = dict(os.environ, ORA_MEMORY_INDEX=_idx)
    _r = subprocess.run([sys.executable, HOOK], input=json.dumps(_payload),
                        capture_output=True, text=True, env=_env)
    _out = (_r.stdout or "").strip()
    check("write to a non-index file -> silent even though the real index is oversized",
          _out == "")

# 6. Desktop Commander write_file shape ("path", not "file_path") is recognized too --
#    same normalization layer as memory-index-guard.py.
with tempfile.TemporaryDirectory() as _d:
    _idx = os.path.join(_d, "MEMORY.md")
    _write_padded(_idx, WARN_BYTES + 500)
    _payload = {"tool_name": "mcp__Desktop_Commander__write_file",
                "tool_input": {"path": _idx, "content": "irrelevant"}}
    _env = dict(os.environ, ORA_MEMORY_INDEX=_idx)
    _r = subprocess.run([sys.executable, HOOK], input=json.dumps(_payload),
                        capture_output=True, text=True, env=_env)
    _out = (_r.stdout or "").strip()
    check("DC write_file ('path' field) recognized -> fires", _out != "")

# 7. Malformed stdin -> fail open silently, exit 0.
r = subprocess.run([sys.executable, HOOK], input="not json {{{",
                   capture_output=True, text=True)
check("malformed stdin -> silent", (r.stdout or "").strip() == "")
check("malformed stdin -> exit 0 (fail open, never blocks)", r.returncode == 0)

# 8. Empty stdin -> fail open silently, exit 0.
r = subprocess.run([sys.executable, HOOK], input="",
                   capture_output=True, text=True)
check("empty stdin -> silent", (r.stdout or "").strip() == "")
check("empty stdin -> exit 0", r.returncode == 0)

# 9. A read-only tool name (never write-capable) targeting the index path by
#    coincidence -> silent, since primary_write_path only resolves write-capable shapes.
with tempfile.TemporaryDirectory() as _d:
    _idx = os.path.join(_d, "MEMORY.md")
    _write_padded(_idx, WARN_BYTES + 500)
    _payload = {"tool_name": "Read", "tool_input": {"file_path": _idx}}
    _env = dict(os.environ, ORA_MEMORY_INDEX=_idx)
    _r = subprocess.run([sys.executable, HOOK], input=json.dumps(_payload),
                        capture_output=True, text=True, env=_env)
    _out = (_r.stdout or "").strip()
    check("Read tool call -> silent (not write-capable)", _out == "")

print()
if failures:
    print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
    sys.exit(1)
print("ALL PASS - memory-nag-correction fires only on real MEMORY.md writes past the "
      "ratified thresholds, and always names the real numbers, never the harness's "
      "stale 17.1KB figure")
sys.exit(0)
