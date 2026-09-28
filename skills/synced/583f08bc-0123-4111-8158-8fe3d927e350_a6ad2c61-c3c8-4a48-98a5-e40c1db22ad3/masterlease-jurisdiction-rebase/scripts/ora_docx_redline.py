#!/usr/bin/env python3
"""
ora_docx_redline.py — ORA shared tracked-change editor for Word XML.

Extracted 2026-08-04 from the master-lease v2.6 build (third ad-hoc reimplementation
of the same machinery: v2.3 build, v2.5 build, v2.6 build). Applies asserted-count
substitutions to word/document.xml as REAL tracked changes (<w:ins>/<w:del> with
author + date), per lease-form-qc Output doctrine. Any count mismatch aborts loudly
with the anchor named — never loosen an assertion to make a run pass.

Ops (JSON spec, list of objects applied in order):
  {"op": "replace",  "old": "...", "new": "...", "count": N}
  {"op": "insert_after", "anchor": "...", "text": "...", "count": N}
  {"op": "insert_paragraphs_after", "anchor_xml": "<exact xml substring>",
   "paragraphs": [{"label": "Bold lead-in:", "text": " value"}], "count": 1}

Usage:
  python3 ora_docx_redline.py --in master.docx --out edited.docx \
      --author "Gabriel Goldberg" --date 2026-08-04T12:00:00Z --spec edits.json

Then ALWAYS validate:  docx skill scripts/office/validate.py <out> --original <in> --author "<author>"
Known limits: anchors must be contiguous inside one <w:t> (run merge_runs.py first if
not); anchor text must not recur inside an inserted string.
"""
import argparse, json, re, shutil, sys, tempfile, zipfile, os

class Redliner:
    def __init__(self, xml, author, date, start_id=9000):
        self.x, self.a, self.d, self.i = xml, author, date, start_id
    def _nid(self):
        self.i += 1
        return self.i
    def _run(self, rpr, txt):
        return f'<w:r>{rpr}<w:t xml:space="preserve">{txt}</w:t></w:r>' if txt else ''
    def _ins(self, rpr, txt):
        return (f'<w:ins w:id="{self._nid()}" w:author="{self.a}" w:date="{self.d}">'
                f'<w:r>{rpr}<w:t xml:space="preserve">{txt}</w:t></w:r></w:ins>')
    def _del(self, rpr, txt):
        return (f'<w:del w:id="{self._nid()}" w:author="{self.a}" w:date="{self.d}">'
                f'<w:r>{rpr}<w:delText xml:space="preserve">{txt}</w:delText></w:r></w:del>')
    def _find_run(self, idx):
        rs = max(self.x.rfind('<w:r>', 0, idx), self.x.rfind('<w:r ', 0, idx))
        return rs, self.x.find('</w:r>', idx) + len('</w:r>')
    def _parts(self, run):
        m = re.search(r'(<w:rPr\b.*?</w:rPr>|<w:rPr/>)', run, re.S)
        rpr = m.group(1) if m else '<w:rPr/>'
        m = re.search(r'<w:t[^>]*>(.*?)</w:t>', run, re.S)
        return rpr, m.group(1)
    def replace(self, old, new, expect):
        n = pos = 0
        while True:
            j = self.x.find(old, pos)
            if j < 0:
                break
            rs, re_ = self._find_run(j)
            run = self.x[rs:re_]
            if old not in run:
                sys.exit(f'SPAN FAIL (run merge needed): {old[:60]}')
            rpr, txt = self._parts(run)
            pre, _, post = txt.partition(old)
            rep = self._run(rpr, pre) + self._del(rpr, old) + self._ins(rpr, new) + self._run(rpr, post)
            self.x = self.x[:rs] + rep + self.x[re_:]
            pos = rs + len(rep) - len(self._run(rpr, post))   # rescan from start of post run
            n += 1
        assert n == expect, f'ANCHOR DRIFT {old[:60]!r}: found {n}, expected {expect}'
    def insert_after(self, anchor, text, expect):
        n = pos = 0
        while True:
            j = self.x.find(anchor, pos)
            if j < 0:
                break
            rs, re_ = self._find_run(j)
            run = self.x[rs:re_]
            if anchor not in run:
                sys.exit(f'SPAN FAIL (run merge needed): {anchor[:60]}')
            rpr, txt = self._parts(run)
            pre, _, post = txt.partition(anchor)
            pre_run = self._run(rpr, pre + anchor)
            rep = pre_run + self._ins(rpr, text) + self._run(rpr, post)
            self.x = self.x[:rs] + rep + self.x[re_:]
            pos = rs + len(pre_run)                            # rescan from after the kept anchor
            n += 1
        assert n == expect, f'ANCHOR DRIFT {anchor[:60]!r}: found {n}, expected {expect}'
    def insert_paragraphs_after(self, anchor_xml, paragraphs, expect=1,
                                pstyle='BodyText'):
        assert self.x.count(anchor_xml) == expect, f'ANCHOR DRIFT (xml) {anchor_xml[:60]!r}'
        rows = ''
        for p in paragraphs:
            rows += (f'<w:p><w:pPr><w:pStyle w:val="{pstyle}"/>'
                     f'<w:rPr><w:ins w:id="{self._nid()}" w:author="{self.a}" w:date="{self.d}"/></w:rPr></w:pPr>'
                     f'<w:ins w:id="{self._nid()}" w:author="{self.a}" w:date="{self.d}">'
                     f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{p["label"]}</w:t></w:r>'
                     f'<w:r><w:rPr/><w:t xml:space="preserve">{p["text"]}</w:t></w:r></w:ins></w:p>')
        self.x = self.x.replace(anchor_xml, anchor_xml + rows, 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--author', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--spec', required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(a.src) as z:
            z.extractall(td)
        dx = os.path.join(td, 'word', 'document.xml')
        r = Redliner(open(dx, encoding='utf-8').read(), a.author, a.date)
        for e in spec:
            if e['op'] == 'replace':
                r.replace(e['old'], e['new'], e['count'])
            elif e['op'] == 'insert_after':
                r.insert_after(e['anchor'], e['text'], e['count'])
            elif e['op'] == 'insert_paragraphs_after':
                r.insert_paragraphs_after(e['anchor_xml'], e['paragraphs'], e.get('count', 1))
            else:
                sys.exit(f'unknown op {e["op"]}')
        open(dx, 'w', encoding='utf-8').write(r.x)
        if os.path.exists(a.out):
            os.remove(a.out)
        base = shutil.make_archive(a.out + '.tmp', 'zip', td)
        shutil.move(base, a.out)
    print(f'OK: {len(spec)} ops applied -> {a.out}  (validate with validate.py before use)')

if __name__ == '__main__':
    main()
