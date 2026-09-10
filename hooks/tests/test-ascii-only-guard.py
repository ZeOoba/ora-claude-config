"""Tests for ascii-only-guard.py -- the PreToolUse gate that stops a write from
introducing non-ASCII bytes into a file whose module docstring declares itself
ASCII-only.

Written FIRST (TDD), and run against the real hook as a subprocess with real
PreToolUse payloads.

WHY THE CONVENTION IS LOAD-BEARING (not style): reference_powershell_git_show_
corrupts_nonascii.md measured `& git show "HEAD:path"` in an unattended
`powershell.exe -NoProfile` run on this machine decoding child stdout as IBM437,
silently mangling every non-ASCII byte; reference_windows_hook_stdin_cp1252_
encoding_gap.md documents the stdin twin. 64 of this repo's 258 tracked .py
files declare "ASCII-only" in their module docstring and, before this guard,
NOTHING enforced it -- six were measurably in violation at c27d3b6. Three are
repaired on this branch; the other three live in hooks/tests/ and carry U+200B,
U+FF20 and U+202E as deliberate ADVERSARIAL FIXTURES (the homoglyph, zero-width
and RTL-override strings fed to config-write-guard, ora-autonomy-gate and the
path canonicalizer), so --repair rightly refuses them and the fix there is to
escape the fixture or qualify the claim -- see the guard's own docstring.

PAYLOAD SHAPES ARE VERIFIED AGAINST REAL TRANSCRIPTS, NOT ASSUMED.
feedback_fixture_shaped_tests_certify_dead_branches.md records eos-telemetry.py
matching tool name "Task" with a fixture that encoded "Task" -- both wrong, the
real tool is "Agent" (0 vs 672 occurrences) -- a green test over a dead branch
for months. So every tool name and field name asserted below was first counted
across the 1628 real transcripts in C:/Users/Owner/.claude/projects/**/*.jsonl:

    Write                                 2386 calls; keys file_path, content
    Edit                                  5398 calls; keys file_path, old_string,
                                          new_string (new_string ABSENT on 3 --
                                          hence the missing-field allow test)
    mcp__Desktop_Commander__edit_block      30 calls; keys file_path, old_string,
                                          new_string
    mcp__Desktop_Commander__write_file       4 calls; keys path, content
                                          -- NOTE: "path", NOT "file_path". A
                                          fixture assuming file_path here would
                                          have certified a dead branch.
    MultiEdit                                0 calls  -> NO branch, and a test
    NotebookEdit                             0 calls  -> below pins that absence.

THE DISPATCHER PATH IS TESTED SEPARATELY, AND THAT IS NOT REDUNDANT. Tests 1-10
below spawn the guard as a SUBPROCESS, which is how the harness ran it before
2026-08-05 and is no longer how it actually runs on Edit/Write: settings.json
now routes that matcher through hooks/pretooluse-dispatcher.py, which imports
each guard and calls its main() IN-PROCESS, deriving the exit code ONLY from
`except SystemExit`. A guard that signals a block by `return 2` from main()
instead of sys.exit(2) is therefore INVISIBLE to the dispatcher -- rc stays 0,
the message prints, and the write proceeds. That is not hypothetical: session
9ca9fdea shipped exactly that guard with 14 green subprocess-spawning tests;
only a dispatcher-path test caught it. Test 11 is that test.

CONTRACT:
  * exit 0 == allow, exit 2 + stderr == block. NEVER exit 1 (non-blocking error:
    the tool call would PROCEED, silently disabling the gate) -- see
    reference_pretooluse_vs_git_hook_exit_codes.md.
  * FAIL OPEN BY CONSTRUCTION. Blocks only on THREE affirmative signals:
    (a) the target exists and its MODULE DOCSTRING declares ASCII-only, AND
    (b) the post-write content demonstrably carries a codepoint > 127, AND
    (c) both were read reliably and unambiguously.
    Any missing, unreadable, undecodable, unparseable or ambiguous signal ->
    ALLOW. cf. feedback_confidentiality_guard_selfdeadlock.md, where a
    fail-CLOSED guard bricked Write/Edit/Bash machine-wide.
  * an allow-ascii-only-write override token (hooks/lib/override_tokens.py, the
    shared session-scoped contract) permits an otherwise-blocked write.

Run: python test-ascii-only-guard.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "ascii-only-guard.py")

SID = "test-session-ascii-0123456789"
DC = "mcp__Desktop_Commander__"

# Built from escapes on purpose: this test file must itself be ASCII-only, and it
# is one of the fixtures in test_guard_source_passes_its_own_check.
EM_DASH = "\u2014"
ARROW = "\u2192"
GE = "\u2265"
LE = "\u2264"
MIDDOT = "\u00b7"
BOM = "\ufeff"

ASCII_ONLY_MODULE = '"""A fixture module.\n\nStdlib only. ASCII-only. Windows (`python`).\n"""\nX = 1\n'
PLAIN_MODULE = '"""A fixture module with no such promise.\n\nStdlib only. Windows (`python`).\n"""\nX = 1\n'
# The phrase appears, but in a COMMENT -- not the module docstring. Not a signal.
COMMENT_ONLY_MODULE = '# ASCII-only. Windows (`python`).\nX = 1\n'
NO_DOCSTRING_MODULE = 'X = 1  # ASCII-only\n'
SYNTAX_ERROR_MODULE = '"""Broken. ASCII-only."""\ndef (:\n'

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


class Rig(object):
    """One isolated guard environment: a temp workspace + a temp sessions dir."""

    def __init__(self):
        self.work = tempfile.mkdtemp(prefix="aog-work-")
        self.sessions = tempfile.mkdtemp(prefix="aog-sess-")

    def env(self):
        env = dict(os.environ)
        # Documented TEST SEAM of hooks/lib/override_tokens.py. Never set in
        # settings.json or any scheduled task: it redirects a security gate's
        # override lookup to an arbitrary directory.
        env["ORA_OVERRIDE_SESSIONS_DIR"] = self.sessions
        return env

    def run(self, payload, raw_stdin=None):
        data = raw_stdin if raw_stdin is not None else \
            json.dumps(payload).encode("utf-8")
        proc = subprocess.run([sys.executable, HOOK], input=data,
                              capture_output=True, env=self.env())
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), \
            proc.stderr.decode("utf-8", "replace")

    def write_file(self, name, text):
        p = os.path.join(self.work, name)
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return p.replace("\\", "/")

    def write_bytes(self, name, raw):
        p = os.path.join(self.work, name)
        with open(p, "wb") as fh:
            fh.write(raw)
        return p.replace("\\", "/")

    def mint_token(self, session_id=SID, scope="ascii-only-write",
                   filename="allow-ascii-only-write"):
        d = os.path.join(self.sessions, session_id, "overrides")
        if not os.path.isdir(d):
            os.makedirs(d)
        p = os.path.join(d, filename)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("scope: %s\nsession: %s\nreason: test\n" % (scope, session_id))
        return p

    def cleanup(self):
        for d in (self.work, self.sessions):
            shutil.rmtree(d, ignore_errors=True)


def write_payload(path, content, session_id=SID):
    """A real Write PreToolUse payload. Field names verified: 2386/2386 real
    Write calls carry exactly {file_path, content}."""
    return {"session_id": session_id, "cwd": os.getcwd(), "tool_name": "Write",
            "tool_input": {"file_path": path, "content": content}}


def edit_payload(path, new_string, old_string="X = 1", session_id=SID,
                 tool_name="Edit"):
    """A real Edit PreToolUse payload. Field names verified: 5398/5398 real Edit
    calls carry file_path + old_string; 5395 also carry new_string."""
    return {"session_id": session_id, "cwd": os.getcwd(), "tool_name": tool_name,
            "tool_input": {"file_path": path, "old_string": old_string,
                           "new_string": new_string}}


# ---------------------------------------------------------------- 1. the block
def test_blocks_write_introducing_non_ascii(rig):
    p = rig.write_file("declared.py", ASCII_ONLY_MODULE)
    rc, _, err = rig.run(write_payload(p, ASCII_ONLY_MODULE + "Y = 'a %s b'\n" % EM_DASH))
    check("1 blocks Write introducing non-ASCII into an ASCII-only file",
          rc == 2, "rc=%r err=%r" % (rc, err[:200]))
    check("1a block names the guard", "ascii-only-guard" in err, err[:200])
    check("1b block reports a byte offset", "offset" in err.lower(), err[:300])
    check("1c block names the U+2014 codepoint", "U+2014" in err, err[:400])
    check("1d block names the ASCII replacement", "--" in err, err[:400])
    check("1e block names the override remediation",
          "allow-ascii-only-write" in err, err[:600])


def test_blocks_edit_introducing_non_ascii(rig):
    p = rig.write_file("declared_edit.py", ASCII_ONLY_MODULE)
    rc, _, err = rig.run(edit_payload(p, "Y = 'a %s b'" % ARROW))
    check("1f blocks an Edit whose new_string carries non-ASCII", rc == 2,
          "rc=%r" % rc)
    check("1g Edit block names U+2192 and its replacement",
          "U+2192" in err and "->" in err, err[:400])


def test_blocks_dc_edit_block(rig):
    """mcp__Desktop_Commander__edit_block: 30 real calls, keys file_path/
    old_string/new_string -- same shape as Edit, so it is covered."""
    p = rig.write_file("declared_dc.py", ASCII_ONLY_MODULE)
    rc, _, _ = rig.run(edit_payload(p, "Y = '%s'" % GE,
                                    tool_name=DC + "edit_block"))
    check("1h blocks Desktop Commander edit_block", rc == 2, "rc=%r" % rc)


def test_blocks_dc_write_file_path_field(rig):
    """mcp__Desktop_Commander__write_file: 4 real calls, keys `path` + `content`.
    The path field is `path`, NOT `file_path` -- asserting file_path here would
    have certified a branch the real tool never reaches."""
    p = rig.write_file("declared_dcw.py", ASCII_ONLY_MODULE)
    payload = {"session_id": SID, "cwd": os.getcwd(),
               "tool_name": DC + "write_file",
               "tool_input": {"path": p,
                              "content": ASCII_ONLY_MODULE + "Y = '%s'\n" % LE}}
    rc, _, err = rig.run(payload)
    check("1i blocks Desktop Commander write_file via its `path` field",
          rc == 2, "rc=%r err=%r" % (rc, err[:200]))
    check("1j and names <= as the replacement for U+2264",
          "U+2264" in err and "<=" in err, err[:400])


# ------------------------------------------------------ 2. no declaration -> allow
def test_allows_when_file_does_not_declare(rig):
    p = rig.write_file("plain.py", PLAIN_MODULE)
    rc, _, err = rig.run(write_payload(p, PLAIN_MODULE + "Y = '%s'\n" % EM_DASH))
    check("2 allows the same non-ASCII write into a file with no declaration",
          rc == 0, "rc=%r err=%r" % (rc, err[:200]))


def test_allows_declaration_outside_docstring(rig):
    """The signal is the MODULE DOCSTRING, not the file text. A comment saying
    ASCII-only is prose about the convention, not a declaration of it -- this
    guard's own remediation text would otherwise make every file mentioning it
    self-gating."""
    for name, src in (("comment.py", COMMENT_ONLY_MODULE),
                      ("nodoc.py", NO_DOCSTRING_MODULE)):
        p = rig.write_file(name, src)
        rc, _, _ = rig.run(write_payload(p, src + "Y = '%s'\n" % EM_DASH))
        check("2a allows when the phrase is outside the docstring (%s)" % name,
              rc == 0, "rc=%r" % rc)


def test_allows_scoped_ascii_only_output_claim(rig):
    """"ASCII-only OUTPUT" is a claim about what a script PRINTS to a cp1252
    console. It is NOT a claim about the source bytes, and conflating the two is
    not academic: maintenance/doctrine-integrity-probe.py, its test, and
    maintenance/test-governor-drift-probe.py all make the output claim, honor it
    (the probe ships an ascii_safe() that encodes output with backslashreplace),
    and MUST hold non-ASCII source literals to work -- governor-drift-probe.py's
    regexes contain literal U+00D7 and U+2264 character classes matched against
    real doctrine text, so its fixtures have to reproduce those bytes.

    A substring matcher reads all three as violating and would block every future
    edit to them forever. This test is the regression pin on that distinction.
    """
    scoped = ('"""A probe.\n\nPure stdlib. ASCII-only output '
              '(Windows cp1252 console).\n"""\nX = 1\n')
    p = rig.write_file("scoped.py", scoped)
    rc, _, err = rig.run(write_payload(p, scoped + "Y = '%s'\n" % GE))
    check("2c allows when the docstring claims ASCII-only OUTPUT, not source",
          rc == 0, "rc=%r err=%r" % (rc, err[:200]))

    # ...while the real source declaration on the very same file still blocks.
    src = ('"""A probe.\n\nStdlib only. ASCII-only. Windows (`python`).\n"""\n'
           "X = 1\n")
    p2 = rig.write_file("sourced.py", src)
    rc, _, _ = rig.run(write_payload(p2, src + "Y = '%s'\n" % GE))
    check("2d but the standalone source declaration still blocks", rc == 2,
          "rc=%r" % rc)


def test_allows_line_wrapped_scoped_claim(rig):
    """The ONE shape the noun lookahead actually defends.

    Measured during independent review (2026-09-10): deleting the lookahead
    changes the verdict on ZERO of the repo's tracked .py files -- every scoped
    claim in the corpus today is already dropped by the standalone-sentence
    assertion. The lookahead earns its place only when the docstring LINE-WRAPS
    between the phrase and its noun, because `$` is multiline in this pattern,
    so "ASCII-only\\noutput" would otherwise satisfy "next non-space char ends
    the clause" and read as a source declaration. Test 2c does NOT pin this (it
    passes with the lookahead removed); this one does.
    """
    wrapped = ('"""A probe.\n\nPure stdlib. ASCII-only\noutput (Windows cp1252 '
               'console).\n"""\nX = 1\n')
    p = rig.write_file("wrapped_scope.py", wrapped)
    rc, _, err = rig.run(write_payload(p, wrapped + "Y = '%s'\n" % GE))
    check("2f allows a LINE-WRAPPED 'ASCII-only\\noutput' scoped claim", rc == 0,
          "rc=%r err=%r" % (rc, err[:200]))


def test_negated_claim_is_not_a_declaration(rig):
    """A disclaimer is not a declaration. Reading "NOT ASCII-only." as a claim
    would BLOCK a file that had explicitly said the opposite -- a false BLOCK,
    the one direction this guard must never fail in. The shape is reachable:
    this guard's own block message invites people to write about the convention
    in their docstrings."""
    for label, doc in (
        ("not", '"""A module.\n\nThis file is NOT ASCII-only.\n"""\nX = 1\n'),
        ("never", '"""A module.\n\nThis is never ASCII-only.\n"""\nX = 1\n'),
    ):
        p = rig.write_file("negated_%s.py" % label, doc)
        rc, _, err = rig.run(write_payload(p, doc + "Y = '%s'\n" % EM_DASH))
        check("2g a negated claim (%s) is not a declaration" % label, rc == 0,
              "rc=%r err=%r" % (rc, err[:200]))


def test_punctuation_terminators_still_declare(rig):
    """`!` and `:` end a sentence just as `.` does; a declaration written with
    either must still gate, or the file is silently ungated."""
    for label, doc in (
        ("bang", '"""A module.\n\nStdlib only. ASCII-only!\n"""\nX = 1\n'),
        ("colon", '"""A module.\n\nASCII-only: no exceptions.\n"""\nX = 1\n'),
    ):
        p = rig.write_file("term_%s.py" % label, doc)
        rc, _, _ = rig.run(write_payload(p, doc + "Y = '%s'\n" % EM_DASH))
        check("2h a declaration terminated by %s still blocks" % label, rc == 2,
              "rc=%r" % rc)


def test_allows_prose_that_merely_names_the_convention(rig):
    """A docstring discussing the override token name, or the guard's own title
    line, must not read as a declaration."""
    for name, doc in (
        ("mentions_token.py",
         '"""Mints an allow-ascii-only-write token.\n\nStdlib only.\n"""\nX = 1\n'),
        ("title_line.py",
         '"""ASCII-only guard -- a hook.\n\nStdlib only.\n"""\nX = 1\n'),
    ):
        p = rig.write_file(name, doc)
        rc, _, _ = rig.run(write_payload(p, doc + "Y = '%s'\n" % EM_DASH))
        check("2e allows prose that merely names the convention (%s)" % name,
              rc == 0, "rc=%r" % rc)


def test_allows_non_python_target(rig):
    """A module docstring is a Python concept. A .md file carrying the words is
    prose -- not a declaration this guard can read reliably."""
    p = rig.write_file("notes.md", "ASCII-only. Windows.\n")
    rc, _, _ = rig.run(write_payload(p, "ASCII-only.\n%s\n" % EM_DASH))
    check("2b allows a non-.py target even when the words appear", rc == 0)


# ------------------------------------------------ 3. ASCII write -> allow
def test_allows_ascii_write_into_declared_file(rig):
    p = rig.write_file("declared_ok.py", ASCII_ONLY_MODULE)
    rc, _, err = rig.run(write_payload(p, ASCII_ONLY_MODULE + "Y = 'plain -- ok'\n"))
    check("3 allows a pure-ASCII write into an ASCII-only file", rc == 0,
          "rc=%r err=%r" % (rc, err[:200]))


# ------------------------------------------------ 4. missing target -> allow
def test_allows_when_target_absent(rig):
    p = os.path.join(rig.work, "brand-new.py").replace("\\", "/")
    rc, _, err = rig.run(write_payload(p, '"""New. ASCII-only."""\nY = "%s"\n' % EM_DASH))
    check("4 allows when the target does not exist (no declaration to read)",
          rc == 0, "rc=%r err=%r" % (rc, err[:200]))


# ------------------------------------- 5. unreadable / permission denied -> allow
def test_fails_open_on_unreadable_target(rig):
    """Three real unreadable shapes, all of which must ALLOW.

    (a) a DIRECTORY named *.py -- os.path.exists() is True but open() raises
        PermissionError (errno 13) on Windows: a genuine permission denial with
        no external tooling, so it is deterministic in every environment.
    (b) an ACL-denied file via icacls, the real permission-denied case. Skipped
        (not failed) if icacls is unavailable or the deny does not take.
    (c) undecodable bytes -- a target that is not valid UTF-8 cannot be parsed
        for a docstring, so the declaration signal is unreadable.
    """
    d = os.path.join(rig.work, "adir.py")
    os.makedirs(d)
    rc, _, err = rig.run(write_payload(d.replace("\\", "/"), "Y = '%s'\n" % EM_DASH))
    check("5a fails open when the target cannot be opened (PermissionError)",
          rc == 0, "rc=%r err=%r" % (rc, err[:200]))

    denied = rig.write_file("denied.py", ASCII_ONLY_MODULE)
    user = os.environ.get("USERNAME") or ""
    acl_ok = False
    if user:
        try:
            subprocess.run(["icacls", denied.replace("/", "\\"), "/deny",
                            "%s:(R)" % user], capture_output=True, timeout=30)
            try:
                open(denied, "rb").read()
            except PermissionError:
                acl_ok = True
            except OSError:
                acl_ok = True
        except Exception:
            acl_ok = False
    if acl_ok:
        try:
            rc, _, err = rig.run(write_payload(denied, "Y = '%s'\n" % EM_DASH))
            check("5b fails open on an ACL permission-denied target", rc == 0,
                  "rc=%r err=%r" % (rc, err[:200]))
        finally:
            subprocess.run(["icacls", denied.replace("/", "\\"), "/remove:d",
                            user], capture_output=True, timeout=30)
    else:
        print("SKIP 5b ACL deny unavailable in this environment "
              "(5a already proves the PermissionError path)")

    bad = rig.write_bytes("undecodable.py",
                          b'"""Fixture. ASCII-only."""\nX = "\xff\xfe raw"\n')
    rc, _, err = rig.run(write_payload(bad, "Y = '%s'\n" % EM_DASH))
    check("5c fails open on an undecodable target", rc == 0,
          "rc=%r err=%r" % (rc, err[:200]))

    p = rig.write_file("broken.py", SYNTAX_ERROR_MODULE)
    rc, _, err = rig.run(write_payload(p, "Y = '%s'\n" % EM_DASH))
    check("5d fails open when the target cannot be parsed for a docstring",
          rc == 0, "rc=%r err=%r" % (rc, err[:200]))


# ------------------------------------------- 6. malformed stdin -> allow
def test_fails_open_on_malformed_stdin(rig):
    for label, raw in (
        ("not json", b"this is not json at all"),
        ("empty", b""),
        ("truncated", b'{"tool_name": "Write", "tool_inp'),
        ("json list", b'[1, 2, 3]'),
        ("json string", b'"just a string"'),
        ("json null", b'null'),
        ("nul bytes", b'\x00\x00\x00'),
        ("invalid utf-8", b'{"tool_name": "\xff\xfe"}'),
    ):
        rc, _, err = rig.run(None, raw_stdin=raw)
        check("6 fails open on malformed stdin (%s)" % label, rc == 0,
              "rc=%r err=%r" % (rc, err[:160]))


def test_never_exits_one(rig):
    """exit 1 is the NON-blocking error code: the tool call proceeds and the gate
    is silently disabled. It must never be produced -- see
    reference_pretooluse_vs_git_hook_exit_codes.md."""
    seen = []
    p = rig.write_file("declared_rc.py", ASCII_ONLY_MODULE)
    for payload, raw in (
        (write_payload(p, "Y = '%s'\n" % EM_DASH), None),
        (write_payload(p, "Y = 'ok'\n"), None),
        (None, b"garbage"),
        ({"tool_name": "Write"}, None),
    ):
        rc, _, _ = rig.run(payload, raw_stdin=raw)
        seen.append(rc)
    check("6a never exits 1 (the non-blocking error code)",
          all(rc in (0, 2) for rc in seen), "codes=%r" % seen)


# ------------------------------------------------- 7. override token
def test_override_token_permits_the_write(rig):
    p = rig.write_file("declared_ovr.py", ASCII_ONLY_MODULE)
    payload = write_payload(p, "Y = '%s'\n" % EM_DASH)
    rc, _, _ = rig.run(payload)
    check("7 (precondition) the write blocks without a token", rc == 2,
          "rc=%r" % rc)

    rig.mint_token()
    rc, _, err = rig.run(payload)
    check("7a a valid allow-ascii-only-write token permits the write", rc == 0,
          "rc=%r err=%r" % (rc, err[:200]))


def test_override_token_is_scope_and_session_bound(rig):
    """The shared contract's whole point: a token is not a bare sentinel. A wrong
    scope, or a token minted for another session, grants nothing."""
    p = rig.write_file("declared_ovr2.py", ASCII_ONLY_MODULE)
    payload = write_payload(p, "Y = '%s'\n" % EM_DASH)

    rig.mint_token(scope="config-write")
    rc, _, _ = rig.run(payload)
    check("7b a wrong-scope token grants nothing", rc == 2, "rc=%r" % rc)

    rig.mint_token(session_id="some-other-session-999")
    rc, _, _ = rig.run(payload)
    check("7c another session's token grants nothing", rc == 2, "rc=%r" % rc)


def declares_ascii_only_via_guard(path):
    """Ask the guard's OWN matcher whether `path` declares the convention, by
    importing it the way the dispatcher does. Used only to prove test 8 is
    about a file the guard would actually gate."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_aog_probe", HOOK)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.declares_ascii_only(path)


# --------------------------------- 8. the guard passes its own check
def test_guard_source_passes_its_own_check(rig):
    """A guard that could not survive its own rule would be unshippable. Both the
    guard and this test file declare ASCII-only, so both must BE ASCII."""
    for label, path in (("guard", HOOK), ("this test file", os.path.abspath(__file__))):
        with open(path, "rb") as fh:
            raw = fh.read()
        bad = [i for i, b in enumerate(raw) if b > 127]
        check("8 %s source is byte-for-byte ASCII" % label, not bad,
              "first offending offsets: %r" % bad[:5])

    # The guard must also DECLARE the convention, or "its source is ASCII" is a
    # claim about a file the guard would never have gated -- 8b below would pass
    # on any undeclared file. This is the assertion that makes 8/8b bite.
    check("8c the guard's own docstring declares ASCII-only",
          declares_ascii_only_via_guard(HOOK) is True)

    # And prove it through the guard itself, not just by inspection: a Write of
    # the guard's own current bytes back over itself must be ALLOWED.
    with open(HOOK, encoding="utf-8") as fh:
        text = fh.read()
    rc, _, err = rig.run(write_payload(HOOK.replace("\\", "/"), text))
    check("8a the guard allows a rewrite of its own source", rc == 0,
          "rc=%r err=%r" % (rc, err[:200]))

    # ...and the guard's --check mode agrees, run over the whole repo convention.
    rc = subprocess.run([sys.executable, HOOK, "--check", HOOK],
                        capture_output=True).returncode
    check("8b `--check` reports the guard's own source clean", rc == 0)


# ------------------------------------- 9. repair mode: idempotent, byte-exact
def test_repair_is_byte_exact_and_idempotent(rig):
    src = ('"""Fixture. ASCII-only."""\n'
           "# em %s en %s arrow %s ge %s le %s dot %s bom %s\n"
           "X = 1\n" % (EM_DASH, "\u2013", ARROW, GE, LE, MIDDOT, BOM))
    expect = ('"""Fixture. ASCII-only."""\n'
              "# em -- en - arrow -> ge >= le <= dot - bom U+FEFF\n"
              "X = 1\n")
    p = rig.write_file("repairme.py", src)

    rc = subprocess.run([sys.executable, HOOK, "--check", p],
                        capture_output=True).returncode
    check("9 --check flags a violating file (non-zero)", rc != 0, "rc=%r" % rc)

    rc = subprocess.run([sys.executable, HOOK, "--repair", p],
                        capture_output=True).returncode
    got = open(p, "rb").read()
    check("9a --repair rewrites the file byte-exactly",
          got == expect.encode("ascii"),
          "got=%r want=%r" % (got[:160], expect.encode("ascii")[:160]))
    check("9b --repair exits 0", rc == 0, "rc=%r" % rc)

    subprocess.run([sys.executable, HOOK, "--repair", p], capture_output=True)
    check("9c --repair is idempotent (second run is byte-identical)",
          open(p, "rb").read() == got)

    rc = subprocess.run([sys.executable, HOOK, "--check", p],
                        capture_output=True).returncode
    check("9d the repaired file passes --check", rc == 0, "rc=%r" % rc)


def test_repair_refuses_unmapped_characters(rig):
    """Guessing at a character with no canonical ASCII spelling is how a repair
    silently changes meaning. An unmapped codepoint REFUSES the file rather than
    dropping or approximating it."""
    p = rig.write_file("emoji.py",
                       '"""Fixture. ASCII-only."""\n# done \u2705\nX = 1\n')
    before = open(p, "rb").read()
    rc = subprocess.run([sys.executable, HOOK, "--repair", p],
                        capture_output=True)
    check("9e --repair refuses a file carrying an unmapped codepoint",
          rc.returncode != 0, "rc=%r" % rc.returncode)
    check("9f and leaves that file untouched", open(p, "rb").read() == before)
    check("9g and says which codepoint it could not map",
          "U+2705" in (rc.stdout + rc.stderr).decode("utf-8", "replace"))


def test_repair_refuses_a_real_bom(rig):
    """U+FEFF maps to the literal text "U+FEFF", which is right for the two real
    in-repo cases (both PROSE inside a comment ABOUT BOM handling) and wrong for
    a genuine byte-order mark at offset 0. So a real BOM is refused, not
    rewritten into the word."""
    p = rig.write_bytes("bommed.py",
                        b'\xef\xbb\xbf"""Fixture. ASCII-only."""\nX = 1\n')
    before = open(p, "rb").read()
    r = subprocess.run([sys.executable, HOOK, "--repair", p], capture_output=True)
    check("9h --repair refuses a file that opens with a real BOM",
          r.returncode != 0, "rc=%r" % r.returncode)
    check("9i and leaves it untouched", open(p, "rb").read() == before)


def test_repair_is_never_reachable_from_the_hook_path(rig):
    """The hook path is stdin-driven and takes no argv. Repair must never be
    triggerable by a payload -- a guard that can rewrite files as a side effect
    of being consulted is a far worse hazard than the one it guards against."""
    p = rig.write_file("untouched.py",
                       '"""Fixture. ASCII-only."""\n# em %s\nX = 1\n' % EM_DASH)
    before = open(p, "rb").read()
    rig.run(write_payload(p, "Y = '%s'\n" % EM_DASH))
    check("9j a hook invocation never rewrites the target",
          open(p, "rb").read() == before)


# ------------------------------- 10. regression: absent signal -> always allow
def test_regression_absent_signal_always_allows(rig):
    """The fail-open invariant as a matrix. Every row removes exactly ONE of the
    three affirmative signals from an otherwise-blocking call; every row must
    ALLOW. This is the test that would catch a future 'tighten it up' edit
    turning an unknown into a block."""
    p = rig.write_file("declared_matrix.py", ASCII_ONLY_MODULE)
    nonascii = "Y = '%s'\n" % EM_DASH
    base = write_payload(p, nonascii)

    rc, _, _ = rig.run(base)
    check("10 (control) the fully-signalled call blocks", rc == 2, "rc=%r" % rc)

    def drop(mutate, label):
        payload = json.loads(json.dumps(base))
        mutate(payload)
        rc, _, err = rig.run(payload)
        check("10 allows when %s" % label, rc == 0,
              "rc=%r err=%r" % (rc, err[:160]))

    drop(lambda d: d.pop("tool_name"), "tool_name is absent")
    drop(lambda d: d.update(tool_name=None), "tool_name is null")
    drop(lambda d: d.update(tool_name="Bash"), "the tool is not a write tool")
    drop(lambda d: d.update(tool_name="MultiEdit"),
         "the tool is MultiEdit (0 real calls -- deliberately uncovered)")
    drop(lambda d: d.update(tool_name="NotebookEdit"),
         "the tool is NotebookEdit (0 real calls -- deliberately uncovered)")
    drop(lambda d: d.pop("tool_input"), "tool_input is absent")
    drop(lambda d: d.update(tool_input=None), "tool_input is null")
    drop(lambda d: d.update(tool_input="a string"), "tool_input is not a dict")
    drop(lambda d: d.update(tool_input=[]), "tool_input is a list")
    drop(lambda d: d["tool_input"].pop("file_path"), "file_path is absent")
    drop(lambda d: d["tool_input"].update(file_path=""), "file_path is empty")
    drop(lambda d: d["tool_input"].update(file_path=None), "file_path is null")
    drop(lambda d: d["tool_input"].update(file_path=123), "file_path is not a string")
    drop(lambda d: d["tool_input"].pop("content"), "content is absent")
    drop(lambda d: d["tool_input"].update(content=None), "content is null")
    drop(lambda d: d["tool_input"].update(content=123), "content is not a string")
    drop(lambda d: d["tool_input"].update(path=p + ".other"),
         "two different path fields disagree (ambiguous)")
    drop(lambda d: d.pop("session_id"), "session_id is absent")
    drop(lambda d: d.update(session_id=None), "session_id is null")
    drop(lambda d: d.update(session_id=123), "session_id is not a string")
    drop(lambda d: d.update(session_id=""), "session_id is empty")
    # NON-EMPTY BUT NON-ADDRESSABLE. Regression pin, independent review
    # 2026-09-10: an earlier revision tested only `isinstance(str) and
    # session_id`, but override_tokens.token_path() ALSO requires the id to
    # match SESSION_ID_RE. "../../.." passed the weak test, BLOCKED, and then
    # printed a remedy saying no override could be created -- a block with no
    # escape hatch, which is precisely what the guard's own comment says it
    # refuses to produce. The guard now asks token_path() directly.
    drop(lambda d: d.update(session_id="../../.."),
         "session_id cannot address a token (path traversal)")
    drop(lambda d: d.update(session_id="has/slash"),
         "session_id cannot address a token (separator)")
    drop(lambda d: d.update(session_id="x" * 5000),
         "session_id cannot address a token (absurd length)")

    # An Edit missing new_string: 3 of 5398 real Edit calls arrived this way, so
    # this is a shape the harness genuinely emits, not a hypothetical.
    ed = edit_payload(p, "unused")
    ed["tool_input"].pop("new_string")
    rc, _, _ = rig.run(ed)
    check("10a allows an Edit with no new_string (3/5398 real calls)", rc == 0,
          "rc=%r" % rc)


# -------------------------------------- 11. THE REAL DISPATCHER PATH
def _load_dispatcher():
    """Import hooks/pretooluse-dispatcher.py (hyphenated -- not importable by
    name) as a module. Top level is constants and defs only, so importing it
    runs no guard."""
    import importlib.util
    path = os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py")
    spec = importlib.util.spec_from_file_location("_pretooluse_dispatcher", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_block_reaches_the_real_dispatcher(rig):
    """The block must survive the path the harness ACTUALLY uses on Edit/Write.

    Every test above spawns the guard as a subprocess. Since 2026-08-05 that is
    not how it runs: settings.json routes Edit|Write|MultiEdit through
    hooks/pretooluse-dispatcher.py, which imports each guard and calls main()
    IN-PROCESS, deriving rc ONLY from `except SystemExit as e` (rc is
    initialised to 0). A guard signalling a block with `return 2` from main()
    prints its message and returns rc=0 -- the dispatcher never sees a block and
    the write proceeds. Session 9ca9fdea shipped precisely that, green across 14
    subprocess-spawning tests. So this test asserts against
    dispatcher.run_guard() itself, and pins THREE things a spawn cannot:

      * rc == 2 actually ARRIVES at the dispatcher's return value;
      * mode == "inprocess" -- the block came from the in-process SystemExit,
        not from a silent degrade to the subprocess fallback (which would mask
        exactly the defect this test exists to catch);
      * the stderr the dispatcher relays still carries the guard's message.

    run_guard(name, raw) takes BYTES. Passing str is not a benign type error: it
    raises inside _StdinShim, run_guard degrades to _run_subprocess, and that
    call blocks on unclosed stdin for the full 60s timeout -- presenting as a
    hung guard rather than a type error. The final assertion below pins that
    hazard cheaply by calling _run_inprocess directly (no fallback, no timeout).
    """
    dispatcher = _load_dispatcher()
    check("11 dispatcher exposes run_guard()", callable(getattr(dispatcher, "run_guard", None)))

    p = rig.write_file("declared_dispatch.py", ASCII_ONLY_MODULE)
    blocking = json.dumps(
        write_payload(p, ASCII_ONLY_MODULE + "Y = 'a %s b'\n" % EM_DASH)
    ).encode("utf-8")
    allowing = json.dumps(
        write_payload(p, ASCII_ONLY_MODULE + "Y = 'plain -- ok'\n")
    ).encode("utf-8")
    check("11a the payload handed to run_guard is bytes, not str",
          isinstance(blocking, bytes))

    prior = os.environ.get("ORA_OVERRIDE_SESSIONS_DIR")
    os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = rig.sessions
    try:
        rc, out, err, mode = dispatcher.run_guard("ascii-only-guard", blocking)
        check("11b a block REACHES the dispatcher's return value (rc==2)",
              rc == 2, "rc=%r mode=%r err=%r" % (rc, mode, err[:200]))
        check("11c and via the IN-PROCESS path, not a subprocess degrade",
              mode == "inprocess", "mode=%r stderr=%r" % (mode, err[:200]))
        check("11d the dispatcher relays the guard's message",
              "BLOCKED (ascii-only-guard)" in err, err[:200])
        check("11e and the codepoint detail survives the relay",
              "U+2014" in err, err[:400])

        rc, out, err, mode = dispatcher.run_guard("ascii-only-guard", allowing)
        check("11f an ASCII write allows through the dispatcher (rc==0)",
              rc == 0, "rc=%r mode=%r err=%r" % (rc, mode, err[:200]))
        check("11g and that allow is also in-process", mode == "inprocess",
              "mode=%r" % mode)

        # An override token must be honored on the dispatcher path too: the
        # guard reads it at call time, so an in-process run picks up the same
        # ORA_OVERRIDE_SESSIONS_DIR seam the subprocess tests use.
        rig.mint_token()
        rc, _, _, mode = dispatcher.run_guard("ascii-only-guard", blocking)
        check("11h an override token permits the write on the dispatcher path",
              rc == 0, "rc=%r mode=%r" % (rc, mode))
    finally:
        if prior is None:
            os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)
        else:
            os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = prior

    # MAIN() MUST FAIL OPEN ON ITS OWN, not via the dispatcher's subprocess
    # fallback. Regression pin, independent review 2026-09-10: the
    # `except Exception: pass` used to live only under `if __name__ ==
    # "__main__"`, which the in-process path never executes. A file_path
    # carrying a NUL raises ValueError out of open() (before any OSError is
    # reachable) and escaped main() entirely; the call was still allowed, but
    # only because pretooluse-dispatcher.py caught it and re-ran the guard as a
    # subprocess. The invariant was upheld by a SIBLING FILE. Asserting
    # mode == "inprocess" here is the whole point: it proves the guard itself
    # absorbed the error rather than being rescued.
    nul = json.dumps({"session_id": SID, "cwd": os.getcwd(), "tool_name": "Write",
                      "tool_input": {"file_path": "C:/tmp/a\x00b.py",
                                     "content": "Y = '%s'\n" % EM_DASH}}
                     ).encode("utf-8")
    rc, _, err, mode = dispatcher.run_guard("ascii-only-guard", nul)
    check("11j a NUL in file_path fails open IN-PROCESS (main() absorbs it)",
          rc == 0 and mode == "inprocess", "rc=%r mode=%r err=%r" % (rc, mode, err[:200]))

    # The bytes contract, pinned without paying the 60s subprocess timeout that
    # run_guard's fallback would incur on the same mistake.
    raised = False
    try:
        dispatcher._run_inprocess("ascii-only-guard", blocking.decode("utf-8"))
    except Exception:
        raised = True
    check("11i run_guard's payload contract is BYTES (str raises in-process, "
          "and via run_guard would hang the 60s subprocess fallback)", raised)


def main():
    tests = [
        test_blocks_write_introducing_non_ascii,
        test_blocks_edit_introducing_non_ascii,
        test_blocks_dc_edit_block,
        test_blocks_dc_write_file_path_field,
        test_allows_when_file_does_not_declare,
        test_allows_declaration_outside_docstring,
        test_allows_scoped_ascii_only_output_claim,
        test_allows_line_wrapped_scoped_claim,
        test_negated_claim_is_not_a_declaration,
        test_punctuation_terminators_still_declare,
        test_allows_prose_that_merely_names_the_convention,
        test_allows_non_python_target,
        test_allows_ascii_write_into_declared_file,
        test_allows_when_target_absent,
        test_fails_open_on_unreadable_target,
        test_fails_open_on_malformed_stdin,
        test_never_exits_one,
        test_override_token_permits_the_write,
        test_override_token_is_scope_and_session_bound,
        test_guard_source_passes_its_own_check,
        test_repair_is_byte_exact_and_idempotent,
        test_repair_refuses_unmapped_characters,
        test_repair_refuses_a_real_bom,
        test_repair_is_never_reachable_from_the_hook_path,
        test_regression_absent_signal_always_allows,
        test_block_reaches_the_real_dispatcher,
    ]
    if not os.path.exists(HOOK):
        print("FAIL hook not found: " + HOOK)
        return 1
    for t in tests:
        rig = Rig()
        try:
            t(rig)
        finally:
            rig.cleanup()
    print("")
    if _failures:
        print("FAILURES (%d): %s" % (len(_failures), ", ".join(_failures)))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
