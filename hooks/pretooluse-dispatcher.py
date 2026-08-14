#!/usr/bin/env python3
"""Run the PreToolUse Edit/Write guard chain in ONE process instead of nine.

WHY (measured 2026-08-05, isolated worktree): the nine PreToolUse guards cost
1,307 ms per single Edit/Write call, of which 585 ms (45%) is pure CPython
interpreter startup -- 9 x 65 ms paid before any guard runs a line of logic.
Dispatching in-process pays that startup once.

WHAT THIS DELIBERATELY DOES *NOT* CHANGE
----------------------------------------
No guard's logic, order, exit codes, or messages change. This file is pure
plumbing. Each guard is still the single source of truth for its own decision.

THE SAFETY PROPERTY THAT MATTERS
--------------------------------
Nine independent processes fail INDEPENDENTLY: a crash in one leaves the other
eight enforcing. One dispatcher process fails TOGETHER -- a bug here could
silently vaporize the entire PreToolUse guard layer, which is strictly worse
than the latency it saves. That is unacceptable for security-gate code, so:

  * Every guard is attempted IN-PROCESS, individually wrapped.
  * If a guard cannot be loaded or raises anything other than SystemExit, that
    ONE guard is re-run as a SUBPROCESS -- exactly today's behavior -- and its
    real exit code is honored. Degradation is per-guard and costs only latency.
  * A guard that fails BOTH paths is reported on stderr and treated as
    fail-open, matching what every one of these guards already does on
    malformed input (verified: all return 0, never 1, on garbage stdin).
  * The first guard to return 2 wins and short-circuits, preserving the
    settings.json ordering semantics exactly.

GUARD_CHAIN ORDER IS LOAD-BEARING and mirrors settings.json's PreToolUse block.
Reordering changes which block message the user sees first. Keep them in sync;
`--selfcheck` asserts every listed guard file exists.

=============================================================================
WIRED INTO settings.json 2026-08-05 (Gabriel-approved) -- THE MATCHER PARTITION
=============================================================================
Validated before wiring: 18/18 decision-equivalent with the real 9-process
chain; 85% faster on the common all-nine-run path (490ms -> 73ms).
Validated after wiring: 19/19 tools have IDENTICAL guard coverage vs the
pre-wire config (Edit/Write/MultiEdit/NotebookEdit/Bash + 10 MCP write tools +
read-only controls). Pre-wire backup of settings.json was taken first.

THE TRAP THIS PARTITION EXISTS TO AVOID: the nine guards do NOT share a matcher.
All nine DO fire on Edit|Write|MultiEdit (so the dispatcher is exactly right for
those three), but five ALSO fire on Bash, NotebookEdit, and assorted MCP write
tools -- where a different, SMALLER subset belongs. A naive one-entry-for-nine
swap would silently (a) stop running autonomy/confidentiality/config-write on
Bash, and (b) start running all nine on NotebookEdit, where only three belong.
Both are security regressions, and neither would announce itself.

So each matcher had ONLY Edit|Write|MultiEdit removed:

  ADDED   pretooluse-dispatcher    Edit|Write|MultiEdit          (runs all nine)
  NARROWED ora-autonomy-gate    -> Bash|NotebookEdit|mcp__.*netlify.*-updater
  NARROWED confidentiality-guard-> NotebookEdit|Bash|mcp__.*notion-(...)|
                                   mcp__.*OUTLOOK_(...)
  NARROWED config-write-guard   -> NotebookEdit|Bash|mcp__excel__.*|mcp__.*(...)
  NARROWED registry-write-guard -> Desktop-Commander write_file/edit_block only
  NARROWED memory-index-guard   -> Desktop-Commander write_file/edit_block only
  DELETED  eos-plan-gate, shared-checkout-guard, eos-claude-md-guard,
           rules-md-guard  (matcher was EXACTLY Edit|Write|MultiEdit, so the
                            dispatcher fully subsumes them)

IF YOU ADD A GUARD to the Edit/Write path, add it to GUARD_CHAIN here -- NOT as
a new settings.json PreToolUse entry -- or it will run twice on Edit/Write.
Conversely a guard needing Bash/NotebookEdit/MCP coverage still needs its own
settings.json entry; this dispatcher only ever handles Edit|Write|MultiEdit.
"""
import io
import importlib.util
import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))

# settings.json PreToolUse order for the Edit|Write|MultiEdit matchers.
# (The inline bash sensitive-file-blocker stays inline in settings.json -- it is
# not a python module and is not dispatched here.)
GUARD_CHAIN = [
    "ora-autonomy-gate",
    "confidentiality-guard",
    "eos-plan-gate",
    "shared-checkout-guard",
    "registry-write-guard",
    "config-write-guard",
    "eos-claude-md-guard",
    "memory-index-guard",
    "rules-md-guard",
    "lint-config-guard",  # OI-148, 2026-08-13 -- Edit/Write/MultiEdit into an
    # existing oxford-command-center lint/format/typecheck config
]


class _StdinShim:
    """Feed each guard the same payload. Guards read EITHER sys.stdin.read()
    (text) or sys.stdin.buffer.read() (bytes -- the 2026-07-17 Windows cp1252
    fix), so both must work, and each must be independently re-readable across
    guards."""

    def __init__(self, raw: bytes):
        self._raw = raw
        self.buffer = io.BytesIO(raw)
        self._text = io.StringIO(raw.decode("utf-8", errors="replace"))

    def read(self, *a):
        return self._text.read(*a)

    def readline(self, *a):
        return self._text.readline(*a)

    def __iter__(self):
        return iter(self._text)

    def isatty(self):
        return False


def _load(name):
    """Import a hyphenated guard script as a module WITHOUT executing its
    main() (every guard is `if __name__ == "__main__": main()`-guarded, and we
    import under a different name, so top-level import is side-effect-only)."""
    path = os.path.join(HOOKS_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location("_guard_" + name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError("no spec for " + path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_subprocess(name, raw):
    """Today's behavior, for one guard. Used whenever in-process dispatch is not
    provably safe for that guard."""
    path = os.path.join(HOOKS_DIR, name + ".py")
    r = subprocess.run([sys.executable, path], input=raw,
                       capture_output=True, timeout=60)
    return r.returncode, r.stdout.decode("utf-8", "replace"), \
        r.stderr.decode("utf-8", "replace")


def _run_inprocess(name, raw):
    """(rc, stdout, stderr) or None if this guard must fall back to a subprocess."""
    mod = _load(name)
    main = getattr(mod, "main", None)
    if not callable(main):
        return None
    real_in, real_out, real_err = sys.stdin, sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    rc = 0
    try:
        sys.stdin, sys.stdout, sys.stderr = _StdinShim(raw), out, err
        try:
            main()
        except SystemExit as e:
            code = e.code
            rc = 0 if code is None else (code if isinstance(code, int) else 1)
    finally:
        sys.stdin, sys.stdout, sys.stderr = real_in, real_out, real_err
    return rc, out.getvalue(), err.getvalue()


def guard_path(name):
    return os.path.join(HOOKS_DIR, name + ".py")


def run_guard(name, raw):
    """(rc, stdout, stderr, mode). Never raises.

    NOTE the missing-file case is handled by the caller, NOT here: a absent
    guard script makes the CPython launcher itself exit 2, which is
    indistinguishable from a guard deliberately deciding to BLOCK. Relaying that
    as a block would mean a single typo in GUARD_CHAIN silently bricks every
    Edit/Write on the machine with an unexplained denial."""
    try:
        result = _run_inprocess(name, raw)
        if result is not None:
            return result + ("inprocess",)
    except Exception as e:  # noqa: BLE001 -- any in-process failure degrades, never escapes
        print("dispatcher: %s in-process failed (%s: %s); using subprocess"
              % (name, type(e).__name__, e), file=sys.stderr)
    try:
        return _run_subprocess(name, raw) + ("subprocess",)
    except Exception as e:  # noqa: BLE001
        print("dispatcher: %s FAILED BOTH PATHS (%s: %s) -- guard did not run, "
              "failing open" % (name, type(e).__name__, e), file=sys.stderr)
        return 0, "", "", "failed"


def main():
    try:
        raw = sys.stdin.buffer.read()
    except Exception:
        return 0

    # NO pre-parse / early-out on malformed input. An earlier revision of this
    # dispatcher short-circuited to 0 when the payload would not json.loads(),
    # on the stated assumption that "every guard fails open on garbage stdin."
    # THE EQUIVALENCE HARNESS DISPROVED THAT (2026-08-05): on raw non-JSON,
    # the real chain returns 2 because confidentiality-guard.py fails CLOSED by
    # design -- invariant 3, confidential-leak protection is deliberately not
    # fail-open (see feedback_confidentiality_guard_selfdeadlock.md). The
    # short-circuit silently weakened that. Malformed input is now passed
    # straight through to the guards so each applies its OWN policy; the
    # dispatcher makes no allow/block decision of its own, ever.
    # A guard script that is missing entirely is a CONFIGURATION EMERGENCY, not
    # a decision: the security layer is not what it claims to be. Fail closed
    # with an explicit, actionable message rather than either (a) silently
    # dropping that guard's protection, or (b) relaying the launcher's own
    # exit-2 as if some guard had deliberately blocked.
    missing = [n for n in GUARD_CHAIN if not os.path.isfile(guard_path(n))]
    if missing:
        print("BLOCKED (pretooluse-dispatcher): guard script(s) missing from %s: %s\n"
              "The PreToolUse security layer is incomplete, so this write is refused.\n"
              "Restore the file(s) or correct GUARD_CHAIN, then re-run "
              "`python hooks/pretooluse-dispatcher.py --selfcheck`."
              % (HOOKS_DIR, ", ".join(missing)), file=sys.stderr)
        return 2

    stdouts = []
    for name in GUARD_CHAIN:
        rc, out, err, _mode = run_guard(name, raw)
        if out and out.strip():
            stdouts.append(out)
        if err:
            sys.stderr.write(err)
        if rc == 2:
            # A blocking guard's own stdout is the only one that still matters.
            sys.stdout.write(out if (out and out.strip()) else "")
            return 2
    emit_stdout(stdouts)
    return 0


def emit_stdout(chunks):
    """Emit ONE valid JSON object for the harness, or nothing.

    Guards talk to the harness through structured JSON on stdout -- notably
    `systemMessage` (user-visible) and `hookSpecificOutput.additionalContext`
    (the only PreToolUse field that is both model-visible and non-blocking; see
    shared-checkout-guard.py's DELIVERY note, and
    reference_hook_systemmessage_not_model_visible.md for the 7-day outage that
    established it).

    Naively concatenating two guards' JSON objects yields `{...}{...}`, which
    parses as NOTHING -- silently losing BOTH messages. Today only one guard in
    the chain emits, so this never fires; it exists so that adding a second
    emitter to GUARD_CHAIN does not silently break delivery."""
    if not chunks:
        return
    if len(chunks) == 1:
        sys.stdout.write(chunks[0])
        return
    msgs, ctxs, merged = [], [], {}
    for c in chunks:
        try:
            obj = json.loads(c)
        except (ValueError, TypeError):
            continue  # non-JSON chatter is not a delivery channel; drop it
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if k == "systemMessage":
                if v:
                    msgs.append(str(v))
            elif k == "hookSpecificOutput" and isinstance(v, dict):
                hso = merged.setdefault("hookSpecificOutput", {})
                for hk, hv in v.items():
                    if hk == "additionalContext":
                        if hv:
                            ctxs.append(str(hv))
                    else:
                        hso.setdefault(hk, hv)
            else:
                merged.setdefault(k, v)
    if msgs:
        merged["systemMessage"] = "\n\n".join(msgs)
    if ctxs:
        merged.setdefault("hookSpecificOutput", {})["additionalContext"] = \
            "\n\n".join(ctxs)
    if merged:
        sys.stdout.write(json.dumps(merged))


def selfcheck():
    missing = [n for n in GUARD_CHAIN
               if not os.path.isfile(os.path.join(HOOKS_DIR, n + ".py"))]
    if missing:
        print("MISSING guard files: %s" % ", ".join(missing))
        return 1
    print("selfcheck OK -- %d guards present, chain order:" % len(GUARD_CHAIN))
    for i, n in enumerate(GUARD_CHAIN, 1):
        print("  %d. %s" % (i, n))
    return 0


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    sys.exit(main())
