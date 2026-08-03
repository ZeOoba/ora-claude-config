#!/usr/bin/env python3
"""Tests for scrub-before-optin.py (TDD).

Run: python test-scrub-before-optin.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "scrub-before-optin.py"

_spec = importlib.util.spec_from_file_location("sbo", SCRIPT)
sbo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbo)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _mkterms(tmpdir, data):
    p = os.path.join(tmpdir, "terms.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return p


def _mkfile(tmpdir, name, content):
    p = os.path.join(tmpdir, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def run_cli(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True)


# --- confidential-term scan (reused doctrine-integrity-probe.py matching) ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    terms = _mkterms(tmp, {
        "test_deal": {"active": True, "always": ["zebraquartz portfolio"]},
        "old_deal": {"active": False, "always": ["retiredterm"]},
    })
    dirty = _mkfile(tmp, "dirty.md", "Notes about the zebraquartz portfolio deal.\n")
    clean = _mkfile(tmp, "clean.md", "Nothing sensitive here.\n")
    declassified_ok = _mkfile(tmp, "declassified.md", "Mentions retiredterm freely.\n")

    term_hits, secret_hits, warnings = sbo.scrub([tmp], terms_path=terms)
    dirty_hit = next((h for f, h in term_hits if str(f) == dirty), None)
    expect("active deal term detected in dirty file", dirty_hit == [1],
           "got %r" % dirty_hit)
    expect("clean file has no term hit", not any(str(f) == clean for f, _ in term_hits))
    expect("declassified deal term NOT flagged (out of scope for this scan)",
           not any(str(f) == declassified_ok for f, _ in term_hits))
    expect("no warnings on a well-formed terms file", warnings == [])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- secret-pattern scan ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    cases = {
        "apikey.txt": "api_key=abcdef0123456789abcdef0123456789\n",
        "aws.txt": "AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n",
        "gh.txt": "token: ghp_abcdefghijklmnopqrstuvwxyz0123456789\n",
        "slack.txt": "xoxb-111111111111-222222222222-abcdefghijklmnopqrstuvwx\n",
        "anthropic.txt": "ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz\n",
        "bearer.txt": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345\n",
        "password.txt": "password: SuperSecret123\n",
        "pem.txt": "-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n-----END RSA PRIVATE KEY-----\n",
    }
    for name, content in cases.items():
        _mkfile(tmp, name, content)
    _mkfile(tmp, "clean.txt", "just some ordinary prose, nothing to see\n")

    _term_hits, secret_hits, _warnings = sbo.scrub([tmp])
    flagged = {os.path.basename(str(f)) for f, _ in secret_hits}
    for name in cases:
        expect("secret pattern detected: %s" % name, name in flagged)
    expect("clean file not flagged as a secret hit", "clean.txt" not in flagged)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- report never echoes the actual matched value ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    _mkfile(tmp, "secret.txt", "api_key=TOPSECRETVALUE1234567890\n")
    r = run_cli([tmp])
    expect("CLI exits 1 on a secret hit", r.returncode == 1)
    expect("CLI report never echoes the actual secret value",
           "TOPSECRETVALUE1234567890" not in r.stdout)
    expect("CLI report names the pattern label",
           "generic API key assignment" in r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- CLI: clean tree exits 0 ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    _mkfile(tmp, "a.md", "Nothing sensitive.\n")
    _mkfile(tmp, "sub/b.md", "Also nothing sensitive.\n")
    r = run_cli([tmp])
    expect("CLI exits 0 on a clean tree", r.returncode == 0)
    expect("CLI prints SCRUB CLEAN", "SCRUB CLEAN" in r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- CLI: no args ---

r = run_cli([])
expect("CLI with no args exits 1 (usage)", r.returncode == 1)

# --- a single file path (not a directory) works directly ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    f = _mkfile(tmp, "onefile.txt", "password: hunter2345\n")
    r = run_cli([f])
    expect("a single file path is scanned directly", r.returncode == 1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- .git / __pycache__ / node_modules subtrees are skipped ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    _mkfile(tmp, ".git/config", "api_key=abcdef0123456789abcdef0123456789\n")
    _mkfile(tmp, "node_modules/pkg/index.js", "api_key=abcdef0123456789abcdef0123456789\n")
    _mkfile(tmp, "real.txt", "nothing here\n")
    r = run_cli([tmp])
    expect("skip-dir contents are not scanned", r.returncode == 0 and "SCRUB CLEAN" in r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- malformed / missing terms file fails open with a warning, doesn't crash ---

tmp = tempfile.mkdtemp(prefix="sbo_test_")
try:
    _mkfile(tmp, "ok.md", "fine\n")
    r = run_cli([tmp, "--terms-doesnotexist-flag-is-ignored"]) if False else None
    term_hits, secret_hits, warnings = sbo.scrub([tmp], terms_path=os.path.join(tmp, "absent.json"))
    expect("missing terms file fails open (no crash)", term_hits == [] and warnings != [])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- 2026-08-03: scrub must route secret detection through scan_text -----------------
# Root cause (REFUTE pass 2 of the secret_patterns gap fix, 2026-07-30):
# scan_file_for_secrets iterated SECRET_PATTERNS RAW per line, so neither the
# reference/placeholder suppressor nor scan_text's multi-line handling ever reached this
# consumer -- the two scanners could disagree about the same file, which is precisely the
# divergence the shared lib exists to prevent.
tmp = tempfile.mkdtemp(prefix="sbo_scantext_")
try:
    # (a) suppressor must now apply: env lookups / templates / code refs are NOT secrets
    _mkfile(tmp, "envref.py", "TOKEN = os.environ.get('NETLIFY_AUTH_TOKEN')\n")
    _mkfile(tmp, "template.yml", 'NETLIFY_AUTH_TOKEN: "${NETLIFY_AUTH_TOKEN}"\n')
    _mkfile(tmp, "coderef.py", "SECRET_PATTERNS = lib.SECRET_PATTERNS\n")
    # (b) recall preserved -- a real key still fires
    _mkfile(tmp, "real.env", "NETLIFY_AUTH_TOKEN=nfp_a3Kq9xb3Kq9xc3Kq9xd3Kq9x\n")
    # (c) MULTI-LINE assignment: the raw per-line loop could never see this
    _mkfile(tmp, "multiline.yml", "CRON_SECRET:\n  zq8r4tkx91mmv2abcd\n")
    _t, _secret_hits, _w = sbo.scrub([tmp])
    _flagged = {os.path.basename(str(f)) for f, _ in _secret_hits}
    expect("scrub suppresses an env-lookup value", "envref.py" not in _flagged, _flagged)
    expect("scrub suppresses a template placeholder", "template.yml" not in _flagged, _flagged)
    expect("scrub suppresses a code reference", "coderef.py" not in _flagged, _flagged)
    expect("scrub still flags a real Netlify key", "real.env" in _flagged, _flagged)
    expect("scrub flags a MULTI-LINE assignment (raw per-line loop could not)",
           "multiline.yml" in _flagged, _flagged)
    for _f, _hits in _secret_hits:
        if os.path.basename(str(_f)) == "real.env":
            expect("single-line hit keeps its line number", _hits and _hits[0][0] == 1, _hits)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

passed = sum(1 for ok, _ in results if ok)
print("\nscrub-before-optin tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
