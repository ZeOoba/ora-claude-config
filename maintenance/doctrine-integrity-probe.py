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
     SKILL.md skill directory on EITHER surface: Code (~/.claude plugins + skills,
     or the ora-skills repo) or Cowork (the OneDrive workspace), or be a genuinely
     plugin-only skill in PLUGIN_SKILL_ALLOWLIST.
     Backup/archive copies are excluded.                                [MISSING -> fail]
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
     > WORD_BUDGET_WARN = AT the consolidation floor -- a nudge,  [WARN only]
     never a cue to trim; see the constants' calibration comment
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
 14. Stage-exclusion four-site sync: the five ratified terminal Stage values
     must be present at all four sites that carry the list --
     ora-deal-command-board STEP 1, ora-deal-aging-sla STEP 1,
     ora-health-guard 4d (all exclusion) and ora-weekly-hygiene   [WARN only]
     check C (the inclusion complement). Value-PRESENCE, not byte-identity:
     the sites legitimately differ in syntax, so a byte compare would fail
     against correct files. Origin: 4d was found carrying three of the five
     on 2026-08-03, enforced until then only by prose in the four files.
     Live-mode only; a site whose SKILL.md is unreadable makes the sweep
     report PARTIAL rather than clean.
     (Checks 12 and 13 are registered in main() but were never added to this
     list -- pre-existing gap, noted 2026-08-12, not fixed here.)
 15. Skill frontmatter-version vs changelog-version drift (2026-08-22): for
     EVERY real skill dir under SKILL_SCAN_ROOTS (not just those named in
     doctrine), extract the skill's own version (body H1 heading marker
     first, else the frontmatter description's trailing 'vX.Y (' token --
     see reference_skill_description_version_extraction_gotcha.md) and the
     top entry under its '## Changelog' heading. Flag a mismatch     [WARN only]
     Fail-open per skill: no H1, no description version, or no Changelog
     section at all just means nothing to compare -- most skills carry no
     changelog section, and that is not itself a finding.

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
# OI-100 (2026-08-05): CLAUDE_DIR above is REASSIGNABLE -- apply_content_root_override()
# repoints it (and the other git-TRACKED-content constants below) at a worktree of the
# commit being pushed, so gate #1 can validate that commit instead of the working tree,
# without ever setting live_mode=False (Trap 1 -- that flag disables 7 unrelated checks).
# LIVE_CLAUDE_DIR is a SEPARATE, NEVER-reassigned alias for the paths that have no
# meaningful "as of this commit" version and must stay pinned to the real install even
# while CLAUDE_DIR is redirected: PREPUSH_SHIM (untracked, not version-controlled, and
# structurally broken under a worktree root -- worktree/.git is a FILE, not the directory
# CLAUDE_DIR/".git"/"hooks" assumes), SESSION_CONTEXT_MD and TERMS_JSON (both gitignored
# -- a worktree of any commit never has them, so redirecting would read "missing" instead
# of the live roster), the plugins/ skill-scan root (locally installed, gitignored), and
# the backup-coverage sweep (its whole point is untracked top-level dirs in the LIVE
# install -- a worktree has none, so redirecting would silently report always-clean).
LIVE_CLAUDE_DIR = CLAUDE_DIR
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
    ".claude", ".firecrawl", ".pytest_cache", ".superpowers", "artifacts",
    "backups", "cache", "daemon", "debug", "downloads", "handoffs", "ide",
    "jobs", "paste-cache", "plans", "plugins", "session-env", "sessions",
    "shell-snapshots", "statsig", "tasks", "telemetry", "todos", "worktrees",
    # append-event-log.py staging (drains into event_log.md; transient by design)
    "_tmp_entries",
    # 2026-08-15 (Gabriel-directed): harness usage telemetry -- per-session facets/
    # + session-meta/ JSON and generated report-*.html. Derived, per-session,
    # regenerable, and machine-local; same class as telemetry/ and sessions/ above.
    # Carries no doctrine, so there is nothing here the private-remote backup needs.
    "usage-data",
    # 2026-08-16 (Gabriel-directed): harness worktree root. Distinct from the
    # "worktrees" entry above -- that one sits under .claude/, this is a sibling
    # top-level dir (config-write-guard.py's token-boundary matcher documents the
    # same two-name distinction). Every child is a git worktree: a checkout of a
    # commit that is already ON the remote, so backing it up stores nothing the
    # backup does not already have, and a worktree of a repo carrying deal terms
    # would drag them off-machine. Transient by construction -- created and
    # removed per feature branch, and empty between them.
    ".claude-worktrees",
    # NEVER track (invariant 3): confidential staging must not reach the remote.
    # daemon/ (above) additionally holds key files -- also never track.
    "_confidential-staging",
    # NEVER track (2026-08-24, recurring WARN since 08-18 per push-fleet-heartbeat.log):
    # .secrets/ holds live credential files (e.g. notion-outreach.token) -- exactly the
    # class this .gitignore's own header rationale names ("this dir mixes secrets... with
    # the config worth tracking") as the reason for its /* default-deny in the first place.
    # A .gitignore opt-in (the sweep's other suggested remediation) is categorically wrong
    # here, not just unratified -- unlike _confidential-staging (deal terms, catastrophic
    # if lost) or session-context.md's roster (see backup-session-context.py), a lost API
    # token is regenerable from its issuing service's own admin UI, so no off-machine
    # mirror is set up for it here; if that stops being true for some future file placed
    # in .secrets/, add the same local-rotation + OneDrive-mirror pattern
    # backup-session-context.py already uses, don't opt the dir into git.
    ".secrets",
}

# Tokens that look like slash commands but resolve via a plugin skill rather than
# a ~/.claude/commands/<name>.md file -> not a command-file MISSING.
SLASH_SKILL_ALLOWLIST = {"code-review"}

# --- Skill check (cross-surface) ---
# Skills span TWO surfaces and CLAUDE.md "Skill precedence" routes across BOTH:
#   Code surface   -> ~/.claude/skills + ~/.claude/plugins + the ora-skills repo
#   Cowork surface -> the OneDrive workspace
# Backup/archive trees are pruned so a deleted skill that lingers only in a backup
# still reports MISSING (correct), and so the live skill is found wherever it sits.
WORKSPACE = HOME / "OneDrive - Oxford Capital Partners" / "Claude_Workspace"
# CLAUDE.md's own "Site repo canon" pointer names this as "ORA-built skills
# source: github.com/ZeOoba/ora-skills" -- the canonical live home for
# ORA-authored Code-surface skills. Most of them ALSO have a Cowork outputs/
# mirror under WORKSPACE (found via that root instead), but a skill that loses
# its mirror -- or never had one -- previously resolved nowhere and false-
# MISSING'd (proven 2026-08-14: register-scheduled-task, whose only copy left
# on disk is C:/Users/Owner/ora-skills/register-scheduled-task/SKILL.md; its
# WORKSPACE mirror survives only under an _archive/ prune). Defined here
# (rather than only at its original IDENTITY_EMITTER_SPECS use below) so both
# checks share one constant instead of two independently-hand-maintained paths.
ORA_SKILLS_ROOT = HOME / "ora-skills"
# plugins/ is gitignored (locally installed, not a repo-content dir) -> pinned to
# LIVE_CLAUDE_DIR always, same reasoning as the other pinned paths above.
SKILL_SCAN_ROOTS = (CLAUDE_DIR / "skills", LIVE_CLAUDE_DIR / "plugins", WORKSPACE,
                     ORA_SKILLS_ROOT)
# ORA's own skill SOURCE repo (CLAUDE.md: "ORA-built skills source: ZeOoba/ora-skills").
# Declared here rather than at its former home further down because SKILL_SCAN_ROOTS
# needs it; the identity-emitter specs below still use the same constant.
ORA_SKILLS_ROOT = HOME / "ora-skills"
# ADDED 2026-08-14 (OI-149, Gabriel-approved): ora-skills was NOT scanned, so any skill
# whose only real dir lives there read as MISSING no matter what. That is what actually
# broke `register-scheduled-task` -- it has a real, current dir at ora-skills/register-
# scheduled-task/. OI-149's filed remedy was to add all three flagged names to
# PLUGIN_SKILL_ALLOWLIST; for THIS one that would have been precisely the masking
# regression the CAUTION above forbids, hiding a resolvable dir behind an allowlist
# entry. The gap was latent for every other ora-skills-only skill too, not just this one.
# Accepted tradeoff, named explicitly: a skill that exists in ora-skills SOURCE but is
# installed on no surface now resolves as present. That is a weaker guarantee than
# before -- source presence is not installed presence -- but it is strictly better than
# the status quo, which was a permanent false MISSING that blocked every push.
SKILL_SCAN_ROOTS = (CLAUDE_DIR / "skills", LIVE_CLAUDE_DIR / "plugins", WORKSPACE,
                    ORA_SKILLS_ROOT)
# Pruned ONLY for correctness (backup/archive copies) and speed (the top-level
# 02_Outputs artifact tree). Resolution is by SKILL.md presence (see
# collect_skill_dirs), which already excludes non-skill junk, so the prune list is
# deliberately minimal. DO NOT add bare "outputs": 01_Workspace/outputs/ is a real
# skill home for several Cowork skills, and pruning it once hid them so they passed
# only via the allowlist (review of c9dcdb9, finding #1).
SKILL_PRUNE_DIRS = {".git", "__pycache__", "node_modules", "third_party", "backups",
                    "_archive", "02_outputs", "_state", "_manifest", ".obsidian"}
# "third_party" added 2026-08-13: LIVE_CLAUDE_DIR/plugins/marketplaces/chrome-devtools-
# plugins bundles a vendored LLVM test-fixture tree (third_party/devtools-frontend/.../
# third_party/llvm/src/clang/test/Driver/Inputs/...) nested deep enough to exceed Windows
# MAX_PATH (260 chars). os.walk's onerror hook was catching 60-140 FileNotFoundError
# [WinError 3] there EVERY run -- 100% deterministic, not the transient "OneDrive offline?"
# case the degraded-scan fallback below was written for -- which set `degraded=True`
# unconditionally and silently downgraded EVERY unresolved skill token file-wide from
# MISSING to a WARN, defeating this check's entire purpose. CORRECTION (independent
# review, 2026-08-13): this prune is NOT a no-op for skill-dir coverage -- unlike
# node_modules, this third_party tree genuinely contains 28 vendored Chromium/DevTools
# SKILL.md dirs (e.g. devtools-ci, gerrit-cli, code-review-workflow) under
# .../third_party/devtools-frontend/.agents/skills/. None are referenced anywhere in
# CLAUDE.md's "Skill precedence" section, so pruning them costs nothing today -- and it
# is the SAFE direction: leaving them scannable would let an ORA token accidentally
# resolve [OK] against an unrelated vendored Chromium dev-workflow skill that merely
# happens to share a name (the same false-PRESENT class the dated-archive-prefix fix
# below guards against), rather than failing closed to MISSING as it now would. If a
# real ORA skill token ever collides with one of these 28 names, this prune is why it
# would report MISSING -- check here first before assuming the skill itself vanished.
# The exact-name set above missed the LIVE archive convention, "_archive_<date>[_suffix]"
# (fixed 2026-07-24, same class as governor-drift-probe's iter_files gap). Four such dirs sit
# under Claude_Workspace/00_Governance/Scheduled/ holding 11 SKILL.md files, so RETIRED skills
# resolved as PRESENT -- exactly defeating this scan's stated intent that "a deleted skill that
# lingers only in a backup still reports MISSING". On a RESOLVER both directions are unsafe:
# an unpruned archive hides retired-skill drift (false negative), and an over-broad prune makes
# a live skill read MISSING (also false negative). So the match requires the "_" separator --
# "_archives_live" and a bare "archive" dir are deliberately NOT pruned.
SKILL_PRUNE_PREFIXES = ("_archive_", "_staging_", "backups_")

def _is_pruned_skill_dir(name):
    low = str(name).lower()
    return low in SKILL_PRUNE_DIRS or low.startswith(SKILL_PRUNE_PREFIXES)
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
# CAUTION (2026-07-21): do NOT add a skill here just because its outputs/ copy looks
# stale -- test_real_doctrine_skills_resolve() deliberately asserts communication-
# intelligence and deal-comparison resolve via a REAL dir, not this list, guarding
# against the exact 2026-06-06 masking regression this list exists to avoid repeating.
# If an outputs/ copy is stale, refresh its content from the ora-skills repo in place
# (see 01_Workspace/_archive/2026-07-21_stale-outputs-skills/ for the audit that found
# 12 stale copies, 2 governor-relevant, and the refreshed-in-place fix) -- don't paper
# over the gap with an allowlist entry.
# EMPTIED 2026-08-05 (automation audit). Two independent reasons the sole remaining
# entry, "re-operations", was dead weight:
#   1. This allowlist is only ever consulted for skills NAMED in CLAUDE.md's "Skill
#      precedence" section. `re-operations` is not named anywhere in CLAUDE.md, so the
#      entry could never be reached.
#   2. Its premise was disproven (reference_skill_surfaces.md): `re-operations` was
#      assumed plugin-only with no local source, but it has a real, current dir at
#      C:/Users/Owner/ora-skills/re-operations/. The `anthropic-skills:` prefix is the
#      generic Code/CLI namespace label for the whole catalog, NOT a plugin-only marker.
# Kept as an empty set rather than deleted: the resolution logic still branches on it,
# and a genuinely plugin-only skill could legitimately need it again. The CAUTION above
# still governs -- do not add an entry to paper over a stale outputs/ copy.
#
# REPOPULATED 2026-08-14 (pre-push gate false failure): "morning" and "schedule" are
# named in CLAUDE.md's Skill tie-breaks section ("the generic `morning` skill", "the
# generic `schedule` skill") purely to say ORA's own skills (daily-brief,
# register-scheduled-task) take precedence over them -- but the generic skills
# themselves are genuine Claude Code built-ins with NO on-disk SKILL.md anywhere:
# verified absent from ~/.claude/skills, ~/.claude/plugins (incl. every installed
# marketplace), the ora-skills repo, and the Cowork WORKSPACE tree. Unlike the
# re-operations case above, there is no real dir to find by widening the scan --
# these ship inside the harness itself, the same class SLASH_SKILL_ALLOWLIST covers
# for slash commands (e.g. code-review). Do not treat their presence here as
# precedent for any *ORA-authored* skill going missing -- verify no real dir exists
# on any surface first, per the CAUTION above.
# REPOPULATED 2026-08-14 (OI-149, Gabriel-approved) with exactly the two names that
# satisfy the CAUTION above -- verified, not assumed. Both were checked against all four
# SKILL_SCAN_ROOTS (including ora-skills, added the same day): neither has a SKILL.md dir
# on ANY of them, so there is no real dir for an entry here to mask. Both are supplied by
# the harness/plugin catalog and are live in the session skill listing.
#   - "morning": Anthropic-provided; CLAUDE.md's morning-brief tie-break names it as the
#     generic fallback that only fires on an explicit /morning (ora-am-brief and
#     daily-brief, its ORA counterparts, DO resolve via real dirs and are not listed).
#   - "schedule": Anthropic-provided; CLAUDE.md's scheduling tie-break names it only to
#     ROUTE AWAY from it ("never the generic `schedule` skill"). It is referenced
#     precisely so the doctrine can forbid it, which is still a reference the probe must
#     be able to resolve.
# The third name flagged with these two, `register-scheduled-task`, is deliberately NOT
# here: it has a real dir at ora-skills/register-scheduled-task/ and now resolves through
# the scan. Adding it would have been the masking regression the CAUTION describes.
PLUGIN_SKILL_ALLOWLIST: set[str] = {"morning", "schedule"}

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
# SESSION_CONTEXT_MD/TERMS_JSON pinned to LIVE_CLAUDE_DIR -- both gitignored, so a
# worktree of any commit never has them (see the OI-100 note at LIVE_CLAUDE_DIR's
# definition above).
SESSION_CONTEXT_MD = LIVE_CLAUDE_DIR / "session-context.md"
RULES_MD = MEMORY_DIR / "rules.md"
TERMS_JSON = LIVE_CLAUDE_DIR / "hooks" / "confidential-terms.json"
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
# Pinned to LIVE_CLAUDE_DIR, not CLAUDE_DIR: the shim is NOT version-controlled (see its
# own docstring) and hooks/ live in the git COMMON dir, shared across every worktree --
# under a worktree root, "<worktree>/.git" is a FILE (gitlink), not a directory, so
# CLAUDE_DIR-relative would silently resolve to a path that can never exist.
PREPUSH_SHIM = LIVE_CLAUDE_DIR / ".git" / "hooks" / "pre-push"
# 2026-08-05: the PreToolUse Edit/Write chain moved in-process. Four guards
# (eos-plan-gate, shared-checkout-guard, eos-claude-md-guard, rules-md-guard) lost
# their settings.json entries entirely and now run only via the dispatcher's
# GUARD_CHAIN -- invisible to sources (a)-(c), so this check called a live guard an
# orphan. Parse the LIST LITERAL, not the file text: the dispatcher's docstring names
# all four in prose, so a whole-file substring match would hand out OKs for guards
# that are merely mentioned. A false OK is strictly worse than a false WARN here --
# it is exactly the orphan this check exists to catch.
PRETOOLUSE_DISPATCHER = CLAUDE_DIR / "hooks" / "pretooluse-dispatcher.py"
GUARD_CHAIN_RE = re.compile(r"^GUARD_CHAIN\s*=\s*\[(.*?)\]", re.S | re.M)
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
            # Honours the caller's exact-name `prune` set AND the module-level dated-archive
            # prefixes (see SKILL_PRUNE_PREFIXES) -- the latter are a property of the on-disk
            # naming convention, not of any one caller's set.
            dirnames[:] = [d for d in dirnames
                           if d.lower() not in prune
                           and not d.lower().startswith(SKILL_PRUNE_PREFIXES)]
            if "SKILL.md" in filenames:
                names.add(os.path.basename(dirpath).lower())
    return names, errs, absent_roots


# --- Check 15 (2026-08-22): skill frontmatter-version vs changelog-version
# drift. See reference_skill_description_version_extraction_gotcha.md -- a
# bare 'vX.Y' in a skill's frontmatter description is not reliably the FILE
# version (a sub-component/schema version, or a superseded entry stacked
# ahead of the true current one, can also match 'vX.Y('). That memory's rule:
# prefer the body H1 heading's version marker; only fall back to the
# frontmatter description's trailing 'vX.Y (' token when no H1 marker exists.
# A skill whose own version and its changelog's TOP entry disagree is exactly
# the drift a recent case (deal-retirement, 2026-07-21) caught only by hand --
# this makes it a daily probe finding instead.
H1_VERSION_RE = re.compile(r"^#\s.*\(v(\d+\.\d+(?:\.\d+)?)\b", re.M)
DESC_VERSION_RE = re.compile(r"\bv(\d+\.\d+(?:\.\d+)?)\s*\(")
CHANGELOG_HEADER_RE = re.compile(r"^##\s+Changelog\s*$", re.M | re.I)
# Matches only a changelog BULLET's leading version tag ("- v1.1 (date): ..." or
# "- **v1.2 (date):** ...") -- not any vX.Y mentioned mid-sentence. Confirmed
# necessary against live content: communication-intelligence's own v1.3 entry
# reads "...same fix applied to `tenant-email` v1.1, the higher-volume..." --
# a naive whole-line/whole-section search would pick up that cross-reference's
# v1.1 as if it were one of THIS skill's own changelog entries.
CHANGELOG_ENTRY_LEAD_VERSION_RE = re.compile(r"^\s*-\s*\**v(\d+\.\d+(?:\.\d+)?)\b", re.M)


def collect_skill_md_paths(roots, prune):
    """{name: SKILL.md path} for every real skill dir under `roots`, mirroring
    collect_skill_dirs's walk/prune logic (same SKILL.md-presence match, same
    prune set + SKILL_PRUNE_PREFIXES) but keeping the path instead of
    discarding it -- needed here to read content for the version/changelog
    drift check. First match wins if the same name resolves under more than
    one root (mirrors collect_skill_dirs's name-only dedup)."""
    out = {}
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames
                           if d.lower() not in prune
                           and not d.lower().startswith(SKILL_PRUNE_PREFIXES)]
            if "SKILL.md" in filenames:
                name = os.path.basename(dirpath).lower()
                out.setdefault(name, os.path.join(dirpath, "SKILL.md"))
    return out


def extract_frontmatter_description(text):
    """The frontmatter 'description:' field's value (the `---`-fenced block at
    file top), or None if absent/unparseable. Deliberately simple -- reads
    only the opening line of the value, which is enough to find a trailing
    'vX.Y (' token; this is not a YAML parser."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    dm = re.search(r"^description:\s*(.+)$", m.group(1), re.M)
    return dm.group(1).strip() if dm else None


def extract_skill_own_version(text):
    """The skill's own version per reference_skill_description_version_
    extraction_gotcha.md: the body H1 heading's '(vX.Y...)' marker FIRST;
    only when no H1 marker exists, fall back to the frontmatter description's
    trailing 'vX.Y (' token. None if neither is present. Pure."""
    h1 = H1_VERSION_RE.search(text)
    if h1:
        return h1.group(1)
    desc = extract_frontmatter_description(text)
    if desc:
        dm = DESC_VERSION_RE.search(desc)
        if dm:
            return dm.group(1)
    return None


def extract_changelog_top_version(text):
    """The HIGHEST version tagged on a changelog bullet under a '## Changelog'
    heading, or None if there is no Changelog section or no bullet in it
    carries a leading vX.Y tag.

    Deliberately NOT "the first bullet's version": ORA skills are not
    consistently ordered newest-first -- confirmed live against
    communication-intelligence, whose Changelog lists v1.1/v1.2/v1.3 in
    ascending (oldest-first) order, which would make a first-line read
    report the true-current v1.3 skill as a false v1.1-vs-v1.3 mismatch.
    Comparing all bullet versions numerically (each dotted segment as an
    int, so v1.10 correctly outranks v1.9) and taking the max is ordering-
    agnostic. Pure."""
    hm = CHANGELOG_HEADER_RE.search(text)
    if not hm:
        return None
    rest = text[hm.end():]
    nh = NEXT_HEADER_RE.search(rest)
    section = rest[:nh.start()] if nh else rest
    versions = [m.group(1) for m in CHANGELOG_ENTRY_LEAD_VERSION_RE.finditer(section)]
    if not versions:
        return None
    return max(versions, key=lambda v: tuple(int(p) for p in v.split(".")))


def check_skill_version_changelog_drift(name, text):
    """Return a finding string if `name`'s own version (H1-first, else
    frontmatter description) diverges from its changelog's top-entry version.
    None when either side is unresolvable -- fail-open, since most skills
    carry no changelog section at all -- or the two already agree. Pure."""
    own = extract_skill_own_version(text)
    top = extract_changelog_top_version(text)
    if own is None or top is None or own == top:
        return None
    return ("%s: frontmatter/H1 version v%s does not match changelog top "
            "entry v%s -- one was bumped without the other" % (name, own, top))


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


# Builtin tool names an agent may legitimately grant. Used ONLY to raise a WARN on a
# name nothing recognises -- never to hard-fail. A hardcoded roster like this goes stale
# the moment the harness adds a tool, and a stale allowlist inside a BLOCKING pre-push
# gate is itself the false-positive class this check exists to prevent. Anything
# 'mcp__*'-prefixed, or the '*' wildcard, is accepted without membership.
AGENT_BUILTIN_TOOLS = {
    "read", "write", "edit", "notebookedit", "grep", "glob", "bash", "bashoutput",
    "killshell", "websearch", "webfetch", "task", "agent", "todowrite", "skill",
    "slashcommand", "exitplanmode", "artifact", "sendusermessage", "senduserfile",
}


def check_agent_definitions(agents_dir):
    """Strict-validate every agents/*.md definition. Returns (hard_failures, warnings).

    Exists because check 14 resolves agent tokens through collect_flat_names(), which
    reads FILENAMES only and never opens the file -- so a definition whose frontmatter
    cannot parse (which silently unregisters the agent) resolved as [OK]. Proven
    2026-09-10: five deliberately-broken definitions passed the gate at exit 0, while
    DELETING a referenced agent correctly exited 1.

    Hard failures (blocking) are limited to unambiguous, self-evident defects: absent
    frontmatter, unparseable YAML, name/filename-stem mismatch, duplicate name. Anything
    requiring a maintained roster to judge is a WARN. Fails open on an absent directory
    or an unreadable file, matching the rest of this probe.
    """
    failures, warnings = [], []
    if not Path(agents_dir).is_dir():
        return failures, warnings

    try:
        import yaml  # optional; this probe is otherwise stdlib-only
    except ImportError:
        yaml = None

    try:
        names = sorted(fn for fn in os.listdir(agents_dir) if fn.lower().endswith(".md"))
    except OSError as exc:
        warnings.append("agents dir unreadable (%s) -- validation skipped"
                        % ascii_safe(exc))
        return failures, warnings

    if names and yaml is None:
        warnings.append("PyYAML unavailable -- agent frontmatter checked structurally "
                        "only (fence + name), not parsed strictly")

    seen = {}
    for fn in names:
        path = os.path.join(agents_dir, fn)
        stem = fn[:-3]
        try:
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
        except OSError as exc:
            warnings.append("%s unreadable (%s)" % (ascii_safe(fn), ascii_safe(exc)))
            continue

        if not text.startswith("---"):
            failures.append("%s: no frontmatter block (must open with '---')" % fn)
            continue
        end = text.find("\n---", 3)
        if end == -1:
            failures.append("%s: frontmatter block is never closed" % fn)
            continue
        block = text[3:end]

        if yaml is not None:
            try:
                meta = yaml.safe_load(block)
            except yaml.YAMLError as exc:
                first = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
                failures.append("%s: frontmatter fails strict YAML parse (%s)"
                                % (fn, ascii_safe(first)))
                continue
            if not isinstance(meta, dict):
                failures.append("%s: frontmatter is not a mapping" % fn)
                continue
            name = meta.get("name")
            tools_raw = meta.get("tools")
        else:
            m = re.search(r"^name:\s*(.+?)\s*$", block, re.M)
            name = m.group(1).strip("'\"") if m else None
            tm = re.search(r"^tools:\s*(.+?)\s*$", block, re.M)
            tools_raw = tm.group(1) if tm else None

        if not isinstance(name, str) or not name.strip():
            failures.append("%s: frontmatter has no usable 'name'" % fn)
            continue
        name = name.strip()
        if name.lower() != stem.lower():
            failures.append("%s: name '%s' does not match filename stem '%s'"
                            % (fn, ascii_safe(name), stem))
        if name.lower() in seen:
            failures.append("duplicate agent name '%s' in %s and %s"
                            % (ascii_safe(name), seen[name.lower()], fn))
        else:
            seen[name.lower()] = fn

        if isinstance(tools_raw, str):
            for tool in (t.strip() for t in tools_raw.split(",")):
                if not tool or tool == "*" or tool.lower().startswith("mcp__"):
                    continue
                if tool.lower() not in AGENT_BUILTIN_TOOLS:
                    warnings.append("%s: grants unrecognised tool '%s' (allowlist may "
                                    "simply be stale -- verify before acting)"
                                    % (fn, ascii_safe(tool)))

    return failures, warnings


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


# Check 13 extension (2026-07-16): rules.md 7b's checklist has 6 items; the
# original check 13 covers only the ONE item (CLAUDE.md + ported copies) that
# caused the proven E. Fulton miss. The other 4 file-level items --
# session-context.md, projects.md, MEMORY.md, firm.md -- legitimately still
# MENTION a declassified deal after the checklist runs (only the CONFIDENTIAL
# markers should be gone, per the checklist's own "dropped [CONFIDENTIAL],
# removed 'must never appear externally' language" wording from the real
# E. Fulton fix, event_log.md). So this extension does NOT flag every mention
# of a declassified deal in these files (that would be noisy and wrong --
# these files are SUPPOSED to keep discussing the deal, just without the
# confidentiality tags) -- it flags a declassified deal's term co-occurring
# with a leftover confidentiality MARKER within a small line window, which is
# the specific defect class the checklist exists to prevent.
DECLASSIFICATION_MARKER_TOKENS = ("[confidential]", "(confidential",
                                  "must never appear externally")
DECLASSIFICATION_RESIDUE_WINDOW = 3  # lines; markdown entries often span 2-3 lines


def find_marker_residue(text, always_terms, window=DECLASSIFICATION_RESIDUE_WINDOW):
    """{(term, marker): first 1-indexed line_no} for every place a declassified
    deal's term and a confidentiality marker token both appear within `window`
    consecutive lines of each other. Line-windowed (not whole-file) so a marker
    used for a DIFFERENT, still-active deal elsewhere in a multi-deal roster
    file doesn't false-positive against an unrelated declassified deal."""
    lowered_lines = [ln.lower() for ln in text.splitlines()]
    hits = {}
    for i in range(len(lowered_lines)):
        window_text = "\n".join(lowered_lines[i:i + window])
        for term in always_terms:
            if term not in window_text:
                continue
            for marker in DECLASSIFICATION_MARKER_TOKENS:
                if marker in window_text:
                    key = (term, marker)
                    hits.setdefault(key, i + 1)
    return hits


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
        elif a.startswith("--roster-files="):
            v = a.split("=", 1)[1]
            overrides["roster_files"] = [Path(p) for p in v.split(",") if p]
        elif a.startswith("--live-root="):
            # OI-100: redirect the git-TRACKED-content roots (CLAUDE.md, commands/,
            # agents/, workflows/, skills/, memory/, settings.json, scheduled-tasks/,
            # hooks/pretooluse-dispatcher.py) at this directory -- typically a
            # `git worktree add --detach` checkout of the commit about to be pushed --
            # WITHOUT setting live_mode=False. See apply_content_root_override().
            overrides["live_root"] = Path(a.split("=", 1)[1])
        elif a.startswith("--"):
            # A typo'd flag must not silently become the CLAUDE.md path (which
            # would also disable live-mode scanning). Fail loud.
            print("[MISSING] unknown option: %s (known: --session-context= "
                  "--rules= --terms= --quick --memory-index= --backup-root= "
                  "--ported-copies= --roster-files= --live-root=)" % ascii_safe(a))
            sys.exit(1)
        else:
            pos.append(a)
    return pos, overrides


# --- Check 12 (2026-07-16): ora-am-brief SOFR-narration guardrail presence.
# Defect (event_log.md 2026-07-16): ora-am-brief Block A narrated the freshness
# of the SOFR 30/90/180-day averages / Index in its degraded-status callout --
# fields OWNED by the separate CC/MCP task ora-sofr-direct-prefetch, not by this
# task -- so the header rotted the instant that task patched the page (and under
# a catch-up burst the two can fire in either order). The fix installed a literal
# CALLOUT TEMPLATE (with the SOFR-average clause deliberately ABSENT) plus a
# CALLOUT SCOPE hard rule. This check asserts BOTH guardrails still exist in the
# SKILL.md so a later edit cannot silently strip them.
#
# Why this is a fix-PRESENCE check, not an anti-pattern grep: the hard rule
# legitimately QUOTES the forbidden phrases ("carried forward", "SOFR ... Index")
# in order to forbid them, so a co-occurrence scan would flag the very fix that
# prevents the defect. Narrow by design -- one task, WARN-only, fail-open.
# Repointed 2026-07-16: ora-am-brief migrated LAMS/Cowork -> CC/MCP (LAMS sandbox
# had no local COM, so its email leg structurally couldn't send -- event_log.md
# 2026-07-16 "RATIFIED: LAMS ora-am-brief retired"). The retired LAMS folder was
# archived to Documents\Claude\Scheduled\_archive_2026-07-16_retired-to-ccmcp\ and
# is no longer live; all 3 sentinels verified present in the CC/MCP copy (carried
# over verbatim from the LAMS spec) before repointing. ---
# Rebased onto CLAUDE_DIR (was a standalone HOME-derived constant) so OI-100's
# apply_content_root_override() can redirect it too -- it is tracked content
# (scheduled-tasks/ora-am-brief/SKILL.md) checked only in live_mode, so it should
# validate the commit being pushed, same as SCHEDULED_TASKS_DIR/SETTINGS_JSON.
AM_BRIEF_SKILL = CLAUDE_DIR / "scheduled-tasks" / "ora-am-brief" / "SKILL.md"
AM_BRIEF_SENTINELS = (
    "CALLOUT TEMPLATE (assemble",
    "There is deliberately NO clause for the SOFR 30/90/180-day averages",
    "CALLOUT SCOPE (hard rule)",
)


# --- Check 13 (2026-08-03 extension): doctrine-vs-deliverable identity drift.
# Defect (event_log.md 2026-08-03): CLAUDE.md's Identity line said "Principal"
# while 38 .docx deliverables, three ora-skills sources, and
# build_t1_letterpack.py's OUTBOUND owner-letter signature block all said "VP
# Acquisitions". Two contradictory ratified rulings (2026-06-10 and 2026-07-08)
# coexisted for nearly two months and no guard noticed, because nothing compared
# the doctrine file against what deliverables actually emit. A title in CLAUDE.md
# is not self-enforcing.
#
# Scope is EMITTERS, not artifacts: templates, SKILL.mds and document generators
# -- the things that produce NEW paper. Historical .docx deliverables are
# deliberately out of scope per Gabriel's 2026-08-03 "live sources only" ruling;
# they are dated records and rewriting them would falsify the archive.
#
# WARN-only and fail-open, like the other sweeps: a missing tree or an unreadable
# file must never fail the probe. ---
IDENTITY_NAME = "Gabriel Goldberg"
IDENTITY_LINE_RE = re.compile(
    re.escape(IDENTITY_NAME) + r",\s*([^,\n]+?),\s*Oxford Realty Advisors")

# Surface renderings, longest first so "vice president, acquisitions" wins over
# the "principal"-style short keys and over its own prefixes.
IDENTITY_TITLE_SURFACES = (
    "vice president of acquisitions",
    "vice president, acquisitions",
    "vice president acquisitions",
    "vp of acquisitions",
    "vp acquisitions",
    "co-principal",
    "principal",
    "founder",
)
IDENTITY_TITLE_KEYS = {
    "vice president of acquisitions": "VP-ACQUISITIONS",
    "vice president acquisitions": "VP-ACQUISITIONS",
    "vp of acquisitions": "VP-ACQUISITIONS",
    "vp acquisitions": "VP-ACQUISITIONS",
    "co-principal": "CO-PRINCIPAL",
    "principal": "PRINCIPAL",
    "founder": "FOUNDER",
}
# Characters that may sit between the name and its title (markdown emphasis,
# dashes, bullets, quotes, parens) and be skipped.
_IDENT_SEP = " \t\"'*_|:,-—–·•()\r\n"
_QUOTED_LITERAL_RE = re.compile(r'"([^"\n]{1,120})"|\'([^\'\n]{1,120})\'')

# ORA_SKILLS_ROOT is defined earlier, alongside SKILL_SCAN_ROOTS (the skill-scan
# root list this same path was added to 2026-08-14) -- reused here rather than
# redefined so the two checks can't drift onto different paths.
# (ORA_SKILLS_ROOT is declared up beside SKILL_SCAN_ROOTS, which needs it -- 2026-08-14.)
# Document generators live beside the deal data they draw on, not in a repo.
OUTREACH_GENERATOR_DIR = (HOME / "OneDrive - Oxford Capital Partners"
                          / "Business" / "Investment Candidates -- 2026")
IDENTITY_EMITTER_SPECS = (
    (ORA_SKILLS_ROOT, "*/SKILL.md"),
    (ORA_SKILLS_ROOT / "cowork-settings" / "templates", "*.md"),
    (OUTREACH_GENERATOR_DIR, "*.py"),
)
# Version snapshots and archives are historical record, not live emitters.
IDENTITY_PRUNE_PARTS = ("_archive", "versions", "__pycache__", ".git")

# (label, line marker) pairs whose title assertion is NOT a firm-title claim.
# Scoped to the LINE, never the whole file, so any other drift in the same
# emitter is still reported.
IDENTITY_ASSERTION_EXEMPTIONS = (
    # document-assembly's signing-authority rule states the capacity in which
    # Gabriel binds an LLC ("Member"), not his title at the firm. Signing
    # capacity is a legal question -- "Principal" is a more standard capacity in
    # an entity signature block than a departmental title, and getting it wrong
    # bears on whether a signature binds. Gabriel ruled 2026-08-03 to leave the
    # line as-is; exempted here rather than left as a standing WARN that would
    # train the reader to ignore this check.
    ("document-assembly/SKILL.md", "Signing authority:"),
    # The explanatory comment for the exemption above (the line directly below
    # "Signing authority:") illustrates the SAME ruling with a second worked
    # example -- the 21 Outlook landlord signatures, "...Gabriel Goldberg,
    # Principal" -- on a DIFFERENT line, so the line-scoped rule above does not
    # cover it. That left the comment EXPLAINING a known false positive as a
    # second false positive of its own (found 2026-08-03 by running this probe
    # live against the real file, right after the signing-authority line was
    # first exempted). Scoped to this specific explanatory line, not the whole
    # file, for the same reason as the entry above.
    ("document-assembly/SKILL.md", 'DO NOT "correct" this to "VP Acquisitions"'),
)


def normalize_title(s):
    """Fold a title rendering to a stable key, or None if unrecognised.
    'VP Acquisitions', 'Vice President, Acquisitions' and 'vice  president of
    acquisitions' are the SAME title -- without this the probe would report
    build_t1_letterpack.py as drifting from CLAUDE.md when it agrees."""
    if not s:
        return None
    t = s.strip().strip('"\'').strip()
    t = t.replace("—", " ").replace("–", " ")
    t = re.sub(r"^[\*_]+|[\*_]+$", "", t)
    t = re.sub(r"[,.;:]+$", "", t)
    t = t.replace(",", " ")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return IDENTITY_TITLE_KEYS.get(t)


def canonical_identity_title(text):
    """The title CLAUDE.md's Identity line asserts, as a key (None if absent)."""
    m = IDENTITY_LINE_RE.search(text)
    return normalize_title(m.group(1)) if m else None


def _title_at_start(rem):
    """If `rem` BEGINS with a title surface used as a title, return (surface,key).

    The terminator rule is what keeps 'principal' -- an ordinary finance word --
    from registering: a real assertion is followed by end-of-line or punctuation
    ('Principal (Cornell, economics)', 'VP Acquisitions, Oxford...'), whereas
    prose continues in lowercase ('principal balance was written down')."""
    s = re.sub(r"[ \t]+", " ", rem).lstrip(_IDENT_SEP)
    # Compound roles ("Member / Principal", "Manager / VP Acquisitions") state the
    # title in the tail. Try the whole string first, then after each leading
    # "<word> /" segment, so document-assembly's signing-authority line is seen.
    candidates = [s]
    tail = s
    for _ in range(3):
        mm = re.match(r"[A-Za-z]+\s*/\s*", tail)
        if not mm:
            break
        tail = tail[mm.end():]
        candidates.append(tail)
    for cand in candidates:
        low = cand.lower()
        for surf in IDENTITY_TITLE_SURFACES:
            if not low.startswith(surf):
                continue
            rest = cand[len(surf):].lstrip()
            if not rest or not rest[0].islower():
                return surf, IDENTITY_TITLE_KEYS[surf]
            # "Principal at Oxford Realty Advisors" is an assertion; "principal
            # of the loan" is not. The preposition alone cannot tell them apart
            # -- what follows it can: a proper noun means an employer.
            pm = re.match(r"(at|of|for|with)\s+(\S+)", rest)
            if pm and pm.group(2)[:1].isupper():
                return surf, IDENTITY_TITLE_KEYS[surf]
    return None


def scan_title_assertions(text):
    """Return [(lineno, surface, key)] where `text` asserts a title for Gabriel.

    Two shapes, because the real defects took both forms:
      A. same line  -- '**Owner:** Gabriel Goldberg, VP Acquisitions'
      B. adjacent quoted literals -- a generator's signature block, where the
         name and the title are separate string literals on separate lines.
    Line reported is the TITLE's, since that is the token a fix edits."""
    hits, seen = [], set()
    for i, line in enumerate(text.splitlines(), 1):
        pos = line.find(IDENTITY_NAME)
        if pos < 0:
            continue
        got = _title_at_start(line[pos + len(IDENTITY_NAME):])
        if got and (i, got[1]) not in seen:
            seen.add((i, got[1]))
            hits.append((i, got[0], got[1]))

    literals = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in _QUOTED_LITERAL_RE.finditer(line):
            literals.append((i, (m.group(1) or m.group(2)).strip()))
    for idx, (line_no, lit) in enumerate(literals[:-1]):
        if lit != IDENTITY_NAME:
            continue
        nline, nlit = literals[idx + 1]
        # A signature block puts the name and the title on SEPARATE lines. Two
        # quoted strings on ONE line are prose -- e.g. a changelog documenting
        # this very kind of fix ('signed "Gabriel Goldberg" ... as "Principal"'),
        # which otherwise makes the record of the fix trip the check.
        if nline == line_no:
            continue
        key = normalize_title(nlit)
        if key and (nline, key) not in seen:
            seen.add((nline, key))
            hits.append((nline, nlit.strip(), key))
    return sorted(hits)


def check_identity_drift(canonical_key, sources):
    """sources = [(label, text)]. Return one finding per source asserting a title
    that conflicts with `canonical_key`. Reports EVERY conflicting source, not
    just the first -- 38 drifted at once, and a first-hit-only report would let
    the rest survive a 'fixed it' claim."""
    if not canonical_key:
        return []
    out = []
    for label, text in sources:
        lines = text.splitlines()
        bad = set()
        for ln, surf, key in scan_title_assertions(text):
            if key == canonical_key:
                continue
            src = lines[ln - 1] if 0 < ln <= len(lines) else ""
            if any(lbl == label and mark in src
                   for lbl, mark in IDENTITY_ASSERTION_EXEMPTIONS):
                continue
            bad.add((ln, surf, key))
        bad = sorted(bad)
        if bad:
            where = ", ".join("line %d: %r" % (ln, surf) for ln, surf, _ in bad[:3])
            extra = "" if len(bad) <= 3 else " (+%d more)" % (len(bad) - 3)
            out.append("%s asserts %s -- %s%s"
                       % (label, "/".join(sorted({k for _, _, k in bad})),
                          where, extra))
    return out


def collect_identity_emitters():
    """(label, text) for every live emitter that is readable. Fail-open: an
    absent tree (e.g. OneDrive not synced on this machine) yields nothing."""
    out = []
    for root, pattern in IDENTITY_EMITTER_SPECS:
        try:
            if not root.is_dir():
                continue
            for p in sorted(root.glob(pattern)):
                if any(part in IDENTITY_PRUNE_PARTS for part in p.parts):
                    continue
                try:
                    # parent/name -- bare "SKILL.md" is ambiguous across ~50 skills.
                    label = "%s/%s" % (p.parent.name, p.name)
                    out.append((label, p.read_text(encoding="utf-8",
                                                   errors="replace")))
                except Exception:
                    continue
        except Exception:
            continue
    return out


# --- Check 14 (2026-08-12): four-site stage-exclusion list sync. -----------
# The five terminal Stage values were ratified 2026-07-27 and extended to
# ora-health-guard block 4d on 2026-08-03, when 4d was found carrying only
# THREE of the five. The "all four sites stay identical" rule is stated only in
# prose inside the four SKILL.mds; no guard enforced it and the gap survived
# weeks. This is that guard.
#
# The assertion is value-PRESENCE, not byte-identity. The four sites
# legitimately differ in syntax -- 4d spaces its commas, and ora-weekly-hygiene
# states the same five as an INCLUSION list in backticked prose (it is the
# complement check) -- so a byte comparison would fail against correct files on
# day one. Matching the em-dash literally is load-bearing: the doctrine warns
# that a hyphen silently fails the string comparison, so a hyphenated site
# reports as missing, which is exactly the desired behaviour.
STAGE_TERMINAL_VALUES = (
    "Closed Won",
    "Passed",
    "Killed",
    "Killed — Reneg Only",
    "Killed — Note/Short-Sale in Discussion",
)
STAGE_EXCLUSION_SITES = (
    ("ora-deal-command-board", "STEP 1"),
    ("ora-deal-aging-sla", "STEP 1"),
    ("ora-health-guard", "block 4d"),
    ("ora-weekly-hygiene", "check C (inclusion complement)"),
)


def check_stage_exclusion_sync(sources):
    """sources = [(label, text)]. Every site must carry all five canonical
    terminal-stage values in quoted form. Returns one finding per site with a
    gap -- EVERY such site, not just the first, for the same reason
    check_identity_drift reports them all: a first-hit-only report lets the
    remainder survive a 'fixed it' claim."""
    out = []
    for label, text in sources:
        missing = [v for v in STAGE_TERMINAL_VALUES if ("'%s'" % v) not in text]
        if missing:
            out.append("%s missing %d of %d: %s"
                       % (label, len(missing), len(STAGE_TERMINAL_VALUES),
                          ", ".join(missing)))
    return out


def collect_stage_exclusion_sites():
    """(label, text) for each of the four SKILL.mds that is readable. Fail-open
    per file: an absent/unreadable file is SKIPPED rather than reported as
    'missing all five'. An absent SKILL.md is a different problem (check 2's
    territory) and reporting it as stage drift would be an inferred null. The
    caller compares the returned count against STAGE_EXCLUSION_SITES and warns
    on a partial sweep, so a skip can never read as clean."""
    out = []
    for name, _where in STAGE_EXCLUSION_SITES:
        p = SCHEDULED_TASKS_DIR / name / "SKILL.md"
        try:
            if p.is_file():
                out.append((name, p.read_text(encoding="utf-8",
                                              errors="replace")))
        except Exception:
            continue
    return out


def check_am_brief_sofr_guardrail(text):
    """Return the list of guardrail sentinels ABSENT from the SKILL.md text
    (empty == guardrail intact). Pure over text so it is unit-testable without
    the cloud read."""
    return [s for s in AM_BRIEF_SENTINELS if s not in text]


def check_worktree_baseref(settings_obj):
    """Return a WARN message if settings.json's worktree.baseRef isn't the
    ratified "head" (None if compliant). Pure over the parsed settings.json
    object so it is unit-testable without a live file.

    2026-08-05: EnterWorktree's worktree.baseRef governs which commit a new
    worktree branches from. Unset (or "fresh") branches from
    origin/<default-branch>, silently dropping local-ahead-of-origin commits --
    the routine state of this repo's main (frequent local commits, infrequent
    pushes; same pattern in ora-skills and oxford-command-center). Gabriel
    ratified "head" as the standing default (event_log.md, 2026-08-05)."""
    wt = settings_obj.get("worktree")
    base_ref = wt.get("baseRef") if isinstance(wt, dict) else None
    if base_ref == "head":
        return None
    if base_ref is None:
        return ("worktree.baseRef is unset in settings.json (defaults to "
                "\"fresh\" -- branches new worktrees from origin/<default-branch>, "
                "silently dropping local-ahead-of-origin commits). Ratified "
                "default is \"head\" (event_log.md, 2026-08-05).")
    return ("worktree.baseRef=%r in settings.json, expected \"head\" (branches "
            "new worktrees from origin/<default-branch> instead of local HEAD -- "
            "silently drops local-ahead-of-origin commits). Ratified default is "
            "\"head\" (event_log.md, 2026-08-05)." % (base_ref,))


def apply_content_root_override(root):
    """OI-100: redirect every git-TRACKED-content path constant at `root` (normally a
    `git worktree add --detach` checkout of the commit about to be pushed), leaving
    live_mode untouched (the caller sets it separately) and leaving every PINNED
    constant (LIVE_CLAUDE_DIR itself, and everything already defined in terms of it --
    SESSION_CONTEXT_MD, TERMS_JSON, PREPUSH_SHIM, the plugins/ skill-scan root) alone.

    Reassigns module GLOBALS rather than threading a root parameter through every check
    function: every call site below reads these names at call time (verified -- none is
    captured as a function-default value, which binds at def time and would freeze the
    pre-override value), so reassigning here, before any check runs, is sufficient and
    keeps this a small, auditable, single-purpose change instead of a call-site rewrite
    across the whole file.

    Deliberately narrow -- do NOT add REPO_ROOT, WORKSPACE, PORTED_CLAUDE_MD_COPIES, or
    ORA_SKILLS_ROOT/OUTREACH_GENERATOR_DIR here: those name genuinely separate repos or
    cross-surface (OneDrive/Cowork) locations with no version inside THIS repo's commits
    -- redirecting them would just make them resolve against unrelated content."""
    global CLAUDE_DIR, COMMANDS_DIR, MEMORY_DIR, RULES_MD, MEMORY_INDEX_MD
    global AGENTS_DIR, WORKFLOWS_DIR, SETTINGS_JSON, SCHEDULED_TASKS_DIR
    global PRETOOLUSE_DISPATCHER, SKILL_SCAN_ROOTS, AM_BRIEF_SKILL
    CLAUDE_DIR = root
    COMMANDS_DIR = root / "commands"
    MEMORY_DIR = (root / "projects"
                  / "C--Users-Owner-OneDrive---Oxford-Capital-Partners" / "memory")
    RULES_MD = MEMORY_DIR / "rules.md"
    MEMORY_INDEX_MD = MEMORY_DIR / "MEMORY.md"
    AGENTS_DIR = root / "agents"
    WORKFLOWS_DIR = root / "workflows"
    SETTINGS_JSON = root / "settings.json"
    SCHEDULED_TASKS_DIR = root / "scheduled-tasks"
    PRETOOLUSE_DISPATCHER = root / "hooks" / "pretooluse-dispatcher.py"
    AM_BRIEF_SKILL = root / "scheduled-tasks" / "ora-am-brief" / "SKILL.md"
    SKILL_SCAN_ROOTS = (root / "skills", LIVE_CLAUDE_DIR / "plugins", WORKSPACE,
                        ORA_SKILLS_ROOT)


def main():
    pos, overrides = parse_args(sys.argv[1:])
    argv_path = pos[0] if pos else None
    live_root = overrides.get("live_root")
    if live_root is not None:
        if argv_path is not None:
            print("[MISSING] --live-root= cannot be combined with a positional "
                  "CLAUDE.md path -- they set live_mode differently (--live-root "
                  "stays live; a positional path is single-fixture-file mode)")
            sys.exit(1)
        apply_content_root_override(live_root)
        claude_md = CLAUDE_DIR / "CLAUDE.md"
        live_mode = True  # OI-100 Trap 1: NEVER False on this path (7 coupled checks)
    else:
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
        # TERMS_JSON, not CLAUDE_DIR/"hooks"/"...": this file is gitignored (OI-100 --
        # a worktree of any commit never has it, so redirecting this reference would
        # hard-FAIL check 2 on every --live-root= run for a file that was never
        # supposed to be tracked in the first place). TERMS_JSON is pinned to
        # LIVE_CLAUDE_DIR for exactly this reason -- see its definition above.
        file_checks.append(("confidential-terms.json", TERMS_JSON))
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

    # --- 14b. agent definitions parse and self-identify correctly ---
    # Deliberately OUTSIDE the skill-precedence block above: check 14 only inspects
    # agents named as CLAUDE.md tokens, and resolves those by filename. This validates
    # every definition on disk, whether doctrine names it or not.
    agent_failures, agent_warnings = check_agent_definitions(AGENTS_DIR)
    print("Agent definitions validated: %d"
          % len(collect_flat_names(AGENTS_DIR, ".md")))
    for w in agent_warnings:
        warn(w)
    for f in agent_failures:
        print("  [MISSING] %s" % f)
        missing.append("%s (agent definition)" % f)

    # --- 15. skill frontmatter-version vs changelog-version drift (all skills,
    # not just those named in doctrine) ---
    skill_paths = collect_skill_md_paths(SKILL_SCAN_ROOTS, SKILL_PRUNE_DIRS)
    drift_checked = 0
    drift_read_errors = 0
    for name, path in sorted(skill_paths.items()):
        try:
            skill_text = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            drift_read_errors += 1
            continue
        drift_checked += 1
        finding = check_skill_version_changelog_drift(name, skill_text)
        if finding:
            warn(finding)
    print("Skill version/changelog drift: checked %d skill(s)%s"
          % (drift_checked,
             (" (%d unreadable, skipped)" % drift_read_errors) if drift_read_errors else ""))

    # --- 5. CLAUDE.md size budget ---
    words = len(text.split())
    print("CLAUDE.md size: %d words (warn > %d = consolidation floor; "
          "fail > %d = the real gate)"
          % (words, WORD_BUDGET_WARN, WORD_BUDGET_FAIL))
    if words > WORD_BUDGET_FAIL:
        print("  [MISSING] size budget exceeded: %d > %d words "
              "(one-in-one-out gate breached -- trim an equivalent amount elsewhere "
              "in this same change; move a rule down a layer)"
              % (words, WORD_BUDGET_FAIL))
        missing.append("CLAUDE.md size budget (%d > %d words)" % (words, WORD_BUDGET_FAIL))
    elif words > WORD_BUDGET_WARN:
        warn("%d words is AT the consolidation floor (%d), not near the gate (%d) -- "
             "this line is a one-in-one-out nudge, NOT 'the file is too big'. Do not "
             "trim to satisfy it: two independent full-file passes both bottomed out "
             "here, so cuts below the floor remove load-bearing doctrine. A genuine "
             "reduction is relocation (move a whole rule down a layer, leave a "
             "pointer), never deletion. Ruled 'don't trim' in this band on 2026-07-28 "
             "and again 2026-08-09; calibration: "
             "memory/reference_claude_md_word_budget_is_a_floor.md"
             % (words, WORD_BUDGET_WARN, WORD_BUDGET_FAIL))
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

        # (d) the PreToolUse dispatcher's GUARD_CHAIN (in-process Edit/Write chain).
        chain_names = set()
        dispatcher_text, disp_err = read_optional(PRETOOLUSE_DISPATCHER)
        if dispatcher_text is None:
            degraded = True
            warn("guard-liveness: dispatcher unreadable (%s) -- GUARD_CHAIN "
                 "invocation points not checked this run" % ascii_safe(disp_err))
        else:
            m = GUARD_CHAIN_RE.search(dispatcher_text)
            if m is None:
                degraded = True
                warn("guard-liveness: GUARD_CHAIN list not found in %s -- in-process "
                     "invocation points not checked this run"
                     % PRETOOLUSE_DISPATCHER.name)
            else:
                chain_names = set(re.findall(r"[\"']([^\"']+)[\"']", m.group(1)))
                if not chain_names:
                    degraded = True
                    warn("guard-liveness: GUARD_CHAIN parsed empty -- in-process "
                         "invocation points not checked this run")

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
                   or stem in shim_text
                   or stem in chain_names)
            if hit:
                print("  [OK]      %s -> live invocation point found" % ascii_safe(name))
            elif degraded:
                warn("guard '%s' unresolved, but a liveness source was unavailable "
                     "this run (see notes above) -- not asserting orphan"
                     % ascii_safe(name))
            else:
                warn("guard '%s' named in CLAUDE.md's Guards: line has no live "
                     "invocation point found (checked: settings.json hooks, CC/MCP "
                     "scheduled-task SKILL.mds, ~/.claude pre-push shim, "
                     "pretooluse-dispatcher GUARD_CHAIN)"
                     % ascii_safe(name))

    # --- 12. backup-coverage sweep (top-level dirs invisible to the backup) ---
    # Runs live (root = ~/.claude) or on a fixture root via --backup-root=.
    # WARN-only by design: a hit is an opt-in review candidate, not drift --
    # see BACKUP_SWEEP_TRANSIENT_DIRS for rationale and the allowlist contract.
    # Pinned to LIVE_CLAUDE_DIR (not CLAUDE_DIR): this sweep's whole point is untracked
    # top-level dirs in the LIVE install -- a worktree of a commit has none by
    # construction, so redirecting would silently report always-clean (OI-100 Trap 1).
    backup_root = overrides.get("backup_root") or (LIVE_CLAUDE_DIR if live_mode else None)
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

    # --- Workspace-pointer staleness (2026-07-29, Phase-5 blueprint): the thin
    # pointer CLAUDE.md self-declares "If older than 30 days, treat as stale" via a
    # 'Last verified: YYYY-MM-DD' line, but nothing machine-checked that promise --
    # a stale pointer silently misroutes Cowork sessions. WARN-only, fail-open.
    if live_mode:
        try:
            import datetime as _dt
            _wp = Path(r"C:\Users\Owner\OneDrive - Oxford Capital Partners"
                       r"\Claude_Workspace\01_Workspace\CLAUDE.md")
            _body, _err = read_optional(_wp)
            if _body is None:
                warn("workspace-pointer staleness: file unreadable (fail-open) -- %s"
                     % ascii_safe(_err))
            else:
                _m = re.search(r"Last verified:\s*(\d{4})-(\d{2})-(\d{2})", _body)
                if not _m:
                    warn("workspace-pointer staleness: no 'Last verified: YYYY-MM-DD' "
                         "line found -- the self-staleness contract is unverifiable")
                else:
                    _age = (_dt.date.today()
                            - _dt.date(*map(int, _m.groups()))).days
                    if _age > 30:
                        warn("workspace-pointer CLAUDE.md is STALE by its own rule: "
                             "last verified %s (%d days ago > 30) -- re-verify or "
                             "re-point it" % (_m.group(0)[14:], _age))
                    else:
                        print("Workspace-pointer staleness: OK (last verified %d days ago)"
                              % _age)
        except Exception as _e:
            warn("workspace-pointer staleness check errored (fail-open): %s"
                 % ascii_safe(str(_e)))

    # --- worktree.baseRef config drift (2026-08-05, EnterWorktree investigation
    # follow-up): WARN-only, fail-open -- settings.json is best-effort here, same
    # as every other config-drift check in this module. ---
    if live_mode:
        settings_text, settings_read_err = read_optional(SETTINGS_JSON)
        if settings_text is None:
            warn("worktree.baseRef check: settings.json unreadable (fail-open) -- %s"
                 % ascii_safe(settings_read_err))
        else:
            try:
                settings_obj = json.loads(settings_text)
            except ValueError as e:
                warn("worktree.baseRef check: settings.json unparseable "
                     "(fail-open) -- %s" % ascii_safe(e))
            else:
                gap = check_worktree_baseref(settings_obj)
                if gap:
                    warn(gap)
                else:
                    print("worktree.baseRef: OK (\"head\")")

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
        # --- roster-file extension: session-context.md, projects.md,
        # MEMORY.md, firm.md -- see find_marker_residue's docstring for why
        # this checks marker+term CO-OCCURRENCE, not bare mention.
        roster_files = (overrides["roster_files"] if "roster_files" in overrides
                        else ([SESSION_CONTEXT_MD, MEMORY_DIR / "projects.md",
                              MEMORY_DIR / "MEMORY.md", MEMORY_DIR / "firm.md"]
                              if live_mode else []))
        for key, entry in terms_data.items():
            if key.startswith("_") or not isinstance(entry, dict):
                continue
            if entry.get("active") is not False:
                continue
            always = [t.lower() for t in entry.get("always", []) if isinstance(t, str)]
            if not always:
                continue
            for roster_path in roster_files:
                body, err = read_optional(roster_path)
                if body is None:
                    warn("declassification-residue sweep: roster file unreadable "
                         "(fail-open, not asserted this file) -- %s" % ascii_safe(err))
                    continue
                marker_hits = find_marker_residue(body, always)
                for (term, marker), line_no in sorted(marker_hits.items()):
                    residue_total += 1
                    warn("declassified deal '%s' still has a confidentiality "
                         "marker (%r) near its term at %s:%d -- rules.md 7b "
                         "requires the marker be dropped even though the deal "
                         "may still be legitimately mentioned there"
                         % (ascii_safe(key), ascii_safe(marker),
                            ascii_safe(str(roster_path)), line_no))
        if residue_total == 0:
            print("Declassification-residue sweep: clean (0 hits across "
                  "CLAUDE.md + %d ported cop%s + %d roster file(s) checked)"
                  % (len(ported_copies), "y" if len(ported_copies) == 1 else "ies",
                     len(roster_files)))

    # --- Check 12: ora-am-brief SOFR-narration guardrail presence (LAMS/cloud,
    # WARN-only, fail-open) -- guards the event_log.md 2026-07-16 fix from silent
    # removal. Skips in single-file argv mode (live_mode False). ---
    if live_mode:
        ab_text, ab_err = read_optional(AM_BRIEF_SKILL)
        if ab_text is None:
            warn("ora-am-brief SOFR-narration guardrail: SKILL.md unreadable "
                 "(fail-open, not asserted) -- %s" % ascii_safe(ab_err))
        else:
            gaps = check_am_brief_sofr_guardrail(ab_text)
            if gaps:
                warn("ora-am-brief Block A SOFR-narration guardrail INCOMPLETE "
                     "-- missing sentinel(s): %s. A later edit stripped the "
                     "CALLOUT TEMPLATE / SCOPE rule that stops the degraded-"
                     "status callout from narrating SOFR-average/Index freshness "
                     "(fields owned by ora-sofr-direct-prefetch). Restore per "
                     "event_log.md 2026-07-16."
                     % ascii_safe(" | ".join(gaps)))
            else:
                print("ora-am-brief SOFR-narration guardrail: intact "
                      "(%d/%d sentinels present)"
                      % (len(AM_BRIEF_SENTINELS), len(AM_BRIEF_SENTINELS)))

    # --- 13. doctrine-vs-deliverable identity sweep (2026-08-03). Live-mode
    # only: it compares the doctrine file against what live EMITTERS say, which
    # is meaningless against a single fixture path. WARN-only, fail-open. ---
    if live_mode:
        canon = canonical_identity_title(text)
        if canon is None:
            warn("Doctrine-vs-deliverable identity sweep: no parseable Identity "
                 "line in CLAUDE.md ('%s, <title>, Oxford Realty Advisors') -- "
                 "sweep SKIPPED, not asserted." % IDENTITY_NAME)
        else:
            emitters = collect_identity_emitters()
            if not emitters:
                warn("Doctrine-vs-deliverable identity sweep: no live emitters "
                     "readable (ora-skills / outreach generators absent?) -- "
                     "sweep SKIPPED, not asserted.")
            else:
                drift = check_identity_drift(canon, emitters)
                if drift:
                    warn("Doctrine-vs-deliverable identity DRIFT -- CLAUDE.md "
                         "says %s but %d live emitter(s) disagree: %s. These "
                         "produce NEW paper, so the drift compounds until fixed. "
                         "Reconcile against CLAUDE.md's Identity line (see "
                         "event_log.md 2026-08-03)."
                         % (canon, len(drift), ascii_safe(" | ".join(drift))))
                else:
                    print("Doctrine-vs-deliverable identity sweep: clean "
                          "(%s across %d live emitter(s))"
                          % (canon, len(emitters)))

    # --- 14. four-site stage-exclusion list sync (2026-08-12). Live-mode only:
    # it reads the four scheduled-task SKILL.mds, which do not exist beside a
    # single fixture path. WARN-only, fail-open. ---
    if live_mode:
        sites = collect_stage_exclusion_sites()
        if len(sites) < len(STAGE_EXCLUSION_SITES):
            seen = set(lbl for lbl, _ in sites)
            absent = [n for n, _ in STAGE_EXCLUSION_SITES if n not in seen]
            warn("Stage-exclusion four-site sweep: only %d of %d SKILL.md "
                 "readable (absent: %s) -- sweep PARTIAL, not asserted. A "
                 "silent pass on an unread site is the inferred-null failure."
                 % (len(sites), len(STAGE_EXCLUSION_SITES), ", ".join(absent)))
        if sites:
            drift = check_stage_exclusion_sync(sites)
            if drift:
                warn("Stage-exclusion list DRIFT -- %d of the four ratified "
                     "sites disagree: %s. The failure directions are opposite "
                     "and both silent: a missing value in the three exclusion "
                     "sites leaks a retired deal onto a live board, while in "
                     "ora-weekly-hygiene's inclusion form it means retired "
                     "artifacts are never flagged for archival. Match on the "
                     "em-dash -- a hyphen fails the comparison. Fix all four "
                     "in ONE session (each SKILL.md carries the rule)."
                     % (len(drift), ascii_safe(" | ".join(drift))))
            else:
                print("Stage-exclusion four-site sync: clean (%d values across "
                      "%d site(s))"
                      % (len(STAGE_TERMINAL_VALUES), len(sites)))

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
