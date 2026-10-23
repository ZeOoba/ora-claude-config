"""End-to-end tests for hooks/mcp-delete-guard.py (R-06).

Run: python test-mcp-delete-guard.py
Every run is a subprocess with ALL seams pointed at a fresh temp dir:
ORA_OVERRIDE_SESSIONS_DIR (tokens), ORA_SESSION_STORE_DIRS (session records),
ORA_MCP_DELETE_ALLOWLIST, ORA_MCP_DELETE_LOG, ORA_GUARD_TELEMETRY=0, and an explicit
CLAUDE_CODE_ENTRYPOINT -- so no live token, record or log can flip a result.

Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "mcp-delete-guard.py")
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
import mcp_delete_tiers as tiers  # noqa: E402

SESSION_A = "aaaaaaaa-1111-2222-3333-444444444444"   # interactive Desktop session
SESSION_S = "cccccccc-1111-2222-3333-444444444444"   # scheduled firing of ora-test-task
SESSION_C = "dddddddd-1111-2222-3333-444444444444"   # no record (plain CLI)
NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__"
SCHED_DEL = "mcp__scheduled-tasks__delete_scheduled_task"
PAGES = NOTION + "notion-delete-pages"
TI_SCHED = {"taskId": "r06-test-task"}
PAGE_ID = "0123456789abcdef0123456789abcdef"
TI_PAGES = {"page_ids": [PAGE_ID], "user_confirmed": True}
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def make_env(entries=None, entrypoint="claude-desktop"):
    root = tempfile.mkdtemp(prefix="mdg-")
    store = os.path.join(root, "store")
    os.makedirs(store)
    for name, rec in (("local_a.json", {"cliSessionId": SESSION_A}),
                      ("local_s.json", {"cliSessionId": SESSION_S,
                                        "scheduledTaskId": "ora-test-task"})):
        with open(os.path.join(store, name), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    allow = os.path.join(root, "allow.json")
    with open(allow, "w", encoding="utf-8") as fh:
        json.dump({"max_days": 90, "entries": entries or []}, fh)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update({
        "ORA_OVERRIDE_SESSIONS_DIR": os.path.join(root, "sessions"),
        "ORA_SESSION_STORE_DIRS": store,
        "ORA_MCP_DELETE_ALLOWLIST": allow,
        "ORA_MCP_DELETE_LOG": os.path.join(root, "log.jsonl"),
        "ORA_GUARD_TELEMETRY": "0",
        "CLAUDE_CODE_ENTRYPOINT": entrypoint,
    })
    return root, env


def run(env, tool, tool_input, sid=SESSION_A, raw=None, hook=HOOK, cwd=None):
    payload = raw if raw is not None else json.dumps({
        "tool_name": tool, "tool_input": tool_input, "session_id": sid,
        "hook_event_name": "PreToolUse"})
    p = subprocess.run([sys.executable, "-I", hook], input=payload.encode("utf-8"),
                       capture_output=True, env=env, timeout=60, cwd=cwd)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def mint(env, sid, targets, scope="mcp-delete", name="allow-mcp-delete", age=0):
    d = os.path.join(env["ORA_OVERRIDE_SESSIONS_DIR"], sid, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="ascii") as fh:
        fh.write("scope: %s\nsession: %s\ntargets: %s\nreason: Gabriel approved in-turn "
                 "(test)\n" % (scope, sid, ", ".join(targets)))
    if age:
        old = time.time() - age
        os.utime(path, (old, old))
    return path


def label(tool, ti):
    return tiers.target_label(tool.rsplit("__", 1)[-1], ti)


def decision(stdout):
    try:
        return json.loads(stdout)["hookSpecificOutput"].get("permissionDecision")
    except Exception:
        return None


def entry(**over):
    today = datetime.date.today()
    e = {"task_id": "ora-test-task", "tool": "notion-delete-pages",
         "match": {"page_ids": "[0-9a-f]{32}"},
         "ratified": (today - datetime.timedelta(days=1)).isoformat() + " Gabriel in-turn",
         "expires": (today + datetime.timedelta(days=30)).isoformat(),
         "reason": "test row"}
    e.update(over)
    return e


def test_irreversible():
    _, env = make_env()
    rc, out, err = run(env, SCHED_DEL, TI_SCHED)
    check("G1 irreversible without a token is blocked", rc == 2, "rc=%d" % rc)
    check("G1b block message names the tier and the exact target",
          "allow-mcp-delete" in err and label(SCHED_DEL, TI_SCHED) in err, err[-300:])
    tok = mint(env, SESSION_A, [label(SCHED_DEL, TI_SCHED)])
    rc, out, err = run(env, SCHED_DEL, TI_SCHED)
    check("G2 a token naming the exact call allows it", rc == 0, "rc=%d %s" % (rc, err[-200:]))
    check("G2b and is consumed (single-use)", not os.path.exists(tok))
    rc, _, _ = run(env, SCHED_DEL, TI_SCHED)
    check("G2c a second identical call is blocked again", rc == 2)
    tok = mint(env, SESSION_A, [label(SCHED_DEL, {"taskId": "other-task"})])
    rc, _, _ = run(env, SCHED_DEL, TI_SCHED)
    check("G3 a token for a different input is refused", rc == 2)
    check("G3b and is NOT burned", os.path.exists(tok))
    os.remove(tok)
    tok = mint(env, SESSION_A, [label(SCHED_DEL, TI_SCHED)], scope="destructive-delete")
    check("G4 wrong scope is refused", run(env, SCHED_DEL, TI_SCHED)[0] == 2)
    os.remove(tok)
    mint(env, SESSION_A, [label(SCHED_DEL, TI_SCHED)], name="allow-destructive-delete",
         scope="destructive-delete")
    check("G4b config-write-guard's allow-destructive-delete token does not open it",
          run(env, SCHED_DEL, TI_SCHED)[0] == 2)
    tok = mint(env, SESSION_A, [label(SCHED_DEL, TI_SCHED)], age=400)
    check("G5 an aged-out token (400 s > 300 s) is refused", run(env, SCHED_DEL, TI_SCHED)[0] == 2)
    os.remove(tok)
    rc, _, err = run(env, SCHED_DEL, TI_SCHED, sid="../evil")
    check("G6 an unsafe session id cannot address a token", rc == 2)
    ti = {"filepath": "C:/x/model.xlsx", "sheet_name": "Inputs"}
    check("G7 excel delete_worksheet is irreversible",
          run(env, "mcp__excel__delete_worksheet", ti)[0] == 2)
    ti = {"older_than_days": 30, "delete_sessions": True}
    check("G8 clean_up_worktrees with delete_sessions is irreversible",
          run(env, "mcp__ccd_host__clean_up_worktrees", ti)[0] == 2)


def test_recoverable_and_unknown():
    _, env = make_env()
    rc, out, err = run(env, PAGES, TI_PAGES)
    check("G9 recoverable interactive -> exit 0 with an ask decision",
          rc == 0 and decision(out) == "ask", "rc=%d out=%s" % (rc, out[:200]))
    rc, out, _ = run(env, "mcp__ccd_host__clean_up_worktrees", {"older_than_days": 30})
    check("G10 plain worktree cleanup asks", rc == 0 and decision(out) == "ask")
    rc, out, _ = run(env, "mcp__x__purge_everything", {"all": True})
    check("G11 unknown delete-shaped name asks interactively", rc == 0 and decision(out) == "ask")


def test_exempt():
    _, env = make_env()
    for tool in ("mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_delete_event",
                 "mcp__7c55602a-d1ec-4c77-a92e-06ee3c786d3a__image_remove_background",
                 "mcp__x__list_deleted_items"):
        rc, out, err = run(env, tool, {"id": "1"})
        check("G12 exempt %s passes silently" % tool.rsplit("__", 1)[-1],
              rc == 0 and decision(out) is None, "rc=%d out=%s" % (rc, out[:120]))


def test_scheduled_sessions():
    _, env = make_env()
    rc, _, err = run(env, PAGES, TI_PAGES, sid=SESSION_S)
    check("G13 recoverable in a scheduled session without an allowlist row is blocked",
          rc == 2 and "scheduled" in err, err[-200:])
    tok = mint(env, SESSION_S, [label(SCHED_DEL, TI_SCHED)])
    rc, _, _ = run(env, SCHED_DEL, TI_SCHED, sid=SESSION_S)
    check("G14 a valid token is NOT honored in a scheduled session", rc == 2)
    check("G14b and is left in place (never spent)", os.path.exists(tok))
    _, env = make_env(entries=[entry()])
    rc, out, _ = run(env, PAGES, TI_PAGES, sid=SESSION_S)
    check("G15 an allowlisted call from the matching task passes with context",
          rc == 0 and "allowlist" in out, "rc=%d out=%s" % (rc, out[:200]))
    check("G15b the same row does not admit an interactive session to skip the ask",
          decision(run(env, PAGES, TI_PAGES)[1]) == "ask")
    bad_page = {"page_ids": ["not-a-hex-id"], "user_confirmed": True}
    check("G16 input failing the row's regex is blocked",
          run(env, PAGES, bad_page, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(task_id="ora-other-task")])
    check("G17 a row for another task does not apply",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    today = datetime.date.today()
    _, env = make_env(entries=[entry(expires=(today - datetime.timedelta(days=1)).isoformat())])
    check("G18 an expired row does not apply", run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(
        expires=(today + datetime.timedelta(days=200)).isoformat())])
    check("G19 a row longer than max_days does not apply",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(tool="delete_scheduled_task",
                                     match={"taskId": "r06-test-task"})])
    check("G20 an irreversible row without irreversible_ack does not apply",
          run(env, SCHED_DEL, TI_SCHED, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(tool="delete_scheduled_task",
                                     match={"taskId": "r06-test-task"},
                                     irreversible_ack=True)])
    check("G21 an irreversible row WITH irreversible_ack applies",
          run(env, SCHED_DEL, TI_SCHED, sid=SESSION_S)[0] == 0)
    _, env = make_env(entries=[entry(match={})])
    check("G22 a row with an empty match never applies",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(tool="notion-update-page")])
    check("G15c a row whose tool differs from the called tool is refused (M15)",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(match={"absent_field": ".*"})])
    check("G15d a row whose match field is missing from the input is refused (M16)",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry()])
    with open(env["ORA_MCP_DELETE_ALLOWLIST"], "w", encoding="utf-8") as fh:
        json.dump({"max_days": 365, "entries": [entry()]}, fh)
    check("G19b a file-level max_days of 365 makes every row inert (M7)",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entries=[entry(
        ratified=(today + datetime.timedelta(days=1)).isoformat() + " Gabriel in-turn")])
    check("G18b a row with a future ratified date is refused (M9)",
          run(env, PAGES, TI_PAGES, sid=SESSION_S)[0] == 2)
    _, env = make_env(entrypoint="sdk-cli")
    check("G23 headless entrypoint with no record is treated as scheduled",
          run(env, PAGES, TI_PAGES, sid=SESSION_C)[0] == 2)


def test_plain_cli():
    _, env = make_env(entrypoint="cli")
    check("G24 plain CLI session (no record) asks on recoverable",
          decision(run(env, PAGES, TI_PAGES, sid=SESSION_C)[1]) == "ask")
    mint(env, SESSION_C, [label(SCHED_DEL, TI_SCHED)])
    check("G25 plain CLI session can spend a token",
          run(env, SCHED_DEL, TI_SCHED, sid=SESSION_C)[0] == 0)


def test_fail_modes_and_log():
    _, env = make_env()
    rc, _, err = run(env, None, None, raw="{not json")
    check("G26 unparseable payload is blocked", rc == 2 and "parsed" in err, err[-160:])
    rc, _, _ = run(env, None, None, raw="[]")
    check("G27 a non-object payload is blocked", rc == 2)
    tmp = tempfile.mkdtemp(prefix="mdg-nolib-")
    os.makedirs(os.path.join(tmp, "hooks", "lib"))
    copy = os.path.join(tmp, "hooks", "mcp-delete-guard.py")
    shutil.copyfile(HOOK, copy)
    rc, _, err = run(env, PAGES, TI_PAGES, hook=copy, cwd=tmp)
    check("G28 a missing tier library fails closed on a delete call",
          rc == 2 and "mcp_delete_tiers" in err, "rc=%d %s" % (rc, err[-200:]))
    _, env = make_env()
    run(env, PAGES, TI_PAGES)
    run(env, SCHED_DEL, TI_SCHED)
    with open(env["ORA_MCP_DELETE_LOG"], "r", encoding="ascii") as fh:
        text = fh.read()
    rows = [json.loads(x) for x in text.splitlines()]
    check("G29 one decision row per call", len(rows) == 2, "rows=%d" % len(rows))
    check("G29b rows record tool, tier and decision",
          rows[0].get("decision") == "ask" and rows[1].get("decision") == "deny")
    check("G29c rows carry no input content (page id absent)", PAGE_ID not in text)
    check("G29d every row has why (ASCII, <= 200 chars) and classify_ms (digits)",
          all(isinstance(r.get("why"), str) and 0 < len(r["why"]) <= 200
              and r.get("classify_ms", "").isdigit() for r in rows),
          repr([(r.get("why"), r.get("classify_ms")) for r in rows]))
    check("G29e deny row why names the session_kind evidence",
          "scheduledTaskId" in rows[1].get("why", ""), repr(rows[1].get("why")))
    check("G29f new fields carry no tool input (page id, task id, user_confirmed absent)",
          all(PAGE_ID not in str(r.get("why")) and "r06-test-task" not in str(r.get("why"))
              and "user_confirmed" not in json.dumps(r) for r in rows))


def _tree(patch_name, patch_src):
    """A temp copy of hooks/ (guard + lib) with one lib module replaced by patch_src."""
    tmp = tempfile.mkdtemp(prefix="mdg-tree-")
    os.makedirs(os.path.join(tmp, "hooks"))
    shutil.copyfile(HOOK, os.path.join(tmp, "hooks", "mcp-delete-guard.py"))
    shutil.copytree(os.path.join(HOOKS_DIR, "lib"), os.path.join(tmp, "hooks", "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    with open(os.path.join(tmp, "hooks", "lib", patch_name), "w", encoding="ascii") as fh:
        fh.write(patch_src)
    return os.path.join(tmp, "hooks", "mcp-delete-guard.py")


def test_hardening():
    _, env = make_env()
    # session_kind is consulted only for gated tiers (cheap classification first)
    sk_boom = "def classify(*a, **k):\n    raise RuntimeError('boom')\n"
    hook = _tree("session_kind.py", sk_boom)
    rc, out, _ = run(env, "mcp__x__list_deleted_items", {"id": "1"}, hook=hook)
    check("G30 exempt call never touches session_kind", rc == 0 and decision(out) is None)
    rc, out, _ = run(env, "mcp__x__get_page", {"id": "1"}, hook=hook)
    check("G30b unrouted call never touches session_kind", rc == 0 and decision(out) is None)
    rc, _, err = run(env, PAGES, TI_PAGES, hook=hook)
    check("G31 session_kind raising on a delete-shaped call denies (fail closed)",
          rc == 2 and "internal error" in err, "rc=%d %s" % (rc, err[-160:]))
    rc, _, _ = run(env, SCHED_DEL, TI_SCHED, hook=hook)
    check("G31b same for an irreversible call", rc == 2)
    sk_gone = "raise ImportError('gone')\n"
    hook = _tree("session_kind.py", sk_gone)
    rc, out, err = run(env, PAGES, TI_PAGES, hook=hook)
    check("G31c session_kind import failure on a gated call denies (M18)",
          rc == 2 and "session_kind" in err, "rc=%d %s" % (rc, err[-160:]))
    rc, out, _ = run(env, "mcp__x__list_deleted_items", {"id": "1"}, hook=hook)
    check("G31d session_kind import failure leaves an exempt call alone",
          rc == 0 and decision(out) is None)
    # tiers.classify raising: delete-keyword names deny, others pass
    t_boom = ("EXEMPT='exempt'\nUNROUTED='unrouted'\nIRREVERSIBLE='irreversible'\n"
              "def classify(*a, **k):\n    raise RuntimeError('boom')\n")
    hook = _tree("mcp_delete_tiers.py", t_boom)
    rc, _, err = run(env, PAGES, TI_PAGES, hook=hook)
    check("G32 classify raising on a delete-keyword name denies", rc == 2, err[-160:])
    rc, out, _ = run(env, "mcp__x__get_page", {"id": "1"}, hook=hook)
    check("G32b classify raising on a non-delete name allows", rc == 0 and decision(out) is None)
    # import failure of the tiers library: keyword fallback
    hook = _tree("mcp_delete_tiers.py", "raise ImportError('gone')\n")
    rc, _, err = run(env, "mcp__x__remove_thing", {}, hook=hook)
    check("G33 tiers import failure + delete keyword name denies",
          rc == 2 and "mcp_delete_tiers" in err)
    rc, out, err = run(env, "mcp__x__get_page", {"id": "1"}, hook=hook)
    check("G33b tiers import failure denies every mcp__ name (no keyword gap)",
          rc == 2 and "mcp_delete_tiers" in err, "rc=%d" % rc)
    for name in ("mcp__ccd_host__clean_up_worktrees",
                 NOTION + "notion-calendar-cancel-events",
                 "mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__sharepoint_move_item",
                 "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__manage_segment",
                 "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__manage_campaign_objects"):
        rc, _, err = run(env, name, {"id": "1"}, hook=hook)
        check("G33c tiers import failure denies routed non-keyword %s" % name.rsplit("__", 1)[-1],
              rc == 2 and "mcp_delete_tiers" in err, "rc=%d" % rc)
    rc, out, _ = run(env, "Read", {"file_path": "x"}, hook=hook)
    check("G33d tiers import failure still allows a non-mcp, non-keyword name",
          rc == 0 and decision(out) is None)
    # session kind UNKNOWN follows the entrypoint
    rc, out, _ = run(env, PAGES, TI_PAGES, sid="")
    check("G34 desktop entrypoint + no session id is treated as scheduled", rc == 2)
    _, env_cli = make_env(entrypoint="cli")
    rc, out, _ = run(env_cli, PAGES, TI_PAGES, sid="")
    check("G34b non-desktop entrypoint + no session id is treated as interactive (ask)",
          rc == 0 and decision(out) == "ask")
    # unknown tier in a scheduled session needs the ack like irreversible
    unk = {"id": "1"}
    row = entry(tool="purge_everything", match={"id": "1"})
    _, env_a = make_env(entries=[row])
    check("G35 unknown-tier row without ack does not apply in a scheduled session",
          run(env_a, "mcp__x__purge_everything", unk, sid=SESSION_S)[0] == 2)
    row["irreversible_ack"] = True
    _, env_a = make_env(entries=[row])
    check("G35b unknown-tier row WITH ack applies",
          run(env_a, "mcp__x__purge_everything", unk, sid=SESSION_S)[0] == 0)
    # oversized name is unknown tier: ask interactively, never raises
    big = "mcp__x__" + "delete_" * 200
    rc, out, _ = run(env, big, {"id": "1"})
    check("G36 oversized delete-shaped name asks (no crash)", rc == 0 and decision(out) == "ask",
          "rc=%d" % rc)
    # no exit code 1 anywhere; normal call is fast
    t0 = time.time()
    rc, _, _ = run(env, PAGES, TI_PAGES)
    check("G37 a normal gated call finishes well inside the 2 s budget",
          time.time() - t0 < 2.0, "%.2fs" % (time.time() - t0))
    rcs = set(run(env, t, i)[0] for t, i in ((PAGES, TI_PAGES), (SCHED_DEL, TI_SCHED),
                                              ("mcp__x__get_page", {})))
    check("G38 exit codes are only 0 or 2", rcs <= {0, 2}, str(rcs))


if __name__ == "__main__":
    test_irreversible()
    test_recoverable_and_unknown()
    test_exempt()
    test_scheduled_sessions()
    test_plain_cli()
    test_fail_modes_and_log()
    test_hardening()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL mcp-delete-guard tests passed.")
    sys.exit(0)
