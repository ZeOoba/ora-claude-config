"""Probe gis.indy.gov MapIndyProperty service."""
import urllib.request, json, ssl, sys, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Accept':'application/json'}

def jget(url, timeout=40):
    req = urllib.request.Request(url, headers=HDR)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8','replace'))
    except Exception as e:
        return {"_err": str(e)}

SVC = "https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer"
which = sys.argv[1] if len(sys.argv)>1 else 'svc'

if which == 'svc':
    j = jget(SVC + "?f=json")
    print("layers:")
    for l in j.get('layers',[]): print(" ", l['id'], l['name'])
    print("tables:")
    for t in j.get('tables',[]): print(" ", t['id'], t['name'])
    if '_err' in j: print(j)

if which == 'layer':
    lid = sys.argv[2]
    j = jget(f"{SVC}/{lid}?f=json")
    print("name:", j.get('name'), "| maxRecordCount:", j.get('maxRecordCount'), "| type:", j.get('type'))
    for f in j.get('fields',[]) or []: print(" ", f['name'], f['type'])
    if '_err' in j: print(j)

if which == 'sample':
    lid = sys.argv[2]
    where = sys.argv[3] if len(sys.argv)>3 else '1=1'
    n = sys.argv[4] if len(sys.argv)>4 else '3'
    q = urllib.parse.urlencode({'where':where,'outFields':'*','resultRecordCount':n,'returnGeometry':'false','f':'json'})
    j = jget(f"{SVC}/{lid}/query?{q}")
    if 'features' in j:
        for f in j['features']: print(json.dumps(f['attributes'], indent=1)[:2500]); print('---')
    else: print(j)

if which == 'count':
    lid = sys.argv[2]; where = sys.argv[3]
    q = urllib.parse.urlencode({'where':where,'returnCountOnly':'true','f':'json'})
    print(jget(f"{SVC}/{lid}/query?{q}"))
