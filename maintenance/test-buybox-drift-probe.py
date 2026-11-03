#!/usr/bin/env python3
"""Tests for buybox-drift-probe.py (TDD).

Two layers:
  * UNIT  -- import scan_text() / check_canon() and assert the DETECTION logic: canonical
             buy-box statements are clean; a $10M ceiling with no portfolio-path mention in the
             same line/bullet flags; market-research prose and changelog lines do not.
  * E2E   -- build a throwaway ~/.claude + ora-skills tree in a temp dir and run the probe
             against it (--claude-root / --skills-root). One drift fixture per scanned file
             class, plus the exit-code contract (0 clean, 1 drift, 2 probe error).

HERMETIC BY DESIGN: there is deliberately NO real-tree "exit 0" assertion. The pre-push gate
(hooks/git-prepush-hook-tests-gate.py) runs every maintenance/test-*.py, so a real-tree check
would block every push in the repo while any live drift exists. The live scan is the probe's
own job, not this suite's.

Run: python test-buybox-drift-probe.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import os
import sys
import shutil
import tempfile
import subprocess
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "buybox-drift-probe.py")

CANON_GATE2 = (
    "2. **Size/Price:** $500K–$10M single asset; ≤$15M multi-building portfolio of "
    "**2–5 buildings sold together (Amendment H)**; <50,000 SF per building. A portfolio "
    "over $15M or over 5 buildings = gate flag (Ruling 5: surfaces for Gabriel's call, never a kill).\n"
)


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("buybox_drift_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load_probe_module()


def flags(text):
    return P.scan_text(text)


def assert_clean(text, why):
    got = flags(text)
    assert got == [], "expected CLEAN (%s), got %r" % (why, got)


def assert_flags(text, why, n=1):
    got = flags(text)
    assert len(got) == n, "expected %d finding(s) (%s), got %r" % (n, why, got)
    return got


# --------------------------------------------------------------------------- UNIT: price rule

def test_canon_gate2_line_clean_unit():
    assert_clean(CANON_GATE2, "the canon line itself")


def test_sub_10m_buybox_without_portfolio_flags_unit():
    got = assert_flags("- Buy-box: sub-$10M, sub-50K SF, Class B/C industrial/flex.\n",
                       "CLAUDE.md pre-#391 wording")
    assert got[0][0] == 1, got


def test_ceiling_phrasings_all_flag_unit():
    for line in (
        "ORA targets sub-$10M, sub-50K SF, Class B/C assets.\n",
        "a family-office industrial buyer working sub-$10M Class B/C.\n",
        "a family-office owner that buys under $10M and under 50K SF.\n",
        "Acquisition focus: sub-$10M, shallow-bay, multi-tenant.\n",
        "- **$1M–$10M per acquisition, sub-50,000 SF per building.**\n",
        "- **Price:** **$500K-$10M** total.\n",
        "- ORA box: Class B/C shallow-bay industrial/flex · $1-10M\n",
        "- Deal size: up to $10 million.\n",
        "- Buy box price ≤$10M per deal.\n",
        "- Buy-box: $10M max per acquisition.\n",
    ):
        assert_flags(line, "ceiling phrasing: %r" % line)


def test_portfolio_mention_same_line_clean_unit():
    assert_clean("- ORA box: $1-10M (portfolio sold together: up to $15M total, Amendment H)\n",
                 "portfolio path on the same line")
    assert_clean("- Buy-box: sub-$10M single asset; 2-5 building portfolios sold together to $15M.\n",
                 "sold-together wording")


def test_portfolio_mention_wrapped_bullet_clean_unit():
    text = ("- **Price:** **$1M–$10M** total for a single-building deal.\n"
            "  **Portfolio path (Amendment H):** buildings sold together are in-box up to **$15M total**.\n")
    assert_clean(text, "portfolio path on the bullet's continuation line")


def test_portfolio_mention_in_other_bullet_does_not_clean_unit():
    text = ("- Buy-box: sub-$10M, sub-50K SF.\n"
            "- Portfolio path (Amendment H): up to $15M total.\n")
    got = assert_flags(text, "portfolio mention belongs to a different bullet")
    assert got[0][0] == 1, got


def test_blank_line_ends_paragraph_unit():
    text = ("ORA targets sub-$10M assets.\n"
            "\n"
            "Amendment H lets a portfolio go to $15M.\n")
    assert_flags(text, "portfolio mention is in the next paragraph")


def test_market_research_prose_clean_unit():
    for line in (
        "| Columbus OH | [GAP — no sub-$10M/small-deal series found] | $6.57/SF NNN |\n",
        "- Owner-user transactions dominate sub-$10M — no institutional competition\n",
        "- Confirmed sub-$10M/building basis: Weston portfolio ~$25M\n",
        "Institutional-only: one portfolio traded ~5.75% cap, not representative of sub-$10M deals\n",
        "STEP 2 (c) dropped every deal over $10M, so a portfolio never reached scoring.\n",
    ):
        assert_clean(line, "no buy-box statement: %r" % line)


def test_sweet_spot_below_ceiling_ignored_unit():
    assert_clean("Deal size $1M-$10M (sweet spot $1.5-6M); a portfolio sold together up to $15M total\n",
                 "sub-band below $10M is not a ceiling claim")


def test_15m_without_portfolio_flags_unit():
    assert_flags("- Buy-box: sub-$15M, sub-50K SF.\n",
                 "$15M applies only to portfolios sold together")


def test_portfolio_ceiling_other_than_15_flags_unit():
    assert_flags("- Buy-box: $500K-$10M single asset; portfolio sold together up to $20M.\n",
                 "portfolio ceiling contradicts canon $15M")


def test_single_asset_ceiling_raised_flags_unit():
    assert_flags("- Buy-box: $500K-$12M per acquisition.\n", "single-asset ceiling above $10M")


def test_10_15m_portfolio_range_clean_unit():
    assert_clean("A $10–15M portfolio sold together was being dropped at the price filter.\n",
                 "$10M is the range floor here, not a ceiling; portfolio named")


def test_aum_and_firm_scale_figures_ignored_unit():
    # live false positives from the first real-tree run (firm.md, portfolio-growth, procurement memo)
    assert_clean("- **AUM:** ~$60M current → **$700–800M target over 35+ years.**\n", "AUM target")
    assert_clean("| Target AUM | $700-800M | 35+ year horizon |\n", "AUM table row")
    assert_clean("ORA targets tooling spend; per-seat SaaS ROI is negative at sub-$150M scale.\n",
                 "firm-scale threshold far above any deal price")


def test_broker_outreach_buybox_flags_unit():
    # live true positive (ora-broker-touch-cadence STEP 3): outbound broker mail restates the box
    assert_flags("asks about off-market industrial listings in ORA's buy-box (sub-$10M, sub-50K SF, "
                 "Class B/C industrial/flex). No form-letter feel.\n", "broker email buy-box text")
    # live true positive (ora-skills market-monitor): survives the target-market context veto
    assert_flags("3. Flag any ORA-relevant deal (sub-$10M, shallow-bay, target market)\n",
                 "ORA-relevant deal filter")


# --------------------------------------------------------------------------- UNIT: size rule

def test_canonical_size_clean_unit():
    assert_clean("- Buy-box: sub-50K SF per building.\n", "canon size")
    assert_clean("- **Size:** **sub-50,000 SF per building.**\n", "canon size, comma form")
    assert_clean("ORA buys under 50K SF.\n", "canon size, under")


def test_size_ceiling_drift_flags_unit():
    assert_flags("- Buy-box: sub-60K SF per building.\n", "size ceiling contradicts 50K")
    assert_flags("- **Size:** under 75,000 SF per building, ORA targets.\n", "size ceiling 75K")


def test_size_ceiling_without_context_ignored_unit():
    assert_clean("Recorded industrial sales <150K SF for Franklin OH into two Notion DBs.\n",
                 "market-intel cap, not the buy-box")


def test_size_sub_bands_and_floors_ignored_unit():
    # live false positives: sub-scale floors, narrower target profiles, suite-size bands
    assert_clean("sub-scale exclusions (<10K SF or <$1M: address + SF + ask -- the buy-box floor is unchanged)\n",
                 "SF floor written with '<'")
    assert_clean("- **Execute:** single-asset test entry; target multi-tenant shallow-bay, sub-30K SF\n",
                 "narrower market target is inside the box")
    assert_clean("1. **Product:** functional single-tenant ≤40,000 SF. Quasi-IOS <20K SF = explicit target profile.\n",
                 "canon Gate 1 product sub-bands")


def test_target_market_is_not_buybox_context_unit():
    assert_clean("Track ALL industrial sales <150,000 SF recorded weekly in ORA's target-market counties.\n",
                 "'target-market' names geography, not the box")


def test_unit_size_range_ignored_unit():
    assert_clean("owner of shallow-bay flex (units roughly 1,000-20,000 SF) that buys under 50K SF\n",
                 "a suite-size range is not a building ceiling")


# --------------------------------------------------------------------------- UNIT: allowlist

def test_changelog_version_line_clean_unit():
    assert_clean("- **v1.10 (2026-10-30):** the $500K–$10M buy-box filter dropped portfolios.\n",
                 "version-led changelog bullet")
    assert_clean("| v4.40 | 2026-10-30 | Gabriel | buy-box was sub-$10M before Amendment | none |\n",
                 "version-led table row")
    assert_clean("- 2026-10-30: buy-box moved off sub-$10M.\n", "date-led history bullet")


def test_changelog_wrapped_bullet_clean_unit():
    text = ("- **v2.9 (2026-07-14):** tightened the filter so ORA targets\n"
            "  sub-$10M only.\n")
    assert_clean(text, "continuation line of a changelog bullet")


def test_changelog_section_clean_unit():
    text = ("## Changelog\n"
            "- tightened the filter: ORA targets sub-$10M only.\n"
            "## Rules\n"
            "- Buy-box: sub-$10M.\n")
    got = assert_flags(text, "only the bullet outside the Changelog section")
    assert got[0][0] == 4, got


def test_version_history_heading_clean_unit():
    text = ("### Version history\n"
            "Old wording: ORA targets sub-$10M.\n")
    assert_clean(text, "version history section")


def test_code_fence_lines_are_separate_units_unit():
    text = ("```\n"
            "# buy-box comment line\n"
            "#   \"under $10M ... a $1,000/mo ... a $3.3M\"\n"
            "```\n")
    assert_clean(text, "fence lines do not borrow context from neighbours")


def test_heading_resets_changelog_section_at_same_level_unit():
    text = ("## Revision history\n"
            "### v1.1\n"
            "- ORA targets sub-$10M.\n"
            "## Scope\n"
            "- ORA targets sub-$10M.\n")
    got = assert_flags(text, "subheading stays inside history; next H2 exits it")
    assert got[0][0] == 5, got


# --------------------------------------------------------------------------- UNIT: review round 1
# (adversarial REFUTE pass 2026-11-03: C2 heading over-suppression, C3 bare-"portfolio" qualifier,
#  C4 dated live rules, C5 recall phrasings, C6 lender/fund figures)

def test_non_history_headings_do_not_allowlist_unit():
    assert_flags("## Tenant history\n- Buy-box: sub-$10M.\n", "'history' inside an ordinary heading")
    assert_flags("# Buy-box history & rules\n## Rules\n- Buy-box: sub-$10M.\n", "H1 mentioning history")
    assert_flags("## CRITICAL PROVISIONS (Gabriel's history-derived)\n- ORA targets sub-$10M.\n",
                 "live legal-intelligence heading shape")
    assert_clean("## Build history\n- ORA targets sub-$10M.\n", "a real history section")
    assert_clean("## Changelog (v1.x)\n- ORA targets sub-$10M.\n", "qualified changelog heading")


def test_bare_portfolio_word_is_not_the_portfolio_path_unit():
    for line in (
        "- Buy-box: sub-$10M per deal; fits the existing portfolio mix.\n",
        "- Buy-box: sub-$10M. No portfolio deals.\n",
        "- Buy-box: sub-$10M (see portfolio-growth).\n",
        "- Buy-box: up to $15M, portfolio-agnostic.\n",
    ):
        assert_flags(line, "owned-book 'portfolio' is not Amendment H: %r" % line)
    assert_clean("- Buy-box: sub-$10M single asset (portfolio path: to $15M).\n", "explicit portfolio path")


def test_dated_live_rule_is_not_changelog_unit():
    assert_flags("- 2026-11-01 standing rule: Buy-box sub-$10M.\n", "date-led live rule")
    assert_flags("- v2.0 buy-box: sub-$10M.\n", "version word in a live rule")


def test_recall_phrasings_unit():
    for line in (
        "- Oxford acquires sub-$10M industrial.\n",
        "- Investment criteria: sub-$10M, Class B/C.\n",
        "| Price | sub-$10M |\n",
        "- Buy-box: at most $10M per deal.\n",
        "- Buy-box: $10M or less per deal.\n",
        "- Buy-box: not exceeding $10M.\n",
    ):
        assert_flags(line, "recall: %r" % line)


def test_lender_and_fund_figures_ignored_unit():
    for line in (
        "- Lender targets loans up to $20M.\n",
        "- Fund size: up to $25M equity raise.\n",
        "- Loan size: up to $12M.\n",
    ):
        assert_clean(line, "financing figure, not the buy-box: %r" % line)


# --------------------------------------------------------------------------- UNIT: canon anchor

def test_check_canon_accepts_current_canon_unit():
    assert P.check_canon_text("# STAGE 0\n" + CANON_GATE2) == []


def test_check_canon_detects_moved_canon_unit():
    moved = CANON_GATE2.replace("≤$15M", "≤$20M")
    probs = P.check_canon_text("# STAGE 0\n" + moved)
    assert probs and any("15" in p for p in probs), probs


def test_check_canon_missing_gate_line_unit():
    probs = P.check_canon_text("# STAGE 0\nnothing here\n")
    assert probs, probs


# --------------------------------------------------------------------------- E2E helpers

DRIFT = "- Buy-box: sub-$10M, sub-50K SF, Class B/C industrial/flex.\n"
CLEAN = "- Buy-box: $500K-$10M single asset; portfolio of 2-5 buildings sold together to $15M.\n"

FILE_CLASSES = {
    "CLAUDE.md": "CLAUDE.md",
    "agent": os.path.join("agents", "deal-recon.md"),
    "scheduled-task": os.path.join("scheduled-tasks", "ora-am-brief", "SKILL.md"),
    "skill": os.path.join("skills", "some-skill", "SKILL.md"),
    "memory": os.path.join("projects", "C--Users-Owner-X", "memory", "firm.md"),
    "ora-skills": os.path.join("@skills", "deal-comparison", "SKILL.md"),
}


class Tree(object):
    def __init__(self):
        self.base = tempfile.mkdtemp(prefix="buybox_probe_test_")
        self.claude = os.path.join(self.base, "claude")
        self.skills = os.path.join(self.base, "ora-skills")
        self.write(os.path.join("@skills", "acquisition-underwriting", "SKILL.md"),
                   "# STAGE 0\n" + CANON_GATE2)
        for rel in FILE_CLASSES.values():
            self.write(rel, CLEAN)

    def path(self, rel):
        if rel.startswith("@skills"):
            return os.path.join(self.skills, rel[len("@skills") + 1:])
        return os.path.join(self.claude, rel)

    def write(self, rel, text):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def run(self, extra_env=None):
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        cmd = [sys.executable, PROBE, "--claude-root", self.claude, "--skills-root", self.skills]
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env)

    def close(self):
        shutil.rmtree(self.base, ignore_errors=True)


def _with_tree(fn):
    t = Tree()
    try:
        fn(t)
    finally:
        t.close()


# --------------------------------------------------------------------------- E2E

def test_clean_tree_exits_0_e2e():
    def body(t):
        r = t.run()
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
        assert "OK" in r.stdout, r.stdout
    _with_tree(body)


def test_each_file_class_drift_exits_1_e2e():
    for cls, rel in FILE_CLASSES.items():
        def body(t, cls=cls, rel=rel):
            p = t.write(rel, "# Heading\n" + DRIFT)
            r = t.run()
            assert r.returncode == 1, (cls, r.returncode, r.stdout, r.stderr)
            assert os.path.normpath(p) + ":2" in r.stdout, (cls, r.stdout)
        _with_tree(body)


def test_archive_paths_excluded_e2e():
    def body(t):
        t.write(os.path.join("scheduled-tasks", "_archive_2026-08-09_retired", "SKILL.md"), DRIFT)
        t.write(os.path.join("scheduled-tasks", "_archive", "SKILL.md"), DRIFT)
        t.write(os.path.join("skills", "_archive_2026-08-13_retired", "SKILL.md"), DRIFT)
        t.write(os.path.join("@skills", "_archive", "SKILL.md"), DRIFT)
        r = t.run()
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    _with_tree(body)


def test_narrative_logs_excluded_e2e():
    def body(t):
        mem = os.path.join("projects", "C--Users-Owner-X", "memory")
        for name in ("event_log.md", "event_log_2026-07-09.md", "MEMORY.md",
                     "INDEX_projects_system.md", "open-items-tracker.md",
                     "deal-decision-ledger.md"):
            t.write(os.path.join(mem, name), DRIFT)
        t.write(os.path.join("@skills", "acquisition-underwriting", "versions", "CHANGELOG-v4.23.md"), DRIFT)
        r = t.run()
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    _with_tree(body)


def test_missing_canon_exits_2_e2e():
    def body(t):
        os.remove(t.path(os.path.join("@skills", "acquisition-underwriting", "SKILL.md")))
        r = t.run()
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    _with_tree(body)


def test_moved_canon_exits_2_e2e():
    def body(t):
        t.write(os.path.join("@skills", "acquisition-underwriting", "SKILL.md"),
                "# STAGE 0\n" + CANON_GATE2.replace("<50,000 SF", "<60,000 SF"))
        r = t.run()
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
        assert "canon" in (r.stdout + r.stderr).lower(), r.stdout + r.stderr
    _with_tree(body)


def test_missing_or_bad_root_exits_2_e2e():
    # review C1: a typo'd --claude-root used to scan nothing and report OK (fail-open)
    def body(t):
        r = subprocess.run([sys.executable, PROBE, "--claude-root", os.path.join(t.base, "nope"),
                            "--skills-root", t.skills], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
        r = subprocess.run([sys.executable, PROBE, "--claude-root", "--quiet", "--skills-root", t.skills],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    _with_tree(body)


def test_unreadable_target_exits_2_e2e():
    def body(t):
        # a DIRECTORY named SKILL.md matches the scheduled-tasks/*/SKILL.md glob but cannot be
        # opened -> probe error, never a silent skip.
        os.makedirs(os.path.join(t.claude, "scheduled-tasks", "broken", "SKILL.md"))
        r = t.run()
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    _with_tree(body)


def test_utf8_output_survives_cp1252_stdout_e2e():
    def body(t):
        t.write("CLAUDE.md", "- Buy-box ≤$10M — Class B/C ≥ flex.\n")
        r = t.run(extra_env={"PYTHONIOENCODING": "cp1252"})
        assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
        assert "Traceback" not in r.stderr, r.stderr
    _with_tree(body)


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except AssertionError as e:
            failed += 1
            print("FAIL  %s: %s" % (name, str(e).encode("ascii", "replace").decode("ascii")))
    if failed:
        print("%d of %d BUYBOX-PROBE TESTS FAILED" % (failed, len(tests)))
        sys.exit(1)
    print("ALL BUYBOX-PROBE TESTS PASS (%d)" % len(tests))


if __name__ == "__main__":
    main()
