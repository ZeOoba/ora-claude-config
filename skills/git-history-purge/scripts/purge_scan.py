"""Build and verify git-filter-repo replace rules for a history purge. Prints COUNTS ONLY.

  python -I purge_scan.py scan   <repo.git> <purge-config.json> <rules-out.txt>
  python -I purge_scan.py verify <repo.git> <purge-config.json> <rules.txt>

purge-config.json lives OUTSIDE every repo (it holds the private values):
  {"remove_path_regex": "(^|/)notes/",   # paths filter-repo removes outright
   "values": [123457, 9876.54, ...],      # private figures
   "min_integer": 10000,                  # optional; whole numbers below it are skipped (default 10000)
   "literals": ["Exact private string", ...],
   "phones": true, "public_phones": ["6145550100"],   # 10-digit numbers allowed to stay
   "tip_ref": "refs/heads/main"}          # optional; the tree the purge must not change

Every blob is examined under EVERY path it was ever stored at (git log --raw over all
branches and tags), not just the first path rev-list reports. A blob is scanned when at
least one of its paths is kept. Text vs binary is decided by content, as filter-repo does
(a NUL byte in the first 8192 bytes means binary); binary files holding private data must
be removed by path. Commit messages and annotated-tag messages are scanned too.

Figure forms: a whole number gives "123,457", "123457", "123,457.00" and "123457.00"
(round thousands and values below min_integer are skipped: too common to replace safely);
a non-whole value of 1,000 or more gives "9,876.54", "9876.54" and its shortest form
("123,456.5"). Every
rule is a boundary-anchored regex: digits inside a longer number or a hex hash (before or
after), and a phone number inside a longer digit run, are never touched. Skipped values are
counted in the output: they are NOT searched, so purge them another way if they matter.
scan exits 2 if tip_ref does not exist or a literal contains a line break.

scan   - writes one rule per form ACTUALLY present, drops any rule that matches a blob in
         tip_ref's tree (a purge must leave the tip unchanged; scrub it with a reviewed PR
         first) and writes <rules-out>.paths.txt (affected paths).
verify - exit 1 if any removed path is still reachable, any rule still matches a blob, a
         commit message or a tag message, OR the independent search finds a configured
         value or literal anywhere in the object store (every blob, commit and tag object,
         not walked by ref or path; values present in the tip's files are accepted and
         counted separately). Run it on the rewrite and on a fresh `git clone --bare`
         (a --mirror clone also fetches GitHub's refs/pull/*, which still hold old history).
"""
import json
import re
import subprocess
import sys
from collections import defaultdict

PH = b"[figure: private]"
PH_PHONE = b"[phone: private]"
PHONE_RE = re.compile(rb"(?<![\dA-Za-z])(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")
HEX = rb"0-9A-Fa-f"


def git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", repo] + list(a), input=inp, capture_output=True, check=True).stdout


def refs_of(repo):
    return [r for r in git(repo, "for-each-ref", "--format=%(refname)").decode().split()
            if r.startswith(("refs/heads/", "refs/tags/"))]


def blob_paths(repo, refs):
    """sha -> set of every path that blob was ever stored at, across all branches and tags."""
    out = defaultdict(set)
    if not refs:
        return out
    # --branches --tags instead of listing refs: hundreds of ref names exceed the Windows command line.
    raw = git(repo, "log", "-z", "--raw", "--no-abbrev", "--no-renames", "--root", "-m", "--format=",
              "--branches", "--tags")
    toks = raw.split(b"\0")
    i = 0
    while i < len(toks):
        t = toks[i].lstrip(b"\n")
        if t.startswith(b":") and i + 1 < len(toks):
            new = t.split()[3].decode()
            if set(new) != {"0"}:
                out[new].add(toks[i + 1].decode("utf-8", "surrogateescape"))
            i += 2
        else:
            i += 1
    if out:
        kinds = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                    inp="\n".join(out).encode()).decode().splitlines()
        blobs = {s for s, t in (k.split() for k in kinds) if t == "blob"}
        out = {s: p for s, p in out.items() if s in blobs}
    return out


def text_blobs(repo, shas):
    """Yield (sha, data) for blobs filter-repo treats as text (no NUL in the first 8192 bytes)."""
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    try:
        for sha in shas:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            data = proc.stdout.read(int(header[2]))
            proc.stdout.read(1)
            if b"\0" not in data[:8192]:
                yield sha, data
    finally:
        proc.stdin.close()
        proc.wait()


def messages(repo, refs):
    """Commit messages plus annotated-tag messages, as one bytes blob."""
    if not refs:
        return b""
    msgs = git(repo, "log", "--format=%B%x00", "--branches", "--tags")
    tags = git(repo, "for-each-ref", "--format=%(objecttype)%00%(contents)%00", "refs/tags").split(b"\0")
    for kind, body in zip(tags[0::2], tags[1::2]):
        if kind.strip() == b"tag":
            msgs += body + b"\0"
    return msgs


def history(repo, remove_rx):
    refs = refs_of(repo)
    paths = blob_paths(repo, refs)
    removed = {p for ps in paths.values() for p in ps if remove_rx and remove_rx.search(p)}
    kept = {s: sorted(p for p in ps if not (remove_rx and remove_rx.search(p))) for s, ps in paths.items()}
    kept = {s: ps for s, ps in kept.items() if ps}
    return refs, kept, removed, messages(repo, refs)


def figure_forms(v, min_integer):
    if v == int(v):
        i = int(v)
        if abs(i) < min_integer or i % 1000 == 0:
            return set()
        return {"{:,}".format(i), str(i), "{:,.2f}".format(i), "{:.2f}".format(i)}
    if abs(v) < 1000:
        return set()
    short = repr(float(v))
    whole, _, frac = short.partition(".")
    return {"{:,.2f}".format(v), "{:.2f}".format(v), short, "{:,}".format(int(whole)) + "." + frac}


def num_pattern(form):
    """Anchored pattern for one written form of a figure.

    Always: no hex/digit glued on either side (hashes, longer numbers), no decimal point
    before it (0.123457) or decimal digits after it (123457.12). Only for comma-grouped
    forms: no thousands group before or after (1,123,457 / 123,457,000). A plain form next
    to a comma is a CSV or JSON neighbour (BldgA,123457,2450000), so it still matches.
    """
    pre = b"(?<![" + HEX + b"])(?<![0-9]\\.)"
    post = b"(?:\\.0+)?(?![" + HEX + b"])(?!\\.[0-9])"
    if "," in form:
        if len(form.split(",")[0].lstrip("-")) == 3:
            pre += b"(?<![0-9],)"
        post += b"(?!,[0-9]{3}(?![0-9]))"
    return pre + b"\\$?" + re.escape(form.encode()) + post


def num_rule(form):
    return b"regex:" + num_pattern(form) + b"==>" + PH


def phone_rule(p):
    return b"regex:(?<![0-9A-Za-z])" + re.escape(p) + b"(?![0-9])==>" + PH_PHONE


def lit_rule(s):
    return b"regex:" + re.escape(s.encode("utf-8")) + b"==>" + PH


def rule_regex(rule):
    pat = rule.rpartition(b"==>")[0]
    return re.compile(pat[6:]) if pat.startswith(b"regex:") else re.compile(re.escape(pat))


def scan(repo, cfg, out):
    remove_rx = re.compile(cfg["remove_path_regex"]) if cfg.get("remove_path_regex") else None
    min_int = int(cfg.get("min_integer", 10000))
    public = set(cfg.get("public_phones", []))
    if any("\n" in s or "\r" in s for s in cfg.get("literals", [])):
        print("a literal contains a line break: filter-repo rules are one per line; split it into one literal per line")
        return 2
    refs, kept, _, msgs = history(repo, remove_rx)
    tip_ref = cfg.get("tip_ref", "refs/heads/main")
    if tip_ref not in refs:
        print("tip_ref %s not found: set \"tip_ref\" in the config to the branch whose tree must not change" % tip_ref)
        return 2
    texts = dict(text_blobs(repo, list(kept)))
    corpus = list(texts.values()) + [msgs]

    candidates = []   # (kind, rule)
    skipped = 0
    for v in cfg.get("values", []):
        forms = figure_forms(v, min_int)
        skipped += 0 if forms else 1
        candidates += [("number", num_rule(f)) for f in sorted(forms, key=len, reverse=True)]
    candidates += [("literal", lit_rule(s)) for s in cfg.get("literals", [])]
    if cfg.get("phones"):
        phones = set()
        for d in corpus:
            for m in PHONE_RE.finditer(d):
                if re.sub(rb"\D", b"", m.group(0))[-10:].decode() not in public:
                    phones.add(m.group(0))
        candidates += [("phone", phone_rule(p)) for p in sorted(phones, key=len, reverse=True)]

    present = []
    for kind, rule in dict.fromkeys(candidates):
        rx = rule_regex(rule)
        if any(rx.search(d) for d in corpus):
            present.append((kind, rule))

    ls = git(repo, "ls-tree", "-r", tip_ref).decode().splitlines()
    tip = [d for _, d in text_blobs(repo, [l.split()[2] for l in ls if l.split()[1] == "blob"])]
    keep = [(k, r) for k, r in present if not any(rule_regex(r).search(d) for d in tip)]

    rxs = [rule_regex(r) for _, r in keep]
    hit_paths = {p for s, d in texts.items() if any(x.search(d) for x in rxs) for p in kept[s]}
    with open(out, "wb") as fh:
        fh.write(b"\n".join(r for _, r in keep) + (b"\n" if keep else b""))
    with open(out + ".paths.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(hit_paths)) + "\n")
    count = lambda rows, k: sum(1 for kind, _ in rows if kind == k)
    print("blobs scanned: %d; affected paths: %d" % (len(texts), len(hit_paths)))
    print("found: numbers %d, literals %d, phones %d"
          % (count(present, "number"), count(present, "literal"), count(present, "phone")))
    print("rules written: %d; dropped (present at tip): %d" % (len(keep), len(present) - len(keep)))
    print("values skipped (round thousands or below threshold, NOT searched): %d" % skipped)
    return 0


def all_objects(repo):
    """Yield (sha, type, data) for EVERY object in the repo's store (no ref or path walk)."""
    lst = git(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)").decode().split("\n")
    shas = [l.split()[0] for l in lst if l and l.split()[1] in ("blob", "commit", "tag")]
    kinds = {l.split()[0]: l.split()[1] for l in lst if l}
    for sha, data in text_blobs(repo, shas):
        yield sha, kinds[sha], data


def residual(repo, cfg, tip_ref):
    """Independent of the scan's rules: search every object for every configured value.

    Loose patterns (only hex/digit neighbours excluded), so a value the rules missed -
    wrong form, odd context, unusual file - still shows up. Values present in the tip's
    files are reported as kept at the tip (accepted) and not counted as residual.
    Returns (values with a residual, occurrences, values kept at tip).
    """
    min_int = int(cfg.get("min_integer", 10000))
    pats = []
    for v in cfg.get("values", []):
        forms = figure_forms(v, min_int)
        if forms:
            alt = b"|".join(re.escape(f.encode()) for f in sorted(forms, key=len, reverse=True))
            pats.append(re.compile(b"(?<![" + HEX + b"])(?:" + alt + b")(?![" + HEX + b"])"))
    pats += [re.compile(re.escape(s.encode("utf-8"))) for s in cfg.get("literals", [])]
    tip_blobs = set()
    if tip_ref:
        tip_blobs = {l.split()[2] for l in git(repo, "ls-tree", "-r", tip_ref).decode().splitlines()
                     if l.split()[1] == "blob"}
    objs = list(all_objects(repo))
    at_tip = {i for i, rx in enumerate(pats) if any(rx.search(d) for s, _, d in objs if s in tip_blobs)}
    left, count = set(), 0
    for sha, _, data in objs:
        if sha in tip_blobs:
            continue
        for i, rx in enumerate(pats):
            if i in at_tip:
                continue
            n = len(rx.findall(data))
            if n:
                left.add(i)
                count += n
    return len(left), count, len(at_tip)


def verify(repo, cfg, rules_path):
    remove_rx = re.compile(cfg["remove_path_regex"]) if cfg.get("remove_path_regex") else None
    with open(rules_path, "rb") as fh:
        rxs = [rule_regex(r) for r in fh.read().splitlines() if r]
    refs, kept, removed, msgs = history(repo, remove_rx)
    tip_ref = cfg.get("tip_ref", "refs/heads/main")
    if tip_ref not in refs:
        print("tip_ref %s not found" % tip_ref)
        return 2
    hit_blobs = sum(1 for _, d in text_blobs(repo, list(kept)) if any(x.search(d) for x in rxs))
    msg_hits = sum(len(x.findall(msgs)) for x in rxs)
    left, occ, at_tip = residual(repo, cfg, tip_ref)
    print("removed paths still reachable: %d" % len(removed))
    print("blobs checked: %d; blobs matching a rule: %d; message hits: %d" % (len(kept), hit_blobs, msg_hits))
    print("independent search of every object: values still present: %d (%d occurrences); "
          "kept at tip (accepted): %d" % (left, occ, at_tip))
    return 1 if (removed or hit_blobs or msg_hits or left) else 0


def main(argv):
    if len(argv) != 5 or argv[1] not in ("scan", "verify"):
        print(__doc__)
        return 2
    with open(argv[3], encoding="utf-8") as fh:
        cfg = json.load(fh)
    return (scan if argv[1] == "scan" else verify)(argv[2], cfg, argv[4])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
