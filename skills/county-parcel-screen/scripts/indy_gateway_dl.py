"""Download DLGF Gateway property files (Real Property / Tax Bill) per county.
Usage: indy_gateway_dl.py <dataset:3|5> <county2digit> <outname> [yearLabelSubstr]
Dataset values: 4=Adjustments 6=Personal Property 5=Real Property 3=Tax Bill
"""
import urllib.request, ssl, re, sys, urllib.parse, os, time

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36'
URL='https://gateway.ifionline.org/public/download.aspx'
OUT='/sessions/vibrant-laughing-bardeen/mnt/outputs/county-parcel-screen/data/indy'
os.makedirs(OUT, exist_ok=True)

def fetch_page():
    req = urllib.request.Request(URL, headers={'User-Agent':UA,'Accept':'text/html'})
    with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
        cookies = r.headers.get_all('Set-Cookie') or []
        return r.read().decode('utf-8','replace'), '; '.join(c.split(';')[0] for c in cookies)

def hidden(t):
    h = {}
    for name in ['__VIEWSTATE','__VIEWSTATEGENERATOR','__EVENTVALIDATION','__EVENTTARGET','__EVENTARGUMENT']:
        m = re.search(r'id="'+name+r'" value="([^"]*)"', t)
        h[name] = m.group(1) if m else ''
    return h

def options(t, selid):
    i = t.find(f'id="{selid}"')
    seg = t[i:t.find('</select>', i)]
    return re.findall(r'<option(?:\s+selected="selected")?\s+value="([^"]*)">([^<]*)</option>', seg)

if __name__ == '__main__':
    ds, county, outname = sys.argv[1], sys.argv[2], sys.argv[3]
    yearpick = sys.argv[4] if len(sys.argv)>4 else None
    t, ck = fetch_page()
    h = hidden(t)
    yopts = options(t, 'ctl00_ContentPlaceHolder1_DropDownList2')
    copts = options(t, 'ctl00_ContentPlaceHolder1_DropDownList3')
    print("year options:", yopts[:6])
    yv = None
    if yearpick:
        for v,lab in yopts:
            if yearpick in lab: yv = v; break
    if yv is None: yv = yopts[0][0]
    cv = None
    for v,lab in copts:
        if v == county or lab.lower()==county.lower(): cv = v; break
    print("using year", yv, "county", cv)
    form = {
        '__VIEWSTATE':h['__VIEWSTATE'], '__VIEWSTATEGENERATOR':h['__VIEWSTATEGENERATOR'],
        '__EVENTVALIDATION':h['__EVENTVALIDATION'], '__EVENTTARGET':'', '__EVENTARGUMENT':'',
        'ctl00$ContentPlaceHolder1$DropDownList1': ds,
        'ctl00$ContentPlaceHolder1$DropDownList2': yv,
        'ctl00$ContentPlaceHolder1$DropDownList3': cv,
        'ctl00$ContentPlaceHolder1$button2': 'Download',
        # finance section defaults (present in form)
        'ctl00$ContentPlaceHolder1$DDL_Files':'1',
        'ctl00$ContentPlaceHolder1$DDL_UnitTypes':'-99',
        'ctl00$ContentPlaceHolder1$DDL_Years':'2025',
    }
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(URL, data=data, headers={
        'User-Agent':UA,'Accept':'*/*','Content-Type':'application/x-www-form-urlencoded',
        'Referer':URL,'Cookie':ck,'Origin':'https://gateway.ifionline.org'})
    t0=time.time()
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
        ctype = r.headers.get('Content-Type'); cdisp = r.headers.get('Content-Disposition')
        print("resp:", r.status, ctype, cdisp)
        path = os.path.join(OUT, outname)
        n=0
        with open(path,'wb') as f:
            while True:
                chunk = r.read(1<<20)
                if not chunk: break
                f.write(chunk); n+=len(chunk)
        print("saved", path, n, "bytes in", round(time.time()-t0,1),"s")
