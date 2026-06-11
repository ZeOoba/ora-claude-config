#!/usr/bin/env python3
"""ORA doctrine-integrity probe. REPORT-ONLY -- never edits anything.

Detects "doctrine drift": when CLAUDE.md references a slash command, local file,
repo, or skill that no longer resolves. Mirrors the memory-integrity-probe.py
pattern (report + exit code).

Checks:
  1. Slash commands  /build /debug /plan /refactor /research /ship etc.
     (EOS section)   -> ~/.claude/commands/<name>.md must exist        [MISSING -> fail]
  2. Referenced local files (EOS section)
       confidential-repos.json        -> ~/.claude/confidential-repos.json
       confidential-terms.json        -> ~/.claude/hooks/confidential-terms.json
       memory/event_log.md            -> ...projects/.../memory/event_log.md  [MISSING -> fail]
  3. Repo names (EOS section: oxford-command-center, website-canonical, oxford-site,
                 ora-pm) -> directory C:/Users/Owner/<repo> should exist  [WARN only]
  4. Skills named in the "Skill precedence" section -> must resolve as a real
     SKILL.md skill directory on EITHER surface: Code (~/.claude plugins + skills)
     or Cowork (the OneDrive workspace), or be a genuinely plugin-only skill in
     PLUGIN_SKILL_ALLOWLIST. Backup/archive copies are excluded.         [MISSING -> fail]
     The section header itself is required; its absence/rename is drift  [MISSING -> fail]
     NOTE: this check is cross-surface ON PURPOSE. Scanning only the Code surface
     produced a false "dead skill" finding during the 2026-06-06 setup review;
     the deal-lifecycle skills (deal-screen, acquisition-underwriting, etc.) live
     on the Cowork surface. Never narrow this back to one surface. If the skill
     scan is degraded (OneDrive offline / IO error), an unresolved skill is a
     [WARN], not [MISSING], so a transient cloud condition can't fail the gate.

  5. CLAUDE.md size budget: > WORD_BUDGET_FAIL words            [MISSING -> fail]
     (the pre-trim v1 file was 1,597 words; regression to that size must fail),
     > WORD_BUDGET_WARN = approaching                            [WARN only]
  6. Dated annotations: CLAUDE.md is doctrine-dateless (v2.1 layering: ALL dated
     history -> event_log.md). Any bare ISO date in CLAUDE.md    [MISSING -> fail]
     Dates embedded in hyphenated slugs (spec filenames like
     2026-06-05-engineering-...) are exempt. session-context.md (the volatile
     layer) MAY carry dates, but a date > TOMBSTONE_AGE_DAYS old is an aging
     tombstone that should have been consolidated                [WARN only]
  7. Cross-file duplication ("one fact, one home"): a run of >= DUP_SHINGLE_WORDS
     consecutive words shared verbatim between any two of CLAUDE.md /
     session-context.md / memory/rules.md                        [WARN only]
     WARN, not fail, while the known-deliberate residuals stand (rules.md
     secs 2-3 restate send-path/routing pending the next consolidation pass --
     event_log 2026-06-11). Flip to fail after that pass lands.
  8. Confidential-term leak (invariant 3: never name an active confidential deal
     in CLAUDE.md -- ~/.claude is git-tracked off-machine): any "always" term of
     an ACTIVE deal in hooks/confidential-terms.json found in CLAUDE.md, or (live
     mode) in any other *.md at the ~/.claude root              [MISSING -> fail]
     session-context.md is exempt: the sanctioned, git-UNTRACKED roster home.
     The report references deal/term by INDEX ONLY -- this probe's stdout is
     emailed weekly (eos-health-report.ps1) and must never echo a term.
     Unreadable terms file -> WARN (fail open), never a crash.

Exit 1 = any hard [MISSING] (command/file/skill absent, size budget, dated
         annotation, confidential leak), or CLAUDE.md / the EOS section is
         missing. Exit 0 = OK. WARN items never cause exit 1.

Optional argv[1] = path to a CLAUDE.md override (defaults to the real one),
so tests can point it at a fixture. Optional --session-context=PATH /
--rules=PATH / --terms=PATH override the companion files the same way.
Live mode (no CLAUDE.md override) additionally leak-scans ~/.claude root *.md.

Pure stdlib (re, os, sys, json, datetime, pathlib). ASCII-only output
(Windows cp1252 console).
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
CLAUDE_DIR = HOME / ".claude"
REAL_CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
COMMANDS_DIR = CLAUDE_DIR / "commands"
MEMORY_DIR = (CLAUDE_DIR / "projects"
              / "C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-" / "memory")
REPO_ROOT = Path("C:/Users/Owner")

# v2.1 (2026-06-11) renamed the section to "## Engineering OS (...)"; accept both
# forms so neither rewrite direction silently disables the whole probe.
SECTION_HEADER_RE = re.compile(r"^##\s+Engineering (?:Operating System|OS)\b")
NEXT_HEADER_RE = re.compile(r"^##\s+")
# A genuine slash command in this doctrine is written backtick-opened: `/name ...
# (every real command -- /build, /ram, /code-review -- follows this convention).
# The backtick must be an OPENING one (preceded by start-of-string, whitespace,
# or '('). This excludes path/word continuations such as `/oxford-site`/live and
# `Workflow`/parallel, where the backtick before '/' is a CLOSING backtick
# (preceded by a word character).
SLASH_RE = re.compile(r"(?:^|(?<=[\s(]))`/([a-z][a-z0-9-]*)\b")

# Repo names to check for as a local directory (WARN only).
REPO_NAMES = ("oxford-command-center", "website-canonical", "oxford-site", "ora-pm")

# Tokens that look like slash commands but resolve via a plugin skill rather than
# a ~/.claude/commands/<name>.md file -> not a command-file MISSING.
SLASH_SKILL_ALLOWLIST = {"code-review"}

# --- Skill check (cross-surface) ---
# Skills span TWO surfaces and CLAUDE.md "Skill precedence" routes across BOTH:
#   Code surface   -> ~/.claude/skills + ~/.claude/plugins
#   Cowork surface -> the OneDrive workspace
# Backup/archive trees are pruned so a deleted skill that lingers only in a backup
# still reports MISSING (correct), and so the live skill is found wherever it sits.
WORKSPACE = HOME / "OneDrive - Oxford Capital Partners (1)" / "Claude_Workspace"
SKILL_SCAN_ROOTS = (CLAUDE_DIR / "skills", CLAUDE_DIR / "plugins", WORKSPACE)
# Pruned ONLY for correctness (backup/archive copies) and speed (the top-level
# 02_Outputs artifact tree). Resolution is by SKILL.md presence (see
# collect_skill_dirs), which already excludes non-skill junk, so the prune list is
# deliberately minimal. DO NOT add bare "outputs": 01_Workspace/outputs/ is a real
# skill home for several Cowork skills, and pruning it once hid them so they passed
# only via the allowlist (review of c9dcdb9, finding #1).
SKILL_PRUNE_DIRS = {".git", "__pycache__", "node_modules", "backups", "_archive",
                    "02_outputs", "_state", "_manifest", ".obsidian"}
# Case-insensitive: a recase like "## Skill Precedence" must still be parsed, else
# a one-line header edit silently disables this whole check (review finding #2).
# v2.1 renamed the section "## Skill tie-breaks"; accept both forms.
SKILL_SECTION_RE = re.compile(r"^##\s+skill (?:precedence|tie-breaks)", re.I)
# Backtick-quoted skill name, optionally with a {-suffix} brace variant, e.g.
# `deal-screen` or `lease-abstraction{-pipeline}`.
SKILL_TOKEN_RE = re.compile(r"`([a-z][a-z0-9-]*(?:\{[a-z0-9-]+\})?)`")
# Skills that resolve via a PLUGIN (anthropic-skills:*) with NO local SKILL.md dir
# anywhere on disk -> absence of a local dir is NOT drift. Keep this MINIMAL: add a
# skill here ONLY if it has no on-disk SKILL.md on either surface (verify first).
# re-operations is currently the only such skill; the other anthropic-skills:*
# business skills DO have real SKILL.md homes under 01_Workspace/outputs/ and must
# resolve as real dirs, not via this list. Mirrors SLASH_SKILL_ALLOWLIST.
PLUGIN_SKILL_ALLOWLIST = {"re-operations"}

# The "Skill precedence" block names orchestration primitives that are NOT SKILL.md
# skills and must resolve against their own homes, else they false-positive as MISSING:
#   * AGENTS    -> ~/.claude/agents/<name>.md. CLAUDE.md literally labels these "agent"
#                  ("the bare `deal-recon` agent", "the `lease-sweep` agent", "the
#                  `portfolio-anomaly-scout` agent").
#   * WORKFLOWS -> ~/.claude/workflows/<name>.js (e.g. `verified-deal-recon`, the live
#                  DEFAULT pre-screen skill, is workflow-backed -- no SKILL.md dir).
# These live under ~/.claude (local), so they are NOT subject to the OneDrive
# degraded-scan downgrade and are checked before it.
AGENTS_DIR = CLAUDE_DIR / "agents"
WORKFLOWS_DIR = CLAUDE_DIR / "workflows"

# --- Checks 5-8 (2026-06-11 extension: enforce the v2.1 layered-doctrine model) ---
SESSION_CONTEXT_MD = CLAUDE_DIR / "session-context.md"
RULES_MD = MEMORY_DIR / "rules.md"
TERMS_JSON = CLAUDE_DIR / "hooks" / "confidential-terms.json"
# Budget calibration: the ratified v2.1 file (post Cowork-merge + Gabriel's edits,
# 2026-06-11) = 1,555 words; pre-trim v1 = 1,597 words and MUST fail. WARN starts
# below current size so the weekly report keeps nudging consolidation. TIGHTEN to
# 1400/1500 after the next consolidation pass claws back the merge-day growth.
WORD_BUDGET_FAIL = 1590
WORD_BUDGET_WARN = 1450
TOMBSTONE_AGE_DAYS = 30
DUP_SHINGLE_WORDS = 12
# Bare ISO date. The lookahead exempts dates embedded in hyphenated slugs
# (e.g. the spec filename 2026-06-05-engineering-operating-system-design.md):
# a slug date is immediately followed by '-<alnum>'; an annotation date is not.
# The digit guard stops partial matches inside longer numbers (2026-06-115).
# Deliberately NOT exempting trailing-slug dates (name-2026-06-05.md): that
# pattern is indistinguishable from a dated annotation -- fail closed.
ISO_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?![0-9]|-[0-9A-Za-z])")

WARN_COUNT = 0


def warn(msg):
    """Print a WARN line and count it -- the verdict reports the total so a
    fail-open degradation can never hide behind a clean exit code."""
    global WARN_COUNT
    WARN_COUNT += 1
    print("  [WARN]    %s" % msg)


def ascii_safe(s):
    """Untrusted text (filenames, exception messages) made cp1252-console-proof."""
    return str(s).encode("ascii", "backslashreplace").decode("ascii")

# Skills named in the doctrine PURELY as deprecated/legacy references: CLAUDE.md says
# "the standalone `deal-screen` / `cap-rate-snapshot` / `market-comp-analyzer` are
# legacy duplicates subsumed by [acquisition-underwriting]". They intentionally resolve
# to nothing on disk (archived) -- the reference IS the deprecation notice, so absence
# is expected-by-design, not drift. Mirrors SLASH_SKILL_ALLOWLIST / PLUGIN_SKILL_ALLOWLIST.
# Keep MINIMAL: add a name ONLY when CLAUDE.md references it expressly as legacy/subsumed.
LEGACY_DEPRECATED_ALLOWLIST = {"deal-screen", "cap-rate-snapshot", "market-comp-analyzer"}


def extract_section(text, header_re=SECTION_HEADER_RE):
    """Return a section (header through EOF or next '## ' header), or None."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if header_re.match(ln):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if NEXT_HEADER_RE.match(lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def expand_skill_token(tok):
    """Candidate skill names for a token, expanding a {..} brace variant.
    'lease-abstraction{-pipeline}' -> ['lease-abstraction-pipeline', 'lease-abstraction'].
    'deal-screen' -> ['deal-screen']."""
    m = re.match(r"^([a-z0-9-]*)\{([a-z0-9-]+)\}([a-z0-9-]*)$", tok)
    if m:
        pre, inner, post = m.group(1), m.group(2), m.group(3)
        return [pre + inner + post, pre + post]
    return [tok]


def collect_skill_dirs(roots, prune):
    """Scan roots for real skill dirs (directories that CONTAIN a SKILL.md).

    Returns (names, scan_errors, absent_roots):
      names        - lowercased set of skill-dir names found
      scan_errors  - OSErrors raised while walking (captured, not swallowed)
      absent_roots - configured roots that were not present (e.g. OneDrive offline)
    Matching by SKILL.md presence -- not bare directory name -- avoids resolving a
    skill against an unrelated eval/artifact folder that merely shares its name.
    The onerror hook + absent-root list let main() downgrade an unresolved skill to
    a visible WARN when the scan was degraded, rather than failing the gate falsely
    on a transient OneDrive/IO error (review finding #3)."""
    names = set()
    errs = []
    absent_roots = []
    for root in roots:
        if not root.is_dir():
            absent_roots.append(str(root))
            continue
        for dirpath, dirnames, filenames in os.walk(root, onerror=errs.append):
            dirnames[:] = [d for d in dirnames if d.lower() not in prune]
            if "SKILL.md" in filenames:
                names.add(os.path.basename(dirpath).lower())
    return names, errs, absent_roots


def collect_flat_names(directory, suffix):
    """Lowercased set of <name> for files named <name><suffix> directly in directory.
    Used for agents (~/.claude/agents/*.md) and workflows (~/.claude/workflows/*.js),
    which are flat single-file definitions, not SKILL.md directories."""
    if not directory.is_dir():
        return set()
    out = set()
    try:
        for fn in os.listdir(directory):
            low = fn.lower()
            if low.endswith(suffix):
                out.add(low[: -len(suffix)])
    except OSError:
        pass
    return out


def bare_dates(text):
    """(line_no, 'YYYY-MM-DD') for every bare ISO date (slug-embedded exempt)."""
    out = []
    for ln_no, ln in enumerate(text.splitlines(), 1):
        for m in ISO_DATE_RE.finditer(ln):
            out.append((ln_no, m.group(0)))
    return out


def word_stream(text):
    """Lowercased alphanumeric word sequence -- normalization for the
    duplication check (markdown, punctuation and unicode dashes drop out)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def shared_runs(words_a, words_b, n=DUP_SHINGLE_WORDS):
    """ASCII excerpts (one per maximal run) of >= n consecutive words that appear
    verbatim in both word streams. Detection by n-word shingle intersection;
    adjacent matching shingles in B are merged so one duplicated paragraph
    reports once, not per-shingle."""
    if len(words_a) < n or len(words_b) < n:
        return []
    shingles_a = set()
    for i in range(len(words_a) - n + 1):
        shingles_a.add(tuple(words_a[i:i + n]))
    runs = []
    j = 0
    limit = len(words_b) - n + 1
    while j < limit:
        if tuple(words_b[j:j + n]) in shingles_a:
            start = j
            while j < limit and tuple(words_b[j:j + n]) in shingles_a:
                j += 1
            runs.append(" ".join(words_b[start:start + n]) + " ...")
        else:
            j += 1
    return runs


def read_optional(path):
    """(text, error) -- never raises; absent/unreadable -> (None, reason).
    Encoding fallbacks: utf-8 -> utf-16 (Windows PowerShell 5 Out-File default)
    -> cp1252, so an oddly-encoded staging file is scanned, not skipped."""
    try:
        p = Path(path)
        if not p.is_file():
            return None, "not found: %s" % p
        for enc in ("utf-8", "utf-16", "cp1252"):
            try:
                return p.read_text(encoding=enc), None
            except UnicodeError:
                continue
        return None, "undecodable: %s" % p
    except Exception as e:
        return None, "unreadable (%s): %s" % (path, e)


def term_word_seqs(terms_data):
    """([(deal_idx, term_idx, word-tuple)], [shape_warnings]) for ACTIVE deals.

    Word-sequence (not raw substring) matching: a term split by a line wrap,
    markdown emphasis, NBSP or punctuation still matches its normalized word
    run. deal_idx counts EVERY non-'_' key (even malformed ones) so index-only
    reports point at the right entry in the terms file. Malformed shapes
    (non-dict entry, non-list 'always') degrade to a warning, never a crash."""
    seqs, shape_warns = [], []
    deal_idx = 0
    for key, entry in terms_data.items():
        if key.startswith("_"):
            continue
        deal_idx += 1
        if not isinstance(entry, dict):
            shape_warns.append("terms deal #%d: entry is not an object -- "
                               "skipped (fail-open)" % deal_idx)
            continue
        if not entry.get("active"):
            continue
        always = entry.get("always")
        if not isinstance(always, list):
            shape_warns.append("terms deal #%d: 'always' is not a list -- "
                               "skipped (fail-open)" % deal_idx)
            continue
        for t_i, term in enumerate(always):
            ws = tuple(word_stream(str(term)))
            if ws:
                seqs.append((deal_idx, t_i, ws))
    return seqs, shape_warns


def contains_run(haystack_words, needle_words):
    """True if needle_words appears as a contiguous run in haystack_words."""
    n = len(needle_words)
    if n == 0 or len(haystack_words) < n:
        return False
    first = needle_words[0]
    for i in range(len(haystack_words) - n + 1):
        if haystack_words[i] == first and tuple(haystack_words[i:i + n]) == needle_words:
            return True
    return False


def git_tracked_md(repo_dir):
    """Repo-relative paths (posix) of git-TRACKED *.md files, or None if git is
    unavailable -- tracked files are exactly what reaches the off-machine remote."""
    try:
        import subprocess
        r = subprocess.run(["git", "-C", str(repo_dir), "ls-files", "-z", "--", "*.md"],
                           capture_output=True, timeout=15)
        if r.returncode != 0:
            return None
        return {p for p in r.stdout.decode("utf-8", "replace").split("\0") if p}
    except Exception:
        return None


def parse_args(argv):
    """Positional CLAUDE.md override + --session-context/--rules/--terms=PATH."""
    overrides = {}
    pos = []
    for a in argv:
        if a.startswith("--session-context="):
            overrides["session_context"] = Path(a.split("=", 1)[1])
        elif a.startswith("--rules="):
            overrides["rules"] = Path(a.split("=", 1)[1])
        elif a.startswith("--terms="):
            overrides["terms"] = Path(a.split("=", 1)[1])
        elif a.startswith("--"):
            # A typo'd flag must not silently become the CLAUDE.md path (which
            # would also disable live-mode scanning). Fail loud.
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms=)" % ascii_safe(a))
            sys.exit(1)
        else:
            pos.append(a)
    return pos, overrides


def main():
    pos, overrides = parse_args(sys.argv[1:])
    argv_path = pos[0] if pos else None
    claude_md = Path(argv_path) if argv_path else REAL_CLAUDE_MD
    live_mode = argv_path is None

    if not claude_md.is_file():
        print("[MISSING] CLAUDE.md not found: %s" % claude_md)
        sys.exit(1)

    try:
        text = claude_md.read_text(encoding="utf-8")
    except Exception as e:
        print("[MISSING] cannot read CLAUDE.md (%s): %s" % (claude_md, e))
        sys.exit(1)

    section = extract_section(text)
    if section is None:
        print("[MISSING] '## Engineering Operating System' / '## Engineering OS' "
              "section not found in %s" % claude_md)
        sys.exit(1)

    print("DOCTRINE INTEGRITY PROBE -- source: %s" % claude_md)
    missing = []

    # --- 1. slash commands ---
    cmds = sorted({m.group(1) for m in SLASH_RE.finditer(section)})
    print("Slash commands referenced: %d" % len(cmds))
    for name in cmds:
        target = COMMANDS_DIR / ("%s.md" % name)
        if target.is_file():
            print("  [OK]      /%s -> %s" % (name, target))
        elif name in SLASH_SKILL_ALLOWLIST:
            print("  [OK]      /%s -> (plugin skill; no command file expected)" % name)
        else:
            print("  [MISSING] /%s -> %s" % (name, target))
            missing.append("/%s (command file %s)" % (name, target))

    # --- 2. referenced local files ---
    file_checks = []
    if "confidential-repos.json" in section:
        file_checks.append(("confidential-repos.json",
                            CLAUDE_DIR / "confidential-repos.json"))
    if "confidential-terms.json" in section:
        file_checks.append(("confidential-terms.json",
                            CLAUDE_DIR / "hooks" / "confidential-terms.json"))
    if "event_log.md" in section:
        file_checks.append(("memory/event_log.md", MEMORY_DIR / "event_log.md"))

    print("Local files referenced: %d" % len(file_checks))
    for label, target in file_checks:
        if target.is_file():
            print("  [OK]      %s -> %s" % (label, target))
        else:
            print("  [MISSING] %s -> %s" % (label, target))
            missing.append("%s (file %s)" % (label, target))

    # --- 3. repo names (WARN only) ---
    repos = [r for r in REPO_NAMES if r in section]
    print("Repos referenced: %d" % len(repos))
    for r in repos:
        target = REPO_ROOT / r
        if target.is_dir():
            print("  [OK]      %s -> %s" % (r, target))
        else:
            warn("%s -> %s (not at expected path; repo may be elsewhere)" % (r, target))

    # --- 4. skills referenced in the "Skill precedence" section (cross-surface) ---
    skill_section = extract_section(text, SKILL_SECTION_RE)
    if skill_section is None:
        # The section this check audits is canonical doctrine; its removal/rename
        # is itself drift -> hard-fail, mirroring the EOS section (review finding #2).
        print("Skills referenced: 0")
        print("  [MISSING] '## Skill precedence' section not found "
              "(canonical doctrine; removal/rename is itself drift)")
        missing.append("'Skill precedence' section (absent from %s)" % claude_md)
    else:
        tokens = sorted({m.group(1) for m in SKILL_TOKEN_RE.finditer(skill_section)})
        print("Skills referenced: %d" % len(tokens))
        known, scan_errs, absent_roots = collect_skill_dirs(SKILL_SCAN_ROOTS, SKILL_PRUNE_DIRS)
        agents = collect_flat_names(AGENTS_DIR, ".md")
        workflows = collect_flat_names(WORKFLOWS_DIR, ".js")
        degraded = bool(scan_errs) or bool(absent_roots)
        for r in absent_roots:
            warn("skill-scan root unavailable (offline?): %s" % r)
        if scan_errs:
            warn("%d IO error(s) during skill scan -- unresolved skills "
                 "downgraded to WARN, not drift" % len(scan_errs))
        for tok in tokens:
            variants = expand_skill_token(tok)
            hit = next((v for v in variants if v.lower() in known), None)
            if hit:
                print("  [OK]      %s -> skill dir '%s' (Code/Cowork surface)" % (tok, hit))
            elif any(v.lower() in PLUGIN_SKILL_ALLOWLIST for v in variants):
                print("  [OK]      %s -> (plugin-provided skill; no local skill dir)" % tok)
            # Resolution below is by NAME-match (a real on-disk agent/workflow file
            # exists), not ROLE-match (we don't verify CLAUDE.md calls the token an
            # "agent"/"workflow"). The skill/agent/workflow namespaces are deliberately
            # distinct here, so a collision that masks a missing skill is not a realistic
            # condition; if that ever changes, gate these on nearby "agent"/"workflow" text.
            elif any(v.lower() in agents for v in variants):
                print("  [OK]      %s -> agent definition (~/.claude/agents/)" % tok)
            elif any(v.lower() in workflows for v in variants):
                print("  [OK]      %s -> workflow (~/.claude/workflows/)" % tok)
            elif any(v.lower() in LEGACY_DEPRECATED_ALLOWLIST for v in variants):
                print("  [OK]      %s -> legacy/deprecated reference (subsumed; intentionally archived)" % tok)
            elif degraded:
                warn("%s -> unresolved, but skill scan was degraded "
                     "(OneDrive offline?); not treating as drift" % tok)
            else:
                print("  [MISSING] %s -> no skill dir (Code/Cowork) and not a known plugin skill"
                      % tok)
                missing.append("%s (skill; Code/Cowork/plugin)" % tok)

    # --- 5. CLAUDE.md size budget ---
    words = len(text.split())
    print("CLAUDE.md size: %d words (warn > %d, fail > %d)"
          % (words, WORD_BUDGET_WARN, WORD_BUDGET_FAIL))
    if words > WORD_BUDGET_FAIL:
        print("  [MISSING] size budget exceeded: %d > %d words "
              "(pre-trim v1 was 1,597 -- this is regression; move a rule down a layer)"
              % (words, WORD_BUDGET_FAIL))
        missing.append("CLAUDE.md size budget (%d > %d words)" % (words, WORD_BUDGET_FAIL))
    elif words > WORD_BUDGET_WARN:
        warn("approaching the size budget (%d words; fail at %d)"
             % (words, WORD_BUDGET_FAIL))
    else:
        print("  [OK]      within budget")

    # --- 6. dated annotations (CLAUDE.md dateless; session-context tombstone aging) ---
    dates = bare_dates(text)
    print("Dated annotations in CLAUDE.md: %d (doctrine: dateless; slug filenames exempt)"
          % len(dates))
    for ln_no, d in dates:
        print("  [MISSING] bare date %s at line %d (dated history belongs in event_log.md)"
              % (d, ln_no))
        missing.append("dated annotation %s (CLAUDE.md line %d)" % (d, ln_no))

    sc_text, sc_err = read_optional(overrides.get("session_context", SESSION_CONTEXT_MD))
    if sc_text is None:
        warn("session-context aging check skipped: %s" % ascii_safe(sc_err))
    else:
        today = datetime.date.today()
        aging = []
        for ln_no, d in bare_dates(sc_text):
            try:
                age = (today - datetime.date.fromisoformat(d)).days
            except ValueError:
                continue
            if age > TOMBSTONE_AGE_DAYS:
                aging.append((ln_no, d, age))
        print("Aging tombstones in session-context: %d (dates > %d days old)"
              % (len(aging), TOMBSTONE_AGE_DAYS))
        for ln_no, d, age in aging:
            warn("aging tombstone: %s (%d days old) at session-context "
                 "line %d -- consolidate to event_log.md" % (d, age, ln_no))

    # --- confidential-term sequences (loaded BEFORE checks 7-8: check 7 screens
    # its printed excerpts against them; check 8 is the leak scan itself) ---
    term_seqs = []
    terms_raw, terms_err = read_optional(overrides.get("terms", TERMS_JSON))
    if terms_raw is None:
        warn("confidential-term scan skipped (fail-open): %s" % ascii_safe(terms_err))
    else:
        try:
            terms_data = json.loads(terms_raw)
        except ValueError as e:
            terms_data = None
            warn("confidential-term scan skipped (fail-open): terms file "
                 "unparseable (%s)" % ascii_safe(e))
        if terms_data is not None:
            if not isinstance(terms_data, dict):
                warn("confidential-term scan skipped (fail-open): terms file is "
                     "not a JSON object")
            else:
                term_seqs, shape_warns = term_word_seqs(terms_data)
                for w in shape_warns:
                    warn(w)

    # --- 7. cross-file duplication (one fact, one home) ---
    rules_text, rules_err = read_optional(overrides.get("rules", RULES_MD))
    sources = [("CLAUDE.md", text)]
    if sc_text is not None:
        sources.append(("session-context.md", sc_text))
    if rules_text is None:
        warn("rules.md duplication check skipped: %s" % ascii_safe(rules_err))
    else:
        sources.append(("memory/rules.md", rules_text))
    dup_total = 0
    for i in range(len(sources)):
        for k in range(i + 1, len(sources)):
            (name_a, body_a), (name_b, body_b) = sources[i], sources[k]
            runs = shared_runs(word_stream(body_a), word_stream(body_b))
            dup_total += len(runs)
            for excerpt in runs[:5]:
                # session-context.md is the confidential-roster home: an excerpt
                # could echo a deal name into this emailed report. Screen every
                # excerpt against the active term sequences before printing.
                if any(contains_run(excerpt.split(), seq) for _, _, seq in term_seqs):
                    warn("duplicated run (%s <-> %s): (excerpt withheld -- "
                         "contains a confidential term)" % (name_a, name_b))
                else:
                    warn("duplicated run (%s <-> %s): \"%s\"" % (name_a, name_b, excerpt))
            if len(runs) > 5:
                warn("... and %d more duplicated run(s) (%s <-> %s)"
                     % (len(runs) - 5, name_a, name_b))
    print("Cross-file duplication: %d shared run(s) of >= %d words "
          "(WARN-only until the rules.md consolidation pass; then flip to fail)"
          % (dup_total, DUP_SHINGLE_WORDS))

    # --- 8. confidential-term leak scan (invariant 3) ---
    # Coverage = the probed CLAUDE.md + (live mode) every git-TRACKED *.md in
    # ~/.claude (tracked files are exactly what reaches the off-machine remote;
    # verified 29+ tracked .md live in agents/, commands/, docs/, ...) + every
    # UNTRACKED *.md at the root (local staging hygiene -- port artifacts etc.).
    # session-context.md is the sanctioned roster home (invariant 3) and is
    # exempt ONLY while untracked: the exemption is revoked at runtime the
    # moment git ls-files reports it. Matching is by normalized word run
    # (word_stream), so case, line wraps, markdown emphasis and NBSP cannot
    # defeat it. Reports are INDEX-ONLY (deal #/term #, and a filename is
    # withheld when the term appears in the name itself): this probe's stdout
    # is emailed weekly and must never echo a term.
    if term_seqs:
        leak_targets = [("CLAUDE.md", text)]
        if live_mode:
            sc_name = "session-context.md"
            tracked = git_tracked_md(CLAUDE_DIR)
            if tracked is None:
                warn("leak scan: git unavailable -- coverage limited to ~/.claude root")
                tracked = set()
            sc_tracked = sc_name in tracked
            if sc_tracked:
                warn("session-context.md is git-TRACKED -- roster-home exemption "
                     "revoked; scanning it")
            seen = {"claude.md"}
            candidates = []
            for rel in sorted(tracked):
                if rel.lower() in seen:
                    continue
                candidates.append(rel)
                seen.add(rel.lower())
            try:
                for fn in sorted(os.listdir(CLAUDE_DIR)):
                    fl = fn.lower()
                    if (not fl.endswith(".md")) or fl in seen:
                        continue
                    if fl == sc_name and not sc_tracked:
                        continue
                    if (CLAUDE_DIR / fn).is_file():
                        candidates.append(fn)
                        seen.add(fl)
            except OSError as e:
                warn("leak scan: cannot list ~/.claude root (%s)" % ascii_safe(e))
            for rel in candidates:
                body, err = read_optional(CLAUDE_DIR / rel)
                if body is None:
                    warn("leak scan cannot read %s (%s)" % (ascii_safe(rel), ascii_safe(err)))
                else:
                    leak_targets.append((rel, body))
        active_deals = len({d for d, _, _ in term_seqs})
        print("Confidential-term scan: %d file(s) x %d active term(s) across %d deal(s)"
              % (len(leak_targets), len(term_seqs), active_deals))
        for tgt_i, (label, body) in enumerate(leak_targets, 1):
            body_words = word_stream(body)
            name_words = word_stream(label)
            for deal_idx, t_i, seq in term_seqs:
                hit_name = contains_run(name_words, seq)
                if hit_name:
                    print("  [MISSING] confidential term (deal #%d, always[%d]) in the "
                          "FILENAME of scan target #%d (name withheld) -- invariant 3"
                          % (deal_idx, t_i, tgt_i))
                    missing.append("confidential leak in FILENAME of scan target #%d "
                                   "(deal #%d, term %d)" % (tgt_i, deal_idx, t_i))
                if contains_run(body_words, seq):
                    safe_label = (("scan target #%d (name withheld)" % tgt_i)
                                  if hit_name else ascii_safe(label))
                    print("  [MISSING] confidential term (deal #%d, always[%d]) found "
                          "in %s -- invariant 3: tracked/staged in ~/.claude"
                          % (deal_idx, t_i, safe_label))
                    missing.append("confidential leak in %s (deal #%d, term %d)"
                                   % (safe_label, deal_idx, t_i))
    else:
        # 0 active term sequences = either every deal genuinely closed, or the
        # terms file degraded above. Either way say so -- silence is how a
        # gutted terms file impersonates a clean pass.
        warn("confidential-term scan: 0 active term(s) resolved -- leak check "
             "inert this run")

    # --- verdict ---
    if missing:
        print("DOCTRINE DRIFT: %d unresolved reference(s); %d warning(s)"
              % (len(missing), WARN_COUNT))
        for m in missing:
            print("  - " + m)
        sys.exit(1)
    print("OK -- all referenced commands, local files and skills resolve. "
          "(%d warning(s))" % WARN_COUNT)
    sys.exit(0)


if __name__ == "__main__":
    main()
