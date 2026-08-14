"""Tests for lint-config-guard.py -- fail-closed guard against silent edits to
EXISTING lint/format/typecheck config files in oxford-command-center (OI-148).

Written FIRST (TDD). Drives the real hook as a subprocess with real PreToolUse
payloads, isolated from the live machine via TEST-SEAM env vars:
  ORA_LINT_CONFIG_GUARD_ROOT  -> a temp stand-in for C:/Users/Owner/oxford-command-center
  ORA_OVERRIDE_SESSIONS_DIR   -> a temp stand-in for hooks/sessions (lib seam)

Contract:
  * exit 2 + stderr reason == block; exit 0 == allow
  * protects EXISTING config files only -- first-time creation is allowed
  * fail-closed on a stat error that is NOT "file does not exist" (permission
    error, root path component not a directory, etc.)
  * a valid allow-lint-config-write token (session-scoped, TTL'd) grants the write
  * worktree copies under <root>/.claude/worktrees/** are exempt
  * shell-text writers are caught best-effort (repo-name + basename markers), the
    same documented structural ceiling as every other shell-text guard here
  * any internal error / malformed payload fails OPEN

Run: python test-lint-config-guard.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "lint-config-guard.py")

SID = "test-session-0123456789abcdef"
DC = "mcp__Desktop_Commander__"

_failures = []
_total = 0


def check(name, cond, detail=""):
    global _total
    _total += 1
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


class Rig(object):
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="lcg-root-")
        self.sessions = tempfile.mkdtemp(prefix="lcg-sess-")

    def env(self, root=None):
        env = dict(os.environ)
        env["ORA_LINT_CONFIG_GUARD_ROOT"] = root if root is not None else self.root
        env["ORA_OVERRIDE_SESSIONS_DIR"] = self.sessions
        return env

    def run(self, payload, root=None, raw_stdin=None):
        data = raw_stdin if raw_stdin is not None else \
            json.dumps(payload).encode("utf-8")
        proc = subprocess.run([sys.executable, HOOK], input=data,
                              capture_output=True, env=self.env(root))
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), \
            proc.stderr.decode("utf-8", "replace")

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def touch(self, *parts):
        p = self.path(*parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("x")
        return p

    def mint_token(self, session_id=SID, scope="lint-config-write", age_seconds=0):
        d = os.path.join(self.sessions, session_id, "overrides")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "allow-lint-config-write")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("scope: %s\nsession: %s\nreason: test\n" % (scope, session_id))
        if age_seconds:
            t = time.time() - age_seconds
            os.utime(p, (t, t))
        return p


def payload(tool_name, tool_input, session_id=SID):
    return {"tool_name": tool_name, "tool_input": tool_input,
            "session_id": session_id}


def main():
    # ---- unrelated file: always allowed --------------------------------
    r = Rig()
    r.touch("src", "foo.ts")
    rc, out, err = r.run(payload("Edit", {
        "file_path": r.path("src", "foo.ts"), "old_string": "a", "new_string": "b"}))
    check("unrelated file allowed", rc == 0, "rc=%d err=%s" % (rc, err))

    # ---- protected filename that does not exist yet: first-create allowed
    r = Rig()
    rc, out, err = r.run(payload("Write", {
        "file_path": r.path("eslint.config.js"), "content": "export default []"}))
    check("first-time-create of eslint.config.js allowed", rc == 0,
          "rc=%d err=%s" % (rc, err))

    # ---- existing protected file, no token: blocked ---------------------
    for rel in ("eslint.config.js", "tsconfig.json", "tsconfig.node.json",
                "functions/tsconfig.json", "vitest.config.ts", ".prettierrc.json"):
        r = Rig()
        r.touch(*rel.split("/"))
        rc, out, err = r.run(payload("Edit", {
            "file_path": r.path(*rel.split("/")),
            "old_string": "a", "new_string": "b"}))
        check("existing %s blocked with no token" % rel, rc == 2 and rel in err,
              "rc=%d err=%s" % (rc, err))

    # ---- existing protected file, valid token: allowed -------------------
    r = Rig()
    r.touch("eslint.config.js")
    r.mint_token()
    rc, out, err = r.run(payload("Edit", {
        "file_path": r.path("eslint.config.js"),
        "old_string": "a", "new_string": "b"}))
    check("existing eslint.config.js allowed with valid token", rc == 0,
          "rc=%d err=%s" % (rc, err))

    # ---- expired token: blocked ------------------------------------------
    r = Rig()
    r.touch("tsconfig.json")
    r.mint_token(age_seconds=3700)  # TTL is 3600s
    rc, out, err = r.run(payload("Edit", {
        "file_path": r.path("tsconfig.json"), "old_string": "a", "new_string": "b"}))
    check("expired token blocked", rc == 2, "rc=%d err=%s" % (rc, err))

    # ---- wrong-session token: blocked -------------------------------------
    r = Rig()
    r.touch("tsconfig.json")
    r.mint_token(session_id="other-session-0123456789")
    rc, out, err = r.run(payload("Edit", {
        "file_path": r.path("tsconfig.json"), "old_string": "a", "new_string": "b"}))
    check("wrong-session token blocked", rc == 2, "rc=%d err=%s" % (rc, err))

    # ---- worktree copy: exempt even without token -------------------------
    r = Rig()
    r.touch(".claude", "worktrees", "somebranch", "eslint.config.js")
    rc, out, err = r.run(payload("Edit", {
        "file_path": r.path(".claude", "worktrees", "somebranch", "eslint.config.js"),
        "old_string": "a", "new_string": "b"}))
    check("worktree copy exempt", rc == 0, "rc=%d err=%s" % (rc, err))

    # ---- DC write_file / edit_block shapes also covered --------------------
    r = Rig()
    r.touch("eslint.config.js")
    rc, out, err = r.run(payload(DC + "write_file", {
        "path": r.path("eslint.config.js"), "content": "x"}))
    check("DC write_file on existing config blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    r = Rig()
    r.touch("tsconfig.json")
    rc, out, err = r.run(payload(DC + "edit_block", {
        "file_path": r.path("tsconfig.json"), "old_string": "a", "new_string": "b"}))
    check("DC edit_block on existing config blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    # ---- DC move_file / write_pdf shapes (independent-review finding: these
    # were reachable in code via write_targets() but never ROUTED by the old
    # settings.json matcher, which enumerated exact tool names rather than the
    # MCP-suffix pattern -- fixed 2026-08-13. Direct coverage here so a future
    # settings.json regression is at least suspectable from this suite even
    # though it can't see the routing itself, only the hook's own behavior) ---
    r = Rig()
    r.touch("eslint.config.js")
    rc, out, err = r.run(payload(DC + "move_file", {
        "source": r.path("staged.js"), "destination": r.path("eslint.config.js")}))
    check("DC move_file onto existing config blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    r = Rig()
    r.touch("eslint.config.js")
    rc, out, err = r.run(payload(DC + "write_pdf", {
        "path": r.path("eslint.config.js"), "content": "x"}))
    check("DC write_pdf onto existing config blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    # ---- shell write hit: blocked (repo-name + basename marker) -----------
    r = Rig()
    r.touch("eslint.config.js")
    rc, out, err = r.run(payload("Bash", {
        "command": "sed -i 's/error/off/' oxford-command-center/eslint.config.js"}))
    check("shell sed -i on eslint.config.js blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    # ---- quote-split bypass: blocked (independent-review finding, 2026-08-13) --
    # Two adjacent quoted/unquoted fragments the shell concatenates into ONE
    # argument must not defeat a bare substring check. Empirically confirmed
    # live (pre-fix) to actually rewrite a file in a sandbox.
    r = Rig()
    r.touch("tsconfig.json")
    rc, out, err = r.run(payload("Bash", {
        "command": "cd oxford-command-center; sed -i 's/x/y/' ts''config.json"}))
    check("quote-split bypass (ts''config.json) blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    r = Rig()
    r.touch("tsconfig.json")
    rc, out, err = r.run(payload("Bash", {
        "command": "sed -i 's/x/y/' oxford-command-center/ts^config.json"}))
    check("caret-escape bypass (ts^config.json) blocked", rc == 2,
          "rc=%d err=%s" % (rc, err))

    # ---- heredoc body mention: allowed (the guard's own verification commands
    # must not false-block on their own output/log naming a protected file) ----
    r = Rig()
    rc, out, err = r.run(payload("Bash", {
        "command": "cat <<'EOF' > notes.md\nfixed tsconfig.json strictness in "
                   "oxford-command-center\nEOF"}))
    check("heredoc body mention allowed (not a real write target)", rc == 0,
          "rc=%d err=%s" % (rc, err))

    # ---- shell worktree exemption: allowed even without token --------------
    r = Rig()
    rc, out, err = r.run(payload("Bash", {
        "command": "sed -i 's/x/y/' oxford-command-center/.claude/worktrees/"
                   "wt1/tsconfig.json"}))
    check("shell command targeting a worktree copy is exempt", rc == 0,
          "rc=%d err=%s" % (rc, err))

    # ---- worktree exemption is TOKEN-scoped, not whole-command (independent-
    # review finding #2, 2026-08-13): a bare mention of .claude/worktrees
    # anywhere in the command must not silence an UNRELATED real write
    # elsewhere in the same command.
    r = Rig()
    rc, out, err = r.run(payload("Bash", {
        "command": "echo 'see .claude/worktrees for context'; "
                   "sed -i 's/strict/off/' oxford-command-center/tsconfig.json"}))
    check("worktree mention does not silence an unrelated real write "
          "elsewhere in the command", rc == 2, "rc=%d err=%s" % (rc, err))

    # ---- shell read-only mention: allowed (no write indicator) ------------
    r = Rig()
    rc, out, err = r.run(payload("Bash", {
        "command": "cat oxford-command-center/eslint.config.js"}))
    check("shell read-only cat allowed", rc == 0, "rc=%d err=%s" % (rc, err))

    # ---- path through a non-directory component: PLATFORM NOTE -- on
    # Windows, os.stat() raises FileNotFoundError (WinError 3) for this shape,
    # not a distinct "not a directory" error the way POSIX's NotADirectoryError
    # would -- empirically confirmed, not assumed. That is CORRECT to allow
    # here: there is genuinely no config file at that resolved path (the
    # parent isn't even a real directory), so there is nothing to protect and
    # no quality-bar loophole is possible. This collapses into the same
    # "absent" branch as first-time-create, which is why the hook's _file_state
    # docstring calls out this platform behavior rather than assuming POSIX
    # semantics. The genuinely-untestable-portably branch is 'unknown' (a real
    # PermissionError from a restrictive ACL) -- exercised by code review of
    # _file_state, not a subprocess test, since Windows ACLs cannot be
    # reliably manipulated from a test harness without admin rights.
    r = Rig()
    fake_root = tempfile.mktemp(prefix="lcg-not-a-dir-")
    with open(fake_root, "w", encoding="utf-8") as fh:
        fh.write("x")
    rc, out, err = r.run(payload("Edit", {
        "file_path": os.path.join(fake_root, "eslint.config.js"),
        "old_string": "a", "new_string": "b"}), root=fake_root)
    check("path through non-directory component allowed (no real file there)",
          rc == 0, "rc=%d err=%s" % (rc, err))
    os.remove(fake_root)

    # ---- malformed payload: fails open -------------------------------------
    r = Rig()
    rc, out, err = r.run(None, raw_stdin=b"not json")
    check("malformed JSON fails open", rc == 0, "rc=%d err=%s" % (rc, err))

    rc, out, err = r.run(None, raw_stdin=b"[]")
    check("non-dict JSON fails open", rc == 0, "rc=%d err=%s" % (rc, err))

    print("\n%d failed / %d total" % (len(_failures), _total))
    if _failures:
        print("FAILURES: " + ", ".join(_failures))
        sys.exit(1)
    if _total == 0:
        print("NO TESTS RAN -- this is a failure, not a pass")
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
