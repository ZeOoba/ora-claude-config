"""Build and verify git-filter-repo replace rules for a history purge. Prints COUNTS ONLY.

  python -I purge_scan.py scan   <repo.git> <purge-config.json> <rules-out.txt>
  python -I purge_scan.py verify <repo.git> <purge-config.json> <rules.txt>

purge-config.json lives OUTSIDE every repo (it holds the private values):
  {"remove_path_regex": "(^|/)notes/",          # paths filter-repo removes outright (not scanned)
   "values": [123457.0, ...],                     # private figures; round thousands are ignored
   "literals": ["Exact private string", ...],
   "phones": true, "public_phones": ["6145550100"]}   # 10-digit numbers allowed to stay

scan   - reads every text blob and commit message reachable from refs/heads + refs/tags, writes one
         --replace-text rule per private value ACTUALLY present, and DROPS any rule that also matches
         a blob in main's tip tree (a purge must leave main's tree unchanged; scrub the tip with a
         normal reviewed PR first). Numeric rules are boundary-anchored: digits inside a longer
         number or a hex hash are never touched. Also writes <rules-out>.paths.txt (affected paths).
verify - exit 1 if any removed path is still reachable or any rule in <rules.txt> still matches a
         blob or commit message (run it on the rewritten repo, and again on a fresh clone).
"""
import json
import re
import subprocess
import sys

TEXT_EXT = {".md", ".py", ".json", ".jsonl", ".txt", ".ps1", ".sh", ".yml", ".yaml", ".js", ".ts",
            ".csv", ".html", ".toml", ".ini", ".cfg", ""}
PH = b"[figure: private]"
PH_PHONE = b"[phone: private]"
PHONE_RE = re.compile(r"(?<![\dA-Za-z])(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")


def git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", repo] + list(a), input=inp, capture_output=True, check=True).stdout


def ext(path):
    base = path.rsplit("/", 1)[-1]
    return ("." + base.rsplit(".", 1)[-1].lower()) if "." in base else ""


def text_blobs(repo, shas):
    """Yield (sha, text) for non-binary blobs, via one cat-file --batch process."""
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    try:
        for sha in shas:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            data = proc.stdout.read(int(header[2]))
            proc.stdout.read(1)
            if b"\0" not in data[:8000]:
                yield sha, data
    finally:
        proc.stdin.close()
        proc.wait()


def history(repo, remove_rx):
    """Text blobs reachable from heads+tags, keyed sha -> first path; plus removed-path hits."""
    refs = [r for r in git(repo, "for-each-ref", "--format=%(refname)").decode().split()
            if r.startswith(("refs/heads/", "refs/tags/"))]
    blobs, removed = {}, set()
    for line in git(repo, "rev-list", "--objects", *refs).decode("utf-8", "replace").splitlines():
        sha, _, path = line.partition(" ")
        if not path:
            continue
        if remove_rx and remove_rx.search(path):
            removed.add(path)
            continue
        if ext(path) in TEXT_EXT:
            blobs.setdefault(sha, path)
    if blobs:
        kinds = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                    inp="\n".join(blobs).encode()).decode().splitlines()
        blobs = {s: blobs[s] for s, t in (k.split() for k in kinds) if t == "blob"}
    msgs = git(repo, "log", "--format=%B%x00", *refs) if refs else b""
    return refs, blobs, removed, msgs


def rule_regex(rule):
    pat = rule.partition(b"==>")[0]
    return re.compile(pat[6:]) if pat.startswith(b"regex:") else re.compile(re.escape(pat))


def num_rule(form):
    return (b"regex:(?<![0-9A-Fa-f])(?<![0-9][.,])\\$?" + re.escape(form).encode()
            + b"(?:\\.0+)?(?![0-9])(?![.,][0-9])==>" + PH)


def scan(repo, cfg, out):
    remove_rx = re.compile(cfg["remove_path_regex"]) if cfg.get("remove_path_regex") else None
    forms = set()
    for v in cfg.get("values", []):
        if v >= 10000 and not (v == int(v) and int(v) % 1000 == 0):
            if v == int(v):
                forms.add("{:,}".format(int(v)))
            forms.add("{:,.2f}".format(v))
    num = re.compile(r"(?<![0-9A-Fa-f])(?<![\d][.,])(%s)(?:\.0+)?(?![\d])(?![.,]\d)"
                     % "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))) if forms else None
    lits = cfg.get("literals", [])
    lit = re.compile("|".join(re.escape(x) for x in sorted(lits, key=len, reverse=True))) if lits else None
    public = set(cfg.get("public_phones", []))
    refs, blobs, _, msgs = history(repo, remove_rx)
    f_num, f_lit, f_ph, hit_paths = set(), set(), set(), set()
    for sha, data in text_blobs(repo, list(blobs)):
        text = data.decode("utf-8", "replace")
        n0 = len(f_num) + len(f_lit) + len(f_ph)
        hit = False
        for rx, bucket in ((num, f_num), (lit, f_lit)):
            if rx:
                for m in rx.finditer(text):
                    bucket.add(m.group(1) if rx is num else m.group(0))
                    hit = True
        if cfg.get("phones"):
            for m in PHONE_RE.finditer(text):
                if re.sub(r"\D", "", m.group(0))[-10:] not in public:
                    f_ph.add(m.group(0))
                    hit = True
        if hit or len(f_num) + len(f_lit) + len(f_ph) > n0:
            hit_paths.add(blobs[sha])
    mtext = msgs.decode("utf-8", "replace")
    for rx, bucket in ((num, f_num), (lit, f_lit)):
        if rx:
            for m in rx.finditer(mtext):
                bucket.add(m.group(1) if rx is num else m.group(0))
    rules = [num_rule(f) for f in sorted(f_num, key=len, reverse=True)]
    rules += [x.encode("utf-8") + b"==>" + PH for x in sorted(f_lit, key=len, reverse=True)]
    rules += [p.encode("utf-8") + b"==>" + PH_PHONE for p in sorted(f_ph, key=len, reverse=True)]
    # Drop rules that would change main's tip tree.
    tip = []
    if "refs/heads/main" in refs:
        ls = git(repo, "ls-tree", "-r", "main").decode().splitlines()
        tip = [d for _, d in text_blobs(repo, [l.split()[2] for l in ls if l.split()[1] == "blob"])]
    keep = [r for r in rules if not any(rule_regex(r).search(d) for d in tip)]
    with open(out, "wb") as fh:
        fh.write(b"\n".join(keep) + (b"\n" if keep else b""))
    with open(out + ".paths.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(hit_paths)) + "\n")
    print("blobs scanned: %d; affected paths: %d" % (len(blobs), len(hit_paths)))
    print("found: numbers %d, literals %d, phones %d" % (len(f_num), len(f_lit), len(f_ph)))
    print("rules written: %d; dropped (present at main tip): %d" % (len(keep), len(rules) - len(keep)))
    return 0


def verify(repo, cfg, rules_path):
    remove_rx = re.compile(cfg["remove_path_regex"]) if cfg.get("remove_path_regex") else None
    rules = [r for r in open(rules_path, "rb").read().splitlines() if r]
    rxs = [rule_regex(r) for r in rules]
    _, blobs, removed, msgs = history(repo, remove_rx)
    hit_blobs = sum(1 for _, d in text_blobs(repo, list(blobs)) if any(x.search(d) for x in rxs))
    msg_hits = sum(len(x.findall(msgs)) for x in rxs)
    print("removed paths still reachable: %d" % len(removed))
    print("blobs checked: %d; blobs matching a rule: %d; commit-message hits: %d"
          % (len(blobs), hit_blobs, msg_hits))
    return 1 if (removed or hit_blobs or msg_hits) else 0


def main(argv):
    if len(argv) != 5 or argv[1] not in ("scan", "verify"):
        print(__doc__)
        return 2
    cfg = json.load(open(argv[3], encoding="utf-8"))
    return (scan if argv[1] == "scan" else verify)(argv[2], cfg, argv[4])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
