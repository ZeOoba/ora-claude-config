#!/usr/bin/env python3
"""ORA governor-drift probe (Phase 1.1).

Enforces G5 invariant I3: the acquisition governor is DSCR >= 1.25x and LTV <= 40%
EVERYWHERE -- config, memory, skills. Greps the system for any DSCR threshold != 1.25x
or LTV ceiling != 40% and exits NON-ZERO with the offending file:line, so it can gate
the weekly health report.

Design notes (precision over recall, to avoid false positives):
  * Scoring-rubric lines (e.g. "≥2.5x=10; 2.0-2.49x=8; ...") legitimately list many DSCR
    multiples -- they are EXCLUDED from the equality check, but the 1.75 regression
    sentinel still guards them.
  * The known-wrong historical value 1.75 co-occurring with DSCR/governor is always
    flagged UNLESS the line is an audit note ("corrected ...") that also states 1.25.
  * Exit 0 = clean; exit 1 = drift found; exit 2 = probe error (fail loud, not silent -- I5).

Usage: python governor-drift-probe.py            # scan default roots
       python governor-drift-probe.py --quiet     # only print on drift
"""
import os, re, sys

# Output may echo file content with non-cp1252 chars (≠, ≥, ×) -> force UTF-8 so the
# probe never crashes on its own output when stdout is a Windows cp1252 pipe (I5).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CANON_DSCR = "1.25"
CANON_LTV = "40"

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
MEM = os.path.join(CLAUDE, "projects",
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")

ORA_SKILLS_REPO = os.path.join(HOME, "ora-skills")

# Scan roots: (path, file-extensions). Missing roots are skipped silently (logged once).
def build_targets():
    targets = []
    targets.append((MEM, (".md",)))
    targets.append((os.path.join(CLAUDE, "CLAUDE.md"), None))            # single file
    targets.append((os.path.join(CLAUDE, "agents"), (".md",)))
    targets.append((os.path.join(CLAUDE, "hooks"), (".py", ".json")))
    targets.append((os.path.join(CLAUDE, "maintenance"), (".py", ".json")))
    # Canonical ora-skills repo (source of truth for skill edits, per tech.md) -- NOT the AppData
    # runtime cache (the prior target here, via discover_skills_root(), removed 2026-07-12). The
    # cache is a passive mirror that converges from this repo with propagation lag (repo push ->
    # claude.ai cloud converge -> Cowork runtime resync); scanning the lagging cache instead of the
    # repo was producing false-positive HIGH alarms when a skill was already corrected in the repo
    # but the cache copy hadn't caught up yet (2026-07-12 EOD ledger finding). _archive/_staging
    # hold retired/in-progress content, not live governor declarations -- excluded in iter_files()
    # the same way node_modules/dist/.git already are.
    if os.path.isdir(ORA_SKILLS_REPO):
        targets.append((ORA_SKILLS_REPO, (".md", ".json")))
    brain = os.path.join(HOME, "oxford-command-center")
    for sub in ("src", "server", "scripts", "data"):
        targets.append((os.path.join(brain, sub), (".ts", ".tsx", ".js", ".json", ".md")))
    return targets

def iter_files(root, exts):
    if os.path.isfile(root):
        yield root
        return
    if not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # never descend into dependency / build trees, or retired/in-progress skill content
        dirnames[:] = [d for d in dirnames
                       if d not in ("node_modules", "dist", ".git", "__pycache__", "_archive", "_staging")]
        for fn in filenames:
            if exts is None or fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)

# DSCR threshold near 'dscr'. The trailing x/× is OPTIONAL: a drifted governor may be
# written "DSCR floor 1.10" with no multiplier sign, and the equality check must catch it.
# Guards against over-match: a value immediately followed by '%' is an LTV-style figure,
# not a DSCR multiple -> excluded via lookahead. Still gated to governor-DECLARATION lines
# (is_gov) in scan_line, so prose mentions of a deal's DSCR don't trip it.
# 2026-07-11 precision guards (each unambiguously excludes a NON-threshold; none narrows a real
# drift shape -- REFUTE-verified against Hole 5):
#   * (?<![vV]) version-prefix lookbehind: a digit glued to a 'v'/'V' is a VERSION token ("v3.8"),
#     never a DSCR multiple. NARROWED from the earlier (?<![a-zA-Z]): a blanket letter-lookbehind
#     also silenced a genuine letter-glued drift ("changed to1.10" -- 'o' abuts the digit), which
#     is the catastrophic class. Only 'v'/'V' (the version marker) is excluded now, so "to1.10"
#     still flags while "v3.8" does not.
#   * (?![0-9]) full-number capture: without it, "DSCR, 7.00% fixed" backtracked to the PARTIAL
#     capture "7.0" (leaving "0" to slip past the percent guard) and read a refi RATE as a DSCR
#     multiple. The value must be consumed whole, so a %-suffixed rate can never match.
#   * (?!%) percent guard placed IMMEDIATELY after the number (before any \s*): only a percent
#     ABUTTING the digits ("1.25%") is an LTV-style figure to exclude. The old (?!\s*%) after the
#     optional x also swallowed a space-separated "1.10 %" (a real DSCR multiple with a stray
#     space) -- another Hole-5 false negative. Abutting-only keeps "1.25%" out yet flags "1.10 %".
RE_DSCR_THRESH = re.compile(
    r"dscr[^0-9\n]{0,40}?(?<![vV])([0-9]+\.[0-9]+)(?![0-9])(?!%)\s*[x×]?", re.I)
# Scoring-rubric PAIR: a single "<value>=<points>" or "<band>=<points>" assignment, e.g.
# ">=2.5x=10", "2.0-2.49x=8", "<1.25x=0". We match the WHOLE pair (the DSCR multiple/band
# AND its "=points" tail together) -- deliberately NOT a bare "=N" or a bare band. This is
# what lets us COUNT pairs (see scan_line branch 2): a genuine rubric REPEATS this structure
# (>=2 pairs), while a governor declaration carries at most ONE incidental fragment.
#   * Point-value set kept narrow {0,1,2,3,5,8,10} + (?!\.[0-9]) lookahead: a guardrail must
#     err toward DETECTION, so we only treat a line as a rubric when it looks unmistakably
#     like one -- an exotic single-entry "rubric" flags loudly rather than masking real drift.
#   * Pairing the multiple WITH its "=points" tail (vs. the old span-strip) means a lone
#     governor floor that shares the line with one such pair is never mistaken for a rubric.
RE_RUBRIC_PAIR = re.compile(
    r"[<>]?=?\s*"                              # optional leading comparator (>=, <, <=, ...)
    r"[0-9]+\.[0-9]+\s*[x×]?"                  # a decimal DSCR multiple, optional x/×
    r"(?:\s*-\s*[0-9]+\.[0-9]+\s*[x×]?)?"      # optional band upper bound (2.0-2.49x)
    r"\s*=\s*(?:0|1|2|3|5|8|10)\b(?!\.[0-9])", # = rubric point value (not the head of a decimal)
    re.I)
# LTV ceiling bound to a comparator immediately after "ltv" (high precision).
RE_LTV_CMP = re.compile(r"ltv[^0-9\n]{0,15}?[≤<]=?\s*([0-9]{1,3})\s*%", re.I)
RE_LTV_NUM = re.compile(r"([0-9]{1,3})\s*%")
# LTV value in CLOSE PROXIMITY to the word "ltv" (no comparator) -- e.g. "LTV 65%" / "65% LTV".
# Proximity-bound so unrelated %s on the same line (replacement-discount, yield-on-cost) are NOT
# misread as LTV merely because the line also mentions "ltv" (fixes the deal-recon buy-box false positive).
RE_LTV_NEAR = re.compile(r"ltv[^0-9\n]{0,12}([0-9]{1,3})\s*%|([0-9]{1,3})\s*%[^0-9\n]{0,8}ltv", re.I)
# --- I-2: canonical-decoy detection ----------------------------------------------------------
# A drifted threshold can hide behind a CANONICAL restatement on the same line ("DSCR floor
# raised from 1.25 to 1.40x") because the primary extractors bind to the FIRST value (the
# canonical 1.25) and stop. We add a second pass that finds a threshold value bound to an
# explicit DECLARATION/CHANGE construct ANYWHERE on the line. The binding is deliberately TIGHT
# because the real tree is DENSE with incidental non-canonical numbers on governor/standards
# lines -- cap rates ("7.0"), phase tags ("1.1"), basis discounts ("≥25%"), exit caps ("max 7%"),
# clear heights ("ceiling 32.0 ft"), rents ("floor 5.50 psf"), occupancy/vacancy ("80% → 95%").
# A single false positive flips the probe to exit 1, so two metric-discriminators keep those out:
#   * DSCR secondary matches REQUIRE a trailing x/× -- a DSCR multiple is "1.40x", not "5.50 psf"
#     / "32.0 ft" / "3.5 units". (The PRIMARY dscr-anchored pass keeps x optional -- next to the
#     word "dscr" the context is unambiguous; only these far-from-keyword passes need the x.)
#   * LTV secondary requires an LTV-ADJACENT ceiling/max anchor ("LTV ceiling", "max LTV") -- a
#     bare "ceiling"/"max"/comparator/arrow matches exit-cap, rent-ceiling and occupancy figures,
#     which are also percents. Comparators stay anchored to "ltv" via RE_LTV_CMP.
# Shapes caught:
#   * <change-verb> from <CANONICAL> to <NEW>   -- the classic decoy restates canonical then drifts.
#     Gated on the "from" value being canonical: a non-canonical "from" is itself drift, caught by
#     the primary pass (DSCR) or the ceiling/max anchor scan (LTV). Keeps incidental ranges
#     ("comps moved from 30% to 38%") out. Captures the NEW value.
#   * floor/ceiling/min/max keyword, comparator, arrow (->/→), or a "<verb> to" / "now" / "then"
#     pivot introducing a NEW value -- the natural ways a drift edit is written.
_CHANGE_VERB = (r"raised|increased|reduced|lowered|changed|dropped|cut|moved|revised|updated"
                r"|bumped|hiked|pushed|tightened|relaxed|loosened|adjusted|set")
_PIVOT = r"(?:" + _CHANGE_VERB + r")\s+to|→|->|\bnow\b|\bthen\b"
RE_DSCR_FROMTO = re.compile(
    r"(?:" + _CHANGE_VERB + r")\b[^0-9\n]{0,16}?from\s+" + re.escape(CANON_DSCR)
    + r"\s*[x×]?\s+to\s+([0-9]+\.[0-9]+)\s*[x×]?(?!\s*%)", re.I)
# DSCR DECL: keyword / comparator / pivot bound value -- REQUIRES trailing x/× (metric guard).
# The x separates a DSCR multiple from a throughput/height/rent decimal; relaxing it broadly (even
# when canonical 1.25 co-occurs) re-flags "DSCR floor 1.25x; throughput 2.0 -> 3.5 units". The
# common no-x decoy ("DSCR floor 1.25 -> 1.40") is instead caught by RE_DSCR_PIVOT_DECOY below
# (canonical-LEFT-of-pivot guard). Remaining accepted residual: a no-x drift bound by a comparator/
# verb-to FAR (>40 chars) from "dscr" with NO canonical restatement -- contrived; the 1.75 sentinel
# and x-optional PRIMARY pass cover the realistic cases. Left deliberately.
RE_DSCR_DECL = re.compile(
    r"(?:floor|minimum|min|maximum|max|ceiling|>=|<=|[≥≤]|" + _PIVOT + r")"
    r"\s*(?:[<>]=?|[≥≤])?\s*([0-9]+\.[0-9]+)\s*[x×](?!\s*%)", re.I)
# DSCR DECL, REVERSE WORD ORDER (2026-07-08): the NUMBER-then-keyword form "1.40x floor" /
# "1.40x minimum" -- the mirror image of RE_DSCR_DECL, which only reads keyword-BEFORE-number
# ("floor 1.40x"). A governor restatement written "This 1.40x floor is the acquisition governor"
# carries NO literal "dscr" (so RE_DSCR_THRESH, anchored on the word "dscr", misses it) AND puts the
# keyword AFTER the value (so RE_DSCR_DECL misses it) -- a genuine false-negative discovered in the
# 2026-07-08 CLAUDE.md audit (a line was reworded to dodge it; this closes the root gap). Same metric
# guard as RE_DSCR_DECL: the trailing x/× is REQUIRED and must abut the value -- that is what
# separates a DSCR multiple ("1.40x floor") from a rent/height/throughput decimal that merely
# precedes a keyword ("5.50 psf rent floor", "32.0 ft clear-height ceiling" -- neither has an x
# touching the number). It is added to the branch-2 candidate list, so it flows through the SAME
# suppressors as every other DSCR candidate (canonical-skip, correction-span, portfolio-level,
# post-close-refi, rubric-pair); a portfolio-wide "1.75x floor" or a refi tier is still suppressed.
RE_DSCR_DECL_REV = re.compile(
    r"([0-9]+\.[0-9]+)\s*[x×]\s*(?:floor|ceiling|minimum|min|maximum|max)\b", re.I)
# DSCR DECL, value->DSCR->keyword order (2026-07-12, follow-up 1): "1.10x DSCR floor" / "1.10x DSCR
# minimum" -- a value, then the literal 'dscr', then a floor-word AFTER it. This closes a pre-existing
# false negative that BOTH reverse passes missed: RE_DSCR_DECL_REV requires the floor-word to abut the
# value ("1.10x floor", no 'dscr' between), and RE_DSCR_THRESH anchors on 'dscr' and reads FORWARD (so
# a value BEFORE the word 'dscr' is invisible to it). Same metric guards as the other reverse matcher:
# the trailing x/× is REQUIRED and abuts the value (separates a DSCR multiple from a rent/height
# decimal that merely precedes a keyword), and the (?<![vV]) version-prefix guard applies. Added to the
# branch-2 candidate list, so it flows through EVERY suppressor (canonical-skip, correction-span,
# portfolio, refi member-span, rubric) -- no bypass.
RE_DSCR_KW_AFTER_DSCR = re.compile(
    r"(?<![vV])([0-9]+\.[0-9]+)\s*[x×]\s*dscr\s+(?:floor|minimum|min|maximum|max|ceiling)\b", re.I)
RE_LTV_FROMTO = re.compile(
    r"(?:" + _CHANGE_VERB + r")\b[^0-9\n]{0,16}?from\s+" + re.escape(CANON_LTV)
    + r"\s*%\s+to\s+([0-9]{1,3})\s*%", re.I)
# DSCR pivot decoy (I-3): "<CANONICAL> <arrow|then|now> <NEW>" with NO trailing x -- the canonical
# value sitting immediately LEFT of the pivot is the metric guard that the missing x would
# otherwise provide. "DSCR floor 1.25 -> 1.40" flags; an incidental "throughput 2.0 -> 3.5"
# (left operand 2.0, not canonical) does not. Only DSCR has this pass: 1.25 is DSCR-specific,
# whereas a "40% -> N%" analog is unsafe (40% is a common percent -- occupancy, splits, etc.).
RE_DSCR_PIVOT_DECOY = re.compile(
    re.escape(CANON_DSCR) + r"\s*[x×]?\s*(?:→|->|\bthen\b|\bnow\b)\s*([0-9]+\.[0-9]+)", re.I)
# LTV anchor: an LTV-qualified ceiling/max ("LTV ceiling", "ceiling LTV", "max LTV", "LTV max").
# Branch 3 reads the FIRST percent in a short window after the anchor -- that percent IS the
# declared ceiling. "LTV ceiling now 65%" / "raised from 45% to 65%" flag (first % is the drift),
# while "max 7% exit cap" / "occupancy 80% → 95%" never match (no LTV adjacency / no anchor).
# Taking only the FIRST percent is the FP guard: if the ceiling is canonical 40%, any later
# percent ("max LTV 40% and 25% basis discount", "ceiling 40% with 8% yield") is a DIFFERENT
# metric and is left alone -- this holds even when a connective (not a list delimiter) joins them.
RE_LTV_ANCHOR = re.compile(r"ltv\s*(?:ceiling|maximum|max)|(?:ceiling|maximum|max)\s*ltv", re.I)
# LTV ceiling, REVERSE WORD ORDER (2026-07-08): the NUMBER-then-keyword form "65% ceiling" /
# "65% maximum" on a governor line that carries NO literal "ltv" -- the LTV analog of the reverse
# DSCR gap above. "This 65% ceiling is the acquisition governor" never enters the ltv-gated LTV
# branch (no "ltv" token), so it silently evades. A percent has no intrinsic metric discriminator
# (no x-analog), so precision rests on two things: (a) is_gov line-level gating (used at the call
# site -- the line must already carry a governor keyword), and (b) the keyword set kept to
# {ceiling, maximum} ONLY. "min"/"minimum" are DSCR-floor words; bare "max"/"maximum" abut non-LTV
# percents ("vacancy 15% max", "exit cap 8% max") -- so bare "max" is DELIBERATELY EXCLUDED, and
# "maximum" (spelled in full) is a rare enough non-LTV collocation to accept. "ceiling"/"maximum"
# abutting a percent read unambiguously as an LTV ceiling on a governor line.
RE_LTV_CEIL_REV = re.compile(r"([0-9]{1,3})\s*%\s*(?:ceiling|maximum)\b", re.I)
# LTV audit-note suppressor (I-4): a PAST correction landing on canonical 40%. Kept TIGHT --
# requires the explicit "corrected ... from <N>% to/→ 40%" structure. Its MATCH SPAN is used to
# SPAN-SCOPE the suppression (branch 3): only a percent sitting INSIDE the span (the corrected-away
# old value) is skipped, so a live "65% ceiling" sharing a line with an unrelated correction still
# flags. (Suppression = a false negative, so a guardrail scopes it to the quoted old value, not the
# whole line. The pre-existing DSCR note stays loose/whole-branch; this new one is stricter.)
RE_LTV_CORRECTION = re.compile(
    r"corrected[^0-9\n]{0,20}from\s+[0-9]{1,3}\s*%\s+(?:to|→|->|=>)\s+" + re.escape(CANON_LTV)
    + r"\s*%", re.I)
# DSCR analog (M-2 symmetry): "corrected ... from <X> to/→ 1.25" -- same tight from->to-canonical
# structure, span-scoped the same way so only the corrected-away DSCR value is skipped, not the
# whole DSCR branch. Replaces the prior loose whole-line is_dscr_note ("corrected" + "1.25").
RE_DSCR_CORRECTION = re.compile(
    r"corrected[^0-9\n]{0,20}from\s+[0-9]+\.[0-9]+\s*[x×]?\s*(?:\bto\b|→|->|=>)\s*"
    + re.escape(CANON_DSCR) + r"(?![0-9])", re.I)  # (?![0-9]) not \b: a trailing x ("→ 1.25x") must still suppress
# --- CODE-AWARE governor check (2026-06-14) -------------------------------------------------
# Prose proximity is WRONG for code: a camelCase identifier (`dscrFloor`) embeds the keyword,
# and the real governor is the ENFORCEMENT COMPARISON, not an error-string. `.ts/.tsx/.js` files
# are routed to scan_code() (NOT scan_line) -- so the identifier-substring false-positive class
# (e.g. the `> 3` sanity ceiling reading as a 3.0 DSCR threshold) cannot occur, and a drifted
# CONSTANT (`dscrFloor < 1.10`) is caught directly instead of only-if-the-message-also-changed.
# Keyed on identifier + the floor/ceiling-defining operator. Capital config is unit-interval:
# DSCR floor literal == 1.25, LTV ceiling literal == 0.40 (NOT 40). The legit sanity ceiling
# `dscrFloor > 3` is ignored; an inverted floor `dscrFloor > <=2>` (the governor range, not a
# sane ceiling) IS flagged.
# The acquisition governor lives in exactly ONE code file (CLAUDE.md §4). scan_code is routed ONLY
# to that file by main(): the identifiers dscrFloor/ltvCeiling are OVERLOADED -- conditions.ts reuses
# them for operational ALERT thresholds at different LEGIT values (e.g. dscrFloor: 1.1, ltvCeiling:
# 0.65), so a global check would false-positive. Number literal allows leading-dot (.40) -- a valid
# TS form. Capital config is unit-interval: DSCR floor == 1.25, LTV ceiling == 0.40 (NOT 40).
GOVERNOR_CODE_FILES = {"capital-config.ts"}
_NUM = r"(?:[0-9]*\.[0-9]+|[0-9]+)"
# Enforcement-GUARD forms: identifier <op> literal  (`if (next.dscrFloor < 1.25)`).
RE_CODE_DSCR = re.compile(r"\bdscrFloor\s*(<=?|>=?)\s*(" + _NUM + r")")
RE_CODE_LTV = re.compile(r"\bltvCeiling\s*(<=?|>=?)\s*(" + _NUM + r")")
# SEED-literal forms: `dscrFloor: 1.25` (the ratified CAPITAL_CONFIG default -- the LIVE governor
# value merged into every write). The type annotation `dscrFloor: number` and an expression RHS
# (`?? current.x`) do NOT match -- _NUM requires a digit/dot literal.
RE_CODE_DSCR_ASSIGN = re.compile(r"\bdscrFloor\s*:\s*(" + _NUM + r")")
RE_CODE_LTV_ASSIGN = re.compile(r"\bltvCeiling\s*:\s*(" + _NUM + r")")
# PRESENCE (deletion guard, used in main): any NUMERIC governor declaration (seed OR guard). The
# bare interface type `dscrFloor: number` must NOT satisfy it, else deleting the value while keeping
# the type would mask the deletion -- so a numeric literal is required.
RE_CODE_DSCR_ANY = re.compile(r"\bdscrFloor\s*(?::|<=?|>=?)\s*" + _NUM)
RE_CODE_LTV_ANY = re.compile(r"\bltvCeiling\s*(?::|<=?|>=?)\s*" + _NUM)
CANON_DSCR_NUM = 1.25
CANON_LTV_NUM = 0.40

def scan_code(text):
    """Validate the acquisition-governor ENFORCEMENT CONSTANTS in the GOVERNOR SOURCE FILE
    (capital-config.ts) -- not prose. main() routes ONLY that file here (see GOVERNOR_CODE_FILES:
    the identifiers are overloaded, so a global check would false-positive on conditions.ts alert
    thresholds). Numeric equality: 0.4 == 0.40, 1.250 == 1.25, leading-dot .40 == 0.40.

    Covers: the ratified SEED literal (`dscrFloor: 1.25`, `ltvCeiling: 0.40`) AND the write-time
    GUARD (`dscrFloor < 1.25`, `ltvCeiling > 0.40`); a changed literal, an operator flip (<=/>=), an
    inverted guard (`dscrFloor > 1.25`). The `> 3` sanity ceiling is exempt. Whole-file DELETION of a
    governor declaration is caught separately in main() (presence guard).

    Adversarial residuals (single-line regex, stdlib-only -- a full TS AST is out of scope; low risk
    given the scope is ONE small controlled file using identifier-first literal forms): a renamed
    identifier; a constant via a variable (`< MIN`) or scientific notation (`1.25e-1` / `4e-1`); a
    Yoda comparison (`1.10 > dscrFloor`); a declaration split across lines or broken by a comment."""
    out = []
    for i, raw in enumerate(text.splitlines(), 1):
        # SEED literals -- the ratified default value; must equal canonical.
        for m in RE_CODE_DSCR_ASSIGN.finditer(raw):
            if float(m.group(1)) != CANON_DSCR_NUM:
                out.append((i, "DSCR floor seed constant %s != canonical %s" % (m.group(1), CANON_DSCR),
                            raw.strip()[:120]))
        for m in RE_CODE_LTV_ASSIGN.finditer(raw):
            if float(m.group(1)) != CANON_LTV_NUM:
                out.append((i, "LTV ceiling seed constant %s != canonical %s" % (m.group(1), CANON_LTV_NUM),
                            raw.strip()[:120]))
        # ENFORCEMENT guards.
        for m in RE_CODE_DSCR.finditer(raw):
            op, num = m.group(1), float(m.group(2))
            if op in ("<", "<="):  # the FLOOR guard: refuse when floor is below the canonical min
                if op == "<=":
                    out.append((i, "DSCR floor guard uses '<=' (direction drift; expected '< %s')"
                                % CANON_DSCR, raw.strip()[:120]))
                elif num != CANON_DSCR_NUM:
                    out.append((i, "DSCR floor constant %s != canonical %s" % (m.group(2), CANON_DSCR),
                                raw.strip()[:120]))
            elif num <= 2:  # '>'/'>=' in the governor range = inverted/relaxed floor; '> 3' sanity exempt
                out.append((i, "DSCR floor compared with '%s %s' -- inverted/relaxed floor"
                            % (op, m.group(2)), raw.strip()[:120]))
        for m in RE_CODE_LTV.finditer(raw):
            op, num = m.group(1), float(m.group(2))
            if op in (">", ">="):  # the CEILING guard: refuse when ceiling is above the canonical max
                if op == ">=":
                    out.append((i, "LTV ceiling guard uses '>=' (direction drift; expected '> %s')"
                                % CANON_LTV_NUM, raw.strip()[:120]))
                elif num != CANON_LTV_NUM:
                    out.append((i, "LTV ceiling constant %s != canonical %s" % (m.group(2), CANON_LTV_NUM),
                                raw.strip()[:120]))
            elif num >= 0.2:  # '<'/'<=' in range = inverted/relaxed ceiling
                out.append((i, "LTV ceiling compared with '%s %s' -- inverted/relaxed ceiling"
                            % (op, m.group(2)), raw.strip()[:120]))
    return out
# --------------------------------------------------------------------------------------------
# Governor-declaration signals. The equality checks fire ONLY on lines that actually
# DECLARE the governor -- not on prose that merely cites a deal's DSCR or current LTV.
GOV_KEYWORDS = ("governor", "hard filter", "hard screen", "hard acquisition",
                "disqualif", "non-negotiable", "dscr floor", "ltv ceiling",
                "self-imposed", "minimum dscr", "min dscr", "acquisition screen",
                # N6 (2026-07-12): 'hard cap'/'hard ceiling' are veto tokens (ACQ_DECL_NEARBY), so
                # they must ALSO gate is_gov -- otherwise a line whose ONLY governor signal is one of
                # them is never scanned and a drift declared solely via it goes silent. The skill uses
                # "aggregate/per-property/refi-sizing ceiling", never "hard cap"/"hard ceiling".
                "hard cap", "hard ceiling")

# --- Portfolio-level DSCR qualifier (2026-07-08) --------------------------------------------
# Gabriel-ratified doctrine (2026-07-08): "DSCR of 1.25 for each property and 1.75 for the entire
# portfolio." So DSCR 1.25x is the PER-DEAL / per-property acquisition governor (canonical, I3),
# while 1.75x is a SEPARATE, legitimate PORTFOLIO-WIDE blended target -- a distinct aggregate
# metric, NOT the per-deal floor. Before this, the 1.75 regression sentinel (scan_line branch 1)
# and the DSCR equality check (branch 2) flagged ANY 1.75 near dscr/governor, which conflated the
# two figures and would false-positive on a legitimately-labelled portfolio-level 1.75.
#
# _portfolio_qualified() SUPPRESSES the flag ONLY when the line unambiguously frames the value as
# portfolio-level. Same detection-over-silence bias as the rest of the module -- suppression is a
# false negative, so it is kept TIGHT with two independent guards:
#   * VETO first: any per-deal / per-property marker on the line ("per-deal", "per property",
#     "hard acquisition governor") means the line claims to be the DEAL-level governor -- if that
#     shows 1.75 it is a REAL per-deal drift and must STILL flag, so we never suppress it.
#   * Then REQUIRE an explicit portfolio qualifier: a "portfolio dscr"/"portfolio-wide"/
#     "portfolio-level"/"blended portfolio" token, OR the bare word "portfolio" within 30 chars of
#     the offending value. A stray "portfolio" far from the number does NOT qualify (so it cannot
#     be used to mask a governor drift elsewhere on a long line).
PORTFOLIO_QUALIFIERS = ("portfolio dscr", "portfolio-wide", "portfolio wide",
                        "portfolio-level", "portfolio level", "blended portfolio")
PERDEAL_MARKERS = ("per-deal", "per deal", "per-property", "per property",
                   "hard acquisition governor")

def _portfolio_qualified(low, val_start):
    """True when the DSCR value at index `val_start` (already lower-cased `low`) is unambiguously a
    PORTFOLIO-LEVEL figure and the 1.75/equality flag should be suppressed. A per-deal marker
    anywhere on the line vetoes suppression (real per-deal drift must still flag)."""
    if any(m in low for m in PERDEAL_MARKERS):
        return False
    if any(q in low for q in PORTFOLIO_QUALIFIERS):
        return True
    return "portfolio" in low[max(0, val_start - 30):val_start + 30]

# --- Post-close refinancing-scenario qualifier (2026-07-08) ----------------------------------
# Gabriel-ratified doctrine: DSCR 1.25x / LTV 40% is the ACQUISITION-time governor (how ORA buys).
# The acquisition-underwriting skill ALSO documents a distinct POST-CLOSE REFINANCING scenario
# ("all-cash bid + refi post-close") whose debt-SIZING assumptions legitimately cite different
# numbers -- a refi LTV taken against STABILIZED EXIT value (65%) and DSCR-based rate-pricing tiers
# ("-25 bps for stabilized multi-tenant >=1.40x DSCR"). Those are refinance-market inputs, NOT the
# acquisition governor; the SAME line states the governor CORRECTLY ("1.25x DSCR (the governor --
# never exceed)"). Because the bare word "governor" on that line trips is_gov, the DSCR-equality
# pass (branch 2) and the LTV proximity pass (branch 3) flag the refi figures as drift -- a false
# positive of exactly the class this module's docstring warns against.
#
# _refi_qualified() SUPPRESSES a DSCR/LTV flag ONLY when the offending value sits in an unambiguous
# post-close-refi debt-sizing context. Detection-over-silence bias, so kept TIGHT with three guards:
#   * VETO on any ACQUISITION-governor marker on the line -- it would make the value the acquisition
#     governor itself, so a drift there must STILL flag.
#   * REQUIRE the line to be an explicit refi debt-sizing line: a refi/refinance token AND a
#     post-close / refi-debt / refi-sized frame (a stray "refi" alone does not qualify).
#   * VETO if the value is itself declared AS "the governor" -- the literal token "governor" within
#     25 chars either side of the value -- so drifting the on-line governor CITATION (e.g. the 1.25x
#     -> 1.40x in "(the governor -- never exceed)") is NOT masked. The genuine refi figures sit far
#     from any "governor" token, so they are still suppressed.
REFI_TOKENS = ("refi", "refinance")
REFI_FRAME = ("post-close", "post close", "refi debt", "refi sized", "refi assumption",
              "refinance debt", "refinancing")
# markers that would make the flagged value the ACQUISITION governor (veto suppression):
ACQ_GOV_MARKERS = ("acquisition governor", "acquisition screen", "hard filter", "hard screen",
                   "hard acquisition", "ltv ceiling", "dscr floor", "min dscr", "minimum dscr",
                   "buy box", "buy-box", "non-negotiable") + PERDEAL_MARKERS

def _refi_qualified(low, val_start):
    """True when the DSCR/LTV value at index `val_start` (in already-lower-cased `low`) is
    unambiguously a POST-CLOSE REFI debt-sizing figure and the drift flag should be suppressed.
    TIGHT by design (suppression is a false negative): an acquisition-governor marker anywhere on
    the line, or the value being declared AS "the governor" (token within 25 chars), both veto
    suppression so a real acquisition-governor drift still flags."""
    if any(m in low for m in ACQ_GOV_MARKERS):
        return False
    if not (any(t in low for t in REFI_TOKENS) and any(f in low for f in REFI_FRAME)):
        return False
    # "governor" token close to the value = the value is declared AS the governor (a drifted
    # citation) -> do NOT suppress. The after-reach (40) spans a "Nx DSCR** (the governor" markdown
    # declaration (~26 chars) while staying well short of the genuine refi figures, whose nearest
    # "governor" token sits 60+ chars away (the refi-sizing "65% LTV ... and 1.25x DSCR (the
    # governor")) and which therefore stay suppressed.
    if "governor" in low[max(0, val_start - 25):val_start + 40]:
        return False
    return True

# --- Refi-sizing CONSTRUCT member-value spans (2026-07-11; redesigned after adversarial review) --
# _refi_qualified() is LINE-scoped and its ACQ_GOV_MARKERS veto misfires on the v3.8-ratified skill
# text: post-2026-07-11 doctrine, "per-property governor: LESSER of 65% LTV and 1.25x DSCR"
# legitimately NAMES the refi-sizing rule with per-deal/per-property words, and the same dense lines
# also carry "dscr floor" (correctly, for the canonical 1.25x floor) -- so the line-level veto
# swallows the suppression and the refi figures false-positive.
#
# An earlier fix suppressed the WHOLE construct span; adversarial review proved that masks a real
# drift hidden INSIDE a construct's gap (the canonical 1.25x member still terminates the match while
# a drifted floor sits between). The catastrophic class -- a false NEGATIVE -- so this version
# suppresses ONLY the construct's OWN MEMBER VALUES (captured as regex groups: the N% LTV member,
# the canonical 1.25 DSCR member, the bps-tier DSCR band). Any OTHER value on the line -- including a
# drift in the gap -- stays fully visible to the normal passes.
# Two further hardenings from the review:
#   * DECIMAL/PERCENT-FREE gaps ([^\n%0-9]): a construct can never LEAPFROG a real figure to reach
#     its terminator, so injecting "DSCR floor 1.10 / 1.25x DSCR" into a LESSER-of simply breaks the
#     match -> the 65% and the 1.10 both stay visible.
#   * The bps RATE-PRICING TIER is additionally gated on a refi TOKEN being present on the line
#     (REFI_TOKENS): a "-25 bps ... >=1.10x DSCR" governor-change note with no refi context is NOT a
#     refi rate tier and its DSCR value stays visible.
# Veto policy (which members honor _governor_declared_nearby):
#   * NO-VETO member -- the canonical-anchored LESSER-of N% only. It is unambiguously the refi-sizing
#     ceiling AND, in the real skill, legitimately sits a few chars from the word "governor"
#     ("per-property governor: LESSER of 65%"). Group-scoping + decimal-free gaps already make it safe
#     (a drift can't hide as the ceiling member or in the gap), so a nearby-governor veto would only
#     re-introduce the 10 false positives.
#   * VETO members -- "refi(s) to N% LTV" (follow-up 2), "N% LTV refi-sizing figure", "1.25x DSCR at
#     N% LTV" (PAIRED), and the bps DSCR band. A nearby singular 'governor' or acquisition-declaration
#     token (incl. "hard ceiling"/"hard cap") means the value is being declared AS the governor, so it
#     must flag ("65% LTV refi-sizing figure is the governor now", "refi to 65% LTV as the hard
#     ceiling"). The real skill's "refis running to 65% LTV" has its 'governor' >VETO_BEFORE away and
#     no ceiling declaration, so it stays suppressed. The task-acknowledged residual: a drift phrased
#     as the canonical LESSER-of construct is masked -- but the anchor/comparator/FROMTO/reverse LTV
#     passes (never suppressed) catch every explicitly-declared "LTV ceiling 65%" / "65% ceiling" form.
#     The real skill's occurrences of these have their nearest 'governor' either >40 chars away,
#     PLURAL ("two distinct governors: 65% LTV is the ...refi-sizing ceiling"), or inside the
#     canonical phrase "1.25x DSCR governor" -- all exempt, so they stay suppressed. (Full-file test
#     enforces that these margins hold if the skill is reworded.)
# Construct GAP fragment: any non-percent, non-digit char OR the literal canonical DSCR ("1.25").
# Allowing the canonical figure (benign) keeps a legit refi-sizing phrase intact even when it reads
# "65% LTV / 1.25x DSCR refi-sizing convention" (SKILL.md:112) -- the 1.25 sits in the gap. Any
# OTHER number (a DRIFTED floor like 1.10) is NOT the canonical literal, so it still BREAKS the gap
# and the construct fails to match -> the drift stays fully visible (review Holes 1-3).
_GAP = r"(?:[^\n%0-9]|" + re.escape(CANON_DSCR) + r")"
RE_REFI_LESSER_OF_PAIR = re.compile(        # capture: (1) N% LTV member, (2) canonical DSCR member
    r"lesser[\s\-]*of\b" + _GAP + r"{0,15}?([0-9]{1,3})\s*%[\s\-*]*ltv" + _GAP + r"{0,60}?"
    + r"(" + re.escape(CANON_DSCR) + r")\s*[x×][\s\-*]*dscr", re.I)
RE_REFI_SIZING_NAMED = re.compile(          # "<N>% LTV ... refi-sizing/refi-sized"; capture (1) N%
    r"([0-9]{1,3})\s*%[\s\-*]*ltv\b" + _GAP + r"{0,30}?refi[\s\-]?siz", re.I)
RE_REFI_TO_LTV = re.compile(                # "refi(s/nanced) ... to <N>% LTV"; capture (1) N%
    r"refi\w*\b" + _GAP + r"{0,20}?to\s+([0-9]{1,3})\s*%[\s\-*]*ltv", re.I)
RE_CANON_DSCR_PAIRED_LTV = re.compile(      # "1.25x DSCR <at/,> <N>% LTV"; capture (1) canon, (2) N%
    r"(" + re.escape(CANON_DSCR) + r")\s*[x×][\s\-*]*dscr\b" + _GAP + r"{0,20}?([0-9]{1,3})\s*%[\s\-*]*ltv",
    re.I)
RE_BPS_DSCR_TIER = re.compile(              # "+/-N bps ... <X.XX>x DSCR" rate tier; capture (1) band
    r"[+\-−±]\s*[0-9]+\s*bps\b" + _GAP + r"{0,50}?([0-9]+\.[0-9]+)\s*[x×][\s\-*]*dscr", re.I)
RE_GOV_TOKEN = re.compile(r"governors?\b")
RE_CANON_DSCR_GOV_PHRASE = re.compile(
    re.escape(CANON_DSCR) + r"\s*[x×][\s\-*]*dscr\s+governor\b", re.I)

# --- RATIFIED DUAL-GOVERNOR PAIRING (2026-07-16) ---------------------------------------------
# Gabriel-ratified doctrine (2026-07-11; recorded at acquisition-underwriting/SKILL.md:221,
# restated :343). ORA runs TWO LTV governors at TWO LEVELS:
#   * per-property refi-sizing ceiling = LESSER of 65% LTV and 1.25x DSCR
#   * portfolio-aggregate ceiling      = 40% LTV  (Hard Invariant 4 -- CANON_LTV, unchanged)
# They are not in tension: one property can refi to 65% while the portfolio stays under 40%. This
# probe tracks the AGGREGATE governor, so a correctly-stated per-property member is not a drift
# candidate. (LTV analog of the DSCR 1.25x-per-deal / 1.75x-portfolio split in _portfolio_qualified.)
#
# Why this is needed on top of the 2026-07-11 refi machinery: those suppressors recognize the 65%
# ONLY inside its refi-sizing SYNTACTIC forms ("LESSER of 65% LTV and 1.25x DSCR", "refi to 65%
# LTV", "65% LTV refi-sizing"). SKILL.md v4.0 (2026-07-16) states the SAME ratified governor in a
# new bare shorthand -- "governor constants (DSCR 1.25x / per-property LTV 65% /
# portfolio-aggregate LTV 40%)" -- matching no construct, so the weakest bare-proximity pass read
# it as drift. That is why the probe (and the repo gate's full-file test) went red on 2026-07-16.
#
# TWO independent conditions are BOTH required to suppress the per-property member. Either alone
# leaves a hole, and each closes the other's:
#   * COMPANION-ANCHORED: the same line's portfolio-aggregate companion must equal canonical 40.
#     A drifted companion suppresses nothing -- the aggregate figure AND the per-property member
#     alongside it both stay visible.
#   * VALUE-LOCKED to the ratified 65: without this, "per-property LTV 80% / portfolio-aggregate
#     LTV 40%" would ride the canonical companion and silence a REAL per-property drift.
# This also refutes the shape the setup-audit note (C4) sketched -- a blanket "per-property veto
# span". Instrumentation showed "Per-property LTV 80% is the governor now" flags ONLY via the
# bare-proximity pass, so a blanket span would silence exactly that drift: the catastrophic
# false-negative class. C4's prescription should not be implemented as written.
#
# Scope guards, consistent with the rest of the module:
#   * DECIMAL/PERCENT-FREE gaps ([^\n%0-9], canonical 1.25 permitted) -- the construct cannot
#     LEAPFROG an intervening figure to reach its companion, so injecting a drift between the two
#     members simply breaks the match and leaves everything visible.
#   * GROUP-SCOPED: only the per-property member's own digits are suppressed (span(1)); the
#     aggregate member (span(2)) is never suppressed and stays fully checked by the normal passes.
#   * WEAKEST-PASS-ONLY at the call site: comparator, LTV-adjacent ceiling/max anchor,
#     reverse-order and FROM-TO passes stay fully armed, so a bare "per-property LTV ceiling 65%"
#     (no companion; 65 declared AS an acquisition ceiling) still flags -- pinned by
#     test_perdeal_perproperty_drift_still_flags_unit.
CANON_LTV_PERPROPERTY = "65"
RE_PERPROP_PORTFOLIO_PAIR = re.compile(
    r"per[\s\-]?propert(?:y|ies)\b(?:[^\n%0-9]){0,10}?ltv\b(?:[^\n%0-9]){0,6}?([0-9]{1,3})\s*%"
    + r"(?:[^\n%0-9]|" + re.escape(CANON_DSCR) + r"){0,40}?portfolio[\s\-]?aggregate\b"
    + r"(?:[^\n%0-9]){0,10}?ltv\b(?:[^\n%0-9]){0,6}?([0-9]{1,3})\s*%",
    re.I)

def _perprop_portfolio_paired_veto_spans(low):
    """Digit-group spans of per-property LTV members ELIGIBLE for pairing suppression: the member
    is the ratified 65 AND the same line's portfolio-aggregate companion is the canonical 40.
    VETO tier (2026-07-16, closes REFUTE Finding 2): a nearby acquisition-ceiling/governor
    declaration on the per-property member means the line is MISLABELING 65 as the acquisition
    ceiling -- a framing error, not numeric drift, but it must still surface. Mirrors the veto
    policy every other named refi-sizing member already uses (_governor_declared_nearby). Returns
    the per-property member span only -- never the companion's, which stays fully checked."""
    spans = []
    for mm in RE_PERPROP_PORTFOLIO_PAIR.finditer(low):
        if mm.group(1) == CANON_LTV_PERPROPERTY and mm.group(2) == CANON_LTV:
            spans.append(mm.span(1))
    return spans

def _refi_member_value_spans(low):
    """Return (ltv_noveto, ltv_veto, dscr_veto): the exact digit-group spans of refi-sizing
    construct MEMBER VALUES -- never whole-construct spans. Only these specific values are
    refi-market inputs to (conditionally) suppress; any other value on the line stays visible."""
    ltv_noveto, ltv_veto, dscr_veto = [], [], []
    for mm in RE_REFI_LESSER_OF_PAIR.finditer(low):
        ltv_noveto.append(mm.span(1))       # canonical-anchored refi ceiling -> no veto
        # group(2) is the canonical 1.25 DSCR member; the DSCR loop skips canonical anyway.
    for mm in RE_REFI_TO_LTV.finditer(low):
        ltv_veto.append(mm.span(1))         # "refi(s) to N% LTV" -> VETO tier (follow-up 2): a real
        # drift "refi to 65% LTV as the hard ceiling" flags; the skill's plain "refis running to 65%
        # LTV" (portfolio governor >VETO_BEFORE away, no ceiling/gov declaration) stays suppressed.
    for mm in RE_REFI_SIZING_NAMED.finditer(low):
        ltv_veto.append(mm.span(1))
    for mm in RE_CANON_DSCR_PAIRED_LTV.finditer(low):
        ltv_veto.append(mm.span(2))         # the N% LTV member of the pairing -> veto
    if any(t in low for t in REFI_TOKENS):  # bps tier is a refi input only in a refi context
        for mm in RE_BPS_DSCR_TIER.finditer(low):
            dscr_veto.append(mm.span(1))
    return ltv_noveto, ltv_veto, dscr_veto

def _in_spans(vs, ve, spans):
    """True when the value span [vs, ve) is fully contained in one of `spans`."""
    return any(s <= vs and ve <= e for (s, e) in spans)

# Tokens that, near a VETO-tier member, mean the value is being declared AS the (acquisition)
# governor -- so suppression is vetoed and the value flags. Bare 'floor'/'dscr floor'/'minimum dscr'
# added per review: a value declared as a floor next to a refi phrasing is a governor declaration.
# None of these sit within +-40 of any real-skill VETO-tier member (full-file test enforces this).
ACQ_DECL_NEARBY = ("acquisition", "buy box", "buy-box", "hard filter", "hard screen",
                   "hard ceiling", "hard cap", "floor", "dscr floor", "minimum dscr", "min dscr")

def _spans_overlap(a0, a1, b0, b1):
    return a0 < b1 and a1 > b0

# Direction-aware veto reach. A declaration token is far more meaningful AFTER the value ("65% ...
# is the governor" / "65% ... acquisition ceiling") than BEFORE it. The before-reach is deliberately
# SHORT so a governor named earlier in the sentence as a DIFFERENT subject does NOT veto -- the real
# skill writes "This [portfolio] governor is distinct from the per-property 65% ... refi-sizing
# convention" (governor ~35 chars before the member) and "portfolio governor even with individual
# refis running to 65% LTV". A tight before-reach keeps those suppressed while still catching a
# value declared right after a lead-in ("the acquisition LTV governor is 65%", token ~12 before).
# After-reach 40 catches "65% ... is the governor now" (~34 after). Widened 2026-07-12 (round-2
# review W1: a real drift "acquisition governor was hereby raised to 55% LTV refi-sizing parity"
# parks its declaring 'governor' ~22 chars before the value, in the old dead-zone). The tightest
# real-skill BEFORE gap for a veto-tier member is 32 (:196 "40% LTV governor. Gabriel confirmed
# 2026-07-11: 65% ..." -- a benign contrast mention), next is 39 (:300); 28 stays clear of both
# while catching the ~22-char declaration. Margins enforced by the full-file test.
VETO_BEFORE = 28
VETO_AFTER = 40

def _governor_declared_nearby(low, vs, ve=None):
    """True when a bare singular 'governor' token -- or an acquisition-declaration token
    (ACQ_DECL_NEARBY) -- OVERLAPS the DIRECTION-AWARE interval [vs-VETO_BEFORE, ve+VETO_AFTER]
    around the value: the value may be declared AS the governor, so a VETO-tier refi member must
    NOT be suppressed. Whole-line search + overlap test (review Hole 4: the prior finditer
    end-bound / substring slice silently shrank the effective reach and biased toward silence).
    Exemptions (both err toward detection elsewhere): PLURAL 'governors' (names multiple governors),
    and a 'governor' inside the canonical phrase '1.25x DSCR governor' (binds to the canonical DSCR
    on its left, e.g. 'the 1.25x DSCR governor at 65% LTV')."""
    if ve is None:
        ve = vs
    lo, hi = vs - VETO_BEFORE, ve + VETO_AFTER
    # acquisition-declaration substrings: any occurrence overlapping the interval vetoes.
    for t in ACQ_DECL_NEARBY:
        start = 0
        while True:
            k = low.find(t, start)
            if k == -1:
                break
            if _spans_overlap(k, k + len(t), lo, hi):
                return True
            start = k + 1
    phrase_spans = [pm.span() for pm in RE_CANON_DSCR_GOV_PHRASE.finditer(low)]
    for gm in RE_GOV_TOKEN.finditer(low):
        if gm.group(0).endswith("s"):        # plural 'governors' -> exempt
            continue
        gs, ge = gm.span()
        if not _spans_overlap(gs, ge, lo, hi):
            continue
        if any(s <= gs and ge <= e for (s, e) in phrase_spans):  # canonical '1.25x DSCR governor'
            continue
        return True
    return False

def _refi_construct_suppressed(low, vs, ve, uncond_spans, guarded_spans):
    """True when the value span [vs, ve) sits INSIDE a refi-sizing construct span and (for the
    guarded tier) is not declared AS the governor nearby. Span containment only -- a value
    outside every construct is never suppressed here."""
    if any(s <= vs and ve <= e for (s, e) in uncond_spans):
        return True
    if any(s <= vs and ve <= e for (s, e) in guarded_spans):
        return not _governor_declared_nearby(low, vs)
    return False

def scan_line(raw):
    """Return list of (reason) drift findings for one line."""
    out = []
    low = raw.lower()
    # Audit-note suppressors are METRIC-SPECIFIC and SPAN-SCOPED (I-4 + M-2): a "corrected ... from
    # <X> to/→ canonical" note suppresses ONLY the corrected-away old value (the span), never the
    # whole branch -- so a live drift sharing the line still flags. DSCR and LTV are independent.
    dscr_corr_spans = [mm.span() for mm in RE_DSCR_CORRECTION.finditer(low)]
    ltv_corr_spans = [mm.span() for mm in RE_LTV_CORRECTION.finditer(low)]
    is_gov = any(k in low for k in GOV_KEYWORDS)
    # refi-sizing construct MEMBER-VALUE spans (2026-07-11): member-scoped suppression for the
    # DSCR-candidate loop and the LTV proximity fallback ONLY -- the comparator (RE_LTV_CMP), anchor
    # (RE_LTV_ANCHOR), FROMTO and reverse-order passes stay fully armed as the backstop for any
    # explicitly-declared ceiling/floor, and the 1.75 sentinel (branch 1) is untouched. Only the
    # construct's own member digits are suppressed -- a drift elsewhere on the line stays visible.
    refi_ltv_noveto, refi_ltv_veto, refi_dscr_veto = (
        _refi_member_value_spans(low) if is_gov else ([], [], []))
    # Ratified dual-governor pairing (2026-07-16): per-property member spans that are BOTH the
    # ratified 65 AND paired with a canonical-40 aggregate companion. VETO tier: consumed via
    # refi_ltv_veto (not refi_ltv_noveto) so a nearby acquisition-ceiling/governor declaration on
    # the member still flags it (mislabeled framing, not numeric drift). Consumed ONLY by the
    # bare-proximity LTV fallback below -- every explicit-declaration pass stays armed.
    perprop_paired_veto = _perprop_portfolio_paired_veto_spans(low) if is_gov else []
    refi_ltv_veto = refi_ltv_veto + perprop_paired_veto

    # 1) Regression sentinel: 1.75 near DSCR/governor. Fires only for a 1.75 that is NEITHER (a) the
    #    corrected-away value of a "corrected from 1.75 → 1.25" note NOR (b) an explicit PORTFOLIO-LEVEL
    #    DSCR figure (1.75x is the ratified blended portfolio-wide target -- a distinct metric from the
    #    1.25x per-deal governor). _portfolio_qualified() vetoes suppression on any per-deal marker, so
    #    a per-deal governor that has drifted to 1.75 STILL flags. Scanning continues past a suppressed
    #    1.75 so a second, unqualified 1.75 on the same line is not missed.
    if "dscr" in low or "governor" in low:
        idx = low.find("1.75")
        while idx != -1:
            safe = (any(s <= idx < e for (s, e) in dscr_corr_spans)
                    or _portfolio_qualified(low, idx))
            if not safe:
                out.append("DSCR governor appears as 1.75 (canonical is %sx)" % CANON_DSCR)
                break
            idx = low.find("1.75", idx + 1)

    # 2) DSCR threshold equality -- only on governor-declaration lines (skip notes & rubrics).
    #    Rubric discrimination (I-1): a SCORING RUBRIC repeats value=points / band=points pairs
    #    (">=2.5x=10; 2.0-2.49x=8; ..."). A governor DECLARATION carries at most ONE incidental
    #    such fragment (a "=0 if below" consequence clause, a "=5 points" aside, a "was 1.0-1.5"
    #    band note). Two independent guards, BOTH required to suppress a value:
    #      (a) the line is a genuine rubric -- >=2 rubric PAIRS present (a single fragment is
    #          incidental, not structure: the old "skip on any =N/band" gate swallowed real
    #          drift), AND
    #      (b) the OFFENDING value itself sits INSIDE one of those pairs (it is a scored
    #          multiple, e.g. the "2.5" of "2.5x=10") -- a declared floor written OUTSIDE every
    #          pair (e.g. "minimum DSCR 1.40x" with a scoring band ref appended) is NOT a scored
    #          multiple and must still flag, so a rubric tail can't be used to mask a real floor.
    #    Trade-off (guardrail bias = detection over silence): both tests are conservative, so an
    #    exotic single-entry / out-of-set-weight rubric flags LOUDLY rather than a drifted
    #    governor escaping SILENTLY -- false positives are visible, false negatives are not.
    #    I-2 decoy: the primary extractor binds to the FIRST decimal after "dscr", so a canonical
    #    restatement ("raised from 1.25 to 1.40x") hid the real value. We now also scan FROMTO /
    #    DECL (declaration/change-bound values anywhere on the line) -- see those regexes for the
    #    tight-binding rationale that keeps the real tree's stray figures invisible.
    if is_gov:
        pair_spans = [mm.span() for mm in RE_RUBRIC_PAIR.finditer(low)]
        is_rubric = len(pair_spans) >= 2
        seen = set()
        kw_after_spans = [mm.span(1) for mm in RE_DSCR_KW_AFTER_DSCR.finditer(low)]
        cands = (list(RE_DSCR_THRESH.finditer(low)) + list(RE_DSCR_FROMTO.finditer(low))
                 + list(RE_DSCR_DECL.finditer(low)) + list(RE_DSCR_DECL_REV.finditer(low))
                 + list(RE_DSCR_KW_AFTER_DSCR.finditer(low)))
        # PIVOT_DECOY keys only on the literal canonical value + a pivot, so require the word
        # "dscr" on the line -- otherwise an unrelated "v1.25 -> 2.00" / "ratio 1.25 now 1.80"
        # would mis-fire (the other passes are self-qualifying via "dscr"-anchor or x/keyword).
        if "dscr" in low:
            cands += list(RE_DSCR_PIVOT_DECOY.finditer(low))
        for m in cands:
            val = m.group(1)
            if val == CANON_DSCR or val in seen:
                continue
            vs, ve = m.span(1)
            # skip the corrected-away old value of a DSCR correction note (span-scoped, M-2).
            if any(s <= vs and ve <= e for (s, e) in dscr_corr_spans):
                continue
            # skip an explicit PORTFOLIO-LEVEL DSCR figure: the blended portfolio-wide target
            # (ratified 1.75x, 2026-07-08) is a SEPARATE aggregate metric, not the per-deal governor
            # threshold, so it is not measured against the 1.25x per-deal floor. Vetoed by any
            # per-deal marker (see _portfolio_qualified), so a per-deal floor drifted off-canonical
            # still flags here.
            if _portfolio_qualified(low, vs):
                continue
            # skip a POST-CLOSE-REFI debt-sizing DSCR figure (a DSCR-based rate-pricing tier such as
            # ">=1.40x DSCR", or a refi-sizing DSCR) -- a distinct refinance-market input, not the
            # acquisition governor. Vetoed by any acquisition-governor marker or a value declared AS
            # the governor (see _refi_qualified), so a real per-deal governor drift still flags.
            if _refi_qualified(low, vs):
                continue
            # skip a DSCR value that IS the bps rate-pricing tier's band member (a refi input) --
            # member-scoped, so a floor declared elsewhere on the line still flags. Vetoed if the
            # value is declared AS the governor nearby, OR if it is itself written "Nx DSCR
            # floor/minimum" (a KW_AFTER_DSCR declaration): an explicitly-declared floor is a
            # governor statement, not a rate-tier band, so it must flag even inside a bps tier
            # (round-2 review W3). The legit ":196" tier "1.40x DSCR)" has no trailing floor-word,
            # so it is NOT a KW_AFTER_DSCR match and stays suppressed.
            if (_in_spans(vs, ve, refi_dscr_veto) and not _in_spans(vs, ve, kw_after_spans)
                    and not _governor_declared_nearby(low, vs, ve)):
                continue
            in_pair = any(s <= vs and ve <= e for (s, e) in pair_spans)
            if is_rubric and in_pair:
                continue  # a scored multiple inside a genuine rubric -- not a declared floor
            seen.add(val)
            out.append("DSCR governor threshold %sx != canonical %sx" % (val, CANON_DSCR))

    # 3) LTV ceiling equality -- comparator-bound "ltv <= N%" anywhere, or any % on a
    #    governor-declaration line. Plain prose mentions of LTV are ignored. I-2 decoy: a ceiling
    #    restated as canonical then changed ("LTV ceiling now 65%", "raised from 40% to 65%") is
    #    caught by FROMTO and by scanning a short clause window after an LTV-adjacent ceiling/max
    #    anchor (the metric guard that keeps exit-cap/rent/occupancy percents out).
    #    Reverse-order gap (2026-07-08): a governor line may carry NO literal "ltv" yet still declare
    #    the ceiling number-then-keyword ("65% ceiling"/"65% maximum"). The outer gate therefore also
    #    admits any is_gov line; every ltv-TOKEN-dependent pass below stays behind an explicit 'ltv'
    #    check so its pre-2026-07-08 firing is byte-for-byte unchanged, and ONLY RE_LTV_CEIL_REV is
    #    new. seen_ltv dedupes so an ltv-present value already flagged forward is not double-flagged.
    if "ltv" in low or is_gov:
        seen_ltv = set()
        def _flag_ltv(val, kind="ceiling"):
            if val and val != CANON_LTV and val not in seen_ltv and 1 <= int(val) <= 100:
                seen_ltv.add(val)
                out.append("LTV %s %s%% != canonical %s%%" % (kind, val, CANON_LTV))
        cmp_hits = RE_LTV_CMP.findall(low)  # RE_LTV_CMP embeds 'ltv' -> [] on an ltv-less line
        for val in cmp_hits:
            _flag_ltv(val)
        if is_gov:
            # ltv-TOKEN-dependent passes -- kept behind 'ltv in low' so their firing is UNCHANGED
            # (RE_LTV_FROMTO carries no 'ltv' literal, so it MUST stay gated to avoid new behavior).
            if "ltv" in low:
                for m in RE_LTV_FROMTO.finditer(low):
                    _flag_ltv(m.group(1))
                # read the FIRST percent after each LTV-adjacent ceiling/max anchor -- that is the
                # declared ceiling. A canonical 40% there satisfies it and leaves any later figure
                # (basis discount, yield, exit cap) untouched; a non-canonical first percent flags.
                # The window reaches 40 chars (I-3: catches a moderately verbose "ceiling ... set to
                # 65%") but stops at a clause break [(;|] so a following clause's percent is never the
                # one read when the ceiling itself states no percent. Commas are NOT breaks, so
                # "LTV ceiling, revised, 65%" still reads 65 as the declared ceiling.
                for am in RE_LTV_ANCHOR.finditer(low):
                    base = am.end()
                    window = re.split(r"[(;|\n]", low[base:base + 40])[0]
                    pm = RE_LTV_NUM.search(window)
                    # skip the percent if it is the corrected-away old value of an LTV correction note
                    if pm and not any(s <= base + pm.start(1) < e for (s, e) in ltv_corr_spans):
                        _flag_ltv(pm.group(1))
                if not cmp_hits:  # proximity fallback only when no comparator-bound value was found
                    for m in RE_LTV_NEAR.finditer(low):
                        # skip a POST-CLOSE-REFI LTV sizing figure (e.g. "refi ... 65% LTV" against
                        # stabilized exit value) -- not the acquisition LTV governor. Vetoed by any
                        # acquisition-governor marker or a value declared AS the governor.
                        if _refi_qualified(low, m.start()):
                            continue
                        # skip a percent that IS a refi-sizing construct's own LTV member value
                        # ("LESSER of 65% LTV and 1.25x DSCR", "65% LTV refi-sizing figure",
                        # "refi to 65% LTV", "1.25x DSCR governor at 65% LTV"). Member-scoped: a
                        # ceiling declared elsewhere on the line stays visible. NO-VETO members
                        # (LESSER-of ceiling, refi-to) suppress unconditionally; VETO members
                        # (refi-sizing-named, PAIRED) flag if declared AS the governor nearby.
                        # Applies ONLY to this weakest (bare-proximity) pass; comparator/anchor/
                        # FROMTO/reverse passes stay un-suppressed.
                        pvs, pve = m.span(1) if m.group(1) else m.span(2)
                        if _in_spans(pvs, pve, refi_ltv_noveto):
                            continue
                        if (_in_spans(pvs, pve, refi_ltv_veto)
                                and not _governor_declared_nearby(low, pvs, pve)):
                            continue
                        _flag_ltv(m.group(1) or m.group(2), kind="governor")
            # REVERSE-ORDER ceiling ("65% ceiling"/"65% maximum") -- number-then-keyword, needs NO
            # 'ltv' token, so it closes "This 65% ceiling is the acquisition governor". Correction-
            # span-skipped and post-close-refi-suppressed exactly like the forward passes.
            for m in RE_LTV_CEIL_REV.finditer(low):
                vs = m.start(1)
                if any(s <= vs < e for (s, e) in ltv_corr_spans):
                    continue
                if _refi_qualified(low, vs):
                    continue
                _flag_ltv(m.group(1))
    return out

# DATED AUDIT/PROJECT memory files (2026-07-16): the same append-only NARRATIVE class as
# event_log.md / MEMORY.md -- an audit file RECORDS a finding ("governor-drift probe FP on
# 'per-property LTV 65%'"), it does not DECLARE a live governor. This exemption already existed in
# INTENT (main()'s skip_names comment says "dated audit/project memory files are the same class")
# but was hardcoded to ONE filename, so every new dated audit re-tripped the probe: the 2026-07-16
# setup-audit file did exactly that, and its flagged line is literally the note describing this
# false positive -- the probe re-flagging its own paper trail. Generalized to a pattern for the same
# reason EVENT_LOG_ARCHIVE_RE exists: so a future file needs no hand-added entry.
# Kept TIGHT -- 'project_' prefix AND an 'audit' token AND a FULL ISO date -- so live doctrine files
# (project_replacement_cost_benchmark_unratified.md) stay fully in scope. Module-level so it is
# unit-testable. Accepted blind spot, unchanged IN KIND from the existing precedent: a governor
# change recorded ONLY in a dated audit file and nowhere in standards.md / rules.md / firm.md /
# CLAUDE.md / skills (the doctrinal homes) would go unseen.
DATED_AUDIT_RE = re.compile(r"^project_.*audit.*\d{4}-\d{2}-\d{2}\.md$", re.I)

def _is_test_file(path):
    """Test modules and _tests/ fixtures are NOT governor declarations -- they intentionally quote
    off-canonical values (a mock "[GOVERNOR DRIFT] DSCR 1.20" summary, a 1.75 sentinel) to exercise
    detection/gating, EXACTLY like the probe's own test file (already in skip_names) and
    restore-skill-governor.py. The living governor is declared in standards.md / rules.md / CLAUDE.md
    / skills / capital-config.ts, never in a test. Skips the maintenance/_tests/ subtree (any file)
    and sibling python test modules (test-*.py / test_*.py / *_test.py). Added 2026-07-08 after
    maintenance/_tests/test_git_prepush_doctrine_gate.py -- committed AFTER this probe -- tripped it
    on its fixture strings (a pre-existing false positive; precision over recall, per the docstring)."""
    low = path.replace("\\", "/").lower()
    if "/_tests/" in low:
        return True
    bn = os.path.basename(low)
    return bn.endswith(".py") and (bn.startswith("test-") or bn.startswith("test_")
                                   or bn.endswith("_test.py"))

def main():
    quiet = "--quiet" in sys.argv
    findings = []
    scanned = 0
    skipped_roots = []
    self_path = os.path.abspath(__file__)  # never flag the probe's own example strings
    # Governor-tooling scripts legitimately mention 1.75 / wrong values to detect/restore/
    # test them -> skip them (mirrors self_path).
    skip_names = {"governor-drift-probe.py", "restore-skill-governor.py",
                  "test-governor-drift-probe.py"}
    # Append-only history logs NARRATE past/incident values (a deal's "65% LTV financing",
    # a [SPECULATIVE] audit note) that are not live governor declarations -- they legitimately
    # quote off-canonical numbers and would false-positive forever. The LIVING governor lives in
    # standards.md / rules.md / firm.md / CLAUDE.md / skills, which stay in scope. (Precision over
    # recall, per the module docstring.)
    # MEMORY.md (the index) and dated audit/project memory files are the same class: they NARRATE
    # findings (e.g. "governor-drift probe caught DSCR 1.75x") rather than declare a live governor.
    # Exempting the index broadly (not just event_log.md) accepts a small blind spot -- a governor
    # change accidentally recorded ONLY in the index, never in standards.md/rules.md/firm.md/CLAUDE.md/
    # skills, would go undetected -- judged acceptable since those are the doctrinal homes for a real
    # change, not the index (2026-07-08, added after the formal CLAUDE.md audit's own tracking file
    # tripped this sentinel).
    skip_names |= {"event_log.md", "MEMORY.md"}
    # DATED AUDIT/PROJECT memory files: exempt by pattern -- see DATED_AUDIT_RE at module level.
    # Dated event_log rollover archives (memory-policy.md's rollover rule, first exercised
    # 2026-07-09: _archive/event_log_<YYYY-MM-DD>.md) are the SAME append-only narrative class
    # as event_log.md itself -- a straight cut of its older entries, not a new kind of file.
    # Exempt by pattern so every future rollover doesn't need its own skip_names entry.
    EVENT_LOG_ARCHIVE_RE = re.compile(r"^event_log_\d{4}-\d{2}-\d{2}\.md$")
    for root, exts in build_targets():
        if not (os.path.isfile(root) or os.path.isdir(root)):
            skipped_roots.append(root)
            continue
        for path in iter_files(root, exts):
            basename = os.path.basename(path)
            if (os.path.abspath(path) == self_path or basename in skip_names
                    or EVENT_LOG_ARCHIVE_RE.match(basename) or DATED_AUDIT_RE.match(basename)
                    or _is_test_file(path)):
                continue
            low_path = path.lower().replace("\\", "/")
            is_code = low_path.endswith((".ts", ".tsx", ".js"))
            is_governor_code = os.path.basename(low_path) in GOVERNOR_CODE_FILES
            # brain data snapshots hold per-DEAL dscr/ltv VALUES, not governor declarations --
            # skip them so a deal landing at 1.75 / 0.54 never reads as drift.
            is_data_json = low_path.endswith(".json") and "/data/" in low_path
            try:
                if is_data_json:
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    if is_governor_code:
                        # The ONE governor source file: validate enforcement CONSTANTS directly.
                        content = fh.read()
                        for ln, reason, txt in scan_code(content):
                            findings.append((path, ln, reason, txt))
                        # deletion guard: the governor file MUST carry a numeric declaration of each.
                        if not RE_CODE_DSCR_ANY.search(content):
                            findings.append((path, 0, "DSCR floor governor declaration ABSENT (deleted?)", ""))
                        if not RE_CODE_LTV_ANY.search(content):
                            findings.append((path, 0, "LTV ceiling governor declaration ABSENT (deleted?)", ""))
                    elif is_code:
                        # other code files: dscrFloor/ltvCeiling here are NOT the governor (overloaded
                        # identifiers -- e.g. conditions.ts alert thresholds) -- never governor-checked.
                        pass
                    else:
                        for i, raw in enumerate(fh, 1):
                            for reason in scan_line(raw):
                                findings.append((path, i, reason, raw.strip()[:120]))
                scanned += 1
            except Exception as e:
                # fail loud per I5 -- a file we cannot read is a probe error, not a silent skip
                print("[ACTION] governor-drift-probe could not read %s: %s" % (path, e), file=sys.stderr)
                sys.exit(2)

    if findings:
        print("GOVERNOR DRIFT DETECTED (%d) -- canonical is DSCR >= %sx, LTV <= %s%%:"
              % (len(findings), CANON_DSCR, CANON_LTV))
        for path, ln, reason, txt in findings:
            print("  %s:%d  %s" % (path, ln, reason))
            print("        | %s" % txt)
        sys.exit(1)

    if not quiet:
        print("governor-drift-probe OK -- %d files scanned, DSCR %sx / LTV %s%% consistent."
              % (scanned, CANON_DSCR, CANON_LTV))
        if skipped_roots:
            print("  (roots not present, skipped: %d)" % len(skipped_roots))
    sys.exit(0)

if __name__ == "__main__":
    main()
