"""Reverse-engineer the Gateway RealParcel fixed-width layout empirically."""
import zipfile, sys, re

path = sys.argv[1]
z = zipfile.ZipFile(path)
name = z.namelist()[0]
lines = []
with z.open(name) as f:
    hdr = f.readline()
    for i, raw in enumerate(f):
        if i > 50000: break
        lines.append(raw.decode('utf-8','replace').rstrip('\n').rstrip('\r'))

lens = {}
for l in lines: lens[len(l)] = lens.get(len(l),0)+1
print("line lengths:", sorted(lens.items(), key=lambda x:-x[1])[:5])

L = max(lens, key=lens.get)
rows = [l for l in lines if len(l) == L]
print("rows:", len(rows))

# find a commercial/industrial row for contrast (LLC owner)
samples = [rows[0], rows[1]]
for r in rows:
    if ' LLC' in r: samples.append(r); break
for r in rows:
    if re.search(r'\b3[1-9]\d\b', r[:140]): pass
# print ruler + slices
def ruler(width, start):
    s1 = ''.join(str((start+i)//100 % 10) for i in range(width))
    s2 = ''.join(str((start+i)//10 % 10) for i in range(width))
    s3 = ''.join(str((start+i) % 10) for i in range(width))
    return s1+'\n'+s2+'\n'+s3

for seg in range(0, L, 160):
    print(f"=== cols {seg}-{min(seg+160,L)} ===")
    print(ruler(min(160, L-seg), seg))
    for s in samples[:3]:
        print(s[seg:seg+160])
