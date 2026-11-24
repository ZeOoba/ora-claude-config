"""Tests for ora-autonomy-gate.py -- Gates 1e update_draft / 1f teams_create_chat (part 3 of 5).

Run: python test-ora-autonomy-gate-drafts-chats.py
Stdlib only. ASCII-only. Shared helpers: hooks/tests/_autonomy_gate_testlib.py.

Covers: outlook_update_draft re-pointing a draft at outside recipients (1e) and
teams_create_chat adding outside members (1f): the two MCP calls that set up an external
conversation without themselves being a send.

Split out of the former single test-ora-autonomy-gate.py on 2026-11-23 (per-file time
budget); tests moved verbatim.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _autonomy_gate_testlib import *  # noqa: E402,F401,F403 -- shared helpers; see its __all__


# ---------------------------------------------------------------------------------------
# Gate 1e: outlook_update_draft. A send_draft token names the draft id, not its contents, so
# an ungated update re-pointed an approved draft at a new recipient (adversarial review of
# #292). Schema VERIFIED 2026-10-01 against the live connector: additionalProperties false,
# keys messageId (required) / to / cc / bcc (arrays of email strings) / subject / body /
# bodyType. outlook_create_draft stays ungated: drafting for Gabriel to send is the normal flow.
# ---------------------------------------------------------------------------------------


def test_draft_repoint_sequence_is_closed():
    """The exact sequence from the #292 review: update re-points the draft, then the token that
    named only the draft id sends it. The update must now block, so the send is never reached
    with a changed recipient."""
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["draft:AAMk"])
    rc, _, err = run_hook(upd(messageId="AAMk", to=["a@evil.com"]), sessions_dir=d)
    assert rc == 2, "re-pointing an approved draft at an outside recipient must block, got %s (%s)" % (rc, err)
    assert "a@evil.com" in err, "block message must name the recipient to put in the token"
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_send_draft", {"messageId": "AAMk"}), sessions_dir=d)
    assert rc == 0, "the blocked update must not have spent the draft token, got %s (%s)" % (rc, err)
    print("PASS test_draft_repoint_sequence_is_closed")


def test_draft_update_without_external_recipient_passes():
    for ti in ({}, {"subject": "s"}, {"body": "b", "bodyType": "html"}, {"to": []},
               {"to": ["ggoldberg@oxfordra.net"], "cc": ["EGoldberg@OxfordRA.net"], "bcc": []},
               {"to": [], "cc": [], "bcc": []}):
        rc, _, err = run_hook(upd(**ti))
        assert rc == 0, "internal-only / recipient-free update %r must pass, got %s (%s)" % (ti, rc, err)
    print("PASS test_draft_update_without_external_recipient_passes")


def test_draft_update_external_in_any_recipient_field_blocks():
    for field in ("to", "cc", "bcc"):
        rc, _, err = run_hook(upd(**{field: ["x@example.com"]}))
        assert rc == 2, "external address in %s must block, got %s (%s)" % (field, rc, err)
    rc, _, err = run_hook(upd(to=["ggoldberg@oxfordra.net"], bcc=["x@example.com"]))
    assert rc == 2, "one external among internal must block, got %s (%s)" % (rc, err)
    print("PASS test_draft_update_external_in_any_recipient_field_blocks")


def test_draft_update_lookalike_addresses_count_as_external():
    for bad in ("a@oxfordra.net.evil.com", "Name <x@evil.com>", " ggoldberg@oxfordra.net",
                "ggoldberg@oxfordra.net ", "ggoldberg@oxfordra.net\n", "a@oxfordra.net@evil.com",
                "evil@x.com,ggoldberg@oxfordra.net", "ggoldberg@oxfordra.nеt",
                "ggoldberg@oxfordra​.net", "ggoldberg＠oxfordra.net", "ggoldberg"):
        rc, _, err = run_hook(upd(to=[bad]))
        assert rc == 2, "%r is not provably internal and must block, got %s (%s)" % (bad, rc, err)
    print("PASS test_draft_update_lookalike_addresses_count_as_external")


def test_draft_update_token_names_recipients_and_is_single_use():
    p = upd(to=["x@example.com"], cc=["y@example.org"])
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com", "y@example.org"])
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 0, "a token naming every external recipient must authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "the token is single-use, got %s (%s)" % (rc, err)
    for named in (["x@example.com"], ["y@example.org"],
                  ["z@example.net"], ["draft:AAMkAGDraftOne"]):
        d = fresh_sessions_dir()
        mint(d, "allow-external-send", "external-send", recipients=named)
        rc, _, err = run_hook(p, sessions_dir=d)
        assert rc == 2, "token naming %r must not authorize, got %s (%s)" % (named, rc, err)
    d = fresh_sessions_dir()
    mint(d, "allow-website-write", "website-write")
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "a token of another scope must not authorize, got %s (%s)" % (rc, err)
    print("PASS test_draft_update_token_names_recipients_and_is_single_use")


def test_draft_update_internal_recipients_are_not_named_in_token():
    p = upd(to=["ggoldberg@oxfordra.net", "x@example.com"])
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com"])
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 0, "internal recipients need no naming, got %s (%s)" % (rc, err)
    print("PASS test_draft_update_internal_recipients_are_not_named_in_token")


def test_draft_update_malformed_shapes_fail_closed():
    bad_inputs = (
        {"to": "ggoldberg@oxfordra.net"},                 # schema says array; a bare string is not
        {"to": None}, {"cc": None}, {"bcc": 5}, {"to": {"a": "b"}},
        {"to": {"ggoldberg@oxfordra.net": 1}},            # iterating a dict yields an internal-looking key
        {"to": ["ggoldberg@oxfordra.net", 7]}, {"to": [None]},
        {"to": [{"email": "ggoldberg@oxfordra.net"}]},    # object entries are not in the schema
        {"to": [["ggoldberg@oxfordra.net"]]},
        {"replyTo": ["x@evil.com"]}, {"To": ["x@evil.com"]}, {"toRecipients": ["x@evil.com"]},
        {"attachments": []}, {"importance": "high"},
        {"messageId": ""}, {"messageId": "   "}, {"messageId": 5}, {"messageId": None},
        {"messageId": ["AAA"]},
    )
    for ti in bad_inputs:
        payload = tool_payload(MS365 + "outlook_update_draft", dict({"messageId": "AAMkAGDraftOne"}, **ti))
        rc, _, err = run_hook(payload)
        assert rc == 2, "%r must fail closed, got %s (%s)" % (ti, rc, err)
        # The SHAPE refusal, not a token-style block: a bare string would otherwise be over-blocked
        # as a pile of external "characters" while still passing for the wrong reason.
        assert "uninspectable input shape" in err, "%r must be refused as a bad shape, got: %s" % (ti, err)
    rc, _, err = run_hook(tool_payload(MS365 + "outlook_update_draft", {"to": ["ggoldberg@oxfordra.net"]}))
    assert rc == 2, "missing messageId must fail closed, got %s (%s)" % (rc, err)
    for ti in (None, "x", [], 7, {}):
        rc, _, err = run_hook(tool_payload(MS365 + "outlook_update_draft", ti))
        assert rc == 2, "tool_input %r must fail closed, got %s (%s)" % (ti, rc, err)
        assert "uninspectable input shape" in err, "%r must be refused as a bad shape, got: %s" % (ti, err)
    print("PASS test_draft_update_malformed_shapes_fail_closed")


def test_draft_update_malformed_shape_fails_closed_even_with_a_token():
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com"])
    rc, _, err = run_hook(upd(to=["x@example.com"], replyTo=["z@evil.com"]), sessions_dir=d)
    assert rc == 2, "a stray recipient-bearing key must block even with a token, got %s (%s)" % (rc, err)
    print("PASS test_draft_update_malformed_shape_fails_closed_even_with_a_token")


def test_create_draft_stays_ungated():
    for ti in ({"to": ["x@example.com"], "subject": "s", "body": "b", "bodyType": "text"},
               {"to": ["x@example.com"], "bcc": ["y@example.com"]}, {}):
        rc, _, err = run_hook(tool_payload(MS365 + "outlook_create_draft", ti))
        assert rc == 0, "create_draft is the normal Outlook-pane flow and must pass, got %s (%s)" % (rc, err)
    print("PASS test_create_draft_stays_ungated")


def test_draft_update_gate_matches_by_suffix_on_any_server_prefix():
    for prefix in ("mcp__ms365__", "mcp__other-ms365__", "mcp__claude_ai_Microsoft_365__"):
        rc, _, err = run_hook(tool_payload(prefix + "outlook_update_draft",
                                           {"messageId": "AAA", "to": ["x@example.com"]}))
        assert rc == 2, "%s must be gated by suffix, got %s (%s)" % (prefix, rc, err)
    print("PASS test_draft_update_gate_matches_by_suffix_on_any_server_prefix")


def test_unparseable_payload_naming_update_draft_fails_closed():
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-sess-")
    raw = '{"tool_name": "%soutlook_update_draft", "tool_input": %s1%s}' % (MS365, "[" * 100000, "]" * 100000)
    proc = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=env)
    assert proc.returncode == 2, "unparseable payload naming update_draft must fail closed, got %s" % proc.returncode
    print("PASS test_unparseable_payload_naming_update_draft_fails_closed")


def test_draft_update_check_exception_fails_closed_in_process():
    import importlib.util
    spec = importlib.util.spec_from_file_location("oag_inproc3", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def boom(*args, **kwargs):
        raise RuntimeError("injected failure")

    mod._check_draft_update = boom
    try:
        mod.check_mcp(MS365 + "outlook_update_draft", "sess", {"messageId": "A", "to": ["a@oxfordra.net"]})
    except SystemExit as exc:
        assert exc.code == 2, "wrong exit code %r" % (exc.code,)
    else:
        raise AssertionError("an exception inside the draft-update check must exit 2, not return")
    print("PASS test_draft_update_check_exception_fails_closed_in_process")


def test_settings_matcher_registers_update_draft():
    import re
    with open(os.path.join(HERE, "..", "settings.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    matchers = [e.get("matcher", "") for e in cfg.get("hooks", {}).get("PreToolUse", [])
                for h in e.get("hooks", []) if "ora-autonomy-gate.py" in h.get("command", "")]
    assert matchers, "ora-autonomy-gate.py is not registered under PreToolUse"
    covered = lambda t: any(re.fullmatch(m, t) for m in matchers)  # noqa: E731
    for prefix in (MS365, "mcp__ms365__"):
        assert covered(prefix + "outlook_update_draft"), "update_draft is gated but not selected by the matcher"
        assert not covered(prefix + "outlook_create_draft"), "create_draft must stay out of the gate"
    print("PASS test_settings_matcher_registers_update_draft")


# ---------------------------------------------------------------------------------------
# Gate 1f: teams_create_chat. Live schema read 2026-10-01 (additionalProperties:false):
# members (array 1-50 of AAD object ids or UPNs, required), chatType oneOnOne|group, topic
# (group only). Creating a chat sends no message, but a teams_send_*_message token names only
# `teams:<chatId>`, never who is IN the chat -- the same id-not-contents hole the draft re-point
# had. So a chat created with an outside member could later be approved for a send by id.
# Membership is therefore gated at creation, with the Gate 1b rule: every member must be one
# plain @oxfordra.net UPN; a GUID cannot be proven internal, so it needs a token like any outsider.
# ---------------------------------------------------------------------------------------


def test_teams_create_chat_internal_upns_pass():
    for ti in ({"members": ["egoldberg@oxfordra.net"]},
               {"members": ["egoldberg@oxfordra.net"], "chatType": "oneOnOne"},
               {"members": ["EGoldberg@OxfordRA.net", "ggoldberg@oxfordra.net"], "chatType": "group",
                "topic": "Closing checklist"}):
        rc, _, err = run_hook(chat(**ti))
        assert rc == 0, "an all-internal chat %r must pass, got %s (%s)" % (ti, rc, err)
    print("PASS test_teams_create_chat_internal_upns_pass")


def test_teams_create_chat_outside_or_unprovable_member_blocks():
    guid = "0f1e2d3c-4b5a-6978-8695-a4b3c2d1e0f9"
    for members in (["x@example.com"], ["egoldberg@oxfordra.net", "x@example.com"], [guid],
                    ["a@oxfordra.net.evil.com"], ["Name <x@oxfordra.net>"], [" egoldberg@oxfordra.net"],
                    ["egoldberg@oxfordra.net\n"], ["a@oxfordra.net@evil.com"],
                    ["egoldberg@oxfordra.net,x@example.com"], ["egoldberg@oxfordra.nеt"],
                    ["egoldberg＠oxfordra.net"], ["egoldberg"]):
        for chat_type in ("oneOnOne", "group"):
            rc, _, err = run_hook(chat(members=members, chatType=chat_type))
            assert rc == 2, "%r (%s) is not provably internal and must block, got %s (%s)" % (members, chat_type, rc, err)
            assert "uninspectable input shape" not in err, "%r is a valid shape, must be a token block" % (members,)
    print("PASS test_teams_create_chat_outside_or_unprovable_member_blocks")


def test_teams_create_chat_token_names_each_member_and_is_single_use():
    p = chat(members=["x@example.com", "egoldberg@oxfordra.net", "y@example.org"], chatType="group", topic="t")
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com", "y@example.org"])
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 0, "a token naming every non-internal member must authorize, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "the token is single-use, got %s (%s)" % (rc, err)
    for named in (["x@example.com"], ["y@example.org"], ["z@example.net"], ["teams:19:abc@thread.v2"]):
        d = fresh_sessions_dir()
        mint(d, "allow-external-send", "external-send", recipients=named)
        rc, _, err = run_hook(p, sessions_dir=d)
        assert rc == 2, "token naming %r must not authorize, got %s (%s)" % (named, rc, err)
    print("PASS test_teams_create_chat_token_names_each_member_and_is_single_use")


def test_teams_create_chat_malformed_shapes_fail_closed():
    ok = ["egoldberg@oxfordra.net"]
    bad = ({"members": "egoldberg@oxfordra.net"}, {"members": []}, {"members": None},
           {"members": {"egoldberg@oxfordra.net": 1}}, {"members": ok + [7]}, {"members": ok + [None]},
           {"members": [{"id": "egoldberg@oxfordra.net"}]}, {"members": [ok]},
           {"members": ok, "chatType": 5}, {"members": ok, "chatType": None}, {"members": ok, "topic": 5},
           {"members": ok, "message": "hello"}, {"members": ok, "firstMessage": "hello"},
           {"members": ok, "users": ["x@evil.com"]}, {"Members": ["x@evil.com"]}, {"topic": "t"}, {})
    for ti in bad:
        rc, _, err = run_hook(chat(**ti))
        assert rc == 2, "%r must fail closed, got %s (%s)" % (ti, rc, err)
        assert "uninspectable input shape" in err, "%r must be refused as a bad shape, got: %s" % (ti, err)
    for ti in (None, "x", [], 7):
        rc, _, err = run_hook(tool_payload(MS365 + "teams_create_chat", ti))
        assert rc == 2 and "uninspectable input shape" in err, "tool_input %r must fail closed, got %s (%s)" % (ti, rc, err)
    print("PASS test_teams_create_chat_malformed_shapes_fail_closed")


def test_teams_create_chat_stray_key_blocks_even_with_a_token():
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=["x@example.com"])
    rc, _, err = run_hook(chat(members=["x@example.com"], message="hi"), sessions_dir=d)
    assert rc == 2, "an unknown key must block even with a token, got %s (%s)" % (rc, err)
    print("PASS test_teams_create_chat_stray_key_blocks_even_with_a_token")


def test_teams_create_chat_gate_matches_by_suffix_on_any_server_prefix():
    for prefix in ("mcp__ms365__", "mcp__other-ms365__"):
        rc, _, err = run_hook(tool_payload(prefix + "teams_create_chat", {"members": ["x@example.com"]}))
        assert rc == 2, "%s must be gated by suffix, got %s (%s)" % (prefix, rc, err)
    print("PASS test_teams_create_chat_gate_matches_by_suffix_on_any_server_prefix")


def test_unparseable_payload_naming_teams_create_chat_fails_closed():
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="oag-sess-")
    raw = '{"tool_name": "%steams_create_chat", "tool_input": %s1%s}' % (MS365, "[" * 100000, "]" * 100000)
    proc = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=env)
    assert proc.returncode == 2, "unparseable payload naming teams_create_chat must fail closed, got %s" % proc.returncode
    print("PASS test_unparseable_payload_naming_teams_create_chat_fails_closed")


def test_teams_create_chat_check_exception_fails_closed_in_process():
    import importlib.util
    spec = importlib.util.spec_from_file_location("oag_inproc4", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def boom(*args, **kwargs):
        raise RuntimeError("injected failure")

    mod._check_teams_create_chat = boom
    try:
        mod.check_mcp(MS365 + "teams_create_chat", "sess", {"members": ["egoldberg@oxfordra.net"]})
    except SystemExit as exc:
        assert exc.code == 2, "wrong exit code %r" % (exc.code,)
    else:
        raise AssertionError("an exception inside the create-chat check must exit 2, not return")
    print("PASS test_teams_create_chat_check_exception_fails_closed_in_process")


def test_settings_matcher_registers_teams_create_chat():
    import re
    with open(os.path.join(HERE, "..", "settings.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    matchers = [e.get("matcher", "") for e in cfg.get("hooks", {}).get("PreToolUse", [])
                for h in e.get("hooks", []) if "ora-autonomy-gate.py" in h.get("command", "")]
    assert matchers, "ora-autonomy-gate.py is not registered under PreToolUse"
    covered = lambda t: any(re.fullmatch(m, t) for m in matchers)  # noqa: E731
    for prefix in (MS365, "mcp__ms365__"):
        assert covered(prefix + "teams_create_chat"), "teams_create_chat is gated but not selected by the matcher"
        for read in ("teams_list_chats", "teams_list_teams", "teams_list_channels", "teams_list_channel_messages"):
            assert not covered(prefix + read), "%s is a read and must not be routed through the gate" % read
    print("PASS test_settings_matcher_registers_teams_create_chat")


def test_teams_create_chat_guest_upn_and_guid_with_token():
    # An Entra guest UPN (#EXT#) is never one plain @oxfordra.net address, so it blocks.
    for guest in ("x_example.com#EXT#@oxfordra.net", "x%40example.com@oxfordra.net"):
        rc, _, err = run_hook(chat(members=[guest], chatType="oneOnOne"))
        assert rc == 2, "%r must block, got %s (%s)" % (guest, rc, err)
    # A GUID cannot be proven internal; it is authorized only by a token naming it as written.
    guid = "0f1e2d3c-4b5a-6978-8695-a4b3c2d1e0f9"
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=[guid])
    rc, _, err = run_hook(chat(members=[guid], chatType="oneOnOne"), sessions_dir=d)
    assert rc == 0, "a token naming the GUID as written must authorize, got %s (%s)" % (rc, err)
    print("PASS test_teams_create_chat_guest_upn_and_guid_with_token")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    try:
        for t in tests:
            t()
    finally:
        for _root in _ISO_ROOTS:
            shutil.rmtree(_root, ignore_errors=True)
    print("ALL AUTONOMY-GATE DRAFTS-CHATS TESTS PASS (%d)" % len(tests))
