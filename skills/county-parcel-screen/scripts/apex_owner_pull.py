"""
apex_owner_pull.py — reusable Oracle APEX owner-recovery module for the ORA
county-parcel-screen pipeline (v1.0, 2026-06-09).

Why: some county CAMA front-ends (Oracle APEX / ORDS, typically Vision or
locally-built apps at <host>/ords/<schema>/f?p=<app>:<page>) publish owner data
ONLY through a JS search form — absent from GIS REST and bulk files. Henrico VA
was the first case: GIS owner-scrubbed, but the APEX form accepts a scripted
`wwv_flow.accept` POST. Validated 2026-06-09: 279/279 recovery, ~0.85s/parcel,
no browser required.

Method (generic to APEX 20+ apps):
  1. GET f?p={app}:{page} to establish session (cookie jar) — capture p_instance
     from the redirected URL/HTML, and hidden fields pPageSubmissionId, pSalt,
     pPageItemsProtected.
  2. POST wwv_flow.accept with p_json={"pageItems":{"itemsToSubmit":[...all page
     items, search key filled...],"protected":<pProt>,...},"salt":<pSalt>} and
     p_request=<item or button request>, p_reload_on_submit='A' (CRITICAL: 'A'
     renders the results grid inline in the response; without it APEX 302s to a
     page you cannot fetch without re-submitting).
  3. Parse the HTML results table.

Adding a county: view-source the search page, list ALL P{page}_* items into
`items` (blank values), set `request` to the item/button that triggers search,
and write a `parse_row` keyed on your search key. Fresh session per worker;
throttle >=0.5s; checkpoint JSON (sandbox calls are 45s — resume across calls).

CLI: python3 apex_owner_pull.py henrico <csv_in> <id_column> <ckpt.json> [budget_s]
     python3 apex_owner_pull.py --smoke   (live Henrico 3-GPIN validation)
"""
import urllib.request, urllib.parse, ssl, re, http.cookiejar, json, time, sys, os, csv, html as htmlmod

_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE
_HD = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}

COUNTIES = {
    'henrico': {
        'base': 'https://realestate.henrico.gov/ords/cam',
        'app': '510101', 'page': '1',
        'search_item': 'P1_PARCEL_ID',
        'request': 'P1_PARCEL_ID',          # item-triggered submit
        'items': ['P1_PARCEL_ID', 'P1_VISION_PID', 'P1_STR_NUM', 'P1_STR_PREFIX',
                  'P1_ADDRESS', 'P1_STR_UNIT', 'P1_LEGAL_DESC', 'P1_USE_CODE', 'P1_SEL_SORT'],
        'note': 'GPIN format 999-999-9999. Condo-suffix GPINs (...XXXX.019) need exact-cell '
                'fallback relaxed to startswith. Results: owner-current, owner-jan1, gpin, situs, PID.',
    },
    # Append further APEX counties here after validating (many VA localities run
    # Vision/ORDS — probe <host>/ords/*/f?p= before assuming a county is closed).
}

def _opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=_CTX))

def _get(op, u):
    h = dict(_HD); h['Accept'] = 'text/html,application/xhtml+xml'
    r = op.open(urllib.request.Request(u, headers=h), timeout=25)
    return r.geturl(), r.read().decode('utf-8', 'replace')

def _post(op, u, data):
    h = dict(_HD); h['Content-Type'] = 'application/x-www-form-urlencoded'; h['Accept'] = 'text/html'
    r = op.open(urllib.request.Request(u, data=data.encode(), headers=h), timeout=25)
    return r.geturl(), r.read().decode('utf-8', 'replace')

def _hidden(html, iid):
    m = re.search(r'value="([^"]*)"\s+id="' + iid + '"', html) or re.search(r'id="' + iid + '"[^>]*value="([^"]*)"', html)
    return htmlmod.unescape(m.group(1)) if m else None

def recover_one(cfg, key):
    """One search round-trip on a fresh session. Returns (status, owner, situs)."""
    op = _opener()
    fu, h = _get(op, f"{cfg['base']}/f?p={cfg['app']}:{cfg['page']}")
    msess = re.search(r'f\?p=' + cfg['app'] + r':\d+:(\d+)', fu + h)
    if not msess: return ('ERROR', 'no-session', '')
    sess = msess.group(1)
    pSubmit, pSalt, pProt = (_hidden(h, x) for x in ('pPageSubmissionId', 'pSalt', 'pPageItemsProtected'))
    if not (pSubmit and pSalt): return ('ERROR', 'no-hidden-fields', '')
    items = [{'n': n, 'v': key if n == cfg['search_item'] else ''} for n in cfg['items']]
    pjson = {'pageItems': {'itemsToSubmit': items, 'protected': pProt or '', 'rowVersion': '', 'formRegionChecksums': []}, 'salt': pSalt}
    body = urllib.parse.urlencode({
        'p_flow_id': cfg['app'], 'p_flow_step_id': cfg['page'], 'p_instance': sess,
        'p_page_submission_id': pSubmit, 'p_request': cfg['request'],
        'p_reload_on_submit': 'A', 'p_json': json.dumps(pjson, separators=(',', ':'))})
    _, h2 = _post(op, f"{cfg['base']}/wwv_flow.accept?p_context={cfg['app']}:{cfg['page']}:{sess}", body)
    return parse_row(h2, key)

def parse_row(h2, key):
    if re.search(r'a-Error-title', h2):
        m = re.search(r'<p>([^<]+)</p>', h2)
        return ('ERROR', m.group(1) if m else 'apex-error', '')
    txt = re.sub(r'<script.*?</script>', '', h2, flags=re.S)
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', txt, flags=re.S):
        cells = [htmlmod.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', c))).strip()
                 for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)]
        if not any(cells): continue
        gi = next((i for i, c in enumerate(cells) if c == key), None)
        if gi is None:  # condo-suffix / formatted variants
            gi = next((i for i, c in enumerate(cells) if c.startswith(key)), None)
        if gi is None or gi < 2: continue
        owner = cells[gi - 2] or cells[gi - 1]
        situs = cells[gi + 1] if gi + 1 < len(cells) else ''
        if owner: return ('OK', owner, situs)
    return ('OWNER-UNRECOVERED', '', '')

def bulk(county, keys, ckpt_path, budget_s=38.0, throttle=0.6):
    """Resumable bulk run. Call repeatedly (45s sandbox cap) until done."""
    cfg = COUNTIES[county]
    done = json.load(open(ckpt_path)) if os.path.exists(ckpt_path) else {}
    t0 = time.time(); n = 0
    for k in [k for k in keys if k not in done]:
        if time.time() - t0 > budget_s: break
        try:
            st, own, situs = recover_one(cfg, k)
            done[k] = {'status': st, 'owner': own, 'situs': situs}
        except Exception as e:
            done[k] = {'status': 'ERROR', 'owner': '', 'situs': '', 'err': repr(e)[:120]}
        n += 1; time.sleep(throttle)
    json.dump(done, open(ckpt_path, 'w'))
    ok = sum(1 for v in done.values() if v['status'] == 'OK')
    return {'processed': n, 'done': len(done), 'total': len(keys), 'ok': ok}

if __name__ == '__main__':
    if '--smoke' in sys.argv:
        expect = {'774-749-2132': 'SLOVAK', '771-754-2766': 'RUBISCO', '775-745-7183': 'BERTOZZI'}
        bad = 0
        for g, want in expect.items():
            st, own, situs = recover_one(COUNTIES['henrico'], g)
            ok = st == 'OK' and want in own.upper()
            bad += (not ok)
            print(f'{"OK " if ok else "FAIL"} {g} -> [{st}] {own} | {situs}')
            time.sleep(0.7)
        print('SMOKE', 'PASS' if bad == 0 else 'FAIL'); sys.exit(bad)
    county, csv_in, idcol, ckpt = sys.argv[1:5]
    budget = float(sys.argv[5]) if len(sys.argv) > 5 else 38.0
    with open(csv_in) as f:
        keys = [r[idcol].strip() for r in csv.DictReader(f) if r[idcol].strip()]
    print(bulk(county, keys, ckpt, budget))
