#!/usr/bin/env python3
"""ORA target-geography drift probe.

Sibling of buybox-drift-probe.py (acquisition price/size band) and governor-drift-probe.py (DSCR/LTV),
for the acquisition GEOGRAPHY. Canon: ora-skills target-markets.json `clusters`, read live on every run.
Nothing about the clusters is hard-coded here, so a ratified cluster change moves the probe with it.

Origin (2026-11-05 data-flow review): agents/deal-flow-triage.md and agents/deal-recon.md stated ORA's
seven holdings states (OH, MD, IN, WI, MO, KS, TN) as its target geography, while target-markets.json
(v1.14) held eleven clusters, five of them entry-phase (Grand Rapids MI, Richmond VA, Des Moines IA,
Louisville KY, Chicago-Greater Cook County IL), and listed Nashville TN as a watch market, not a target.
A triage reading that line PASSes entry-market listings on geography and treats TN as in-box. ora-skills
PR #215 (branch claude/ora-skills-review-0bf6a8, UNMERGED as of 2026-11-06) adds
tools/doctrine_consistency.py to guard the ora-skills copies; it does not scan ~/.claude, so this probe
covers agents/, memory and task specs here.

Rule (target_geography(), ported from that branch's tools/doctrine_consistency.py with its pinned tests):
a line that presents ORA's target geography and names five or more states, at least four of them
established-cluster states, must name every cluster state, must not name a state no cluster covers
(unless that state is labeled a watch market: "TN watch", "Nashville TN (watch ..."), and, if it names
four or more clusters by city, must name them all. Holdings statements ("ORA holds/owns/spans ...")
and counted subsets ("five of ten target clusters") are left alone.

What presents target geography (an anchor):
  ported   "target market(s) / state(s) / cluster(s) / geography" or "ORA / we / the firm / it targets",
           within 160 characters before the first state named or 40 after the last.
  added    (2026-11-05: the port alone missed all three live defects; see test-target-geography-probe.py)
           * a verb whose subject is ORA anywhere earlier in the SAME clause (a clause ends at '.', '!' or
             '?' before whitespace, or at ';', outside parentheses): "ORA / we / the firm / it targets /
             is targeting", "... buys / acquires / sources / pursues / invests in", and "buyer working /
             buying / active / focused". deal-recon's Amendment H parenthetical put "ORA targets" about 260
             characters before its list; dd-package-sweep said "a ... buyer working sub-$10M ... across".
           * a criterion label leading the line: "Geography:", "**Geography** OH", "| Geo |", "Target / In-box
             geography:", "Buy-box:", "ORA box:", "ORA's acquisition box:" (deal-flow-triage: "- **Geography:**
             OH, MD, ..."). "Markets:" is NOT one: in ORA prose it names the holdings footprint as often as a
             target set (memory/firm.md), so it is left for a human rather than guessed.
  The anchor nearest the list is the one tested. A holdings word between it and the list ("holds", "owns",
  "owned", "spans", "holdings", the verb "own") vetoes the line; the adjective "own" ("on its own account")
  no longer does, as it did in the port. A count just before the anchor marks a subset only when it says so
  ("five OF ten target clusters", "the six ESTABLISHED target clusters"); a bare count ("Seven target states:")
  claims the whole set and is checked like one. Date and version digits ("2026-10-01", "v1.14") are not
  counts. Date-led history bullets ("- 2026-11-05: ...") are skipped like version-led ones.

Scope: agents/*.md, projects/*/memory/*.md and scheduled-tasks/*/SKILL.md under --claude-root,
non-recursive; folders named _archive*/_staging* are pruned. scheduled-tasks joined 2026-11-06 (Gabriel)
after review found ora-am-brief's inline C.5.5 box screen, the live 06:00 broker filter, restating the
holdings states. Skipped as append-only records of past wording: event_log*.md, open-items trackers, the
deal decision and disposition ledgers, CHANGELOG*. MEMORY.md and INDEX_*.md ARE scanned (buybox-drift-probe
skips them): they are live context loaded into sessions, the widest-reach place a stale geography could
sit. Inside a file, changelog sections and version- or date-led history lines are skipped. A task spec here
is the git-tracked copy; the scheduler reads the fleet store, so a clean probe run is not a live check.

LIMITS, stated plainly: pattern checks, one line at a time. They catch the phrasings above and the
variants pinned in test-target-geography-probe.py, not every wording. Known gaps:
  * missed: a target claim and its state list on different lines (including a list under a "## Geography"
    heading); fewer than five states named; a holdings word inside a target clause ("ORA targets markets
    where it already holds scale: ...") vetoes the whole line.
  * false alarms possible: the ported 160-character window crosses clauses ("ORA targets a 7.5% yield; its
    portfolio sits in OH, MD, ..."), and a buying or targeting verb is not checked for a geographic object
    ("ORA buys insurance in OH, ...", "we target a 3-day turnaround in OH, ..."). Reword such a line.
  * old wording quoted in a non-history memory note reads as live: reword it or date-lead the bullet.
A new phrasing that drifts needs a new anchor and a test.

COUNT RULE (added 2026-11-06; count_claims()). ora-deal-sourcing-scan v2.14 ran every week off "For each of
the ten clusters, web-search ..." and a three-line "TEN clusters: Columbus OH, ... LOUISVILLE KY." fallback
list while the canon held eleven; neither line names five states, so the rule above passed it and Chicago-
Greater Cook County IL was never scanned. A whole-set count -- "the / all / each of the / ORA's / our / its
N clusters", "N target|canonical|acquisition markets", "N clusters:" or "N clusters × ..." -- must equal the
number of clusters in the canon, and a list a "N clusters:" claim introduces (read across up to
LIST_MAX_LINES lines to its sentence end or a blank line) must name every cluster once it names four.
Not claims: "five of ten", "the other nine", "six established clusters", "the 10th cluster", "nine market
agents". Lines of a changelog paragraph (its first line opens at column 0 with "vX.Y — ") are history
for this rule; nothing else is.
Known gaps: a count and its noun split across a line break ("outside the ten\\n clusters"); bare "N markets"
(left out because the live tree used it only for non-target sets: "the 55 markets", "each of the 5 markets").

Exit 0 = clean; 1 = drift found; 2 = probe error (missing root or canon, a canon it cannot trust, an
unreadable target, an unexpected, malformed or repeated argument, or a root with no agents/memory files).

Usage: python target-geography-probe.py [--quiet] [--claude-root DIR] [--skills-root DIR]
  defaults: --claude-root ~/.claude, --skills-root ~/ora-skills (the canon's home)
"""
import glob
import json
import os
import re
import sys
from collections import namedtuple

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CANON_NAME = "target-markets.json"

CLAUDE_GLOBS = (
    os.path.join("agents", "*.md"),
    os.path.join("projects", "*", "memory", "*.md"),
    # Added 2026-11-06 (Gabriel, REFUTE round 1 C9): ora-am-brief's inline C.5.5 box screen restated the
    # holdings states as the box geography, and it is the live 06:00 broker filter.
    os.path.join("scheduled-tasks", "*", "SKILL.md"),
)
# ops_decision_log.md is NOT skipped: it holds standing answers updated in place (REFUTE 2026-11-06), so its
# "Targeting: all 10 canonical clusters" owner-outreach line is a live answer the count rule should surface.
SKIP_NAMES = {"event_log.md", "open-items-tracker.md", "open-items-tracker-history.md",
              "deal-decision-ledger.md", "disposition-ledger.md"}
SKIP_NAME_RE = re.compile(r"^(?:event_log_\d{4}-\d{2}-\d{2}|CHANGELOG.*)\.md$", re.I)
# Retired and in-progress folders hold no live doctrine (same rule as buybox-drift-probe.py).
_PRUNE_EXACT = ("_archive", "_staging")
_PRUNE_PREFIX = ("_archive_", "_staging_")

# --------------------------------------------------------------------------- ported verbatim
# From ora-skills tools/doctrine_consistency.py (target-geography check) on PR #215's branch
# claude/ora-skills-review-0bf6a8 (unmerged), 2026-11-05.

US_STATES = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO '
                'MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
STATE_NAMES = {'ohio': 'OH', 'maryland': 'MD', 'indiana': 'IN', 'wisconsin': 'WI', 'missouri': 'MO',
               'kansas': 'KS', 'michigan': 'MI', 'virginia': 'VA', 'iowa': 'IA', 'kentucky': 'KY',
               'illinois': 'IL', 'tennessee': 'TN'}
NUMBER_WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
                'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
                'fourteen': 14, 'fifteen': 15}
LOOKBACK = 160   # 'target' may come this far before the first state named
LOOKAHEAD = 40   # or this close after the last one ("... TN are ORA's target states")

_TARGET_GEO = re.compile(
    r"\btarget[- ](?:markets?|states?|clusters?|geograph\w*)\b|\b(?:ORA|we|the firm|it)\s+targets?\b", re.I)
# Changed from the port: the port's `owns?` also matched the ADJECTIVE "own" ("on its own account", "its own
# box") and vetoed real target claims (REFUTE 2026-11-05, O2). "own" after a possessive or "on" is the
# adjective; any other "own" is still the verb ("we own property in ...").
_HOLDINGS = re.compile(
    r"\b(?:holds?|holdings|owns|owned|spans)\b"
    r"|(?<!its )(?<!their )(?<!our )(?<!his )(?<!her )(?<!my )(?<!your )(?<!'s )(?<!’s )(?<!on )\bown\b", re.I)
_STATE_TOKEN = re.compile(r'\b[A-Z]{2}\b')
_STATE_NAME = re.compile(r'\b(%s)\b' % '|'.join(STATE_NAMES), re.I)
# Changed from the port: a digit run inside a date, version or range ("2026-10-01", "v1.14", "1/2")
# is not a subset count. The port read "10" in "- 2026-10-01 standing rule: ORA targets ..." as
# "ten clusters" and dropped the line.
_COUNT_TOKEN = re.compile(r'(?<![\d/.\-])\b(\d{1,2}|%s)\b(?![\d/\-])' % '|'.join(NUMBER_WORDS), re.I)
_HISTORY_HEADING = re.compile(
    r'^(#{1,6})\s.*\b(changelog|change log|version history|revision history|release notes)\b', re.I)
_HEADING = re.compile(r'^(#{1,6})\s')
_VERSION_LINE = re.compile(r'^\s*(?:[-*]\s+|\|\s*)?\*{0,2}v\d+\.\d+\b')

# --------------------------------------------------------------------------- added 2026-11-05
# The port's anchors missed all three live defects (see the module docstring). These widen what
# counts as "this line presents ORA's target geography", nothing else.

# A date token followed directly by changelog punctuation ("- 2026-11-05: ..."), as in
# buybox-drift-probe.py. "- 2026-11-01 standing rule: ..." is a live rule, not history.
_DATE_LEAD = re.compile(r"^[\s|>*_`\-+]*\d{4}-\d{2}-\d{2}[*_`]*\s*[(:|–—]")
# A verb whose subject is ORA anchors its whole clause, at any distance before the list.
_SUBJECT = r"\b(?:ORA|we|the firm|it)(?:\s+(?:is|are)|['’](?:s|re))?\s+"
_TARGET_VERB = re.compile(_SUBJECT + r"(?:targets?|targeting)\b", re.I)
_BUY_VERB = re.compile(
    _SUBJECT + r"(?:buys|buying|acquires|acquiring|sources|sourcing|pursues|pursuing|invests\s+in|investing\s+in)\b"
    r"|\bbuyers?\s+(?:working|buying|active|focused)\b", re.I)
# A criterion label leading the line: "- **Geography:**", "**Geography** OH", "| Geo |", "In-box geography:",
# "1. Target geography:", "- ORA box:", "ORA's acquisition box:", "**Buy-box:**". "Markets:" is deliberately
# absent: in ORA prose it names the holdings footprint as often as a target set (memory/firm.md), so it is
# not guessed at.
_LABEL = re.compile(
    r"^\s*(?:[-*+>]\s+|\d+[.)]\s+|\|\s*)?[*_`]*\s*"
    r"(?P<label>(?:(?:target|acquisition|in[- ]box|buy[- ]?box)\s+)?geo(?:graph(?:y|ies))?|geographic\s+focus"
    r"|(?:the\s+)?(?:ORA(?:['’]s)?\s+)?(?:acquisition\s+|buy[- ]?)?box)"
    r"(?:[*_`]*\s*(?::|\||—|–|\s-\s)|(?:\*\*|__)(?=\s))", re.I)
# A count is a SUBSET only when it says so: "five of ten target clusters", "the six established target
# clusters". A bare count ("Seven target states: ...") claims to be the whole set and is checked like one
# (REFUTE 2026-11-05, C6). The port vetoed any count below the cluster total.
_SUBSET_WORD = re.compile(
    r"\b(?:of|established|entry(?:[- ]phase)?|beachhead|priority|core|tier|satellites?|new|other|remaining)\b",
    re.I)

# --------------------------------------------------------------------------- added 2026-11-06
# COUNT CLAIMS. ora-deal-sourcing-scan v2.14's STEP 1 read "For each of the ten clusters, web-search ..." and
# its fallback block "TEN clusters: Columbus OH, ... LOUISVILLE KY." spanned three lines, while the canon held
# eleven. Neither line names five states, so the geography rule passed the file and Chicago-Greater Cook
# County IL went unscanned. A count is a whole-set claim when it is "<N> [target|canonical|acquisition]
# clusters|markets|metros" AND it is marked as the whole set: a determiner just before it ("the", "all",
# "each of the", "ORA's", "our", "its"), a colon right after ("TEN clusters:"), or a matrix sign right after
# ("ten markets × F1"). "five OF ten target clusters", "the other nine clusters", "six established clusters",
# "the 10th cluster" and "nine market agents" are not claims. A bare "markets"/"metros" (no target/canonical/
# acquisition word) is NOT counted: on the 2026-11-06 live tree it read "the 55 markets" (oxford-edge), "each of
# the 5 markets" (ora-entry-market-scan's entry subset) and two dated facts as drift, and caught nothing real.
# Known gap, so: "all ten markets" and "ten markets × F1" pass; write "clusters" or "target markets".
_COUNT_CLAIM = re.compile(
    r"(?<![\d/.\-])\b(?P<n>\d{1,2}|%s)\b(?![\d/\-])\s+(?P<mod>(?:target|canonical|acquisition)[- ])?"
    r"(?P<noun>clusters|markets|metros)\b(?P<tail>\s*:|\s+[×x]\s)?" % '|'.join(NUMBER_WORDS), re.I)
_WHOLE_SET_LEAD = re.compile(
    r"(?:\b(?:the|all|each\s+of\s+the|every\s+one\s+of\s+the|our|its)|\bORA['’]s)\s+$", re.I)
# A list introduced by a count claim may run this many physical lines past the claim (the scan's ran three).
LIST_MAX_LINES = 8


# A '.' after one of these is an abbreviation, not a sentence end ("Washington D.C. / Baltimore",
# "incl. St. Charles"). Two-letter state codes are NOT here: "... LOUISVILLE KY." ends the list. Nor are
# words that commonly END a sentence ("etc.", "Cook Co.", "Inc.", "no."): reading past them let the next
# sentence supply a cluster the list omitted (REFUTE 2026-11-06, N1) -- fail-open, so they stay out.
_ABBREVIATIONS = {'st', 'mt', 'ft', 'incl', 'approx', 'vs', 'e.g', 'i.e', 'd.c', 'u.s', 'n', 's', 'e', 'w'}


def _list_after(lines, index, col, parens=True):
    """Text of the list that starts at lines[index][col:], continued across following lines until a sentence
    end ('.' before whitespace or end of line, outside parentheses, not after an abbreviation), a blank line
    or LIST_MAX_LINES. If a '(' never closes before the stop, the read is redone ignoring parentheses, so an
    unbalanced paren cannot swallow the next sentence (REFUTE 2026-11-06, C6)."""
    parts, depth = [], 0
    for i in range(index, min(len(lines), index + LIST_MAX_LINES)):
        seg = lines[i][col:] if i == index else lines[i]
        if i > index and not seg.strip():
            break
        for j, ch in enumerate(seg):
            if parens and ch == '(':
                depth += 1
            elif parens and ch == ')':
                depth = max(0, depth - 1)
            elif ch == '.' and depth == 0 and (j + 1 == len(seg) or seg[j + 1].isspace()):
                words = seg[:j].split()
                token = words[-1].lstrip('(["\'').lower() if words else ''
                if token in _ABBREVIATIONS:
                    continue
                parts.append(seg[:j])
                return ' '.join(parts)
        parts.append(seg)
    if parens and depth > 0:
        return _list_after(lines, index, col, parens=False)
    return ' '.join(parts)


def count_claims(lines, index, clusters):
    """[message] for every whole-set cluster count on lines[index] that disagrees with the canon, and for
    every list such a claim introduces ("N clusters: ...", read across lines) that omits a cluster."""
    line = lines[index]
    problems = []
    for m in _COUNT_CLAIM.finditer(line):
        n = _as_int(m.group('n'))
        lead = _WHOLE_SET_LEAD.search(line[:m.start()])
        tail = m.group('tail')
        if not (lead or tail):
            continue
        if not m.group('mod') and m.group('noun').lower() != 'clusters':
            continue
        if n != clusters.count:
            problems.append('states %d clusters as the whole target set; target-markets.json has %d'
                            % (n, clusters.count))
        if tail and tail.strip() == ':':
            listed = _list_after(lines, index, m.end())
            named = [name for name, tokens in clusters.names
                     if any(re.search(r'\b%s\b' % re.escape(t), listed, re.I) for t in tokens)]
            if 4 <= len(named) < len(clusters.names):
                absent = [name for name, _ in clusters.names if name not in named]
                problems.append('cluster list after "%s" names %d of %d clusters; missing %s'
                                % (m.group(0).strip(), len(named), len(clusters.names), ', '.join(absent)))
    return problems


Clusters = namedtuple('Clusters', 'count states established allowed_states names')


def _as_int(token):
    token = token.lower()
    return NUMBER_WORDS[token] if token in NUMBER_WORDS else int(token)


def _phrase(text):
    return ' '.join(text.lower().split())


def _state_positions(line):
    hits = [(m.start(), m.group(0)) for m in _STATE_TOKEN.finditer(line) if m.group(0) in US_STATES]
    hits += [(m.start(), STATE_NAMES[m.group(0).lower()]) for m in _STATE_NAME.finditer(line)]
    return sorted(hits)


def _labeled_watch(line, code):
    return bool(re.search(r'\b%s\b\s*[(:-]?\s*watch' % code, line, re.I)
                or re.search(r'\bwatch\w*\b[^.;]{0,25}\b%s\b' % code, line, re.I))


def _clause_start(line, pos):
    """Index where the clause holding `pos` begins: just past the last sentence end ('.', '!' or '?' before
    whitespace) or semicolon that is outside parentheses. deal-recon's Amendment H parenthetical holds a
    semicolon that must not cut "ORA targets" off from its list."""
    start, depth = 0, 0
    for i, ch in enumerate(line[:pos]):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        elif depth == 0 and (ch == ';' or (ch in '.!?' and (i + 1 == len(line) or line[i + 1].isspace()))):
            start = i + 1
    return start


def _anchors_before(line, first):
    """(start, end, kind) for every phrase before the first state that presents the list as ORA's
    target geography. kind 'window' is the port's rule; 'clause' and 'label' are the additions."""
    found = [(m.start(), m.end(), 'window') for m in _TARGET_GEO.finditer(line)
             if first - LOOKBACK <= m.start() < first]
    clause = _clause_start(line, first)
    for rx in (_TARGET_VERB, _BUY_VERB):
        found += [(m.start(), m.end(), 'clause') for m in rx.finditer(line)
                  if clause <= m.start() and m.end() <= first]
    label = _LABEL.match(line)
    if label and label.end() <= first:
        found.append((label.start('label'), label.end(), 'label'))
    return found


def _counted_subset(line, anchor_start, total):
    """True when the words just before the anchor say the list is a subset: a count below the cluster
    total, qualified by "of" or a subset word between the count and the anchor."""
    window = line[max(0, anchor_start - 30):anchor_start]
    m = _COUNT_TOKEN.search(window)
    return bool(m and _as_int(m.group(1)) < total and _SUBSET_WORD.search(window[m.end():]))


def target_geography(line, clusters):
    """[(message, phrase)] when a line presents an incomplete or padded list as ORA's target set."""
    hits = _state_positions(line)
    named = {code for _, code in hits}
    if len(named) < 5 or len(named & set(clusters.established)) < 4:
        return []
    first, last = hits[0][0], hits[-1][0]
    before = _anchors_before(line, first)
    after = [m for m in _TARGET_GEO.finditer(line) if last < m.start() <= last + LOOKAHEAD]
    if before:
        start, end, kind = max(before, key=lambda a: (a[1], a[0]))  # the anchor nearest the list
        if _HOLDINGS.search(line[end:first]):
            return []
        anchor_start, counted = start, kind != 'label'  # a label carries no subset count
    elif after:
        if _HOLDINGS.search(line[last:after[0].start()]):
            return []
        anchor_start, counted = after[0].start(), True
    else:
        return []
    if counted and _counted_subset(line, anchor_start, clusters.count):
        return []
    problems = []
    missing = sorted(set(clusters.states) - named)
    if missing:
        problems.append('target geography omits cluster states %s (target-markets.json)' % ', '.join(missing))
    extra = sorted(code for code in named - set(clusters.allowed_states)
                   if not _labeled_watch(line, code))  # "...; TN watch" names a watch market, not a target
    if extra:
        problems.append('target geography lists %s, which no cluster in target-markets.json covers'
                        % ', '.join(extra))
    named_clusters = [name for name, tokens in clusters.names
                      if any(re.search(r'\b%s\b' % re.escape(t), line, re.I) for t in tokens)]
    if len(named_clusters) >= 4 and len(named_clusters) < len(clusters.names):
        absent = [name for name, _ in clusters.names if name not in named_clusters]
        problems.append('target geography names %d of %d clusters; missing %s'
                        % (len(named_clusters), len(clusters.names), ', '.join(absent)))
    return [(p, _phrase(p)) for p in problems]


def live_lines(text):
    """(line number, line) for lines outside changelog sections, version bullets and index rows,
    and (added) date-led history bullets."""
    history_level = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if history_level is not None and level <= history_level:
                history_level = None
            if _HISTORY_HEADING.match(line):
                history_level = level
                continue
        if history_level is not None or _VERSION_LINE.match(line) or _DATE_LEAD.match(line):
            continue
        yield number, line


def _cluster_tokens(market):
    primary = re.split(r'\s*[–—(-]\s*|\s+[A-Z]{2}(?:/[A-Z]{2})*\s*$', market)[0].strip()
    extra = re.findall(r'\(([^)]*)\)', market)
    tokens = [primary] + [t.strip() for part in extra for t in part.split('/')]
    return [t for t in tokens if len(t) >= 4]


# --------------------------------------------------------------------------- canon

def load_canon(skills_root):
    """(Clusters, version) from <skills_root>/target-markets.json. Raises on anything it cannot
    trust (unreadable, not JSON, no non-empty clusters list, a cluster without a market and a valid
    two-letter state): a probe that silently read a broken canon as 'no clusters' would pass
    everything."""
    with open(os.path.join(skills_root, CANON_NAME), 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    clusters = data['clusters']
    if not isinstance(clusters, list) or not clusters:
        raise ValueError('`clusters` is not a non-empty list')
    for c in clusters:
        if not isinstance(c, dict) or not c.get('market') or c.get('state') not in US_STATES:
            raise ValueError('cluster without a market and a two-letter state: %r' % (c,))
    states = sorted({c['state'] for c in clusters})
    established = sorted({c['state'] for c in clusters if c.get('status') == 'established'})
    allowed = set(states)
    names = []
    for c in clusters:
        market = c['market']
        allowed.update(code for code in re.findall(r'\b[A-Z]{2}\b', market) if code in US_STATES)
        names.append((market, _cluster_tokens(market)))
    return Clusters(len(clusters), states, established or states, sorted(allowed), names), data.get('version', '?')


def load_clusters(skills_root):
    return load_canon(skills_root)[0]


# --------------------------------------------------------------------------- scanning

def scan_text(text, clusters):
    """[(lineno, message, line), ...], one per problem, for every drifting target-geography line."""
    out = []
    lines = text.splitlines()
    history = history_paragraph_lines(lines)
    for number, line in live_lines(text):
        for message, _phrase_key in target_geography(line, clusters):
            out.append((number, message, line))
        if number in history:
            continue
        for message in count_claims(lines, number - 1, clusters):
            out.append((number, message, line))
    return out


# A task-spec changelog paragraph opens, at column 0, with "vX.Y — " (em/en dash or " - ").
_CHANGELOG_PARA = re.compile(r"^v\d+\.\d+\s+(?:[—–]|-)\s")


def history_paragraph_lines(lines):
    """Line numbers (1-based) of every line in a task-spec changelog paragraph: one whose FIRST line (previous
    line blank, a heading, or the file start) opens at column 0 with "vX.Y — ", running to the next blank line
    or heading. Used by the count rule only: a changelog quoting the old count ("... was disqualified as
    'outside the ten clusters'") is history, and wrapping put the quote on a continuation line live_lines()
    keeps. Deliberately narrow (REFUTE 2026-11-06, C5): the first cut flipped to history at ANY version- or
    date-led line, so a wrapped "2026-10-05: ..." mid-paragraph hid 81 live lines of the scan spec (all of
    STEP 1B-A/1B-B). Indented "  v2.8 RESOLUTION:" notes, "vX.Y note:" lines and date-led bullets do not open
    a history paragraph (date-led bullets are already skipped line by line in live_lines())."""
    out, in_history, para_start = set(), False, True
    for number, line in enumerate(lines, 1):
        if not line.strip() or _HEADING.match(line):
            in_history, para_start = False, True
            continue
        if para_start:
            in_history = bool(_CHANGELOG_PARA.match(line))
            para_start = False
        if in_history:
            out.add(number)
    return out


def _is_pruned(path, root):
    return any(part in _PRUNE_EXACT or part.startswith(_PRUNE_PREFIX)
               for part in os.path.relpath(path, root).split(os.sep)[:-1])


def iter_targets(claude_root):
    for pat in CLAUDE_GLOBS:
        for path in sorted(glob.glob(os.path.join(claude_root, pat))):
            name = os.path.basename(path)
            if name in SKIP_NAMES or SKIP_NAME_RE.match(name) or _is_pruned(path, claude_root):
                continue
            yield os.path.normpath(path)


def _arg(argv, flag, default):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv):
            print("[ACTION] target-geography-probe: %s needs a value" % flag, file=sys.stderr)
            sys.exit(2)
        val = argv[i + 1]
        if val.startswith("--"):
            print("[ACTION] target-geography-probe: %s got another flag (%s) as its value" % (flag, val),
                  file=sys.stderr)
            sys.exit(2)
        return val
    return default


KNOWN_FLAGS = ("--quiet", "--claude-root", "--skills-root")


def _check_argv(argv):
    """Every token must be a known flag or the value right after a value flag, each flag at most once.
    Anything else -- "--claude-root=X", a typo, a stray positional path -- would otherwise fall back to the
    real roots and report on the wrong tree (REFUTE 2026-11-05, C7)."""
    seen, i = set(), 0
    while i < len(argv):
        a = argv[i]
        if a not in KNOWN_FLAGS:
            print("[ACTION] target-geography-probe: unexpected argument %s (use '--flag value')" % a,
                  file=sys.stderr)
            sys.exit(2)
        if a in seen:
            print("[ACTION] target-geography-probe: %s given twice" % a, file=sys.stderr)
            sys.exit(2)
        seen.add(a)
        i += 1 if a == "--quiet" else 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    _check_argv(argv)
    quiet = "--quiet" in argv
    claude_root = _arg(argv, "--claude-root", os.path.join(HOME, ".claude"))
    skills_root = _arg(argv, "--skills-root", os.path.join(HOME, "ora-skills"))
    for root in (claude_root, skills_root):
        if not os.path.isdir(root):
            print("[ACTION] target-geography-probe: scan root missing: %s" % root, file=sys.stderr)
            sys.exit(2)

    canon_path = os.path.join(skills_root, CANON_NAME)
    try:
        clusters, version = load_canon(skills_root)
    except Exception as e:
        print("[ACTION] target-geography-probe: cannot trust canon %s: %s" % (canon_path, e), file=sys.stderr)
        sys.exit(2)

    targets = list(iter_targets(claude_root))
    # An existing but empty/wrong root would scan nothing and read as clean.
    if not targets:
        print("[ACTION] target-geography-probe: no agents/, memory or scheduled-task files under %s -- wrong root?"
              % claude_root, file=sys.stderr)
        sys.exit(2)
    findings = []
    for path in targets:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as e:
            print("[ACTION] target-geography-probe could not read %s: %s" % (path, e), file=sys.stderr)
            sys.exit(2)
        for ln, message, line in scan_text(text, clusters):
            findings.append((path, ln, message, line.strip()[:160]))

    if findings:
        print("TARGET-GEOGRAPHY DRIFT DETECTED (%d) -- canon: %s v%s, %d clusters (%s); ORA's target "
              "geography is this cluster set, not its holdings states:"
              % (len(findings), canon_path, version, clusters.count,
                 "; ".join(name for name, _ in clusters.names)))
        for path, ln, message, txt in findings:
            print("  %s:%d  %s" % (path, ln, message))
            print("        | %s" % txt)
        sys.exit(1)

    if not quiet:
        print("target-geography-probe OK -- %d files scanned, target-geography statements consistent with "
              "%s v%s (%d clusters)." % (len(targets), canon_path, version, clusters.count))
    sys.exit(0)


if __name__ == "__main__":
    main()
