#!/usr/bin/env python3
"""Pre-opt-in scrub helper — a reusable check to run before adding a new
top-level ~/.claude directory to git tracking (the .gitignore !/dirname/
opt-in pattern used for scheduled-tasks/, memory/, workflows/, prompts/,
mcp-servers/, obsidian-fleet-mirror/, and _scheduled_tasks_backup/ so far).

WHY (2026-07-16): doctrine-integrity-probe.py check 12 (backup-coverage sweep)
will keep surfacing new untracked-dir opt-in candidates, and each one so far
needed the same confidential-terms + secret-pattern grep sequence rebuilt by
hand -- which is exactly how the FRED API key hardcoded in a retired SKILL.md
got caught, but only because that grep happened to be written that day. This
wraps it into one reusable, tested script instead of re-deriving it each time.

Two checks, both index-only / redacted in the report (never echoes a real
confidential term or secret value):
  1. Confidential-term scan — reuses doctrine-integrity-probe.py's own
     term_word_seqs/word_stream/contains_run (the SAME matching logic the
     enforced probe uses), so "is this text confidential" never drifts
     between the two tools. ACTIVE deals only (declassified deals are, by
     definition, no longer confidential — that's check 13's job, not this).
  2. Secret-pattern scan — a small set of common credential shapes (API key
     assignment, AWS/GitHub/Slack/Anthropic key prefixes, bearer tokens,
     password assignment, PEM private-key blocks). Advisory, not exhaustive:
     a HELPER for the human doing the opt-in review, not a hard gate.

Usage:
  python scrub-before-optin.py [--terms <roster.json>] <file-or-directory> [...]
Exit 0 = clean (or no scannable files found). Exit 1 = at least one hit
(confidential term or secret pattern) — read the report before opting in.
Exit 2 = TERM SCAN NOT RUN: the confidential roster could not be read (absent,
unparseable, not an object), so "no confidential hits" would be meaningless.
Never reported as clean (egress audit 2026-11-12, M32).

Roster resolution: --terms if given (used exactly, no fallback); else this
checkout's hooks/confidential-terms.json; else the MAIN worktree's copy (the
roster is gitignored, so a linked worktree never has one) -- the same two-step
as confidentiality-guard.py and git-prepush-confidential-scan.py.

Files that cannot be read or decoded are LISTED as "NOT scanned" in the report
(they used to be skipped silently). They do not change the exit code: a binary
blob is common in an opt-in candidate, and the human reviewer decides.
"""
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dip", HERE / "doctrine-integrity-probe.py")
dip = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dip)

TERMS_JSON = HERE.parent / "hooks" / "confidential-terms.json"

# Directories never worth scanning (binary/regenerable/VCS-internal). Mirrors
# the spirit of BACKUP_SWEEP_TRANSIENT_DIRS in doctrine-integrity-probe.py but
# scoped to "skip while walking a candidate tree", not "skip the whole dir".
SKIP_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv"}

# Advisory secret-shape patterns -- now IMPORTED, not redefined (Gabriel ruling
# 2026-07-24). This list and setup-self-audit.py's had already diverged, with neither a
# superset of the other; hooks/lib/secret_patterns.py is their union and the single source
# the pre-push gate also uses. This mirrors what this file already does for confidential
# terms (it imports doctrine-integrity-probe's matcher rather than copying it) -- the
# stated reason there was that the two must never drift apart, and the same applies here.
# The MATCHED TEXT is still never printed, only the label + file:line.
_LIB = HERE.parent / "hooks" / "lib"
sys.path.insert(0, str(_LIB))
import secret_patterns as _secret_lib  # noqa: E402

SECRET_PATTERNS = _secret_lib.SECRET_PATTERNS


def iter_scannable_files(paths):
    """Yields Path objects for every regular file under `paths` (files passed
    directly are yielded as-is), skipping SKIP_DIR_NAMES directories."""
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
                for name in files:
                    yield Path(root) / name


def _main_worktree_terms():
    """hooks/confidential-terms.json in the MAIN worktree (via git-common-dir), or None."""
    try:
        r = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return None
    common = Path(out) if os.path.isabs(out) else (HERE / out)
    cand = common.resolve().parent / "hooks" / "confidential-terms.json"
    try:
        if cand.resolve() == TERMS_JSON.resolve():
            return None
    except Exception:
        pass
    return cand


def resolve_terms_path(terms_path=None):
    """Explicit path as given; else this checkout's roster, falling back to the main worktree's."""
    if terms_path:
        return Path(terms_path)
    if TERMS_JSON.is_file():
        return TERMS_JSON
    return _main_worktree_terms() or TERMS_JSON


def load_active_term_seqs(terms_path=None):
    """(term_seqs, shape_warnings) via doctrine-integrity-probe.py's own
    matching functions -- term_seqs is [(deal_idx, term_idx, word-tuple)] for
    ACTIVE deals only. Returns ([], []) if the terms file is absent/malformed
    (fail-open, matching the probe's own posture; a warning explains why)."""
    raw, err = dip.read_optional(resolve_terms_path(terms_path))
    if raw is None:
        return [], ["confidential-term scan skipped (fail-open): %s" % err]
    try:
        import json
        data = json.loads(raw)
    except ValueError as e:
        return [], ["confidential-term scan skipped (fail-open): terms file unparseable (%s)" % e]
    if not isinstance(data, dict):
        return [], ["confidential-term scan skipped (fail-open): terms file is not a JSON object"]
    return dip.term_word_seqs(data)


def scan_file_for_terms(path, term_seqs):
    """[deal_idx, ...] (deduped) of ACTIVE deals whose terms appear anywhere in
    `path`'s content, or None if the file is unreadable/undecodable (skipped,
    not a hit). Index-only, matching doctrine-integrity-probe.py's own
    convention -- never surfaces the actual matched term or deal key."""
    body, _err = dip.read_optional(path)
    if body is None:
        return None
    words = dip.word_stream(body)
    hits = sorted({deal_idx for deal_idx, _term_idx, seq in term_seqs
                   if dip.contains_run(words, seq)})
    return hits


MULTILINE_SENTINEL = 0  # line_no for a label that matched ACROSS lines, not on any one


def scan_file_for_secrets(path):
    """[(line_no, label), ...] for every secret hit in `path`. Never returns or prints
    the matched text itself.

    Routed through `secret_patterns.scan_text` (2026-08-03) instead of iterating
    SECRET_PATTERNS raw. The raw loop bypassed BOTH of scan_text's guarantees, so this
    consumer silently disagreed with the pre-push gate and the daily audit about the same
    file -- exactly the divergence importing the shared lib was meant to end:
      * the reference/placeholder/code suppressor never ran here, so `TOKEN =
        os.environ.get(...)` and `NAME = lib.CONST` were reported as credentials;
      * per-line matching cannot see a MULTI-LINE assignment (`CRON_SECRET:` then an
        indented value) -- the pattern's whitespace run spans newlines, which is why
        scan_text evaluates whole text. That was a REFUTE-confirmed false negative
        class in the 2026-07-30 gap fix.

    scan_text is whole-text and returns labels only, so line numbers are re-derived
    best-effort for display: a label that no single line reproduces came from a
    cross-line match and is reported at MULTILINE_SENTINEL. The authoritative
    determination is always scan_text's -- line attribution never adds or drops a label.

    NOT applied here, deliberately: `secret_patterns.is_exempt_path()`. The pre-push gate
    exempts test-fixture paths because it must not block every push; scrub gates a NEW
    tree ENTERING version control, where a `tests/` directory is exactly as unvetted as
    any other. Staying stricter than the gate is the safe direction for this caller, and
    the difference is a policy choice rather than drift -- recorded so a future reader
    does not "fix" it into consistency."""
    body, _err = dip.read_optional(path)
    if body is None:
        return []
    labels = set(_secret_lib.scan_text(body))
    if not labels:
        return []
    hits, attributed = [], set()
    for ln_no, line in enumerate(body.splitlines(), start=1):
        for label in _secret_lib.scan_text(line):
            if label in labels and (ln_no, label) not in hits:
                hits.append((ln_no, label))
                attributed.add(label)
    for label in sorted(labels - attributed):
        hits.append((MULTILINE_SENTINEL, label))
    return hits


def scrub_report(paths, terms_path=None):
    """Both scans over every scannable file under `paths`, as a dict:
      term_hits     -- [(file, [deal_idx, ...]), ...] for files with a term hit
      secret_hits   -- [(file, [(line_no, label), ...]), ...] for files with a secret hit
      warnings      -- shape/skip warnings (terms file issues, etc.)
      term_scan_ran -- False when the roster could not be read: NO term scan happened
      skipped       -- files that could not be read/decoded (scanned for nothing)
    Pure function -- no printing, no exit."""
    term_seqs, warnings = load_active_term_seqs(terms_path)
    ran = not any(w.startswith("confidential-term scan skipped") for w in warnings)
    term_hits, secret_hits, skipped = [], [], []
    for f in iter_scannable_files(paths):
        deal_idxs = scan_file_for_terms(f, term_seqs)
        if deal_idxs is None:
            skipped.append(f)
            continue
        if deal_idxs:
            term_hits.append((f, deal_idxs))
        secrets = scan_file_for_secrets(f)
        if secrets:
            secret_hits.append((f, secrets))
    return {"term_hits": term_hits, "secret_hits": secret_hits, "warnings": warnings,
            "term_scan_ran": ran, "skipped": skipped}


def scrub(paths, terms_path=None):
    """(term_hits, secret_hits, warnings) -- the original 3-tuple view of scrub_report()."""
    r = scrub_report(paths, terms_path)
    return r["term_hits"], r["secret_hits"], r["warnings"]


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    terms_path = None
    if "--terms" in argv:
        i = argv.index("--terms")
        if i + 1 >= len(argv):
            print("usage: python scrub-before-optin.py [--terms <roster.json>] <path> [...]")
            return 1
        terms_path = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        print("usage: python scrub-before-optin.py [--terms <roster.json>] <path> [...]")
        return 1
    rep = scrub_report(argv, terms_path)
    term_hits, secret_hits, warnings = rep["term_hits"], rep["secret_hits"], rep["warnings"]
    for w in warnings:
        print("[WARN] %s" % w)
    for f in rep["skipped"]:
        print("[SKIPPED] %s -- unreadable or undecodable, NOT scanned; review it by hand" % f)
    unscanned = ("; %d file(s) NOT scanned (listed above)" % len(rep["skipped"])
                 if rep["skipped"] else "")
    if not rep["term_scan_ran"]:
        print("TERM SCAN NOT RUN -- the confidential roster could not be read, so this tree was "
              "NOT checked for confidential deal terms. %d secret-pattern hit file(s)%s.\n"
              "Next step: run from the main ~/.claude checkout, or pass --terms <roster.json>; "
              "do not opt this path in on this result." % (len(secret_hits), unscanned))
        for f, hits in secret_hits:
            for ln_no, label in hits:
                print("  [SECRET-PATTERN] %s:%d -- %s (value withheld)" % (f, ln_no, label))
        return 2
    if not term_hits and not secret_hits:
        print("SCRUB CLEAN -- 0 confidential-term hits, 0 secret-pattern hits, "
              "%d warning(s)%s" % (len(warnings), unscanned))
        return 0
    print("SCRUB FOUND ISSUES -- review before opting this path into git tracking:")
    for f, deal_idxs in term_hits:
        print("  [CONFIDENTIAL-TERM] %s -- active deal #%s (index-only; "
              "review manually, term withheld)" % (f, ", #".join(str(d) for d in deal_idxs)))
    for f, hits in secret_hits:
        for ln_no, label in hits:
            print("  [SECRET-PATTERN] %s:%d -- %s (value withheld)" % (f, ln_no, label))
    print("\n%d file(s) with confidential-term hits, %d file(s) with secret-pattern hits%s"
          % (len(term_hits), len(secret_hits), unscanned))
    return 1


if __name__ == "__main__":
    sys.exit(main())
