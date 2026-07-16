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
  python scrub-before-optin.py <file-or-directory> [<file-or-directory> ...]
Exit 0 = clean (or no scannable files found). Exit 1 = at least one hit
(confidential term or secret pattern) — read the report before opting in.
"""
import importlib.util
import os
import re
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

# Advisory secret-shape patterns. Each is (label, compiled regex); the MATCHED
# TEXT is never printed, only the label + file:line, so a false positive
# costs a glance at the line, not a leaked value in the report itself.
SECRET_PATTERNS = [
    ("generic API key assignment",
     re.compile(r'(?i)\b(?:api[_-]?key|apikey)\b\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}')),
    ("AWS access key ID", re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ("GitHub token", re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b')),
    ("Slack token", re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}\b')),
    ("Anthropic API key", re.compile(r'\bsk-ant-[A-Za-z0-9_-]{20,}\b')),
    ("generic bearer token", re.compile(r'(?i)\bbearer\s+[A-Za-z0-9._-]{20,}')),
    ("password assignment", re.compile(r'(?i)\bpassword\b\s*[:=]\s*["\']?[^\s"\']{6,}')),
    ("PEM private-key block",
     re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
]


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


def load_active_term_seqs(terms_path=None):
    """(term_seqs, shape_warnings) via doctrine-integrity-probe.py's own
    matching functions -- term_seqs is [(deal_idx, term_idx, word-tuple)] for
    ACTIVE deals only. Returns ([], []) if the terms file is absent/malformed
    (fail-open, matching the probe's own posture; a warning explains why)."""
    raw, err = dip.read_optional(terms_path or TERMS_JSON)
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


def scan_file_for_secrets(path):
    """[(line_no, label), ...] for every secret-pattern hit in `path`. Never
    returns or prints the matched text itself."""
    body, _err = dip.read_optional(path)
    if body is None:
        return []
    hits = []
    for ln_no, line in enumerate(body.splitlines(), start=1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append((ln_no, label))
    return hits


def scrub(paths, terms_path=None):
    """Runs both scans over every scannable file under `paths`. Returns
    (term_hits, secret_hits, warnings):
      term_hits   -- [(file, [deal_idx, ...]), ...] for files with a term hit
      secret_hits -- [(file, [(line_no, label), ...]), ...] for files with a secret hit
      warnings    -- shape/skip warnings (terms file issues, etc.)
    Pure function -- no printing, no exit."""
    term_seqs, warnings = load_active_term_seqs(terms_path)
    term_hits, secret_hits = [], []
    for f in iter_scannable_files(paths):
        deal_idxs = scan_file_for_terms(f, term_seqs)
        if deal_idxs:
            term_hits.append((f, deal_idxs))
        secrets = scan_file_for_secrets(f)
        if secrets:
            secret_hits.append((f, secrets))
    return term_hits, secret_hits, warnings


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python scrub-before-optin.py <file-or-directory> [...]")
        return 1
    term_hits, secret_hits, warnings = scrub(argv)
    for w in warnings:
        print("[WARN] %s" % w)
    if not term_hits and not secret_hits:
        print("SCRUB CLEAN -- 0 confidential-term hits, 0 secret-pattern hits, "
              "%d warning(s)" % len(warnings))
        return 0
    print("SCRUB FOUND ISSUES -- review before opting this path into git tracking:")
    for f, deal_idxs in term_hits:
        print("  [CONFIDENTIAL-TERM] %s -- active deal #%s (index-only; "
              "review manually, term withheld)" % (f, ", #".join(str(d) for d in deal_idxs)))
    for f, hits in secret_hits:
        for ln_no, label in hits:
            print("  [SECRET-PATTERN] %s:%d -- %s (value withheld)" % (f, ln_no, label))
    print("\n%d file(s) with confidential-term hits, %d file(s) with secret-pattern hits"
          % (len(term_hits), len(secret_hits)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
