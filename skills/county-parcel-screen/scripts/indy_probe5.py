"""Distinct PROPERTY_CLASS / SUB_CLASS values on MapIndy parcel layer."""
import urllib.request, json, ssl, sys, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Accept':'application/json'}
URL = "https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer/10/query?"

def jq(params, timeout=60):
    req = urllib.request.Request(URL+urllib.parse.urlencode(params), headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8','replace'))

which = sys.argv[1] if len(sys.argv)>1 else 'class'

if which == 'class':
    j = jq({'where':'1=1','returnDistinctValues':'true','outFields':'PROPERTY_CLASS','returnGeometry':'false','f':'json'})
    vals = sorted([(f['attributes']['PROPERTY_CLASS'] or 'NULL') for f in j.get('features',[])])
    print(len(vals), "distinct:", vals)
    if 'error' in j: print(j['error'])

if which == 'subclass':
    cls = sys.argv[2]
    j = jq({'where':f"PROPERTY_CLASS='{cls}'",'returnDistinctValues':'true',
            'outFields':'PROPERTY_SUB_CLASS,PROPERTY_SUB_CLASS_DESCRIPTION','returnGeometry':'false','f':'json'})
    rows = sorted([(f['attributes']['PROPERTY_SUB_CLASS'], f['attributes']['PROPERTY_SUB_CLASS_DESCRIPTION']) for f in j.get('features',[])], key=lambda x:(x[0] is None, x[0]))
    for r in rows: print(r)
    if 'error' in j: print(j['error'])
