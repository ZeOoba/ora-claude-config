"""Probe collar-county GIS servers + DLGF sales disclosure bulk paths."""
import urllib.request, json, ssl, sys

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json,text/html;q=0.9,*/*;q=0.8'}

def get(url, timeout=20):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8','replace')
    except Exception as e:
        return f"ERR: {e}"

which = sys.argv[1]

if which == 'servers':
    cands = [
        "https://gis.hamiltoncounty.in.gov/arcgis/rest/services?f=json",
        "https://gis1.hamiltoncounty.in.gov/arcgis/rest/services?f=json",
        "https://maps.hamiltoncounty.in.gov/arcgis/rest/services?f=json",
        "https://gis.co.hendricks.in.us/arcgis/rest/services?f=json",
        "https://gis2.co.hendricks.in.us/arcgis/rest/services?f=json",
        "https://maps.co.hendricks.in.us/arcgis/rest/services?f=json",
        "https://gis.boonecounty.in.gov/arcgis/rest/services?f=json",
        "https://gis.co.johnson.in.us/arcgis/rest/services?f=json",
    ]
    for u in cands:
        t = get(u, 12)
        ok = t[:200].replace('\n',' ')
        print(u, "->", ok[:160])
        print()

if which == 'agol':
    # AGOL search for county parcel feature services
    import urllib.parse
    term = sys.argv[2]
    q = urllib.parse.urlencode({'q': term + ' type:"Feature Service"', 'f':'json', 'num':'15'})
    t = get("https://www.arcgis.com/sharing/rest/search?" + q, 25)
    try:
        j = json.loads(t)
        print("total:", j.get('total'))
        for r in j.get('results',[]):
            print("-", r.get('title'), "|", r.get('owner'), "|", r.get('url'))
    except Exception: print(t[:300])

if which == 'dlgf':
    # DLGF sales data submission page - look for bulk sales files
    t = get("https://www.in.gov/dlgf/assessments/sales-data-submission/", 25)
    print(t[:200])
    import re
    links = re.findall(r'href="([^"]+)"[^>]*>([^<]{3,80})<', t)
    for h, txt in links:
        if any(k in (h+txt).lower() for k in ['sale', 'zip', 'sdf', 'data']):
            print(h, "|", txt.strip())
