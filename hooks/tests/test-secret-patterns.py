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


# --- 2026-07-30 GAP: underscore-prefixed credential names + Netlify PAT ---------------
# Found by the credential-exposure sweep. `(?:SECRET|TOKEN)` cannot match inside
# NETLIFY_AUTH_TOKEN because `_` is a WORD character, so no boundary exists before TOKEN.
# Measured: 10 of 12 realistic shapes evaded EVERY pattern -- including every secret name
# in ORA's own stack (tech.md 7: SUPABASE_SERVICE_ROLE_KEY, STRIPE_SECRET_KEY,
# CRON_SECRET, RESEND_API_KEY). The pre-push gate would NOT have blocked them.
# Live proof: archive/oxford-realty_archived-20260726/oxfordra-net commit 4b7a3bb carries
# NETLIFY_AUTH_TOKEN = nfp_... and the whole-history scan returned CLEAN.
V = "A" * 24
for _name in ("NETLIFY_AUTH_TOKEN", "GITHUB_TOKEN", "SLACK_BOT_TOKEN", "STRIPE_SECRET_KEY",
              "SUPABASE_SERVICE_ROLE_KEY", "CRON_SECRET", "RESEND_API_KEY",
              "STRIPE_WEBHOOK_SECRET", "ANTHROPIC_API_KEY"):
    expect("underscore-prefixed %s is caught" % _name,
           bool(sp.scan_text('%s = "%s"' % (_name, V))), _name)
for _name in ("access_token", "refresh_token", "auth_token", "client_secret"):
    expect("lowercase %s is caught" % _name,
           bool(sp.scan_text('%s: "%s"' % (_name, V))), _name)
expect("Netlify PAT bare shape is caught",
       "Netlify token" in sp.scan_text("nfp_" + "b3Kq9x" * 6))
expect("Netlify PAT in assignment is caught",
       bool(sp.scan_text('NETLIFY_AUTH_TOKEN = "nfp_' + "c" * 36 + '"')))

# Precision guards for the widened matcher: env-var REFERENCES and placeholders are not
# leaks. A scanner that fires on `process.env.GITHUB_TOKEN` is alarm fatigue by 2026-07-24
# ruling, and alarm fatigue is how a real finding gets ignored.
expect("env-var reference (no value) is not a finding",
       sp.scan_text("const t = process.env.NETLIFY_AUTH_TOKEN;") == [])
expect("os.environ reference is not a finding",
       sp.scan_text("key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')") == [])
expect("templated placeholder is not a finding",
       sp.scan_text('NETLIFY_AUTH_TOKEN = "${NETLIFY_AUTH_TOKEN}"') == [])
expect("YOUR_ placeholder is not a finding",
       sp.scan_text('GITHUB_TOKEN = "YOUR_TOKEN_HERE_XXXXXXXX"') == [])
expect("empty assignment is not a finding",
       sp.scan_text('CRON_SECRET = ""') == [])
expect("short value below threshold is not a finding",
       sp.scan_text('API_TOKEN = "abc"') == [])

expect("function-call value is not a finding (code, not credential)",
       sp.scan_text("token = _normalize(new_stage)") == [])
expect("constant reference is not a finding",
       sp.scan_text("SECRET_PATTERNS = sp.SECRET_PATTERNS") == [])
expect("unquoted digit-bearing value STILL fires (nfp_/env-file shape)",
       bool(sp.scan_text("NETLIFY_AUTH_TOKEN=nfp_a3Kq9xb3Kq9xc3Kq9xd3Kq9x")))
expect("quoted no-digit value STILL fires (a real key can lack digits)",
       bool(sp.scan_text('CRON_SECRET = "AAAAAAAAAAAAAAAAAAAAAAAA"')))


# --- REFUTE findings, 2026-07-30 (all were REAL false negatives I introduced) ---------
# F1 multi-line: the pattern's whitespace run after the separator spans newlines, so a
# YAML-style name-then-indented-value matched the FULL text but NO single line --
# per-LINE evaluation dropped the label entirely. Fixed by evaluating PER MATCH.
expect("F1 multi-line YAML-style assignment is still caught",
       bool(sp.scan_text("TOKEN:\n  zq8r4tkx91mmv2abcd")))
# F2 greedy capture: a template value followed by a REAL assignment on the same line was
# swallowed into one value, and the leading ${ suppressed the whole line.
expect("F2 real assignment after a template on one line is still caught",
       bool(sp.scan_text("A_TOKEN=${TPL} SECRET=zq8r4tkx91mmv2")))
# F3 unanchored placeholder: any value merely BEGINNING with your/sample/todo/fake was
# suppressed -- including quoted, high-entropy values.
for _v in ("yourk9x84qplm22abc", "samplev8k2m4x9qp11", "todok9x84qplm22abc",
           "fakev8k2m4x9qp1122", "redactedk9x84qplm2"):
    expect("F3 entropy value starting with a placeholder word is still caught (%s)" % _v[:6],
           bool(sp.scan_text('SECRET = "%s"' % _v)), _v)
# ...while genuine SHOUTED placeholders stay suppressed
expect("F3 shouted placeholder still suppressed",
       sp.scan_text('GITHUB_TOKEN = "YOUR_TOKEN_HERE_XXXXXXXX"') == [])
# F4 self-block: the module's own source must pass its own gate, else no push can ship it.
_lib_src = open(LIB, encoding="utf-8").read()
expect("module source is CLEAN under its own patterns (must stay pushable)",
       sp.scan_text(_lib_src) == [], sp.scan_text(_lib_src))
# residual added from the REFUTE pass
expect("MASTER_KEY is caught",
       bool(sp.scan_text('RAILS_MASTER_KEY = "a1b2c3d4e5f6g7h8"')))


# --- REFUTE pass 2, 2026-07-30: surviving placeholder-prefix entropy hole ------------
# The anchored tail [A-Z0-9_-]* still swallowed arbitrary entropy, so any ALL-CAPS value
# merely BEGINNING with a placeholder word was suppressed -- including a valid
# uppercase-hex secret starting "ADD". Word-form suppression now requires DIGIT-FREE.
for _v in ("YOURK9X84QPLM22ABC", "ADDF9E2B41C77A03", "SAMPLEK9X84QPLM22"):
    expect("R2 all-caps entropy value starting with a placeholder word is caught (%s)" % _v[:6],
           bool(sp.scan_text("TOKEN = %s" % _v)), _v)
expect("R2 digit-free shouted placeholders stay suppressed",
       sp.scan_text('GITHUB_TOKEN = "YOUR_TOKEN_HERE_XXXXXXXX"') == []
       and sp.scan_text("CRON_SECRET = REPLACE_WITH_YOUR_TOKEN") == [])
# _CALL_RE was dead code (the value class excludes '('), which made a vault lookup a FP.
# Call detection now reads the char AFTER the match.
expect("R2 function-call value is suppressed via trailing char",
       sp.scan_text("AUTH_TOKEN = get_credential_from_vault(scope)") == [])
expect("R2 a real literal is still caught when a call appears elsewhere on the line",
       bool(sp.scan_text('AUTH_TOKEN = "k9x84qplm22abcd" # cf get_credential(scope)')))
# repo-relative tests/ paths must be exempt (they were not -- leading-slash bug)
expect("R2 repo-root tests/ path is exempt",
       sp.is_exempt_path("tests/unit/x.test.ts") and sp.is_exempt_path("src/tests/y.ts"))
expect("R2 non-test path is still NOT exempt",
       not sp.is_exempt_path("server/routes/stripe.ts"))


# --- REFUTE pass 3, 2026-07-30: prose parenthetical read as a function call -----------
# _TRAILING_CALL_RE carried a leading \s*, so an annotation after an UNQUOTED secret --
# `SECRET = <value> (rotate monthly)` -- and (because \s* spans newlines) a value whose
# NEXT LINE opened with '(' were both suppressed. Two executed OLD-caught/NEW-missed
# regressions. Fixed with immediate-paren AND a digit-free callee gate.
expect("R3 prose parenthetical after an unquoted secret still fires",
       bool(sp.scan_text("SECRET = zq8r4tkx91mmv2 (rotate monthly)")))
expect("R3 parenthetical on the NEXT line still fires",
       bool(sp.scan_text("SECRET = zq8r4tkx91mmv2\n(see rotation doc)")))
expect("R3 digit-bearing value keeps its finding even with an immediate paren",
       bool(sp.scan_text("SECRET = zq8r4tkx91mmv2(rotate)")))
expect("R3 genuine call is still suppressed",
       sp.scan_text("AUTH_TOKEN = get_credential_from_vault(scope)") == [])


# --- 2026-08-03: legacy password placeholder shape swallowed entropy ------------------
# _PLACEHOLDER_SHAPE_RE (2026-07-24) allowed [A-Z0-9_] in its ALL-CAPS branch, so a real
# shouted password carrying digits read as a placeholder. Same class as the 2026-07-30
# word-form fix; that gate was never applied to this older regex. Found by the REFUTE
# pass on the scrub-before-optin scan_text routing change.
expect("all-caps password WITH digits is caught",
       "password assignment" in sp.scan_text("password = ALLCAPS99X"))
expect("all-caps password with trailing digits is caught",
       "password assignment" in sp.scan_text("db password: HUNTER2XYZABC"))
expect("digit-free shouted placeholders stay suppressed",
       sp.scan_text("password: YOUR_PASSWORD") == []
       and sp.scan_text("password: PASSWORD") == []
       and sp.scan_text("password = CHANGEME") == [])
expect("bracketed/starred placeholder branches unaffected",
       sp.scan_text("password=<password>") == []
       and sp.scan_text("password: ********") == [])

# --- 2026-11-08 audit finding secret-patterns-missing-stack-token-prefixes ------------
# ORA's own stack issues prefixed tokens the module had no rule for. Each must fire on a
# realistic shape and stay quiet on prose / short look-alikes. Fixtures are built by
# concatenation so no complete credential-shaped literal sits in this file's source.
_A40 = "Ab3dEf6hIj9kLm2nOp5qRs8tUv1wXy4zAb7dEf0h"  # 40 mixed alnum chars, synthetic
expect("GitHub fine-grained PAT is caught",
       "GitHub fine-grained token" in sp.scan_text("github_pat_" + "11ABCDEFG0" + _A40 + "_" + _A40))
expect("Notion ntn_ integration token is caught",
       "Notion token" in sp.scan_text("NOTION=ntn_" + _A40 + "abcdef"))
expect("Notion legacy secret_ (43+ chars) is caught",
       "Notion token" in sp.scan_text("key secret_" + _A40 + "xyz"))
expect("HubSpot private-app pat-na1- token is caught",
       "HubSpot private app token" in sp.scan_text(
           "pat-na1-" + "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"))
expect("HubSpot pat-eu1- token is caught",
       "HubSpot private app token" in sp.scan_text(
           "pat-eu1-" + "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"))
expect("Supabase sbp_ access token is caught",
       "Supabase access token" in sp.scan_text("sbp_" + "0123456789abcdef0123456789abcdef01234567"))
expect("Supabase versioned sbp_v0_ token is caught",
       "Supabase access token" in sp.scan_text("sbp_v0_" + "0123456789abcdef0123456789abcdef01234567"))
# negatives: prose and short look-alikes must not flag
expect("prose 'secret_sauce' does not flag",
       sp.scan_text("our secret_sauce is shallow-bay flex") == [])
expect("short secret_ identifier (< 43 chars) does not flag",
       sp.scan_text("x = secret_" + "a" * 30) == [])
expect("ntn_ prose word does not flag", sp.scan_text("see ntn_notes for detail") == [])
expect("pat-na1 without a uuid does not flag", sp.scan_text("pat-na1-portal setting") == [])
expect("github_pat_ placeholder word does not flag", sp.scan_text("github_pat_HERE") == [])
expect("sbp_ short id does not flag", sp.scan_text("sbp_123") == [])
expect("new labels appended AFTER the original 13 (callers report by index)",
       [l for l, _ in sp.SECRET_PATTERNS][:13] == [
           "Anthropic API key", "Composio-style key", "AWS access key ID", "GitHub token",
           "Slack token", "generic API key assignment", "Netlify token",
           "secret/token assignment", "secret/token assignment",
           "generic API key assignment", "generic bearer token", "password assignment",
           "PEM private-key block"])

# --- 2026-11-09: ENV-VAR-NAME reference rule (event_log false positive) ---------------
# A prose/log line naming WHICH env var holds a secret (`secret = SOME_ENV_VAR_NAME`)
# is a reference, not a credential. Fixtures are SYNTHETIC names, never the real one.
SECRET_LABEL = "secret/token assignment"
for _name in ("ORA_INTAKE_JWS_SIGNING_KEY", "OWNER_SUBMISSION_HMAC",
              "OAUTH2_CLIENT_SECRET", "S3_BUCKET_SIGNING_SECRET", "X509_CERT_KEY_PATH"):
    expect("env-var-name value %s is a reference, not a finding" % _name,
           sp.scan_text("JWS secret = %s" % _name) == [])
expect("event_log shape (spaces, trailing '),') does not flag",
       sp.scan_text("owner-submission-intake, JWS secret = ORA_INTAKE_JWS_KEY_NAME),") == [])
expect("env-var-name in backticks does not flag",
       sp.scan_text("set `TOKEN = GITHUB_APP_PRIVATE_KEY` in CI") == [])
expect("env-var-name via generic API key label does not flag",
       sp.scan_text("FRED_API_KEY = FRED_KEY_FROM_VAULT_NAME") == [])
expect("code constant reference (spaced, unquoted identifier) does not flag",
       sp.scan_text("AUTH_TOKEN = DEFAULT_AUTH_TOKEN_NAME\n") == [])
expect("env-var-name at exactly 64 chars does not flag",
       sp.scan_text("SECRET = " + "AB_" * 21 + "C") == [])
expect("env-var-name followed by <=4 closers then end of text does not flag",
       sp.scan_text("JWS secret = SOME_ENV_VAR_NAME),") == [])
# REFUTE 2026-11-09 C1: machine-config forms (no space BEFORE the separator) keep firing,
# because that is where a generated `_`-grouped all-caps secret would actually live.
for _form in ("SECRET=ABCD1234_EFGH5678_IJKL9012", "export TOKEN=JBSWY_DPEHP_KPXPQ_RSTUV",
              "api_secret: DEADBEEF_CAFEBABE_FEED", "auth_token:QWERTY_ASDFGH_ZXCVBN",
              "--secret=QWERTY_ASDFGH_ZXCVBN", "SECRET= QWERTY_ASDFGH_ZXCVBN",
              "SECRET =QWERTY_ASDFGH_ZXCVBN"):
    expect("unspaced/config assignment form still flags: %s" % _form.split("=")[0][:16],
           SECRET_LABEL in sp.scan_text(_form))
# REFUTE 2026-11-09 C3: a closing delimiter followed by MORE token chars is a truncated
# secret, not the end of a name.
for _tail in (";k9!x", ")k9x", "|k9x", ">k9x", "}k9x", ",k9x", "]k9x", "`k9x", "),k9x",
              ")))))k9x", ")))))"):
    expect("delimiter tail %r after an upper-snake prefix still flags" % _tail,
           SECRET_LABEL in sp.scan_text("SECRET = QWERTZ_UIOPAS_DFGH" + _tail))
# --- must STILL flag ---
expect("all-caps alnum with NO underscore still flags",
       SECRET_LABEL in sp.scan_text("secret=AB12CD34EF56GH78IJ90"))
expect("mixed-case value with underscore still flags",
       SECRET_LABEL in sp.scan_text("secret=Ab12_Cd34_Ef56_Gh78"))
expect("lowercase underscore value still flags",
       SECRET_LABEL in sp.scan_text("secret=abcd_efgh_ijkl_mnop"))
expect("all-caps underscore value LONGER than 64 chars still flags",
       SECRET_LABEL in sp.scan_text("SECRET=" + "AB_" * 21 + "CD"))
expect("leading-underscore value still flags",
       SECRET_LABEL in sp.scan_text("SECRET=_ABCDEF_GHIJKL"))
expect("trailing-underscore value still flags",
       SECRET_LABEL in sp.scan_text("SECRET=ABCDEF_GHIJKL_"))
expect("double-underscore value still flags",
       SECRET_LABEL in sp.scan_text("SECRET=ABCDEF__GHIJKL"))
expect("interleaved-entropy segment (letter after digit) still flags",
       SECRET_LABEL in sp.scan_text("SECRET=AB12CD34EF_56GH78IJ"))
expect("long pure-digit segment still flags",
       SECRET_LABEL in sp.scan_text("SECRET=PIN_83920174"))
expect("quoted all-caps underscore literal still flags (hardcoded value, not a name)",
       SECRET_LABEL in sp.scan_text('JWT_SECRET = "MY_SUPER_SECRET_KEY"'))
expect("value that continues past the match ('/', '+') still flags",
       SECRET_LABEL in sp.scan_text("SECRET=ABCDEF_GHIJKL/MNOP+QRST"))
expect("value that continues past the match ('=' padding) still flags",
       SECRET_LABEL in sp.scan_text("SECRET=ABCDEF_GHIJKL=="))
expect("known AWS key-id prefix with underscore still flags",
       SECRET_LABEL in sp.scan_text("SECRET=AKIA_IOSFODNN_EXAMPLE"))
expect("known GitHub prefix uppercased still flags",
       SECRET_LABEL in sp.scan_text("TOKEN=GHP_ABCDEFGHIJKLMNOP"))
expect("one real value among env-name references still flags (per-match)",
       SECRET_LABEL in sp.scan_text("A_SECRET=SOME_ENV_NAME B_TOKEN=Zx9Kq2Lm8Np4Rt6"))
# Same shape guards in the SPACED form, so each guard is exercised on its own (the
# unspaced cases above would also fire on the spacing rule alone).
for _v in ("AB12CD34EF56GH78IJ90", "Ab12_Cd34_Ef56_Gh78", "abcd_efgh_ijkl_mnop",
           "AB_" * 21 + "CD", "_ABCDEF_GHIJKL", "ABCDEF_GHIJKL_", "ABCDEF__GHIJKL",
           "AB12CD34EF_56GH78IJ", "PIN_83920174", '"MY_SUPER_SECRET_KEY"',
           "ABCDEF_GHIJKL/MNOP+QRST", "ABCDEF_GHIJKL==", "AKIA_IOSFODNN_EXAMPLE",
           "GHP_ABCDEFGHIJKLMNOP"):
    # NOT listed: a spaced, unquoted `_`-grouped all-caps value whose groups are
    # letters-then-<=4-digits (e.g. ABCD1234_EFGH...) -- the ACCEPTED residual documented
    # at _looks_like_env_var_name; the unspaced/config form of it fires (asserted above).
    expect("spaced form still flags: %s" % _v[:14],
           SECRET_LABEL in sp.scan_text("SECRET = " + _v))
expect("prefix-shaped labels unaffected: AKIA key still caught",
       "AWS access key ID" in sp.scan_text("SECRET=AKIAIOSFODNN7EXAMPLE"))

npass = sum(1 for ok, _ in results if ok)
print("secret-patterns tests: %d/%d pass" % (npass, len(results)))
sys.exit(0 if npass == len(results) else 1)
