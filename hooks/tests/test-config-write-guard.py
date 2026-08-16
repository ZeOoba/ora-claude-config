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

    def mint_token(self, session_id=SID, scope="config-write", age_seconds=0,
                   filename=None):
        # filename defaults to allow-config-write and is NOT derived from scope:
        # several tests deliberately write a WRONG scope into the RIGHT file to
        # prove scope mismatch is rejected. A second tier passes it explicitly.
        d = os.path.join(self.sessions, session_id, "overrides")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, filename or "allow-config-write")
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


def test_blocks_destructive_recursive_deletes():
    """The gap PR #112's detector was built for and never actually closed.

    Two classes only -- catastrophic scope and business-data surfaces. Anything
    reproducible stays allowed; see test_allows_routine_recursive_deletes."""
    r = Rig()
    cases = [
        ("rm -rf ~/Documents/deals", "business-data surface"),
        ("rm -rf ~/Desktop/x", "business-data surface"),
        ('rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Deals"',
         "business-data surface"),
        ('rm -r "C:/Users/Owner/OneDrive - Oxford Capital Partners"',
         "business-data surface"),
        ("rm -rf .", "catastrophic scope"),
        ("rm -rf /", "catastrophic scope"),
        ("rm -rf ~", "catastrophic scope"),
        ("rm -rf C:\\", "catastrophic scope"),
    ]
    for cmd, reason in cases:
        rc, out, err = r.run(payload("Bash", {"command": cmd}))
        check("destructive delete blocked: %r" % cmd, rc == 2,
              "rc=%s err=%r" % (rc, err))
        check("names the reason (%s): %r" % (reason, cmd), reason in err,
              "err=%r" % err)
        check("offers the archive-instead alternative: %r" % cmd,
              "/archive/" in err and "allow-destructive-delete" in err,
              "err=%r" % err)


def test_delete_bypasses_found_by_independent_review():
    """Every concrete bypass the 2026-08-16 independent review demonstrated.

    Each of these reached exit 0 against the first cut of this guard. They are
    pinned as inputs, not as reasoning, so a future refactor that reintroduces
    any of them fails here rather than in production."""
    r = Rig()
    must_block = [
        # MAJOR 1 -- subshell/brace/substitution was a 1-char bypass.
        "(rm -rf ~/Documents/deals)",
        "{ rm -rf ~/Documents/deals; }",
        "$(rm -rf ~/Documents/deals)",
        # MAJOR 2 -- ephemeral leaf name inside a protected store.
        'rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Insurance/coverage"',
        'rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Deals/build"',
        'rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Deals/Target"',
        "rm -rf ~/Documents/out",
        "rm -rf ~/Desktop/tmp",
        # MAJOR 3 -- glob-tail spellings of an already-blocked scope.
        "rm -rf ./*",
        "rm -rf ${HOME}/*",
        # MAJOR 4 -- ancestor of every protected store.
        "rm -rf C:/Users/Owner",
        # --- second review pass, 2026-08-16 -------------------------------
        # MAJOR A: a trailing group delimiter glued onto the operand defeated
        # EVERY exact-match class. The first fix only ever tested the
        # business-data variant, which matches by SUBSTRING and so masked it.
        "(rm -rf /)", "(rm -rf .)", "(rm -rf ~)", "(rm -rf C:/)",
        "(rm -rf C:/Users/Owner)",
        "`rm -rf C:/Users/Owner`",
        "{ rm -rf ~/Documents/deals; }",
        # MAJOR B: a redirect BEFORE the operand dropped the operand entirely.
        "rm -rf 2>/dev/null ~/Documents/deals",
        "rm -rf 2> /dev/null ~/Documents/deals",
        "rm -rf >/dev/null ~/Documents/deals",
        # MAJOR C: the dotglob spelling wipes ~/.ssh, ~/.gitconfig, ~/.claude.
        "rm -rf ~/.*",
        # --- third review pass, 2026-08-16 --------------------------------
        # MAJOR: an fd-duplication redirect BEFORE the operand. The `&` inside
        # `2>&1` was read as a command separator, severing rm from its path.
        # The round-2 tests used only `&`-free redirect forms, which is exactly
        # why they stayed green while this leaked.
        "rm -rf 2>&1 ~/Documents/deals",
        "rm -rf 1>&2 ~/Documents/deals",
        "rm -rf >&2 ~/Documents/deals",
        "rm -rf &>/dev/null ~/Documents/deals",
        "rm -rf &> /dev/null ~/Documents/deals",
        "rm -rf 2>&1 C:/Users/Owner",        # ancestor class
        "rm -rf 2>&1 /",                     # catastrophic class
        # MINOR: ${IFS} evasion -- the detector advertised seeing through this
        # and fired, but extraction yielded a junk operand the guard could not
        # resolve, so the guard allowed what the detector had flagged.
        "rm${IFS}-rf${IFS}/",
        "rm${IFS}-rf${IFS}~/Documents/deals",
        "rm${IFS}-rf${IFS}C:/Users/Owner",
    ]
    for cmd in must_block:
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("review bypass now blocked: %r" % cmd, rc == 2,
              "rc=%s err=%r" % (rc, err))

    # MAJOR 5 -- correct shell quoting must NOT be blocked. A false positive here
    # forces a broader override token, which is strictly worse than the gap.
    must_allow = [
        'rm -rf "$HOME"/scratch/build',
        'rm -rf ~/"my folder"/node_modules',
        'rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Cowork OS/foo"',
        # The delimiter strip must be UNBALANCED-only: a real directory whose
        # name legitimately contains brackets must survive the operand intact.
        'rm -rf "build/Closing (final)"',
        "rm -rf build > log.txt",          # redirect AFTER operand, still fine
        "rm -rf 2>/dev/null node_modules",  # redirect before a routine target
        "rm -rf C:/Users/OwnerBackup",      # sibling prefix, not the profile
        # fd-dup stripping must not turn routine deletes into blocks, and a real
        # `&&` chain must still separate commands rather than being eaten.
        "rm -rf 2>&1 node_modules",
        "rm -rf build 2>&1",
        "ls && rm -rf build",
        "rm -rf dist && echo done",
    ]
    for cmd in must_allow:
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("correct quoting not falsely blocked: %r" % cmd, rc == 0,
              "rc=%s err=%r" % (rc, err))


def test_claude_workspace_exemption_is_actually_exercised():
    """The Claude_Workspace exemption, tested on a NON-ephemeral leaf.

    The original test used `.../Claude_Workspace/tmp`, which passed via the
    ephemeral-basename rule -- so the exemption it claimed to cover was never
    exercised (independent review 2026-08-16, MINOR 7)."""
    r = Rig()
    cmd = ('rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/'
           'Claude_Workspace/01_Workspace/sessiondata"')
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("Claude_Workspace exempt on a non-ephemeral leaf", rc == 0,
          "rc=%s err=%r" % (rc, err))


def test_allows_routine_recursive_deletes():
    """A guard people route around protects nothing.

    Reproducible build output, agent working surface (Hard Invariant 5 names
    ~/.claude and Claude_Workspace as free surface), and the command-position
    false positives that PR #112's own SCOPE note called "the operationally
    damaging class" must all sail through untouched."""
    r = Rig()
    allowed = [
        "rm -rf node_modules", "rm -rf build", "rm -rf dist", "rm -rf .venv",
        "rm -rf __pycache__", "rm -rf .cache",
        "rm -rf C:/Users/Owner/.claude/.claude-worktrees/foo",
        'rm -rf "C:/Users/Owner/OneDrive - Oxford Capital Partners/Claude_Workspace/tmp"',
        "git rm -r --cached node_modules",   # unstages; never touches disk
        "grep rm -r .", "# rm -rf /tmp/x", "echo rm -rf x",
        "rm file.txt", "ls -R", "docker run --rm img",
    ]
    for cmd in allowed:
        rc, out, err = r.run(payload("Bash", {"command": cmd}))
        check("routine command allowed: %r" % cmd, rc == 0,
              "rc=%s err=%r" % (rc, err))


def test_destructive_delete_token_allows():
    """An explicitly approved deletion clears, on its OWN tier -- a
    config-write token must not silently authorize a tree deletion."""
    r = Rig()
    cmd = "rm -rf ~/Documents/deals"
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("blocked without a token", rc == 2, "rc=%s" % rc)
    r.mint_token(scope="config-write")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("a config-write token does NOT authorize a delete", rc == 2,
          "rc=%s err=%r" % (rc, err))
    r.mint_token(scope="destructive-delete", filename="allow-destructive-delete")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("a destructive-delete token allows it", rc == 0,
          "rc=%s err=%r" % (rc, err))


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


# REFUTE round 3 (2026-07-22): Win32's CreateFile silently strips trailing
# '.'/' ' characters from a path's final component -- "CLAUDE.md." and
# "CLAUDE.md" are the SAME file on disk, but os.path.realpath() does NOT
# replicate that stripping, so a raw string comparison sees them as
# different. Confirmed this ALREADY bypassed the untouched, currently-live
# hook for a plain structured Write call (file_path="<root>/CLAUDE.md.") --
# a pre-existing gap in _norm()/_classify() far broader than this session's
# shell-matcher scope. Fixed once, in _norm() (the single shared
# normalizer), so both the pre-existing structured-file-tool gap and the
# shell-text regression it caused via _shell_absolute_hits are closed
# together.
def test_trailing_dot_exact_match_targets_still_block_structured_tools():
    r = Rig()
    for label, p in [
        ("CLAUDE.md trailing dot", r.path("CLAUDE.md") + "."),
        ("CLAUDE.md trailing dots+space", r.path("CLAUDE.md") + ".. "),
        ("settings.json trailing dot", r.path("settings.json") + "."),
        ("settings.local.json trailing dot", r.path("settings.local.json") + "."),
    ]:
        rc, _, err = r.run(payload("Write", {"file_path": p, "content": "x"}))
        check("Write to %s -> still blocks" % label, rc == 2,
              "rc=%s err=%r" % (rc, err))


def test_trailing_dot_exact_match_targets_still_block_shell():
    r = Rig()
    for label, target_suffix in [
        ("CLAUDE.md trailing dot", "CLAUDE.md."),
        ("settings.json trailing dot", "settings.json."),
        ("settings.local.json trailing dot", "settings.local.json."),
    ]:
        cmd = "cmd /c copy /y x.json %s/%s" % (r.path(), target_suffix)
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("shell write to %s -> still blocks" % label, rc == 2,
              "rc=%s cmd=%r err=%r" % (rc, cmd, err))


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
        ("hooks/active-work claim broadcast (2026-07-26 fix)",
         r.path("hooks", "active-work", "hooks-override-auth.json")),
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
        ("Bash claim_work.py claim (writes hooks/active-work, 2026-07-26 fix)",
         'python "%s" claim hooks-override-auth "test claim"'
         % r.path("hooks", "lib", "claim_work.py")),
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


def test_quote_split_and_caret_escape_bypasses_closed():
    """2026-08-05: the two bypasses left open in
    reference_config_write_guard_quote_split_gap.md, each live-proven ALLOW
    against the current guard before the _shell_variants fix.

    (1) QUOTE-SPLIT: quote chars break a path into fragments the matcher never
        sees as one token, while the shell strips them before the FS does.
    (2) CARET-ESCAPE: cmd.exe removes `^` at parse time, so `CLA^UDE.md` reaches
        disk as CLAUDE.md while the matcher only ever sees the caret form."""
    r = Rig()
    root = r.path().rstrip("/\\")
    leaks = [
        ('cp x.json "%s"/hooks/evil.py' % root, "quote-split mid-path"),
        ('cp a.json "%s"/settings.json' % root, "quote-split settings.json"),
        ("cp x.json '%s'/settings.json" % root, "single-quote split"),
        ('echo x > %s/CLA^UDE.md' % root, "caret in CLAUDE.md"),
        ('cp a %s/set^tings.json' % root, "caret in settings.json"),
        ('cp x "%s/hoo^ks/evil.py"' % root, "caret inside quotes"),
        ('echo x > %s/ho"o"ks/evil.py' % root, "quotes inside a segment"),
        # every segment quoted separately -- built from the RIG's root, not a
        # hardcoded real path, or it silently tests nothing.
        ('echo x > %s/"hooks"/"e.py"'
         % "/".join('"%s"' % seg for seg in root.split("/")),
         "every segment separately quoted"),
    ]
    for cmd, label in leaks:
        rc, _, _ = r.run(payload("Bash", {"command": cmd}))
        check("bypass closed: %s -> blocked" % label, rc == 2, "rc=%s" % rc)


def test_quote_caret_normalization_does_not_overblock():
    """The union-only variant scan must not turn benign commands into blocks --
    this is the guard against repeating the 2026-08-03 direction-of-error
    mistake, where a boundary fix changed classification of unrelated shapes."""
    r = Rig()
    benign = [
        ('echo "^_^" > C:/tmp/face.txt', "caret art in an unrelated echo"),
        ('grep -E "^hooks" C:/tmp/list.txt', "regex anchor, not an escape"),
        ('cp a.md "C:/Users/Owner/OneDrive - Oxford Capital Partners"/n.md',
         "quoted path with spaces, unrelated root"),
        ('cp x "C:/Users/Owner/ora-skills"/daily-brief/SKILL.md',
         "quoted ora-skills path is not governance"),
    ]
    for cmd, label in benign:
        rc, _, _ = r.run(payload("Bash", {"command": cmd}))
        check("no over-block: %s -> allowed" % label, rc == 0, "rc=%s" % rc)


# ------------------------------------------------------------ REFUTE regressions
def test_refute_shape_bypasses_closed():
    """2026-07-18 adversarial REFUTE pass: five live-proven bypasses (each reached
    exit 0 against a blocked control before the fix). Locked in as regressions."""
    r = Rig()
    hooks_t = r.path("hooks", "g.py")
    cases = [
        ("DC write_pdf onto a hook", DC + "write_pdf",
         {"path": hooks_t, "content": "x"}),
        ("excel MCP writer onto settings.json (generic path-field scan)",
         "mcp__excel__write_data_to_excel",
         {"filepath": r.path("settings.json"), "data": [["x"]]}),
        ("hypothetical third-prefix DC write_file (suffix-family matching)",
         "mcp__desktop-commander-v2__write_file",
         {"path": hooks_t, "content": "x"}),
        ("git checkout rewriting the live checkout", "Bash",
         {"command": "git -C ~/.claude checkout main -- hooks/"}),
        ("PowerShell Move-Item onto live settings.json", "Bash",
         {"command": "Move-Item evil.json ~/.claude/settings.json"}),
    ]
    for label, tool, ti in cases:
        rc, _, err = r.run(payload(tool, ti))
        check("REFUTE: %s -> block" % label, rc == 2, "rc=%s" % rc)
    # controls: the breadth must not swallow legitimate work
    allows = [
        ("read-only git on the live checkout", "Bash",
         {"command": "git -C ~/.claude log --oneline -- hooks/"}),
        ("mutating git inside an isolated worktree (full path named)", "Bash",
         {"command": "git -C %s checkout -- hooks/g.py"
          % r.path(".claude", "worktrees", "wg")}),
        ("excel writer on an ordinary workbook", "mcp__excel__write_data_to_excel",
         {"filepath": r.path("outputs", "model.xlsx"), "data": [["x"]]}),
    ]
    for label, tool, ti in allows:
        rc, _, err = r.run(payload(tool, ti))
        check("REFUTE control: %s -> allow" % label, rc == 0,
              "rc=%s err=%r" % (rc, err))


# ------------------------------------------------------------ boundary-bug regressions
# BUG (2026-07-21, oxford-command-center worktree session, fix-refute-workflow-em-dash):
# classify_shell's marker matching was pure lexical substring scanning with no
# path-segment boundaries and no notion of "this occurrence sits inside a
# provably-different absolute path." Three confirmed false positives:
#   1. ".claude" (a root_mentions entry) matched as a raw substring INSIDE the
#      unrelated ".claude-worktrees" directory name (this environment's actual
#      repo-local worktree convention, dash-joined -- NOT the nested
#      "<root>/worktrees" form the module already exempts).
#   2. The generic ".claude/workflows" / ".claude/hooks" markers fired on a
#      fully drive-qualified absolute path under a DIFFERENT repo entirely
#      (oxford-command-center's own repo-local .claude/workflows/), which can
#      never resolve to the live root regardless of shell cwd.
#   3. classify_shell scanned an ENTIRE heredoc body (commit-message prose,
#      written to a temp file via `cat <<'EOF' > msg.txt`) for markers, even
#      though that text is DATA being written into an unrelated file, not a
#      path any command argument names.
def test_shell_dot_claude_worktrees_dash_suffix_not_matched():
    r = Rig()
    # ".claude-worktrees" is a sibling dir name, not a "worktrees" subdir OF
    # .claude -- the existing exemption list only covers the latter. The bare
    # ".claude" substring must not fire just because it's a text-prefix of
    # ".claude-worktrees".
    cmd = ("git checkout -- C:/Users/Owner/oxford-command-center/"
           ".claude-worktrees/fix-refute-workflow-em-dash/foo.py")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("git checkout in an unrelated .claude-worktrees dir -> allow", rc == 0,
          "rc=%s err=%r" % (rc, err))


def test_shell_dot_claude_worktrees_regression_real_root_still_blocks():
    # The boundary fix must not weaken the real case it exists to catch.
    r = Rig()
    cmd = 'git checkout -- "%s"' % r.path("hooks", "confidentiality-guard.py")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("git checkout of a real live hooks/** file -> still blocks", rc == 2,
          "rc=%s" % rc)
    cmd2 = "git checkout -- ~/.claude/hooks/confidentiality-guard.py"
    rc2, _, err2 = r.run(payload("Bash", {"command": cmd2}))
    check("git checkout via tilde-form live root -> still blocks", rc2 == 2,
          "rc=%s" % rc2)


# CODE REVIEW FINDING (2026-07-22, review of commit 569ef4b): _ABS_PATH_TOKEN_RE
# stopped only at whitespace/quotes/<>/| -- not at shell-sequencing/substitution
# metacharacters (; & ` $ ( )). A command/path glued directly onto an absolute
# governance path via one of those (`cp x.py <root>/CLAUDE.md;echo pwned`)
# produced a CORRUPTED token ("...claude.md;echo") that (a) failed _classify's
# EXACT-EQUALITY check for the three single-file targets (settings.json,
# settings.local.json, CLAUDE.md -- unlike hooks/**/handoffs/**/workflows/**,
# which are prefix-matched and so tolerate a corrupted trailing suffix), and
# (b) was then SKIPPED by _marker_matches on the (wrong, in this case)
# assumption that _shell_absolute_hits already handled it. Confirmed via `git
# show` on the pre-session base SHA that the ORIGINAL bare-substring matcher
# correctly blocked all of these -- this was a genuine regression introduced
# by the absolute-token-classification redesign, not a pre-existing gap.
def test_shell_metachar_glued_exact_match_targets_still_block():
    r = Rig()
    for label, suffix in [
        ("semicolon", ';echo pwned'),
        ("ampersand", '&echo pwned'),
        ("closing paren", ')echo pwned'),
        ("dollar-paren command substitution", '$(whoami)'),
        ("backtick command substitution", '`whoami`'),
    ]:
        for target, marker in [
            ("CLAUDE.md", "CLAUDE.md"),
            ("settings.json", "settings.json"),
            ("settings.local.json", "settings.local.json"),
        ]:
            # UNQUOTED path -- the metacharacter must be glued directly onto
            # the token with nothing (no quote) delimiting it, matching the
            # actual reported repro shape.
            cmd = 'cp x.json %s%s' % (r.path(target), suffix)
            rc, _, err = r.run(payload("Bash", {"command": cmd}))
            check("%s glued onto %s -> still blocks" % (label, marker), rc == 2,
                  "rc=%s cmd=%r err=%r" % (rc, cmd, err))


# NOTE: ".claude/workflows" is a CLAIM-lock marker, not a governance one -- the
# claim-lock fails OPEN on a missing/malformed chip-claims.log (ratified
# doctrine), so a Rig() with no log at all would "pass" these regardless of
# classify_shell's marker logic. Write a log with a claim that is provably NOT
# this session's (same shape as test_claim_lock_blocks_without_open_claim) so
# these tests actually exercise the marker-matching fix, not fail-open.
def _deny_claim_rig():
    r = Rig()
    r.write_log(CLAIM_HEADER +
                "%s | CLAIMED | some-other-chip | Code/otherses1\n" % now_iso(5))
    return r


def test_shell_absolute_unrelated_repo_dot_claude_workflows_not_matched():
    r = _deny_claim_rig()
    # Fully drive-qualified absolute path under a DIFFERENT repo's own
    # repo-local .claude/workflows/ -- cannot be the live root under any cwd.
    cmd = ('cp x.json "C:/Users/Owner/oxford-command-center/.claude/'
           'workflows/foo.json"')
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("write into an unrelated repo's own .claude/workflows/ -> allow",
          rc == 0, "rc=%s err=%r" % (rc, err))


def test_shell_absolute_unrelated_repo_regression_ambiguous_forms_still_block():
    # Bare relative and tilde forms remain genuinely ambiguous (depend on an
    # unknown shell cwd) -- the absolute-path carve-out must NOT extend to them.
    for label, cmd in [
        ("bare relative .claude/workflows",
         'cp x.json ".claude/workflows/foo.json"'),
        ("tilde-form ~/.claude/workflows",
         'cp x.json "~/.claude/workflows/foo.json"'),
    ]:
        r = _deny_claim_rig()
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("%s -> still blocks" % label, rc == 2, "rc=%s err=%r" % (rc, err))
    # true live-root workflows/** via an absolute path that matches guard_root()
    r = _deny_claim_rig()
    cmd = 'cp x.json "%s"' % r.path("workflows", "foo.json")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("true live-root workflows/** (absolute, matches guard root) -> "
          "still blocks", rc == 2, "rc=%s err=%r" % (rc, err))


def test_shell_heredoc_body_prose_not_matched():
    r = Rig()
    cmd = ('cat <<\'EOF\' > msg.txt\n'
           'Fix workflow script; .gitattributes already references '
           '.claude/hooks/session-start.sh for line-ending handling\n'
           'EOF\n'
           'git commit -F msg.txt')
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("hooks/** merely mentioned in heredoc'd commit-message prose -> allow",
          rc == 0, "rc=%s err=%r" % (rc, err))


def test_shell_heredoc_regression_real_write_outside_body_still_blocks():
    r = Rig()
    # The redirect TARGET (outside the heredoc body) is a real write into
    # hooks/** and must still block -- heredoc-body stripping must not blind
    # the guard to the surrounding command structure.
    cmd = ('cat <<\'EOF\' > "%s"\n'
           'just some ordinary content\n'
           'EOF' % r.path("hooks", "evil.py"))
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("heredoc redirected INTO hooks/** (target outside body) -> still blocks",
          rc == 2, "rc=%s" % rc)


def test_shell_open_readonly_end_to_end_allowed():
    r = Rig()
    # End-to-end repro of the exact reported pattern: a read-only open() whose
    # path text happens to contain the generic ".claude/workflows" marker.
    cmd = ("python3 -c \"open(r'C:/Users/Owner/oxford-command-center/.claude/"
           "workflows/foo.json','rb').read()\"")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("read-only open() of an unrelated repo path -> allow", rc == 0,
          "rc=%s err=%r" % (rc, err))


def test_shell_open_write_mode_end_to_end_still_blocks():
    r = Rig()
    cmd = "python3 -c \"open(r'%s','w').write('x')\"" % r.path("hooks", "g.py")
    rc, _, err = r.run(payload("Bash", {"command": cmd}))
    check("write-mode open() into real hooks/** -> still blocks", rc == 2,
          "rc=%s" % rc)


# REFUTE 2026-07-21 (adversarial pass on the boundary fix above): the
# absolute-path-divergence exemption in _marker_reaches_live_root did a raw
# STRING-PREFIX comparison, which a lexical `..` segment defeats -- a path
# through a nonexistent intermediate directory that RESOLVES onto the live
# root (Windows/cmd collapses ".." without requiring the intermediate
# directory to exist -- confirmed empirically) looked like "a different
# absolute root" and was wrongly exempted. Locked in as a regression: any
# occurrence that lexically normalizes onto the live root must still block,
# no token required.
def test_shell_dotdot_traversal_onto_live_root_still_blocks():
    r = Rig()
    for label, cmd in [
        ("dotdot through nonexistent dir onto hooks/**",
         'cmd /c echo evil > "%s"' %
         r.path("some_nonexistent_dir_xyz", "..", "hooks", "evil.py")),
        ("dotdot through nonexistent dir onto settings.json",
         'cmd /c echo {} > "%s"' % r.path("a", "b", "..", "..", "settings.json")),
        ("double-dotdot onto CLAUDE.md",
         'cmd /c echo x > "%s"' %
         r.path("x", "y", "z", "..", "..", "..", "CLAUDE.md")),
    ]:
        rc, _, err = r.run(payload("Bash", {"command": cmd}))
        check("%s -> still blocks" % label, rc == 2, "rc=%s err=%r" % (rc, err))
    # the divergence exemption itself must still work for a GENUINE different
    # root, even with an incidental ".." inside it (regression control;
    # workflows/** is a CLAIM marker so use a deny-claim rig, not fail-open)
    r2 = _deny_claim_rig()
    rc2, _, err2 = r2.run(payload("Bash", {
        "command": 'cp x.json "C:/Users/Owner/oxford-command-center/sub/'
                   '../.claude/workflows/foo.json"'}))
    # this dotdot resolves to oxford-command-center/.claude/workflows/foo.json
    # -- still a different repo entirely, must still be exempt
    check("dotdot resolving within a genuinely different repo -> still allow",
          rc2 == 0, "rc=%s err=%r" % (rc2, err2))


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


def test_block_message_covers_the_governance_cli_invocation_case():
    # WHY (2026-08-12, live-hit twice in one session). The block message offered
    # exactly two exits: "it was a READ -> use Read/Grep/Glob" and "it's a REAL edit
    # -> do it in a worktree". Neither fits the case that actually keeps firing --
    # INVOKING a governance CLI whose writes land in paths this guard already
    # EXEMPTS. eos-review-gate's own blocking text tells the operator to run
    # `eos-review-gate.py --record ... --notes "<prose>"`; review prose routinely
    # carries an ASCII arrow ("199/204 -> 204/204"), and ">" is a write indicator,
    # so the sanctioned way to clear the review gate is blocked by this one. The
    # only exit the message then named was minting a 60-min multi-use
    # governance-WIDE token -- the same "false positive forces a strictly broader
    # privilege" security regression the 2026-08-03 word-anchoring fix in
    # tool_call_paths.py was written to kill (see its _BOUNDED_VERBS note, which
    # fixed the `--model ` -> "del " half of this same deadlock).
    #
    # The arrow itself CANNOT simply be un-armed: `echo x ->f` is a real redirect
    # that truncates f in bash, so ">" stays an indicator and the fix belongs in
    # the guidance, not the matcher.
    r = Rig()
    gate = r.path("hooks", "eos-review-gate.py")
    rc, _, err = r.run(payload("Bash", {
        "command": 'python "%s" --record --verdict approved --model claude-fable-5 '
                   '--notes "199/204 -> 204/204"' % gate}))
    check("record-with-arrow-in-notes still blocks (matcher unchanged)", rc == 2,
          "rc=%s" % rc)
    check("block message flags the governance-CLI invocation case",
          "GOVERNANCE-TOOL INVOCATION" in err, "err=%r" % err)

    # SCOPE THE ASSERTIONS TO THE NEW PARAGRAPH, NOT TO ALL OF stderr. The message
    # ECHOES the blocked command back on its `target:` line, so a bare `"->" in err`
    # or `"worktree" in err` is satisfied by the probe's own input (and "worktree"
    # was already in the pre-existing REAL-edit paragraph) -- both passed against
    # the un-fixed message when this test was first run RED. One paragraph per
    # line, matching the rest of the block text.
    guidance = next((l for l in err.splitlines()
                     if "GOVERNANCE-TOOL INVOCATION" in l), "")
    check("...naming the exempt destinations such tools actually write to",
          "hooks/sessions" in guidance and "hooks/active-work" in guidance,
          "guidance=%r" % guidance)
    check("...and explaining the prose write indicator, arrow included",
          "ASCII arrow" in guidance, "guidance=%r" % guidance)
    check("...and why the arrow stays armed rather than being exempted",
          "redirect" in guidance, "guidance=%r" % guidance)
    check("...and pointing at the worktree copy of the TOOL as the re-run route",
          "worktree" in guidance, "guidance=%r" % guidance)
    check("...and steering off the token, which is the over-broad exit here",
          "do NOT mint" in guidance, "guidance=%r" % guidance)

    # Second live shape: a governance-path READ compounded with an unrelated write
    # (cleaning up a scratchpad file). The matcher sees the whole command, so the
    # actionable advice is to split it -- not to mint anything.
    rc, _, err = r.run(payload("Bash", {
        "command": 'python "%s" release s; rm -f /tmp/scratch.py'
                   % r.path("hooks", "lib", "claim_work.py")}))
    check("read compounded with an unrelated write still blocks", rc == 2,
          "rc=%s" % rc)
    guidance = next((l for l in err.splitlines()
                     if "GOVERNANCE-TOOL INVOCATION" in l), "")
    check("...and the message says to split the command up",
          "split" in guidance, "guidance=%r" % guidance)

    # The pre-existing exits must survive the addition -- this is guidance ADDED
    # alongside them, not a replacement.
    check("the READ guidance is still present", "IF THIS WAS A READ" in err,
          "err=%r" % err)
    check("the REAL-edit worktree guidance is still present",
          "Preferred path for a REAL edit" in err, "err=%r" % err)
    check("the token mechanism is still named", "allow-config-write" in err,
          "err=%r" % err)


def test_governance_cli_guidance_is_advice_only_not_an_exemption():
    # The guidance must not have quietly become a matcher carve-out: the same
    # commands still BLOCK (asserted above), and a real write dressed up as a
    # governance-CLI invocation still blocks too.
    r = Rig()
    rc, _, err = r.run(payload("Bash", {
        "command": 'python "%s" --record --notes "x" > "%s"'
                   % (r.path("hooks", "eos-review-gate.py"),
                      r.path("hooks", "evil.py"))}))
    check("a real redirect into hooks/ alongside --record still blocks", rc == 2,
          "rc=%s err=%r" % (rc, err))


if __name__ == "__main__":
    test_blocks_hooks_write_without_token()
    test_blocks_settings_claude_md_registry_without_token()
    test_trailing_dot_exact_match_targets_still_block_structured_tools()
    test_trailing_dot_exact_match_targets_still_block_shell()
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
    test_quote_split_and_caret_escape_bypasses_closed()
    test_quote_caret_normalization_does_not_overblock()
    test_refute_shape_bypasses_closed()
    test_shell_dot_claude_worktrees_dash_suffix_not_matched()
    test_shell_dot_claude_worktrees_regression_real_root_still_blocks()
    test_shell_absolute_unrelated_repo_dot_claude_workflows_not_matched()
    test_shell_absolute_unrelated_repo_regression_ambiguous_forms_still_block()
    test_shell_heredoc_body_prose_not_matched()
    test_shell_heredoc_regression_real_write_outside_body_still_blocks()
    test_shell_open_readonly_end_to_end_allowed()
    test_shell_open_write_mode_end_to_end_still_blocks()
    test_shell_dotdot_traversal_onto_live_root_still_blocks()
    test_shell_metachar_glued_exact_match_targets_still_block()
    test_claim_lock_fails_open_when_log_missing_or_malformed()
    test_claim_lock_blocks_without_open_claim()
    test_claim_lock_allows_with_open_claim()
    test_claim_lock_closed_or_stale_claims_block()
    test_claim_lock_heartbeat_refreshes_staleness()
    test_claim_lock_missing_session_id_fails_open()
    test_claim_log_itself_is_never_gated()
    test_fail_open_on_garbage_input()
    test_exit_code_is_never_one()
    test_block_message_covers_the_governance_cli_invocation_case()
    test_governance_cli_guidance_is_advice_only_not_an_exemption()
    test_blocks_destructive_recursive_deletes()
    test_delete_bypasses_found_by_independent_review()
    test_claude_workspace_exemption_is_actually_exercised()
    test_allows_routine_recursive_deletes()
    test_destructive_delete_token_allows()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL config-write-guard tests passed.")
    sys.exit(0)
