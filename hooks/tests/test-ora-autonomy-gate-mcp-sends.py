"""Tests for ora-autonomy-gate.py -- MCP send gates 1b / 1c / 3 / 3b (part 2 of 5).

Run: python test-ora-autonomy-gate-mcp-sends.py
Stdlib only. ASCII-only. Shared helpers: hooks/tests/_autonomy_gate_testlib.py.

Covers: ms365 email sends and forwards (1b), Teams sends (1c), HubSpot CMS writes (3) and
social posts (3b), unparseable-payload fail-closed handling and the settings matcher
registration for these tools.

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
# Gate 1b/1c/3: ms365 email sends, Teams sends, HubSpot CMS writes (MCP surface).
# Before this, the only MCP gate was Netlify's. The ms365 and HubSpot connectors expose
# send/publish tools that a session under bypassPermissions could call with no prompt and
# no hook; the confidentiality-guard matcher that looked like cover was registered on
# uppercase Composio-era names (OUTLOOK_SEND...) and never matched the live lowercase ones.
# ---------------------------------------------------------------------------------------


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


def test_hubspot_cms_reads_pass():
    for name, ti in HS_READS:
        rc, _, err = run_hook(tool_payload(HUBSPOT + name, ti))
        assert rc == 0, "%s %r is a read and must pass, got %s (%s)" % (name, ti, rc, err)
    print("PASS test_hubspot_cms_reads_pass")


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


def test_hubspot_social_posts_previews_drafts_and_cancel_pass():
    for ti in SOCIAL_PASS:
        rc, _, err = run_hook(tool_payload(SOCIAL, ti))
        assert rc == 0, "%r writes nothing public and must pass, got %s (%s)" % (ti, rc, err)
    print("PASS test_hubspot_social_posts_previews_drafts_and_cancel_pass")


def test_hubspot_social_posts_publish_schedule_update_block():
    for ti in SOCIAL_BLOCK:
        rc, _, err = run_hook(tool_payload(SOCIAL, ti))
        assert rc == 2, "%r can make a post public and must block, got %s (%s)" % (ti, rc, err)
    print("PASS test_hubspot_social_posts_publish_schedule_update_block")


def test_hubspot_social_posts_malformed_fails_closed():
    for ti in SOCIAL_MALFORMED + (None, "CREATE", []):
        rc, _, err = run_hook(tool_payload(SOCIAL, ti))
        assert rc == 2, "%r must fail closed, got %s (%s)" % (ti, rc, err)
    print("PASS test_hubspot_social_posts_malformed_fails_closed")


def test_hubspot_social_posts_token_is_dedicated_and_single_use():
    """Review C8 (2026-11-08): a broadcast to an external network cannot be pulled back, and is one
    call, so it gets its OWN single-use tier -- a multi-use CMS editing token must not authorize it."""
    p = tool_payload(SOCIAL, SOCIAL_BLOCK[0])
    d = fresh_sessions_dir()
    mint(d, "allow-hubspot-social-publish", "hubspot-social-publish")
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 0, "a hubspot-social-publish token must authorize one publish, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(p, sessions_dir=d)
    assert rc == 2, "the social token is single-use; a second publish must block, got %s (%s)" % (rc, err)
    d2 = fresh_sessions_dir()
    mint(d2, "allow-hubspot-cms-write", "hubspot-cms-write")
    rc, _, err = run_hook(p, sessions_dir=d2)
    assert rc == 2, "a CMS write token must not authorize a social publish, got %s (%s)" % (rc, err)
    d3 = fresh_sessions_dir()
    mint(d3, "allow-external-send", "external-send", recipients=["c1"])
    rc, _, err = run_hook(p, sessions_dir=d3)
    assert rc == 2, "an external-send token must not authorize a social publish, got %s (%s)" % (rc, err)
    print("PASS test_hubspot_social_posts_token_is_dedicated_and_single_use")


def test_hubspot_social_posts_cancel_and_draft_pass_only_in_minimal_shape():
    """Review C3a: a CANCEL or DRAFT create carrying scheduling/edit fields is not provably inert."""
    for ti in ({"action": "CANCEL", "broadcastGuid": "g", "mode": "PUBLISH_NOW", "confirmed": True},
               {"action": "CANCEL", "broadcastGuid": "g", "publishAt": "2027-01-01T00:00:00Z",
                "confirmed": True},
               {"action": "CANCEL", "broadcastGuid": "g", "content": "x", "confirmed": True},
               {"action": "CREATE", "broadcastGuid": "g", "channelId": "c1", "content": "x",
                "mode": "DRAFT", "confirmed": True}):
        rc, _, err = run_hook(tool_payload(SOCIAL, ti))
        assert rc == 2, "%r must need a token, got %s (%s)" % (ti, rc, err)
    print("PASS test_hubspot_social_posts_cancel_and_draft_pass_only_in_minimal_shape")


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


def test_unparseable_payload_naming_a_gated_tool_fails_closed():
    """Review finding C8. json.loads raises RecursionError on deeply nested input and main()
    treated EVERY parse failure as 'not a payload we can evaluate' -> exit 0, so a padded extra
    key let a live send/publish through with no token. A payload that cannot be parsed but
    NAMES a gated tool must block (every unparseable payload now does; see
    test_unparseable_payload_fails_closed_for_every_tool)."""
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
    print("PASS test_unparseable_payload_naming_a_gated_tool_fails_closed")


def test_unparseable_payload_fails_closed_for_every_tool():
    """The gate is only ever invoked for a gated matcher, and in production Bash/Edit/Write
    already fail closed on garbage via confidentiality-guard inside the dispatcher, so failing
    closed here costs nothing new. A marker scan (the prior MCP-only fix) cannot cover Bash:
    the command is model-controlled and `\u006f`-style JSON escapes hide the marker from a raw
    scan. So EVERY payload the gate cannot parse into a JSON object is refused."""
    deep = "[" * 5000 + "]" * 5000
    marker = "send-via-" + "outlook.ps1"
    site = "website-" + "canonical"
    escaped = "send-via-outl" + chr(92) + "u006fok.ps1"  # JSON text carries a literal backslash-u
    cases = (
        ("Bash", '{"command":"powershell %s -To a@evil.com","x":%s}' % (marker, deep)),
        ("Bash", '{"command":"powershell %s -To a@evil.com","x":%s}' % (escaped, deep)),
        ("Bash", '{"command":"ls","x":%s}' % deep),
        ("Write", '{"file_path":"C:/Users/Owner/%s/i.html","content":"x","x":%s}' % (site, deep)),
        ("Edit", '{"file_path":"C:/Users/Owner/%s/i.html","x":%s}' % (site, deep)),
        ("MultiEdit", '{"file_path":"C:/Users/Owner/%s/i.html","x":%s}' % (site, deep)),
        ("NotebookEdit", '{"notebook_path":"C:/Users/Owner/%s/n.ipynb","x":%s}' % (site, deep)),
        ("Read", '{"x":%s}' % deep),
        (MS365 + "outlook_email_search", '{"x":%s}' % deep),
    )
    for tool, ti in cases:
        raw = '{"tool_name":"%s","tool_input":%s,"session_id":"%s"}' % (tool, ti, SESSION_A)
        rc, out, err = run_raw(raw)
        assert rc == 2, "unparseable %s payload must fail closed, got %s (%s)" % (tool, rc, err)
        assert out == "" and "could not be parsed" in err, (out, err)
    # int-digit cap is a second attacker-inducible ValueError (not RecursionError)
    big = '{"tool_name":"Bash","tool_input":{"command":"ls","n":%s},"session_id":"s"}' % ("9" * 6000)
    rc, _, err = run_raw(big)
    assert rc == 2, "oversized-integer payload must fail closed, got %s (%s)" % (rc, err)
    for junk in ("not json at all", "", "   ", "[]", "null", '"Bash"', "42"):
        rc, _, err = run_raw(junk)
        assert rc == 2, "non-object/unparseable stdin %r must fail closed, got %s (%s)" % (junk, rc, err)
    rc, _, err = run_raw_bytes(b'{"tool_name":"Bash","tool_input":{"command":"' + bytes([0xff, 0xfe]) + b'"}}')
    assert rc == 2, "invalid UTF-8 stdin must fail closed, got %s (%s)" % (rc, err)
    # a well-formed benign payload is untouched
    rc, _, err = run_hook(tool_payload("Bash", {"command": "ls"}))
    assert rc == 0, "a parseable benign payload must still pass, got %s (%s)" % (rc, err)
    print("PASS test_unparseable_payload_fails_closed_for_every_tool")


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
                                 "teams_reply_channel_message", "outlook_update_draft")]
    gated += [HUBSPOT + n for n in ("manage_blog_post", "manage_landing_page", "manage_website_page",
                                    "manage_social_posts")]
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
    print("ALL AUTONOMY-GATE MCP-SENDS TESTS PASS (%d)" % len(tests))
