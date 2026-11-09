"""push-live-backup.py pure-unit checks: push classifier, gate precondition, beacons,
off-box verdict. No git network, no pushes.

The git-heavy suite (real bare remote, real pre-push hook, lease, containment) lives in
_tests/integration/test_push_live_backup_git.py, which the pre-push hook-tests gate does
not discover (same reason as safe-push's: git-spawn suites blow the 240s per-file budget
under load). Run it by hand after any change to push-live-backup.py:
    python maintenance/_tests/integration/test_push_live_backup_git.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "push-live-backup.py")

_spec = importlib.util.spec_from_file_location("push_live_backup", TOOL)
plb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plb)

def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _json(p):
    return json.loads(_read(p))


TARGET = "refs/heads/backup/live-primary"
SHIM_V2 = plb.KNOWN_GOOD_SHIMS["v2 (installed 2026-11-08)"]
GOOD_SCAN = ("def scan_compressed(rng, terms):\n    return [], [], False\n\n"
             "def main():\n    c_hits, c_leaks, c_bad = scan_compressed(None, [])\n    return 0\n")
HDR = "To https://github.com/x/y.git\n"


def porcelain(flag, summary):
    return HDR + "%s\tf00:%s\t%s\nDone\n" % (flag, TARGET, summary)


class ClassifyPushTest(unittest.TestCase):
    def test_success_flags(self):
        self.assertEqual(plb.classify_push(0, porcelain("*", "[new branch]"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain("+", "a..b (forced update)"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain(" ", "a..b"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain("=", "[up to date]"), TARGET), "UP_TO_DATE")

    def test_lease_rejection_is_its_own_verdict(self):
        self.assertEqual(plb.classify_push(1, porcelain("!", "[rejected] (stale info)"), TARGET), "LEASE_REJECTED")

    def test_other_rejections(self):
        self.assertEqual(plb.classify_push(1, porcelain("!", "[remote rejected] (protected branch hook declined)"), TARGET), "REJECTED")
        self.assertEqual(plb.classify_push(1, porcelain("!", "[rejected] (fetch first)"), TARGET), "REJECTED")

    def test_gate_block_has_no_status_block(self):
        # pre-push hook exit 1: git prints no porcelain status for the ref at all
        out = "confidential-scan: BLOCKED (deal #2, 1 hit)\nerror: failed to push some refs to 'x'\n"
        self.assertEqual(plb.classify_push(1, out, TARGET), "BLOCKED_OR_FAILED")

    def test_status_shaped_text_before_header_is_ignored(self):
        # a gate's own log can contain status-shaped lines; only git's block after "To <url>" counts
        gate = "*\tf00:%s\t[new branch]\n" % TARGET
        self.assertEqual(plb.classify_push(1, gate + "error: failed to push\n", TARGET), "BLOCKED_OR_FAILED")
        self.assertEqual(plb.classify_push(0, gate, TARGET), "BLOCKED_OR_FAILED")

    def test_up_to_date_line_with_nonzero_rc_is_not_success(self):
        self.assertEqual(plb.classify_push(1, porcelain("=", "[up to date]"), TARGET), "BLOCKED_OR_FAILED")

    def test_rc_zero_with_rejected_line_is_not_success(self):
        self.assertEqual(plb.classify_push(0, porcelain("!", "[rejected] (stale info)"), TARGET), "LEASE_REJECTED")

    def test_other_ref_line_is_ignored(self):
        out = HDR + "*\tf00:refs/heads/other\t[new branch]\nDone\n"
        self.assertEqual(plb.classify_push(0, out, TARGET), "BLOCKED_OR_FAILED")


class PushArgvTest(unittest.TestCase):
    def test_argv_uses_explicit_lease_and_never_skips_hooks(self):
        argv = plb.push_argv("origin", "a" * 40, TARGET, "b" * 40)
        self.assertIn("--force-with-lease=%s:%s" % (TARGET, "b" * 40), argv)
        self.assertIn("%s:%s" % ("a" * 40, TARGET), argv)
        self.assertIn("--porcelain", argv)
        for bad in ("--no-verify", "-n", "--force", "-f", "--mirror", "--all"):
            self.assertNotIn(bad, argv)

    def test_absent_remote_ref_leases_on_nonexistence(self):
        argv = plb.push_argv("origin", "a" * 40, TARGET, None)
        self.assertIn("--force-with-lease=%s:" % TARGET, argv)

    def test_source_never_contains_no_verify(self):
        src = _read(TOOL)
        code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        # the literal may appear in prose (docstring) but never as an argv element
        self.assertNotIn('"--no-verify"', code)
        self.assertNotIn("'--no-verify'", code)


class GatePreconditionTest(unittest.TestCase):
    """Static half: allowlisted shim + AST lint (canary=False). Behavioural half: CanaryTest."""
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="plb-unit-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.hooks = os.path.join(self.root, "githooks")
        os.makedirs(self.hooks)
        os.makedirs(os.path.join(self.root, "hooks"))

    def _write(self, rel, text, newline="\n"):
        with open(os.path.join(self.root, rel), "w", encoding="utf-8", newline=newline) as f:
            f.write(text)

    def _good(self):
        self._write("githooks/pre-push", SHIM_V2)
        self._write("hooks/git-prepush-confidential-scan.py", GOOD_SCAN)

    def _ok(self):
        return plb.gate_precondition(self.root, self.hooks, canary=False)

    def test_ok(self):
        self._good()
        ok, why = self._ok()
        self.assertTrue(ok, why)

    def test_both_known_shims_accepted_including_comment_and_whitespace_drift(self):
        self._good()
        for name, text in plb.KNOWN_GOOD_SHIMS.items():
            drifted = text.replace("ROOT=", "# a reworded header comment\nROOT=").replace("\n", "  \n")
            self._write("githooks/pre-push", drifted, newline="")
            self.assertTrue(self._ok()[0], name)

    def test_missing_pre_push(self):
        self._good()
        os.remove(os.path.join(self.hooks, "pre-push"))
        ok, why = self._ok()
        self.assertFalse(ok)
        self.assertIn("pre-push", why)

    def test_shim_variants_that_skip_the_scan_are_refused(self):
        # REFUTE rounds 1-2: each of these defeated a substring or line-parse check
        self._good()
        scan = 'python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@" <"$REFS"'
        variants = {
            "comment only": "#!/bin/sh\nexit 0\n# git-prepush-confidential-scan.py\n",
            "exit first": SHIM_V2.replace("ROOT=", "exit 0\nROOT="),
            "exec first": SHIM_V2.replace("ROOT=", "exec true\nROOT="),
            "if false": SHIM_V2.replace(scan, "if false; then " + scan + "; fi"),
            "backgrounded": SHIM_V2.replace(scan, scan + " &"),
            "or true": SHIM_V2.replace(scan, scan + " || true"),
            "other ROOT": SHIM_V2.replace('ROOT="$(git rev-parse --show-toplevel)"', 'ROOT="/tmp/elsewhere"'),
            "extra line after": SHIM_V2 + "exit 0\n",
        }
        for name, text in variants.items():
            self._write("githooks/pre-push", text)
            self.assertFalse(self._ok()[0], name)

    def test_each_stray_character_on_the_refs_line_is_refused(self):
        # REFUTE round 3 (2026-11-09): one stray \r or Unicode space after `cat > "$REFS"`
        # compared equal, starved the scan's stdin, and pushed unscanned end to end.
        self._good()
        line = 'cat > "$REFS"'
        self.assertIn(line + "\n", SHIM_V2)
        for ch in ("\r", "\x0b", "\x0c", "\x1f", "\x85", "\xa0", " ", "　", "\x7f", "\x00"):
            text = SHIM_V2.replace(line + "\n", line + ch + "\n")
            self.assertIsNone(plb.known_shim(text), repr(ch))
            with open(os.path.join(self.hooks, "pre-push"), "wb") as fh:
                fh.write(text.encode("utf-8"))   # on disk, as the shell would read it
            self.assertFalse(self._ok()[0], repr(ch))

    def test_crlf_is_refused_whole_file_or_one_line(self):
        # one CRLF line in an LF shim IS the round-3 bypass; installed shims are LF-only
        self._good()
        for text in (SHIM_V2.replace("\n", "\r\n"), SHIM_V2.replace('cat > "$REFS"\n', 'cat > "$REFS"\r\n')):
            with open(os.path.join(self.hooks, "pre-push"), "wb") as fh:
                fh.write(text.encode("ascii"))
            self.assertFalse(self._ok()[0])

    def test_trailing_space_tab_and_utf8_comment_lines_accepted(self):
        # the installed shims carry UTF-8 em-dashes in header comments (verified 2026-11-09)
        self._good()
        text = SHIM_V2.replace("#!/bin/sh\n", "#!/bin/sh\n# Pre-push gate — SHIM v2 — note\n", 1)
        text = text.replace('cat > "$REFS"\n', 'cat > "$REFS" \t\n')
        with open(os.path.join(self.hooks, "pre-push"), "wb") as fh:
            fh.write(text.encode("utf-8"))
        self.assertTrue(self._ok()[0])

    def test_non_ascii_on_an_executable_line_is_refused_even_in_a_trailing_comment(self):
        self.assertIsNone(plb.known_shim(SHIM_V2.replace('cat > "$REFS"\n', 'cat > "$REFS" # —\n')))

    def test_only_hash_lines_are_dropped_as_comments(self):
        # a line that merely starts with whitespace-then-something-else is content
        self.assertIsNone(plb.known_shim(SHIM_V2.replace('cat > "$REFS"\n', 'cat > "$REFS"\n  true\n')))
        self.assertEqual(plb.known_shim(SHIM_V2.replace('cat > "$REFS"\n', 'cat > "$REFS"\n \t# note\n')),
                         "v2 (installed 2026-11-08)")

    def test_push_env_opts_into_require_refs(self):
        self.assertEqual(plb._env().get(plb.REQUIRE_REFS_ENV), "1")

    def test_scan_without_compressed_scan(self):
        # the live branch's state on 2026-11-08: scan present, #427's compressed scan absent
        self._good()
        self._write("hooks/git-prepush-confidential-scan.py", "def main():\n    pass\n")
        ok, why = self._ok()
        self.assertFalse(ok)
        self.assertIn("scan_compressed", why)

    def test_ast_lint_requires_a_bare_name_call_inside_main(self):
        cases = {
            "docstring mention only": '"""see scan_compressed() below"""\ndef scan_compressed(rng, terms):\n    pass\n\n'
                                      'def main():\n    a, b, c = [], [], []\n',
            "called outside main": "def scan_compressed(r, t):\n    pass\n\ndef helper():\n    scan_compressed(1, 2)\n\n"
                                   "def main():\n    return 0\n",
            "attribute call": "import x\ndef scan_compressed(r, t):\n    pass\n\ndef main():\n    x.scan_compressed(1, 2)\n",
            "similar name": "def scan_compressed(r, t):\n    pass\n\ndef main():\n    scan_compressed_v2(1, 2)\n",
            "not top-level": "class K:\n    def scan_compressed(self, r, t):\n        pass\n\ndef main():\n    scan_compressed(1, 2)\n",
            "no main": "def scan_compressed(r, t):\n    pass\n\nscan_compressed(1, 2)\n",
            "syntax error": "def main(:\n",
        }
        for name, src in cases.items():
            self.assertFalse(plb.scan_main_calls_compressed(src), name)
        self.assertTrue(plb.scan_main_calls_compressed(GOOD_SCAN))

    def test_scan_file_missing(self):
        self._good()
        os.remove(os.path.join(self.root, "hooks", "git-prepush-confidential-scan.py"))
        self.assertFalse(self._ok()[0])

    def test_canary_is_on_by_default(self):
        # the stub GOOD_SCAN passes the lint but blocks nothing: only the canary catches it
        self._good()
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)
        self.assertIn("CANARY", why)


class CanaryTest(unittest.TestCase):
    """canary_scan() runs a scan against a throwaway repo in TEMP. No live checkout touched."""
    REAL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "hooks", "git-prepush-confidential-scan.py")

    def _stub(self, src):
        d = tempfile.mkdtemp(prefix="plb-stub-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "scan.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)
        return p

    def _hermetic_real_scan(self, terms_json):
        """This checkout's REAL scan bytes in a TEMP hooks dir, with hooks/lib beside it and a
        synthetic confidential-terms.json (or none when terms_json is None). The real file is
        gitignored, so a fresh CI checkout has none; run in place there, the scan fails closed
        on 'terms unreadable' before it reaches either path the canary probes (and outside a
        git repo the main-worktree fallback cannot rescue it either)."""
        d = tempfile.mkdtemp(prefix="plb-realscan-")
        self.addCleanup(shutil.rmtree, d, True)
        hooks = os.path.join(d, "hooks")
        os.makedirs(hooks)
        shutil.copy2(self.REAL, os.path.join(hooks, os.path.basename(self.REAL)))
        shutil.copytree(os.path.join(os.path.dirname(self.REAL), "lib"), os.path.join(hooks, "lib"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        if terms_json is not None:
            with open(os.path.join(hooks, "confidential-terms.json"), "w", encoding="utf-8") as fh:
                fh.write(terms_json)
        return os.path.join(hooks, os.path.basename(self.REAL))

    def test_this_checkouts_real_scan_blocks_the_canary(self):
        # Hermetic: does not depend on the gitignored live terms file (absent in CI).
        ok, why = plb.canary_scan(self._hermetic_real_scan("{}"))
        self.assertTrue(ok, why)

    def test_real_scan_blocks_the_canary_with_a_loaded_roster(self):
        # REFUTE 2026-11-09: the {} variant alone is blind to a regression that skips the
        # compressed/credential scan only while a roster is loaded. Synthetic term only.
        roster = '{"synthetic": {"active": true, "always": ["zz-not-in-any-blob"]}}'
        ok, why = plb.canary_scan(self._hermetic_real_scan(roster))
        self.assertTrue(ok, why)

    def test_real_scan_without_terms_fails_the_canary_without_claiming_it_allowed(self):
        # The CI state since #440: the scan BLOCKS (exit 1, terms unreadable) on the starved
        # stdin. The canary must still fail (that block proves nothing about the guard), but
        # must not report a fail-closed block as a push it "allowed".
        ok, why = plb.canary_scan(self._hermetic_real_scan(None))
        self.assertFalse(ok)
        self.assertNotIn("allowed", why)
        self.assertIn("unreadable", why)

    def test_other_fail_closed_block_on_starved_stdin_is_not_reported_as_allowed(self):
        ok, why = plb.canary_scan(self._stub(
            "import sys\nsys.stdin.read()\nprint('BLOCKED (fail-closed): terms unreadable')\nsys.exit(1)\n"))
        self.assertFalse(ok)
        self.assertNotIn("allowed", why)
        self.assertIn("CANARY FAILED", why)

    def test_scan_that_lets_everything_through_fails_the_canary(self):
        ok, why = plb.canary_scan(self._stub("import sys\nsys.stdin.read()\nsys.exit(0)\n"))
        self.assertFalse(ok)
        self.assertIn("CANARY FAILED", why)

    def test_fail_closed_block_for_another_reason_does_not_count(self):
        # e.g. terms file unreadable: blocks, but proves nothing about the compressed path
        ok, _ = plb.canary_scan(self._stub("import sys\nsys.stdin.read()\nprint('BLOCKED (fail-closed): terms unreadable')\nsys.exit(1)\n"))
        self.assertFalse(ok)

    def test_scan_that_ignores_starved_stdin_fails_the_canary(self):
        # blocks the compressed credential, but allows zero ref lines: the pre-round-3 scan
        src = ("import sys\nt = sys.stdin.read()\n"
               "if t.strip():\n    print('pre-push BLOCKED: ... inside COMPRESSED file(s)')\n    sys.exit(1)\n"
               "sys.exit(0)\n")
        ok, why = plb.canary_scan(self._stub(src))
        self.assertFalse(ok)
        self.assertIn("ZERO ref lines", why)

    def test_scan_that_only_guards_starved_stdin_fails_the_canary(self):
        src = ("import sys\nt = sys.stdin.read()\n"
               "if not t.strip():\n    print('BLOCKED: zero ref lines')\n    sys.exit(1)\n"
               "sys.exit(0)\n")
        ok, why = plb.canary_scan(self._stub(src))
        self.assertFalse(ok)
        self.assertIn(".gz", why)

    def test_canary_secret_is_not_a_literal_in_the_source(self):
        self.assertNotIn(plb._canary_secret(), _read(TOOL))
        self.assertRegex(plb._canary_secret(), r"^AKIA[0-9A-Z]{16}$")


class BeaconTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="plb-beacon-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.ok = os.path.join(self.d, plb.OK_STAMP)
        self.failed = os.path.join(self.d, plb.FAILED_MARKER)

    def test_failure_writes_marker_and_keeps_ok_stamp(self):
        plb.write_beacon(self.d, True, {"verdict": "PUSHED", "sha": "a"})
        before = _read(self.ok)
        plb.write_beacon(self.d, False, {"verdict": "BLOCKED_OR_FAILED", "sha": "b"})
        self.assertTrue(os.path.exists(self.failed))
        self.assertEqual(_json(self.failed)["verdict"], "BLOCKED_OR_FAILED")
        self.assertEqual(_read(self.ok), before)  # last success preserved

    def test_success_clears_marker(self):
        plb.write_beacon(self.d, False, {"verdict": "REJECTED"})
        plb.write_beacon(self.d, True, {"verdict": "PUSHED"})
        self.assertFalse(os.path.exists(self.failed))
        self.assertEqual(_json(self.ok)["verdict"], "PUSHED")

    def test_beacon_carries_timestamp(self):
        plb.write_beacon(self.d, False, {"verdict": "X"})
        self.assertIn("ts", _json(self.failed))

    def test_creates_missing_state_dir(self):
        sub = os.path.join(self.d, "nested", "_state")
        self.assertTrue(plb.write_beacon(sub, False, {"verdict": "X"}))
        self.assertTrue(os.path.exists(os.path.join(sub, plb.FAILED_MARKER)))

    def test_never_raises(self):
        # a file where the directory should be: write fails, returns False, does not raise
        blocker = os.path.join(self.d, "blocker")
        open(blocker, "w").close()
        self.assertFalse(plb.write_beacon(os.path.join(blocker, "x"), False, {"verdict": "X"}))


class OffboxVerdictTest(unittest.TestCase):
    NOW = 1_800_000_000

    def test_contained(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual((v["verdict"], v["rc"]), ("CONTAINED", 0))

    def test_pending_within_grace(self):
        v = plb.offbox_verdict(pending_times=[self.NOW - 3600, self.NOW - 7200], now=self.NOW, grace_hours=26,
                               failed_marker=None, ok_stamp_age_hours=5.0)
        self.assertEqual((v["verdict"], v["rc"]), ("PENDING_WITHIN_GRACE", 0))
        self.assertEqual(v["pending_count"], 2)

    def test_pending_within_grace_but_backup_stale_or_never_ran(self):
        # a rebase resets committer time; the ok stamp's age is the independent signal
        for age in (None, 60.0):
            v = plb.offbox_verdict(pending_times=[self.NOW - 3600], now=self.NOW, grace_hours=26,
                                   failed_marker=None, ok_stamp_age_hours=age, stamp_max_hours=48)
            self.assertEqual((v["verdict"], v["rc"]), ("NOT_OFFBOX", 1), age)

    def test_stale_stamp_alone_is_fine_when_nothing_pending(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26, failed_marker=None,
                               ok_stamp_age_hours=500.0)
        self.assertEqual(v["rc"], 0)

    def test_all_future_dated_pending_clamps_to_zero_not_negative(self):
        v = plb.offbox_verdict(pending_times=[self.NOW + 99999], now=self.NOW, grace_hours=26,
                               failed_marker=None, ok_stamp_age_hours=1.0)
        self.assertEqual(v["oldest_pending_hours"], 0.0)

    def test_not_offbox_past_grace_keys_on_oldest(self):
        v = plb.offbox_verdict(pending_times=[self.NOW - 3600, self.NOW - 30 * 3600], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual((v["verdict"], v["rc"]), ("NOT_OFFBOX", 1))
        self.assertAlmostEqual(v["oldest_pending_hours"], 30.0, places=1)

    def test_future_dated_commit_does_not_hide_an_old_one(self):
        v = plb.offbox_verdict(pending_times=[self.NOW + 99999, self.NOW - 40 * 3600], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual(v["rc"], 1)

    def test_failed_marker_alarms_even_when_contained(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26,
                               failed_marker={"verdict": "BLOCKED_OR_FAILED", "ts": "2026-11-08T00:00:00Z"})
        self.assertEqual(v["rc"], 1)
        self.assertIn("BACKUP_PUSH_FAILED", v["problems"][0])

    def test_unreadable_failed_marker_is_a_problem_not_a_pass(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26, failed_marker={"_unreadable": True})
        self.assertEqual(v["rc"], 1)


class CliSurfaceTest(unittest.TestCase):
    def test_target_is_fixed_not_an_option(self):
        # REFUTE 2026-11-08: --target main force-rewrote remote main in a scratch repo
        self.assertEqual(plb.TARGET_REF, "refs/heads/backup/live-primary")
        import io
        import contextlib
        buf = io.StringIO()
        d = tempfile.mkdtemp(prefix="plb-cli-")
        self.addCleanup(shutil.rmtree, d, True)
        with contextlib.redirect_stdout(buf):
            rc = plb.main(["--check", "--repo", d, "--target", "main"])
        self.assertEqual(rc, 6)
        self.assertTrue(buf.getvalue().strip().splitlines()[-1].startswith("RESULT_JSON="))

    def _run(self, argv):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = plb.main(argv)
        return rc, buf.getvalue()

    def test_branch_is_a_constant_not_an_option(self):
        self.assertEqual(plb.BRANCH, "live/primary-checkout")
        d = tempfile.mkdtemp(prefix="plb-cli-")
        self.addCleanup(shutil.rmtree, d, True)
        rc, _ = self._run(["--check", "--repo", d, "--branch", "main"])
        self.assertEqual(rc, 6)

    def test_option_abbreviations_are_rejected(self):
        d = tempfile.mkdtemp(prefix="plb-cli-")
        self.addCleanup(shutil.rmtree, d, True)
        rc, out = self._run(["--che", "--repo", d])
        self.assertEqual(rc, 6, out)
        rc, out = self._run(["--check", "--rep", d])
        self.assertEqual(rc, 6, out)

    def test_push_usage_error_writes_marker_only_where_argv_points(self):
        d = tempfile.mkdtemp(prefix="plb-cli-")
        self.addCleanup(shutil.rmtree, d, True)
        state = os.path.join(d, "st")
        rc, _ = self._run(["--repo", d, "--state-dir", state, "--bogus"])
        self.assertEqual(rc, 6)
        self.assertEqual(_json(os.path.join(state, plb.FAILED_MARKER))["verdict"], "ERROR")
        rc, _ = self._run(["--repo", d, "--bogus"])
        self.assertTrue(os.path.exists(os.path.join(d, "maintenance", "_state", plb.FAILED_MARKER)))
        # resolution, without writing: no --repo -> default live state; check mode -> nothing
        self.assertEqual(plb._usage_state_dir(["--bogus"]),
                         os.path.join(plb.DEFAULT_REPO, "maintenance", "_state"))
        self.assertIsNone(plb._usage_state_dir(["--check", "--bogus"]))
        self.assertEqual(plb._usage_state_dir(["--repo", d, "--x"]), os.path.join(d, "maintenance", "_state"))

    def test_check_usage_error_writes_nothing(self):
        d = tempfile.mkdtemp(prefix="plb-cli-")
        self.addCleanup(shutil.rmtree, d, True)
        rc, _ = self._run(["--check", "--repo", d, "--state-dir", os.path.join(d, "st"), "--bogus"])
        self.assertEqual(rc, 6)
        self.assertFalse(os.path.exists(os.path.join(d, "st")))

    def test_non_ascii_detail_cannot_break_result_line(self):
        # REFUTE 2026-11-08: em-dash in gate stderr + cp1252 stdout crashed print()
        import io
        raw = io.BytesIO()
        cp = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        old = sys.stdout
        sys.stdout = cp
        try:
            plb._safe_stdout()
            print("[BLOCKED] pre-push BLOCKED — �")
            cp.flush()
        finally:
            sys.stdout = old
        self.assertIn(b"BLOCKED", raw.getvalue())


class BeaconsIgnoredTest(unittest.TestCase):
    """A tracked outage marker or a daily-changing stamp would be committed by the next
    `git add -A` sweep; both beacons (and their atomic-write .tmp) must be git-ignored."""
    def test_beacons_are_git_ignored(self):
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for name in (plb.OK_STAMP, plb.FAILED_MARKER, plb.OK_STAMP + ".tmp", plb.FAILED_MARKER + ".tmp"):
            rel = "maintenance/_state/" + name
            p = subprocess.run(["git", "-C", root, "check-ignore", "-q", "--no-index", rel])
            self.assertNotEqual(p.returncode, 128, "git check-ignore errored on " + rel)
            self.assertEqual(p.returncode, 0, rel + " is NOT git-ignored")


if __name__ == "__main__":
    unittest.main(verbosity=1)
