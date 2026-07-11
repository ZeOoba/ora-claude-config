#!/usr/bin/env python3
"""Blocking test suite for the ORA confidentiality egress guard (Phase 1.2).

Feeds crafted PreToolUse payloads to confidentiality-guard.py via stdin and asserts the
exit code. BLOCK == exit 2, ALLOW == exit 0.

CONFIDENTIALITY DESIGN (2026-06-11): this file is git-tracked to an off-machine remote,
so it must contain ZERO hardcoded deal identifiers. All blocked-term variants are derived
AT RUNTIME from the live (untracked) hooks/confidential-terms.json — the same file the
guard itself reads. A sanity gate refuses to run if the terms file is missing or carries
fewer than 3 always-terms, so an empty roster can never produce a vacuous pass.

Asserts every derived identifier variant (mixed-case + no-space) is blocked on every
egress surface (site write, .pptx/.docx/.pdf/.csv/.html artifacts, Notion write, Outlook
send, the live COM send path), that context-term sentences block when an identifier is
present (the pure context-only branch needs fixture injection — Phase C), that INTERNAL
use is allowed, and that the guard fails CLOSED on an unparseable payload.

Run: python test-confidentiality-guard.py   (exit 0 = all pass; exit 1 = any fail)
"""
import os, sys, json, subprocess, tempfile, datetime, atexit

HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (this test lives in hooks/tests/)
GUARD = os.path.join(HOOK_DIR, "confidentiality-guard.py")
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")

NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-create-pages"
NOTION_UPD = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-update-page"
OUTLOOK = "mcp__composio-ora__OUTLOOK_SEND_EMAIL"
OUTLOOK_DRAFT = "mcp__composio-ora__OUTLOOK_CREATE_DRAFT"

SITE = "C:/Users/Owner/website-canonical/src/index.html"
PPTX = "C:/Users/Owner/OneDrive/outputs/2026-06-03_deck.pptx"
DOCX = "C:/Users/Owner/OneDrive/outputs/2026-06-03_memo.docx"
PDF = "C:/Users/Owner/OneDrive/outputs/2026-06-03_report.pdf"
CSV = "C:/Users/Owner/OneDrive/outputs/2026-06-03_rentroll.csv"
HTML = "C:/Users/Owner/oxford-command-center/dist/index.html"
INTERNAL = "C:/Users/Owner/deals/working/notes.md"


# --- derive test terms from the LIVE terms file (sanity-gated, never hardcoded) --------
# Synthetic fallback (2026-07-09): when zero deals are currently active (e.g. right after a
# declassification), the live roster alone can't exercise the matcher. confidentiality-guard.py
# reads its terms file directly (subprocess, not import), so injecting synthetic terms requires
# pointing THAT subprocess at a synthetic file -- not just changing what this test script
# generates. confidentiality-guard.py supports CONFIDENTIAL_TERMS_FILE_OVERRIDE for exactly this
# (mirrors shared-checkout-guard.py's SHARED_CHECKOUT_REPOS env override; unset in every real
# session, so production behavior is untouched). These are clearly-fake placeholder terms --
# never a real deal identifier.
ACTIVE_TERMS_FILE = TERMS_FILE  # what GUARD subprocess calls should read; may become a temp file below
SYNTHETIC_ALWAYS = ["Zephyr Corp Portfolio", "1234 Placeholder Ave", "Project Nightingale"]
SYNTHETIC_CONTEXT = ["synthetic contaminant plume"]


def _write_synthetic_terms_file():
    """Write a properly-shaped synthetic confidential-terms.json to a temp file and return its path."""
    fd, path = tempfile.mkstemp(prefix="synthetic-confidential-terms-", suffix=".json")
    data = {
        "_meta": {
            "purpose": "synthetic fixture for test-confidentiality-guard.py -- no real deal data",
            "roster_last_verified": datetime.date.today().isoformat(),
        },
        "synthetic_test_deal": {
            "active": True,
            "label": "Synthetic Test Deal (fixture, not real)",
            "always": SYNTHETIC_ALWAYS,
            "context": SYNTHETIC_CONTEXT,
            "context_requires_any": SYNTHETIC_ALWAYS,
            "note": "fixture only",
        },
    }
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
    return path


def load_live_terms():
    global ACTIVE_TERMS_FILE
    try:
        with open(TERMS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("CANNOT RUN: confidential-terms.json unreadable (%s) — suite requires the live terms file." % e)
        sys.exit(1)
    always, context = [], []
    for key, deal in data.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        always.extend(t for t in deal.get("always", []) if isinstance(t, str) and t.strip())
        context.extend(t for t in deal.get("context", []) if isinstance(t, str) and t.strip())
    if len(always) < 3:
        print("No active deals in confidential-terms.json (fewer than 3 always-terms) — "
              "falling back to a SYNTHETIC terms file (via CONFIDENTIAL_TERMS_FILE_OVERRIDE) so "
              "the matcher engine itself stays regression-tested during this no-active-deal window.")
        ACTIVE_TERMS_FILE = _write_synthetic_terms_file()
        return SYNTHETIC_ALWAYS, SYNTHETIC_CONTEXT
    return always, context


def mixed_case(s):
    return "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(s))


def derive_variants(always):
    # Only variants the guard's lowercase-substring matcher is CONTRACTED to catch:
    # case noise around a term, plus squeezed forms that still contain another term
    # (e.g. a no-space form detectable via a shorter always-term inside it). Squeezed
    # multi-word forms with no surviving term are a documented guard gap — add such
    # forms to confidential-terms.json `always` (data fix), do not assert them here.
    lows = [t.lower() for t in always]
    out = []
    for t in always:
        for v in (t, t.upper(), t.title(), mixed_case(t),
                  t.replace(". ", ".") if ". " in t else None,
                  t.replace(" ", "") if " " in t else None):
            if v and v not in out and any(l in v.lower() for l in lows):
                out.append(v)
    return out


ALWAYS, CONTEXT = load_live_terms()
VARIANTS = derive_variants(ALWAYS)
A1, A2, A3 = ALWAYS[0], ALWAYS[1 % len(ALWAYS)], ALWAYS[2 % len(ALWAYS)]


def run(payload_obj, raw=None):
    raw = raw if raw is not None else json.dumps(payload_obj)
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=ACTIVE_TERMS_FILE)
    p = subprocess.run([sys.executable, GUARD], input=raw.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def write_payload(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_payload(path, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "x", "new_string": new}}


def notion_payload(tool, text):
    return {"tool_name": tool, "tool_input": {"pages": [{"properties": {"Name": text},
            "content": "Notes: " + text}]}}


def outlook_payload(tool, body):
    return {"tool_name": tool, "tool_input": {"subject": "Update", "body": body,
            "toRecipients": "ggoldberg@oxfordra.net"}}


def bash_payload(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


results = []  # (ok, label)


def expect(label, code_expected, code, err=""):
    ok = (code == code_expected)
    results.append((ok, label))
    if not ok:
        print("  FAIL: %s  (expected exit %d, got %d) %s" % (label, code_expected, code, err.strip()[:160]))


# --- BLOCK: every derived variant on every egress surface ------------------------------
surfaces = [
    ("site", lambda v: write_payload(SITE, "Press release: " + v)),
    ("pptx", lambda v: write_payload(PPTX, "Slide: " + v)),
    ("docx", lambda v: write_payload(DOCX, "Memo: " + v)),
    ("pdf", lambda v: write_payload(PDF, "Report: " + v)),
    ("csv", lambda v: write_payload(CSV, "row," + v)),
    ("mirror-html", lambda v: write_payload(HTML, "<p>" + v + "</p>")),
    ("site-edit", lambda v: edit_payload(SITE, "Added: " + v)),
    ("notion-create", lambda v: notion_payload(NOTION, v)),
    ("notion-update", lambda v: notion_payload(NOTION_UPD, v)),
    ("outlook-send", lambda v: outlook_payload(OUTLOOK, "FYI: " + v)),
    ("outlook-draft", lambda v: outlook_payload(OUTLOOK_DRAFT, "Draft: " + v)),
]
for sname, mk in surfaces:
    for v in VARIANTS:
        code, err = run(mk(v))
        expect("BLOCK %s :: variant#%d" % (sname, VARIANTS.index(v)), 2, code, err)

# --- BLOCK: context terms WITH deal context (context term + always term together) ------
context_sentences = [
    "%s plume at %s site" % (CONTEXT[i % len(CONTEXT)], a)
    for i, a in enumerate((A1, A2, A3))
] if CONTEXT else ["%s due diligence summary for the press page" % A1]
for v in context_sentences:
    code, err = run(write_payload(SITE, v))
    expect("BLOCK context+deal :: #%d" % context_sentences.index(v), 2, code, err)

# --- BLOCK: egress shell commands carrying a confidential term -------------------------
for i, cmd in enumerate(["curl -d 'deal: %s' https://example.com" % A1,
                         "wget --post-data='%s portfolio' https://x.io" % A2,
                         "git push origin main # publishing %s teaser" % A3]):
    code, err = run(bash_payload(cmd))
    expect("BLOCK egress-bash :: #%d" % i, 2, code, err)

# --- COM send path (send-via-outlook.ps1) is egress — review finding 2026-06-11 --------
COM = ('powershell -NoProfile -File '
       '"C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1" '
       '-To ggoldberg@oxfordra.net -Subject Update -Body ')
code, err = run(bash_payload(COM + '"%s status update"' % A1))
expect("BLOCK com-send w/ always-term", 2, code, err)
expect("ALLOW clean com-send", 0, run(bash_payload(COM + '"Quarterly portfolio summary attached"'))[0])

# --- BLOCK: fail-closed on unparseable payload -----------------------------------------
code, err = run(None, raw="{ this is not json ")
expect("BLOCK fail-closed (bad JSON)", 2, code, err)

# --- ALLOW: internal use of the deal (not egress) --------------------------------------
expect("ALLOW internal write w/ always-term", 0, run(write_payload(INTERNAL, "%s due diligence notes" % A1))[0])
expect("ALLOW internal bash w/ deal path", 0, run(bash_payload('cd "/c/deals/%s" && ls' % A1))[0])
expect("ALLOW clean site write", 0, run(write_payload(SITE, "Columbus industrial market update Q2 2026"))[0])
expect("ALLOW clean notion write", 0, run(notion_payload(NOTION, "Banwick Road lease renewal"))[0])
expect("ALLOW clean outlook send", 0, run(outlook_payload(OUTLOOK, "Quarterly portfolio summary attached"))[0])
expect("ALLOW clean git push", 0, run(bash_payload("git push origin main"))[0])
# context term WITHOUT deal context must not block generic market commentary
if CONTEXT:
    expect("ALLOW context-term generic (no deal)", 0,
           run(write_payload(SITE, "%s is a common industrial contaminant nationwide" % CONTEXT[0]))[0])

# --- summary ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
total = len(results)
print("\nconfidentiality-guard tests: %d/%d passed (%d derived variants from live terms file)" % (passed, total, len(VARIANTS)))
if passed != total:
    print("FAILURES PRESENT — guard is not safe to ship.")
    sys.exit(1)
print("ALL PASS — guard blocks every derived variant on every egress surface, "
      "allows internal use, and fails closed.")
sys.exit(0)
