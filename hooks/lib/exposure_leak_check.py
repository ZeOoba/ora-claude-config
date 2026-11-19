#!/usr/bin/env python3
"""Exposure leak check: block a push that re-publishes pipeline, PII or debt data.

WHY (2026-11-18). The cross-repo audit of 2026-11-18 found this PUBLIC repo
(ZeOoba/ora-claude-config) publishing data that the roster-term, credential and RCT scans
cannot see, because none of it is a roster term, a credential or an RCT figure:
  * the acquisition-pipeline snapshot (deal names + stages + Notion page ids),
  * a co-tenant's default record, the principal's contact record,
  * third-party broker / PM / vendor phone numbers in memory files (and archived copies),
  * loan balances and appraisal values.
Gabriel's ruling the same day: untrack the files and guard the push now (history purge is a
separate decision). The files are untracked and gitignored. This check stops them, or the same
data in another file, from being pushed again.

FOUR RULES, all over ADDED content only ('+' lines of the pinned `git log` the caller runs --
see GIT_LOG_ARGS -- plus rename / copy targets). Removed lines are the fix, not the leak, so
the push that deletes data passes.
  1. EXPOSURE PATH   -- content added to, or a file renamed / copied onto, a path matching
                        EXPOSURE_PATHS, at ANY depth (an archive snapshot under
                        maintenance/_archive/... is the same file), case-insensitively.
  2. PHONE IN MEMORY -- an added line in a memory file (any .../projects/*/memory/... path,
                        archive copies included) carrying a North-American phone number
                        (separated, parenthesised, E.164, Unicode dashes, glued extension).
                        Published government office lines in PUBLIC_PHONES are allowed.
  3. PIPELINE SHAPE  -- a .json / .jsonl file whose added lines carry BOTH a "deal" key and a
                        "stage" key (any case): the {page_id: {deal, stage}} snapshot shape.
  4. DEBT FIGURE     -- an added line or commit-message line carrying a loan figure from the
                        gitignored data/loan-terms.json (every number >= 100,000 under
                        "loans": principal, balloon, appraisal, anchor balance, schedule) in
                        comma, bare or cents form, or a literal from the optional private
                        denylist ~/.ora-private/exposure-denylist.json {"strings": [...]}
                        (lender loan numbers and anything else worth guarding).

PATH PARSING. The caller pins `--src-prefix=a/ --dst-prefix=b/ -c core.quotePath=false`, so a
host's diff.noprefix / diff.srcPrefix cannot change the headers. The path is taken from the
`+++ b/` (or, for a deletion, `--- a/`) line, C-unquoted when git quotes it, never from the
`diff --git` line, whose split on " b/" is ambiguous for a directory ending in " b".
`--no-textconv --no-ext-diff` stop a local textconv driver hiding content.

FAIL MODES (same contract as rct_leak_check). Rules 1-3 need no private input and always run.
Rule 4: no loan-terms file and no denylist on this machine (CI, fresh clone) -> its needles are
None and the caller SKIPS rule 4, saying so. A source that EXISTS but cannot be read, parsed or
yields nothing, a set-but-missing env path, or a repo root that cannot be resolved (so the
default loan-terms location is unknown) -> ExposureSourceError; the caller BLOCKS.

REPORTS carry the path and the rule, never the matched value. Never publish a hash of a value.

RESIDUAL (stated, not hidden): phone numbers outside memory paths and non-NANP formats,
figures re-typed in another form ("$1.2M", words), compressed / UTF-16 blobs, annotated-tag
messages, and history already on the remote are not caught. Editing a line that already holds
a guarded figure counts as adding it, so such a push blocks until the figure is moved out.
Stdlib only. ASCII-only (non-ASCII dash code points are built with chr()).
"""
import fnmatch
import json
import os
import re
import subprocess

# Arguments the caller MUST use for the `git log` whose output feeds scan_diff().
GIT_LOG_ARGS = ["-c", "core.quotePath=false", "log", "-p", "--cc", "--text", "--no-color",
                "--no-textconv", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/",
                "--no-abbrev-commit", "--pretty=medium", "--no-renames"]
# --no-renames (REFUTE round 2): with -M/-C a copy or rename shows the moved lines as
# unchanged CONTEXT, so a phone copied into memory, or a file renamed onto people.md with
# edits, was never scanned. Without rename detection the target is a full add.

# Rule 1. Lower-case fnmatch patterns over the lower-cased repo-relative path; the leading
# '*' (which crosses '/') makes each one match at any depth. Keep in step with .gitignore.
EXPOSURE_PATHS = (
    "*deal-stage-snapshot.json",
    "*projects/*/memory/people.md",
    "*projects/*/memory/user.md",
    "*projects/*/memory/tenant_*default*.md",
    "*projects/*/memory/_archive/user_gabriel_consolidated_*.md",
)
MEMORY_GLOB = "*projects/*/memory/*"

# Rule 2. Separator: hyphen, dot, slash, space or a Unicode dash (U+2010..U+2015, U+2212),
# with optional spaces around it.
_DASHES = "".join(chr(c) for c in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212))
_SEP = r"\s*[-./ " + re.escape(_DASHES) + r"]\s*"
PHONE_RE = re.compile(
    r"(?<!\d)(?:"
    r"\+1[2-9]\d{2}[2-9]\d{6}"                                  # E.164, no separators
    r"|(?:\+?1" + _SEP + r")?"                                  # optional country code
    r"(?:\(\s*[2-9]\d{2}\s*\)\s*|[2-9]\d{2}" + _SEP + r")"      # area code
    r"[2-9]\d{2}" + _SEP + r"\d{4}"                             # exchange + line
    r")(?!\d)")

# Published government office lines (not personal data), as 10 digits. Add only a number
# printed on the office's own public site; never a person's direct line.
PUBLIC_PHONES = frozenset({
    "6145253930",  # Franklin County (OH) Recorder, main office line
})

# Rule 3.
DEAL_KEY_RE = re.compile(r'"deal"\s*:', re.I)
STAGE_KEY_RE = re.compile(r'"stage"\s*:', re.I)

DEBT_FLOOR = 100000


class ExposureSourceError(Exception):
    """A private source exists but is unusable -- the caller must BLOCK."""


def _norm(path):
    return path.replace("\\", "/").lower()


def is_exposure_path(path):
    p = _norm(path)
    return any(fnmatch.fnmatchcase(p, pat) for pat in EXPOSURE_PATHS)


def is_memory_path(path):
    return fnmatch.fnmatchcase(_norm(path), MEMORY_GLOB)


def _private_phone(text):
    for mt in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", mt.group(0))[-10:]
        if digits not in PUBLIC_PHONES:
            return True
    return False


_ESC = {"a": "\a", "b": "\b", "t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r",
        '"': '"', "\\": "\\"}


def _unquote(s):
    """git's C-style path quoting ("a/caf\\303\\251.md") -> plain text."""
    s = s.rstrip("\t")  # git appends a TAB to ---/+++ names that contain a space
    if not (len(s) >= 2 and s[0] == '"' and s[-1] == '"'):
        return s
    body, out, i = s[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            octal = body[i + 1:i + 4]
            if re.fullmatch(r"[0-7]{3}", octal):
                out.append(int(octal, 8))
                i += 4
                continue
            out += _ESC.get(body[i + 1], body[i + 1]).encode("utf-8")
            i += 2
            continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", "replace")


def _strip_prefix(name, prefix):
    name = _unquote(name)
    return name[len(prefix):] if name.startswith(prefix) else name


def _main_worktree_root(start_dir="."):
    try:
        p = subprocess.run(["git", "-C", start_dir, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.dirname(os.path.normpath(p.stdout.strip()))


def _source(explicit, env_name, default):
    """(path, required). An explicit arg or a set env var is REQUIRED to exist."""
    if explicit:
        return explicit, True
    env = os.environ.get(env_name)
    if env:
        return env, True
    return default, False


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise ExposureSourceError("%s unreadable or not JSON (%s)"
                                  % (os.path.basename(path), type(e).__name__))


def _fmt_number(v):
    out = set()
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v < DEBT_FLOOR:
        return out
    out.add("{:,.0f}".format(v))
    out.add("{:.0f}".format(v))
    out.add("{:,.2f}".format(v))
    out.add("{:.2f}".format(v))
    return out


def _walk_numbers(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_numbers(v, out)
    else:
        out |= _fmt_number(obj)


def _loan_needles(doc):
    loans = doc.get("loans") if isinstance(doc, dict) else None
    if not isinstance(loans, list):
        raise ExposureSourceError("loan-terms file has no 'loans' list")
    out = set()
    _walk_numbers(loans, out)
    return out


def load_needles(loan_terms_path=None, denylist_path=None, start_dir="."):
    """Set of literal needles for rule 4, or None when no private source is on this machine."""
    lt, lt_req = _source(loan_terms_path, "ORA_LOAN_TERMS_PATH", None)
    if lt is None:
        root = _main_worktree_root(start_dir)
        if root is None:
            raise ExposureSourceError("repo root could not be resolved, so the default "
                                      "data/loan-terms.json location is unknown")
        lt = os.path.join(root, "data", "loan-terms.json")
    dl, dl_req = _source(denylist_path, "ORA_EXPOSURE_DENYLIST",
                         os.path.join(os.path.expanduser("~"), ".ora-private",
                                      "exposure-denylist.json"))
    needles, found = set(), False
    for path, required, kind in ((lt, lt_req, "loan"), (dl, dl_req, "deny")):
        if not os.path.exists(path):
            if required:
                raise ExposureSourceError("configured source %s does not exist"
                                          % os.path.basename(path))
            continue
        found = True
        doc = _read_json(path)
        if kind == "loan":
            got = _loan_needles(doc)
        else:
            strings = doc.get("strings") if isinstance(doc, dict) else None
            if not isinstance(strings, list):
                raise ExposureSourceError("denylist has no 'strings' list")
            got = {s.strip() for s in strings if isinstance(s, str) and len(s.strip()) >= 4}
        if not got:
            raise ExposureSourceError("%s yielded no needles" % os.path.basename(path))
        needles |= got
    return needles if found else None


def _matcher(needles):
    if not needles:
        return None
    alts = "|".join(re.escape(n) for n in sorted(needles, key=len, reverse=True))
    # Not inside a longer number: no digit (or digit + group/decimal mark) on either side,
    # except a zero-cents tail ("1,111,111.00", "1111111.0"), which is the same figure.
    return re.compile(r"(?<![\d])(?<![\d][.,])(?:%s)(?:\.0+)?(?![\d])(?![.,][\d])" % alts)


def scan_diff(body, needles=None):
    """Sorted list of (path_or_marker, rule) for a body produced with GIT_LOG_ARGS.
    Never returns a matched value."""
    m = _matcher(needles)
    hits = set()
    commit, path, minus, width, in_msg = None, None, None, 0, False
    shape = {}  # (commit, path) -> {"deal": bool, "stage": bool}
    for line in body.split("\n"):
        if line.endswith("\r"):
            line = line[:-1]
        if line.startswith("commit ") and re.fullmatch(r"commit [0-9a-f]{40}.*", line):
            commit, path, minus, width, in_msg = line.split()[1], None, None, 0, True
            continue
        if line.startswith("diff --git ") or line.startswith("diff --cc ") \
                or line.startswith("diff --combined "):
            # The path is set from the ---/+++ lines that follow, never from this line.
            path, minus, width, in_msg = None, None, 0, False
            continue
        if in_msg:
            if m and line.startswith("    ") and commit and m.search(line):
                hits.add(("<commit message %s>" % commit[:8], "debt-figure"))
            continue
        if not width:
            for pre in ("rename to ", "copy to "):
                if line.startswith(pre):
                    tgt = _unquote(line[len(pre):])
                    if is_exposure_path(tgt):
                        hits.add((tgt, "exposure-path"))
            if line.startswith("--- "):
                name = line[4:]
                minus = None if name == "/dev/null" else _strip_prefix(name, "a/")
                continue
            if line.startswith("+++ "):
                name = line[4:]
                path = minus if name == "/dev/null" else _strip_prefix(name, "b/")
                continue
        if line.startswith("@@"):
            width = max(1, len(line) - len(line.lstrip("@")) - 1)
            continue
        if not width or path is None:
            continue
        prefix = line[:width]
        if "+" not in prefix or "-" in prefix:
            continue
        text = line[width:]
        if is_exposure_path(path):
            hits.add((path, "exposure-path"))
        if is_memory_path(path) and _private_phone(text):
            hits.add((path, "phone-in-memory"))
        if _norm(path).endswith((".json", ".jsonl")):
            s = shape.setdefault((commit, path), {"deal": False, "stage": False})
            s["deal"] = s["deal"] or bool(DEAL_KEY_RE.search(text))
            s["stage"] = s["stage"] or bool(STAGE_KEY_RE.search(text))
            if s["deal"] and s["stage"]:
                hits.add((path, "pipeline-shape"))
        if m and m.search(text):
            hits.add((path, "debt-figure"))
    return sorted(hits)
