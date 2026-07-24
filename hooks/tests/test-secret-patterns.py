#!/usr/bin/env python3
"""Tests for hooks/lib/secret_patterns.py (TDD).

Run: python hooks/tests/test-secret-patterns.py   (exit 0 = all pass)
Pure stdlib. ASCII-only output (Windows cp1252 console).

NOTE: this file necessarily contains credential-SHAPED fixtures. It lives under
hooks/tests/, which is_exempt_path() exempts -- that self-consistency is asserted below.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib", "secret_patterns.py")

spec = importlib.util.spec_from_file_location("secret_patterns", LIB)
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# --- the UNION property: nothing the prior two lists caught may be lost -------------
# setup-self-audit carried three shapes scrub-before-optin did NOT. Losing any of them
# would silently weaken the daily scan -- the exact regression this module could cause.
expect("Composio ak_ shape still caught (setup-self-audit-only)",
       "Composio-style key" in sp.scan_text("key = ak_abcdefghijklmnop"))
expect("bare SECRET assignment still caught (setup-self-audit-only)",
       "secret/token assignment" in sp.scan_text("SECRET = abcdefghijklmnop"))
expect("bare TOKEN assignment still caught (setup-self-audit-only)",
       "secret/token assignment" in sp.scan_text("TOKEN: abcdefghijklmnop"))
expect("FRED_API_KEY still caught",
       bool(sp.scan_text("FRED_API_KEY=abcdefghijklmnopqrst")))
# claimed-but-unverified in the old code: x-api-key covered by the api[_-]?key alternation
expect("x-api-key covered by the api[_-]?key alternation (verified, not assumed)",
       "generic API key assignment" in sp.scan_text("x-api-key: abcdefghijklmnopqrst"))
# ...and everything scrub-before-optin carried
expect("AWS key", "AWS access key ID" in sp.scan_text("AKIAIOSFODNN7EXAMPLE"))
expect("GitHub token", "GitHub token" in sp.scan_text("ghp_" + "a" * 24))
expect("Slack token", "Slack token" in sp.scan_text("xoxb-1234567890abcd"))
expect("Anthropic key", "Anthropic API key" in sp.scan_text("sk-ant-api03-" + "x" * 20))
expect("bearer token", "generic bearer token" in sp.scan_text("Authorization: Bearer " + "a" * 20))
expect("password assignment", "password assignment" in sp.scan_text("password: hunter2xyz"))
expect("PEM block", "PEM private-key block" in sp.scan_text("-----BEGIN RSA PRIVATE KEY-----"))

expect("clean text yields nothing", sp.scan_text("DSCR 1.25x, LTV 40%, no secrets here") == [])

# --- password placeholders (measured false-positive class, 2026-07-24) --------------
# The stock `pdf` skill's docs carry `qpdf --password=secret123 --decrypt`; that was 2 of
# the daily scan's 3 findings. Suppressed narrowly -- a real password must still fire.
expect("qpdf doc example is not a finding",
       sp.scan_text("qpdf --password=secret123 --decrypt encrypted.pdf out.pdf") == [])
expect("second qpdf doc example is not a finding",
       sp.scan_text("qpdf --password=mypassword --decrypt encrypted.pdf out.pdf") == [])
expect("ALL_CAPS placeholder is not a finding",
       sp.scan_text("password: YOUR_PASSWORD") == [])
expect("bracketed placeholder is not a finding", sp.scan_text("password=<password>") == [])
expect("masked value is not a finding", sp.scan_text("password: ********") == [])
# ...and the recall side, which is what the suppression must not cost:
expect("a REAL-looking password still fires",
       "password assignment" in sp.scan_text("db password: Tr0ub4dor&3xK9"))
expect("one real password among placeholders still fires",
       "password assignment" in sp.scan_text(
           "example: password=secret123\nprod: password=Zx9!kQ2mVv"))
expect("labels only, never the matched text",
       all("ak_abcdefghijklmnop" not in lab for lab in sp.scan_text("ak_abcdefghijklmnop")))

# --- path exemptions ---------------------------------------------------------------
expect("this very test file is exempt (else the gate blocks every push)",
       sp.is_exempt_path("hooks/tests/test-secret-patterns.py"))
expect("the measured real-world hit is exempt",
       sp.is_exempt_path("maintenance/test-scrub-before-optin.py"))
expect("maintenance/_tests/ fixtures exempt", sp.is_exempt_path("maintenance/_tests/x.json"))
expect("mcp-builder docs exempt", sp.is_exempt_path("skills/mcp-builder/reference/evaluation.md"))
expect("windows separators normalised",
       sp.is_exempt_path(r"C:\Users\Owner\.claude\hooks\tests\test-x.py"))
# NOT exempt -- the exemption list is a hole in a security gate, so it must stay narrow
expect("a real memory file is NOT exempt",
       not sp.is_exempt_path("projects/x/memory/reference_tech.md"))
expect("a real hook is NOT exempt", not sp.is_exempt_path("hooks/confidentiality-guard.py"))
expect("'latest.md' is NOT exempt (substring paranoia)",
       not sp.is_exempt_path("memory/latest.md"))
expect("a scheduled task named ...test... in the middle is NOT exempt",
       not sp.is_exempt_path("scheduled-tasks/ora-contest-watch/SKILL.md"))

# --- scan_diff: per-file attribution ------------------------------------------------
DIFF = """commit abc123
Author: x

    a normal commit message

diff --git a/maintenance/test-scrub-before-optin.py b/maintenance/test-scrub-before-optin.py
index 1..2 100644
--- a/maintenance/test-scrub-before-optin.py
+++ b/maintenance/test-scrub-before-optin.py
@@ -1 +1 @@
+    ("AWS", "AKIAIOSFODNN7EXAMPLE"),
diff --git a/memory/notes.md b/memory/notes.md
index 3..4 100644
--- a/memory/notes.md
+++ b/memory/notes.md
@@ -1 +1 @@
+the key is sk-ant-api03-realleakvaluehere
"""
hits = sp.scan_diff(DIFF)
paths = [p for p, _ in hits]
expect("scan_diff exempts the fixture file", "maintenance/test-scrub-before-optin.py" not in paths, paths)
expect("scan_diff catches the real leak", "memory/notes.md" in paths, paths)
expect("scan_diff reports the right label",
       dict(hits).get("memory/notes.md") == ["Anthropic API key"], hits)

# A blob scan (no attribution) would have flagged BOTH -- i.e. blocked every push.
expect("blob scan would have false-positived on the fixture (why attribution is required)",
       bool(sp.scan_text(DIFF)))

MSG_ONLY = """commit abc123
Author: x

    oops pasted sk-ant-api03-leakedinacommitmessage here
"""
hits2 = sp.scan_diff(MSG_ONLY)
expect("a key in a commit message with no diff is caught",
       hits2 and hits2[0][0] == "<commit-message>", hits2)

PREAMBLE = """commit abc
    message with ghp_""" + "b" * 24 + """

diff --git a/x.md b/x.md
+clean line
"""
expect("commit-message key caught even when a diff follows",
       "<commit-message>" in [p for p, _ in sp.scan_diff(PREAMBLE)], sp.scan_diff(PREAMBLE))

expect("clean diff yields nothing", sp.scan_diff(
    "diff --git a/x.md b/x.md\n+DSCR 1.25x\n") == [])

npass = sum(1 for ok, _ in results if ok)
print("secret-patterns tests: %d/%d pass" % (npass, len(results)))
sys.exit(0 if npass == len(results) else 1)
