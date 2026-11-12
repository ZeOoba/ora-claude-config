#!/usr/bin/env python3
"""Tests for snapshot-guard.py (stdlib unittest; no real data)."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('snapshot_guard', os.path.join(HERE, 'snapshot-guard.py'))
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)

BASE = {
    'meta': {'asOf': '2026-11-01', 'generatedAt': '2026-11-10T06:15:00Z'},
    'quickbooks': {'parsedAt': '2026-11-10T06:15:01Z', 'properties': [{'id': 'p1'}]},
    'leases': [{'id': 'L1', 'leaseEnd': '2027-01-31'}, {'id': 'L2', 'leaseEnd': '2028-06-30'}],
    'deals': [{'id': 'd1'}], 'counterparties': [{'id': 'c1'}], 'properties': [{'id': 'p1'}],
    'loans': [{'id': 'n1'}], 'arBalances': {'L1': 1}, 'dataQuality': [{'severity': 'info'}],
}


def clone(o):
    return json.loads(json.dumps(o))


class Guard(unittest.TestCase):
    def test_clock_only_change_is_not_material(self):
        cur = clone(BASE)
        cur['meta']['generatedAt'] = '2026-11-17T06:15:00Z'
        cur['quickbooks']['parsedAt'] = '2026-11-17T06:15:02Z'
        lines, material, shrunk = sg.evaluate(BASE, cur)
        self.assertFalse(material)
        self.assertFalse(shrunk)
        self.assertIn('meta.generatedAt', lines[0])

    def test_real_change_is_material(self):
        cur = clone(BASE)
        cur['leases'][0]['leaseEnd'] = '2027-02-28'
        _, material, shrunk = sg.evaluate(BASE, cur)
        self.assertTrue(material)
        self.assertFalse(shrunk)

    def test_list_shrink_is_flagged(self):
        cur = clone(BASE)
        cur['deals'] = []
        lines, _, shrunk = sg.evaluate(BASE, cur)
        self.assertTrue(shrunk)
        self.assertIn('SHRINK deals: 1 -> 0', lines)

    def test_non_list_section_emptied_is_flagged(self):
        cur = clone(BASE)
        cur['arBalances'] = {}
        lines, _, shrunk = sg.evaluate(BASE, cur)
        self.assertTrue(shrunk)
        self.assertIn('SHRINK arBalances: populated -> empty/null', lines)

    def test_fewer_dataquality_flags_is_not_shrink(self):
        cur = clone(BASE)
        cur['dataQuality'] = []
        _, _, shrunk = sg.evaluate(BASE, cur)
        self.assertFalse(shrunk)

    def test_emptied_meta_is_not_shrink(self):
        cur = clone(BASE)
        cur['meta'] = {}
        lines, _, shrunk = sg.evaluate(BASE, cur)
        self.assertFalse(shrunk)
        self.assertFalse(any(l.startswith('SHRINK meta') for l in lines))

    def test_non_iso_at_value_is_material(self):
        prev, cur = clone(BASE), clone(BASE)
        prev['leases'][0]['signedAt'] = 'pending'
        cur['leases'][0]['signedAt'] = 'executed'
        _, material, _ = sg.evaluate(prev, cur)
        self.assertTrue(material)

    def test_section_removed_entirely_is_shrink(self):
        cur = clone(BASE)
        del cur['arBalances']
        lines, _, shrunk = sg.evaluate(BASE, cur)
        self.assertTrue(shrunk)
        self.assertIn('SHRINK arBalances: populated -> empty/null', lines)

    def test_list_key_removed_entirely_is_shrink(self):
        cur = clone(BASE)
        del cur['loans']
        _, _, shrunk = sg.evaluate(BASE, cur)
        self.assertTrue(shrunk)

    def test_malformed_list_section_raises(self):
        cur = clone(BASE)
        cur['leases'] = None
        with self.assertRaises(ValueError):
            sg.evaluate(BASE, cur)

    def test_material_lists_changed_paths(self):
        cur = clone(BASE)
        cur['leases'][0]['leaseEnd'] = '2027-02-28'
        lines, material, _ = sg.evaluate(BASE, cur)
        self.assertTrue(material)
        self.assertIn('  changed leases[0].leaseEnd', lines)

    def _cli(self, prev_obj, cur_obj):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'a.json'), os.path.join(d, 'b.json')
            for p, o in ((a, prev_obj), (b, cur_obj)):
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(o, f)
            return subprocess.run([sys.executable, os.path.join(HERE, 'snapshot-guard.py'), a, b],
                                  capture_output=True, text=True)

    def test_cli_json_array_gives_no_verdict(self):
        r = self._cli(BASE, [1, 2])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('VERDICT', r.stdout)

    def test_cli_malformed_section_gives_no_verdict(self):
        cur = clone(BASE)
        cur['leases'] = 5
        r = self._cli(BASE, cur)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('VERDICT', r.stdout)

    def test_cli_missing_file_gives_no_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'prev.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(BASE, f)
            r = subprocess.run([sys.executable, os.path.join(HERE, 'snapshot-guard.py'), p,
                                os.path.join(d, 'absent.json')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn('VERDICT', r.stdout)

    def test_cli_verdict_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'a.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(BASE, f)
            r = subprocess.run([sys.executable, os.path.join(HERE, 'snapshot-guard.py'), p, p],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn('MATERIAL: none', r.stdout)
            self.assertIn('VERDICT: clean', r.stdout)


if __name__ == '__main__':
    unittest.main()
