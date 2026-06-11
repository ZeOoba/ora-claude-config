"""Pull SDF sales from gatewaysdf.ifionline.org /api/fileApi/SearchList (DataTables POST)."""
import urllib.request, json, ssl, sys, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def post(county, year, propclass, start=0, length=100):
    obj = {
        "SdfId":"", "Year":str(year), "County":county, "ParcelNumber":"",
        "BuyerFirstName":"","BuyerLastName":"","BuyerCompany":"",
        "SellerFirstName":"","SellerLastName":"","SellerCompany":"",
        "PreparerFirstName":"","PreparerLastName":"","ParcelAddress":"","ZipCode":"",
        "TaxDistrict":"","MinSalesPrice":"","MaxSalesPrice":"",
        "MinConveyanceDate":"","MaxConveyanceDate":"","MinSaleDate":"","MaxSaleDate":"",
        "MinDateReceived":"","MaxDateReceived":"","MinTransferDate":"","MaxTransferDate":"",
        "ValidforTrending":"Selected",
        "PropertyClass":propclass or "Selected", "CaptchaCode":""
    }
    dt = {'draw':'1','start':str(start),'length':str(length),
          'searchProperty': json.dumps(obj)}
    data = urllib.parse.urlencode(dt).encode()
    req = urllib.request.Request("https://gatewaysdf.ifionline.org/api/fileApi/SearchList",
        data=data, headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept':'application/json, text/javascript, */*; q=0.01',
        'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With':'XMLHttpRequest',
        'Referer':'https://gatewaysdf.ifionline.org/Search.aspx',
        'Origin':'https://gatewaysdf.ifionline.org'})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        return json.loads(r.read().decode('utf-8','replace'))

if __name__ == '__main__':
    county = sys.argv[1] if len(sys.argv)>1 else '49'
    year = sys.argv[2] if len(sys.argv)>2 else '2025'
    pc = sys.argv[3] if len(sys.argv)>3 else '300'
    j = post(county, year, pc, 0, 5)
    print("recordsTotal:", j.get('recordsTotal'), "| recordsFiltered:", j.get('recordsFiltered'))
    for d in (j.get('data') or [])[:3]:
        print(json.dumps(d, indent=1)[:1500])
