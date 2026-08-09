# test-engineering-router.py — run: python test-engineering-router.py
import subprocess, json, sys, os
HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engineering-router.py")  # hooks/ (test in hooks/tests/)

def run(prompt):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": prompt}),
                       capture_output=True, text=True)
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout

cases = [
    ("there's a bug, the rent roll parser is failing", "/debug"),
    ("build a new dashboard widget for WALT", "/build"),
    ("refactor the overlay module, it's too big", "/refactor"),
    ("research which charting library is fastest", "/research"),
    ("ship the brain mirror to production", "/ship"),
]
for prompt, expected in cases:
    out = run(prompt)
    assert expected in out, f"prompt {prompt!r} should suggest {expected}, got: {out!r}"
    assert out.isascii(), f"hook output must be ASCII-only (Windows cp1252 console safe); non-ASCII in: {out!r}"

# Still-firing core cases (explicit / unambiguous action prompts)
firing = [
    ("the rent roll parser throws an error", "/debug"),
    ("build a new dashboard widget", "/build"),
    ("ship the brain mirror to production", "/ship"),
]
for prompt, expected in firing:
    out = run(prompt)
    assert expected in out, f"prompt {prompt!r} should suggest {expected}, got: {out!r}"
    assert out.isascii(), f"hook output must be ASCII-only (Windows cp1252 console safe); non-ASCII in: {out!r}"

# Silence on non-work prompts and empty prompts (no false nudges)
assert run("what's the weather") == "", "should stay silent on non-coding prompts"
assert run("") == "", "should stay silent on empty prompt"

# Negative-context regression cases: analytical/meta/scheduling -> MUST stay silent
silent = [
    "Assume this engineering operating system isn't perfect and fails more often than it should. Explain why this would happen and suggest improvements.",
    "explain why the deploy keeps failing in general terms",
    "remind me to debug this tomorrow",
    "what are the tradeoffs of refactoring vs rewriting",
]
for prompt in silent:
    out = run(prompt)
    assert out == "", f"analytical/meta prompt should stay silent, got: {out!r}"

# Cloud-review confidentiality warning (fix #1b): naming a confidential repo + ultra/cloud review MUST warn -> LOCAL
cr = run("can you run /code-review ultra on oxford-command-center")
assert ("confidential" in cr.lower()) and ("local" in cr.lower()), f"cloud review on confidential repo must warn to use LOCAL, got: {cr!r}"
assert cr.isascii(), f"warning must be ASCII, got: {cr!r}"
# cloud review WITHOUT naming a confidential repo -> no confidentiality flag
cr2 = run("run /code-review ultra on my-public-sandbox")
assert "confidential" not in cr2.lower(), f"should not flag a non-confidential repo, got: {cr2!r}"

# --- Defect class 1 (2026-07-18 fixture): research/plan-dominant prompt MUST NOT route L7 /ship,
# even when it name-drops deploy/ship tokens or says "do not start coding". Should route L5/L3-plan (or be silent).
research_plan_fixture = (
    "Perform deep research on AI coding architecture and agent deployment patterns. "
    "Create a plan. Do not start coding yet. Present the detailed step by step plan before we ship anything."
)
rp = run(research_plan_fixture)
assert "/ship" not in rp and "L7" not in rp, f"research/plan prompt must NOT route L7, got: {rp!r}"
assert "DOCTRINE BLOCK" not in rp, f"research/plan prompt must not trip the doctrine block, got: {rp!r}"
assert (rp == "") or ("/research" in rp) or ("/plan" in rp) or ("/build" in rp), \
    f"research/plan prompt should be silent or suggest L5/L3-plan, got: {rp!r}"
assert rp.isascii(), f"output must be ASCII, got: {rp!r}"

# explicit "do not start coding" alone MUST never yield L7 even with a bare deploy token
nocode = run("Outline the migration steps, do not start coding. We may deploy later.")
assert "/ship" not in nocode and "L7" not in nocode, f"'do not start coding' must never yield L7, got: {nocode!r}"

# --- Defect class 2 (2026-07-18 fixture): '/code-review ultra' inside a SYSTEM-NOTIFICATION /
# task-result turn (agent notification text, NOT a user request) MUST NOT trip the DOCTRINE BLOCK.
sysnotif = run(
    "[SYSTEM NOTIFICATION - NOT USER INPUT] Background task completed. "
    "The agent ran /code-review ultra on oxford-command-center and reported findings."
)
assert "DOCTRINE BLOCK" not in sysnotif, f"system-notification text must not trip the doctrine block, got: {sysnotif!r}"
assert "/ship" not in sysnotif and "L7" not in sysnotif, f"system-notification text must not route a lane, got: {sysnotif!r}"

# task-notification-shaped wrapper likewise ignored
taskwrap = run("<task-notification>agent finished: /code-review ultra on oxford-command-center</task-notification>")
assert "DOCTRINE BLOCK" not in taskwrap, f"task-notification wrapper must not trip the doctrine block, got: {taskwrap!r}"

# --- Regression: a GENUINE deploy request still routes L7 /ship
dep = run("deploy the site to production")
assert "/ship" in dep, f"genuine deploy request must still route L7 /ship, got: {dep!r}"

# --- Regression: a GENUINE user '/code-review ultra' on a confidential repo still BLOCKS
genblock = run("run /code-review ultra on oxford-command-center")
assert ("confidential" in genblock.lower()) and ("local" in genblock.lower()), \
    f"genuine cloud review on confidential repo must still warn/block, got: {genblock!r}"

# --- Plan-gate in-turn budget reset (2026-08-05) ------------------------------
# A qualifying scoped directive resets eos-plan-gate's per-session edit budget,
# so Gabriel is not asked to re-approve work he already enumerated. FALSE
# POSITIVES ARE THE DANGEROUS DIRECTION -- each one silently weakens a safety
# gate -- so the negative cases below matter more than the positive ones.
import importlib.util as _ilu, os as _os, tempfile as _tf, shutil as _sh

_spec = _ilu.spec_from_file_location(
    "_er_pg", _os.path.join(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))), "engineering-router.py"))
_er = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_er)

_base = _tf.mkdtemp(prefix="router-plangate-")


def _resets(prompt, sid):
    """True if `prompt` resets a CONSUMED edit budget."""
    sess = _os.path.join(_base, sid)
    _os.makedirs(sess, exist_ok=True)
    cf = _os.path.join(sess, "code-edits.count")
    with open(cf, "w") as fh:
        fh.write("7")
    _os.environ["EOS_SESSIONS_DIR"] = _base
    _er._reset_plan_gate_budget({"session_id": sid}, prompt, prompt.lower())
    with open(cf) as fh:
        return fh.read().strip() == "0"


# MUST reset -- drawn from real override-reason strings in lane telemetry
_QUALIFY = [
    "Implement 1-3 now",
    "implementing items 1-3 of the 5 ranked recommendations",
    "execute the pre-written top-5 plan from memory/x.md",
    "Fix this: item 1, item 2 and item 3 -- proceed",
    "do all four now",
    "Fix these items:\n1. the guard\n2. the probe\n3. the tests",
    "apply steps 2 through 5",
    "proceed with the plan",
]
for _i, _p in enumerate(_QUALIFY):
    assert _resets(_p, "q%02d" % _i), \
        "scoped directive must reset the plan-gate budget: %r" % _p

# MUST NOT reset -- a false positive here silently disables the gate
_VAGUE = [
    "fix this", "Proceed", "what's next?", "this is broken",
    "add a test", "build the feature",
    "can you explain how the guard works",
    "I have 3 monitors and 2 keyboards",             # bare quantities
    "summarize the last 3 commits",                  # analytical
    "explain step 1 and step 2 of the algorithm",    # item refs, no imperative
    "the invoice has item 1 and item 2 on it",       # item refs, no imperative
    "",
]
for _i, _p in enumerate(_VAGUE):
    assert not _resets(_p, "v%02d" % _i), \
        "vague/non-directive prompt must NOT reset the plan-gate budget: %r" % _p

# Never fabricates session state for a session that has consumed no budget.
_virgin = _os.path.join(_base, "virgin")
_os.makedirs(_virgin, exist_ok=True)
_er._reset_plan_gate_budget({"session_id": "virgin"},
                            "Implement 1-3 now", "implement 1-3 now")
assert not _os.path.isfile(_os.path.join(_virgin, "code-edits.count")), \
    "must not create a count file for a session that has edited nothing"

# Malformed session ids must not raise -- this runs on every user turn.
for _bad in (None, "", 123, {"a": 1}):
    _er._reset_plan_gate_budget({"session_id": _bad}, "Implement 1-3 now",
                                "implement 1-3 now")

_sh.rmtree(_base, ignore_errors=True)

# --- Concurrent-session advisory (2026-08-05) ---------------------------------
# 2026-08-05 investigation (reference_concurrent_session_duplicate_hardening_work.md):
# three near-collisions in one ~20-concurrent-session day, none caught proactively.
# Root cause: CLAUDE.md's own "already-done" pre-flight check has no enforcement
# point -- nothing surfaces concurrent-session activity automatically at task START.
# This hook already fires on every prompt, so it is the right place to append a
# cheap, fail-open, ADVISORY-ONLY line (never blocks, mirrors this file's own
# non-blocking contract) using the already-proven session_liveness reader.

# A real, EXISTING, empty directory -- not a missing path. This matters for the
# run_env() subprocess cases below, which exercise session_liveness's PRODUCTION
# resolution path (sessions_dir=None -> ORA_FLEET_SESSIONS_DIR env var): a MISSING
# directory there falls through to session_liveness's documented old-format
# fallback (the REAL production legacy session-state.json), which is exactly what
# those fixtures must NOT exercise. (The explicit-sessions_dir calls just below --
# _concurrent_session_note(..., sessions_dir=_sdir_empty) -- don't need this: an
# explicit sessions_dir argument is honored with no fallback either way, per
# session_liveness.py's own docstring; verified separately by the
# "does/not/exist" case further down.) An existing-but-empty dir cleanly means
# "zero other sessions" on both paths.
_sdir_empty = _tf.mkdtemp(prefix="router-liveness-empty-")
_note_none = _er._concurrent_session_note("me", sessions_dir=_sdir_empty)
assert _note_none == "", f"no live sessions -> no note, got: {_note_none!r}"

_sdir = _tf.mkdtemp(prefix="router-liveness-live-")
def _write_session(sid, status="working"):
    with open(_os.path.join(_sdir, sid + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"_sid": sid, "status": status, "cwd": "C:/x", "lastAt": "2026-08-05T12:00:00"}, fh)

_write_session("other1")
_write_session("other2")
_write_session("ended-one", status="ended")  # must be excluded, matches session_liveness contract
_note = _er._concurrent_session_note("me", sessions_dir=_sdir)
assert "2" in _note, f"note should count the 2 non-ended other sessions, got: {_note!r}"
assert "list_sessions" in _note or "event_log" in _note, \
    f"note should point at how to check, got: {_note!r}"
assert _note.isascii(), f"note must be ASCII-only, got: {_note!r}"

# Own session is excluded even if present in the same dir.
_write_session("me", status="working")
_note_self = _er._concurrent_session_note("me", sessions_dir=_sdir)
assert "2" in _note_self, f"own session must not count itself, got: {_note_self!r}"

# Never raises on a broken/missing sessions dir or malformed session_id -- fail-open,
# same posture as every other session_liveness consumer in this codebase.
assert _er._concurrent_session_note("me", sessions_dir="C:/definitely/does/not/exist") == ""

# A non-string/empty session_id must short-circuit BEFORE self-exclusion is even
# attempted -- other_active_sessions() excludes only an EXACT own-sid match, so an
# invalid sid would otherwise never match this session's own file and count the
# caller as one of the "other" sessions. Tested against the POPULATED dir (not the
# empty one): a weaker test against an empty dir would pass for the wrong reason
# (nothing to falsely count) and prove nothing about self-exclusion.
for _bad_sid in (None, "", "   ", 123, {"a": 1}):
    _bad_note = _er._concurrent_session_note(_bad_sid, sessions_dir=_sdir)
    assert _bad_note == "", \
        f"invalid session_id must short-circuit to '', got: {_bad_note!r} for {_bad_sid!r}"

# End-to-end: the advisory is APPENDED to a firing lane's output, never replaces it,
# never appears when the hook would otherwise be silent, and keeps output ASCII.
def run_env(prompt, sessions_dir):
    env = dict(_os.environ)
    env["ORA_FLEET_SESSIONS_DIR"] = sessions_dir
    p = subprocess.run([sys.executable, HOOK],
                       input=json.dumps({"prompt": prompt, "session_id": "me"}),
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout

out_live = run_env("build a new dashboard widget for WALT", _sdir)
assert "/build" in out_live, f"lane suggestion must still fire, got: {out_live!r}"
assert "2 other session" in out_live, f"live sessions -> advisory appended, got: {out_live!r}"
assert out_live.isascii(), f"output must stay ASCII, got: {out_live!r}"

out_solo = run_env("build a new dashboard widget for WALT", _sdir_empty)
assert "/build" in out_solo, f"lane suggestion must still fire, got: {out_solo!r}"
assert "other session" not in out_solo, f"no live sessions -> no advisory, got: {out_solo!r}"

# Silent prompts stay silent regardless of concurrent-session state -- the advisory
# only ever appends to an already-firing lane, never fires standalone.
out_silent = run_env("what's the weather", _sdir)
assert out_silent == "", f"non-work prompt must stay silent even with live sessions, got: {out_silent!r}"

_sh.rmtree(_sdir, ignore_errors=True)
_sh.rmtree(_sdir_empty, ignore_errors=True)

print("ALL ROUTER TESTS PASS")
