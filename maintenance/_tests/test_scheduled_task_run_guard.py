#!/usr/bin/env python3
"""Fleet-level conformance + no-op regression tests for the double-fire run guard.

WHAT THIS COVERS THAT test-block-sentinel.py DOES NOT
-----------------------------------------------------
`scheduled-tasks/_shared/test-block-sentinel.py` tests the HELPER: given a state
file, does `claim` return 10 on a second call. It says nothing about whether any
actual scheduled-task entrypoint calls it, calls it BEFORE its first side effect,
or passes the `--period` that matches its own cron cycle. Every guard defect found
in the 2026-09-10 audit was of that second kind, so this file tests the WIRING:

  1. every entrypoint is classified: guarded, on the frozen backlog, or explicitly
     reviewed as side-effect-free. An UNCLASSIFIED task FAILS -- see below.
  2. the claim precedes the first side effect
  3. a claiming entrypoint also declares `complete` and `fail` (ownership contract)
  4. a MONTHLY-cron entrypoint claims with `--period month`
  5. END-TO-END: the entrypoint's OWN claim command line, executed twice inside one
     cycle, is a no-op the second time -- exit 10, state file byte-identical

Test 5 parses the literal `block-sentinel.py claim …` line out of each SKILL.md and
runs THAT, so a spec that omits `--period` is caught by construction. What it proves
is precise: for a `--period month` task the state key is `YYYY-MM`, so re-keying to
another day of the month is a no-op and the assertion reduces to the one
test-block-sentinel.py already makes. Its real value is as a REGRESSION guard --
drop `--period month` from a spec and the bucket becomes day-keyed, the re-key
starts biting, and this test fails. That is exactly how ora-passed-deal-tracker
below is caught.

UNKNOWN MUST FAIL, NOT PASS. A 2026-09-10 review found the first cut of this file
clearing five genuinely side-effecting tasks because SIDE_EFFECTS matched only
literal tool identifiers and those specs reach their side effect through prose --
ora-pm-daily-crons says "sends that digest via the canonical Outlook-COM sender"
and also POSTs to an endpoint that writes late fees to tenant ledgers. Regex cannot
settle this, so it no longer tries to: a task that is neither detected nor listed is
an ERROR, and NO_SIDE_EFFECT_REVIEWED is the only way to declare one harmless.

RATCHET, NOT SNAPSHOT. The frozen sets are the 2026-09-10 inventory. Adding an
unguarded side-effecting task FAILS. So does fixing a gap without removing its
waiver -- an unexpected PASS is a failure here, which keeps the lists from rotting
into permanent excuses (the exact rot that left hooks/tests/test-shared-checkout-
guard.py asserting a pre-fix contract).

SCOPE: the CC/MCP fleet's in-repo specs. LAMS/Cowork SKILL.md files live under
`OneDrive .../Documents/Claude/Scheduled/` and are NOT in this repo, so they cannot
be gated here (README-DOUBLE-FIRE-GUARD.md, "ora-monday-sync lives on the LAMS
fleet"). Note also that a CC task registered on a branch not yet merged is
invisible to this suite until it lands -- being in-repo is what makes a task
gateable, not being in the registry.
"""

import glob
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

# FAIL details quote task SKILL.md lines verbatim (e.g. "STEP 2 → ..."); on a Windows
# cp1252 pipe (the pre-push hook-tests gate) printing one raised UnicodeEncodeError,
# aborting the run before the failure was recorded or summarized.
for _s in (sys.stdout, sys.stderr):  # UTF-8 safe output on Windows cp1252 pipes
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.dirname(os.path.dirname(HERE))          # ~/.claude
SCHED = os.path.join(CLAUDE, "scheduled-tasks")
SENTINEL = os.path.join(SCHED, "_shared", "block-sentinel.py")

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        _failures.append(name)


# --------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------

# An "external side effect" is an action a duplicate fire makes VISIBLE or DURABLE
# outside this machine: mail leaves, a Notion/HubSpot record mutates, a commit is
# pushed, a site or Artifact republishes, a registry row changes. Local-only work
# (a read, a scratch file, an unpushed commit) is not one.
#
# The prose alternatives are not decoration. ora-pm-daily-crons reaches the COM
# sender through a script and describes it in English; ora-acquisition-underwriting-
# eval-harness says "Post to Notion". Both were wrongly cleared before these landed.
SIDE_EFFECTS = (
    ("email",    re.compile(r"send-via-outlook|send-parked-drafts|Outlook-COM sender|"
                            r"\bdigest send\b|sends? (?:that |the )?digest", re.I)),
    ("notion",   re.compile(r"notion-(?:create-pages|update-page|create-comment|"
                            r"update-data-source|create-database|move-pages)|"
                            r"\bPost to Notion\b|post(?:s|ing)? (?:a |the )?"
                            r"(?:run report|finding|banner) .{0,40}Notion", re.I)),
    ("gitpush",  re.compile(r"\bgit\s+push\b", re.I)),
    ("hubspot",  re.compile(r"manage_crm_objects|manage_campaign_objects", re.I)),
    ("sched",    re.compile(r"\b(?:create|update|delete)_scheduled_task\b", re.I)),
    ("deploy",   re.compile(r"netlify\s+deploy|netlify-\w+-services-updater", re.I)),
    ("artifact", re.compile(r"publish via Artifact|republish(?:es)? the artifact|"
                            r"refresh of the interactive .{0,40}artifact|"
                            r"artifact updater", re.I)),
)

CLAIM_LINE = re.compile(r"block-sentinel(?:\.py)?\s+claim\b", re.I)
FINALIZE_LINE = re.compile(r"block-sentinel(?:\.py)?\s+(complete|fail)\b", re.I)
PLACEHOLDER = re.compile(r"<[^>]*>")

# A line the RUN executes, as opposed to prose that merely names a script: inside a
# fenced code block, or a numbered/lettered step ("7.", "B.4", "Step 3").
STEP_LINE = re.compile(r"^\s{0,3}(?:\*\*)?(?:\d+[.)]|[A-Z]\.\d+|Step\s+\d+)", re.I)

# Flags `claim` accepts that `complete`/`fail` reject -- stripped when the same
# parsed argv is reused to close the claim (a stray --ttl-min exits 2).
# --slot-times (2026-09-24): claim resolves the block itself; the spec then closes
# with the `block` claim emitted, which finalize_argv appends via `resolved_block`.
CLAIM_ONLY_FLAGS = {"--ttl-min": 1, "--force": 0, "--slot-times": 1}

# Frozen 2026-09-10. Side effects, no run guard. The documented per-task adoption
# backlog (README-DOUBLE-FIRE-GUARD.md: "adoption is proven per-task, not
# retrofitted en masse"), ranked there by the consequence of a duplicate.
UNGUARDED_BACKLOG = {
    "ora-aaos-expire-leases", "ora-aaos-publish-contracts", "ora-appsec-sweep",
    "ora-ar-feed-sweep", "ora-calibration-snapshot",
    "ora-cc-snapshot-refresh", "ora-checkout-merge-forward",
    "ora-command-center-mirror-drift-check", "ora-deal-command-board",
    "ora-deal-sourcing-scan", "ora-doctrine-integrity-guard",
    "ora-financial-code-integrity-sweep",
    "ora-lease-snapshot-refresh", "ora-master-workbook-ingest",
    "ora-model-release-watch", "ora-pm-daily-crons", "ora-pm-ledger",
    "ora-pm-monthly-billing", "ora-routine-pause-resume-2026-09-11",
    "ora-site-exposure-probe", "ora-sofr-direct-prefetch",
    "ora-task-integrity-guard", "ora-weekly-hygiene",
    # Added 2026-09-10 after review: all four were wrongly cleared by the
    # literal-identifier-only detector, and all four write outside this machine.
    "ora-psa-drift-watch",                       # appends a DISPUTED banner to live
                                                 # Notion pipeline rows; posts a run report
    "ora-acquisition-underwriting-eval-harness", # "Post to Notion" on doctrine change
    "ora-cc-schematic-refresh",                  # republishes a live Claude Artifact
    "ora-claude-setup-audit",                    # publishes an Automation Audit rev-band
    # Tracked on main but NOT in the live CC registry, and its SKILL.md is staged
    # for deletion in the shared checkout (` D` in git status) -- a retirement in
    # progress, per the CC order "delete_scheduled_task first, archive second". Not
    # a live entrypoint; listed only so this suite is green against main, where the
    # folder still exists in git. Inert once that deletion is committed.
    "ora-754-flaute-escalation-check",
    # Added 2026-09-17 (dirty-tree-triage). One-time ATTENDED resume of the 37 CC tasks
    # paused 09-14, same class as ora-routine-pause-resume-2026-09-11 above: side effects
    # (update_scheduled_task, run_scheduled_task, a COM send), no run guard. It was
    # UNTRACKED until a7d87ca, so this suite passed at every commit and failed only in the
    # live working tree -- which is how it reached a push gate as a surprise. Inert once
    # the task fires and its folder is archived.
    "ora-routine-pause-resume-09-21",
    # Added 2026-09-28 (dirty-tree-triage, PR #284). Registered after the 2026-09-10
    # inventory and UNTRACKED until that PR, so this suite passed at every commit and
    # failed only in the live working tree. Each has a real side effect and no run guard;
    # adopt the guard per task (README-DOUBLE-FIRE-GUARD.md) and remove the entry then.
    "ora-hubspot-renewal-closeout-tasks",        # creates HubSpot tasks (manage_crm_objects)
    "ora-incentive-registry-refresh",            # emails a summary
    "ora-jackson-boe-prep-reminder",             # one-time reminder email
    "ora-loopnet-listings-sync",                 # git push
    "ora-noi-opportunity-digest",                # emails the monthly digest
    "ora-recovery-billing-monthly",              # emails a billing-check summary
    "ora-recovery-structure-audit-annual",       # emails an annual summary
    "ora-wicomico-reassessment-reminder",        # one-time reminder email
    # Added 2026-09-29. Registered (disabled, monthly, day 3) but its spec and script are
    # deliberately NOT tracked: held out of PR #285 for OI-360 (archive overwrite, in-repo
    # scanner-blind archive folder). The spec is untracked in the live checkout, so the
    # ratchet saw it only there. Emails on errors / skipped_locked. Remove this entry in the
    # same change that lands the task with a block-sentinel claim (OI-360, OI-363).
    "ora-audit-log-sweep",
    # Added 2026-10-08 (ora-prepush-gate-sweep). Both registered after the 09-28 inventory
    # and UNTRACKED, so this suite fails only in the live working tree. Report-only, but
    # each EMAILS ggoldberg with no run guard; adopt the guard per task and remove the entry.
    "ora-agent-usage-report-monthly",            # emails the monthly agent-usage summary
    "ora-site-market-snapshot-refresh",          # emails the quarterly stale-figures digest
}

# The ONLY way to declare a task harmless. Each entry means a human read the spec
# and confirmed no external side effect -- not that a regex failed to find one.
NO_SIDE_EFFECT_REVIEWED = {
    # "Never pushes, never switches branches ... purely additive local commits";
    # "Do not send any email or Outlook message ... Do not touch Notion." (SKILL.md:18,23)
    "ora-memory-commit-sweep",
}

# Guarded tasks whose ordering regex cannot settle, checked by hand instead.
# Listing one is a claim that someone READ it and confirmed the claim precedes every
# side effect. A NEW guarded task whose ordering is unverifiable FAILS until read.
ORDERING_VERIFIED_BY_HAND = {
    # Read by hand 2026-10-08 (v0.6 digest-reader rewrite): the sole claim is the unfenced
    # STEP -1 line at :9, the run's first action. Everything after only READS the Notion
    # worker DBs; the one side effect is the unfenced prose "Send via Outlook COM" at :35,
    # followed by the complete line at :12's contract. "Writes outside the email and the
    # block-sentinel calls: none" (:37).
    "ora-county-sales-monitor": "claim@9 precedes send@35 (reads only in between)",
    # Read by hand 2026-10-18: the sole claim is STEP -1 (first action). Steps 1-3 only READ
    # ora-skills cowork-settings versions and the governance copy; the side effects are the
    # step 4 email and step 5 Notion completion row, both after the claim.
    "ora-cowork-settings-quarterly-review": "claim@STEP -1 precedes email@step 4 and Notion@step 5; steps 1-3 read-only",
    # Read by hand 2026-10-17: the sole claim is STEP -1 (first action). STEP 0-3 only crawl
    # the public site read-only; the one side effect is the STEP 4 regression email, after it.
    "ora-site-seo-crawl-weekly": "claim@STEP -1 precedes email@STEP 4; crawl is read-only",
    # Read by hand 2026-10-17: the sole claim is the STEP 0 line (first action). STEP 1 only
    # READS the pause file/workbook mtime; STEP 2 fetches and adds a detached worktree from the shared checkout's .git (after the claim) and runs npm ci there; the only write
    # before the claim-holder reports is the full-gate-weekly.json state file (STEP 3); the one
    # email is STEP 4, after STEP 0.
    "ora-full-gate-weekly": "claim@STEP 0 precedes email@STEP 4; STEP 1 reads only, STEP 2 fetch+worktree after claim",
    # Read by hand 2026-09-28: the sole claim is the STEP 0 line at :11, the run's first
    # action. Step 1 only READS Notion and writes a %TEMP% json; the side effects all
    # follow: COM send :32, Ops Hub Notion row :35.
    "ora-loan-balance-check": "claim@11 precedes send@32, Ops Hub write@35",
    # Read by hand 2026-09-23 (v1.8 guard landed from the live file): the sole claim is
    # the fenced STEP 0-B block at :33. STEP 0-A (:18-24) runs first but only exits
    # silently. Side effects all follow: Deal Sourcing Log creates :96, COM send :125,
    # Ops Hub failure log :127. Off UNGUARDED_BACKLOG in the same change (ratchet).
    "ora-entry-market-scan": "claim@33 precedes Notion creates@96, send@125, Ops Hub@127",
    # Read by hand 2026-09-23 (new task, guard added before its first live fire): the
    # sole claim is the unfenced GUARD 1 line at :12. GUARD 0 (:8) only reads the scan's
    # done-marker file and ends silently -- no write, no send. Side effects all follow:
    # Notion update_properties WRITES :34, COM send EMAIL :45.
    "ora-sourcing-construction-verify": "claim@12 precedes Notion writes@34, send@45",
    # claim@27, only send at :241, inside a prose line beginning "Post a NEW DATED
    # CHILD PAGE" that matches neither a fence nor a step marker.
    "ora-deal-aging-sla": "claim@27 precedes sends@40,241",
    # Read by hand 2026-09-22 (v1.2 adoption): the sole claim is the unfenced STEP 0
    # line at :23. first_side_effect(lines) (any-mode) finds email mentions only at
    # :80 (STEP 0.5 backlog-gate email), :208/:210 (STEP 4 comments naming
    # send-via-outlook as forbidden), :277 (STEP 5 email), :333 (changelog), none
    # fenced or on a STEP_LINE. The STEP 4 Outlook COM draft (CreateItem/.Save()
    # at :227-232) is no SIDE_EFFECTS kind at all. Every one follows the claim.
    "ora-broker-touch-cadence": "claim@23 precedes email@80,277 and COM draft@227",
    "ora-monthly-portfolio-briefing": "claim@17 precedes sends@40,59",
    "ora-open-sessions-board": "claim@13 precedes send@65",
    # :8 is a RESTORATION NOTE naming send-via-outlook.ps1 in prose, not a step.
    # Real sends are :195 and :233, both after claim@15.
    "ora-passed-deal-tracker": "claim@15 precedes real sends@195,233 (:8 is prose)",
    # :3 is the frontmatter description's own changelog prose (names "block-sentinel.py
    # claim/complete/fail" while describing the STEP 0 addition) -- not an invocation.
    # Real claim is @18; real send is @69, both unfenced/unmarked so the regex can't
    # see them either, same shape as ora-deal-aging-sla/ora-passed-deal-tracker above.
    "ora-forward-calendar-digest": "claim@18 precedes send@69 (:3 is frontmatter prose)",
    # Computed via claim_lines()/first_side_effect(lines) (any-mode), 2026-09-18: claim
    # is the sole fenced block at :13. The email side effect is STEP 5's unfenced prose
    # paragraph at :62 ("Send ONE summary email via ... send-via-outlook.ps1 ..."), which
    # matches neither a fence nor STEP_LINE -- same unfenced-prose shape as
    # ora-deal-aging-sla/ora-passed-deal-tracker above.
    "ora-excess-usage-sweep": "claim@13 precedes send@62",
    # Computed the same way, 2026-09-18: claim is the sole fenced block at :13. The
    # email side effect is STEP 6's unfenced prose sentence at :70 ("TO
    # `ggoldberg@oxfordra.net` ONLY ... via the sole send path `...send-via-outlook.ps1`.
    # On non-zero exit: retry once; ..."). The STEP 1c fail-loud-gate send (an earlier,
    # conditional path) is prose too ("send the email anyway with subject ...") and does
    # not literally match the SIDE_EFFECTS email regex (no "send-via-outlook" substring
    # on that line), so :70 is genuinely the first regex-matchable occurrence either way.
    "ora-vacancy-aging-report": "claim@13 precedes send@70",
}

# Guarded entrypoints whose guard does NOT yet satisfy a check below. Each entry
# names the defect; an entry that starts passing FAILS so the waiver comes out in
# the same commit as the fix.
KNOWN_GAPS = {
    # Monthly cron `30 6 15 * *`, but claims with the default --period day. Its own
    # exit-10 row reads "This month's sweep already completed" -- the behavior is
    # "already completed TODAY". A catch-up fire on the 16th, or any re-fire on a
    # different day of the same month, is NOT suppressed. `--period` landed
    # 2026-09-06, after this guard was wired 2026-08-16; the three other monthly
    # tasks were retrofitted and this one was missed.
    ("ora-passed-deal-tracker", "period_matches_cron_cycle"),
    ("ora-passed-deal-tracker", "same_cycle_second_fire_is_noop"),
}


def specs():
    """(task_id, path, lines) for every live CC/MCP entrypoint spec."""
    out = []
    for d in sorted(os.listdir(SCHED)):
        p = os.path.join(SCHED, d)
        if not os.path.isdir(p) or d.startswith("_"):
            continue
        md = os.path.join(p, "SKILL.md")
        if not os.path.exists(md):
            cand = sorted(glob.glob(os.path.join(p, "*.md")))
            if not cand:
                continue
            md = cand[0]
        with open(md, encoding="utf-8", errors="replace") as fh:
            out.append((d, md, fh.read().split("\n")))
    return out


def body_start(lines):
    """First line after the YAML frontmatter.

    An earlier revision used the first H2. That silently dropped three
    side-effecting tasks whose STEPS sit above any H2 -- ora-doctrine-integrity-guard
    (notion-create-pages :58, COM send :64; first H2 :89),
    ora-command-center-mirror-drift-check (send at step 7, :64; first H2 :69) and
    ora-site-exposure-probe (send at step 6, :58; first H2 :64). Frontmatter is the
    only boundary every spec actually shares."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def first_side_effect(lines, executable_only=False):
    """(line_index, kind) of the first side effect in the spec body, or None.

    TWO detectors, because the two questions want opposite errors:

      executable_only=False -- "does this need a guard at all?" Any body mention
      counts. Over-inclusive on purpose: a task wrongly flagged just needs a list
      entry, while one wrongly cleared ships unguarded.

      executable_only=True -- "does the claim come first?" Only fenced-code or
      step lines count. Prose that NAMES send-via-outlook is not an invocation, and
      counting it produced false ordering violations (ora-am-brief :32, the
      root-cause narrative inside the guard section; ora-health-guard :53, the
      SHARED MCP ROUTING reference block) -- a guard section that explains what it
      prevents will always mention the thing it prevents."""
    fenced = False
    for i in range(body_start(lines), len(lines)):
        line = lines[i]
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if executable_only and not (fenced or STEP_LINE.match(line)):
            continue
        for kind, rx in SIDE_EFFECTS:
            if rx.search(line):
                return i, kind
    return None


def claim_lines(lines):
    return [i for i, line in enumerate(lines) if CLAIM_LINE.search(line)]


def claim_commands(lines):
    """Every literal claim invocation, as argv, with <placeholders> filled.

    Parsed from the spec rather than reconstructed, so --period/--block/--ttl-min
    are whatever the entrypoint actually tells the run to type."""
    cmds = []
    for i in claim_lines(lines):
        raw = lines[i].strip().strip("`")
        if "block-sentinel" not in raw:
            continue
        raw = raw[raw.index("block-sentinel"):]
        # Many claim lines are an inline `code span` inside a sentence, so the
        # command ends at the closing backtick, not at end of line. Without this the
        # last token arrives as "30`," and argparse rejects it (exit 2).
        if "`" in raw:
            raw = raw[:raw.index("`")]
        raw = raw.rstrip().rstrip(",.;:")
        raw = PLACEHOLDER.sub("TESTRUNID", raw)
        try:
            argv = shlex.split(raw)
        except ValueError:
            continue
        if len(argv) < 2 or argv[1] != "claim":
            continue
        cmds.append(argv[1:])          # drop the script name; we supply SENTINEL
    return cmds


def flag_value(argv, flag, default=None):
    """argv value after `flag`, or default. Tolerates the flag arriving last."""
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def finalize_argv(claim_argv, verb, resolved_block=None):
    """Turn a parsed `claim ...` argv into the matching `complete`/`fail` argv.

    A `claim --slot-times` spec closes with the `block` the claim emitted (the
    spec tells the run to reuse it verbatim), so pass it as `resolved_block`; it
    replaces any literal --block."""
    out, i = [verb], 1
    while i < len(claim_argv):
        tok = claim_argv[i]
        if tok in CLAIM_ONLY_FLAGS:
            i += 1 + CLAIM_ONLY_FLAGS[tok]
            continue
        if resolved_block and tok == "--block":
            i += 2
            continue
        out.append(tok)
        i += 1
    if resolved_block:
        out += ["--block", resolved_block]
    return out


def run_sentinel(argv, state):
    p = subprocess.run([sys.executable, SENTINEL] + argv + ["--state", state],
                       capture_output=True, text=True)
    try:
        return p.returncode, json.loads(p.stdout)
    except Exception:
        return p.returncode, {"_stdout": p.stdout, "_stderr": p.stderr}


def cron_table():
    """{task_id: cronExpression} from the live CC/MCP registry, or None if the
    registry is not on this host (a clone, CI, another machine)."""
    pat = os.path.expandvars(
        r"%APPDATA%\Claude\claude-code-sessions\**\scheduled-tasks.json")
    files = glob.glob(pat, recursive=True)
    if not files:
        return None
    table = {}
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for t in json.load(fh).get("scheduledTasks", []):
                    if t.get("cronExpression"):
                        table[t["id"]] = t["cronExpression"]
        except Exception:
            continue
    return table or None


def is_monthly(cron):
    """True only when day-of-month is pinned. `* * 1-5` is daily-on-weekdays and
    `* * 1` is weekly -- both have a one-DAY cycle, and day keying is correct for
    them. ora-open-sessions-board proves week keying would be actively wrong: it
    fires Mon/Wed/Fri, three separate cycles inside one ISO week. Only a
    day-of-month cron has a cycle wider than a day, so only it is asserted.

    NOTE this scheduler resolves a restricted day-of-month and a restricted
    day-of-week as OR, not AND, so a cron with both fires on the union."""
    f = cron.split()
    return len(f) >= 5 and f[2] != "*"


def ratchet(task, test, passed, detail="", label=None):
    """Fail on a regression, and equally on a waived gap that has started passing."""
    name = "%s :: %s" % (label or task, test)
    if (task, test) in KNOWN_GAPS:
        if passed:
            check(name + " [waiver is stale -- gap is fixed, remove it from KNOWN_GAPS]",
                  False, detail)
        else:
            print("  WAIVED  %s  (KNOWN_GAPS)  %s" % (name, detail))
        return
    check(name, passed, detail)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_lams_fleet_is_out_of_repo():
    """Not a gate -- a standing reminder that half the fleet is ungatable here, so
    a green run of this file never means 'the fleet is covered'."""
    print("\ntest_lams_fleet_is_out_of_repo")
    lams = os.path.expandvars(
        r"%USERPROFILE%\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled")
    n = len([d for d in glob.glob(os.path.join(lams, "*")) if os.path.isdir(d)]) \
        if os.path.isdir(lams) else 0
    print("  NOTE  %d LAMS/Cowork task folder(s) exist outside this repo and are "
          "NOT gated by this suite." % n)


def test_every_entrypoint_is_classified():
    """Guarded, on the backlog, or reviewed side-effect-free. Nothing else."""
    print("\ntest_every_entrypoint_is_classified")
    for task, _p, lines in specs():
        eff = first_side_effect(lines)
        guarded = bool(claim_lines(lines))
        if guarded:
            check("%s :: guarded" % task, True)
            check("%s :: not stale on the backlog list" % task,
                  task not in UNGUARDED_BACKLOG,
                  "now guarded -- remove it from UNGUARDED_BACKLOG")
            continue
        if eff is not None:
            check("%s :: unguarded %s side effect is on the frozen backlog"
                  % (task, eff[1]), task in UNGUARDED_BACKLOG,
                  "line %d: %s" % (eff[0] + 1, lines[eff[0]].strip()[:120]))
            continue
        # Nothing detected. That is NOT clearance -- regex missed five real ones
        # before. Someone must have read it and said so.
        check("%s :: undetected side effects, but reviewed as harmless" % task,
              task in NO_SIDE_EFFECT_REVIEWED or task in UNGUARDED_BACKLOG,
              "UNCLASSIFIED: read the spec, then add it to NO_SIDE_EFFECT_REVIEWED "
              "(with the quote proving it) or to UNGUARDED_BACKLOG")


def test_guard_precedes_first_side_effect():
    print("\ntest_guard_precedes_first_side_effect")
    for task, _p, lines in specs():
        cl = claim_lines(lines)
        if not cl:
            continue
        eff = first_side_effect(lines, executable_only=True)
        if eff is None:
            # Previously a silent `continue`, which hid HALF the guarded fleet.
            check("%s :: ordering unverifiable by regex, verified by hand" % task,
                  task in ORDERING_VERIFIED_BY_HAND,
                  "no fenced/step side effect found; read the spec and record the "
                  "evidence in ORDERING_VERIFIED_BY_HAND")
            continue
        ratchet(task, "guard_precedes_first_side_effect", min(cl) < eff[0],
                "claim@%d vs first %s side effect@%d" % (min(cl) + 1, eff[1], eff[0] + 1))


def test_guarded_entrypoints_declare_claim_termination():
    """claim exit 0 obliges the run to close with complete or fail. A spec that
    claims and never says how to close it strands IN_PROGRESS until the TTL, which
    stands down every fire inside that window."""
    print("\ntest_guarded_entrypoints_declare_claim_termination")
    for task, _p, lines in specs():
        if not claim_lines(lines):
            continue
        ratchet(task, "declares_complete_or_fail",
                any(FINALIZE_LINE.search(l) for l in lines),
                "no complete/fail call site in the spec")


def test_claim_lines_are_parseable():
    """A spec that claims must yield at least one RUNNABLE claim command. Without
    this, a reformat that breaks the parser drops the task out of test 5 silently
    while the suite stays green."""
    print("\ntest_claim_lines_are_parseable")
    for task, _p, lines in specs():
        if not claim_lines(lines):
            continue
        check("%s :: claim line parses to argv" % task, bool(claim_commands(lines)),
              "%d claim line(s) found, none parseable" % len(claim_lines(lines)))


def test_claim_period_matches_cron_cycle():
    print("\ntest_claim_period_matches_cron_cycle")
    crons = cron_table()
    if crons is None:
        print("CANNOT RUN: no CC/MCP scheduled-tasks.json on this host "
              "(registry lives outside the repo under %APPDATA%).")
        return
    for task, _p, lines in specs():
        cmds = claim_commands(lines)
        if not cmds or task not in crons or not is_monthly(crons[task]):
            continue
        for argv in cmds:
            period = flag_value(argv, "--period", "day")
            ratchet(task, "period_matches_cron_cycle", period == "month",
                    "cron %r is monthly but claim uses --period %s" % (crons[task], period))


def test_second_invocation_in_same_cycle_is_a_noop():
    """THE regression proof, run against each entrypoint's own claim command line.

    Fire #1 claims and completes. Fire #2 -- same task, same block, same cycle --
    must exit 10 and must not touch the state file. For a monthly entrypoint fire #2
    is re-keyed onto a different day of the same month; see the module docstring for
    exactly what that does and does not prove.

    REQUIRES THE REGISTRY. Without it every task looks non-monthly, the re-key never
    fires, ora-passed-deal-tracker trivially exits 10, and the ratchet would report
    its waiver as STALE -- telling a maintainer to delete the waiver for a live
    double-fire defect. A safety ratchet must never fail in that direction, so this
    refuses to run rather than run blind."""
    print("\ntest_second_invocation_in_same_cycle_is_a_noop")
    crons = cron_table()
    if crons is None:
        print("CANNOT RUN: no CC/MCP scheduled-tasks.json on this host -- cannot tell "
              "which entrypoints are monthly, and a day-only run would report the "
              "monthly gaps as fixed.")
        return
    for task, _p, lines in specs():
        cmds = claim_commands(lines)
        if not cmds:
            continue
        monthly = task in crons and is_monthly(crons[task])
        for argv in cmds:
            block = flag_value(argv, "--block", "main")
            label = "%s/%s" % (task, block)
            fd, state = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            os.remove(state)
            try:
                rc1, out1 = run_sentinel(argv, state)
                if rc1 != 0:
                    check("%s :: fire #1 claims" % label, False,
                          "exit %s %s" % (rc1, out1))
                    continue
                resolved = out1.get("block") if "--slot-times" in argv else None
                if "--slot-times" in argv and not resolved:
                    check("%s :: fire #1 emits a resolved block" % label, False, str(out1))
                    continue
                if resolved:
                    label = "%s/%s" % (task, resolved)
                rc, _ = run_sentinel(finalize_argv(argv, "complete", resolved), state)
                if rc != 0:
                    check("%s :: fire #1 completes" % label, False, "exit %s" % rc)
                    continue

                if monthly:
                    # Re-key fire #1's record onto another day of the same month. A
                    # month-keyed guard is unaffected (its bucket is "YYYY-MM" and
                    # does not match this pattern); a day-keyed one now looks at a
                    # bucket it has never seen, which is the defect.
                    with open(state, encoding="utf-8") as fh:
                        data = json.load(fh)
                    rekeyed = {}
                    for k, v in data.items():
                        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k):
                            d = datetime.strptime(k, "%Y-%m-%d")
                            earlier = d - timedelta(days=1)
                            if earlier.month != d.month:
                                earlier = d + timedelta(days=1)
                            k = earlier.strftime("%Y-%m-%d")
                        rekeyed[k] = v
                    with open(state, "w", encoding="utf-8") as fh:
                        json.dump(rekeyed, fh)

                with open(state, "rb") as fh:
                    before = fh.read()
                rc2, out2 = run_sentinel(argv, state)
                with open(state, "rb") as fh:
                    after = fh.read()

                ratchet(task, "same_cycle_second_fire_is_noop",
                        rc2 == 10 and out2.get("decision") == "SKIP_ALREADY_COMPLETE"
                        and before == after,
                        "monthly=%s exit=%s decision=%s state_mutated=%s"
                        % (monthly, rc2, out2.get("decision"), before != after),
                        label=label)
            finally:
                if os.path.exists(state):
                    os.remove(state)


if __name__ == "__main__":
    if not os.path.exists(SENTINEL):
        print("CANNOT RUN: block-sentinel.py not found at %s" % SENTINEL)
        sys.exit(0)
    if not os.path.isdir(SCHED):
        print("CANNOT RUN: no scheduled-tasks tree at %s" % SCHED)
        sys.exit(0)

    test_lams_fleet_is_out_of_repo()
    test_every_entrypoint_is_classified()
    test_guard_precedes_first_side_effect()
    test_guarded_entrypoints_declare_claim_termination()
    test_claim_lines_are_parseable()
    test_claim_period_matches_cron_cycle()
    test_second_invocation_in_same_cycle_is_a_noop()

    if _failures:
        print("\n%d FAILURE(S):\n  - %s" % (len(_failures), "\n  - ".join(_failures)))
        sys.exit(1)
    print("\nALL scheduled-task run-guard conformance tests passed.")
    sys.exit(0)
