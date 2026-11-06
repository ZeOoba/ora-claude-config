#!/usr/bin/env python3
"""Tests for target-geography-probe.py (TDD: written before the probe).

WHY (2026-11-05 data-flow review): agents/deal-flow-triage.md and agents/deal-recon.md stated ORA's
seven HOLDINGS states (OH, MD, IN, WI, MO, KS, TN) as its TARGET geography. ora-skills
target-markets.json holds eleven clusters, five of them entry-phase (Grand Rapids MI, Richmond VA,
Des Moines IA, Louisville KY, Chicago-Greater Cook County IL), and lists Nashville TN as a watch
market, not a target. The broker-inbox triage, the first filter on every broker email and OM,
therefore PASSed entry-market listings on geography and treated TN as in-box.

Layers:
  * PORTED: TargetGeographyTests and RoundTwoGeographyTests are ora-skills
    tools/test_doctrine_consistency.py's pinned target-geography tests, verbatim, on the same
    fixture. The probe's target_geography() must keep passing them.
  * DEFECTS: the three live lines as they stood on origin/main 2026-11-05. The ported check alone
    misses all three: deal-recon's Amendment H parenthetical pushes "ORA targets" past the
    160-character lookback, deal-flow-triage's line is a bare "Geography:" label with no "target"
    word, and dd-package-sweep says "buyer working ... across".
  * FALSE POSITIVES: holdings lines from the live tree, which must stay clean.
  * E2E: a throwaway ~/.claude + ora-skills tree run as a subprocess. Scope (agents/ and memory
    only), skipped append-only logs, the exit-code contract (0 clean, 1 drift, 2 probe error), and
    a canon change (a 12th cluster) flipping a once-clean line, so nothing is hard-coded.

HERMETIC BY DESIGN, the same stance as test-buybox-drift-probe.py: no real-tree assertion. The
pre-push hook-tests gate runs every maintenance/test-*.py, so a real-tree check here would block
every push in the repo while any live drift exists. Scanning the live tree is the probe's job.

Run: python maintenance/test-target-geography-probe.py   (stdlib unittest)
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "target-geography-probe.py")


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("target_geography_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load_probe_module()

# Same fixture as ora-skills tools/test_doctrine_consistency.py (target-markets.json v1.14).
MARKETS = ['Columbus OH', 'Kansas City MO/KS', 'Indianapolis IN', 'Maryland (Baltimore/DC)', 'Cincinnati OH',
           'Madison WI', 'Grand Rapids MI', 'Richmond VA', 'Des Moines IA', 'Louisville KY',
           'Chicago–Greater Cook County IL']
STATES = ['IA', 'IL', 'IN', 'KY', 'MD', 'MI', 'MO', 'OH', 'VA', 'WI']
CL = P.Clusters(11, STATES, ['IN', 'MD', 'MO', 'OH', 'WI'], sorted(set(STATES) | {'KS', 'DC'}),
                [(m, P._cluster_tokens(m)) for m in MARKETS])
ENTRY_PHASE = {'Grand Rapids MI', 'Richmond VA', 'Des Moines IA', 'Louisville KY', 'Chicago–Greater Cook County IL'}
MISSING_ENTRY_STATES = 'omits cluster states IA, IL, KY, MI, VA'


def messages(items):
    return [message for message, _ in items]


def canon_json(markets=MARKETS):
    clusters = [{'market': m, 'state': m.split()[-1][:2], 'status': 'entry_phase' if m in ENTRY_PHASE else 'established'}
                for m in markets]
    for c in clusters:
        if c['market'].startswith('Maryland'):
            c['state'] = 'MD'
    return {'version': '1.14', 'updated': '2026-10-20', 'clusters': clusters}


# --------------------------------------------------------------------------- PORTED (verbatim)

class TargetGeographyTests(unittest.TestCase):
    def check(self, line):
        return messages(P.target_geography(line, CL))

    def test_target_line_missing_entry_states_and_listing_tn(self):
        found = self.check('ORA targets sub-$10M assets in OH, MD, IN, WI, MO, KS, and TN (DSCR >= 1.25x)')
        self.assertTrue(any('omits cluster states IA, IL, KY, MI, VA' in m for m in found))
        self.assertTrue(any('lists TN' in m for m in found))

    def test_target_markets_parenthetical(self):
        found = self.check('Covers all ORA target markets (OH, MD, IN, WI, MO, KS, TN) and submarkets.')
        self.assertTrue(any('omits cluster states' in m for m in found))

    def test_state_names_count_as_states(self):
        line = ("ORA's target-market clusters (Columbus OH, Kansas City MO/KS, Indianapolis IN, "
                "Maryland/Baltimore-DC, Madison WI, Grand Rapids MI, Richmond VA, Des Moines IA, Louisville KY)")
        found = self.check(line)
        self.assertTrue(any('omits cluster states IL ' in m for m in found))

    def test_holdings_statement_without_target_is_fine(self):
        self.assertEqual(self.check('ORA spans OH, MD, IN, WI, MO, KS and TN and the editions differ.'), [])

    def test_complete_target_line_is_fine(self):
        line = 'Covers every ORA target market: OH, MO/KS, IN, MD, WI, MI, VA, IA, KY and IL.'
        self.assertEqual(self.check(line), [])

    def test_short_state_mentions_are_not_target_lists(self):
        self.assertEqual(self.check('Target the MD and OH comps first'), [])

    def test_entry_phase_only_list_is_a_subset(self):
        line = ('Entry/beachhead clusters (score 4, "new target market") = Grand Rapids MI, Richmond VA, '
                'Des Moines IA, Louisville KY, Chicago-Greater Cook County IL')
        self.assertEqual(self.check(line), [])

    def test_counted_subset_is_not_the_target_set(self):
        line = ('Five of ten target clusters have no working local news source (OH, MO/KS, MI, KY, TN) and '
                'two are only partly covered (MD: DC/NoVA via Bisnow; WI: Milwaukee proxy).')
        self.assertEqual(self.check(line), [])

    def test_target_word_far_after_the_list_does_not_count(self):
        line = ('Cyclical states (OH/MD/IN/WI/MO/KS/TN/VA/IA/IL): tax chases market on the assessment cycle; '
                'a long clause later mentions the target markets only in passing, far past the list itself.')
        self.assertEqual(self.check(line), [])


class RoundTwoGeographyTests(unittest.TestCase):
    """Misses and false positives from the ora-skills 2026-11-05 adversarial review (finding C2c)."""

    def check(self, line):
        return messages(P.target_geography(line, CL))

    def test_dropping_one_city_in_a_shared_state_is_caught(self):
        line = ('ORA targets assets in its target-market clusters: Columbus OH, Kansas City MO/KS, Indianapolis IN, '
                'Maryland (Baltimore/DC), Madison WI, Grand Rapids MI, Richmond VA, Des Moines IA, '
                'Louisville KY and Chicago–Greater Cook County IL')
        found = self.check(line)
        self.assertTrue(any('missing Cincinnati OH' in m for m in found))

    def test_all_eleven_named_is_clean(self):
        line = ('ORA targets assets in its target-market clusters: Columbus and Cincinnati OH, Kansas City MO/KS, '
                'Indianapolis IN, Maryland (Baltimore/DC), Madison WI, Grand Rapids MI, Richmond VA, '
                'Des Moines IA, Louisville KY and Chicago–Greater Cook County IL')
        self.assertEqual(self.check(line), [])

    def test_target_word_just_after_the_list(self):
        found = self.check('OH, MD, IN, WI, MO, KS and TN are ORA\'s target states.')
        self.assertTrue(any('omits cluster states' in m for m in found))

    def test_non_geographic_targets_word(self):
        self.assertEqual(self.check('Tax-appeal filing targets: OH, MD, IN, WI, MO and KS this year.'), [])

    def test_state_labeled_watch_is_not_a_target_claim(self):
        line = ('- Target markets: OH, MD, IN, MO, KS, WI (Columbus, Cincinnati, Baltimore/DC, Indianapolis, Kansas '
                'City, Madison) + entry-phase MI (Grand Rapids), VA (Richmond), IA (Des Moines), KY (Louisville), '
                'IL (Chicago–Greater Cook County); TN watch')
        self.assertEqual(self.check(line), [])

    def test_holdings_line_that_mentions_targets_first(self):
        line = 'Unlike its target markets, ORA holds property in OH, MD, IN, WI, MO, KS and TN today.'
        self.assertEqual(self.check(line), [])


# --------------------------------------------------------------------------- DEFECTS (live lines)

# Verbatim, origin/main 2026-11-05.
DEAL_RECON_L8 = (
    "You are an acquisitions research analyst for Oxford Realty Advisors (ORA). ORA targets sub-$10M "
    "(2–5-building portfolios sold together up to $15M — acquisition-underwriting Amendment H; a larger or "
    "flagged portfolio is surfaced for Gabriel, never dismissed), sub-50K SF per building, Class B/C "
    "shallow-bay industrial/flex assets in OH, MD, IN, WI, MO, KS, and TN (DSCR >= 1.25x, LTV <= 40%). Your "
    "job is fast, broad reconnaissance on a candidate so Gabriel can decide in minutes whether it's worth "
    "underwriting.")
DEAL_FLOW_TRIAGE_L17 = (
    "- **Geography:** OH, MD, IN, WI, MO, KS, TN. (Core: DC Metro/MD, Baltimore, Columbus OH, Indianapolis IN, "
    "Kansas City MO. Expansion: WI, KS, TN.)")
DD_PACKAGE_SWEEP_L8 = (
    "You are the due-diligence document reader for Oxford Realty Advisors (ORA), a family-office industrial "
    "buyer working sub-$10M (2–5-building portfolios up to $15M, acquisition-underwriting Amendment H), "
    "sub-50K SF per building, Class B/C industrial and flex across OH, MD, IN, WI, MO, KS and TN.")

# ora-skills verified-deal-recon v1.4 (verified-deal-recon/references/verified-deal-recon.js), the
# reference wording deal-recon line 8 is rewritten to.
REFERENCE_V14 = (
    "You are an acquisitions research analyst for Oxford Realty Advisors (ORA). ORA targets sub-$10M "
    "(2–5-building portfolios sold together up to $15M — acquisition-underwriting Amendment H; a larger or "
    "flagged portfolio is surfaced for Gabriel, never dismissed), sub-50K SF per building, Class B/C "
    "shallow-bay industrial/flex assets in its target-market clusters: Columbus and Cincinnati OH, Kansas "
    "City MO/KS, Indianapolis IN, Maryland (Baltimore/DC), Madison WI, Grand Rapids MI, Richmond VA, Des "
    "Moines IA, Louisville KY and Chicago–Greater Cook County IL (target-markets.json in the ora-skills repo "
    "is authoritative). Governors are confirmed in underwriting, not here: DSCR >= 1.25x; LTV <= 40% "
    "portfolio aggregate and a 65% per-property refi ceiling. Your job is fast, broad reconnaissance on a "
    "candidate so Gabriel can decide in minutes whether it's worth underwriting.")
FIXED_TRIAGE_L17 = (
    "- **Geography:** ORA's target-market clusters (ora-skills `target-markets.json` is authoritative). "
    "Established: Columbus and Cincinnati OH, Kansas City MO/KS, Indianapolis IN, Maryland (Baltimore/DC), "
    "Madison WI. Entry-phase: Grand Rapids MI, Richmond VA, Des Moines IA, Louisville KY, Chicago–Greater Cook "
    "County IL. A town within 30 min of an ESTABLISHED cluster is in-box as a satellite (acquisition-underwriting "
    "STAGE 0 Gate 3; an entry cluster has no satellites until ORA's first close there); if you cannot tell "
    "whether it is that close, WATCH. Anything else fails geography, even in a state where ORA already holds "
    "property.")
# scheduled-tasks/ora-am-brief/SKILL.md:270, origin/main 2026-11-06: the 06:00 broker-mail box screen (C.5.5).
AM_BRIEF_L270 = (
    "- ORA box: Class B/C shallow-bay industrial/flex · $1-10M sourcing filter (the screen floor is $500K, "
    "acquisition-underwriting Gate 2; two floors, Gabriel in-turn 2026-11-03: a $500K–$1M deal is PASS with the "
    "reason \"below $1M sourcing filter (screen floor $500K)\" for Gabriel's hand override) (portfolio sold "
    "together: up to $15M total, Amendment H; >5 buildings, >$15M, or a building failing the type or sub-50,000 "
    "SF rule (the per-building gates visible in a broker email; SCREEN tests the rest per acquisition-underwriting "
    "Amendment H (i)) = WATCH with a \"PORTFOLIO-FLAG: <cause>\" note naming the building and rule, never PASS on "
    "that alone) · sub-50,000 SF/building · OH/MD/IN/WI/MO/KS/TN. Replacement-cost reference ~$85-$120/SF.")
FIXED_AM_BRIEF_L270 = AM_BRIEF_L270.replace(
    "· OH/MD/IN/WI/MO/KS/TN.",
    "· geography = ORA's eleven target-market clusters (ora-skills target-markets.json is authoritative): "
    "established Columbus and Cincinnati OH, Kansas City MO/KS, Indianapolis IN, Maryland (Baltimore/DC), "
    "Madison WI; entry-phase Grand Rapids MI, Richmond VA, Des Moines IA, Louisville KY, Chicago–Greater Cook "
    "County IL; a town within 30 min of an ESTABLISHED cluster counts as a satellite (acquisition-underwriting "
    "STAGE 0 Gate 3; an entry cluster has none before ORA's first close there), WATCH if you cannot tell; "
    "anything else fails geo, even in a state where ORA already holds property.")
# The same line after the owned-submarket exception (Gabriel in-turn 2026-11-06): its geography tail no longer
# ends on the holdings-state clause, and it must stay clean.
OWNED_SUBMARKET_AM_BRIEF_L270 = FIXED_AM_BRIEF_L270.replace(
    "WATCH if you cannot tell; anything else fails geo, even in a state where ORA already holds property.",
    "WATCH if you cannot tell; owned-submarket exception (Gabriel in-turn 2026-11-06; matches "
    "acquisition-underwriting Market & Location, which scores an ORA-owned submarket max): a listing in the "
    "same submarket as a property ORA currently owns (any Oxford share; the same town always qualifies) fits "
    "geo even outside every cluster and satellite, WATCH if you cannot tell whether it is the same submarket "
    "— read holdings once per run, before C.3 scoring: `portfolio.json` `properties[].address` (Master "
    "Workbook lineage) when its `meta.asOf` is ≤7 days old, otherwise the Master Workbook's property rows at "
    "the Block D path (locate the tab via `EXPORT_Index`), and only if the workbook is unreadable the older "
    "snapshot tagged `[holdings STALE as of {asOf}]`; nothing readable → WATCH with `[holdings unreadable]`, "
    "never a PASS verdict on geo; never a holdings list from memory; anything else fails geo, and holding "
    "property elsewhere in the same state is not enough.")
FIXED_DD_PACKAGE_SWEEP_L8 = (
    "You are the due-diligence document reader for Oxford Realty Advisors (ORA), a family-office industrial "
    "buyer working sub-$10M (2–5-building portfolios up to $15M, acquisition-underwriting Amendment H), "
    "sub-50K SF per building, Class B/C industrial and flex in its target-market clusters: Columbus and "
    "Cincinnati OH, Kansas City MO/KS, Indianapolis IN, Maryland (Baltimore/DC), Madison WI, Grand Rapids MI, "
    "Richmond VA, Des Moines IA, Louisville KY and Chicago–Greater Cook County IL (target-markets.json in the "
    "ora-skills repo is authoritative).")


class DefectLineTests(unittest.TestCase):
    def check(self, line):
        return messages(P.target_geography(line, CL))

    def assert_holdings_states_flagged(self, line):
        found = self.check(line)
        self.assertTrue(any(MISSING_ENTRY_STATES in m for m in found), found)
        self.assertTrue(any('lists TN' in m for m in found), found)
        return found

    def test_deal_recon_line_8_is_caught_past_the_lookback(self):
        self.assert_holdings_states_flagged(DEAL_RECON_L8)

    def test_deal_flow_triage_geography_label_is_caught(self):
        found = self.assert_holdings_states_flagged(DEAL_FLOW_TRIAGE_L17)
        self.assertTrue(any('names 4 of 11 clusters' in m for m in found), found)

    def test_dd_package_sweep_buyer_line_is_caught(self):
        self.assert_holdings_states_flagged(DD_PACKAGE_SWEEP_L8)

    def test_reference_wording_is_clean(self):
        self.assertEqual(self.check(REFERENCE_V14), [])

    def test_fixed_triage_line_is_clean(self):
        self.assertEqual(self.check(FIXED_TRIAGE_L17), [])

    def test_fixed_dd_package_sweep_line_is_clean(self):
        self.assertEqual(self.check(FIXED_DD_PACKAGE_SWEEP_L8), [])

    def test_am_brief_box_line_is_caught(self):
        self.assert_holdings_states_flagged(AM_BRIEF_L270)

    def test_fixed_am_brief_box_line_is_clean(self):
        self.assertNotEqual(FIXED_AM_BRIEF_L270, AM_BRIEF_L270)
        self.assertEqual(self.check(FIXED_AM_BRIEF_L270), [])

    def test_owned_submarket_am_brief_box_line_is_clean(self):
        self.assertNotEqual(OWNED_SUBMARKET_AM_BRIEF_L270, FIXED_AM_BRIEF_L270)
        self.assertEqual(self.check(OWNED_SUBMARKET_AM_BRIEF_L270), [])


class AnchorTests(unittest.TestCase):
    """The anchors added on top of the port, and their limits."""

    def check(self, line):
        return messages(P.target_geography(line, CL))

    def test_target_verb_anchors_its_whole_sentence(self):
        line = ('ORA targets sub-$10M (a long parenthetical about the portfolio path that runs well past one hundred '
                'and sixty characters on purpose, so the verb sits far from the list and no sentence ends inside '
                'it), sub-50K SF, Class B/C assets in OH, MD, IN, WI, MO, KS and TN.')
        self.assertGreater(line.index(' OH,') - line.index('ORA targets'), P.LOOKBACK)
        self.assertTrue(any(MISSING_ENTRY_STATES in m for m in self.check(line)))

    def test_target_verb_in_an_earlier_sentence_beyond_the_window_does_not_anchor(self):
        # No holdings word anywhere (REFUTE 2026-11-05: an earlier fixture's "its own calendar" tripped the
        # holdings veto, so the test passed without exercising the sentence bound at all).
        line = ('ORA targets Class B/C shallow-bay flex. Its property-tax work is a separate program with a '
                'calendar, counsel and filing deadlines that vary by county and by state, and it runs all year. '
                'Appeals this year covered OH, MD, IN, WI, MO, KS and TN.')
        self.assertIsNone(P._HOLDINGS.search(line))
        self.assertGreater(line.index(' OH,') - line.index('ORA targets'), P.LOOKBACK)
        self.assertEqual(self.check(line), [])

    def test_target_verb_in_an_earlier_clause_beyond_the_window_does_not_anchor(self):
        """A semicolon outside parentheses ends the clause; deal-recon's semicolon sits inside one."""
        line = ('ORA targets sub-$10M Class B/C flex with a long qualifier that keeps going well past the '
                'lookback window so that only the clause rule can matter for this line at all; separately, '
                'tax counsel files appeals in OH, MD, IN, WI, MO, KS and TN.')
        self.assertIsNone(P._HOLDINGS.search(line))
        self.assertGreater(line.index(' OH,') - line.index('ORA targets'), P.LOOKBACK)
        self.assertEqual(self.check(line), [])

    def test_nearest_anchor_decides_the_holdings_veto(self):
        """The anchor closest to the list is the one tested for a holdings word in between."""
        line = ('- **Geography:** where ORA holds property today; its target markets: '
                'OH, MD, IN, WI, MO, KS and TN.')
        self.assertTrue(any(MISSING_ENTRY_STATES in m for m in self.check(line)))

    def test_geography_label_forms(self):
        for line in ('- **Geography:** OH, MD, IN, WI, MO, KS, TN.',
                     'Geography — OH, MD, IN, WI, MO, KS, TN',
                     '| Geography | OH, MD, IN, WI, MO, KS, TN |',
                     '1. **Target geography:** OH, MD, IN, WI, MO, KS, TN'):
            self.assertTrue(any(MISSING_ENTRY_STATES in m for m in self.check(line)), line)

    def test_buy_box_label_forms(self):
        for line in ('- ORA box: Class B/C shallow-bay industrial/flex · $1-10M sourcing filter · sub-50,000 '
                     'SF/building · OH/MD/IN/WI/MO/KS/TN. Replacement-cost reference ~$85-$120/SF.',
                     '- **Buy-box:** Class B/C flex, sub-$10M, OH, MD, IN, WI, MO, KS, TN'):
            self.assertTrue(any(MISSING_ENTRY_STATES in m for m in self.check(line)), line)

    def test_label_must_lead_the_line(self):
        self.assertEqual(self.check('Shipping geography for the vendor: OH, MD, IN, WI, MO, KS, TN'), [])
        self.assertEqual(self.check('Box trucks serve OH, MD, IN, WI, MO, KS and TN weekly.'), [])

    def test_markets_label_is_not_an_anchor(self):
        """memory/firm.md:17 shape. "Markets: core (+ expansion: WI, KS, TN)" reads as either the holdings
        footprint or a target claim; precision over recall, so it is left for a human, not guessed."""
        line = ('**Markets:** DC Metro/MD, Baltimore, Columbus OH, Indianapolis IN, Kansas City MO '
                '(+ expansion: WI, KS, TN).')
        self.assertEqual(self.check(line), [])

    def test_buyer_verb_anchors(self):
        self.assertTrue(any(MISSING_ENTRY_STATES in m for m in
                            self.check('ORA buys Class B/C flex across OH, MD, IN, WI, MO, KS and TN.')))

    def test_holdings_word_vetoes_the_new_anchors(self):
        self.assertEqual(self.check('- **Geography:** ORA holds property in OH, MD, IN, WI, MO, KS and TN.'), [])
        self.assertEqual(self.check('a family-office industrial buyer working sub-$10M that already holds '
                                    'property in OH, MD, IN, WI, MO, KS and TN'), [])
        self.assertEqual(self.check('- **Geography:** we own property in OH, MD, IN, WI, MO, KS and TN.'), [])


class RefuteRoundOneRecallTests(unittest.TestCase):
    """Plausible restatements the 2026-11-05 REFUTE pass showed slipping through (finding C6, O2)."""

    def check(self, line):
        return messages(P.target_geography(line, CL))

    def test_restatements_are_caught(self):
        for line in ('Seven target states: OH, MD, IN, WI, MO, KS, TN.',
                     'ORA is targeting OH, MD, IN, WI, MO, KS and TN.',
                     "We're targeting Class B/C flex in OH, MD, IN, WI, MO, KS and TN.",
                     'In-box geography: OH, MD, IN, WI, MO, KS, TN',
                     '**Geography** OH, MD, IN, WI, MO, KS, TN',
                     '| Geo | OH, MD, IN, WI, MO, KS, TN |',
                     'ORA sources deals in OH, MD, IN, WI, MO, KS and TN.',
                     'ORA pursues acquisitions in OH, MD, IN, WI, MO, KS and TN.',
                     "ORA's acquisition box: Class B/C flex · OH/MD/IN/WI/MO/KS/TN",
                     'ORA targets, on its own account, Class B/C shallow-bay flex in OH, MD, IN, WI, MO, KS and TN.'):
            self.assertTrue(any(MISSING_ENTRY_STATES in m for m in self.check(line)), line)

    def test_qualified_counts_are_still_subsets(self):
        """A count is a subset only when it says so: "N of M" or a subset word. A bare count claims the set."""
        for line in ('The six established target clusters: Columbus OH, Kansas City MO/KS, Indianapolis IN, '
                     'Maryland (Baltimore/DC), Cincinnati OH, Madison WI.',
                     'Five of ten target clusters lack coverage: OH, MD, IN, WI, MO and KS.'):
            self.assertEqual(self.check(line), [], line)


class LiveHoldingsLinesStayClean(unittest.TestCase):
    """Holdings statements from the live tree (2026-11-05): no target claim, so no finding."""

    LINES = (
        # agents/listing-channel-scout.md:8 (first sentence)
        "You are the listing channel scout for Oxford Realty Advisors (ORA), a private family-office owner of "
        "~513K SF of shallow-bay industrial/flex (units roughly 1,000-20,000 SF, Class B/C) across OH, MD, IN, "
        "WI, MO/KS and TN.",
        # agents/tax-appeal-scout.md:8
        "You are the property-tax scout for Oxford Realty Advisors (ORA), a family-office industrial owner: "
        "~513K SF of shallow-bay industrial/flex, ~140 tenants, ~14 properties across OH, MD, IN, WI, MO, KS "
        "and TN.",
        # CLAUDE.md:9
        "- Firm: ~513K SF shallow-bay industrial/flex · ~140 tenants · ~14 properties (13 Oxford-share) · "
        "OH/MD/IN/WI/MO/KS/TN · ~$60M AUM · 30–40-yr goal $700–800M.",
        # scheduled-tasks/ora-am-brief/SKILL.md:109
        "ORA context (Block B): ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, "
        "MD, IN, WI, MO, KS, TN. Acquisition focus: $500K–$10M single asset; up to $15M for 2–5 buildings sold "
        "together (Amendment H); shallow-bay, multi-tenant, below replacement cost.",
        # memory/project_oxfordra_seo_audit_2026-07.md:25 (excerpt)
        "strategically a D. The firm operates in 7 states (OH/MD/IN/WI/MO/KS/TN) but publishes exactly 1 market "
        "page (Columbus) and has zero blog/insights/seller-education content",
        # agents/mfg-investment-scout.md:3 (excerpt)
        "Sweeps the 15 state economic-development press feeds (PA, MD, VA, WV, OH, IN, MI, KY, MO, KS, WI, IA, "
        "NE, IL, MN) and site-selection news",
    )

    def test_holdings_lines(self):
        for line in self.LINES:
            self.assertEqual(messages(P.target_geography(line, CL)), [], line)


# --------------------------------------------------------------------------- history handling

class HistorySkipTests(unittest.TestCase):
    def test_ported_changelog_and_version_rules(self):
        text = '\n'.join([
            '# Skill (v1.3)',
            'Run across all ten canonical markets.',
            '## Changelog',
            '- the old text said all ten canonical markets',
            '## Procedure',
            '- v1.2 (2026-08-21): HIGH fix: DSCR was tested at 40% LTV, now fixed',
            '**v1.1 (2026-08-15):** Louisville became the 10th; all ten canonical markets',
            'Live line again: all ten canonical markets.',
        ])
        self.assertEqual([n for n, _ in P.live_lines(text)], [1, 2, 5, 8])

    def test_date_led_history_bullet_is_skipped(self):
        text = '- 2026-11-05: deal-recon said ORA targets assets in OH, MD, IN, WI, MO, KS, and TN; fixed.\n'
        self.assertEqual(P.scan_text(text, CL), [])

    def test_dated_live_rule_is_not_history(self):
        text = '- 2026-11-01 standing rule: ORA targets assets in OH, MD, IN, WI, MO, KS and TN.\n'
        self.assertEqual([ln for ln, _, _ in P.scan_text(text, CL)], [1, 1])

    def test_date_digits_are_not_a_subset_count(self):
        """The ported count veto read "10" in "2026-10-01" as "ten clusters" and dropped the line."""
        text = '- 2026-10-01 standing rule: ORA targets assets in OH, MD, IN, WI, MO, KS and TN.\n'
        self.assertEqual([ln for ln, _, _ in P.scan_text(text, CL)], [1, 1])

    def test_scan_text_reports_line_numbers(self):
        text = '# Agent\n\n' + DEAL_FLOW_TRIAGE_L17 + '\n'
        self.assertEqual(sorted({ln for ln, _, _ in P.scan_text(text, CL)}), [3])


# --------------------------------------------------------------------------- count claims (2026-11-06)
# ora-deal-sourcing-scan v2.14 drove every run off "For each of the ten clusters, web-search ..." and a
# multi-line "TEN clusters: Columbus OH, ... LOUISVILLE KY." fallback list, while target-markets.json held
# eleven (Chicago-Greater Cook County IL ratified 2026-09-29). Neither line names five states, so the
# geography rule above passed the file. These pin the count rule that catches it.

SCAN_STEP1 = 'For each of the ten clusters, web-search for newly listed industrial/flex product:'
SCAN_FALLBACK = (
    '  staleness in the email. TEN clusters: Columbus OH, Cincinnati OH, Kansas City\n'
    '  MO/KS, Indianapolis IN, Madison WI, Maryland Baltimore/DC (established) +\n'
    '  entry-phase Grand Rapids MI, Richmond VA, Des Moines IA, LOUISVILLE KY.\n'
    '  (Louisville ratified as the 10th canonical cluster by Gabriel 2026-08-05.)\n')
ELEVEN_LIST = (
    'ELEVEN clusters: Columbus OH, Cincinnati OH, Kansas City MO/KS, Indianapolis IN,\n'
    '  Madison WI, Maryland Baltimore/DC (established) + entry-phase Grand Rapids MI,\n'
    '  Richmond VA, Des Moines IA, Louisville KY, Chicago–Greater Cook County IL.\n')


class CountClaimTests(unittest.TestCase):
    def found(self, text, clusters=CL):
        return [(ln, m) for ln, m, _ in P.scan_text(text, clusters)]

    def test_live_step1_line_is_caught(self):
        found = self.found(SCAN_STEP1 + '\n')
        self.assertEqual([ln for ln, _ in found], [1], found)
        self.assertIn('states 10 clusters', found[0][1])
        self.assertIn('has 11', found[0][1])

    def test_whole_set_phrasings_are_caught(self):
        for line in ("Find listings in ORA's ten target markets.",
                     'Disqualify anything outside the ten clusters; institutional pricing.',
                     'R4 text scouts, all ten clusters.',
                     'The file carries the ten clusters with submarkets.',
                     'Run across all ten canonical markets.',
                     'TEN clusters: Columbus OH and the rest.',
                     'Cap at 30 loads across all 10 target markets.',
                     '7b SOURCE COVERAGE MATRIX — ten clusters × F1 Yardi / F2 Crexi'):
            self.assertTrue(self.found(line + '\n'), line)

    def test_bare_markets_is_a_known_gap(self):
        """Bare "markets" is not counted: on the live tree it only produced false alarms ("the 55 markets",
        "each of the 5 markets" for the entry subset). Pinned so a change here is deliberate."""
        for line in ('Cap at 30 loads across all 10 markets.', '7b MATRIX — ten markets × F1',
                     'markets.json = the 55 markets', 'in each of the 5 markets for listings'):
            self.assertEqual(self.found(line + '\n'), [], line)

    def test_correct_count_is_clean(self):
        for line in ('For each of the eleven clusters, web-search.', 'outside the 11 clusters',
                     "ORA's eleven target markets", 'MATRIX — eleven markets × F1'):
            self.assertEqual(self.found(line + '\n'), [], line)

    def test_subsets_and_non_claims_are_clean(self):
        for line in ('Five of ten target clusters have no news source.',
                     'the six established clusters and the five entry-phase clusters',
                     'The other nine clusters KEEP theirs.',
                     'on the 2026-08-04 run all nine market agents returned UNKNOWN',
                     'the 2026-08-11 run covered nine markets while the canon said ten.',
                     'Louisville ratified as the 10th canonical cluster.',
                     'compare the two markets side by side',
                     'v2.5 — THE SCAN IS NOW TEN MARKETS, NOT NINE; all ten clusters.',
                     '- 2026-08-11: the scan covered all nine clusters.'):
            self.assertEqual(self.found(line + '\n'), [], line)

    def test_multi_line_fallback_list_is_caught_on_count_and_on_list(self):
        found = self.found(SCAN_FALLBACK)
        msgs = [m for _, m in found]
        self.assertEqual({ln for ln, _ in found}, {1}, found)
        self.assertTrue(any('states 10 clusters' in m for m in msgs), msgs)
        self.assertTrue(any('names 10 of 11 clusters' in m and 'Chicago' in m for m in msgs), msgs)

    def test_multi_line_list_with_right_count_but_missing_cluster_is_caught(self):
        text = ELEVEN_LIST.replace(', Chicago–Greater Cook County IL', '')
        msgs = [m for _, m in self.found(text)]
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn('names 10 of 11 clusters', msgs[0])
        self.assertIn('Chicago', msgs[0])

    def test_complete_multi_line_list_is_clean(self):
        self.assertEqual(self.found(ELEVEN_LIST), [])

    def test_list_stops_at_blank_line(self):
        text = 'ELEVEN clusters: Columbus OH, Cincinnati OH, Kansas City MO/KS, Indianapolis IN\n\nChicago.\n'
        msgs = [m for _, m in self.found(text)]
        self.assertTrue(any('names 4 of 11' in m for m in msgs), msgs)

    def test_wrapped_changelog_paragraph_is_history(self):
        text = ('v2.15 — CHICAGO LEG ADDED (2026-11-06). STEP 1 still said\n'
                'For each of the ten clusters, so a Cook listing was disqualified as\n'
                '"outside the ten clusters".\n'
                '\n'
                'For each of the ten clusters, web-search.\n')
        self.assertEqual([ln for ln, _ in self.found(text)], [5])

    def test_heading_ends_a_history_paragraph(self):
        text = '- v1.2 (2026-08-21): old note\n## Procedure\nR4 text scouts, all ten clusters.\n'
        self.assertEqual([ln for ln, _ in self.found(text)], [3])

    def test_count_follows_canon(self):
        twelve = P.Clusters(12, CL.states, CL.established, CL.allowed_states,
                            CL.names + [('Nashville TN', ['Nashville'])])
        msgs = [m for _, m in self.found('For each of the eleven clusters, scan.\n', twelve)]
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn('has 12', msgs[0])


# --------------------------------------------------------------------------- canon loading

class LoadClustersTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='target_geo_canon_')

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def write(self, payload):
        with open(os.path.join(self.base, 'target-markets.json'), 'w', encoding='utf-8') as fh:
            fh.write(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False))

    def test_reads_the_v114_shape(self):
        self.write(canon_json())
        got = P.load_clusters(self.base)
        self.assertEqual((got.count, got.states, got.established, got.allowed_states),
                         (CL.count, CL.states, CL.established, CL.allowed_states))
        # Literal tokens, not P._cluster_tokens again (REFUTE 2026-11-05: comparing the function with itself).
        self.assertEqual(got.names, [
            ('Columbus OH', ['Columbus']), ('Kansas City MO/KS', ['Kansas City']),
            ('Indianapolis IN', ['Indianapolis']), ('Maryland (Baltimore/DC)', ['Maryland', 'Baltimore']),
            ('Cincinnati OH', ['Cincinnati']), ('Madison WI', ['Madison']), ('Grand Rapids MI', ['Grand Rapids']),
            ('Richmond VA', ['Richmond']), ('Des Moines IA', ['Des Moines']), ('Louisville KY', ['Louisville']),
            ('Chicago–Greater Cook County IL', ['Chicago'])])

    def test_rejects_a_canon_it_cannot_trust(self):
        bad = ('not json', {}, {'clusters': []}, {'clusters': 'x'}, {'clusters': [{'market': 'Columbus OH'}]},
               {'clusters': [{'state': 'OH'}]}, {'clusters': [{'market': 'Somewhere', 'state': 'ZZ'}]})
        for payload in bad:
            self.write(payload)
            with self.assertRaises((ValueError, KeyError, TypeError), msg=repr(payload)):
                P.load_clusters(self.base)


# --------------------------------------------------------------------------- E2E

DRIFT = 'ORA targets sub-$10M assets in OH, MD, IN, WI, MO, KS, and TN (DSCR >= 1.25x).\n'
CLEAN = ('ORA targets Class B/C flex in its target-market clusters: Columbus and Cincinnati OH, Kansas City MO/KS, '
         'Indianapolis IN, Maryland (Baltimore/DC), Madison WI, Grand Rapids MI, Richmond VA, Des Moines IA, '
         'Louisville KY and Chicago–Greater Cook County IL.\n')
MEM = os.path.join('projects', 'C--Users-Owner-X', 'memory')


class Tree(object):
    def __init__(self):
        self.base = tempfile.mkdtemp(prefix='target_geo_probe_test_')
        self.claude = os.path.join(self.base, 'claude')
        self.skills = os.path.join(self.base, 'ora-skills')
        os.makedirs(self.skills)
        self.write_canon(canon_json())
        self.write(os.path.join('agents', 'deal-recon.md'), CLEAN)
        self.write(os.path.join(MEM, 'firm.md'), CLEAN)

    def write_canon(self, payload):
        with open(os.path.join(self.skills, 'target-markets.json'), 'w', encoding='utf-8') as fh:
            fh.write(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False))

    def write(self, rel, text):
        p = os.path.join(self.claude, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return p

    def run(self, *extra, **kw):
        env = dict(os.environ)
        env.update(kw.get('env') or {})
        cmd = [sys.executable, PROBE, '--claude-root', self.claude, '--skills-root', self.skills] + list(extra)
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)

    def run_raw(self, args):
        return subprocess.run([sys.executable, PROBE] + args, capture_output=True, text=True,
                              encoding='utf-8', errors='replace')


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.t = Tree()

    def tearDown(self):
        shutil.rmtree(self.t.base, ignore_errors=True)

    def assert_rc(self, r, rc):
        self.assertEqual(r.returncode, rc, (r.returncode, r.stdout, r.stderr))

    def test_clean_tree_exits_0(self):
        r = self.t.run()
        self.assert_rc(r, 0)
        self.assertIn('OK', r.stdout)

    def test_quiet_clean_run_prints_nothing(self):
        r = self.t.run('--quiet')
        self.assert_rc(r, 0)
        self.assertEqual(r.stdout.strip(), '')

    def test_in_scope_drift_exits_1_with_path_and_line(self):
        for rel in (os.path.join('agents', 'deal-flow-triage.md'), os.path.join(MEM, 'firm.md'),
                    os.path.join(MEM, 'MEMORY.md'), os.path.join(MEM, 'INDEX_markets.md'),
                    os.path.join('scheduled-tasks', 'ora-am-brief', 'SKILL.md')):
            p = self.t.write(rel, '# Heading\n' + DRIFT)
            r = self.t.run()
            self.assert_rc(r, 1)
            self.assertIn(os.path.normpath(p) + ':2', r.stdout)
            self.t.write(rel, CLEAN)

    def test_append_only_logs_are_skipped(self):
        for name in ('event_log.md', 'event_log_2026-07-09.md', 'open-items-tracker.md',
                     'open-items-tracker-history.md', 'deal-decision-ledger.md', 'disposition-ledger.md',
                     'ops_decision_log.md',
                     'CHANGELOG.md'):
            self.t.write(os.path.join(MEM, name), DRIFT)
        self.assert_rc(self.t.run(), 0)

    def test_scope_is_agents_memory_and_task_specs_only(self):
        st = 'scheduled-tasks'
        for rel in ('CLAUDE.md', os.path.join('skills', 'some-skill', 'SKILL.md'),
                    os.path.join('agents', '_archive', 'old.md'), os.path.join('agents', 'nested', 'deeper.md'),
                    os.path.join(MEM, '_archive', 'old.md'),
                    os.path.join(st, '_archive_2026-08-09_retired', 'SKILL.md'),
                    os.path.join(st, '_archive_2026-08-09_retired', 'old-task', 'SKILL.md'),
                    os.path.join(st, '_staging', 'SKILL.md'),
                    os.path.join(st, 'ora-am-brief', 'notes.md'),
                    os.path.join(st, 'ora-am-brief', 'SKILL.md.bak-2026-11-06-geography')):
            self.t.write(rel, DRIFT)
        self.assert_rc(self.t.run(), 0)

    def test_history_sections_are_skipped(self):
        self.t.write(os.path.join('agents', 'x.md'), '# X (v1.1)\n\n## Changelog\n- ' + DRIFT +
                     '\n## Procedure\n- 2026-11-05: ' + DRIFT)
        self.assert_rc(self.t.run(), 0)

    def test_a_canon_change_flips_a_once_clean_line(self):
        self.assert_rc(self.t.run(), 0)
        self.t.write_canon(canon_json(MARKETS + ['Pittsburgh PA']))
        r = self.t.run()
        self.assert_rc(r, 1)
        self.assertIn('omits cluster states PA', r.stdout)
        self.assertIn('names 11 of 12 clusters', r.stdout)

    def test_missing_or_untrusted_canon_exits_2(self):
        os.remove(os.path.join(self.t.skills, 'target-markets.json'))
        self.assert_rc(self.t.run(), 2)
        for payload in ('{not json', {'clusters': []}, {'clusters': [{'market': 'Columbus OH'}]}):
            self.t.write_canon(payload)
            self.assert_rc(self.t.run(), 2)

    def test_bad_arguments_and_roots_exit_2(self):
        t = self.t
        self.assert_rc(t.run_raw(['--claude-root', os.path.join(t.base, 'nope'), '--skills-root', t.skills]), 2)
        self.assert_rc(t.run_raw(['--claude-root', t.claude, '--skills-root', os.path.join(t.base, 'nope')]), 2)
        self.assert_rc(t.run_raw(['--claude-root', '--quiet', '--skills-root', t.skills]), 2)
        self.assert_rc(t.run_raw(['--claude-root=' + t.claude, '--skills-root', t.skills]), 2)
        self.assert_rc(t.run_raw(['--bogus']), 2)
        self.assert_rc(t.run_raw(['--claude-root', t.claude, '--skills-root']), 2)
        # REFUTE 2026-11-05 (C7): a stray positional was ignored and the default root scanned instead.
        self.assert_rc(t.run_raw(['--claude-root', t.claude, '--skills-root', t.skills, t.claude]), 2)
        self.assert_rc(t.run_raw([t.claude, '--skills-root', t.skills]), 2)
        self.assert_rc(t.run_raw(['--claude-root', t.claude, '--claude-root', t.claude, '--skills-root', t.skills]), 2)
        empty = os.path.join(t.base, 'empty')
        os.makedirs(empty)
        self.assert_rc(t.run_raw(['--claude-root', empty, '--skills-root', t.skills]), 2)

    def test_unreadable_target_exits_2(self):
        os.makedirs(os.path.join(self.t.claude, 'agents', 'broken.md'))
        self.assert_rc(self.t.run(), 2)

    def test_utf8_output_survives_a_cp1252_stdout(self):
        self.t.write(os.path.join('agents', 'x.md'), '- **Geography:** OH, MD, IN, WI, MO, KS, TN — ≥ core.\n')
        r = self.t.run(env={'PYTHONIOENCODING': 'cp1252'})
        self.assert_rc(r, 1)
        self.assertNotIn('Traceback', r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=1)
