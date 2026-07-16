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
     (fail is a one-in-one-out gate ~95 words above the honest post-consolidation
     floor -- see the WORD_BUDGET_* constants for the calibration),
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
     Files under ~/.claude/_confidential-staging/ are likewise exempt: the
     sanctioned untracked home for active deal-bound artifacts (rules.md sec 7a).
     The exemption is NARROW -- only that one subtree, and only while untracked;
     a git-TRACKED file there is still scanned (tracked = off-machine remote).
     The report references deal/term by INDEX ONLY -- this probe's stdout is
     emailed weekly (eos-health-report.ps1) and must never echo a term.
     Unreadable terms file -> WARN (fail open), never a crash.
  9. MEMORY.md index-entry hook length: for any index bullet
     (- [Title](file.md) -- desc), the hook text after the link, if over
     MEMORY_INDEX_HOOK_MAXLEN chars -- memory-policy.md sec 3 mandates
     "a one-line description" per entry (no numeric cap of its own)  [WARN only]
 10. session-context.md terseness: whole file over SESSION_CONTEXT_MAX_LINES lines,
     or any bullet over SESSION_CONTEXT_MAX_BULLET_WORDS words -- the volatile
     current-state layer must not accrete dated narratives (dated history ->
     event_log.md, per CLAUDE.md's scope-layering rule)             [WARN only]
 11. Guard liveness: every guard named in CLAUDE.md's "Guards:" line (EOS section)
     must have a LIVE invocation point -- a settings.json hook command, a CC/MCP
     scheduled-task SKILL.md, or the ~/.claude git pre-push shim -- not merely a
     file that exists on disk. Closes the orphan class that motivated this probe:
     a guard named "active" whose only runner was silently retired, unnoticed.
     Code-surface scope only (no OneDrive LAMS fleet I/O); an unreadable source
     downgrades an unresolved guard to a soft WARN, never a false orphan  [WARN only]

Exit 1 = any hard [MISSING] (command/file/skill absent, size budget, dated
         annotation, confidential leak), or CLAUDE.md / the EOS section is
         missing. Exit 0 = OK. WARN items never cause exit 1.

Optional argv[1] = path to a CLAUDE.md override (defaults to the real one),
so tests can point it at a fixture. Optional --session-context=PATH /
--rules=PATH / --terms=PATH override the companion files the same way.
Live mode (no CLAUDE.md override) additionally leak-scans ~/.claude root *.md.
--quick runs only checks 5+6 (size budget, bare dates) against the given/default path and skips everything else -- fast enough to run on every CLAUDE.md edit.

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
              / "C--Users-Owner-OneDrive---Oxford-Capital-Partners" / "memory")
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

# Known ported copies of CLAUDE.md (the master ~/.claude/CLAUDE.md is the probed
# file itself and is covered separately). Used by check 13 -- see that check for
# why this specific set of files matters.
PORTED_CLAUDE_MD_COPIES = (
    Path(r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude Command Center Code\CLAUDE.md"),
    Path(r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\CLAUDE.md"),
    Path(r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\oxford-site\.claude\CLAUDE.md"),
    Path(r"C:\Users\Owner\Obsidian\BrainVault\CLAUDE.md"),
)

# --- Check 12 (2026-07-16 extension): backup-coverage sweep. Three times now a
# top-level ~/.claude dir accumulated doctrine-bearing content while the
# .gitignore /* default-deny silently kept it out of the private-remote backup
# AND out of git-status single-writer visibility (scheduled-tasks -> opt-in 2b,
# memory/ -> 2c, workflows/ -> 2026-07-16). The sweep flags any top-level dir
# with ZERO git-tracked files that is not a known-transient runtime dir -- an
# opt-in REVIEW CANDIDATE, not a verdict (WARN-only: every opt-in needs its own
# confidential-terms scrub first). Root-level FILES are out of scope: they are
# opted in one-by-one and a new one is conspicuous in any .gitignore review;
# dirs are where content accumulates unnoticed. Adding a name here is a
# deliberate, git-recorded ruling that the dir is transient/runtime state (or,
# for _confidential-staging, must NEVER reach the off-machine remote).
BACKUP_SWEEP_TRANSIENT_DIRS = {
    # harness/runtime state, caches, per-session scratch -- regenerable
    ".claude", ".firecrawl", ".superpowers", "artifacts", "backups", "cache",
    "daemon", "debug", "downloads", "handoffs", "ide", "jobs", "paste-cache",
    "plans", "plugins", "session-env", "sessions", "shell-snapshots", "statsig",
    "tasks", "telemetry", "todos", "worktrees",
    # append-event-log.py staging (drains into event_log.md; transient by design)
    "_tmp_entries",
    # NEVER track (invariant 3): confidential staging must not reach the remote.
    # daemon/ (above) additionally holds key files -- also never track.
    "_confidential-staging",
}

# Tokens that look like slash commands but resolve via a plugin skill rather than
# a ~/.claude/commands/<name>.md file -> not a command-file MISSING.
SLASH_SKILL_ALLOWLIST = {"code-review"}

# --- Skill check (cross-surface) ---
# Skills span TWO surfaces and CLAUDE.md "Skill precedence" routes across BOTH:
#   Code surface   -> ~/.claude/skills + ~/.claude/plugins
#   Cowork surface -> the OneDrive workspace
# Backup/archive trees are pruned so a deleted skill that lingers only in a backup
# still reports MISSING (correct), and so the live skill is found wherever it sits.
WORKSPACE = HOME / "OneDrive - Oxford Capital Partners" / "Claude_Workspace"
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
# Sanctioned untracked confidential-staging home (rules.md sec 7a): active
# deal-bound files legitimately sit UNTRACKED under this subtree during a live
# deal. They never reach git (the fail-closed .gitignore ignores the whole dir,
# plus the pre-push scanner), so check 8's leak scan intentionally does NOT
# descend into it -- otherwise every staged file re-fires an unresolvable
# [MISSING] every run and buries a genuinely new leak in known noise (alert
# fatigue). The exemption is NARROW: it covers this one dir, and only for
# UNTRACKED files -- git_tracked_md() still scans anything git-TRACKED under it,
# so a file that ever gets `git add`ed here is still caught (tracked =
# off-machine remote = real egress; invariant 3 holds).
CONFIDENTIAL_STAGING_DIRNAME = "_confidential-staging"
# Budget calibration (recalibrated 2026-07-08): the old 1590 fail was just a
# snapshot of pre-trim v1 (1,597 words), not a principled ceiling. Two independent
# full-file consolidation passes -- each verified by THIS probe at 0 cross-file
# duplication with every skill/file ref still [OK] -- both bottomed out at
# ~1700-1755 words as the honest floor for CLAUDE.md's current legitimate scope;
# cutting further would gut Hard Invariants or skill-routing rules that fixed real
# bugs. FAIL (1850) sits ~95 words above the actual count ON PURPOSE: it is a
# one-in-one-out forcing function -- additions get a small buffer, but anything past
# it demands an equivalent trim elsewhere in the SAME change, turning CLAUDE.md's
# own "when adding a rule, move something down a layer" principle into a measurable
# gate instead of an aspiration. WARN (1700) marks the consolidation floor so the
# weekly report keeps nudging before the gate bites.
WORD_BUDGET_FAIL = 1850
WORD_BUDGET_WARN = 1700
TOMBSTONE_AGE_DAYS = 30
DUP_SHINGLE_WORDS = 12
# Bare ISO date. The lookahead exempts dates embedded in hyphenated slugs
# (e.g. the spec filename 2026-06-05-engineering-operating-system-design.md):
# a slug date is immediately followed by '-<alnum>'; an annotation date is not.
# The digit guard stops partial matches inside longer numbers (2026-06-115).
# Deliberately NOT exempting trailing-slug dates (name-2026-06-05.md): that
# pattern is indistinguishable from a dated annotation -- fail closed.
ISO_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?![0-9]|-[0-9A-Za-z])")

# --- Checks 9-10 (2026-07-08 extension): the same one-fact-one-home / terseness
# discipline this probe already enforces on CLAUDE.md, extended to the two files
# that were failing it undetected because the probe only ever scanned CLAUDE.md --
# MEMORY.md's index and session-context.md. ---
# Check 9: memory-policy.md sec 3 requires each MEMORY.md index entry be "a one-line
# description", but states NO numeric cap; 150 chars operationalizes "one-line" --
# past it a "- [Title](file.md) -- desc" bullet has become a paragraph, not a
# pointer (a prior audit found index entries running 400-800 chars). WARN, mirroring
# check 7's severity: index bloat is hygiene drift, not a broken reference, so it
# nudges via the weekly report without flipping the exit code.
# The measurement is the HOOK text only (the description after the link),
# not the whole bulleted line. Renamed MEMORY_INDEX_LINE_MAXLEN ->
# MEMORY_INDEX_HOOK_MAXLEN accordingly.
MEMORY_INDEX_MD = MEMORY_DIR / "MEMORY.md"
MEMORY_INDEX_HOOK_MAXLEN = 150
# An index entry = a bulleted markdown link to a .md file: "- [Title](file.md) ...".
# '>' blockquote pointer lines at the top of MEMORY.md are intentionally NOT matched.
MEMORY_INDEX_ENTRY_RE = re.compile(r"^\s*[-*]\s*\[[^\]]+\]\([^)]*\.md[^)]*\)")
# Check 10: session-context.md's own header says "keep terse" and the v2.1 layering
# makes it the VOLATILE current-state layer only -- ALL dated history belongs in
# event_log.md. It had no numeric enforcement and accreted 200-300 word incident
# narratives. Two proxies for "this is a narrative, not a terse state pointer": the
# whole file over 40 lines, OR any single bullet over 80 words. WARN, not fail --
# what is still "current state" vs. "history" legitimately needs a human judgment
# call, so this informs rather than blocks.
SESSION_CONTEXT_MAX_LINES = 40
SESSION_CONTEXT_MAX_BULLET_WORDS = 80
BULLET_RE = re.compile(r"^\s*[-*]\s+\S")

# --- Check 11 (2026-07-08 extension): guard liveness. The failure THIS probe exists
# to catch was itself an orphan -- for weeks doctrine-integrity-probe.py had no live
# runner after its only scheduled trigger was retired, and nothing noticed. Checks 1-4
# prove a named guard's FILE exists; none proved it is actually WIRED to run. Check 11
# verifies each guard in CLAUDE.md's "Guards:" line has >=1 live invocation point. ---
SETTINGS_JSON = CLAUDE_DIR / "settings.json"
SCHEDULED_TASKS_DIR = CLAUDE_DIR / "scheduled-tasks"
PREPUSH_SHIM = CLAUDE_DIR / ".git" / "hooks" / "pre-push"
# A backtick-quoted token on the Guards: line. Guard names are bare filenames/
# identifiers; GUARD_NAME_RE drops anything else the parse catches (e.g. the
# eos-plan-gate override recipe `touch hooks/sessions/<id>/override`, which is a
# command with spaces/slashes, not a guard).
GUARD_TOKEN_RE = re.compile(r"`([^`]+)`")
GUARD_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

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


def collect_hook_commands(settings_obj):
    """Every hook 'command' string anywhere under settings['hooks'], walked
    generically across ALL lifecycle stages (PreToolUse/PostToolUse/SessionStart/
    Stop/SessionEnd/...) so a guard wired into any stage resolves. Used by check 11
    (guard liveness) to test a guard's filename stem against real invocations."""
    cmds = []

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "command" and isinstance(v, str):
                    cmds.append(v)
                else:
                    _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(settings_obj.get("hooks", {}) if isinstance(settings_obj, dict) else {})
    return cmds


def bare_dates(text):
    """(line_no, 'YYYY-MM-DD') for every bare ISO date (slug-embedded exempt)."""
    out = []
    for ln_no, ln in enumerate(text.splitlines(), 1):
        for m in ISO_DATE_RE.finditer(ln):
            out.append((ln_no, m.group(0)))
    return out


def check_size_and_dates(text):
    """CLAUDE.md hard-fail violations only (checks 5+6's MISSING-tier findings):
    size budget and bare ISO dates. Pure function -- no I/O, no printing, no
    side effects on the module-level 'missing'/WARN_COUNT state main() uses.
    Returns a list of violation message strings (empty = clean).

    Deliberately NOT reused by main()'s own checks 5/6 (which keep their
    existing inline print/warn/missing.append flow untouched) -- main()'s path
    is exercised by test_size_budget_fail/test_dated_annotation_fails and must
    stay byte-for-byte unchanged; this is intentionally the small amount of
    accepted duplication with bare_dates()/WORD_BUDGET_FAIL that buys that
    guarantee, not an oversight.

    Does NOT include check 6's session-context tombstone-aging sub-check
    (WARN-only, reads session-context.md, not CLAUDE.md -- out of scope for a
    per-edit CLAUDE.md check).
    """
    violations = []
    words = len(text.split())
    if words > WORD_BUDGET_FAIL:
        violations.append(
            "size budget exceeded: %d > %d words (one-in-one-out gate breached -- "
            "trim an equivalent amount elsewhere in this same change; move a rule "
            "down a layer)" % (words, WORD_BUDGET_FAIL))
    for ln_no, d in bare_dates(text):
        violations.append(
            "bare date %s at line %d (dated history belongs in event_log.md)"
            % (d, ln_no))
    return violations


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
        if not entry.get("active", True):
            # default-ACTIVE matches confidentiality-guard.py (aligned 2026-06-11):
            # a deal missing the flag must be both enforced AND leak-scanned.
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


# Synthetic control terms for the no-active-deal self-check (check 8). Chosen to be
# distinctive enough to never legitimately appear in the tree, so the NEGATIVE control
# (they must be absent from real content) is stable.
SYNTHETIC_LEAK_TERMS = [
    "Zephyr Nightingale Portfolio LLC",
    "1742 Chimera Fixture Boulevard",
    "Project Halcyon Placeholder",
]


def leak_scan_selfcheck(samples):
    """Positive+negative control that the confidential leak MATCHER (word_stream +
    contains_run) is still live during a no-active-deal window -- when there are zero
    real term sequences and check 8 would otherwise be fully inert, silently providing
    no assurance on this fail-closed boundary. Mirrors the synthetic-terms fallback in
    hooks/tests/test-confidentiality-guard.py, reused inside the probe itself.

    samples = [(label, body_text)] of real content KNOWN not to contain the synthetic
    terms (e.g. CLAUDE.md). Returns (ok, findings): findings is a list of hard-fail
    strings -- a broken matcher (a planted synthetic term NOT detected) or an
    over-match/collision (a synthetic control term found in real content). Empty
    findings => ok=True."""
    findings = []
    seqs = [tuple(word_stream(t)) for t in SYNTHETIC_LEAK_TERMS]
    # POSITIVE control: a body that DOES contain each synthetic term MUST match.
    for term, seq in zip(SYNTHETIC_LEAK_TERMS, seqs):
        planted = word_stream("lead-in noise " + term + " trailing noise")
        if not seq or not contains_run(planted, seq):
            findings.append("leak-scan SELF-CHECK FAILED: the matcher did not detect a "
                            "planted synthetic term -- confidential leak detection is "
                            "NON-FUNCTIONAL (word_stream/contains_run regression)")
    # NEGATIVE control: the synthetic terms MUST NOT appear in any real sample.
    for label, body in samples:
        bw = word_stream(body)
        for seq in seqs:
            if seq and contains_run(bw, seq):
                findings.append("leak-scan SELF-CHECK: a synthetic control term matched in "
                                "%s -- matcher over-matching or a synthetic term collided "
                                "with real content" % ascii_safe(label))
    return (not findings), findings


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
        elif a == "--quick":
            overrides["quick"] = True
        elif a.startswith("--memory-index="):
            overrides["memory_index"] = Path(a.split("=", 1)[1])
        elif a.startswith("--backup-root="):
            overrides["backup_root"] = Path(a.split("=", 1)[1])
        elif a.startswith("--ported-copies="):
            v = a.split("=", 1)[1]
            overrides["ported_copies"] = [Path(p) for p in v.split(",") if p]
        elif a.startswith("--"):
            # A typo'd flag must not silently become the CLAUDE.md path (which
            # would also disable live-mode scanning). Fail loud.
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms= --quick --memory-index= --backup-root= "
                  "--ported-copies=)" % ascii_safe(a))
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

    if overrides.get("quick"):
        violations = check_size_and_dates(text)
        if violations:
            print("DOCTRINE QUICK-CHECK -- source: %s" % claude_md)
            for v in violations:
                print("  [MISSING] " + v)
            print("QUICK-CHECK DRIFT: %d violation(s)" % len(violations))
            sys.exit(1)
        print("QUICK-CHECK OK -- %s within word budget, no bare dates" % claude_md)
        sys.exit(0)

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
              "(one-in-one-out gate breached -- trim an equivalent amount elsewhere "
              "in this same change; move a rule down a layer)"
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
    terms_data = None
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
    # FLIPPED 2026-07-14: was WARN-only pending the rules.md consolidation pass
    # (10 dated history-wall section headers removed, 3 narrative walls trimmed
    # to event_log.md pointers, 2677 -> 2449 words -- see event_log.md). That
    # pass has landed, so a new duplication is now a hard failure, not just
    # advisory -- the individual excerpts above still print via warn() for
    # detail, but the run itself now also fails the probe.
    print("Cross-file duplication: %d shared run(s) of >= %d words"
          % (dup_total, DUP_SHINGLE_WORDS))
    if dup_total > 0:
        missing.append("%d cross-file duplicated run(s) of >= %d words (one fact, "
                        "one home -- see the [WARN] lines above for which files/excerpts)"
                        % (dup_total, DUP_SHINGLE_WORDS))

    # --- 8. confidential-term leak scan (invariant 3) ---
    # Coverage = the probed CLAUDE.md + (live mode) every git-TRACKED *.md in
    # ~/.claude (tracked files are exactly what reaches the off-machine remote;
    # verified 29+ tracked .md live in agents/, commands/, docs/, ...) + every
    # UNTRACKED *.md at the root (local staging hygiene -- port artifacts etc.).
    # The ~/.claude/_confidential-staging/ subtree is exempt from the untracked
    # root scan (rules.md sec 7a: sanctioned untracked home for active deal-bound
    # files); TRACKED files there are NOT exempt -- see CONFIDENTIAL_STAGING_DIRNAME.
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
                    # Sanctioned untracked confidential-staging home (rules.md
                    # sec 7a): the root listing is non-recursive, so this subtree's
                    # UNTRACKED files are already out of scope; skip the dir entry
                    # explicitly so the exemption is intentional, not incidental,
                    # and survives any future move to a recursive walk. A TRACKED
                    # file under it is NOT exempt -- git_tracked_md() above still
                    # scans it (tracked = off-machine remote = real egress).
                    if fl == CONFIDENTIAL_STAGING_DIRNAME:
                        continue
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
        # 0 active term sequences = every deal genuinely closed, or the terms file
        # degraded above. Either way, the leak MATCHER (word_stream + contains_run)
        # would go fully untested through the whole no-active-deal window -- a silent
        # loss of assurance on this fail-closed boundary. Run a synthetic
        # positive+negative control so the matcher stays regression-tested EVERY run
        # (reusing the synthetic-terms idea from test-confidentiality-guard.py). A
        # planted synthetic term MUST be detected (else the matcher is broken); the
        # synthetic terms MUST be absent from real content (else over-match/collision) --
        # either failure is a hard [MISSING], because it means the leak scan is not
        # actually working.
        warn("confidential-term scan: 0 active term(s) resolved -- no real leak "
             "target this run; running synthetic matcher self-check")
        sc_ok, sc_findings = leak_scan_selfcheck([("CLAUDE.md", text)])
        if sc_ok:
            print("Confidential leak-scan self-check: PASS -- matcher live "
                  "(%d synthetic control term(s), 0 real terms this window)"
                  % len(SYNTHETIC_LEAK_TERMS))
        else:
            for f in sc_findings:
                print("  [MISSING] " + f)
                missing.append(f)

    # --- 9. MEMORY.md index-entry hook length (memory-policy.md sec 3: each index
    # entry is "a one-line description"). WARN-only, mirroring check 7: this ADDS
    # detection, it does not remediate -- an over-long entry is flagged, not edited. ---
    mem_path = overrides.get("memory_index", MEMORY_INDEX_MD)
    mem_text, mem_err = read_optional(mem_path)
    if mem_text is None:
        warn("MEMORY.md index-entry check skipped: %s" % ascii_safe(mem_err))
    else:
        over = []
        for ln_no, ln in enumerate(mem_text.splitlines(), 1):
            m = MEMORY_INDEX_ENTRY_RE.match(ln)
            if m:
                hook_text = ln[m.end():].strip()
                length = len(hook_text)
                if length > MEMORY_INDEX_HOOK_MAXLEN:
                    over.append((ln_no, length))
        print("MEMORY.md index entries with a hook description over %d chars: %d "
              "(memory-policy sec 3: entries are 'a one-line description')"
              % (MEMORY_INDEX_HOOK_MAXLEN, len(over)))
        for ln_no, length in over:
            warn("MEMORY.md index entry at line %d has a %d-char hook description "
                 "(> %d) -- collapse to a one-line pointer; detail belongs in the "
                 "linked file" % (ln_no, length, MEMORY_INDEX_HOOK_MAXLEN))

    # --- 10. session-context.md terseness (header: "keep terse"; volatile
    # current-state layer only -- dated narratives belong in event_log.md). sc_text
    # was loaded once for check 6/7; reuse it. WARN-only (structural hygiene). ---
    if sc_text is None:
        warn("session-context terseness check skipped: %s" % ascii_safe(sc_err))
    else:
        sc_lines = sc_text.splitlines()
        print("session-context.md size: %d lines (warn > %d; per-bullet cap %d words)"
              % (len(sc_lines), SESSION_CONTEXT_MAX_LINES, SESSION_CONTEXT_MAX_BULLET_WORDS))
        if len(sc_lines) > SESSION_CONTEXT_MAX_LINES:
            warn("session-context.md is %d lines (> %d) -- move dated incident "
                 "narratives to event_log.md; this layer is current state only"
                 % (len(sc_lines), SESSION_CONTEXT_MAX_LINES))
        for ln_no, ln in enumerate(sc_lines, 1):
            if BULLET_RE.match(ln):
                wc = len(ln.split())
                if wc > SESSION_CONTEXT_MAX_BULLET_WORDS:
                    warn("session-context bullet at line %d is %d words (> %d) -- reads "
                         "as narrative, not a terse state pointer; move history to "
                         "event_log.md" % (ln_no, wc, SESSION_CONTEXT_MAX_BULLET_WORDS))

    # --- 11. guard liveness (every named guard has a LIVE invocation point) ---
    # THE failure this whole probe exists to catch was itself an orphan: for weeks
    # doctrine-integrity-probe.py had no live runner after its only scheduled trigger
    # was retired on a false rationale, and nothing noticed. Checks 1-4 prove a named
    # guard's FILE exists; none proved it is actually WIRED to run. This closes that
    # gap -- each guard in CLAUDE.md's "Guards:" line must resolve to >=1 live
    # invocation home: (a) a settings.json hook command, (b) a CC/MCP scheduled-task
    # SKILL.md, or (c) the ~/.claude git pre-push shim.
    # WARN-ONLY this rollout, deliberately: checks 9 and 10 (added the same day) both
    # launched "detection first", and check 7 documents the same WARN->fail discipline
    # -- a new structural check earns a hard [MISSING] only after a burn-in with zero
    # false positives, never on day one. Escalate to fail once the wiring is stable.
    # SCOPE: Code surface only (settings.json + the CC/MCP scheduled-tasks tree + the
    # ~/.claude shim). It does NOT reach the OneDrive LAMS fleet -- no other check here
    # does cross-surface scheduler I/O, and widening scope silently would be its own
    # drift. A guard whose ONLY runner is a LAMS task WARNs here; that is a known,
    # accepted Code-surface limitation, not a false positive to engineer around.
    guards_line = next((ln for ln in section.splitlines() if "Guards:" in ln), None)
    if guards_line is None:
        # The line this check audits is absent from the EOS section. Fail-open to a
        # WARN (this rollout is WARN-only; a future burn-in could escalate absence to
        # a hard [MISSING], mirroring check 4's treatment of a vanished section).
        warn("guard-liveness check skipped: no 'Guards:' line in the EOS section")
        print("Guard liveness: 0 guard(s) checked (no 'Guards:' line found)")
    else:
        frag = guards_line.split("Guards:", 1)[1]
        # Cut trailing prose at the sentence terminator so "; all fail open." and any
        # later text on the line never enter the token parse.
        frag = re.split(r";\s*all fail open\.", frag, maxsplit=1)[0]
        # Enumerate guards by EVERY backtick token in the fragment, kept only if it is a
        # bare filename/identifier. This is chosen deliberately over a "split on the
        # middle-dot separator, take the first backtick per entry" parse: a separator
        # that ever drifts (a different dot glyph, a stray one) would SILENTLY drop a
        # guard -- and a dropped guard is exactly the orphan this check must surface, so
        # the extraction's own failure mode must never be "quietly enumerate fewer
        # guards". The shape filter still excludes the only non-guard backtick on the
        # line, eos-plan-gate's `touch hooks/sessions/<id>/override` override recipe
        # (spaces/slashes fail GUARD_NAME_RE). Precision over recall, one exact line.
        guards = [t.strip() for t in GUARD_TOKEN_RE.findall(frag)
                  if GUARD_NAME_RE.match(t.strip())]

        # Build the three invocation-point haystacks, each fail-open. A guard that HITS
        # a readable source resolves regardless; only a ZERO-hit guard is affected by a
        # degraded source, and then it is downgraded to a soft WARN rather than asserted
        # a hard orphan on incomplete visibility (mirrors check 4's `degraded` handling).
        degraded = False

        # (a) settings.json hook command strings (parsed JSON, walked generically).
        hook_cmds = []
        settings_raw, settings_err = read_optional(SETTINGS_JSON)
        if settings_raw is None:
            degraded = True
            warn("guard-liveness: settings.json unreadable (%s) -- hook invocation "
                 "points not checked this run" % ascii_safe(settings_err))
        else:
            try:
                hook_cmds = collect_hook_commands(json.loads(settings_raw))
            except ValueError as e:
                degraded = True
                warn("guard-liveness: settings.json unparseable (%s) -- hook "
                     "invocation points not checked this run" % ascii_safe(e))

        # (b) CC/MCP scheduled-task SKILL.md bodies (non-archived only; Code fleet).
        skill_md_blob = ""
        if not SCHEDULED_TASKS_DIR.is_dir():
            degraded = True
            warn("guard-liveness: scheduled-tasks dir absent (%s) -- SKILL.md "
                 "invocation points not checked this run" % SCHEDULED_TASKS_DIR)
        else:
            for skill_md in sorted(SCHEDULED_TASKS_DIR.glob("*/SKILL.md")):
                if skill_md.parent.name.lower().startswith("_archive"):
                    continue
                body, err = read_optional(skill_md)
                if body is None:
                    warn("guard-liveness: cannot read %s (%s)"
                         % (ascii_safe(skill_md.parent.name + "/SKILL.md"),
                            ascii_safe(err)))
                    continue
                skill_md_blob += "\n" + body

        # (c) the ~/.claude git pre-push shim (doctrine gate + confidentiality scan).
        shim_text, shim_err = read_optional(PREPUSH_SHIM)
        if shim_text is None:
            degraded = True
            warn("guard-liveness: pre-push shim unreadable (%s) -- git-hook "
                 "invocation point not checked this run" % ascii_safe(shim_err))
            shim_text = ""

        print("Guard liveness: %d guard(s) checked" % len(guards))
        for name in guards:
            # Match on the filename STEM (trailing .py/.sh dropped) as a substring.
            # This makes the conceptual-name -> file mapping automatic and table-free:
            # `eos-telemetry` is a substring of the wired `eos-telemetry.py`, and
            # `doctrine-integrity-probe` matches the pre-push shim that names it without
            # the .py. The stems are long, specific, hyphenated names, so a stem
            # substring cannot collide across guards (`eos-plan-gate` is not a substring
            # of `eos-plan-marker` / `eos-gate-sentinel`).
            stem = re.sub(r"\.(py|sh)$", "", name)
            hit = (any(stem in c for c in hook_cmds)
                   or stem in skill_md_blob
                   or stem in shim_text)
            if hit:
                print("  [OK]      %s -> live invocation point found" % ascii_safe(name))
            elif degraded:
                warn("guard '%s' unresolved, but a liveness source was unavailable "
                     "this run (see notes above) -- not asserting orphan"
                     % ascii_safe(name))
            else:
                warn("guard '%s' named in CLAUDE.md's Guards: line has no live "
                     "invocation point found (checked: settings.json hooks, CC/MCP "
                     "scheduled-task SKILL.mds, ~/.claude pre-push shim)"
                     % ascii_safe(name))

    # --- 12. backup-coverage sweep (top-level dirs invisible to the backup) ---
    # Runs live (root = ~/.claude) or on a fixture root via --backup-root=.
    # WARN-only by design: a hit is an opt-in review candidate, not drift --
    # see BACKUP_SWEEP_TRANSIENT_DIRS for rationale and the allowlist contract.
    backup_root = overrides.get("backup_root") or (CLAUDE_DIR if live_mode else None)
    if backup_root is not None:
        sweep_skipped = None
        candidates = []
        try:
            import subprocess
            r = subprocess.run(["git", "-C", str(backup_root), "ls-files", "-z"],
                               capture_output=True, timeout=30)
            if r.returncode != 0:
                sweep_skipped = "git ls-files rc=%d" % r.returncode
            else:
                tracked_top = {p.split("/", 1)[0] for p in
                               r.stdout.decode("utf-8", "replace").split("\0") if p}
                for entry in sorted(Path(backup_root).iterdir(),
                                    key=lambda e: e.name):
                    if not entry.is_dir() or entry.name == ".git":
                        continue
                    if entry.name in tracked_top:
                        continue
                    if entry.name in BACKUP_SWEEP_TRANSIENT_DIRS:
                        continue
                    candidates.append(entry.name)
        except Exception as e:
            sweep_skipped = ascii_safe(e)
        if sweep_skipped is not None:
            warn("backup-coverage sweep skipped -- %s (fail-open; coverage "
                 "not asserted this run)" % ascii_safe(sweep_skipped))
        else:
            print("Backup-coverage sweep: %d opt-in review candidate(s)"
                  % len(candidates))
            for name in candidates:
                warn("top-level dir '%s/' has no git-tracked files and is not on "
                     "the transient allowlist -- invisible to the private-remote "
                     "backup and to git-status single-writer checks; review for a "
                     ".gitignore opt-in (2b/2c/workflows precedent -- scrub for "
                     "confidential terms FIRST) or add it to "
                     "BACKUP_SWEEP_TRANSIENT_DIRS with a reason" % ascii_safe(name))

    # --- 13. declassification-residue sweep (rules.md §7b checklist gap) ---
    # rules.md §7b's checklist item "remove the belt-and-suspenders deal-name
    # reference outright" was missed for CLAUDE.md and its ported copies for 3
    # days after the 2026-07-09 E. Fulton declassification (event_log.md,
    # 2026-07-12 entry) -- nothing re-checked those surfaces because they sit
    # outside the routine memory-file sweep. For every deal in
    # confidential-terms.json explicitly marked active:false (declassified --
    # mirrors term_word_seqs' own default-active convention), scan the probed
    # CLAUDE.md AND every known ported copy (PORTED_CLAUDE_MD_COPIES) for that
    # deal's "always" terms. WARN-only: a declassified deal's name is no longer
    # confidential, so this is a checklist-completeness signal, not a leak
    # (check 8 already hard-fails on ACTIVE-deal terms anywhere).
    ported_copies = (overrides["ported_copies"] if "ported_copies" in overrides
                     else (list(PORTED_CLAUDE_MD_COPIES) if live_mode else []))
    if terms_data is not None and isinstance(terms_data, dict):
        residue_total = 0
        for key, entry in terms_data.items():
            if key.startswith("_") or not isinstance(entry, dict):
                continue
            if entry.get("active") is not False:
                continue  # only EXPLICITLY declassified deals are in scope
            always = [t.lower() for t in entry.get("always", []) if isinstance(t, str)]
            if not always:
                continue
            check_sources = [("CLAUDE.md", text)]
            for copy_path in ported_copies:
                body, err = read_optional(copy_path)
                if body is None:
                    warn("declassification-residue sweep: ported copy unreadable "
                         "(fail-open, not asserted this file) -- %s" % ascii_safe(err))
                    continue
                check_sources.append((str(copy_path), body))
            for label, body in check_sources:
                low = body.lower()
                hits = sorted(set(t for t in always if t in low))
                if hits:
                    residue_total += 1
                    warn("declassified deal '%s' still named in %s (terms: %s) -- "
                         "rules.md 7b requires this reference be removed outright "
                         "(proven miss: E. Fulton lingered in CLAUDE.md 3 days "
                         "post-declassification, event_log.md 2026-07-12)"
                         % (ascii_safe(key), ascii_safe(label), ", ".join(hits[:3])))
        if residue_total == 0:
            print("Declassification-residue sweep: clean (0 hits across "
                  "CLAUDE.md + %d ported cop%s checked)"
                  % (len(ported_copies), "y" if len(ported_copies) == 1 else "ies"))

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
