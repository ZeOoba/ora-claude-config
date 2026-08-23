#!/usr/bin/env python3
"""ORA session-context cross-reference probe. REPORT-ONLY -- never edits anything.

session-context.md is the volatile current-state layer, and its whole design is to
be terse and POINT somewhere else for detail ("History: `event_log.md` 2026-08-22",
"Detail: `oxford-cc-repo-health.md`", "Full claim protocol: `tech.md` sec 2"). Those
pointers are load-bearing -- a session reads the bullet, follows the pointer, and acts
on what it finds. A pointer to something that does not exist is worse than no pointer:
it reads as "the history is recorded, go look" when nothing was ever written.

That is not hypothetical. On 2026-08-22 session-context.md cited "History:
`event_log.md` 2026-08-22" for `ora-passed-deal-tracker`; the ratification had been
recorded in session-context.md ONLY and no such event_log entry existed. Nothing
detected it -- it was noticed by a session that happened to go looking for the entry.
doctrine-integrity-probe.py checks CLAUDE.md's references, not session-context.md's,
and its check 10 only measures session-context.md's LENGTH. This is that missing edge.

Checks:
  1. DATED event_log citations: `event_log.md` named on the same line as an ISO date
     must correspond to a "## YYYY-MM-DD ..." entry heading in event_log.md, or in one
     of the rolled-over chunks under memory/_archive/. Undated mentions of event_log.md
     are not checkable and are ignored on purpose.        [XREF-MISSING -> exit 1]
  2. FILE citations: any backticked token that looks like a real filename/path
     (.md/.py/.ps1/.json) must resolve on disk, searched against the memory dir,
     ~/.claude and its usual subdirs, and the ora-skills repo.  [XREF-MISSING -> exit 1]
     Elided paths (containing an ellipsis), spaced prose, and non-file tokens are
     skipped -- this probe is deliberately narrow, because a false [XREF-MISSING]
     in a daily guard is more expensive than a missed one.

Fail-open: an unreadable/absent session-context.md or memory dir prints [SKIP] and
exits 0 -- "could not look" is never reported as "nothing wrong", and the missing-source
alarm is already backup-session-context.py's job, not this probe's.

Exit 1 = at least one unresolved cross-reference. Exit 0 = clean or skipped.

Usage:
    python session-context-xref-probe.py [--source PATH] [--memory-dir PATH] [--json]
"""
import argparse
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):  # UTF-8 safe output on Windows cp1252 pipes
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CLAUDE_DIR = os.path.join(HOME, ".claude")
DEFAULT_SOURCE = os.path.join(CLAUDE_DIR, "session-context.md")
DEFAULT_MEMORY_DIR = os.path.join(
    CLAUDE_DIR, "projects", "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")
ORA_SKILLS = os.path.join(HOME, "ora-skills")

ISO_DATE_RE = re.compile(r"\b(20\d\d-[01]\d-[0-3]\d)\b")
BACKTICK_RE = re.compile(r"`([^`]+)`")
ENTRY_HEADING_RE = re.compile(r"^##\s+(20\d\d-[01]\d-[0-3]\d)", re.MULTILINE)
# A citation token only counts as a file reference if it ENDS in one of these.
FILE_SUFFIXES = (".md", ".py", ".ps1", ".json")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def event_log_dates(memory_dir):
    """Every date that has an entry heading in event_log.md OR in a rolled-over archive
    chunk. The archives matter: event_log.md is rolled over periodically (see
    rollover-event-log.py), so a citation to a date older than the current rollover
    window resolves in memory/_archive/, not in the live log. Checking only the live
    log would turn every rollover into a wave of false [XREF-MISSING] lines."""
    dates = set()
    files = [os.path.join(memory_dir, "event_log.md")]
    archive = os.path.join(memory_dir, "_archive")
    if os.path.isdir(archive):
        files += [os.path.join(archive, n) for n in os.listdir(archive)
                  if n.endswith(".md") and "event_log" in n.lower()]
    found_any = False
    for p in files:
        try:
            text = _read(p)
        except Exception:
            continue
        found_any = True
        dates.update(ENTRY_HEADING_RE.findall(text))
    return dates, found_any


def dated_event_log_citations(text):
    """(line_no, date) for every line that names event_log.md AND carries an ISO date.

    Same-line proximity is the whole heuristic, and it is deliberately crude: a bullet
    that says "History: `event_log.md` 2026-08-16" is making a checkable claim, while a
    bare "History: `event_log.md`" is not. Multiple dates on one line each get checked
    (a bullet may cite two entries)."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        if "event_log.md" not in line:
            continue
        for d in ISO_DATE_RE.findall(line):
            out.append((i, d))
    return out


def extra_roots():
    """Optional additional search roots, one JSON list at _state/xref-extra-roots.json.

    session-context.md legitimately cites files that live outside ~/.claude -- the
    owner-outreach bounding manifests under the OneDrive business folder, for one. A
    citation this probe simply cannot SEE is a verified-null, and reporting it as
    XREF-MISSING would be exactly the false-positive class this probe must not produce.
    Rather than hardcode every such home forever, the well-known ones are listed below
    and anything new goes in that file. Fail-open: unreadable/malformed -> no extras."""
    try:
        with open(os.path.join(CLAUDE_DIR, "maintenance", "_state", "xref-extra-roots.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    roots = data.get("roots") if isinstance(data, dict) else data
    return [r for r in roots if isinstance(r, str)] if isinstance(roots, list) else []


ONEDRIVE = os.path.join(HOME, "OneDrive - Oxford Capital Partners")


def search_roots(memory_dir):
    """Where a bare citation like `tech.md` or `hooks/confidential-terms.json` may live.
    Order is cheapest-most-likely first; resolution stops at the first hit."""
    return [
        memory_dir,
        os.path.dirname(memory_dir.rstrip("\\/")),   # lets `memory/foo.md` resolve
        CLAUDE_DIR,
        os.path.join(CLAUDE_DIR, "maintenance"),
        os.path.join(CLAUDE_DIR, "hooks"),
        os.path.join(CLAUDE_DIR, "scheduled-tasks"),
        os.path.join(CLAUDE_DIR, "commands"),
        os.path.join(memory_dir, "_archive"),
        ORA_SKILLS,
        # LAMS/Cowork fleet store + the two OneDrive homes session-context.md points into
        os.path.join(ONEDRIVE, "Documents", "Claude", "Scheduled"),
        os.path.join(ONEDRIVE, "Business", "Investment Candidates -- 2026"),
        os.path.join(ONEDRIVE, "Claude_Workspace"),
    ] + extra_roots()


def is_file_citation(token):
    """Narrow on purpose. A token qualifies only if it is a bare filename or a path with
    no whitespace and no elision. Everything else -- prose in backticks, code fragments,
    `update_scheduled_task(enabled:false)`, an elided registry path like
    `AppData\\Roaming\\Claude\\...\\scheduled-tasks.json` -- is skipped, because a false
    XREF-MISSING in a daily guard costs more attention than a missed one."""
    t = token.strip()
    if not t or any(c.isspace() for c in t):
        return False
    if "…" in t or "..." in t:
        return False
    if not t.lower().endswith(FILE_SUFFIXES):
        return False
    # a trailing sentence period, a glob, or a wildcard segment is not a literal path
    return "*" not in t and "?" not in t


def resolve(token, memory_dir):
    """Absolute path this citation resolves to, or None. Handles ~ and both slash
    directions; a drive-lettered or UNC path is taken literally."""
    t = token.strip().replace("/", os.sep).replace("\\", os.sep)
    if t.startswith("~"):
        cand = os.path.expanduser(t)
        return cand if os.path.exists(cand) else None
    if re.match(r"^[A-Za-z]:", t) or t.startswith(os.sep * 2):
        return t if os.path.exists(t) else None
    for root in search_roots(memory_dir):
        cand = os.path.join(root, t)
        if os.path.exists(cand):
            return cand
    return None


def file_citations(text):
    """(line_no, token) for every backticked token that looks like a real file path."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        for tok in BACKTICK_RE.findall(line):
            if is_file_citation(tok):
                out.append((i, tok.strip()))
    return out


def probe(source=None, memory_dir=None):
    """Returns (findings, skips, stats). A finding is an unresolved cross-reference."""
    source = source or DEFAULT_SOURCE
    memory_dir = memory_dir or DEFAULT_MEMORY_DIR
    findings, skips = [], []

    try:
        text = _read(source)
    except Exception as exc:
        return [], [f"session-context source unreadable ({source}): {exc}"], {}
    if not text.strip():
        return [], [f"session-context source is empty ({source})"], {}

    dated = dated_event_log_citations(text)
    known_dates, log_readable = event_log_dates(memory_dir)
    if not log_readable:
        skips.append(f"event_log.md + archives unreadable under {memory_dir} "
                     f"-- {len(dated)} dated citation(s) NOT checked")
    else:
        for line_no, date in dated:
            if date not in known_dates:
                findings.append({
                    "kind": "event-log-entry",
                    "line": line_no,
                    "ref": date,
                    "detail": f"session-context.md:{line_no} cites event_log.md {date}, "
                              f"but no '## {date}' entry exists in event_log.md or memory/_archive/",
                })

    cited = file_citations(text)
    for line_no, tok in cited:
        if resolve(tok, memory_dir) is None:
            findings.append({
                "kind": "file",
                "line": line_no,
                "ref": tok,
                "detail": f"session-context.md:{line_no} cites `{tok}`, which resolves nowhere "
                          f"under the memory dir, ~/.claude (+ maintenance/hooks/scheduled-tasks/"
                          f"commands), or ora-skills",
            })

    stats = {"datedEventLogCitations": len(dated), "fileCitations": len(cited),
             "eventLogDatesKnown": len(known_dates)}
    return findings, skips, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=None, help="path to session-context.md")
    ap.add_argument("--memory-dir", default=None, help="path to the ORA memory directory")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    findings, skips, stats = probe(args.source, args.memory_dir)

    if args.json:
        print(json.dumps({"findings": findings, "skips": skips, "stats": stats}, indent=2))
    else:
        for s in skips:
            print(f"[SKIP] {s}")
        for f in findings:
            print(f"[XREF-MISSING] {f['detail']}")
        if not findings:
            print(f"[OK] session-context.md cross-references resolve "
                  f"({stats.get('datedEventLogCitations', 0)} dated event_log citation(s), "
                  f"{stats.get('fileCitations', 0)} file citation(s) checked)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
