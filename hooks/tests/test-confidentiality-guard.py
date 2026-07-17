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
import os, sys, json, subprocess, tempfile, datetime, atexit, io, importlib.util

HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (this test lives in hooks/tests/)
GUARD = os.path.join(HOOK_DIR, "confidentiality-guard.py")
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")


def _load_guard_module():
    """Import confidentiality-guard.py as a module so a unit test can call its
    internal stdin-decode helper directly, without a subprocess. Needed for the
    same reason eos-claude-md-guard.py's fix required this: the cp1252-vs-UTF-8
    stdin mis-decode this hook shares with it (both did bare sys.stdin.read())
    is an OS/parent-process codepage quirk that a subprocess spawned from this
    dev shell does not reliably reproduce, even though sys.stdin.encoding
    reports 'cp1252' in synthetic attempts too (see
    reference_windows_hook_stdin_cp1252_encoding_gap.md). Module-level code
    (site_markers import, TERMS_FILE resolution) runs on import but has no
    stdin dependency, so this is safe."""
    spec = importlib.util.spec_from_file_location("confidentiality_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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

# --- load_terms(): linked-worktree fallback to the main checkout's terms file ----------
# 2026-07-12: hooks/confidential-terms.json is gitignored, so `git worktree add` never
# materializes it in a fresh linked worktree -- confidentiality-guard.py's load_terms() must
# fall back to the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, which
# always points at the shared .git dir regardless of which worktree asks). Mirrors the
# equivalent test added to test-git-prepush-scan.py, adapted for this guard's
# subprocess-invocation style: it's exec'd as a standalone script, not imported as a module,
# so the repro copies the real (just-edited) guard source into a throwaway git repo rather
# than monkeypatching an imported module's globals.
with tempfile.TemporaryDirectory() as td:
    main_repo = os.path.join(td, "main-repo")
    os.makedirs(os.path.join(main_repo, "hooks"))
    subprocess.run(["git", "init", "-q", main_repo], check=True)
    subprocess.run(["git", "-C", main_repo, "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", main_repo, "config", "user.name", "t"], check=True)
    with open(os.path.join(main_repo, "README.md"), "w") as f:
        f.write("seed\n")
    # confidentiality-guard.py is tracked under hooks/ in the real repo, so it DOES
    # materialize into a linked worktree's checkout -- only confidential-terms.json is
    # gitignored out of it. Copy the actual current guard source so this exercises the
    # real implementation, not a stale hand-written stand-in.
    with open(GUARD, encoding="utf-8") as f:
        guard_src = f.read()
    with open(os.path.join(main_repo, "hooks", "confidentiality-guard.py"), "w", encoding="utf-8") as f:
        f.write(guard_src)
    # hooks/lib/site_markers.py (2026-07-12) is a tracked dependency confidentiality-guard.py
    # now imports at load time -- it must be seeded into this synthetic repo too, exactly
    # like the real one, or the linked-worktree repro below fails for a reason unrelated to
    # what this test actually exercises (the terms-file fallback).
    os.makedirs(os.path.join(main_repo, "hooks", "lib"), exist_ok=True)
    real_lib_dir = os.path.join(os.path.dirname(GUARD), "lib")
    with open(os.path.join(real_lib_dir, "site_markers.py"), encoding="utf-8") as f:
        site_markers_src = f.read()
    with open(os.path.join(main_repo, "hooks", "lib", "site_markers.py"), "w", encoding="utf-8") as f:
        f.write(site_markers_src)
    subprocess.run(
        ["git", "-C", main_repo, "add", "README.md",
         "hooks/confidentiality-guard.py", "hooks/lib/site_markers.py"],
        check=True,
    )
    subprocess.run(["git", "-C", main_repo, "commit", "-q", "-m", "seed"], check=True)

    # Never committed -- mirrors the real file being gitignored (present in the main
    # checkout's working tree, absent from anything `git worktree add` creates).
    terms_path = os.path.join(main_repo, "hooks", "confidential-terms.json")
    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"roster_last_verified": datetime.date.today().isoformat()},
            "worktree_fallback_test_deal": {
                "active": True,
                "label": "Worktree Fallback Test Deal (fixture, not real)",
                "always": ["Wraith Fallback Corp"],
            },
        }, f)

    linked_wt = os.path.join(td, "linked-wt")
    subprocess.run(["git", "-C", main_repo, "worktree", "add", linked_wt, "-b", "wt-branch"],
                    check=True, capture_output=True)

    linked_terms = os.path.join(linked_wt, "hooks", "confidential-terms.json")
    expect("setup: linked worktree genuinely lacks a local terms file (proves the repro)",
           True, not os.path.isfile(linked_terms))

    linked_guard = os.path.join(linked_wt, "hooks", "confidentiality-guard.py")
    # No CONFIDENTIAL_TERMS_FILE_OVERRIDE here -- must resolve on its own via the fallback,
    # not via the escape hatch the rest of this suite relies on.
    wt_env = dict(os.environ)
    wt_env.pop("CONFIDENTIAL_TERMS_FILE_OVERRIDE", None)

    def run_in_worktree(payload_obj):
        p = subprocess.run([sys.executable, linked_guard], input=json.dumps(payload_obj).encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=wt_env)
        return p.returncode, p.stderr.decode("utf-8", "replace")

    code, err = run_in_worktree(write_payload(SITE, "Press release: Wraith Fallback Corp update"))
    expect("load_terms: falls back to main worktree's terms file (blocks the hit)", 2, code, err)
    # Exit 2 alone doesn't prove the fallback FOUND the deal -- a totally broken (pre-fix)
    # guard also blocks everything with exit 2, just because terms are unreadable everywhere.
    # Require the block reason to name the fixture deal, not a generic unreadable-file error,
    # so this assertion actually discriminates "fallback worked" from "still fail-closed-broken".
    expect("load_terms: block reason names the fixture deal (proves fallback, not blanket fail-closed)",
           True, "Worktree Fallback Test Deal" in err and "unreadable" not in err, err)

    code, err = run_in_worktree(write_payload(SITE, "Columbus industrial market update Q2 2026"))
    expect("load_terms: falls back to main worktree's terms file (allows clean egress)", 0, code, err)

    # Truly missing everywhere (main copy removed too) must still fail closed -- even for a
    # non-egress-shaped payload, since load_terms() is evaluated before the surface check.
    os.remove(terms_path)
    code, err = run_in_worktree({"tool_name": "Read", "tool_input": {}})
    expect("load_terms: missing everywhere -> fails closed (blocks even a non-egress call)", 2, code, err)

# --- BLOCK: site_markers.py import failure must not degrade fail-closed to fail-open ----
# 2026-07-12 code review finding: the module-level `from site_markers import ...` sat
# outside main()'s try/except, so a missing/broken shared module raised at import time and
# exited 1 (non-blocking) -- silently ALLOWING egress instead of blocking it. Fixed with a
# try/except + hardcoded fallback around the import. This proves the fallback actually
# classifies a site path as an egress surface (not just "still exits 2 for some other
# unrelated reason like a missing terms file").
with tempfile.TemporaryDirectory() as td2:
    iso_hooks = os.path.join(td2, "hooks")
    os.makedirs(iso_hooks)  # deliberately NO lib/ subdirectory -- site_markers.py is absent
    with open(GUARD, encoding="utf-8") as f:
        iso_guard_src = f.read()
    iso_guard = os.path.join(iso_hooks, "confidentiality-guard.py")
    with open(iso_guard, "w", encoding="utf-8") as f:
        f.write(iso_guard_src)

    iso_terms = os.path.join(td2, "confidential-terms.json")
    with open(iso_terms, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"roster_last_verified": datetime.date.today().isoformat()},
            "site_markers_fallback_test_deal": {
                "active": True,
                "label": "Site Markers Fallback Test Deal (fixture, not real)",
                "always": ["Grommet Fallback Industries"],
            },
        }, f)

    iso_env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=iso_terms)
    p = subprocess.run(
        [sys.executable, iso_guard],
        input=json.dumps(write_payload(
            "C:/Users/Owner/website-canonical/src/press.html",
            "Announcing the Grommet Fallback Industries partnership",
        )).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=iso_env,
    )
    iso_err = p.stderr.decode("utf-8", "replace")
    expect("site_markers import failure: still recognizes the site path as an egress "
           "surface via the hardcoded fallback (blocks the hit)", 2, p.returncode, iso_err)
    expect("site_markers import failure: block reason names the fixture deal (proves the "
           "fallback SITE_MARKERS worked, not a generic/unrelated block)",
           True, "Grommet Fallback Industries" in iso_err, iso_err)

# --- stdin decode: must be explicit UTF-8, not sys.stdin's own (locale-dependent) encoding
# 2026-07-17: eos-claude-md-guard.py had this exact bug -- a harness-spawned hook process
# resolved sys.stdin.encoding to cp1252 (Windows ANSI codepage), silently corrupting any
# non-ASCII byte in the payload before json.loads ever ran. confidentiality-guard.py shares
# the same bare `sys.stdin.read()` pattern. It is NOT exploitable against the live roster
# today (every current term is pure ASCII -- an ASCII term's own byte sequence survives
# cp1252 corruption of OTHER non-ASCII bytes elsewhere in scan_text, verified empirically),
# but it silently defeats the fail-closed leak scanner for ANY future confidential term that
# itself contains a non-ASCII character (an accented name, a curly quote, an em-dash copied
# from Notion/Word) -- exactly the dangerous under-block case this hook's own docstring
# calls out as the one fail-closed cannot catch on its own. Fixed proactively before it bites.
guard_module = _load_guard_module()
expect("guard exposes _read_stdin_text() (explicit UTF-8 decode off sys.stdin.buffer)",
       True, hasattr(guard_module, "_read_stdin_text"))

if hasattr(guard_module, "_read_stdin_text"):
    # ensure_ascii=False is required: the default True would \\u-escape the non-ASCII
    # character into pure ASCII before .encode(), so the payload bytes would never
    # actually contain a multi-byte UTF-8 sequence and this test would pass even against
    # the unfixed sys.stdin.read() -- the exact test-quality defect an adversarial review
    # caught in eos-claude-md-guard.py's first version of this same test.
    nonascii_payload = json.dumps({"probe": "Café Roastery — deal notes"}, ensure_ascii=False)
    utf8_bytes = nonascii_payload.encode("utf-8")

    class _FakeStdin:
        def __init__(self, data):
            self.buffer = io.BytesIO(data)

        def read(self):
            # Emulates the exact live failure mode: text-mode .read() using a
            # non-UTF-8 codepage silently corrupts multi-byte characters instead
            # of raising -- this must NOT be what the fix relies on.
            return self.buffer.getvalue().decode("cp1252")

    real_stdin = sys.stdin
    sys.stdin = _FakeStdin(utf8_bytes)
    try:
        decoded_text = guard_module._read_stdin_text()
    finally:
        sys.stdin = real_stdin
    decoded = json.loads(decoded_text)
    expect("_read_stdin_text() round-trips a non-ASCII confidential-term-shaped string "
           "correctly regardless of sys.stdin's own (locale-dependent) encoding",
           True, decoded.get("probe") == "Café Roastery — deal notes",
           "got %r" % decoded.get("probe"))

# --- BLOCK: end-to-end, a confidential term containing a non-ASCII character must still be
# caught crossing an egress surface. Uses a synthetic terms file (never a real deal
# identifier) since this test is git-tracked. This is defense-in-depth wiring coverage --
# it does not reliably reproduce the cp1252 mis-decode on every dev machine (subprocess
# pipes here happened to decode correctly even before the fix), so it is not proof of the
# fix by itself; the direct _read_stdin_text() unit test above is the primary regression
# guard.
nonascii_terms_path = _write_synthetic_terms_file()
with open(nonascii_terms_path, encoding="utf-8") as f:
    nonascii_terms_data = json.load(f)
nonascii_terms_data["synthetic_test_deal"]["always"].append("Café Roastery Holdings")
with open(nonascii_terms_path, "w", encoding="utf-8") as f:
    json.dump(nonascii_terms_data, f, ensure_ascii=False)

nonascii_env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=nonascii_terms_path)
nonascii_payload_raw = json.dumps(
    write_payload(SITE, "Announcing the Café Roastery Holdings partnership"),
    ensure_ascii=False,
)
p_nonascii = subprocess.run(
    [sys.executable, GUARD], input=nonascii_payload_raw.encode("utf-8"),
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=nonascii_env,
)
nonascii_err = p_nonascii.stderr.decode("utf-8", "replace")
expect("BLOCK egress write containing a non-ASCII confidential term (end-to-end)",
       2, p_nonascii.returncode, nonascii_err)

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
