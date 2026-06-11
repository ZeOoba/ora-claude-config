import re

# ESTATE_V2 — corrected estate-signal pattern (2026-06-05)
# Principle: a true estate signal is a PERSON acting in a fiduciary/succession
# capacity, not a company with 'estate' in its trade name.

# Hard exclusions: banks/trust companies acting as institutional trustees
BANKISH = re.compile(r'\bTRUST (COMPANY|CO|CORP|CORPORATION)\b|\bBANK\b|\bNATIONAL ASSOCIATION\b|\bN A\b')

# Institutional / corporate tokens — a name containing these is NOT a personal fiduciary
INSTITUTIONAL = re.compile(
    r'\b(LLC|L L C|INC|LTD|LLP|LP|CORP|CORPORATION|CO|COMPANY|COMPANIES|HOLDING|HOLDINGS|'
    r'PROPERTIES|PROPERTY|REALTY|GROUP|ENTERPRISE|ENTERPRISES|INVESTMENT|INVESTMENTS|INVESTORS|'
    r'VENTURE|VENTURES|PARTNERS|PARTNERSHIP|ASSOCIATES|ASSOCIATION|ASSN|MANAGEMENT|MGMT|'
    r'DEVELOPMENT|CAPITAL|EQUITIES|SERVICES|SOLUTIONS|BUSINESS|'
    r'CHURCH|TEMPLE|SYNAGOGUE|PARISH|DIOCESE|CONGREGATION|MINISTRIES|MINISTRY|LODGE|MASONIC|'
    r'UNION|LOCAL|IBEW|TOWNSHIP|TWP|CITY|COUNTY|STATE|BOARD|UNIVERSITY|SCHOOL|SCHOOLS|COLLEGE|'
    r'AUTHORITY|COMMISSION|DISTRICT|CONSERVANCY|COMMUNITY|FOUNDATION|INSTITUTE|VETERANS|AFFAIRS|'
    r'REAL ESTATE|ESTATES)\b')

# Strong personal-fiduciary markers
STRONG = re.compile(
    r'\b(?<!REAL )ESTATE OF\b|\bLIFE ESTATE\b|'
    r'\bEXECUT(OR|ORS|RIX)\b|\bEXRX?\b|'
    r'\bADMINISTRAT(OR|ORS|RIX)\b|\bADMRX?\b|'
    r'\bSUCCESSOR TRUSTEE(S)?\b|'
    r'\bCO (TR|TRS|TTEE|TRUSTEES?)\b|'
    r'\bTRUST (DATED|AGREEMENT)\b|\bDECLARATION OF TRUST\b|'
    r'\b(REVOCABLE|IRREVOCABLE|LIVING|FAMILY|REV|LIV) (TRUST|TR)\b')

TTEE = re.compile(r'\bTTEES?\b')
TRUSTEE = re.compile(r'\bTRUSTEES?\b')

def _norm(name):
    s = re.sub(r'[^A-Z0-9&() ]', ' ', str(name).upper())
    return re.sub(r'\s+', ' ', s).strip()

_STREET_SUFFIX = {'ST', 'STREET', 'AVE', 'AVENUE', 'RD', 'ROAD', 'DR', 'DRIVE', 'LN', 'LANE',
                  'BLVD', 'BOULEVARD', 'PIKE', 'CT', 'COURT', 'CIR', 'CIRCLE', 'HWY', 'HIGHWAY',
                  'RT', 'RTE', 'ROUTE', 'PKWY', 'PARKWAY', 'PL', 'PLACE', 'SQ', 'SQUARE'}

def _personal_prefix(tokens):
    """tokens before TR/TRS look like a personal name: >=2 alpha tokens, no digits,
    and not ending in a street-suffix word ('MAIN STREET TR' = trail, not trustee)"""
    if len(tokens) < 2:
        return False
    if tokens[-1] in _STREET_SUFFIX:
        return False
    return all(t.isalpha() for t in tokens)

def estate_v2(name):
    if name is None:
        return False
    s = _norm(name)
    if not s:
        return False
    if BANKISH.search(s):
        return False                       # bank / trust-company trustee = institutional
    if STRONG.search(s):
        return True                        # ESTATE OF / LIFE ESTATE / EXECUTOR / ADMR / REV-LIV-FAMILY TRUST
    if TTEE.search(s):
        return True                        # TTEE is fiduciary-only usage
    inst = INSTITUTIONAL.search(s) is not None
    if TRUSTEE.search(s) and not inst:
        return True                        # TRUSTEE(S) excluding township/board/church trustees
    if inst:
        return False
    # ' TR' / ' TRS' suffix on a personal-name segment (handles 'A TR & B TR', 'X TR (Y TRUST)',
    # trailing fractional-interest markers '@ 3' and 'ETAL')
    segs = [seg.strip().rstrip(')').strip() for seg in re.split(r'[&(]', s)]
    personal_seg = False
    for seg in segs:
        m = re.search(r'^(.*?)\s(TR|TRS)( \d+| ETAL| ET AL)?$', seg)
        if m and _personal_prefix(m.group(1).split()):
            return True
        toks = seg.split()
        if len(toks) >= 2 and all(t.isalpha() for t in toks) and toks[-1] not in _STREET_SUFFIX:
            personal_seg = True
    # bare 'TR'/'TRS'/'TTEE' segment after '&' alongside a personal-name segment
    # (e.g. 'TSOLOMETES PETER G & TR')
    if personal_seg and any(seg in ('TR', 'TRS', 'TTEE') for seg in segs):
        return True
    # name ending in TRUST / TRUSTEES with personal-looking prefix (e.g. SMITH FAMILY TRUST,
    # JOHNSON 2014 TRUST — year tokens allowed here)
    m = re.search(r'^(.*?)\s?TRUST(EES)?$', s)
    if m:
        toks = [t for t in m.group(1).split() if t not in ('THE', '&')]  # '&' allowed: CHARLES I COLBY & RUTH COLBY TRUST (Polk 2026-06-09 audit)
        if toks and all(t.isalpha() or t.isdigit() for t in toks):
            return True
    return False

def nominal_xfer(saledate, saleprice, cutoff='2021-01-01', thresh=25000):
    """Secondary booster: recent nominal transfer (<$25K since 2021)."""
    import pandas as pd
    try:
        d = pd.to_datetime(saledate)
        p = float(saleprice)
    except Exception:
        return False
    if pd.isna(d) or pd.isna(p):
        return False
    return d >= pd.Timestamp(cutoff) and p < thresh
