#!/usr/bin/env python3
"""Tests for git-prepush-confidential-scan.py: CONTEXT roster terms and URL-ENCODED views.

Two gaps the pre-push gate shared with its ports (audit 2026-11-12, Defect 2):
  (a) load_terms() read only `always` terms, so an active deal carrying only `context` /
      `context_requires_any` contributed NOTHING -- `if terms:` was false and the terms scan
      was skipped entirely (allow-without-scan).
  (b) no percent / `+` decoding, so `Quiet%20Marsh%20Park` and `Quiet+Marsh+Park` in a pushed
      diff never matched the roster term "quiet marsh park".

Semantics pinned here (the windowing is now STRICTER than the ora-skills port,
tools/prepush_confidential_scan.py -- REFUTE 2026-11-23):
  * a context term counts only when one of its deal's anchors co-occurs in the SAME window;
    window = one whole commit (header + message + patch), one blob view (each decompressed
    member / UTF-16 view), or the full content of a plain file a pushed commit adds or modifies
    (anchored context entries only);
  * anchorless context (no / empty / blank / non-list / non-string anchors) FAILS CLOSED: the
    context term counts on its own;
  * a malformed `context` or `always` field (not a list, or a non-string entry) makes the roster
    unreadable -> load_terms() None -> the push blocks;
  * decoding is bounded (URL_DECODE_MAX_ROUNDS) and covers both unquote and unquote_plus.

Synthetic terms only -- this repo is PUBLIC. Run: python test-git-prepush-context-urlencode.py
"""
import gzip
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "pps_ctx", os.path.join(HOOKS, "git-prepush-confidential-scan.py"))
pps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pps)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# Synthetic roster (never real deal data).
ALWAYS = "quiet marsh park"
CTX_TERM = "kestrel"
ANCHORS = ["offering memo", "rent roll"]
ALL_SYNTHETIC = [ALWAYS, CTX_TERM] + ANCHORS


def _with_roster(roster, fn):
    """Point the module at a temp terms file holding `roster` (dict, or raw str) and run fn().
    HOOK_DIR goes outside any git repo, so the main-worktree fallback cannot pull in the live
    roster behind the test's back."""
    td = tempfile.mkdtemp(prefix="pps-ctx-roster-")
    hooks = os.path.join(td, "hooks")
    os.makedirs(hooks)
    path = os.path.join(hooks, "confidential-terms.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(roster if isinstance(roster, str) else json.dumps(roster))
    saved = pps.HOOK_DIR, pps.TERMS_FILE
    try:
        pps.HOOK_DIR, pps.TERMS_FILE = hooks, path
        return fn()
    finally:
        pps.HOOK_DIR, pps.TERMS_FILE = saved


def _deal(**fields):
    d = {"label": "Synthetic", "active": True}
    d.update(fields)
    return {"_meta": {"purpose": "synthetic"}, "synthetic_deal": d}


# --- (a) load_terms: context terms are loaded --------------------------------------------
ctx_only = _deal(always=[], context=[CTX_TERM], context_requires_any=ANCHORS)
t = _with_roster(ctx_only, pps.load_terms)
expect("load: a context-only active deal yields a NON-EMPTY term list (no allow-without-scan)",
       bool(t), repr(t))
expect("load: an always-only deal still loads exactly as before",
       _with_roster(_deal(always=["Quiet Marsh Park"]), pps.load_terms) == [ALWAYS])
expect("load: an inactive context-only deal contributes nothing",
       _with_roster({"d": {"active": False, "context": [CTX_TERM],
                           "context_requires_any": ANCHORS}}, pps.load_terms) == [])
expect("load: `context` not a list -> roster malformed -> None (fail-closed)",
       _with_roster(_deal(always=[], context=CTX_TERM, context_requires_any=ANCHORS),
                    pps.load_terms) is None)
expect("load: non-string `context` entry -> None (fail-closed)",
       _with_roster(_deal(always=[], context=[CTX_TERM, 7], context_requires_any=ANCHORS),
                    pps.load_terms) is None)
expect("load: `always` as a bare string (not a list) -> None (fail-closed, not per-char terms)",
       _with_roster(_deal(always=ALWAYS), pps.load_terms) is None)

# --- (a) scan_text: anchor co-occurrence in the same window ------------------------------
terms_ctx = _with_roster(ctx_only, pps.load_terms) or []
expect("scan: context term WITHOUT an anchor in the window -> no hit",
       pps.scan_text("note: kestrel", terms_ctx) == [])
expect("scan: context term WITH an anchor in the same window -> hit",
       pps.scan_text("Kestrel -- see the Offering Memo", terms_ctx) != [])
expect("scan: anchor alone is not a hit",
       pps.scan_text("the rent roll is attached", terms_ctx) == [])
expect("scan: a hit reports indices, never the term",
       all(s not in repr(pps.scan_text("kestrel rent roll", terms_ctx)) for s in ALL_SYNTHETIC))

for lbl, anchors_field in (("missing", None), ("empty list", []), ("blank entry", ["  "]),
                           ("blank next to a real anchor", ["rent roll", ""]),
                           ("not a list", "rent roll"), ("non-string entry", [3])):
    fields = {"always": [], "context": [CTX_TERM]}
    if anchors_field is not None:
        fields["context_requires_any"] = anchors_field
    tt = _with_roster(_deal(**fields), pps.load_terms)
    expect("anchorless (%s): context term counts on its own (fail-closed)" % lbl,
           tt is not None and pps.scan_text("kestrel", tt) != [], repr(tt))

# --- (b) URL-encoded views ---------------------------------------------------------------
terms_a = [ALWAYS]
for lbl, text in (("%20", "https://x.example/?q=Quiet%20Marsh%20Park"),
                  ("+", "https://x.example/?q=Quiet+Marsh+Park"),
                  ("lowercase hex", "q=quiet%20marsh%20park"),
                  ("encoded letters", "q=%51uiet%20%4Darsh%20Park"),
                  ("double-encoded %2520", "q=Quiet%2520Marsh%2520Park"),
                  ("triple-encoded %252520", "q=Quiet%252520Marsh%252520Park"),
                  # %2B -> "+" on round 1, "+" -> " " on round 2 of the unquote_plus chain.
                  # Over-decoding can only ADD matches: the fail-closed direction.
                  ("%2B then +", "q=Quiet%2BMarsh+Park")):
    expect("url: %s -> hit" % lbl, pps.scan_text(text, terms_a) != [], text)
expect("url: clean encoded text -> no hit",
       pps.scan_text("q=quarterly%20summary+report", terms_a) == [])
expect("url: encoded context term + plain anchor in the same window -> hit",
       pps.scan_text("ke%73trel in the offering+memo", terms_ctx) != [])
expect("url: +-encoded context term with an anchor that itself contains '+' -> hit "
       "(term and anchor may match in DIFFERENT decoded views of one window; REFUTE E)",
       pps.scan_text("q=kes+trel and s&p+500",
                     [("kes trel", ("s&p+500",))]) != [])
expect("url: decoding is bounded (a constant, not unbounded recursion)",
       isinstance(getattr(pps, "URL_DECODE_MAX_ROUNDS", None), int)
       and 2 <= pps.URL_DECODE_MAX_ROUNDS <= 8)

# --- End-to-end through main(), in-process, on throwaway repos ---------------------------
def _git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)


def _repo_with_commits(commits):
    """Base commit (stands in for the remote tip), then one commit per (files, message).
    Returns (repo, stdin) pushing every new commit as an EXISTING remote ref (delta range)."""
    repo = tempfile.mkdtemp(prefix="pps-ctx-repo-")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "base.txt"), "w", encoding="utf-8") as fh:
        fh.write("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    for files, message in commits:
        for rel, data in files.items():
            full = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", message)
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, "refs/heads/main %s refs/heads/main %s\n" % (tip, base)


def _main_inproc(repo, stdin_text, roster):
    """Run main() against `repo` with `roster` as the terms file."""
    saved = (sys.stdin, sys.stderr, os.getcwd())
    err = io.StringIO()

    def run():
        sys.stdin, sys.stderr = io.StringIO(stdin_text), err
        os.chdir(repo)
        return pps.main()
    try:
        rc = _with_roster(roster, run)
    finally:
        sys.stdin, sys.stderr = saved[0], saved[1]
        os.chdir(saved[2])
    return rc, err.getvalue()


def _no_echo(err):
    return not any(s in err.lower() for s in ALL_SYNTHETIC)


E2E = [
    ("context-only deal: term + anchor in one commit's patch -> BLOCK",
     ctx_only, [({"notes.md": "kestrel numbers per the rent roll\n"}, "notes")], 1),
    ("context-only deal: term without anchor -> allow",
     ctx_only, [({"notes.md": "kestrel sighting at the lake\n"}, "birds")], 0),
    ("context-only deal: anchor in commit 1, term in commit 2 -> allow (window = one commit)",
     ctx_only, [({"a.md": "rent roll attached\n"}, "a"), ({"b.md": "kestrel\n"}, "b")], 0),
    ("context-only deal: term + anchor in the commit MESSAGE -> BLOCK",
     ctx_only, [({"c.md": "clean\n"}, "kestrel per offering memo")], 1),
    # REFUTE 2026-11-23 (A3): a commit's message and its patch are ONE window -- both are
    # published together, so a term in one and its anchor in the other must block.
    ("context-only deal: anchor in message, term in patch -> BLOCK (window = whole commit)",
     ctx_only, [({"d.md": "kestrel\n"}, "update the offering memo")], 1),
    ("context-only deal: term in a FILE NAME, anchor in the message -> BLOCK (A3b)",
     ctx_only, [({"kestrel-notes.md": "clean\n"}, "see the rent roll")], 1),
    # REFUTE 2026-11-23 (B1): the same file gains the term in one commit and the anchor in a
    # later one -- the pushed file holds both, so its full content is a window.
    ("context-only deal: term then anchor added to ONE file in two commits -> BLOCK (B1)",
     ctx_only, [({"deal.md": "kestrel\n" + "filler\n" * 20}, "one"),
                ({"deal.md": "kestrel\n" + "filler\n" * 20 + "rent roll\n"}, "two")], 1),
    ("context-only deal: term and anchor in DIFFERENT files, different commits -> allow",
     ctx_only, [({"x.md": "kestrel\n"}, "x"), ({"y.md": "the rent roll\n"}, "y")], 0),
    ("anchorless context deal: bare term -> BLOCK (fail-closed)",
     _deal(always=[], context=[CTX_TERM]), [({"e.md": "kestrel\n"}, "e")], 1),
    ("always term %20-encoded in a diff -> BLOCK",
     _deal(always=["Quiet Marsh Park"]),
     [({"f.md": "curl 'https://x.example/?q=Quiet%20Marsh%20Park'\n"}, "f")], 1),
    ("always term +-encoded in a diff -> BLOCK",
     _deal(always=["Quiet Marsh Park"]),
     [({"g.py": "requests.get('https://x.example/?q=Quiet+Marsh+Park')\n"}, "g")], 1),
    ("always term double-encoded in a diff -> BLOCK",
     _deal(always=["Quiet Marsh Park"]), [({"h.md": "q=Quiet%2520Marsh%2520Park\n"}, "h")], 1),
    ("clean encoded diff -> allow",
     _deal(always=["Quiet Marsh Park"]), [({"i.md": "q=quarterly%20summary\n"}, "i")], 0),
    ("context term + anchor inside a .gz blob -> BLOCK",
     ctx_only, [({"logs/a.jsonl.gz": gzip.compress(b"kestrel / rent roll\n")}, "gz")], 1),
]
_zbuf = io.BytesIO()
with zipfile.ZipFile(_zbuf, "w", zipfile.ZIP_DEFLATED) as _zf:
    _zf.writestr("a.txt", "see Quiet%20Marsh%20Park")
E2E.append(("URL-encoded always term inside a .zip member -> BLOCK",
            _deal(always=["Quiet Marsh Park"]), [({"out/p.zip": _zbuf.getvalue()}, "zip")], 1))

# REFUTE C7/C2: file CONTENT forging git's own header lines must not split one commit's patch
# into windows that separate a term from its anchor. A spoofed line is "+"-prefixed in the patch;
# this pins the `^` anchoring of the split regexes.
_SPOOF = "kestrel\ncommit %s\ndiff --git a/x b/x\nrent roll\n" % ("a" * 40)
E2E.append(("spoofed `commit <sha>` / `diff --git` lines inside one patch -> BLOCK",
            ctx_only, [({"spoof.md": _SPOOF}, "spoof")], 1))
for lbl, roster, commits, want in E2E:
    repo, stdin = _repo_with_commits(commits)
    rc, err = _main_inproc(repo, stdin, roster)
    expect("e2e: %s" % lbl, rc == want, "rc=%s err=%s" % (rc, err[:300]))
    expect("e2e: %s -> never echoes a term" % lbl, _no_echo(err), err[:300])

# REFUTE F: a pusher's own format.pretty must not change the window split. With %H%n%B the
# message is unindented, so a message line "diff --git ..." would be read as the patch start and
# cut the term (message line 1) from its anchor (message line 3). main() pins --format=medium.
repo, stdin = _repo_with_commits([({"k.md": "clean\n"}, "kestrel\ndiff --git a/q b/q\nrent roll")])
_git(repo, "config", "format.pretty", "%H%n%B")
rc, err = _main_inproc(repo, stdin, ctx_only)
expect("e2e: format.pretty=%H%n%B cannot split a message's term from its anchor -> BLOCK",
       rc == 1, "rc=%s err=%s" % (rc, err[:300]))

# REFUTE C5b: an archive PATH carrying a context term (no anchor in the path) must be withheld
# from the block message -- printing it next to "confidential term(s)" discloses the term.
_zb = io.BytesIO()
with zipfile.ZipFile(_zb, "w", zipfile.ZIP_DEFLATED) as _zf:
    _zf.writestr("a.txt", "kestrel per the rent roll")
repo, stdin = _repo_with_commits([({"kestrel-notes/a.zip": _zb.getvalue()}, "zip")])
rc, err = _main_inproc(repo, stdin, ctx_only)
expect("e2e: archive path containing a context term -> BLOCK with the path withheld",
       rc == 1 and "withheld" in err and "kestrel" not in err.lower(),
       "rc=%s err=%s" % (rc, err[:300]))

# REFUTE 2026-11-23 (B2): the term was pushed earlier (already on the remote, alone it is not a
# hit); a LATER push adds the anchor to the same file. The pushed file now holds both -> BLOCK.
repo, _ = _repo_with_commits([({"deal.md": "kestrel\n" + "filler\n" * 20}, "first push")])
first = _git(repo, "rev-parse", "HEAD").stdout.strip()
with open(os.path.join(repo, "deal.md"), "a", encoding="utf-8") as fh:
    fh.write("rent roll\n")
_git(repo, "commit", "-qam", "second push")
tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
rc, err = _main_inproc(repo, "refs/heads/main %s refs/heads/main %s\n" % (tip, first), ctx_only)
expect("e2e: anchor added in a LATER push to a file already holding the term -> BLOCK (B2)",
       rc == 1 and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))
expect("e2e: B2 block names the file-content scan",
       "file content" in err.lower(), err[:300])

# REFUTE 2026-11-23 (C5): every block message withholds a path that carries a roster term --
# not only the compressed-blob report. Credential (built at runtime so this file never holds a
# key-shaped literal) and exposure-path reports on a term-bearing path.
_fake_key = "AKIA" + "Q7XYZ4LMNOPQRSTU"
for lbl, files in (
        ("credential report", {"quiet marsh park/creds.txt": "aws_key = %s\n" % _fake_key}),
        ("exposure-path report", {"quiet marsh park/deal-stage-snapshot.json": "{}\n"})):
    repo, stdin = _repo_with_commits([(files, "c5")])
    rc, err = _main_inproc(repo, stdin, _deal(always=["Quiet Marsh Park"]))
    expect("e2e: %s on a term-bearing path -> BLOCK with the path withheld" % lbl,
           rc == 1 and "withheld" in err and _no_echo(err), "rc=%s err=%s" % (rc, err[:400]))

# C5, RCT report: a synthetic denylist string (never a real figure) on a term-bearing path.
_rct_dir = tempfile.mkdtemp(prefix="pps-ctx-rct-")
_rct_deny = os.path.join(_rct_dir, "deny.json")
with open(_rct_deny, "w", encoding="utf-8") as fh:
    json.dump({"strings": ["zz-synthetic-rct-needle-42"]}, fh)
_saved_rct = os.environ.get("ORA_RCT_LEAK_DENYLIST")
os.environ["ORA_RCT_LEAK_DENYLIST"] = _rct_deny
try:
    repo, stdin = _repo_with_commits(
        [({"quiet marsh park/costs.md": "zz-synthetic-rct-needle-42\n"}, "rct")])
    rc, err = _main_inproc(repo, stdin, _deal(always=["Quiet Marsh Park"]))
finally:
    if _saved_rct is None:
        os.environ.pop("ORA_RCT_LEAK_DENYLIST", None)
    else:
        os.environ["ORA_RCT_LEAK_DENYLIST"] = _saved_rct
expect("e2e: RCT report on a term-bearing path -> BLOCK with the path withheld",
       rc == 1 and "RCT" in err and "withheld" in err and _no_echo(err),
       "rc=%s err=%s" % (rc, err[:400]))

# --- #497 follow-ups (2026-11-23) ---------------------------------------------------------
ALWAYS_DEAL = _deal(always=["Quiet Marsh Park"])


def _tag_push(message, nested=False):
    """Repo whose origin/main is the base commit, plus an annotated tag (optionally a tag OF a
    tag) carrying `message`. Returns (repo, stdin) pushing the tag as a NEW remote ref."""
    repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "tagged commit")])
    base = _git(repo, "rev-parse", "HEAD~1").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base)
    _git(repo, "tag", "-a", "v1", "-m", message if not nested else "inner clean")
    name = "v1"
    if nested:
        _git(repo, "tag", "-a", "v1-outer", "v1", "-m", message)
        name = "v1-outer"
    sha = _git(repo, "rev-parse", "refs/tags/%s" % name).stdout.strip()
    return repo, "refs/tags/%s %s refs/tags/%s %s\n" % (name, sha, name, "0" * 40)


# F1: annotated-tag messages are published with the tag but `git log` never shows them.
for lbl, msg, nested, want in (("annotated tag message carries the term", "release for Quiet Marsh Park", False, 1),
                               ("tag OF a tag: outer message carries the term", "Quiet+Marsh+Park notes", True, 1),
                               ("clean annotated tag message", "release 1.0", False, 0)):
    repo, stdin = _tag_push(msg, nested)
    rc, err = _main_inproc(repo, stdin, ALWAYS_DEAL)
    expect("e2e F1: %s -> %s" % (lbl, "BLOCK" if want else "allow"),
           rc == want and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

# F1: the pushed REF NAME is published too; ref names join words with - _ . /
for lbl, ref, want in (("branch named after the deal (hyphens)", "refs/heads/quiet-marsh-park", 1),
                       ("branch named with underscores / dots", "refs/heads/wip/quiet_marsh.park", 1),
                       ("ordinary branch name", "refs/heads/feature/rent-escalator", 0)):
    repo, stdin = _repo_with_commits([({"r.md": "clean\n"}, "r")])
    tip, base = stdin.split()[1], stdin.split()[3]
    rc, err = _main_inproc(repo, "%s %s %s %s\n" % (ref, tip, ref, base), ALWAYS_DEAL)
    expect("e2e F1: ref name: %s -> %s" % (lbl, "BLOCK" if want else "allow"),
           rc == want and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

# F1 round 2 (REFUTE 2026-11-23): tags that peel to a BLOB or TREE, UTF-16 tag messages, the
# tag NAME inside the tag object, more ref-name separators, run-together names.
def _blob_tag_push(annotated, tree):
    repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "c")])
    base = _git(repo, "rev-parse", "HEAD~1").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base)
    blob = subprocess.run(["git", "-C", repo, "hash-object", "-w", "--stdin"],
                          input=b"notes on Quiet Marsh Park\n", capture_output=True
                          ).stdout.decode().strip()
    obj = blob
    if tree:
        obj = subprocess.run(["git", "-C", repo, "mktree"],
                             input=("100644 blob %s\tn.txt\n" % blob).encode(),
                             capture_output=True).stdout.decode().strip()
    if annotated:
        _git(repo, "tag", "-a", "t1", obj, "-m", "clean message")
    else:
        _git(repo, "tag", "t1", obj)
    sha = _git(repo, "rev-parse", "refs/tags/t1").stdout.strip()
    return repo, "refs/tags/t1 %s refs/tags/t1 %s\n" % (sha, "0" * 40)


for lbl, annotated, tree in (("annotated tag on a BLOB holding the term", True, False),
                             ("lightweight tag on a BLOB holding the term", False, False),
                             ("annotated tag on a TREE holding the term", True, True)):
    repo, stdin = _blob_tag_push(annotated, tree)
    rc, err = _main_inproc(repo, stdin, ALWAYS_DEAL)
    expect("e2e F1b: %s -> BLOCK" % lbl, rc == 1 and _no_echo(err),
           "rc=%s err=%s" % (rc, err[:300]))

repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "c")])
_git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD~1").stdout.strip())
_u16 = os.path.join(repo, "..", "msg16-%s.txt" % os.path.basename(repo))
with open(_u16, "wb") as fh:
    fh.write("release notes: Quiet Marsh Park\n".encode("utf-16"))
_git(repo, "tag", "-a", "u16", "-F", _u16)
_sha = _git(repo, "rev-parse", "refs/tags/u16").stdout.strip()
rc, err = _main_inproc(repo, "refs/tags/u16 %s refs/tags/u16 %s\n" % (_sha, "0" * 40), ALWAYS_DEAL)
expect("e2e F1b: UTF-16 annotated tag message -> BLOCK", rc == 1 and _no_echo(err),
       "rc=%s err=%s" % (rc, err[:300]))

repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "c")])
_git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD~1").stdout.strip())
_git(repo, "tag", "-a", "quiet-marsh-park", "-m", "clean")
_obj = _git(repo, "rev-parse", "refs/tags/quiet-marsh-park").stdout.strip()
_git(repo, "update-ref", "refs/tags/v2", _obj)
_git(repo, "tag", "-d", "quiet-marsh-park")
rc, err = _main_inproc(repo, "refs/tags/v2 %s refs/tags/v2 %s\n" % (_obj, "0" * 40), ALWAYS_DEAL)
expect("e2e F1b: tag NAME inside the tag object carries the term (pushed as v2) -> BLOCK",
       rc == 1 and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

# Round 3: a hyphenated PATH inside a tagged tree; a BOM-less UTF-16 tag message followed by a
# signature-shaped block (git stores the tag message verbatim).
repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "c")])
_git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD~1").stdout.strip())
_bl = subprocess.run(["git", "-C", repo, "hash-object", "-w", "--stdin"], input=b"clean\n",
                     capture_output=True).stdout.decode().strip()
_tr = subprocess.run(["git", "-C", repo, "mktree"],
                     input=("100644 blob %s\tquiet-marsh-park.txt\n" % _bl).encode(),
                     capture_output=True).stdout.decode().strip()
_git(repo, "tag", "-a", "tp", _tr, "-m", "clean")
_sha = _git(repo, "rev-parse", "refs/tags/tp").stdout.strip()
rc, err = _main_inproc(repo, "refs/tags/tp %s refs/tags/tp %s\n" % (_sha, "0" * 40), ALWAYS_DEAL)
expect("e2e F1c: hyphenated term in a PATH inside a tagged tree -> BLOCK",
       rc == 1 and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

repo, _ = _repo_with_commits([({"t.md": "clean\n"}, "c")])
_git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD~1").stdout.strip())
_msgf = os.path.join(repo, "..", "msg16s-%s.txt" % os.path.basename(repo))
with open(_msgf, "wb") as fh:
    fh.write("notes: Quiet Marsh Park\n".encode("utf-16-le")
             + b"-----BEGIN PGP SIGNATURE-----\n" + b"A" * 800 + b"\n-----END PGP SIGNATURE-----\n")
_git(repo, "tag", "-a", "u16s", "-F", _msgf)
_sha = _git(repo, "rev-parse", "refs/tags/u16s").stdout.strip()
rc, err = _main_inproc(repo, "refs/tags/u16s %s refs/tags/u16s %s\n" % (_sha, "0" * 40),
                       ALWAYS_DEAL)
expect("e2e F1c: BOM-less UTF-16 tag message followed by a signature block -> BLOCK",
       rc == 1 and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

for lbl, ref, want in (("commas", "refs/heads/quiet,marsh,park", 1),
                       ("= and !", "refs/heads/quiet=marsh!park", 1),
                       ("run together, CamelCase", "refs/heads/QuietMarshPark", 1),
                       ("ordinary name with commas", "refs/heads/fix,lint,docs", 0)):
    repo, stdin = _repo_with_commits([({"r.md": "clean\n"}, "r")])
    tip, base = stdin.split()[1], stdin.split()[3]
    rc, err = _main_inproc(repo, "%s %s %s %s\n" % (ref, tip, ref, base), ALWAYS_DEAL)
    expect("e2e F1b: ref name with %s -> %s" % (lbl, "BLOCK" if want else "allow"),
           rc == want and _no_echo(err), "rc=%s err=%s" % (rc, err[:300]))

# Non-ASCII ref names: git writes the ref lines as UTF-8, whatever the console code page.
_line = ("refs/heads/café-row %s refs/heads/café-row %s\n" % ("a" * 40, "b" * 40))
_stream = io.TextIOWrapper(io.BytesIO(_line.encode("utf-8")), encoding="cp1252")
expect("stdin F1b: ref lines are decoded as UTF-8 even under a cp1252 console",
       "café-row" in pps._read_stdin(_stream) if hasattr(pps, "_read_stdin") else False)

# F2: a deal entry that is not a dict cannot be read -> roster malformed -> fail closed.
for lbl, bad in (("a list", ["Quiet Marsh Park"]), ("a string", "Quiet Marsh Park"),
                 ("null", None)):
    expect("load F2: non-dict deal entry (%s) -> None (fail-closed)" % lbl,
           _with_roster({"_meta": {}, "deal": bad}, pps.load_terms) is None)
expect("load F2: `_`-prefixed non-dict keys stay ignored",
       _with_roster({"_meta": "notes", "_v": 2, "d": {"active": True, "always": ["x y z"]}},
                    pps.load_terms) == ["x y z"])

# F3: surrounding whitespace in a roster string must not narrow matching.
padded = _deal(always=["  Quiet Marsh Park "], context=[" kestrel"],
               context_requires_any=[" rent roll  "])
tp = _with_roster(padded, pps.load_terms) or []
expect("load F3: terms and anchors are stripped",
       ALWAYS in tp and ("kestrel", ("rent roll",)) in tp, repr(tp)[:0])
expect("scan F3: padded anchor still gates its term ('kestrel ... rent roll,')",
       pps.scan_text("kestrel notes, see rent roll, attached", tp) != [])

# F4: decoded views are bounded in MEMORY, not just rounds -- views are produced one at a time.
import tracemalloc
_big = ("kestrel%20x+y " * 400000)  # ~5.6 MB, decodes on every round of both chains
tracemalloc.start()
pps.scan_text(_big, terms_ctx)
_peak = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
expect("scan F4: peak memory of one decoded scan < 5x the window (was ~9 copies): %.1fx"
       % (_peak / float(len(_big))), _peak < 5 * len(_big))
expect("scan F4: streaming still finds a term only present in a later decoded view",
       pps.scan_text("q=Quiet%252520Marsh%252520Park", [ALWAYS]) == [0])
# Chunked decoding: a (double-)encoded term STRADDLING every chunk boundary is still found, and so
# is a context term whose anchor sits in a far-away chunk of the same window.
_C = getattr(pps, "DECODE_CHUNK", 1 << 20)
_enc = "Quiet%2520Marsh%2520Park"
for _off in range(1, len(_enc)):
    _s = "x" * (_C - _off) + _enc + "y" * 64
    if pps.scan_text(_s, [ALWAYS]) != [0]:
        expect("scan F4: encoded term straddling the chunk boundary (offset %d) found" % _off,
               False)
        break
else:
    expect("scan F4: encoded term straddling the chunk boundary found at every offset", True)
# REFUTE round 2: the overlap must cover NON-ASCII preimages -- a 4-byte UTF-8 char is 12 chars
# per round, and the Kelvin sign (U+212A, `%E2%84%AA`) lowercases to ASCII 'k'. The window must be
# LONGER than one chunk plus overlap, or a too-small overlap is never exercised.
def _enc4(s):
    """Worst-case preimage: EVERY byte percent-encoded, four rounds deep (quote() would leave
    ASCII letters alone and never reach the bound)."""
    for _ in range(4):
        s = "".join("%%%02X" % b for b in s.encode("utf-8"))
    return s


for _lbl, _plain, _roster in (("Kelvin-sign 'k' in an ASCII term", "Kestrel", ["kestrel"]),
                              ("accented term", "café row", ["café row"]),
                              ("4-byte UTF-8 term", "\U0001F3E0 lot", ["\U0001F3E0 lot"])):
    _e = _enc4(_plain)
    _miss = None
    for _off in range(1, len(_e)):  # every offset: a too-small overlap misses only a few
        _s = "x" * (_C - _off) + _e + "y" * (2 * _C)
        if pps.scan_text(_s, _roster) != [0]:
            _miss = _off
            break
    expect("scan F4b: 4-round-encoded %s straddling a chunk boundary of a multi-chunk window "
           "is found (first miss at offset %s)" % (_lbl, _miss), _miss is None)
expect("scan F4: context term and its anchor in different chunks of one window -> hit",
       pps.scan_text("kestrel " + "z" * (3 * _C) + " rent%20roll", terms_ctx) != [])

# A malformed roster blocks the push outright, with the fail-closed message.
repo, stdin = _repo_with_commits([({"j.md": "nothing\n"}, "j")])
rc, err = _main_inproc(repo, stdin, _deal(always=[], context="kestrel"))
expect("e2e: malformed `context` field -> BLOCK (fail-closed) with a clear message",
       rc == 1 and "fail-closed" in err, "rc=%s err=%s" % (rc, err[:300]))

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-context-urlencode tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
