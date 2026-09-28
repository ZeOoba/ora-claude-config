"""Self-test: confirm diff_verdict() flags the mutated-Port-Sheldon replay
against the REAL (unmutated) golden file. Never writes to runs/ -- this is a
fixture-only proof, not a real run. See SKILL.md 'Self-test' section.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from diff_verdict import diff_verdict

golden_path = Path(__file__).parent.parent / "golden_set" / "2196-port-sheldon-st-jenison-mi.json"
golden = json.loads(golden_path.read_text(encoding="utf-8"))

# Observed = the frozen replay's result AGAINST THE MUTATED FIXTURE
# (asking_price $1,995,000 -> $995,000), reported by the fable-pinned subagent.
observed_from_mutated_replay = {
    "combined": 71.5,
    "quality": 29.0,
    "economics": 42.5,
    "expected_score": 50.0,
    "p_exec_pct": 70.0,
    "verdict_tier": "T2 WATCH",
    "floor_result": "CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)",
    "category_breakdown": {
        "basis": 22.8, "yield": 19.7, "product_physical": 13.0,
        "market_location": 7.0, "seller_motivation": 0.0,
        "tenancy_lease": 0.0, "value_add": 9.0,
    },
    "notes": "mutated-input self-test replay",
}

result = diff_verdict(golden, observed_from_mutated_replay)

print(json.dumps(result, indent=2))
print()
print(f"golden (real, unmutated asking $1,995,000):  Combined = {golden['golden']['combined']}")
print(f"observed (mutated asking $995,000 fixture):   Combined = {observed_from_mutated_replay['combined']}")
print(f"delta = {result['combined_delta']:+.2f}  (tolerance = {result['tolerance_pts']})")
print(f"status = {result['status']}")

assert result["status"] == "FLAG", "SELF-TEST FAILED: mutation was not flagged"
assert abs(result["combined_delta"]) > result["tolerance_pts"], "delta not actually beyond tolerance"
assert result["scored"] is True, "Port Sheldon should be a scored (HIGH-confidence) row"
print("\nSELF-TEST PASSED: mutated-input regression was correctly flagged.")
