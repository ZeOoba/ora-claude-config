"""Check Hosted/Parcels_2023 fields; probe DLGF data-download pages; probe Boone alternatives."""
import urllib.request, json, ssl, sys, re

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json,text/html;q=0.9,*/*;q=0.8'}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8','replace')
    except Exception as e:
        return f"ERR: {e}"

which = sys.argv[1]

if which == 'p2023':
    t = get("https://gisdata.in.gov/server/rest/services/Hosted/Parcels_2023/FeatureServer/0?f=json")
    try:
        j = json.loads(t)
        print("name:", j.get('name'))
        print([f['name'] for f in j.get('fields',[])])
    except Exception: print(t[:300])

if which == 'dlgfpages':
    for u in ["https://www.in.gov/dlgf/assessments/data-downloads/",
              "https://www.in.gov/dlgf/understanding-your-tax-bill/download-data/",
              "https://gateway.ifionline.org/public/download.aspx"]:
        t = get(u, 25)
        print("===", u, "->", ("OK len "+str(len(t)) if not t.startswith('ERR') else t))
        if not t.startswith('ERR'):
            links = re.findall(r'href="([^"]+)"', t)
            hits = [l for l in links if any(k in l.lower() for k in ['.zip','.csv','sale','parcel','data'])]
            for h in hits[:25]: print("   ", h)

if which == 'boonealt':
    for u in ["https://gis.boonecounty.in.gov/arcgis/rest/services?f=json",
              "https://maps.boonecounty.in.gov/arcgis/rest/services?f=json",
              "https://beacon.schneidercorp.com/api/search?QPS=boone",
              "https://www.arcgis.com/sharing/rest/search?q=Boone%20County%20Indiana%20parcels%20owner&f=json&num=10"]:
        t = get(u, 20)
        if u.endswith('num=10'):
            try:
                j = json.loads(t)
                for r in j.get('results',[]): print("-", r.get('title'),"|",r.get('owner'),"|",r.get('url'))
            except Exception: print(t[:200])
        else:
            print(u, "->", t[:150].replace('\n',' '))
