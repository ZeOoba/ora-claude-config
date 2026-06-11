"""Derive exact offsets: print landmark indices for sample rows + column-stability stats."""
import zipfile, sys, re
from collections import Counter

path = sys.argv[1]
z = zipfile.ZipFile(path)
rows = []
with z.open(z.namelist()[0]) as f:
    f.readline()
    for i, raw in enumerate(f):
        l = raw.decode('utf-8','replace').rstrip('\r\n')
        if len(l) > 1000: rows.append(l)
        if i > 60000: break

print("n rows", len(rows))
r = rows[0]
landmarks = {
    'zip1(46052)': r.find('46052-0000'),
    'owner(EAVEY)': r.find('EAVEY'),
    'flags(NNNN)': r.find('NNNNNNNNNANNB'),
    'isodate': r.find('2021-09-09'),
}
print(landmarks)

# class code candidate at 193:196 — distribution
c = Counter(x[193:196] for x in rows)
print("cols193:196 top:", c.most_common(15))

# check where ISO date appears across rows (stable col?)
pos = Counter()
for x in rows[:20000]:
    m = re.search(r'\d{4}-\d{2}-\d{2}', x)
    if m: pos[m.start()] += 1
print("ISO date start col:", pos.most_common(5))

# check mm/dd/yyyy (transfer/contract?) position
pos2 = Counter()
for x in rows[:20000]:
    m = re.search(r'\d{2}/\d{2}/\d{4}', x)
    if m: pos2[m.start()] += 1
print("US date start col:", pos2.most_common(5))

# AV numeric block: find start of first AV (after 'N'/'Y' flag) — check cols 455-500 of 3 rows
for x in rows[:3]:
    print(repr(x[440:540]))
