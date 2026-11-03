#!/usr/bin/env python3
"""ORA buy-box drift probe.

Sibling of governor-drift-probe.py, for the acquisition PRICE/SIZE band instead of DSCR/LTV.
Canon: ora-skills/acquisition-underwriting/SKILL.md STAGE 0 Gate 2 --
  single asset $500K-$10M; Amendment H portfolio of 2-5 buildings sold together <= $15M;
  <50,000 SF per building.
Origin (2026-11-03): the code review of ora-claude-config#378 found CLAUDE.md, deal-recon,
dd-package-sweep and memory/firm.md still saying "sub-$10M" after Amendment H let portfolios run
to $15M; #391 fixed them by hand. This probe makes the next doctrine move fail loud instead.

Rules (precision over recall, same stance as the governor probe):
  * Only BUY-BOX STATEMENTS count: a price/size ceiling with buy-box context (buy-box, ORA
    targets/buys, Price:, deal size, per acquisition, ...) within a short window around it.
    Market-research prose ("no sub-$10M cap-rate series found") carries no such context.
  * $10M ceiling with NO portfolio-path mention in the same unit (line / wrapped bullet /
    paragraph / table row) = drift. A $15M ceiling with no portfolio mention = drift (the $15M
    applies only to portfolios sold together). Any other ceiling above $10M = drift. Ceilings
    below $10M (sweet spots, sub-bands) are ignored.
  * A per-building SF ceiling (sub-/under/</<=) above 50,000 SF in buy-box context = drift.
    Lower SF ceilings (floors, sub-bands) and SF ranges ("units 1,000-20,000 SF") are ignored.
  * AUM/firm-scale figures ($700-800M target, sub-$150M AUM gate) are never deal prices.
  * Canon anchor: Gate 2 is parsed first. If it no longer states $500K / $10M / $15M / 2-5
    buildings / 50,000 SF, the probe's constants are stale -> exit 2 (update the probe and the
    funnels together), never a silent pass against an outdated canon.
  * Allowlisted: changelog/history lines (version- or date-led bullets and table rows, units
    under a Changelog / Version history / Revision history heading), append-only narrative logs
    (event_log*, MEMORY.md, INDEX_*, open-items trackers, decision ledgers), and _archive/_staging
    paths.
Known blind spots: floors are not checked (several funnels say $1M-$10M vs canon $500K); a
ceiling written as "$10,000,000" or with no buy-box word nearby is not seen; a below-canon SF
ceiling ("sub-40K SF buy-box") is read as a sub-band, not drift.

Exit 0 = clean; 1 = drift found; 2 = probe error (unreadable target, missing or moved canon).

Usage: python buybox-drift-probe.py [--quiet] [--claude-root DIR] [--skills-root DIR]
"""
import glob
import os
import re
import sys

# Output echoes file content (en dash, <=, middle dot) -> force UTF-8 so the probe never crashes
# on its own output when stdout is a Windows cp1252 pipe.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CANON_SINGLE_FLOOR_K = 500
CANON_SINGLE_CEIL_M = 10
CANON_PORTFOLIO_CEIL_M = 15
CANON_PORTFOLIO_BUILDINGS = (2, 5)
CANON_SF_CEIL = 50000

HOME = os.path.expanduser("~")
CANON_REL = os.path.join("acquisition-underwriting", "SKILL.md")

# Relative to the ~/.claude root. Non-recursive on purpose: these are the doctrinal homes.
CLAUDE_GLOBS = (
    "CLAUDE.md",
    os.path.join("agents", "*.md"),
    os.path.join("scheduled-tasks", "*", "SKILL.md"),
    os.path.join("skills", "*", "SKILL.md"),
    os.path.join("projects", "*", "memory", "*.md"),
)
SKILLS_GLOBS = (os.path.join("*", "SKILL.md"),)

_PRUNE_EXACT = ("_archive", "_staging")
_PRUNE_PREFIX = ("_archive_", "_staging_")

# Append-only narrative logs: they RECORD past wording, they do not declare the live box.
# Same class (and same names) the governor probe exempts.
SKIP_NAMES = {"event_log.md", "MEMORY.md", "open-items-tracker.md",
              "open-items-tracker-history.md", "deal-decision-ledger.md", "disposition-ledger.md"}
SKIP_NAME_RE = re.compile(r"^(?:event_log_\d{4}-\d{2}-\d{2}|INDEX_.*|CHANGELOG.*)\.md$", re.I)

# --------------------------------------------------------------------------- patterns

_DASH = r"[–—\-]"
_MILL = r"(?:M|MM|mm|million)\b"
_NUM = r"(\d+(?:\.\d+)?)"
RE_PRICE_CEIL_WORD = re.compile(
    r"(?:\bsub-?|\bunder\s+|\bbelow\s+|\bless than\s+|<=?\s*|≤\s*|\bup to\s+|\bmax(?:imum)?\s+"
    r"|\bat most\s+|\bnot exceeding\s+|\bno more than\s+|\bceiling of\s+)"
    r"[*_`]*\$\s?" + _NUM + r"\s?" + _MILL, re.I)
RE_PRICE_CEIL_RANGE = re.compile(
    r"\$\s?\d+(?:\.\d+)?\s?(?:K|M|MM)?[*_`]*\s?(?:" + _DASH + r"|\bto\b)\s?[*_`]*\$?\s?" + _NUM + r"\s?" + _MILL,
    re.I)
RE_PRICE_CEIL_SUFFIX = re.compile(
    r"\$\s?" + _NUM + r"\s?" + _MILL + r"\s+(?:max(?:imum)?|cap|ceiling|or (?:less|under|below))\b", re.I)

RE_SIZE_CEIL = re.compile(
    r"(?:\bsub-?|\bunder\s+|\bbelow\s+|\bless than\s+|<=?\s*|≤\s*|\bup to\s+|\bmax(?:imum)?\s+)"
    r"[*_`]*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?\s?K)\s?(?:SF|sq\.?\s?ft|square feet)\b", re.I)

RE_CONTEXT = re.compile(
    r"buy[- ]?box|\bin[- ]box\b|\bORA box\b|\bORA[- ]relevant\b|\btargets?\b(?![- ]markets?)|\bbuys\b|\bbuying\b|\bbuyer\b|\bworking\b"
    r"|\bacquisition (?:focus|criteria|band|range|size|targets?)\b|\bdeal size\b|\bcheck size\b"
    r"|\bper (?:acquisition|transaction|deal)\b|\bprice\b[*_`\s]*[:/|]|\bsize\b[*_`\s]*[:/|]"
    r"|\bacquir(?:es|ing)\b|\binvest(?:s|ing)? in\b|\binvestment criteria\b|\bacquisition criteria\b", re.I)
CONTEXT_BEFORE = 160
CONTEXT_AFTER = 80
# Firm-scale figures (AUM targets, tooling AUM gates) are not deal prices: an AUM word in the
# window vetoes the match, and no buy-box ceiling is ever stated at $100M+.
RE_FIRM_SCALE = re.compile(r"\bAUM\b|assets under management", re.I)
FIRM_SCALE_MIN_M = 100
# Financing figures (loan size, lender appetite, fund/equity raise) right before the amount are
# not the buy-box. Kept to a short reach so "Buy-box: sub-$10M; lender ..." still flags.
RE_FINANCING = re.compile(r"\b(?:loans?|lenders?|fund|equity|raise|debt|refi\w*|proceeds)\b", re.I)
RE_BUYBOX_WORD = re.compile(r"buy[- ]?box", re.I)
FINANCING_BEFORE = 40

# The Amendment H qualifier itself -- NOT any "portfolio" (in ORA prose that is usually the owned
# book: "fits the existing portfolio mix", "see portfolio-growth"). Review C3, 2026-11-03.
RE_PORTFOLIO = re.compile(
    r"amendment h\b|sold together|portfolio path|multi-building portfolio|portfolio of 2(?![0-9])"
    r"|\b2\s?" + _DASH + r"\s?5[\s-]+buildings?|portfolios?\s+(?:up to|to|of up to|≤|<=)\s*\$", re.I)
# "not sold together", "Amendment H does not apply" negate the qualifier (review round 2).
RE_NEGATION_BEFORE = re.compile(r"\b(?:not|no|never|without|excludes?)\b[^.;]{0,6}$", re.I)
# Only an explicit non-application counts after the qualifier: "never exceed $15M" / "do not exceed"
# BOUND the portfolio path rather than negate it (review round 3).
RE_NEGATION_AFTER = re.compile(r"^[^.;]{0,6}(?:\b(?:does not|doesn't|do not|never) apply\b|\bn/a\b)", re.I)

RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
# Anchored to the START of the heading text: "## Tenant history" or "CRITICAL PROVISIONS
# (history-derived)" are live sections, not changelogs (review C2).
# The WHOLE heading must be the history label, optionally with a parenthetical or a version/date
# suffix: "Changelog (v1.x)", "Changelog -- v1.x". "History of the buy-box decision" and "Changes to
# the screening funnel" are live sections (review round 2).
RE_HISTORY_HEADING = re.compile(
    r"^[\W_]*(?:change\s?log|changes|history|release notes"
    r"|(?:version|revision|build|update|change|edit|release|amendment)\s+(?:history|log|notes))[*_`]*"
    r"\s*(?:\([^)]*\))?\s*(?:[:–—-]+\s*v?[\d.x]+(?:\s*[–—-]\s*v?[\d.x]+)?)?[\W_]*$", re.I)
RE_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
RE_FENCE = re.compile(r"^\s*(```|~~~)")
# A version/date token followed directly by changelog punctuation ("v1.10 (", "2026-10-30:",
# "| v4.40 |"). "- 2026-11-01 standing rule:" and "- v2.0 buy-box:" are live rules (review C4).
RE_HISTORY_LEAD = re.compile(
    r"^[\s|>*_`\-+]*(?:v\d+(?:\.\d+)+|\d{4}-\d{2}-\d{2})[*_`]*\s*[(:|–—]", re.I)


def _price_value_m(raw):
    return float(raw)


def _size_value_sf(raw):
    raw = raw.replace(" ", "")
    if raw.lower().endswith("k"):
        return float(raw[:-1]) * 1000
    return float(raw.replace(",", ""))


# --------------------------------------------------------------------------- segmentation

def iter_units(text):
    """Yield (first_lineno, [(lineno, line), ...], allowlisted) statement units.

    A unit is a wrapped list item or paragraph (ends at a blank line, heading, new list item or
    table row); a table row, heading and every line inside a code fence are units of their own.
    allowlisted = the unit sits under a history heading or its first line is version/date-led."""
    lines = text.splitlines()
    history_level = None       # heading level of the open history section, if any
    in_fence = False
    cur = []

    def flush():
        if cur:
            first = cur[0][1]
            allow = history_level is not None or bool(RE_HISTORY_LEAD.match(first))
            yield (cur[0][0], list(cur), allow)
            del cur[:]

    for i, line in enumerate(lines, 1):
        if RE_FENCE.match(line):
            for u in flush():
                yield u
            in_fence = not in_fence
            continue
        if in_fence:
            for u in flush():
                yield u
            yield (i, [(i, line)], history_level is not None)
            continue
        m = RE_HEADING.match(line)
        if m:
            for u in flush():
                yield u
            level = len(m.group(1))
            if history_level is not None and level <= history_level:
                history_level = None
            if history_level is None and RE_HISTORY_HEADING.search(m.group(2)):
                history_level = level
            continue
        if not line.strip():
            for u in flush():
                yield u
            continue
        if line.lstrip().startswith("|"):
            for u in flush():
                yield u
            yield (i, [(i, line)], history_level is not None or bool(RE_HISTORY_LEAD.match(line)))
            continue
        if RE_LIST_ITEM.match(line):
            for u in flush():
                yield u
        cur.append((i, line))
    for u in flush():
        yield u


# --------------------------------------------------------------------------- scanning

def _scan_unit(numbered):
    joined = ""
    starts = []
    for ln, line in numbered:
        starts.append((len(joined), ln))
        joined += line + "\n"

    def lineno_at(pos):
        ln = starts[0][1]
        for off, n in starts:
            if off <= pos:
                ln = n
        return ln

    def has_context(ms, me):
        return RE_CONTEXT.search(joined[max(0, ms - CONTEXT_BEFORE):me + CONTEXT_AFTER]) is not None

    has_portfolio = any(
        not RE_NEGATION_BEFORE.search(joined[max(0, q.start() - 20):q.start()])
        and not RE_NEGATION_AFTER.search(joined[q.end():q.end() + 20])
        for q in RE_PORTFOLIO.finditer(joined))
    out = []
    seen = set()
    for rx in (RE_PRICE_CEIL_WORD, RE_PRICE_CEIL_RANGE, RE_PRICE_CEIL_SUFFIX):
        for m in rx.finditer(joined):
            if m.start(1) in seen:
                continue
            seen.add(m.start(1))
            if not has_context(m.start(), m.end()):
                continue
            v = _price_value_m(m.group(1))
            window = joined[max(0, m.start() - CONTEXT_BEFORE):m.end() + CONTEXT_AFTER]
            if v >= FIRM_SCALE_MIN_M or RE_FIRM_SCALE.search(window):
                continue
            reach = joined[max(0, m.start() - FINANCING_BEFORE):m.start()]
            if RE_FINANCING.search(reach) and not RE_BUYBOX_WORD.search(reach):
                continue
            reason = None
            if v == CANON_SINGLE_CEIL_M and not has_portfolio:
                reason = ("$%gM ceiling with no portfolio-path mention in the same line/bullet "
                          "(canon: Amendment H portfolios of %d-%d buildings sold together run to $%dM)"
                          % (v, CANON_PORTFOLIO_BUILDINGS[0], CANON_PORTFOLIO_BUILDINGS[1],
                             CANON_PORTFOLIO_CEIL_M))
            elif v == CANON_PORTFOLIO_CEIL_M and not has_portfolio:
                reason = ("$%gM ceiling stated without the portfolio qualifier (canon: single asset "
                          "<= $%dM; $%dM only for portfolios sold together)"
                          % (v, CANON_SINGLE_CEIL_M, CANON_PORTFOLIO_CEIL_M))
            elif v > CANON_SINGLE_CEIL_M and v != CANON_PORTFOLIO_CEIL_M:
                reason = ("$%gM price ceiling contradicts canon (single asset <= $%dM, portfolio "
                          "<= $%dM)" % (v, CANON_SINGLE_CEIL_M, CANON_PORTFOLIO_CEIL_M))
            if reason:
                out.append((lineno_at(m.start()), reason, m.group(0)))
    for m in RE_SIZE_CEIL.finditer(joined):
        if not has_context(m.start(), m.end()):
            continue
        sf = _size_value_sf(m.group(1))
        # Below-canon SF ceilings are sub-bands or floors ("<10K SF sub-scale", "Quasi-IOS <20K
        # SF") that sit inside the box -- same stance as sub-$10M price sweet spots.
        if sf > CANON_SF_CEIL:
            out.append((lineno_at(m.start()),
                        "%s SF size ceiling contradicts canon (<%s SF per building)"
                        % ("{:,.0f}".format(sf), "{:,}".format(CANON_SF_CEIL)), m.group(0)))
    return out


def scan_text(text):
    """Return [(lineno, reason, matched_text), ...] for every drifting buy-box statement."""
    findings = []
    for _first, numbered, allow in iter_units(text):
        if allow:
            continue
        findings.extend(_scan_unit(numbered))
    findings.sort(key=lambda f: f[0])
    return findings


# --------------------------------------------------------------------------- canon anchor

RE_CANON_LINE = re.compile(r"\*\*Size/Price:?\*\*", re.I)


def check_canon_text(text):
    """Problems (empty list = canon still matches this probe's constants)."""
    line = next((l for l in text.splitlines() if RE_CANON_LINE.search(l)), None)
    if line is None:
        return ["canon Gate 2 'Size/Price' line not found"]
    probs = []
    if not re.search(r"\$%dK\s*%s\s*\$%dM\s+single asset" % (CANON_SINGLE_FLOOR_K, _DASH, CANON_SINGLE_CEIL_M),
                     line, re.I):
        probs.append("canon single-asset band is no longer $%dK-$%dM" % (CANON_SINGLE_FLOOR_K, CANON_SINGLE_CEIL_M))
    if not re.search(r"(?:≤|<=)\s*\$%dM\s+multi-building portfolio" % CANON_PORTFOLIO_CEIL_M, line, re.I):
        probs.append("canon portfolio ceiling is no longer <= $%dM" % CANON_PORTFOLIO_CEIL_M)
    if not re.search(r"\b%d\s*%s\s*%d buildings" % (CANON_PORTFOLIO_BUILDINGS[0], _DASH, CANON_PORTFOLIO_BUILDINGS[1]),
                     line, re.I):
        probs.append("canon portfolio scope is no longer %d-%d buildings" % CANON_PORTFOLIO_BUILDINGS)
    if not re.search(r"<\s*%s SF per building" % "{:,}".format(CANON_SF_CEIL), line, re.I):
        probs.append("canon size ceiling is no longer <%s SF per building" % "{:,}".format(CANON_SF_CEIL))
    return probs


# --------------------------------------------------------------------------- walk + main

def _is_pruned(path, root):
    rel = os.path.relpath(path, root)
    for part in rel.split(os.sep)[:-1]:
        if part in _PRUNE_EXACT or part.startswith(_PRUNE_PREFIX):
            return True
    return False


def iter_targets(claude_root, skills_root):
    for root, patterns in ((claude_root, CLAUDE_GLOBS), (skills_root, SKILLS_GLOBS)):
        if not os.path.isdir(root):
            continue
        for pat in patterns:
            for path in sorted(glob.glob(os.path.join(root, pat))):
                name = os.path.basename(path)
                if _is_pruned(path, root) or name in SKIP_NAMES or SKIP_NAME_RE.match(name):
                    continue
                yield os.path.normpath(path)


def _arg(argv, flag, default):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv):
            print("[ACTION] buybox-drift-probe: %s needs a value" % flag, file=sys.stderr)
            sys.exit(2)
        val = argv[i + 1]
        if val.startswith("--"):
            print("[ACTION] buybox-drift-probe: %s got another flag (%s) as its value" % (flag, val),
                  file=sys.stderr)
            sys.exit(2)
        return val
    return default


KNOWN_FLAGS = ("--quiet", "--claude-root", "--skills-root")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    # Unknown args ("--claude-root=X", typos) would otherwise fall back to the real ~/.claude.
    for i, a in enumerate(argv):
        if a.startswith("--") and a not in KNOWN_FLAGS:
            print("[ACTION] buybox-drift-probe: unknown argument %s (use '--flag value')" % a,
                  file=sys.stderr)
            sys.exit(2)
    quiet = "--quiet" in argv
    claude_root = _arg(argv, "--claude-root", os.path.join(HOME, ".claude"))
    skills_root = _arg(argv, "--skills-root", os.path.join(HOME, "ora-skills"))
    # A missing root would scan nothing and read as clean -- fail loud instead (review C1).
    for root in (claude_root, skills_root):
        if not os.path.isdir(root):
            print("[ACTION] buybox-drift-probe: scan root missing: %s" % root, file=sys.stderr)
            sys.exit(2)

    canon_path = os.path.join(skills_root, CANON_REL)
    try:
        with open(canon_path, "r", encoding="utf-8", errors="replace") as fh:
            canon_probs = check_canon_text(fh.read())
    except Exception as e:
        print("[ACTION] buybox-drift-probe could not read canon %s: %s" % (canon_path, e), file=sys.stderr)
        sys.exit(2)
    if canon_probs:
        print("[ACTION] buybox-drift-probe: canon moved (%s) -- update the probe's CANON_* constants "
              "and every funnel together:" % canon_path, file=sys.stderr)
        for p in canon_probs:
            print("  - %s" % p, file=sys.stderr)
        sys.exit(2)

    findings = []
    scanned = 0
    targets = list(iter_targets(claude_root, skills_root))
    # An existing but empty/wrong ~/.claude root would scan nothing and read as clean.
    if not any(not os.path.relpath(p, claude_root).startswith("..") for p in targets):
        print("[ACTION] buybox-drift-probe: no target files under %s -- wrong root?" % claude_root,
              file=sys.stderr)
        sys.exit(2)
    for path in targets:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as e:
            print("[ACTION] buybox-drift-probe could not read %s: %s" % (path, e), file=sys.stderr)
            sys.exit(2)
        lines = text.splitlines()
        for ln, reason, _hit in scan_text(text):
            findings.append((path, ln, reason, lines[ln - 1].strip()[:160]))
        scanned += 1

    if findings:
        print("BUY-BOX DRIFT DETECTED (%d) -- canon: $%dK-$%dM single asset; <= $%dM for %d-%d buildings "
              "sold together (Amendment H); <%s SF per building:"
              % (len(findings), CANON_SINGLE_FLOOR_K, CANON_SINGLE_CEIL_M, CANON_PORTFOLIO_CEIL_M,
                 CANON_PORTFOLIO_BUILDINGS[0], CANON_PORTFOLIO_BUILDINGS[1], "{:,}".format(CANON_SF_CEIL)))
        for path, ln, reason, txt in findings:
            print("  %s:%d  %s" % (path, ln, reason))
            print("        | %s" % txt)
        sys.exit(1)

    if not quiet:
        print("buybox-drift-probe OK -- %d files scanned, buy-box statements consistent with canon."
              % scanned)
    sys.exit(0)


if __name__ == "__main__":
    main()
