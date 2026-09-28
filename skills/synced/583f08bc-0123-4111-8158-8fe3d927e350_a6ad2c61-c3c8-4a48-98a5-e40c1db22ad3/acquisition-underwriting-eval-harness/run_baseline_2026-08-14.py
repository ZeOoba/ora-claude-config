"""One-off driver for the 2026-08-14 baseline run.

Feeds each golden_set/*.json's own `golden` block back through diff_verdict()
as the "observed" result (since golden == the fresh 2026-08-14 replay itself,
per the re-baselining decision documented in each file's known_gaps) and
writes the first dated snapshot via record_run(). This establishes run #1 --
future doctrine-edit runs compare their live replay output against this
snapshot's golden values, not against this script.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))

from diff_verdict import diff_verdict
from record_run import record_run

GOLDEN_DIR = Path(__file__).parent / "golden_set"
RUN_DIR = Path(__file__).parent / "runs"
SKILL_SHA = "83547a76651c53c8f3311c2f30db53cbf16fd219"


def main():
    results = []
    for f in sorted(GOLDEN_DIR.glob("*.json")):
        golden = json.loads(f.read_text(encoding="utf-8"))
        g = golden["golden"]
        observed = {
            "combined": g["combined"],
            "quality": g.get("quality"),
            "economics": g.get("economics"),
            "expected_score": g.get("expected_score"),
            "p_exec_pct": g.get("p_exec_pct"),
            "verdict_tier": g.get("verdict_tier"),
            "floor_result": g.get("floor_result"),
            "category_breakdown": g.get("category_breakdown"),
            "notes": g.get("replay_notes"),
        }
        result = diff_verdict(golden, observed)
        results.append(result)
        print(f"{result['deal_id']:<45} {result['status']:<5} scored={result['scored']!s:<5} "
              f"combined={result['combined_golden']:.1f} delta={result['combined_delta']:+.2f}")

    out = record_run(
        results,
        run_dir=str(RUN_DIR),
        skill_sha=SKILL_SHA,
        run_label="baseline-rebaselined",
    )
    print(f"\nSnapshot written: {out['snapshot_path']}")
    print(f"Summary: {out['summary']}")


if __name__ == "__main__":
    main()
