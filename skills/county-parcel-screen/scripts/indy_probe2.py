"""Probe statewide parcel layer schema + a sample Marion County record."""
import urllib.request, json, ssl, sys, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'application/json'}

def jget(url, timeout=30):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode('utf-8','replace'))
    except Exception as e:
        return {"_err": str(e)}

BASE = "https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer"
which = sys.argv[1] if len(sys.argv)>1 else 'schema'

if which == 'schema':
    j = jget(BASE + "?f=json")
    print("layers:", [(l.get('id'), l.get('name')) for l in j.get('layers',[])], "| err:", j.get('_err'))
    j0 = jget(BASE + "/0?f=json")
    print("name:", j0.get('name'), "| maxRecordCount:", j0.get('maxRecordCount'))
    flds = j0.get('fields',[])
    print("fields:")
    for f in flds: print(" ", f['name'], f['type'])

if which == 'sample':
    q = urllib.parse.urlencode({
        'where': "county_name='Marion'", 'outFields':'*', 'resultRecordCount':'3',
        'returnGeometry':'false', 'f':'json'})
    j = jget(BASE + "/0/query?" + q)
    if '_err' in j or 'error' in j: print(j)
    else:
        for f in j.get('features',[]): print(json.dumps(f['attributes'], indent=1)[:1800]); print('---')

if which == 'count':
    where = sys.argv[2]
    q = urllib.parse.urlencode({'where': where, 'returnCountOnly':'true', 'f':'json'})
    j = jget(BASE + "/0/query?" + q)
    print(where, "->", j)
