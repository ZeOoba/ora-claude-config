"""Probe Gateway SDF (sales disclosure) site structure."""
import urllib.request, json, ssl, sys, re

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36',
     'Accept':'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8'}

def get(url, timeout=30, data=None, hdr=None):
    h = dict(HDR); h.update(hdr or {})
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, dict(r.headers), r.read().decode('utf-8','replace')
    except Exception as e:
        return None, {}, f"ERR: {e}"

which = sys.argv[1]

if which == 'root':
    for u in ["https://gatewaysdf.ifionline.org/",
              "https://gatewaysdf.ifionline.org/Search.aspx",
              "https://gatewaysdf.ifionline.org/DownloadData.aspx",
              "https://gatewaysdf.ifionline.org/Download.aspx"]:
        s, h, t = get(u)
        print("===", u, "->", s, "len", len(t))
        if s == 200:
            # find forms, selects, interesting links
            for m in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{2,60})</a>', t)[:20]:
                print("  link:", m)
            for m in re.findall(r'<select[^>]+(?:name|id)="([^"]+)"', t)[:15]:
                print("  select:", m)
            for m in re.findall(r'<input[^>]+name="([^"]+)"[^>]*type="(submit|button|text)"', t)[:15]:
                print("  input:", m)
