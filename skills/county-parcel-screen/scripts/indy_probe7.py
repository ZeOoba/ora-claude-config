"""Hamilton IN folders + Boone retry + AGOL searches."""
import urllib.request, json, ssl, sys

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json'}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8','replace')
    except Exception as e:
        return f"ERR: {e}"

which = sys.argv[1]

if which == 'hamfolders':
    for fld in ['ProVal','OpenData','Hosted']:
        t = get(f"https://gis1.hamiltoncounty.in.gov/arcgis/rest/services/{fld}?f=json")
        try:
            j = json.loads(t)
            print(f"=== {fld} ===")
            for s in j.get('services',[]): print("  ", s['name'], s['type'])
        except Exception: print(fld, t[:200])

if which == 'boone':
    t = get("https://gis.boonecounty.in.gov/arcgis/rest/services?f=json", 40)
    print(t[:600])

if which == 'agol':
    import urllib.parse
    for term in [sys.argv[2]]:
        q = urllib.parse.urlencode({'q': term, 'f':'json', 'num':'20'})
        t = get("https://www.arcgis.com/sharing/rest/search?" + q, 30)
        try:
            j = json.loads(t)
            print("total:", j.get('total'))
            for r in j.get('results',[]):
                print("-", r.get('title'), "|", r.get('type'), "|", r.get('owner'), "|", r.get('url'))
        except Exception: print(t[:300])
