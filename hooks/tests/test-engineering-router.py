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

print("ALL ROUTER TESTS PASS")
