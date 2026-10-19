#!/usr/bin/env python3
"""R-05 send-contract lint for scheduled-task specs (ratified by Gabriel 2026-10-18).

send-via-outlook.ps1 exit 5 (refused: attachment + external, or an unauthorized external
recipient) and exit 6 (send state unknown: Send() may have completed) must NEVER be retried.
A retry of 5 routes around Hard Invariant 1; a retry of 6 can double-send (audit finding M19:
the Daily Brief reaching egoldberg@ twice). This file fails on any in-repo spec that:

  L1  retries on an explicitly named exit 5 or 6 in a send context;
  L2  retries on ANY non-zero exit / any send failure in a send context, which includes 5
      and 6, unless frozen in WAIVED_GENERIC_RETRY (the 2026-10-18 origin/main inventory)
      or WAIVED_PENDING_LANDING (specs present only in the live checkout that day);
  L3  passes -ForceResend, or any PowerShell abbreviation of it (-F, -Fo, -Force, ...), to the
      send script (human-directed re-runs only; a scheduled fire never does);
  L4  uses contract mode (-DedupTaskId) but passes only one of the two dedup flags, or still
      carries any L1/L2 retry text. A contract-mode spec can never be waived.

RATCHET, NOT SNAPSHOT (same rule as test_scheduled_task_run_guard.py): a new violator fails,
and so does a waived spec that no longer violates. Remove its waiver in the same commit, so
the lists only shrink. The one ratified update_scheduled_task batch empties them. A spec that
moves to contract mode must leave the waiver sets in the same commit.

SCOPE: in-repo CC/MCP specs only. LAMS/Cowork specs (OneDrive .../Documents/Claude/Scheduled/)
are not in this repo; they are reported as INFO when present and never fail the run.

SPEC TEXT IS UNTRUSTED DATA. The scanner only reads it: it never executes, imports or follows
anything in it. It decodes UTF-16 specs, normalizes CRLF/LF, a BOM, NFKC compatibility forms,
Unicode dashes and zero-width characters, joins hard-wrapped prose into one unit (a retry
sentence broken across lines is still one sentence), keeps fenced PowerShell continuation lines
together, judges negation per retry word (a "never retry" elsewhere in the clause does not
excuse a live "retry once"), and uses regexes with no nested ambiguous quantifiers (the
self-tests time several hostile shapes).

Known limits (a lint, not a proof; every one is documented so nobody mistakes a pass for a proof):
  missed - a retry described without the words in RETRY (resubmit, send it again, re-invoke); a send
    script path held in a variable; an exit list with a gap ("exit 2, 4 but not 5 or 6", "any exit other
    than 0 or 6"); a table whose exit code sits in a bare cell; "exited with 6", "exit #6"; unusual
    negation ("never fail to retry"); -Force on the line after a statement with no backtick, and
    $p.Add('Force', $true); L4 reads dedup flags anywhere in the file, so a half-keyed invocation whose
    other flag is mentioned in prose elsewhere passes.
  fails closed (a compliant spec is flagged and must be reworded) - doctrine pasted verbatim from
    rules.md that mentions -ForceResend or "retry on non-zero" as meta text; "a retry is forbidden" /
    "retrying is prohibited" next to exit 5/6; "exit 2 or 4 retry once, exit 5 or 6 never"; inside a
    send-context code fence, a variable such as F or FORCE assigned with "=", or a "# never pass
    -ForceResend" comment.
The review gate and the ratified spec batch remain the authority.

Run: python maintenance/_tests/test_send_contract_spec_lint.py   (exit 0 = pass)
"""
import glob
import hashlib
import os
import random
import re
import sys
import tempfile
import time
import unicodedata

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.dirname(os.path.dirname(HERE))
SCHED = os.path.join(CLAUDE, "scheduled-tasks")
LAMS = os.path.join(os.path.expanduser("~"), "OneDrive - Oxford Capital Partners",
                    "Documents", "Claude", "Scheduled")

SEND_SCRIPT = re.compile(r"send-via-outlook\.ps1", re.I)
SEND = re.compile(r"send-via-outlook\.ps1|Outlook COM|COM send|COM exit|send exit", re.I)
# "re-run" counts only when it is the send being re-run ("re-run the send", "re-run it"), not a probe.
RETRY = re.compile(r"(?<![A-Za-z0-9])retr(?:y|ies|ied|ying)(?![A-Za-z0-9])|\bre-?send\b|\btry\s+again\b"
                   r"|\bre-?run\s+(?:it\b|the\s+(?:send|script|command|helper|same)|send-via)"
                   r"|\bre-?attempt\b|\bsecond\s+attempt\b|\bonce\s+more\b|\bone\s+more\s+time\b",
                   re.I)
# A negation binds to a retry/exit mention only when it sits directly before it ("do NOT retry",
# "never exit 5/6", "NOT every failure retries", "no further retries", "without any retry").
# "do not hesitate to retry", "do not delay retrying", "not just exit 5/6", "do not skip exit 5/6",
# "no cc, retry" and "without delay retry" are NOT negations: between a negator and its target
# only one of a few adverbs (ever, automatically, blindly, immediately, ...) may stand.
NEG_PREFIX = re.compile(
    r"(?:(?:\bdo\s+not|\bdon't|\bnever|\bmust\s+not|\bmustn't|\bnor|\bexcept|\bexcluding|\bother\s+than)\s+"
    r"(?:(?:ever|automatically|blindly|immediately|simply|further|also|then|again|retry|re-?send)\s+){0,1}"
    r"|\bnot\s+(?:(?:a|an|the|every|all|any|always|even)\s+(?:[\w'/-]+\s+)?)?"
    r"|\bno\s+(?:further\s+|more\s+)?"
    r"|\bwithout\s+(?:any\s+|a\s+)?)[`\"'*_(]*$", re.I)
# L3 counts only an unambiguous prohibition as a negation of -ForceResend.
FORCE_NEG_PREFIX = re.compile(r"(?:\bnever|\bdon't|\bdo\s+not|\bmust\s+not|\bmustn't)\s+"
                              r"(?:(?!to\b)[\w'/`\"*_-]+\s+){0,2}[`\"'*_(]*$", re.I)
# The SEND SCRIPT'S own bounded retry ("it already performs one bounded internal retry on
# RPC_E_CALL_REJECTED") is not a caller retry. Only that subject-verb form is stripped; "do one
# bounded retry on exit 6" is a caller instruction and stays.
RETRY_INTERNAL = re.compile(r"\b(?:it|the\s+(?:send\s+)?(?:script|helper))\s+(?:already\s+|itself\s+)?"
                            r"(?:performs?|does|makes|runs)\s+(?:one\s+|a\s+|an\s+)?"
                            r"(?:(?:bounded|internal|built-in|automatic)\s+){1,3}retr\w*", re.I)
# Exit-number list ending in 5 or 6 ("exit 6", "exits 5/6", "exit codes 2, 4, 5 and 6",
# "exit code (6)", "code 6", "$LASTEXITCODE -in 5,6"). Every list item must consume a digit, so
# whitespace runs can only be matched one way (no exponential backtracking).
_NUMSEP = r"(?:\s*[,/]\s*(?:(?:and|or)\s+)?|\s+(?:and|or)\s+|\s+)"
EXPLICIT_56 = re.compile(
    r"(?:\bexit(?:s|ed)?(?:[\s-]*(?:codes?|status))?(?:\s+with\s+codes?)?|\b(?:return|error)\s*codes?"
    r"|\bstatus|\bcodes?|\bLASTEXITCODE|\berrorlevel|\breturn(?:s|ed)?)"
    r"[\s-]*(?:of\s+|is\s+|=+\s*|:\s*|-eq\s+|-in\s+|\(\s*)?(?:\d+" + _NUMSEP + r")*[56]\b"
    r"|\bexit(?:\s+codes?)?\s*[1-5]\s*(?:-|to|through)\s*6\b", re.I)
GENERIC = re.compile(r"\bnon[\s-]?zero|\bany\s+(?:send\s+)?(?:failure|error)|\bon\s+(?:any\s+)?error\b|"
                     r"\bon\s+(?:a\s+)?(?:COM\s+)?(?:send\s+)?failure|\bif\s+(?:the\s+)?send\s+fails|"
                     r"\bif\s+it\s+fails\b(?!\s+again)|-ne\s*0\b|-gt\s*0\b|-ge\s*[1-5]\b|!=\s*0\b|>=\s*[1-5]\b", re.I)
# Per-code wording that is compliant even though it names a generic failure phrase. Each form ties
# the word "only" to the retry and a list of exit codes 1-4 (never 5/6): "retry only on exit 2 or 4",
# "only exit 2 or 4 is ever retried", "retry exit 2/4 only". "retry only once (exit 2 or 4)" is NOT
# per-code wording. EXCEPT_BOTH: "any non-zero exit except exit 5/6" (both codes must be excluded).
_L14 = (r"(?:[1-4]\s*(?:,|/|\bor\b|\band\b)\s*)*[1-4]\b(?!\s*(?:,|/|\bor\b|\band\b)?\s*(?:exit\s*)?[56]\b)")
PERCODE = re.compile(r"\bretr\w*\s+only\s+(?:on|for|when|if)\s+exits?(?:\s+codes?)?\s*" + _L14
                     + r"|\bonly\s+exits?(?:\s+codes?)?\s*" + _L14 + r"\s+(?:is|are)\s+(?:ever\s+)?retr\w*"
                     + r"|\bretr\w*\s+exits?(?:\s+codes?)?\s*" + _L14 + r"\s+only\b", re.I)
EXCEPT_BOTH = re.compile(r"\b(?:except|excluding|other\s+than|but\s+not|but\s+never)\b[^.;]{0,25}?"
                         r"\bexits?\s*(?:codes?\s*)?(?:5\s*(?:,|/|\bor\b|\band\b)\s*(?:exit\s*)?6"
                         r"|6\s*(?:,|/|\bor\b|\band\b)\s*(?:exit\s*)?5)\b", re.I)
CLAUSE = re.compile(r"(\.(?=\s|$)|;|\s[\u2014\u2013]\s|\s--\s)")
WINDOW = 6

# PowerShell resolves any unambiguous prefix of a parameter name. ForceResend is the only
# send-script parameter starting with F, so -F, -Fo, -For, -Forc, -Force ... -ForceResend all bind it.
_FORCE_NAME = r"F(?:o(?:r(?:c(?:e(?:R(?:e(?:s(?:e(?:n(?:d)?)?)?)?)?)?)?)?)?)?"
FORCE_FULL = re.compile(r"(?<![\w])[-/]ForceResend\b|\bForceResend\s*[=:]", re.I)
FORCE_ABBR = re.compile(r"(?<![\w$-])-" + _FORCE_NAME + r"(?![\w-])", re.I)
FORCE_SPLAT = re.compile(r"@\{[^}]{0,300}?(?<![\w])" + _FORCE_NAME + r"['\"]?\s*=", re.I)
DEDUP_TASK = re.compile(r"(?<![\w])-DedupT\w*", re.I)
DEDUP_PERIOD = re.compile(r"(?<![\w])-DedupP\w*", re.I)
_ZW = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u00ad"), None)
# PowerShell accepts a Unicode dash as the parameter prefix ("\u2013Force"); a dash glued to a letter is a flag.
_UDASH = re.compile(r"(?<![\w])[\u2010-\u2015\u2212](?=[A-Za-z])")
FENCE = re.compile(r"^\s*(?:```|~~~)")
# one [\s,]* class between words, so a run of spaces can only be matched one way (no backtracking blowup)
ACTION_ONLY = re.compile(r"^\s*(?:[-*+]\s+|\d{1,3}[.)]\s+)?[*_`]*"
                         r"(?:(?:immediately|then|now|simply|just|again|once|automatically|always"
                         r"|wait\s+\d+\s*[a-z]+)\b[\s,]*)*(?:retry|retries|re-?send|try\s+again|re-?run)", re.I)
BLOCK_START = re.compile(r"^\s*(?:[-*+>]\s|\d{1,3}[.)]\s|#{1,6}\s|\|)")
PSCONT = re.compile(r"(?:`|\^)\s*$")

WAIVED_GENERIC_RETRY = frozenset({
    "ora-am-brief", "ora-appsec-sweep", "ora-audit-log-sweep", "ora-broker-touch-cadence",
    "ora-cc-snapshot-refresh", "ora-command-center-mirror-drift-check", "ora-county-sales-monitor",
    "ora-deal-command-board", "ora-deal-sourcing-scan", "ora-doctrine-integrity-guard", "ora-entry-market-scan",
    "ora-excess-usage-sweep", "ora-financial-code-integrity-sweep", "ora-forward-calendar-digest",
    "ora-health-guard", "ora-hubspot-renewal-closeout-tasks", "ora-incentive-registry-refresh",
    "ora-jackson-boe-prep-reminder", "ora-lease-snapshot-refresh", "ora-loan-balance-check",
    "ora-loopnet-listings-sync", "ora-master-workbook-ingest", "ora-monthly-portfolio-briefing",
    "ora-noi-opportunity-digest", "ora-open-sessions-board", "ora-passed-deal-tracker",
    "ora-pm-monthly-billing", "ora-pr-land-watch", "ora-prepush-gate-sweep", "ora-recovery-billing-monthly",
    "ora-recovery-structure-audit-annual", "ora-renewal-hubspot-reconcile", "ora-site-exposure-probe",
    "ora-sourcing-construction-verify", "ora-task-integrity-guard", "ora-tenant-hubspot-reconciliation",
    "ora-vacancy-aging-report", "ora-weekly-hygiene", "ora-wicomico-reassessment-reminder",
})
WAIVED_PENDING_LANDING = frozenset({
    "ora-agent-usage-report-monthly", "ora-doc-index-rebuild-monthly", "ora-edge-mfg-scout-weekly",
    "ora-edge-news-overlay-refresh", "ora-full-gate-weekly", "ora-quarterly-estimate-check",
    "ora-rep-hours-monthly", "ora-site-market-snapshot-refresh", "ora-site-seo-crawl-weekly",
})
# name -> (sha256[:16] of the ONE reviewed explicit-5/6 unit's normalized text, why it is not a send-exit
# retry). Any edit to that unit (or a new retry joined into it) changes the hash and fails L1.
REVIEWED_NOT_SEND_EXIT = {
    "ora-aaos-expire-leases": ("350b7b59f0cee2e9",
                               "its 'exit 5 (EVENT COMMIT FAILURE): retry' is the aaos tool's own exit "
                               "code; the retry targets that tool, and the email is sent once after it"),
}

failures = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else " -- " + detail))
    if not cond:
        failures.append(name)


def normalize(text):
    text = _UDASH.sub("-", unicodedata.normalize("NFKC", text).translate(_ZW))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_spec(path):
    """Spec text from disk. UTF-16 (PowerShell 5 Out-File default) is decoded, not mangled."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data[:4096]:
        return data.decode("utf-16-le", errors="replace")
    return data.decode("utf-8", errors="replace")


def build_units(lines):
    """Group lines into sentence units: [(first_idx, last_idx, text, in_fence)].
    Prose: a blank line, a bullet/number/heading/table row, or a fence starts a new unit, so
    hard-wrapped text joins; a bullet right after a line ending in ':' joins its header
    ("On exit 6:" then "- retry once"). Fenced code: a line ending in ` or ^ continues."""
    units, cur, fence = [], None, False

    def close():
        nonlocal cur
        if cur:
            units.append((cur[0], cur[1], " ".join(cur[2]), cur[3]))
        cur = None

    for i, ln in enumerate(lines):
        if FENCE.match(ln):
            close()
            fence = not fence
            continue
        if not ln.strip():
            close()
            continue
        if fence:
            if cur and PSCONT.search(lines[i - 1]):
                cur[1] = i
                cur[2].append(ln.strip())
            else:
                close()
                cur = [i, i, [ln.strip()], True]
            continue
        if cur and (not BLOCK_START.match(ln) or (cur[2][-1].rstrip("*_` \t").endswith(":") and ACTION_ONLY.match(ln))):
            cur[1] = i
            cur[2].append(ln.strip())
        else:
            close()
            cur = [i, i, [ln.strip()], False]
    close()
    return units


EXCL_PREFIX = re.compile(r"(?:\bexcept|\bexcluding|\bother\s+than)\s+(?:[\w'/-]+\s+){0,1}$", re.I)


def _neg_before(text, pos):
    return bool(NEG_PREFIX.search(text[max(0, pos - 60):pos]))


DEDUP_NEG = re.compile(r"\b(?:not|never|no|without|yet)\b[^.;\n]{0,30}$", re.I)


def _force_neg_before(text, pos):
    return bool(FORCE_NEG_PREFIX.search(text[max(0, pos - 60):pos]))


def classify_text(text, ctx=None):
    """'explicit', 'generic' or None for one unit of text (ctx = surrounding text for SEND)."""
    if not SEND.search(text if ctx is None else ctx):
        return None
    parts = CLAUSE.split(RETRY_INTERNAL.sub(" ", text))
    clauses, seps = parts[0::2], parts[1::2]
    found = None
    for i, clause in enumerate(clauses):
        # negation is judged per retry word: "retry once and never retry again" still retries
        live = [m for m in RETRY.finditer(clause) if not _neg_before(clause, m.start())]
        if not live:
            continue
        scope = clause
        if i and seps[i - 1].strip() in ("\u2014", "\u2013", "--") and live[0].start() < 60:
            scope = clauses[i - 1] + " " + clause  # "On non-zero exit -- retry once": condition, then action
        for m in EXPLICIT_56.finditer(scope):
            if not _neg_before(scope, m.start()):
                return "explicit"
            # "except exit 5/6, which are retried after a probe" still retries those codes
            if EXCL_PREFIX.search(scope[max(0, m.start() - 40):m.start()]) and any(
                    not _neg_before(scope, r.start()) for r in RETRY.finditer(scope, m.end())):
                return "explicit"
        # per-code wording is cut out first: a generic retry beside it must still be seen
        rest = PERCODE.sub(" ", scope)
        if GENERIC.search(rest) and not EXCEPT_BOTH.search(rest) and any(
                not _neg_before(rest, r.start()) for r in RETRY.finditer(rest)):
            found = "generic"  # keep scanning: a later clause may be an explicit exit 5/6 retry
    return found


def classify(lines, i):
    """Single-line helper kept for the fixtures: 'explicit', 'generic' or None for line i."""
    ctx = "\n".join(lines[max(0, i - WINDOW): i + WINDOW + 1])
    return classify_text(lines[i], ctx)


FORCE_KEY = re.compile(r"(?<![\w$-])['\"]?" + _FORCE_NAME + r"['\"]?\s*(?:\]\s*)?=\s*\$|\[\s*['\"]" + _FORCE_NAME
                       + r"['\"]\s*\]\s*=|['\"]-" + _FORCE_NAME + r"['\"]", re.I)


def fenced_blocks(lines):
    """[(first_idx, last_idx, text)] for each fenced code block (an unclosed fence runs to the end)."""
    blocks, cur, fence = [], None, False
    for i, ln in enumerate(lines):
        if FENCE.match(ln):
            if fence:
                blocks.append((cur[0], i, "\n".join(cur[1])))
                cur = None
            else:
                cur = [i, []]
            fence = not fence
        elif fence:
            cur[1].append(ln)
    if fence and cur:
        blocks.append((cur[0], len(lines) - 1, "\n".join(cur[1])))
    return blocks


def _cut_at_separator(s, start):
    """s[start:] up to the first statement separator (; | &) outside a quoted string. Quote state
    is tracked from the beginning of s, so a script path that is itself quoted stays balanced."""
    q = None
    for k, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch == '"' or (ch == "'" and (k == 0 or not s[k - 1].isalnum())):
            q = ch
        elif ch in ";|&" and k >= start:
            return s[start:k]
    return s[start:]


def _force_hit(text, in_fence, has_send):
    """True if this unit passes -ForceResend (or an abbreviation) to the send script."""
    for m in FORCE_FULL.finditer(text):
        if in_fence or not _force_neg_before(text, m.start()):
            return True
    if has_send and FORCE_SPLAT.search(text):
        return True
    m = SEND_SCRIPT.search(text)
    if m:
        seg = _cut_at_separator(text, m.end())
        for f in FORCE_ABBR.finditer(seg):
            if in_fence or not _force_neg_before(seg, f.start()):
                return True
    return False


def scan_text(text):
    lines = normalize(text).split("\n")
    hits = {"explicit": [], "explicit_text": [], "generic": [], "force": []}
    for first, last, utext, in_fence in build_units(lines):
        ctx = "\n".join(lines[max(0, first - WINDOW): last + WINDOW + 1])
        kind = classify_text(utext, ctx)
        if kind:
            hits[kind].append(first + 1)
            if kind == "explicit":
                hits["explicit_text"].append(utext)
        if _force_hit(utext, in_fence, bool(SEND.search(ctx))):
            hits["force"].append(first + 1)
    for first, last, btext in fenced_blocks(lines):
        # a splat or argument array spread over several lines: judged on the whole block, in send context
        if SEND.search("\n".join(lines[max(0, first - WINDOW): last + WINDOW + 1])) and (
                FORCE_KEY.search(btext) or FORCE_SPLAT.search(btext) or FORCE_FULL.search(btext)):
            hits["force"].append(first + 1)
    joined = "\n".join(lines)
    has_task = any(not DEDUP_NEG.search(joined[max(0, m.start() - 40):m.start()])
                   for m in DEDUP_TASK.finditer(joined))
    has_period = any(not DEDUP_NEG.search(joined[max(0, m.start() - 40):m.start()])
                     for m in DEDUP_PERIOD.finditer(joined))
    hits["contract"] = has_task or has_period
    hits["contract_complete"] = has_task and has_period
    return hits


def evaluate(name, text, waived_generic, waived_pending, reviewed):
    """Ratchet verdict for one spec: [(label, ok, detail)]. Pure; used by main and the self-tests."""
    out = []
    h = scan_text(text)
    waived = name in waived_generic or name in waived_pending
    if h["force"]:
        out.append(("L3 %s never passes -ForceResend" % name, False, "lines %s" % h["force"]))
    if h["contract"]:
        out.append(("L4 %s passes both dedup flags" % name, h["contract_complete"], ""))
        out.append(("L4 %s (contract mode) carries no retry text" % name,
                    not h["explicit"] and not h["generic"], "lines %s" % (h["explicit"] + h["generic"])))
        if waived or name in reviewed:
            out.append(("L4 %s is in contract mode: remove it from the waiver/review sets" % name, False,
                        "a contract-mode spec can never be waived"))
        return out
    if name in reviewed:
        want = reviewed[name][0]
        got = [hashlib.sha256(u.encode("utf-8")).hexdigest()[:16] for u in h["explicit_text"]]
        out.append(("L1 %s reviewed non-send exit-5 wording is unchanged" % name, got == [want],
                    "expected exactly one explicit unit with hash %s, got %s (lines %s); a changed unit "
                    "must be re-reviewed, any other exit 5/6 retry is a real violation"
                    % (want, got, h["explicit"])))
    elif h["explicit"]:
        out.append(("L1 %s does not retry an explicit exit 5/6" % name, False, "lines %s" % h["explicit"]))
    if h["generic"] and not waived:
        out.append(("L2 %s does not retry on any non-zero send exit" % name, False,
                    "lines %s -- move it to contract mode or per-code wording (rules.md section 2)"
                    % h["generic"]))
    if waived and not h["generic"]:
        out.append(("L2 %s waiver still needed" % name, False,
                    "no generic retry left; remove it from the waiver set in this commit"))
    return out


def failing(rows):
    return [r[0] for r in rows if not r[1]]


# --- classifier fixtures (real spec wording, 2026-10-18) -------------------------------------
print("\nclassifier fixtures")
FIXTURES = [
    ("On non-zero COM exit: retry once, then flag \u2014 do NOT halt.", "generic"),
    ("On COM send failure: retry once; if it still fails, do not halt", "generic"),
    ("Exit-code doctrine: exit 2 (COM failure) or 4 (timeout) \u2192 retry once then flag loudly; "
     "exit 1 (usage) or 3 (stuck Outlook wizard) \u2192 do NOT retry, flag immediately.", None),
    ("On a non-zero send exit, act on the exit code (rules.md \u00a72 per-code table) -- NOT every failure retries:", None),
    ("If send-via-outlook.ps1 exits non-zero, flag this loudly \u2014 a failed run needs a human look, "
     "not a quiet retry next month.", None),
    ("send-via-outlook.ps1 exit 6: retry once.", "explicit"),
    ("send-via-outlook.ps1 exit 5 or exit 6: do NOT retry, flag immediately.", None),
    ("send-via-outlook.ps1: exit 2 or 4 -> retry once.", None),
    ("Exit 2 (USAGE ERROR) or exit 5 (EVENT COMMIT FAILURE): retry the exact same command once. "
     "If it fails again, send exactly one email via send-via-outlook.ps1", "explicit"),
    ("Notion create failed: retry once.", None),
    # hardening fixtures: wording variants the original classifier missed or mishandled
    ("send-via-outlook.ps1 exit codes 2, 4, 5 and 6: retry once.", "explicit"),
    ("send-via-outlook.ps1 exits 5/6 -> retry once.", "explicit"),
    ("send-via-outlook.ps1 exit 4 to 6: try again.", "explicit"),
    ("send-via-outlook.ps1: if $LASTEXITCODE -eq 6, re-run it.", "explicit"),
    ("send-via-outlook.ps1: if $LASTEXITCODE -in 5,6 then retry.", "explicit"),
    ("send-via-outlook.ps1 exits with code 6; retry once.", None),  # split at ';' -> no explicit in the retry clause
    ("send-via-outlook.ps1 exits with code 6, retry once.", "explicit"),
    ("send-via-outlook.ps1 exit-6: retry once.", "explicit"),
    ("send-via-outlook.ps1 exit code (6): retry once.", "explicit"),
    ("send-via-outlook.ps1 exit 2 through 6: retry once.", "explicit"),
    ("send-via-outlook.ps1 status 6 (state unknown): _retry_ once.", "explicit"),
    ("send-via-outlook.ps1: if $LASTEXITCODE -ne 0, retry.", "generic"),
    ("On a non-zero Outlook COM exit, re-run the send once.", "generic"),
    ("send-via-outlook.ps1: on non-zero exit \u2014 retry once.", "generic"),
    ("send-via-outlook.ps1: on exit 6 -- retry once.", "explicit"),
    ("send-via-outlook.ps1: exit 2 (COM failure) or 4 (timeout) -- retry once, then flag loudly if it fails again.", None),
    ("send-via-outlook.ps1: if it fails, retry once.", "generic"),
    ("Do not hesitate to retry send-via-outlook.ps1 on any non-zero exit.", "generic"),
    ("On exit 6 from send-via-outlook.ps1: never retry; flag immediately.", None),
    ("On any send failure, retry once.", None),  # no send context in the text or its window
    ("Route via send-via-outlook.ps1 to ggoldberg ONLY -- no cc, retry once on COM failure then flag.", "generic"),
    ("On a non-zero exit from send-via-outlook.ps1 it already performs one bounded internal retry; "
     "at the task level, do not retry beyond that.", None),
    # a negation elsewhere in the clause must not excuse a live retry (negation is per retry word)
    ("send-via-outlook.ps1 on exit 6, retry once and never retry a second time.", "explicit"),
    ("send-via-outlook.ps1 on exit 5 or 6, retry once without re-running the probe.", "explicit"),
    ("send-via-outlook.ps1 on a non-zero send exit, retry once and do not retry again.", "generic"),
    # compliant per-code doctrine must not trip the lint
    ("send-via-outlook.ps1: only exit 2/4 is retried, never exit 5/6.", None),
    ("send-via-outlook.ps1: retry exit 2 or 4 once, never exit 5 or 6.", None),
    ("send-via-outlook.ps1 exit 6 means state unknown: re-run the Sent-Items probe; never retry exit 6.", None),
    ("On a non-zero send exit, retry only on exit 2 or 4.", None),
    ("On a non-zero COM exit: act on the exit code per Step 4 (only exit 2 or 4 is ever retried, once).", None),
    ("send-via-outlook.ps1: retry once on any non-zero exit except exit 5/6.", None),
    ("send-via-outlook.ps1: retry once on any non-zero exit except exit 5.", "generic"),
    # the exemptions must not hide a real retry (adversarial review round 2)
    ("send-via-outlook.ps1 on exit 6, do one bounded retry.", "explicit"),
    ("send-via-outlook.ps1 exit 6: automatic retry once.", "explicit"),
    ("send-via-outlook.ps1 on exit 5 or 6 perform one internal retry of the send.", "explicit"),
    ("send-via-outlook.ps1 on any non-zero exit, do a bounded retry once.", "generic"),
    ("send-via-outlook.ps1 on any non-zero exit, retry only once (typically exit 2 or 4).", "generic"),
    ("send-via-outlook.ps1 on a non-zero exit, retry only once, then flag exit 2 or 4 loudly.", "generic"),
    ("send-via-outlook.ps1 on any non-zero exit retry once, not only on exit 2 or 4.", "generic"),
    ("send-via-outlook.ps1: retry once on any non-zero exit, just as for exit 2 or 4.", "generic"),
    ("send-via-outlook.ps1 on any send failure, retry once (only exit 1 is fatal).", "generic"),
    ("send-via-outlook.ps1: retry once on any non-zero exit, not just exit 5/6.", "explicit"),
    ("send-via-outlook.ps1 on any non-zero exit retry once, and do not skip exit 5/6.", "explicit"),
    ("send-via-outlook.ps1 on any non-zero exit, retry once, not excepting exit 5 or 6.", "explicit"),
    ("send-via-outlook.ps1 on any non-zero exit retry once, never mind exit 5 or 6.", "explicit"),
    ("send-via-outlook.ps1: on exit 6 \u2014 after a 30-second pause, retry once.", "explicit"),
    ("send-via-outlook.ps1: on exit 6, without delay retry once.", "explicit"),
    ("send-via-outlook.ps1: on exit 6 with no output retry once.", "explicit"),
    ("send-via-outlook.ps1: if exit 6 and not delivered retry once.", "explicit"),
    ("send-via-outlook.ps1: only exit 2/4 is ever retried; exit 5/6 never.", None),
    ("send-via-outlook.ps1: retry exit 2/4 only.", None),
    ("send-via-outlook.ps1: on exit 6 there is no retry; flag it.", None),
    ("send-via-outlook.ps1: on exit 6 make no further retries.", None),
    ("send-via-outlook.ps1: on exit 6 proceed without any retry.", None),
    # round 3
    ("send-via-outlook.ps1 on any non-zero exit, retry once, and retry only on exit 2 or 4 a second time.", "generic"),
    ("send-via-outlook.ps1 on a non-zero exit retry once, and retry exit 2 or 4 only after a 30 s pause.", "generic"),
    ("send-via-outlook.ps1: retry once on any non-zero exit (only exit 2 or 4 are retried twice).", "generic"),
    ("send-via-outlook.ps1 on exit 6 do not delay retrying.", "explicit"),
    ("send-via-outlook.ps1 on exit 6 never hesitate retrying.", "explicit"),
    ("send-via-outlook.ps1 on a non-zero exit retry once \u2014 except exit 5/6, which are retried after a probe.", "explicit"),
    ("send-via-outlook.ps1 on a non-zero exit retry once, except exit 6, which is retried only after the probe.", "explicit"),
    ("send-via-outlook.ps1: on exit 6 do not ever retry.", None),
    ("send-via-outlook.ps1: on exit 6 never automatically retry.", None),
]
for text, want in FIXTURES:
    got = classify([text], 0)
    check("fixture -> %s: %s" % (want, text[:60]), got == want, "got %s" % got)
check("waiver sets are disjoint", not (WAIVED_GENERIC_RETRY & WAIVED_PENDING_LANDING))

# --- scanner self-tests: line endings, wrapping, fences, -Force abbreviations, ratchet, ReDoS ---
print("\nscanner self-tests")
PS = 'powershell -NoProfile -File "C:\\x\\send-via-outlook.ps1" -To "a@b.net" -Subject "s"'
for label, text, want in [
    ("abbrev -F", PS + " -F", True),
    ("abbrev -Fo", PS + " -Fo", True),
    ("abbrev -Force", PS + " -Force", True),
    ("abbrev -ForceR", PS + " -ForceR", True),
    ("full -ForceResend", PS + " -ForceResend", True),
    ("-ForceResend:$true", PS + " -ForceResend:$true", True),
    ("lower-case -forceresend", PS + " -forceresend", True),
    ("full-width -\uff26orce", PS + " -\uff26orce", True),
    ("zero-width inside -Force", PS + " -Fo\u200brce", True),
    ("en dash before Force", PS + " \u2013Force", True),
    ("em dash before F", PS + " \u2014F", True),
    ("splat ForceResend=", "$p = @{ ForceResend = $true }  # for send-via-outlook.ps1", True),
    ("splat Force=", "$p = @{ To = 'x'; Force = $true }; & send-via-outlook.ps1 @p", True),
    ("pipe inside a quoted subject", 'powershell -File send-via-outlook.ps1 -Subject "a | b" -Force', True),
    ("ampersand inside a quoted subject", 'powershell -File send-via-outlook.ps1 -To "R&D" -Force', True),
    ("semicolon inside a quoted subject", "powershell -File send-via-outlook.ps1 -Subject 'x; y' -F", True),
    ("Start-Process argument list", "Start-Process powershell -ArgumentList '-File','send-via-outlook.ps1','-Force'", True),
    ("excuse far away from the flag", "If the email did not arrive, re-run send-via-outlook.ps1 with -ForceResend.", True),
    ("-File is not -F", PS, False),
    ("-Subject is not -F", PS + " -Body x", False),
    ("-Force on a different statement", "Set-ExecutionPolicy -Scope Process Bypass -Force; " + PS, False),
    ("-Force after a separator", PS + "; Remove-Item x -Force", False),
    ("negated prose mention", "A scheduled fire never passes `-ForceResend` to send-via-outlook.ps1.", False),
    ("-Force with no send script", "Remove-Item x -Force", False),
]:
    check("L3 detection: %s" % label, bool(scan_text(text)["force"]) == want)
fenced = "```powershell\n" + PS.replace(' -To', ' `\n  -To') + " `\n  -ForceResend\n```\n"
check("L3 detection: fenced continuation line", bool(scan_text(fenced)["force"]))
for label, text in [
    ("multi-line hashtable splat", "```\n$p=@{\n  To='X'\n  Force=$true\n}\n& send-via-outlook.ps1 @p\n```\n"),
    ("hashtable index assignment", "```\n$p=@{}\n$p['Force'] = $true\n& send-via-outlook.ps1 @p\n```\n"),
    ("argument array", "```\n$a = @('-To','X','-Force')\n& send-via-outlook.ps1 @a\n```\n"),
]:
    check("L3 detection: %s" % label, bool(scan_text(text)["force"]))
check("L3 detection: a variable named $For is not a splat key",
      not scan_text("```\n$For = $x\n& send-via-outlook.ps1 -To a -Subject b\n```\n")["force"])
for label, text in [
    ("'no copy' is not a prohibition", "If Sent Items has no copy pass -ForceResend to send-via-outlook.ps1."),
    ("'if not found' is not a prohibition", "If not found use -ForceResend with send-via-outlook.ps1."),
    ("'without exception' is not a prohibition", "Without exception pass -ForceResend to send-via-outlook.ps1."),
]:
    check("L3 detection: %s" % label, bool(scan_text(text)["force"]))
check("L3 detection: negation does not excuse a fenced invocation",
      bool(scan_text("```\n" + PS + " -ForceResend  # never\n```")["force"]))

RETRY_TEXT = "Run send-via-outlook.ps1 once.\nOn a non-zero send exit, retry once.\nThen stop.\n"
check("CRLF and LF scan identically",
      scan_text(RETRY_TEXT) == scan_text(RETRY_TEXT.replace("\n", "\r\n")) and
      scan_text(RETRY_TEXT)["generic"] == [1])
check("a BOM does not hide a hit", scan_text("\ufeff" + RETRY_TEXT)["generic"] == [1])
check("a retry sentence wrapped across lines is still found",
      scan_text("Send via send-via-outlook.ps1.\nIf it exits\nnon-zero, retry\nonce.\n")["generic"] == [1])
check("a retry sentence wrapped across lines: explicit exit 6",
      scan_text("Send via send-via-outlook.ps1.\nOn exit 6\nretry once.\n")["explicit"] == [1])
check("a table row 'exit 6 | retry' is explicit",
      scan_text("send-via-outlook.ps1 exit codes:\n| exit 6 | retry once |\n")["explicit"] == [2])
check("a child bullet joins its 'On exit 6:' header",
      scan_text("send-via-outlook.ps1\n\nOn exit 6:\n- retry once\n")["explicit"] == [3])
check("a nested child bullet joins its '- Exit 6:' header",
      scan_text("send-via-outlook.ps1\n\n- Exit 6:\n  - retry once\n")["explicit"] == [3])
check("a header naming exit 6 does not absorb a per-code child bullet",
      scan_text("send-via-outlook.ps1 exit 6 = state unknown:\n- exit 2 or 4: retry once\n")["explicit"] == [])
check("a header naming exit 5/6 as terminal does not absorb a child bullet",
      scan_text("send-via-outlook.ps1\n\nExit codes 5 and 6 are terminal:\n- on exit 2 or 4, retry once\n")["explicit"] == [])
for label, text in [
    ("bold header", "send-via-outlook.ps1\n\n- **Exit 6:**\n  - retry once\n"),
    ("bold line header", "send-via-outlook.ps1\n\n**On exit 6:**\n- retry once\n"),
    ("adverb bullet", "send-via-outlook.ps1\n\nOn exit 6:\n- Immediately retry.\n"),
    ("wait-then bullet", "send-via-outlook.ps1\n\nOn exit 6:\n- Wait 30 s, then retry once.\n"),
]:
    check("a child bullet joins its header: %s" % label, bool(scan_text(text)["explicit"]))
check("a bullet does not absorb the next bullet",
      scan_text("send-via-outlook.ps1:\n- exit 6: flag it\n- retry once on anything else\n")["explicit"] == [])
check("zero-width characters cannot split 'retry'",
      scan_text("send-via-outlook.ps1\nOn non-zero exit, re\u200btry once.\n")["generic"] == [1])
check("a send invocation 5 lines above the retry sentence is still in context",
      scan_text("send-via-outlook.ps1\n\na\n\nb\n\nOn non-zero exit, retry once.\n")["generic"] == [7])
check("contract mode: both flags", scan_text(PS + " -DedupTaskId t -DedupPeriodKey k")["contract_complete"])
check("contract mode: one flag is incomplete",
      scan_text(PS + " -DedupTaskId t")["contract"] and not scan_text(PS + " -DedupTaskId t")["contract_complete"])
check("contract mode: an abbreviated flag still counts", scan_text(PS + " -DedupT t -DedupP k")["contract_complete"])
check("contract mode: prose 'does not use -DedupTaskId yet' is not contract mode",
      not scan_text("This spec does not use -DedupTaskId yet. " + PS)["contract"])
check("no hits in an unrelated paragraph", scan_text("Notion create failed: retry once.\n") ==
      {"explicit": [], "explicit_text": [], "generic": [], "force": [], "contract": False,
       "contract_complete": False})

# hostile input: every shape must scan in well under a second each (budget 20 s for all, generous for a loaded host; exponential patterns take minutes)
_t0 = time.time()
for _adv in (
    "send-via-outlook.ps1 " + "exit 1, " * 10000 + "retry " + "do not " * 2500,
    "send-via-outlook.ps1 retry exit " + "1   " * 40 + "x",
    "send-via-outlook.ps1 retry exit codes " + "0    1    2    3    4    " * 400 + "x",
    "send-via-outlook.ps1 retry exit " + "1" * 50000,
    "send-via-outlook.ps1 retry " + "exit 1 " * 10000,
    "send-via-outlook.ps1 " + "retry not " * 10000,
    "send-via-outlook.ps1 " + "a" * 100000,
    "send-via-outlook.ps1 " + "-F" * 25000,
    "send-via-outlook.ps1 " + "@{" * 10000,
    "send-via-outlook.ps1 " + "\"" * 25001 + " -F",
    "send-via-outlook.ps1\n" + "- exit 6:\n" * 10000,
    "Send via send-via-outlook.ps1.\n\nOn exit 6:\n- " + "then   " * 40 + "flag it.\n",
    "Send via send-via-outlook.ps1.\n\nOn exit 6:\n- " + "wait 1111111111 " * 40 + "x\n",
    "Send via send-via-outlook.ps1.\n\nOn exit 6:\n- " + "now , " * 5000 + "x\n",
    "send-via-outlook.ps1\n```\nf" + " " * 100000 + "x\n```\n",
    "send-via-outlook.ps1\n```\n$p[ 'f'" + " " * 100000 + "]" + " " * 100000 + "x\n```\n",
    "send-via-outlook.ps1\n```\nF" + "'" * 50000 + " " * 50000 + "x\n```\n",
):
    scan_text(_adv)
check("hostile 50-100 KB inputs scan in linear time (<20 s total)", time.time() - _t0 < 20.0,
      "took %.1f s" % (time.time() - _t0))

# seeded fuzz over the scanner's own vocabulary: no random document may take long (catches any
# regex that blows up on a shape the hand-written cases above did not think of)
_rng = random.Random(20261018)
_vocab = ["exit", "retry", "not", "never", "then", "wait", "30", "s", "1", "5", "6", "2/4", "or", "and", "only",
          "except", "send-via-outlook.ps1", "non-zero", ",", ";", ".", ":", "-", "--", "\n", "\n- ", "\n\n", "  ",
          "   ", "`", "**", "|", "(", ")", "-Force", "@{", "}", "=", "$true", "\"", "'", "do", "to", "any",
          "failure", "code", "status", "once", "it", "internal", "bounded", "performs", "again"]
_worst = 0.0
for _ in range(120):
    _doc = " ".join(_rng.choice(_vocab) for _ in range(400))
    _t = time.time()
    scan_text(_doc)
    _worst = max(_worst, time.time() - _t)
check("fuzz: 120 random 400-token documents each scan in under 2 s", _worst < 2.0, "worst %.2f s" % _worst)

# ratchet semantics on synthetic specs (never reads or writes a real spec)
CLEAN = "Send via send-via-outlook.ps1. On exit 5 or 6 do NOT retry; flag it.\n"
GEN = "Send via send-via-outlook.ps1.\nOn non-zero COM exit: retry once, then flag.\n"
EXP6 = "Send via send-via-outlook.ps1. On exit 6: retry once.\n"
KEYED = PS + " -DedupTaskId t -DedupPeriodKey k\n"
E = frozenset()
check("ratchet: clean spec passes", not failing(evaluate("a", CLEAN, E, E, {})))
check("ratchet: new generic-retry spec fails (L2)",
      failing(evaluate("a", GEN, E, E, {})) == ["L2 a does not retry on any non-zero send exit"])
check("ratchet: the same spec passes while waived", not failing(evaluate("a", GEN, frozenset({"a"}), E, {})))
check("ratchet: pending-landing waiver also passes", not failing(evaluate("a", GEN, E, frozenset({"a"}), {})))
check("ratchet: a waived spec that no longer violates fails (waiver must go)",
      failing(evaluate("a", CLEAN, frozenset({"a"}), E, {})) == ["L2 a waiver still needed"])
check("ratchet: explicit exit-6 retry fails even when waived (L1)",
      "L1 a does not retry an explicit exit 5/6" in failing(evaluate("a", EXP6, frozenset({"a"}), E, {})))
check("ratchet: contract mode cannot be waived (retry text)",
      "L4 a (contract mode) carries no retry text" in failing(evaluate("a", KEYED + GEN, frozenset({"a"}), E, {})))
check("ratchet: a clean keyed spec still in a waiver set fails (waiver must go)",
      failing(evaluate("a", KEYED, frozenset({"a"}), E, {})) ==
      ["L4 a is in contract mode: remove it from the waiver/review sets"])
check("ratchet: a clean keyed spec in the pending set fails the same way",
      failing(evaluate("a", KEYED, E, frozenset({"a"}), {})) ==
      ["L4 a is in contract mode: remove it from the waiver/review sets"])
check("ratchet: a clean keyed spec in the review set fails the same way",
      failing(evaluate("a", KEYED, E, E, {"a": ("x", "r")})) ==
      ["L4 a is in contract mode: remove it from the waiver/review sets"])
check("ratchet: contract mode with one flag fails",
      failing(evaluate("a", PS + " -DedupTaskId t\n", E, E, {})) == ["L4 a passes both dedup flags"])
check("ratchet: a clean keyed spec passes", not failing(evaluate("a", KEYED, E, E, {})))
check("ratchet: -F fails (L3)", failing(evaluate("a", PS + " -F\n", E, E, {})) ==
      ["L3 a never passes -ForceResend"])
_REV_UNIT = "Exit 5 (EVENT COMMIT FAILURE): retry the same command once."
_REV = {"a": (hashlib.sha256(_REV_UNIT.encode("utf-8")).hexdigest()[:16], "reason")}
_REV_TEXT = "Send via send-via-outlook.ps1.\n\n" + _REV_UNIT + "\n"
check("ratchet: reviewed non-send exit-5 spec passes while its wording stands",
      not failing(evaluate("a", _REV_TEXT, E, E, _REV)))
check("ratchet: an exit-6 retry hard-wrapped into the reviewed unit fails",
      failing(evaluate("a", _REV_TEXT.rstrip() + "\n  On exit 6 from send-via-outlook.ps1, retry the send once.\n",
                       E, E, _REV)) == ["L1 a reviewed non-send exit-5 wording is unchanged"])
check("ratchet: a second real exit-6 retry in a reviewed spec fails",
      failing(evaluate("a", _REV_TEXT + "\nIf send-via-outlook.ps1 returns exit 6, retry the send once.\n",
                       E, E, _REV)) == ["L1 a reviewed non-send exit-5 wording is unchanged"])
check("ratchet: reviewed entry whose wording is gone fails",
      failing(evaluate("a", CLEAN, E, E, _REV)) == ["L1 a reviewed non-send exit-5 wording is unchanged"])

# end-to-end on a temp tree: the same file-reading path main uses, real CRLF and UTF-16 bytes on disk
with tempfile.TemporaryDirectory() as _td:
    os.makedirs(os.path.join(_td, "ora-x"))
    os.makedirs(os.path.join(_td, "ora-y"))
    with open(os.path.join(_td, "ora-x", "SKILL.md"), "wb") as _f:
        _f.write(GEN.replace("\n", "\r\n").encode("utf-8"))
    with open(os.path.join(_td, "ora-y", "SKILL.md"), "wb") as _f:
        _f.write(b"\xff\xfe" + EXP6.replace("\n", "\r\n").encode("utf-16-le"))
    _p = sorted(glob.glob(os.path.join(_td, "*", "SKILL.md")))
    check("temp tree: specs found", len(_p) == 2)
    check("temp tree: CRLF-on-disk spec is flagged",
          len(failing(evaluate("ora-x", read_spec(_p[0]), E, E, {}))) == 1)
    check("temp tree: UTF-16 spec is decoded and flagged (L1)",
          failing(evaluate("ora-y", read_spec(_p[1]), E, E, {})) == ["L1 ora-y does not retry an explicit exit 5/6"])

# --- in-repo specs (gating) --------------------------------------------------------------------
print("\nin-repo specs")
specs = sorted(glob.glob(os.path.join(SCHED, "*", "SKILL.md")))
present = {os.path.basename(os.path.dirname(p)) for p in specs}
check("found in-repo specs to lint", len(specs) >= 40, "found %d" % len(specs))
for name in sorted(WAIVED_GENERIC_RETRY - present):
    check("waived spec exists: %s" % name, False, "stale waiver: spec is gone, remove it")
for name in sorted(WAIVED_PENDING_LANDING & present):
    check("pending-landing spec %s is now in the repo" % name, False,
          "it landed: move it from WAIVED_PENDING_LANDING to WAIVED_GENERIC_RETRY")
for name in sorted(set(REVIEWED_NOT_SEND_EXIT) - present):
    check("reviewed spec exists: %s" % name, False, "stale review entry: spec is gone, remove it")

for path in specs:
    name = os.path.basename(os.path.dirname(path))
    for label, ok, detail in evaluate(name, read_spec(path), WAIVED_GENERIC_RETRY, WAIVED_PENDING_LANDING,
                                      REVIEWED_NOT_SEND_EXIT):
        if not ok:
            check(label, False, detail)
        elif label.startswith("L4"):
            check(label, True)
print("  INFO  ratchet baseline: %d in-repo specs waived (generic retry), %d pending landing" % (
    len(WAIVED_GENERIC_RETRY & present), len(WAIVED_PENDING_LANDING)))

# --- LAMS (report only; not in this repo) ------------------------------------------------------
if os.path.isdir(LAMS):
    print("\nLAMS specs (INFO only, never fails)")
    for path in sorted(glob.glob(os.path.join(LAMS, "*", "SKILL.md"))):
        h = scan_text(read_spec(path))
        if h["explicit"] or h["generic"] or h["force"]:
            print("  INFO  %s: explicit=%s generic=%s force=%s" % (
                os.path.basename(os.path.dirname(path)), h["explicit"], h["generic"], h["force"]))

print("\nsend-contract spec lint: %d failure(s)" % len(failures))
sys.exit(1 if failures else 0)
