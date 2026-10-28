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
    # Scheduled-task fleet SKILL.mds, BOTH fleets (coverage gap closed 2026-07-24). 17 fleet
    # SKILL.md files declare DSCR/LTV (ora-am-brief, ora-monthly-portfolio-briefing,
    # ora-master-workbook-ingest, ora-underwrite-doctrine-staleness-check, ...), so a governor
    # edit landing in one was invisible to this guard. Roots are the fixed skillFolderRoots from
    # _shared/scheduler-stores.json -- hardcoded here rather than imported because this probe is
    # deliberately dependency-free (pure stdlib, no _shared import) so it stays runnable when
    # store_discovery is broken. A root that does not exist is skipped silently, as with all others.
    targets.append((os.path.join(CLAUDE, "scheduled-tasks"), (".md",)))
    targets.append((os.path.join(HOME, "OneDrive - Oxford Capital Partners",
                                 "Documents", "Claude", "Scheduled"), (".md",)))
    return targets

_PRUNE_EXACT = ("node_modules", "dist", ".git", "__pycache__", "_archive", "_staging",
                 "active-work", "sessions")
# Archive dirs are named "_archive_<date>[_suffix]" in practice (26 such dirs live across the
# fleet roots, memory, hooks/sessions and the brain warehouse) -- the exact-name test above
# matched NONE of them, so every dated archive was being scanned as live content. Fixed
# 2026-07-24; the archived 2026-04 draft carrying "DSCR ... below 1.75 (ORA hard governor)"
# was the trigger. Requires the trailing separator so the match stays TIGHT: suppression on a
# governor guard is a false NEGATIVE, and "_archives_live" must still be scanned.
_PRUNE_PREFIX = ("_archive_", "_staging_")
# hooks/active-work/*.json (2026-08-22, found while landing the tilde-hedge fix above): these are
# claim_work.py's EPHEMERAL cross-session claim broadcasts, not governor documentation -- same
# narrative-artifact class as event_log.md/MEMORY.md (skip_names, in main()), just JSON instead of
# markdown and under hooks/ instead of memory/. A claim's free-text `description` legitimately
# quotes whatever bug/task it's about (e.g. "Fix ... 'inflating computed DSCR ~1.6x' misread as a
# declared threshold"), and a --force takeover additionally embeds the DISPLACED claim's own
# description verbatim in `prior_claim` -- so the exact bug text this fix targets ended up
# self-triggering via this session's own claim file the moment it was written. Pruned by directory
# name (not skip_names, since claim filenames are slug-derived and unbounded) -- consistent with
# _PRUNE_EXACT's directory-level exclusions above.
# hooks/sessions/<id>/{overrides,reviews}/*.json (2026-08-22, found while landing the LTV-narrative
# fix above): the SAME ephemeral cross-session narrative-artifact class as active-work -- an
# eos-review-gate.py --record artifact's free-text `notes` and a git-prepush-hook-tests-gate.py
# override token's free-text `reason` both legitimately quote whatever bug they're about. This
# session's OWN review artifact for the LTV-narrative fix quoted "LTV 65%/40%" in its notes and
# self-triggered the probe the moment it was written. Pruned by directory name (session ids are
# unbounded, same as claim slugs) -- consistent with active-work's precedent above.

def _is_pruned_dir(name):
    return name in _PRUNE_EXACT or name.startswith(_PRUNE_PREFIX)

def iter_files(root, exts):
    if os.path.isfile(root):
        yield root
        return
    if not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # never descend into dependency / build trees, or retired/in-progress skill content
        dirnames[:] = [d for d in dirnames if not _is_pruned_dir(d)]
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
# DECIMAL-FRAGMENT GUARD (2026-07-29): every free-floating percent capture below carries
# (?<![0-9.]) plus a full-decimal tail. Without them, a narrated per-property figure like
# "54.3% LTV" let the engine bind the FRACTIONAL digits alone ("3% LTV" -> "LTV governor 3%"),
# a nonsense value -- the live false-positive class caught 2026-07-29 (disposition-ledger.md:38,
# project_historical_evaluations...:46). The fix is detection-POSITIVE, not a suppression: a
# genuinely drifted decimal ceiling ("LTV ceiling 42.5%") previously bound a garbage fragment or
# nothing at all; it now binds whole and flags with the true value. Comparison is NUMERIC in
# _flag_ltv, so "40.0%" correctly reads as canonical.
_LTV_VAL = r"(?<![0-9.])([0-9]{1,3}(?:\.[0-9]+)?)"
RE_LTV_CMP = re.compile(r"ltv[^0-9\n]{0,15}?[≤<]=?\s*" + _LTV_VAL + r"\s*%", re.I)
RE_LTV_NUM = re.compile(_LTV_VAL + r"\s*%")
# LTV value in CLOSE PROXIMITY to the word "ltv" (no comparator) -- e.g. "LTV 65%" / "65% LTV".
# Proximity-bound so unrelated %s on the same line (replacement-discount, yield-on-cost) are NOT
# misread as LTV merely because the line also mentions "ltv" (fixes the deal-recon buy-box false positive).
RE_LTV_NEAR = re.compile(r"ltv[^0-9\n]{0,12}" + _LTV_VAL + r"\s*%|"
                         + _LTV_VAL + r"\s*%[^0-9\n]{0,8}ltv", re.I)
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
# GAP 2 CLOSED 2026-08-12: the first alternative required CONTIGUOUS "ltv ceiling" (\s* only), so a
# qualifier defeated it exactly as the contiguous GOV_KEYWORDS literals defeated is_gov -- "LTV hard
# ceiling 75%" was ARMED ("hard ceiling" is a GOV_KEYWORDS token, N6) yet extracted nothing. The
# 2026-08-11 revision misattributed this to the arming gate; independent review corrected it to the
# extractor, and the middle alternative closes it here.
# Bounded like the DSCR gate (clause enders, non-greedy) and deliberately NARROWER: bare "max" is
# NOT allowed across a gap, only contiguously. "maximum" spelled in full is a rare non-LTV
# collocation, but a gapped bare "max" would reach unrelated percents ("ltv ... vacancy 15% max").
# Safe against the ratified 65% per-property refi-ceiling false positive that forced the earlier
# revert, because that line is excluded by ARMING, not by extraction -- pinned by
# test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit.
RE_LTV_ANCHOR = re.compile(r"ltv\s*(?:ceiling|maximum|max)"
                           r"|ltv[^.;!?\n]{0,16}?(?:ceiling|maximum)\b"
                           r"|(?:ceiling|maximum|max)\s*ltv", re.I)
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
RE_LTV_CEIL_REV = re.compile(_LTV_VAL + r"\s*%\s*(?:ceiling|maximum)\b", re.I)
# INTERIM-CHECKLIST threshold wording (ora-skills PR #165, debt-management/references/
# ltv-interim-netting-checklist.md). The checklist states its OPERATIVE 40% in two shapes that carry no
# governor keyword and no "<=" comparator, so no earlier pass read them and a hand edit of the threshold
# was silent (reviewer finding on PR #165). Both extractors are comparator-bound to a DISTINCTIVE
# anchor, not to a bare percent, so unrelated prose ("vacancy above 10%") cannot match:
#   * RE_LTV_INTERIM_CMP + RE_LTV_FLAG_TERM: "<above|over|exceeds|...> N%" bound to the flag term
#     'ltv-flag(ged)' in the same sentence, either order (see block 4 in scan_line for the windows).
#   * RE_LTV_ROW_*: the worksheet row "| N | Result = (...loan...) / (...value...), vs N% |"; the 'loan'
#     and 'value' tokens in the FORMULA are the metric guard (an unrelated "Result = NOI / debt, vs 8%"
#     row has neither).
# REFUTE round 1 (2026-10-27) reshaped these: (1) each comparator+value is matched ON ITS OWN (a
# lookahead/lookbehind check for the flag term replaces the consuming ".{0,80}?ltv-flag" tail, which
# let a canonical 40% earlier on the line swallow a drifted value after it); (2) markdown bold around
# the number, dash/underscore variants of 'ltv-flag', the extra comparator spellings and 'versus' /
# 'loans' are accepted; (3) the per-property veto is scoped to the VALUE, not the whole line.
_BOLD = r"[*_`]*"
RE_LTV_INTERIM_CMP = re.compile(
    r"(?:above|over|exceeds?|exceeding|greater\s+than|more\s+than|in\s+excess\s+of|beyond|&gt;=?|[>≥]=?)\s*" + _BOLD
    + _LTV_VAL + _BOLD + r"\s*%", re.I)
RE_LTV_FLAG_TERM = re.compile(r"ltv[\s\-‐-―−_*]*flag", re.I)
# words that make an 'LTV flag ... over N%' sentence a STATISTIC about flags, not the threshold
# (hyphen-aware: "Oxford-share" is the checklist's own wording and is NOT a flag statistic -- REFUTE
# round 2 N1)
LTV_FLAG_STAT_WORDS = re.compile(
    r"(?<![\w-])(?:rate|rates|count|counts|share|shares|pipeline)(?![\w-])", re.I)
# a DIFFERENT ratio named just before the comparator ("LTC above 80%", "occupancy above 90%");
# hyphen-aware so "yield-adjusted result exceeds 55%" is not "yield" (N3)
LTV_OTHER_RATIO_BEFORE = re.compile(
    r"(?<![\w-])(?:ltc|dscr|occupancy|vacancy|yield|noi)(?![\w-])", re.I)
# sentence end: '. ' that is not an abbreviation ("i.e. ", "e.g. ", "vs. ", "etc. ") -- N2. A flag term
# in the NEXT sentence is deliberately not bound ("... target. LTV-FLAGGED deals ..."); the one accepted
# residual is a split like "above 40% gross; above 55% netted. Either is LTV-FLAGGED".
RE_LTV_SENT_END = re.compile(r"(?<!i\.e)(?<!e\.g)(?<!\bvs)(?<!\betc)\.\s")
# the flag term this value binds to carries a portfolio/aggregate qualifier: "LTV-FLAGGED (portfolio)"
RE_LTV_FLAG_PORTFOLIO_QUAL = re.compile(r"\w*[\s*_`]*\(\s*(?:portfolio|aggregate)", re.I)
# Worksheet result row. Linear-time by construction (REFUTE round 2, C11: the earlier single regex with
# nested lazy quantifiers was cubic on a long line): locate the row head, then the first 'vs'/'versus',
# then check the FORMULA between them in code.
RE_LTV_ROW_HEAD = re.compile(r"\|\s*[*_`]*result[*_`]*\s*[=:]", re.I)
RE_LTV_ROW_VS = re.compile(r"\b(?:vs\.?|versus)\b", re.I)
RE_LTV_ROW_LOAN = re.compile(r"\bloans?\b", re.I)
RE_LTV_ROW_VALUE = re.compile(r"\bvalues?\b", re.I)
RE_LTV_ROW_PCT = re.compile(_BOLD + _LTV_VAL + _BOLD + r"\s*%", re.I)
RE_LTV_ROW_PCT_ONLY = re.compile(r"\s*" + _BOLD + _LTV_VAL + _BOLD + r"\s*%\s*", re.I)
# a result row that is about another ratio (debt yield, LTC, DSCR, lender max): FORMULA part only
RE_LTV_ROW_NEG = re.compile(r"\b(?:lender|ltc|dscr|noi|yield)\b", re.I)
# ...and the owner named right AFTER a threshold percentage in the 'vs' cell ("vs 75% lender max")
RE_LTV_ROW_PCT_OWNER = re.compile(r"\b(?:lender|ltc)\b", re.I)
INTERIM_FLAG_WINDOW_AFTER = 200   # bounded by the end of the sentence ('. ') inside this window
INTERIM_FLAG_WINDOW_BEFORE = 120
INTERIM_PERPROP_NEAR = 30
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
# Tilde-hedged CHANGELOG narration suppressor (2026-08-21 FP fix; M-3 symmetry with the correction
# notes above). A Changelog entry narrating a past bug's SYMPTOM value glues '~' directly to the
# digits ("inflating computed DSCR ~1.6x ... corrected to the LESSER-of-65%-LTV/1.25x-DSCR basis")
# -- but unlike RE_DSCR_CORRECTION's tight "corrected from X to 1.25" structure, real changelog
# prose doesn't always land in that exact shape (no "from X to Y" pair here).
# TWO REFUTE-caught gaps, both closed:
#   1) (2026-08-21, first attempt) a blanket (?<![vV~]) lookbehind straight on RE_DSCR_THRESH
#      unconditionally suppressed EVERY tilde-glued value -- silently hiding a REAL drift report
#      written the same way ("dscr floor ~1.10x" with no companion canonical restatement, e.g. an
#      audit note reading "the governor now reads ~1.10x"). Fixed by span-scoping (below).
#   2) (2026-08-21, second attempt) span-scoping to "tilde value + a bare 1.25 ANYWHERE on the
#      line" was still too loose: "the acquisition dscr floor reads ~1.10x in three files -- needs
#      reverting to 1.25x" is an UNRESOLVED drift report (the fix has NOT happened) that also
#      mentions 1.25, and would have been wrongly suppressed. This is the exact "whole-line
#      corrected + 1.25" shape line 267's comment already says was tried and REPLACED for being
#      too loose (just not span-scoped that time). Fixed by ALSO requiring the literal word
#      "corrected" -- the same completed-action anchor RE_DSCR_CORRECTION already uses -- so a
#      still-broken "needs reverting" report is never mistaken for an already-fixed changelog note.
# Suppression now requires ALL THREE, checked PER TILDE VALUE (round-1 independent review,
# 2026-08-22 -- two more REFUTE gaps found and closed):
#   (a) the value is tilde-glued,
#   (b) the WORD-BOUNDARY token "corrected" (not a bare substring -- "un**corrected**" is NOT a
#       completed-action anchor, it is the opposite) appears AFTER that SPECIFIC value, within
#       TILDE_HEDGE_CORRECTED_AFTER_REACH chars (directional + windowed, same house convention as
#       VETO_BEFORE/VETO_AFTER elsewhere in this module) -- so "corrected" narrating an UNRELATED
#       fix earlier on the line, or "corrected to ~1.40x" where the tilde-hedged value is itself
#       the NEW (bad) figure, cannot arm suppression for a value it doesn't actually describe, and
#       a second, still-broken tilde value later on the same line (sharing a line with one
#       genuinely-fixed value) is unaffected by the first value's "corrected",
#   (c) the line separately restates the PLAIN (non-hedged) canonical 1.25.
# A tilde-hedged value with any signal missing -- no directionally-after "corrected", or no
# plain-1.25 companion -- still flags via RE_DSCR_THRESH untouched. Real-line margin: the actual
# deal-comparison/SKILL.md:153 target has an 87-char gap from the tilde value to "corrected". The
# EFFECTIVE reach is REACH minus len("corrected")=9, since the 9-char word must fit whole inside
# the window (round-1 independent review, 2026-08-22: REACH=100 gave only a 4-char true margin,
# not the "with margin" an earlier draft of this comment implied) -- REACH=150 restores real
# headroom (91 -> 141 char true reach) against a lightly-reworded future changelog line, while
# still staying far short of reaching into an unrelated clause. The failure direction if a real
# line ever DOES exceed this is safe either way: the value flags loudly (re-blocks the push) and
# test_deal_comparison_skill_file_clean fails at push time -- it does not silently under-flag.
#
# KNOWN RESIDUALS (round-1 independent review, non-blocking, inherent to any positional-window
# anchor rather than true semantic binding): a genuinely drifted tilde value can still be masked
# if an UNRELATED completed-action "corrected" (fixing some other metric) happens to land inside
# the after-window on the SAME line as a plain-1.25 companion --
#   "the dscr floor now reads ~1.10x, still wrong; the ltv typo was corrected and canonical dscr
#   is 1.25x." -- suppressed, though the DSCR figure itself was never corrected.
# -- and a trailing SECOND "corrected" can re-open the J-shape fix (a value corrected TO a bad
# tilde figure, then narrated as corrected again) --
#   "dscr floor corrected to ~1.40x from 1.25x, then corrected again in v3." -- suppressed.
# Both require deliberately dense, unusual phrasing not observed in the live tree; closing them
# needs semantic binding (which "corrected" clause a value belongs to), not a wider or narrower
# window, and was judged not worth a further round. Left as accepted residuals -- a future REFUTE
# pass should not re-derive these as new findings without a plan to actually close them.
RE_DSCR_TILDE_HEDGE = re.compile(r"~([0-9]+\.[0-9]+)(?![0-9])(?!%)\s*[x×]?", re.I)
# Qodo PR #145 review finding (2026-08-22, HIGH): the original lookbehind/lookahead pair
# ((?<![~0-9.]) ... (?![0-9])) excluded a tilde/digit/dot glued immediately before or a digit
# immediately after, but NOT a version-token 'v'/'V' before it ("v1.25", mirroring the SAME gap
# RE_DSCR_THRESH's own (?<![vV]) already closed above) or a percent immediately after ("1.25%",
# mirroring RE_DSCR_THRESH's (?!%)) -- either would let a version string or an unrelated rate let
# a tilde-hedged DRIFT value ride an accidental "plain 1.25" companion into wrong suppression.
RE_DSCR_CANON_PLAIN = re.compile(
    r"(?<![vV~0-9.])" + re.escape(CANON_DSCR) + r"(?![0-9])(?!%)", re.I)
RE_CORRECTED_WORD = re.compile(r"\bcorrected\b", re.I)
TILDE_HEDGE_CORRECTED_AFTER_REACH = 150

def _tilde_hedge_suppressed_spans(low):
    """Per-span, directional tilde-hedge suppression (see the block comment above). Returns the
    digit-group spans of tilde-hedged DSCR values that are unambiguously a COMPLETED-fix
    changelog narration, not a pending/unresolved drift report or an unrelated value sharing the
    line with one."""
    if RE_DSCR_CANON_PLAIN.search(low) is None:
        return []
    spans = []
    for mm in RE_DSCR_TILDE_HEDGE.finditer(low):
        vs, ve = mm.span(1)
        window = low[ve:ve + TILDE_HEDGE_CORRECTED_AFTER_REACH]
        if RE_CORRECTED_WORD.search(window):
            spans.append((vs, ve))
    return spans
# Probe SELF-DESCRIPTION suppressor (2026-07-24): documentation of THIS probe's own detection
# semantics must quote the sentinel value to be useful -- ora-doctrine-integrity-guard/SKILL.md
# reads "...or the 1.75 regression sentinel". That is prose ABOUT the detector, not a governor
# declaration, and it surfaced the moment the fleet roots were added to build_targets().
# Deliberately bound to the probe's TERM OF ART ("regression sentinel"), not to a bare nearby
# "sentinel" token, and SPAN-SCOPED like the correction notes: branch 1 keeps scanning past a
# suppressed 1.75, so a real declaration sharing the line still flags. Anything looser would
# hand a drifting editor a one-word evasion on a Hard-Invariant-4 guard.
RE_SENTINEL_PROSE = re.compile(r"1\.75\s*[x×]?\s+regression\s+sentinel", re.I)
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
# 2026-09-30: governor-constants.ts joins the set. oxford-command-center PR 386 moved the ratified
# LITERALS (`dscrFloor: 1.25`, `ltvCeiling: 0.40`) out of capital-config.ts into
# src/contracts/governor-constants.ts (RATIFIED_GOVERNORS), leaving capital-config.ts comparing
# against the variable. Without this entry the probe verified no literal at all and a weakened
# constant would have passed silently. Both files hold only governor values (no alert-threshold
# reuse of the identifiers), so routing them to scan_code carries no false-positive risk.
GOVERNOR_CODE_FILES = {"capital-config.ts", "governor-constants.ts"}
# Variable-form canonical guards (`next.dscrFloor < RATIFIED_GOVERNORS.dscrFloor`), the shape
# capital-config.ts uses since PR 386. They license the `> 0` positivity exemption in scan_code.
# Matched as the EXACT real shape `if (next.X <op> RATIFIED_GOVERNORS.X)` -- no extra operand, no
# `&&`/`||` composition, no arithmetic on the constant, `next.` only -- so a neutered guard
# (`&& false`, `- 0.15`, `prev.dscrFloor`) fails closed instead of licensing the exemption.
# The guard must START its own line (`^[ \t]*if`), so text mid-line inside a string, template or
# regex literal can never license the exemption even if tokenizing desyncs.
RE_CODE_DSCR_RATIFIED_GUARD = re.compile(
    r"^[ \t]*if\s*\(\s*next\.dscrFloor\s*<\s*RATIFIED_GOVERNORS\.dscrFloor\s*\)", re.M)
RE_CODE_LTV_RATIFIED_GUARD = re.compile(
    r"^[ \t]*if\s*\(\s*next\.ltvCeiling\s*>\s*RATIFIED_GOVERNORS\.ltvCeiling\s*\)", re.M)
# Comments and string/template literals are blanked in ONE left-to-right pass (leftmost match wins,
# so a `/*` inside a string is part of the string and a `'` inside a comment is part of the comment)
# before guard detection. Two separate passes desync on exactly those cases.
RE_CODE_TOKENS = re.compile(
    r"//[^\n]*|/\*.*?\*/|'(?:[^'\\\n]|\\.)*'?|\"(?:[^\"\\\n]|\\.)*\"?|`(?:[^`\\]|\\.)*`?|/\*.*", re.S)
# The closing quote/backtick is OPTIONAL on purpose: with a mandatory closer, every unclosed quote
# rescanned to end-of-line (backtick: end-of-file), which was quadratic (~2.4s at 32KB). Optional,
# an unterminated literal simply swallows to its boundary in linear time -- which also fails closed,
# because the swallowed text can no longer supply a canonical guard.
# Simple template interpolation body: identifiers, dots, whitespace, then the closing brace.
RE_CODE_TMPL_INTERP_SIMPLE = re.compile(r"[\w.\s]*\}")
_NUM = r"(?:[0-9]*\.[0-9]+|[0-9]+)"
# Numeric-form canonical guards, same exact-shape discipline: `if (next.dscrFloor < 1.25)`.
RE_CODE_DSCR_NUM_GUARD = re.compile(r"^[ \t]*if\s*\(\s*next\.dscrFloor\s*<\s*(" + _NUM + r")\s*\)", re.M)
RE_CODE_LTV_NUM_GUARD = re.compile(r"^[ \t]*if\s*\(\s*next\.ltvCeiling\s*>\s*(" + _NUM + r")\s*\)", re.M)
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
    (capital-config.ts, governor-constants.ts) -- not prose. main() routes ONLY those files here (see GOVERNOR_CODE_FILES:
    the identifiers are overloaded, so a global check would false-positive on conditions.ts alert
    thresholds). Numeric equality: 0.4 == 0.40, 1.250 == 1.25, leading-dot .40 == 0.40.

    Covers: the ratified SEED literal (`dscrFloor: 1.25`, `ltvCeiling: 0.40`) AND the write-time
    GUARD (`dscrFloor < 1.25`, `ltvCeiling > 0.40`); a changed literal, an operator flip (<=/>=), an
    inverted guard (`dscrFloor > 1.25`). The `> 3` sanity ceiling is exempt. Whole-file DELETION of a
    governor declaration is caught separately in main() (presence guard).

    Adversarial residuals (single-line regex, stdlib-only -- a full TS AST is out of scope; low risk
    given the scope is TWO small controlled files using identifier-first literal forms). Residuals
    accepted in the 2026-09-30 review of the `> 0` exemption: it is FILE-scoped, not path-scoped
    (a second write function carrying only a `> 0` guard is licensed by the canonical guard in a
    different function); the guard is matched textually, never validated as reachable or as having
    a throwing body (an empty `{}` body, an earlier `return`, a shadowed `next`, or a dead branch
    built inside an unrelated `if` all pass; shapes with `&&`/`||`/arithmetic still fail closed);
    complex template interpolation, or a backtick surviving the tokenizer, disables the exemption
    for the whole file (fail closed); a deliberately BALANCED tokenizer desync built from regex
    literals (e.g. a regex containing a backtick paired with a later one, exposing template text as
    live code) is NOT detected -- the tokenizer has no regex-literal awareness and a full TS lexer
    is out of scope; this probe is a tripwire for accidental drift, and a deliberate edit to these
    two small files is caught in PR review; seed literals with arithmetic (`1.25 - 0.15`)
    or `&&` tails pass the seed regex, as before. A renamed
    identifier; a constant via a variable (`< MIN`) or scientific notation (`1.25e-1` / `4e-1`); a
    Yoda comparison (`1.10 > dscrFloor`); a declaration split across lines or broken by a comment."""
    out = []
    # Positivity-guard exemption (2026-09-30). capital-config.ts carries fail-closed `x > 0` guards
    # beside the real guards (a zero ceiling turns the DSCR proxy into Infinity). Read alone, `> 0`
    # looks like a relaxed floor/ceiling, which blocked a push. It is exempt ONLY while the real
    # canonical guard for the SAME metric (`if (next.dscrFloor < 1.25)` / `if (next.ltvCeiling > 0.40)`
    # or the RATIFIED_GOVERNORS variable form) is still present as a whole line OUTSIDE every comment
    # and literal -- so replacing or deleting the real guard re-arms the flag. Strictly `> 0`:
    # `>= 0`, `> 0.5` and any drifted canonical constant stay flagged.
    # Blank comments and literals in one pass, keeping each match's newlines so line starts stay true.
    desync = []  # set when any quote/backtick/block-comment token is unterminated

    def _blank(m):
        tok = m.group(0)
        if tok[0] in "'\"`":
            bs = len(tok) - 1 - len(tok[:-1].rstrip("\\"))  # backslashes immediately before the last char
            if len(tok) < 2 or tok[-1] != tok[0] or bs % 2:
                desync.append(tok[:1])
        elif tok.startswith("/*") and not tok.endswith("*/"):
            desync.append("/*")
        return " " + "\n" * tok.count("\n")

    code_only = RE_CODE_TOKENS.sub(_blank, text)
    has_dscr_guard = (
        any(float(m.group(1)) == CANON_DSCR_NUM for m in RE_CODE_DSCR_NUM_GUARD.finditer(code_only))
        or RE_CODE_DSCR_RATIFIED_GUARD.search(code_only) is not None)
    has_ltv_guard = (
        any(float(m.group(1)) == CANON_LTV_NUM for m in RE_CODE_LTV_NUM_GUARD.finditer(code_only))
        or RE_CODE_LTV_RATIFIED_GUARD.search(code_only) is not None)
    # Fail closed on complex template interpolation: a backtick, quote, comment or brace inside `${...}`
    # can close the tokenizer's template early and expose template TEXT as live code (second-pass
    # review: a guard on its own line inside a multi-line template after `${"`"}`). Regex cannot track
    # nested templates, so any `${...}` holding more than identifiers, dots and whitespace disables
    # the exemption for the whole file. Every `${...}` in the real capital-config.ts is a plain
    # identifier chain (`${next.dscrFloor}`), so the real file is unaffected.
    # Linear scan (a findall over `[^}]*` was quadratic on `${${${...`; measured 29s at 160KB): each
    # `${` must be followed by a short identifier run and its `}` or the exemption is dropped.
    pos = text.find("${")
    while pos != -1:
        if not RE_CODE_TMPL_INTERP_SIMPLE.match(text, pos + 2):
            has_dscr_guard = has_ltv_guard = False
            break
        pos = text.find("${", pos + 2)
    # An UNTERMINATED quote, template or block comment means a template/regex literal desynced the
    # tokenizer (the closers are optional, so such a token swallows to its boundary): fail closed. A
    # deliberately BALANCED desync built from regex literals is an accepted residual (see docstring).
    if desync or "`" in code_only:
        has_dscr_guard = has_ltv_guard = False
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
            elif op == ">" and num == 0 and has_dscr_guard:
                continue  # positivity guard; the real floor guard is present (see exemption note above)
            elif num <= 2:  # '>'/'>=' in the governor range = inverted/relaxed floor; '> 3' sanity exempt
                out.append((i, "DSCR floor compared with '%s %s' -- inverted/relaxed floor"
                            % (op, m.group(2)), raw.strip()[:120]))
        for m in RE_CODE_LTV.finditer(raw):
            op, num = m.group(1), float(m.group(2))
            if op in (">", ">="):  # the CEILING guard: refuse when ceiling is above the canonical max
                if op == ">=":
                    out.append((i, "LTV ceiling guard uses '>=' (direction drift; expected '> %s')"
                                % CANON_LTV_NUM, raw.strip()[:120]))
                elif op == ">" and num == 0 and has_ltv_guard:
                    continue  # positivity guard; the real ceiling guard is present (see note above)
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

# INTERVENING-QUALIFIER gate gap (2026-08-11). Every metric-paired entry above is a CONTIGUOUS
# literal ("dscr floor", "ltv ceiling", "min dscr"), so a single qualifier between the metric and
# its floor/ceiling word defeated is_gov and skipped the ENTIRE equality branch: "DSCR hard floor
# 1.40x" scanned clean. That is not a hypothetical wording -- it is verbatim how the 2026-08-11
# Notion Acquisition Pipeline Tracker defect was written ("hard floor 1.75"), so the false negative
# sat squarely on the most probable real-world drift phrasing.
#
# Fixed by PAIRING the metric token with its bound-word across a short gap, NOT by adding "hard
# floor"/"hard ceiling" as standalone keywords. That distinction is the precision guarantee: "hard
# floor" is also a building term ("Suite B has a hard floor"), and a bare token would arm unrelated
# property prose on a Hard-Invariant-4 guard. Requiring the metric token means only a line that
# actually names DSCR/LTV near a bound-word is armed.
#
# Bounded deliberately: the gap class excludes CLAUSE ENDERS (. ; ! ?) and line breaks, so the gate
# cannot reach across a sentence or clause into an unrelated metric: "DSCR is disclosed quarterly.
# The rent floor is 1.40 psf." and "DSCR fine; rent floor is 1.40 psf." both stay unarmed. Excluding
# '.' alone was NOT enough -- ';' '!' '?' each let the gap cross into a rent/area figure that
# RE_DSCR_THRESH (40-char reach) then captured as a DSCR threshold. Caught in independent review;
# the four clause boundaries are pinned by test_qualifier_gate_requires_the_metric_token_unit.
# Arming a line is NOT a finding -- every equality check, veto and suppressor downstream still
# applies unchanged; this only decides whether the line is looked at at all.
#
# DO NOT extend the exclusion set past clause enders. ',' ':' '--' '|' and parentheses deliberately
# still cross the gap: "DSCR, hard floor, 1.40x" and the house "DSCR -- hard floor 1.40x" style are
# plausible governor DECLARATIONS, so blacklisting those separators would convert a visible false
# positive into a silent false negative -- the wrong side of this guard's bias. A markdown table row
# ("| DSCR | floor | 1.40x |") arming is a TRUE positive, not collateral damage. Recommended
# explicitly in independent review 2026-08-12; a future "hardening" pass should not undo it.
#
# GAP 1 -- CLOSED 2026-08-12 (was a known gap for one day). The metric-VALUE-boundword order
# ("DSCR 1.40x minimum") did not arm, because the value's own decimal is a '.' and the gap class
# above excludes it -- so the extractor for that shape (RE_DSCR_DECL_REV, 2026-07-08) was
# unreachable on any line whose only governor signal was this phrasing.
#
# Closed by ADDING a second, value-abutting pattern rather than loosening the first. The decimal
# lives INSIDE the pattern, so it can never be mistaken for a sentence boundary, and bare "min" is
# accepted ONLY after an explicit x/× -- because "min" is a duration unit at least as often as it is
# "minimum". That distinction is the whole fix: the simpler alternative (allow a dot between digits
# anywhere in the gap) was implemented and REJECTED on measurement, since it reports "DSCR of 1.42
# with a 10 min cure period" as governor drift. Duration prose is pinned clean by
# test_value_abutting_arming_does_not_flag_durations_unit.
#
# Note on why this is safe to arm at all: the probe SKIPS its own source file and every test file
# (main(): self_path / skip_names / _is_test_file), so the example strings quoted in these comments
# and in the test suite are never scanned in a real run. An earlier review believed this gap needed
# new self-file exemption machinery before it could close; that machinery already existed.
#
# KNOWN GAP 2 -- DSCR ONLY; there is no LTV analog. It was implemented, tested and REVERTED because
# it armed prose describing the RATIFIED per-property 65% refi ceiling, e.g.
# oxford-command-center/server/warehouse/debt-maturity.DESIGN.md:18 ("Per-property LTV vs the 65%
# refi ceiling"), which then flagged 65 != canonical 40. It escapes both existing suppressors:
# _refi_qualified's REFI_FRAME has no "refi ceiling" token, and the per-property pairing suppressor
# is companion-anchored on a canonical 40 that line does not carry. Closing it requires widening LTV
# SUPPRESSION -- a false-negative risk on Hard Invariant 4 that belongs in its own reviewed change.
# ATTRIBUTION (corrected in review): do NOT start at this gate. A line like "LTV hard ceiling 75%"
# is ALREADY armed today ("hard ceiling" is a GOV_KEYWORDS token, N6 2026-07-12) and still yields
# nothing -- the binding constraint is the LTV EXTRACTORS (RE_LTV_ANCHOR needs a contiguous "ltv
# ceiling"; RE_LTV_NEAR's window is shorter than " hard ceiling "), not is_gov.
RE_GOV_DSCR_BOUND = re.compile(r"\bdscr\b[^.;!?\n]{0,24}?\b(?:floor|minimum|min)\b", re.I)
# Value-abutting order: dscr ... <value> [x] <bound-word>. Bare "min" REQUIRES the x/× (duration
# guard, see GAP 1 above); "floor"/"minimum" spell themselves out and do not.
RE_GOV_DSCR_VALUE_BOUND = re.compile(
    r"\bdscr\b[^.;!?\n]{0,24}?[0-9]+\.[0-9]+\s*(?:[x×]\s*(?:floor|minimum|min)|floor|minimum)\b",
    re.I)


def _is_gov_line(low):
    """True when the line carries a governor-DECLARATION signal: a GOV_KEYWORDS token, or the DSCR
    metric token paired with its bound-word -- either across a short intra-sentence gap
    ("DSCR hard floor 1.40x") or with the value between the two ("DSCR 1.40x minimum")."""
    return (any(k in low for k in GOV_KEYWORDS)
            or RE_GOV_DSCR_BOUND.search(low) is not None
            or RE_GOV_DSCR_VALUE_BOUND.search(low) is not None)

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

# --- Deal-specific stabilization-conditioned covenant qualifier (2026-08-15) -----------------
# A deal-pipeline file legitimately narrates ONE deal's LENDER covenant that only clears at
# stabilization -- the live trigger is projects.md's 754 Old State Route 74 row: "transition-year
# DSCR breaches (clears the 1.75x floor only at Yr3+ stabilization) → all-cash close mandatory".
# That is the PROPERTY'S OWN projected DSCR measured against a deal-specific loan covenant across
# a lease-up timeline, NOT a restatement of ORA's canonical acquisition governor (CANON_DSCR
# 1.25x). The phrase arms _is_gov via the dscr..value..floor pairing (RE_GOV_DSCR_VALUE_BOUND),
# and the value then flags in BOTH the 1.75 sentinel (branch 1) and the equality pass (branch 2)
# -- a false positive of exactly the class _portfolio_qualified / _refi_qualified exist for, and
# one no existing suppressor catches (no portfolio token, no refi frame, no correction note).
#
# _stabilization_qualified() SUPPRESSES a DSCR flag ONLY when the value is unambiguously framed
# as a stabilization/lease-up-timeline covenant figure. Detection-over-silence bias -- suppression
# is a false negative -- so it is kept TIGHT with the same guard structure as its two precedents:
#   * VETO first on any acquisition-governor marker on the line (STAB_GOV_MARKERS =
#     ACQ_GOV_MARKERS + PERDEAL_MARKERS + the arming-vocabulary alignment tokens, see below): a
#     genuine acquisition-governor declaration dressed up in stabilization language ("hard
#     acquisition governor ... DSCR floor 1.75x at stabilization") must STILL flag.
#   * VETO if the value is itself declared AS "the governor" -- the literal token within the same
#     direction-aware reach _refi_qualified uses -- so "DSCR 1.75x at stabilization (the
#     governor)" is never masked.
#   * VETO structurally on RE_GOV_DSCR_BOUND anywhere on the line (2026-08-15 REFUTE
#     remediation): a metric-then-bound-word pairing ("DSCR minimum", "DSCR hard floor") is a
#     governor DECLARATION shape regardless of word order, so no token list has to enumerate
#     orderings ("dscr minimum" vs "minimum dscr") -- the gap closes by construction. This can
#     never veto the legitimate covenant narration, because that shape puts the VALUE between
#     the metric and its bound-word ("clears the 1.75x floor") and the value's own decimal
#     point sits in RE_GOV_DSCR_BOUND's clause-ender exclusion class, so BOUND cannot match
#     across it. RE_GOV_DSCR_VALUE_BOUND is deliberately NOT a veto -- it matches the covenant
#     narration itself (it is what arms the line) and would kill the intended suppression.
#   * Then REQUIRE an explicit stabilization/lease-up marker in CLOSE PROXIMITY to the value:
#     a qualifier substring inside a window around val_start (the _portfolio_qualified bare-word
#     pattern, widened to 40 because the real line reads "1.75x floor only at Yr3+ stabilization"
#     -- 'stabiliz' ends 33 chars after the value). A stray "stabilized" far away on a long line
#     cannot be used to mask a governor drift elsewhere on that line.
# DSCR-only by design: the deal-covenant shape is a DSCR ratio conditioned on lease-up years;
# widening it to LTV would be new suppression surface with no observed false positive behind it.
# YEAR TOKENS (2026-08-15 REFUTE remediation): the yr1/yr2/yr3/"year N" qualifiers were bare
# substrings, so "year 2" matched INSIDE "year 2026" -- every dated doctrine line near a DSCR
# value qualified for suppression. They are now a digit-bounded regex: the year digit must be
# 1-3 and must NOT be followed by another digit ("yr3+" still matches; "year 2026" cannot).
STABILIZATION_QUALIFIERS = ("stabiliz", "lease-up", "lease up", "transition-year",
                            "transition year")
RE_STAB_YEAR = re.compile(r"(?<![a-z0-9])(?:yr\s?|year\s)[1-3](?!\d)")
# STABILIZATION-ONLY veto extension (2026-08-15 REFUTE remediation): every GOV_KEYWORDS token
# that can ARM is_gov must also be able to VETO this suppressor -- a veto vocabulary narrower
# than the arming vocabulary is a structural hole (a line armed SOLELY by "hard cap"/
# "self-imposed"/"disqualif" was suppressible here while carrying real drift). These tokens are
# deliberately NOT added to the shared ACQ_GOV_MARKERS: ratified refi doctrine treats a
# "self-imposed ... post-close" sizing cap as a legitimate refi figure (pinned by
# test_reverse_order_refi_suppression_unit), so widening the SHARED list would convert that
# visible-and-correct suppression into a false positive. The stabilization suppressor has no
# such ratified counter-case, so it takes the full arming vocabulary as veto. "governor" itself
# stays proximity-scoped (the veto below), and "dscr minimum" is carried both here and by the
# structural RE_GOV_DSCR_BOUND veto -- belt-and-suspenders on a Hard-Invariant-4 guard.
STAB_GOV_MARKERS = ACQ_GOV_MARKERS + ("dscr minimum", "hard cap", "hard ceiling",
                                      "self-imposed", "disqualif")

def _stabilization_qualified(low, val_start):
    """True when the DSCR value at index `val_start` (in already-lower-cased `low`) is
    unambiguously a deal-specific STABILIZATION-CONDITIONED covenant figure (a projected DSCR
    that only clears its lender floor at lease-up/stabilization) and the drift flag should be
    suppressed. TIGHT by design (suppression is a false negative): an acquisition-governor
    marker anywhere on the line, a metric+bound-word declaration pairing anywhere on the line
    (RE_GOV_DSCR_BOUND), or the value being declared AS "the governor" nearby, each veto
    suppression so a real acquisition-governor drift still flags."""
    if any(m in low for m in STAB_GOV_MARKERS):
        return False
    if RE_GOV_DSCR_BOUND.search(low) is not None:
        return False
    if "governor" in low[max(0, val_start - 25):val_start + 40]:
        return False
    window = low[max(0, val_start - 40):val_start + 40]
    return (any(q in window for q in STABILIZATION_QUALIFIERS)
            or RE_STAB_YEAR.search(window) is not None)

# --- Bug-fix/audit-changelog SCALING-MULTIPLIER qualifier (2026-08-22) -----------------------
# A changelog/audit-fix narrative describing a PAST DEFECT can state that a BUGGY CALCULATION
# inflated/overstated a computed metric by a MULTIPLIER -- e.g. deal-comparison/SKILL.md:153's
# v1.2 entry: "DSCR was tested at 40% LTV ... inflating computed DSCR ~1.6x and letting deals that
# would floor-flag ... score clean here; corrected to the LESSER-of-65%-LTV/1.25x-DSCR basis." That
# is describing how WRONG the buggy output was (a scaling factor on a CALCULATION RESULT), never a
# declared governor threshold -- but RE_DSCR_THRESH has no notion of "multiplier vs threshold":
# "dscr ~1.6x" (the second "DSCR" token, immediately followed by the approximation) reads
# identically to a declared "DSCR floor 1.6x" candidate, so it fell straight into the branch-2
# equality check and flagged "DSCR governor threshold 1.6x != canonical 1.25x" -- live on main,
# overridden 5x by 3 sessions across 2026-08-21/22 (hooks/_state/override-usage-log.jsonl,
# signature d491c6e47418) before this fix.
#
# This is a DIFFERENT false-positive shape from every existing qualifier above: _portfolio_qualified
# / _refi_qualified / _stabilization_qualified all suppress a value that IS a legitimate alternate
# METRIC (a portfolio-wide target, a refi-sizing input, a lease-up covenant) -- this line's "1.6" is
# not a metric at all, it is the MAGNITUDE OF A BUG. None of the three existing qualifiers'
# narrative shapes match it, so it needed its own suppressor rather than a reuse of any of them.
#
# The dense real-tree line is also why a WIDE proximity veto (the module's usual pattern, e.g.
# _governor_declared_nearby's +-28/40-char reach used by every sibling qualifier above) is UNSAFE
# here: the same changelog entry narrates TWO OTHER defects on the SAME line ("...score clean here"
# is 31 chars before "floor-flag", and the line separately carries "HARD FILTER"/"disqualif" for an
# unrelated defect #2) -- "floor" alone sits well inside any +-40ish reach, and ACQ_DECL_NEARBY /
# STAB_GOV_MARKERS both include bare "floor" and "hard filter". A generic nearby-token veto reused
# from the sibling qualifiers would misread "would floor-flag" (ORA's own Ruling-5 term of art for
# "gets flagged for breaching a floor", see FLOOR-FLAGGED just after) as a floor DECLARATION next to
# the value and refuse to suppress the very false positive this fix targets.
#
# _dscr_scaling_multiplier_spans() therefore does NOT use a proximity-window veto at all. Instead it
# relies on the extraction pattern itself being STRUCTURALLY exclusive of a real declaration, PLUS
# two independent gates added after round-1 independent review (eos-review-gate.py, claude-fable-5)
# found both a false negative and a tense-blindness gap in the first cut:
#   * REQUIRE the exact narrative shape "<scaling verb> ... computed/calculated/measured ... dscr
#     ... (~ | by [a factor of]) ... <value>x" (RE_DSCR_COMPUTED_SCALING, clause-bounded gaps so it
#     cannot reach across a clause boundary into an unrelated sentence).
#   * RIGHT-SIDE KEYWORD LOOKAHEAD (round-1 review Finding 1, false-negative class): the claim that
#     "a floor/ceiling/minimum/maximum keyword sits immediately adjacent to ITS value in every real
#     declaration" is only true for keyword-BEFORE-value forms (RE_DSCR_DECL). RE_DSCR_DECL_REV's
#     shape puts the keyword AFTER the value ("1.40x floor"), which the scaling regex's left-only
#     bound does not guard -- "bug inflating computed DSCR ~1.40x floor going forward" matched and
#     silenced a genuine value-then-keyword declaration (repro confirmed pre-fix; RE_GOV_DSCR_BOUND
#     cannot catch it either, because the value's own decimal point sits inside its clause-exclusion
#     gap class, same reasoning as the per-property-refi fix's decimal-free-gap precedent). The
#     trailing `(?!\s*(?:floor|ceiling|minimum|min|maximum|max)\b)` closes this: an explicitly
#     declared floor/ceiling immediately after the value is never suppressed, mirroring the
#     kw_after_spans exemption the bps-tier refi veto already carries (round-2 review W3: "an
#     explicitly-declared floor is a governor statement... must flag even inside a bps tier").
#   * CHANGELOG-CONTEXT REQUIREMENT (round-1 review Finding 2, tense-blindness class): the doctrine
#     above scopes this suppressor to a PAST-DEFECT changelog narrative, but the regex alone encodes
#     no notion of pastness -- "the model now deliberately scales computed DSCR by 1.4x before
#     comparison" (a present-tense multiplicative fudge -- a real drift MECHANISM, not a typo) and
#     "scoring still inflates computed DSCR ~1.6x; not yet corrected" (a live, uncorrected defect)
#     both matched and were silenced pre-fix. RE_CHANGELOG_CONTEXT requires an explicit fix/bug/
#     correction token ANYWHERE on the line -- the real false-positive line carries "fix", "Two
#     defects", "corrected" (three times) well past this bar, while a live-behavior or currently-
#     applied-multiplier line generally will not.
#   * STRUCTURAL VETO on RE_GOV_DSCR_BOUND anywhere on the line (same belt-and-suspenders precedent
#     as _stabilization_qualified): a genuine "dscr ... floor/minimum/min" pairing sharing the line
#     means a real declaration is present and every candidate on the line -- including the
#     multiplier value -- must stay fully visible. Verified against the real false-positive line:
#     its nearest "dscr"-to-"floor" gap is ~37 chars, outside RE_GOV_DSCR_BOUND's 24-char reach, so
#     this veto does not fire there (test_dscr_scaling_multiplier_changelog_stays_clean_unit pins
#     this margin) -- but a synthetic line that adds an explicit "DSCR floor 1.60x" alongside the
#     multiplier phrase DOES trip it, and both values flag
#     (test_dscr_scaling_multiplier_real_drift_still_flags_unit).
#   * "governor" proximity veto as a final belt-and-suspenders check, anchored to the VALUE'S OWN
#     SPAN [vs-25, ve+40] (not value-START-anchored like _refi_qualified/_stabilization_qualified's
#     [val_start-25, val_start+40] -- this window is therefore slightly wider on the after side, by
#     the value's own length; direction-safe, since a wider veto only means MORE detection) --
#     narrow enough that it cannot collide with "floor-flag" the way a bare-"floor" veto would.
#
# ACCEPTED RESIDUAL (round-1 review Finding 2, non-blocking): RE_CHANGELOG_CONTEXT is a lexical
# token check, not a negation-aware or topic-aware one, and both gaps were verified in round-2
# review rather than merely asserted:
#   * NEGATION-BLIND: "OPEN BUG (hard filter): scoring still inflates computed DSCR ~1.6x; not yet
#     corrected" carries both "bug" and "corrected" and is therefore still suppressed, even though
#     the defect is explicitly NOT YET fixed.
#   * TOPIC-BLIND: the token search is ANYWHERE on the line, not proximity-scoped to the value --
#     "per the hard filter, we fixed a typo in the README; separately, the model now deliberately
#     scales computed DSCR by 1.4x before comparison" is suppressed by the unrelated README-typo
#     "fixed", even though the DSCR multiplier clause itself describes a live, deliberately-applied
#     mechanism with no fix/correction language of its own.
# Round-2 review confirmed both are NOT cheaply closeable: proximity- or clause-scoping the token
# search un-suppresses the real target line itself (deal-comparison/SKILL.md:153's nearest fix/
# correct token sits ~200-300 chars from the "~1.6x" value, across a ';' clause boundary), and a
# negation gate is new suppression-logic surface with its own false-negative/false-positive risk on
# a Hard-Invariant-4 guard. Both residuals are the SAME underlying category-boundary issue: this
# gate can only ask "does the LINE mention a fix/bug/correction anywhere", not "is THIS VALUE the
# subject of one" -- closing that for real needs the gate re-scoped to a clause or sentence around
# the value, which is deferred as its own reviewed change rather than guessed at here. Out of
# proportion to the actual risk today: an armed line with a topically-unrelated fix/bug mention
# elsewhere is a narrow, dense-changelog-specific shape, and the failure direction (silent
# suppression of a value that was never a governor DECLARATION in the first place, only ever a
# computed-figure narration) is bounded by the fact that this suppressor's OWN extraction pattern
# already requires the narrow "verb...computed/calculated/measured...dscr...connective...value"
# shape -- a topically-unrelated fix mention widens WHEN it applies, never WHAT it applies to. Both
# residuals pinned deliberately by test_dscr_scaling_multiplier_accepted_residuals_unit rather than
# left latent; a future pass closing either should start from this comment.
_SCALING_VERBS = r"(?:inflat|overstat|understat|deflat|scal)\w*"
RE_DSCR_COMPUTED_SCALING = re.compile(
    r"\b" + _SCALING_VERBS + r"\b[^.;!?\n]{0,20}?\b(?:computed|calculated|measured)\b"
    r"[^.;!?\n]{0,15}?\bdscr\b\s*(?:~|by\s+(?:a\s+factor\s+of\s+)?)\s*([0-9]+\.[0-9]+)\s*[x×]"
    # RIGHT-SIDE KEYWORD LOOKAHEAD, widened after round-2 review: the original single-word-adjacent
    # form (?!\s*(?:floor|...)\b) missed a value-then-MODIFIER-then-keyword declaration ("~1.40x
    # hard floor", "~1.40x strict minimum") -- vocabulary the module treats as canonical elsewhere
    # (_is_gov_line's own docstring example is "DSCR hard floor 1.40x"; STAB_GOV_MARKERS carries
    # "hard cap"/"hard ceiling"). Allowing up to 2 intervening hyphen/space-joined modifier words
    # closes it; direction-safe per the module's own doctrine (a wider lookahead only BLOCKS
    # suppression, i.e. more detection, never less). Verified this does not over-block: "floor-flag"
    # (2 words after a suppressible value, on the real target line) is >2 words past any value in
    # that line's scaling-multiplier match, so it is unaffected; a value sitting within 2 words of a
    # literal "floor-flag" WOULD now flag -- loud, not silent, and never observed on the real tree.
    r"(?!\s*(?:\w+[-\s]+){0,2}(?:floor|ceiling|minimum|min|maximum|max)\b)",
    re.I)
# Any explicit fix/bug/correction token on the line -- the PAST-DEFECT narrative marker this
# suppressor is scoped to (see CHANGELOG-CONTEXT REQUIREMENT above). Word-bounded so it does not
# match inside an unrelated word ("suffix", "prefix", "fixture").
RE_CHANGELOG_CONTEXT = re.compile(r"\b(?:fix(?:ed|es|ing)?|correct\w*|bug\w*|defect\w*)\b", re.I)

def _dscr_scaling_multiplier_spans(low):
    """Digit-group spans of DSCR values that are approximate INFLATION/SCALING MULTIPLIERS on a
    COMPUTED figure in a bug-fix changelog narrative ("inflating computed DSCR ~1.6x") -- the
    magnitude of a PAST defect, not a declared governor threshold. Empty (no suppression) whenever
    the line also carries a structural dscr+floor/min pairing (RE_GOV_DSCR_BOUND) -- a real
    declaration sharing the line must stay fully visible, so this suppressor defers to that veto for
    the WHOLE line rather than per-value, matching _stabilization_qualified's structural-veto
    precedent -- or whenever the line carries no fix/bug/correction context token (RE_CHANGELOG_
    CONTEXT), which would mean a live-behavior or presently-applied multiplier is being described,
    not a past, corrected defect."""
    if RE_GOV_DSCR_BOUND.search(low) is not None:
        return []
    if RE_CHANGELOG_CONTEXT.search(low) is None:
        return []
    spans = []
    for mm in RE_DSCR_COMPUTED_SCALING.finditer(low):
        vs, ve = mm.span(1)
        if "governor" in low[max(0, vs - 25):ve + 40]:
            continue
        spans.append((vs, ve))
    return spans

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
# DSCR-TIER BUCKET LABEL (2026-08-22 FP fix; session 438b62fb, human-authorized override). A
# refi-rate adjustment tier is sometimes named with a hyphenated descriptor glued directly onto its
# DSCR threshold -- "stabilized-multi-tenant-≥1.40x adjustments are unchanged in magnitude"
# (acquisition-underwriting SKILL.md v4.13, mirroring the sibling "+25 bp sub-$2M/single-tenant"
# tier right beside it). The label IS the value's subject (which bucket a property falls into), not
# a DSCR floor/governor restatement -- but RE_DSCR_DECL's bare "[≥≤]...x" match has no
# concept of subject, so it read the bucket's threshold as a governor declaration. The intended
# suppressors (_refi_qualified / _stabilization_qualified) recognize this shape via "stabiliz" but
# their veto check is a WHOLE-LINE "any(m in low ...)" scan (STAB_GOV_MARKERS / ACQ_GOV_MARKERS),
# so an unrelated "per-property" mention elsewhere in the same dense paragraph (the correct,
# ratified dual-governor restatement in the line's OWN closing sentence) vetoed the suppression by
# accident.
# Structurally distinct from every governor-DECLARATION shape in this module: a floor/ceiling/
# governor restatement is always SPACE-separated from its keyword ("DSCR floor 1.25x", "1.25x DSCR
# floor"); only a rate-tier bucket NAME hyphen-glues straight into the comparator with no space
# ("label-word-≥1.40x"). That is the metric guard here, in place of a keyword/proximity test.
# VETO-tier (added to dscr_veto alongside the bps-tier band, consumed by the SAME check at the DSCR
# equality call site): _governor_declared_nearby is PROXIMITY-scoped (VETO_BEFORE/VETO_AFTER), not
# whole-line, so a real drift dressed in this shape ("the acquisition governor is
# stabilized-multi-tenant-≥1.40x") still flags -- pinned by
# test_dscr_rate_tier_bucket_label_veto_when_declared_as_governor_unit. Gated on a refi context
# (REFI_TOKENS, same gate as the bps tier) so the shape is only trusted where a rate-tier bucket
# plausibly appears.
RE_DSCR_TIER_LABEL = re.compile(
    r"[a-z]+(?:-[a-z0-9$]+){1,5}-[≥≤<>]=?\s*([0-9]+\.[0-9]+)\s*[x×]", re.I)
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

def _line_reaffirms_ratified_ltv_pair(low):
    """True when the line contains the tight, correctly-paired ratified restatement ('per-property
    LTV 65% / portfolio-aggregate LTV 40%') ANYWHERE -- not necessarily adjacent to the value being
    considered for suppression. See the LINE-WIDE reaffirmation comment at its _flag_ltv call site
    for why this is needed on top of the local pairing spans above (2026-08-22 FP fix). Delegates to
    _perprop_portfolio_paired_veto_spans (same COMPANION-ANCHORED regex, same canonical-40
    requirement) rather than re-filtering RE_PERPROP_PORTFOLIO_PAIR itself, so the two can never
    drift apart (independent-review non-blocking finding, 2026-08-22). Implicitly VALUE-LOCKED by
    its caller (only invoked when val == 65)."""
    return bool(_perprop_portfolio_paired_veto_spans(low))

# AGGREGATE/PORTFOLIO clause veto for _line_reaffirms_ratified_ltv_pair (independent review
# finding, 2026-08-22, session 438b62fb -- see the veto's call site in _flag_ltv for the concrete
# masked-drift example). Deliberately CLAUSE-BOUNDED rather than a fixed-width window like
# _governor_declared_nearby: there is no real-tree margin data to tune a window against here, and
# widening a VETO only ever adds detection (never risks masking a drift), so the safe direction is
# the wider, whole-clause reach -- bounded by the same clause-ender convention as
# _nonltv_subject_owns (RE_CLAUSE_END) so it cannot leap into an unrelated clause elsewhere in a
# long paragraph.
RE_LTV_AGGREGATE_SUBJECT = re.compile(r"\baggregate\b|\bportfolio\b", re.I)

def _aggregate_ltv_declared_in_clause(low, vs):
    """True when the CLAUSE containing the value at index `vs` itself names 'aggregate' or
    'portfolio' -- meaning the value is being asserted AS (or in the same breath as) the
    portfolio-AGGREGATE ceiling, not the per-property one, even though the line elsewhere carries
    the correct ratified pairing. Whole-clause, not proximity-windowed (see module comment above)."""
    lo = 0
    for cm in RE_CLAUSE_END.finditer(low[:vs]):
        lo = cm.end()
    hi = len(low)
    m = RE_CLAUSE_END.search(low, vs)
    if m:
        hi = m.start()
    return RE_LTV_AGGREGATE_SUBJECT.search(low, lo, hi) is not None

# --- Standalone per-property refi-sizing ceiling (KNOWN GAP 2, closed) -----------------------
# The pairing suppressor above requires the portfolio-aggregate 40% companion on the SAME LINE.
# Doctrine also states the two governors on SEPARATE bullets (acquisition-buy-box-v1.md:31 states
# only "per-property refi sizing ... <= 65%"; the aggregate 40% companion is a separate bullet two
# lines below, :33). That standalone line escapes every existing suppressor: the literal "LTV
# ceiling" token arms is_gov (correctly -- it usually IS the acquisition/aggregate governor label),
# so _refi_qualified's unconditional veto on "ltv ceiling" (in ACQ_GOV_MARKERS) refuses to treat it
# as a refi-market figure; the pairing suppressor above requires the missing companion; and the
# refi-construct member suppressors (_refi_member_value_spans) require a same-line "LESSER of ...
# DSCR" / "refi to N% LTV" / "N% LTV refi-sizing" construct, none of which is present in a bare
# "(per-property refi sizing): <= 65%" bullet. This was KNOWN GAP 2 in an earlier version of this
# module's comments: "Closing it requires widening LTV SUPPRESSION -- a false-negative risk on Hard
# Invariant 4 that belongs in its own reviewed change." This is that change.
#
# Kept to the SAME safety pattern as every suppressor in this module (detection over silence):
#   * VALUE-LOCKED to the ratified 65 (CANON_LTV_PERPROPERTY) -- a drifted per-property figure
#     (any value other than 65) never matches, so it is untouched by this check and still flags
#     through the normal passes below. This is the same guarantee test_perprop_member_value_
#     locked_to_ratified_65_unit already relies on for the pairing suppressor, and it is why a
#     value-locked check is safe where the rejected "blanket per-property veto span" (setup-audit
#     note C4, see test_perproperty_non_ratified_ltv_still_flags_unit) was not: that alternative
#     would have silenced a REAL per-property drift regardless of value.
#   * FRAME-GATED on the ratified wording: "per-propert(y/ies)" and "refi ... siz(ing)" (either
#     order, percent/digit-free gap so an intervening drift value breaks the match, matching the
#     _GAP convention used by every refi-construct regex above) -- the literal phrasing this
#     governor is declared with everywhere it appears (SKILL.md "per-property refi-sizing",
#     buy-box-v1.md "per-property refi sizing"). A bare "per-property ... 65% ceiling" with no
#     refi/sizing framing does NOT match and stays fully checked (test_perdeal_perproperty_drift_
#     still_flags_unit's "Hard filter: per-property LTV ceiling 65%." has neither token).
#   * VALUE-ADJACENT (round-1 independent review finding, 2026-08-21): the frame match must END
#     within PERPROPERTY_REFI_FRAME_REACH chars immediately BEFORE the suppressed value -- unlike
#     the earlier revision of this check, a line-wide "does the frame appear ANYWHERE on the line"
#     test is NOT safe here, because every OTHER suppressor in this module is span/proximity-scoped
#     to the value it suppresses (_refi_member_value_spans, the pairing veto, the correction spans)
#     and this is the module's ratified doctrine wording ALWAYS precedes the value it qualifies
#     ("(per-property refi sizing): <= 65%", "per-property refi-sizing ceiling = LESSER of 65%
#     LTV") -- a line-wide test let a genuinely drifted AGGREGATE value slip through whenever the
#     ratified per-property phrase happened to sit ANYWHERE ELSE on the same line, even after the
#     value or across a clause boundary the frame's own gap regex does not stop at:
#       "Portfolio LTV ceiling raised to 65% given our per-property refi sizing convention."
#       "Aggregate LTV ceiling 65%; per-property refi sizing unchanged."
#     Both are AGGREGATE-governor drift narrations (the "raised to"/"aggregate" framing is the
#     acquisition/portfolio ceiling, not the per-property one) with the ratified phrase sitting
#     AFTER the value -- pinned clean-must-still-flag by
#     test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit. Requiring
#     the frame to END just before the value closes this: both masked examples have the frame
#     AFTER the value, so "ends before, within reach" never matches them, while the two ratified
#     real-tree lines (buy-box-v1.md:31 gap ~12 chars, its hyphenated SKILL.md-style spelling gap
#     ~9 chars) stay comfortably inside the reach.
#   * VETOED by the existing _governor_declared_nearby check: a bare "governor" token or an
#     ACQ_DECL_NEARBY token (acquisition/buy-box/hard filter/hard screen/hard ceiling/hard cap/
#     floor) near the value means it is being declared AS the acquisition/aggregate ceiling despite
#     the refi-sizing wording -- a mislabeling, not numeric drift, and it must still flag.
#     KNOWN RESIDUAL (round-1 independent review, non-blocking): this veto's window (VETO_BEFORE=28
#     chars) is narrower than the frame-adjacency reach below, so a governor/acquisition token that
#     sits BEFORE the frame -- outside the veto's reach but still on the line, e.g. "The acquisition
#     governor: per-property refi sizing LTV ceiling 65%." -- is not caught by either guard. Left
#     as a documented residual rather than widening VETO_BEFORE (which is independently tuned
#     against real per-property/refi prose margins -- see its own comment); the value-lock still
#     means only the literal ratified 65 can ever be affected, never an actual drifted figure.
_PERPROPERTY_REFI_FRAME_GAP = r"(?:[^\n%0-9]|" + re.escape(CANON_LTV_PERPROPERTY) + r")"
RE_PERPROPERTY_REFI_FRAME = re.compile(
    r"per[\s\-]?propert(?:y|ies)\b" + _PERPROPERTY_REFI_FRAME_GAP + r"{0,40}?refi[\s\-]?siz"
    r"|refi[\s\-]?siz" + _PERPROPERTY_REFI_FRAME_GAP + r"{0,40}?per[\s\-]?propert(?:y|ies)\b",
    re.I)
# Reach for the value-adjacency test above. Comfortably covers both real-tree gaps (~12 and ~9
# chars) with margin for reasonable phrasing variance, while staying far short of the masked
# examples' frame-after-value placement (which "ends before vs" excludes regardless of reach size).
PERPROPERTY_REFI_FRAME_REACH = 24

def _perproperty_refi_frame_immediately_before(low, vs):
    """True when a RE_PERPROPERTY_REFI_FRAME match ends within PERPROPERTY_REFI_FRAME_REACH chars
    before index `vs` -- i.e. the ratified per-property refi-sizing phrase is the thing actually
    qualifying THIS value, not merely present somewhere else on the line (see the value-adjacency
    note above)."""
    lo = vs - PERPROPERTY_REFI_FRAME_REACH
    for fm in RE_PERPROPERTY_REFI_FRAME.finditer(low):
        if lo <= fm.end() <= vs:
            return True
    return False

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
        for mm in RE_DSCR_TIER_LABEL.finditer(low):  # rate-tier bucket label, see RE_DSCR_TIER_LABEL
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
# NON-LTV PERCENT SUBJECTS (2026-08-12). A veto, NOT a positive gate -- that distinction is the
# whole lesson of this fix. The first attempt REQUIRED an LTV-side governor marker near the value;
# it closed the false positives but silenced five realistic drift declarations that had flagged
# since 2026-07-08, because it reused _governor_declared_nearby -- a helper whose short before-reach
# and plural/canonical-phrase exemptions are tuned to err toward DETECTION when vetoing, and
# therefore err toward SILENCE when used as a requirement. Caught in independent review.
#
# Vetoing on the subject instead keeps the module's stated bias (suppression tight, detection over
# silence): every confirmed false positive names an explicit non-LTV subject immediately before the
# percentage ("vacancy 10% maximum", "TI cap 12% maximum", "site coverage 45% maximum"), while a
# real governor declaration never does. Bare "cap" is deliberately ABSENT from the list: "LTV cap
# 65%" is ceiling-declaration phrasing, so vetoing on "cap" would suppress it. (It happens not to be
# detected today for an unrelated reason -- no extractor accepts bare "cap" as a ceiling word -- but
# the veto list must not be the thing standing in the way if that is ever closed.)
# Bare "coverage" is deliberately ABSENT: DSCR *is* the debt-service-COVERAGE ratio, so "coverage"
# is the one candidate subject that routinely appears in genuine governor prose right where a
# paired LTV ceiling is declared ("Governor: coverage 1.30x; 65% ceiling."). Listing it silenced
# real declarations. Only the two-word "site coverage" is a non-LTV subject, and it alone is what
# closes the site-coverage false positive.
NON_LTV_PCT_SUBJECTS = ("vacancy", "occupancy", "tenant improvement", "ti", "parking",
                        "site coverage", "exit cap", "cap rate", "downtime",
                        "cure", "credit loss", "concession")
RE_NON_LTV_SUBJECT = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in NON_LTV_PCT_SUBJECTS) + r")\b", re.I)
# How far back to look for the subject that owns the percentage. Deliberately SHORT: the subject of
# a percentage sits immediately before it, so a distant mention elsewhere on the line ("vacancy 5%
# assumed; LTV ceiling 65%") must not suppress a real ceiling.
NON_LTV_SUBJECT_REACH = 24
# A clause ender, EXCLUDING the '.' of a decimal. Raw rfind(".") treated "2.5x" as a sentence
# boundary and truncated the veto window, reopening the very false positives this closes -- and
# DSCR-adjacent prose is dense with decimal multiples. The module already reasons about this
# distinction in the GAP-1 arming comment.
RE_CLAUSE_END = re.compile(r"[;!?]|\.(?!\d)")
RE_LTV_BOUND_WORD = re.compile(r"\b(?:ceiling|maximum|max)\b", re.I)
# ACCEPTED RESIDUALS, recorded so they are decisions and not rediscoveries:
#   * a listed subject sitting directly before a genuine explicit ceiling still suppresses it
#     ("LTV ceiling net of TI allowances: 65%."). Inherent to any subject veto; phrasing is rare,
#     and the alternative -- requiring positive evidence -- is the mistake this fix reverted.
#   * terse site-coverage prose that drops the "site" ("coverage 45% maximum") now flags. That is
#     the deliberate cost of keeping bare "coverage" off the list: detection over silence.
#   * a DOUBLED bound word around the subject's own figure ("vacancy ceiling 10% maximum") flags:
#     the first bound word satisfies the between-test. Redundant phrasing, no observed instance.
#   * an abbreviation or ellipsis between subject and value ("vacancy (i.e. stabilized) 10%
#     maximum") truncates the lookback and lets the figure through. Both residuals are FP-direction
#     only -- window truncation can never manufacture silence, so neither can hide real drift.


def _nonltv_subject_owns(low, vs):
    """True when a non-LTV subject noun owns the percentage at index `vs`, meaning the figure
    belongs to that subject rather than to an LTV ceiling.

    CLAUSE-BOUNDED, matching this module's house convention everywhere else: the reach never
    crosses a clause ender, so a previous clause's subject cannot suppress this clause's ceiling
    ("Governor: assume 5% vacancy; leverage 55% maximum." must still flag).

    Whole-line finditer + span overlap rather than a substring slice: slicing manufactures a word
    boundary at the cut, so a token severed mid-word can match by pure offset coincidence (a slice
    landing inside "multi" leaves a bare "ti"). That is the Hole-4 defect already documented in
    _governor_declared_nearby's docstring; this follows the same precedent."""
    lo = max(0, vs - NON_LTV_SUBJECT_REACH)
    clause = -1
    for cm in RE_CLAUSE_END.finditer(low[:vs]):
        clause = cm.start()
    if clause >= lo:
        lo = clause + 1
    if lo >= vs:
        return False
    for mm in RE_NON_LTV_SUBJECT.finditer(low):
        # The subject must END inside the window. An earlier cut accepted any subject merely
        # OVERLAPPING it, which let a subject sit up to a full reach before the value with whole
        # phrases in between -- wider than this helper's own stated theory, and it silenced a
        # baseline-flagged line.
        if not lo <= mm.end() <= vs:
            continue
        # ...and a bound word BETWEEN the subject and the value means the value binds to the
        # ceiling, not to the subject: "at 95% occupancy the ceiling is 65% maximum" declares a
        # ceiling. In every confirmed false positive the bound word sits after the value
        # ("vacancy 10% maximum") or before the subject ("maximum TI 12%"), never between.
        if RE_LTV_BOUND_WORD.search(low[mm.end():vs]):
            continue
        # ...and an intervening PERCENT disproves ownership outright: the subject demonstrably owns
        # that earlier figure, not this one ("Governor: vacancy 5% assumed and 65% maximum." -- the
        # vacancy is the 5%, and the 65% ceiling must still flag). Without this the veto leapfrogs a
        # real figure, which is the same failure the refi machinery's percent-free gaps exist to
        # prevent. Percent-based deliberately, NOT digit-based: "at 2.5x turnover" carries digits
        # but no percent, and a digit guard would reopen the decimal false positives above.
        if "%" in low[mm.end():vs]:
            continue
        return True
    return False

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

def _governor_declared_nearby(low, vs, ve=None, exclude=()):
    """True when a bare singular 'governor' token -- or an acquisition-declaration token
    (ACQ_DECL_NEARBY) -- OVERLAPS the DIRECTION-AWARE interval [vs-VETO_BEFORE, ve+VETO_AFTER]
    around the value: the value may be declared AS the governor, so a VETO-tier refi member must
    NOT be suppressed. Whole-line search + overlap test (review Hole 4: the prior finditer
    end-bound / substring slice silently shrank the effective reach and biased toward silence).
    Exemptions (both err toward detection elsewhere): PLURAL 'governors' (names multiple governors),
    and a 'governor' inside the canonical phrase '1.25x DSCR governor' (binds to the canonical DSCR
    on its left, e.g. 'the 1.25x DSCR governor at 65% LTV').

    `exclude` (2026-08-23, floor-result round-2 review): ACQ_DECL_NEARBY tokens to SKIP -- for a
    caller whose own construct anchor unavoidably contains one of the tokens (the floor-result
    narration's canonical anchor IS '1.25x floor', so 'floor'/'dscr floor' would veto every
    genuine match unconditionally). Only the named tokens are skipped; every other declaration
    token and the bare-'governor' scan stay fully armed. Default () = existing call sites are
    byte-for-byte unchanged."""
    if ve is None:
        ve = vs
    lo, hi = vs - VETO_BEFORE, ve + VETO_AFTER
    # acquisition-declaration substrings: any occurrence overlapping the interval vetoes.
    for t in ACQ_DECL_NEARBY:
        if t in exclude:
            continue
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

# --- Eval-harness FLOOR-RESULT narration (2026-08-23 FP fix) ---------------------------------
# An auto-generated acquisition-underwriting eval-harness run log narrates ONE deal's floor-check
# RESULT, quoting the deal's ACHIEVED DSCR against the canonical floor at the ratified 65%-LTV
# per-property refi-sizing basis -- live triggers: ora-skills/acquisition-underwriting-eval-harness/
# runs/2026-08-23T171623Z_scheduled-poll.json:399 ("DSCR floor PASSES (1.42x vs 1.25x floor at
# 65%-LTV sizing, LTV binds)") and :195 ("DSCR floor PASS (1.48x vs 1.25x floor at 65%-LTV refi
# sizing, LTV binds)"). BOTH figures are doctrine-correct: 1.42x/1.48x is the deal's computed DSCR
# (an underwriting RESULT), and 65% is the ratified PER-PROPERTY refi-sizing ceiling
# (CANON_LTV_PERPROPERTY), not a drift on the 40% aggregate. Yet both flag:
#   * DSCR side: RE_DSCR_THRESH binds the achieved value ("DSCR floor PASSES (1.42x"), and no
#     suppressor applies -- no refi token (:399), no bps tier, no stabilization/portfolio frame.
#   * LTV side (:399): NONE of the refi-construct regexes match -- RE_REFI_SIZING_NAMED needs a
#     literal "refi" before "siz" ("65%-LTV sizing" has none), RE_CANON_DSCR_PAIRED_LTV needs
#     "1.25x DSCR" (this phrasing writes "1.25x floor"), LESSER-of/refi-to are absent.
#   * LTV side (:195): RE_REFI_SIZING_NAMED DOES match ("65%-LTV refi sizing"), but the veto-tier
#     check _governor_declared_nearby vetoes suppression anyway: ACQ_DECL_NEARBY contains "floor",
#     and this phrasing NECESSARILY places "1.25x floor" a few chars before the 65 -- the shared
#     veto vocabulary structurally defeats suppression for this construct, so a construct-specific
#     suppressor (with its own, narrower veto) is required rather than a new member regex alone.
# Suppression is kept TIGHT with the module's usual guards, plus two construct-specific ones:
#   * CANONICAL-ANCHORED: both regexes require the literal plain canonical 1.25 restated as the
#     floor ("vs 1.25x floor" / "1.25x floor at"). A drifted floor restatement ("1.42x vs 1.40x
#     floor") matches nothing, so the 1.40 AND the 1.42 both stay fully visible.
#   * RESULT-VERB GATED: a pass/clear/breach/fail/miss token must sit adjacent to the construct
#     (whole-line finditer + span overlap, per the Hole-4 slicing precedent) -- the harness always
#     narrates a floor-check VERDICT ("PASSES (", "clears ("), while a drift DECLARATION written in
#     the same word order ("DSCR governor: 1.42x vs 1.25x floor previously") carries none.
#   * DECL-SHAPE VETO (DSCR, at the call site): a value whose span is ALSO bound by a
#     declaration-shaped extractor (RE_DSCR_DECL / FROMTO / DECL_REV / PIVOT_DECOY / KW_AFTER) is
#     being DECLARED, not narrated -- "DSCR floor raised to 1.42x vs 1.25x floor -- passes" still
#     flags via RE_DSCR_DECL's "raised to 1.42x" binding.
#   * VALUE-LOCKED (LTV): only the ratified 65 (CANON_LTV_PERPROPERTY) is ever suppressed -- a
#     drifted sizing basis ("at 80%-LTV sizing") never matches the lock and still flags, same
#     guarantee as the per-property pairing/standalone-frame suppressors above.
#   * DECLARATION-TOKEN VETO: the full _governor_declared_nearby check runs on the WHOLE construct
#     span (member spans are strictly inside it, so this is the wider window -- see the veto-scope
#     comment in _floor_result_spans), excluding ONLY the two tokens that are part of this
#     construct's own canonical anchor
#     ("floor", "dscr floor" -- see the :195 analysis above for why those would veto every genuine
#     match unconditionally). Every OTHER declaration token stays live: "...at 65%-LTV sizing, the
#     hard ceiling" / "hard cap" / "acquisition"/"buy-box" phrasing near either value still flags
#     (round-2 independent review, 2026-08-23: the first cut dropped the WHOLE token list and
#     silenced exactly those shapes -- a real false-negative regression, fixed by the exclusion
#     being a two-token surgical trim instead).
#   * KEYWORD-DIRECT-BIND VETO (DSCR; round-2 review 2026-08-23, restructured round-3): a
#     floor-keyword that reaches the achieved value with NO verdict verb between them is BINDING
#     the value -- a DECLARATION ("floor is 1.42x", "floor set at 1.42x", "floor stands at
#     1.42x", "floor = 1.42x", a table cell "floor | 1.42x") -- the I-2 canonical-decoy class,
#     which none of the extractor-shaped spans catch (RE_DSCR_DECL's comparator/pivot set has no
#     copula or verb-phrase binders). Round 2 enumerated single-token binders (is|was|of|at|=|:|
#     '|') and round-3 review found the structural hole in enumerating at all: any VERB-PHRASE
#     binder ("set at", "stands at", "pegged at", "rises to") falls outside any finite list.
#     INVERTED instead: when the NEAREST floor-keyword before the value sits in the SAME clause
#     (a clause ender between them means the keyword belongs to a previous clause and binds
#     nothing here), suppression REQUIRES a RE_FLOOR_RESULT_VERB match wholly between keyword-end
#     and value-start. NO distance cap (round-4: a cap creates a suppression band just past it --
#     "floor under the revised doctrine is 1.42x" -- and distance never protects a genuine
#     narration; the verb-between test and clause boundary do). The genuine harness
#     construct ALWAYS has the verdict verb exactly there ("floor PASSES (1.42x", "floor PASS
#     (1.48x"), so no real narration is touched; every binder -- known or novel -- fails the
#     requirement and flags. Also from round 2: bare "clear" dropped from RE_FLOOR_RESULT_VERB
#     (harness verdicts write "clears"/"cleared"; bare "clear" is clear-height prose -- "28 ft
#     clear" -- and was an arming vector for the copula shapes; bare "pass"/"fail" stay, the
#     harness writes "PASS ("/"FAIL" verbatim).
#   * AGGREGATE-CLAUSE VETO (LTV): reuses _aggregate_ltv_declared_in_clause, so a 65 asserted in
#     the same clause as an "aggregate"/"portfolio" subject (a drift of the 40% governor TO 65,
#     the most plausible wrong value) still flags.
#   * SPAN-SCOPED + WEAKEST-PASS-ONLY: only the construct's own member digits are suppressed, and
#     only in the passes that actually bind them (the dscr-anchored primary pass and the LTV
#     bare-proximity fallback); comparator/anchor/FROMTO/reverse-order passes stay fully armed, and
#     the 1.75 sentinel (branch 1) is untouched -- an achieved DSCR of exactly 1.75 in a future
#     harness log would flag as a visible FP rather than widening suppression of the most-guarded
#     value (deliberate: detection over silence).
RE_FLOOR_RESULT_VERB = re.compile(
    r"\b(?:pass(?:es|ed)?|clear(?:s|ed)|breach(?:es|ed)?|fail(?:s|ed)?|miss(?:es|ed)?)\b", re.I)
# Achieved-vs-canonical-floor: "<achieved>x vs 1.25x [dscr ]floor"; capture (1) the achieved value.
# Same lookbehind class as RE_DSCR_CANON_PLAIN (no version/tilde/decimal-fragment binding).
RE_DSCR_VS_CANON_FLOOR = re.compile(
    r"(?<![vV~0-9.])([0-9]+\.[0-9]+)\s*[x×]\s*vs\.?\s*" + re.escape(CANON_DSCR)
    + r"\s*[x×][\s\-]*(?:dscr\s+)?floor\b", re.I)
# Sizing-basis LTV: "1.25x [dscr ]floor at <N>%[- ]LTV [refi ]siz(ing)"; capture (1) N. The literal
# "at" + the "siz" tail are the sizing-context anchors -- "1.25x floor and 65% LTV ceiling" (a
# conjunction, plausibly declaring a ceiling) matches neither and stays fully checked.
RE_CANON_FLOOR_AT_LTV_SIZING = re.compile(
    re.escape(CANON_DSCR) + r"\s*[x×][\s\-]*(?:dscr\s+)?floor\s+at\s+"
    r"([0-9]{1,3})\s*%[\s\-]*ltv\b[\s\-]*(?:refi[\s\-]?)?siz", re.I)
# Verb-adjacency reaches. BEFORE spans the harness's "PASSES (1.42x vs " lead-in (~10 chars between
# verb end and construct start, with margin); AFTER catches a trailing verdict ("...floor clears").
# Deliberately short so a verb elsewhere on a long line cannot arm suppression.
FLOOR_RESULT_VERB_BEFORE = 24
FLOOR_RESULT_VERB_AFTER = 12
# The two ACQ_DECL_NEARBY tokens that are part of this construct's OWN canonical anchor ("1.25x
# floor" / "1.25x dscr floor") and therefore cannot serve as veto evidence here -- and ONLY those
# two. "minimum dscr"/"min dscr" and every non-floor token ("hard ceiling", "hard cap",
# "acquisition", "buy box"/"buy-box", "hard filter", "hard screen") stay live as vetoes.
FLOOR_RESULT_VETO_EXCLUDE = ("floor", "dscr floor")
# KEYWORD-DIRECT-BIND veto (see the block comment above). The keyword set mirrors RE_DSCR_DECL's
# bound-words, plus the plural/verb form "floors" ("DSCR floors at 1.42x" is equally a
# declaration; round-4 review) -- the regex's only consumer is this veto, so widening it is
# detection-positive by construction. NO distance cap (round-4 review): an earlier revision
# bounded the keyword's reach at 24 chars, and any cap creates a suppression band just past it
# ("DSCR floor under the revised doctrine is 1.42x vs 1.25x floor -- passes" put 26 chars of
# qualifier between keyword and value and slipped through). Distance never protects a genuine
# narration -- the verb-between test and the clause boundary do -- so the veto reaches the whole
# clause. The check itself lives in _floor_kw_binds_value_directly(), which is what the DSCR
# suppression condition consults.
RE_DSCR_FLOOR_KW = re.compile(r"\b(?:floors?|minimum|min|maximum|max|ceiling)\b", re.I)

def _floor_kw_binds_value_directly(low, vs):
    """True when the NEAREST floor-keyword ending at or before index `vs` (the candidate value's
    start) sits in the SAME clause and has NO verdict verb (RE_FLOOR_RESULT_VERB) wholly between
    its end and `vs` -- i.e. the keyword is binding the value directly ("floor is 1.42x", "floor
    set at 1.42x", "floor under the revised doctrine is 1.42x"): a DECLARATION, so floor-result
    suppression must not apply. Returns False when there is no keyword before the value, the
    keyword is in a previous clause ("...8.0% floor; DSCR 1.42x..." -- the clause ender breaks
    the binding, matching the module's clause-bounded house convention), or the verdict verb sits
    between keyword and value ("floor PASSES (1.42x" -- the genuine harness narration). No
    distance cap, deliberately -- see the round-4 note above."""
    kw_end = None
    for km in RE_DSCR_FLOOR_KW.finditer(low):
        e = km.end()
        if e <= vs and (kw_end is None or e > kw_end):
            kw_end = e
    if kw_end is None:
        return False
    if RE_CLAUSE_END.search(low, kw_end, vs):
        return False
    for vm in RE_FLOOR_RESULT_VERB.finditer(low):
        if kw_end <= vm.start() and vm.end() <= vs:
            return False
    return True

def _floor_result_spans(low):
    """Return (dscr_spans, ltv_spans): the exact digit-group spans of a floor-RESULT narration's
    member values -- the achieved DSCR compared against the canonical floor, and the ratified
    65%-LTV sizing basis it was computed at. Every guard described in the block comment above is
    applied here except the DSCR decl-shape and binder-decl vetoes, which live at the call site
    (the former needs the extractor spans, the latter the candidate value's exact start)."""
    dscr_spans, ltv_spans = [], []
    verb_spans = [vm.span() for vm in RE_FLOOR_RESULT_VERB.finditer(low)]
    def _verb_near(s, e):
        return any(_spans_overlap(a, b, s - FLOOR_RESULT_VERB_BEFORE,
                                  e + FLOOR_RESULT_VERB_AFTER) for (a, b) in verb_spans)
    # The declaration-token veto runs on the WHOLE construct span, not just the member's digits:
    # the construct is ONE narration, so a declaration token hung off either end ("...at 65%-LTV
    # sizing, the hard ceiling") taints all of it. The member span is strictly inside the match
    # span, so the whole-match window strictly CONTAINS the member window -- widening the veto is
    # detection-positive only. It also matters concretely: on the "hard ceiling"-tail shapes the
    # token sits ~40 chars past the ACHIEVED value (just outside a member-scoped VETO_AFTER reach)
    # but well within reach of the construct's end, and HEAD flagged the DSCR value on those lines
    # -- member-scoping would have silently kept that half of the regression (round-2 review).
    for mm in RE_DSCR_VS_CANON_FLOOR.finditer(low):
        ms, me = mm.span()
        if not _verb_near(ms, me):
            continue
        if _governor_declared_nearby(low, ms, me, exclude=FLOOR_RESULT_VETO_EXCLUDE):
            continue
        dscr_spans.append(mm.span(1))
    for mm in RE_CANON_FLOOR_AT_LTV_SIZING.finditer(low):
        if mm.group(1) != CANON_LTV_PERPROPERTY:    # VALUE-LOCK: only the ratified 65, ever
            continue
        ms, me = mm.span()
        if not _verb_near(ms, me):
            continue
        if _governor_declared_nearby(low, ms, me, exclude=FLOOR_RESULT_VETO_EXCLUDE):
            continue
        if _aggregate_ltv_declared_in_clause(low, mm.start(1)):
            continue
        ltv_spans.append(mm.span(1))
    return dscr_spans, ltv_spans

def scan_line(raw):
    """Return list of (reason) drift findings for one line."""
    out = []
    low = raw.lower()
    # Audit-note suppressors are METRIC-SPECIFIC and SPAN-SCOPED (I-4 + M-2): a "corrected ... from
    # <X> to/→ canonical" note suppresses ONLY the corrected-away old value (the span), never the
    # whole branch -- so a live drift sharing the line still flags. DSCR and LTV are independent.
    dscr_corr_spans = [mm.span() for mm in RE_DSCR_CORRECTION.finditer(low)]
    # Tilde-hedged changelog narration (2026-08-21, directional fix 2026-08-22) -- see
    # _tilde_hedge_suppressed_spans' own docstring and the block comment above RE_DSCR_TILDE_HEDGE
    # for why this must be per-span and directional, not a whole-line "corrected" substring test.
    dscr_tilde_hedge_spans = _tilde_hedge_suppressed_spans(low)
    # Probe self-description ("...the 1.75 regression sentinel") -- span-scoped exactly like the
    # correction notes above, so only the quoted sentinel token is skipped, never the branch.
    sentinel_prose_spans = [mm.span() for mm in RE_SENTINEL_PROSE.finditer(low)]
    ltv_corr_spans = [mm.span() for mm in RE_LTV_CORRECTION.finditer(low)]
    is_gov = _is_gov_line(low)
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
    # Bug-fix/audit-changelog SCALING-MULTIPLIER spans (2026-08-22): DSCR values that are an
    # approximate inflation/scaling factor on a COMPUTED figure in a changelog narrative
    # ("inflating computed DSCR ~1.6x"), not a declared governor threshold. See
    # _dscr_scaling_multiplier_spans for why this cannot reuse the sibling qualifiers' proximity
    # veto (a bare "floor" token collides with ORA's own "floor-flag" term of art on the real
    # false-positive line).
    scaling_mult_spans = _dscr_scaling_multiplier_spans(low) if is_gov else []
    # Eval-harness floor-RESULT narration spans (2026-08-23): the achieved-DSCR member and the
    # ratified 65%-LTV sizing-basis member of a "PASSES (1.42x vs 1.25x floor at 65%-LTV sizing)"
    # verdict. All guards except the DSCR decl-shape veto are applied inside the helper; consumed
    # ONLY by the dscr-anchored candidate loop and the LTV bare-proximity fallback below.
    floor_result_dscr, floor_result_ltv = (
        _floor_result_spans(low) if is_gov else ([], []))

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
                    or any(s <= idx < e for (s, e) in sentinel_prose_spans)
                    or _portfolio_qualified(low, idx)
                    or _stabilization_qualified(low, idx))
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
        # Declaration-shaped extractor spans, for the floor-result DECL-SHAPE veto below: a value
        # bound by any of these is being DECLARED (keyword/pivot/from-to construct), so a
        # floor-result narration match on the same span must NOT suppress it. Computed only when a
        # floor-result construct is actually present (the only consumer).
        decl_shaped_spans = (
            [mm.span(1) for mm in RE_DSCR_DECL.finditer(low)]
            + [mm.span(1) for mm in RE_DSCR_FROMTO.finditer(low)]
            + [mm.span(1) for mm in RE_DSCR_DECL_REV.finditer(low)]
            + [mm.span(1) for mm in RE_DSCR_PIVOT_DECOY.finditer(low)]
        ) if floor_result_dscr else []
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
            # skip a tilde-hedged changelog-narration value, ONLY when the line also separately
            # restates the plain canonical 1.25 (span-scoped, 2026-08-21 -- see RE_DSCR_TILDE_HEDGE).
            if any(s <= vs and ve <= e for (s, e) in dscr_tilde_hedge_spans):
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
            # skip a deal-specific STABILIZATION-CONDITIONED covenant DSCR (a projected property
            # DSCR that only clears its lender floor at lease-up/stabilization -- e.g. "clears the
            # 1.75x floor only at Yr3+ stabilization") -- a deal-financing narration, not the
            # acquisition governor. Vetoed by any acquisition-governor marker or a value declared
            # AS the governor (see _stabilization_qualified), so a real governor drift dressed in
            # stabilization language still flags.
            if _stabilization_qualified(low, vs):
                continue
            # skip a DSCR value that is an approximate INFLATION/SCALING MULTIPLIER on a computed
            # figure in a bug-fix changelog narrative ("inflating computed DSCR ~1.6x") -- the
            # magnitude of a defect, not a declared governor threshold. Structurally excluded from
            # ever matching a real declaration (see RE_DSCR_COMPUTED_SCALING) and deferred whole-
            # line to the RE_GOV_DSCR_BOUND structural veto at the source, so a real "dscr floor/
            # minimum" pairing sharing the line still flags in full (see _dscr_scaling_multiplier_spans).
            if _in_spans(vs, ve, scaling_mult_spans):
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
            # skip an ACHIEVED DSCR narrated against the canonical floor -- an eval-harness
            # floor-check VERDICT ("DSCR floor PASSES (1.42x vs 1.25x floor at 65%-LTV sizing)"),
            # not a governor declaration (see the floor-result block comment). Canonical-anchored,
            # result-verb-gated and declaration-token-vetoed in _floor_result_spans; the DECL-SHAPE
            # veto here keeps a declaration dressed in the same word order visible ("DSCR floor
            # raised to 1.42x vs 1.25x floor -- passes" still flags via RE_DSCR_DECL's pivot
            # binding), and the KEYWORD-DIRECT-BIND veto covers every binder form those extractors
            # miss -- copula AND verb-phrase alike ("DSCR floor is 1.42x...", "DSCR floor set at
            # 1.42x...", "DSCR floor stands at 1.42x..." all still flag): suppression requires the
            # verdict verb to sit BETWEEN a same-clause nearby floor-keyword and the value, which
            # only the genuine narration shape satisfies ("floor PASSES (1.42x").
            if (_in_spans(vs, ve, floor_result_dscr)
                    and not _in_spans(vs, ve, kw_after_spans)
                    and not _in_spans(vs, ve, decl_shaped_spans)
                    and not _floor_kw_binds_value_directly(low, vs)):
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
        def _flag_ltv(val, kind="ceiling", vs=None, ve=None):
            # NUMERIC comparison (2026-07-29, with the decimal-fragment guard): captures may now be
            # decimals, so "40.0" must read as canonical and "54.3" must flag as itself -- never as
            # its fractional fragment. Unparseable input is impossible from these regexes but is
            # dropped defensively (detection elsewhere is unaffected).
            if not val or val in seen_ltv:
                return
            try:
                num = float(val)
            except ValueError:
                return
            # STANDALONE per-property refi-sizing ceiling (KNOWN GAP 2, closed -- see
            # RE_PERPROPERTY_REFI_FRAME above): the ratified 65 declared on its own bullet, with no
            # same-line aggregate companion or refi construct, is a SECOND canonical governor value
            # at this level, not a drift on the 40% aggregate. VALUE-LOCKED (only "65" ever matches,
            # so a real per-property drift is untouched and still flags below) and FRAME-GATED
            # (requires the ratified "per-property ... refi ... siz(ing)" wording on the line), with
            # position info required so the existing _governor_declared_nearby veto still applies --
            # a value mislabeled AS the acquisition/aggregate ceiling nearby still flags.
            if (val == CANON_LTV_PERPROPERTY and vs is not None
                    and _perproperty_refi_frame_immediately_before(low, vs)
                    and not _governor_declared_nearby(low, vs, ve if ve is not None else vs)):
                return
            # LINE-WIDE ratified dual-governor reaffirmation (2026-08-22 FP fix; session 438b62fb,
            # human-authorized override). The tight companion-anchored pairing above
            # (_perprop_portfolio_paired_veto_spans / RE_PERPROP_PORTFOLIO_PAIR) already suppresses
            # "per-property LTV 65% / portfolio-aggregate LTV 40%" when both members sit close
            # together -- but that pairing is consumed ONLY via refi_ltv_veto, itself scoped to the
            # single RE_LTV_NEAR match it was extracted from. A dense paragraph can restate that
            # SAME ratified pairing once, in its own closing sentence ("governor constant (DSCR
            # 1.25x / per-property LTV 65% / portfolio-aggregate LTV 40%) changed"), while ALSO
            # discussing "the 65% LTV ceiling" earlier in an unrelated clause with no "per-property"
            # token anywhere near THAT occurrence ("DSCR binds less often and the 65% LTV ceiling
            # binds more often" -- acquisition-underwriting SKILL.md v4.13). Both name the SAME
            # ratified per-property figure; only the wording differs, and the reaffirming pairing is
            # sitting in plain sight elsewhere on the SAME line.
            # _line_reaffirms_ratified_ltv_pair() answers "does this line contain the tight
            # companion-anchored pairing ANYWHERE" (not local to THIS value) -- still
            # COMPANION-ANCHORED (the aggregate 40% must be present and correctly paired, so a
            # drifted companion earns no reaffirmation) and VALUE-LOCKED to 65 (a real per-property
            # drift at any OTHER value is untouched and still flags below, exactly like the
            # standalone-frame check above). Still vetoed by _governor_declared_nearby at THIS
            # value's own position, so a mislabeled "65% ... is now the acquisition governor"
            # sharing a line with the correct pairing still flags -- pinned by
            # test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_governor_declared_drift_unit.
            # ALSO vetoed by _aggregate_ltv_declared_in_clause (independent review finding,
            # 2026-08-22, session 438b62fb): a partial-edit drift line naturally quotes the OLD
            # correct pairing alongside a genuinely wrong NEW aggregate figure ("Aggregate LTV
            # ceiling raised to 65% ... doctrine had read per-property LTV 65% / portfolio-aggregate
            # LTV 40%.") -- without this veto the reaffirmation elsewhere on the line would mask a
            # real drift of the 40%-governor TO 65%, the single most plausible wrong value for it.
            # Pinned by test_ltv_ceiling_reaffirmed_elsewhere_does_not_mask_aggregate_drift_unit.
            if (val == CANON_LTV_PERPROPERTY and vs is not None
                    and _line_reaffirms_ratified_ltv_pair(low)
                    and not _governor_declared_nearby(low, vs, ve if ve is not None else vs)
                    and not _aggregate_ltv_declared_in_clause(low, vs)):
                return
            # 0 < num < 1 flags too (REFUTE residual #1, 2026-07-29): "LTV ceiling 0.65%" is the
            # unit-interval notation a human porting capital-config.ts (ltvCeiling: 0.65) into
            # prose would write; whole-value binding would otherwise EXTEND the old 1..100 gate's
            # silence to it. Includes "0.40%" -- ambiguous notation on a governor line is worth a
            # loud look, not a silent guess (detection over silence).
            if num != float(CANON_LTV) and 0 < num <= 100:
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
                        # ...and skip it when a non-LTV subject owns it: the anchor can bind a
                        # ceiling word that belongs to another noun ("LTV steady, maximum TI 12% of
                        # TDC"), and the window would then read that subject's percentage as the
                        # declared LTV ceiling. Same veto as the reverse pass, same reason.
                        if not _nonltv_subject_owns(low, base + pm.start(1)):
                            _flag_ltv(pm.group(1), vs=base + pm.start(1), ve=base + pm.end(1))
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
                        # skip the ratified 65%-LTV sizing basis of a floor-RESULT narration
                        # ("...1.25x floor at 65%-LTV sizing, LTV binds") -- value-locked to 65,
                        # canonical-anchored, result-verb-gated, and governor-/aggregate-clause-
                        # vetoed inside _floor_result_spans (see the floor-result block comment).
                        if _in_spans(pvs, pve, floor_result_ltv):
                            continue
                        if _in_spans(pvs, pve, refi_ltv_noveto):
                            continue
                        if (_in_spans(pvs, pve, refi_ltv_veto)
                                and not _governor_declared_nearby(low, pvs, pve)):
                            continue
                        _flag_ltv(m.group(1) or m.group(2), kind="governor", vs=pvs, ve=pve)
            # REVERSE-ORDER ceiling ("65% ceiling"/"65% maximum") -- number-then-keyword, needs NO
            # 'ltv' token, so it closes "This 65% ceiling is the acquisition governor". Correction-
            # span-skipped and post-close-refi-suppressed exactly like the forward passes.
            for m in RE_LTV_CEIL_REV.finditer(low):
                vs = m.start(1)
                if any(s <= vs < e for (s, e) in ltv_corr_spans):
                    continue
                if _refi_qualified(low, vs):
                    continue
                # NON-LTV SUBJECT VETO (2026-08-12, MAJOR review finding). This pass needs no 'ltv'
                # token, so on a line armed by something else it read ANY capped percentage as an
                # LTV ceiling -- "DSCR 1.25x minimum; underwrite vacancy 10% maximum." reported a
                # 10% LTV ceiling. Suppress only when the percentage demonstrably belongs to another
                # subject; do NOT require positive LTV evidence (see NON_LTV_PCT_SUBJECTS for why
                # the requirement form silenced real declarations).
                if _nonltv_subject_owns(low, vs):
                    continue
                _flag_ltv(m.group(1), vs=vs, ve=m.end(1))
    # 4) INTERIM-CHECKLIST threshold wording -- independent of is_gov (these lines carry no governor
    #    keyword; that is exactly why the passes above missed them). Equality-checked numerically like
    #    every other LTV pass; the ratified per-property 65 is not read as an aggregate drift when a
    #    per-property marker sits next to the value (see _interim_flag).
    interim_seen = set()

    def _interim_flag(val, vs, ve, portfolio_bound=False):
        """Numeric equality vs the canonical aggregate 40. The ratified per-property 65 is vetoed only
        when a per-property marker sits NEXT TO THE VALUE (within INTERIM_PERPROP_NEAR chars) AND the
        flag term the value binds to is not itself qualified '(portfolio)'/'(aggregate)': a 40->65
        drift on a portfolio flag line must flag even when 'per-property' appears elsewhere on the line
        (REFUTE round 1 C1 / round 2 C5). No correction-note skip: a real note ('corrected ... from 55%
        to 40%') carries none of these comparator forms; a changelog line that narrates an OLD value in
        comparator form ('corrected the LTV-FLAGGED trigger from over 45% to over 40%') flags LOUDLY and
        is reworded, the probe's established practice (REFUTE round 2 C8, pinned by a test)."""
        if not val or val in interim_seen:
            return
        try:
            num = float(val)
        except ValueError:
            return
        if num == float(CANON_LTV_PERPROPERTY) and not portfolio_bound:
            near = low[max(0, vs - INTERIM_PERPROP_NEAR):ve + INTERIM_PERPROP_NEAR]
            if any(mk in near for mk in PERDEAL_MARKERS):
                return
        if num != float(CANON_LTV) and 0 < num <= 100:
            interim_seen.add(val)
            out.append("LTV interim-checklist threshold %s%% != canonical %s%%" % (val, CANON_LTV))

    # (a) '<above|over|exceeds|...> N%' bound to an LTV-FLAG term in the same sentence: the first flag
    #     term AFTER the value (<=200 chars, to the end of the sentence '. '), else the last one BEFORE it
    #     (<=120 chars from the start of its sentence) with no flag-STATISTIC wording in between. A
    #     different ratio named just before the comparator ("LTC above 80%"), or a statistic right
    #     after the value ("over 25% of pipeline"), is not the threshold.
    for m in RE_LTV_INTERIM_CMP.finditer(low):
        a_end = m.end()
        after = low[a_end:a_end + INTERIM_FLAG_WINDOW_AFTER]
        se = RE_LTV_SENT_END.search(after)
        if se:
            after = after[:se.start()]
        b_start = max(0, m.start() - INTERIM_FLAG_WINDOW_BEFORE)
        before = low[b_start:m.start()]
        last_end = None
        for se in RE_LTV_SENT_END.finditer(before):
            last_end = se.end()
        if last_end is not None:
            b_start += last_end
            before = before[last_end:]
        # the lead guard looks only inside the current CLAUSE (N3): "Hold DSCR at 1.25x; above 55% ..."
        lead = re.split(r"[;:,]", low[max(0, m.start() - 30):m.start()])[-1]
        if (LTV_OTHER_RATIO_BEFORE.search(lead)
                or LTV_FLAG_STAT_WORDS.search(low[a_end:a_end + 30])):
            continue
        bound_end = None
        fm = RE_LTV_FLAG_TERM.search(after)
        if fm:
            bound_end = a_end + fm.end()
        else:
            for h in RE_LTV_FLAG_TERM.finditer(before):
                if not LTV_FLAG_STAT_WORDS.search(before[h.end():]):
                    bound_end = b_start + h.end()
        if bound_end is None:
            continue
        _interim_flag(m.group(1), m.start(1), m.end(1),
                      portfolio_bound=RE_LTV_FLAG_PORTFOLIO_QUAL.match(low, bound_end) is not None)
    # (b) the worksheet result row '| N | Result = (...loan...) / (...value...), vs N% |'. Linear-time:
    #     head, first 'vs', then the FORMULA is checked in code; the threshold is the cell after 'vs'
    #     plus (for 'vs 40% | 55% |') a following cell that is nothing but a percentage.
    if "result" in low and "loan" in low:
        rm = RE_LTV_ROW_HEAD.search(low)
        vsm = RE_LTV_ROW_VS.search(low, rm.end()) if rm else None
        if vsm:
            formula = low[rm.end():vsm.start()]
            if (RE_LTV_ROW_LOAN.search(formula) and "/" in formula
                    and RE_LTV_ROW_VALUE.search(formula) and not RE_LTV_ROW_NEG.search(formula)):
                base = vsm.end()
                cells = low[base:].split("|")
                offs = base
                for ci, cell in enumerate(cells[:2]):
                    if ci == 1 and not RE_LTV_ROW_PCT_ONLY.fullmatch(cell):
                        break
                    for pm in RE_LTV_ROW_PCT.finditer(cell):
                        # 'vs 75% lender max' / 'vs 80% LTC': the threshold of ANOTHER ratio
                        if RE_LTV_ROW_PCT_OWNER.search(cell[pm.end():pm.end() + 15]):
                            continue
                        _interim_flag(pm.group(1), offs + pm.start(1), offs + pm.end(1))
                    offs += len(cell) + 1
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
# 2026-07-29: a proposed 'review' token alongside 'audit' was REFUTE-REJECTED -- it would also
# sweep in project_*_doctrine_review_*.md files (a pending doctrine-REVIEW plan is a place a
# governor change could plausibly first be written down: FN-biased on the catastrophic class).
# The one live 'review' narrative file is exempted by EXACT NAME in skip_names instead.
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

def _is_eval_harness_run_log(path):
    """2026-08-24 path-class exemption. acquisition-underwriting-eval-harness/runs/*.json is
    machine-generated RESULT narration -- a deal's achieved DSCR/LTV at scoring time, quoted in
    LLM-authored floor_result_variants prose -- never a governor DECLARATION. Same class as
    is_data_json's /data/ exemption (per-DEAL values, not governor text), but these live under
    .../runs/, not /data/, so that check doesn't reach them.

    The 2026-08-23 floor-result suppressor (ba831dc, ~220 lines, 4 rounds of adversarial review)
    already narrowly covers two known phrasings ("DSCR floor PASSES (1.42x vs 1.25x floor at
    65%-LTV sizing)") by requiring the sentence to explicitly restate "vs 1.25x floor" as its
    canonical anchor. A third phrasing re-tripped it within 24h:
    2026-08-24T163634Z_scheduled-poll.json:204 (liberty-office-park-west-chester-oh) --
    "DSCR floor PASSES (~1.42x at 65%-LTV-bound refi sizing)" -- never restates 1.25x at all, so
    no canonical-anchored regex can lock onto it without abandoning the anchor guarantee that
    makes the existing suppressor safe. Regex whack-a-mole against unpredictable per-run LLM
    phrasing is a losing, ever-recurring game for this one file class (flagged as the cheaper
    alternative in ba831dc's own commit message but deferred to Gabriel; now empirically
    recurred, so taken here instead of a fourth narrow regex branch).

    A real governor drift in what the acquisition-underwriting skill COMPUTES would first drift
    at its declaration in standards.md / rules.md / CLAUDE.md / skills / capital-config.ts, all
    still fully in scope -- this file class only ever narrates a downstream result. Path-based
    (not skip_names by exact name), since a new dated run file is created on every scheduled
    poll. Narrowly scoped to .../runs/ specifically -- sibling eval-harness content (README,
    golden-deal fixtures) is hand-authored and stays fully in scope, matching this module's
    precision-over-recall design throughout."""
    return "/acquisition-underwriting-eval-harness/runs/" in path.replace("\\", "/").lower()

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
    # Append-only DECISION LEDGERS (2026-07-29): disposition-ledger.md and deal-decision-ledger.md
    # are the same append-only narrative class as event_log.md -- one row per ratified past decision,
    # legitimately quoting off-canonical historicals ("54.3% LTV ... exceeds 40% governor -- ACCEPTED",
    # Gabriel-ratified exceptions). They RECORD outcomes; the living governor stays declared in
    # standards.md / rules.md / firm.md / CLAUDE.md / skills / capital-config.ts, all still in scope.
    # Same accepted blind spot as event_log.md, unchanged in kind. The historical-evaluations
    # review file is exempt by EXACT NAME (not by a 'review' pattern token -- REFUTE-rejected,
    # see DATED_AUDIT_RE comment): it narrates the same two Gabriel-ACCEPTED LTV exceptions.
    skip_names |= {"disposition-ledger.md", "deal-decision-ledger.md",
                   "project_historical_evaluations_acquisition_review_2026-07-29.md"}
    # reference_concurrent_session_duplicate_hardening_work.md (2026-08-22): same append-only
    # NARRATIVE class -- it records what OTHER sessions investigated/were/weren't working on,
    # quoting one session's own title verbatim ('Fix governor-drift-probe false positive on
    # LTV 65%/40%') while explaining it was a DIFFERENT, already-landed bug. That quoted title
    # trips is_gov purely because it contains the literal substring "governor" (as part of the
    # tool's own compound name, "governor-drift-probe") -- not because it declares a live
    # governor. Exact-name exemption, not a pattern token (REFUTE-rejected precedent above):
    # this file is a narrative investigation log, never the doctrinal home for a governor value.
    skip_names |= {"reference_concurrent_session_duplicate_hardening_work.md"}
    # INDEX_projects_system.md (2026-08-23): the "Projects & system" SUB-INDEX split out of
    # MEMORY.md (already exempted above) when MEMORY.md's own size gate got tight -- same
    # append-only-pointer NARRATIVE class as its parent, just in a separate file. Its bullets
    # POINT to project files and quote their titles verbatim, e.g. "- [governor-drift-probe LTV
    # 65%/40% split false positive](...) -- LANDED 08-22 (`c7875a5`)" -- a record of a
    # ALREADY-LANDED fix, not a live governor declaration. Same reasoning as MEMORY.md itself:
    # exact-name exemption, not a pattern token (REFUTE-rejected precedent above).
    skip_names |= {"INDEX_projects_system.md"}
    # open-items-tracker.md + open-items-tracker-history.md (2026-09-21): the append-only open-items
    # ledger and its rollover file -- the same NARRATIVE class as event_log.md and the decision
    # ledgers above. One row per item, each RECORDING a finding; OI-338's row (a single 4,454-char
    # table line) reports "Governor flag (no constant changed)" ONCE, at offset ~2,400, and that one
    # word armed the whole line (_is_gov_line), so the bare-proximity pass read three ordinary
    # per-loan LTVs (66.8% / 7.7% / 37.7%) thousands of characters away as governor declarations --
    # failing test_event_log_excluded_e2e and blocking every push. Exact names, no pattern token
    # (REFUTE-rejected precedent above). Both files, not just the live one: rows roll into -history,
    # so exempting only the live file would re-trip the moment OI-338 is archived. Accepted blind
    # spot, unchanged in kind from the ledgers: a governor change recorded ONLY in a tracker row,
    # never in standards.md / rules.md / firm.md / CLAUDE.md / skills / capital-config.ts, goes unseen.
    skip_names |= {"open-items-tracker.md", "open-items-tracker-history.md"}
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
                    or _is_test_file(path) or _is_eval_harness_run_log(path)):
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
