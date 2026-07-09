#!/usr/bin/env python3
"""Native git pre-push gate #1 for ~/.claude — DOCTRINE-DRIFT block (runs AHEAD of the
confidentiality scan).

WHY (audit finding 2026-07-08): doctrine drift (CLAUDE.md / rules / session-context
integrity) could reach the private remote unremarked. This gate runs
`maintenance/doctrine-integrity-probe.py` (no flags -- the probe has no --quiet option,
only --session-context=/--rules=/--terms=) and BLOCKS the push when the probe exits
non-zero (drift found), UNLESS a valid `allow-doctrine-drift` override sentinel is
present. It is INDEPENDENT of and does NOT modify the confidentiality scan — that
FAIL-CLOSED scan (git-prepush-confidential-scan.py) still runs after this one.

OVERRIDE (same family + 60-min window as ora-autonomy-gate.py's allow-external-send /
allow-website-change; protocol in memory/rules.md §10): sentinel file
  ~/.claude/hooks/overrides/allow-doctrine-drift
valid for 60 minutes from its mtime. Create it ONLY after Gabriel's explicit in-turn
confirmation; scheduled/headless sessions must NEVER self-create one — flag and stop.
Every use of the override to bypass a doctrine-drift block is LOGGED (newest-first) to
memory/event_log.md via maintenance/append-event-log.py.

FAIL-CLOSED on the probe: if the probe cannot be launched at all, that is treated as a
non-zero (drift) result — a probe we cannot run cannot prove doctrine is intact. This
gate reads NOTHING from stdin, so git's ref payload is preserved intact for the
confidentiality scan that the shim exec's after it.

Install (done 2026-07-08; re-do after any fresh clone — the .git/hooks/pre-push shim is
NOT version-controlled, this script and the confidentiality scan ARE. See
docs/MIGRATION_RUNBOOK.md). The shim must run BOTH tracked checks, doctrine gate first:
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (doctrine gate takes </dev/null so it never consumes git's ref stdin; the exec hands
   that stdin to the confidentiality scan unchanged.)

Exit 0 = allow push (no drift, or drift with a valid logged override).
Exit 1 = block (drift, no valid override) — git pre-push convention.
"""
import importlib.util
import os
import re
import subprocess
import sys
import time
from datetime import datetime

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOK_DIR)
OVERRIDE_DIR = os.path.join(HOOK_DIR, "overrides")
OVERRIDE_NAME = "allow-doctrine-drift"
OVERRIDE_TTL_SECONDS = 3600  # 60 min — same window as ora-autonomy-gate.py sentinels
PROBE_SCRIPT = os.path.join(CLAUDE_DIR, "maintenance", "doctrine-integrity-probe.py")
APPEND_LOG_SCRIPT = os.path.join(CLAUDE_DIR, "maintenance", "append-event-log.py")
# Layer-2 durable status file (audit Phase 3): the hyphenated sibling module is imported
# by path via importlib (the idiom in maintenance/_tests/test_hardening.py); plain
# `import` can't load a hyphenated module name.
STATUS_WRITER = os.path.join(CLAUDE_DIR, "maintenance", "_shared", "write-doctrine-status.py")
# Test seam only: when set (test monkeypatch), passed to append-event-log.py as --log so
# an override-logging test never writes to the canonical event_log.md. None -> canonical.
EVENT_LOG_OVERRIDE = None
# Test seam only (mirrors EVENT_LOG_OVERRIDE): when set, the status file is written here
# instead of the canonical maintenance/_state/doctrine-status.json. None -> canonical.
STATUS_PATH_OVERRIDE = None


def override_active(name=OVERRIDE_NAME):
    """True iff the named sentinel exists AND its mtime is < 60 min old. Mirrors
    ora-autonomy-gate.py.override_active exactly (existence alone is NOT enough)."""
    path = os.path.join(OVERRIDE_DIR, name)
    try:
        return (time.time() - os.path.getmtime(path)) < OVERRIDE_TTL_SECONDS
    except OSError:
        return False


def run_doctrine_probe():
    """Run the probe (it has no --quiet flag -- unlike governor-drift-probe.py, its only
    options are --session-context=/--rules=/--terms=; passing --quiet would itself be an
    unrecognized-option [MISSING] finding and always fail-closed-block every push).

    CAPTURE-then-echo (was: inherit) so the SAME diagnostics still surface live to the git
    user AND the text is available to derive a one-line status-file summary from -- without
    re-running the probe (a second run would double the cost and could race a mid-push
    CLAUDE.md edit). Returns (exit_code, stdout_text). A launch failure is reported as
    (1, "") -- fail-closed: a probe we cannot run cannot prove doctrine is intact.

    Decoded utf-8/errors=replace and echoed through the utf-8-reconfigured streams so the
    probe's box/arrow/em-dash glyphs neither corrupt the display nor raise on a cp1252
    console (same stream-reconfigure guard as maintenance/append-event-log.py)."""
    try:
        result = subprocess.run(
            [sys.executable, PROBE_SCRIPT],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        # Echo exactly what the user would have seen when the probe inherited the console.
        if result.stdout:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
        if result.stderr:
            sys.stderr.write(result.stderr)
            sys.stderr.flush()
        return result.returncode, (result.stdout or "")
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push doctrine gate: could not launch doctrine-integrity-probe.py "
            "(%s) - treating as drift (fail-closed).\n" % e)
        return 1, ""


def summarize_probe_output(probe_rc, probe_stdout):
    """Derive the one-line status-file summary from the probe's exit code + captured
    stdout. Pure. Mirrors eos-health-report.ps1's [WARN]-count idiom.
      rc != 0 -> the last '[MISSING]' line (the specific drift), else 'drift (exit N)'.
      rc == 0 -> 'clean', or 'clean, N warning(s)' when fail-open [WARN]s are present."""
    text = probe_stdout or ""
    if probe_rc != 0:
        missing = [ln.strip() for ln in text.splitlines() if "[MISSING]" in ln]
        if missing:
            return missing[-1]
        return "drift (exit %d)" % probe_rc
    warn_count = len(re.findall(r"\[WARN\]", text))
    if warn_count:
        return "clean, %d warning(s)" % warn_count
    return "clean"


def _load_status_writer():
    """Load the hyphenated sibling status-writer module by path (importlib idiom, per
    maintenance/_tests/test_hardening.py). Best-effort: return None if it can't be
    loaded so a missing/broken module never blocks a push."""
    try:
        spec = importlib.util.spec_from_file_location("write_doctrine_status", STATUS_WRITER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push doctrine gate: status-writer module unavailable (%s) - "
            "skipping status file (non-fatal).\n" % e)
        return None


def write_status_snapshot(probe_rc, probe_stdout):
    """Layer-2 of the audit's triple-redundant drift notification: overwrite
    maintenance/_state/doctrine-status.json with this run's snapshot. Called on BOTH the
    drift and no-drift paths -- every gate run leaves a fresh trace. Best-effort: never
    raises, never blocks a push (write_status itself already swallows write errors; the
    module load is guarded here). The pre-push gate runs ONLY the doctrine probe, so
    governor_* stay None."""
    mod = _load_status_writer()
    if mod is None:
        return
    try:
        mod.write_status(
            source="pre-push",
            doctrine_rc=probe_rc,
            doctrine_summary=summarize_probe_output(probe_rc, probe_stdout),
            path=STATUS_PATH_OVERRIDE,
        )
    except Exception as e:  # pragma: no cover - defensive; write_status already swallows
        sys.stderr.write(
            "pre-push doctrine gate: status snapshot skipped (%s) - non-fatal.\n" % e)


def decide(probe_rc, override_is_active):
    """Pure decision. Returns (exit_code, log_override).
      probe_rc == 0                 -> (0, False)  no drift: allow, nothing to log.
      probe_rc != 0 and override    -> (0, True)   drift but overridden: allow + LOG.
      probe_rc != 0 and no override -> (1, False)  drift, no override: BLOCK."""
    if probe_rc == 0:
        return 0, False
    if override_is_active:
        return 0, True
    return 1, False


def build_override_entry(now=None):
    """Newest-first event_log entry (must start '## ') recording an override use."""
    now = now or datetime.now()
    return (
        "## %s — Pre-push proceeded DESPITE doctrine drift (allow-doctrine-drift override used)\n\n"
        "- The `~/.claude` git pre-push doctrine gate (`hooks/git-prepush-doctrine-gate.py`) ran "
        "`doctrine-integrity-probe.py`, which reported drift (non-zero exit), but a valid "
        "`allow-doctrine-drift` override sentinel (< 60 min from mtime) was present, so the push was "
        "ALLOWED rather than blocked.\n"
        "- Mechanical record only, per the rules.md §10 override protocol (sentinel created only after "
        "Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override "
        "consumed at %s local.\n"
        % (now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))
    )


def log_override_use():
    """Append the override-use record to event_log.md via the canonical, collision-safe
    appender. Best-effort: a logging failure must not itself block a push Gabriel has
    already authorized to proceed."""
    entry = build_override_entry()
    cmd = [sys.executable, APPEND_LOG_SCRIPT]
    if EVENT_LOG_OVERRIDE:
        cmd += ["--log", EVENT_LOG_OVERRIDE]
    try:
        subprocess.run(cmd, input=entry.encode("utf-8"), capture_output=True)
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push doctrine gate: override used but event_log append FAILED (%s) - "
            "record it manually.\n" % e)


def main():
    # Reconfigure std streams to utf-8 so echoing the probe's box/arrow/em-dash glyphs
    # never raises on a cp1252 console (same guard as maintenance/append-event-log.py).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    probe_result = run_doctrine_probe()
    # run_doctrine_probe now returns (exit_code, stdout_text). BACKWARD-COMPAT: the
    # pre-existing gate test (hooks/tests/test-git-prepush-doctrine-gate.py) stubs
    # run_doctrine_probe to the legacy bare-int contract (`lambda: 1`); normalize so that
    # still unpacks, and treat only a real (tuple) probe run as a "gate run" for the
    # status snapshot -- a stubbed unit test must NOT clobber the real _state snapshot
    # with a fake drift result (it does not redirect STATUS_PATH_OVERRIDE).
    real_run = isinstance(probe_result, tuple)
    probe_rc, probe_stdout = probe_result if real_run else (probe_result, "")
    exit_code, log_override = decide(probe_rc, override_active())
    # Layer-2 durable trace on every REAL gate run (both the drift AND no-drift paths).
    # Best-effort: a status-file failure never changes the gate's decision or exit code.
    if real_run:
        write_status_snapshot(probe_rc, probe_stdout)
    if log_override:
        log_override_use()
        sys.stderr.write(
            "pre-push: doctrine drift present but OVERRIDDEN - a valid allow-doctrine-drift "
            "sentinel (< 60 min) was found. Push ALLOWED; the override was logged to "
            "event_log.md.\n")
    elif exit_code != 0:
        sys.stderr.write(
            "pre-push BLOCKED: doctrine-integrity-probe.py reported drift. Fix the "
            "drift first. If Gabriel has just explicitly authorized pushing anyway, create the "
            "override sentinel (valid 60 min) and retry:\n  %s\n"
            % os.path.join(OVERRIDE_DIR, OVERRIDE_NAME))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
