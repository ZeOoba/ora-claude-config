#!/usr/bin/env python3
"""Native git pre-push gate #1 for ~/.claude — DOCTRINE-DRIFT block (runs AHEAD of the
confidentiality scan).

WHY (audit finding 2026-07-08): doctrine drift (CLAUDE.md / rules / session-context
integrity) could reach the private remote unremarked. This gate runs
`maintenance/doctrine-integrity-probe.py` against a scratch worktree of the commit about
to be pushed (see materialize_pushed_commit(), OI-100 below) and BLOCKS the push when the
probe exits non-zero (drift found), UNLESS a valid `allow-doctrine-drift` override
sentinel is present. It is INDEPENDENT of and does NOT modify the confidentiality scan —
that FAIL-CLOSED scan (git-prepush-confidential-scan.py) still runs after this one.

RESCOPE (OI-100, 2026-08-05, Gabriel-approved): prior to this, run_doctrine_probe() ran
the probe with NO arguments, which validates the WORKING TREE, not the commit(s) being
pushed -- a false-negative hole (commit drift, revert it uncommitted, push: the gate saw
a clean working tree and allowed a drifted commit through). The fix materializes HEAD via
`git worktree add --detach` into a scratch dir and passes it to the probe as
`--live-root=<scratch dir>` -- a NEW flag that redirects the probe's git-TRACKED-content
paths (CLAUDE.md, commands/, agents/, workflows/, skills/, memory/, settings.json,
scheduled-tasks/, hooks/pretooluse-dispatcher.py) at that root WITHOUT setting
live_mode=False the way the probe's pre-existing positional-path/--session-context=/
--rules=/--terms= overrides do (that flag flip silently disables 7 coupled checks --
see doctrine-integrity-probe.py's LIVE_CLAUDE_DIR comment). Paths with no meaningful
"as of this commit" version (session-context.md, confidential-terms.json -- both
gitignored; the pre-push shim itself -- not version-controlled) stay pinned to the real
live ~/.claude. KNOWN, ACCEPTED LIMITATION: this validates HEAD, not literally whatever
ref/sha git names on pre-push's stdin (this gate still reads no stdin -- see below) --
correct for ORA's actual workflow (push your current branch at its tip); pushing an
explicit refspec for a DIFFERENT, non-checked-out ref is not covered.

OVERRIDE (hardened 2026-07-16; shared contract in hooks/lib/override_tokens.py, which
carries the full rationale; protocol in memory/rules.md §10). A token lives at
  ~/.claude/hooks/sessions/<session_id>/overrides/allow-doctrine-drift
valid 60 minutes from its mtime, and its content must declare `scope: doctrine-drift` and a
`session:` matching the pushing session. Create it ONLY after Gabriel's explicit in-turn
confirmation; scheduled/headless sessions must NEVER self-create one — flag and stop. Every
use of the override to bypass a doctrine-drift block is LOGGED (newest-first) to
memory/event_log.md via maintenance/append-event-log.py.

The RETIRED flat `hooks/overrides/allow-doctrine-drift` sentinel is no longer consulted at
all. It was content-blind (any bytes, or none, granted the bypass), global across every
concurrent session, and — fatally — mintable by git: a tracked token is materialized by a
clone/checkout at age ~0, and mtime alone was the whole check. `hooks/sessions/` is
gitignored, so a token there cannot be committed. See override_tokens.py.

SESSION IDENTITY: unlike a PreToolUse hook, a git hook gets no payload, so the session is
read from CLAUDE_CODE_SESSION_ID in the environment. A push from a bare terminal carries no
such variable and therefore CANNOT be overridden — it must fix the drift instead. That is
deliberate and fail-closed: the override exists for a live session in which Gabriel has just
said yes, and a bare terminal cannot evidence that.

FAIL-CLOSED on the probe: if the probe cannot be launched at all, that is treated as a
non-zero (drift) result — a probe we cannot run cannot prove doctrine is intact. This
gate reads NOTHING from stdin, so git's ref payload is preserved intact for the
confidentiality scan that the shim exec's after it.

Install (done 2026-07-08, extended 2026-07-24; re-do after any fresh clone — the
.git/hooks/pre-push shim is NOT version-controlled, this script and its siblings ARE.
See docs/MIGRATION_RUNBOOK.md). The shim must run THREE tracked checks in order —
this doctrine gate first, then the hook-test-suite gate, then the confidentiality scan:
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (this gate and the hook-test gate both take </dev/null so neither consumes git's ref
   stdin; the final exec hands that stdin to the confidentiality scan unchanged.)

Exit 0 = allow push (no drift, or drift with a valid logged override).
Exit 1 = block (drift, no valid override) — git pre-push convention.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOK_DIR)
LIB_DIR = os.path.join(HOOK_DIR, "lib")
sys.path.insert(0, LIB_DIR)
# NO fallback on this import, deliberately — unlike ora-autonomy-gate.py's SITE_PATH_MARKERS
# (whose gate is fail-open-on-malfunction by design), a missing override_tokens module here
# must NOT degrade to some looser local check. It raises, the pre-push hook exits non-zero,
# and the push is blocked. A validator we cannot load cannot validate an override.
from override_tokens import Tier, token_grants, describe_token  # noqa: E402

# Scrubbed from every git subprocess this module spawns (worktree add/remove): git
# exports these to hook subprocesses, and an inherited GIT_DIR/GIT_WORK_TREE would
# silently redirect `git worktree add` at whatever repo/tree those name instead of
# the `cwd=` this module passes -- same hazard, same fix, as hooks/lib/isolated_commit.py.
_GIT_ENV_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_PREFIX")


def _clean_git_env():
    env = dict(os.environ)
    for v in _GIT_ENV_VARS:
        env.pop(v, None)
    return env

# One name, one tier. 60 min, multi-use: unchanged from the retired flat sentinel, so this
# hardening changes WHO a token authorizes and WHETHER its content is load-bearing — not how
# long a push stays authorized. (Single-use was considered and rejected for now: this gate
# runs BEFORE the confidentiality scan, so consuming the token here would burn it whenever
# that later scan blocks, forcing a re-mint to retry a push Gabriel already approved.)
DOCTRINE_DRIFT = Tier("allow-doctrine-drift", "doctrine-drift", 3600, single_use=False)
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
# Test seam only (mirrors EVENT_LOG_OVERRIDE): the repo `git worktree add`/`remove`
# operate against. None -> CLAUDE_DIR (the real, live checkout this gate ships in).
# A test points this at a throwaway repo so it never touches the real ~/.claude repo's
# worktree registry.
REPO_ROOT_OVERRIDE = None
# Test seam only (mirrors EVENT_LOG_OVERRIDE): the probe script actually invoked.
# None -> PROBE_SCRIPT (the real doctrine-integrity-probe.py in this checkout). A test
# combining this with REPO_ROOT_OVERRIDE can run the REAL run_doctrine_probe() end to
# end against a throwaway repo carrying its own copy of the probe script, with no risk
# to the real ~/.claude repo -- see hooks/tests/test-git-prepush-doctrine-gate-worktree.py.
PROBE_SCRIPT_OVERRIDE = None


def current_session_id():
    """The session this push is running under, or None. A git hook receives no payload, so
    the environment is the only channel. Absent -> no override is possible (fail closed)."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or None


def override_token(session_id):
    """The validated allow-doctrine-drift token's fields for `session_id`, or None: it must
    sit at the session-scoped path, be fresh within the TTL, be non-empty, declare
    `scope: doctrine-drift`, and carry a `session:` matching `session_id`. Delegates to the
    shared contract so this gate and ora-autonomy-gate.py cannot drift apart."""
    return token_grants(session_id, DOCTRINE_DRIFT)


def override_active(session_id):
    """Bool form of override_token(), for the pure decision table. Every failure mode is
    False -- there is no path on which an unreadable or ambiguous token grants anything."""
    return override_token(session_id) is not None


def materialize_pushed_commit(repo_root=None):
    """git-worktree-checkout HEAD of `repo_root` into a fresh scratch dir, so the probe
    can validate the COMMIT about to be pushed instead of the working tree (OI-100: the
    prior no-args invocation validated the working tree, so commit-then-uncommitted-fix
    left drift that reached the remote unremarked while the gate reported clean).

    Returns (worktree_path, error): worktree_path is None on any failure, with `error`
    describing why -- the caller treats a None here as fail-closed drift, matching this
    module's existing "a probe we cannot run cannot prove doctrine is intact" posture.

    HEAD, NOT the ref/sha git supplies on pre-push's stdin: this gate deliberately reads
    NO stdin (module docstring) so that payload reaches the confidentiality scan after it
    untouched. HEAD is the commit about to be pushed in the overwhelming common case here
    (push your current branch at its current tip). KNOWN, ACCEPTED LIMITATIONS (OI-100
    design direction, 2026-08-05; independent review + adversarial REFUTE, 2026-08-05):
      * Validates HEAD, not literally whatever ref(s) git names on stdin -- covers a plain
        `git push`/`push origin <current-branch>`, but NOT an explicit refspec for a
        different (non-checked-out) ref, `git push --all`/`--mirror`, a
        `push.default=matching` multi-branch push, or a tag push -- none of those are
        "pushing my current branch," and none is validated here. The tradeoff was made to
        keep the no-stdin contract rather than re-architect stdin sharing across all three
        gates in the same change.
      * Validates the TIP only, not the whole pushed commit range -- drift introduced and
        then fixed in an earlier commit of the same push is not flagged by this gate (gate
        #3, the confidentiality scan, reads the full pushed range separately and remains
        the backstop for that history-egress case).
      * Check 8's untracked-root-*.md leak-scan leg (doctrine-integrity-probe.py) is
        structurally inert here: a fresh worktree has no untracked files, so a confidential
        term sitting only in an untracked root *.md no longer trips this gate the way the
        pre-fix working-tree read did. Accepted: an untracked file cannot itself reach the
        remote (the push carries no such content), so this is a lost hygiene tripwire, not
        lost egress control -- the scheduled live probe runs still cover it."""
    repo_root = repo_root or REPO_ROOT_OVERRIDE or CLAUDE_DIR
    worktree_path = tempfile.mkdtemp(prefix="ora-doctrine-push-")
    try:
        # `git worktree add` refuses a non-empty target, and on some git versions an
        # already-EXISTING-but-empty one too -- remove the mkdtemp()-created dir and
        # let git create the leaf itself, same idiom as isolated_commit.py's scratch dirs.
        os.rmdir(worktree_path)
    except OSError as e:
        return None, "could not prepare worktree scratch dir (%s)" % e
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", "--quiet", worktree_path, "HEAD"],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_git_env())
    except Exception as e:  # pragma: no cover - defensive
        # mkdtemp's dir was already rmdir'd above (empty), so there is nothing left on
        # disk to clean up on this specific path -- git never got far enough to create one.
        return None, "could not launch git worktree add (%s)" % e
    if result.returncode != 0:
        # Independent review (2026-08-05): on a mid-failure (e.g. git created the leaf
        # then errored partway through registration), don't orphan it -- best-effort,
        # errors ignored, since the gate is about to fail-closed-block regardless.
        shutil.rmtree(worktree_path, ignore_errors=True)
        return None, "git worktree add failed (rc=%d): %s" % (
            result.returncode, (result.stderr or "").strip()[:500])
    return worktree_path, None


def remove_worktree(worktree_path, repo_root=None):
    """Best-effort cleanup -- by the time this runs the probe has already finished
    reading the worktree, so a cleanup failure here must NEVER change the gate's
    decision. Falls back to a plain rmtree (worktree left administratively registered,
    harmless, prunable later via `git worktree prune`) if `git worktree remove` itself
    fails for any reason."""
    if not worktree_path:
        return
    repo_root = repo_root or REPO_ROOT_OVERRIDE or CLAUDE_DIR
    try:
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_git_env())
    except Exception as e:  # pragma: no cover - defensive
        result = None
        sys.stderr.write(
            "pre-push doctrine gate: could not launch git worktree remove (%s).\n" % e)
    if result is None or result.returncode != 0:
        detail = (result.stderr or "").strip()[:300] if result is not None else ""
        sys.stderr.write(
            "pre-push doctrine gate: could not cleanly remove scratch worktree %s "
            "(%s) -- harmless but stale; `git worktree prune` clears it later.\n"
            % (worktree_path, detail))
        shutil.rmtree(worktree_path, ignore_errors=True)


def run_doctrine_probe():
    """Materialize the commit about to be pushed into a scratch worktree (see
    materialize_pushed_commit()) and run the probe against it with --live-root=, so it
    validates that commit's content in FULL live mode -- not the positional-argv single-
    fixture path, which would flip live_mode False and silently disable 7 coupled checks
    (OI-100 Trap 1). The probe has no --quiet flag -- unlike governor-drift-probe.py, its
    only options are --session-context=/--rules=/--terms=/--live-root=/...; passing an
    unrecognized flag would itself be an unrecognized-option [MISSING] finding and always
    fail-closed-block every push.

    CAPTURE-then-echo (was: inherit) so the SAME diagnostics still surface live to the git
    user AND the text is available to derive a one-line status-file summary from -- without
    re-running the probe (a second run would double the cost and could race a mid-push
    CLAUDE.md edit). Returns (exit_code, stdout_text). A launch failure -- including a
    worktree that could not be materialized -- is reported as (1, "") -- fail-closed: a
    probe we cannot run cannot prove doctrine is intact.

    Decoded utf-8/errors=replace and echoed through the utf-8-reconfigured streams so the
    probe's box/arrow/em-dash glyphs neither corrupt the display nor raise on a cp1252
    console (same stream-reconfigure guard as maintenance/append-event-log.py).

    env=_clean_git_env() (independent review, 2026-08-05): the probe itself shells out to
    git (check 8's tracked-.md roster, the backup-coverage sweep) -- an inherited
    GIT_DIR/GIT_WORK_TREE from the pre-push hook's own environment would silently redirect
    THOSE calls at the live repo instead of the materialized --live-root worktree, by the
    exact mechanism this module's own _clean_git_env() docstring already describes for its
    own git calls. Without this, git_tracked_md()'s roster for check 8 could read the live
    index (e.g. a file `git rm --cached`'d, uncommitted, still present in the pushed
    commit) instead of the worktree's -- narrow, but the same false-negative shape as
    OI-100 itself, so it is closed here rather than left as a second undisclosed gap."""
    worktree_path, err = materialize_pushed_commit()
    if worktree_path is None:
        sys.stderr.write(
            "pre-push doctrine gate: could not materialize the pushed commit (%s) - "
            "treating as drift (fail-closed).\n" % err)
        return 1, ""
    try:
        probe_script = PROBE_SCRIPT_OVERRIDE or PROBE_SCRIPT
        result = subprocess.run(
            [sys.executable, probe_script, "--live-root=%s" % worktree_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=_clean_git_env())
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
    finally:
        remove_worktree(worktree_path)


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


def build_override_entry(now=None, session_id=None, reason=None):
    """Newest-first event_log entry (must start '## ') recording an override use. Names the
    session that held the token AND the reason written into it: content-binding only pays
    for itself if the content reaches the audit trail.

    The session id is self-asserted (see override_tokens.py, HONEST LIMITS b) -- it records
    which id was presented, which is not the same as proving who pushed."""
    now = now or datetime.now()
    reason = (reason or "").strip() or "<none given in the token>"
    return (
        "## %s — Pre-push proceeded DESPITE doctrine drift (allow-doctrine-drift override used)\n\n"
        "- The `~/.claude` git pre-push doctrine gate (`hooks/git-prepush-doctrine-gate.py`) ran "
        "`doctrine-integrity-probe.py`, which reported drift (non-zero exit), but session `%s` held a "
        "valid `allow-doctrine-drift` token (session-scoped, `scope: doctrine-drift`, < 60 min from "
        "mtime), so the push was ALLOWED rather than blocked.\n"
        "- Reason recorded in the token: %s\n"
        "- Mechanical record only, per the rules.md §10 override protocol (token created only after "
        "Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override "
        "used at %s local.\n"
        % (now.strftime("%Y-%m-%d"), session_id or "<unknown>", reason,
           now.strftime("%Y-%m-%d %H:%M:%S"))
    )


def log_override_use(session_id=None, reason=None):
    """Append the override-use record to event_log.md via the canonical, collision-safe
    appender. Best-effort: a logging failure must not itself block a push Gabriel has
    already authorized to proceed."""
    entry = build_override_entry(session_id=session_id, reason=reason)
    cmd = [sys.executable, APPEND_LOG_SCRIPT]
    if EVENT_LOG_OVERRIDE:
        cmd += ["--log", EVENT_LOG_OVERRIDE]
    # --entry-file, NOT stdin -- see the identical fix in
    # git-prepush-hook-tests-gate.py: piped UTF-8 is decoded by append-event-log.py's
    # bare sys.stdin.read() using the Windows locale (cp1252) and lands
    # double-encoded. Same template, same corruption, same remedy (2026-08-03).
    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=".md", prefix="ora-override-entry-")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(entry)
        subprocess.run(cmd + ["--entry-file", path], capture_output=True)
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push doctrine gate: override used but event_log append FAILED (%s) - "
            "record it manually.\n" % e)
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


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
    session_id = current_session_id()
    # Look for a token ONLY when there is drift to override. decide() ignores the override
    # on a clean run anyway, and token_grants() CONSUMES a single-use token at validation
    # time -- so evaluating this eagerly would burn a token on a push that never needed one.
    # DOCTRINE_DRIFT is multi-use today, which makes this latent rather than live; the
    # short-circuit is what keeps adopting a single-use tier here safe instead of subtly
    # wrong (independent review, 2026-07-16).
    fields = override_token(session_id) if probe_rc != 0 else None
    exit_code, log_override = decide(probe_rc, fields is not None)
    # Layer-2 durable trace on every REAL gate run (both the drift AND no-drift paths).
    # Best-effort: a status-file failure never changes the gate's decision or exit code.
    if real_run:
        write_status_snapshot(probe_rc, probe_stdout)
    if log_override:
        log_override_use(session_id, (fields or {}).get("reason"))
        sys.stderr.write(
            "pre-push: doctrine drift present but OVERRIDDEN - session %s holds a valid "
            "allow-doctrine-drift token. Push ALLOWED; the override was logged to "
            "event_log.md.\n" % session_id)
    elif exit_code != 0:
        sys.stderr.write(
            "pre-push BLOCKED: doctrine-integrity-probe.py reported drift. Fix the drift "
            "first. If Gabriel has just explicitly authorized pushing anyway, write this "
            "override token and retry:\n%s"
            % describe_token(session_id, DOCTRINE_DRIFT))
        if not session_id:
            sys.stderr.write(
                "  NOTE: this push carries no CLAUDE_CODE_SESSION_ID, so no override can be "
                "honored here at all. Fix the drift -- do not try to mint a token.\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
