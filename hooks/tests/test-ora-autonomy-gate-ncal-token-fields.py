"""Tests for ora-autonomy-gate.py -- Gate 1g Notion calendar binding and token-field rules (part 5 of 5).

Run: python test-ora-autonomy-gate-ncal-token-fields.py
Stdlib only. ASCII-only. Shared helpers: hooks/tests/_autonomy_gate_testlib.py.

Covers: the Gate 1g notion-calendar-update-events token binding (PR #477), the Gate 1d/1g
token-field charset parity (eventId / set_vacation audience, PR #480) including the
exhaustive every-ASCII-char-on-every-field check, and stuck override claims (PR #481).

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
# Gate 1g token binding (port of the Gate 1d binding, PR #477). notion-calendar-update-events
# minted `event:<eventId>` per update plus every bare external attendee address: the token was
# not bound to UPDATE vs RSVP or to the content, and the bare addresses were tool-unbound
# recipient tokens. Each update is now named `ncal-<update|rsvp>:<eventId>:<digest>`, where the
# digest is sha256[:16] of the WHOLE call (timeZone and sibling updates included).
# ---------------------------------------------------------------------------------------


def test_ncal_update_and_rsvp_always_gated_and_name_the_bound_token():
    for ti in (_ncal_upd(), _ncal_upd(rsvp={"responseStatus": "accepted"})):
        rc, _, err = _ncal_run(ti)
        assert rc == 2, "update/RSVP must always be gated, got %s (%s)" % (rc, err)
        assert _tokens_named_by_block_message(err) == _ncal_dests(ti), \
            "block message must name exactly the bound token(s): %s" % err
        rc, _, err = _ncal_run(ti, recipients=_ncal_dests(ti))
        assert rc == 0, "the bound token must authorize, got %s (%s)" % (rc, err)
    print("PASS test_ncal_update_and_rsvp_always_gated_and_name_the_bound_token")


def test_ncal_token_is_single_use():
    ti = _ncal_upd()
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=_ncal_dests(ti))
    rc, _, err = run_hook(tool_payload(NCAL_UPDATE, ti), sessions_dir=d)
    assert rc == 0, "first use must pass, got %s (%s)" % (rc, err)
    rc, _, err = run_hook(tool_payload(NCAL_UPDATE, ti), sessions_dir=d)
    assert rc == 2, "single-use, got %s (%s)" % (rc, err)
    print("PASS test_ncal_token_is_single_use")


def test_ncal_pre_binding_token_names_no_longer_authorize():
    ti = _ncal_upd(update={"summary": "moved", "attendees": [{"email": "x@example.com"}]})
    for old in (["event:evt-1"], ["event:evt-1", "x@example.com"], ["ncal-update:evt-1"],
                ["ncal:evt-1:" + _digest(ti)], ["evt-1"]):
        rc, _, err = _ncal_run(ti, recipients=old)
        assert rc == 2, "old-style token %r must not authorize, got %s (%s)" % (old, rc, err)
    print("PASS test_ncal_pre_binding_token_names_no_longer_authorize")


def test_ncal_token_is_bound_to_update_vs_rsvp():
    rsvp = _ncal_upd(rsvp={"responseStatus": "accepted"})
    upd = _ncal_upd(update={"attendees": [{"email": "ggoldberg@oxfordra.net"}]})
    rc, _, err = _ncal_run(upd, recipients=_ncal_dests(rsvp))
    assert rc == 2, "an RSVP token must not authorize an UPDATE, got %s (%s)" % (rc, err)
    swapped = ["ncal-update:" + t.split(":", 1)[1] for t in _ncal_dests(rsvp)]
    rc, _, err = _ncal_run(rsvp, recipients=swapped)
    assert rc == 2, "an update-typed token must not authorize an RSVP, got %s (%s)" % (rc, err)
    print("PASS test_ncal_token_is_bound_to_update_vs_rsvp")


def test_ncal_token_is_bound_to_the_content_of_the_call():
    approved = _ncal_upd(rsvp={"responseStatus": "accepted", "comment": "see you there"})
    for variant in (_ncal_upd(rsvp={"responseStatus": "declined", "comment": "see you there"}),
                    _ncal_upd(rsvp={"responseStatus": "accepted", "comment": "Deal is off."}),
                    _ncal_upd(event_id="evt-2", rsvp={"responseStatus": "accepted",
                                                      "comment": "see you there"}),
                    _ncal_upd(rsvp={"responseStatus": "accepted", "comment": "see you there"},
                              tz="UTC")):
        rc, _, err = _ncal_run(variant, recipients=_ncal_named(approved))
        assert rc == 2, "a token for one call must not authorize %r, got %s (%s)" % (variant, rc, err)
    keep = _ncal_upd(update={"attendees": [{"email": "ggoldberg@oxfordra.net"},
                                           {"email": "t@example.com"}]})
    drop = _ncal_upd(update={"attendees": [{"email": "ggoldberg@oxfordra.net"}]})
    rc, _, err = _ncal_run(drop, recipients=_ncal_named(keep) + ["t@example.com"])
    assert rc == 2, "a token for keeping an outside attendee must not authorize dropping them, got %s (%s)" % (rc, err)
    moved = _ncal_upd(update={"period": _NCAL_PERIOD})
    later = _ncal_upd(update={"period": dict(_NCAL_PERIOD,
                                             start={"dateTime": "2027-01-01T10:00:00Z"})})
    rc, _, err = _ncal_run(later, recipients=_ncal_named(moved))
    assert rc == 2, "a token for one time must not authorize another, got %s (%s)" % (rc, err)
    print("PASS test_ncal_token_is_bound_to_the_content_of_the_call")


def test_ncal_multi_update_call_needs_every_token_and_binds_the_set():
    a = _ncal_upd(event_id="evt-1")["updates"][0]
    b = _ncal_upd(event_id="evt-2", rsvp={"responseStatus": "accepted"})["updates"][0]
    both = {"timeZone": "UTC", "updates": [a, b]}
    dests = _ncal_dests(both)
    assert len(dests) == 2
    rc, _, err = _ncal_run(both)
    assert rc == 2 and _tokens_named_by_block_message(err) == dests, err
    for partial in ([dests[0]], [dests[1]]):
        rc, _, err = _ncal_run(both, recipients=partial)
        assert rc == 2, "a token naming only %r must not authorize both updates, got %s" % (partial, rc)
    rc, _, err = _ncal_run(both, recipients=dests)
    assert rc == 0, "naming every bound token must authorize, got %s (%s)" % (rc, err)
    only_a = {"timeZone": "UTC", "updates": [a]}
    rc, _, err = _ncal_run(only_a, recipients=dests)
    assert rc == 2, "an approval of a two-update call must not authorize a subset, got %s (%s)" % (rc, err)
    print("PASS test_ncal_multi_update_call_needs_every_token_and_binds_the_set")


def test_ncal_update_token_cannot_be_spent_as_a_send_to_the_attendee():
    """The pre-binding token list carried the outside attendee's bare address, a tool-unbound
    recipient token: the approval also authorized a send_mail, a Notion create or a Teams chat
    to that address. Mint what the block message asks for; it must authorize only the update."""
    x = "x@example.com"
    ti = _ncal_upd(update={"attendees": [{"email": x, "displayName": "X"}]})
    rc, _, err = _ncal_run(ti)
    assert rc == 2
    named = _tokens_named_by_block_message(err)
    assert named == _ncal_dests(ti), "block message must ask for ONLY the bound token: %r" % named
    assert x not in named
    for tool, payload in ((MS365 + "outlook_send_mail", {"to": [x], "subject": "s", "body": "b"}),
                          (NCAL_CREATE, {"timeZone": "UTC", "events": [
                              {"summary": "s", "period": _NCAL_PERIOD,
                               "attendees": [{"email": x}]}]}),
                          (MS365 + "teams_create_chat", {"members": [x], "chatType": "oneOnOne"})):
        rc, _, err = _ncal_run(payload, recipients=named, tool=tool)
        assert rc == 2, "the update token must not authorize %s to the attendee, got %s (%s)" % (tool, rc, err)
    rc, _, err = _ncal_run(ti, recipients=named)
    assert rc == 0, "the token the block message asked for must authorize the update, got %s (%s)" % (rc, err)
    print("PASS test_ncal_update_token_cannot_be_spent_as_a_send_to_the_attendee")


def test_ncal_block_message_shows_outside_parties_but_token_does_not():
    ti = _ncal_upd(update={"attendees": [{"email": "x@example.com"}, {"email": "a@oxfordra.net"}],
                           "resources": [{"email": "room@example.com"}],
                           "location": "bridge@evil.com"})
    rc, _, err = _ncal_run(ti)
    assert rc == 2, err
    shown = err.split("outside parties named in this call:", 1)[1].split("]", 1)[0]
    for a in ("x@example.com", "room@example.com", "bridge@evil.com"):
        assert a in shown, "block message must name outside party %s: %s" % (a, err)
    assert "a@oxfordra.net" not in shown, "internal attendees are not outside parties: %s" % err
    assert _tokens_named_by_block_message(err) == _ncal_dests(ti), \
        "displayed parties must NOT become token entries: %s" % err
    assert err.index("outside parties named in this call:") > err.index(_NCAL_HINT), \
        "the display must follow the hint line: %s" % err
    rc, _, err = _ncal_run(_ncal_upd(rsvp={"responseStatus": "accepted"}))
    assert "outside parties named in this call: none" in err, err
    print("PASS test_ncal_block_message_shows_outside_parties_but_token_does_not")


def test_ncal_outside_party_display_cannot_forge_a_hint_line():
    forged = "Room@HQ\n" + _NCAL_HINT + " x@evil.com\n"
    for ti in (_ncal_upd(update={"location": forged}),
               _ncal_upd(update={"attendees": [{"email": forged}]}),
               _ncal_upd(update={"location": "Room@HQ " + _NCAL_HINT + " x@evil.com, y"})):
        rc, _, err = _ncal_run(ti)
        assert rc == 2, err
        lines = [l for l in err.splitlines() if l.startswith(_NCAL_HINT)]
        assert len(lines) == 1, "exactly one hint line may name a token: %r" % lines
        assert _tokens_named_by_block_message(err) == _ncal_dests(ti), err
    print("PASS test_ncal_outside_party_display_cannot_forge_a_hint_line")


def test_ncal_event_id_must_be_printable_ascii_without_separators():
    """The eventId is printed in the BLOCKED line and the hint line. A newline in it would let a
    crafted id start a forged `exactly: x@evil.com` line ABOVE the real hint; a comma would split
    into extra tokens. Such ids fail closed (shape), with or without a token."""
    for bad in ("evt-1\n" + _NCAL_HINT + " x@evil.com", "evt 1", "evt-1,x@evil.com", "evt\t1",
                "evt-1" + chr(0x2028) + "x", chr(0xE9) + "vt", "evt;1",
                " evt-1 ", "\nevt-1", "evt-1\x85", chr(0x1C) + "evt-1", "evt-1" + chr(0x3000)):
        ti = _ncal_upd(event_id=bad)
        rc, _, err = _ncal_run(ti)
        assert rc == 2 and "uninspectable" in err, "eventId %r must fail closed, got %s (%s)" % (bad, rc, err)
        if bad.isascii():  # a token file is ASCII; a non-ASCII id could not be named in one anyway
            rc, _, err = _ncal_run(ti, recipients=_ncal_dests(ti))
            assert rc == 2 and "uninspectable" in err, "eventId %r must fail closed even with a token" % bad
    for ok in ("evt-1", "3kq0vte9mfp1_20261201T150000Z", "abc@google.com"):
        ti = _ncal_upd(event_id=ok)
        rc, _, err = _ncal_run(ti, recipients=_ncal_dests(ti))
        assert rc == 0, "eventId %r must be authorizable, got %s (%s)" % (ok, rc, err)
    print("PASS test_ncal_event_id_must_be_printable_ascii_without_separators")


def test_ncal_malformed_updates_fail_closed_even_with_a_bound_token():
    base = _ncal_upd()["updates"][0]
    bads = [
        {"timeZone": "UTC", "updates": []},
        {"timeZone": "UTC", "updates": "x"},
        {"timeZone": "UTC", "updates": [dict(base, updateType="DELETE")]},
        {"timeZone": "UTC", "updates": [dict(base, extra=1)]},
        {"timeZone": "UTC", "updates": [dict(base, update={"notify": True})]},
        {"timeZone": "UTC", "updates": [dict(base, update={"attendees": "x@example.com"})]},
        {"timeZone": "UTC", "updates": [dict(base, update={"attendees": [{"email": 5}]})]},
        {"timeZone": "UTC", "updates": [dict(base, event={"eventId": ""})]},
        {"timeZone": "UTC", "updates": [dict(base, event={"eventId": 5})]},
        {"timeZone": "UTC", "updates": [{"updateType": "RSVP", "event": base["event"],
                                         "rsvp": {"responseStatus": "accepted", "to": "x@e.com"}}]},
        {"timeZone": "UTC", "updates": [base], "notify": True},
    ]
    for ti in bads:
        rc, _, err = _ncal_run(ti, recipients=["ncal-update:evt-1:" + _digest(ti),
                                               "ncal-rsvp:evt-1:" + _digest(ti)])
        assert rc == 2 and "uninspectable" in err, "%r must fail closed, got %s (%s)" % (ti, rc, err)
    print("PASS test_ncal_malformed_updates_fail_closed_even_with_a_bound_token")


def test_ncal_create_unchanged_by_the_binding():
    ev = {"summary": "s", "period": _NCAL_PERIOD, "attendees": [{"email": "broker@example.com"}]}
    ti = {"timeZone": "UTC", "events": [ev]}
    rc, _, err = _ncal_run(ti, tool=NCAL_CREATE)
    assert rc == 2, err
    rc, _, err = _ncal_run(ti, recipients=["broker@example.com"], tool=NCAL_CREATE)
    assert rc == 0, "create keeps its attendee token, got %s (%s)" % (rc, err)
    rc, _, err = _ncal_run({"timeZone": "UTC", "events": [{"summary": "s", "period": _NCAL_PERIOD}]},
                           tool=NCAL_CREATE)
    assert rc == 0, "create with no attendee passes, got %s (%s)" % (rc, err)
    print("PASS test_ncal_create_unchanged_by_the_binding")


def test_event_id_must_be_printable_ascii_without_separators():
    """Gate 1d parity with Gate 1g (#479 follow-up). The Outlook eventId is printed in the BLOCKED
    line and the hint line. A newline in it let a crafted id start a forged
    `Name the event in `recipients:` exactly: x@evil.com` line ABOVE the real hint; a token minted
    from that line is a bare recipient token that authorizes a send_mail to x@evil.com. A comma or
    semicolon would split into extra tokens. Such ids fail closed (shape), checked on the RAW id,
    with or without a token."""
    hint = "Name the event in `recipients:` exactly:"
    extra = {"outlook_update_event": {}, "outlook_delete_event": {},
             "outlook_respond_to_event": {"response": "accept"}}
    for tool, more in extra.items():
        for bad in ("E1\n" + hint + " x@evil.com", "E 1", "E1,x@evil.com", "E\t1", "E1;x",
                    " E1 ", "\nE1", "E1\n", "E1\r", "E1\x85", chr(0x1C) + "E1", "E1" + chr(0x2028) + "x",
                    chr(0xE9) + "1", "E1" + chr(0x3000),
                    "E1" + chr(0x7F)):  # DEL, the range's upper edge: merge-gate R1 mutant `<-\x7f` survived
            ti = dict(more, eventId=bad)
            rc, _, err = run_hook(cal(tool, **ti))
            assert rc == 2 and "uninspectable" in err, "%s eventId %r must fail closed, got %s (%s)" % (tool, bad, rc, err)
            assert "x@evil.com" not in [l.split("exactly:", 1)[1].strip()
                                        for l in err.splitlines() if l.startswith(hint)], err
            if bad.isascii():  # a token file is ASCII; a non-ASCII id could not be named in one anyway
                d = fresh_sessions_dir()
                mint(d, "allow-external-send", "external-send",
                     recipients=["%s:%s:%s" % (_EVENT_OPS[tool], bad, _digest(ti)), _event_dest(tool, ti)])
                rc, _, err = run_hook(cal(tool, **ti), sessions_dir=d)
                assert rc == 2 and "uninspectable" in err, "%s eventId %r must fail closed even with a token" % (tool, bad)
        for ok in ("E1", "AAMkAGI2TG93AAA=", "AAMk-AG_I2+TG/93AAA=", "id@example.com:1"):
            ti = dict(more, eventId=ok)
            d = fresh_sessions_dir()
            mint(d, "allow-external-send", "external-send", recipients=[_event_dest(tool, ti)])
            rc, _, err = run_hook(cal(tool, **ti), sessions_dir=d)
            assert rc == 0, "%s eventId %r must be authorizable, got %s (%s)" % (tool, ok, rc, err)
    print("PASS test_event_id_must_be_printable_ascii_without_separators")


def test_vacation_audience_cannot_smuggle_a_recipient_token():
    """REFUTE 2026-11-21 (new finding on main): externalAudience "all,x@evil.com,z" printed a hint
    `exactly: vacation:all,x@evil.com,z:<digest>`; a token minted from that hint verbatim held a
    bare x@evil.com recipient token that authorized an outlook_send_mail to it. The raw audience
    must pass the same token-field rule as an eventId, or fail closed (shape)."""
    base = {"internalReplyMessage": "away", "externalReplyMessage": "away"}
    hint = "Name the event in `recipients:` exactly:"
    for bad in ("all,x@evil.com,z", "all;x@evil.com", "all\n" + hint + " x@evil.com", " all", "all ",
                "contacts Only", "all\t", "\nall", chr(0x1C) + "all", "all" + chr(0x2028), chr(0xE0) + "ll",
                "   ", "\n",  # whitespace-only: REFUTE round 2 V5, an `audience.strip() and` guard survived
                "all" + chr(0x7F)):  # DEL, the range's upper edge: merge-gate R1 mutant `<-\x7f` survived
        ti = dict(base, externalAudience=bad)
        rc, _, err = run_hook(cal("outlook_set_vacation", **ti))
        assert rc == 2 and "uninspectable" in err, "externalAudience %r must fail closed, got %s (%s)" % (bad, rc, err)
        assert "x@evil.com" not in _tokens_named_by_block_message(err), err
        if bad.isascii():
            d = fresh_sessions_dir()
            mint(d, "allow-external-send", "external-send",
                 recipients=["vacation:%s:%s" % (bad, _digest(ti)), _vac_dest(ti)])
            rc, _, err = run_hook(cal("outlook_set_vacation", **ti), sessions_dir=d)
            assert rc == 2 and "uninspectable" in err, "externalAudience %r must fail closed even with a token" % bad
    # The reported exploit end to end: whatever the block message tells a person to name must not
    # authorize a send to an address smuggled into the audience.
    ti = dict(base, externalAudience="all,x@evil.com,z")
    rc, _, err = run_hook(cal("outlook_set_vacation", **ti))
    named = _tokens_named_by_block_message(err)
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=named or ["vacation:none:0"])
    rc, _, err = run_hook(mail(["x@evil.com"]), sessions_dir=d)
    assert rc == 2, "a token copied from the vacation block message must not authorize a send, got %s (%s)" % (rc, err)
    for ok in ("all", "contactsOnly", ""):  # "" is "unspecified" (REFUTE round 2 V5: a key-present guard survived)
        ti = dict(base, externalAudience=ok)
        if ok == "":
            assert _vac_dest(ti).startswith("vacation:unspecified:"), _vac_dest(ti)
        d = fresh_sessions_dir()
        mint(d, "allow-external-send", "external-send", recipients=[_vac_dest(ti)])
        rc, _, err = run_hook(cal("outlook_set_vacation", **ti), sessions_dir=d)
        assert rc == 0, "externalAudience %r must be authorizable, got %s (%s)" % (ok, rc, err)
    print("PASS test_vacation_audience_cannot_smuggle_a_recipient_token")


def test_token_field_rule_holds_for_every_ascii_char_on_every_field():
    """Merge-gate rounds 1-2 (PR #480) found the hand-picked lists missed range edges twice
    (DEL; then '!', '<', '~' and the Gate 1g alias). Every ASCII code point is checked in-process
    against _token_field_char_ok on the gate's shared regex AND through the three gate check
    functions themselves (round 4, F-008: a regex-only sweep let an inline regex at a check site
    accept VT or reject '\\' unseen), the Gate 1g alias must BE that regex, and the range edges
    plus both separators go end to end through the hook on each of the three printed fields.
    (Round 3: a 384-subprocess sweep pushed this file past the hook-test gate's 240s per-file
    budget, so the sweep is in-process and only the edges spawn the hook.)"""
    mod = _load_hook_module()
    assert mod._NCAL_EVENT_ID is mod._TOKEN_FIELD_CHARS, "Gate 1g must use the shared token-field rule"
    for i in range(0x80):
        c = chr(i)
        for v in ("E" + c + "1", c):
            got = bool(mod._TOKEN_FIELD_CHARS.fullmatch(v))
            assert got == _token_field_char_ok(c), "rule mismatch for %r: regex %s" % (v, got)

    # Round 4 (F-008): the regex check above cannot see an inline regex at a check site, so every
    # code point (plus non-ASCII line breaks and ASCII-folding characters, round 5) also goes
    # through the three gate functions themselves, on every operation that prints the field, at
    # the start, middle and end of the value, and in either of two Notion updates. override_active is stubbed
    # to grant and record what it was asked about (no token files are touched): an allowed
    # character must reach it with the raw value in the token; a disallowed one must fail closed
    # through block_shape BEFORE override_active is ever asked (round 5: the token list is kept on
    # the SystemExit path too, so a check moved after the token lookup is caught).
    import contextlib
    import io
    asked = []

    def grant(session_id, tier, external=None, consume=True):
        asked.append(list(external or []))
        return True

    mod.override_active = grant

    def gate(fn, short, ti):
        del asked[:]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                fn(short, "mcp__x__" + short, ti, SESSION_A)
                rc = None
            except SystemExit as e:
                rc = e.code
        return rc, (asked[-1] if asked else None), err.getvalue()

    outlook_ops = (("outlook_delete_event", "event-delete", {}),
                   ("outlook_update_event", "event-update", {}),
                   ("outlook_respond_to_event", "event-respond", {"response": "accept"}))
    sites = [("%s eventId" % short, (lambda v, short=short, extra=extra: gate(
                  mod._check_calendar, short, dict(extra, eventId=v))), op)
             for short, op, extra in outlook_ops]
    sites.append(("vacation externalAudience", lambda v: gate(
        mod._check_calendar, "outlook_set_vacation",
        {"internalReplyMessage": "away", "externalReplyMessage": "away", "externalAudience": v}),
        "vacation"))
    sites.append(("ncal UPDATE eventId", lambda v: gate(
        mod._check_notion_calendar, "notion-calendar-update-events", _ncal_upd(event_id=v)),
        "ncal-update"))
    sites.append(("ncal RSVP eventId", lambda v: gate(
        mod._check_notion_calendar, "notion-calendar-update-events",
        _ncal_upd(event_id=v, rsvp={"responseStatus": "accepted"})), "ncal-rsvp"))

    def ncal_second(v):
        ti = _ncal_upd(event_id="evt-ok")
        ti["updates"].append(_ncal_upd(event_id=v)["updates"][0])
        return gate(mod._check_notion_calendar, "notion-calendar-update-events", ti)

    sites.append(("ncal second-update eventId", ncal_second, "ncal-update"))

    def ncal_first(v):  # round 5c X6: a check on only the last update survived
        ti = _ncal_upd(event_id=v)
        ti["updates"].append(_ncal_upd(event_id="evt-ok")["updates"][0])
        return gate(mod._check_notion_calendar, "notion-calendar-update-events", ti)

    sites.append(("ncal first-of-two eventId", ncal_first, "ncal-update"))
    chars = [chr(i) for i in range(0x80)] + ["", " ", " ", "é", "　",
                                         "Ａ", "ı", "K", "ſ"]
    # ...the last four fold into ASCII: fullwidth A (NFKC), dotless i (upper), Kelvin sign
    # (lower/casefold to 'k'), long s (casefold to 's')
    for name, call, prefix in sites:
        for c in chars:
            for v in ("E" + c + "1", c, c + "E1", "E1" + c):
                rc, tok, err = call(v)
                if _token_field_char_ok(c):
                    assert rc is None and tok and any(t.startswith("%s:%s:" % (prefix, v)) for t in tok), (
                        "%s %s must reach the token check with the raw value, got rc=%s tok=%s (%s)"
                        % (name, ascii(v), rc, ascii(tok), ascii(err)))
                else:
                    assert rc == 2 and "uninspectable" in err and tok is None, (
                        "%s %s must fail closed (shape) before any token check, got rc=%s tok=%s (%s)"
                        % (name, ascii(v), rc, ascii(tok), ascii(err)))

    def outlook_event(c):
        ti = {"eventId": "E" + c + "1"}
        d = fresh_sessions_dir()
        if _token_field_char_ok(c):
            mint(d, "allow-external-send", "external-send",
                 recipients=[_event_dest("outlook_delete_event", ti)])
        return run_hook(cal("outlook_delete_event", **ti), sessions_dir=d)

    def vacation_audience(c):
        ti = {"internalReplyMessage": "away", "externalReplyMessage": "away",
              "externalAudience": "a" + c + "l"}
        d = fresh_sessions_dir()
        if _token_field_char_ok(c):
            mint(d, "allow-external-send", "external-send", recipients=[_vac_dest(ti)])
        return run_hook(cal("outlook_set_vacation", **ti), sessions_dir=d)

    def ncal_event(c):
        ti = _ncal_upd(event_id="evt" + c + "1")
        return _ncal_run(ti, recipients=_ncal_dests(ti) if _token_field_char_ok(c) else None)

    edges = (" ", "!", "<", "~", chr(0x7F), ",", ";")  # 0x20/0x21, '<' (range join), 0x7E/0x7F, separators
    for name, fn in (("outlook eventId", outlook_event), ("vacation externalAudience", vacation_audience),
                     ("ncal eventId", ncal_event)):
        for c in edges:
            rc, _, err = fn(c)
            if _token_field_char_ok(c):
                assert rc == 0, "%s with %r must be authorizable, got %s (%s)" % (name, c, rc, err)
            else:
                assert rc == 2 and "uninspectable" in err, (
                    "%s with %r must fail closed (shape), got %s (%s)" % (name, c, rc, err))
    # An omitted externalAudience means "unspecified" (merge-gate round 2: a default of "all" survived).
    ti = {"internalReplyMessage": "away", "externalReplyMessage": "away"}
    assert _vac_dest(ti).startswith("vacation:unspecified:"), _vac_dest(ti)
    rc, _, err = run_hook(cal("outlook_set_vacation", **ti))
    assert rc == 2 and "vacation:unspecified:" in err, err
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=[_vac_dest(ti)])
    rc, _, err = run_hook(cal("outlook_set_vacation", **ti), sessions_dir=d)
    assert rc == 0, "an omitted externalAudience must be authorizable as unspecified, got %s (%s)" % (rc, err)
    print("PASS test_token_field_rule_holds_for_every_ascii_char_on_every_field")


def test_stuck_claim_is_named_in_the_block_message():
    """PR #481 follow-up: a claim left by a caller killed mid-spend keeps refusing a valid
    token. The block message must say so, or the operator rewrites nothing and retries forever."""
    tool = "outlook_delete_event"
    ti = {"eventId": "E-stuck"}
    d = fresh_sessions_dir()
    tok = mint(d, "allow-external-send", "external-send", recipients=[_event_dest(tool, ti)])
    _plant_stuck_claim(tok)
    rc, _, err = run_hook(cal(tool, **ti), sessions_dir=d)
    assert rc == 2, "a stuck-claimed token must still refuse (fail closed), got %s" % rc
    assert "STUCK CLAIM" in err, "block message must name the stuck claim: %s" % err[-600:]
    assert os.path.exists(tok), "the refused token must not be burned"
    print("PASS test_stuck_claim_is_named_in_the_block_message")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    try:
        for t in tests:
            t()
    finally:
        for _root in _ISO_ROOTS:
            shutil.rmtree(_root, ignore_errors=True)
    print("ALL AUTONOMY-GATE NCAL/TOKEN-FIELD TESTS PASS (%d)" % len(tests))
