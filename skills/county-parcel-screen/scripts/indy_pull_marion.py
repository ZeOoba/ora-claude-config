"""Pull Marion County industrial/flex universe from MapIndy layer 10. Paged, saves raw JSON."""
import urllib.request, json, ssl, urllib.parse, os, time

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Accept':'application/json'}
URL = "https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer/10/query?"
OUT = "/sessions/vibrant-laughing-bardeen/mnt/outputs/county-parcel-screen/data/indy"
os.makedirs(OUT, exist_ok=True)

WHERE = "PROPERTY_SUB_CLASS IN (310,320,330,340,345,346,350,360,370,399,480,482)"
FIELDS = ("STATEPARCELNUMBER,PARCEL_C,STNUMBER,PRE_DIR,FULL_STNAME,CITY,TOWNSHIP,ZIPCODE,"
          "FULLOWNERNAME,PROPERTY_CLASS,PROPERTY_SUB_CLASS,PROPERTY_SUB_CLASS_DESCRIPTION,"
          "OWNERADDRESS,OWNERADDRESS2,OWNERCITY,OWNERSTATE,OWNERZIP,"
          "ASSESSORYEAR_LANDTOTAL,ASSESSORYEAR_IMPTOTAL,ASSESSORYEAR_TOTALAV,"
          "NEIGHBORHOOD,TAX_DISTRICT_ID,ASSESSOR_DISTRICT,ACREAGE,ESTSQFT")

all_feats = []
offset = 0
while True:
    q = urllib.parse.urlencode({'where':WHERE,'outFields':FIELDS,'returnGeometry':'false',
        'resultOffset':str(offset),'resultRecordCount':'1000','orderByFields':'OBJECTID','f':'json'})
    req = urllib.request.Request(URL+q, headers=HDR)
    j = json.loads(urllib.request.urlopen(req, timeout=60, context=ctx).read().decode('utf-8','replace'))
    if 'error' in j:
        print("ERROR at offset", offset, j['error']); break
    feats = j.get('features',[])
    all_feats.extend(feats)
    print("offset", offset, "got", len(feats))
    if len(feats) < 1000: break
    offset += 1000
    time.sleep(0.4)

with open(os.path.join(OUT, "marion_industrial_raw.json"), "w") as f:
    json.dump([x['attributes'] for x in all_feats], f)
print("TOTAL", len(all_feats), "saved -> marion_industrial_raw.json")
