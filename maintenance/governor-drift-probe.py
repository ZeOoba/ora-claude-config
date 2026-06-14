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
import os, re, sys, glob

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
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-", "memory")

def discover_skills_root():
    """Auto-discover the live Cowork skills tree (GUIDs rotate -- never hardcode, I4)."""
    base = os.path.join(os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming")),
                        "Claude", "local-agent-mode-sessions", "skills-plugin")
    hits = glob.glob(os.path.join(base, "*", "*", "skills"))
    # newest by mtime wins
    hits = [h for h in hits if os.path.isdir(h)]
    return max(hits, key=os.path.getmtime) if hits else None

# Scan roots: (path, file-extensions). Missing roots are skipped silently (logged once).
def build_targets():
    targets = []
    targets.append((MEM, (".md",)))
    targets.append((os.path.join(CLAUDE, "CLAUDE.md"), None))            # single file
    targets.append((os.path.join(CLAUDE, "agents"), (".md",)))
    targets.append((os.path.join(CLAUDE, "hooks"), (".py", ".json")))
    targets.append((os.path.join(CLAUDE, "maintenance"), (".py", ".json")))
    sk = discover_skills_root()
    if sk:
        targets.append((sk, (".md", ".json")))
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
        # never descend into dependency / build trees
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "dist", ".git", "__pycache__")]
        for fn in filenames:
            if exts is None or fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)

# DSCR threshold near 'dscr'. The trailing x/× is OPTIONAL: a drifted governor may be
# written "DSCR floor 1.10" with no multiplier sign, and the equality check must catch it.
# Guards against over-match: a value immediately followed by '%' is an LTV-style figure,
# not a DSCR multiple -> excluded via lookahead. Still gated to governor-DECLARATION lines
# (is_gov) in scan_line, so prose mentions of a deal's DSCR don't trip it.
RE_DSCR_THRESH = re.compile(r"dscr[^0-9\n]{0,40}?([0-9]+\.[0-9]+)\s*[x×]?(?!\s*%)", re.I)
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
                "self-imposed", "minimum dscr", "min dscr", "acquisition screen")

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

    # 1) Regression sentinel: 1.75 near DSCR/governor. Fires only for a 1.75 OUTSIDE any correction
    #    span -- a live drift, not the corrected-away value of a "corrected from 1.75 → 1.25" note.
    if "dscr" in low or "governor" in low:
        idx = low.find("1.75")
        while idx != -1:
            if not any(s <= idx < e for (s, e) in dscr_corr_spans):
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
        cands = (list(RE_DSCR_THRESH.finditer(low)) + list(RE_DSCR_FROMTO.finditer(low))
                 + list(RE_DSCR_DECL.finditer(low)))
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
    if "ltv" in low:
        seen_ltv = set()
        def _flag_ltv(val, kind="ceiling"):
            if val and val != CANON_LTV and val not in seen_ltv and 1 <= int(val) <= 100:
                seen_ltv.add(val)
                out.append("LTV %s %s%% != canonical %s%%" % (kind, val, CANON_LTV))
        cmp_hits = RE_LTV_CMP.findall(low)
        for val in cmp_hits:
            _flag_ltv(val)
        if is_gov:
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
                    _flag_ltv(m.group(1) or m.group(2), kind="governor")
    return out

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
    skip_names |= {"event_log.md"}
    for root, exts in build_targets():
        if not (os.path.isfile(root) or os.path.isdir(root)):
            skipped_roots.append(root)
            continue
        for path in iter_files(root, exts):
            if os.path.abspath(path) == self_path or os.path.basename(path) in skip_names:
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
