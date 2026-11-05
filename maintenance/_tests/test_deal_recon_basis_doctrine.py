#!/usr/bin/env python3
"""Doctrine pin: the deal-recon agent applies ONE basis threshold, the ratified
vintage-ramp floor, and states its numbers in exactly one place.

Origin: audit finding dealrecon-stale-fair-basis-margin (I-06a, 2026-11-05).
acquisition-underwriting v4.37 (#383) aligned research lanes 5-6 of
agents/deal-recon.md to the ratified floor ("linear vintage ramp: 65% at/below
1995 -> 60% at/above 2005", acquisition-underwriting SKILL.md Stage 1, ratified
2026-07-14) but left two downstream lines on the retired pre-RCT-v03 cliff:
  - the Output-format "Basis read" bullet ("no ~20-25% margin"), and
  - the Recommendation rule ("below-replacement ... -> PURSUE-eligible"),
so every first-look screened basis against two (three) inconsistent thresholds.

The fix keeps lane 6 as the single home of the floor's numbers; the two
downstream lines refer to the floor by name only. Asserting "no digits" in the
Basis-read bullet is what keeps them from forking the value again.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "agents", "deal-recon.md")

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    print(("PASS %s" % name) if cond else ("FAIL %s  %s" % (name, detail)))


def bullet(lines, label):
    """The single Output-format bullet starting with '- **<label>**'."""
    hits = [ln for ln in lines if ln.startswith("- **%s**" % label)]
    return hits[0] if len(hits) == 1 else None


def main():
    with open(AGENT, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()

    # 1. The retired margin cliff is gone, in either dash form.
    retired = re.search(r"20\s*[–—-]\s*25\s*%", text)
    check("retired ~20-25% margin cliff absent", retired is None,
          ascii(retired.group(0)) if retired else "")

    # 2. The Basis-read bullet points at the vintage-ramp floor.
    basis = bullet(lines, "Basis read")
    check("exactly one Basis-read bullet", basis is not None)
    basis = basis or ""
    check("Basis-read bullet references the vintage-ramp floor",
          "vintage-ramp" in basis and "floor" in basis, ascii(basis))

    # 3. No digits in that bullet: the floor's numbers stay single-sourced in lane 6.
    digits = re.findall(r"\d", basis)
    check("Basis-read bullet carries no digits", not digits, ascii(basis))

    # 3b. Lowercase 'pass' must not sit next to the PURSUE/PASS/NEEDS MORE verdict enum.
    check("Basis-read bullet does not say 'pass'",
          re.search(r"\bpass\b", basis, re.IGNORECASE) is None, ascii(basis))

    # 4. Lane 6 still states the ratified floor (guard against deleting the source).
    lane6 = [ln for ln in lines if ln.startswith("6. **Basis vs. replacement**")]
    check("exactly one lane-6 line", len(lane6) == 1)
    lane6 = lane6[0] if lane6 else ""
    check("lane 6 states the vintage-ramp floor 65% -> 60%",
          "vintage-ramp basis floor" in lane6 and "65%" in lane6 and "60%" in lane6
          and "1995" in lane6 and "2005" in lane6, ascii(lane6[:200]))

    # 5. The Recommendation rule uses the same floor, not a bare "below-replacement".
    rec = bullet(lines, "Recommendation") or ""
    check("Recommendation rule references the vintage-ramp floor",
          "vintage-ramp floor" in rec, ascii(rec))
    check("Recommendation rule drops bare below-replacement PURSUE trigger",
          "below-replacement or clear value-add upside" not in rec, ascii(rec))

    passed = sum(1 for ok, _ in _results if ok)
    print("\ndeal-recon basis doctrine tests: %d/%d passed" % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
