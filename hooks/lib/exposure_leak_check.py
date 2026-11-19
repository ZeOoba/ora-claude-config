#!/usr/bin/env python3
"""Exposure leak check: block a push that re-publishes pipeline, PII or debt data.

WHY (2026-11-18). The cross-repo audit of 2026-11-18 found this PUBLIC repo
(ZeOoba/ora-claude-config) publishing data that the roster-term, credential and RCT scans
cannot see, because none of it is a roster term, a credential or an RCT figure:
  * the acquisition-pipeline snapshot (deal names + stages + Notion page ids),
  * a named co-tenant's default record, the principal's contact record,
  * third-party broker / PM / vendor phone numbers in memory files,
  * loan balances and appraisal values.
Gabriel's ruling the same day: untrack the files and guard the push now (history purge is a
separate decision). The files are untracked and gitignored. This check stops them, or the same
data in another file, from being pushed again.

FOUR RULES, all over ADDED content only ('+' lines of `git log -p --cc --text`, plus rename /
copy targets). Removed lines are the fix, not the leak, so the push that deletes data passes.
  1. EXPOSURE PATH   -- content added to, or a file renamed / copied onto, a path in
                        EXPOSURE_PATHS (the untracked files). Path + rule reported.
  2. PHONE IN MEMORY -- an added line in a memory file (projects/*/memory/**) carrying a
                        North-American phone number. Contacts live in the gitignored
                        contacts.local.md; tracked memory carries a placeholder.
  3. PIPELINE SHAPE  -- a .json file whose added lines carry BOTH a "deal" key and a "stage"
                        key: the {page_id: {deal, stage}} pipeline-snapshot shape.
  4. DEBT FIGURE     -- an added line or commit-message line carrying a loan figure from the
                        gitignored data/loan-terms.json (original principal, balloon payment,
                        appraisal value; >= 100,000) or a literal from the optional private
                        denylist ~/.ora-private/exposure-denylist.json {"strings": [...]}
                        (lender loan numbers and anything else worth guarding).

FAIL MODES (same contract as rct_leak_check). Rules 1-3 need no private input and always run.
Rule 4: no loan-terms file and no denylist on this machine (CI, fresh clone) -> its needles are
None and the caller SKIPS rule 4, saying so. A source that EXISTS but cannot be read, parsed or
yields nothing -> ExposureSourceError; the caller BLOCKS. A set-but-missing env path BLOCKS.

REPORTS carry the path and the rule, never the matched value. Never publish a hash of a value.

RESIDUAL (stated, not hidden): phone numbers outside memory paths, international formats,
figures re-typed in another form ("$1.2M", words), compressed / UTF-16 blobs, and history
already on the remote are not caught. Stdlib only. ASCII-only.
"""
import fnmatch
import json
import os
import re
import subprocess

# Rule 1. Repo-relative, forward slashes, fnmatch syntax. Keep in step with .gitignore.
EXPOSURE_PATHS = (
    "maintenance/_state/deal-stage-snapshot.json",
    "projects/*/memory/people.md",
    "projects/*/memory/user.md",
    "projects/*/memory/tenant_*default*.md",
    "projects/*/memory/_archive/user_gabriel_consolidated_*.md",
)
MEMORY_GLOB = "projects/*/memory/*"  # fnmatch '*' crosses '/', so this covers subdirs

# Rule 2. NANP: optional +1, area code 2-9xx (parenthesised or not), exchange, line; the
# separators are required so a bare 10-digit id or a date never matches.
PHONE_RE = re.compile(
    r"(?<![\w.])(?:\+?1[-. ]?)?(?:\([2-9]\d{2}\)\s?|[2-9]\d{2}[-. ])[2-9]\d{2}[-. ]\d{4}(?![\w])")

# Published government office lines (not personal data), as 10 digits. Add only a number
# printed on the office's own public site; never a person's direct line.
PUBLIC_PHONES = frozenset({
    "6145253930",  # Franklin County (OH) Recorder, main office line
})


def _private_phone(text):
    for mt in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", mt.group(0))[-10:]
        if digits not in PUBLIC_PHONES:
            return True
    return False


# Rule 3.
DEAL_KEY_RE = re.compile(r'"deal"\s*:')
STAGE_KEY_RE = re.compile(r'"stage"\s*:')

DEBT_FLOOR = 100000
LOAN_FIELDS = ("original_principal", "balloon_payment")


class ExposureSourceError(Exception):
    """A private source exists but is unusable -- the caller must BLOCK."""


def is_exposure_path(path):
    return any(fnmatch.fnmatchcase(path, pat) for pat in EXPOSURE_PATHS)


def is_memory_path(path):
    return fnmatch.fnmatchcase(path, MEMORY_GLOB)


def _main_worktree_root(start_dir="."):
    try:
        p = subprocess.run(["git", "-C", start_dir, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True, timeout=5)
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
    if float(v) != int(v):
        out.add("{:,.2f}".format(v))
        out.add("{:.2f}".format(v))
    return out


def _loan_needles(doc):
    loans = doc.get("loans") if isinstance(doc, dict) else None
    if not isinstance(loans, list):
        raise ExposureSourceError("loan-terms file has no 'loans' list")
    out = set()
    for loan in loans:
        if not isinstance(loan, dict):
            continue
        for k in LOAN_FIELDS:
            out |= _fmt_number(loan.get(k))
        ap = loan.get("appraisal")
        if isinstance(ap, dict):
            out |= _fmt_number(ap.get("value"))
    return out


def load_needles(loan_terms_path=None, denylist_path=None, start_dir="."):
    """Set of literal needles for rule 4, or None when no private source is on this machine."""
    root = _main_worktree_root(start_dir)
    lt_default = os.path.join(root, "data", "loan-terms.json") if root else None
    lt, lt_req = _source(loan_terms_path, "ORA_LOAN_TERMS_PATH", lt_default)
    dl, dl_req = _source(denylist_path, "ORA_EXPOSURE_DENYLIST",
                         os.path.join(os.path.expanduser("~"), ".ora-private",
                                      "exposure-denylist.json"))
    needles, found = set(), False
    for path, required, kind in ((lt, lt_req, "loan"), (dl, dl_req, "deny")):
        if not path or not os.path.exists(path):
            if required:
                raise ExposureSourceError("configured source %s does not exist"
                                          % os.path.basename(path or "?"))
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
    # Not inside a longer number: no digit, or digit-group separator + digit, on either side.
    return re.compile(r"(?<![\d])(?<![\d][.,])(?:%s)(?![\d])(?![.,][\d])" % alts)


def scan_diff(body, needles=None):
    """Sorted list of (path_or_marker, rule) for a `git log -p --cc --text` body.
    Never returns a matched value."""
    m = _matcher(needles)
    hits = set()
    commit, path, width, in_msg = None, None, 0, False
    shape = {}  # (commit, path) -> {"deal": bool, "stage": bool}
    for line in body.split("\n"):
        if line.endswith("\r"):
            line = line[:-1]
        if line.startswith("commit ") and re.fullmatch(r"commit [0-9a-f]{40}.*", line):
            commit, path, width, in_msg = line.split()[1], None, 0, True
            continue
        if line.startswith("diff --git "):
            path, width, in_msg = line.rsplit(" b/", 1)[-1], 0, False
            continue
        if line.startswith("diff --cc ") or line.startswith("diff --combined "):
            path, width, in_msg = line.split(" ", 2)[2], 0, False
            continue
        if in_msg:
            if m and line.startswith("    ") and commit and m.search(line):
                hits.add(("<commit message %s>" % commit[:8], "debt-figure"))
            continue
        if not width:
            # File header zone: catch a rename / copy ONTO an exposure path (no hunk follows
            # for a 100%-similar rename, so the added-line rules would never see it).
            for pre in ("rename to ", "copy to "):
                if line.startswith(pre) and is_exposure_path(line[len(pre):]):
                    hits.add((line[len(pre):], "exposure-path"))
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
        if path.endswith(".json"):
            s = shape.setdefault((commit, path), {"deal": False, "stage": False})
            s["deal"] = s["deal"] or bool(DEAL_KEY_RE.search(text))
            s["stage"] = s["stage"] or bool(STAGE_KEY_RE.search(text))
            if s["deal"] and s["stage"]:
                hits.add((path, "pipeline-shape"))
        if m and m.search(text):
            hits.add((path, "debt-figure"))
    return sorted(hits)
