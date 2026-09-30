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

import ast
import importlib.util
import inspect
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
    # ignore="sessions": the gate resolves its session-override dir via the ORA_OVERRIDE_
    # SESSIONS_DIR test seam (set below, per invocation) or else DEFAULT_SESSIONS_DIR, which
    # is an ABSOLUTE path to the real hooks/sessions -- never anything relative to this copied
    # tree. Copying the real hooks/sessions/ here was therefore always dead weight, and with
    # many Claude Code sessions routinely live in this shared checkout, it collided with their
    # concurrent writes there: found 2026-08-28 (session aa0eb89c) as a shutil.copytree crash
    # racing test_sessions_reviews_excluded_e2e's own scratch session dir.
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"),
                    ignore=shutil.ignore_patterns("sessions"))
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


def test_stale_token_module_without_consume_param_fails_closed():
    """SAME failure mode as test_broken_token_module_fails_closed, different trigger:
    a version-SKEWED (not missing/broken) override_tokens.py whose token_grants() predates
    the `consume` keyword this gate now always passes.

    Adversarial review, 2026-08-24: a plain `from override_tokens import token_grants`
    succeeds against such a module -- only the CALL fails, with TypeError, not the import.
    Unguarded, that TypeError would propagate past the except-Exception import fallback
    (which had already committed to TOKEN_CONTRACT_LOADED = True) and crash the process
    with exit 1 -- non-blocking for PreToolUse, so the gated action would proceed with NO
    authorization check at all. This environment routinely runs several concurrent sessions
    and worktrees against a shared ~/.claude checkout, and override_tokens.py is edited for
    the doctrine gate too, so this is a real reachable state, not a hypothetical.

    The fix: ora-autonomy-gate.py's import block now inspects token_grants' signature and
    raises (routing through the SAME fallback stub as a missing module) if `consume` is
    absent. This test proves that guard actually fires, using a real stale module -- copied
    from a fixture with the `consume` parameter stripped, not just deleted -- so this
    exercises the ONE failure mode the signature check exists for that
    test_broken_token_module_fails_closed does not.
    """
    sandbox = tempfile.mkdtemp(prefix="oag-stale-")
    # ignore="sessions": the gate resolves its session-override dir via the ORA_OVERRIDE_
    # SESSIONS_DIR test seam (set below, per invocation) or else DEFAULT_SESSIONS_DIR, which
    # is an ABSOLUTE path to the real hooks/sessions -- never anything relative to this copied
    # tree. Copying the real hooks/sessions/ here was therefore always dead weight, and with
    # many Claude Code sessions routinely live in this shared checkout, it collided with their
    # concurrent writes there: found 2026-08-28 (session aa0eb89c) as a shutil.copytree crash
    # racing test_sessions_reviews_excluded_e2e's own scratch session dir.
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"),
                    ignore=shutil.ignore_patterns("sessions"))
    gate = os.path.join(sandbox, "hooks", "ora-autonomy-gate.py")
    stale_lib_path = os.path.join(sandbox, "hooks", "lib", "override_tokens.py")
    real_lib_path = os.path.join(os.path.dirname(HOOK), "lib", "override_tokens.py")
    with open(real_lib_path, "r", encoding="utf-8") as fh:
        real_source = fh.read()
    # Strip ONLY the `consume` parameter/behavior, leaving everything else (path resolution,
    # freshness, parsing, scope/session checks) exactly as the real module -- this must be a
    # believable "older version", not a stub, or the test would not be exercising the actual
    # signature-mismatch path.
    stale_source = real_source.replace(
        "def token_grants(session_id, tier, extra_check=None, consume=True):",
        "def token_grants(session_id, tier, extra_check=None):",
    ).replace(
        "if consume and tier.single_use and not consume_token(path):",
        "if tier.single_use and not consume_token(path):",
    )
    with open(stale_lib_path, "w", encoding="utf-8") as fh:
        fh.write(stale_source)
    # Verify the fixture STRUCTURALLY (via the actual function signature, not a string/prose
    # search -- the docstring legitimately still says "consume" throughout its explanation of
    # WHY the parameter is being removed) before trusting the test that follows.
    _spec = importlib.util.spec_from_file_location("stale_override_tokens", stale_lib_path)
    _stale_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_stale_mod)
    assert "consume" not in inspect.signature(_stale_mod.token_grants).parameters, (
        "fixture setup failed -- the stale token_grants() still has a 'consume' parameter; "
        "this test would not be exercising the version-skew path it claims to")

    def run_stale(payload):
        env = dict(os.environ)
        env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-stale-sess-")
        payload = dict(payload)
        payload["session_id"] = SESSION_A
        proc = subprocess.run([sys.executable, gate], input=json.dumps(payload),
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr

    for label, payload in (
        ("prod deploy", bash_payload(PROD_DEPLOY)),
        ("external send", bash_payload(
            "powershell -File send-via-outlook.ps1 -To broker@example.com -Subject x -Body y")),
    ):
        rc, err = run_stale(payload)
        assert rc == 2, (
            "%s must BLOCK (exit 2) against a stale override_tokens.py missing the "
            "'consume' parameter, got exit %s -- exit 1 (an uncaught TypeError) is "
            "NON-BLOCKING for PreToolUse and would let the action through with NO "
            "authorization check at all.\n%s" % (label, rc, err))

    # An UNGATED call must still pass -- the signature guard degrades exactly like any other
    # broken-module case, not more aggressively.
    rc, err = run_stale(write_payload("C:/proj/src/index.html"))
    assert rc == 0, (
        "an ungated call must still pass with a stale module (got exit %s)\n%s" % (rc, err))

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_stale_token_module_without_consume_param_fails_closed")


def test_broken_email_send_tier_fails_closed():
    """A broken/missing hooks/lib/email_send_tier.py (added 2026-07-17 for the outbound-
    action check, OI-007) must ALSO still block every gated action -- not just external
    send. Same failure shape as test_broken_token_module_fails_closed: both modules are
    imported in ONE try/except so a broken email_send_tier.py (while override_tokens.py
    stays intact) degrades exactly as fail-closed, not silently disabling Gate 1."""
    sandbox = tempfile.mkdtemp(prefix="oag-broken-est-")
    # ignore="sessions": the gate resolves its session-override dir via the ORA_OVERRIDE_
    # SESSIONS_DIR test seam (set below, per invocation) or else DEFAULT_SESSIONS_DIR, which
    # is an ABSOLUTE path to the real hooks/sessions -- never anything relative to this copied
    # tree. Copying the real hooks/sessions/ here was therefore always dead weight, and with
    # many Claude Code sessions routinely live in this shared checkout, it collided with their
    # concurrent writes there: found 2026-08-28 (session aa0eb89c) as a shutil.copytree crash
    # racing test_sessions_reviews_excluded_e2e's own scratch session dir.
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"),
                    ignore=shutil.ignore_patterns("sessions"))
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
    # ignore="sessions": the gate resolves its session-override dir via the ORA_OVERRIDE_
    # SESSIONS_DIR test seam (set below, per invocation) or else DEFAULT_SESSIONS_DIR, which
    # is an ABSOLUTE path to the real hooks/sessions -- never anything relative to this copied
    # tree. Copying the real hooks/sessions/ here was therefore always dead weight, and with
    # many Claude Code sessions routinely live in this shared checkout, it collided with their
    # concurrent writes there: found 2026-08-28 (session aa0eb89c) as a shutil.copytree crash
    # racing test_sessions_reviews_excluded_e2e's own scratch session dir.
    shutil.copytree(os.path.dirname(HOOK), os.path.join(sandbox, "hooks"),
                    ignore=shutil.ignore_patterns("sessions"))
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

def test_gate_2a_deploy_check_peeks_and_does_not_consume():
    """SUPERSEDES the pre-2026-08-24 'deploy grant is consumed at gate-pass' rule.

    Gate 2a is the fast, explicitly-documented-as-indirection-blind PreToolUse pre-check
    (see the module docstring's ALSO DEFERRED section) -- it is NOT the authoritative
    enforcement point for a CLI deploy; netlify-guard.js's check_website_deploy.py is (it
    runs after argv is fully resolved, immune to indirection, and its own docstring already
    says the grant is "consumed as a side effect of THIS check"). Before 2026-08-24, Gate 2a
    ALSO consumed the same single-use token via override_active()'s default consume=True,
    so a real `netlify deploy --build --prod` run reached exit 0 here (token burned) and
    then exit 5 (DENY) inside netlify-guard.js's own check moments later -- a correctly
    authorized deploy could never complete. Proven live 2026-08-24, root-caused, and fixed
    by passing consume=False at this call site (see override_tokens.token_grants' own
    docstring for the full two-layer rationale). This test locks in the fix: Gate 2a must
    grant WITHOUT touching the token file, and must do so again identically on a second
    check with the SAME still-valid token -- proving it is a genuine peek, not merely
    delayed consumption. test_check_website_deploy_consumes_after_gate_2a_peek below proves
    the OTHER half: the downstream layer still enforces single-use correctly."""
    d = fresh_sessions_dir()
    path = mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, "first deploy check must pass, got %s (%s)" % (rc, err)
    assert os.path.exists(path), (
        "Gate 2a must NOT consume the token -- it is a peek; the downstream "
        "check_website_deploy.py is the sole intended consumer")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, (
        "a second Gate 2a check against the SAME still-valid token must also pass "
        "(not merely delayed single-use) -- got %s (%s)" % (rc, err))
    print("PASS test_gate_2a_deploy_check_peeks_and_does_not_consume")


def test_check_website_deploy_consumes_after_gate_2a_peek():
    """The direct regression test for the 2026-08-24 incident: run the REAL two-layer
    flow end to end -- Gate 2a's PreToolUse peek, then the actual downstream
    check_website_deploy.py subprocess netlify-guard.js invokes -- and prove a single,
    freshly-minted token satisfies BOTH. Before the fix this sequence failed at the
    second step with exit 1 (DENY), reproducing exit 5 from netlify-guard.js in production."""
    d = fresh_sessions_dir()
    mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(bash_payload(PROD_DEPLOY), sessions_dir=d)
    assert rc == 0, "Gate 2a must pass first, got %s (%s)" % (rc, err)
    check_script = os.path.join(HERE, "lib", "check_website_deploy.py")
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = d
    proc = subprocess.run(
        [sys.executable, check_script, "--session", SESSION_A],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, (
        "check_website_deploy.py must ALLOW using the same token Gate 2a already peeked "
        "at, got exit %s (%s) -- this is the exact incident this fix closes"
        % (proc.returncode, proc.stderr))
    proc2 = subprocess.run(
        [sys.executable, check_script, "--session", SESSION_A],
        capture_output=True, text=True, env=env,
    )
    assert proc2.returncode == 1, (
        "a second check_website_deploy.py call must DENY -- single-use is still enforced, "
        "just at the correct (downstream) layer now, got exit %s" % proc2.returncode)
    print("PASS test_check_website_deploy_consumes_after_gate_2a_peek")


def test_gate_1_send_check_peeks_and_does_not_consume():
    """Same fix, same rationale, applied to the EXTERNAL_SEND sibling of the deploy bug
    (Gate 1 / check_external_send.py inside send-via-outlook.ps1). See
    test_gate_2a_deploy_check_peeks_and_does_not_consume's docstring for the full story."""
    d = fresh_sessions_dir()
    path = mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 0, "first Gate 1 check must pass, got %s (%s)" % (rc, err)
    assert os.path.exists(path), (
        "Gate 1 must NOT consume the token -- check_external_send.py is the sole "
        "intended consumer")
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 0, (
        "a second Gate 1 check against the SAME still-valid token must also pass, "
        "got %s (%s)" % (rc, err))
    print("PASS test_gate_1_send_check_peeks_and_does_not_consume")


def test_check_external_send_consumes_after_gate_1_peek():
    """End-to-end regression test mirroring
    test_check_website_deploy_consumes_after_gate_2a_peek, for the email-send path."""
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["broker@example.com"])
    rc, out, err = run_hook(send_payload("broker@example.com"), sessions_dir=d)
    assert rc == 0, "Gate 1 must pass first, got %s (%s)" % (rc, err)
    check_script = os.path.join(HERE, "lib", "check_external_send.py")
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = d
    proc = subprocess.run(
        [sys.executable, check_script, "--session", SESSION_A],
        input="broker@example.com\n", capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, (
        "check_external_send.py must ALLOW using the same token Gate 1 already peeked "
        "at, got exit %s (%s)" % (proc.returncode, proc.stderr))
    proc2 = subprocess.run(
        [sys.executable, check_script, "--session", SESSION_A],
        input="broker@example.com\n", capture_output=True, text=True, env=env,
    )
    assert proc2.returncode == 1, (
        "a second check_external_send.py call must DENY -- single-use is still enforced "
        "at the correct layer, got exit %s" % proc2.returncode)
    print("PASS test_check_external_send_consumes_after_gate_1_peek")


def test_netlify_mcp_deploy_token_is_still_single_use():
    """ASYMMETRY LOCK, not a regression of the 2026-08-24 fix: the Netlify MCP
    mutating-tool path (Gate 2c/check_mcp) has NO downstream wrapped-binary layer to
    defer to -- it is the ONLY enforcement point for that action, so it must keep
    consuming the token itself (override_active's default consume=True). If a future
    edit accidentally set consume=False here too, a single grant could authorize
    unlimited MCP prod-deploy-equivalent calls within the token's 5-minute window."""
    d = fresh_sessions_dir()
    path = mint(d, "allow-website-deploy", "website-deploy")
    rc, out, err = run_hook(mcp_payload("mcp__netlify__project-updater"), sessions_dir=d)
    assert rc == 0, "first MCP updater call must pass, got %s (%s)" % (rc, err)
    assert not os.path.exists(path), (
        "the MCP path has no downstream check -- it MUST consume the token itself")
    rc, out, err = run_hook(mcp_payload("mcp__netlify__project-updater"), sessions_dir=d)
    assert rc == 2, "a second MCP updater call on a consumed token must block, got %s (%s)" % (rc, err)
    print("PASS test_netlify_mcp_deploy_token_is_still_single_use")


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


# ---------------------------------------------------------------------------
# 2026-09-18 -- check_file_write's Claude-managed slug-directory exemption.
#
# Claude Code names two directories after the PROJECT PATH, so working in the site repo
# produces slugs that embed a site marker while pointing nowhere near the site tree:
#   ~/.claude/projects/C--Users-Owner-website-canonical/memory/
#   %TEMP%/claude/C--Users-Owner-website-canonical/<session>/scratchpad/
# Both blocked every Write (confirmed live, exit 2), so a session in this project could
# not save a memory without minting a live-site write override. The exemption keys on the
# RESOLVED real path only; these tests pin both the relief and its boundaries.
# ---------------------------------------------------------------------------

# The hook derives its anchor from its own location (hooks/ -> .claude/); mirror that
# here so these tests follow the file whether it runs from a worktree or the live tree.
CLAUDE_ROOT = os.path.dirname(HERE)
SLUG = "C--Users-Owner-website-canonical"
OTHER_MARKER = "oxford-site"


def _load_hook_module():
    """Import the hook for direct unit calls. main() is under a __main__ guard, so import
    is side-effect-free apart from resolving the module-level exemption anchors."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ora_autonomy_gate_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_project_memory_write_allowed():
    """The reported friction: this session's OWN memory directory is not the site tree."""
    path = os.path.join(CLAUDE_ROOT, "projects", SLUG, "memory", "reference_x.md")
    rc, out, err = run_hook(write_payload(path))
    assert rc == 0, (
        "a write to the project memory dir must not need a live-site override, got %s (%s)"
        % (rc, err)
    )
    print("PASS test_project_memory_write_allowed")


def test_session_scratchpad_write_allowed():
    """The harness MANDATES the scratchpad for temp files, and its slug embeds the marker."""
    path = os.path.join(tempfile.gettempdir(), "claude", SLUG, SESSION_A, "scratchpad", "n.txt")
    rc, out, err = run_hook(write_payload(path))
    assert rc == 0, (
        "a write to the session scratchpad must not need a live-site override, got %s (%s)"
        % (rc, err)
    )
    print("PASS test_session_scratchpad_write_allowed")


def test_real_site_tree_write_still_blocks():
    """Control for the two tests above -- the gate's actual job is untouched."""
    for path in (SITE_FILE, "C:/Users/Owner/%s/index.html" % OTHER_MARKER):
        rc, out, err = run_hook(write_payload(path))
        assert rc == 2, "a real site-tree write must still block: %s got %s (%s)" % (path, rc, err)
    print("PASS test_real_site_tree_write_still_blocks")


def test_slug_dir_exemption_defeated_by_junction():
    """The exemption keys on the RESOLVED path, so a directory named exactly like an
    exempt scratchpad but junctioned INTO the site tree resolves back out of the
    exemption and still blocks. This is the bypass a literal-text exemption would open."""
    tmp = tempfile.mkdtemp(prefix="oag-slugjunc-")
    real_site = os.path.join(tmp, "actual-target", "website-canonical")
    os.makedirs(real_site, exist_ok=True)
    fake = os.path.join(tempfile.gettempdir(), "claude", "oag-slugjunc-" + SESSION_A,
                        SESSION_B, "scratchpad")
    os.makedirs(os.path.dirname(fake), exist_ok=True)
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", fake, real_site],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print("SKIP test_slug_dir_exemption_defeated_by_junction (junction unavailable: %s)"
              % (proc.stderr or proc.stdout).strip())
        return
    try:
        rc, out, err = run_hook(write_payload(os.path.join(fake, "index.html")))
        assert rc == 2, (
            "a scratchpad-shaped path junctioned into the site tree must still block, "
            "got %s (%s)" % (rc, err)
        )
    finally:
        subprocess.run(["cmd", "/c", "rmdir", fake], capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(os.path.join(tempfile.gettempdir(), "claude",
                                   "oag-slugjunc-" + SESSION_A), ignore_errors=True)
    print("PASS test_slug_dir_exemption_defeated_by_junction")


def test_dot_claude_inside_site_tree_not_exempt():
    """The exemption is ANCHORED to the real Claude root, not to the shape alone -- so a
    `.claude/projects/<slug>/memory/` directory sitting INSIDE a site checkout matches the
    shape but not the anchor, and a write into the site repo still blocks."""
    path = "C:/Users/Owner/website-canonical/.claude/projects/%s/memory/y.md" % SLUG
    rc, out, err = run_hook(write_payload(path))
    assert rc == 2, (
        "a memory-shaped path inside the site checkout must still block, got %s (%s)"
        % (rc, err)
    )
    print("PASS test_dot_claude_inside_site_tree_not_exempt")


def test_slug_dir_exemption_is_narrow():
    """Only the two named shapes are exempt. A sibling directory under the same project
    slug, or the slug directory itself, still carries the marker and still blocks --
    the fix relieves the reported friction, it does not open `~/.claude/projects/<slug>/`."""
    for path in (
        os.path.join(CLAUDE_ROOT, "projects", SLUG, "todos", "x.md"),
        os.path.join(CLAUDE_ROOT, "projects", SLUG, "memory.md"),
        os.path.join(tempfile.gettempdir(), "claude", SLUG, SESSION_A, "not-scratchpad", "n.txt"),
    ):
        rc, out, err = run_hook(write_payload(path))
        assert rc == 2, "outside the exempt shapes must still block: %s got %s (%s)" % (
            path, rc, err)
    print("PASS test_slug_dir_exemption_is_narrow")


def _junction(link_path, target):
    """mklink /J, returning False when junctions are unavailable in this environment."""
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", link_path, target],
                          capture_output=True, text=True)
    return proc.returncode == 0


def test_normalization_differential_junction_blocks():
    """CRITICAL, adversarial review 2026-09-18. The exemption resolved the NORMALIZED path
    while the Write tool opens the LITERAL one. A directory whose name differs from an
    exempt directory only by a character that NFKC folds or that the Cf/Mn strip deletes is
    a DIFFERENT object to Windows and the SAME object to this hook -- so a junction named
    `scratchpad<ZWSP>` pointing into a site checkout was exempted while the bytes landed in
    the site tree (exit 0, proven). `mklink` is not a write indicator, so Gate 2b does not
    see the junction being created either: the whole chain needed no override.

    Each variant below is test_slug_dir_exemption_defeated_by_junction with ONE character
    changed. They must all block."""
    tmp = tempfile.mkdtemp(prefix="oag-normdiff-")
    real_site = os.path.join(tmp, "actual-target", "website-canonical")
    os.makedirs(real_site, exist_ok=True)
    variants = [
        ("zero-width space (Cf, stripped)", u"scratchpad\u200b"),
        ("fullwidth latin (NFKC-folded)", u"\uff53\uff43\uff52\uff41\uff54\uff43\uff48"
                                          u"\uff50\uff41\uff44"),
        ("combining low line (Mn, stripped)", u"scratchpad\u0332"),
    ]
    made_any = False
    for label, component in variants:
        base = os.path.join(tempfile.gettempdir(), "claude",
                            "oag-normdiff-" + SESSION_A, SESSION_B + label[:3])
        link = os.path.join(base, component)
        if not _junction(link, real_site):
            continue
        made_any = True
        try:
            assert _normalize_for_matching_component(component) != component, (
                "test setup bug: %s must not be a normalization fixed point" % label)
            rc, out, err = run_hook(write_payload(os.path.join(link, "index.html")))
            assert rc == 2, (
                "a junction into the site tree named `%s` must block, got %s (%s)"
                % (label, rc, err)
            )
        finally:
            # rmdir the LINK, then remove the sandbox parent. Removing only the link
            # leaves junction sandboxes outliving the session that made them, and a
            # future pass that points one at the real checkout and forgets it would
            # leave a standing alias into the live site tree (adversarial review,
            # 2026-09-18, which found this suite's own leftovers still on disk).
            subprocess.run(["cmd", "/c", "rmdir", link], capture_output=True, text=True)
            shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(os.path.join(tempfile.gettempdir(), "claude",
                               "oag-normdiff-" + SESSION_A), ignore_errors=True)
    if not made_any:
        print("SKIP test_normalization_differential_junction_blocks (junctions unavailable)")
        return
    print("PASS test_normalization_differential_junction_blocks")


def _normalize_for_matching_component(text):
    """Local mirror of the hook's normalization, for test SETUP assertions only."""
    import unicodedata
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded
                   if unicodedata.category(ch) not in ("Cf", "Mn"))


def test_invisible_char_junction_blocks_without_any_slug():
    """Same root cause, but PRE-EXISTING on main and reachable with no slug directory
    anywhere: a junction whose name carries an invisible character, sitting in an ordinary
    temp directory, resolved to the site tree while the hook resolved the normalized name
    to something else -- exit 0 on both main and the first draft of this branch. Marker-
    matching the realpath of the RAW path closes it. No exemption is involved; this pins
    the base gate."""
    tmp = tempfile.mkdtemp(prefix="oag-plainjunc-")
    real_site = os.path.join(tmp, "actual-target", "oxford-site")
    os.makedirs(real_site, exist_ok=True)
    link = os.path.join(tmp, u"mem\u200bory")
    if not _junction(link, real_site):
        print("SKIP test_invisible_char_junction_blocks_without_any_slug (junctions unavailable)")
        return
    target = os.path.join(link, "a.html")
    assert not any(m in target.replace("\\", "/").lower()
                   for m in ("website-canonical", "oxford-site")), (
        "test setup bug: the literal path must name no site marker")
    try:
        rc, out, err = run_hook(write_payload(target))
        assert rc == 2, (
            "a write reaching the site tree through an invisible-character junction must "
            "block even with no slug directory involved, got %s (%s)" % (rc, err)
        )
    finally:
        subprocess.run(["cmd", "/c", "rmdir", link], capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_invisible_char_junction_blocks_without_any_slug")


def test_embedded_nul_path_is_not_exempt():
    """os.path.realpath() swallows the ValueError for an embedded NUL and returns an
    UNRESOLVED normpath, so the exemption would have been reachable on a path the
    filesystem never confirmed. Benign today only because Node refuses NUL in paths --
    pinned so it stays that way."""
    path = os.path.join(tempfile.gettempdir(), "claude", SLUG, SESSION_A,
                        "scratchpad", "c\x00.txt")
    rc, out, err = run_hook(write_payload(path))
    assert rc == 2, "a NUL-bearing path must never be exempt, got %s (%s)" % (rc, err)
    print("PASS test_embedded_nul_path_is_not_exempt")


def test_gettempdir_failure_yields_no_anchor_not_a_crash():
    """The branch test_hostile_temp_vars_do_not_disable_the_gate does NOT reach (adversarial
    review, 2026-09-18: with the temp vars SET, `_temp_dir_names()` returns them and the
    guarded gettempdir() call is never made, so that test proves the env path only).

    A module-level tempfile.gettempdir() raises FileNotFoundError when no candidate temp dir
    is writable, and this hook exiting 1 is treated as NON-BLOCKING by the harness -- so an
    unguarded traceback would not merely lose the exemption, it would silently disable Gates
    1/2a/2b/2c for that call. Strictly worse than any narrowing miss. Clear the vars so the
    fallback is actually taken, and make it raise."""
    mod = _load_hook_module()
    saved_env = dict(os.environ)
    saved_gettempdir = mod.tempfile.gettempdir
    try:
        for var in ("TEMP", "TMP", "TMPDIR"):
            os.environ.pop(var, None)

        def _boom():
            raise FileNotFoundError("No usable temporary directory found")

        mod.tempfile.gettempdir = _boom
        assert mod._temp_dir_names() == [], (
            "a raising gettempdir() with no temp vars set must yield NO anchor, not an "
            "exception: got %r" % (mod._temp_dir_names(),)
        )
    finally:
        mod.tempfile.gettempdir = saved_gettempdir
        os.environ.clear()
        os.environ.update(saved_env)
    print("PASS test_gettempdir_failure_yields_no_anchor_not_a_crash")


def test_existing_hardlink_forfeits_the_exemption():
    """A hardlink is a second NAME for one inode, not a reparse point -- realpath() has
    nothing to follow, so a file inside an exempt directory that is hardlinked to a site
    file would be written through the exempt name. The general hardlink class is documented
    as deferred and is reachable today through any marker-free path with no exemption
    involved; this pins only that the exemption does not become a second, more convenient
    spelling of it (adversarial review, 2026-09-18)."""
    tmp = tempfile.mkdtemp(prefix="oag-hardlink-")
    site_dir = os.path.join(tmp, "target", "website-canonical")
    os.makedirs(site_dir, exist_ok=True)
    site_file = os.path.join(site_dir, "index.html")
    with open(site_file, "w") as handle:
        handle.write("original")
    # The slug component must be the REAL marker-bearing slug: with a marker-free slug the
    # path trips no marker match at all, the gate returns without ever reaching the
    # exemption, and the test would pass vacuously against the pre-existing hardlink class
    # rather than against this exemption.
    exempt_dir = os.path.join(tempfile.gettempdir(), "claude", SLUG,
                              "oag-hardlink-" + SESSION_B, "scratchpad")
    os.makedirs(exempt_dir, exist_ok=True)
    link = os.path.join(exempt_dir, "hl.txt")
    try:
        os.link(site_file, link)
    except (OSError, NotImplementedError, AttributeError) as exc:
        print("SKIP test_existing_hardlink_forfeits_the_exemption (hardlinks unavailable: %s)"
              % exc)
        shutil.rmtree(tmp, ignore_errors=True)
        return
    try:
        rc, out, err = run_hook(write_payload(link))
        assert rc == 2, (
            "an exempt-shaped path that is already a hardlink must forfeit the exemption, "
            "got %s (%s)" % (rc, err)
        )
        # Control: an ordinary new file in the same exempt directory still passes, so the
        # guard costs nothing in the case this whole change exists to enable.
        rc, out, err = run_hook(write_payload(os.path.join(exempt_dir, "ordinary.txt")))
        assert rc == 0, "an ordinary scratchpad write must still pass, got %s (%s)" % (rc, err)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Remove the session PARENT, not just the scratchpad leaf, or an empty
        # oag-hardlink-* directory outlives every run (adversarial re-review, 2026-09-18).
        shutil.rmtree(os.path.dirname(exempt_dir), ignore_errors=True)
    print("PASS test_existing_hardlink_forfeits_the_exemption")


def test_overlong_exempt_path_blocks_and_does_not_crash():
    """os.stat() raises ValueError -- NOT OSError -- at >= 32768 characters on Windows
    ("stat: path too long for Windows"), while os.path.realpath() at that length does not
    raise. So resolve_ok stays True, the four earlier exemption conditions pass on an
    exempt-SHAPED path, and an uncaught throw in _is_multiply_linked escapes
    check_file_write. This hook exiting 1 is NON-BLOCKING, so that would disable Gates
    1/2a/2b/2c for the call -- strictly worse than any narrowing miss, and the exact class
    the realpath guard already catches. Exit 1 is the failure this pins; exit 2 is the
    contract (adversarial re-review, 2026-09-18)."""
    path = os.path.join(tempfile.gettempdir(), "claude", SLUG, SESSION_A, "scratchpad",
                        "a" * 40000)
    rc, out, err = run_hook(write_payload(path))
    assert rc != 1, (
        "an overlong exempt-shaped path must never crash the hook to exit 1 (the harness "
        "treats that as NON-BLOCKING, disabling every gate for this call): %s" % err[:400]
    )
    assert rc == 2, "an overlong exempt-shaped path must block, got %s (%s)" % (rc, err)
    print("PASS test_overlong_exempt_path_blocks_and_does_not_crash")


def test_hostile_temp_vars_do_not_disable_the_gate():
    """Every temp variable pointed at a nonexistent directory: the site-tree write must
    still BLOCK (exit 2), never crash (exit 1). Covers the env path; the guarded
    gettempdir() fallback is covered by the test above."""
    env_overrides = {"TMPDIR": r"Z:\no-such-temp-dir",
                     "TEMP": r"Z:\no-such-temp-dir",
                     "TMP": r"Z:\no-such-temp-dir"}
    env = dict(os.environ)
    env.update(env_overrides)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = fresh_sessions_dir()
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": SITE_FILE, "content": "x"},
               "session_id": SESSION_A}
    proc = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 2, (
        "with no usable temp dir the gate must still BLOCK a site write, got %s (%s)"
        % (proc.returncode, proc.stderr)
    )
    print("PASS test_hostile_temp_vars_do_not_disable_the_gate")


def test_exemption_anchor_refuses_site_contaminated_root():
    """If the hook layer itself were ever relocated under a site checkout, the anchor must
    be discarded rather than becoming a write hole into that checkout."""
    mod = _load_hook_module()
    assert mod._exemption_anchor("C:/Users/Owner/website-canonical/.claude") is None, (
        "an anchor root inside the site tree must yield no exemption"
    )
    assert mod._exemption_anchor("C:/Users/Owner/%s/.claude" % OTHER_MARKER) is None, (
        "an anchor root inside the second site checkout must yield no exemption"
    )
    assert mod._exemption_anchor(CLAUDE_ROOT) is not None, (
        "control: the real Claude root must resolve to a usable anchor"
    )
    print("PASS test_exemption_anchor_refuses_site_contaminated_root")


# --------------------------------------------------------------------------
# STRIP_CATEGORIES single-source-of-truth (2026-09-18)
#
# Until this change the gate carried its OWN `_STRIP_CATEGORIES = ("Cf", "Mn")`,
# duplicating hooks/lib/tool_call_paths.py's copy (which feeds normalize_text for three of
# its six importing guards). Nothing kept them in sync, and the failure mode was silent and
# one-directional: harden the lib copy, forget this one, and the hook with the broadest
# blast radius -- the SOLE enforcement of hard invariant 2 under bypassPermissions, where
# no permission prompt exists as a backstop -- quietly becomes the layer's WEAKEST
# normalizer while the guards routing through normalize_text are stronger. No test goes
# red; nothing throws.
#
# The tests below pin the three things that make the collapse real rather than cosmetic:
# the gate's behavior FOLLOWS the shared module (not a local copy), the one hardcoded
# fallback copy that must survive a missing module cannot drift from it, and the fallback
# actually keeps both gates armed.
# --------------------------------------------------------------------------

LIB_DIR = os.path.join(HERE, "lib")

# A Cc control character mid-word is the differential probe: it is NOT in the shipped
# category set, so it currently defeats the `\bnetlify\b` match exactly the way a ZWSP did
# before Round 3 -- verified live, exit 0 below. That makes it the one input whose verdict
# flips when, and only when, the SHARED module's tuple changes.
CTRL_SPLIT_DEPLOY = "cmd /c net\x01lify deploy --build --prod"


def _shared_strip_categories():
    """The canonical tuple, loaded from hooks/lib/text_normalization.py by path so this
    test never depends on sys.path ordering (or on the gate having imported it)."""
    spec = importlib.util.spec_from_file_location(
        "_text_normalization_under_test", os.path.join(LIB_DIR, "text_normalization.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.STRIP_CATEGORIES


_ISO_ROOTS = []


def _isolated_gate(shared_module_source=None, drop_shared_module=False):
    """Copy the gate + the whole lib/ into a temp tree and return the copied gate's path,
    optionally rewriting or deleting the shared normalization module in that copy ONLY.
    The real tree is never touched. Roots are registered for cleanup at the end of the
    run (sibling tests clean their sandboxes; these copy the whole lib/ three times)."""
    root = tempfile.mkdtemp(prefix="oag-iso-")
    _ISO_ROOTS.append(root)
    hooks_dir = os.path.join(root, "hooks")
    os.makedirs(hooks_dir)
    shutil.copy2(HOOK, os.path.join(hooks_dir, "ora-autonomy-gate.py"))
    shutil.copytree(LIB_DIR, os.path.join(hooks_dir, "lib"))
    target = os.path.join(hooks_dir, "lib", "text_normalization.py")
    if drop_shared_module:
        os.remove(target)
    elif shared_module_source is not None:
        with open(target, "w", encoding="ascii") as fh:
            fh.write(shared_module_source)
    return os.path.join(hooks_dir, "ora-autonomy-gate.py")


def _run_gate(gate_path, command):
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = fresh_sessions_dir()
    # Scrub PYTHONPATH (2026-09-18 review finding): it is INHERITED, so a developer or CI
    # runner with the real hooks/lib on PYTHONPATH would let the copied gate import the
    # REAL text_normalization.py -- and the drop_shared_module test would pass vacuously,
    # proving nothing. Verified: with PYTHONPATH set to the real lib, the missing-module
    # case still returned exit 2 because the module was found elsewhere.
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, gate_path],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                          "session_id": SESSION_A}),
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stderr


def test_control_char_split_netlify_is_the_live_differential():
    """Control (baseline) for the test below, and a standing statement of scope: Cc is NOT
    stripped today, so a control character mid-word still defeats Gate 2a. That is the
    SHIPPED posture -- widening the category set is a deliberate decision with its own
    false-positive budget, not something to slip in here. This test exists so the
    differential test below cannot silently become a tautology if Cc is ever added: add it
    and this test goes red first, on purpose."""
    rc, out, err = run_hook(bash_payload(CTRL_SPLIT_DEPLOY))
    assert rc == 0, (
        "premise broken: a Cc-split 'netlify' is expected to pass on the shipped category "
        "set (that is what makes it a usable differential probe), got exit %s" % rc)
    print("PASS test_control_char_split_netlify_is_the_live_differential")


def test_strip_categories_comes_from_shared_module():
    """THE test the duplication defeated. Harden ONLY hooks/lib/text_normalization.py --
    nothing in the gate -- and the gate's verdict must change. Before 2026-09-18 the gate
    read its own copy, so this input stayed exit 0 no matter what the shared module said,
    which is precisely the silent divergence this change closes."""
    hardened = ('"""Hardened copy for test_strip_categories_comes_from_shared_module.\n'
                'ASCII-only."""\n'
                'STRIP_CATEGORIES = ("Cf", "Mn", "Cc")\n')
    gate = _isolated_gate(shared_module_source=hardened)
    rc, err = _run_gate(gate, CTRL_SPLIT_DEPLOY)
    assert rc == 2, (
        "adding Cc to the SHARED module must arm the gate against a Cc-split 'netlify' "
        "(it is exit 0 on the shipped set -- see the control test). Got exit %s (%s). "
        "A still-passing call here means the gate is reading a LOCAL copy of "
        "STRIP_CATEGORIES again." % (rc, err))
    # ... and the unmodified copy of the same tree must still allow it, so the result above
    # is attributable to the one-line module edit and not to the copying itself.
    rc_ctl, _ = _run_gate(_isolated_gate(), CTRL_SPLIT_DEPLOY)
    assert rc_ctl == 0, (
        "control: an UNMODIFIED copied tree must reproduce the shipped verdict (exit 0), "
        "got %s -- the differential above is not attributable" % rc_ctl)
    print("PASS test_strip_categories_comes_from_shared_module")


def test_strip_categories_fallback_matches_shared_module():
    """The gate keeps ONE hardcoded fallback copy, because an uncaught ImportError exits 1,
    which PreToolUse treats as a non-blocking error -- the tool call PROCEEDS and both
    gates go silently off. That copy is therefore mandatory, and it is also the only thing
    left that can drift, so it is pinned here BY VALUE against the shared module.

    Parsed with ast rather than imported: importing the gate would resolve the try branch
    and never show what the except branch actually holds.

    The structural check is deliberately STRICT about placement (2026-09-18 review: a
    looser `ast.walk` version accepted 5 of 7 dead-code placements -- a nested def, an
    `if False:`, a class body, an unrelated handler elsewhere in the file -- each of which
    leaves the gate exiting 1 when the module is missing, and it false-RED'd a valid
    annotated assignment). The fallback must be a DIRECT statement of the handler attached
    to the try that imports the name."""
    with open(HOOK, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    def _targets_name(node):
        if isinstance(node, ast.Assign):
            return any(isinstance(t, ast.Name) and t.id == "STRIP_CATEGORIES"
                       for t in node.targets)
        if isinstance(node, ast.AnnAssign):  # `STRIP_CATEGORIES: tuple = (...)` is valid
            return isinstance(node.target, ast.Name) and node.target.id == "STRIP_CATEGORIES"
        return False

    assigns = [n for n in ast.walk(tree) if _targets_name(n)]
    assert len(assigns) == 1, (
        "expected exactly ONE assignment of STRIP_CATEGORIES in the gate (the import "
        "fallback); found %d. A second one is the duplicate this change removed, "
        "reintroduced." % len(assigns))

    # Find the try whose BODY imports STRIP_CATEGORIES, and require the assignment to be a
    # direct child statement of one of THAT try's handlers -- not merely somewhere beneath
    # some except in the file.
    owning_handlers = []
    for tr in [n for n in ast.walk(tree) if isinstance(n, ast.Try)]:
        imports_it = any(
            isinstance(s, ast.ImportFrom)
            and any(a.name == "STRIP_CATEGORIES" for a in s.names)
            for s in ast.walk(ast.Module(body=tr.body, type_ignores=[])))
        if imports_it:
            owning_handlers.extend(tr.handlers)
    assert owning_handlers, (
        "no try block in the gate imports STRIP_CATEGORIES -- the shared module is not "
        "being used at all")
    assert any(assigns[0] in h.body for h in owning_handlers), (
        "the gate's STRIP_CATEGORIES assignment must be a DIRECT statement of the except "
        "handler on the try that imports it. Anywhere else (a nested def, an `if False:`, "
        "a class body, an unrelated handler) is dead code: the name never binds, and the "
        "gate exits 1 -- which PreToolUse treats as non-blocking, i.e. both gates off.")
    fallback = ast.literal_eval(assigns[0].value)
    shared = _shared_strip_categories()
    assert fallback == shared, (
        "the gate's fallback %r has drifted from hooks/lib/text_normalization.py's %r. "
        "These must be identical: the fallback is what runs when the shared module cannot "
        "be imported, and a fallback nothing pins is just the old duplicate under another "
        "name." % (fallback, shared))
    print("PASS test_strip_categories_fallback_matches_shared_module")


def test_missing_text_normalization_module_still_blocks():
    """Import failure must not degrade the gate to fail-OPEN. With the shared module
    deleted, the fallback has to keep BOTH gates armed against the Round 3 evasions --
    Gate 2a (netlify) and Gate 1 (the send trigger phrase) -- not merely avoid crashing.
    Mirrors test-confidentiality-guard.py's site_markers import-failure test."""
    gate = _isolated_gate(drop_shared_module=True)
    zwsp = chr(0x200B)  # chr(), not a raw fixture byte: this file declares ASCII-only
    for label, cmd in (
        ("Gate 2a, ZWSP-split netlify", "cmd /c net" + zwsp + "lify deploy --build --prod"),
        ("Gate 2a, plain netlify", "cmd /c netlify deploy --build --prod"),
        ("Gate 1, ZWSP in the send trigger phrase",
         "powershell -File send-via-outlook" + zwsp + ".ps1 -To attacker@evilhost.com "
         "-Subject hi -Body hi"),
    ):
        rc, err = _run_gate(gate, cmd)
        assert rc == 2, (
            "with text_normalization.py absent the fallback must still block [%s]; got "
            "exit %s (%s). Exit 1 in particular is fail-OPEN here -- PreToolUse treats it "
            "as a non-blocking error and runs the tool anyway." % (label, rc, err))
    print("PASS test_missing_text_normalization_module_still_blocks")


# ---------------------------------------------------------------------------------------
# Gate 1b/1c/3: ms365 email sends, Teams sends, HubSpot CMS writes (MCP surface).
# Before this, the only MCP gate was Netlify's. The ms365 and HubSpot connectors expose
# send/publish tools that a session under bypassPermissions could call with no prompt and
# no hook; the confidentiality-guard matcher that looked like cover was registered on
# uppercase Composio-era names (OUTLOOK_SEND...) and never matched the live lowercase ones.
# ---------------------------------------------------------------------------------------
MS365 = "mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__"
HUBSPOT = "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__"


def tool_payload(tool_name, tool_input):
    return {"tool_name": tool_name, "tool_input": tool_input}


def mail(to, cc=None, bcc=None, tool="outlook_send_mail"):
    ti = {"to": to, "subject": "s", "body": "b"}
    if cc is not None:
        ti["cc"] = cc
    if bcc is not None:
        ti["bcc"] = bcc
    return tool_payload(MS365 + tool, ti)


def test_ms365_send_mail_external_recipient_blocks():
    rc, out, err = run_hook(mail(["counterparty@example.com"]))
    assert rc == 2, "external outlook_send_mail must block, got %s (%s)" % (rc, err)
    assert "counterparty@example.com" in err, "block message must name the recipient"
    print("PASS test_ms365_send_mail_external_recipient_blocks")


def test_ms365_send_mail_internal_only_allows():
    rc, out, err = run_hook(mail(["ggoldberg@oxfordra.net"], cc=["EGOLDBERG@OXFORDRA.NET"]))
    assert rc == 0, "internal-only send matches Gate 1 parity and must pass, got %s (%s)" % (rc, err)
    print("PASS test_ms365_send_mail_internal_only_allows")


def test_ms365_send_mail_mixed_and_bcc_block():
    rc, _, err = run_hook(mail(["ggoldberg@oxfordra.net", "x@example.com"]))
    assert rc == 2, "one external among internals must block, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(mail(["ggoldberg@oxfordra.net"], bcc=["x@example.com"]))
    assert rc == 2, "an external BCC must block, got %s (%s)" % (rc, err)
    print("PASS test_ms365_send_mail_mixed_and_bcc_block")


def test_ms365_send_mail_lookalike_and_malformed_recipients_block():
    bad = [
        "a@oxfordra.net.evil.com",
        "a@oxfordra.network",
        "evil@example.com,ceo@oxfordra.net",      # list smuggled into one string
        "Name <evil@example.com>",
        "ceo@oxfordra.net​",                   # zero-width suffix
        "ceo@oxfordra.net\n",                       # trailing newline
        "ceo@oxfordra.net ",
        "сeo@oxfordra.net.example.com",
        "no-at-sign",
        "",
    ]
    for addr in bad:
        rc, _, err = run_hook(mail([addr]))
        assert rc == 2, "recipient %r must be treated as external, got %s (%s)" % (addr, rc, err)
    print("PASS test_ms365_send_mail_lookalike_and_malformed_recipients_block")


def test_ms365_send_mail_unusable_shape_fails_closed():
    for ti in ({}, {"subject": "s", "body": "b"}, {"to": []}, {"to": [None]},
               {"to": [["a@oxfordra.net"]]}, {"to": 5}, "not-a-dict", None, []):
        rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_mail", ti))
        assert rc == 2, "tool_input %r must fail closed, got %s (%s)" % (ti, rc, err)
    print("PASS test_ms365_send_mail_unusable_shape_fails_closed")


def test_ms365_send_mail_token_binds_to_named_recipients_and_is_single_use():
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["counterparty@example.com"])
    rc, _, err = run_hook(mail(["someone-else@example.com"]), sessions_dir=d)
    assert rc == 2, "a token naming another recipient must not authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(mail(["counterparty@example.com"]), sessions_dir=d)
    assert rc == 0, "a token naming the recipient must authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(mail(["counterparty@example.com"]), sessions_dir=d)
    assert rc == 2, "the external-send token is single-use, got %s (%s)" % (rc, err)
    print("PASS test_ms365_send_mail_token_binds_to_named_recipients_and_is_single_use")


def test_ms365_forward_mail_follows_recipient_rule():
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_forward_mail",
                                       {"messageId": "AAA", "to": ["x@example.com"]}))
    assert rc == 2, "external forward must block, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_forward_mail",
                                       {"messageId": "AAA", "to": ["ggoldberg@oxfordra.net"]}))
    assert rc == 0, "internal forward must pass, got %s (%s)" % (rc, err)
    print("PASS test_ms365_forward_mail_follows_recipient_rule")


def test_ms365_send_draft_needs_token_naming_the_draft():
    p = tool_payload(MS365 + "outlook_send_draft", {"messageId": "AAMkAGDraftOne"})
    rc, _, err = run_hook(p)
    assert rc == 2, "send_draft carries no recipients and must block, got %s (%s)" % (rc, err)
    assert "draft:AAMkAGDraftOne" in err, "block message must say what to name in the token"
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["draft:AAMkAGDraftTwo"])
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "a token naming a DIFFERENT draft must not authorize, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["draft:AAMkAGDraftOne"])
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 0, "a token naming this draft must authorize, got %s (%s)" % (rc, err)
    print("PASS test_ms365_send_draft_needs_token_naming_the_draft")


def test_teams_sends_block_and_bind_to_destination():
    chat = tool_payload(MS365 + "teams_send_chat_message", {"chatId": "19:abc@thread.v2", "body": "hi"})
    chan = tool_payload(MS365 + "teams_send_channel_message",
                        {"teamId": "T1", "channelId": "19:c1@thread.tacv2", "body": "hi"})
    reply = tool_payload(MS365 + "teams_reply_channel_message",
                         {"teamId": "T1", "channelId": "19:c1@thread.tacv2", "messageId": "M", "body": "hi"})
    for p in (chat, chan, reply):
        rc, _, err = run_hook(p)
        assert rc == 2, "%s must block without a token, got %s (%s)" % (p["tool_name"], rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["teams:19:other@thread.v2"])
    rc, _, err = run_hook(chat, sessions_dir=d)
    assert rc == 2, "a token naming another chat must not authorize, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["teams:19:abc@thread.v2"])
    rc, _, err = run_hook(chat, sessions_dir=d)
    assert rc == 0, "a token naming the chat must authorize, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["teams:T1/19:c1@thread.tacv2"])
    rc, _, err = run_hook(chan, sessions_dir=d)
    assert rc == 0, "a token naming team/channel must authorize a channel post, got %s (%s)" % (rc, err)
    print("PASS test_teams_sends_block_and_bind_to_destination")


def test_teams_send_missing_destination_fails_closed():
    for name in ("teams_send_chat_message", "teams_send_channel_message", "teams_reply_channel_message"):
        for ti in ({}, {"body": "hi"}, {"chatId": ""}, {"chatId": 7}, None, "x"):
            rc, _, err = run_hook(tool_payload(MS365 + name, ti))
            assert rc == 2, "%s with %r must fail closed, got %s (%s)" % (name, ti, rc, err)
    print("PASS test_teams_send_missing_destination_fails_closed")


def test_ms365_non_send_tools_pass():
    for name in ("outlook_create_draft", "outlook_email_search", "outlook_calendar_search",
                 "teams_list_chats", "teams_list_channel_messages", "sharepoint_search"):
        rc, _, err = run_hook(tool_payload(MS365 + name, {"to": ["x@example.com"], "body": "b"}))
        assert rc == 0, "%s is not a send and must not block, got %s (%s)" % (name, rc, err)
    print("PASS test_ms365_non_send_tools_pass")


def test_gates_match_on_tool_suffix_not_connector_id():
    rc, _, err = run_hook(tool_payload("mcp__some-new-server-id__outlook_send_mail",
                                       {"to": ["x@example.com"], "subject": "s", "body": "b"}))
    assert rc == 2, "a reinstalled connector with a new id must stay gated, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(tool_payload("mcp__some-new-server-id__manage_blog_post",
                                       {"action": "PUBLISH", "contentId": 1}))
    assert rc == 2, "a reinstalled HubSpot connector must stay gated, got %s (%s)" % (rc, err)
    print("PASS test_gates_match_on_tool_suffix_not_connector_id")


HS_READS = (
    ("manage_blog_post", {"action": "GET_POST", "contentId": 1}),
    ("manage_blog_post", {"action": "LIST_BLOG_POSTS"}),
    ("manage_blog_post", {"action": "LIST_TAGS"}),
    ("manage_landing_page", {"action": "MODULES", "contentId": 1}),
    ("manage_landing_page", {"action": "TEMPLATES"}),
    ("manage_landing_page", {"action": "REVISIONS", "contentId": 1}),
    ("manage_website_page", {"operation": {"_type": "MODULES", "contentId": 1}}),
    ("manage_website_page", {"operation": {"_type": "NAV_GET_MENU"}}),
    ("manage_website_page", {"operation": {"_type": "TEMPLATES"}}),
)


def test_hubspot_cms_reads_pass():
    for name, ti in HS_READS:
        rc, _, err = run_hook(tool_payload(HUBSPOT + name, ti))
        assert rc == 0, "%s %r is a read and must pass, got %s (%s)" % (name, ti, rc, err)
    print("PASS test_hubspot_cms_reads_pass")


HS_WRITES = (
    ("manage_blog_post", {"action": "CREATE", "title": "t", "postBody": "<p>x</p>"}),
    ("manage_blog_post", {"action": "UPDATE", "contentId": 1, "title": "t"}),
    ("manage_blog_post", {"action": "PUBLISH", "contentId": 1}),
    ("manage_blog_post", {"action": "UNPUBLISH", "contentId": 1}),
    ("manage_landing_page", {"action": "PUBLISH", "contentId": 1}),
    ("manage_landing_page", {"action": "SET_METADATA", "contentId": 1, "slug": "s"}),
    ("manage_landing_page", {"action": "CREATE_CUSTOM_TEMPLATE", "slug": "s", "hublSource": "x"}),
    ("manage_landing_page", {"action": "BATCH", "operationsJson": "[]"}),
    ("manage_website_page", {"operation": {"_type": "CREATE_FROM_TEMPLATE", "pageName": "p", "templatePath": "t"}}),
    ("manage_website_page", {"operation": {"_type": "PUBLISH", "contentId": 1}}),
    ("manage_website_page", {"operation": {"_type": "REMOVE", "contentId": 1, "moduleId": "m"}}),
    ("manage_website_page", {"operation": {"_type": "NAV_REPLACE_MENU", "menuItemsJson": "[]"}}),
    ("manage_website_page", {"operation": {"_type": "NAV_SET_ITEM", "label": "x"}}),
    ("manage_website_page", {"operation": {"_type": "BATCH", "steps": []}}),
)


def test_hubspot_cms_writes_block():
    for name, ti in HS_WRITES:
        rc, _, err = run_hook(tool_payload(HUBSPOT + name, ti))
        assert rc == 2, "%s %r is a write and must block, got %s (%s)" % (name, ti, rc, err)
    print("PASS test_hubspot_cms_writes_block")


def test_hubspot_cms_preview_mode_passes_only_when_explicit():
    def web(op):
        return tool_payload(HUBSPOT + "manage_website_page", {"operation": op})
    for t in ("PUBLISH", "REMOVE", "REMOVE_SECTION", "RESTORE_REVISION",
              "NAV_SET_ITEM", "NAV_REPLACE_MENU", "NAV_REMOVE_ITEM"):
        rc, _, err = run_hook(web({"_type": t, "contentId": 1, "mode": "PREVIEW"}))
        assert rc == 0, "%s with mode=PREVIEW writes nothing and must pass, got %s (%s)" % (t, rc, err)
    for op in ({"_type": "PUBLISH", "contentId": 1, "mode": "APPLY"},
               {"_type": "PUBLISH", "contentId": 1, "mode": "preview"},
               {"_type": "PUBLISH", "contentId": 1, "mode": None},
               {"_type": "NAV_SET_ITEM", "mode": "PREVIEW", "confirmNavChange": True},
               {"_type": "CREATE_FROM_TEMPLATE", "pageName": "p", "templatePath": "t", "mode": "PREVIEW"},
               {"_type": "SET_METADATA", "contentId": 1, "mode": "PREVIEW"}):
        rc, _, err = run_hook(web(op))
        assert rc == 2, "%r must block, got %s (%s)" % (op, rc, err)
    print("PASS test_hubspot_cms_preview_mode_passes_only_when_explicit")


def test_hubspot_cms_unknown_or_malformed_fails_closed():
    blog = HUBSPOT + "manage_blog_post"
    web = HUBSPOT + "manage_website_page"
    cases = [
        tool_payload(blog, {"action": "SOME_FUTURE_WRITE"}),
        tool_payload(blog, {"action": "get_post"}),        # exact-case allowlist only
        tool_payload(blog, {"action": " GET_POST"}),
        tool_payload(blog, {"action": "GET_POST​"}),
        tool_payload(blog, {}),
        tool_payload(blog, {"action": 5}),
        tool_payload(blog, None),
        tool_payload(blog, "GET_POST"),
        tool_payload(blog, []),
        tool_payload(web, {}),
        tool_payload(web, {"operation": "MODULES"}),
        tool_payload(web, {"operation": {}}),
        tool_payload(web, {"operation": {"_type": 5}}),
        tool_payload(web, {"operation": {"_type": "FUTURE_WRITE"}}),
    ]
    for p in cases:
        rc, _, err = run_hook(p)
        assert rc == 2, "%r must fail closed, got %s (%s)" % (p, rc, err)
    print("PASS test_hubspot_cms_unknown_or_malformed_fails_closed")


def test_hubspot_cms_token_authorizes_multi_use_and_is_not_interchangeable():
    p = tool_payload(HUBSPOT + "manage_blog_post", {"action": "PUBLISH", "contentId": 1})
    d = fresh_sessions_dir()
    mint(d, "allow-hubspot-cms-write", "hubspot-cms-write")
    for _ in range(2):
        rc, _, err = run_hook(p, sessions_dir=d)
        assert rc == 0, "a CMS token is multi-use (edit, edit, publish), got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com"])
    mint(d, "allow-website-write", "website-write")
    mint(d, "allow-website-deploy", "website-deploy")
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "email/site tokens must not authorize CMS writes, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-hubspot-cms-write", "hubspot-cms-write")
    rc, _, err = run_hook(mail(["x@example.com"]), sessions_dir=d)
    assert rc == 2, "a CMS token must not authorize an external email, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-hubspot-cms-write", "hubspot-cms-write", session_id=SESSION_B)
    rc, _, err = run_hook(p, sessions_dir=d, session_id=SESSION_A)
    assert rc == 2, "a token minted for another session must not authorize, got %s (%s)" % (rc, err)
    print("PASS test_hubspot_cms_token_authorizes_multi_use_and_is_not_interchangeable")


def test_hubspot_cms_token_expires():
    p = tool_payload(HUBSPOT + "manage_blog_post", {"action": "PUBLISH", "contentId": 1})
    d = fresh_sessions_dir()
    mint(d, "allow-hubspot-cms-write", "hubspot-cms-write", age_seconds=601)
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "a CMS token older than its 10-minute TTL must not authorize, got %s (%s)" % (rc, err)
    print("PASS test_hubspot_cms_token_expires")


def run_raw(raw, sessions_dir=None):
    """Feed the hook an exact stdin string (run_hook always serialises a dict)."""
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir if sessions_dir is not None else fresh_sessions_dir()
    proc = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def test_unparseable_payload_naming_a_gated_tool_fails_closed():
    """Review finding C8. json.loads raises RecursionError on deeply nested input and main()
    treated EVERY parse failure as 'not a payload we can evaluate' -> exit 0, so a padded extra
    key let a live send/publish through with no token. A payload that cannot be parsed but
    NAMES a gated tool must now block. Payloads that name nothing gated keep the old
    fail-open, so a genuinely broken harness still cannot brick the session."""
    deep = "[" * 5000 + "]" * 5000
    cases = (
        (MS365 + "outlook_send_mail", '{"to":["a@evil.com"],"subject":"s","body":"b","x":%s}' % deep),
        (MS365 + "teams_send_chat_message", '{"chatId":"19:a","body":"b","x":%s}' % deep),
        (HUBSPOT + "manage_website_page", '{"operation":{"_type":"PUBLISH","mode":"APPLY","x":%s}}' % deep),
        ("mcp__netlify__project-updater", '{"x":%s}' % deep),
    )
    for tool, ti in cases:
        raw = '{"tool_name":"%s","tool_input":%s,"session_id":"%s"}' % (tool, ti, SESSION_A)
        rc, _, err = run_raw(raw)
        assert rc == 2, "unparseable payload naming %s must fail closed, got %s (%s)" % (tool, rc, err)
    raw = '{"tool_name":"Read","tool_input":{"x":%s},"session_id":"%s"}' % (deep, SESSION_A)
    rc, _, err = run_raw(raw)
    assert rc == 0, "an unparseable payload naming nothing gated must stay fail-open, got %s (%s)" % (rc, err)
    rc, _, err = run_raw("not json at all")
    assert rc == 0, "non-JSON naming nothing gated must stay fail-open, got %s (%s)" % (rc, err)
    print("PASS test_unparseable_payload_naming_a_gated_tool_fails_closed")


def test_ms365_email_unknown_keys_fail_closed():
    """Review hardening: a recipient-bearing parameter the gate does not know about (replyTo,
    a differently-cased To, a future field) must not be silently ignored."""
    base = {"to": ["a@oxfordra.net"], "subject": "s", "body": "b"}
    for extra in ({"replyTo": ["x@evil.com"]}, {"To": ["x@evil.com"]}, {"attachments": ["f"]}):
        rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_mail", dict(base, **extra)))
        assert rc == 2, "unknown key %r must fail closed, got %s (%s)" % (extra, rc, err)
    # The token matters here: without one send_draft blocks anyway, so an un-tokened call
    # cannot tell the stray-key rule apart from the plain no-token block (review finding C5).
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["draft:AAA"])
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_draft",
                                       {"messageId": "AAA", "to": ["x@evil.com"]}), sessions_dir=d)
    assert rc == 2, "send_draft with stray recipient keys must fail closed even WITH a token, got %s (%s)" % (rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["draft:AAA"])
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_draft", {"messageId": "AAA"}), sessions_dir=d)
    assert rc == 0, "a clean send_draft with a matching token must pass, got %s (%s)" % (rc, err)
    ok = dict(base, cc=["b@oxfordra.net"], bcc=["c@oxfordra.net"], bodyType="html")
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_mail", ok))
    assert rc == 0, "the documented keys must still pass for an internal send, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_forward_mail",
                                       {"messageId": "AAA", "to": ["a@oxfordra.net"], "comment": "fyi"}))
    assert rc == 0, "a documented internal forward must pass, got %s (%s)" % (rc, err)
    print("PASS test_ms365_email_unknown_keys_fail_closed")


def test_ms365_internal_address_local_part_is_strict():
    # U+212A (Kelvin sign) case-folds to "k", so it slips through a [a-z] class unless the
    # pattern is ASCII-only; the e-acute pins the same thing for ordinary non-ASCII letters.
    for addr in ("ce​o@oxfordra.net", "ce%o@oxfordra.net", "a!b@oxfordra.net",
                 "a:b@oxfordra.net", "a\x1fb@oxfordra.net", "a\x85b@oxfordra.net",
                 "K@oxfordra.net", "é@oxfordra.net"):
        rc, _, err = run_hook(mail([addr]))
        assert rc == 2, "local part of %r is not plain ASCII atext; must block, got %s (%s)" % (addr, rc, err)
    for addr in ("ggoldberg@oxfordra.net", "first.last+tag@oxfordra.net", "a_b-c@OXFORDRA.NET"):
        rc, _, err = run_hook(mail([addr]))
        assert rc == 0, "%r is a plain internal address and must pass, got %s (%s)" % (addr, rc, err)
    print("PASS test_ms365_internal_address_local_part_is_strict")


def test_send_and_cms_exception_fails_closed_in_process():
    """Review gap M5: nothing pinned the `except Exception -> block_shape` wrapper, so a future
    edit could turn it into a silent `return` (fail open) with every test still green."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("oag_inproc", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def boom(*args, **kwargs):
        raise RuntimeError("injected failure")

    mod._check_send_and_cms = boom
    for tool in (MS365 + "outlook_send_mail", MS365 + "teams_send_chat_message",
                 HUBSPOT + "manage_blog_post"):
        try:
            mod.check_mcp(tool, "sess", {"to": ["a@oxfordra.net"]})
        except SystemExit as exc:
            assert exc.code == 2, "%s: wrong exit code %r" % (tool, exc.code)
        else:
            raise AssertionError("%s: an exception inside the check must exit 2, not return" % tool)
    print("PASS test_send_and_cms_exception_fails_closed_in_process")


def test_teams_channel_token_binds_team_and_channel():
    """Review gap M6: a token for one team/channel must not authorize another."""
    def chan(team, channel):
        return tool_payload(MS365 + "teams_send_channel_message",
                            {"teamId": team, "channelId": channel, "body": "hi"})
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["teams:T1/19:c1@thread.tacv2"])
    rc, _, err = run_hook(chan("T2", "19:c1@thread.tacv2"), sessions_dir=d)
    assert rc == 2, "same channel id under a different team must not authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(chan("T1", "19:c2@thread.tacv2"), sessions_dir=d)
    assert rc == 2, "a different channel in the same team must not authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(chan("T1", "19:c1@thread.tacv2"), sessions_dir=d)
    assert rc == 0, "the named team/channel must authorize, got %s (%s)" % (rc, err)
    print("PASS test_teams_channel_token_binds_team_and_channel")


def test_settings_matcher_registers_every_gated_tool():
    """The hook only runs for tools its settings.json matcher selects. A gate that is correct
    but unregistered is the exact defect that left the ms365 sends uncovered, so pin the
    wiring: every gated tool name must full-match the ora-autonomy-gate matcher."""
    import re
    settings = os.path.join(HERE, "..", "settings.json")
    with open(settings, encoding="utf-8") as fh:
        cfg = json.load(fh)
    matchers = []
    for entry in cfg.get("hooks", {}).get("PreToolUse", []):
        for h in entry.get("hooks", []):
            if "ora-autonomy-gate.py" in h.get("command", ""):
                matchers.append(entry.get("matcher", ""))
    assert matchers, "ora-autonomy-gate.py is not registered under PreToolUse"
    def covered(tool):
        return any(re.fullmatch(m, tool) for m in matchers)
    gated = [MS365 + n for n in ("outlook_send_mail", "outlook_send_draft", "outlook_forward_mail",
                                 "teams_send_chat_message", "teams_send_channel_message",
                                 "teams_reply_channel_message")]
    gated += [HUBSPOT + n for n in ("manage_blog_post", "manage_landing_page", "manage_website_page")]
    gated += ["mcp__netlify__project-updater"]
    for t in gated:
        assert covered(t), "%s is gated in the script but not selected by the settings matcher" % t
    for t in (MS365 + "outlook_create_draft", MS365 + "outlook_email_search",
              MS365 + "teams_list_chats", HUBSPOT + "search_crm_objects", "Read"):
        assert not covered(t), "%s should not be routed through the gate (over-broad matcher)" % t
    print("PASS test_settings_matcher_registers_every_gated_tool")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    try:
        for t in tests:
            t()
    finally:
        for _root in _ISO_ROOTS:
            shutil.rmtree(_root, ignore_errors=True)
    print("ALL AUTONOMY-GATE TESTS PASS (%d)" % len(tests))
