"""Shared helpers for the ora-autonomy-gate.py PreToolUse hook tests (Gates 1 and 2).

Not a test file: run the five hooks/tests/test-ora-autonomy-gate-*.py files.
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

2026-11-23 -- split. The single test-ora-autonomy-gate.py (191 tests, ~190 hook subprocesses)
ran 110-390s under load against the pre-push hook-tests gate's 240s per-file budget and passed
the PR #480 push only on the gate's one 2x-budget retry. Its tests now live, verbatim, in five
files -- hooks/tests/test-ora-autonomy-gate-{core,mcp-sends,drafts-chats,calendar,
ncal-token-fields}.py -- and every module-level helper and constant moved here verbatim. This
module sits beside the test files (not in hooks/tests/lib/, a FULL-suite trigger for the
pre-push selector): its only importers name it, so selector rule 7 maps an edit here to
exactly those five files. The original is retired at
hooks/archive/test-ora-autonomy-gate.py.retired-2026-11-23. Each test file does
`from _autonomy_gate_testlib import *`; __all__ below is the full export list, underscore
names included.
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

__all__ = (
    "HERE",
    "HOOK",
    "SESSION_A",
    "SESSION_B",
    "SITE_FILE",
    "PROD_DEPLOY",
    "run_hook",
    "fresh_sessions_dir",
    "mint",
    "write_payload",
    "bash_payload",
    "mcp_payload",
    "send_payload",
    "CLAUDE_ROOT",
    "SLUG",
    "OTHER_MARKER",
    "_load_hook_module",
    "_junction",
    "_normalize_for_matching_component",
    "LIB_DIR",
    "CTRL_SPLIT_DEPLOY",
    "_shared_strip_categories",
    "_ISO_ROOTS",
    "_isolated_gate",
    "_run_gate",
    "MS365",
    "HUBSPOT",
    "tool_payload",
    "mail",
    "HS_READS",
    "HS_WRITES",
    "SOCIAL",
    "SOCIAL_PASS",
    "SOCIAL_BLOCK",
    "SOCIAL_MALFORMED",
    "run_raw",
    "run_raw_bytes",
    "CAL_TOOLS",
    "_filter_dest",
    "_digest",
    "_EVENT_OPS",
    "_event_dest",
    "_vac_dest",
    "cal",
    "_ev",
    "upd",
    "_EID",
    "_LIVE_START",
    "_LIVE_END",
    "_event_token",
    "chat",
    "_tokens_named_by_block_message",
    "NOTION",
    "NCAL_UPDATE",
    "NCAL_CREATE",
    "_NCAL_CAL",
    "_NCAL_PERIOD",
    "_NCAL_HINT",
    "_ncal_upd",
    "_ncal_dests",
    "_ncal_run",
    "_ncal_named",
    "_token_field_char_ok",
    "_plant_stuck_claim",
)


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


def _junction(link_path, target):
    """mklink /J, returning False when junctions are unavailable in this environment."""
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", link_path, target],
                          capture_output=True, text=True)
    return proc.returncode == 0


def _normalize_for_matching_component(text):
    """Local mirror of the hook's normalization, for test SETUP assertions only."""
    import unicodedata
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded
                   if unicodedata.category(ch) not in ("Cf", "Mn"))

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


# Gate 3b (audit finding confidentiality-guard-misses-hubspot-social-posts, 2026-11-08):
# manage_social_posts publishes to the firm's public social channels. Live schema (read
# 2026-11-08): action CREATE|UPDATE|CANCEL, confirmed (the connector's own preview gate),
# mode DRAFT|SCHEDULE|PUBLISH_NOW, plus broadcastGuid/channelId/content/fileIds/mediaUrl/
# publishAt/title; additionalProperties false.
SOCIAL = HUBSPOT + "manage_social_posts"
SOCIAL_PASS = (
    {"action": "CREATE", "channelId": "c1", "content": "x"},                         # preview
    {"action": "CREATE", "channelId": "c1", "content": "x", "mode": "PUBLISH_NOW",
     "confirmed": False},                                                            # preview
    {"action": "UPDATE", "broadcastGuid": "g", "content": "x"},                      # preview
    {"action": "CREATE", "channelId": "c1", "content": "x", "confirmed": True},      # draft
    {"action": "CREATE", "channelId": "c1", "content": "x", "mode": "DRAFT", "confirmed": True},
    {"action": "CANCEL", "broadcastGuid": "g", "confirmed": True},                   # unschedule
)
SOCIAL_BLOCK = (
    {"action": "CREATE", "channelId": "c1", "content": "x", "mode": "PUBLISH_NOW", "confirmed": True},
    {"action": "CREATE", "channelId": "c1", "content": "x", "mode": "SCHEDULE", "confirmed": True},
    {"action": "CREATE", "channelId": "c1", "content": "x", "publishAt": "2027-01-01T10:00:00Z",
     "confirmed": True},
    {"action": "UPDATE", "broadcastGuid": "g", "mode": "PUBLISH_NOW", "confirmed": True},
    {"action": "UPDATE", "broadcastGuid": "g", "content": "x", "confirmed": True},   # may be scheduled
    {"action": "FUTURE_ACTION", "confirmed": True},
    # E4 (#427 review, 2026-11-08): an EXPLICIT null mode is not the documented default. Only an
    # absent key or "DRAFT" is provably a draft; how the connector treats null is unverified.
    {"action": "CREATE", "channelId": "c1", "content": "x", "mode": None, "confirmed": True},
)
SOCIAL_MALFORMED = (
    {"action": "CREATE", "channelId": "c1", "content": "x", "confirmed": "true"},
    {"action": "CREATE", "channelId": "c1", "content": "x", "confirmed": True, "extra": 1},
    {"action": 5, "confirmed": True},
    {"action": "CREATE", "mode": 5, "confirmed": True},
)


def run_raw(raw, sessions_dir=None):
    """Feed the hook an exact stdin string (run_hook always serialises a dict)."""
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir if sessions_dir is not None else fresh_sessions_dir()
    proc = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def run_raw_bytes(raw):
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = fresh_sessions_dir()
    proc = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, env=env)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")
CAL_TOOLS = ("outlook_create_event", "outlook_update_event", "outlook_delete_event",
             "outlook_respond_to_event", "outlook_set_vacation", "outlook_create_filter")


def _filter_dest(tool_input):
    import hashlib
    blob = json.dumps(tool_input, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "filter:" + hashlib.sha256(blob.encode("ascii")).hexdigest()[:16]


def _digest(tool_input):
    import hashlib
    blob = json.dumps(tool_input, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()[:16]


_EVENT_OPS = {"outlook_update_event": "event-update", "outlook_delete_event": "event-delete",
              "outlook_respond_to_event": "event-respond"}


def _event_dest(tool, tool_input):
    """The token target for update/delete/respond: operation + event id + a digest of the WHOLE
    input, so an approval for one action on an event cannot be spent on another (Opus 5.5 review
    of #296/#299, finding C9)."""
    return "%s:%s:%s" % (_EVENT_OPS[tool], tool_input["eventId"], _digest(tool_input))


def _vac_dest(tool_input):
    aud = tool_input.get("externalAudience", "")
    return "vacation:%s:%s" % ((aud or "unspecified"), _digest(tool_input))


def cal(tool, **ti):
    return tool_payload(MS365 + tool, ti)


def _ev(attendees, **extra):
    ti = {"subject": "s", "start": {"dateTime": "2026-10-01T10:00:00", "timeZone": "UTC"},
          "end": {"dateTime": "2026-10-01T11:00:00", "timeZone": "UTC"}}
    if attendees is not None:
        ti["attendees"] = attendees
    ti.update(extra)
    return cal("outlook_create_event", **ti)
def upd(**ti):
    ti.setdefault("messageId", "AAMkAGDraftOne")
    return tool_payload(MS365 + "outlook_update_draft", ti)
_EID = "AAMkAGEventOne"
_LIVE_START = {"dateTime": "2026-10-02T10:00:00", "timeZone": "Eastern Standard Time"}
_LIVE_END = {"dateTime": "2026-10-02T11:00:00", "timeZone": "Eastern Standard Time"}


def _event_token(recipients):
    d = fresh_sessions_dir()
    mint(d, "allow-external-send", "external-send", recipients=recipients)
    return d
def chat(**ti):
    return tool_payload(MS365 + "teams_create_chat", ti)


def _tokens_named_by_block_message(err):
    """What a person would copy: the token after `exactly:` in the hint line."""
    for line in err.splitlines():
        if "exactly:" in line:
            return [t.strip() for t in line.split("exactly:", 1)[1].split(",") if t.strip()]
    return []
NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__"
NCAL_UPDATE = NOTION + "notion-calendar-update-events"
NCAL_CREATE = NOTION + "notion-calendar-create-events"
_NCAL_CAL = {"accountId": "acct", "calendarId": "cal"}
_NCAL_PERIOD = {"type": "DATE_TIME", "start": {"dateTime": "2026-12-01T10:00:00Z"},
                "end": {"dateTime": "2026-12-01T11:00:00Z"}}
_NCAL_HINT = "Name every event in `recipients:` exactly:"


def _ncal_upd(event_id="evt-1", update=None, rsvp=None, tz="America/New_York"):
    u = {"event": {"calendar": dict(_NCAL_CAL), "eventId": event_id}}
    if rsvp is not None:
        u.update(updateType="RSVP", rsvp=rsvp)
    else:
        u.update(updateType="UPDATE", update=update if update is not None else {"summary": "moved"})
    return {"timeZone": tz, "updates": [u]}


def _ncal_dests(tool_input):
    """Every token the gate requires for an update-events call, in call order."""
    dig = _digest(tool_input)
    out = []
    for u in tool_input["updates"]:
        t = "ncal-%s:%s:%s" % (u["updateType"].lower(), u["event"]["eventId"], dig)
        if t not in out:
            out.append(t)
    return out


def _ncal_run(tool_input, recipients=None, tool=NCAL_UPDATE):
    d = None
    if recipients is not None:
        d = fresh_sessions_dir()
        mint(d, "allow-external-send", "external-send", recipients=recipients)
    return run_hook(tool_payload(tool, tool_input), sessions_dir=d)


def _ncal_named(tool_input):
    """The token(s) the GATE's block message asks for (not the test's own recomputation), so a
    negative binding test still fails if a field silently drops out of the gate's digest
    (REFUTE 2026-11-21, C8: mutants M1/M5/M9 survived negative tests that minted _ncal_dests)."""
    rc, _, err = _ncal_run(tool_input)
    assert rc == 2, err
    named = _tokens_named_by_block_message(err)
    assert named, err
    return named


def _token_field_char_ok(c):
    """The rule, written independently of the gate's regex: printable ASCII 0x21-0x7E except the
    two token-list separators ',' and ';'."""
    return 0x21 <= ord(c) <= 0x7E and c not in ",;"


def _plant_stuck_claim(token_file, age_seconds=60):
    """Leave the claim a caller killed mid-spend would leave behind (override_tokens' layout:
    <sid>/override-claims/<name>.<ino>-<mtime_ns>-<size>.lock), aged past a live spend."""
    st = os.stat(token_file)
    d = os.path.join(os.path.dirname(os.path.dirname(token_file)), "override-claims")
    os.makedirs(d, exist_ok=True)
    claim = os.path.join(d, "%s.%d-%d-%d.lock" % (os.path.basename(token_file), st.st_ino,
                                                  st.st_mtime_ns, st.st_size))
    open(claim, "w").close()
    old = time.time() - age_seconds
    os.utime(claim, (old, old))
    return claim
