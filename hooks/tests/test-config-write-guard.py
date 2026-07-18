"""Tests for config-write-guard.py -- the hard write-gate over the governance layer
(hooks/**, settings.json, CLAUDE.md, scheduled-task registries) plus the chip
claim-lock over coordination paths (handoffs/**, workflows/**).

Written FIRST (TDD). Drives the real hook as a subprocess with real PreToolUse
payloads, fully isolated from the live machine via the documented TEST-SEAM env vars:
  ORA_CONFIG_GUARD_ROOT      -> a temp stand-in for C:/Users/Owner/.claude
  ORA_OVERRIDE_SESSIONS_DIR  -> a temp stand-in for hooks/sessions (lib seam)
  ORA_CHIP_CLAIMS_LOG        -> a temp stand-in for chip-claims.log

Contract:
  * exit 2 + stderr reason == block; exit 0 == allow (PreToolUse convention --
    exit 1 would be NON-blocking, see reference_pretooluse_vs_git_hook_exit_codes.md)
  * governance writes need a valid allow-config-write token (hooks/lib/
    override_tokens.py mechanism -- session-scoped, content-bound, TTL'd)
  * hooks/sessions/** and hooks/state/** are EXEMPT (self-deadlock defense: the
    override token itself lives under hooks/sessions/)
  * claim-lock FAILS OPEN on a missing or malformed chip-claims.log (ratified
    doctrine: feedback_fail_open_over_mutex_for_fleet_gates)
  * any internal error fails OPEN (a bug here must never brick a session --
    cf. feedback_confidentiality_guard_selfdeadlock.md)

Run: python test-config-write-guard.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "config-write-guard.py")

SID = "test-session-0123456789abcdef"
DC = "mcp__Desktop_Commander__"
DCP = "mcp__plugin_desktop-commander_desktop-commander__"

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


class Rig(object):
    """One isolated guard environment: temp root + temp sessions dir + temp log."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="cwg-root-")
        self.sessions = tempfile.mkdtemp(prefix="cwg-sess-")
        self.log = os.path.join(tempfile.mkdtemp(prefix="cwg-log-"), "chip-claims.log")

    def env(self):
        env = dict(os.environ)
        env["ORA_CONFIG_GUARD_ROOT"] = self.root
        env["ORA_OVERRIDE_SESSIONS_DIR"] = self.sessions
        env["ORA_CHIP_CLAIMS_LOG"] = self.log
        return env

    def run(self, payload, raw_stdin=None):
        data = raw_stdin if raw_stdin is not None else \
            json.dumps(payload).encode("utf-8")
        proc = subprocess.run([sys.executable, HOOK], input=data,
                              capture_output=True, env=self.env())
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), \
            proc.stderr.decode("utf-8", "replace")

    def path(self, *parts):
        return os.path.join(self.root, *parts).replace("\\", "/")

    def mint_token(self, session_id=SID, scope="config-write", age_seconds=0):
        d = os.path.join(self.sessions, session_id, "overrides")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "allow-config-write")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("scope: %s\nsession: %s\nreason: test\n" % (scope, session_id))
        if age_seconds:
            t = time.time() - age_seconds
            os.utime(p, (t, t))
        return p

    def write_log(self, text):
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write(text)

    def write_log_bytes(self, data):
        with open(self.log, "wb") as fh:
            fh.write(data)


def payload(tool_name, tool_input, session_id=SID):
    return {"session_id": session_id, "tool_name": tool_name,
            "tool_input": tool_input}


def now_iso(minutes_ago=0):
    dt = datetime.now(timezone.utc).astimezone() - timedelta(minutes=minutes_ago)
    return dt.isoformat(timespec="seconds")


# ------------------------------------------------------------ token gate: file tools
def test_blocks_hooks_write_without_token():
    r = Rig()
    rc, out, err = r.run(payload("Write", {"file_path": r.path("hooks", "x-guard.py"),
                                           "content": "x"}))
    check("Write to hooks/** without token -> block", rc == 2, "rc=%s err=%r" % (rc, err))
    check("block message names the token mechanism",
          "allow-config-write" in err and "scope" in err, "err=%r" % err)


def test_blocks_settings_claude_md_registry_without_token():
    r = Rig()
    cases = [
        ("settings.json", r.path("settings.json")),
        ("settings.local.json", r.path("settings.local.json")),
        ("CLAUDE.md", r.path("CLAUDE.md")),
        ("CC registry", "C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/"
                        "aaaa/bbbb/scheduled-tasks.json"),
        ("LAMS registry", "C:/Users/Owner/AppData/Roaming/Claude/"
                          "local-agent-mode-sessions/aaaa/bbbb/scheduled-tasks.json"),
    ]
    for label, p in cases:
        rc, out, err = r.run(payload("Write", {"file_path": p, "content": "x"}))
        check("Write to %s without token -> block" % label, rc == 2, "rc=%s" % rc)


def test_exempt_sessions_and_state_never_blocked():
    # SELF-DEADLOCK DEFENSE: the override token lives under hooks/sessions/ -- if
    # writing it were gated, no token could ever be created to satisfy the gate.
    r = Rig()
    for label, p in [
        ("hooks/sessions token write",
         r.path("hooks", "sessions", SID, "overrides", "allow-config-write")),
        ("hooks/sessions plan-gate override",
         r.path("hooks", "sessions", SID, "override")),
        ("hooks/state breadcrumb", r.path("hooks", "state", "roster.json")),
    ]:
        rc, out, err = r.run(payload("Write", {"file_path": p, "content": "x"}))
        check("%s -> allow (exempt)" % label, rc == 0, "rc=%s err=%r" % (rc, err))


def test_allows_unrelated_and_worktree_paths():
    r = Rig()
    for label, p in [
        ("ordinary file", r.path("outputs", "note.md")),
        ("root sibling of CLAUDE.md", r.path("CLAUDE.md.backup-notes", "x.md")),
        ("worktree hooks copy",
         r.path(".claude", "worktrees", "wg-2026-07-18", "hooks", "x-guard.py")),
        ("worktree settings copy",
         r.path(".claude", "worktrees", "wg-2026-07-18", "settings.json")),
        ("unrelated scheduled-tasks.json",
         "C:/Users/Owner/some-project/config/scheduled-tasks.json"),
    ]:
        rc, out, err = r.run(payload("Write", {"file_path": p, "content": "x"}))
        check("%s -> allow" % label, rc == 0, "rc=%s err=%r" % (rc, err))


def test_valid_token_allows_and_is_multi_use():
    r = Rig()
    r.mint_token()
    p = r.path("hooks", "x-guard.py")
    rc1, _, err1 = r.run(payload("Write", {"file_path": p, "content": "x"}))
    rc2, _, err2 = r.run(payload("Edit", {"file_path": r.path("settings.json"),
                                          "old_string": "a", "new_string": "b"}))
    check("valid token -> hooks write allowed", rc1 == 0, "err=%r" % err1)
    check("token is multi-use (second gated write also allowed)", rc2 == 0,
          "err=%r" % err2)


def test_bad_tokens_still_block():
    cases = [
        ("wrong scope", dict(scope="website-write")),
        ("wrong session", dict(session_id="some-other-session")),
        ("stale (aged past TTL)", dict(age_seconds=7200)),
    ]
    for label, kwargs in cases:
        r = Rig()
        r.mint_token(**kwargs)
        rc, _, err = r.run(payload("Write", {"file_path": r.path("hooks", "g.py"),
                                             "content": "x"}))
        check("%s token -> still blocks" % label, rc == 2, "rc=%s" % rc)


def test_missing_session_id_fails_closed_for_governance():
    r = Rig()
    rc, _, err = r.run(payload("Write", {"file_path": r.path("hooks", "g.py"),
                                         "content": "x"}, session_id=""))
    check("no session_id -> governance write still blocks (no token reachable)",
          rc == 2, "rc=%s" % rc)


# ------------------------------------------------------------ token gate: DC shapes
def test_blocks_dc_shapes():
    r = Rig()
    hooks_target = r.path("hooks", "g.py")
    cases = [
        ("DC write_file (path arg)", DC + "write_file",
         {"path": hooks_target, "content": "x"}),
        ("DC-plugin write_file (path arg)", DCP + "write_file",
         {"path": hooks_target, "content": "x"}),
        ("DC write_file (file_path arg)", DC + "write_file",
         {"file_path": hooks_target, "content": "x"}),
        ("DC edit_block", DC + "edit_block",
         {"file_path": r.path("settings.json"), "old_string": "a", "new_string": "b"}),
        ("DC-plugin edit_block", DCP + "edit_block",
         {"file_path": r.path("CLAUDE.md"), "old_string": "a", "new_string": "b"}),
        ("NotebookEdit", "NotebookEdit", {"notebook_path": r.path("hooks", "g.ipynb")}),
        ("DC move_file onto settings.json", DC + "move_file",
         {"source": r.path("outputs", "x.json"), "destination": r.path("settings.json")}),
        ("DC move_file of a hook away", DC + "move_file",
         {"source": hooks_target, "destination": r.path("outputs", "g.py")}),
        ("DC-plugin move_file onto a hook", DCP + "move_file",
         {"source": r.path("outputs", "x.py"), "destination": hooks_target}),
        ("decoy double-field write_file (innocent file_path, gated path)",
         DC + "write_file",
         {"file_path": r.path("outputs", "innocent.txt"), "path": hooks_target,
          "content": "x"}),
    ]
    for label, tool, ti in cases:
        rc, _, err = r.run(payload(tool, ti))
        check("%s without token -> block" % label, rc == 2, "rc=%s" % rc)


def test_dc_move_unrelated_allows():
    r = Rig()
    rc, _, err = r.run(payload(DC + "move_file",
                               {"source": r.path("outputs", "a.txt"),
                                "destination": r.path("outputs", "b.txt")}))
    check("DC move_file of unrelated files -> allow", rc == 0, "err=%r" % err)


# ------------------------------------------------------------ token gate: shell
def test_blocks_shell_writes_into_governance_paths():
    r = Rig()
    cases = [
        ("Bash redirect into hooks",
         "Bash", 'echo x > "%s"' % r.path("hooks", "g.py")),
        ("Bash copy onto settings.json",
         "Bash", 'cp evil.json "%s"' % r.path("settings.json")),
        ("Bash rm of a hook",
         "Bash", 'rm "%s"' % r.path("hooks", "confidentiality-guard.py")),
        ("Bash tilde-form hooks write",
         "Bash", "echo x > ~/.claude/hooks/g.py"),
        ("DC start_process redirect into hooks",
         DC + "start_process", 'cmd /c echo x > "%s"' % r.path("hooks", "g.py")),
        ("DC-plugin start_process onto CLAUDE.md",
         DCP + "start_process", 'cmd /c copy z.md "%s"' % r.path("CLAUDE.md")),
        ("DC interact_with_process REPL write into hooks",
         DC + "interact_with_process", None),  # input-based, built below
    ]
    for label, tool, cmd in cases:
        if cmd is None:
            ti = {"pid": 1, "input": "open(r'%s','w').write('x')"
                                     % r.path("hooks", "g.py")}
        else:
            ti = {"command": cmd}
        rc, _, err = r.run(payload(tool, ti))
        check("%s without token -> block" % label, rc == 2, "rc=%s err=%r" % (rc, err))


def test_shell_reads_and_unrelated_writes_allow():
    r = Rig()
    cases = [
        ("Bash read of a hook", 'cat "%s"' % r.path("hooks", "g.py")),
        ("Bash read with 2>&1", 'ls "%s" 2>&1' % r.path("hooks")),
        ("Bash grep with null redirect",
         'grep -r x "%s" 2>/dev/null' % r.path("hooks")),
        ("Bash unrelated write", 'echo x > "%s"' % r.path("outputs", "n.md")),
        ("Bash write into a worktree hooks copy",
         'echo x > "%s"' % r.path(".claude", "worktrees", "wg", "hooks", "g.py")),
        ("Bash token write into hooks/sessions (exempt)",
         'echo "scope: config-write" > "%s"'
         % r.path("hooks", "sessions", SID, "overrides", "allow-config-write")),
        ("Bash python running a hook TEST (read/exec, no write verb)",
         'python "%s"' % r.path("hooks", "tests", "test-config-write-guard.py")),
    ]
    for label, cmd in cases:
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("%s -> allow" % label, rc == 0, "rc=%s err=%r" % (rc, err))


def test_shell_write_with_token_allows():
    r = Rig()
    r.mint_token()
    rc, _, err = r.run(payload("Bash", {"command": 'echo x > "%s"'
                                                   % r.path("hooks", "g.py")}))
    check("Bash governance write with valid token -> allow", rc == 0, "err=%r" % err)


def test_shell_unicode_evasion_blocked():
    r = Rig()
    # ZWSP (U+200B) inserted inside the path must not evade marker matching
    # (autonomy-gate Round 3 precedent, 2026-07-17)
    cmd = ('echo x > "'
           + r.path("hooks", "g.py").replace("hooks", "ho​oks") + '"')
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("ZWSP-in-path shell write -> still blocked", rc == 2, "rc=%s" % rc)


# ------------------------------------------------------------ claim-lock
CLAIM_HEADER = "# ORA chip claim-lock\n"


def test_claim_lock_fails_open_when_log_missing_or_malformed():
    for label, setup in [
        ("missing log", lambda r: None),
        ("empty file", lambda r: r.write_log("")),
        ("truncated line", lambda r: r.write_log(CLAIM_HEADER + "2026-07-18T10:00")),
        ("non-UTF8 bytes", lambda r: r.write_log_bytes(b"\xff\xfe\x00garbage\x81")),
    ]:
        r = Rig()
        setup(r)
        rc, _, err = r.run(payload("Write", {"file_path": r.path("handoffs", "h.md"),
                                             "content": "x"}))
        check("claim-lock %s -> FAIL OPEN (allow)" % label, rc == 0,
              "rc=%s err=%r" % (rc, err))


def test_claim_lock_blocks_without_open_claim():
    r = Rig()
    r.write_log(CLAIM_HEADER +
                "%s | CLAIMED | some-other-chip | Code/otherses1\n" % now_iso(10))
    rc, _, err = r.run(payload("Write", {"file_path": r.path("handoffs", "h.md"),
                                         "content": "x"}))
    check("handoffs write with no claim for THIS session -> block", rc == 2,
          "rc=%s err=%r" % (rc, err))
    check("claim block message points at chip-claims.log",
          "chip-claims.log" in err and "CLAIMED" in err, "err=%r" % err)


def test_claim_lock_allows_with_open_claim():
    r = Rig()
    r.write_log(CLAIM_HEADER +
                "%s | CLAIMED | my-task | Code/%s\n" % (now_iso(5), SID[:8]))
    for label, tool, ti in [
        ("handoffs Write", "Write",
         {"file_path": r.path("handoffs", "h.md"), "content": "x"}),
        ("workflows Write", "Write",
         {"file_path": r.path("workflows", "w.js"), "content": "x"}),
        ("handoffs DC write_file", DC + "write_file",
         {"path": r.path("handoffs", "h.md"), "content": "x"}),
        ("handoffs Bash write", "Bash",
         {"command": 'echo x > "%s"' % r.path("handoffs", "h.md")}),
    ]:
        rc, _, err = r.run(payload(tool, ti))
        check("%s with open claim (8-char id match) -> allow" % label, rc == 0,
              "rc=%s err=%r" % (rc, err))


def test_claim_lock_closed_or_stale_claims_block():
    p = None
    for label, log in [
        ("claim later marked DONE",
         "%s | CLAIMED | my-task | Code/%s\n%s | DONE | my-task | Code/%s\n"
         % (now_iso(30), SID[:8], now_iso(1), SID[:8])),
        ("claim later ABORTED",
         "%s | CLAIMED | my-task | Code/%s\n%s | ABORTED gone | my-task | Code/%s\n"
         % (now_iso(30), SID[:8], now_iso(1), SID[:8])),
        ("stale claim (>60 min, no heartbeat)",
         "%s | CLAIMED | my-task | Code/%s\n" % (now_iso(90), SID[:8])),
    ]:
        r = Rig()
        r.write_log(CLAIM_HEADER + log)
        rc, _, err = r.run(payload("Write", {"file_path": r.path("handoffs", "h.md"),
                                             "content": "x"}))
        check("%s -> block" % label, rc == 2, "rc=%s" % rc)


def test_claim_lock_heartbeat_refreshes_staleness():
    r = Rig()
    r.write_log(CLAIM_HEADER +
                "%s | CLAIMED | my-task | Code/%s\n"
                "%s | HEARTBEAT | my-task | Code/%s\n"
                % (now_iso(120), SID[:8], now_iso(10), SID[:8]))
    rc, _, err = r.run(payload("Write", {"file_path": r.path("handoffs", "h.md"),
                                         "content": "x"}))
    check("old claim + fresh HEARTBEAT -> allow", rc == 0, "rc=%s err=%r" % (rc, err))


def test_claim_lock_missing_session_id_fails_open():
    r = Rig()
    r.write_log(CLAIM_HEADER +
                "%s | CLAIMED | my-task | Code/whoever\n" % now_iso(5))
    rc, _, err = r.run(payload("Write", {"file_path": r.path("handoffs", "h.md"),
                                         "content": "x"}, session_id=""))
    check("claim-lock with no session_id -> FAIL OPEN (cannot attribute)", rc == 0,
          "rc=%s err=%r" % (rc, err))


def test_claim_log_itself_is_never_gated():
    # appending CLAIMED/HEARTBEAT lines must never require a claim (deadlock)
    r = Rig()
    r.write_log(CLAIM_HEADER)
    rc, _, err = r.run(payload("Bash", {"command": 'echo "x | CLAIMED | t | s" >> "%s"'
                                                   % r.log.replace("\\", "/")}))
    check("appending to chip-claims.log -> allow (never self-gated)", rc == 0,
          "rc=%s err=%r" % (rc, err))


# ------------------------------------------------------------ fail-open robustness
def test_fail_open_on_garbage_input():
    r = Rig()
    for label, raw in [
        ("empty stdin", b""),
        ("malformed json", b"{not json"),
        ("non-dict payload", b'"just a string"'),
        ("non-UTF8 stdin bytes", b"\xff\xfe{\x00}"),
        ("tool_input not a dict",
         json.dumps({"session_id": SID, "tool_name": "Write",
                     "tool_input": "nope"}).encode("utf-8")),
    ]:
        rc, out, err = r.run(None, raw_stdin=raw)
        check("%s -> fail open (exit 0)" % label, rc == 0, "rc=%s err=%r" % (rc, err))


def test_exit_code_is_never_one():
    # exit 1 from a PreToolUse hook is NON-blocking (tool proceeds) -- this guard
    # must only ever use 0 (allow) or 2 (block).
    r = Rig()
    probes = [
        (None, b"\x81\x82\x83"),
        (payload("Write", {"file_path": r.path("hooks", "g.py"), "content": "x"}), None),
        (payload("Write", {"file_path": r.path("outputs", "x.md"), "content": "x"}), None),
    ]
    ok = True
    for p, raw in probes:
        rc, _, _ = r.run(p, raw_stdin=raw)
        if rc not in (0, 2):
            ok = False
    check("exit codes are only ever 0 or 2", ok)


if __name__ == "__main__":
    test_blocks_hooks_write_without_token()
    test_blocks_settings_claude_md_registry_without_token()
    test_exempt_sessions_and_state_never_blocked()
    test_allows_unrelated_and_worktree_paths()
    test_valid_token_allows_and_is_multi_use()
    test_bad_tokens_still_block()
    test_missing_session_id_fails_closed_for_governance()
    test_blocks_dc_shapes()
    test_dc_move_unrelated_allows()
    test_blocks_shell_writes_into_governance_paths()
    test_shell_reads_and_unrelated_writes_allow()
    test_shell_write_with_token_allows()
    test_shell_unicode_evasion_blocked()
    test_claim_lock_fails_open_when_log_missing_or_malformed()
    test_claim_lock_blocks_without_open_claim()
    test_claim_lock_allows_with_open_claim()
    test_claim_lock_closed_or_stale_claims_block()
    test_claim_lock_heartbeat_refreshes_staleness()
    test_claim_lock_missing_session_id_fails_open()
    test_claim_log_itself_is_never_gated()
    test_fail_open_on_garbage_input()
    test_exit_code_is_never_one()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL config-write-guard tests passed.")
    sys.exit(0)
