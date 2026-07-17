"""Tests for ora-autonomy-gate.py PreToolUse hook (Gates 1 and 2).

Run: python test-ora-autonomy-gate.py
Stdlib only. ASCII-only. Self-contained.

No existing test file covered this hook before 2026-07-12 (verified absent).
Written alongside the site-marker de-duplication fix (hooks/lib/site_markers.py)
to lock in both the pre-existing legacy-marker behavior and the newly-closed
domain-form-marker gap.

2026-07-16 -- override-token hardening. The old flat `hooks/overrides/<name>`
sentinel was mtime-only: content-blind, session-blind, one name for four gates,
and (worst) git-tracked, so a plain `git clone` materialized the token with
mtime=now and self-granted a live production-deploy window with no human
involved. That was proven empirically: a fresh clone made the gate return exit 0
for `netlify deploy --prod`, against an empty-dir control returning exit 2.

Tokens now live in `hooks/sessions/<session_id>/overrides/<name>`, which is
already gitignored -- a token is now structurally impossible to commit. Every
test below drives that path through ORA_OVERRIDE_SESSIONS_DIR, isolated per
test, so the suite never depends on (nor can be flipped by) a real live token
from a concurrent session.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HERE, "ora-autonomy-gate.py")

SESSION_A = "aaaaaaaa-1111-2222-3333-444444444444"
SESSION_B = "bbbbbbbb-5555-6666-7777-888888888888"

SITE_FILE = "C:/Users/Owner/website-canonical/src/index.html"
PROD_DEPLOY = "netlify deploy --build --prod"


def run_hook(payload_dict, sessions_dir=None, session_id=SESSION_A, omit_session=False):
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = (
        sessions_dir if sessions_dir is not None else tempfile.mkdtemp(prefix="oag-sess-")
    )
    payload = dict(payload_dict)
    if not omit_session:
        payload["session_id"] = session_id
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def fresh_sessions_dir():
    return tempfile.mkdtemp(prefix="oag-sess-")


def mint(sessions_dir, name, scope, session_id=SESSION_A, recipients=None,
         reason="Gabriel approved in-turn", age_seconds=0, raw=None):
    """Write an override token into the session-scoped override dir."""
    d = os.path.join(sessions_dir, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    if raw is not None:
        body = raw
    else:
        lines = ["scope: %s" % scope, "session: %s" % session_id]
        if recipients is not None:
            lines.append("recipients: %s" % ", ".join(recipients))
        lines.append("reason: %s" % reason)
        body = "\n".join(lines) + "\n"
    with open(path, "w", encoding="ascii") as fh:
        fh.write(body)
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(path, (old, old))
    return path


def write_payload(file_path):
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "x"}}


def bash_payload(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def mcp_payload(tool_name):
    return {"tool_name": tool_name, "tool_input": {}}


def send_payload(recipient):
    cmd = ('powershell -File send-via-outlook.ps1 -To %s -Subject "hi" -Body "hi"' % recipient)
    return bash_payload(cmd)


# --------------------------------------------------------------------------
# Pre-existing behavior (must not regress)
# --------------------------------------------------------------------------

def test_blocks_legacy_markers():
    for marker_path in [
        "C:/Users/Owner/website-canonical/src/index.html",
        "C:/Users/Owner/oxford-site/foo.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 2, "%s expected block (exit 2), got %s (%s)" % (marker_path, rc, err)
    print("PASS test_blocks_legacy_markers")


def test_domain_form_markers_do_not_block_via_this_hook():
    for marker_path in [
        "C:/some/other/tree/oxfordra.net/page.html",
        "C:/some/other/tree/oxfordra_net/page.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 0, (
            "%s must NOT block via ora-autonomy-gate (domain aliases are "
            "confidentiality-guard.py's concern, not Gate 2's), got %s (%s)"
            % (marker_path, rc, err)
        )
    print("PASS test_domain_form_markers_do_not_block_via_this_hook")


def test_allows_internal_email_with_redirect():
    rc, out, err = run_hook(bash_payload("echo notify ggoldberg@oxfordra.net > note.txt"))
    assert rc == 0, "internal email + redirect must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_internal_email_with_redirect")


def test_allows_curl_fetch_of_site():
    rc, out, err = run_hook(bash_payload("curl -s https://oxfordra.net > page.html"))
    assert rc == 0, "fetching the live site to a local file must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_curl_fetch_of_site")


def test_allows_internal_send_with_redirect():
    cmd = ('powershell -File send-via-outlook.ps1 -To ggoldberg@oxfordra.net '
           '-Subject "hi" -Body "hi" > send.log')
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 0, "pre-authorized internal send + log redirect must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_internal_send_with_redirect")


def test_allows_file_mentioning_domain_in_name():
    rc, out, err = run_hook(write_payload("C:/Users/Owner/notes/re-oxfordra.net-seo.md"))
    assert rc == 0, "a file merely mentioning the domain in its name must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_file_mentioning_domain_in_name")


def test_non_site_path_allows():
    rc, out, err = run_hook(write_payload("C:/proj/src/index.html"))
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    print("PASS test_non_site_path_allows")


def test_broken_token_module_fails_closed():
    """A broken/missing hooks/lib/override_tokens.py must still BLOCK every gated action.

    Regression, adversarial review 2026-07-17: when this gate adopted the shared token
    contract, the import had no fallback -- on ImportError the gate exited 1, and a
    PreToolUse hook exiting 1 is a NON-BLOCKING error, so the tool call PROCEEDS. A broken
    shared module therefore disabled Gate 1 AND Gate 2 (prod deploy, site write, external
    send all passed through) leaving only a traceback the model never sees. The module is
    now SHARED with git-prepush-doctrine-gate.py, so an edit made for that gate's benefit
    can break this one -- this is the test that keeps that from being a silent bypass.

    Note the gate must still exit 0 for UNGATED calls even with the module broken: exiting 2
    at import time would brick every tool call in the session (confidentiality-guard
    self-deadlock). Fail closed on gated actions, stay available otherwise.
    """
    sandbox = tempfile.mkdtemp(prefix="oag-broken-")
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"))
    gate = os.path.join(sandbox, "hooks", "ora-autonomy-gate.py")
    os.remove(os.path.join(sandbox, "hooks", "lib", "override_tokens.py"))

    def run_broken(payload):
        env = dict(os.environ)
        env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-broken-sess-")
        payload = dict(payload)
        payload["session_id"] = SESSION_A
        proc = subprocess.run([sys.executable, gate], input=json.dumps(payload),
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr

    for label, payload in (
        ("prod deploy", bash_payload(PROD_DEPLOY)),
        ("site write", write_payload(SITE_FILE)),
        ("external send", bash_payload(
            "powershell -File send-via-outlook.ps1 -To broker@example.com -Subject x -Body y")),
        ("netlify MCP updater", {"tool_name": "mcp__netlify__netlify-deploy-services-updater",
                                 "tool_input": {}}),
    ):
        rc, err = run_broken(payload)
        assert rc == 2, (
            "%s must BLOCK (exit 2) when override_tokens.py is unimportable, got exit %s. "
            "Exit 1 is NON-BLOCKING for PreToolUse -- the action would proceed.\n%s"
            % (label, rc, err))

    # ...and an UNGATED call must still pass: import-time exit 2 would brick the session.
    rc, err = run_broken(write_payload("C:/proj/src/index.html"))
    assert rc == 0, (
        "an ungated call must still pass with the module broken (got exit %s) -- blocking "
        "every tool call would brick the session\n%s" % (rc, err))

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_broken_token_module_fails_closed")


def test_broken_email_send_tier_fails_closed():
    """A broken/missing hooks/lib/email_send_tier.py (added 2026-07-17 for the outbound-
    action check, OI-007) must ALSO still block every gated action -- not just external
    send. Same failure shape as test_broken_token_module_fails_closed: both modules are
    imported in ONE try/except so a broken email_send_tier.py (while override_tokens.py
    stays intact) degrades exactly as fail-closed, not silently disabling Gate 1."""
    sandbox = tempfile.mkdtemp(prefix="oag-broken-est-")
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"))
    gate = os.path.join(sandbox, "hooks", "ora-autonomy-gate.py")
    os.remove(os.path.join(sandbox, "hooks", "lib", "email_send_tier.py"))

    def run_broken(payload):
        env = dict(os.environ)
        env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-broken-est-sess-")
        payload = dict(payload)
        payload["session_id"] = SESSION_A
        proc = subprocess.run([sys.executable, gate], input=json.dumps(payload),
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr

    for label, payload in (
        ("external send", bash_payload(
            "powershell -File send-via-outlook.ps1 -To broker@example.com -Subject x -Body y")),
        ("prod deploy", bash_payload(PROD_DEPLOY)),
        ("site write", write_payload(SITE_FILE)),
    ):
        rc, err = run_broken(payload)
        assert rc == 2, (
            "%s must BLOCK (exit 2) when email_send_tier.py is unimportable, got exit %s.\n%s"
            % (label, rc, err))

    rc, err = run_broken(write_payload("C:/proj/src/index.html"))
    assert rc == 0, (
        "an ungated call must still pass with the module broken (got exit %s)\n%s" % (rc, err))

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_broken_email_send_tier_fails_closed")


def test_broken_website_deploy_tier_fails_closed():
    """A broken/missing hooks/lib/website_deploy_tier.py (added 2026-07-17 for the netlify
    CLI wrapper's outbound-action check, OI-007) must ALSO still block every gated action.
    Same failure shape as the email_send_tier / override_tokens variants above."""
    sandbox = tempfile.mkdtemp(prefix="oag-broken-wdt-")
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"))
    gate = os.path.join(sandbox, "hooks", "ora-autonomy-gate.py")
    os.remove(os.path.join(sandbox, "hooks", "lib", "website_deploy_tier.py"))

    def run_broken(payload):
        env = dict(os.environ)
        env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-broken-wdt-sess-")
        payload = dict(payload)
        payload["session_id"] = SESSION_A
        proc = subprocess.run([sys.executable, gate], input=json.dumps(payload),
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr

    for label, payload in (
        ("prod deploy", bash_payload(PROD_DEPLOY)),
        ("site write", write_payload(SITE_FILE)),
        ("external send", bash_payload(
            "powershell -File send-via-outlook.ps1 -To broker@example.com -Subject x -Body y")),
        ("netlify MCP updater", mcp_payload("mcp__netlify__project-updater")),
    ):
        rc, err = run_broken(payload)
        assert rc == 2, (
            "%s must BLOCK (exit 2) when website_deploy_tier.py is unimportable, got exit %s.\n%s"
            % (label, rc, err))

    rc, err = run_broken(write_payload("C:/proj/src/index.html"))
    assert rc == 0, (
        "an ungated call must still pass with the module broken (got exit %s)\n%s" % (rc, err))

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_broken_website_deploy_tier_fails_closed")


def test_malformed_stdin_fails_open():
    proc = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
    assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
    print("PASS test_malformed_stdin_fails_open")


# --------------------------------------------------------------------------
# Gate 2c coverage: NotebookEdit is enrolled in the dispatch, so it must
# actually be gated. Its tool param is `notebook_path`, NOT `file_path`
# (adversarial review, 2026-07-16) -- reading only `file_path` left a live
# invariant-2 bypass: a notebook write into the site tree resolved to "" and
# passed.
# --------------------------------------------------------------------------

def test_notebook_edit_into_site_tree_blocks():
    payload = {"tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": "C:/Users/Owner/oxford-site/x.ipynb",
                              "new_source": "y"}}
    rc, out, err = run_hook(payload)
    assert rc == 2, "NotebookEdit into the site tree must block, got %s (%s)" % (rc, err)
    print("PASS test_notebook_edit_into_site_tree_blocks")


def test_notebook_edit_outside_site_tree_allows():
    payload = {"tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": "C:/proj/analysis.ipynb", "new_source": "y"}}
    rc, out, err = run_hook(payload)
    assert rc == 0, "a notebook edit outside the site tree must not block, got %s (%s)" % (rc, err)
    print("PASS test_notebook_edit_outside_site_tree_allows")


def test_notebook_edit_into_site_tree_allowed_with_write_token():
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    payload = {"tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": "C:/Users/Owner/website-canonical/x.ipynb",
                              "new_source": "y"}}
    rc, out, err = run_hook(payload, sessions_dir=d)
    assert rc == 0, "a write token must authorize a site notebook edit, got %s (%s)" % (rc, err)
    print("PASS test_notebook_edit_into_site_tree_allowed_with_write_token")


# --------------------------------------------------------------------------
# Fail CLOSED on a malformed payload SHAPE for a gated tool. A parseable-JSON
# payload whose tool_input is not a dict, or whose gated field is not a string,
# must never fall through to exit 0 for a gated tool (adversarial review,
# 2026-07-16). Note: an UNPARSEABLE payload still fails OPEN (that is the
# deliberate don't-brick-every-tool-call behavior, covered above).
# --------------------------------------------------------------------------

def test_gated_bash_with_nondict_tool_input_blocks():
    payload = {"tool_name": "Bash", "tool_input": ["netlify", "deploy", "--prod"]}
    rc, out, err = run_hook(payload)
    assert rc == 2, "a gated Bash call with non-dict tool_input must fail closed, got %s (%s)" % (rc, err)
    print("PASS test_gated_bash_with_nondict_tool_input_blocks")


def test_gated_write_with_nonstring_path_blocks():
    payload = {"tool_name": "Write", "tool_input": {"file_path": ["a", "b"], "content": "x"}}
    rc, out, err = run_hook(payload)
    assert rc == 2, "a gated Write with a non-string file_path must fail closed, got %s (%s)" % (rc, err)
    print("PASS test_gated_write_with_nonstring_path_blocks")


def test_gated_bash_with_nonstring_command_blocks():
    payload = {"tool_name": "Bash", "tool_input": {"command": {"nested": "obj"}}}
    rc, out, err = run_hook(payload)
    assert rc == 2, "a gated Bash with a non-string command must fail closed, got %s (%s)" % (rc, err)
    print("PASS test_gated_bash_with_nonstring_command_blocks")


def test_non_gated_tool_with_nondict_input_passes():
    """A tool the gate does not police (e.g. Read) must not be blocked by the
    fail-closed shape guard -- that guard is only for gated tools."""
    payload = {"tool_name": "Read", "tool_input": ["whatever"]}
    rc, out, err = run_hook(payload)
    assert rc == 0, "a non-gated tool must pass regardless of input shape, got %s (%s)" % (rc, err)
    print("PASS test_non_gated_tool_with_nondict_input_passes")


def test_empty_session_override_dir_still_blocks():
    """Proves the hook reads ORA_OVERRIDE_SESSIONS_DIR (not silently falling back
    to a live default) and that isolation doesn't accidentally allow-by-default."""
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=fresh_sessions_dir())
    assert rc == 2, "an empty isolated sessions dir must still block, got %s (%s)" % (rc, err)
    print("PASS test_empty_session_override_dir_still_blocks")


# --------------------------------------------------------------------------
# Happy paths -- a correctly-scoped token in the CURRENT session grants
# --------------------------------------------------------------------------

def test_write_token_allows_site_file_write():
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
    assert rc == 0, "a fresh website-write token must allow the site write, got %s (%s)" % (rc, err)
    print("PASS test_write_token_allows_site_file_write")


def test_deploy_token_allows_prod_deploy():
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, "a fresh website-deploy token must allow the prod deploy, got %s (%s)" % (rc, err)
    print("PASS test_deploy_token_allows_prod_deploy")


def test_external_send_token_allows_named_recipient():
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 0, "a token naming the recipient must allow that send, got %s (%s)" % (rc, err)
    print("PASS test_external_send_token_allows_named_recipient")


# --------------------------------------------------------------------------
# FIX 2 -- severity split: a write grant must not open a deploy
# --------------------------------------------------------------------------

def test_write_token_does_not_authorize_prod_deploy():
    """The headline severity bug: the routine case is a local file edit, but the
    old single `allow-website-change` token also opened `netlify --prod`."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "a website-write token must NOT authorize a prod deploy, got %s (%s)" % (rc, err)
    print("PASS test_write_token_does_not_authorize_prod_deploy")


def test_write_token_does_not_authorize_netlify_mcp_updater():
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    rc, out, err = run_hook(mcp_payload("mcp__netlify__project-updater"), sessions_dir=d)
    assert rc == 2, "a website-write token must NOT authorize a Netlify MCP updater, got %s (%s)" % (rc, err)
    print("PASS test_write_token_does_not_authorize_netlify_mcp_updater")


def test_deploy_token_does_not_authorize_site_file_write():
    """Strict one-grant-one-tier: the split cuts both ways."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
    assert rc == 2, "a website-deploy token must NOT authorize a site file write, got %s (%s)" % (rc, err)
    print("PASS test_deploy_token_does_not_authorize_site_file_write")


def test_legacy_token_name_grants_nothing():
    """MIGRATION: the retired `allow-website-change` name must be inert. An
    in-flight token from the old scheme fails CLOSED (blocks), never grants."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-change", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "the retired allow-website-change name must grant nothing, got %s (%s)" % (rc, err)
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
    assert rc == 2, "the retired allow-website-change name must grant nothing, got %s (%s)" % (rc, err)
    print("PASS test_legacy_token_name_grants_nothing")


# --------------------------------------------------------------------------
# FIX 1 -- session scoping
# --------------------------------------------------------------------------

def test_other_sessions_token_is_ignored():
    """The cross-session leak. Session B's live token must not grant session A."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy", session_id=SESSION_B)
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d, session_id=SESSION_A)
    assert rc == 2, "another session's token must not grant this one, got %s (%s)" % (rc, err)
    print("PASS test_other_sessions_token_is_ignored")


def test_missing_session_id_blocks():
    """Fail CLOSED: no session_id means no override is reachable at all."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d, omit_session=True)
    assert rc == 2, "a payload with no session_id must block, got %s (%s)" % (rc, err)
    print("PASS test_missing_session_id_blocks")


def test_session_id_path_traversal_blocks():
    """A session_id of '..' shapes must not escape the sessions root and reach
    the legacy flat overrides dir (or anything else)."""
    d = fresh_sessions_dir()
    legacy = os.path.join(d, "overrides")
    os.makedirs(legacy, exist_ok=True)
    with open(os.path.join(legacy, "allow-website-deploy"), "w") as fh:
        fh.write("scope: website-deploy\nsession: ../x\n")
    for evil in ["..", "../..", "../overrides", "a/../../overrides", "\\..\\overrides"]:
        rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d, session_id=evil)
        assert rc == 2, "traversal session_id %r must block, got %s (%s)" % (evil, rc, err)
    print("PASS test_session_id_path_traversal_blocks")


# --------------------------------------------------------------------------
# FIX 3 -- content is load-bearing
# --------------------------------------------------------------------------

def test_contentless_token_blocks():
    """The 2026-07-12 test wrote the literal string 'test override' and the gate
    honored it. Any bytes used to work. Now they must not."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", None, raw="test override")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "a token with no parseable scope must block, got %s (%s)" % (rc, err)
    print("PASS test_contentless_token_blocks")


def test_not_a_deploy_token_cannot_deploy():
    """Verbatim from the live incident: a token whose justification says it is
    NOT a deploy must not be able to deploy."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-write",
         reason="recompress 10 oversized WebP property-card images. Not a deploy.")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "a 'Not a deploy' (website-write scope) token must not deploy, got %s (%s)" % (rc, err)
    print("PASS test_not_a_deploy_token_cannot_deploy")


def test_scope_mismatch_inside_token_blocks():
    """Filename says deploy, content says write -> refuse. Catches a copied or
    renamed token."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-write")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "scope mismatch must block, got %s (%s)" % (rc, err)
    print("PASS test_scope_mismatch_inside_token_blocks")


def test_session_mismatch_inside_token_blocks():
    """Token sits in session A's dir but its content names session B -> refuse."""
    d = fresh_sessions_dir()
    path = mint(d, "allow-website-deploy", "website-deploy")
    with open(path, "w", encoding="ascii") as fh:
        fh.write("scope: website-deploy\nsession: %s\nreason: copied\n" % SESSION_B)
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d, session_id=SESSION_A)
    assert rc == 2, "session mismatch inside the token must block, got %s (%s)" % (rc, err)
    print("PASS test_session_mismatch_inside_token_blocks")


def test_oversized_token_blocks():
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", None,
         raw="scope: website-deploy\nsession: %s\n" % SESSION_A + ("x" * 9000))
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "an oversized token must block, got %s (%s)" % (rc, err)
    print("PASS test_oversized_token_blocks")


# --------------------------------------------------------------------------
# FIX 3 (Gate 1) -- the lender-style recipient mismatch
# --------------------------------------------------------------------------

def test_external_send_recipient_mismatch_blocks():
    """The brief's named requirement: token approves a send to the broker; the
    command sends to the lender. Must BLOCK."""
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    rc, out, err = run_hook(send_payload("lender@example.com"), sessions_dir=d)
    assert rc == 2, "a send to an unnamed recipient must block, got %s (%s)" % (rc, err)
    print("PASS test_external_send_recipient_mismatch_blocks")


def test_external_send_extra_recipient_blocks():
    """Token names the broker; command sends to broker AND lender -> block. One
    approved recipient must not smuggle a second."""
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    cmd = ('powershell -File send-via-outlook.ps1 -To broker@example.com '
           '-Cc lender@example.com -Subject "hi" -Body "hi"')
    rc, out, err = run_hook(bash_payload(cmd), sessions_dir=d)
    assert rc == 2, "an extra un-named recipient must block, got %s (%s)" % (rc, err)
    print("PASS test_external_send_extra_recipient_blocks")


def test_external_send_token_without_recipients_blocks():
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send")
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 2, "an external-send token naming no recipients must block, got %s (%s)" % (rc, err)
    print("PASS test_external_send_token_without_recipients_blocks")


def test_website_token_does_not_authorize_external_send():
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 2, "a website token must not authorize an external send, got %s (%s)" % (rc, err)
    print("PASS test_website_token_does_not_authorize_external_send")


# --------------------------------------------------------------------------
# FIX 4 -- deploy/send tier: single-use + short TTL
# --------------------------------------------------------------------------

def test_deploy_token_is_single_use():
    """Ratified 2026-07-16: the deploy grant is consumed at gate-pass."""
    d = fresh_sessions_dir()
    path = mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, "first deploy must pass, got %s (%s)" % (rc, err)
    assert not os.path.exists(path), "token must be consumed (deleted) at gate-pass"
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "second deploy on a consumed token must block, got %s (%s)" % (rc, err)
    print("PASS test_deploy_token_is_single_use")


def test_external_send_token_is_single_use():
    d = fresh_sessions_dir()
    path = mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 0, "first send must pass, got %s (%s)" % (rc, err)
    assert not os.path.exists(path), "send token must be consumed at gate-pass"
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 2, "second send on a consumed token must block, got %s (%s)" % (rc, err)
    print("PASS test_external_send_token_is_single_use")


def test_write_token_is_multi_use():
    """The write tier stays multi-use -- routine editing must not need a token
    per keystroke."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    for i in range(3):
        rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
        assert rc == 0, "write %d must pass on a multi-use token, got %s (%s)" % (i, rc, err)
    print("PASS test_write_token_is_multi_use")


def test_deploy_token_expires_at_300s():
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy", age_seconds=400)
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "a 400s-old deploy token must be expired (TTL 300), got %s (%s)" % (rc, err)
    print("PASS test_deploy_token_expires_at_300s")


def test_deploy_token_valid_inside_300s():
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy", age_seconds=120)
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, "a 120s-old deploy token must still be valid, got %s (%s)" % (rc, err)
    print("PASS test_deploy_token_valid_inside_300s")


def test_write_token_expires_at_3600s():
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write", age_seconds=4000)
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
    assert rc == 2, "a 4000s-old write token must be expired (TTL 3600), got %s (%s)" % (rc, err)
    print("PASS test_write_token_expires_at_3600s")


def test_write_token_valid_inside_3600s():
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write", age_seconds=1800)
    rc, out, err = run_hook(write_payload(SITE_FILE), sessions_dir=d)
    assert rc == 0, "a 1800s-old write token must still be valid, got %s (%s)" % (rc, err)
    print("PASS test_write_token_valid_inside_3600s")


def test_future_dated_token_blocks():
    """A token mtime in the future would otherwise read as 'negative age' and
    sail past a naive `age < TTL` check forever."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy", age_seconds=-9999)
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 2, "a future-dated token must block, got %s (%s)" % (rc, err)
    print("PASS test_future_dated_token_blocks")


# --------------------------------------------------------------------------
# FIX 5 -- git can never mint a token
# --------------------------------------------------------------------------

def test_token_dir_is_gitignored():
    """The root cause of the clone self-grant: a token must be structurally
    un-committable. hooks/sessions/ is gitignored; assert it stays that way."""
    claude_dir = os.path.dirname(HERE)
    probe = os.path.join(claude_dir, "hooks", "sessions", SESSION_A, "overrides", "allow-website-deploy")
    proc = subprocess.run(
        ["git", "check-ignore", "-q", probe],
        cwd=claude_dir, capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        "hooks/sessions/ must remain gitignored so an override token can never be "
        "committed and re-materialized by a clone with a fresh mtime "
        "(git check-ignore returned %s)" % proc.returncode
    )
    print("PASS test_token_dir_is_gitignored")


# --------------------------------------------------------------------------
# MATCHER HARDENING (2026-07-17) -- five detection-gap bypasses found by
# adversarial review of the OVERRIDE-TOKEN work, all independent of any
# token: each lets a real, functionally-equivalent malicious command evade
# detection entirely, so NO override is ever even requested. Personally
# reproduced against the live gate before this fix, each against a passing
# control of the equivalent already-blocked form.
# --------------------------------------------------------------------------

def test_dotless_domain_email_blocks():
    """GAP 1: EMAIL_RE required a dot in the domain, so `attacker@evilhost`
    (no TLD) was invisible to Gate 1 entirely -- exit 0, zero override needed.
    Proven live: attacker@evilhost -> exit 0; attacker@evilhost.com -> exit 2."""
    rc, out, err = run_hook(send_payload("attacker@evilhost"))
    assert rc == 2, "a dotless-domain external recipient must block, got %s (%s)" % (rc, err)
    print("PASS test_dotless_domain_email_blocks")


def test_dotted_domain_email_still_blocks():
    """Regression control for GAP 1's fix -- the ordinary case must still block."""
    rc, out, err = run_hook(send_payload("attacker@evilhost.com"))
    assert rc == 2, "a normal external recipient must still block, got %s (%s)" % (rc, err)
    print("PASS test_dotted_domain_email_still_blocks")


def test_recipient_flag_prefix_blocks():
    """GAP 2: RECIPIENT_FLAGS matched only the literal substrings -to/-cc/-bcc.
    send-via-outlook.ps1's param block has only ONE parameter starting with
    T ($To), so PowerShell's unambiguous-prefix binder resolves `-T` to `-To`
    -- verified against a stand-in script with the identical param block.
    `-T attacker@evilhost.com` reached exit 0 (unblocked) before this fix."""
    cmd = 'powershell -File send-via-outlook.ps1 -T attacker@evilhost.com -Subject hi -Body hi'
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 2, "a -T prefix-bound external recipient must block, got %s (%s)" % (rc, err)
    print("PASS test_recipient_flag_prefix_blocks")


def test_netlify_cmd_indirection_blocks():
    """GAP 3: NETLIFY_INVOKE_RE anchored to a command-boundary position, so
    `cmd /c netlify deploy --prod` (netlify preceded by a space from `/c `,
    not by ^/;/&/|/$() reached exit 0 (unblocked) before this fix."""
    rc, out, err = run_hook(bash_payload("cmd /c netlify deploy --build --prod"))
    assert rc == 2, "cmd /c netlify indirection must block, got %s (%s)" % (rc, err)
    print("PASS test_netlify_cmd_indirection_blocks")


def test_netlify_powershell_command_indirection_blocks():
    """GAP 4: same anchor gap, quoted-string form -- `netlify` inside a
    powershell -Command "..." string is preceded by a quote character, not
    an anchor. Reached exit 0 (unblocked) before this fix."""
    rc, out, err = run_hook(bash_payload('powershell -Command "netlify deploy --build --prod"'))
    assert rc == 2, "powershell -Command netlify indirection must block, got %s (%s)" % (rc, err)
    print("PASS test_netlify_powershell_command_indirection_blocks")


def test_netlify_plain_still_blocks():
    """Regression control for GAPs 3/4's fix -- the ordinary anchored case
    (already covered elsewhere in this file) must still block."""
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY))
    assert rc == 2, "a plain leading-token netlify deploy must still block, got %s (%s)" % (rc, err)
    print("PASS test_netlify_plain_still_blocks")


def test_netlify_mention_in_unrelated_command_now_blocks():
    """De-anchoring GATE 2a is a deliberate breadth tradeoff, matching Gate
    2b's already-accepted philosophy (documented in check_bash's own
    comments): a command that merely QUOTES/echoes the phrase now also
    trips the gate. A false positive costs a retry; the alternative is the
    cmd/powershell indirection gap GAPs 3/4 just closed. This test locks in
    the tradeoff as an intentional, known cost -- not a silent regression."""
    rc, out, err = run_hook(bash_payload('echo "the docs explain netlify deploy --prod"'))
    assert rc == 2, (
        "quoting the phrase now also blocks -- this is the accepted breadth "
        "tradeoff, got %s (%s)" % (rc, err)
    )
    print("PASS test_netlify_mention_in_unrelated_command_now_blocks")


def test_site_write_via_junction_blocks():
    """GAP 5: check_file_write matched only the LITERAL file_path string, so
    a directory junction pointing INTO the site tree from an innocuous-
    looking path (whose own path text never contains a site marker) evaded
    detection. Resolving the real path (following junctions/symlinks)
    before matching closes this."""
    tmp = tempfile.mkdtemp(prefix="oag-junction-")
    real_site = os.path.join(tmp, "actual-target", "website-canonical")
    os.makedirs(real_site, exist_ok=True)
    innocuous = os.path.join(tmp, "innocuous-name")
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", innocuous, os.path.join(tmp, "actual-target", "website-canonical")],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("SKIP test_site_write_via_junction_blocks (junction creation unavailable: %s)"
              % (proc.stderr or proc.stdout).strip())
        return
    file_through_junction = os.path.join(innocuous, "index.html")
    assert "website-canonical" not in file_through_junction.replace("\\", "/").lower(), (
        "test setup bug: the junction path must NOT itself contain the site marker"
    )
    rc, out, err = run_hook(write_payload(file_through_junction))
    assert rc == 2, (
        "a write reaching the site tree via a junction must block even though its "
        "own path text names no site marker, got %s (%s)" % (rc, err)
    )
    print("PASS test_site_write_via_junction_blocks")


def test_site_write_via_unrelated_symlink_still_allows():
    """Regression control for GAP 5's fix -- a junction to an ordinary,
    non-site directory must NOT be swept up by the realpath resolution."""
    tmp = tempfile.mkdtemp(prefix="oag-junction-safe-")
    real_other = os.path.join(tmp, "actual-target", "not-the-site")
    os.makedirs(real_other, exist_ok=True)
    innocuous = os.path.join(tmp, "innocuous-name-2")
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", innocuous, real_other],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("SKIP test_site_write_via_unrelated_symlink_still_allows (junction creation unavailable)")
        return
    rc, out, err = run_hook(write_payload(os.path.join(innocuous, "notes.md")))
    assert rc == 0, (
        "a junction to a non-site directory must not block, got %s (%s)" % (rc, err)
    )
    print("PASS test_site_write_via_unrelated_symlink_still_allows")


# --------------------------------------------------------------------------
# ROUND 2 FIXES (2026-07-17) -- fullwidth-@ Unicode homoglyph and the
# send-via-outlook.ps1 8.3 short-name alias, both found trying to break
# Round 1's surviving fixes.
# --------------------------------------------------------------------------

def test_fullwidth_at_sign_email_blocks():
    """A fullwidth Unicode '＠' is invisible to a literal ASCII '@' match --
    EMAIL_RE.findall() returned nothing and Gate 1 never fired: exit 0, zero
    override needed. NFKC normalization folds it to ASCII '@' before matching."""
    rc, out, err = run_hook(send_payload(u"attacker＠evilhost.com"))
    assert rc == 2, "a fullwidth-@ external recipient must block, got %s (%s)" % (rc, err)
    print("PASS test_fullwidth_at_sign_email_blocks")


def test_send_script_8dot3_shortname_blocks():
    """send-via-outlook.ps1 has a standing, zero-setup Windows 8.3 short-name
    alias (SEND-V~1.PS1, confirmed live via `dir /x`) that the plain substring
    check never saw -- reached exit 0 before this fix."""
    cmd = 'powershell -File SEND-V~1.PS1 -To attacker@evilhost.com -Subject hi -Body hi'
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 2, "the 8.3 short-name alias must block, got %s (%s)" % (rc, err)
    print("PASS test_send_script_8dot3_shortname_blocks")


def test_send_script_8dot3_shortname_internal_recipient_allows():
    """Regression control -- the short-name alias with a purely internal
    recipient must still pass, same as the long name would."""
    cmd = 'powershell -File SEND-V~1.PS1 -To ggoldberg@oxfordra.net -Subject hi -Body hi'
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 0, "internal-only recipient via short name must not block, got %s (%s)" % (rc, err)
    print("PASS test_send_script_8dot3_shortname_internal_recipient_allows")


# --------------------------------------------------------------------------
# ROUND 3 FIXES (2026-07-17) -- invisible Unicode characters (Cf/Mn) breaking
# a word-boundary match after NFKC, and check_mcp's allow-by-default suffix
# check. Both found trying to break Round 1+2's surviving fixes.
# --------------------------------------------------------------------------

def test_zero_width_space_in_netlify_blocks():
    """A ZWSP (U+200B) inserted mid-word breaks `\\bnetlify\\b` after NFKC
    alone (NFKC doesn't strip format characters) -- reached exit 0 before
    this fix. Stripping Cf/Mn categories closes it."""
    cmd = u"cmd /c net​lify deploy --build --prod"
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 2, "a ZWSP-split 'netlify' must still block, got %s (%s)" % (rc, err)
    print("PASS test_zero_width_space_in_netlify_blocks")


def test_zero_width_space_in_trigger_phrase_blocks():
    """A ZWSP inside 'send-via-outlook.ps1' itself broke the Gate 1 TRIGGER
    phrase, disabling the gate for that call entirely -- reached exit 0."""
    cmd = u"powershell -File send-via-outlook​.ps1 -To attacker@evilhost.com -Subject hi -Body hi"
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 2, "a ZWSP-split trigger phrase must still block, got %s (%s)" % (rc, err)
    print("PASS test_zero_width_space_in_trigger_phrase_blocks")


def test_rtl_override_in_netlify_blocks():
    """An RTL override character (U+202E) mid-word has the same effect as a
    ZWSP -- breaks the word-boundary match invisibly."""
    cmd = u"cmd /c net‮lify deploy --build --prod"
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 2, "an RTL-override-split 'netlify' must still block, got %s (%s)" % (rc, err)
    print("PASS test_rtl_override_in_netlify_blocks")


def test_combining_mark_in_email_blocks():
    """A combining low line (U+0332, category Mn) inserted in a recipient's
    local-part has the same invisible-break effect as the Cf characters."""
    rc, out, err = run_hook(send_payload(u"n̲etlifyattacker@evilhost.com"))
    assert rc == 2, "a combining-mark-bearing recipient must still block, got %s (%s)" % (rc, err)
    print("PASS test_combining_mark_in_email_blocks")


def test_netlify_mcp_non_reader_non_updater_blocks():
    """check_mcp was allow-by-default (gated only exact '-updater' suffix) --
    a hypothetical mutating tool with any OTHER name evaded it entirely."""
    rc, out, err = run_hook(mcp_payload("mcp__netlify__project-services-writer"))
    assert rc == 2, "a non-reader netlify MCP tool must block by default, got %s (%s)" % (rc, err)
    print("PASS test_netlify_mcp_non_reader_non_updater_blocks")


def test_netlify_mcp_reader_still_allows():
    """Regression control -- every real reader tool in the current connector
    must still pass through ungated."""
    for name in ("mcp__netlify__deploy-services-reader", "mcp__netlify__project-services-reader"):
        rc, out, err = run_hook(mcp_payload(name))
        assert rc == 0, "%s (a reader tool) must not block, got %s (%s)" % (name, rc, err)
    print("PASS test_netlify_mcp_reader_still_allows")


def test_stdin_decoded_as_utf8_not_platform_codepage():
    """sys.stdin.encoding defaults to the PLATFORM codepage (cp1252 on this
    Windows machine), not UTF-8. Reading a REAL multi-byte UTF-8 payload byte
    (not Python's own ensure_ascii=True-escaped ASCII, which every other test
    in this file relies on) through that decoder does not reliably raise -- it
    SILENTLY MOJIBAKES: a UTF-8-encoded soft hyphen (2 bytes: 0xC2 0xAD)
    decoded as cp1252 became TWO wrong characters, one of them a spurious
    VISIBLE character that broke a `\\bnetlify\\b` match which should have
    blocked. This bypasses this file's whole Round-3 Unicode hardening for any
    invocation whose real payload contains literal (non-\\uXXXX-escaped)
    non-ASCII bytes. Constructs the payload with ensure_ascii=False and writes
    RAW UTF-8 bytes directly to the subprocess's stdin (bypassing run_hook's
    normal ensure_ascii=True path, which never exercises this bug)."""
    sessions_dir = fresh_sessions_dir()
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": u"cmd /c net­lify deploy --build --prod"},
        "session_id": SESSION_A,
    }
    raw_utf8 = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK], input=raw_utf8, capture_output=True, env=env,
    )
    assert proc.returncode == 2, (
        "a real UTF-8-encoded soft-hyphen-split 'netlify' must still block, got %s (%s)"
        % (proc.returncode, proc.stderr)
    )
    print("PASS test_stdin_decoded_as_utf8_not_platform_codepage")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("ALL AUTONOMY-GATE TESTS PASS (%d)" % len(tests))
