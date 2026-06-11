"""Hunt owner-bearing parcel sources for Hendricks, Boone, Johnson IN."""
import urllib.request, json, ssl, sys

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json,text/html;q=0.9,*/*;q=0.8'}

def get(url, timeout=15):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8','replace')
    except Exception as e:
        return f"ERR: {e}"

which = sys.argv[1]

if which == 'hosts':
    cands = [
        # Hendricks
        "https://hendricks.maps39.com/arcgis/rest/services?f=json",
        "https://maps.hendrickscounty.in.gov/arcgis/rest/services?f=json",
        "https://data-hendricksco.opendata.arcgis.com/api/feed/dcat-us/1.1.json",
        "https://gis.hendrickscounty.in.gov/arcgis/rest/services?f=json",
        # Johnson
        "https://gis.johnsoncounty.in.gov/arcgis/rest/services?f=json",
        "https://maps.johnsoncounty.in.gov/arcgis/rest/services?f=json",
        # Boone retry + alternates
        "https://gis.boonecounty.in.gov/arcgis/rest/services?f=json",
        "https://gis2.boonecounty.in.gov/arcgis/rest/services?f=json",
    ]
    for u in cands:
        t = get(u, 12)
        print(u, "->", t[:120].replace('\n',' '))

if which == 'vintage':
    # do older statewide vintages carry owner?
    for yr in ['2024','2023','2021']:
        t = get(f"https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_{yr}/FeatureServer/0?f=json", 25)
        try:
            j = json.loads(t)
            fl = [f['name'] for f in j.get('fields',[])]
            own = [f for f in fl if 'own' in f.lower() or 'name' in f.lower()]
            print(yr, "owner-ish:", own, "| nfields:", len(fl))
        except Exception: print(yr, t[:150])

if which == 'agol2':
    import urllib.parse
    for term in ["Johnson County Indiana parcels owner", "Boone County Indiana parcels owner", "Hendricks parcels"]:
        q = urllib.parse.urlencode({'q': term + ' type:"Feature Service"', 'f':'json','num':'8'})
        t = get("https://www.arcgis.com/sharing/rest/search?" + q, 25)
        print("===", term)
        try:
            j = json.loads(t)
            for r in j.get('results',[]):
                print("-", r.get('title'),"|",r.get('owner'),"|",r.get('url'))
        except Exception: print(t[:200])
