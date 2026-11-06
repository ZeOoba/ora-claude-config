#!/usr/bin/env python3
"""Doctrine pin: the deal-recon agent AND the default pre-screen workflow apply ONE
basis threshold -- the ratified vintage-ramp floor on ALL-IN basis -- and bind it
correctly (direction, endpoints, denominator, verdict mapping), not just by keyword.

Canonical source: ora-skills acquisition-underwriting SKILL.md, Stage 1 Basis floor:
"all-in basis (price + 2% closing + CapEx + lease-up carry) discount to replacement,
where replacement = LOW end of the RCT band ... Floor = linear vintage ramp: 65% at/below
1995 -> 60% at/above 2005", construction-type-adjusted (v4.37); ratified 2026-07-14.

Origin: audit finding dealrecon-stale-fair-basis-margin (I-06a, 2026-11-05).
#383 aligned research lanes 5-6 of agents/deal-recon.md but left the Output-format
Basis-read bullet on the retired "~20-25% margin" cliff and the Recommendation rule on
bare "below-replacement". REFUTE round 2 on PR #401 then showed that a token-only test
passed 8 wrong-doctrine mutants (reversed ramp, HIGH denominator, premium-not-discount,
inverted PURSUE, the 20-25% cliff, a $150/SF benchmark, the stale 30/25 ramp, a step
instead of a ramp) and that workflows/verified-deal-recon.js -- the default pre-screen
path -- still carried the retired floor in three prompts. This test pins the binding.

Lane 6 stays the single home of the agent's numbers: the Basis-read bullet refers to
the floor by name only (no digits), so it cannot fork the value again.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
AGENT = os.path.join(ROOT, "agents", "deal-recon.md")
WORKFLOW = os.path.join(ROOT, "workflows", "verified-deal-recon.js")

ARROW = "(?:->|→)"

# Retired thresholds -- none may appear in either file, in any spelling.
RETIRED = {
    "retired 20-25% margin cliff": re.compile(r"20\s*%?\s*(?:[–—-]|to)\s*25\s*%"),
    "retired >=25% floor": re.compile(r"(?:>=|≥)\s*25\s*%"),
    "retired 25%-below/discount floor": re.compile(r"\b25\s*%\s*(?:below|discount)", re.I),
    "retired $150/SF benchmark": re.compile(r"150\s*/\s*SF", re.I),
    "stale 30/25 ramp pair": re.compile(r"\b30\s*%[^\n]{0,60}?\b25\s*%|\b30\s*/\s*25\b"),
}

# Lane 6: the full clause, with each endpoint bound to its vintage, the ramp shape, the
# direction (discount below) and the denominator (construction-type-adjusted LOW).
LANE6_FLOOR = re.compile(
    r"linear\s+vintage-ramp\s+basis\s+floor\s+of\s+a\s+\*\*65%\s+\(1995\s+or\s+earlier\)\s+"
    r"down\s+to\s+60%\s+\(2005\s+or\s+later\)\s+discount\s+below\*\*\s+the\s+"
    r"construction-type-adjusted\s+replacement\s+LOW")

ALL_IN = "all-in basis (price plus closing, CapEx and lease-up carry; [est] where unknown)"

# Recommendation (agent): the verdict mapping, bound phrase by phrase.
REC_MAPPING = {
    "at/above replacement + no value-add path -> PASS": re.compile(
        r"basis at/above replacement with NO credible value-add path to ORA[’']s >8% "
        r"stabilized yield-on-cost " + ARROW + r" PASS;"),
    "fair (short of floor) + value-add path -> NEEDS MORE": re.compile(
        r"\*fair\* basis \(below replacement but short of the vintage-ramp floor\) WITH a "
        r"credible value-add path " + ARROW + r" NEEDS MORE"),
    "clears floor or clear upside -> PURSUE-eligible": re.compile(
        r"basis that clears the vintage-ramp floor, or clear value-add upside " + ARROW +
        r" PURSUE-eligible\."),
    "no PURSUE on fair basis without upside": re.compile(
        r"do NOT call PURSUE on a fair-basis deal with no upside path"),
}

# Workflow: the same floor, stated identically at each of the three prompt sites.
WF_FLOOR = re.compile(
    r"vintage-ramp floor \(65% at/below 1995 " + ARROW + r" 60% at/above 2005, linear between, "
    r"as a discount below the construction-type-adjusted MARKET-SPECIFIC replacement LOW\)")
WF_SITES = {
    "recon dispatch": "Pre-screen this acquisition target for Oxford Realty Advisors",
    "comps-basis verifier": "key:'comps-basis'",
    "synthesis": "Apply ORA basis discipline to the verdict",
}
WF_SYNTH_MAPPING = {
    "at/above replacement + no value-add path -> PASS": re.compile(
        r"basis at/above MARKET-SPECIFIC replacement AND no credible value-add path to >8% "
        r"stabilized yield-on-cost -> PASS;"),
    "fair (short of floor) + value-add path -> NEEDS_MORE": re.compile(
        r"merely-fair basis \(below replacement but short of the vintage-ramp floor\) WITH a "
        r"credible value-add path -> NEEDS_MORE"),
    "all-in basis clears floor or clear upside -> PURSUE": re.compile(
        re.escape(ALL_IN) + r" that clears the " + WF_FLOOR.pattern +
        r" OR clear value-add upside -> PURSUE\."),
}

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    print(("PASS %s" % name) if cond else ("FAIL %s  %s" % (name, detail)))


def bullet(lines, label):
    """The single Output-format bullet starting with '- **<label>**'."""
    hits = [ln for ln in lines if ln.startswith("- **%s**" % label)]
    return hits[0] if len(hits) == 1 else None


def site_line(lines, marker):
    hits = [ln for ln in lines if marker in ln]
    return hits[0] if len(hits) == 1 else None


def main():
    with open(AGENT, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()

    # 1. No retired threshold anywhere in the agent.
    for name, rx in RETIRED.items():
        m = rx.search(text)
        check("agent: %s absent" % name, m is None, ascii(m.group(0)) if m else "")

    # 2. Basis-read bullet: all-in basis vs the named floor against the adjusted LOW.
    basis = bullet(lines, "Basis read")
    check("agent: exactly one Basis-read bullet", basis is not None)
    basis = basis or ""
    check("agent: Basis read tests ALL-IN basis (not entry basis)",
          ALL_IN in basis and "entry basis" not in basis, ascii(basis))
    check("agent: Basis read names the vintage-ramp basis floor",
          "vintage-ramp basis floor" in basis, ascii(basis))
    check("agent: Basis read binds the construction-type-adjusted replacement LOW",
          "against the construction-type-adjusted replacement LOW" in basis, ascii(basis))
    # 3. No digits in that bullet: the floor's numbers stay single-sourced in lane 6.
    check("agent: Basis-read bullet carries no digits", not re.findall(r"\d", basis), ascii(basis))
    # 3b. Lowercase 'pass' must not sit next to the PURSUE/PASS/NEEDS MORE verdict enum.
    check("agent: Basis-read bullet does not say 'pass'",
          re.search(r"\bpass\b", basis, re.IGNORECASE) is None, ascii(basis))

    # 4. Lane 6 states the ratified floor, bound: 65%<->1995, 60%<->2005, linear ramp,
    #    discount below, construction-type-adjusted replacement LOW.
    lane6 = [ln for ln in lines if ln.startswith("6. **Basis vs. replacement**")]
    check("agent: exactly one lane-6 line", len(lane6) == 1)
    lane6 = lane6[0] if lane6 else ""
    check("agent: lane 6 binds the full vintage-ramp floor clause",
          LANE6_FLOOR.search(lane6) is not None, ascii(lane6[:400]))

    # 5. Recommendation: the verdict mapping, bound.
    rec = bullet(lines, "Recommendation") or ""
    for name, rx in REC_MAPPING.items():
        check("agent: Recommendation maps %s" % name, rx.search(rec) is not None, ascii(rec))
    check("agent: Recommendation drops bare below-replacement PURSUE trigger",
          "below-replacement or clear value-add upside" not in rec, ascii(rec))

    # 6. The default pre-screen workflow carries the same doctrine.
    check("workflow: verified-deal-recon.js exists", os.path.isfile(WORKFLOW), WORKFLOW)
    wf = open(WORKFLOW, encoding="utf-8").read() if os.path.isfile(WORKFLOW) else ""
    wf_lines = wf.splitlines()
    for name, rx in RETIRED.items():
        m = rx.search(wf)
        check("workflow: %s absent" % name, m is None, ascii(m.group(0)) if m else "")
    check("workflow: no bare below-replacement PURSUE trigger",
          re.search(r"below-replacement\s+OR\s+clear value-add upside", wf, re.I) is None)
    for name, marker in WF_SITES.items():
        ln = site_line(wf_lines, marker) or ""
        check("workflow[%s]: exactly one prompt line" % name, bool(ln), marker)
        check("workflow[%s]: tests all-in basis" % name, ALL_IN in ln, ascii(ln[:300]))
        check("workflow[%s]: binds the full vintage-ramp floor clause" % name,
              WF_FLOOR.search(ln) is not None, ascii(ln[:400]))
        check("workflow[%s]: a floor miss is a flag, not a kill" % name,
              "floor miss is a flag, not an automatic kill" in ln, ascii(ln[:300]))
    synth = site_line(wf_lines, WF_SITES["synthesis"]) or ""
    for name, rx in WF_SYNTH_MAPPING.items():
        check("workflow[synthesis]: maps %s" % name, rx.search(synth) is not None, ascii(synth[:600]))

    passed = sum(1 for ok, _ in _results if ok)
    print("\ndeal-recon basis doctrine tests: %d/%d passed" % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
