#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_edit_engine.py — JSON-driven, tracked-change-capable editor for ORA lease DOCX files.

Generalized from the 2026-09-07 Suite 15A (2207 Northwood) build, where it produced a clean
lease and a validator-clean tracked-change redline from the same op list.

USAGE
  python3 docx_edit_engine.py apply <in.docx> <ops.json> <out.docx> [--redline] [--author "Oxford Realty Advisors"]
  python3 docx_edit_engine.py dump  <in.docx>              # numbered paragraph listing (index | style | text)
  python3 docx_edit_engine.py fill  <in.docx> <tokens.json> <out.docx> [--redline]   # [TOKEN] fill, body + footers, asserted counts

OPS FILE  — JSON list of objects, applied in order. Paragraph refs ("at") are either
  {"index": 83}                                  original paragraph index (from `dump`), or
  {"match": "LANDLORD WORK"}                     first paragraph whose text contains the string, or
  {"match": "…", "nth": 2}                       nth such paragraph.
Refs always resolve against the ORIGINAL paragraph snapshot, so earlier inserts/deletes never shift them.

  {"op":"set_body",   "at":REF, "keep":1, "title":"Term", "text":".  Body with **bold** defined terms."}
      keep = number of leading runs to preserve (1 = keep the bold section title run); title = optional sub-title run
  {"op":"replace_all","at":REF, "title":null, "text":"…"}                       same as set_body with keep 0
  {"op":"sub",        "at":REF, "old":"exact phrase", "new":"replacement"}       in-run substitution; tracked as del/ins
  {"op":"sub_all",    "old":"All Risk Property insurance", "new":"…", "min":1}   document-wide
  {"op":"append",     "at":REF, "text":"  Sentence appended to the paragraph."}
  {"op":"insert_after","at":REF, "paras":[PARA, …]}                            new paragraphs after REF
  {"op":"delete",     "at":REF}
  {"op":"restyle",    "at":REF, "style":"H2"}                                    H1|H2|H3|BODY|IND|SIG|TITLE (tracked as pPrChange)
  {"op":"footer_field_replace", "field":"FILENAME", "text":"…"}                 replace a footer field with static text
  {"op":"footer_text_replace",  "startswith":"Rev ", "text":"…"}
  {"op":"strip_highlight"}      {"op":"strip_nbsp"}                            (strip_nbsp is skipped in redline mode)

PARA specs (for insert_after):
  {"kind":"H1","title":"RIGHTS RESERVED BY LANDLORD","text":".  Landlord reserves…"}   auto-numbered section
  {"kind":"H2","title":"Option to Extend","text":".  Provided that…"}                  auto-lettered (a)(b)…; title may be null
  {"kind":"H3","text":"…"}   {"kind":"BODY","text":"…"}   {"kind":"IND","text":"…"}     IND = body, 1" left indent
  {"kind":"SIG","text":"…","tabs":2}   {"kind":"TITLE","text":"EXHIBIT A"}   {"kind":"PAGEBREAK"}
Text markup: **…** → bold run (defined terms). Tabs inside text: use "tabs" on SIG only.

STYLE TEMPLATES are cloned from the document itself: the first Heading1/Heading2/Heading3/BodyText/Signature
paragraph found, so the output matches the form's own numbering and fonts. Override with "templates" in the
ops file: {"templates":{"H1":REF,"H2":REF,"H3":REF,"BODY":REF,"SIG":REF,"TITLE":REF,"BOLD_RUN":[REF,run_idx]}}.

REDLINE MODE emits real <w:ins>/<w:del>/<w:pPrChange> under the given author. Validate with the docx skill:
  python3 scripts/office/validate.py out.docx --original in.docx --author "Oxford Realty Advisors"
"""
import sys, os, re, copy, json, shutil, zipfile, tempfile, argparse
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'w': W}
def q(t): return '{%s}%s' % (W, t)

SEGTAGS = (q('t'), q('noBreakHyphen'), q('softHyphen'), q('tab'))


class Engine:
    def __init__(self, unpacked_dir, track=False, author='Oxford Realty Advisors', date='2026-01-01T00:00:00Z'):
        self.dir = unpacked_dir; self.track = track; self.author = author; self.date = date
        self._id = 9000
        self.tree = etree.parse(os.path.join(unpacked_dir, 'word/document.xml'))
        self.root = self.tree.getroot(); self.body = self.root.find('w:body', NS)
        self._unwrap_smarttags()
        self.P = self.body.findall('w:p', NS)          # snapshot: original paragraphs
        self.sectPr = self.body.find('w:sectPr', NS)
        self.templates = {}
        self._auto_templates()

    # ---------- infrastructure ----------
    def nid(self):
        self._id += 1; return str(self._id)

    def _unwrap_smarttags(self):
        for st in list(self.root.iter(q('smartTag'))):
            parent = st.getparent(); pos = parent.index(st)
            for k, c in enumerate([c for c in st if c.tag != q('smartTagPr')]):
                parent.insert(pos + k, c)
            parent.remove(st)

    @staticmethod
    def text_of(p): return ''.join(t.text or '' for t in p.iter(q('t')))
    @staticmethod
    def norm(s): return s.replace('\xa0', ' ')

    def style_of(self, p):
        pp = p.find('w:pPr', NS)
        if pp is None: return None
        s = pp.find('w:pStyle', NS)
        return s.get(q('val')) if s is not None else None

    def _auto_templates(self):
        want = {'H1': 'Heading1', 'H2': 'Heading2', 'H3': 'Heading3', 'BODY': 'BodyText', 'SIG': 'Signature'}
        for key, style in want.items():
            for p in self.P:
                if self.style_of(p) == style and p.find('w:pPr', NS).find('w:numPr', NS) is None:
                    self.templates[key] = copy.deepcopy(p.find('w:pPr', NS)); break
        for key in ('H1', 'H2', 'H3', 'BODY', 'SIG'):
            self.templates.setdefault(key, etree.Element(q('pPr')))
        # title paragraph: centered, no style (e.g. "LEASE")
        t = etree.Element(q('pPr')); jc = etree.SubElement(t, q('jc')); jc.set(q('val'), 'center')
        self.templates['TITLE'] = t
        # run properties
        def first_run_rpr(style):
            for p in self.P:
                if self.style_of(p) == style:
                    r = p.find('w:r', NS)
                    if r is not None and r.find('w:rPr', NS) is not None: return copy.deepcopy(r.find('w:rPr', NS))
            return None
        self.templates['H1_TITLE_RPR'] = first_run_rpr('Heading1')
        self.templates['H2_TITLE_RPR'] = first_run_rpr('Heading2')
        b = etree.Element(q('rPr')); etree.SubElement(b, q('b'))
        self.templates['BOLD_RPR'] = b

    def apply_template_overrides(self, spec):
        for key, ref in (spec or {}).items():
            if key == 'BOLD_RUN':
                p = self.resolve(ref[0]); r = p.findall('w:r', NS)[ref[1]]
                self.templates['BOLD_RPR'] = copy.deepcopy(r.find('w:rPr', NS))
            elif key.endswith('_RPR'):
                p = self.resolve(ref); self.templates[key] = copy.deepcopy(p.find('w:r', NS).find('w:rPr', NS))
            else:
                self.templates[key] = copy.deepcopy(self.resolve(ref).find('w:pPr', NS))

    def resolve(self, ref):
        if isinstance(ref, int): return self.P[ref]
        if 'index' in ref: return self.P[ref['index']]
        n = ref.get('nth', 1); hits = 0
        for p in self.P:
            if self.norm(ref['match']) in self.norm(self.text_of(p)):
                hits += 1
                if hits == n: return p
        raise SystemExit('REF NOT FOUND: %r' % ref)

    def _all_body_paragraphs(self):
        """All <w:p> elements anywhere in the body, INCLUDING ones nested inside tables
        (recursively, since tables can nest) -- used by document-wide ops like sub_all.
        self.P intentionally stays top-level-only: `dump`'s paragraph indices and
        {"index": N} refs must keep matching Word's own body-level paragraph numbering,
        which does not include table-cell paragraphs."""
        return list(self.body.iter(q('p')))

    # ---------- run builders ----------
    def mk_run(self, text, rPr=None, tabs=0, br=False):
        r = etree.Element(q('r'))
        if rPr is not None: r.append(copy.deepcopy(rPr))
        for _ in range(tabs): etree.SubElement(r, q('tab'))
        if br:
            b = etree.SubElement(r, q('br')); b.set(q('type'), 'page')
        if text:
            t = etree.SubElement(r, q('t')); t.text = text; t.set('{%s}space' % XML, 'preserve')
        return r

    def mk_runs(self, markup, base_rPr=None):
        runs = []
        for part in re.split(r'(\*\*.+?\*\*)', markup or ''):
            if not part: continue
            if part.startswith('**'): runs.append(self.mk_run(part[2:-2], self.templates['BOLD_RPR']))
            else: runs.append(self.mk_run(part, base_rPr))
        return runs

    def _mark(self, tag):
        m = etree.Element(q(tag)); m.set(q('id'), self.nid()); m.set(q('author'), self.author); m.set(q('date'), self.date)
        return m

    def ins_wrap(self, runs):
        if not self.track: return runs
        w = self._mark('ins')
        for r in runs: w.append(r)
        return [w]

    def del_wrap(self, runs):
        if not self.track: return []
        w = self._mark('del')
        for r in runs:
            for t in r.findall('w:t', NS): t.tag = q('delText')
            w.append(r)
        return [w]

    def _para_mark(self, p, tag):
        pp = p.find('w:pPr', NS)
        if pp is None: pp = etree.Element(q('pPr')); p.insert(0, pp)
        rpr = pp.find('w:rPr', NS)
        if rpr is None: rpr = etree.SubElement(pp, q('rPr'))
        rpr.insert(0, self._mark(tag))

    # ---------- paragraph builders ----------
    def new_para(self, kind, spec):
        pPr = copy.deepcopy(self.templates['BODY' if kind == 'IND' else kind])
        if kind == 'IND':
            ind = etree.SubElement(pPr, q('ind')); ind.set(q('left'), str(spec.get('indent', 1440)))
        p = etree.Element(q('p')); p.append(pPr)
        runs = []
        if kind == 'H1':
            runs.append(self.mk_run(spec['title'], self.templates['H1_TITLE_RPR'])); runs += self.mk_runs(spec.get('text', ''))
        elif kind == 'H2':
            if spec.get('title'): runs.append(self.mk_run(spec['title'], self.templates['H2_TITLE_RPR']))
            runs += self.mk_runs(spec.get('text', ''))
        elif kind in ('H3', 'BODY', 'IND'):
            runs += self.mk_runs(spec.get('text', ''))
        elif kind == 'SIG':
            if spec.get('text') or spec.get('tabs'): runs.append(self.mk_run(spec.get('text', ''), None, spec.get('tabs', 2)))
        elif kind == 'TITLE':
            runs.append(self.mk_run(spec['text'], self.templates['BOLD_RPR']))
        elif kind == 'PAGEBREAK':
            runs.append(self.mk_run('', None, 0, br=True))
        else:
            raise SystemExit('unknown para kind %r' % kind)
        for e in self.ins_wrap(runs): p.append(e)
        if self.track: self._para_mark(p, 'ins')
        return p

    # ---------- ops ----------
    def insert_after(self, ref, specs):
        anchor = self.resolve(ref); parent = anchor.getparent(); idx = parent.index(anchor)
        for k, s in enumerate(specs): parent.insert(idx + 1 + k, self.new_para(s['kind'], s))

    def set_body(self, ref, text, keep=1, title=None):
        p = self.resolve(ref); runs = p.findall('w:r', NS)
        if keep > 0 and len(runs) <= keep:
            raise SystemExit(
                'set_body: paragraph has %d run(s), which is <= keep=%d -- cannot safely '
                'preserve %d leading run(s) and replace "the rest" when there is no "rest" '
                '(this would silently APPEND the new text after the old text instead of '
                'replacing it). Paragraph text: %r' % (len(runs), keep, keep, self.text_of(p)[:120]))
        keep_runs, old = runs[:keep], runs[keep:]
        anchor = keep_runs[-1] if keep_runs else p.find('w:pPr', NS)
        for r in old: p.remove(r)
        new = ([self.mk_run(title, self.templates['H2_TITLE_RPR'])] if title else []) + self.mk_runs(text)
        seq = self.del_wrap(old) + self.ins_wrap(new)
        pos = (list(p).index(anchor) + 1) if anchor is not None else 0
        for k, e in enumerate(seq): p.insert(pos + k, e)

    @staticmethod
    def _segments(r):
        out = []
        for c in r:
            if c.tag == q('t'): out.append((c, c.text or ''))
            elif c.tag == q('noBreakHyphen'): out.append((c, '-'))
            elif c.tag == q('softHyphen'): out.append((c, ''))
            elif c.tag == q('tab'): out.append((c, '\t'))
        return out

    def _run_text(self, r): return ''.join(t for _, t in self._segments(r))

    def _live_runs(self, p):
        """Direct-child <w:r> runs of p, PLUS runs nested one level inside a direct-child
        <w:ins> wrapper -- already-tracked insertions are live document text (matches
        text_of()'s view, since <w:t> under <w:ins> still tags as <w:t>) and must stay
        matchable by a later op on the same paragraph. Runs inside <w:del> are excluded:
        deleted text is struck, not live (and del_wrap() already retags its <w:t> as
        <w:delText>, so text_of() itself never sees it). Without this, a second match in
        the same paragraph after a tracked substitution would silently vanish from
        _locate()'s view -- the just-inserted run is no longer a direct child of p -- and
        offset bookkeeping in sub_all() would desync from text_of()."""
        out = []
        for c in p:
            if c.tag == q('r'): out.append(c)
            elif c.tag == q('ins'): out.extend(c.findall('w:r', NS))
        return out

    def _locate(self, p, old, start=0):
        """Find `old` in p's LIVE run text (see _live_runs) at or after normalized-text
        offset `start`. Returns (runs, ia, ib, oa, ob, a) where `a` is the absolute match
        start offset in the normalized full text -- callers that substitute document-wide
        (sub_all) use `a` plus the replacement length to advance `start` past what they
        just inserted, so a replacement that contains its own search target (e.g. "Rent"
        -> "Base Rent") is never re-matched inside the text it just wrote."""
        runs = [r for r in self._live_runs(p) if self._run_text(r)]
        texts = [self.norm(self._run_text(r)) for r in runs]
        full = ''.join(texts); a = full.find(self.norm(old), start)
        if a < 0: return None
        b = a + len(self.norm(old)); pos = 0; ia = ib = oa = ob = None
        for k, tx in enumerate(texts):
            if ia is None and pos + len(tx) > a: ia = k; oa = a - pos
            if pos + len(tx) >= b: ib = k; ob = b - pos; break
            pos += len(tx)
        return runs, ia, ib, oa, ob, a

    def _slice_run(self, r, a, b):
        rPr = r.find('w:rPr', NS)
        outs = [etree.Element(q('r')) for _ in range(3)]
        for o in outs:
            if rPr is not None: o.append(copy.deepcopy(rPr))
        def add(o, elem, text):
            if elem.tag == q('t'):
                if text == '': return
                t = etree.SubElement(o, q('t')); t.text = text; t.set('{%s}space' % XML, 'preserve')
            else: o.append(copy.deepcopy(elem))
        pos = 0
        for elem, text in self._segments(r):
            n = len(text); s0, s1 = pos, pos + n
            if elem.tag != q('t'):
                add(outs[0 if s0 < a else (1 if s0 < b else 2)], elem, text)
            elif s1 <= a: add(outs[0], elem, text)
            elif s0 >= b: add(outs[2], elem, text)
            else:
                add(outs[0], elem, text[:max(0, a - s0)])
                add(outs[1], elem, text[max(0, a - s0):min(n, b - s0)])
                add(outs[2], elem, text[min(n, b - s0):])
            pos = s1
        return [o if any(c.tag in SEGTAGS for c in o) else None for o in outs]

    def sub(self, ref, old, new, start=0):
        """Substitute the first occurrence of `old` at/after normalized offset `start`
        with `new` (tracked as del/ins when self.track). Returns the absolute normalized
        offset where the match started, so sub_all can advance past its own output."""
        p = self.resolve(ref) if not isinstance(ref, etree._Element) else ref
        loc = self._locate(p, old, start)
        if loc is None: raise SystemExit('SUB FAILED (absent): %r' % old[:80])
        runs, ia, ib, oa, ob, a = loc
        if ia != ib:
            # _live_runs() (below) makes runs inside an existing <w:ins> visible to
            # _locate, so a match can now straddle the boundary between plain body runs
            # and an earlier op's <w:ins> wrapper -- impossible before that change. Moving
            # a plain (base-document) run's children into a run that lives inside <w:ins>
            # would silently relabel original text as a fresh insertion (or, on the
            # symmetric case, drop it with no <w:del> at all): a real data-loss/mislabel
            # risk on a legal instrument. Fail loudly instead of guessing. (2026-09-07
            # Fable review, finding: mixed-parent run merge.)
            # _live_runs() only ever exposes <w:r> elements that are direct children of
            # p, or direct children of a direct-child <w:ins> -- never <w:del> (deleted
            # text is retagged <w:delText> and excluded, see _live_runs' own docstring),
            # so the only boundary a span can cross here is plain-body <-> <w:ins>.
            parents = {id(runs[k].getparent()) for k in range(ia, ib + 1)}
            if len(parents) != 1:
                raise SystemExit(
                    'SUB FAILED (crosses tracked-change boundary): match for %r spans '
                    'runs that do not share one parent -- part of it is plain body text '
                    'and part is inside an existing <w:ins> from an earlier op. Cannot '
                    'merge without corrupting or mislabeling text; narrow the match or '
                    'apply this substitution before the op that created the earlier '
                    'tracked change.' % old[:80])
            base = runs[ia]
            for r in runs[ia + 1:ib + 1]:
                for c in list(r):
                    if c.tag != q('rPr'): base.append(c)
                r.getparent().remove(r)
            # Merging runs doesn't move any text, but a stale (start-less) re-locate here
            # would re-scan from offset 0 and could land on an EARLIER match this call
            # wasn't asked to touch (e.g. one already substituted into text that still
            # contains `old` as a substring of `new`) -- so re-locate with the same start.
            runs, ia, ib, oa, ob, a = self._locate(p, old, start)
            if ia != ib:
                raise SystemExit(
                    'SUB FAILED (internal): re-locate after merging runs for %r still '
                    'spans multiple runs (ia=%d, ib=%d) -- refusing to guess which one '
                    'to slice.' % (old[:80], ia, ib))
        r = runs[ia]; before, middle, after = self._slice_run(r, oa, ob)
        rPr = r.find('w:rPr', NS); parent = r.getparent(); pos = parent.index(r); parent.remove(r)
        # If the matched run already lives inside a <w:ins> (this paragraph carries an
        # earlier, still-uncommitted insertion an EARLIER op made -- never one this same
        # call just made; start-offset advancement rules that out), there is nothing to
        # mark del/ins around: the text was never part of the base document, so editing
        # it just rewrites the live content of that same <w:ins>. Wrapping it in a NEW
        # <w:del>/<w:ins> would nest <w:del> inside <w:ins>, which real Word never emits
        # and which validate.py would rightly flag.
        already_inserted = parent.tag == q('ins')
        seq = []
        if before is not None: seq.append(before)
        if self.track and not already_inserted:
            seq += self.del_wrap([middle]) + (self.ins_wrap([self.mk_run(new, rPr)]) if new else [])
        elif new: seq.append(self.mk_run(new, rPr))
        if after is not None: seq.append(after)
        for k, e in enumerate(seq): parent.insert(pos + k, e)
        return a

    def sub_all(self, old, new, minimum=1):
        """Document-wide substitution across every body paragraph, INCLUDING paragraphs
        nested inside tables (recursively -- see _all_body_paragraphs). Clean and redline
        mode share this exact code path: each match is substituted once, then the search
        offset advances past the just-inserted `new` text before searching again, so a
        pair where `old` is a substring of `new` (e.g. "Rent" -> "Base Rent") can never
        re-match inside its own freshly-written output -- in either mode. This replaces
        the old `if self.track and old in new: break` guard, which only protected redline
        mode (where it silently produced ZERO substitutions) and left clean mode -- the
        mode that ships -- to self-match up to the old 50-iteration cap.

        Existence checks use _locate() itself (via sub()'s own SystemExit-on-absent),
        NOT text_of(). text_of() counts only <w:t> text and skips <w:tab>/<w:noBreakHyphen>
        entirely, while _locate()'s offsets (what `start` is expressed in) come from
        _segments(), which counts a tab/no-break-hyphen as one character. Checking
        "any match left" against text_of() while advancing `start` in _locate()'s space
        mixes two different offset spaces -- on a paragraph with a tab or no-break-hyphen
        before a match, the text_of()-space search can land short of where the next real
        match actually is (in _locate()-space) and silently stop early, exactly the kind
        of silent skip defect 1 was about. Reusing _locate() end to end keeps everything
        in one consistent coordinate space (2026-09-07 second Fable review finding)."""
        n = 0
        norm_new = self.norm(new)
        for p in self._all_body_paragraphs():
            start = 0; guard = 0
            while guard < 50:
                if self._locate(p, old, start) is None: break
                a = self.sub(p, old, new, start=start)
                start = a + len(norm_new)
                n += 1; guard += 1
            else:
                raise SystemExit(
                    'SUB_ALL: guard limit (50) hit in one paragraph for %r -- stopped '
                    'rather than silently truncating; paragraph text: %r'
                    % (old[:60], self.text_of(p)[:120]))
        if n < minimum: raise SystemExit('SUB_ALL: %d < %d for %r' % (n, minimum, old[:60]))
        return n

    def append(self, ref, text):
        p = self.resolve(ref)
        for e in self.ins_wrap(self.mk_runs(text)): p.append(e)

    def delete(self, ref):
        p = self.resolve(ref)
        if self.track:
            runs = p.findall('w:r', NS)
            for r in runs: p.remove(r)
            for e in self.del_wrap(runs): p.append(e)
            self._para_mark(p, 'del')
        else:
            p.getparent().remove(p)

    def restyle(self, ref, style):
        p = self.resolve(ref); old = p.find('w:pPr', NS)
        npp = copy.deepcopy(self.templates['BODY' if style == 'IND' else style])
        if style == 'IND':
            ind = etree.SubElement(npp, q('ind')); ind.set(q('left'), '1440')
        if self.track and old is not None:
            chg = etree.SubElement(npp, q('pPrChange')); chg.set(q('id'), self.nid()); chg.set(q('author'), self.author); chg.set(q('date'), self.date)
            inner = copy.deepcopy(old)
            for c in list(inner):
                if c.tag in (q('rPr'), q('sectPr'), q('pPrChange')): inner.remove(c)
            chg.append(inner)
        if old is not None: p.remove(old)
        p.insert(0, npp)

    def strip_highlight(self):
        for h in list(self.root.iter(q('highlight'))): h.getparent().remove(h)

    def strip_nbsp(self):
        if self.track: return
        for t in self.root.iter(q('t')):
            if t.text and '\xa0' in t.text: t.text = t.text.replace('\xa0', ' ')

    # ---------- tokens ----------
    def fill_tokens(self, mapping):
        """Replace [TOKEN] occurrences in body + all footers/headers. Returns {token: count}."""
        counts = {k: 0 for k in mapping}
        parts = [self.tree] + self._aux_trees()
        for tr in parts:
            for p in tr.getroot().iter(q('p')):
                for tok, val in mapping.items():
                    needle = '[%s]' % tok
                    guard = 0
                    while needle in self.text_of(p) and guard < 20:
                        self.sub(p, needle, val); counts[tok] += 1; guard += 1
                    if guard >= 20:
                        raise SystemExit(
                            'fill_tokens: guard limit (20) hit filling [%s] in one '
                            'paragraph -- stopped rather than silently truncating; '
                            'paragraph text: %r' % (tok, self.text_of(p)[:120]))
        return counts

    def _aux_trees(self):
        if getattr(self, '_aux', None) is None:
            self._aux = []; self._aux_paths = []
            wd = os.path.join(self.dir, 'word')
            for n in sorted(os.listdir(wd)):
                if re.match(r'(footer|header)\d*\.xml$', n):
                    self._aux.append(etree.parse(os.path.join(wd, n))); self._aux_paths.append(os.path.join(wd, n))
        return self._aux

    def footer_field_replace(self, field, text):
        for tr in self._aux_trees():
            for p in tr.getroot().iter(q('p')):
                runs = p.findall('w:r', NS); idx = None
                for k, r in enumerate(runs):
                    it = r.find('w:instrText', NS)
                    if it is not None and field in (it.text or ''): idx = k; break
                if idx is None: continue
                def is_fld(r, kind):
                    f = r.find('w:fldChar', NS); return f is not None and f.get(q('fldCharType')) == kind
                b = idx
                while b >= 0 and not is_fld(runs[b], 'begin'): b -= 1
                e = idx
                while e < len(runs) and not is_fld(runs[e], 'end'): e += 1
                rPr = copy.deepcopy(runs[idx].find('w:rPr', NS)); pos = p.index(runs[b])
                for r in runs[b:e + 1]: p.remove(r)
                p.insert(pos, self.mk_run(text, rPr))

    def footer_text_replace(self, startswith, text):
        for tr in self._aux_trees():
            for t in tr.getroot().iter(q('t')):
                if (t.text or '').startswith(startswith): t.text = text

    # ---------- save ----------
    def save(self):
        self.tree.write(os.path.join(self.dir, 'word/document.xml'), xml_declaration=True, encoding='UTF-8', standalone=True)
        for tr, pth in zip(getattr(self, '_aux', []) or [], getattr(self, '_aux_paths', []) or []):
            tr.write(pth, xml_declaration=True, encoding='UTF-8', standalone=True)

    def apply_ops(self, ops):
        for i, op in enumerate(ops):
            k = op['op']
            try:
                if k == 'set_body': self.set_body(op['at'], op['text'], op.get('keep', 1), op.get('title'))
                elif k == 'replace_all': self.set_body(op['at'], op['text'], 0, op.get('title'))
                elif k == 'sub': self.sub(op['at'], op['old'], op['new'])
                elif k == 'sub_all': self.sub_all(op['old'], op['new'], op.get('min', 1))
                elif k == 'append': self.append(op['at'], op['text'])
                elif k == 'insert_after': self.insert_after(op['at'], op['paras'])
                elif k == 'delete': self.delete(op['at'])
                elif k == 'restyle': self.restyle(op['at'], op['style'])
                elif k == 'footer_field_replace': self.footer_field_replace(op['field'], op['text'])
                elif k == 'footer_text_replace': self.footer_text_replace(op['startswith'], op['text'])
                elif k == 'strip_highlight': self.strip_highlight()
                elif k == 'strip_nbsp': self.strip_nbsp()
                elif k == 'fill_tokens':
                    c = self.fill_tokens(op['tokens'])
                    missing = [t for t, n in c.items() if n == 0 and op.get('assert_all', True)]
                    if missing: raise SystemExit('fill_tokens: tokens not found in document: %s' % missing)
                else: raise SystemExit('unknown op %r' % k)
            except SystemExit as e:
                raise SystemExit('op #%d (%s) failed: %s' % (i, k, e))


# ---------- CLI ----------
def _unpack(docx, d):
    with zipfile.ZipFile(docx) as z: z.extractall(d)
    for rootd, _, files in os.walk(d):
        for f in files:
            pth = os.path.join(rootd, f)
            if os.path.islink(pth): os.remove(pth)

def _pack(d, out):
    if os.path.exists(out): os.remove(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rootd, _, files in os.walk(d):
            for f in files:
                full = os.path.join(rootd, f); z.write(full, os.path.relpath(full, d))

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('apply'); a.add_argument('inp'); a.add_argument('ops'); a.add_argument('out')
    a.add_argument('--redline', action='store_true'); a.add_argument('--author', default='Oxford Realty Advisors'); a.add_argument('--date', default='2026-01-01T00:00:00Z')
    d = sp.add_parser('dump'); d.add_argument('inp')
    f = sp.add_parser('fill'); f.add_argument('inp'); f.add_argument('tokens'); f.add_argument('out'); f.add_argument('--redline', action='store_true'); f.add_argument('--author', default='Oxford Realty Advisors')
    args = ap.parse_args()
    tmp = tempfile.mkdtemp()
    try:
        _unpack(args.inp, tmp)
        if args.cmd == 'dump':
            e = Engine(tmp)
            for i, p in enumerate(e.P):
                t = e.text_of(p)
                if t.strip(): print('%4d | %-10s | %s' % (i, e.style_of(p) or '-', t[:110]))
            return
        e = Engine(tmp, track=args.redline, author=args.author, date=getattr(args, 'date', '2026-01-01T00:00:00Z'))
        if args.cmd == 'apply':
            spec = json.load(open(args.ops, encoding='utf-8'))
            ops = spec['ops'] if isinstance(spec, dict) else spec
            if isinstance(spec, dict) and spec.get('templates'): e.apply_template_overrides(spec['templates'])
            e.apply_ops(ops)
        else:
            mapping = json.load(open(args.tokens, encoding='utf-8'))
            c = e.fill_tokens(mapping); print(json.dumps(c, indent=1))
            missing = [t for t, n in c.items() if n == 0]
            if missing:
                # Matches this script's own docstring ("any token found 0 times during a
                # fill operation is a fill error") and SKILL.md -- a hard failure (non-zero
                # exit), not a warning that a caller can silently ignore.
                raise SystemExit('fill: unfilled token(s), 0 occurrences found: %s' % missing)
        e.save(); _pack(tmp, args.out)
        print('written', args.out, '(redline)' if args.redline else '(clean)')
    finally:
        # Guaranteed cleanup on every exit path (success, `dump`'s early return, or any
        # SystemExit/exception raised above) -- previously only the success path cleaned
        # up, so every failure (including the fill-unfilled-token hard-fail this same
        # change adds) leaked its unpacked tempdir.
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == '__main__':
    main()
