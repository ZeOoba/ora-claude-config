"""Indy market endpoint discovery — probe state + county GIS endpoints."""
import urllib.request, json, ssl, sys

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json,text/html;q=0.9,*/*;q=0.8'}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', 'replace')
    except Exception as e:
        return f"ERR: {e}"

def jget(url, timeout=25):
    t = get(url, timeout)
    try: return json.loads(t)
    except Exception: return {"_raw": t[:400]}

which = sys.argv[1] if len(sys.argv)>1 else 'all'

if which in ('all','hosted'):
    j = jget("https://gisdata.in.gov/server/rest/services/Hosted?f=json")
    names = [s['name'] for s in j.get('services',[])]
    print("=== gisdata.in.gov Hosted:", len(names), "services ===")
    for n in names:
        if any(k in n.lower() for k in ['parcel','cadast','property','tax']):
            print("MATCH:", n)

if which in ('all','indy'):
    # Indy (Marion) — xmaps.indy.gov
    j = jget("https://xmaps.indy.gov/arcgis/rest/services?f=json")
    print("=== xmaps.indy.gov root ===")
    print("folders:", j.get('folders'))
    print("services:", [s['name'] for s in j.get('services',[])][:30])
    if '_raw' in j: print(j['_raw'])

if which in ('all','dcat'):
    j = jget("https://data.indy.gov/api/feed/dcat-us/1.1.json", timeout=40)
    ds = j.get('dataset', [])
    print("=== data.indy.gov DCAT:", len(ds), "datasets ===")
    for d in ds:
        ti = d.get('title','')
        if any(k in ti.lower() for k in ['parcel','property','assess','tax']):
            urls = [x.get('accessURL') or x.get('downloadURL') for x in d.get('distribution',[])]
            print("MATCH:", ti, "|", (urls[:2] if urls else d.get('landingPage')))
