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
CLAUDE.md), so a bug in the test helper cannot corrupt anything live. Most assertions
derive their expected values from maintenance/memory-integrity-probe.py and the hook
itself (so the write-time correction, the audit-time gate, and this suite cannot drift
apart on ORDINARY changes) -- EXCEPT two deliberately hardcoded pin checks near the
top, which exist because a derived-only suite already proved unable to catch the one
failure mode that actually matters: the probe file itself holding the WRONG value.
2026-08-03 code review caught this live -- see the comment above those two checks.

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


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_probe = _load_module("memory_integrity_probe", PROBE)
_hook = _load_module("memory_nag_correction", HOOK)
WARN_BYTES = _probe.MEMORY_WARN_BYTES
HARD_BYTES = _probe.MEMORY_HARD_BYTES
FLOOR_BYTES = _hook.HARNESS_NAG_FLOOR_BYTES

failures = []


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label)


# PINNED, not derived: the whole point of these two lines is to catch drift the
# derived checks below structurally cannot. 2026-08-03 code review caught exactly
# this failure mode live -- the hook imported MEMORY_WARN_BYTES from a copy of the
# probe that still held the OLD, un-recalibrated 17100, and every assertion below
# (which reads its expected value from that SAME copy) passed green while the hook
# emitted a message naming 17100 as "the ratified threshold (Gabriel, 2026-07-31)".
# A test that derives its expectation from the thing it's testing cannot catch the
# thing it's testing having the wrong value baked in -- see
# feedback_fixture_shaped_tests_certify_dead_branches.md. These two lines are the
# ONLY assertions in this file that do not route through _probe/_hook.
check("probe still carries the ratified 2026-07-31 constants (21500 / 24400)",
      (WARN_BYTES, HARD_BYTES) == (21500, 24400))
check("hook's harness-nag floor is still the pre-recalibration 17100",
      FLOOR_BYTES == 17100)


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


# Effective fire threshold is the LOWER of WARN and the harness-nag floor -- since the
# floor (17100) sits below the recalibrated WARN (21500), the floor is what actually
# governs today. Assert that ordering explicitly so these tests fail loudly (not
# silently mis-target) if a future recalibration ever pushes WARN below the floor.
check("floor is currently the binding threshold (floor < WARN)", FLOOR_BYTES < WARN_BYTES)
EFFECTIVE_FLOOR = min(WARN_BYTES, FLOOR_BYTES)

# 1. Below the effective floor -> silent. Nothing to correct, and the harness's own
#    nag cannot plausibly have fired here either.
ctx, _ = run("Write", EFFECTIVE_FLOOR - 100)
check("size below the effective floor -> silent", ctx == "")

# 2. Exactly at the effective floor -> silent (strictly-greater, mirroring the probe).
ctx, _ = run("Write", EFFECTIVE_FLOOR)
check("size == floor exactly -> silent (strict >)", ctx == "")

# 3. Past the floor but still BELOW WARN -- this is the band the original design left
#    uncovered (2026-08-03 review finding #4): the harness's nag has been observed to
#    fire here (reference_memory_index_size_gate_is_a_runway_marker.md, 20,455 bytes),
#    below our post-recalibration WARN. Must now fire.
ctx, out = run("Write", FLOOR_BYTES + 200)
check("size past the floor but below WARN -> fires (closes the silent-band gap)",
      ctx != "")
check("floor-band message mentions the real WARN threshold", str(WARN_BYTES) in ctx)
check("floor-band message mentions the real HARD threshold", str(HARD_BYTES) in ctx)
check("floor-band message never re-states the stale 17100 as itself ratified",
      "17100" not in ctx)
check("floor-band message names the stale 17.1KB harness figure for context",
      "17.1" in ctx)

# 4. Just past WARN, still under HARD -> fires, names the real thresholds, and tells
#    the model to ignore the harness's 17.1KB figure.
ctx, out = run("Write", WARN_BYTES + 500)
check("size just past WARN -> fires", ctx != "")
check("mentions the real WARN threshold", str(WARN_BYTES) in ctx)
check("mentions the real HARD threshold", str(HARD_BYTES) in ctx)
check("explicitly names the stale 17.1KB harness figure", "17.1" in ctx)
check("message never states the stale 17100 byte figure as itself ratified",
      "17100" not in ctx)
check("explicitly instructs NOT to delete live pointers",
      "not delete" in ctx.lower() or "not to delete" in ctx.lower())
check("points at the standing-answer memory file",
      "reference_memory_index_size_gate_is_a_runway_marker" in ctx)
check("hookEventName is PostToolUse", '"hookEventName": "PostToolUse"' in out
      or '"hookEventName":"PostToolUse"' in out)
WARN_BAND_CTX = ctx  # reused below to prove the HARD-only token is HARD-exclusive

# 5. Past HARD -> still fires, but this is a REAL problem (Read-tool limit), not just
#    a nag to correct -- the message must say so distinctly and use a token the WARN
#    branch never uses (2026-08-03 review finding #3: the original assertion here was
#    satisfiable by EITHER branch and never actually distinguished them).
ctx, _ = run("Write", HARD_BYTES + 500)
check("size past HARD -> fires", ctx != "")
check("HARD-exceeded message names it a genuine problem", "genuine problem" in ctx)
check("WARN-band message does NOT claim the genuine-problem framing (branches differ)",
      "genuine problem" not in WARN_BAND_CTX)

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
