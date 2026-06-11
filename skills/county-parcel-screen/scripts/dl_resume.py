import urllib.request, os, sys
u=sys.argv[1]; out=sys.argv[2]; limit=int(sys.argv[3]) if len(sys.argv)>3 else 10**12
pos = os.path.getsize(out) if os.path.exists(out) else 0
req=urllib.request.Request(u, headers={'Range':f'bytes={pos}-'})
try: r=urllib.request.urlopen(req,timeout=38)
except Exception as e:
    print('open fail',e); sys.exit(1)
total = pos + int(r.headers.get('Content-Length',0))
with open(out,'ab') as f:
    got=0
    while got<limit:
        b=r.read(1<<20)
        if not b: break
        f.write(b); got+=len(b)
print(f'{os.path.getsize(out)}/{total}')
