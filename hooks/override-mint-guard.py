#!/usr/bin/env python3
"""Refuse override-token writes from scheduled/headless sessions -- PreToolUse (R-06).

override_tokens.py: a token "may be created ONLY after Gabriel's explicit in-turn
confirmation in a live session. Scheduled/headless sessions must NEVER self-create one."
Until R-06 that rule was prose. In a session lib/session_kind.py classifies as SCHEDULED,
this guard blocks any Edit/Write/MultiEdit/Bash call whose write target or command text
names hooks/sessions/<id>/overrides/. It covers EVERY tier's tokens, not only
allow-mcp-delete, and every session id (a scheduled session minting into an interactive
session's directory is blocked too).

WIRING (Task 6): pretooluse-dispatcher.py GUARD_CHAIN (Edit/Write/MultiEdit) and
BASH_GUARD_CHAIN (Bash) only. No settings.json entry yet. NotebookEdit and Desktop
Commander writes (write_file/edit_block/move_file/start_process/interact_with_process)
are NOT covered until a separate settings.json entry (Task 7, deferred) with matcher
`NotebookEdit|mcp__.*(write_file|edit_block|move_file|start_process|interact_with_process|write_pdf)`.

FAILS OPEN on every internal error and on unparseable input: it sits on the Edit/Write/
Bash path, where a fail-closed bug would brick sessions (confidentiality-guard already
refuses unparseable payloads on that path). It blocks only on a positive path match in a
positively-SCHEDULED session; UNKNOWN (plain CLI) is not blocked.

PATH MATCHING: text is normalised first (lower-case, slashes collapsed, '/./' removed). A
hit is 'hooks/sessions' followed later by 'overrides' or the 8.3 alias 'overri~', or an
'overrides'/'overri~' token while the payload cwd is under hooks/sessions (covers a
persistent `cd` made in an earlier call).

HONEST LIMITS: Bash matching is on pre-expansion text (a variable holding the path evades
it), the limit config-write-guard.py states for its own Bash layer. Directory junction/
symlink aliasing of hooks/sessions or an overrides dir cannot be detected from text and
evades it. Until Task 7, NotebookEdit and Desktop Commander writes do not reach this
guard (see WIRING). Whether the PowerShell tool is routed through the Bash chain is
unconfirmed; treat PowerShell-tool coverage as absent until verified. The backstop is the consumption side: mcp-delete-guard.py
never spends a token in a scheduled session, whoever wrote it.

SCOPE EXTENSION (R-06 Task 3 review). lib/session_kind.py documents residual (c): a
scheduled session with a shell could move/hide/rename its own session record dir, forge
store roots, or edit local_*.json, and so reclassify itself. So in a SCHEDULED session
(same rule as mcp-delete-guard.py: SCHEDULED, or UNKNOWN under a claude-desktop
entrypoint) this guard also exits 2 when (i) a Write/Edit/MultiEdit path (NotebookEdit once Task 7 wires it)
contains 'claude-code-sessions' (case-insensitive, either slash style), or (ii) a Bash
command text contains 'claude-code-sessions', 'ORA_SESSION_STORE_DIRS' or
'CLAUDE_CODE_ENTRYPOINT'. Interactive sessions are never affected. This is
detective-light: obfuscated names (env-var expansion, string concatenation, globbing)
evade a text match. session_kind's own fail-closed Desktop rule is the backstop.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))


def _norm(text):
    """Lower-case, backslashes to '/', runs of '/' collapsed, '/./' segments removed."""
    t = text.replace("\\", "/").lower()
    t = re.sub(r"/+", "/", t)
    while "/./" in t:
        t = t.replace("/./", "/")
    return t


def _has_overrides_token(t):
    return "overrides" in t or "overri~" in t


def names_override_path(text, cwd=None):
    """True when normalised text names hooks/sessions/<id>/overrides (or its 8.3 alias),
    directly, or relatively while the payload cwd is under hooks/sessions."""
    if not isinstance(text, str) or not text:
        return False
    t = _norm(text)
    i = t.find("hooks/sessions")
    if i != -1 and _has_overrides_token(t[i:]):
        return True
    if isinstance(cwd, str) and cwd and "hooks/sessions" in _norm(cwd + "/"):
        return _has_overrides_token(t)
    return False


_SESSION_STORE_MARKERS = ("claude-code-sessions",)
_BASH_ONLY_MARKERS = ("ora_session_store_dirs", "claude_code_entrypoint")


def names_session_store(text, bash=False):
    if not isinstance(text, str) or not text:
        return False
    t = text.replace("\\", "/").lower()
    if any(m in t for m in _SESSION_STORE_MARKERS):
        return True
    return bash and any(m in t for m in _BASH_ONLY_MARKERS)


def _desktop_entrypoint():
    ep = os.environ.get("CLAUDE_CODE_ENTRYPOINT") or ""
    return ep.strip().lower().startswith("claude-desktop")


def _main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    sid = payload.get("session_id")
    sid = sid if isinstance(sid, str) else ""
    cwd = payload.get("cwd")
    import tool_call_paths as tcp  # noqa: E402
    hit = False
    if tcp.is_shell_tool(tool_name):
        sa = tcp.shell_analysis(tool_name, tool_input)
        texts = [sa.command] if sa else []
        if isinstance(tool_input, dict):
            texts.append(tool_input.get("command"))
        hit = any(names_override_path(x, cwd) or names_session_store(x, bash=True) for x in texts)
    else:
        texts = []
        for target in tcp.write_targets(tool_name, tool_input):
            texts.extend((target.raw_path, target.path))
        if isinstance(tool_input, dict):
            texts.extend(tool_input.get(f) for f in
                         ("file_path", "path", "notebook_path", "output_path"))
        hit = any(names_override_path(x, cwd) or names_session_store(x) for x in texts)
    if not hit:
        sys.exit(0)
    import session_kind  # noqa: E402
    kind, _task_id, evidence = session_kind.classify(sid)
    if kind == session_kind.UNKNOWN and _desktop_entrypoint():
        kind = session_kind.SCHEDULED
        evidence = "desktop entrypoint, session kind unknown: fail closed (%s)" % evidence
    if kind != session_kind.SCHEDULED:
        sys.exit(0)
    sys.stderr.write(
        "BLOCKED (override-mint-guard): this %s call writes or names an override-token path "
        "(hooks/sessions/<id>/overrides/) or the Desktop session store "
        "(claude-code-sessions, ORA_SESSION_STORE_DIRS, CLAUDE_CODE_ENTRYPOINT) in a "
        "scheduled/headless session (%s). Override "
        "tokens stand in for Gabriel's in-turn yes and may be created only in a live "
        "session. Stop and report what needed approval.\n" % (tool_name, evidence))
    sys.exit(2)


def main():
    try:
        _main()
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 -- dispatcher-chain guard: never brick a session
        sys.exit(0)


if __name__ == "__main__":
    main()
