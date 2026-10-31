"""
institutional_owners.py — ORA county-parcel-screen canonical institutional/self-deal
exclusion module (v1.0, 2026-06-09).

Replaces the ad-hoc substring regex used in market runs 1-8. Motivated by two audit
findings: (a) fund-style naming slipped the brand list — 'G&I XI BKG POOL III LLC'
(DRA Advisors fund, Kent Co MI 2026-06-09) was only caught by a human-pattern read;
(b) bare-token matching false-positived — 'DUKE COMBINED LLC' (Henrico, likely a
local LLC, NOT Duke Realty which was absorbed by Prologis 2022), '2665 N BROOKFIELD
RD' (street name), 'FREDERICK WOLFGANG INDUS' (truncated INDUSTRIES), 'MAHOOZI VA
PROPERTIES' (mail on Brookfield Corporate Dr).

API:
  screen_owner(name)        -> ('EXCLUDE', canonical) | ('VERIFY', canonical) | (None, None)
  screen_mail(name_or_addr) -> same tiers, with street-name guards (mail hit = lead
                               for affiliate clustering, F9 agent-mail, NOT auto-exclude)
  ora_never_call(name)      -> ('ORA-SELF', m) | ('NEVER-CALL', m) | (None, None)
Doctrine: EXCLUDE = drop from prospect pool. VERIFY = keep, flag VERIFY-INSTITUTIONAL,
adjudicate before outreach (the DUKE COMBINED lesson: never silently drop on a weak token).
ORA-SELF (per Gabriel 2026-06-10): KEEP + flag ORA-AFFILIATED, never drop — 'OXFORD CAMPUS
I LLC' mail-name FP showed drops lose real prospects. NEVER-CALL (deal counterparties) = drop.
"""
import datetime
import json
import os
import re

def _norm(s):
    s = re.sub(r'[^A-Z0-9& ]', ' ', str(s or '').upper())
    return re.sub(r'\s+', ' ', s).strip()

# ---- TIER 1: unambiguous brands / entities. Word-boundary regex, owner fields. ----
TIER1 = [
    (r'\bPROLOGIS\b',                 'Prologis'),
    (r'\bSTAG\s+(INDUSTRIAL|HOLDINGS?)\b|\bSTAG\s+[IVXL]+\b', 'STAG Industrial'),
    (r'\bEXETER\s+(\d|PROPERTY|PORTFOLIO|[A-Z]+\s+(LP|LLC))', 'EQT Exeter (fund naming: EXETER + number/asset)'),
    (r'\bEQT\s+EXETER\b|\bEQT\s+RE\b', 'EQT Exeter'),
    (r'\bLINK\s+LOGISTICS\b',         'Link Logistics (Blackstone)'),
    (r'\bBLACKSTONE\b|\bBREIT\b',     'Blackstone'),
    (r'\bBECKNELL\b',                 'Becknell Industrial'),
    (r'\bFIRST\s+INDUSTRIAL\b',       'First Industrial Realty'),
    (r'\bDRA\s+ADVISORS\b',           'DRA Advisors'),
    (r'\bG\s*&\s*I\s+[IVXL]+\b',      'DRA Advisors (G&I fund series)'),   # G&I XI BKG POOL III
    (r'\bAMBROSE\s+(PROP|PG|MONON|[A-Z]*\s*(LLC|LP))', 'Ambrose Property Group'),
    (r'\bDUKE\s+REALTY\b',            'Duke Realty (now Prologis)'),
    (r'\bCENTERPOINT\s+PROP',         'CenterPoint Properties'),
    (r'\bICON\s+MARS\b',              'ICON industrial fund pool (RVA 2026-06)'),
    (r'\bDERMODY\b',                  'Dermody Properties'),
    (r'\bIDI\s+LOGISTICS\b',          'IDI Logistics'),
    (r'\bHILLWOOD\b',                 'Hillwood'),
    (r'\bSCANNELL\s+PROP',            'Scannell Properties'),
    (r'\bNORTHPOINT\s+DEV',           'NorthPoint Development'),
    (r'\bVANTRUST\b',                 'VanTrust Real Estate'),
    (r'\bTERRENO\b',                  'Terreno Realty'),
    (r'\bREXFORD\s+INDUSTRIAL\b',     'Rexford Industrial'),
    (r'\bBROOKFIELD\s+(PROPERTIES|ASSET|LOGISTICS|FUND)\b', 'Brookfield'),
    (r'\bCLARION\s+PARTNERS\b',       'Clarion Partners'),
    (r'\bGLP\s+(US|CAPITAL|FUND)\b',  'GLP'),
    (r'\bILPT\b',                     'Industrial Logistics Properties Trust'),
    (r'\bAMAZON\.?\s*COM\b|\bAMAZON\s+(LOGISTICS|FULFILLMENT|DATA)\b', 'Amazon'),
    (r'\bCONSUMERS\s+(ENERGY|POWER)\b', 'Consumers Energy (MI utility; 386 Kent parcels 2026-06)'),
    (r'\bSTEELCASE\b',                'Steelcase (GR owner-occupier institutional)'),
    (r'\b(MILLERKNOLL|HERMAN\s+MILLER)\b', 'MillerKnoll'),
    (r'\bAIC\s+(INCOME\s+)?FUND\b|\bAIC\s+VENTURES\b', 'AIC Ventures (Austin TX sale-leaseback funds; AIC INCOME FUND CROSSROADS had no numeral — caught retro-sweep 2026-06-10)'),
    (r'\bNL\s+VENTURES\b',            'NL Ventures (AIC Ventures net-lease fund series; NL VENTURES XII GROVEPORT slipped the X&Y-only roman rule — Columbus 2026-07-24)'),
    (r'\bMERITEX\b',                  'Meritex (Minneapolis institutional industrial owner — Columbus 2026-07-24)'),
]

# ---- Fund-morphology patterns (generic): EXCLUDE tier, they exist only as fund vehicles ----
FUND_MORPH = [
    (r'\b[A-Z]{1,4}\s*&\s*[A-Z]{1,4}\s+[IVXL]{1,6}\b.*\b(POOL|PORTFOLIO|FUND|LLC|LP)\b', 'fund-series morphology (X&Y + roman numeral)'),
    (r'\b(BKG|BULK|CORE|VALUE[- ]ADD)\s+POOL\s+[IVXL0-9]+\b', 'pool-numbered fund vehicle'),
    (r'\b(FUND|REIT|PORTFOLIO)\s+[IVXL]{2,6}\b\s*(LLC|LP)?', 'numbered fund/REIT vehicle'),
]

# ---- TIER 2: VERIFY — ambiguous tokens, never auto-exclude (DUKE COMBINED lesson) ----
TIER2 = [
    (r'\bDUKE\b',     'bare DUKE (Duke Realty defunct 2022 — most bare-DUKE LLCs are local; verify)'),
    (r'\bLINK\b',     'bare LINK (only LINK LOGISTICS is institutional)'),
    (r'\bICON\b',     'bare ICON (specific pools tier-1; generic icon-named LLCs common)'),
    (r'\bEXETER\b',   'bare EXETER (street/place name common; fund naming is EXETER+number)'),
    (r'\bINDUS\b(?!TR)', 'INDUS token (often truncated INDUSTRIES in county exports)'),
    (r'\bTPG\b',      'TPG (also common local initials)'),
    (r'\bEQT\b',      'bare EQT (also oil/gas and local initials)'),
    (r'\bGOODMAN\b',  'Goodman Group vs personal surname — verify'),
    (r'\b(VENTURES|CAPITAL|PARTNERS|REALTY|PROPERTIES|HOLDINGS|INVESTORS|EQUITIES)\s+(?:[IVX]{2,5}|[0-9]{1,2})\b',
     'fund-series morphology: entity-word + standalone series numeral (LIBERTY CAPITAL PARTNERS III, NL VENTURES XII — Columbus 2026-07-24; VERIFY not EXCLUDE, local sponsors also number their vehicles)'),
]

# ---- Tax-agent mail (F9 flag — mail is agent, not principal; never an exclusion) ----
AGENT_MAIL = [
    (r'\bRYAN\s+LLC\b', 'Ryan LLC'), (r'\bALTUS\s+GROUP\b', 'Altus Group'),
    (r'\bPARADIGM\s+TAX\b', 'Paradigm Tax Group'), (r'\bMARVIN\s+F\s+POER\b', 'Marvin F. Poer'),
]

# Street-suffix guard for MAIL-field matching (the '2665 N BROOKFIELD RD' lesson):
_ST_SUFFIX = r'(RD|ROAD|DR|DRIVE|ST|STREET|AVE|AVENUE|LN|LANE|BLVD|CT|COURT|CIR|PKWY|PARKWAY|PL|WAY|HWY|TRL)'

# ---- ORA self / never-call ----
# Counterparty patterns live in the UNTRACKED data/pipeline-guard.local.json
# (externalized 2026-06-11 — deal counterparty names never live in this tracked
# file). It is gitignored on purpose and exists in exactly ONE place on this
# machine, under ~/.claude/skills/ — NOT in the ora-skills repo checkout and NOT
# in the AppData plugin bundle.
#
# FAIL-LOUD, hardened 2026-09-18. This used to resolve the guard RELATIVE to
# __file__ and, on failure, warn and fall back to an ORA-self-only floor. That
# relative path resolves to nothing whenever the skill executes from any copy
# other than ~/.claude/skills/, so the fallback fired in normal use and its
# warning went unacted-on: the 2026-09-18 Jackson MO ring screen shipped a call
# list screened against ORA-self patterns only (…JacksonMO_Summary_v01.md, the
# 'honest limits' item on the degraded floor), and the same-day
# Howard MD run recorded that the relative path "resolves into the plugin cache,
# where the file does not exist, and would have degraded the floor silently".
# A degraded floor is no longer an allowed run mode: "no match" from a degraded
# screen is not the same as screened. Load the CANONICAL ABSOLUTE PATH or raise.
_GUARD_FILE = os.environ.get(
    'ORA_PIPELINE_GUARD',
    r'C:\Users\Owner\.claude\skills\county-parcel-screen\data\pipeline-guard.local.json')


class PipelineGuardUnavailable(RuntimeError):
    """The never-call counterparty floor could not be loaded. STOP the run."""


def guard_evidence():
    """Path / mtime (UTC) / entry counts, for the workbook README and run summary.

    Every deliverable must record this as proof the floor was actually applied
    (SKILL.md 'Counterparty floor' rule 4). Reports BOTH counts: never_call_names
    is what callers pass to the workflow, never_call_patterns is what THIS module
    actually screens on — they are not the same list and a deliverable that cites
    only the former can look screened while the pattern list is empty.

    mtime is UTC ISO-8601 with a trailing Z, matching test-pipeline-match.mjs, so
    the same guard file reads identically whichever consumer recorded it.
    """
    try:
        st = os.stat(_GUARD_FILE)
    except OSError as e:
        raise PipelineGuardUnavailable(
            'guard %r vanished after load (%s) -- STOP; do not ship a deliverable '
            'whose floor cannot be evidenced.' % (_GUARD_FILE, e))
    return {
        'path': os.path.abspath(_GUARD_FILE),
        'modified': datetime.datetime.fromtimestamp(
            st.st_mtime, datetime.timezone.utc).isoformat(timespec='milliseconds'
                                                          ).replace('+00:00', 'Z'),
        'never_call_names': len(_GUARD_RAW.get('never_call_names', [])),
        'never_call_patterns': len(_GUARD_RAW.get('never_call_patterns', [])),
    }


def _load_guard():
    try:
        with open(_GUARD_FILE, encoding='utf-8') as f:
            g = json.load(f)
    except Exception as e:
        raise PipelineGuardUnavailable(
            'never-call counterparty floor UNAVAILABLE -- cannot load %r (%s).\n'
            'This is a STOP, not a warning: do not score, rank, or produce any '
            'call list, workbook or summary. The guard file is untracked and '
            'lives only at the canonical absolute path above; set '
            'ORA_PIPELINE_GUARD to override. Degraded ORA-self-only screening '
            'was removed 2026-09-18 (Jackson MO run shipped a degraded list).'
            % (_GUARD_FILE, e))
    # Gate on BOTH lists. never_call_patterns is what ora_never_call() below
    # actually screens on; never_call_names is what callers hand to
    # parcel-screen-fanout.js. A guard carrying one but not the other passes a
    # single-key check while screening nothing on the other path.
    missing = [k for k in ('never_call_names', 'never_call_patterns') if not g.get(k)]
    if missing:
        raise PipelineGuardUnavailable(
            'never-call counterparty floor INCOMPLETE in %r -- empty or absent: %s. '
            'A guard missing either list screens nothing on that path. STOP the run.'
            % (_GUARD_FILE, ', '.join(missing)))
    return (list(g.get('ora_self_patterns', [])),
            [tuple(x) for x in g.get('never_call_patterns', [])],
            g)


ORA_SELF, NEVER_CALL, _GUARD_RAW = _load_guard()

def screen_owner(name):
    s = _norm(name)
    if not s: return (None, None)
    for pat, canon in TIER1:
        if re.search(pat, s): return ('EXCLUDE', canon)
    for pat, canon in FUND_MORPH:
        if re.search(pat, s): return ('EXCLUDE', canon)
    for pat, canon in TIER2:
        if re.search(pat, s): return ('VERIFY', canon)
    return (None, None)

def screen_mail(text):
    """Mail name/address: institutional brand at a mail address = affiliate-cluster
    lead (VERIFY), tax-agent = F9. Street-suffix guard suppresses place-name FPs."""
    s = _norm(text)
    if not s: return (None, None)
    for pat, canon in AGENT_MAIL:
        if re.search(pat, s): return ('F9-AGENT-MAIL', canon)
    for pat, canon in TIER1 + [(p, c) for p, c in TIER2]:
        m = re.search(pat, s)
        if m and not re.search(m.group(0).split()[0] + r'\s+\w*\s*' + _ST_SUFFIX + r'\b', s):
            return ('VERIFY', canon)
    return (None, None)

def ora_never_call(name):
    s = _norm(name)
    if not s: return (None, None)
    for pat in ORA_SELF:
        m = re.search(pat, s)
        if m: return ('ORA-SELF', m.group(0))
    for pat, canon in NEVER_CALL:
        if re.search(pat, s): return ('NEVER-CALL', canon)
    return (None, None)

if __name__ == '__main__':
    cases = [
        # (name, expected_tier)
        ('PROLOGIS TARGETED US LOGISTICS FUND LP', 'EXCLUDE'),
        ('G&I XI BKG POOL III LLC', 'EXCLUDE'),            # the Kent miss
        ('STAG INDUSTRIAL HOLDINGS LLC', 'EXCLUDE'),
        ('EXETER 8750 PARK CENTRAL LLC', 'EXCLUDE'),
        ('ICON MARS OWNER POOL 3 VA LLC', 'EXCLUDE'),
        ('AIC INCOME FUND CROSSROADS LLC', 'EXCLUDE'),  # the Johnson Co A-tier miss (no numeral)
        ('AIC INCOME FUND II FRANKLIN LLC', 'EXCLUDE'),
        ('FIRST INDUSTRIAL LP', 'EXCLUDE'),
        ('DUKE REALTY LIMITED PARTNERSHIP', 'EXCLUDE'),
        ('DUKE COMBINED LLC', 'VERIFY'),                   # the Henrico FP-direction
        ('LINK PROPERTIES OF RICHMOND LLC', 'VERIFY'),
        ('FREDERICK WOLFGANG INDUS', 'VERIFY'),            # truncation
        ('SMP PARTNERSHIP LLP', None),
        ('TNT KALAMAZOO ENTERPRISES LLC', None),
        ('INDUSTRIAL MILE PROPERTIES LLC', None),          # INDUSTR... must NOT hit INDUS token
        ('BROOKFIELD PROPERTIES LOGISTICS LP', 'EXCLUDE'),
        ('MAHOOZI VA PROPERTIES LLC', None),
    ]
    bad = 0
    for name, want in cases:
        got, canon = screen_owner(name)
        ok = got == want
        bad += (not ok)
        print(f'{"OK " if ok else "FAIL"} {name!r:48} -> {got} ({canon})')
    m_cases = [('2665 N BROOKFIELD RD', None), ('C/O PARADIGM TAX GROUP', 'F9-AGENT-MAIL'),
               ('BROOKFIELD ASSET MGMT, 250 VESEY ST', 'VERIFY')]
    for t, want in m_cases:
        got, canon = screen_mail(t)
        ok = got == want
        bad += (not ok)
        print(f'{"OK " if ok else "FAIL"} MAIL {t!r:42} -> {got} ({canon})')
    # owner_test_cases come from the local guard file (counterparty names never
    # live in this tracked file). As of 2026-09-18 an absent/empty guard raises
    # PipelineGuardUnavailable at import, so reaching here means it loaded.
    ev = guard_evidence()
    # This line is the template a run copies into its workbook README / summary,
    # so it carries BOTH counts (SKILL.md rule 4).
    print('GUARD %(path)s  modified=%(modified)s  never_call_names=%(never_call_names)d'
          '  never_call_patterns=%(never_call_patterns)d' % ev)
    o_cases = [tuple(c) for c in _GUARD_RAW.get('owner_test_cases', [])]
    if not o_cases:
        print('NOTE: guard loaded but carries no owner_test_cases')
    for t, want in o_cases:
        got, m = ora_never_call(t)
        ok = got == want
        bad += (not ok)
        print(f'{"OK " if ok else "FAIL"} ORA {t!r:42} -> {got} ({m})')
    print('SELF-TEST', 'PASS' if bad == 0 else f'FAIL ({bad})')
