#!/usr/bin/env python3
"""MCP destructive-delete gate -- PreToolUse hook (R-06; audit M18).

WHY. Under defaultMode=bypassPermissions no permission prompt fires, and before R-06 no
PreToolUse matcher named any delete-shaped MCP tool: one call could empty a Notion
database, delete a scheduled task or a workbook sheet, or discard a worktree for good
(Hard Invariants 5 and 6). This hook stands in for the missing prompt.

WIRING. ONE settings.json PreToolUse entry whose matcher is
mcp_delete_tiers.SETTINGS_MATCHER (asserted byte-identical by test-matcher-coverage.py).
It is deliberately NOT in a pretooluse-dispatcher chain: it is MCP-only.

DECISIONS (tier from lib/mcp_delete_tiers.py, session kind from lib/session_kind.py):
  exempt / unrouted ......................... allow, log
  scheduled/headless session, any tier ...... allow only on a matching row of
                                              hooks/mcp-delete-allowlist.json, else block;
                                              override tokens are never honored here
  irreversible, interactive or unknown ...... allow only with a single-use allow-mcp-delete
                                              token whose `targets:` names
                                              <suffix>:<sha256/16 of the input>; else block
  recoverable / unknown name, interactive ... "ask" decision (Gabriel confirms in the UI)

TOKEN (hooks/lib/override_tokens.py contract): hooks/sessions/<sid>/overrides/
allow-mcp-delete, 5 min, SINGLE-USE, consumed here (the sole enforcement point):
    scope: mcp-delete
    session: <sid>
    targets: <suffix>:<digest>[, ...]
    reason: <why Gabriel approved this>
Distinct from config-write-guard's allow-destructive-delete (Bash tree deletes): one name,
one tier. HONEST LIMIT inherited from override_tokens.py: the gate cannot tell a token
Gabriel approved from one the session wrote itself; it binds scope, session and exact
target, and refuses every token in a scheduled session.

FAIL POLICY. This hook only ever sees delete-shaped MCP calls, so failing closed cannot
brick a session; the worst case is one delete waiting for a fix.
  * unparseable payload .......................... block (this call only)
  * a library cannot be imported ................. block every routed call
  * any internal error, delete-shaped call ....... block (this call only)
  * any internal error, exempt/unrouted call ..... allow (nothing to gate)
  * tier library unimportable ..................... block EVERY mcp__ name (the keyword
    regex misses routed names such as clean_up_worktrees); a non-MCP name is blocked
    only if it matches the built-in delete-keyword fallback regex
  * python or this file missing, or a timeout .... the harness sees a non-2 exit or no
    exit and treats it as NON-blocking: the delete PROCEEDS. (A missing script makes
    CPython exit 2, which DOES block every routed call.) Under onFailure:block (R-09,
    staged) every failure blocks; all of it is scoped to delete-shaped calls.

LOG. One content-free JSON line per decision in hooks/_state/mcp-delete-log.jsonl
(gitignored): ts, decision, tool, tier, kind, task, target (suffix:digest). No input text.
Telemetry: one hooks/lib/guard_telemetry.py record, chain "mcp-delete".

EXIT CODES (PreToolUse): 0 = allow (stdout may carry an "ask" decision or
additionalContext); 2 + stderr = block. Never 1.

Test seams (TEST ONLY; never in settings.json env): ORA_MCP_DELETE_ALLOWLIST,
ORA_MCP_DELETE_LOG, plus the libraries' ORA_OVERRIDE_SESSIONS_DIR and
ORA_SESSION_STORE_DIRS.

Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import inspect
import json
import os
import re
import string
import sys
import time

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

try:
    import mcp_delete_tiers as tiers  # noqa: E402
    TIERS_LOADED = True
except BaseException:
    tiers = None
    TIERS_LOADED = False

try:
    import session_kind  # noqa: E402
    SESSION_KIND_LOADED = True
except BaseException:
    session_kind = None
    SESSION_KIND_LOADED = False

try:
    from override_tokens import Tier, token_grants, token_path  # noqa: E402
    if "consume" not in inspect.signature(token_grants).parameters:
        raise ImportError("override_tokens.token_grants() lacks 'consume'")
    TOKEN_CONTRACT_LOADED = True
except BaseException:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        """Inert stand-in: no validation; token_grants below refuses everything."""

        def __init__(self, name, scope, ttl, single_use=False, requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None, consume=True):
        return None

    def token_path(session_id, name):
        return None

try:
    import guard_telemetry as _telemetry  # noqa: E402
except BaseException:
    _telemetry = None

MCP_DELETE = Tier("allow-mcp-delete", "mcp-delete", 300, single_use=True,
                  requires_extra_check=True)
ALLOWLIST_PATH = os.path.join(HOOKS_DIR, "mcp-delete-allowlist.json")
LOG_PATH = os.path.join(HOOKS_DIR, "_state", "mcp-delete-log.jsonl")
LOG_MAX_BYTES = 2 * 1024 * 1024
_SAFE = frozenset(string.ascii_letters + string.digits + "._:-")
_STATE = {"tool": "", "sid": "", "t0": time.perf_counter(), "shaped": None}
# Built-in fallback used only when the tier library cannot classify a call.
FALLBACK_DELETE_RE = re.compile(r"delete|trash|remove|purge|discard", re.IGNORECASE)


def _sanitize(value, limit=160):
    if not isinstance(value, str):
        return ""
    return "".join(c if c in _SAFE else "_" for c in value)[:limit]


def _log(decision, fields):
    try:
        path = os.environ.get("ORA_MCP_DELETE_LOG") or LOG_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            if os.path.getsize(path) > LOG_MAX_BYTES:
                os.replace(path, path + ".1")
        except OSError:
            pass
        rec = {"ts": round(time.time(), 3), "decision": decision}
        for key, value in fields.items():
            rec[key] = _sanitize(value)
        with open(path, "a", encoding="ascii") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception:
        pass


def _telemetry_flush(rc):
    if _telemetry is None:
        return
    try:
        if not _telemetry.enabled():
            return
        ms = (time.perf_counter() - _STATE["t0"]) * 1000.0
        _telemetry.flush([_telemetry.make_record(
            "mcp-delete", "mcp-delete-guard", _STATE["tool"], _STATE["sid"], rc, ms,
            "inprocess")])
    except Exception:
        pass


def _exit(rc):
    _telemetry_flush(rc)
    sys.exit(rc)


def _deny(message):
    sys.stderr.write("BLOCKED by ORA MCP delete gate: %s\n" % message)
    _exit(2)


def _emit(obj):
    sys.stdout.write(json.dumps(obj))
    _exit(0)


def _ask(message):
    _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "permissionDecision": "ask",
                                  "permissionDecisionReason": message},
           "systemMessage": message})


def _allow_with_context(message):
    _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "additionalContext": message}})


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _load_allowlist():
    path = os.environ.get("ORA_MCP_DELETE_ALLOWLIST") or ALLOWLIST_PATH
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except Exception:
        return [], 0
    if not isinstance(data, dict):
        return [], 0
    entries, max_days = data.get("entries"), data.get("max_days")
    if (not isinstance(entries, list) or not isinstance(max_days, int)
            or isinstance(max_days, bool) or not 1 <= max_days <= 90):
        return [], 0
    return entries, max_days


def _field_matches(value, pattern):
    if not isinstance(pattern, str):
        return False
    values = value if isinstance(value, list) else [value]
    if not values:
        return False
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (str, int)):
            return False
        try:
            if re.fullmatch(pattern, str(v)) is None:
                return False
        except re.error:
            return False
    return True


def allowlisted(task_id, short, tier, tool_input, today=None):
    """The matching row's reason, or None. Rows bind task id + tool suffix + inputs."""
    if not task_id or not isinstance(tool_input, dict):
        return None
    today = today or datetime.date.today()
    entries, max_days = _load_allowlist()
    for row in entries:
        if not isinstance(row, dict):
            continue
        if row.get("task_id") != task_id or row.get("tool") != short:
            continue
        ratified, expires = _date(row.get("ratified")), _date(row.get("expires"))
        if ratified is None or expires is None or not ratified <= today <= expires:
            continue
        if (expires - ratified).days > max_days:
            continue
        if (tier in (tiers.IRREVERSIBLE, tiers.UNKNOWN)
                and row.get("irreversible_ack") is not True):
            continue
        match = row.get("match")
        if not isinstance(match, dict) or not match:
            continue
        if all(field in tool_input and _field_matches(tool_input[field], pattern)
               for field, pattern in match.items()):
            reason = row.get("reason")
            return reason if isinstance(reason, str) and reason else "allowlisted"
    return None


def _fallback_shaped(tool_name):
    return isinstance(tool_name, str) and FALLBACK_DELETE_RE.search(tool_name) is not None


def _desktop_entrypoint():
    ep = os.environ.get("CLAUDE_CODE_ENTRYPOINT") or ""
    return ep.strip().lower().startswith("claude-desktop")


def _shaped_after_error():
    """Was the failing call delete-shaped? Known tier wins; else the keyword fallback."""
    if _STATE["shaped"] is not None:
        return _STATE["shaped"]
    name = _STATE["tool"]
    try:
        if TIERS_LOADED and tiers.is_routed(name):
            return True
    except BaseException:
        pass
    return _fallback_shaped(name)


def _token_ok(sid, target):
    def binds(fields):
        raw = fields.get("targets", "")
        return target in [t.strip() for t in raw.split(",") if t.strip()]
    try:
        return token_grants(sid, MCP_DELETE, extra_check=binds, consume=True) is not None
    except Exception:
        return False


def _block_irreversible(short, reason, sid, target):
    if not TOKEN_CONTRACT_LOADED:
        where = ("<hooks/lib/override_tokens.py could not be imported -- NO override can be "
                 "honored; fix the module, do not mint a token>")
    else:
        where = token_path(sid, MCP_DELETE.name) or (
            "<no valid session_id in this payload -- an override cannot be honored here>")
    _deny(
        "%s is an IRREVERSIBLE delete (%s).\n"
        "Hard Invariants 5/6 require Gabriel's explicit in-turn confirmation. Prefer an "
        "archive or move. If he has just approved exactly this call, write this token and "
        "retry the identical call:\n"
        "  path: %s\n"
        "  valid: %d min, SINGLE-USE\n"
        "  content:\n"
        "    scope: %s\n"
        "    session: %s\n"
        "    targets: %s\n"
        "    reason: <why Gabriel approved this>\n"
        "Any change to the call's input changes the target digest and needs a new token."
        % (short, reason, where, MCP_DELETE.ttl // 60, MCP_DELETE.scope, sid or "<none>",
           target))


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        _deny("the hook payload could not be parsed into a JSON object, so this "
              "delete-shaped call cannot be evaluated. It fails closed for this call only.")
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    sid = payload.get("session_id")
    sid = sid if isinstance(sid, str) else ""
    _STATE["tool"] = tool_name if isinstance(tool_name, str) else ""
    _STATE["sid"] = sid
    if not TIERS_LOADED:
        # Without the tier library the routed-name set is unknown, and the keyword regex
        # misses routed names (clean_up_worktrees, *-cancel-events, sharepoint_move_item,
        # manage_segment, manage_campaign_objects). The matcher only routes delete-class
        # names here, so refuse every MCP name; keep the keyword test for non-MCP names.
        if _STATE["tool"].startswith("mcp__") or _fallback_shaped(_STATE["tool"]):
            _deny("hooks/lib/mcp_delete_tiers.py could not be imported (mcp_delete_tiers); "
                  "every MCP call that reaches this gate (%s) is refused until it is fixed."
                  % _STATE["tool"])
        _exit(0)
    tier, reason, short = tiers.classify(tool_name, tool_input)
    _STATE["shaped"] = tier not in (tiers.EXEMPT, tiers.UNROUTED)
    if tier in (tiers.EXEMPT, tiers.UNROUTED):
        _log("allow", {"tool": _STATE["tool"], "tier": tier})
        _exit(0)
    if not SESSION_KIND_LOADED:
        _deny("hooks/lib/session_kind.py could not be imported, so the gate cannot tell "
              "whether a human is present; %s is refused until it is fixed." % short)
    kind, task_id, evidence = session_kind.classify(sid)
    if kind == session_kind.UNKNOWN and _desktop_entrypoint():
        # UNKNOWN is not proof of an interactive session: under Claude Desktop an
        # unreadable record means a scheduled firing may be running unattended.
        kind = session_kind.SCHEDULED
        evidence = "desktop entrypoint, session kind unknown: fail closed (%s)" % evidence
    target = tiers.target_label(short, tool_input)
    fields = {"tool": _STATE["tool"], "tier": tier, "kind": kind,
              "task": task_id or "", "target": target}
    if kind == session_kind.SCHEDULED:
        why = allowlisted(task_id, short, tier, tool_input)
        if why is not None:
            _log("allow-allowlist", fields)
            _allow_with_context(
                "ORA MCP delete gate: %s allowed for scheduled task %s by "
                "hooks/mcp-delete-allowlist.json (%s)." % (short, task_id, why))
        _log("deny", fields)
        _deny("%s is a %s delete (%s) in a scheduled/headless session (%s). No human is "
              "present to approve it and override tokens are refused here. Stop and report "
              "instead; a recurring need becomes a ratified row in "
              "hooks/mcp-delete-allowlist.json." % (short, tier, reason, evidence))
    if tier == tiers.IRREVERSIBLE:
        if _token_ok(sid, target):
            _log("allow-token", fields)
            _exit(0)
        _log("deny", fields)
        _block_irreversible(short, reason, sid, target)
    _log("ask", fields)
    _ask("ORA MCP delete gate: %s is a %s delete (%s). Hard Invariants 5/6: approve only if "
         "Gabriel asked for exactly this; prefer archive or move." % (short, tier, reason))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 -- any internal error
        if not _shaped_after_error():
            _telemetry_flush(0)
            sys.exit(0)
        sys.stderr.write("BLOCKED by ORA MCP delete gate: internal error (%s) while "
                         "evaluating %s; failing closed for this call only.\n"
                         % (type(exc).__name__, _STATE["tool"] or "a delete-shaped call"))
        _telemetry_flush(2)
        sys.exit(2)
    sys.exit(0)
