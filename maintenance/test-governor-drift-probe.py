#!/usr/bin/env python3
"""Tests for governor-drift-probe.py (TDD).

Two layers:
  * UNIT  -- import scan_line() and assert the DETECTION logic is intact: canonical
             governor lines are clean; real DSCR/LTV drift still flags. This is the
             guardrail that the false-positive fix did NOT weaken enforcement.
  * E2E   -- run the probe as a subprocess against a FIXTURE HOME built in a temp dir
             (HOME/USERPROFILE redirected, see run_probe), never against the live machine.

HERMETIC BY DEFAULT (2026-11-06): the E2E layer used to scan the live machine -- the real
~/.claude, ~/ora-skills and, through ~/ora-skills/.claude/worktrees/, every OTHER Claude
session's in-flight worktree copy. A drift sitting in someone else's unfinished worktree
("portfolio-growth/SKILL.md:33 LTV 65% != 40%", a DSCR 1.75) failed this file and so blocked
every push of ora-claude-config from unrelated branches via git-prepush-hook-tests-gate.py.
The pass/fail of this file now depends only on the probe's code and the fixtures built here.
Live-machine checks still exist, but are OPT-IN: they run only when
ORA_GOVERNOR_PROBE_LIVE_TESTS=1 is set in the environment, which the pre-push gate never
does (they SKIP otherwise).

Run: python test-governor-drift-probe.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import os
import re
import sys
import shutil
import subprocess
import importlib.util
import contextlib
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "governor-drift-probe.py")


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("governor_drift_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Opt-in flag for the tests that read LIVE machine state (the real ~/.claude, ~/ora-skills).
# The pre-push gate never sets it, so the gate's verdict can never depend on what other
# sessions have sitting in their worktrees. Run manually: ORA_GOVERNOR_PROBE_LIVE_TESTS=1.
LIVE_TESTS_FLAG = "ORA_GOVERNOR_PROBE_LIVE_TESTS"

# Every variable os.path.expanduser("~") can resolve the home directory from (ntpath:
# USERPROFILE, else HOMEDRIVE+HOMEPATH; posixpath: HOME). All are stripped and replaced, so
# the probe's module-level HOME -- and through it every scan root in build_targets() --
# resolves inside the fixture.
_HOME_ENV_VARS = ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")


def _live_tests_enabled():
    return os.environ.get(LIVE_TESTS_FLAG) == "1"


def _skip_unless_live(name):
    """True (and prints SKIP) when a live-machine test must not run."""
    if _live_tests_enabled():
        return False
    print("  SKIP %s (reads live machine state; set %s=1 to run)" % (name, LIVE_TESTS_FLAG))
    return True


def _hermetic_env(home):
    """A child environment whose home directory is `home` and nothing else."""
    env = {k: v for k, v in os.environ.items() if k.upper() not in _HOME_ENV_VARS}
    env["HOME"] = home
    env["USERPROFILE"] = home
    return env


def run_probe(argv=None, home=None, live=False):
    """Run the probe as a subprocess. `home` is REQUIRED (a fixture home dir) unless the
    caller is an opt-in live test passing live=True -- an accidental bare run_probe() would
    otherwise scan the live machine, which is exactly the isolation bug fixed 2026-11-06."""
    cmd = [sys.executable, PROBE]
    if argv:
        cmd += argv
    if live:
        assert _live_tests_enabled(), "live probe run requested without %s=1" % LIVE_TESTS_FLAG
        env = None
    else:
        assert home is not None, (
            "run_probe() needs a fixture home (or live=True from an opt-in live test)")
        env = _hermetic_env(home)
    # encoding="utf-8" (found 2026-08-22): text=True with no explicit encoding decodes the
    # probe's stdout/stderr using locale.getpreferredencoding() (cp1252 on Windows). The
    # probe reconfigures ITS OWN stdout to UTF-8 (module docstring: "force UTF-8 so the
    # probe never crashes on its own output") to safely echo scanned file content, but that
    # just moves the crash up here: a smart quote like U+201D encodes as UTF-8 bytes
    # E2 80 9D, and byte 0x9D has no cp1252 mapping at all, so subprocess's internal reader
    # thread crashes (UnicodeDecodeError, printed straight to real stderr, never raised to
    # the caller) and silently drops the captured stdout to None instead.
    return subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)


# Canonical governor declarations seeded into every fixture home, so each in-scope root
# the probe walks has real, scannable, CLEAN content (a fixture that is clean only because
# it is empty would prove nothing).
_FIXTURE_CANON_LINE = "Acquisition governor (non-negotiable): DSCR >= 1.25x, LTV <= 40%.\n"
_MEM_REL = (".claude", "projects", "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _seed_fixture_home(home):
    _write(os.path.join(home, ".claude", "CLAUDE.md"), "# CLAUDE.md\n\n" + _FIXTURE_CANON_LINE)
    _write(os.path.join(home, *(_MEM_REL + ("standards.md",))), _FIXTURE_CANON_LINE)
    _write(os.path.join(home, "ora-skills", "deal-comparison", "SKILL.md"),
           "---\nname: deal-comparison\n---\n\n" + _FIXTURE_CANON_LINE)
    _write(os.path.join(home, ".claude", "scheduled-tasks", "ora-fixture-task", "SKILL.md"),
           "---\nname: ora-fixture-task\n---\n\n" + _FIXTURE_CANON_LINE)
    os.makedirs(os.path.join(home, ".claude", "hooks"), exist_ok=True)
    os.makedirs(os.path.join(home, ".claude", "maintenance"), exist_ok=True)
    _commit_fixture_skills(home)


def _commit_fixture_skills(home, msg="fixture"):
    """The probe reads ~/ora-skills from COMMITTED refs (refs/remotes/origin/main +
    refs/heads/main), never its working tree -- so fixture ora-skills content only counts once
    it is committed on main. Initialises the repo on first use; commits everything (adds,
    edits, deletions) and points origin/main at the result."""
    repo = os.path.join(home, "ora-skills")
    os.makedirs(repo, exist_ok=True)
    if not os.path.isdir(os.path.join(repo, ".git")):
        _git(repo, "init", "-q", "-b", "main")
        _write(os.path.join(repo, ".gitignore"), ".claude/worktrees/\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", msg)
    _git(repo, "update-ref", "refs/remotes/origin/main", "refs/heads/main")


@contextlib.contextmanager
def _fixture_home(prefix="gdp-home-"):
    """A throwaway home dir seeded with clean canonical content in the probe's scan roots."""
    home = tempfile.mkdtemp(prefix=prefix)
    try:
        _seed_fixture_home(home)
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)


def _load_probe_module_at_home(home):
    """Load the probe with its module-level HOME/CLAUDE/MEM/ORA_SKILLS_REPO resolved inside
    `home`, so path-shaped assertions never touch the live machine."""
    saved = {k: os.environ.get(k) for k in _HOME_ENV_VARS}
    try:
        for k in _HOME_ENV_VARS:
            os.environ.pop(k, None)
        os.environ["HOME"] = home
        os.environ["USERPROFILE"] = home
        return _load_probe_module()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_canonical_clean_unit():
    """A line declaring the canonical governor (DSCR 1.25 / LTV 40) is clean."""
    m = _load_probe_module()
    assert m.scan_line("Acquisition governor (non-negotiable): DSCR >= 1.25x, LTV <= 40%.") == [], \
        "canonical governor line should produce no findings"
    print("  PASS test_canonical_clean_unit")


def test_real_ltv_drift_still_flags_unit():
    """A governor declaration with a WRONG LTV ceiling still flags (enforcement intact)."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter / LTV ceiling <= 65% on every deal.")
    assert any("LTV" in o for o in out), (
        "real LTV drift (65%%) must still flag; got %r" % out)
    print("  PASS test_real_ltv_drift_still_flags_unit")


def test_real_dscr_drift_still_flags_unit():
    """A governor declaration with a WRONG DSCR floor still flags (enforcement intact)."""
    m = _load_probe_module()
    out = m.scan_line("Self-imposed minimum DSCR floor is 1.10x (governor).")
    assert any("DSCR" in o for o in out), (
        "real DSCR drift (1.10x) must still flag; got %r" % out)
    # 1.75 regression sentinel still on.
    assert m.scan_line("legacy governor DSCR 1.75x"), "1.75 DSCR sentinel must stay armed"
    print("  PASS test_real_dscr_drift_still_flags_unit")


def test_dscr_drift_without_trailing_x_flags_unit():
    """A governor DSCR floor written WITHOUT a trailing x/× still flags.

    Real governors in this shop are written "DSCR >= 1.25x", but a drift could be
    introduced as a bare "DSCR floor 1.10" with no multiplier sign. The equality
    check must not depend on the 'x' being present.
    """
    m = _load_probe_module()
    out = m.scan_line("Hard acquisition screen (non-negotiable): DSCR floor 1.10.")
    assert any("DSCR" in o for o in out), (
        "x-less DSCR drift (1.10) must flag; got %r" % out)
    # And with an ascii ">=" comparator (which used to false-trip the scoring sentinel
    # via the "= 1" fragment), both with and without a trailing x:
    out2 = m.scan_line("Minimum DSCR >= 1.15 on every deal (governor).")
    assert any("DSCR" in o for o in out2), (
        "x-less DSCR drift (>=1.15) must flag; got %r" % out2)
    out3 = m.scan_line("Hard filter: DSCR >= 1.10x (governor).")
    assert any("DSCR" in o for o in out3), (
        "ascii-comparator DSCR drift (>=1.10x) must flag; got %r" % out3)
    print("  PASS test_dscr_drift_without_trailing_x_flags_unit")


def test_real_scoring_rubric_still_excluded_unit():
    """A genuine DSCR scoring rubric must NOT be read as governor drift (no FP).

    Guards the RE_SCORING tightening: '=10'/'=8' point assignments and 'N.N-N' bands
    still mark the line as a rubric and exclude it from the equality check.
    """
    m = _load_probe_module()
    rubric = "DSCR scoring (governor-adjacent): >=2.5x=10; 2.0-2.49x=8; 1.5-1.99x=5; <1.25x=0."
    assert m.scan_line(rubric) == [], (
        "scoring rubric should be excluded, not flagged as drift; got %r" % m.scan_line(rubric))
    print("  PASS test_real_scoring_rubric_still_excluded_unit")


def test_canonical_dscr_without_x_clean_unit():
    """The canonical 1.25 (no x) on a governor line is still CLEAN (no over-match)."""
    m = _load_probe_module()
    assert m.scan_line("Governor (non-negotiable): DSCR floor 1.25, LTV ceiling 40%.") == [], \
        "canonical DSCR 1.25 (no x) should not flag"
    print("  PASS test_canonical_dscr_without_x_clean_unit")


def test_non_governor_dscr_prose_not_flagged_unit():
    """A non-declaration prose mention of a deal's DSCR must NOT flag (is_gov gate)."""
    m = _load_probe_module()
    assert m.scan_line("The deal's actual DSCR came in at 1.42 last quarter.") == [], \
        "prose DSCR mention (no governor keyword) should not flag"
    print("  PASS test_non_governor_dscr_prose_not_flagged_unit")


def test_narrative_suppression_is_file_level_not_logic_level():
    """The event_log narrative lines DO trip scan_line() -- proving the suppression is
    a file-scoped exclusion, not a gutting of the detection logic."""
    m = _load_probe_module()
    # The exact shape that false-flagged on 2026-06-09 (event_log:57 financing sleeve).
    out = m.scan_line("did NOT find a governor line (only a 65% LTV financing-scenario "
                      "assumption); governors live in CLAUDE.md.")
    assert out, "scan_line should still detect at the line level; file-level skip does the suppression"
    print("  PASS test_narrative_suppression_is_file_level_not_logic_level")


def test_ltv_correction_note_suppressed_unit():
    """I-4: a legit LTV correction note ("LTV ceiling corrected from 65% to 40%") documents a PAST
    fix landing on canonical 40% -- the old 65% it quotes must NOT flag as live drift. Symmetric
    to the DSCR "corrected from 1.75 → 1.25" note that was already suppressed."""
    m = _load_probe_module()
    notes = [
        "Governor: LTV ceiling corrected from 65% to 40% on 2026-06-03.",
        "LTV ceiling corrected down from 65% to 40% (was wrong in v1).",
        "Hard filter: LTV ceiling corrected from 70% → 40%.",
    ]
    for line in notes:
        assert m.scan_line(line) == [], (
            "LTV correction-to-canonical note must be suppressed; line=%r got=%r"
            % (line, m.scan_line(line)))
    # And the DSCR correction note stays suppressed (regression on the pre-existing behavior).
    assert m.scan_line("DSCR >= 1.25x — governor (corrected from 1.75 → 1.25, G5).") == [], \
        "DSCR correction note must remain suppressed"
    print("  PASS test_ltv_correction_note_suppressed_unit")


def test_ltv_correction_note_does_not_oversuppress_unit():
    """I-4 guard: the note suppressor must be TIGHT (40% as the explicit correction destination),
    so it does NOT silence a REAL drift that merely shares a line with the word 'corrected', and
    an LTV note must NOT suppress a co-located DSCR drift (metric-specific suppression)."""
    m = _load_probe_module()
    # 'corrected ... to 40%' with NO 'from <N>%' is not a ceiling correction -> real 65% still flags.
    out1 = m.scan_line("Hard filter: LTV ceiling 65% (typo corrected to 40% in section 4).")
    assert any("65" in o for o in out1), (
        "real 65%% ceiling must still flag when 40%% is not a from->to correction; got %r" % out1)
    # an LTV correction note must NOT suppress a co-located DSCR drift.
    out2 = m.scan_line("Governor DSCR floor 1.40x; LTV corrected from 70% to 40% last cycle.")
    assert any("1.40" in o for o in out2), (
        "DSCR drift must still flag despite a co-located LTV correction note; got %r" % out2)
    assert not any("70" in o for o in out2), (
        "the corrected-away 70%% must be suppressed; got %r" % out2)
    # span-scoped suppression (not whole-branch): a LIVE 65% ceiling co-located with an UNRELATED
    # correction-to-40 in a later clause must STILL flag -- only the corrected-away value is skipped.
    out3 = m.scan_line("Hard filter: LTV ceiling 65%; basis discount corrected from 30% to 40%.")
    assert any("65" in o for o in out3), (
        "live 65%% ceiling must flag despite an unrelated correction-to-40 clause; got %r" % out3)
    print("  PASS test_ltv_correction_note_does_not_oversuppress_unit")


def test_dscr_correction_note_span_scoped_unit():
    """M-2 symmetry: the DSCR correction-note suppressor is now span-scoped too -- only the
    corrected-away old value (inside a 'corrected from <X> to/→ 1.25' span) is skipped, NOT the
    whole DSCR branch. A genuine note stays clean; a live drift sharing the line still flags."""
    m = _load_probe_module()
    # genuine DSCR correction notes stay suppressed (the real-tree shape + an x-less variant).
    for line in ["DSCR >= 1.25x — governor (corrected from 1.75 → 1.25 on 2026-06-03, G5).",
                 "Hard filter: DSCR floor corrected from 1.40 -> 1.25.",
                 "Governor: DSCR floor corrected from 1.75x → 1.25x."]:  # canonical WITH trailing x
        assert m.scan_line(line) == [], (
            "genuine DSCR correction note must be suppressed; line=%r got=%r"
            % (line, m.scan_line(line)))
    # 'corrected to 1.25' WITHOUT a 'from <X>' is not a from->to note -> a live 1.40 still flags.
    out1 = m.scan_line("Governor DSCR floor 1.40x (cap rate corrected to 1.25 elsewhere).")
    assert any("1.40" in o for o in out1), (
        "live 1.40 drift must flag when 1.25 is not a from->to correction dest; got %r" % out1)
    # a live 1.75 NOT inside a correction span must still trip the sentinel.
    out2 = m.scan_line("DSCR governor 1.75x is the new floor; note 1.25 was corrected earlier.")
    assert any("1.75" in o for o in out2), (
        "live 1.75 must still trip the sentinel when not corrected-away; got %r" % out2)
    # two-clause: genuine correction in clause 1, LIVE drift in clause 2 -> the live one flags.
    out3 = m.scan_line("DSCR floor corrected from 1.75 → 1.25; mezz sleeve DSCR floor 1.10x.")
    assert any("1.10" in o for o in out3), (
        "live mezz 1.10 drift must flag despite a co-located correction note; got %r" % out3)
    assert not any("1.75" in o for o in out3), (
        "the corrected-away 1.75 must stay suppressed; got %r" % out3)
    print("  PASS test_dscr_correction_note_span_scoped_unit")


def test_governor_with_incidental_rubric_fragment_flags_unit():
    """I-1: a GOVERNOR DECLARATION that merely SHARES a line with a single rubric-shaped
    fragment (=N point assignment, "was X-Y" band note, "=0 if below" consequence clause)
    must STILL have its declared DSCR floor checked. The old whole-line RE_SCORING skip
    swallowed all four of these (any single =N/band killed the equality check)."""
    m = _load_probe_module()
    cases = [
        "Governor: DSCR floor 1.10 (was 1.0-1.5 band legacy)",  # bare band fragment
        "Governor DSCR >= 1.10x = 5 points",                    # single =5 assignment
        "Governor DSCR floor 1.10, =0 if below",                # =0 consequence clause
        "Governor DSCR floor 1.10x; <1.25x=0",                  # single rubric tail
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "drifted governor (1.10) co-located with a rubric fragment must flag; "
            "line=%r got=%r" % (line, out))
    print("  PASS test_governor_with_incidental_rubric_fragment_flags_unit")


def test_count_gate_not_bypassable_by_appending_rubric_pairs_unit():
    """I-1 hardening: a wrong DSCR floor must NOT escape merely because >=2 rubric pairs
    were appended to the same line to trip the rubric count gate. The declared floor sits
    OUTSIDE every value=points pair, so it must still be checked even on a rubric-looking line."""
    m = _load_probe_module()
    line = ("Acquisition governor: minimum DSCR 1.40x. "
            "(Scoring band ref: >=2.5x=10; 2.0-2.49x=8.)")
    out = m.scan_line(line)
    assert any("1.40" in o for o in out), (
        "wrong floor 1.40 declared outside the rubric pairs must still flag; got %r" % out)
    print("  PASS test_count_gate_not_bypassable_by_appending_rubric_pairs_unit")


def test_multi_pair_rubric_false_positive_guard_unit():
    """The companion guard to the above: a GENUINE multi-entry scoring rubric (>=2 value=points
    pairs) must STILL be excluded -- the fix must not reintroduce the rubric false positive a
    naive span-strip would. Covers the canonical 4-pair rubric and a minimal 2-pair rubric."""
    m = _load_probe_module()
    four = "DSCR scoring (governor-adjacent): >=2.5x=10; 2.0-2.49x=8; 1.5-1.99x=5; <1.25x=0."
    assert m.scan_line(four) == [], (
        "4-pair rubric must stay clean; got %r" % m.scan_line(four))
    two = "Governor DSCR rubric: >=2.5x=10; 2.0-2.49x=8."
    assert m.scan_line(two) == [], (
        "2-pair rubric must stay clean; got %r" % m.scan_line(two))
    print("  PASS test_multi_pair_rubric_false_positive_guard_unit")


def test_canonical_decoy_does_not_hide_dscr_drift_unit():
    """I-2: a drifted DSCR floor must flag even when a CANONICAL value is restated earlier on
    the same line (the decoy). The primary extractor binds to the FIRST decimal after 'dscr'
    (canonical 1.25), so the real value must be picked up via its change/declaration construct."""
    m = _load_probe_module()
    cases = [
        "Acquisition governor: DSCR floor raised from 1.25 to 1.40x.",  # verb from-to pivot
        "Hard filter: minimum DSCR increased to 1.40x (governor).",     # verb-to (no canon)
        "Governor DSCR floor 1.25 -> 1.40x.",                           # arrow pivot
        "Acquisition governor: DSCR floor 1.25 now 1.40x.",             # 'now' pivot (canon-first)
        "Governor: DSCR floor 1.25 then 1.40x.",                        # 'then' pivot
        "Governor: DSCR floor is now 1.40x (was 1.25).",                # 'is now' pivot
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any("1.40" in o for o in out), (
            "drifted DSCR floor 1.40 behind a canonical decoy must flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_canonical_decoy_does_not_hide_dscr_drift_unit")


def test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit():
    """I-3: a no-x DSCR decoy where the canonical 1.25 sits immediately LEFT of an arrow/then/now
    pivot ("DSCR floor 1.25 -> 1.40") must flag. The canonical left-operand is the metric guard
    that replaces the trailing-x requirement for THIS shape: it is what distinguishes a DSCR drift
    edit from an incidental "throughput 2.0 -> 3.5" (left operand 2.0, not canonical)."""
    m = _load_probe_module()
    flag = [
        "Governor DSCR floor 1.25 -> 1.40",       # ascii arrow, no x
        "Governor: DSCR floor 1.25 then 1.40",     # 'then' pivot, no x
        "Acquisition governor DSCR floor 1.25 now 1.40",   # 'now' pivot, no x
    ]
    for line in flag:
        out = m.scan_line(line)
        assert any("1.40" in o for o in out), (
            "no-x canonical-left pivot decoy must flag; line=%r got=%r" % (line, out))
    # The disambiguator must NOT fire when the pivot's left operand is NOT canonical (incidental
    # metric): these stay clean (also re-covered in the incidental-figures guard).
    clean = [
        "Governor: DSCR floor 1.25x; throughput 2.0 -> 3.5 units.",
        "Governor: DSCR 1.25x; occupancy ratio 1.10 -> 1.42 over the year.",
        # M-1 guard: a literal 1.25 + pivot that is NOT a DSCR figure (no 'dscr' on the line).
        "Hard filter governor: schema migrated v1.25 -> 2.00 this quarter.",
        "Acquisition governor: equity multiple 1.25 then 1.60 in the model.",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "non-canonical left operand must not flag; line=%r got=%r" % (line, m.scan_line(line)))
    print("  PASS test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit")


def test_canonical_decoy_does_not_hide_ltv_drift_unit():
    """I-2 (LTV): a drifted LTV ceiling must flag even when 40% is restated earlier on the line.
    LTV detection requires an LTV-adjacent ceiling/max anchor (the metric guard), so the decoy
    must phrase the drift as an LTV ceiling/max -- which is how a real LTV drift edit reads."""
    m = _load_probe_module()
    cases = [
        "Governor: LTV ceiling raised from 40% to 65%.",      # verb from-to pivot
        "Governor: LTV ceiling now 65% (was 40%).",           # 'now' pivot after anchor
        "Hard filter: max LTV 65% (was 40%).",                # max-LTV anchor
        "Governor: LTV ceiling raised from 45% to 65%.",      # non-canonical 'from' (45) must flag
        "Governor: LTV ceiling, revised, 65%.",               # first % after anchor IS the drift
        "Governor: LTV ceiling henceforth set to 65%.",       # I-3: drift >22 chars past anchor
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any(("65" in o) or ("45" in o) for o in out), (
            "drifted LTV ceiling behind a canonical/anchored decoy must flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_canonical_decoy_does_not_hide_ltv_drift_unit")


def test_incidental_figures_not_flagged_unit():
    """I-2 FP guard: an incidental OBSERVED/cap-rate/phase figure on a governor line -- NOT bound
    to a threshold construct -- must NOT flag. This is the false-positive class a naive
    multi-extract reintroduces; the real tree is dense with such figures (cap rates, phase tags,
    deal LTV ranges), so the live probe must stay clean."""
    m = _load_probe_module()
    clean = [
        "Acquisition governor: DSCR floor 1.25x (portfolio came in at 1.42 avg).",
        "Governor: LTV ceiling 40% (deals currently underwritten to 28%).",
        "Hard governor: DSCR >= 1.25x, LTV <= 40% (cap rates 7.0-8.0%, Phase 1.1 done).",
        "Hard filter (non-negotiable): DSCR >= 1.25x at 40% LTV; comps 60-70% of replacement.",
        # real-tree shape: a basis-discount threshold bound to a bare comparator is NOT an LTV.
        "ORA basis buyer: prefer >=25% below replacement, >8% yield; DSCR/LTV governor separate.",
        # change-verb + "from N% to N%" RANGE where N is NOT canonical -> not a decoy, must not flag.
        "Governor note: comps moved within a band from 30% to 38% of cost; DSCR/LTV unchanged.",
        # metric-agnostic keyword/arrow FPs (non-DSCR decimals lack the x; non-LTV %s lack the
        # LTV-adjacent ceiling/max anchor). A realistic combined buy-box line must stay clean:
        "Hard filter: DSCR >= 1.25x, LTV <= 40%, max 7% exit cap, min 8% YoC.",
        "Governor: DSCR 1.25x, LTV 40%; occupancy 80% -> 95%, vacancy 15% -> 8% target.",
        "Governor: DSCR floor 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.",
        "Governor: DSCR floor 1.25x; throughput 2.0 -> 3.5 units/hr.",
        "Hard filter: DSCR >= 1.25x, LTV <= 40%; LTV ceiling 40%; cap rate 7%.",
        # LTV anchor present but a comma separates an unrelated exit-cap max -> window stops.
        "Governor: max LTV 40%, max 8% exit cap.",
        # connective (not a delimiter) joins the canonical ceiling to another metric: the FIRST
        # percent after the anchor is canonical 40%, so the later figure is left alone.
        "Hard filter: max LTV 40% and 25% minimum basis discount per acquisition.",
        "Governor: LTV ceiling 40% with 8% minimum yield on cost.",
        # I-3 window widened to 40 chars but stops at a clause break, so a following clause's
        # percent is not swept in even without a canonical LTV % right after the anchor.
        "Governor: LTV ceiling per policy; exit cap max 8%, basis discount 25%.",
        "Hard filter: max LTV (see appendix B for the 25% basis-discount schedule).",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "incidental figure not bound to a threshold construct must not flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_incidental_figures_not_flagged_unit")


def test_scan_code_canonical_clean_unit():
    """Code-aware path (2026-06-14): the real capital-config ENFORCEMENT CONSTANTS are clean, and
    the `dscrFloor > 3` sanity ceiling no longer reads as a 3.0 DSCR threshold (the FP class is gone
    because code is routed to scan_code, not the prose scan_line). Numeric equality: 0.4 == 0.40."""
    m = _load_probe_module()
    code = "\n".join([
        "export const CAPITAL_CONFIG = {",        # the real seed object (CAPITAL_CONFIG)
        "  dscrFloor: 1.25,",
        "  ltvCeiling: 0.40,",
        "} as const;",
        "  dscrFloor: number;",                    # interface type annotation -- must NOT flag
        "  if (next.dscrFloor < 1.25) { throw new Error('capital-config: DSCR floor below 1.25 -- refused'); }",
        "  if (next.ltvCeiling > 0.40) { throw new Error('capital-config: LTV ceiling above 0.40 -- refused'); }",
        "  if (next.dscrFloor > 3) { throw new Error('exceeds sane ceiling 3.0 -- likely a fat-finger'); }",
        "    dscrFloor: update.dscrFloor ?? current.dscrFloor,",  # expression RHS -- must NOT flag
    ])
    assert m.scan_code(code) == [], "canonical seed + guard + sanity ceiling must be clean; got %r" % m.scan_code(code)
    assert m.scan_code("if (next.ltvCeiling > 0.4) {}") == [], "0.4 must equal 0.40 (no drift)"
    assert m.scan_code("if (next.dscrFloor < 1.250) {}") == [], "1.250 must equal 1.25 (no drift)"
    assert m.scan_code("  ltvCeiling: .40,") == [], "leading-dot .40 must equal 0.40 (no drift)"
    print("  PASS test_scan_code_canonical_clean_unit")


def test_scan_code_constant_drift_flags_unit():
    """Closes the latent FALSE NEGATIVE: a drifted enforcement CONSTANT flags even if no prose /
    error-string changes (the old probe only validated the message)."""
    m = _load_probe_module()
    assert any("DSCR" in r for _, r, _ in m.scan_code("if (next.dscrFloor < 1.10) {}")), \
        "drifted DSCR floor 1.10 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("if (next.ltvCeiling > 0.50) {}")), \
        "drifted LTV ceiling 0.50 must flag"
    print("  PASS test_scan_code_constant_drift_flags_unit")


def test_scan_code_direction_and_inversion_flags_unit():
    """Operator flips and inverted guards are SEMANTIC drift -- must flag; the legit `> 3` sanity
    ceiling must NOT be mistaken for an inverted floor."""
    m = _load_probe_module()
    assert m.scan_code("if (next.dscrFloor <= 1.25) {}"), "dscr '<=' direction drift must flag"
    assert m.scan_code("if (next.ltvCeiling >= 0.40) {}"), "ltv '>=' direction drift must flag"
    assert m.scan_code("if (next.dscrFloor > 1.25) {}"), "inverted dscr floor (>1.25) must flag"
    assert m.scan_code("if (next.ltvCeiling < 0.40) {}"), "inverted ltv ceiling (<0.40) must flag"
    assert m.scan_code("if (next.dscrFloor > 3) {}") == [], "sanity ceiling > 3 must stay clean"
    print("  PASS test_scan_code_direction_and_inversion_flags_unit")


_POSITIVITY_CANON = "\n".join([
    "  if (next.dscrFloor < 1.25) { throw new Error('DSCR floor below hard invariant'); }",
    "  if (next.ltvCeiling > 0.40) { throw new Error('LTV ceiling above hard invariant'); }",
])
_DSCR_POS = "  if (!(Number.isFinite(next.dscrFloor) && next.dscrFloor > 0)) { throw new Error('must be > 0'); }"
_LTV_POS = "  if (!(Number.isFinite(next.ltvCeiling) && next.ltvCeiling > 0)) { throw new Error('must be > 0'); }"


def test_scan_code_positivity_guard_clean_when_canonical_guard_present_unit():
    """capital-config.ts carries fail-closed `> 0` positivity guards beside the real floor/ceiling
    guards (a zero ceiling would turn the DSCR proxy into Infinity). Those are NOT a relaxed floor:
    the real guards are still present. Regression for the 2026-09-30 pre-push block."""
    m = _load_probe_module()
    code = "\n".join([_POSITIVITY_CANON, _LTV_POS, _DSCR_POS])
    assert m.scan_code(code) == [], "positivity guards beside canonical guards must be clean; got %r" % m.scan_code(code)
    print("  PASS test_scan_code_positivity_guard_clean_when_canonical_guard_present_unit")


def test_scan_code_positivity_guard_flags_when_canonical_guard_missing_unit():
    """The exemption is conditional: if the REAL guard is gone (replaced by a `> 0` check, or
    deleted), the `> 0` line must flag again -- otherwise the exemption would hide exactly the
    drift this probe exists to catch."""
    m = _load_probe_module()
    assert any("DSCR" in r for _, r, _ in m.scan_code(_DSCR_POS)), "lone dscr `> 0` must still flag"
    assert any("LTV" in r for _, r, _ in m.scan_code(_LTV_POS)), "lone ltv `> 0` must still flag"
    dscr_canon_only = "  if (next.dscrFloor < 1.25) { throw new Error('x'); }"
    assert any("LTV" in r for _, r, _ in m.scan_code("\n".join([dscr_canon_only, _LTV_POS]))), \
        "ltv `> 0` must flag when only the DSCR canonical guard is present"
    ltv_canon_only = "  if (next.ltvCeiling > 0.40) { throw new Error('x'); }"
    assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join([ltv_canon_only, _DSCR_POS]))), \
        "dscr `> 0` must flag when only the LTV canonical guard is present"
    commented = "\n".join(["  // if (next.dscrFloor < 1.25) { throw new Error('x'); }", _DSCR_POS])
    assert any("DSCR" in r for _, r, _ in m.scan_code(commented)), \
        "a COMMENTED-OUT canonical guard must not license the `> 0` exemption"
    print("  PASS test_scan_code_positivity_guard_flags_when_canonical_guard_missing_unit")


_RATIFIED_CANON = "\n".join([
    "  if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor) { throw new Error('below'); }",
    "  if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling) { throw new Error('above'); }",
])


def test_scan_code_ratified_variable_guard_licenses_positivity_exemption_unit():
    """Since oxford-command-center PR 386 the real guards compare against RATIFIED_GOVERNORS, not a
    literal. That variable form must license the `> 0` exemption (this is the real capital-config
    shape), and a commented-out or flipped variable guard must not."""
    m = _load_probe_module()
    real_shape = "\n".join([_RATIFIED_CANON, _LTV_POS, _DSCR_POS])
    assert m.scan_code(real_shape) == [], "real capital-config shape must be clean; got %r" % m.scan_code(real_shape)
    commented = "\n".join(["  // if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor) {}", _DSCR_POS])
    assert any("DSCR" in r for _, r, _ in m.scan_code(commented)), "commented variable guard must not license"
    flipped = "\n".join(["  if (next.dscrFloor > RATIFIED_GOVERNORS.dscrFloor) {}", _DSCR_POS])
    assert any("DSCR" in r for _, r, _ in m.scan_code(flipped)), "flipped variable guard must not license"
    ltv_flipped = "\n".join(["  if (next.ltvCeiling < RATIFIED_GOVERNORS.ltvCeiling) {}", _LTV_POS])
    assert any("LTV" in r for _, r, _ in m.scan_code(ltv_flipped)), "flipped ltv variable guard must not license"
    # Evasions found in the 2026-09-30 adversarial review: each keeps the `> 0` line and neuters the
    # real guard while it still textually resembles one. All must flag (fail closed).
    neutered = [
        "  /* if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor) {} */",
        "  const s = 'if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor)';",
        "  if (prev.dscrFloor < RATIFIED_GOVERNORS.dscrFloor) {}",
        "  if (false && next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor) {}",
        "  if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor && !OVERRIDE) {}",
        "  if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor - 0.15) {}",
    ]
    for guard in neutered:
        assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join([guard, _DSCR_POS]))), \
            "neutered dscr guard must not license the exemption: %r" % guard
    # Second-pass review evasions: tokenizer desync cases. The guard text appears only inside a
    # literal/comment (or mid-line), never as a whole line outside them.
    G = "if (next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor)"
    desync = [
        "  const a = '/*'; const b = \"*/ " + G + " \";",           # fake comment opener inside a string
        "  const t = `${\"`\"} " + G + " `;",                          # backtick nested in a template
        "  const r = /'/; // ' " + G,                                # quote inside a regex literal
        "  /* never closed\n  " + G + " {}",                         # unterminated block comment
        "  const s = 'x'; " + G + " {}",                             # guard mid-line, not at line start
    ]
    for guard in desync:
        assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join([guard, _DSCR_POS]))), \
            "desync/mid-line guard must not license the exemption: %r" % guard
    ltv_desync = [
        "  const t = `${\"`\"} if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling) `;",
        "  const r = /'/; // ' if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling)",
    ]
    for guard in ltv_desync:
        assert any("LTV" in r for _, r, _ in m.scan_code("\n".join([guard, _LTV_POS]))), \
            "ltv desync guard must not license the exemption: %r" % guard
    # Third-pass review evasions: the guard on its OWN line inside a multi-line template whose `${...}`
    # holds a backtick, so the tokenizer closes the template early. Must flag; plain `${ident}` must not.
    tmpl_inner = ["\"`\"", "'`'", "/`/.source", "/*`*/0"]
    for inner in tmpl_inner:
        body = "  const t = `${" + inner + "}\n  " + G + " { throw new Error('x'); }\n  `;"
        assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join([body, _DSCR_POS]))), \
            "multi-line template with complex ${%s} must not license the dscr exemption" % inner
        ltv_body = ("  const t = `${" + inner + "}\n  if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling) { }\n  `;")
        assert any("LTV" in r for _, r, _ in m.scan_code("\n".join([ltv_body, _LTV_POS]))), \
            "multi-line template with complex ${%s} must not license the ltv exemption" % inner
    # Fourth-pass review: a regex literal holding a backtick opens a fake template that closes on the
    # REAL template's opening backtick, exposing the template body as live code. The unbalanced form
    # leaves a backtick after tokenizing and must flag. (A deliberately balanced form is an accepted,
    # documented residual.)
    regex_desync = "\n".join([
        "  const r = /`/;",
        "  const doc = `",
        "  " + G + " { throw new Error('x'); }",
        "  `;",
    ])
    assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join([regex_desync, _DSCR_POS]))), \
        "unbalanced regex-literal desync must fail closed"
    # Performance: `${` with no closing brace was quadratic (29s at 160KB) -- must be linear now.
    import time as _t
    adversarial = "${" * 200_000  # 400KB
    t0 = _t.time()
    m.scan_code("\n".join([_DSCR_POS, adversarial]))
    elapsed = _t.time() - t0
    assert elapsed < 3.0, "scan_code on 400KB of unterminated `${` took %.1fs (quadratic regression?)" % elapsed
    # Fifth-pass review: unclosed quotes/backticks made the tokenizer quadratic (~2.4s at 32KB).
    for unclosed in ("'\\\"" * 40_000, "\"`\\\"" * 40_000, "`\\\"" * 40_000):  # ~100-120KB each
        t0 = _t.time()
        m.scan_code("\n".join([_DSCR_POS, unclosed]))
        assert _t.time() - t0 < 3.0, "tokenizer quadratic on unclosed literals (%d chars)" % len(unclosed)
    # An unterminated literal swallows a following line-start guard, so it must not license either.
    assert any("DSCR" in r for _, r, _ in m.scan_code("\n".join(["  const s = 'never closed", "  " + G + " {}", _DSCR_POS]))), \
        "a guard swallowed by an unterminated literal must not license the exemption"
    simple_tmpl = "  throw new Error(`DSCR floor ${next.dscrFloor} below ${RATIFIED_GOVERNORS.dscrFloor}`);"
    assert m.scan_code("\n".join([_RATIFIED_CANON, simple_tmpl, _LTV_POS, _DSCR_POS])) == [], \
        "plain identifier interpolation must not disable the exemption (real capital-config shape)"
    ltv_neutered = [
        "  /* if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling) {} */",
        "  if (next.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling + 0.25) {}",
        "  if (prev.ltvCeiling > RATIFIED_GOVERNORS.ltvCeiling) {}",
    ]
    for guard in ltv_neutered:
        assert any("LTV" in r for _, r, _ in m.scan_code("\n".join([guard, _LTV_POS]))), \
            "neutered ltv guard must not license the exemption: %r" % guard
    print("  PASS test_scan_code_ratified_variable_guard_licenses_positivity_exemption_unit")


def test_governor_constants_file_is_routed_to_scan_code_unit():
    """PR 386 moved the ratified literals into governor-constants.ts. It must be in the routed set,
    and a weakened literal there must flag while the canonical pair stays clean."""
    m = _load_probe_module()
    assert "governor-constants.ts" in m.GOVERNOR_CODE_FILES, "governor-constants.ts must be routed to scan_code"
    assert "capital-config.ts" in m.GOVERNOR_CODE_FILES, "capital-config.ts must remain routed"
    canon = "export const RATIFIED_GOVERNORS = {\n  dscrFloor: 1.25,\n  ltvCeiling: 0.40,\n} as const;"
    assert m.scan_code(canon) == [], "canonical governor-constants literals must be clean"
    assert any("DSCR" in r for _, r, _ in m.scan_code(canon.replace("1.25", "1.10"))), "weakened dscr literal must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code(canon.replace("0.40", "0.65"))), "weakened ltv literal must flag"
    print("  PASS test_governor_constants_file_is_routed_to_scan_code_unit")


def test_scan_code_positivity_guard_exemption_is_strictly_greater_than_zero_unit():
    """Only `> 0` is exempt, and only with its canonical guard present. `>= 0`, `> 0.5` and a
    drifted canonical constant stay flagged even when canonical guards exist elsewhere."""
    m = _load_probe_module()
    base = _POSITIVITY_CANON
    assert m.scan_code("\n".join([base, "  if (next.dscrFloor >= 0) {}"])), "dscr `>= 0` must flag"
    assert m.scan_code("\n".join([base, "  if (next.ltvCeiling >= 0) {}"])), "ltv `>= 0` must flag"
    assert m.scan_code("\n".join([base, "  if (next.dscrFloor > 0.5) {}"])), "dscr `> 0.5` must flag"
    assert m.scan_code("\n".join([base, "  if (next.ltvCeiling > 0.50) {}"])), "ltv `> 0.50` must flag"
    assert m.scan_code("\n".join(["  if (next.dscrFloor < 1.10) {}", _DSCR_POS])), \
        "a drifted dscr canonical (1.10) must not license the `> 0` exemption"
    print("  PASS test_scan_code_positivity_guard_exemption_is_strictly_greater_than_zero_unit")


def test_scan_code_ignores_deal_values_unit():
    """scan_code keys ONLY on the enforcement identifiers (dscrFloor / ltvCeiling), so per-deal
    dscr/ltv VALUES -- the latent JSON-sentinel FP (a deal at exactly 1.75) -- never flag."""
    m = _load_probe_module()
    assert m.scan_code('{ "dscr": 1.75, "ltv": 0.54 }') == [], "json deal values must not flag"
    assert m.scan_code("const dscr = 1.10; const ltv = 0.65;") == [], "local deal vars must not flag"
    print("  PASS test_scan_code_ignores_deal_values_unit")


def test_scan_code_seed_literal_drift_flags_unit():
    """BLOCKER fix (adversarial review 2026-06-14): the ratified SEED literal in CAPITAL_CONFIG --
    `dscrFloor: 1.25,` / `ltvCeiling: 0.40,` -- IS the live governor value (a one-char edit there
    weakens the governor). The comparison-only check missed it; the seed (colon) check must flag it.
    Leading-dot form too. NOTE: scan_code flags conditions.ts's legit `dscrFloor: 1.1,` BY DESIGN --
    the FP is avoided by main() ROUTING scan_code ONLY to the governor file, verified by the E2E."""
    m = _load_probe_module()
    assert any("DSCR" in r for _, r, _ in m.scan_code("  dscrFloor: 1.00,")), "seed DSCR 1.00 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("  ltvCeiling: 0.75,")), "seed LTV 0.75 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("  ltvCeiling: .65,")), "leading-dot seed .65 must flag"
    # proof the check is LIVE (so the E2E green => routing, not a dead check, protects conditions.ts):
    assert m.scan_code("  dscrFloor: 1.1,"), "scan_code must flag a non-canonical seed (live check)"
    print("  PASS test_scan_code_seed_literal_drift_flags_unit")


def test_scan_code_presence_regexes_unit():
    """Deletion guard (main): the presence regexes match a NUMERIC governor declaration (seed OR
    guard) but NOT the bare interface type annotation -- so deleting the value while keeping the
    type does not mask the deletion."""
    m = _load_probe_module()
    assert m.RE_CODE_DSCR_ANY.search("  dscrFloor: 1.25,"), "seed satisfies presence"
    assert m.RE_CODE_DSCR_ANY.search("if (next.dscrFloor < 1.25) {"), "guard satisfies presence"
    assert not m.RE_CODE_DSCR_ANY.search("  dscrFloor: number;"), "type annotation must NOT satisfy presence"
    assert m.RE_CODE_LTV_ANY.search("  ltvCeiling: 0.40,"), "ltv seed satisfies presence"
    assert not m.RE_CODE_LTV_ANY.search("  ltvCeiling: number;"), "ltv type annotation must NOT satisfy presence"
    print("  PASS test_scan_code_presence_regexes_unit")


def test_reverse_order_dscr_floor_flags_unit():
    """Reverse-order gap (2026-07-08): a governor DSCR floor written NUMBER-then-keyword
    ("This 1.40x floor is the acquisition governor") carries no literal 'dscr' AND puts the keyword
    AFTER the value, so RE_DSCR_THRESH (dscr-anchored) and RE_DSCR_DECL (keyword-before-number) both
    miss it. Pre-fix this returned [] (a real false negative); RE_DSCR_DECL_REV closes it. The
    trailing x/× stays REQUIRED, so a rent/height decimal that merely precedes a keyword never trips."""
    m = _load_probe_module()
    out = m.scan_line("This 1.40x floor is the acquisition governor for every deal.")
    assert any("1.40" in o for o in out), (
        "reverse-order DSCR floor 1.40x must flag; got %r" % out)
    for line in ["Hard acquisition governor: the 1.10x minimum stands.",
                 "Governor: 1.15x floor, non-negotiable.",
                 "Acquisition screen: a 1.40X ceiling applies."]:   # uppercase X too (re.I)
        out2 = m.scan_line(line)
        assert any(("1.10" in o) or ("1.15" in o) or ("1.40" in o) for o in out2), (
            "reverse-order DSCR drift must flag; line=%r got=%r" % (line, out2))
    # canonical reverse form stays CLEAN (no over-match):
    assert m.scan_line("This 1.25x floor is the acquisition governor.") == [], \
        "canonical reverse 1.25x floor must not flag"
    print("  PASS test_reverse_order_dscr_floor_flags_unit")


def test_reverse_order_ltv_ceiling_flags_unit():
    """Reverse-order LTV gap: "65% ceiling"/"65% maximum" NUMBER-then-keyword with NO literal 'ltv'
    on the line (so the ltv-gated LTV branch never ran). RE_LTV_CEIL_REV closes it on
    governor-declaration lines. Word set is {ceiling, maximum} only."""
    m = _load_probe_module()
    for line in ["This 65% ceiling is the acquisition governor.",
                 "Hard filter: a 65% maximum applies to every deal.",
                 "Acquisition screen: 55% ceiling, non-negotiable."]:
        out = m.scan_line(line)
        assert any(("65" in o) or ("55" in o) for o in out), (
            "reverse-order LTV ceiling drift must flag; line=%r got=%r" % (line, out))
    # canonical reverse form stays CLEAN.
    assert m.scan_line("Governor: 40% ceiling on every deal.") == [], \
        "canonical reverse 40% ceiling must not flag"
    print("  PASS test_reverse_order_ltv_ceiling_flags_unit")


def test_reverse_order_no_false_positive_unit():
    """The reverse-order path must NOT flag stray numbers with no governor meaning: a bare count, a
    physical ceiling, a rent/height decimal preceding a keyword (no abutting x), and non-LTV percents
    abutting bare 'max' (deliberately excluded from the LTV reverse set). This is the false-positive
    class the fix must avoid (precision over recall)."""
    m = _load_probe_module()
    clean = [
        "40 tenants across the portfolio pay on time.",       # bare count -- no % / x
        "The ceiling is 12 feet in the warehouse.",           # physical ceiling -- no % / x, not is_gov
        "Governor: DSCR floor 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.",  # no abutting x
        "Hard filter: DSCR >= 1.25x, LTV <= 40%; vacancy 15% max, exit cap 8% max.",  # bare 'max' excluded
        "Acquisition governor: DSCR >= 1.25x, LTV <= 40% (portfolio 1.42x avg, 28% actual).",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "reverse-order path must not false-positive; line=%r got=%r" % (line, m.scan_line(line)))
    print("  PASS test_reverse_order_no_false_positive_unit")


def test_reverse_order_suppression_still_applies_unit():
    """The reverse-order DSCR path honors the SAME suppressors as the forward passes: a portfolio-
    level "1.75x floor" (the ratified blended target, a distinct metric) stays suppressed, while a
    per-deal / acquisition-governor marker VETOES suppression so a real per-deal drift still flags."""
    m = _load_probe_module()
    assert m.scan_line("Portfolio-wide governor: the 1.75x floor is the blended target.") == [], \
        "portfolio-wide reverse 1.75x floor must be suppressed"
    out = m.scan_line("Per-deal acquisition governor: the 1.75x floor now applies.")
    assert any("1.75" in o for o in out), (
        "per-deal reverse 1.75x floor must still flag (veto); got %r" % out)
    print("  PASS test_reverse_order_suppression_still_applies_unit")


def test_reverse_order_refi_suppression_unit():
    """The reverse-order LTV path honors the post-close-refi suppressor: a refi debt-sizing
    "65% maximum" (no acquisition-governor marker, value not declared AS the governor) is suppressed;
    an acquisition-governor marker on the line vetoes suppression so a real drift still flags."""
    m = _load_probe_module()
    suppressed = "Self-imposed refi debt post-close sizing: a 65% maximum against stabilized exit value."
    assert m.scan_line(suppressed) == [], (
        "post-close-refi reverse 65%% maximum must be suppressed; got %r" % m.scan_line(suppressed))
    vetoed = "Refi post-close note, yet the acquisition governor is now a 65% maximum."
    assert any("65" in o for o in m.scan_line(vetoed)), (
        "acq-governor marker must veto refi suppression on the reverse path; got %r" % m.scan_line(vetoed))
    print("  PASS test_reverse_order_refi_suppression_unit")


def test_version_token_not_a_dscr_threshold_unit():
    """2026-07-11 FP fix (root cause 1): a VERSION token ("v3.8") abutting the digits is NOT a DSCR
    threshold -- a real threshold is never written letter-abutted ("floor 1.10", never "v1.10" /
    "spec3.8"). The letter-lookbehind must kill the version-token read WITHOUT weakening detection:
    a real drifted floor sharing a line with a version token must still flag."""
    m = _load_probe_module()
    # the real SKILL.md:50 shape -- v3.8 read as "DSCR 3.8x" (the false positive):
    clean = [
        "- **DSCR floor (per-property governor — v3.8; reported on every UNDERWRITE, not just "
        "at refi sizing):** post-refi DSCR must be ≥1.25x at the market-rate refi terms.",
        "Governor spec v3.8: DSCR floor unchanged at 1.25x.",
        "Hard filter (v2.7): DSCR >= 1.25x on every deal.",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "version token must not read as a DSCR threshold; line=%r got=%r"
            % (line, m.scan_line(line)))
    # REFUTE guard: real drift NEAR a version token still flags.
    out1 = m.scan_line("Hard filter: DSCR floor 1.10x (spec v3.8).")
    assert any("1.10" in o for o in out1), (
        "real 1.10 drift beside a version token must flag; got %r" % out1)
    assert not any("3.8" in o for o in out1), (
        "the v3.8 version token must never flag; got %r" % out1)
    out2 = m.scan_line("Governor v3.8: DSCR floor 1.10.")
    assert any("1.10" in o for o in out2), (
        "x-less 1.10 drift after a version token must flag; got %r" % out2)
    print("  PASS test_version_token_not_a_dscr_threshold_unit")


def test_approximate_tilde_value_not_a_dscr_threshold_unit():
    """2026-08-21 FP fix (ora-skills deal-comparison/SKILL.md:153): a CHANGELOG entry narrating a
    past bug's symptom ("inflating computed DSCR ~1.6x") read as a live DSCR governor declaration
    and blocked the pre-push hook-tests gate.

    Two REFUTE-caught gaps shaped this into its final, span-scoped, THREE-signal design (all
    required together: tilde-glued value + literal "corrected" + a separate plain-1.25 restatement):
      1) A blanket lookbehind (suppress every tilde-glued value, unconditionally) was rejected --
         it would also hide a REAL drift report written the same way ("dscr floor ~1.10x" with no
         companion canonical restatement).
      2) A looser two-signal gate (tilde value + a bare 1.25 ANYWHERE on the line, no "corrected"
         requirement) was ALSO rejected -- "the acquisition dscr floor reads ~1.10x in three files
         -- needs reverting to 1.25x" is an UNRESOLVED drift report that mentions 1.25 without ever
         saying the fix happened, and would have been wrongly suppressed. Requiring "corrected" (the
         same completed-action anchor RE_DSCR_CORRECTION already uses) closes that gap."""
    m = _load_probe_module()
    # the real deal-comparison/SKILL.md:153 shape (trimmed to the relevant clause) -- must be clean:
    assert m.scan_line(
        "(1) DSCR was tested at 40% LTV — the portfolio-aggregate governor, not per-property refi "
        "sizing — inflating computed DSCR ~1.6x and letting deals that would floor-flag in "
        "acquisition-underwriting score clean here; corrected to the LESSER-of-65%-LTV/1.25x-DSCR "
        "basis."
    ) == [], "the real changelog shape must not read as a DSCR threshold"
    # a shorter changelog shape carrying all three required signals -- also clean:
    assert m.scan_line(
        "Symptom under the old code: DSCR read ~1.10, well above the real floor; corrected to the "
        "canonical 1.25x DSCR floor."
    ) == [], "a corrected changelog note with all three signals must not flag"

    # REFUTE gap 1 (closed): unconditional tilde suppression must NOT hide a bare, unresolved report.
    out_bare = m.scan_line("dscr floor ~1.10x now -- must fix.")
    assert any("1.10" in o for o in out_bare), (
        "a bare tilde value with no companion evidence must still flag; got %r" % out_bare)

    # REFUTE gap 2 (closed): tilde + bare 1.25 with NO "corrected" is still an unresolved report,
    # not a changelog note -- must flag, not be suppressed.
    out_unresolved = m.scan_line(
        "the acquisition dscr floor reads ~1.10x in three files -- needs reverting to 1.25x.")
    assert any("1.10" in o for o in out_unresolved), (
        "an unresolved drift report mentioning 1.25 without 'corrected' must still flag; got %r"
        % out_unresolved)

    # Sanity: a genuinely off-canonical value elsewhere on the line, sharing a line with a
    # "corrected"+tilde note but on its OWN un-hedged "dscr" occurrence, is untouched by the
    # tilde suppressor (which is span-scoped to the tilde-glued value only) and still flags.
    out_guard = m.scan_line(
        "Changelog: old code read DSCR ~1.6x; corrected to 1.25x. Unrelated: DSCR floor 1.10x.")
    assert any("1.10" in o for o in out_guard), (
        "a real drift on its own un-hedged dscr occurrence must still flag; got %r" % out_guard)
    assert not any("1.6" in o for o in out_guard), (
        "the ~1.6x changelog figure, with 'corrected'+1.25 present, must not flag; got %r"
        % out_guard)
    print("  PASS test_approximate_tilde_value_not_a_dscr_threshold_unit")


def test_tilde_hedge_canon_plain_rejects_version_and_percent_tokens_unit():
    """Qodo PR #145 review finding (HIGH): RE_DSCR_CANON_PLAIN's original lookbehind/lookahead
    ((?<![~0-9.]) ... (?![0-9])) did not exclude a version token ('v1.25') or a percent-suffixed
    figure ('1.25%') -- mirroring gaps RE_DSCR_THRESH's own (?<![vV]) and (?!%) guards already
    closed for the primary DSCR extractor, but missing here. Either could hand a tilde-hedged
    DRIFT value a false 'plain canonical 1.25 restatement' companion and wrongly suppress it."""
    m = _load_probe_module()
    out_version = m.scan_line("dscr floor ~1.10x corrected in v1.25 of the script.")
    assert any("1.10" in o for o in out_version), (
        "a 'v1.25' version token must not satisfy the plain-1.25 companion signal; got %r"
        % out_version)
    out_percent = m.scan_line("dscr floor ~1.10x corrected; now at 1.25% of par.")
    assert any("1.10" in o for o in out_percent), (
        "a '1.25%' percent figure must not satisfy the plain-1.25 companion signal; got %r"
        % out_percent)
    # sanity: the genuine plain-1.25 shape (no version/percent decoration) is unaffected.
    out_genuine = m.scan_line("dscr floor ~1.10x corrected; canonical is 1.25x.")
    assert out_genuine == [], (
        "a genuine plain-1.25 restatement must still license suppression; got %r" % out_genuine)
    print("  PASS test_tilde_hedge_canon_plain_rejects_version_and_percent_tokens_unit")


def test_tilde_hedge_corrected_word_boundary_and_directional_unit():
    """ROUND-1 INDEPENDENT REVIEW (2026-08-22): the first cut of the tilde-hedge suppressor
    gated on `"corrected" in low` -- a bare, whole-line, non-directional substring test. Two
    real false negatives followed, both on a Hard-Invariant-4 guard whose stated bias is
    detection over silence:
      1) "un**corrected**" contains the substring "corrected", so a drift report that
         literally says it is NOT fixed was wrongly suppressed.
      2) The gate had no directionality or per-span binding: an unrelated "corrected" earlier
         on the line (describing a DIFFERENT fix), or "corrected" preceding the tilde value
         itself (the NEW/bad figure being hedged, not the old one), or a second still-broken
         tilde value sharing a line with one genuinely-fixed value, could all ride an
         unrelated "corrected" token into silent suppression.
    Fixed by requiring the WORD-BOUNDARY token "corrected" to appear AFTER each tilde value
    individually, within a bounded reach (_tilde_hedge_suppressed_spans)."""
    m = _load_probe_module()
    # gap 1: "uncorrected" must not satisfy the completed-action anchor.
    out1 = m.scan_line(
        "dscr floor still reads ~1.10x across three skills, uncorrected; canonical is 1.25x.")
    assert any("1.10" in o for o in out1), (
        "an explicitly UNcorrected drift report must still flag; got %r" % out1)
    # gap 2a: "corrected to ~1.40x" -- the hedged value IS the new/bad figure, not a symptom
    # of an already-fixed one. "corrected" precedes it, so directionality must not suppress it.
    out2a = m.scan_line("dscr floor corrected to ~1.40x, was 1.25x previously.")
    assert any("1.40" in o for o in out2a), (
        "a tilde-hedged value that is ITSELF the new drift (corrected TO it) must still flag; "
        "got %r" % out2a)
    # gap 2b: an unrelated, earlier "corrected" (fixing something else entirely) must not arm
    # suppression for a DSCR drift later on the same line.
    out2b = m.scan_line(
        "audit: the ltv typo was corrected to 40%; separately the dscr floor now reads ~1.10x "
        "vs the canonical 1.25x -- still open.")
    assert any("1.10" in o for o in out2b), (
        "an unrelated earlier 'corrected' must not mask a real drift later on the line; got %r"
        % out2b)
    # gap 2c: two tilde values on one line, only the FIRST genuinely followed by "corrected" --
    # the second, still-unfixed value must not inherit the first's suppression.
    out2c = m.scan_line(
        "changelog: symptom dscr ~1.6x corrected to 1.25x; note the live floor also reads "
        "~1.40x dscr minimum, unfixed.")
    assert not any("1.6" in o for o in out2c), (
        "the genuinely-corrected ~1.6x symptom must stay suppressed; got %r" % out2c)
    assert any("1.40" in o for o in out2c), (
        "a second, still-unfixed tilde value sharing the line must still flag; got %r" % out2c)
    print("  PASS test_tilde_hedge_corrected_word_boundary_and_directional_unit")


def test_deal_comparison_skill_file_clean():
    """The live deal-comparison SKILL.md (repo copy) must scan CLEAN line-by-line -- the 2026-08-21
    false positive at line 153 (a v1.2 Changelog entry narrating the DSCR-wrong-LTV bug fix, see
    test_approximate_tilde_value_not_a_dscr_threshold_unit)."""
    if _skip_unless_live("test_deal_comparison_skill_file_clean"):
        return
    m = _load_probe_module()
    # Qodo PR #145 review finding (portability): use the probe's own canonical ora-skills root
    # (HOME/ora-skills) rather than a hardcoded Windows path, so this stays correct on a
    # different user/OS. (Pre-existing test_acquisition_underwriting_skill_file_clean uses the
    # older hardcoded form -- unrelated to this PR's diff, left as-is.)
    path = os.path.join(m.ORA_SKILLS_REPO, "deal-comparison", "SKILL.md")
    assert os.path.isfile(path), "skill file not found: %s" % path
    findings = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, raw in enumerate(fh, 1):
            for reason in m.scan_line(raw):
                findings.append((i, reason))
    assert findings == [], (
        "deal-comparison SKILL.md must be clean; got %r" % findings)
    print("  PASS test_deal_comparison_skill_file_clean (0 findings)")


def test_rate_percent_not_a_dscr_threshold_unit():
    """2026-07-11 FP fix (root cause 1b): "DSCR, 7.00% fixed" was read as "DSCR 7.0x" -- the regex
    backtracked to a PARTIAL capture ("7.0" of "7.00") to defeat the (?!\\s*%) percent guard. The
    full-number capture ((?![0-9]) after the value) must kill that, while an actual absurd DSCR
    threshold ("floor 7.0x") still flags."""
    m = _load_probe_module()
    # the real SKILL.md:281 shape:
    clean = ("7. **Debt & Capital Structure** — all-cash close + per-property refi terms "
             "(per UNDERWRITING CONVENTIONS: LESSER of 65% LTV and 1.25x DSCR, 7.00% fixed, "
             "25-yr amort, 5/10-yr term — state which of LTV/DSCR binds), and the "
             "portfolio-aggregate LTV governor check (40% ceiling, STAGE 2.3) stated explicitly.")
    assert m.scan_line(clean) == [], (
        "a percent rate after DSCR must not partial-capture as a threshold; got %r"
        % m.scan_line(clean))
    assert m.scan_line("Governor note: DSCR-linked refi rate 7.00% fixed.") == [], \
        "DSCR-adjacent 7.00%% rate must not flag"
    out = m.scan_line("Governor: DSCR floor 7.0x on every deal.")
    assert any("7.0" in o for o in out), (
        "a real (absurd) DSCR floor 7.0x must still flag; got %r" % out)
    print("  PASS test_rate_percent_not_a_dscr_threshold_unit")


def test_refi_lesser_of_construct_suppressed_unit():
    """2026-07-11 FP fix (root cause 2): a 65% sitting INSIDE the explicit ratified refi-sizing
    construct "LESSER of 65% LTV and 1.25x DSCR" is a refinance-market input, not the acquisition
    governor -- suppressed even when the line carries per-property / dscr-floor markers (which
    legitimately describe the refi rule post-v3.8). The construct's guard is the LITERAL canonical
    1.25x DSCR member: drift EITHER member and the construct no longer suppresses."""
    m = _load_probe_module()
    clean = [
        # SKILL.md:50 (also carries the v3.8 token + "dscr floor" marker):
        "- **DSCR floor (per-property governor — v3.8; reported on every UNDERWRITE, not just "
        "at refi sizing):** post-refi DSCR must be ≥1.25x at the market-rate refi terms in "
        "UNDERWRITING CONVENTIONS (LESSER of 65% LTV per-property and 1.25x DSCR).",
        # SKILL.md:260:
        "  - **LTV-governor check:** the refi LTV assumption on the Inputs tab must be validated "
        "against the stated governor (LESSER of 65% LTV per-property and 1.25x DSCR; UNDERWRITING "
        "CONVENTIONS) via a formula/flag on the Inputs or Returns tab.",
        # SKILL.md:300 (both a LESSER-of pair and a "refis running to 65% LTV"):
        "100% family capital; ~15% portfolio LTV; **Two governors, two levels:** per-property refi "
        "ceiling = LESSER of 65% LTV and 1.25x DSCR (UNDERWRITING CONVENTIONS); portfolio-aggregate "
        "ceiling = 40% LTV (Hard Invariant 4), checked per-deal at STAGE 2.3. At ~15% actual, ORA "
        "carries headroom even with individual refis running to 65% LTV.",
        # SKILL.md:112 (hyphenated/slash form + "refi to 65% LTV"):
        "**A. Portfolio-aggregate LTV governor (RATIFIED — Hard Invariant 4):** compute LTV = "
        "(aggregate debt, including this deal's post-refi debt at the LESSER-of-65%-LTV/1.25x-DSCR "
        "sizing from UNDERWRITING CONVENTIONS) ÷ (aggregate value). This governor is distinct "
        "from the per-property 65% LTV / 1.25x DSCR refi-sizing convention — a single property "
        "can refi to 65% LTV while the portfolio in aggregate stays well under 40%.",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "refi-sizing LESSER-of construct must be suppressed; line=%r got=%r" % (line[:90], out))
    # REFUTE guards -- drift either member of the construct and detection returns:
    out1 = m.scan_line("Acquisition LTV ceiling: LESSER of 65% LTV and 1.10x DSCR.")
    assert any("65" in o for o in out1), (
        "a LESSER-of pair whose DSCR member drifted off 1.25x is NOT the ratified construct; "
        "its 65%% must flag; got %r" % out1)
    out2 = m.scan_line("Governor: refi post-close sized to LESSER of 75% LTV and 1.25x DSCR.")
    # 75% inside a canonical-anchored LESSER-of span is a refi-sizing figure (drift of the refi
    # ceiling, not the acquisition governor) -- out of this probe's scope, stays suppressed.
    assert out2 == [], (
        "the refi-sizing ceiling itself is not the acquisition governor; got %r" % out2)
    print("  PASS test_refi_lesser_of_construct_suppressed_unit")


def test_refi_sizing_phrase_suppressed_unit():
    """SKILL.md:8 shapes: "65% LTV refi-sizing figure" / "65% LTV is the PER-PROPERTY refi-sizing
    ceiling" -- a percent NAMED as the refi-sizing figure is suppressed; a bare singular 'governor'
    token near the value vetoes the suppression (a value declared AS the governor must flag)."""
    m = _load_probe_module()
    line8 = ("**Clarified LTV governor scope** — an earlier draft flagged the skill's 65% LTV "
             "refi-sizing figure as conflicting with ORA's 40% LTV governor. Gabriel confirmed "
             "2026-07-11 these are two distinct, non-conflicting governors: **65% LTV is the "
             "PER-PROPERTY refi-sizing ceiling** (unchanged; correctly LESSER-of with 1.25x DSCR "
             "in UNDERWRITING CONVENTIONS), and **40% LTV is a separate PORTFOLIO-AGGREGATE "
             "ceiling** (Hard Invariant 4).")
    assert m.scan_line(line8) == [], (
        "the ratified refi-sizing scope-clarification must be suppressed; got %r" % m.scan_line(line8))
    # REFUTE guard: the same refi words cannot mask a value declared AS the governor.
    out = m.scan_line("Hard screen: the acquisition LTV governor is 65% LTV refi-sizing parity.")
    assert any("65" in o for o in out), (
        "a 65%% declared AS the governor must flag despite refi-sizing phrasing; got %r" % out)
    print("  PASS test_refi_sizing_phrase_suppressed_unit")


def test_canonical_dscr_governor_at_ltv_suppressed_unit():
    """SKILL.md:249 shape: "the 1.25x DSCR governor at 65% LTV" -- the 65% is the refi level AT
    WHICH the canonical DSCR governor applies (the 'governor' token binds to the canonical 1.25x
    DSCR on its left, not to the 65%). Suppressed. A 'governor' token NOT bound to the canonical
    DSCR phrase still vetoes (a real LTV-governor declaration flags)."""
    m = _load_probe_module()
    line249 = ("- **Madison DSCR caution:** owner-user pricing $148–$176/SF makes DSCR "
               "≥1.25x extremely difficult on most sub-$10M Class B/C assets — verify "
               "deal-level DSCR before LOI on every Madison screen. **[Unaffected by the "
               "LTV-governor scope clarification — this caution was already anchored to the "
               "1.25x DSCR governor at 65% LTV, both unchanged.]**")
    assert m.scan_line(line249) == [], (
        "the '1.25x DSCR governor at 65%% LTV' pairing must be suppressed; got %r"
        % m.scan_line(line249))
    # REFUTE guards:
    out1 = m.scan_line("The LTV governor at 65% LTV must hold on every deal.")
    assert any("65" in o for o in out1), (
        "a bare 'LTV governor at 65%%' declaration must flag; got %r" % out1)
    out2 = m.scan_line("Governor: 1.25x DSCR at 65% LTV applies at acquisition close.")
    assert any("65" in o for o in out2), (
        "'governor:' introducing the pair (not the canonical-DSCR-governor phrase) must flag; "
        "got %r" % out2)
    print("  PASS test_canonical_dscr_governor_at_ltv_suppressed_unit")


def test_bps_rate_pricing_tier_suppressed_unit():
    """SKILL.md:196 shape: "−25 bps for stabilized multi-tenant ≥1.40x DSCR" is a refi
    RATE-PRICING TIER (a bps adjustment keyed to a DSCR band), never a governor floor -- suppressed.
    The same 1.40x declared as a floor/governor elsewhere on the line still flags."""
    m = _load_probe_module()
    line196 = ("- **All-cash bid + refi post-close (per-property governor: LESSER of 65% LTV and "
               "1.25x DSCR).** **Refi debt assumptions (2026 defaults):** fixed rate **7.00%** "
               "(band 6.75–7.25% for DSCR/agency-style industrial; +25 bps for sub-$2M or "
               "single-tenant, −25 bps for stabilized multi-tenant ≥1.40x DSCR) · "
               "**25-yr amortization** · refi sized to the LESSER of **65% LTV** (stabilized "
               "value at exit cap, per-property) **and 1.25x DSCR** (the governor — never "
               "exceed). NOTE: the IRR floor and the DSCR floor (Stage 1) are the two floors "
               "computed with debt layered in.")
    assert m.scan_line(line196) == [], (
        "the bps rate-pricing tier + LESSER-of refi sizing must be suppressed; got %r"
        % m.scan_line(line196))
    # REFUTE guard: a 1.40x declared as a floor OUTSIDE the bps tier still flags on the same line.
    out = m.scan_line("Refi post-close pricing: −25 bps at ≥1.40x DSCR — and this "
                      "1.40x floor is the acquisition governor now.")
    assert any("1.40" in o for o in out), (
        "a 1.40x floor declared as the acquisition governor must flag even beside a bps tier; "
        "got %r" % out)
    # REFUTE guard (closed hole, 2026-07-11): a DECLARED floor whose 'governor' token sits ~30
    # chars before the value must not be masked by the bps-tier span (the -40 before-reach).
    out2 = m.scan_line("Governor floor -25 bps tier >=1.10x DSCR is the new per-deal minimum.")
    assert any("1.10" in o for o in out2), (
        "a governor floor phrased through a bps tier must still flag; got %r" % out2)
    print("  PASS test_bps_rate_pricing_tier_suppressed_unit")


def test_perdeal_perproperty_drift_still_flags_unit():
    """Regression (task-mandated): per-deal / per-property GOVERNOR drift must still flag -- the
    refi-construct suppressors must not extend to bare per-property declarations."""
    m = _load_probe_module()
    for line, val in [
        ("Per-deal governor: DSCR floor 1.10x.", "1.10"),
        ("Per-property DSCR floor 1.40x (governor).", "1.40"),
        ("Per-deal governor DSCR 1.75x on every acquisition.", "1.75"),
        ("Hard filter: per-property LTV ceiling 65%.", "65"),
    ]:
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "per-deal/per-property governor drift must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_perdeal_perproperty_drift_still_flags_unit")


def test_review_hole1_lesser_of_gap_drift_flags_unit():
    """REVIEW HOLE 1: a drift hidden INSIDE a LESSER-of construct's gap must flag -- the earlier
    whole-span suppressor masked it because the canonical 1.25x member still terminated the match.
    Member-scoped suppression + decimal-free gap: the gap drift breaks the match, so both the
    injected floor AND the ceiling member stay visible."""
    m = _load_probe_module()
    out1 = m.scan_line("Per-property governor: LESSER of 65% LTV and DSCR floor 1.10x / 1.25x DSCR.")
    assert any("1.10" in o for o in out1), ("HOLE1a: gap-hidden 1.10 must flag; got %r" % out1)
    assert any("65" in o for o in out1), ("HOLE1a: 65 must flag (construct broken); got %r" % out1)
    out2 = m.scan_line("LESSER of 65% LTV and the governor DSCR floor 1.10x and 1.25x DSCR.")
    assert any("1.10" in o for o in out2), ("HOLE1b: gap-hidden 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole1_lesser_of_gap_drift_flags_unit")


def test_review_hole2_bps_gap_no_leapfrog_flags_unit():
    """REVIEW HOLE 2: the bps rate-tier gap must not leapfrog a declared floor to reach the tier's
    band value -- a decimal-free gap breaks the match so the injected floor stays visible."""
    m = _load_probe_module()
    out1 = m.scan_line("Minimum DSCR schedule: -25 bps applies at DSCR floor 1.10x for >=1.40x DSCR deals.")
    assert any("1.10" in o for o in out1), ("HOLE2a: 1.10 must flag; got %r" % out1)
    out2 = m.scan_line("Hard filter note (see refi tier schedule): -25 bps DSCR floor 1.10x stabilized >=1.40x DSCR.")
    assert any("1.10" in o for o in out2), ("HOLE2b: 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole2_bps_gap_no_leapfrog_flags_unit")


def test_review_hole3_paired_gap_drift_flags_unit():
    """REVIEW HOLE 3: a no-x floor hidden in the PAIRED (1.25x DSCR ... N% LTV) gap must flag, and
    the N% member no longer masks either -- decimal-free gap breaks the match."""
    m = _load_probe_module()
    out = m.scan_line("Minimum DSCR: 1.25x DSCR floor 1.10 at 65% LTV.")
    assert any("1.10" in o for o in out), ("HOLE3: 1.10 must flag; got %r" % out)
    assert any("65" in o for o in out), ("HOLE3: 65 must flag; got %r" % out)
    print("  PASS test_review_hole3_paired_gap_drift_flags_unit")


def test_review_hole4_veto_window_and_refi_gate_flags_unit():
    """REVIEW HOLE 4: the +-40 veto window must be REAL (overlap over the whole line), and the bps
    tier must be gated on a refi token. A value declared AS the governor ~34 chars out flags; a
    bps-shaped governor-change note with NO refi context flags."""
    m = _load_probe_module()
    out1 = m.scan_line("Buy note: 65% LTV refi-sizing figure is the governor now.")
    assert any("65" in o for o in out1), ("HOLE4a: declared-governor 65 must flag; got %r" % out1)
    out2 = m.scan_line("Governor ratified change, all deals, notes: -25 bps at >=1.10x DSCR pricing.")
    assert any("1.10" in o for o in out2), ("HOLE4b: no-refi bps 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole4_veto_window_and_refi_gate_flags_unit")


def test_review_hole5_dscr_extraction_regressions_flags_unit():
    """REVIEW HOLE 5: the version-lookbehind must not silence a letter-glued drift ('changed to1.10'
    -- 'o' abuts, not a version 'v'), and the percent guard must only exclude an ABUTTING percent so
    a space-separated '1.10 %' DSCR multiple still flags. Genuine version token 'v3.8' stays clean."""
    m = _load_probe_module()
    out1 = m.scan_line("Governor DSCR floor changed to1.10 effective now.")
    assert any("1.10" in o for o in out1), ("HOLE5a: letter-glued to1.10 must flag; got %r" % out1)
    out2 = m.scan_line("Governor: minimum DSCR 1.10 %")
    assert any("1.10" in o for o in out2), ("HOLE5b: space-percent 1.10 %% must flag; got %r" % out2)
    # the genuine version token must still NOT flag (FP fix preserved):
    assert m.scan_line("Governor spec v3.8: DSCR floor unchanged at 1.25x.") == [], \
        "v3.8 version token must stay clean"
    print("  PASS test_review_hole5_dscr_extraction_regressions_flags_unit")


def test_followup1_value_dscr_keyword_order_flags_unit():
    """FOLLOW-UP 1: close the pre-existing reverse-order FN for the value->dscr->floor-word shape
    ('1.10x DSCR floor' / '1.10x DSCR minimum') -- a value, then the literal 'dscr', then a
    floor-word AFTER it. RE_DSCR_DECL_REV misses it (dscr between value and keyword) and
    RE_DSCR_THRESH misses it (dscr precedes the value). New matcher feeds the SAME suppressor
    pipeline, so canonical/portfolio/version/rent guards all still apply."""
    m = _load_probe_module()
    for line, val in [
        ("Hard filter: 1.10x DSCR minimum on every deal.", "1.10"),
        ("Acquisition governor: 1.10x DSCR floor per deal.", "1.10"),
        ("Governor screen: 1.40x DSCR ceiling applies.", "1.40"),   # uppercase-insensitive keyword
    ]:
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "value->dscr->floor-word drift must flag; line=%r got=%r" % (line, out))
    # canonical must NOT flag (canonical-skip suppressor):
    assert m.scan_line("Governor: 1.25x DSCR floor on every deal.") == [], \
        "canonical 1.25x DSCR floor must not flag"
    # portfolio-wide 1.75 must NOT flag (portfolio suppressor + 1.75 sentinel portfolio-qualified):
    assert m.scan_line("Governor: 1.75x DSCR floor (portfolio-wide) is the blended target.") == [], \
        "portfolio-wide 1.75x DSCR floor must not flag"
    # version-glued and rent/height decimals must NOT over-match:
    assert m.scan_line("Governor spec v1.10x DSCR floor note (typo).") == [], \
        "version-glued v1.10 must not flag via the new matcher"
    assert m.scan_line("Governor: DSCR >= 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.") == [], \
        "rent/height decimals must not match the value->dscr->keyword shape"
    print("  PASS test_followup1_value_dscr_keyword_order_flags_unit")


def test_followup2_refi_to_ltv_veto_tier_unit():
    """FOLLOW-UP 2: RE_REFI_TO_LTV moves to the VETO tier -- a 'refi to N% LTV' declared AS a
    ceiling/governor nearby FLAGS, while the legitimate skill refi-to lines (no governor-declaration
    nearby) stay suppressed. 'hard ceiling'/'hard cap' added as declaration tokens (the skill uses
    'aggregate ceiling'/'per-property ceiling'/'refi-sizing ceiling', never 'hard ceiling')."""
    m = _load_probe_module()
    # MUST FLAG -- value declared as a hard ceiling / governor / acquisition nearby:
    out1 = m.scan_line("Hard filter: every deal must refi to 65% LTV as the hard ceiling.")
    assert any("65" in o for o in out1), (
        "refi-to-65 declared as the hard ceiling must flag; got %r" % out1)
    out2 = m.scan_line("Governor: refi to 65% LTV is the acquisition ceiling now.")
    assert any("65" in o for o in out2), (
        "refi-to-65 declared as the acquisition ceiling must flag; got %r" % out2)
    # MUST NOT FLAG -- the :300-shaped legit refi-to (portfolio governor far, no hard-ceiling decl):
    clean = "Headroom to the portfolio governor even with individual refis running to 65% LTV."
    assert m.scan_line(clean) == [], (
        "legit refi-to-65 (no governor-declaration nearby) must stay suppressed; got %r"
        % m.scan_line(clean))
    print("  PASS test_followup2_refi_to_ltv_veto_tier_unit")


def test_round2_declaring_governor_before_value_flags_unit():
    """ROUND-2 review W1 (was an OLD-flagged -> NEW-silent regression): a real drift whose declaring
    'governor' sits ~22 chars BEFORE a refi-sizing-named member ("acquisition governor was hereby
    raised to 55% LTV refi-sizing parity") must flag. VETO_BEFORE widened 20->28 to catch it while
    staying below the tightest benign real-skill before-gap (:196 at 32). W3: an "Nx DSCR minimum"
    floor declared inside a bps rate tier is a governor statement and must flag despite the tier."""
    m = _load_probe_module()
    out1 = m.scan_line("The acquisition LTV governor was hereby raised to 55% LTV refi-sizing parity.")
    assert any("55" in o for o in out1), (
        "W1: governor-declared 55%% ~22 chars after the keyword must flag; got %r" % out1)
    out2 = m.scan_line("Refi governor floor for all deals was cut hard to -25 bps 1.10x DSCR minimum.")
    assert any("1.10" in o for o in out2), (
        "W3: an 'Nx DSCR minimum' floor inside a bps tier must flag; got %r" % out2)
    # guard the widened window's upper edge: the benign :196-style contrast mention (governor ~32
    # before a refi-sizing member) must STILL be suppressed -- proven by the full-file test, but
    # pinned here directly against the exact shape.
    benign = ("Scope note: conflicting with ORA's 40% LTV governor. Gabriel confirmed later that "
              "65% LTV is the per-property refi-sizing ceiling.")
    assert m.scan_line(benign) == [], (
        "benign 'governor. <32 chars> 65% refi-sizing' contrast must stay suppressed; got %r"
        % m.scan_line(benign))
    print("  PASS test_round2_declaring_governor_before_value_flags_unit")


def test_n6_hard_cap_ceiling_is_gov_gate_unit():
    """N6 (asymmetry from follow-up 2): 'hard cap'/'hard ceiling' were added to the VETO tokens but
    not to GOV_KEYWORDS, so a line whose ONLY governor signal is 'hard cap'/'hard ceiling' was never
    treated as a governor declaration -> nothing scanned it -> SILENT. Fix adds them to GOV_KEYWORDS.
    A drift declared solely via 'hard cap'/'hard ceiling' must now flag."""
    m = _load_probe_module()
    out1 = m.scan_line("1.25x DSCR at 65% LTV is the hard cap now.")
    assert any("65" in o for o in out1), (
        "N6: '... 65% LTV is the hard cap' must flag 65; got %r" % out1)
    out2 = m.scan_line("65% LTV is the hard ceiling.")
    assert any("65" in o for o in out2), (
        "N6: '65% LTV is the hard ceiling' must flag 65; got %r" % out2)
    out3 = m.scan_line("Every deal: DSCR floor 1.10x is our hard cap.")
    assert any("1.10" in o for o in out3), (
        "N6: a DSCR drift on a 'hard cap'-only line must flag; got %r" % out3)
    # canonical on a 'hard cap' line must stay clean (no over-match from the widened gate):
    assert m.scan_line("DSCR >= 1.25x, LTV <= 40% is our hard cap.") == [], \
        "canonical governor on a hard-cap line must not flag"
    print("  PASS test_n6_hard_cap_ceiling_is_gov_gate_unit")


def test_perprop_portfolio_aggregate_pairing_suppressed_unit():
    """RATIFIED 2026-07-11 dual-governor pairing (setup-review finding C4, 2026-07-16): the real
    acquisition-underwriting SKILL.md v4.0 line 10 closes "...governor constants (DSCR 1.25x /
    per-property LTV 65% / portfolio-aggregate LTV 40%) changed" -- documenting two distinct,
    non-conflicting governors this probe only tracks one of (the portfolio-aggregate 40%). Suppressed
    ONLY when the portfolio-aggregate companion on the same line equals the canonical 40 -- the bare
    per-property case (test_perdeal_perproperty_drift_still_flags_unit, no portfolio-aggregate
    companion at all) and a drifted companion both continue to flag in full."""
    m = _load_probe_module()
    real_line = ("No scorecard weights, Stage 1 floors, or governor constants (DSCR 1.25x / "
                 "per-property LTV 65% / portfolio-aggregate LTV 40%) changed.")
    assert m.scan_line(real_line) == [], (
        "ratified per-property/portfolio-aggregate 40%% pairing must be suppressed; got %r"
        % m.scan_line(real_line))
    # REFUTE guard 1: a drifted portfolio-aggregate companion (not 40) must still flag BOTH members --
    # the pairing is only exempt when the canonical portfolio ceiling is actually present.
    drifted = ("governor constants (DSCR 1.25x / per-property LTV 65% / "
               "portfolio-aggregate LTV 45%) changed.")
    out = m.scan_line(drifted)
    assert any("65" in o for o in out) and any("45" in o for o in out), (
        "a drifted portfolio-aggregate companion must leave both members flagged; got %r" % out)
    # REFUTE guard 2: swapping which member carries which label must not accidentally suppress a
    # real drift -- a per-property value paired with a NON-canonical "portfolio-aggregate" figure
    # elsewhere on the line is not the ratified exemption. (The line MUST carry a governor keyword:
    # without one, is_gov is False and the module's long-standing "plain prose mentions of LTV are
    # ignored" gate makes the line unflaggable for reasons unrelated to this pairing -- which would
    # make the guard vacuous rather than protective.)
    out2 = m.scan_line("Governor constants: per-property LTV 70% / portfolio-aggregate LTV 55% "
                       "-- both revised upward.")
    assert any("70" in o for o in out2) and any("55" in o for o in out2), (
        "a non-canonical portfolio-aggregate companion must not suppress the pairing; got %r" % out2)
    print("  PASS test_perprop_portfolio_aggregate_pairing_suppressed_unit")


def test_perprop_member_value_locked_to_ratified_65_unit():
    """VALUE-LOCK: a per-property member that is NOT the ratified 65 flags even when its
    portfolio-aggregate companion IS canonical 40.

    Closes the hole in companion-anchoring alone: without the value-lock, a real per-property drift
    could ride a correctly-stated canonical companion into silence. The aggregate figure is
    canonical here, so the ONLY thing that can flag this line is the per-property member itself.
    """
    m = _load_probe_module()
    for val in ("80", "55", "45", "70"):
        line = ("governor constants (DSCR 1.25x / per-property LTV %s%% / "
                "portfolio-aggregate LTV 40%%) restated." % val)
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "per-property LTV %s%% must flag despite a canonical-40 companion; got %r" % (val, out))
    print("  PASS test_perprop_member_value_locked_to_ratified_65_unit")


def test_perproperty_non_ratified_ltv_still_flags_unit():
    """ANTI-BLINDING: an unpaired per-property LTV declaration still flags at ANY value.

    This is why the fix is pairing-anchored + value-locked rather than the blanket "per-property
    veto span" the setup-audit note (C4) sketched. Instrumentation: each of these flags ONLY via the
    bare-proximity pass, so a blanket per-property span would silence a REAL per-property drift --
    the catastrophic false-negative class this module is written to avoid. C4 should not be
    implemented as written.
    """
    m = _load_probe_module()
    for line, val in (("Per-property LTV 80% is the governor now.", "80"),
                      ("Governor: per-property LTV 55% hard cap.", "55"),
                      ("Per-property LTV 70% (governor, non-negotiable).", "70"),
                      ("The per-property 45% LTV governor applies to every deal.", "45")):
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "unpaired per-property LTV %s%% must still flag; line=%r got=%r" % (val, line, out))
    # ... and the ratified 65 itself, when UNPAIRED, is still not exempt: the pairing is what
    # licenses it, not the number alone.
    out65 = m.scan_line("Hard filter: per-property LTV ceiling 65%.")
    assert any("65" in o for o in out65), (
        "unpaired per-property 65%% declared as an acquisition ceiling must flag; got %r" % out65)
    print("  PASS test_perproperty_non_ratified_ltv_still_flags_unit")


def test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit():
    """VETO tier (Refute Finding 2, 2026-07-16): a MISLABELED pairing still flags.

    The pairing suppresses "per-property LTV 65% / portfolio-aggregate LTV 40%" because 65 and 40
    are both the ratified numbers -- but if the SAME LINE declares the per-property 65 AS the
    acquisition hard ceiling/governor (a labeling error, not a numeric drift), that must still
    surface: the two-level framing is being misapplied even though neither number is wrong. Mirrors
    the veto policy every other named refi-sizing member already uses (_governor_declared_nearby).
    """
    m = _load_probe_module()
    for line in ("the acquisition hard ceiling: per-property LTV 65% / portfolio-aggregate LTV 40%",
                 "per-property LTV 65% is the governor now / portfolio-aggregate LTV 40%"):
        out = m.scan_line(line)
        assert any("65" in o for o in out), (
            "per-property 65%% declared AS the acquisition ceiling must flag despite a canonical "
            "companion; line=%r got=%r" % (line, out))
    # And the ordinary, correctly-framed pairing (no nearby ceiling/governor declaration on the
    # per-property member) must stay suppressed -- this is a VETO, not a blanket re-flag.
    assert m.scan_line("No scorecard weights or governor constants (DSCR 1.25x / per-property LTV "
                       "65% / portfolio-aggregate LTV 40%) changed.") == [], \
        "the ordinary ratified pairing must remain suppressed"
    print("  PASS test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit")


def test_dated_audit_memory_file_excluded_unit():
    """Dated audit/project memory files NARRATE findings -- they do not declare a live governor.

    The 2026-07-16 setup-audit file tripped the probe on the very line describing this false
    positive. The exemption already existed in intent but was hardcoded to one filename; it is now a
    pattern (mirroring EVENT_LOG_ARCHIVE_RE). Kept tight so live doctrine files stay in scope.
    """
    m = _load_probe_module()
    skipped = ("project_claude-setup-audit-2026-07-16.md",
               "project_claude-md-formal-audit-2026-07-08.md",
               "project_claude-setup-audit-2026-07-09.md")
    for bn in skipped:
        assert m.DATED_AUDIT_RE.match(bn), "dated audit file must be exempt: %s" % bn
    scanned = ("project_replacement_cost_benchmark_unratified.md",  # live doctrine, no date
               "standards.md", "rules.md", "firm.md", "CLAUDE.md",
               "project_oxfordra_seo_audit_2026-07.md")             # partial date -> still scanned
    for bn in scanned:
        assert not m.DATED_AUDIT_RE.match(bn), "live/doctrine file must NOT be exempt: %s" % bn
    # The exemption is FILE-scoped, not logic-level: the narrative line still trips scan_line().
    audit_line = ('- **C4 -- governor-drift probe FP** on "per-property LTV 65%" '
                  '(ratified distinct governor 2026-07-11) -> memory-integrity RED daily.')
    assert m.scan_line(audit_line), (
        "detection logic must be intact -- the audit line is excluded by FILE, not by gutting scan_line")
    print("  PASS test_dated_audit_memory_file_excluded_unit")


def test_skill_version_changelog_excluded_unit():
    """versions/CHANGELOG.md is exempt (provenance record); every neighbour stays in scope, and the
    detection logic itself is untouched (the exemption is by FILE, not by gutting scan_line)."""
    m = _load_probe_module()
    for p in (r"C:\Users\Owner\ora-skills\acquisition-underwriting\versions\CHANGELOG.md",
              "/s/acquisition-underwriting/versions/CHANGELOG-v4.30.md",
              "/s/acquisition-underwriting/versions/CHANGELOG-v3.2-v4.22.md",
              "/home/x/ora-skills/acquisition-underwriting/versions/CHANGELOG.md"):
        assert m._is_skill_version_changelog(p), p
    for p in (r"C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md",
              "/s/acquisition-underwriting/references/doctrine-rationale-and-incidents.md",
              "/s/acquisition-underwriting/CHANGELOG.md",
              "/s/versions/NOTES.md",
              "/s/versions/CHANGELOG.md.bak",
              "/s/versions/CHANGELOG-notes.md",
              "/s/acquisition-underwriting/versions/old/CHANGELOG.md",
              "/s/myversions/CHANGELOG.md"):
        assert not m._is_skill_version_changelog(p), p
    assert m.scan_line("DSCR governor floor raised to 1.40x"), (
        "detection logic must be intact")
    print("  PASS test_skill_version_changelog_excluded_unit")


def test_skill_version_changelog_wiring_hermetic_e2e():
    """Wiring guard (refute C2): drives the real main() over a temp tree. The same unhedged drift line
    is EXEMPT in versions/CHANGELOG.md (and its CHANGELOG-vN.N.md archive) but flagged in a neighbouring
    SKILL.md -- so dropping the helper from main()'s skip clause fails here regardless of live data."""
    import tempfile, contextlib, io
    m = _load_probe_module()
    line = "DSCR governor floor 1.60x\n"
    def run(rel):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, *rel.split("/"))
            os.makedirs(os.path.dirname(p))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(line)
            old = (m.build_targets, sys.argv)
            m.build_targets = lambda: [(d, (".md",))]
            sys.argv = ["governor-drift-probe.py"]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    try:
                        m.main()
                    except SystemExit as e:
                        return e.code
            finally:
                m.build_targets, sys.argv = old
    assert run("s/versions/CHANGELOG.md") == 0, "versions/CHANGELOG.md must be exempt"
    assert run("s/versions/CHANGELOG-v4.30.md") == 0, "archived changelog must be exempt"
    assert run("s/versions/CHANGELOG-v4.31-v4.37.md") == 0, "range-named archive must be exempt"
    assert run("s/SKILL.md") == 1, "same line in SKILL.md must still flag"
    assert run("s/CHANGELOG.md") == 1, "CHANGELOG.md outside versions/ must still flag"
    print("  PASS test_skill_version_changelog_wiring_hermetic_e2e")


def test_acquisition_underwriting_skill_file_clean():
    """The live acquisition-underwriting SKILL.md (repo copy) must scan CLEAN line-by-line --
    the 10 false positives of 2026-07-11 (lines 8, 50, 112, 196, 249, 260, 281, 300).
    Opt-in live test (reads the real ora-skills checkout); the shapes are pinned hermetically by
    the scan_line unit tests."""
    if _skip_unless_live("test_acquisition_underwriting_skill_file_clean"):
        return
    m = _load_probe_module()
    path = os.path.join(m.ORA_SKILLS_REPO, "acquisition-underwriting", "SKILL.md")
    assert os.path.isfile(path), "skill file not found: %s" % path
    findings = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, raw in enumerate(fh, 1):
            for reason in m.scan_line(raw):
                findings.append((i, reason))
    assert findings == [], (
        "acquisition-underwriting SKILL.md must be clean; got %r" % findings)
    print("  PASS test_acquisition_underwriting_skill_file_clean (0 findings)")


def test_test_files_excluded_from_scan_unit():
    """Pre-existing false positive (2026-07-08): the probe scanned maintenance/_tests/ fixture files
    that intentionally quote off-canonical governor values ("[GOVERNOR DRIFT] DSCR 1.20") to test
    OTHER gates -- the same class as the probe's own already-skipped test file. _is_test_file() now
    excludes the _tests/ subtree and sibling python test modules so those fixtures never read as
    live drift."""
    m = _load_probe_module()
    assert m._is_test_file(r"C:\Users\Owner\.claude\maintenance\_tests\test_git_prepush_doctrine_gate.py")
    assert m._is_test_file("/home/x/.claude/maintenance/_tests/anything.json")
    assert m._is_test_file(r"C:\Users\Owner\.claude\maintenance\test-doctrine-integrity-probe.py")
    assert m._is_test_file("/x/maintenance/test_open_sessions_probe.py")
    assert m._is_test_file("/x/foo_test.py")
    # real governor homes must NOT be treated as test files:
    assert not m._is_test_file(r"C:\Users\Owner\.claude\projects\...\memory\standards.md")
    assert not m._is_test_file("/x/.claude/CLAUDE.md")
    assert not m._is_test_file("/x/oxford-command-center/src/capital-config.ts")
    print("  PASS test_test_files_excluded_from_scan_unit")


def test_eval_harness_run_logs_excluded_from_scan_unit():
    """2026-08-24 path-class exemption: acquisition-underwriting-eval-harness/runs/*.json is
    machine-generated RESULT narration (a deal's achieved DSCR/LTV at scoring time), never a
    governor DECLARATION -- the same class as is_data_json's /data/ exemption, but these live
    under .../runs/, not /data/. The 2026-08-23 floor-result suppressor (ba831dc) already needed
    three rounds to cover two known LLM phrasings, and a THIRD phrasing
    ("DSCR floor PASSES (~1.42x at 65%-LTV-bound refi sizing)" -- no explicit "vs 1.25x floor"
    restatement for a canonical-anchored regex to lock onto) re-tripped it within 24h on
    2026-08-24T163634Z_scheduled-poll.json:204 (liberty-office-park-west-chester-oh). Regex
    whack-a-mole against unpredictable LLM narration is a losing, ever-recurring game for this
    one file class; _is_eval_harness_run_log() ends it with a path exemption instead, same
    precedent as _is_test_file(). The living governor stays declared in standards.md/rules.md/
    CLAUDE.md/skills/capital-config.ts, all still fully in scope."""
    m = _load_probe_module()
    assert m._is_eval_harness_run_log(
        r"C:\Users\Owner\ora-skills\acquisition-underwriting-eval-harness\runs\2026-08-24T163634Z_scheduled-poll.json")
    assert m._is_eval_harness_run_log(
        "/home/x/ora-skills/acquisition-underwriting-eval-harness/runs/2026-08-23T171623Z_scheduled-poll.json")
    # case-insensitive, forward-slash-normalized:
    assert m._is_eval_harness_run_log(
        "/HOME/X/ORA-SKILLS/ACQUISITION-UNDERWRITING-EVAL-HARNESS/RUNS/foo.json")
    # narrowly scoped to .../runs/ -- sibling eval-harness content stays IN scope (hand-authored,
    # could legitimately declare/discuss the governor):
    assert not m._is_eval_harness_run_log(
        "/x/ora-skills/acquisition-underwriting-eval-harness/README.md")
    assert not m._is_eval_harness_run_log(
        "/x/ora-skills/acquisition-underwriting-eval-harness/golden-deals/some-deal.json")
    # the real governor home (a DIFFERENT, similarly-named directory) must never match:
    assert not m._is_eval_harness_run_log(
        r"C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md")
    # a bare "runs" substring elsewhere must not false-match:
    assert not m._is_eval_harness_run_log("/home/x/some-other-project/test-runs/file.json")
    print("  PASS test_eval_harness_run_logs_excluded_from_scan_unit")


def test_run_probe_survives_child_utf8_smartquote_e2e():
    """Regression (2026-08-22): run_probe()'s subprocess.run(..., text=True) call had no
    explicit encoding, so it decoded the probe's stdout using locale.getpreferredencoding()
    (cp1252 on Windows). governor-drift-probe.py reconfigures ITS OWN stdout to UTF-8 (see
    its module docstring, "force UTF-8 so the probe never crashes on its own output") so it
    can safely echo scanned file content containing non-cp1252 characters -- but that just
    moves the crash one level up: a smart quote like U+201D encodes as UTF-8 bytes E2 80 9D,
    and byte 0x9D has NO cp1252 mapping at all, so the PARENT's decode crashes inside
    subprocess's internal reader thread instead (prints "Exception in thread ..." straight to
    the real stderr, not raised to the caller) and SILENTLY drops the captured stdout to None.
    git-prepush-hook-tests-gate.py then reads this test file's own (also None-corrupted, see
    the sibling regression in hooks/tests/test-git-prepush-hook-tests-gate.py) output and
    reports a confusing, contentless "fail" for a run that never actually hit real drift.
    Reproduced here by monkeypatching PROBE to a synthetic child that mimics the real probe's
    own stdout-reconfigure pattern, so the test is deterministic and doesn't depend on which
    byte happens to be live in the real scanned tree on any given day."""
    import tempfile
    global PROBE
    child_root = tempfile.mkdtemp(prefix="gdp-smartquote-child-")
    child_path = os.path.join(child_root, "emit_smartquote.py")
    with open(child_path, "w", encoding="utf-8") as fh:
        fh.write(
            "import sys\n"
            "sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
            "sys.stdout.write('GOVERNOR DRIFT DETECTED (1): right double quote "
            "\\u201d present\\n')\n"
            "sys.exit(1)\n")
    real_probe = PROBE
    PROBE = child_path
    try:
        r = run_probe(home=child_root)
    finally:
        PROBE = real_probe
        shutil.rmtree(child_root, ignore_errors=True)
    assert r.stdout is not None and "GOVERNOR DRIFT DETECTED" in r.stdout, (
        "run_probe() must capture the child's UTF-8 smart-quote output instead of "
        "silently dropping it to None; got stdout=%r" % r.stdout)
    print("  PASS test_run_probe_survives_child_utf8_smartquote_e2e")


_FLAG_LTV = "LTV governor ceiling raised to 65% per the review notes."
_FLAG_DSCR = "DSCR governor floor 1.60x per the audit note."


def _assert_flaggable(m, line):
    """A payload used to prove an EXCLUSION must itself flag when scanned, or the e2e that
    uses it proves nothing (see the round-1 review note on the active-work test)."""
    assert m.scan_line(line), "payload must be a flaggable governor declaration: %r" % line


def test_event_log_excluded_e2e():
    """End-to-end over a FIXTURE home: memory/event_log.md carrying an unhedged drift line is
    excluded (exit 0, never cited) while the same line in memory/standards.md flags (exit 1) --
    so the exit 0 is the exclusion working, not an empty or unscanned tree."""
    m = _load_probe_module()
    _assert_flaggable(m, _FLAG_DSCR)
    with _fixture_home() as home:
        mem = os.path.join(home, *_MEM_REL)
        _write(os.path.join(mem, "event_log.md"), "- 2026-11-06 note: " + _FLAG_DSCR + "\n")
        r = run_probe(home=home)
        assert r.returncode == 0, (
            "expected exit 0 (event_log.md excluded), got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (r.returncode, r.stdout, r.stderr))
        assert "event_log.md" not in r.stdout, (
            "event_log.md narrative should not be scanned for governor drift:\n%s" % r.stdout)
        _write(os.path.join(mem, "standards.md"), _FIXTURE_CANON_LINE + _FLAG_DSCR + "\n")
        r = run_probe(home=home)
        assert r.returncode == 1 and "standards.md" in r.stdout, (
            "control: the same line in standards.md must flag; got %d\n%s"
            % (r.returncode, r.stdout))
    print("  PASS test_event_log_excluded_e2e (fixture: exit 0, event_log.md not scanned)")


def test_fixture_roots_drift_detected_e2e():
    """Detection is intact INSIDE the fixture: a drift planted in each in-scope fixture root
    (CLAUDE.md, memory, the ora-skills checkout -- committed on main, which is what the probe
    reads there -- the CC fleet) fails the probe and is cited by
    a path under the fixture home -- proving run_probe() really points the probe's scan roots
    at the fixture, and that a clean fixture run is not vacuous."""
    m = _load_probe_module()
    _assert_flaggable(m, _FLAG_LTV)
    with _fixture_home() as home:
        r = run_probe(home=home)
        assert r.returncode == 0, "seeded fixture must start clean; got %d\n%s" % (
            r.returncode, r.stdout)
        targets = [
            os.path.join(home, ".claude", "CLAUDE.md"),
            os.path.join(home, *(_MEM_REL + ("rules.md",))),
            os.path.join(home, "ora-skills", "portfolio-growth", "SKILL.md"),
            os.path.join(home, ".claude", "scheduled-tasks", "ora-fixture-task", "SKILL.md"),
        ]
        for path in targets:
            before = None
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as fh:
                    before = fh.read()
            _write(path, (before or "") + _FLAG_LTV + "\n")
            in_skills = os.path.join(home, "ora-skills") + os.sep in path
            if in_skills:
                _commit_fixture_skills(home, "plant drift")
            try:
                r = run_probe(home=home)
                rel = os.path.relpath(path, home)
                assert r.returncode == 1, "drift in fixture %s must flag; got %d\n%s" % (
                    rel, r.returncode, r.stdout)
                cited = [ln.strip() for ln in r.stdout.splitlines()
                         if ln.startswith("  ") and not ln.strip().startswith("|")]
                assert cited and all(ln.startswith(home) for ln in cited), (
                    "every finding must cite a path under the fixture home %s; got\n%s"
                    % (home, r.stdout))
                # full relative path, not basename: three roots plant into a SKILL.md, so a
                # basename match could be satisfied by another root's leftover drift
                assert rel.replace(os.sep, "/") in r.stdout.replace("\\", "/"), r.stdout
            finally:
                if before is None:
                    os.remove(path)
                else:
                    _write(path, before)
                if in_skills:
                    _commit_fixture_skills(home, "restore")
    print("  PASS test_fixture_roots_drift_detected_e2e")


# Shape of the real 2026-11-06 blocker: drift inside ANOTHER session's ora-skills worktree.
_SIBLING_WORKTREE_REL = ("ora-skills", ".claude", "worktrees",
                         "ora-skills-diffs-review-441806", "portfolio-growth", "SKILL.md")

# The tests that drive the probe end-to-end. Every one must be ambient-home-independent.
_HERMETIC_E2E_TESTS = (
    "test_event_log_excluded_e2e",
    "test_fixture_roots_drift_detected_e2e",
    "test_active_work_claims_excluded_e2e",
    "test_sessions_reviews_excluded_e2e",
    "test_fleet_roots_are_scanned_unit",
    "test_deal_comparison_skill_file_clean",
    "test_acquisition_underwriting_skill_file_clean",
    "test_live_tree_clean_optin",
)


def test_e2e_outcome_independent_of_ambient_home_e2e():
    """ISOLATION REGRESSION GUARD (2026-11-06). Builds a POISONED home whose ora-skills checkout
    holds a sibling session worktree with real drift (LTV 65%, DSCR 1.75 -- the exact class that
    blocked every push) -- proven INVISIBLE to the probe since it reads ora-skills from committed
    main only -- plus the same drift committed on the poisoned checkout's main, proven live (the
    probe run against the poisoned home exits 1 citing it), then re-runs every end-to-end and live-gated test of this file
    in a child process whose OWN home is the poisoned one. They must all still pass (or SKIP,
    for the opt-in live tests): the outcome depends only on fixtures. Any regression back to
    live reads -- run_probe() inheriting the ambient home, a fixture path built from the real
    HOME, a live test losing its opt-in gate -- makes the child see the planted drift and fail."""
    m = _load_probe_module()
    _assert_flaggable(m, _FLAG_LTV)
    poisoned = tempfile.mkdtemp(prefix="gdp-poisoned-home-")
    try:
        poison = "---\nname: portfolio-growth\n---\n\n" + _FLAG_LTV + "\nAcquisition governor: DSCR floor 1.75x.\n"
        # The real blocker's shape: drift in a sibling session worktree. Since the probe reads
        # ora-skills from committed main only, that copy alone is INVISIBLE (asserted below) --
        # so the poison that a leaked ambient-home read would actually see is the same drift
        # COMMITTED on the poisoned checkout's main.
        _write(os.path.join(poisoned, *_SIBLING_WORKTREE_REL), poison)
        _commit_fixture_skills(poisoned, "init")
        r = run_probe(home=poisoned)
        assert r.returncode == 0 and "worktrees" not in r.stdout, (
            "uncommitted sibling-worktree drift must be invisible to the probe; got %d\n%s"
            % (r.returncode, r.stdout))
        _write(os.path.join(poisoned, "ora-skills", "portfolio-growth", "SKILL.md"), poison)
        _commit_fixture_skills(poisoned, "poison main")
        r = run_probe(home=poisoned)
        assert (r.returncode == 1 and "portfolio-growth" in r.stdout
                and "SKILL.md@refs/" in r.stdout and "worktrees" not in r.stdout), (
            "control: drift committed on the poisoned ora-skills main must be visible to a "
            "probe that scans the poisoned home; got %d\n%s" % (r.returncode, r.stdout))
        code = ("import importlib.util, sys\n"
                "spec = importlib.util.spec_from_file_location('gdp_tests', sys.argv[1])\n"
                "t = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(t)\n"
                "for name in sys.argv[2:]:\n"
                "    getattr(t, name)()\n"
                "print('CHILD-OK')\n")
        env = _hermetic_env(poisoned)
        env.pop(LIVE_TESTS_FLAG, None)
        child = subprocess.run(
            [sys.executable, "-c", code, os.path.abspath(__file__)] + list(_HERMETIC_E2E_TESTS),
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        assert child.returncode == 0 and "CHILD-OK" in child.stdout, (
            "e2e tests must not depend on the ambient home (the poisoned home's committed "
            "ora-skills drift leaked into the outcome); rc=%d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (child.returncode, child.stdout, child.stderr[-3000:]))
    finally:
        shutil.rmtree(poisoned, ignore_errors=True)
    print("  PASS test_e2e_outcome_independent_of_ambient_home_e2e")


def test_live_tree_clean_optin():
    """OPT-IN live check (the pre-2026-11-06 behaviour of test_event_log_excluded_e2e): the real
    machine tree is clean and no finding cites event_log.md. Never run by the pre-push gate."""
    if _skip_unless_live("test_live_tree_clean_optin"):
        return
    r = run_probe(live=True)
    assert r.returncode == 0, (
        "live tree: expected exit 0, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    assert "event_log.md" not in r.stdout, r.stdout
    print("  PASS test_live_tree_clean_optin (live machine, exit 0)")


def test_active_work_claims_pruned_unit():
    """2026-08-22 FP fix, found while landing the tilde-hedge changelog fix above:
    hooks/active-work/*.json (claim_work.py's ephemeral cross-session claim broadcasts) is the
    SAME narrative-artifact class as event_log.md/MEMORY.md -- a claim's free-text `description`
    legitimately quotes whatever bug it's about, and a --force takeover additionally embeds the
    displaced claim's own description verbatim in `prior_claim`. This session's OWN claim file,
    describing this exact fix, ended up quoting 'inflating computed DSCR ~1.6x' and self-triggered
    the probe the moment it was written -- pruned by directory name, same as _archive/_staging."""
    m = _load_probe_module()
    assert m._is_pruned_dir("active-work")
    # Tight: requires the exact directory name, so an unrelated dir is never over-pruned
    # (suppression is a false NEGATIVE on a governor guard).
    assert not m._is_pruned_dir("active-work-archive")
    assert not m._is_pruned_dir("work")
    print("  PASS test_active_work_claims_pruned_unit")


def test_active_work_claims_excluded_e2e():
    """End-to-end companion to test_event_log_excluded_e2e: a claim_work.py claim file quoting an
    off-canonical DSCR value in its free-text description must not fail the probe.

    REGRESSION GUARD (round-1 independent review, 2026-08-22): the payload is a BARE, unhedged
    governor declaration that WOULD flag if scanned (asserted below), so this test can only pass
    because of the active-work prune. Runs in a fixture home (2026-11-06) -- it used to write
    into the live ~/.claude/hooks/active-work and scan the whole machine."""
    m = _load_probe_module()
    _assert_flaggable(m, _FLAG_DSCR)
    with _fixture_home() as home:
        claim = os.path.join(home, ".claude", "hooks", "active-work",
                             "_governor_probe_selftest_claim.json")
        _write(claim, '{"session_id": "test", "title": "selftest", '
                      '"description": "%s", "claimed_at": "2026-08-22T00:00:00"}' % _FLAG_DSCR)
        r = run_probe(home=home)
        assert r.returncode == 0, (
            "a claim file quoting an off-canonical value must not fail the probe (proves the "
            "active-work prune, not merely that the payload text is independently suppressed); "
            "got %d\n%s" % (r.returncode, r.stdout))
        assert "active-work" not in r.stdout, (
            "hooks/active-work claim files should not be scanned for governor drift:\n%s"
            % r.stdout)
        # control: the same JSON one directory up (hooks/ is a .json scan root) DOES flag
        _write(os.path.join(home, ".claude", "hooks", "selftest-control.json"),
               '{"description": "%s"}' % _FLAG_DSCR)
        r = run_probe(home=home)
        assert r.returncode == 1 and "selftest-control.json" in r.stdout, (
            "control: an unpruned hooks/*.json carrying the payload must flag; got %d\n%s"
            % (r.returncode, r.stdout))
    print("  PASS test_active_work_claims_excluded_e2e (fixture: active-work not scanned)")


def test_sessions_dir_pruned_unit():
    """2026-08-22 FP fix, found while pushing the LTV-narrative fix above: hooks/sessions/<id>/
    {overrides,reviews}/*.json is the SAME ephemeral cross-session narrative-artifact class as
    hooks/active-work/*.json -- an override token's free-text `reason` and a review artifact's
    free-text `notes` both legitimately quote whatever bug they're about. This session's OWN
    --record review artifact for the LTV-narrative fix quoted 'LTV 65%/40%' in its notes and
    self-triggered the probe the moment it was written, exactly like active-work did for the
    DSCR fix. Pruned by directory name, same as active-work/_archive/_staging."""
    m = _load_probe_module()
    assert m._is_pruned_dir("sessions")
    # Tight: requires the exact directory name, so an unrelated dir is never over-pruned
    # (suppression is a false NEGATIVE on a governor guard).
    assert not m._is_pruned_dir("sessions-archive")
    assert not m._is_pruned_dir("session")
    print("  PASS test_sessions_dir_pruned_unit")


def test_sessions_reviews_excluded_e2e():
    """End-to-end companion to test_active_work_claims_excluded_e2e: an eos-review-gate.py review
    artifact quoting an off-canonical LTV value in its free-text notes must not fail the probe.
    Runs in a fixture home (2026-11-06) -- it used to create a scratch session dir under the live
    ~/.claude/hooks/sessions and scan the whole machine."""
    m = _load_probe_module()
    _assert_flaggable(m, _FLAG_LTV)
    with _fixture_home() as home:
        review = os.path.join(home, ".claude", "hooks", "sessions",
                              "_governor_probe_selftest_session", "reviews",
                              "_governor_probe_selftest_review.json")
        _write(review, '{"key": "test", "verdict": "approved", "notes": "%s", "ts": 0}'
               % _FLAG_LTV)
        r = run_probe(home=home)
        assert r.returncode == 0, (
            "a review artifact quoting an off-canonical value must not fail the probe (proves "
            "the sessions prune, not merely that the payload text is independently suppressed); "
            "got %d\n%s" % (r.returncode, r.stdout))
        assert "sessions" not in r.stdout, (
            "hooks/sessions review artifacts should not be scanned for governor drift:\n%s"
            % r.stdout)
        _write(os.path.join(home, ".claude", "hooks", "selftest-control.json"),
               '{"notes": "%s"}' % _FLAG_LTV)
        r = run_probe(home=home)
        assert r.returncode == 1 and "selftest-control.json" in r.stdout, (
            "control: an unpruned hooks/*.json carrying the payload must flag; got %d\n%s"
            % (r.returncode, r.stdout))
    print("  PASS test_sessions_reviews_excluded_e2e (fixture: sessions not scanned)")


def test_fleet_roots_are_scanned_unit():
    """COVERAGE GAP closed 2026-07-24: build_targets() scanned neither scheduled-task fleet
    root, yet 17 fleet SKILL.md files declare DSCR/LTV. A governor edit landing in
    ora-am-brief or ora-monthly-portfolio-briefing was invisible to the Hard-Invariant-4
    guard. Both roots must now be targets. Resolved against a fixture home (2026-11-06), so
    build_targets()'s isdir() checks never touch the live machine."""
    with _fixture_home() as home:
        m = _load_probe_module_at_home(home)
        assert os.path.normcase(m.HOME) == os.path.normcase(home), (m.HOME, home)
        roots = [os.path.normcase(os.path.normpath(r)) for r, _ in m.build_targets()]
        cc = os.path.normcase(os.path.normpath(os.path.join(m.CLAUDE, "scheduled-tasks")))
        lams = os.path.normcase(os.path.normpath(os.path.join(
            m.HOME, "OneDrive - Oxford Capital Partners", "Documents", "Claude", "Scheduled")))
        assert cc in roots, "CC/MCP fleet root not scanned: %s" % cc
        assert lams in roots, "LAMS/Cowork fleet root not scanned: %s" % lams
    print("  PASS test_fleet_roots_are_scanned_unit")


def test_dated_archive_dirs_pruned_unit():
    """Pre-existing prune gap: iter_files() pruned a dir named EXACTLY '_archive', but the
    live convention is '_archive_<date>[_suffix]' -- 26 such dirs exist, and the archived
    '_archive_2026-04-28' SKILL.md (a 2026-04 draft carrying 'DSCR ... below 1.75 (ORA hard
    governor)') would read as live drift the moment the fleet roots were added."""
    m = _load_probe_module()
    assert m._is_pruned_dir("_archive")
    assert m._is_pruned_dir("_archive_2026-04-28")
    assert m._is_pruned_dir("_archive_2026-07-16_retired-to-ccmcp")
    assert m._is_pruned_dir("_staging")
    assert m._is_pruned_dir("node_modules") and m._is_pruned_dir(".git")
    # Tight: requires the '_archive_' separator, so a live dir merely starting with the
    # letters must NOT be pruned (suppression is a false NEGATIVE on a governor guard).
    assert not m._is_pruned_dir("_archives_live")
    assert not m._is_pruned_dir("_archivedeals")
    assert not m._is_pruned_dir("archive")
    assert not m._is_pruned_dir("skills")
    print("  PASS test_dated_archive_dirs_pruned_unit")


def test_probe_self_description_prose_suppressed_unit():
    """The probe's OWN exit-code documentation necessarily quotes its sentinel value:
    ora-doctrine-integrity-guard/SKILL.md:35 reads '... or the 1.75 regression sentinel'.
    That is prose ABOUT the detector, not a governor declaration. Suppressed by the term of
    art only -- span-scoped, same pattern as the correction-note suppressors."""
    m = _load_probe_module()
    assert m.scan_line(
        "- governor-drift-probe.py: exit 1 = governor DRIFT found (a DSCR threshold != 1.25x "
        "or LTV ceiling != 40% somewhere, or the 1.75 regression sentinel) with the offending "
        "file:line; exit 2 = PROBE ERROR.") == [], "probe self-description must not self-flag"
    print("  PASS test_probe_self_description_prose_suppressed_unit")


def test_sentinel_suppression_does_not_hide_real_drift_unit():
    """ANTI-SUPPRESSION GUARD (the one that matters). Suppression on a governor guard is a
    false NEGATIVE, so the 1.75-sentinel-prose exclusion must be inert against any real
    declaration -- including a line that also mentions the sentinel."""
    m = _load_probe_module()
    assert m.scan_line("Acquisition governor: DSCR floor 1.75x.") != [], "bare drift must flag"
    assert m.scan_line("DSCR governor is now 1.75 per the new policy.") != []
    # sentinel prose on the SAME line must not launder a separate live declaration
    assert m.scan_line(
        "The 1.75 regression sentinel exists because the DSCR governor floor is 1.75x.") != [], \
        "sentinel prose must not launder a real drift sharing the line"
    # the phrase must be the probe's term of art, not any nearby 'sentinel' token
    assert m.scan_line("DSCR governor 1.75 sentinel value for the portfolio floor.") != []
    # REFUTE-pass finding (2026-07-24): appending the exact suppressed phrase to a real
    # declaration is NOT an evasion -- the suppressor silences only branch 1 (the loose
    # proximity sentinel); every explicit-declaration branch stays armed and catches it via
    # "DSCR governor threshold 1.75x != canonical 1.25x". This asymmetry is the whole reason
    # the suppression is safe; assert it so a future refactor cannot quietly remove it.
    assert m.scan_line("DSCR governor floor 1.75 regression sentinel") != [], \
        "explicit-declaration branches must stay armed through the sentinel suppressor"
    print("  PASS test_sentinel_suppression_does_not_hide_real_drift_unit")


def test_fleet_skill_drift_would_flag_e2e():
    """End-to-end: a real drifted governor written into a fleet SKILL.md is now caught.
    Uses a temp dir shaped like a fleet task folder, scanned through iter_files+scan_line
    exactly as main() does."""
    import tempfile
    m = _load_probe_module()
    root = tempfile.mkdtemp()
    live = os.path.join(root, "ora-fake-task")
    arch = os.path.join(root, "_archive_2026-04-28", "ora-old-task")
    os.makedirs(live)
    os.makedirs(arch)
    drift = "Screen every deal against the DSCR floor of 1.10x and an LTV ceiling of 65%.\n"
    for d in (live, arch):
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: t\ndescription: d\n---\n\n" + drift)
    seen = []
    for path in m.iter_files(root, (".md",)):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if m.scan_line(raw):
                    seen.append(path)
    assert any("ora-fake-task" in p for p in seen), "live fleet drift missed: %s" % seen
    assert not any("_archive_2026-04-28" in p for p in seen), "archived copy must be pruned"
    print("  PASS test_fleet_skill_drift_would_flag_e2e")


def test_decimal_fragment_never_binds_unit():
    """2026-07-29 live FP class: a narrated per-property figure "54.3% LTV" on a governor line let
    the free-floating percent capture bind the FRACTIONAL digits alone -> "LTV governor 3% !=
    canonical 40%", a nonsense value (disposition-ledger.md:38 / historical-evaluations:46).
    The fragment must NEVER bind; the FULL decimal must bind instead (and, being non-canonical on a
    governor-keyword line, flags AS ITSELF -- garbage killed, detection preserved; the live ledger
    files are additionally file-exempt, which test_ledger_files_excluded_source_pin covers)."""
    m = _load_probe_module()
    line = ("Park National loan, 54.3% LTV (exceeds 40% governor -- see event_log.md "
            "2026-07-29, ACCEPTED)")
    out = m.scan_line(line)
    assert not any("governor 3%" in r or "governor 6%" in r for r in out), \
        "fractional fragment bound as an LTV value: %s" % out
    assert any("54.3" in r for r in out), \
        "full decimal must bind (detection preserved) on a governor line: %s" % out
    # canonical restated on the same line ("40% governor") must NOT flag
    assert not any("governor 40%" in r for r in out), "canonical 40 misflagged: %s" % out
    print("  PASS test_decimal_fragment_never_binds_unit")


def test_decimal_ltv_drift_still_flags_unit():
    """A genuinely drifted DECIMAL ceiling previously bound a garbage fragment or nothing at all;
    with the decimal-capture fix it must flag with its true value via BOTH word orders."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter: LTV ceiling <= 42.5% on every deal (governor).")
    assert any("42.5" in r for r in out), "comparator-bound decimal drift missed: %s" % out
    out2 = m.scan_line("This 42.5% ceiling is the acquisition governor.")
    assert any("42.5" in r for r in out2), "reverse-order decimal drift missed: %s" % out2
    print("  PASS test_decimal_ltv_drift_still_flags_unit")


def test_canonical_decimal_forty_clean_unit():
    """"40.0%" is numerically canonical -- the numeric compare must not flag it."""
    m = _load_probe_module()
    out = m.scan_line("Acquisition governor (non-negotiable): LTV <= 40.0%.")
    assert out == [], "canonical 40.0%% misread as drift: %s" % out
    print("  PASS test_canonical_decimal_forty_clean_unit")


def test_dated_review_memory_file_excluded_unit():
    """2026-07-29 REFUTE ruling: a 'review' token in DATED_AUDIT_RE was REJECTED (it would sweep in
    project_*_doctrine_review_*.md -- a doctrinal home, FN-biased). The one live review-narrative
    file is exempt by EXACT NAME in skip_names instead; the RE must NOT match review files."""
    m = _load_probe_module()
    assert not m.DATED_AUDIT_RE.match(
        "project_historical_evaluations_acquisition_review_2026-07-29.md"), \
        "'review' pattern token must stay rejected (REFUTE 2026-07-29)"
    assert not m.DATED_AUDIT_RE.match(
        "project_acquisition_underwriting_doctrine_review_2026-07-18.md"), \
        "doctrine-review plan files must stay IN SCOPE"
    for bn in ("standards.md", "rules.md", "firm.md",
               "project_replacement_cost_benchmark_unratified.md"):
        assert not m.DATED_AUDIT_RE.match(bn), "live/doctrine file must NOT be exempt: %s" % bn
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert '"project_historical_evaluations_acquisition_review_2026-07-29.md"' in src, \
        "exact-name exemption for the historical-evaluations review file missing from skip_names"
    print("  PASS test_dated_review_memory_file_excluded_unit")


def test_unit_interval_ltv_flags_unit():
    """REFUTE residual #1 hardening: unit-interval notation on a governor line ("LTV ceiling
    0.65%" -- a human porting ltvCeiling: 0.65 into prose) must flag loudly, not drop silently."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter: LTV ceiling 0.65% on every deal (governor).")
    assert any("0.65" in r for r in out), "unit-interval LTV drift dropped silently: %s" % out
    print("  PASS test_unit_interval_ltv_flags_unit")


def test_ledger_files_excluded_source_pin():
    """disposition-ledger.md / deal-decision-ledger.md are append-only decision ledgers -- the same
    narrative class as event_log.md. skip_names is main()-local, so this pins the exemption at
    SOURCE level (a rename or accidental removal breaks this test loudly)."""
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    for name in ("disposition-ledger.md", "deal-decision-ledger.md"):
        assert '"%s"' % name in src, "ledger exemption missing from skip_names: %s" % name
    print("  PASS test_ledger_files_excluded_source_pin")


def test_concurrent_session_hardening_narrative_excluded_unit():
    """2026-08-22 false positive: memory/reference_concurrent_session_duplicate_hardening_work.md
    NARRATES a past incident -- one session's own investigation title was literally 'Fix
    governor-drift-probe false positive on LTV 65%/40%', quoted in prose while explaining what
    that OTHER session was and wasn't working on. This is the same append-only NARRATIVE class as
    event_log.md/the ledgers (records findings, does not declare a live governor), tripped ONLY
    because the line separately contains the literal token 'governor' (as part of the compound
    'governor-drift-probe', the tool's own name) which alone satisfies is_gov's bare substring
    GOV_KEYWORDS check. Exempt by EXACT FILENAME, mirroring the ledger/historical-evaluations
    precedent (DATED_AUDIT_RE's docstring: a broad pattern token was REFUTE-rejected 2026-07-29;
    narrow exact names only). Blocked every push in this repo until fixed (2026-08-22).
    skip_names is main()-local, so this pins the exemption at SOURCE level."""
    m = _load_probe_module()
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert '"reference_concurrent_session_duplicate_hardening_work.md"' in src, (
        "narrative exemption missing from skip_names: "
        "reference_concurrent_session_duplicate_hardening_work.md")
    # FILE-scoped, not logic-level (same discipline as test_dated_audit_memory_file_excluded_unit):
    # the triggering span of the real line (verbatim from the file) must still trip scan_line()
    # on its own.
    real_line = (
        "its own title was \"Fix governor-drift-probe false positive on LTV 65%/40%\", a "
        "different, already-landed bug (`c7875a5`)")
    assert m.scan_line(real_line), (
        "detection logic must be intact -- the file is excluded by FILE, not by gutting scan_line")
    print("  PASS test_concurrent_session_hardening_narrative_excluded_unit")


def test_index_projects_system_narrative_excluded_unit():
    """2026-08-23 false positive: memory/INDEX_projects_system.md is the "Projects & system"
    SUB-INDEX split out of MEMORY.md (already exempted) when MEMORY.md's own size gate got tight --
    same append-only-pointer NARRATIVE class as its parent. Its line 59 pointer reads "- [governor-
    drift-probe LTV 65%/40% split false positive](...) -- LANDED 08-22 (`c7875a5`)" -- a record of
    an ALREADY-LANDED fix, not a live governor declaration; tripped only because the pointer text
    quotes the tool's own bug title. Exempt by EXACT FILENAME, mirroring the
    reference_concurrent_session_duplicate_hardening_work.md / ledger precedent immediately above
    (a broad pattern token was REFUTE-rejected 2026-07-29; narrow exact names only). One of the 6
    findings blocking test_event_log_excluded_e2e / test_active_work_claims_excluded_e2e, closed
    alongside the 2 cherry-picked commits that fixed the other 5 (session 8b0c9f4c, 2026-08-23).
    skip_names is main()-local, so this pins the exemption at SOURCE level."""
    m = _load_probe_module()
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert '"INDEX_projects_system.md"' in src, (
        "narrative exemption missing from skip_names: INDEX_projects_system.md")
    # FILE-scoped, not logic-level: the real line's triggering span must still trip scan_line() on
    # its own -- the exemption removes the FILE from scope, it does not gut detection.
    real_line = (
        "- ✅ [governor-drift-probe LTV 65%/40% split false positive]"
        "(project_usage_report_horizon_builds_scoped_2026-08-21.md) — LANDED 08-22 (`c7875a5`)"
    )
    assert m.scan_line(real_line), (
        "detection logic must be intact -- the file is excluded by FILE, not by gutting scan_line")
    print("  PASS test_index_projects_system_narrative_excluded_unit")


def test_open_items_tracker_narrative_excluded_unit():
    """2026-09-21 false positive: memory/open-items-tracker.md line 37 (the OI-338 row, one 4,454-char
    table row) failed test_event_log_excluded_e2e and blocked every push from this repo. The row
    quotes ordinary PER-LOAN LTVs (66.8% / 7.7% / 37.7%) and, once, at offset ~2,400, the words
    "Governor flag (no constant changed)". _is_gov_line() arms the WHOLE line on that single word, and
    the bare-proximity pass (RE_LTV_NEAR, the weakest) then reads every "LTV near a percent" on the
    line -- thousands of characters away -- as a governor declaration. Verified: neutralising that
    one word gives zero findings; a synthetic with the LTV figure ~600 chars from "Governor" flags.

    The open-items tracker is the same append-only NARRATIVE class as event_log.md and the decision
    ledgers: one row per open item, RECORDING findings ("Governor flag (no constant changed)" is the
    row reporting a flag, not declaring a governor). The living governor stays declared in
    standards.md / rules.md / CLAUDE.md / skills / capital-config.ts, all still in scope. Exempt by
    EXACT FILENAME (pattern tokens were REFUTE-rejected, see DATED_AUDIT_RE), both the live tracker
    AND its -history rollover file: rows roll from one into the other, so exempting only the live file
    would re-trip the moment the OI-338 row is archived. Accepted blind spot, unchanged in kind from
    the ledger precedent: a governor change recorded ONLY in a tracker row goes unseen.
    skip_names is main()-local, so this pins the exemption at SOURCE level."""
    m = _load_probe_module()
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    for name in ("open-items-tracker.md", "open-items-tracker-history.md"):
        assert '"%s"' % name in src, (
            "narrative exemption missing from skip_names: %s" % name)
    # FILE-scoped, not logic-level: a row shaped like OI-338 (per-loan LTV in one sentence, the word
    # "Governor" a long way away in another) must STILL trip scan_line() -- the exemption removes the
    # FILE from scope, it does not gut detection or window the arming.
    far = ("3540 E 5th is at about 66.8% LTV on its lender's appraisal. " + ("filler words " * 45)
           + "**Governor flag (no constant changed):** the workbook value gives 54%.")
    assert m.scan_line(far), (
        "detection logic must be intact -- the tracker is excluded by FILE, not by gutting scan_line")
    print("  PASS test_open_items_tracker_narrative_excluded_unit")


def test_intervening_qualifier_dscr_floor_flags_unit():
    """GAP (2026-08-11): GOV_KEYWORDS held the CONTIGUOUS literal 'dscr floor', so any qualifier
    between the metric and its floor-word defeated the is_gov gate and the whole equality branch
    was skipped. 'DSCR hard floor 1.40x' is the exact phrasing the 2026-08-11 Notion defect used
    ('hard floor 1.75'), so this false negative sat on the most likely real-world drift wording."""
    m = _load_probe_module()
    for line in ("DSCR hard floor 1.40x per property.",
                 "DSCR absolute floor 1.40x per property.",
                 "Per-property DSCR minimum floor 1.40x."):
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "drifted DSCR floor with an intervening qualifier must flag: %r -> %r" % (line, out))
    print("  PASS test_intervening_qualifier_dscr_floor_flags_unit")


def test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit():
    """REGRESSION PIN for the reverted LTV half (2026-08-11). Extending the same intervening-
    qualifier pairing to LTV armed prose describing the RATIFIED per-property 65% refi ceiling
    (debt-maturity.DESIGN.md:18) and flagged 65 != 40 -- a false positive on a legitimate figure,
    caught by the E2E test. The LTV half was reverted; this pins the line that exposed it so a
    future LTV attempt fails HERE, at the unit layer, instead of surfacing as a whole-tree E2E
    break. Closing the LTV gap requires widening LTV suppression first (see probe comment)."""
    m = _load_probe_module()
    line = "| Per-property LTV vs the **65% refi ceiling** | **No** (warehouse side) |"
    assert m.scan_line(line) == [], (
        "ratified 65%% per-property refi-ceiling prose must not flag: %r" % (m.scan_line(line),))
    print("  PASS test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit")


def test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit():
    """REGRESSION PIN (governor-drift-probe.py false positive, live on main): the ratified
    per-property refi-sizing ceiling declared on its OWN bullet -- with no same-line
    portfolio-aggregate 40% companion and no same-line "LESSER of ... DSCR" construct, because
    doctrine legitimately states the two governors on SEPARATE bullets -- escaped every existing
    suppressor and flagged "LTV governor 65%% != canonical 40%%".

    Root cause (acquisition-buy-box-v1.md:31): the literal "LTV ceiling" token arms is_gov (a
    GOV_KEYWORDS hit); the parenthetical "(per-property refi sizing)" immediately after "ceiling"
    truncates RE_LTV_ANCHOR's scan window at the "(" clause-splitter, so the anchor pass never
    reads the 65%% at all; the line falls through to the reverse bare-proximity pass
    (RE_LTV_NEAR, "65%%** LTV"), which had no per-property/refi framing suppressor for a
    STANDALONE mention -- every existing one requires either the portfolio-aggregate companion on
    the same line (the 2026-07-16 pairing suppressor) or a same-line refi construct (LESSER-of /
    refi-to / DSCR-paired). This was KNOWN GAP 2 in the probe's own comments, deliberately
    deferred pending a reviewed change -- this is that change.

    This exact wording (acquisition-buy-box-v1.md:31-32, split across two lines by markdown
    wrapping) is scanned ONE LINE AT A TIME by scan_line(), so the test reproduces line 31 alone,
    exactly as the probe sees it."""
    m = _load_probe_module()
    line = ("- **LTV ceiling (per-property refi sizing):** **≤ 65%** LTV at stabilized "
            "exit-cap value. Refi debt")
    out = m.scan_line(line)
    assert out == [], (
        "ratified per-property refi-sizing ceiling on its own bullet must not flag; got %r" % out)
    # Hyphenated doctrine spelling (SKILL.md house style: "refi-sizing") must be equally clean.
    line_hyphen = "LTV ceiling (per-property refi-sizing): <= 65% LTV at stabilized exit value."
    out_hyphen = m.scan_line(line_hyphen)
    assert out_hyphen == [], (
        "hyphenated 'refi-sizing' spelling must not flag either; got %r" % out_hyphen)
    print("  PASS test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit")


def test_perproperty_refi_ceiling_standalone_drift_still_flags_unit():
    """VALUE-LOCK guard for the fix above: a per-property refi-sizing ceiling that has actually
    DRIFTED off the ratified 65%% -- still on its own bullet, still no aggregate companion -- must
    still flag. The suppressor is locked to the literal ratified value, not to the "per-property
    refi sizing" phrase alone, so this is the anti-blinding counterpart to
    test_perproperty_non_ratified_ltv_still_flags_unit for the standalone-bullet shape."""
    m = _load_probe_module()
    for val in ("80", "55", "70"):
        line = ("- **LTV ceiling (per-property refi sizing):** **<= %s%%** LTV at stabilized "
                "exit-cap value. Refi debt" % val)
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "drifted per-property refi-sizing ceiling %s%% must still flag; got %r" % (val, out))
    print("  PASS test_perproperty_refi_ceiling_standalone_drift_still_flags_unit")


def test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit():
    """ADVERSARIAL FINDING (independent review, round 1, 2026-08-21): the first cut of the
    standalone per-property refi-ceiling fix tested "does RE_PERPROPERTY_REFI_FRAME appear
    ANYWHERE on the line", not whether it actually QUALIFIES the flagged value -- unlike every
    other suppressor in this module, which is span/proximity-scoped. That let a genuinely drifted
    AGGREGATE governor slip through whenever the ratified per-property phrase happened to sit
    elsewhere on the same line (a realistic edit: an author conflating the two governors while
    narrating a change to the aggregate one). Both lines below flag on the pre-fix module and must
    still flag now that the frame is required to sit immediately BEFORE the value it qualifies."""
    m = _load_probe_module()
    for line in (
        "Portfolio LTV ceiling raised to 65% given our per-property refi sizing convention.",
        "Aggregate LTV ceiling 65%; per-property refi sizing unchanged.",
    ):
        out = m.scan_line(line)
        assert any("65" in o for o in out), (
            "aggregate-governor drift to 65%% must still flag even when the ratified per-property "
            "refi-sizing phrase sits elsewhere on the line; line=%r got=%r" % (line, out))
    print("  PASS test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit")


def test_dscr_scaling_multiplier_changelog_stays_clean_unit():
    """REGRESSION PIN (governor-drift-probe.py false positive, overridden 5x by 3 sessions across
    2026-08-21/22 via the allow-hook-test-failure override token -- hooks/_state/override-usage-
    log.jsonl signature d491c6e47418): deal-comparison/SKILL.md:153's v1.2 changelog entry narrates
    a PAST BUG ("DSCR was tested at 40% LTV ... inflating computed DSCR ~1.6x") -- a scaling factor
    describing how wrong a buggy CALCULATION was, not a declared governor threshold. RE_DSCR_THRESH
    matched "dscr ~1.6x" (the second "DSCR" token) as if it were a declared floor and flagged
    "DSCR governor threshold 1.6x != canonical 1.25x".

    The reproduction below is the real line verbatim (deal-comparison/SKILL.md:153, one continuous
    changelog paragraph scanned as a single line by scan_line()) -- it deliberately ALSO carries
    "HARD FILTER", "disqualif", and "would floor-flag" elsewhere on the same dense line, which is
    exactly what makes this false-positive shape different from the module's existing qualifiers:
    a generic nearby-token veto (the pattern every sibling qualifier above uses) would misread
    "floor-flag" -- ORA's own Ruling-5 term of art for "gets flagged for breaching a floor" -- as a
    floor DECLARATION next to the value and refuse to suppress. See
    _dscr_scaling_multiplier_spans for why the fix avoids that veto shape entirely."""
    m = _load_probe_module()
    line = (
        "- v1.2 (2026-08-21): HIGH fix (cc-audit-army findings M02-deal-comparison-dscr-wrong-"
        "ltv-and-kills, M13-deal-comparison-basis-band-ignores-vintage-ramp), Gabriel-approved. "
        "Two defects that made this skill disagree with acquisition-underwriting on the firm's "
        "two hardest acquisition gates: (1) DSCR was tested at 40% LTV — the portfolio-"
        "aggregate governor, not per-property refi sizing — inflating computed DSCR ~1.6x "
        "and letting deals that would floor-flag in acquisition-underwriting score clean here; "
        "corrected to the LESSER-of-65%-LTV/1.25x-DSCR basis. (2) A breach was labeled "
        '"immediate disqualification"/"DISQUALIFIED", contradicting Ruling 5 (floors flag, never '
        "kill); corrected to FLOOR-FLAGGED throughout (HARD FILTER line, scoring table, "
        "recommendation thresholds, output template). (3) The Basis band hardcoded a flat "
        ">40%-of-RCT-LOW cutoff — only the loosest (≥2005-vintage) endpoint of the "
        "vintage ramp — so a pre-1995 building (ORA's dominant vintage) could score points "
        "at a basis acquisition-underwriting Stage 1 would already floor-flag; corrected to the "
        "same linear vintage-ramp floor (65% discount at ≤1995 → 60% at ≥2005) "
        "acquisition-underwriting uses. No governor constants changed — this only restates "
        "deal-comparison to apply the already-ratified 1.25x DSCR / RCT v03 vintage ramp correctly."
    )
    out = m.scan_line(line)
    assert out == [], (
        "changelog scaling-multiplier narrative ('inflating computed DSCR ~1.6x') must not flag "
        "as a governor declaration; got %r" % out)
    print("  PASS test_dscr_scaling_multiplier_changelog_stays_clean_unit")


def test_dscr_scaling_multiplier_real_drift_still_flags_unit():
    """ANTI-BLINDING (detection over silence): a genuine DSCR governor drift sharing the line with
    the scaling-multiplier narrative must still flag in full -- the multiplier suppressor defers
    whole-line to the RE_GOV_DSCR_BOUND structural veto the moment a real "dscr ... floor/minimum"
    pairing is present, so BOTH the multiplier value and the drifted floor stay visible (safe
    over-detection, not masking). A second line pins that a real drift phrased with a scaling verb
    ('inflated') in a DIFFERENT word order -- 'the DSCR floor was inflated to 1.60x', keyword
    BEFORE the value, no 'computed/calculated/measured' token -- structurally cannot match
    RE_DSCR_COMPUTED_SCALING at all, so it is untouched and flags via the pre-existing declaration
    extractor exactly as it did before this fix."""
    m = _load_probe_module()
    combined = ("v1.3: fixed the bug inflating computed DSCR ~1.6x; separately, note the DSCR "
                "floor 1.60x needs correction to 1.25x.")
    out = m.scan_line(combined)
    assert any("1.6x" in o for o in out) and any("1.60x" in o for o in out), (
        "both the multiplier value and the co-located real DSCR floor drift must flag when a "
        "genuine declaration shares the line; got %r" % out)

    other_order = ("v1.4: the DSCR floor was inflated to 1.60x due to a config error; "
                   "corrected to 1.25x.")
    out2 = m.scan_line(other_order)
    assert any("1.60x" in o for o in out2), (
        "a real DSCR floor drift phrased with a scaling verb in a different word order (keyword "
        "before value, no computed/calculated/measured token) must still flag; got %r" % out2)
    print("  PASS test_dscr_scaling_multiplier_real_drift_still_flags_unit")


def test_dscr_scaling_multiplier_by_factor_phrasing_stays_clean_unit():
    """Generalization pin: the suppressor is not hardcoded to the literal '~1.6x' tilde notation --
    the equally natural 'by a factor of N.Nx' phrasing must be recognized too, since both are
    describing the same scaling-multiplier narrative shape (a computed figure inflated/overstated
    by a bug), just with different connective wording."""
    m = _load_probe_module()
    line = "v1.5: fixed a bug overstating computed DSCR by a factor of 1.6x in the scoring table."
    out = m.scan_line(line)
    assert out == [], (
        "'overstating computed DSCR by a factor of 1.6x' must not flag; got %r" % out)
    print("  PASS test_dscr_scaling_multiplier_by_factor_phrasing_stays_clean_unit")


def test_dscr_scaling_multiplier_keyword_after_value_still_flags_unit():
    """ADVERSARIAL FINDING (independent review, round 1, 2026-08-22): the first cut of the scaling-
    multiplier suppressor claimed a floor/ceiling/minimum/maximum keyword always sits immediately
    adjacent to ITS value in a real declaration, and relied on that to skip a proximity veto -- but
    that is only true for keyword-BEFORE-value forms (RE_DSCR_DECL). RE_DSCR_DECL_REV's shape puts
    the keyword AFTER the value ("1.40x floor"), which the scaling regex's left-only value bound did
    not guard, so "bug inflating computed DSCR ~1.40x floor going forward" matched the multiplier
    shape and silenced a genuine value-then-keyword declaration -- RE_GOV_DSCR_BOUND cannot catch it
    either, because the value's own decimal point sits inside its clause-exclusion gap class.

    Closed with a trailing negative lookahead in RE_DSCR_COMPUTED_SCALING
    (`(?!\\s*(?:floor|ceiling|minimum|min|maximum|max)\\b)`), mirroring the bps-tier refi veto's
    existing kw_after_spans exemption ("an explicitly-declared floor is a governor statement...
    must flag even inside a bps tier" -- round-2 review W3).

    All three lines carry a fix/bug/correction token (RE_CHANGELOG_CONTEXT), so all three exercise
    the lookahead specifically (round-2 review Finding 3: line 2 originally carried no such token,
    so it was pinning RE_CHANGELOG_CONTEXT rather than the lookahead it was meant to test)."""
    m = _load_probe_module()
    for line, val in (
        ("hard filter: bug inflating computed DSCR ~1.40x floor going forward.", "1.40"),
        ("fix: acquisition screen overstated computed DSCR by 1.30x minimum; correction pending.",
         "1.30"),
        ("hard filter: fixed bug — understated calculated DSCR ~1.40x ceiling.", "1.40"),
    ):
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "a value-then-keyword DSCR declaration inside scaling-verb prose must still flag; "
            "line=%r got=%r" % (line, out))
    print("  PASS test_dscr_scaling_multiplier_keyword_after_value_still_flags_unit")


def test_dscr_scaling_multiplier_intervening_modifier_still_flags_unit():
    """ADVERSARIAL FINDING (independent review, round 2, 2026-08-22): the round-1 lookahead fix
    only guarded a keyword IMMEDIATELY adjacent to the value ("~1.40x floor"). A single modifier
    word between value and keyword slipped past it -- "~1.40x hard floor" / "~1.40x strict
    minimum" -- and was otherwise invisible to every other pass (RE_DSCR_DECL_REV requires the
    keyword to abut the value; RE_GOV_DSCR_BOUND is blocked by the value's own decimal sitting in
    its clause-exclusion gap class). Confirmed as a live regression vs main (main flags both lines
    below; the pre-round-2-fix worktree silenced them). This is not contrived vocabulary -- the
    module's own _is_gov_line docstring uses "DSCR hard floor 1.40x" as its canonical example, and
    STAB_GOV_MARKERS separately carries "hard cap"/"hard ceiling".

    Closed by widening the lookahead to allow up to 2 intervening hyphen/space-joined modifier
    words before the keyword: `(?!\\s*(?:\\w+[-\\s]+){0,2}(?:floor|ceiling|minimum|min|maximum|max)
    \\b)`."""
    m = _load_probe_module()
    for line, val in (
        ("hard filter: fixed bug inflating computed DSCR ~1.40x hard floor going forward.",
         "1.40"),
        ("hard filter: fixed bug inflating computed DSCR ~1.40x strict minimum.", "1.40"),
    ):
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "a value-then-MODIFIER-then-keyword DSCR declaration inside scaling-verb prose must "
            "still flag; line=%r got=%r" % (line, out))
    print("  PASS test_dscr_scaling_multiplier_intervening_modifier_still_flags_unit")


def test_dscr_scaling_multiplier_present_tense_mechanism_still_flags_unit():
    """ADVERSARIAL FINDING (independent review, round 1, 2026-08-22): the scaling-multiplier
    suppressor is scoped by doctrine to a PAST-DEFECT changelog narrative, but the original regex
    encoded no notion of pastness -- a PRESENT-TENSE multiplicative fudge on computed DSCR (a real
    drift MECHANISM, since it effectively shifts the floor by the factor, not a typo) matched and
    was silenced identically to the past-tense bug-fix narrative it was designed for. Closed by
    requiring an explicit fix/bug/correction context token (RE_CHANGELOG_CONTEXT) anywhere on the
    line before suppressing -- present-tense/still-applied narratives generally carry none."""
    m = _load_probe_module()
    for line, val in (
        ("v2.0: per the hard filter, the underwriting model now deliberately scales computed "
         "DSCR by 1.4x before comparison.", "1.4"),
        ("Per the hard acquisition governor doctrine, the model inflates computed DSCR ~1.4x "
         "today.", "1.4"),
    ):
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "a present-tense/live scaling-multiplier narrative with no fix/bug/correction context "
            "token must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_dscr_scaling_multiplier_present_tense_mechanism_still_flags_unit")


def test_dscr_scaling_multiplier_governor_nearby_still_flags_unit():
    """Test-gap finding (independent review, round 1, 2026-08-22): none of the three original
    tests exercised the "governor" proximity veto in _dscr_scaling_multiplier_spans -- deleting
    that veto left all three green. Pins it directly: a scaling-multiplier-shaped value with the
    literal "governor" token inside its [vs-25, ve+40] reach must still flag."""
    m = _load_probe_module()
    line = "changelog: bug inflating computed DSCR ~1.6x governor threshold."
    out = m.scan_line(line)
    assert any("1.6" in o for o in out), (
        "a scaling-multiplier value declared AS the governor nearby must still flag; got %r" % out)
    print("  PASS test_dscr_scaling_multiplier_governor_nearby_still_flags_unit")


def test_dscr_scaling_multiplier_accepted_residuals_unit():
    """Pins the two ACCEPTED RESIDUALS documented above RE_DSCR_COMPUTED_SCALING (round-2 review,
    2026-08-22) DELIBERATELY, so they read as a decision rather than a latent gap:
      * NEGATION-BLIND: RE_CHANGELOG_CONTEXT is a lexical token check, not negation-aware -- a
        line stating a defect is explicitly NOT YET corrected still satisfies the gate (it carries
        "bug" and "corrected").
      * TOPIC-BLIND: the token search is line-wide, not proximity-scoped to the value -- an
        unrelated fix/bug mention elsewhere on the line satisfies the gate for a scaling-multiplier
        clause that has nothing to do with it.
    Both were verified in round-2 review to be NOT cheaply closeable without either reopening the
    real target line (proximity/clause-scoping the token search) or adding new negation-detection
    suppression surface. If either residual is ever closed, this test's assertions flip and it
    should be rewritten as a must-flag pin instead of deleted outright."""
    m = _load_probe_module()
    negation_blind = ("OPEN BUG (hard filter): scoring still inflates computed DSCR ~1.6x; "
                       "not yet corrected.")
    assert m.scan_line(negation_blind) == [], (
        "negation-blind residual changed behavior -- update this test's docstring/assertion "
        "rather than deleting it; got %r" % m.scan_line(negation_blind))

    topic_blind = ("per the hard filter, we fixed a typo in the README; separately, the model "
                   "now deliberately scales computed DSCR by 1.4x before comparison.")
    assert m.scan_line(topic_blind) == [], (
        "topic-blind residual changed behavior -- update this test's docstring/assertion rather "
        "than deleting it; got %r" % m.scan_line(topic_blind))
    print("  PASS test_dscr_scaling_multiplier_accepted_residuals_unit")


def test_value_between_metric_and_boundword_flags_unit():
    """GAP NOW CLOSED (2026-08-12). Was pinned as a known gap on 2026-08-11: the
    metric-VALUE-boundword order did not arm, because the value's own decimal is a '.' and the
    qualifier gap class excludes '.' to stop the gate crossing a sentence. "DSCR 1.40x minimum"
    went undetected even though its extractor (RE_DSCR_DECL_REV) existed.

    Closed with a SECOND, value-abutting arming pattern rather than by loosening the first: the
    decimal now lives INSIDE the pattern, so it can never be confused with a sentence boundary.
    The rejected alternative (allow a dot anywhere between digits in the gap) is still rejected --
    it reports "DSCR of 1.42 with a 10 min cure period" as governor drift; see the FP guard test."""
    m = _load_probe_module()
    for line in ("DSCR 1.40x minimum per property.",
                 "DSCR 1.40 floor per property.",
                 "DSCR 1.40x min per property."):
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "value-between-metric-and-boundword drift must flag: %r -> %r" % (line, out))
    # Canonical in the same shape must stay clean -- arming is not a finding.
    assert m.scan_line("DSCR 1.25x minimum per property.") == [], \
        "canonical value in the value-first shape must not flag"
    print("  PASS test_value_between_metric_and_boundword_flags_unit")


def test_value_abutting_arming_does_not_flag_durations_unit():
    """FP GUARD for the value-abutting pattern (2026-08-12). The whole reason the simpler
    digit-dot fix was rejected: bare 'min' is a DURATION unit as often as it is 'minimum'. These
    must never report a governor finding -- pinned so a future loosening of the value-abutting
    pattern fails here rather than turning cure periods and uptime prose into Hard-Invariant-4
    findings."""
    m = _load_probe_module()
    for line in ("DSCR of 1.42 with a 10 min cure period",
                 "DSCR poller downtime 1.5 min today.",
                 "Cure period is 30 min; DSCR of 1.42 reported.",
                 "DSCR came in at 1.42; minimum lease term 3 yrs."):
        assert m.scan_line(line) == [], (
            "duration/unrelated prose must NOT flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_value_abutting_arming_does_not_flag_durations_unit")


def test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit():
    """FP CLASS CLOSED (2026-08-12, MAJOR finding from independent review).

    RE_LTV_CEIL_REV fires on any "N% ceiling|maximum" anywhere on an ARMED line and needs no 'ltv'
    token -- that is deliberate, so "This 65% ceiling is the acquisition governor" is caught. But
    once the DSCR side started arming the value-first shape, a line could be armed purely by a DSCR
    statement and this pass would then read an unrelated capped percentage as an LTV ceiling. That
    is realistic buy-box list prose, and one false positive flips the weekly gate red.

    Closed by VETOING on the percentage's subject -- not by requiring positive LTV evidence. The
    requirement form was implemented first and reverted: see
    test_ltv_subject_veto_does_not_silence_real_declarations_unit for the five real declarations it
    silenced and why the direction matters."""
    m = _load_probe_module()
    for line in ("DSCR 1.25x minimum; underwrite vacancy 10% maximum.",
                 "DSCR 1.25 floor, TI cap 12% maximum of TDC.",
                 "DSCR 1.25x minimum with parking ratio 2.0 and site coverage 45% maximum."):
        assert m.scan_line(line) == [], (
            "an unrelated capped percentage on a DSCR-armed line must NOT read as an LTV "
            "ceiling: %r -> %r" % (line, m.scan_line(line)))
    # The reverse-order pass must KEEP its reason for existing. Exact string, not a substring
    # match: a weaker assertion passes even when the WRONG percentage is reported.
    assert m.scan_line("This 65% ceiling is the acquisition governor.") == \
        ["LTV ceiling 65% != canonical 40%"], \
        "reverse-order LTV ceiling on a genuine governor declaration must still flag, and must "\
        "report the ceiling's own value"
    print("  PASS test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit")


def test_ltv_subject_veto_does_not_silence_real_declarations_unit():
    """THE REGRESSION GUARD for how this false positive is fixed (2026-08-12).

    The FIRST attempt at this fix REQUIRED a positive LTV-side governor marker near the value. It
    closed the false positives and silently broke five realistic drift declarations that had
    flagged since 2026-07-08 -- verified against baseline ba2b0a8 -- because it reused
    _governor_declared_nearby, a helper whose short before-reach and plural/canonical-phrase
    exemptions are tuned to err toward DETECTION when used to VETO, and therefore err toward
    SILENCE when used as a REQUIREMENT. Independent review caught it.

    These five are the exact lines that broke. They pin the DIRECTION of the fix: suppression must
    stay subject-scoped. If someone reworks this into a positive-evidence gate again, this test
    fails first."""
    m = _load_probe_module()
    for line in ("Under the 1.25x DSCR governor we now allow a 65% maximum.",
                 "Governors: DSCR 1.25x floor and 65% maximum.",
                 "DSCR floor 1.25x and 65% ceiling.",
                 "minimum DSCR 1.25x, 65% maximum leverage.",
                 "Governor note: raised the ceiling to 55% maximum effective today."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a real governor declaration must NOT be silenced by the FP fix: %r -> %r"
            % (line, m.scan_line(line)))
    # A distant subject mention must not reach the ceiling's own value (veto is deliberately short).
    assert m.scan_line("vacancy 5% assumed; LTV ceiling 65%.") == \
        ["LTV ceiling 65% != canonical 40%"], \
        "a subject elsewhere on the line must not suppress a genuine ceiling"

    # THE VETO'S OWN REACH, pinned in both dimensions -- these were lost to the first cut of the
    # veto itself and found only by comparing against the 5-week baseline, not against HEAD.
    # (a) 'coverage' must NOT be a vetoing subject: DSCR is the debt-service-COVERAGE ratio, so it
    #     appears in genuine governor prose exactly where a paired LTV ceiling is declared.
    for line in ("Debt service coverage floor; 65% maximum governor.",
                 "Governor: coverage 1.30x; 65% ceiling.",
                 "Governor -- coverage-based sizing, 65% maximum.",
                 "Governor: debt service coverage 1.25x floor and 65% ceiling."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "'coverage' must not veto -- it is the DSCR's own word: %r -> %r"
            % (line, m.scan_line(line)))
    # (b) the reach must not cross a clause ender into the previous clause's subject.
    for line in ("Governor: assume 5% vacancy; leverage 55% maximum.",
                 "Governor: vacancy 5%; 55% maximum."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a previous clause's subject must not suppress this clause's ceiling: %r -> %r"
            % (line, m.scan_line(line)))
    print("  PASS test_ltv_subject_veto_does_not_silence_real_declarations_unit")


def test_ltv_subject_veto_reach_semantics_unit():
    """Pins the two defects the veto helper itself shipped with (2026-08-12, found in review).

    (a) A DECIMAL POINT IS NOT A CLAUSE ENDER. The first cut computed the clause boundary with a
        raw rfind('.'), so "2.5x" truncated the lookback window and cut the subject out of it --
        reopening the exact false-positive class this veto exists to close, on prose that is dense
        with decimal multiples precisely because it is DSCR-adjacent.

    (b) THE SUBJECT MUST END INSIDE THE WINDOW, and must not be separated from the value by a bound
        word. The first cut accepted any subject merely OVERLAPPING the window, which stretched
        suppression past the helper's own stated theory ("the subject sits immediately before the
        value") and silenced a line that flagged at baseline. An intervening ceiling word means the
        value binds to the ceiling, not to the subject."""
    m = _load_probe_module()
    for line in ("DSCR 1.25x minimum, vacancy at 2.5x turnover 10% maximum.",
                 "TI cap 1.5x factor, 12% maximum of TDC on a DSCR floor 1.25x basis."):
        assert m.scan_line(line) == [], (
            "a decimal must not be read as a clause ender: %r -> %r" % (line, m.scan_line(line)))
    for line in ("Governor: at 95% occupancy the ceiling is 65% maximum.",):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a bound word between subject and value means the value is the ceiling: %r -> %r"
            % (line, m.scan_line(line)))

    # (c) AN INTERVENING PERCENT DISPROVES OWNERSHIP. The subject owns that earlier figure, so the
    # later one is still a ceiling. Without this the veto leapfrogs a real figure -- the same
    # failure the refi machinery's percent-free gaps exist to prevent. These are the "and" form of
    # the clause-crossing lines already pinned above: swap the semicolon for "and" and, before this
    # guard, the line went dark.
    for line in ("Governor: vacancy 5% assumed and 65% maximum.",
                 "Governor: vacancy 8% and 65% maximum leverage.",
                 "Governor: vacancy .5% assumed and 65% maximum."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "an intervening percent means the subject owns the EARLIER figure, so this one must "
            "still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_subject_veto_reach_semantics_unit")


def test_ltv_house_separator_styles_still_flag_unit():
    """The arming-gate doctrine comment explicitly blesses ',' ':' and the house '--' style as
    plausible governor DECLARATIONS. An earlier cut of this fix tightened the anchor gap to
    exclude them, which silenced exactly the phrasings that comment protects; that tightening was
    reverted in favour of the subject veto. Pinned so it is not reintroduced."""
    m = _load_probe_module()
    for line in ("LTV -- hard ceiling 75%", "LTV: hard ceiling 55%.", "LTV, hard ceiling, 75%",
                 "LTV ceiling, revised, 65%"):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "house separator style must still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_house_separator_styles_still_flag_unit")


def test_ltv_anchor_window_respects_the_subject_veto_unit():
    """FP CLASS CLOSED (2026-08-12, same review), second mechanism. RE_LTV_ANCHOR can bind a
    ceiling word that belongs to a different noun ("LTV steady, maximum TI 12% of TDC"), and the
    anchor's 40-char window then read that subject's percentage as the declared LTV ceiling.

    Fixed with the same subject veto as the reverse pass, NOT by tightening the anchor gap: an
    earlier cut did tighten it (two adjacent words, no comma, no 'governor' token) and thereby
    silenced the ',' ':' and house '--' separator styles that the arming-gate doctrine comment
    explicitly protects -- see test_ltv_house_separator_styles_still_flag_unit."""
    m = _load_probe_module()
    for line in ("Governor note: LTV steady, maximum TI 12% of TDC.",
                 "LTV governor maximum vacancy 10% assumed."):
        assert m.scan_line(line) == [], (
            "a percentage owned by a non-LTV subject must not be read as the anchored LTV "
            "ceiling: %r -> %r"
            % (line, m.scan_line(line)))
    # Genuine qualifier forms must survive -- this is the gap the 08-12 change existed to close.
    for line in ("LTV hard ceiling 75% on an aggregate basis.",
                 "LTV absolute maximum 75% is the acquisition governor.",
                 "Acquisition governor: LTV ceiling 65%."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "adjectival-qualifier LTV ceiling must still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_anchor_window_respects_the_subject_veto_unit")


def test_ltv_extractor_spans_intervening_qualifier_unit():
    """GAP 2 CLOSED (2026-08-12). "LTV hard ceiling 75%" was ARMED all along -- "hard ceiling" is a
    GOV_KEYWORDS token (N6) -- but yielded nothing, because the EXTRACTOR RE_LTV_ANCHOR required
    contiguous "ltv ceiling" (\\s* only), so the qualifier defeated it. The 2026-08-11 revision
    blamed the arming gate; independent review corrected the attribution to the extractors, and
    this closes it there.

    Widening the extractor is safe with respect to the ratified 65% refi-ceiling false positive
    that caused the earlier revert, because that line is gated out by ARMING, not by extraction --
    pinned by test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit, which must keep
    passing alongside this."""
    m = _load_probe_module()
    out = m.scan_line("LTV hard ceiling 75% on an aggregate basis.")
    assert any("LTV" in o for o in out), (
        "drifted LTV ceiling with an intervening qualifier must flag: %r" % (out,))
    assert m.scan_line("LTV hard ceiling 40% on an aggregate basis.") == [], \
        "canonical LTV ceiling in the same shape must stay clean"

    # BOUNDARY, asserted deliberately: extraction is only half the requirement -- the line must
    # ALSO be armed. "LTV absolute maximum 75%" carries no GOV_KEYWORDS token (unlike "hard
    # ceiling", N6), so it stays clean even though the widened extractor can now read it. This is
    # the arming gate working as designed, NOT a residual extractor bug: closing it would require
    # widening LTV ARMING, which is the change that false-positived on the ratified 65%
    # per-property refi ceiling and was reverted. Documented so the next reader does not "fix"
    # this by reopening that hole.
    assert m.scan_line("LTV absolute maximum 75% on an aggregate basis.") == [], (
        "unarmed LTV prose must stay clean -- widening LTV ARMING is the reverted change")
    print("  PASS test_ltv_extractor_spans_intervening_qualifier_unit")


def test_intervening_qualifier_canonical_stays_clean_unit():
    """Arming the line must not by itself create a finding: canonical values stay clean."""
    m = _load_probe_module()
    assert m.scan_line("DSCR hard floor 1.25x per property.") == [], "canonical must stay clean"
    print("  PASS test_intervening_qualifier_canonical_stays_clean_unit")


def test_qualifier_gate_requires_the_metric_token_unit():
    """PRECISION GUARDRAIL: the fix must pair the METRIC token with its floor/ceiling word, never
    admit a bare 'hard floor' as a governor signal -- 'hard floor' is also a physical building
    term, and a standalone keyword would arm unrelated property prose.

    Also pins ALL FOUR clause enders. Excluding only '.' was not enough: ';' '!' and '?' each let
    the gap cross into an unrelated rent/area figure that RE_DSCR_THRESH then captured as a DSCR
    threshold -- a NEW false positive introduced by the first cut of this fix and caught in
    independent review, not by the suite. One case per boundary character, so a future narrowing of
    the gap class fails here rather than in a whole-tree scan."""
    m = _load_probe_module()
    for line in ("Suite B has a hard floor and a 32.0 ft clear-height ceiling.",
                 "The tenant's hard floor covers 1.40 acres of the yard.",
                 "The deal's actual DSCR came in at 1.42 last quarter.",
                 "DSCR is disclosed quarterly. The rent floor is 1.40 psf.",
                 "DSCR fine; rent floor is 1.40 psf.",
                 "DSCR solid! The rent floor is 1.40 psf.",
                 "DSCR ok? The rent floor is 1.40 psf.",
                 "DSCR steady; unit floor area 1.40 acres."):
        assert m.scan_line(line) == [], (
            "non-governor prose must NOT be armed by the qualifier fix: %r -> %r"
            % (line, m.scan_line(line)))
    print("  PASS test_qualifier_gate_requires_the_metric_token_unit")


def test_stabilization_conditioned_covenant_suppressed_unit():
    """2026-08-15 FP fix: a deal-pipeline row narrating ONE deal's LENDER covenant that only
    clears at stabilization -- "transition-year DSCR breaches (clears the 1.75x floor only at
    Yr3+ stabilization) -> all-cash close mandatory" (the live projects.md shape) -- is the
    property's own projected DSCR against a deal-specific loan covenant, NOT a restatement of
    the canonical acquisition governor. It armed _is_gov via the dscr..value..floor pairing and
    flagged in BOTH the 1.75 sentinel and the equality pass; no existing suppressor (portfolio,
    refi, correction) caught it. Must now scan clean."""
    m = _load_probe_module()
    clean = [
        # paraphrase of the actual projects.md:27 fragment (deal name elided):
        "Substantive: transition-year DSCR breaches (clears the 1.75x floor only at Yr3+ "
        "stabilization) → all-cash close mandatory; anchor tenant ~50% of rents rolls 5/2027.",
        # same covenant shape, non-sentinel value + lease-up wording:
        "Lender covenant: projected DSCR clears the 1.40x floor only after lease-up "
        "stabilization in year 3.",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "stabilization-conditioned deal covenant must be suppressed; line=%r got=%r"
            % (line[:90], out))
    print("  PASS test_stabilization_conditioned_covenant_suppressed_unit")


def test_stabilization_language_does_not_mask_governor_drift_unit():
    """REFUTE guard for the fix above -- the test that catches an overly-broad suppression: the
    SAME stabilization language plus an explicit acquisition-governor marker (or the value
    declared AS the governor) is a REAL governor drift dressed up in stabilization words, and
    must STILL flag."""
    m = _load_probe_module()
    # ACQ_GOV_MARKERS veto ("hard acquisition governor" / "dscr floor"):
    out1 = m.scan_line("Hard acquisition governor: DSCR floor 1.75x, even at Yr3+ stabilization.")
    assert any("1.75" in o for o in out1), (
        "acq-governor marker must veto stabilization suppression; got %r" % out1)
    out2 = m.scan_line("Per-deal DSCR floor now 1.40x once the asset reaches stabilization.")
    assert any("1.40" in o for o in out2), (
        "per-deal marker must veto stabilization suppression; got %r" % out2)
    # value declared AS the governor nearby (within the _refi_qualified-precedent +40 reach):
    out3 = m.scan_line("DSCR clears 1.40x at stabilization (the governor).")
    assert any("1.40" in o for o in out3), (
        "a value declared AS the governor must not be masked by stabilization words; got %r" % out3)
    print("  PASS test_stabilization_language_does_not_mask_governor_drift_unit")


def test_stabilization_qualifier_does_not_mask_reversed_word_order_unit():
    """2026-08-15 REFUTE remediation (holes 1/2/5/7): "DSCR minimum" (metric-then-bound-word,
    reversed from the "minimum dscr"/"min dscr" literals in ACQ_GOV_MARKERS) arms is_gov via
    RE_GOV_DSCR_BOUND but escaped every marker veto, so _stabilization_qualified silently
    suppressed REAL governor declarations. Fixed structurally: RE_GOV_DSCR_BOUND matching
    anywhere on the line vetoes stabilization suppression -- the declaration shape pairs metric
    and bound-word directly, while the legitimate covenant narration puts the VALUE between
    them ("clears the 1.75x floor"), whose decimal point RE_GOV_DSCR_BOUND cannot cross."""
    m = _load_probe_module()
    # hole 1 -- reversed word order, non-sentinel drift value:
    out = m.scan_line("DSCR minimum raised to 1.40x at stabilization.")
    assert any("1.40" in o for o in out), (
        "reversed-order 'DSCR minimum' declaration must flag despite stabilization word; got %r" % out)
    # hole 2 -- same gap masking the historical 1.75 drift sentinel itself (worst case):
    out = m.scan_line("DSCR minimum 1.75x during lease-up only.")
    assert any("1.75" in o for o in out), (
        "reversed-order declaration must not mask the 1.75 sentinel; got %r" % out)
    # hole 5 -- 'yr3' used in an unrelated exit-cap-timing sense inside the proximity window:
    out = m.scan_line("Yr3 exit cap 7.0%; DSCR minimum 1.40x.")
    assert any("1.40" in o for o in out), (
        "exit-cap 'Yr3' must not qualify a separate declared minimum for suppression; got %r" % out)
    # hole 7 -- multi-value line: the qualifier modifies the FIRST (legitimate) value but the
    # proximity window also swallowed the SECOND (drifted) value in the next clause:
    out = m.scan_line("Covenant clears 1.75x at Yr3 stabilization; DSCR minimum now 1.40x.")
    assert any("1.40" in o for o in out), (
        "a drifted declaration in the next clause must flag even beside a covenant value; got %r" % out)
    print("  PASS test_stabilization_qualifier_does_not_mask_reversed_word_order_unit")


def test_stabilization_qualifier_veto_covers_arming_vocabulary_unit():
    """2026-08-15 REFUTE remediation (holes 3/4): "hard cap"/"self-imposed"/"disqualif" ARM
    is_gov (GOV_KEYWORDS) but were absent from the suppressor's veto list, so a governor
    declaration whose only signal was one of them was suppressible by a nearby lease-up word.
    Fixed by STAB_GOV_MARKERS -- the stabilization suppressor's veto vocabulary is a superset
    of the arming vocabulary (scoped to this suppressor only; the shared ACQ_GOV_MARKERS is
    unchanged because ratified refi doctrine legitimately writes "self-imposed ... post-close"
    sizing caps, pinned by test_reverse_order_refi_suppression_unit)."""
    m = _load_probe_module()
    # hole 3 -- "hard cap" + "self-imposed" arm but did not veto:
    out = m.scan_line("Self-imposed hard cap: DSCR 1.10x during lease-up.")
    assert any("1.10" in o for o in out), (
        "'hard cap'/'self-imposed' governor declaration must flag despite lease-up word; got %r" % out)
    # hole 4 -- "disqualif" arms but did not veto:
    out = m.scan_line("DSCR below 1.10x disqualified pre-stabilization.")
    assert any("1.10" in o for o in out), (
        "'disqualif' governor declaration must flag despite stabilization word; got %r" % out)
    print("  PASS test_stabilization_qualifier_veto_covers_arming_vocabulary_unit")


def test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit():
    """2026-08-15 REFUTE remediation (hole 6, worst surface): the bare-substring qualifier
    "year 2" matched INSIDE "year 2026" (any "year 20xx" date), so ordinary dated doctrine
    prose near a DSCR value qualified for suppression across the whole memory/skill tree.
    Fixed: year tokens are now the digit-bounded RE_STAB_YEAR regex (digit 1-3, not followed
    by another digit), so dates can never qualify while genuine "Yr3+"/"year 3" lease-up
    framing still can."""
    m = _load_probe_module()
    out = m.scan_line("Fiscal year 2026 doctrine: DSCR minimum now 1.40x.")
    assert any("1.40" in o for o in out), (
        "'year 2026' date must not qualify a drifted declaration for suppression; got %r" % out)
    # boundary semantics of the replacement regex itself:
    assert m.RE_STAB_YEAR.search("year 2026") is None, "date 'year 2026' must not match RE_STAB_YEAR"
    assert m.RE_STAB_YEAR.search("only at yr3+ stabilization") is not None, (
        "'yr3+' lease-up framing must still match RE_STAB_YEAR")
    assert m.RE_STAB_YEAR.search("stabilization in year 3.") is not None, (
        "'year 3' lease-up framing must still match RE_STAB_YEAR")
    print("  PASS test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit")


# Real trigger line, quoted VERBATIM (not simplified) from acquisition-underwriting SKILL.md v4.13
# changelog (line 15, as of 2026-08-22) -- both false positives fixed below live on this ONE line.
# This exact failure was overridden via allow-hook-test-failure tokens by 6 distinct sessions in the
# 24h before the fix (2026-08-22, session 438b62fb-30d2-43f3-b1ad-d86ecbcfb749, human-authorized).
REAL_V413_CHANGELOG_LINE = (
    "**v4.13 (2026-08-22):** **Refi rate default cut 7.00% → 6.50%** (Gabriel, in-turn "
    "instruction 2026-08-22). Single-input change to the UNDERWRITING CONVENTIONS refi paragraph. "
    "The ±25 bp band moves with the base (6.75–7.25% → **6.25–6.75%**) because "
    "the band is derived from the base, not set independently — the +25 bp "
    "sub-$2M/single-tenant and −25 bp stabilized-multi-tenant-≥1.40x adjustments are "
    "unchanged in magnitude. Consumers updated to match: `references/ic-memo-structure.md` §7 "
    "Debt & Capital Structure, and the v4.3 rate/refi-shock-bear sentence in the same paragraph. "
    "**One second-order consequence flagged rather than silently inherited:** the paragraph's "
    "long-standing observation that \"DSCR ≥1.25x is typically the more frequently binding "
    "constraint\" was calibrated at 7.00%; a 6.50% coupon on 25-yr amort cuts annual debt service "
    "~4.5% at the same loan amount, so DSCR binds less often and the 65% LTV ceiling binds more "
    "often. The paragraph now carries that caveat and instructs a per-deal test instead of the "
    "inherited heuristic. **No scorecard weight, Stage 1 floor, or governor constant (DSCR 1.25x / "
    "per-property LTV 65% / portfolio-aggregate LTV 40%) changed** — the coupon is an "
    "assumption, not a governor, and the DSCR ≥1.25x floor itself is untouched. Not re-derived "
    "from a lender quote or an index; re-confirm at the annual December back-test alongside the "
    "rest of the 2026 defaults. Downstream note: any workbook built on the prior 7.00% Inputs-tab "
    "value carries a stale refi rate — re-run rather than assume parity."
)


def test_v413_changelog_line_clean_unit():
    """REGRESSION PIN (2026-08-22): the real acquisition-underwriting SKILL.md v4.13 changelog line
    (line 15) must scan fully clean. Prior to this fix it produced TWO false positives on this one
    line: 'DSCR governor threshold 1.40x != canonical 1.25x' (the stabilized-multi-tenant rate-tier
    label) and 'LTV governor 65% != canonical 40%' (the mid-sentence LTV-ceiling mention). This is
    the exact line that blocked git-prepush-doctrine-gate.py and was overridden 6 times in 24h
    before the underlying probe bug was fixed."""
    m = _load_probe_module()
    out = m.scan_line(REAL_V413_CHANGELOG_LINE)
    assert out == [], (
        "the real v4.13 changelog line must scan clean; got %r" % out)
    print("  PASS test_v413_changelog_line_clean_unit")


def test_dscr_rate_tier_bucket_label_not_flagged_as_governor_unit():
    """2026-08-22 FP fix, root cause 1: a refi rate-tier BUCKET LABEL hyphen-glued to its DSCR
    threshold ("stabilized-multi-tenant-≥1.40x") names WHICH rate-adjustment bucket a property
    falls into -- it is not a DSCR floor/governor restatement, mirroring the sibling "+25 bp
    sub-$2M/single-tenant" tier beside it. RE_DSCR_DECL's bare comparator+x match has no concept of
    subject and read it as a governor declaration; the intended suppressors
    (_refi_qualified/_stabilization_qualified) exist for exactly this shape but their veto check is
    WHOLE-LINE, so an unrelated 'per-property' mention elsewhere in the same dense paragraph (the
    line's own correct closing restatement) vetoed the suppression by accident. Isolated from the
    LTV false positive (test_ltv_ceiling_reaffirmed_elsewhere_in_paragraph_suppressed_unit covers
    that one) by trimming the real line down to only the DSCR-tier-label clause plus enough of the
    real closing sentence to reproduce the whole-line veto collision."""
    m = _load_probe_module()
    line = (
        "Refi rate default cut. The +25 bp sub-$2M/single-tenant and −25 bp "
        "stabilized-multi-tenant-≥1.40x adjustments are unchanged in magnitude. No scorecard "
        "weight, Stage 1 floor, or governor constant (DSCR 1.25x / per-property LTV 65% / "
        "portfolio-aggregate LTV 40%) changed."
    )
    out = m.scan_line(line)
    assert not any("1.40" in o for o in out), (
        "DSCR-tier bucket label 'word-word-≥N.NNx' must not be misread as a governor "
        "restatement even when an unrelated 'per-property' token sits elsewhere on the same line; "
        "got %r" % out)
    print("  PASS test_dscr_rate_tier_bucket_label_not_flagged_as_governor_unit")


def test_dscr_rate_tier_bucket_label_veto_when_declared_as_governor_unit():
    """ANTI-BLINDING (mirrors test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit):
    a REAL DSCR drift dressed up in the tier-bucket-label shape must still flag.
    _governor_declared_nearby is PROXIMITY-scoped (unlike the whole-line STAB/ACQ_GOV_MARKERS
    checks this fix works around), so a 'governor' token sitting close to the value still vetoes
    suppression."""
    m = _load_probe_module()
    line = ("Refi note: acquisition governor: stabilized-multi-tenant-≥1.40x for every deal.")
    out = m.scan_line(line)
    assert any("1.40" in o for o in out), (
        "a DSCR drift declared AS the governor nearby must still flag despite the tier-label "
        "shape; got %r" % out)
    print("  PASS test_dscr_rate_tier_bucket_label_veto_when_declared_as_governor_unit")


def test_ltv_ceiling_reaffirmed_elsewhere_in_paragraph_suppressed_unit():
    """2026-08-22 FP fix, root cause 2: '65% LTV ceiling' mentioned mid-sentence with no
    'per-property' token nearby (real text: 'so DSCR binds less often and the 65% LTV ceiling binds
    more often') is the SAME ratified per-property governor as the line's own closing restatement
    ('per-property LTV 65% / portfolio-aggregate LTV 40%'). The existing pairing suppressor
    (_perprop_portfolio_paired_veto_spans) only recognizes the pairing when both members sit close
    together on one RE_LTV_NEAR match -- it does not reach a DIFFERENT, earlier mention of the same
    65% figure elsewhere on the line. _line_reaffirms_ratified_ltv_pair() closes that gap: if the
    line contains the tight, correctly-paired restatement ANYWHERE, any other value-locked (== 65)
    LTV-ceiling mention on the same line is recognized as the same governor, not independent drift.
    Value-locked and companion-anchored exactly like the existing pairing check -- see
    test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_real_drift_unit and
    test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_governor_declared_drift_unit for the two
    ways this stays tight."""
    m = _load_probe_module()
    line = ("so DSCR binds less often and the 65% LTV ceiling binds more often. No scorecard "
            "weight, Stage 1 floor, or governor constant (DSCR 1.25x / per-property LTV 65% / "
            "portfolio-aggregate LTV 40%) changed.")
    out = m.scan_line(line)
    assert not any("65" in o for o in out), (
        "'65%% LTV ceiling' reaffirmed elsewhere on the same line as the ratified per-property/"
        "portfolio-aggregate pairing must not flag as independent drift; got %r" % out)
    print("  PASS test_ltv_ceiling_reaffirmed_elsewhere_in_paragraph_suppressed_unit")


def test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_real_drift_unit():
    """VALUE-LOCK: a genuinely drifted LTV ceiling (not 65) sharing a line with the ratified pairing
    must still flag -- the reaffirmation check only ever recognizes the literal ratified 65, exactly
    like the pre-existing pairing/frame suppressors it extends."""
    m = _load_probe_module()
    line = ("so DSCR binds less often and the 70% LTV ceiling binds more often. No scorecard "
            "weight, Stage 1 floor, or governor constant (DSCR 1.25x / per-property LTV 65% / "
            "portfolio-aggregate LTV 40%) changed.")
    out = m.scan_line(line)
    assert any("70" in o for o in out), (
        "a drifted 70%% LTV ceiling must still flag despite a ratified pairing elsewhere on the "
        "line; got %r" % out)
    print("  PASS test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_real_drift_unit")


def test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_governor_declared_drift_unit():
    """ANTI-BLINDING (mirrors test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit):
    a 65% LTV figure explicitly MISLABELED as the acquisition governor must still flag even when the
    ratified pairing sits elsewhere on the same line -- _governor_declared_nearby is evaluated at
    THIS value's own position, so a nearby 'acquisition governor' declaration vetoes the new
    suppression exactly as it already vetoes the standalone-frame and pairing suppressors."""
    m = _load_probe_module()
    line = ("Hard filter: 65% LTV is now the acquisition governor, while per-property LTV 65% / "
            "portfolio-aggregate LTV 40% remains correct elsewhere.")
    out = m.scan_line(line)
    assert any("65" in o for o in out), (
        "a 65%% LTV figure declared AS the acquisition governor must still flag despite a ratified "
        "pairing elsewhere on the line; got %r" % out)
    print("  PASS test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_governor_declared_drift_unit")


def test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_aggregate_drift_unit():
    """ANTI-BLINDING (independent review finding, 2026-08-22, session 438b62fb): the CATASTROPHIC
    case for the reaffirmation suppressor is a partial-edit drift line that naturally quotes the OLD
    correct pairing alongside a genuinely wrong NEW aggregate figure -- the 40%-governor drifted TO
    65% (the single most plausible wrong value, since 65 is itself a legitimate ratified number one
    level down). Each of these must still flag despite the ratified pairing sitting later on the
    same line, because THIS occurrence is asserted in the same clause as an 'aggregate'/'portfolio'
    subject:"""
    m = _load_probe_module()
    lines = (
        "Aggregate LTV ceiling raised to 65% effective today; doctrine had read per-property LTV "
        "65% / portfolio-aggregate LTV 40%.",
        "Portfolio-aggregate LTV ceiling 65%; per-property LTV 65% / portfolio-aggregate LTV 40% "
        "was the prior reading.",
        "Governor: size the whole portfolio to 65% maximum; per-property LTV 65% / "
        "portfolio-aggregate LTV 40% no longer applies.",
    )
    for line in lines:
        out = m.scan_line(line)
        assert any("65" in o for o in out), (
            "an aggregate/portfolio-labelled 65%% ceiling must still flag despite a ratified "
            "pairing elsewhere on the line; line=%r got=%r" % (line, out))
    print("  PASS test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_aggregate_drift_unit")


def test_eval_harness_floor_result_narration_clean_unit():
    """2026-08-23 FP fix: an auto-generated eval-harness run log narrates a deal's floor-check
    VERDICT -- the ACHIEVED DSCR quoted against the canonical 1.25x floor, computed at the ratified
    65%-LTV per-property refi-sizing basis. Both figures are doctrine-correct (1.42x/1.48x is the
    underwriting RESULT, 65% is CANON_LTV_PERPROPERTY, and the canonical floor is restated
    correctly on the same line), so neither may flag. The two lines below are VERBATIM the live
    triggers (ora-skills/acquisition-underwriting-eval-harness/runs/
    2026-08-23T171623Z_scheduled-poll.json:399 and :195, including the surrounding JSON quoting);
    :195 additionally proves the construct-specific suppressor is needed even where
    RE_REFI_SIZING_NAMED matches, because ACQ_DECL_NEARBY's 'floor' token sits inside this
    phrasing's own canonical anchor and vetoes the shared refi-member suppression."""
    m = _load_probe_module()
    lines = (
        '          "FLOOR-FLAGGED - Basis floor BREACHED (57.3% discount vs 60% floor); Yield '
        'floor BREACHED (7.53% YoC vs 8.0% floor); DSCR floor PASSES (1.42x vs 1.25x floor at '
        '65%-LTV sizing, LTV binds); GATE-FLAGGED on size",',
        '          "FLOOR-FLAGGED - Basis floor FAIL (54.3% discount); Yield floor FAIL (5.99% '
        'YoC vs 8.0% floor); DSCR floor PASS (1.48x vs 1.25x floor at 65%-LTV refi sizing, LTV '
        'binds)",',
    )
    for line in lines:
        out = m.scan_line(line)
        assert out == [], (
            "eval-harness floor-result narration is doctrine-correct and must be clean; "
            "line=%r got=%r" % (line, out))
    print("  PASS test_eval_harness_floor_result_narration_clean_unit")


def test_floor_result_narration_does_not_mask_drift_unit():
    """ANTI-BLINDING for the floor-result suppressor: every guard that keeps it from becoming a
    blind spot, exercised one at a time. Each variant looks like the suppressed construct but
    carries a REAL drift (or a declaration), and must still flag."""
    m = _load_probe_module()
    # (a) CANONICAL ANCHOR: a drifted floor RESTATEMENT ("vs 1.40x floor") matches neither regex,
    #     so the achieved value, the drifted restatement, AND the sizing LTV all stay visible.
    out = m.scan_line('"DSCR floor PASSES (1.42x vs 1.40x floor at 65%-LTV sizing, LTV binds)"')
    assert any("DSCR" in o and "1.40" in o for o in out), (
        "drifted canonical restatement 1.40x must still flag; got %r" % out)
    assert any("LTV" in o and "65" in o for o in out), (
        "without the canonical anchor the 65%% LTV lock must not engage; got %r" % out)
    # (b) VALUE-LOCK: a drifted sizing basis (80% is not the ratified per-property 65) still flags.
    #     Only the LTV finding is asserted: the achieved-DSCR member (1.42x) stays suppressed here
    #     by design -- its own construct (vs-canonical-floor) is intact and independent of the LTV
    #     lock, and the line still goes red via the 80. Expected/acceptable, not an oversight
    #     (round-2 review non-blocking note).
    out = m.scan_line('"DSCR floor PASSES (1.42x vs 1.25x floor at 80%-LTV sizing, LTV binds)"')
    assert any("LTV" in o and "80" in o for o in out), (
        "non-ratified sizing LTV 80%% must still flag (value-lock); got %r" % out)
    # (c) DECL-SHAPE VETO: a declaration dressed in the construct's word order -- pivot-bound
    #     ("raised to 1.42x") and keyword-bound ("floor 1.42x") -- still flags even with a result
    #     verb adjacent, because the value's span is also bound by a declaration-shaped extractor.
    out = m.scan_line("Governor update: DSCR floor raised to 1.42x vs 1.25x floor -- passes")
    assert any("DSCR" in o and "1.42" in o for o in out), (
        "pivot-declared 1.42x must still flag despite the vs-canonical tail; got %r" % out)
    out = m.scan_line("DSCR floor 1.42x vs 1.25x floor -- clears")
    assert any("DSCR" in o and "1.42" in o for o in out), (
        "keyword-declared 1.42x must still flag despite the vs-canonical tail; got %r" % out)
    # (d) RESULT-VERB GATE: the same word order with NO verdict verb is not a harness narration
    #     ("previously" reads as a drift report) and still flags.
    out = m.scan_line("DSCR governor: 1.42x vs 1.25x floor previously")
    assert any("DSCR" in o and "1.42" in o for o in out), (
        "verb-less vs-canonical construct must still flag; got %r" % out)
    # (e) GOVERNOR-TOKEN VETO: the sizing 65 declared AS the governor nearby still flags.
    out = m.scan_line(
        '"DSCR floor PASSES (1.42x vs 1.25x floor at 65%-LTV sizing, the governor now)"')
    assert any("LTV" in o and "65" in o for o in out), (
        "65 declared AS the governor must still flag; got %r" % out)
    # (f) AGGREGATE-CLAUSE VETO: a 65 asserted in the same clause as an aggregate/portfolio
    #     subject is (plausibly) the 40%-aggregate governor drifted TO 65 -- still flags.
    out = m.scan_line(
        '"DSCR floor PASSES (1.42x vs 1.25x floor at 65%-LTV sizing for the aggregate portfolio)"')
    assert any("LTV" in o and "65" in o for o in out), (
        "aggregate-clause 65 must still flag; got %r" % out)
    print("  PASS test_floor_result_narration_does_not_mask_drift_unit")


def test_floor_result_round2_declaration_tokens_still_veto_unit():
    """Round-2 independent review, Finding 1 (2026-08-23): the first cut of the floor-result
    governor veto dropped the WHOLE ACQ_DECL_NEARBY list instead of only the two floor-family
    tokens that collide with the construct's own canonical anchor -- silencing lines HEAD flagged.
    Every remaining declaration token must veto suppression for BOTH members: a "hard ceiling"/
    "hard cap"/"acquisition"/"buy-box"/"hard filter" phrase hung off the construct means one of
    its values is being declared AS the governor, so the achieved DSCR AND the sizing 65 both
    stay visible (the veto is whole-construct-scoped -- the token sits ~40+ chars from the
    achieved value but well inside the construct window)."""
    m = _load_probe_module()
    tails = ("the hard ceiling", "the hard cap", "our acquisition ceiling",
             "the buy-box ceiling", "the hard filter")
    for tail in tails:
        line = ('"DSCR floor PASSES (1.42x vs 1.25x floor at 65%%-LTV sizing, %s)"' % tail)
        out = m.scan_line(line)
        assert any("DSCR" in o and "1.42" in o for o in out), (
            "achieved 1.42x must flag when %r is declared on the construct; got %r" % (tail, out))
        assert any("LTV" in o and "65" in o for o in out), (
            "sizing 65%% must flag when %r is declared on the construct; got %r" % (tail, out))
    print("  PASS test_floor_result_round2_declaration_tokens_still_veto_unit")


def test_floor_result_round2_binder_declarations_still_flag_unit():
    """Round-2 independent review, Finding 2 (2026-08-23): copula/binder-bound declarations
    ("DSCR floor is 1.42x vs 1.25x floor") are the module's own documented I-2 canonical-decoy
    class, and none of the extractor-shaped spans (pivot/keyword-abutting/from-to) bind them --
    so the first cut suppressed them whenever a result verb sat nearby. The KEYWORD-DIRECT-BIND
    veto (round-3 restructuring of round-2's enumerated binder list -- see
    _floor_kw_binds_value_directly) must keep every one of these flagging: a same-clause
    floor-keyword within reach of the value suppresses ONLY when the verdict verb sits wholly
    BETWEEN them, and the genuine harness construct always interposes exactly that ("floor
    PASSES (1.42x"), which no binder shape can match. The last case also pins the bare-'clear'
    removal from the result-verb gate: clear-height prose ("28 ft clear") must not arm
    suppression of a copula declaration."""
    m = _load_probe_module()
    lines = (
        "DSCR floor is 1.42x vs 1.25x floor; deal passes.",
        "Deal PASS: DSCR floor is 1.42x vs 1.25x floor.",
        "DSCR floor at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor = 1.42x vs 1.25x floor -- passes.",
        "Spec: 28 ft clear. DSCR floor is 1.42x vs 1.25x floor.",
    )
    for line in lines:
        out = m.scan_line(line)
        assert any("DSCR" in o and "1.42" in o for o in out), (
            "binder-bound declared 1.42x must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_floor_result_round2_binder_declarations_still_flag_unit")


def test_floor_result_round3_verbphrase_binders_still_flag_unit():
    """Round-3 independent review (2026-08-23): enumerating binder TOKENS was structurally
    unclosable -- any VERB-PHRASE binder falls outside a finite list ("set" is even already in
    the module's own _CHANGE_VERB, but _PIVOT only covers "set TO", not "set at"). The
    keyword-direct-bind veto INVERTS the test instead of growing the list: when the nearest
    floor-keyword before the candidate value sits in the same clause, suppression REQUIRES a
    verdict verb wholly between keyword and value -- which only the genuine harness narration
    shape satisfies ("floor PASSES (1.42x", "floor PASS (1.48x"). Every verb-phrase declaration
    below therefore flags, known or novel, with no enumeration. The trailing "-- passes" on
    each line is the adversarial part: a result verb near the construct must NOT rescue
    suppression when it does not sit between keyword and value. (A 24-char reach cap pinned by
    an earlier revision of this test was deleted in round 4 -- see
    test_floor_result_round4_distant_keyword_declarations_still_flag_unit.)"""
    m = _load_probe_module()
    lines = (
        "DSCR floor set at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor stands at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor sits at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor now sits at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor pegged at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor held at 1.42x vs 1.25x floor -- passes.",
        "DSCR floor rises to 1.42x vs 1.25x floor -- passes.",
        "DSCR floor currently stands at 1.42x vs 1.25x floor -- passes.",
    )
    for line in lines:
        out = m.scan_line(line)
        assert any("DSCR" in o and "1.42" in o for o in out), (
            "verb-phrase-bound declared 1.42x must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_floor_result_round3_verbphrase_binders_still_flag_unit")


def test_floor_result_round4_distant_keyword_declarations_still_flag_unit():
    """Round-4 independent review (2026-08-23): the 24-char keyword reach cap created a
    suppression band just past it -- a declaration whose qualifier phrase pushes the value more
    than 24 chars from the keyword ("floor under the revised doctrine is 1.42x") slipped
    through, silently suppressed. The cap is DELETED, not widened: distance never protects a
    genuine narration (the verb-between requirement and the clause boundary do), so the veto now
    reaches the whole clause and no qualifier length can outrun it. The last case pins the
    plural/verb keyword form ("DSCR floors at 1.42x" -- 'floors' added to RE_DSCR_FLOOR_KW,
    round-4 non-blocking note): equally a declaration, equally flagged."""
    m = _load_probe_module()
    lines = (
        "DSCR floor under the revised doctrine is 1.42x vs 1.25x floor -- passes.",
        "DSCR floor effective next quarter is 1.42x vs 1.25x floor -- passes.",
        "DSCR floor per the updated standard is 1.42x vs 1.25x floor -- passes.",
        "DSCR floor for all deals henceforth is 1.42x vs 1.25x floor -- passes.",
        "DSCR floors at 1.42x vs 1.25x floor -- passes.",
    )
    for line in lines:
        out = m.scan_line(line)
        assert any("DSCR" in o and "1.42" in o for o in out), (
            "distant-keyword declared 1.42x must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_floor_result_round4_distant_keyword_declarations_still_flag_unit")


# Interim-checklist threshold wording (ora-skills PR #165, debt-management/references/
# ltv-interim-netting-checklist.md). The checklist's OPERATIVE 40% lives on two lines that carry no
# governor keyword and no "<=" comparator, so no pre-existing pass read them: a hand edit of the
# threshold to 55% was silent (reviewer finding, PR #165). Lines quoted from the PR branch.
_INTERIM_RESULT_LINE = ("- Result: strictly above %s (unrounded; never round down) is "
                        "**LTV-FLAGGED (portfolio)**: Gabriel signs off or the transaction is not accepted.")
_INTERIM_WORKSHEET_ROW = ("| 7 | Result = (1 + 3 + 5 loan − 6) / (2 − 4 + own value − "
                          "own value sold), vs %s |")


def test_interim_checklist_canonical_threshold_wording_stays_clean_unit():
    m = _load_probe_module()
    for line in (_INTERIM_RESULT_LINE % "40.00%", _INTERIM_RESULT_LINE % "40%",
                 _INTERIM_WORKSHEET_ROW % "40%", _INTERIM_WORKSHEET_ROW % "40.0%"):
        assert m.scan_line(line) == [], (
            "canonical interim-checklist threshold must not flag; line=%r got=%r"
            % (line, m.scan_line(line)))
    print("  PASS test_interim_checklist_canonical_threshold_wording_stays_clean_unit")


def test_interim_checklist_drifted_threshold_wording_flags_unit():
    m = _load_probe_module()
    for tpl in (_INTERIM_RESULT_LINE, _INTERIM_WORKSHEET_ROW):
        for bad in ("55.00%", "45%", "40.5%", "65%", "0.40%"):
            line = tpl % bad
            out = m.scan_line(line)
            assert len(out) == 1 and "canonical 40%" in out[0], (
                "drifted interim-checklist threshold %s must flag exactly once; line=%r got=%r"
                % (bad, line, out))
    # reverse word order and the other comparator verbs of the same construct
    for line in ("Flag: LTV-FLAGGED (portfolio) when the figure exceeds 50.00%.",
                 "Result: greater than 45% is LTV flagged for Gabriel.",
                 "Anything over 55% (unrounded) is **LTV-FLAGGED**."):
        assert m.scan_line(line), "drifted LTV-FLAGGED threshold must flag; line=%r" % line
    print("  PASS test_interim_checklist_drifted_threshold_wording_flags_unit")


def test_interim_checklist_extractor_does_not_flag_unrelated_prose_unit():
    m = _load_probe_module()
    for line in (
            "Vacancy above 10% over 12 months triggers a leasing review.",
            "Flag any tenant with arrears above 5% of rent as watch.",
            "| 2 | Result = NOI / debt service, vs 1.25x |",
            "| 3 | Occupancy = leased SF / total SF, vs 95% |",
            "The refi test is LTV-FLAGGED only for the portfolio; see the checklist.",
            "- Result: strictly above 40.00% is LTV-FLAGGED; per-property refi ceiling stays 65%.",
    ):
        assert m.scan_line(line) == [], (
            "unrelated prose / canonical dual statement must not flag; line=%r got=%r"
            % (line, m.scan_line(line)))
    print("  PASS test_interim_checklist_extractor_does_not_flag_unrelated_prose_unit")


def test_interim_checklist_refute_round1_false_negatives_closed_unit():
    """REFUTE round 1 (2026-10-27), C1-C3: each shape below hid a real drift."""
    m = _load_probe_module()
    must_flag = (
        # C1: 40 -> 65 on a PORTFOLIO flag line that also mentions per-property elsewhere on the line
        "Above 65% → **LTV-FLAGGED (portfolio)**: flag, never kill; the per-property refi ceiling is 65% per-property.",
        "Above 65% is an **LTV-FLAGGED (portfolio)** item requiring sign-off (per-property stays 65%).",
        # C2: a canonical 40% earlier on the line must not hide the drifted value after it
        "- Result: above 40% gross or above 55% netted is LTV-FLAGGED",
        "| 7 | Result = (1 + 3 + 5 loan − 6) / (2 − 4 + own value − own value sold), vs 40% / 55% |",
        # C3: markup, dash and wording variants of the same construct
        "- Result: strictly above **55%** is **LTV-FLAGGED (portfolio)**",
        "- Result: strictly above **55**% is LTV-FLAGGED",
        "- Result: strictly above 55% is LTV–FLAGGED",
        "- Result: strictly above 55% is LTV‑FLAGGED",
        "- Result: strictly above 55% is LTV_FLAGGED",
        "- Result: &gt; 55% is LTV-FLAGGED",
        "- Result: ≥ 55% is LTV-FLAGGED",
        "- Result: more than 55% is LTV-FLAGGED",
        "- Result: exceeding 55% is LTV-FLAGGED",
        "| 7 | Result = (1 + 3 + 5 loan − 6) / (2 − 4 + own value − own value sold), vs **55%** |",
        "| 7 | Result = (1 + 3 + 5 loan − 6) / (2 − 4 + own value − own value sold), versus 55% |",
        "| 7 | Result = (1 + 3 + 5 loans − 6) / (2 − 4 + own value − own value sold), vs 55% |",
    )
    for line in must_flag:
        assert m.scan_line(line), "drifted interim-checklist threshold must flag; line=%r" % line
    print("  PASS test_interim_checklist_refute_round1_false_negatives_closed_unit")


def test_interim_checklist_refute_round1_false_positive_guards_unit():
    """REFUTE round 1, C4/C6: each guard must be pinned by a line that would flag without it."""
    m = _load_probe_module()
    must_stay_clean = (
        # loan-token guard: a debt-yield / LTC / lender-max row shares the word 'loan'
        "| Debt yield | Result = NOI / loan, vs 10% |",
        "| 9 | Result = new loan / total value, vs 75% lender max |",
        "| 5 | Result = (loan + mezz) / cost, vs 80% LTC |",
        # flag STATISTIC, not the threshold
        "LTV flag rate over 30% of pipeline deals last year.",
        # the ratified per-property 65 stated as a comparator on a per-property flag line
        "A single asset above 65% per-property is LTV-flagged at the property level.",
        # canonical dual statement, canonical decoy on both sides
        "- Result: above 40% gross or above 40.00% netted is LTV-FLAGGED",
        # correction note: the corrected-away 55 is skipped, the live 40 is canonical
        "Corrected from 55% to 40%: above 40% is LTV-FLAGGED.",
    )
    for line in must_stay_clean:
        assert m.scan_line(line) == [], (
            "must not flag; line=%r got=%r" % (line, m.scan_line(line)))
    print("  PASS test_interim_checklist_refute_round1_false_positive_guards_unit")


_ROW_FORMULA = "Result = (1 + 3 + 5 loan − 6) / (2 − 4 + own value − own value sold)"


def test_interim_checklist_refute_round2_unit():
    """REFUTE round 2 (2026-10-27): every repro, both directions, plus a pin for each guard that
    survived mutation, the accepted loud-flag case, and a time bound (C11 was cubic)."""
    import time
    m = _load_probe_module()
    must_flag = (
        # C6: worksheet-row edits that dropped the row
        "| 7 | " + _ROW_FORMULA + ", vs 40% (gross) / 55% (netted, noi-neutral) |",
        "| 7 | " + _ROW_FORMULA.replace("value", "values") + ", vs 55% |",
        "| 7 | **Result** = (1 + 3 + 5 loan) / (2 own value), vs 55% |",
        "| 7 | Result: (1 + 3 + 5 loan) / (2 own value), vs 55% |",
        "| 7 | " + _ROW_FORMULA + " | vs 55% |",
        "| 7 | " + _ROW_FORMULA + " vs 55% |",
        "| 7 | " + _ROW_FORMULA + ", vs 40% | 55% |",
        # C5: 40 -> 65 with a per-property parenthetical right next to the value
        "Above 65% (per-property refi ceiling unchanged) → **LTV-FLAGGED (portfolio)**",
        # C3/C4: remaining variants
        "- Result: strictly above `55%` is LTV-FLAGGED",
        "- Result: in excess of 55% is LTV-FLAGGED",
        "- Result: beyond 55% is LTV-FLAGGED",
        ("- Result: strictly above 55% (unrounded; never round down, measured on the Oxford-share booked "
         "debt plus signed loans and the loan under test) is **LTV-FLAGGED (portfolio)**"),
        "LTV-FLAGGED when the result net of lender holdbacks exceeds 55%",
        # round-2 review N1-N3: the checklist's own wording and clause-bounded guards
        "- Result: strictly above 55% (Oxford-share, unrounded) is **LTV-FLAGGED (portfolio)**",
        "- Result: strictly above 55% (unrounded, i.e. never round down) is **LTV-FLAGGED (portfolio)**",
        "Hold DSCR at 1.25x; above 55% → **LTV-FLAGGED (portfolio)**",
        "LTV-FLAGGED (portfolio) when the yield-adjusted result exceeds 55%",
        # per-property marker FAR from the value does not veto a 65 on a flag line (pins veto distance)
        ("Above 65% is LTV-FLAGGED here; many words later in an unrelated clause the note mentions the "
         "per-property refi ceiling"),
    )
    for line in must_flag:
        assert m.scan_line(line), "drifted threshold must flag; line=%r" % line
    must_stay_clean = (
        # C7: dual-ceiling doctrine statements and ratios of other metrics
        "Per-property: above 65% → LTV-FLAGGED (property); portfolio: above 40% → LTV-FLAGGED (portfolio)",
        "A per-property LTV above 65% is LTV-FLAGGED; the portfolio aggregate test stays 40%.",
        "| Loan | LTC above 80% | LTV-FLAGGED if the lender also caps |",
        "Occupancy above 90% and LTV-FLAGGED deals are reviewed weekly.",
        "LTV-FLAGGED share over 25% of pipeline.",
        "Above 25% of pipeline deals are LTV-FLAGGED.",
        "Debt yield above 10% is an LTV-FLAGGED signal for the lender.",   # another ratio named in-clause
        # pins: the 'loan' token and the numeric range guard
        "| 4 | Result = equity / value, vs 55% |",
        "| 4 | Result = new loan / total value, vs 75% lender max |",
        # each formula guard alone (the whole-line 'loan' pre-gate is satisfied by the trailing note)
        "| 4 | Result = equity / value, vs 55% | note: no loan involved |",   # formula lacks 'loan'
        "| 4 | Result = loan / equity, vs 55% |",                            # formula lacks 'value'
        "| 4 | Result = loan x value, vs 55% |",                              # formula lacks '/'
        "| 4 | Result = noi / (loan value), vs 55% |",                        # other-ratio word in formula
        # sentence boundary: a flag term in the NEXT sentence is not this threshold
        "Above 55% of gross revenue is the target. LTV-FLAGGED deals are reviewed weekly.",
        "- Result: above 0% is LTV-FLAGGED",
        "- Result: above 150% is LTV-FLAGGED",
    )
    for line in must_stay_clean:
        assert m.scan_line(line) == [], "must not flag; line=%r got=%r" % (line, m.scan_line(line))
    # C8: accepted LOUD flag -- a changelog line narrating an old comparator value is reworded, not skipped
    assert m.scan_line("v1.7: corrected the LTV-FLAGGED trigger from over 45% to over 40% (typo)."), (
        "narrated old comparator value flags loudly by design")
    # C11: linear time on adversarial long lines
    t0 = time.time()
    m.scan_line("| result = " + "loan / " * 3500 + "value")
    m.scan_line("above 40% " * 4000 + "ltv-flagged")
    m.scan_line("*" * 50000 + "55%")
    assert time.time() - t0 < 3.0, "interim-checklist passes must be linear-time on long lines"
    print("  PASS test_interim_checklist_refute_round2_unit")


# --------------------------------------------------------------------------------------------
# 2026-11-06: ora-skills is read from COMMITTED refs, never from working trees.
# On 2026-11-05/06 an uncommitted draft line in one session's ora-skills worktree
# (.claude/worktrees/*, gitignored but still os.walk'd) and a '1.75'-inside-'11.75' draft in
# another worktree each failed this probe inside the ~/.claude pre-push hook-tests gate and
# blocked every ~/.claude push fleet-wide. The probe now scans origin/main + local main
# (refs/heads/main -- NOT HEAD, see the probe's ORA_SKILLS_SCAN_REFS comment) via git
# ls-tree / cat-file. What it FLAGS is unchanged; only WHERE it reads.
# --------------------------------------------------------------------------------------------

_DRIFT_LINE = "DSCR governor floor 1.60x\n"
_CLEAN_LINE = "Governor: DSCR >= 1.25x, LTV <= 40% aggregate.\n"


def _git(repo, *args):
    import tempfile
    hooks = os.path.join(tempfile.gettempdir(), "gdp-nohooks")
    os.makedirs(hooks, exist_ok=True)
    cmd = ["git", "-C", repo, "-c", "user.name=gdp-test", "-c", "user.email=gdp@test.invalid",
           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + hooks,
           "-c", "core.autocrlf=false"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "git %s failed: %s %s" % (args, r.stdout, r.stderr)
    return r.stdout.strip()


def _write_rel(repo, rel, text):
    p = os.path.join(repo, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _make_skills_repo(d):
    """Temp repo shaped like ~/ora-skills: clean SKILL.md committed on main, origin/main set."""
    repo = os.path.join(d, "ora-skills")
    os.makedirs(repo)
    _git(repo, "init", "-q", "-b", "main")
    _write_rel(repo, ".gitignore", ".claude/worktrees/\n")
    _write_rel(repo, "debt-management/SKILL.md", _CLEAN_LINE)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def _run_main_over(m, targets):
    import contextlib, io
    old = (m.build_targets, sys.argv)
    m.build_targets = lambda: targets
    sys.argv = ["governor-drift-probe.py"]
    out, err = io.StringIO(), io.StringIO()
    code = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                m.main()
            except SystemExit as e:
                code = e.code
    finally:
        m.build_targets, sys.argv = old
    return code, out.getvalue(), err.getvalue()


def _skills_target(m, repo):
    return [(repo, m.GitRefTree((".md", ".json")))]


def test_ora_skills_target_reads_committed_refs_unit():
    """build_targets() must route ~/ora-skills through the committed-ref reader (origin/main +
    refs/heads/main), not a working-tree os.walk -- and never HEAD (a session's branch)."""
    m = _load_probe_module()
    assert tuple(m.ORA_SKILLS_SCAN_REFS) == ("refs/remotes/origin/main", "refs/heads/main"), m.ORA_SKILLS_SCAN_REFS
    if os.path.isdir(m.ORA_SKILLS_REPO):
        hits = [(r, e) for r, e in m.build_targets()
                if os.path.normcase(os.path.normpath(r))
                == os.path.normcase(os.path.normpath(m.ORA_SKILLS_REPO))]
        assert len(hits) == 1, "ora-skills must be targeted exactly once: %r" % hits
        spec = hits[0][1]
        assert isinstance(spec, m.GitRefTree), "ora-skills must be a GitRefTree target: %r" % (spec,)
        assert tuple(spec.refs) == ("refs/remotes/origin/main", "refs/heads/main")
        assert ".md" in spec.exts and ".json" in spec.exts
    print("  PASS test_ora_skills_target_reads_committed_refs_unit")


def test_uncommitted_worktree_drift_does_not_fail_probe_e2e():
    """(a) An uncommitted drift line in a linked worktree under .claude/worktrees/, an untracked
    drift file in the primary checkout, and an uncommitted edit to a tracked file in the primary
    checkout must NOT fail the probe. Also: drift COMMITTED only on a session's worktree branch,
    or WIP-committed on a side branch checked out IN THE PRIMARY checkout (HEAD != main -- REFUTE
    round 1 case A), must not fail it either."""
    import tempfile
    m = _load_probe_module()
    assert m.scan_line(_DRIFT_LINE), "payload must itself flag, or this test proves nothing"
    with tempfile.TemporaryDirectory() as d:
        repo = _make_skills_repo(d)
        wt = os.path.join(repo, ".claude", "worktrees", "wt1")
        _git(repo, "worktree", "add", "-q", "-b", "claude/wt1", wt)
        _write_rel(wt, "debt-management/SKILL.md", _DRIFT_LINE)            # uncommitted, worktree
        _write_rel(wt, "portfolio-growth/SKILL.md", _DRIFT_LINE)           # untracked, worktree
        _write_rel(repo, "debt-management/SKILL.md", _DRIFT_LINE)          # dirty tracked, primary
        _write_rel(repo, "eval-harness/README.md", "DSCR governor floor 1.75x\n")  # untracked, primary
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 0, "uncommitted drift must not fail the probe (got %r)\n%s\n%s" % (code, out, err)
        # committed on the worktree's OWN branch only -> still not origin/main / HEAD
        _git(wt, "add", "-A")
        _git(wt, "commit", "-q", "-m", "wip draft")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 0, "drift on a side branch only must not fail the probe (got %r)\n%s\n%s" % (code, out, err)
        _git(repo, "worktree", "remove", "--force", wt)
        # primary checkout switched to a session branch with a WIP drift commit
        _git(repo, "checkout", "-q", "-b", "claude/session-x")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "wip on primary checkout")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 0, "WIP commit on a primary-checkout side branch must not fail (got %r)\n%s\n%s" % (code, out, err)
    print("  PASS test_uncommitted_worktree_drift_does_not_fail_probe_e2e")


def test_committed_drift_on_main_still_fails_probe_e2e():
    """(b) Drift COMMITTED on main still fails the probe -- via unpushed local main, via local
    main while the primary checkout is parked on a clean side branch (REFUTE round 1 case B),
    via origin/main alone (local main clean), and the finding names the file, line and ref."""
    import tempfile
    m = _load_probe_module()
    with tempfile.TemporaryDirectory() as d:
        repo = _make_skills_repo(d)
        _write_rel(repo, "debt-management/SKILL.md", _CLEAN_LINE + _DRIFT_LINE)
        _git(repo, "commit", "-q", "-am", "drift")
        # local main has the drift; origin/main does not yet (local commit, unpushed)
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 1, "committed drift on local main must flag (got %r)\n%s\n%s" % (code, out, err)
        norm = out.replace("\\", "/")
        assert "debt-management/SKILL.md@refs/heads/main:2 " in norm, "file@ref:line must be reported:\n%s" % out
        # primary checkout parked on a clean side branch; origin/main still stale -> main still read
        _git(repo, "checkout", "-q", "-b", "clean", "HEAD~1")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 1, "local-main drift must flag while HEAD is elsewhere (got %r)\n%s" % (code, out)
        assert "@refs/heads/main:2 " in out, out
        # push it (origin/main = drift), then reset local main to clean
        _git(repo, "update-ref", "refs/remotes/origin/main", "refs/heads/main")
        _git(repo, "branch", "-f", "main", "clean")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 1, "drift on origin/main alone must flag (got %r)\n%s\n%s" % (code, out, err)
        assert "debt-management/SKILL.md@refs/remotes/origin/main:2 " in out.replace("\\", "/"), out
        # a stray LOCAL branch literally named origin/main (at the clean commit) must not shadow
        # the real remote-tracking ref (REFUTE round 2)
        _git(repo, "branch", "origin/main", "clean")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 1, "local origin/main branch must not shadow the remote ref (got %r)\n%s\n%s" % (code, out, err)
        assert "@refs/remotes/origin/main:2 " in out, out
    print("  PASS test_committed_drift_on_main_still_fails_probe_e2e")


def test_committed_ref_scan_keeps_path_exemptions_e2e():
    """The git reader must apply the SAME path rules as the walk: pruned dirs (_archive/,
    _archive_<date>/, node_modules/), versions/CHANGELOG.md, test modules, eval-harness runs/,
    /data/ json and non-.md/.json extensions stay exempt; a neighbouring SKILL.md still flags.
    CRLF content keeps its line numbers."""
    import tempfile
    m = _load_probe_module()
    exempt = ["s/_archive/SKILL.md", "s/_archive_2026-04-01/SKILL.md", "s/node_modules/x.md",
              "s/versions/CHANGELOG.md", "acquisition-underwriting-eval-harness/runs/r.json",
              "s/data/deal.json", "s/notes.txt"]
    with tempfile.TemporaryDirectory() as d:
        repo = _make_skills_repo(d)
        for rel in exempt:
            _write_rel(repo, rel, _DRIFT_LINE)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "exempt classes")
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 0, "exempt path classes must stay exempt (got %r)\n%s\n%s" % (code, out, err)
        _write_rel(repo, "s/SKILL.md", "line one\r\n" + _DRIFT_LINE.replace("\n", "\r\n"))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "real drift")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 1, "SKILL.md drift must flag (got %r)\n%s" % (code, out)
        norm = out.replace("\\", "/")
        assert "/s/SKILL.md@refs/heads/main:2 " in norm, "CRLF line numbering / path:\n%s" % out
        # lone-CR line endings (REFUTE round 1 C6 gap): must be split like open(path, "r") does
        _write_rel(repo, "t/SKILL.md", "line one\r" + _DRIFT_LINE.replace("\n", "\r"))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "lone cr")
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert "/t/SKILL.md@refs/heads/main:2 " in out.replace("\\", "/"), "lone-CR line numbering:\n%s" % out
        for rel in exempt:
            assert rel not in norm, "exempt %s leaked into findings:\n%s" % (rel, out)
    print("  PASS test_committed_ref_scan_keeps_path_exemptions_e2e")


def test_committed_ref_scan_fails_loud_e2e():
    """I5 fail-loud: a present ora-skills dir that is not a git repo (incl. one NESTED inside a
    parent repo -- REFUTE round 1 case I), or a repo where NO scan ref resolves, is a probe error
    (exit 2), never a silent clean pass. An inherited GIT_DIR must not redirect the read to a
    different repo (case J)."""
    import tempfile
    m = _load_probe_module()
    with tempfile.TemporaryDirectory() as d:
        notrepo = os.path.join(d, "ora-skills")
        os.makedirs(notrepo)
        _write_rel(notrepo, "SKILL.md", _DRIFT_LINE)
        code, out, err = _run_main_over(m, _skills_target(m, notrepo))
        assert code == 2, "non-repo must be a probe error (got %r)\n%s\n%s" % (code, out, err)
    with tempfile.TemporaryDirectory() as d:
        repo = os.path.join(d, "ora-skills")
        os.makedirs(repo)
        _git(repo, "init", "-q", "-b", "main")            # no commits -> no ref resolves
        code, out, err = _run_main_over(m, _skills_target(m, repo))
        assert code == 2, "no resolvable ref must be a probe error (got %r)\n%s\n%s" % (code, out, err)
    with tempfile.TemporaryDirectory() as d:
        parent = os.path.join(d, "parent")
        os.makedirs(parent)
        _git(parent, "init", "-q", "-b", "main")
        _write_rel(parent, "other.md", _CLEAN_LINE)
        _git(parent, "add", "-A")
        _git(parent, "commit", "-q", "-m", "p")
        nested = os.path.join(parent, "ora-skills")
        _write_rel(nested, "SKILL.md", _DRIFT_LINE)
        code, out, err = _run_main_over(m, _skills_target(m, nested))
        assert code == 2, "nested non-repo must be a probe error, not the parent tree (got %r)\n%s\n%s" % (code, out, err)
    with tempfile.TemporaryDirectory() as d:
        drift = _make_skills_repo(d)
        _write_rel(drift, "s/SKILL.md", _DRIFT_LINE)
        _git(drift, "add", "-A")
        _git(drift, "commit", "-q", "-m", "drift")
        decoy = os.path.join(d, "decoy")
        os.makedirs(decoy)
        _git(decoy, "init", "-q", "-b", "main")
        _write_rel(decoy, "x.md", _CLEAN_LINE)
        _git(decoy, "add", "-A")
        _git(decoy, "commit", "-q", "-m", "decoy")
        _git(decoy, "update-ref", "refs/remotes/origin/main", "HEAD")
        old = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = os.path.join(decoy, ".git")
        try:
            code, out, err = _run_main_over(m, _skills_target(m, drift))
        finally:
            if old is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = old
        assert code == 1, "inherited GIT_DIR must not redirect the scan (got %r)\n%s\n%s" % (code, out, err)
    print("  PASS test_committed_ref_scan_fails_loud_e2e")


def main():
    assert os.path.isfile(PROBE), "probe not found: %s" % PROBE
    test_fleet_roots_are_scanned_unit()
    test_ora_skills_target_reads_committed_refs_unit()
    test_uncommitted_worktree_drift_does_not_fail_probe_e2e()
    test_committed_drift_on_main_still_fails_probe_e2e()
    test_committed_ref_scan_keeps_path_exemptions_e2e()
    test_committed_ref_scan_fails_loud_e2e()
    test_dated_archive_dirs_pruned_unit()
    test_probe_self_description_prose_suppressed_unit()
    test_sentinel_suppression_does_not_hide_real_drift_unit()
    test_fleet_skill_drift_would_flag_e2e()
    test_canonical_clean_unit()
    test_real_ltv_drift_still_flags_unit()
    test_real_dscr_drift_still_flags_unit()
    test_dscr_drift_without_trailing_x_flags_unit()
    test_real_scoring_rubric_still_excluded_unit()
    test_canonical_dscr_without_x_clean_unit()
    test_non_governor_dscr_prose_not_flagged_unit()
    test_narrative_suppression_is_file_level_not_logic_level()
    test_ltv_correction_note_suppressed_unit()
    test_ltv_correction_note_does_not_oversuppress_unit()
    test_dscr_correction_note_span_scoped_unit()
    test_governor_with_incidental_rubric_fragment_flags_unit()
    test_count_gate_not_bypassable_by_appending_rubric_pairs_unit()
    test_multi_pair_rubric_false_positive_guard_unit()
    test_canonical_decoy_does_not_hide_dscr_drift_unit()
    test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit()
    test_canonical_decoy_does_not_hide_ltv_drift_unit()
    test_incidental_figures_not_flagged_unit()
    test_scan_code_canonical_clean_unit()
    test_scan_code_constant_drift_flags_unit()
    test_scan_code_direction_and_inversion_flags_unit()
    test_scan_code_positivity_guard_clean_when_canonical_guard_present_unit()
    test_scan_code_positivity_guard_flags_when_canonical_guard_missing_unit()
    test_scan_code_positivity_guard_exemption_is_strictly_greater_than_zero_unit()
    test_scan_code_ratified_variable_guard_licenses_positivity_exemption_unit()
    test_governor_constants_file_is_routed_to_scan_code_unit()
    test_scan_code_ignores_deal_values_unit()
    test_scan_code_seed_literal_drift_flags_unit()
    test_scan_code_presence_regexes_unit()
    test_reverse_order_dscr_floor_flags_unit()
    test_reverse_order_ltv_ceiling_flags_unit()
    test_reverse_order_no_false_positive_unit()
    test_reverse_order_suppression_still_applies_unit()
    test_reverse_order_refi_suppression_unit()
    test_version_token_not_a_dscr_threshold_unit()
    test_approximate_tilde_value_not_a_dscr_threshold_unit()
    test_tilde_hedge_canon_plain_rejects_version_and_percent_tokens_unit()
    test_tilde_hedge_corrected_word_boundary_and_directional_unit()
    test_deal_comparison_skill_file_clean()
    test_rate_percent_not_a_dscr_threshold_unit()
    test_refi_lesser_of_construct_suppressed_unit()
    test_refi_sizing_phrase_suppressed_unit()
    test_canonical_dscr_governor_at_ltv_suppressed_unit()
    test_bps_rate_pricing_tier_suppressed_unit()
    test_perdeal_perproperty_drift_still_flags_unit()
    test_review_hole1_lesser_of_gap_drift_flags_unit()
    test_review_hole2_bps_gap_no_leapfrog_flags_unit()
    test_decimal_fragment_never_binds_unit()
    test_decimal_ltv_drift_still_flags_unit()
    test_canonical_decimal_forty_clean_unit()
    test_dated_review_memory_file_excluded_unit()
    test_unit_interval_ltv_flags_unit()
    test_ledger_files_excluded_source_pin()
    test_concurrent_session_hardening_narrative_excluded_unit()
    test_index_projects_system_narrative_excluded_unit()
    test_open_items_tracker_narrative_excluded_unit()
    test_review_hole3_paired_gap_drift_flags_unit()
    test_review_hole4_veto_window_and_refi_gate_flags_unit()
    test_review_hole5_dscr_extraction_regressions_flags_unit()
    test_followup1_value_dscr_keyword_order_flags_unit()
    test_followup2_refi_to_ltv_veto_tier_unit()
    test_round2_declaring_governor_before_value_flags_unit()
    test_n6_hard_cap_ceiling_is_gov_gate_unit()
    test_perprop_portfolio_aggregate_pairing_suppressed_unit()
    test_perprop_member_value_locked_to_ratified_65_unit()
    test_perproperty_non_ratified_ltv_still_flags_unit()
    test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit()
    test_dated_audit_memory_file_excluded_unit()
    test_skill_version_changelog_excluded_unit()
    test_skill_version_changelog_wiring_hermetic_e2e()
    test_acquisition_underwriting_skill_file_clean()
    test_test_files_excluded_from_scan_unit()
    test_eval_harness_run_logs_excluded_from_scan_unit()
    test_run_probe_survives_child_utf8_smartquote_e2e()
    # Registered here, BEFORE the e2e tests below -- an assert failure in an e2e test aborts
    # main() outright, so anything registered after those calls silently never runs on a plain
    # `python test-governor-drift-probe.py` invocation (independent-review blocking finding,
    # 2026-08-22, session 438b62fb; at the time, test_event_log_excluded_e2e /
    # test_active_work_claims_excluded_e2e were failing on 6 pre-existing findings in OTHER
    # files, since closed -- see test_index_projects_system_narrative_excluded_unit).
    test_v413_changelog_line_clean_unit()
    test_dscr_rate_tier_bucket_label_not_flagged_as_governor_unit()
    test_dscr_rate_tier_bucket_label_veto_when_declared_as_governor_unit()
    test_ltv_ceiling_reaffirmed_elsewhere_in_paragraph_suppressed_unit()
    test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_real_drift_unit()
    test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_governor_declared_drift_unit()
    test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_aggregate_drift_unit()
    test_eval_harness_floor_result_narration_clean_unit()
    test_floor_result_narration_does_not_mask_drift_unit()
    test_floor_result_round2_declaration_tokens_still_veto_unit()
    test_floor_result_round2_binder_declarations_still_flag_unit()
    test_floor_result_round3_verbphrase_binders_still_flag_unit()
    test_floor_result_round4_distant_keyword_declarations_still_flag_unit()
    test_interim_checklist_canonical_threshold_wording_stays_clean_unit()
    test_interim_checklist_drifted_threshold_wording_flags_unit()
    test_interim_checklist_extractor_does_not_flag_unrelated_prose_unit()
    test_interim_checklist_refute_round1_false_negatives_closed_unit()
    test_interim_checklist_refute_round1_false_positive_guards_unit()
    test_interim_checklist_refute_round2_unit()
    test_event_log_excluded_e2e()
    test_fixture_roots_drift_detected_e2e()
    test_e2e_outcome_independent_of_ambient_home_e2e()
    test_live_tree_clean_optin()
    test_active_work_claims_pruned_unit()
    test_active_work_claims_excluded_e2e()
    test_sessions_dir_pruned_unit()
    test_sessions_reviews_excluded_e2e()
    test_intervening_qualifier_dscr_floor_flags_unit()
    test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit()
    test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit()
    test_perproperty_refi_ceiling_standalone_drift_still_flags_unit()
    test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit()
    test_dscr_scaling_multiplier_changelog_stays_clean_unit()
    test_dscr_scaling_multiplier_real_drift_still_flags_unit()
    test_dscr_scaling_multiplier_by_factor_phrasing_stays_clean_unit()
    test_dscr_scaling_multiplier_keyword_after_value_still_flags_unit()
    test_dscr_scaling_multiplier_intervening_modifier_still_flags_unit()
    test_dscr_scaling_multiplier_present_tense_mechanism_still_flags_unit()
    test_dscr_scaling_multiplier_governor_nearby_still_flags_unit()
    test_dscr_scaling_multiplier_accepted_residuals_unit()
    test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit()
    test_ltv_subject_veto_does_not_silence_real_declarations_unit()
    test_ltv_subject_veto_reach_semantics_unit()
    test_ltv_house_separator_styles_still_flag_unit()
    test_ltv_anchor_window_respects_the_subject_veto_unit()
    test_ltv_extractor_spans_intervening_qualifier_unit()
    test_value_between_metric_and_boundword_flags_unit()
    test_value_abutting_arming_does_not_flag_durations_unit()
    test_intervening_qualifier_canonical_stays_clean_unit()
    test_qualifier_gate_requires_the_metric_token_unit()
    test_stabilization_conditioned_covenant_suppressed_unit()
    test_stabilization_language_does_not_mask_governor_drift_unit()
    test_stabilization_qualifier_does_not_mask_reversed_word_order_unit()
    test_stabilization_qualifier_veto_covers_arming_vocabulary_unit()
    test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit()
    print("ALL GOVERNOR-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
