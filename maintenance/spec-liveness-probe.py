#!/usr/bin/env python3
"""spec-liveness-probe.py -- report-only drift check between what a fleet spec
CLAIMS about live runtime data and what that data actually says.

WHY THIS EXISTS (OI-171, 2026-08-16). `ora-cc-snapshot-refresh`'s STEP 5 severity
gate escalated to email on "at least one data-quality flag of severity warn or
higher". The single permanent, intentional flag -- the tombstoned Loan Index row
24 duplicate marker -- IS `warn`, so the gate's own condition matched the one
thing it was built to ignore and every clean exit-0 run still sent [ALERT]. The
gate (1706bc2, 2026-08-12 15:42) was written believing that flag was `info`; it
had been bumped info -> warn in 490d89f (2026-08-11 18:15), ~21 HOURS EARLIER,
deliberately, because skipping the row removes its balance from aggregate debt
and moves portfolio LTV in the falsely-clearing direction against Hard Invariant
4's 40% ceiling. Two individually-correct changes; the INTERACTION was the bug.

Nothing caught it, and the coverage gap is structural rather than accidental:
  * doctrine-integrity-probe.py compares spec -> canon constants and resolves
    file/skill references. It reads no live data at all.
  * governor-drift-probe.py checks DSCR/LTV DECLARATIONS across fleet SKILL.mds
    and explicitly excludes snapshot values (see its :1224 comment -- "brain data
    snapshots hold per-DEAL dscr/ltv VALUES, not governor declarations").
Both are spec-to-spec or spec-to-constant. Neither reaches runtime data. This
probe is that missing edge, and only that edge.

DELIBERATELY NOT A PRE-PUSH GATE. doctrine-integrity-probe.py is wired into
git-prepush-doctrine-gate.py, which runs it against a scratch worktree of the
commit under push. A live-data dependency there would let portfolio.json drifting
for reasons unrelated to your diff block an unrelated push. This runs daily,
report-only, and NEVER blocks -- run() returns 0 even when it finds drift.

FAIL-OPEN, matching every other guard in this tree: an unreadable, missing, or
malformed snapshot yields None and a skip note, never a finding and never a
crash. A probe that cannot read ground truth must say so, not invent a verdict
(see feedback_verified_null_vs_inferred_null).

Run: python spec-liveness-probe.py   (always exit 0)
"""
import json
import os
import re
import sys

CLAUDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Findings quote spec text verbatim, and fleet SKILL.mds carry ⚠ · — ⇒ ✓ freely.
# The Windows console is cp1252, which cannot encode most of those: printing an
# unmodified finding raised UnicodeEncodeError and took the whole probe down --
# a report-only probe crashing the daily guard it runs inside. Degrade the
# characters, never the run. (Found by running against the live checkout; the
# unit tests used ASCII fixtures and sailed straight past it.)
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:  # pragma: no cover -- non-reconfigurable stream
    pass

# Overridable so tests and other checkouts do not hardcode one machine's layout.
SNAPSHOT_PATH = os.environ.get(
    "ORA_PORTFOLIO_SNAPSHOT",
    r"C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json")

# BOTH fleets. CC/MCP SKILL.mds live under ~/.claude; LAMS/Cowork ones live on
# OneDrive. Overridable so tests and other machines are not pinned to one layout.
SPEC_ROOTS = [
    ("CC", os.environ.get("ORA_CC_TASKS_DIR",
                          os.path.join(CLAUDE, "scheduled-tasks"))),
    ("LAMS", os.environ.get(
        "ORA_LAMS_TASKS_DIR",
        r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled")),
]

SEVERITY_RE = re.compile(r"\b(info|warn|error)\b", re.IGNORECASE)

# How far apart an identity mention and a severity token may sit and still count
# as one claim. 0 = SAME LINE ONLY, and that is load-bearing.
#
# This was 1 until a run against the live checkout proved it wrong. Real fleet
# specs keep the severity word and the flag identity on one long unwrapped line
# ("- Known permanent **`warn`** flag ... `loans · name` -- ...", live line 59),
# so a window buys nothing on real text. What it DID buy was a false positive:
# ora-cc-snapshot-refresh's own threshold bullet, "**`info`-only, or
# `warn`-flags-all-allowlisted => no email.**", sits one line above the allowlist
# bullet naming "Loan Index row 24" -- so a 1-line window read a RULE as a CLAIM
# and reported drift against a file that was already correct. A probe that cries
# wolf on the fixed state is worse than no probe.
WINDOW = 0

# Flag identities that specs pin BY NAME. Static on purpose: derived-from-live
# matchers cannot detect a pinned flag that has VANISHED from the snapshot, which
# is exactly the allowlist-rot case (a dead allowlist entry silently stops
# covering anything, and the next flag to occupy that slot is unguarded).
#
# EMPTY as of 2026-09-03 (OI-212 close-out). The one entry ever pinned here --
# loans/name, "Loan Index row 24 is tombstoned" -- did its job: it caught OI-171
# (2026-08-16), and OI-212's re-diagnosis (reading the 08-17/08-24
# ora-cc-snapshot-refresh transcripts) found the underlying workbook condition
# itself had resolved around 2026-08-16/17. ora-cc-snapshot-refresh/SKILL.md v1.5
# (2026-08-28) retired the RATIFIED-TOMBSTONE ALLOWLIST this entry guarded and now
# states plainly "No allowlist is currently active." Everything this probe kept
# matching after that point was the v1.5 retirement changelog and the STEP 5
# recurrence-warning bullet ("if it reappears ... it is NOT allowlisted -- it
# emails") -- both intentional, load-bearing, permanent text, not a live claim.
# check_allowlist_rot matches identity patterns anywhere in the spec text with no
# way to tell a changelog entry from an active pin, so a resolved entry left in
# this list produces exactly the "permanent unfixable noise" collect_spec_sources
# already avoids for archived specs -- a probe that cries wolf on an
# already-fixed, already-documented file gets ignored, which is the failure this
# whole probe exists to prevent (see module docstring).
#
# If ora-cc-snapshot-refresh's STEP 5 gate ever needs a NEW ratified allowlist (a
# fresh Gabriel ruling -- the SKILL.md's own text is explicit that a recurrence
# is "not automatic reinstatement"), add its identity here fresh. Do not
# resurrect the retired entry by uncommenting it: the rawValue/issue_substr it
# guarded is retired history now, quoted verbatim in the SKILL.md changelog, not
# a spec claim to keep re-checking against live data. The matching algorithm
# itself stays covered by test-spec-liveness-probe.py's own synthetic fixture,
# independent of whatever is (or isn't) pinned here in production.
PINNED_FLAGS = []


def load_live_flags(path):
    """Live dataQuality[] as a list, [] if the key is absent, or None if the
    snapshot cannot be read or parsed. None means 'could not look' and is NEVER
    reported as 'nothing wrong'."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    flags = data.get("dataQuality")
    if flags is None:
        return []
    if not isinstance(flags, list):
        return None
    return flags


def _match_live(pinned, live_flags):
    """The live flag this pinned identity refers to, or None if it is gone."""
    for f in live_flags:
        if not isinstance(f, dict):
            continue
        if (f.get("entity") == pinned["entity"]
                and f.get("field") == pinned["field"]
                and pinned["issue_substr"] in str(f.get("issue", ""))
                and str(f.get("rawValue", "")) == pinned["raw_value"]):
            return f
    return None


def _claims_in(text, pinned):
    """(lineno, asserted_severity, surface) for each severity token sitting
    within WINDOW lines of a mention of this pinned flag.

    The window is what separates a CLAIM ABOUT A FLAG from a THRESHOLD RULE.
    "Email only if at least one entry is `severity: \"warn\"`" names no flag, so
    it never enters this function's output -- which matters, because that rule
    legitimately says `warn` no matter what the live flag's severity is, and
    reporting it would be a permanent false positive."""
    lines = text.splitlines()
    hit_lines = [i for i, ln in enumerate(lines)
                 if any(p.search(ln) for p in pinned["identity_patterns"])]
    if not hit_lines:
        return []
    out = []
    for i in hit_lines:
        lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
        for j in range(lo, hi):
            toks = {m.group(1).lower() for m in SEVERITY_RE.finditer(lines[j])}
            if toks:
                out.append((j + 1, toks, lines[j].strip()))
    return out


def check_severity_drift(sources, live_flags, pinned_flags=None):
    """sources = [(label, text)]. One finding per (source, pinned flag) whose
    asserted severity conflicts with the live snapshot.

    Reports EVERY conflicting source, not just the first -- the identity-drift
    check in doctrine-integrity-probe.py carries the same note because 38 sources
    drifted at once there, and a first-hit-only report lets the rest survive a
    'fixed it' claim.

    pinned_flags defaults to the module-level PINNED_FLAGS (production, currently
    empty -- see its own comment). Tests pass a synthetic fixture explicitly so
    the matching algorithm stays exercised independent of what production pins."""
    if pinned_flags is None:
        pinned_flags = PINNED_FLAGS
    if live_flags is None:
        return []
    out = []
    for label, text in sources:
        for pinned in pinned_flags:
            live = _match_live(pinned, live_flags)
            if live is None:
                continue  # vanished -> allowlist rot's job, not a severity claim
            actual = str(live.get("severity", "")).lower()
            # A line SATISFIES the live value if ANY severity token on it matches.
            # Order-independent on purpose: a correct spec often cites the history
            # alongside the current value ("was `info`, now reads `warn`", and the
            # real post-fix line 59 does exactly this). Taking only the first token
            # made the verdict depend on word order and reported drift against an
            # accurate spec -- a probe that cries wolf on the fixed state gets
            # ignored, which is the failure this whole probe exists to prevent.
            # Drift is therefore: the line names a severity and NONE of them is live.
            bad = [(ln, toks, surf) for ln, toks, surf in _claims_in(text, pinned)
                   if actual not in toks]
            if not bad:
                continue
            ln, toks, surf = bad[0]
            extra = "" if len(bad) == 1 else " (+%d more line(s))" % (len(bad) - 1)
            out.append(
                "%s asserts severity %s for %s -- live snapshot says %r "
                "(line %d: %r)%s"
                % (label, "/".join(sorted(toks)), pinned["key"], actual, ln,
                   surf[:120], extra))
    return out


def check_allowlist_rot(sources, live_flags, pinned_flags=None):
    """One finding per source that pins a flag identity no longer present live.

    Direction matters: a dead pin is low-harm on its own, but it means the
    suppression it authorises now covers nothing, so whatever next occupies that
    slot is unguarded.

    pinned_flags defaults to the module-level PINNED_FLAGS (production, currently
    empty -- see its own comment). Tests pass a synthetic fixture explicitly so
    the matching algorithm stays exercised independent of what production pins."""
    if pinned_flags is None:
        pinned_flags = PINNED_FLAGS
    if live_flags is None:
        return []
    out = []
    for label, text in sources:
        for pinned in pinned_flags:
            if _match_live(pinned, live_flags) is not None:
                continue
            if not any(p.search(text) for p in pinned["identity_patterns"]):
                continue
            out.append(
                "%s pins flag %r (%s · %s) but NO live dataQuality entry matches "
                "it -- the pin is dead and suppresses nothing"
                % (label, pinned["key"], pinned["entity"], pinned["field"]))
    return out


def collect_spec_sources():
    """(label, text) for every readable fleet SKILL.md across BOTH fleets.

    Scanning only CC/MCP would have been a silent half-sweep: the probe prints
    "N spec(s) checked", which reads as complete coverage, while a LAMS/Cowork
    spec asserting a stale severity sailed through unexamined. governor-drift-
    probe.py:61 closed this identical gap for its DSCR/LTV sweep on 2026-07-24
    ("BOTH fleets"); this matches that precedent rather than re-opening it.

    Archived task folders are skipped -- a retired spec's stale claim is history,
    not drift, and flagging it would be permanent unfixable noise.

    Fail-open: an absent tree (LAMS lives on OneDrive and may not be synced on
    every machine) contributes nothing rather than raising."""
    out = []
    for fleet, root in SPEC_ROOTS:
        if not os.path.isdir(root):
            continue
        try:
            entries = sorted(os.listdir(root))
        except Exception:
            continue
        for entry in entries:
            if entry.startswith("_archive") or entry.startswith("_"):
                continue
            p = os.path.join(root, entry, "SKILL.md")
            if not os.path.isfile(p):
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    out.append(("[%s] %s/SKILL.md" % (fleet, entry), fh.read()))
            except Exception:
                continue
    return out


def run(sources, live_flags):
    """Print findings. ALWAYS returns 0 -- report-only by design."""
    if live_flags is None:
        print("[SKIP] snapshot unreadable at %s -- cannot verify spec claims "
              "against live data. This is 'could not look', NOT 'nothing wrong'."
              % SNAPSHOT_PATH)
        return 0
    findings = check_severity_drift(sources, live_flags) + \
        check_allowlist_rot(sources, live_flags)
    if not findings:
        print("[OK] %d spec(s) checked against %d live flag(s) -- no claim drift."
              % (len(sources), len(live_flags)))
        return 0
    print("[DRIFT] %d spec claim(s) disagree with the live snapshot:" % len(findings))
    for f in findings:
        print("  - %s" % f)
    print("\nA spec asserting a stale runtime value is how OI-171 happened: the "
          "severity gate was written around a flag severity that had changed 21 "
          "hours earlier, so the gate never suppressed anything.")
    return 0


def main():
    return run(collect_spec_sources(), load_live_flags(SNAPSHOT_PATH))


if __name__ == "__main__":
    sys.exit(main())
