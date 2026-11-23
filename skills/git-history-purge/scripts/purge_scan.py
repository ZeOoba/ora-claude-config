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
rule is a boundary-anchored regex: digits inside a longer number or a hex hash, and a
phone number inside a longer digit run, are never touched.

scan   - writes one rule per form ACTUALLY present, drops any rule that matches a blob in
         tip_ref's tree (a purge must leave the tip unchanged; scrub it with a reviewed PR
         first) and writes <rules-out>.paths.txt (affected paths).
verify - exit 1 if any removed path is still reachable, or any rule still matches a blob,
         a commit message or a tag message. Run it on the rewrite and on a fresh clone.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict

PH = b"[figure: private]"
PH_PHONE = b"[phone: private]"
PHONE_RE = re.compile(rb"(?<![\dA-Za-z])(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")
NUM_PRE = rb"(?<![0-9A-Fa-f])(?<![0-9][.,])\$?"
NUM_POST = rb"(?:\.0+)?(?![0-9])(?![.,][0-9])"


def git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", repo] + list(a), input=inp, capture_output=True, check=True).stdout


def refs_of(repo):
    return [r for r in git(repo, "for-each-ref", "--format=%(refname)").decode().split()
            if r.startswith(("refs/heads/", "refs/tags/"))]


def blob_paths(repo, refs):
    """sha -> set of every path that blob was ever stored at, across all refs."""
    out = defaultdict(set)
    if not refs:
        return out
    raw = git(repo, "log", "-z", "--raw", "--no-abbrev", "--no-renames", "--root", "-m", "--format=", *refs)
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
    msgs = git(repo, "log", "--format=%B%x00", *refs)
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


def num_rule(form):
    return b"regex:" + NUM_PRE + re.escape(form.encode()) + NUM_POST + b"==>" + PH


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
    refs, kept, _, msgs = history(repo, remove_rx)
    texts = dict(text_blobs(repo, list(kept)))
    corpus = list(texts.values()) + [msgs]

    candidates = []   # (kind, rule)
    for v in cfg.get("values", []):
        candidates += [("number", num_rule(f)) for f in sorted(figure_forms(v, min_int), key=len, reverse=True)]
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

    tip = []
    tip_ref = cfg.get("tip_ref", "refs/heads/main")
    if tip_ref in refs:
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
    return 0


def verify(repo, cfg, rules_path):
    remove_rx = re.compile(cfg["remove_path_regex"]) if cfg.get("remove_path_regex") else None
    with open(rules_path, "rb") as fh:
        rxs = [rule_regex(r) for r in fh.read().splitlines() if r]
    _, kept, removed, msgs = history(repo, remove_rx)
    hit_blobs = sum(1 for _, d in text_blobs(repo, list(kept)) if any(x.search(d) for x in rxs))
    msg_hits = sum(len(x.findall(msgs)) for x in rxs)
    print("removed paths still reachable: %d" % len(removed))
    print("blobs checked: %d; blobs matching a rule: %d; message hits: %d" % (len(kept), hit_blobs, msg_hits))
    return 1 if (removed or hit_blobs or msg_hits) else 0


def main(argv):
    if len(argv) != 5 or argv[1] not in ("scan", "verify"):
        print(__doc__)
        return 2
    with open(argv[3], encoding="utf-8") as fh:
        cfg = json.load(fh)
    return (scan if argv[1] == "scan" else verify)(argv[2], cfg, argv[4])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
