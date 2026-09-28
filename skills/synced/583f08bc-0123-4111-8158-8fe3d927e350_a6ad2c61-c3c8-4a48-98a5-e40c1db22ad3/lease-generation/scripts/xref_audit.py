#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xref_audit.py — numbering + cross-reference audit for ORA-form leases (DOCX).

Reconstructs Word's style-based auto-numbering (Heading1 = 1., Heading2 = (a), Heading3 = (i)),
then checks every reference in the body:
  * numeric:  "Section 2(a)", "Section 11", "this Section 24", "subsection (c)"      -> target must exist
  * title:    'section of this Lease entitled "TITLE"'                                 -> a Heading1 with that title must exist
  * exhibits: "Exhibit A/B/C"                                                            -> an "EXHIBIT X" title paragraph must exist
  * fragile:  "this Section N" self-references (should be "this Section")
  * defined terms: "Term" means / (the "Term") — reports terms USED in quotes but never defined
  * tokens:   [TOKEN] left unfilled (body + footers)

USAGE: python3 xref_audit.py <lease.docx> [--json]      exit 0 clean, 1 findings
"""
import sys, re, json, zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
def q(t): return '{%s}%s' % (W, t)
ROMAN = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii']
Q = '[\"“”]'

def text_of(p): return ''.join(t.text or '' for t in p.iter(q('t')))

def load(path):
    z = zipfile.ZipFile(path)
    doc = etree.fromstring(z.read('word/document.xml'))
    footers = ' '.join(etree.tostring(etree.fromstring(z.read(n)), method='text', encoding='unicode')
                       for n in z.namelist() if re.match(r'word/(footer|header)\d*\.xml', n))
    return doc, footers

def number(doc):
    """Return list of (label, level, title, text) for numbered paragraphs, honoring w:numPr level overrides."""
    body = doc.find('w:body', NS); out = []; h1 = h2 = h3 = 0
    for p in body.findall('w:p', NS):
        pp = p.find('w:pPr', NS)
        if pp is None: continue
        st = pp.find('w:pStyle', NS); style = st.get(q('val')) if st is not None else ''
        numpr = pp.find('w:numPr', NS)
        lvl = None
        if numpr is not None and numpr.find('w:ilvl', NS) is not None:
            lvl = int(numpr.find('w:ilvl', NS).get(q('val')))
        txt = text_of(p)
        if lvl is None:
            lvl = {'Heading1': 0, 'Heading2': 1, 'Heading3': 2}.get(style)
        if lvl is None or not txt.strip(): continue
        if lvl == 0: h1 += 1; h2 = h3 = 0; label = '%d' % h1
        elif lvl == 1: h2 += 1; h3 = 0; label = '%d(%s)' % (h1, chr(96 + h2))
        elif lvl == 2: h3 += 1; label = '%d(%s)(%s)' % (h1, chr(96 + h2), ROMAN[h3 - 1] if h3 <= len(ROMAN) else h3)
        else: label = '%d.lvl%d' % (h1, lvl)
        title = ''
        if lvl == 0:
            m = re.match(r'\s*([A-Z][A-Z0-9 ,;/’\'&()-]+?)\s*[.:]', txt)
            title = m.group(1).strip() if m else txt.strip()[:60]
        else:
            m = re.match(r'\s*([A-Z][A-Za-z ,;/’\'&()-]+?)\s*\.', txt)
            title = m.group(1).strip() if m else ''
        out.append((label, lvl, title, txt))
    return out

def audit(path):
    doc, footers = load(path)
    body = doc.find('w:body', NS)
    full = '\n'.join(text_of(p) for p in body.findall('w:p', NS))
    numbered = number(doc)
    labels = {n[0] for n in numbered}
    h1_titles = {n[2].upper(): n[0] for n in numbered if n[1] == 0 and n[2]}
    findings = []

    # section map
    smap = [(n[0], n[2]) for n in numbered if n[1] == 0]

    # numeric references
    for m in re.finditer(r'\b(this )?Section\s+(\d+)(\([a-z]\))?(\([ivx]+\))?', full):
        if re.search(r'U\.?\s?S\.?\s?C\.?\s*$', full[max(0, m.start() - 12):m.start()]): continue   # statutory cite
        this, n, a, b = m.group(1), m.group(2), m.group(3) or '', m.group(4) or ''
        target = n + a + b
        if this: findings.append(('HIGH', 'F7 fragile numeric self-reference', m.group(0)))
        if target not in labels: findings.append(('HIGH', 'numeric reference target missing', m.group(0)))
    # title references
    for m in re.finditer(r'entitled[,]?\s*' + Q + r'\s*([A-Z][A-Z ,;/’\'&-]+?)\s*[,.]?\s*' + Q, full):
        t = m.group(1).strip().rstrip(',.').upper()
        if t not in h1_titles:
            findings.append(('HIGH', 'title reference to non-existent section', t))
    # exhibits
    ex_defined = set(re.findall(r'^\s*EXHIBIT\s+([A-Z])\s*$', full, re.M))
    for x in sorted(set(re.findall(r'\bExhibit\s+([A-Z])\b', full))):
        if x not in ex_defined: findings.append(('MED', 'Exhibit referenced but not attached', 'Exhibit ' + x))
    # defined terms used in quotes but never defined
    used = set(re.findall(Q + r'([A-Z][A-Za-z’\' ]{2,40})' + Q, full))
    defined = set()
    for m in re.finditer(Q + r'\s*([A-Z][A-Za-z’\' ]{2,40})\s*' + Q + r'\s*(?:(shall\s+)?means?|is|are|shall be)\b', full): defined.add(m.group(1).strip())
    for m in re.finditer(r'\b(?:an?|the)\s+' + Q + r'\s*([A-Z][A-Za-z’\' ]{2,40})\s*' + Q + r'\s+(?:under|as used|for purposes)', full): defined.add(m.group(1).strip())
    for m in re.finditer(r'\((?:the|each|such|collectively,? the|hereinafter(?: referred to as)? the|each such [a-z]+,)\s*' + Q + r'\s*([A-Z][A-Za-z’\' ]{2,40})\s*' + Q + r'\)', full): defined.add(m.group(1).strip())
    for m in re.finditer(Q + r'\s*([A-Z][A-Za-z’\' ]{2,40})\s*' + Q + r'\s*\)', full): defined.add(m.group(1).strip())
    for m in re.finditer(r'hereinafter referred to as (?:the )?' + Q + r'\s*([A-Z][A-Za-z’\' ]{2,40})\s*' + Q, full): defined.add(m.group(1).strip())
    skip = {'AS IS', 'As Is', 'Money Rates', 'The Wall Street Journal', 'Rules and Regulations', 'Overnight Parking Area'}
    for term in sorted(used - defined - skip):
        if term.isupper(): continue  # heading refs handled above
        if re.search(r'\b' + re.escape(term) + r'\b', full.replace('“%s”' % term, '').replace('"%s"' % term, '')):
            findings.append(('LOW', 'quoted term used without a "means" definition (verify)', term))
    # tokens
    for tok in sorted(set(re.findall(r"\[[A-Z][A-Z0-9 /,.'&-]{2,}\]", full + ' ' + footers))):
        findings.append(('BLOCK', 'unfilled token', tok))
    return smap, findings

def main():
    path = sys.argv[1]; as_json = '--json' in sys.argv
    smap, findings = audit(path)
    if as_json:
        print(json.dumps({'sections': smap, 'findings': findings}, indent=1)); sys.exit(1 if findings else 0)
    print('SECTION MAP'); print('-' * 60)
    for lab, title in smap: print('%4s  %s' % (lab, title))
    print(); print('FINDINGS: %d' % len(findings)); print('-' * 60)
    for sev, kind, detail in findings: print('[%-5s] %-55s %s' % (sev, kind, detail))
    sys.exit(1 if findings else 0)

if __name__ == '__main__':
    main()
