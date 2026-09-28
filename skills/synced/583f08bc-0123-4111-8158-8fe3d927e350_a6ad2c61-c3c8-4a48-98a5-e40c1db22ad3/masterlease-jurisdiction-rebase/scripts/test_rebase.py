#!/usr/bin/env python3
"""Tests for rebase.py (masterlease-jurisdiction-rebase v1.1).

Three cases required by the 2026-08-03 Master Lease conformance session close-out:
1. Parity against a known master — the real OH v2.6 controlled master rebases
   cleanly (no anchor drift, no post-check failure) into a state-conformed template.
2. article() unit cases, including the "an Ohio" / "a Utah" fix that motivated v1.1.
3. Fail-closed on a missing entity_state field and on a RESEARCH-REQUIRED state.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = HERE.parent / "config"
FIXTURE_MASTER = HERE / "fixtures" / "ORA_MasterLease_ShallowBayIndustrial_v2.6_TEMPLATE.docx"

sys.path.insert(0, str(HERE))
import rebase  # noqa: E402
from docx import Document  # noqa: E402


class ArticleTests(unittest.TestCase):
    """The v1.1 fix: 'an' before a vowel-sound state name, 'a Utah' by exception."""

    def test_vowel_initial_states_take_an(self):
        for state in ("Ohio", "Indiana", "Alabama", "Illinois", "Iowa", "Arizona"):
            with self.subTest(state=state):
                self.assertEqual(rebase.article(state), "an")

    def test_consonant_and_u_states_take_a(self):
        # Utah is the case v1.1 exists for: 'U' reads as a consonant sound, so it
        # must NOT fall into the vowel-letter bucket with Indiana/Ohio.
        for state in ("Maryland", "Missouri", "Wisconsin", "Kansas", "Tennessee", "Utah"):
            with self.subTest(state=state):
                self.assertEqual(rebase.article(state), "a")


class FailClosedTests(unittest.TestCase):
    """v1.1: entity_state is REQUIRED and sourced; RESEARCH-REQUIRED states refuse to run."""

    def test_build_rules_fails_closed_on_missing_entity_state(self):
        P = {"entity": "TEST PROPERTY, LLC", "state_code": "MD"}  # no entity_state
        L = {"state": "Maryland"}
        with self.assertRaises(SystemExit) as ctx:
            rebase.build_rules(P, L)
        self.assertIn("entity_state", str(ctx.exception))

    def test_cli_fails_closed_on_research_required_state(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            scripts_dir = td / "scripts"
            config_dir = td / "config"
            scripts_dir.mkdir()
            config_dir.mkdir()
            shutil.copy(HERE / "rebase.py", scripts_dir / "rebase.py")

            real_overlays = json.loads((CONFIG / "state_overlays.json").read_text(encoding="utf-8"))
            self.assertTrue(
                real_overlays["IN"].get("RESEARCH_REQUIRED"),
                "fixture assumption broken: IN is expected to be RESEARCH-REQUIRED in the real config",
            )
            (config_dir / "state_overlays.json").write_text(
                json.dumps({"IN": real_overlays["IN"]}), encoding="utf-8"
            )
            (config_dir / "properties.json").write_text(
                json.dumps({
                    "TEST-IN": {
                        "state_code": "IN",
                        "entity": "TEST INDIANA, LLC",
                        "entity_state": "Indiana",
                        "label": "TEST-IN",
                        "premises": "1 Test St, Test City, Indiana",
                        "building_def": "the building known as 1 Test St, Test City, Indiana, "
                                         "containing 1,000 square feet of rentable area",
                        "project_def": None,
                        "share_denominator": "bears to the total rentable square footage of the "
                                              "Building, being 1,000 square feet ",
                        "payment_direction": None,
                        "pm_block": ["COPY TO:[PROPERTY MANAGER]", "[MANAGER STREET ADDRESS]",
                                     "[MANAGER CITY, STATE ZIP]", "ATTN: [MANAGER CONTACT]"],
                    }
                }),
                encoding="utf-8",
            )

            out_dir = td / "out"
            result = subprocess.run(
                [sys.executable, str(scripts_dir / "rebase.py"),
                 "--master", str(FIXTURE_MASTER), "--property", "TEST-IN", "--out", str(out_dir)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("RESEARCH-REQUIRED", result.stdout + result.stderr)
            self.assertFalse(out_dir.exists() and any(out_dir.iterdir()),
                              "fail-closed run must not leave a partial output file")


class ParityAgainstKnownMasterTests(unittest.TestCase):
    """The real OH v2.5 controlled master rebases cleanly for every ratified property."""

    @classmethod
    def setUpClass(cls):
        if not FIXTURE_MASTER.exists():
            raise unittest.SkipTest(f"fixture master not found: {FIXTURE_MASTER}")
        cls.properties = json.loads((CONFIG / "properties.json").read_text(encoding="utf-8"))
        cls.states = json.loads((CONFIG / "state_overlays.json").read_text(encoding="utf-8"))

    def _rebase_one(self, key, out_dir):
        P = self.properties[key]
        # Single-tenant variants are anchored to the master's own state and take
        # no overlay (mirrors main()); everything else requires a ratified overlay.
        L = self.states.get(P["state_code"], {}) if P.get("variant") == "single-tenant" \
            else self.states[P["state_code"]]
        # Routes through rebase.rebase_one() -- the same pipeline main() uses -- so a
        # step added there (e.g. the NNN override) can't drift out of sync with its
        # own test again the way it did the first time this override was added
        # (2026-08-04: this test called apply()+insert_savings_clause() directly and
        # missed the new convert_to_nnn() step main() had).
        doc = rebase.rebase_one(FIXTURE_MASTER, P, L)
        out = out_dir / f"{key}.docx"
        doc.save(str(out))
        rebase.post_check(out, P, L)
        return out, P, L

    def test_all_ratified_properties_rebase_cleanly(self):
        # Anchor-drift / post-check assertions inside rebase.py itself are the pass
        # condition here: any mismatch against the real master calls sys.exit().
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            for key in self.properties:
                if key == "_comment":
                    continue
                with self.subTest(property=key):
                    out, P, L = self._rebase_one(key, out_dir)
                    full = "\n".join(p.text for p in Document(str(out)).paragraphs)
                    if P.get("variant") == "single-tenant":
                        # Generic OH-anchored variant: keeps Ohio and its tokens;
                        # post_check() inside _rebase_one carries the assertions.
                        self.assertIn("the entire building situated at [PREMISES ADDRESS]", full)
                        self.assertIn(rebase.SAVINGS_TITLE, full)
                        continue
                    self.assertNotIn("Ohio", full)
                    self.assertIn(P["entity"], full)
                    self.assertIn(L["state"], full)
                    self.assertIn(rebase.SAVINGS_TITLE, full)

    def test_md_easton_entity_state_article_applied(self):
        # Regression guard for the specific v1.1 fix: MD-EAS's entity_state is
        # Maryland ('a Maryland limited liability company'), not article-broken.
        with tempfile.TemporaryDirectory() as td:
            out, P, L = self._rebase_one("MD-EAS", pathlib.Path(td))
            full = "\n".join(p.text for p in Document(str(out)).paragraphs)
            self.assertIn("a Maryland limited liability company", full)
            self.assertNotIn("an Maryland", full)


if __name__ == "__main__":
    unittest.main()
