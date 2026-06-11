"""Statewide layer: sample rows + class-code distribution by county."""
import urllib.request, json, ssl, sys, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Accept':'application/json'}
BASE="https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer/0/query?"

def jq(params, timeout=40):
    req = urllib.request.Request(BASE+urllib.parse.urlencode(params), headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8','replace'))

which = sys.argv[1] if len(sys.argv)>1 else 'sample'

if which == 'sample':
    j = jq({'where':"county_id='49'",'outFields':'state_parcel_id,parcel_id,local_id,prop_add,prop_city,prop_zip,dlgf_prop_class_code,county_id,tax_county,source_originator','resultRecordCount':'5','returnGeometry':'false','f':'json'})
    print(json.dumps([f['attributes'] for f in j.get('features',[])], indent=1))

if which == 'classdist':
    # class-code distribution for a county via groupBy
    cid = sys.argv[2]
    j = jq({'where':f"county_id='{cid}' AND dlgf_prop_class_code LIKE '3%'",
            'groupByFieldsForStatistics':'dlgf_prop_class_code',
            'outStatistics':json.dumps([{"statisticType":"count","onStatisticField":"objectid","outStatisticFieldName":"n"}]),
            'returnGeometry':'false','f':'json'})
    rows = [(f['attributes']['dlgf_prop_class_code'], f['attributes']['n']) for f in j.get('features',[])]
    for c,n in sorted(rows): print(c, n)
    print("err:", j.get('error'))

if which == 'count':
    print(jq({'where':sys.argv[2],'returnCountOnly':'true','f':'json'}))
