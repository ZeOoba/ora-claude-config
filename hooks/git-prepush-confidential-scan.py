#!/usr/bin/env python3
"""Native git pre-push gate for ~/.claude — scans every commit genuinely NEW to the
remote, across the full diff of each (not just the tree at HEAD).

Lesson 2026-06-11 (incident, same-day remediation): the first push of this repo
carried pre-scrub commits with confidential deal terms in their diffs. A clean HEAD
does not mean a clean push. This hook runs `git log -p` over every ref range being
pushed and BLOCKS if any active always-term from hooks/confidential-terms.json
appears anywhere in that range. Terms are never echoed — only deal-relative
indices are reported. Compressed blobs (.gz / .tgz / .zip, detected by magic bytes),
which `git log -p` shows only as "Binary files differ", are decompressed in memory and
scanned too -- see scan_compressed() (audit finding 2026-11-08).

Range computation (fixed 2026-07-25 — see rev_range()/_resolve_default_baseline()):
an EXISTING remote ref scans remote_sha..local_sha (the delta), same as always. A
BRAND-NEW remote ref (the normal case for a new branch's first push) scans
origin/<default-branch>..local_sha — commits not yet reachable from the repo's
default/trunk branch — NOT the unbounded `git log -p local_sha` this gate used
before that date, which dumped the ENTIRE history reachable from local_sha and
re-flagged commits already public on origin/main on every single first push of any
new branch (confirmed repro: a6f0689, an origin/main ancestor, re-flagged forever on
a documented placeholder API-key value in server/secrets.env.example -- not spelled
out here verbatim, since this gate scans its own source too). An
orphan branch (no merge-base with the default branch) is scanned in FULL by this same
range, because none of its history is reachable from a baseline it shares no ancestry
with — intentional, not a gap, since none of that history was ever public.

FAIL-CLOSED: terms file unreadable -> block; git log fails (e.g. unknown remote
sha — run `git fetch` first) -> block; a brand-new ref whose default-branch baseline
can't be resolved (no origin remote, nothing fetched) -> block, not a silent
full-history rescan and not a silent skip. No active terms (all deals closed) plus
no credential hits -> allow.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree
add` never checks it out into a fresh linked worktree. load_terms() falls back to
the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, shared by
every worktree of the same repo) when this checkout's own copy is missing or
unreadable. Still fail-closed if the file is unreadable in BOTH places (2026-07-12).

Install (done 2026-06-11, extended 2026-07-24; re-do after any fresh clone — see
docs/MIGRATION_RUNBOOK.md). The .git/hooks/pre-push shim is NOT version-controlled, so
it must be recreated on every fresh clone. It runs THREE tracked checks in order — the
doctrine-drift gate, then the hook-test-suite gate, then this fail-closed
confidentiality scan LAST (the first two take </dev/null so neither consumes git's ref
stdin; the final exec hands that stdin to this scan unchanged):
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (The doctrine-drift check lives in hooks/git-prepush-doctrine-gate.py, the hook-test
   check in hooks/git-prepush-hook-tests-gate.py; THIS scan's own logic is unchanged —
   the other two gates were added ahead of it, not merged into it.)

Exit 0 = allow push. Exit 1 = block (git pre-push convention).
"""
import json
import os
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")
ZERO_RE = "0"

# CREDENTIAL SCAN (Gabriel ruling, 2026-07-24). Until now this gate blocked confidential
# DEAL TERMS only -- it carried zero credential patterns, so nothing stopped an API key
# reaching ZeOoba/ora-claude-config. The detection logic existed in
# maintenance/scrub-before-optin.py but only ran when a human remembered to invoke it; its
# own docstring records that the FRED key hardcoded in a retired SKILL.md was caught "only
# because that grep happened to be written that day".
#
# FAIL-CLOSED like the terms check: if the pattern module cannot be imported we block,
# because we cannot prove the push is clean. (The terms scan already fails closed on an
# unreadable terms file -- same principle, same reason.)
sys.path.insert(0, os.path.join(HOOK_DIR, "lib"))
try:
    import secret_patterns as _sp
except Exception as _e:  # pragma: no cover - exercised via the import-failure test
    _sp = None
    _SP_ERR = str(_e)


def _read_json(path):
    """Parsed JSON from path, or None on any read/parse error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (same for every worktree of
    the same repo), or None on any failure -- not a git repo, git missing, etc."""
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if it can't be
    resolved or doesn't exist there. hooks/confidential-terms.json is gitignored
    (see .gitignore), so `git worktree add` never checks it out into a linked
    worktree -- this lets a linked worktree fall back to the main checkout's
    copy instead of failing closed on every push from a fresh worktree."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    # Assumes the terms file lives at <repo-root>/hooks/confidential-terms.json --
    # same layout TERMS_FILE itself relies on (HOOK_DIR is this script's own dir).
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


def load_terms():
    """Lowercased active always-terms, or None if unreadable both in this
    checkout and (falling back) in the main worktree's copy (fail-closed)."""
    d = _read_json(TERMS_FILE)
    if d is None:
        fallback = _main_worktree_terms_file()
        if fallback is not None:
            d = _read_json(fallback)
    if d is None:
        return None
    out = []
    for key, deal in d.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        out.extend(t.lower() for t in deal.get("always", [])
                   if isinstance(t, str) and t.strip())
    return out


def _is_sha(s):
    return len(s) == 40 and all(c in "0123456789abcdef" for c in s.lower())


def parse_pushrefs(text):
    """Pre-push stdin lines: '<local_ref> <local_sha> <remote_ref> <remote_sha>'.
    Both sha fields must be 40-hex — anything else is noise, not a ref line."""
    refs = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and _is_sha(parts[1]) and _is_sha(parts[3]):
            refs.append(tuple(parts))
    return refs


_DEFAULT_BRANCH_CANDIDATES = ("refs/remotes/origin/main", "refs/remotes/origin/master")


def _resolve_default_baseline(start_dir="."):
    """Best-effort commit-ish for the remote's default/trunk branch (e.g.
    'refs/remotes/origin/main'), used to bound the history scan on a brand-new remote
    ref. Prefers the tracked refs/remotes/origin/HEAD symref (set by a real `git
    clone` or `git remote set-head`); falls back to the common trunk names since a
    plain `git fetch` alone does not set that symref. Returns None if nothing
    resolves -- no `origin` remote, nothing fetched yet, or not a git repo at all --
    so the caller can fail closed instead of silently rescanning full history or
    silently skipping the scan.

    start_dir defaults to "." (the process's own cwd) DELIBERATELY, not HOOK_DIR --
    it must resolve against the SAME repo the `git log -p` scan itself operates on
    (which also relies on inherited cwd, not `-C`). git invokes pre-push hooks with
    cwd already at the top of the repo being pushed, so in real installs this and
    HOOK_DIR's parent are the same directory anyway -- but conflating the two is a
    live bug the moment they diverge (caught in review: it silently baselined
    against the wrong repo and produced a tautologically-passing test).

    ALWAYS fully-qualified (refs/remotes/origin/... , never the short 'origin/main').
    A short name is subject to git's ref-disambiguation order, which checks
    refs/heads/ before refs/remotes/ -- a LOCAL branch literally named 'origin/main'
    would silently shadow the real remote-tracking ref and could exclude genuinely
    new, unpushed commits from the scan (a demonstrated false negative caught in
    review). Fully-qualified refs cannot be shadowed."""
    candidates = []
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        p = None
    if p is not None and p.returncode == 0 and p.stdout.strip():
        symref_target = p.stdout.strip()
        # `git remote set-head` always yields a refs/remotes/... target, but the
        # lower-level `git symbolic-ref refs/remotes/origin/HEAD <anything>` doesn't
        # enforce that -- it would happily point this at a refs/heads/... branch,
        # which reopens exactly the shadowing class the fully-qualified-refs fix
        # above closes (caught in review). Only trust it if it's actually still
        # under refs/remotes/; otherwise fall through to the default candidates.
        if symref_target.startswith("refs/remotes/"):
            candidates.append(symref_target)
    for c in _DEFAULT_BRANCH_CANDIDATES:
        if c not in candidates:
            candidates.append(c)
    for ref in candidates:
        try:
            v = subprocess.run(
                ["git", "-C", start_dir, "rev-parse", "-q", "--verify", ref + "^{commit}"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            continue
        if v.returncode == 0 and v.stdout.strip():
            return ref
    return None


def rev_range(local_sha, remote_sha, baseline):
    """Range of commits to scan for one pushed ref.

    - Existing remote ref (remote_sha not all-zero): unchanged -- the delta,
      remote_sha..local_sha.
    - Brand-new remote ref (remote_sha all-zero, the normal case for a new branch's
      first push): bounded to baseline..local_sha, i.e. only commits NOT already
      reachable from the repo's default/trunk branch (baseline, e.g. origin/main).
      This is the 2026-07-25 fix: the old behavior returned local_sha alone (no range
      at all), which makes `git log -p` dump the ENTIRE history reachable from
      local_sha -- re-scanning commits already public on origin/main on every first
      push of any new branch.
    - Orphan branch (no merge-base with baseline at all): baseline..local_sha then
      naturally covers the branch's FULL history, because none of it is excluded by
      a baseline it shares no ancestry with. This is intentional, not a gap: an
      orphan branch's history was never reachable from the trunk, so none of it is
      "already public" and all of it must be scanned.
    - baseline is None (can't resolve the repo's default branch -- no origin remote,
      nothing fetched, not a repo): returns None to signal the caller must fail
      closed rather than silently falling back to a full-history rescan or silently
      skipping the scan.
    """
    if set(remote_sha) != {ZERO_RE}:
        return "%s..%s" % (remote_sha, local_sha)
    if baseline is None:
        return None
    return "%s..%s" % (baseline, local_sha)


def scan_text(text, terms):
    """Sorted indices of terms present in text (never the terms themselves)."""
    low = text.lower()
    return sorted(i for i, t in enumerate(terms) if t in low)


# --- Compressed blobs (audit finding prepush-scan-blind-to-compressed-transcripts, 2026-11-08) ---
# `git log -p` renders a .gz / .tgz / .zip as "Binary files ... differ", so a roster term or a
# credential inside a compressed session transcript or memory snapshot reached the remote with no
# scan at all. Every blob the pushed range adds or modifies is streamed ONE AT A TIME through
# `git cat-file --batch` (memory = the largest single blob) and classified BY CONTENT -- never by
# extension and never by git's binary/text flag, which a `.gitattributes` or uncommitted
# `.git/info/attributes` `diff` line can flip -- and, when it is gzip (magic bytes) or zip (magic
# bytes or zipfile.is_zipfile, which also finds a prefixed/self-extracting archive), decompressed
# in memory -- tar members inside a gzip included, nested archives to a small
# depth. Scanned for roster terms and credentials: every member's content, the raw blob as text
# (zip member names, the gzip FNAME header, a prefix or trailer around the archive), and the whole
# decompressed tar stream as text (tar member names, PAX headers, bytes after end-of-archive).
# Reports name the archive path only -- never a member name -- and withhold even the path when
# the path itself carries a term.
# FAIL-CLOSED: a compressed blob that cannot be fully read (corrupt, encrypted, past the per-blob
# size cap or member cap, nested too deep) BLOCKS, roster or not: like an unimportable pattern
# module, an unproven credential scan is a blocked push. The size cap is PER BLOB, so one large
# archive cannot switch off the scan of the others. Cost of that choice, accepted deliberately: a
# push adding an encrypted zip or a zip with an unsupported method (e.g. Deflate64) always blocks;
# the only way past is a human's `--no-verify`. Do not downgrade this to a warning.
# UTF-16 (audit E6, 2026-11-08): every decompressed member / stream is ALSO decoded as UTF-16
# when it carries a BOM or is >30% NUL bytes (see _text_views) -- utf-8-with-ignore keeps only the
# ASCII half of each UTF-16 code unit, interleaved with NULs, so a term never matched.
# MERGES (audit prepush-scan-skips-merge-commit-diffs + E6, 2026-11-08): both this blob walk and
# main()'s `git log -p` run with `--cc`, so a merge commit contributes its dense combined diff --
# the paths/hunks whose result differs from EVERY parent, i.e. exactly the content a conflict
# resolution ("evil merge") introduced. Hunks a merge takes verbatim from one parent are omitted by
# --cc on purpose: that content lives in the parent's own commit, which is either inside the pushed
# range (scanned there) or already on the remote.
# A bare (non-archived) UTF-16 file is "Binary files differ" to `git log -p` too, so the same
# blob walk scans its UTF-16 views (REFUTE 2026-11-08).
# RESIDUAL: other binary formats (PDF streams, images, xz/bz2/7z) and BOM-less UTF-16 under 30%
# NUL bytes (CJK-heavy text) or UTF-32 are not decoded; history already on the remote is not
# rescanned; zip entries absent from the central directory are not read.
GZIP_MAGIC = b"\x1f\x8b"
ZIP_MAGIC = b"PK\x03\x04"
COMPRESSED_MAX_BYTES = 256 * 1024 * 1024  # decompressed bytes per compressed blob
COMPRESSED_MAX_MEMBERS = 20000
COMPRESSED_MAX_DEPTH = 3


class UnscannableBlob(Exception):
    pass


def _range_blobs(rng, cwd=None):
    """[(path, blob_sha)] for every blob added or modified anywhere in `rng` (every commit, not
    just the tip). RAISES UnscannableBlob on a git failure (the caller blocks)."""
    # --cc: a merge commit lists the paths its resolution changed relative to EVERY parent, in
    # combined raw form (one leading ':' per parent: N+1 modes, N+1 shas, status). Without it a
    # blob introduced only by a merge resolution was never enumerated (audit E6).
    p = subprocess.run(["git", "log", "--raw", "--cc", "-z", "--no-abbrev", "--no-renames",
                        "--format=", rng], capture_output=True, cwd=cwd)
    if p.returncode != 0:
        raise UnscannableBlob("`git log --raw %s` failed" % rng)
    fields = p.stdout.decode("utf-8", "surrogateescape").split("\0")
    out, seen = [], set()
    i = 0
    while i < len(fields):
        meta = fields[i].lstrip("\n")
        if not meta.startswith(":"):
            i += 1
            continue
        path = fields[i + 1] if i + 1 < len(fields) else ""
        i += 2
        nparents = len(meta) - len(meta.lstrip(":"))
        parts = meta.lstrip(":").split()
        if len(parts) < 2 * nparents + 3:
            raise UnscannableBlob("unparseable `git log --raw` record")
        # result mode/sha are the LAST of the N+1 modes and of the N+1 shas
        new_mode, new_sha = parts[nparents], parts[2 * nparents + 1]
        if set(new_sha) == {ZERO_RE} or new_mode in ("160000", "120000"):
            continue  # deletion, submodule, symlink
        if (path, new_sha) not in seen:
            seen.add((path, new_sha))
            out.append((path, new_sha))
    return out


def _iter_blobs(shas, cwd=None):
    """Yield (sha, bytes) one blob at a time from a single `git cat-file --batch` process, so
    memory is bounded by the largest blob, not the push. RAISES UnscannableBlob on a git failure
    or a missing object."""
    if not shas:
        return
    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd)
    try:
        for sha in shas:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode("ascii", "replace").split()
            if len(header) < 3 or header[1] != "blob":
                raise UnscannableBlob("unexpected cat-file output for object %s" % sha[:12])
            size = int(header[2])
            data = proc.stdout.read(size)
            proc.stdout.read(1)  # trailing newline
            if len(data) != size:
                raise UnscannableBlob("short read for object %s" % sha[:12])
            yield sha, data
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.kill()
        proc.wait()


def _is_zip(blob):
    import io
    import zipfile
    if blob[:4] == ZIP_MAGIC:
        return True
    try:
        return zipfile.is_zipfile(io.BytesIO(blob))
    except Exception:
        return False


def _is_compressed(blob):
    return blob[:2] == GZIP_MAGIC or _is_zip(blob)


UTF16_NUL_RATIO = 0.30


def _text_views(data):
    """Text views of one decompressed buffer: utf-8 (errors ignored) always, plus UTF-16 LE and
    BE when the buffer carries a UTF-16 BOM or is more than 30% NUL bytes. Decoding both byte
    orders (rather than guessing one) costs one extra pass and cannot pick the wrong order."""
    views = [data.decode("utf-8", "ignore")]
    if not data:
        return views
    bom = data[:2] in (b"\xff\xfe", b"\xfe\xff")
    if bom or data.count(b"\x00") > UTF16_NUL_RATIO * len(data):
        body = data[2:] if bom else data
        for enc in ("utf-16-le", "utf-16-be"):
            # U+0000 -> '"' (REFUTE round 2): a NUL code unit is not whitespace, so the
            # `password assignment` value class [^\s"']{6,} ran straight through NUL padding
            # -- sc.exe-shaped `password=` + NULs + `DisplayName=` read as a 6+ char password.
            # A quote ends a value the way the NUL ends the C string; a real value stays whole.
            views.append(body.decode(enc, "ignore").replace("\x00", '"'))
    return views


def _decompress_texts(blob, budget, depth=0):
    """Every text view of a gzip / zip blob: the raw blob, each member, and a decompressed tar
    stream as a whole. `budget` is a one-item list of decompressed bytes still allowed for THIS
    blob. RAISES UnscannableBlob on anything that cannot be fully read."""
    import gzip
    import io
    import tarfile
    import zipfile
    if depth > COMPRESSED_MAX_DEPTH:
        raise UnscannableBlob("archives nested deeper than %d" % COMPRESSED_MAX_DEPTH)

    def _take(n):
        budget[0] -= n
        if budget[0] < 0:
            raise UnscannableBlob("decompressed size over the %d MB per-file scan cap"
                                  % (COMPRESSED_MAX_BYTES // (1024 * 1024)))

    def _expand(data):
        if _is_compressed(data):
            return _decompress_texts(data, budget, depth + 1)
        return _text_views(data)

    out = [blob.decode("utf-8", "ignore")]  # names, gzip FNAME, prefix / trailer bytes
    try:
        if blob[:2] == GZIP_MAGIC:
            with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
                data = gz.read(budget[0] + 1)  # bounded: a header's size can lie, the stream cannot
            _take(len(data))
            out.extend(_text_views(data))  # whole stream: tar names, PAX, trailer, UTF-16 text
            buf = io.BytesIO(data)
            if data[257:262] == b"ustar" or (len(data) >= 512 and tarfile.is_tarfile(buf)):
                buf.seek(0)
                with tarfile.open(fileobj=buf, mode="r:") as tf:
                    members = tf.getmembers()
                    if len(members) > COMPRESSED_MAX_MEMBERS:
                        raise UnscannableBlob("too many tar members")
                    for m in members:
                        if not m.isfile():
                            continue
                        fh = tf.extractfile(m)
                        if fh is None:
                            raise UnscannableBlob("unreadable tar member")
                        out.extend(_expand(fh.read()))
            elif _is_compressed(data):
                out.extend(_decompress_texts(data, budget, depth + 1))
        else:
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                infos = zf.infolist()
                if len(infos) > COMPRESSED_MAX_MEMBERS:
                    raise UnscannableBlob("too many zip members")
                for info in infos:
                    out.append(info.filename)
                    if info.is_dir():
                        continue
                    with zf.open(info) as fh:
                        mdata = fh.read(budget[0] + 1)
                    _take(len(mdata))
                    out.extend(_expand(mdata))
    except UnscannableBlob:
        raise
    except Exception as e:  # corrupt stream, encrypted zip member, truncated tar, ...
        raise UnscannableBlob(type(e).__name__)
    return out


def scan_compressed(rng, terms, cwd=None):
    """(term_hits, cred_leaks, unscannable) for every compressed blob added or modified in
    `rng`. term_hits: [(path, indices)]; cred_leaks: [(path, labels)]; unscannable:
    [reason]. Reports carry the ARCHIVE path only -- never a member name, a term, or a value --
    and a path that itself contains a term is withheld."""
    term_hits, cred_leaks, unscannable = [], [], []

    def _shown(path):
        return "<path withheld: contains a confidential term>" if terms and scan_text(path, terms) \
            else path

    try:
        blobs = _range_blobs(rng, cwd)
        paths_by_sha = {}
        for path, sha in blobs:
            paths_by_sha.setdefault(sha, []).append(path)
        for sha, blob in _iter_blobs(sorted(paths_by_sha), cwd):
            path = paths_by_sha[sha][0]
            if not _is_compressed(blob):
                # A bare UTF-16 file (BOM or NUL-heavy; Windows PowerShell 5.1's `>` and
                # Out-File write UTF-16LE by default) is "Binary files differ" to `git log -p`,
                # so only its UTF-16 views are scanned here -- the utf-8 view is the diff scan's
                # (REFUTE 2026-11-08, E6 residual).
                texts = _text_views(blob)[1:]
                if not texts:
                    continue
            else:
                try:
                    texts = _decompress_texts(blob, [COMPRESSED_MAX_BYTES])
                except UnscannableBlob as e:
                    unscannable.append("%s: %s" % (_shown(path), e))
                    continue
            hits, labels = set(), set()
            for text in texts:
                if terms:
                    hits.update(scan_text(text, terms))
                if not all(_sp.is_exempt_path(p) for p in paths_by_sha[sha]):
                    labels.update(_sp.scan_text(text))
            if hits:
                term_hits.append((_shown(path), sorted(hits)))
            if labels:
                cred_leaks.append((_shown(path), sorted(labels)))
    except (UnscannableBlob, ValueError, OSError) as e:
        unscannable.append("compressed-blob enumeration failed (%s)" % e)
    return term_hits, cred_leaks, unscannable


def main():
    # Fail closed on a broken pattern module, exactly as for an unreadable terms file:
    # an unprovable push is a blocked push.
    if _sp is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): hooks/lib/secret_patterns.py "
                         "could not be imported (%s) -- cannot scan for credentials.\n"
                         % _SP_ERR)
        return 1
    terms = load_terms()
    if terms is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): confidential-terms.json "
                         "unreadable — cannot prove the push is clean.\n")
        return 1
    # NOTE: there is deliberately NO `if not terms: return 0` early exit any more. It used
    # to short-circuit the whole hook whenever no deal was active -- which is the state
    # TODAY -- so a credential scan placed after it would have been dead on arrival. The
    # two scans are independent: an empty terms list disables the TERMS check only.
    # No start_dir arg -- resolves against THIS PROCESS's cwd, same as the `git log -p`
    # scan below (which also has no explicit -C/cwd). git invokes pre-push hooks with
    # cwd at the top of the repo being pushed, so this is the repo actually being
    # scanned -- deliberately NOT HOOK_DIR, which is fixed to wherever this script
    # file happens to live and would silently diverge from the repo being pushed.
    # Always resolved against the "origin" remote -- matches every other assumption
    # in this file (confidential-terms.json fallback, install docs) that ~/.claude
    # has exactly one remote; a push to a second remote would still be scanned, just
    # bounded against origin/main rather than that remote's own trunk.
    baseline = _resolve_default_baseline()
    bad = False
    for local_ref, local_sha, remote_ref, remote_sha in parse_pushrefs(sys.stdin.read()):
        if set(local_sha) == {ZERO_RE}:
            continue  # ref deletion — nothing new is pushed
        rng = rev_range(local_sha, remote_sha, baseline)
        if rng is None:
            sys.stderr.write("pre-push BLOCKED (fail-closed): %s is a brand-new remote "
                             "ref and the repo's default branch (origin/main) could not "
                             "be resolved to bound the history scan -- run `git fetch` "
                             "first.\n" % local_ref)
            bad = True
            continue
        # --cc: a merge commit also shows its dense combined diff, so content introduced only
        # by a conflict resolution is scanned (audit prepush-scan-skips-merge-commit-diffs).
        p = subprocess.run(["git", "log", "-p", "--cc", "--no-color", rng],
                           capture_output=True)
        if p.returncode != 0:
            sys.stderr.write("pre-push BLOCKED (fail-closed): `git log -p %s` failed "
                             "for %s (unknown remote sha? run `git fetch` first).\n"
                             % (rng, local_ref))
            bad = True
            continue
        body = p.stdout.decode("utf-8", "ignore")
        if terms:
            hits = scan_text(body, terms)
            if hits:
                sys.stderr.write("pre-push BLOCKED: %d confidential term(s) (indices %s) "
                                 "found in the HISTORY being pushed on %s (range %s). A "
                                 "clean HEAD does not mean a clean push — purge or rebase "
                                 "the history first (see docs/MIGRATION_RUNBOOK.md).\n"
                                 % (len(hits), hits, local_ref, rng))
                bad = True
        # Credential scan over the SAME body -- per file, so a test fixture in the history
        # cannot block every push (see secret_patterns.scan_diff). Reports path + label
        # only; the matched value is never echoed into the terminal or a CI log.
        leaks = _sp.scan_diff(body)
        if leaks:
            detail = "; ".join("%s -> %s" % (path, ", ".join(labels))
                               for path, labels in leaks)
            sys.stderr.write("pre-push BLOCKED: credential-shaped string(s) in the HISTORY "
                             "being pushed on %s (range %s): %s. Values are not echoed. "
                             "Rotate the credential FIRST, then purge or rebase the "
                             "history -- a force-push alone does not un-leak it.\n"
                             % (local_ref, rng, detail))
            bad = True
        # Compressed and UTF-16 blobs: invisible to `git log -p` (see scan_compressed).
        c_hits, c_leaks, c_bad = scan_compressed(rng, terms)
        if c_hits:
            sys.stderr.write("pre-push BLOCKED: confidential term(s) inside COMPRESSED / UTF-16 file(s) "
                             "being pushed on %s (range %s): %s. Terms are not echoed.\n"
                             % (local_ref, rng, "; ".join("%s -> indices %s" % (p, i)
                                                          for p, i in c_hits)))
            bad = True
        if c_leaks:
            sys.stderr.write("pre-push BLOCKED: credential-shaped string(s) inside COMPRESSED / UTF-16 "
                             "file(s) being pushed on %s (range %s): %s. Values are not echoed.\n"
                             % (local_ref, rng, "; ".join("%s -> %s" % (p, ", ".join(l))
                                                          for p, l in c_leaks)))
            bad = True
        if c_bad:
            # Blocks roster or not: an unproven credential scan is a blocked push, the same
            # rule as the unimportable-pattern-module branch above (review 2026-11-08).
            sys.stderr.write("pre-push BLOCKED (fail-closed): compressed file(s) in the push on "
                             "%s could not be fully read, so they cannot be proven free of "
                             "confidential terms or credentials: %s\n"
                             % (local_ref, "; ".join(c_bad)))
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
