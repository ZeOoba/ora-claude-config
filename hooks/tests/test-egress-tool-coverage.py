#!/usr/bin/env python3
"""Egress-gate coverage beyond Bash and Edit/Write (cc-audit-army 2026-11-09, HIGH 1-4).

The audit of ora-claude-config @ 810e4fd found Hard Invariants 1-3 enforced only on the
Bash and Edit/Write paths. This suite pins the fixes, by BEHAVIOR (real subprocess runs of
the guards) rather than by matcher text:

  H1  Shell-capable tools other than Bash -- Desktop Commander start_process and
      interact_with_process, the terminal panel's run_in_terminal, and the PowerShell
      tool -- reach confidentiality-guard's egress-shell scan and ora-autonomy-gate's
      check_bash. Desktop Commander file writes (write_file, edit_block, write_pdf,
      move_file) reach both guards' path checks.
  H2  confidentiality-guard treats Artifact publish (including the local files it
      uploads), ArtifactData writes, ArtifactComments replies, the Claude Docs connector,
      browser form input / typing / scripting / navigation, and Excel writes into an
      egress path as egress surfaces.
  H3  pretooluse-dispatcher's emit_stdout merges permissionDecision by severity
      (deny > ask > allow), so a warn-only guard's 'allow' can never cancel a later deny.
  H4  override-mint-guard is wired into both dispatcher chains (and the wiring table).

Egress audit 2026-11-12 (ora-claude-config @ 6865c3c0):
  N1  (M02) Notion Calendar create/update events reach confidentiality-guard (whole payload
      scanned) and ora-autonomy-gate (an external attendee is an external send; an update
      always needs a token, like Outlook update_event).
  N2  (M05) pretooluse-dispatcher fails CLOSED when a FAIL_CLOSED guard
      (confidentiality-guard) cannot run on either path; other guards keep failing open.
  N3  (M06) WebFetch URLs and WebSearch queries are scanned; only a roster hit blocks.
  N4  (M43) the block message never echoes the matched term or the deal label.

Every term below is a clearly fake placeholder fed through CONFIDENTIAL_TERMS_FILE_OVERRIDE;
no real deal identifier appears in this file. BLOCK == exit 2, ALLOW == exit 0.

Run: python test-egress-tool-coverage.py   (exit 0 = all pass; exit 1 = any fail)
Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import redirect_stdout, redirect_stderr

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(HOOKS, "confidentiality-guard.py")
AUTO = os.path.join(HOOKS, "ora-autonomy-gate.py")
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")

TERM = "Zephyr Corp Portfolio"          # synthetic always-term (fixture, not a real deal)
DC = "mcp__Desktop_Commander__"
DC2 = "mcp__plugin_desktop-commander_desktop-commander__"
TERMINAL = "mcp__terminal__run_in_terminal"
DOCS = "mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__"
CHROME = "mcp__claude-in-chrome__"
BROWSER = "mcp__Claude_Browser__"
SITE_FILE = "C:/Users/Owner/website-canonical/zz-egress-coverage-test.html"

FAILS = []
TMP = tempfile.mkdtemp(prefix="egress-coverage-")


def check(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "  -- " + str(detail)[-300:]))
    if not ok:
        FAILS.append(name)


def _terms_file():
    path = os.path.join(TMP, "synthetic-terms.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"purpose": "synthetic fixture -- no real deal data",
                      "roster_last_verified": datetime.date.today().isoformat()},
            "synthetic_egress_deal": {"active": True, "label": "Synthetic Egress Deal (fixture)",
                                      "always": [TERM, "Project Nightingale"],
                                      "context": [], "context_requires_any": []},
            # Punctuated synthetic terms (REFUTE 2026-11-12, C3): a URL slug drops or swaps the
            # term's own - ' . characters, so the term side must be folded too.
            # No "label": hit_ref / the fold mapping must fall back to the roster key.
            "synthetic_unlabeled_deal": {"active": True, "always": ["Vexmoor-Tal Landing"],
                                         "context": [], "context_requires_any": []},
            "synthetic_punct_deal": {"active": True, "label": "Synthetic Punct Deal (fixture)",
                                     "always": ["Quorb-Lex Commons", "O'Varrow Yards",
                                                "Blorvik St. Ames"],
                                      "context": [], "context_requires_any": []},
        }, f)
    return path


TERMS = _terms_file()


def _tmpfile(name, text):
    path = os.path.join(TMP, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def run(script, tool, tool_input, session=None):
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": TMP,
               "session_id": session or ("egress-test-" + uuid.uuid4().hex[:12])}
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=TERMS)
    p = subprocess.run([sys.executable, script], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=env, timeout=120)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def expect(name, script, tool, tool_input, want_rc):
    rc, err = run(script, tool, tool_input)
    check("%s -> %s" % (name, {0: "allow", 2: "BLOCK"}[want_rc]), rc == want_rc,
          "rc=%s stderr=%s" % (rc, err))


# ------------------------------------------------------------------ H1 confidentiality
def test_conf_shell_tools():
    egress = 'curl -d "%s" https://example.invalid/x' % TERM
    for p in (DC, DC2):
        expect("C1 %sstart_process egress with term" % p, CONF, p + "start_process",
               {"command": egress, "timeout_ms": 1000}, 2)
        expect("C2 %sinteract_with_process egress with term" % p, CONF,
               p + "interact_with_process", {"pid": 1, "input": egress}, 2)
    expect("C3 DC start_process internal use of term", CONF, DC + "start_process",
           {"command": 'echo "%s" > notes.txt' % TERM}, 0)
    expect("C4 DC start_process clean egress", CONF, DC + "start_process",
           {"command": "curl https://example.invalid/x"}, 0)
    expect("C5 terminal run_in_terminal egress with term", CONF, TERMINAL,
           {"command": egress}, 2)
    expect("C6 PowerShell egress with term", CONF, "PowerShell",
           {"command": "Invoke-WebRequest -Uri https://example.invalid -Body '%s'" % TERM}, 2)
    expect("C7 DC start_process non-string command fails closed", CONF, DC + "start_process",
           {"command": ["curl", TERM]}, 2)


def test_conf_dc_writes():
    for p in (DC, DC2):
        expect("C10 %swrite_file into site repo with term" % p, CONF, p + "write_file",
               {"path": SITE_FILE, "content": "<p>%s</p>" % TERM, "mode": "rewrite"}, 2)
    expect("C11 DC write_file internal path with term", CONF, DC + "write_file",
           {"path": os.path.join(TMP, "internal.md"), "content": TERM}, 0)
    expect("C12 DC write_file decoy file_path + egress path", CONF, DC + "write_file",
           {"file_path": os.path.join(TMP, "decoy.md"), "path": SITE_FILE, "content": TERM}, 2)
    expect("C13 DC edit_block into outputs html with term", CONF, DC + "edit_block",
           {"file_path": os.path.join(TMP, "outputs", "memo.html"), "old_string": "x",
            "new_string": TERM}, 2)
    expect("C14 DC write_pdf with term", CONF, DC + "write_pdf",
           {"outputPath": os.path.join(TMP, "memo.pdf"), "content": "# %s" % TERM}, 2)
    expect("C15 DC write_pdf structured content with term", CONF, DC + "write_pdf",
           {"outputPath": os.path.join(TMP, "memo2.pdf"),
            "content": [{"type": "text", "text": TERM}]}, 2)
    dirty = _tmpfile("dirty-src.txt", "about %s here" % TERM)
    clean = _tmpfile("clean-src.txt", "nothing confidential")
    expect("C16 DC move_file term-bearing file into site repo", CONF, DC + "move_file",
           {"source": dirty, "destination": SITE_FILE}, 2)
    expect("C17 DC move_file clean file into site repo", CONF, DC + "move_file",
           {"source": clean, "destination": SITE_FILE}, 0)
    expect("C18 DC move_file unreadable source into site repo fails closed", CONF,
           DC + "move_file", {"source": os.path.join(TMP, "missing.bin"),
                              "destination": SITE_FILE}, 2)
    expect("C19 DC write_file append into outputs with term", CONF, DC + "write_file",
           {"path": os.path.join(TMP, "outputs", "log.md"), "content": TERM, "mode": "append"}, 2)


# ------------------------------------------------------------------ H2 confidentiality
def test_conf_new_send_surfaces():
    dirty = _tmpfile("page.html", "<h1>%s</h1>" % TERM)
    clean = _tmpfile("clean.html", "<h1>hello</h1>")
    dirty_js = _tmpfile("data.js", "const d = '%s';" % TERM)
    expect("C20 Artifact publish of term-bearing page", CONF, "Artifact",
           {"file_path": dirty, "icon": "chart"}, 2)
    expect("C21 Artifact publish of clean page", CONF, "Artifact", {"file_path": clean}, 0)
    expect("C22 Artifact publish with term-bearing supporting file", CONF, "Artifact",
           {"file_path": clean, "files": {"data.js": dirty_js}}, 2)
    expect("C23 Artifact publish with {from} supporting file", CONF, "Artifact",
           {"file_path": clean, "files": {"data.js": {"from": dirty_js}}}, 2)
    expect("C24 Artifact asset upload batch", CONF, "Artifact",
           {"action": "publish", "asset": True, "url": "https://claude.ai/artifact/x",
            "file_paths": [clean, dirty]}, 2)
    expect("C25 Artifact publish title carries term", CONF, "Artifact",
           {"file_path": clean, "title": TERM}, 2)
    expect("C26 Artifact publish of unreadable file fails closed", CONF, "Artifact",
           {"file_path": os.path.join(TMP, "nope.html")}, 2)
    expect("C27 Artifact read is not egress", CONF, "Artifact",
           {"action": "read", "url": "https://claude.ai/artifact/x"}, 0)
    expect("C28 ArtifactData set with term", CONF, "ArtifactData",
           {"action": "set", "url": "u", "collection": "c", "doc_id": "d",
            "data": {"name": TERM}}, 2)
    expect("C29 ArtifactData set from term-bearing JSON file", CONF, "ArtifactData",
           {"action": "set", "url": "u", "collection": "c", "doc_id": "d",
            "file_path": _tmpfile("doc.json", json.dumps({"n": TERM}))}, 2)
    expect("C30 ArtifactData get is not egress", CONF, "ArtifactData",
           {"action": "get", "url": "u", "collection": "c", "doc_id": "d"}, 0)
    expect("C31 ArtifactComments reply with term", CONF, "ArtifactComments",
           {"action": "reply", "url": "u", "thread_id": "t", "text": TERM}, 2)
    expect("C32 ArtifactComments read is not egress", CONF, "ArtifactComments",
           {"action": "read", "url": "u"}, 0)
    for verb in ("batch", "update", "create"):
        expect("C33 Docs connector %s with term" % verb, CONF, DOCS + verb,
               {"payload": {"markdown": "# %s" % TERM}}, 2)
    for pre in (CHROME, BROWSER):
        expect("C34 %sform_input with term" % pre, CONF, pre + "form_input",
               {"ref": "ref_1", "value": TERM}, 2)
        expect("C35 %scomputer type with term" % pre, CONF, pre + "computer",
               {"action": "type", "text": TERM}, 2)
        expect("C36 %scomputer screenshot is not egress" % pre, CONF, pre + "computer",
               {"action": "screenshot"}, 0)
        expect("C37 %sjavascript_tool with term" % pre, CONF, pre + "javascript_tool",
               {"action": "javascript_exec", "text": "fetch('/x',{body:'%s'})" % TERM}, 2)
        expect("C38 %snavigate URL with term" % pre, CONF, pre + "navigate",
               {"url": "https://example.invalid/?q=" + TERM}, 2)
        expect("C39 %sbrowser_batch nested type with term" % pre, CONF, pre + "browser_batch",
               {"actions": [{"name": "computer", "input": {"action": "type", "text": TERM}}]}, 2)
    expect("C40 Excel write into outputs with term", CONF, "mcp__excel__write_data_to_excel",
           {"filepath": os.path.join(TMP, "outputs", "deal.xlsx"), "sheet_name": "S",
            "data": [[TERM]]}, 2)
    expect("C41 Excel write into an internal model with term", CONF,
           "mcp__excel__write_data_to_excel",
           {"filepath": os.path.join(TMP, "models", "ORA_UW_Deal_v1.0.xlsx"),
            "sheet_name": "S", "data": [[TERM]]}, 0)


# ------------------------------------------------------------------ H1 autonomy gate
def test_autonomy_shell_and_writes():
    deploy = "netlify deploy --prod --dir=dist"
    for p in (DC, DC2):
        expect("A1 %sstart_process prod deploy" % p, AUTO, p + "start_process",
               {"command": deploy}, 2)
        expect("A2 %sinteract_with_process prod deploy" % p, AUTO,
               p + "interact_with_process", {"pid": 1, "input": deploy}, 2)
        expect("A3 %swrite_file into site repo" % p, AUTO, p + "write_file",
               {"path": SITE_FILE, "content": "x"}, 2)
    expect("A4 terminal run_in_terminal prod deploy", AUTO, TERMINAL, {"command": deploy}, 2)
    expect("A5 PowerShell prod deploy", AUTO, "PowerShell", {"command": deploy}, 2)
    expect("A6 DC edit_block into site repo", AUTO, DC + "edit_block",
           {"file_path": SITE_FILE, "old_string": "a", "new_string": "b"}, 2)
    expect("A7 DC write_pdf into site repo", AUTO, DC + "write_pdf",
           {"outputPath": SITE_FILE.replace(".html", ".pdf"), "content": "x"}, 2)
    expect("A8 DC move_file into site repo", AUTO, DC + "move_file",
           {"source": os.path.join(TMP, "a.txt"), "destination": SITE_FILE}, 2)
    expect("A9 DC start_process read-only command", AUTO, DC + "start_process",
           {"command": "git status"}, 0)
    expect("A10 DC write_file outside the site", AUTO, DC + "write_file",
           {"path": os.path.join(TMP, "ok.md"), "content": "x"}, 0)
    expect("A11 DC read_file is not gated", AUTO, DC + "read_file",
           {"path": SITE_FILE}, 0)
    expect("A12 DC start_process non-string command fails closed", AUTO, DC + "start_process",
           {"command": {"x": 1}}, 2)


# ------------------------------------------------------------------ H3 dispatcher merge
def _load_dispatcher():
    spec = importlib.util.spec_from_file_location("_disp_under_test", DISPATCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _decision(kind, reason, ctx=None):
    hso = {"hookEventName": "PreToolUse", "permissionDecision": kind,
           "permissionDecisionReason": reason}
    if ctx:
        hso["additionalContext"] = ctx
    return json.dumps({"hookSpecificOutput": hso})


def _merge(chunks):
    disp = _load_dispatcher()
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        disp.emit_stdout(chunks)
    text = out.getvalue()
    return (json.loads(text) if text.strip() else {}), err.getvalue()


def test_dispatcher_merge():
    got, _ = _merge([_decision("allow", "warn-only", "shared checkout note"),
                     _decision("deny", "rules.md is append-only")])
    hso = got.get("hookSpecificOutput", {})
    check("D1 allow then deny -> deny", hso.get("permissionDecision") == "deny", got)
    check("D2 deny keeps the deny's own reason",
          hso.get("permissionDecisionReason") == "rules.md is append-only", got)
    check("D3 the allow guard's additionalContext still delivered",
          "shared checkout note" in (hso.get("additionalContext") or ""), got)
    got, _ = _merge([_decision("allow", "a"), _decision("ask", "needs Gabriel")])
    hso = got.get("hookSpecificOutput", {})
    check("D4 allow then ask -> ask", hso.get("permissionDecision") == "ask"
          and hso.get("permissionDecisionReason") == "needs Gabriel", got)
    got, _ = _merge([_decision("deny", "first"), _decision("allow", "later")])
    check("D5 deny then allow -> deny (first reason)",
          got.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
          and got["hookSpecificOutput"].get("permissionDecisionReason") == "first", got)
    got, _ = _merge([_decision("deny", "first"), _decision("deny", "second")])
    reason = got.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    check("D6 two denies -> both reasons surfaced", "first" in reason and "second" in reason,
          got)
    got, _ = _merge([_decision("ask", "q"), _decision("deny", "no")])
    check("D7 ask then deny -> deny",
          got.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", got)
    got, _ = _merge([_decision("allow", "a"), _decision("bogus", "?")])
    check("D8 an unknown decision value never outranks a known one",
          got.get("hookSpecificOutput", {}).get("permissionDecision") == "allow", got)


def test_dispatcher_end_to_end_deny_survives():
    """A real chain run: a stub allow-guard ahead of a stub deny-guard. Before the fix the
    harness received permissionDecision 'allow' and the write went through."""
    root = os.path.join(TMP, "disp-e2e")
    os.makedirs(os.path.join(root, "lib"), exist_ok=True)
    shutil.copy(DISPATCHER, os.path.join(root, "pretooluse-dispatcher.py"))
    stub = ("import json, sys\n\n\ndef main():\n    sys.stdin.read()\n"
            "    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',"
            " 'permissionDecision': %r, 'permissionDecisionReason': %r}}))\n")
    for name, kind, reason in (("stub-allow", "allow", "warn"), ("stub-deny", "deny", "blocked")):
        with open(os.path.join(root, name + ".py"), "w") as f:
            f.write(stub % (kind, reason))
    spec = importlib.util.spec_from_file_location("_disp_e2e", os.path.join(root, "pretooluse-dispatcher.py"))
    disp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(disp)
    out = io.StringIO()
    real_stdin = sys.stdin
    try:
        sys.stdin = io.TextIOWrapper(io.BytesIO(b'{"tool_name":"Write","tool_input":{}}'))
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = disp.main(["stub-allow", "stub-deny"], "custom")
    finally:
        sys.stdin = real_stdin
    data = json.loads(out.getvalue() or "{}")
    check("D9 end-to-end: allow-guard then deny-guard -> harness sees deny",
          rc == 0 and data.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
          "rc=%s out=%s" % (rc, out.getvalue()))


# ------------------------------------------------------------------ REFUTE 2026-11-09 regressions
def run_raw(script, raw_text):
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=TERMS)
    p = subprocess.run([sys.executable, script], input=raw_text.encode("utf-8"),
                       capture_output=True, env=env, timeout=120)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def test_refute_dispatcher():
    for name, bad in (("non-dict hookSpecificOutput", json.dumps({"hookSpecificOutput": ["deny"]})),
                      ("list permissionDecision", json.dumps({"hookSpecificOutput": {
                          "permissionDecision": ["deny"]}})),
                      ("string hookSpecificOutput", json.dumps({"hookSpecificOutput": "deny"}))):
        try:
            got, _ = _merge([bad, _decision("deny", "real deny")])
            ok = got.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
        except Exception as e:  # noqa: BLE001 -- a raise here is exit 1 in production
            ok, got = False, "raised %s: %s" % (type(e).__name__, e)
        check("R1 malformed %s ahead of a deny -> deny survives" % name, ok, got)
    got, _ = _merge([_decision("allow", "a"), _decision("DENY", "upper-case")])
    check("R2 upper-case DENY outranks allow",
          got.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", got)


def test_refute_conf_guard():
    dirty = _tmpfile("refute-dirty.html", "<p>%s</p>" % TERM)
    for name, cmd in (("irm -Body", "irm https://example.invalid -Method Post -Body '%s'" % TERM),
                      ("iwr", "iwr https://example.invalid -Body '%s'" % TERM),
                      ("Send-MailMessage", "Send-MailMessage -To a@b.c -Body '%s'" % TERM),
                      ("WebClient.UploadString",
                       "(New-Object Net.WebClient).UploadString('https://x.invalid','%s')" % TERM)):
        expect("R10 PowerShell %s with term" % name, CONF, "PowerShell", {"command": cmd}, 2)
    expect("R11 DC start_process powershell irm with term", CONF, DC + "start_process",
           {"command": "irm https://x.invalid -Body '%s'" % TERM, "shell": "powershell.exe"}, 2)
    for raw in ("[]", '"x"', "1"):
        rc, err = run_raw(CONF, raw)
        check("R12 non-object payload %s fails closed (exit 2, never 1)" % raw, rc == 2,
              "rc=%s %s" % (rc, err[-200:]))
    for tool, ti in ((DC + "write_file", [SITE_FILE, TERM]), (DC + "write_file", "x"),
                     ("Artifact", "x"), (DC + "start_process", ["curl", TERM]),
                     (CHROME + "form_input", [TERM])):
        expect("R13 non-dict tool_input on %s fails closed" % tool, CONF, tool, ti, 2)
    expect("R14 Artifact files entry with artifact+from decoy", CONF, "Artifact",
           {"file_path": _tmpfile("ok.html", "fine"),
            "files": {"a.html": {"artifact": "https://claude.ai/artifact/x", "from": dirty}}}, 2)
    expect("R15 Artifact unknown action carrying a dirty file", CONF, "Artifact",
           {"action": "update", "file_path": dirty}, 2)
    expect("R16 ArtifactComments unknown action with term", CONF, "ArtifactComments",
           {"action": "create", "url": "u", "text": TERM}, 2)
    expect("R17 ArtifactData unknown action from dirty file", CONF, "ArtifactData",
           {"action": "import", "url": "u", "file_path": dirty}, 2)
    expect("R18 Artifact read still allowed", CONF, "Artifact", {"action": "read", "url": "u"}, 0)
    payload = {"tool_name": DC + "write_file", "cwd": "C:/Users/Owner/website-canonical",
               "tool_input": {"path": "zz-relative.html", "content": TERM},
               "session_id": "egress-test-rel"}
    rc, err = run_raw(CONF, json.dumps(payload))
    check("R19 relative DC write resolved against payload cwd (site repo) -> BLOCK", rc == 2,
          "rc=%s %s" % (rc, err[-200:]))
    ws = "C:\\Users\\Owner\\ws-egress-test"  # Windows-style cwd: joins become mixed-slash
    for name, tool, ti in (
            ("DC write_file outputs/", DC + "write_file", {"path": "outputs/x.txt", "content": TERM}),
            ("DC write_file dist/", DC + "write_file", {"path": "dist/x.js", "content": TERM}),
            ("Excel write outputs/", "mcp__excel__write_data_to_excel",
             {"filepath": "outputs/x.xlsx", "sheet_name": "S", "data": [[TERM]]})):
        rc, err = run_raw(CONF, json.dumps({"tool_name": tool, "tool_input": ti, "cwd": ws,
                                            "session_id": "egress-test-rel2"}))
        check("R22 relative %s under a backslash cwd -> BLOCK" % name, rc == 2,
              "rc=%s %s" % (rc, err[-200:]))
    dirty_src = _tmpfile("rel-move-src.txt", TERM)
    rc, err = run_raw(CONF, json.dumps({"tool_name": DC + "move_file", "cwd": ws, "session_id": "s",
                                        "tool_input": {"source": dirty_src,
                                                       "destination": "outputs/x.txt"}}))
    check("R23 relative move_file into outputs/ under a backslash cwd -> BLOCK", rc == 2,
          "rc=%s %s" % (rc, err[-200:]))
    big = os.path.join(TMP, "bigdir")
    for i in range(260):
        sub = os.path.join(big, "d%02d" % (i % 13))
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "f%03d.txt" % i), "w") as f:
            f.write("clean")
    import time as _t
    t0 = _t.monotonic()
    rc, err = run(CONF, "Artifact", {"file_path": big})
    check("R24 directory publish past the file cap fails closed, promptly",
          rc == 2 and _t.monotonic() - t0 < 30, "rc=%s %.1fs" % (rc, _t.monotonic() - t0))
    expect("R20 browser upload_image of a term-bearing file", CONF, CHROME + "upload_image",
           {"imagePath": dirty, "ref": "ref_1"}, 2)
    expect("R21 browser computer key input with term", CONF, CHROME + "computer",
           {"action": "key", "text": TERM}, 2)


def test_refute_autonomy():
    site_win = SITE_FILE.replace("/", "\\")
    for name, cmd in (("Copy-Item", "Copy-Item a.html %s" % site_win),
                      ("Move-Item", "Move-Item a.html %s" % site_win),
                      ("[IO.File]::WriteAllText", "[IO.File]::WriteAllText('%s','x')" % site_win),
                      ("robocopy", "robocopy dist C:\\Users\\Owner\\website-canonical /MIR"),
                      ("ntl deploy --prod", "ntl deploy --prod"),
                      ("netlify deploy -p", "netlify deploy -p --dir=dist")):
        expect("R30 PowerShell %s" % name, AUTO, "PowerShell", {"command": cmd}, 2)
    expect("R31 draft deploy after mkdir -p is NOT a prod deploy", AUTO, "PowerShell",
           {"command": "mkdir -p dist && netlify deploy --dir=dist"}, 0)
    payload = {"tool_name": DC + "write_file", "cwd": "C:/Users/Owner/website-canonical",
               "tool_input": {"path": "index.html", "content": "x"},
               "session_id": "egress-test-" + uuid.uuid4().hex[:12]}
    rc, err = run_raw(AUTO, json.dumps(payload))
    check("R32 relative DC write resolved against payload cwd (site repo) -> BLOCK", rc == 2,
          "rc=%s %s" % (rc, err[-200:]))
    import time as _t
    padded = "ntl deploy " + "deploy " * 30000 + "--prod"   # ~210 KB; was ~50 s quadratic
    t0 = _t.monotonic()
    rc, err = run(AUTO, DC + "interact_with_process", {"pid": 1, "input": padded})
    check("R35 padded prod deploy blocks in linear time", rc == 2 and _t.monotonic() - t0 < 10,
          "rc=%s %.1fs" % (rc, _t.monotonic() - t0))
    padded_p = "netlify deploy " + "x " * 100000 + "-p"
    t0 = _t.monotonic()
    rc, err = run(AUTO, DC + "interact_with_process", {"pid": 1, "input": padded_p})
    check("R36 padded short-flag prod deploy blocks in linear time",
          rc == 2 and _t.monotonic() - t0 < 10, "rc=%s %.1fs" % (rc, _t.monotonic() - t0))
    expect("R37 Excel tool with an unlisted write prefix still reaches the gate", AUTO,
           "mcp__excel__set_cell_value",
           {"filepath": "C:/Users/Owner/website-canonical/data.xlsx", "value": "x"}, 2)
    expect("R33 Excel write into the site tree", AUTO, "mcp__excel__write_data_to_excel",
           {"filepath": "C:/Users/Owner/website-canonical/data.xlsx", "sheet_name": "S",
            "data": [["x"]]}, 2)
    expect("R34 Excel read of a site workbook is not gated", AUTO,
           "mcp__excel__read_data_from_excel",
           {"filepath": "C:/Users/Owner/website-canonical/data.xlsx", "sheet_name": "S"}, 0)


# ------------------------------------------------------------------ N1 Notion Calendar (M02)
NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__"
NCAL_CREATE = NOTION + "notion-calendar-create-events"
NCAL_UPDATE = NOTION + "notion-calendar-update-events"
_PERIOD = {"type": "DATE_TIME", "start": {"dateTime": "2026-12-01T10:00:00Z"},
           "end": {"dateTime": "2026-12-01T11:00:00Z"}}
_CAL = {"accountId": "acct", "calendarId": "cal"}


def _ncal_create(summary="Site walk", attendees=None, **extra):
    ev = {"summary": summary, "period": _PERIOD}
    if attendees is not None:
        ev["attendees"] = [{"email": a} for a in attendees]
    ev.update(extra)
    return {"timeZone": "America/New_York", "events": [ev]}


def _ncal_update(update=None, rsvp=None):
    u = {"event": {"calendar": _CAL, "eventId": "evt-1"}}
    if rsvp is not None:
        u.update(updateType="RSVP", rsvp=rsvp)
    else:
        u.update(updateType="UPDATE", update=update or {"summary": "moved"})
    return {"timeZone": "America/New_York", "updates": [u]}


def test_notion_calendar():
    expect("N1a Notion Calendar create with term in summary", CONF, NCAL_CREATE,
           _ncal_create(summary="Tour of " + TERM), 2)
    expect("N1b Notion Calendar create with term in description", CONF, NCAL_CREATE,
           _ncal_create(description="re " + TERM), 2)
    expect("N1c Notion Calendar create clean", CONF, NCAL_CREATE, _ncal_create(), 0)
    expect("N1d Notion Calendar update with term", CONF, NCAL_UPDATE,
           _ncal_update({"description": TERM}), 2)
    expect("N1e Notion Calendar RSVP comment with term", CONF, NCAL_UPDATE,
           _ncal_update(rsvp={"responseStatus": "accepted", "comment": TERM}), 2)
    expect("N1f Notion Calendar update clean", CONF, NCAL_UPDATE, _ncal_update(), 0)
    # Autonomy gate: an external attendee is an external send (Outlook create_event parity).
    expect("N1g create with external attendee", AUTO, NCAL_CREATE,
           _ncal_create(attendees=["broker@example.com"]), 2)
    expect("N1h create with internal attendee only", AUTO, NCAL_CREATE,
           _ncal_create(attendees=["ggoldberg@oxfordra.net"]), 0)
    expect("N1i create with no attendees", AUTO, NCAL_CREATE, _ncal_create(), 0)
    expect("N1j create with lookalike internal domain", AUTO, NCAL_CREATE,
           _ncal_create(attendees=["x@oxfordra.net.evil.com"]), 2)
    expect("N1k create with an external address in location", AUTO, NCAL_CREATE,
           _ncal_create(location="dial in: bridge@example.com"), 2)
    expect("N1l create with an external resource email", AUTO, NCAL_CREATE,
           _ncal_create(resources=[{"email": "room@example.com", "isOptional": False}]), 2)
    expect("N1m update always gated (existing attendees invisible)", AUTO, NCAL_UPDATE,
           _ncal_update(), 2)
    expect("N1n RSVP always gated (mails the organizer)", AUTO, NCAL_UPDATE,
           _ncal_update(rsvp={"responseStatus": "accepted"}), 2)
    expect("N1o malformed create (events not a list) fails closed", AUTO, NCAL_CREATE,
           {"timeZone": "UTC", "events": "x"}, 2)
    expect("N1p unknown event key fails closed", AUTO, NCAL_CREATE,
           _ncal_create(notifyAll=True), 2)
    expect("N1q cancel-events is not the autonomy gate's (mcp-delete-guard owns it)", AUTO,
           NOTION + "notion-calendar-cancel-events", {"cancellations": []}, 0)


def test_notion_calendar_token():
    """A token naming the external attendee lets exactly that create through."""
    tokdir = os.path.join(TMP, "ncal-sessions")
    sess = "egress-ncal-" + uuid.uuid4().hex[:8]
    od = os.path.join(tokdir, sess, "overrides")
    os.makedirs(od)
    with open(os.path.join(od, "allow-external-send"), "w") as f:
        f.write("scope: external-send\nsession: %s\nreason: test\nrecipients: broker@example.com\n"
                % sess)
    payload = {"tool_name": NCAL_CREATE, "tool_input": _ncal_create(attendees=["broker@example.com"]),
               "cwd": TMP, "session_id": sess}
    env = dict(os.environ, ORA_OVERRIDE_SESSIONS_DIR=tokdir)
    p = subprocess.run([sys.executable, AUTO], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=env, timeout=120)
    check("N1r external-send token naming the attendee -> allow", p.returncode == 0,
          p.stderr.decode("utf-8", "replace"))


# ------------------------------------------------------------------ N2 dispatcher fail-closed (M05)
def _both_paths_fail(disp, sub_rc=None):
    def _inproc(name, raw):
        raise RuntimeError("synthetic in-process failure")

    def _sub(name, raw):
        if sub_rc is None:
            raise OSError("synthetic subprocess failure")
        return sub_rc, "", "Traceback (synthetic crash)\n"
    disp._run_inprocess = _inproc
    disp._run_subprocess = _sub


def test_dispatcher_fail_closed():
    disp = _load_dispatcher()
    check("N2a FAIL_CLOSED contains confidentiality-guard",
          "confidentiality-guard" in getattr(disp, "FAIL_CLOSED", ()))
    _both_paths_fail(disp)
    with redirect_stderr(io.StringIO()) as err:
        rc, _o, _e, mode = disp.run_guard("confidentiality-guard", b"{}")
    check("N2b confidentiality-guard failing both paths -> rc 2 (fail closed)",
          rc == 2 and mode == "failclosed", "rc=%s mode=%s %s" % (rc, mode, err.getvalue()))
    with redirect_stderr(io.StringIO()):
        rc, _o, _e, mode = disp.run_guard("destructive-git-guard", b"{}")
    check("N2c a non-FAIL_CLOSED guard failing both paths keeps failing open",
          rc == 0 and mode == "failed", "rc=%s mode=%s" % (rc, mode))
    disp = _load_dispatcher()
    _both_paths_fail(disp, sub_rc=1)
    with redirect_stderr(io.StringIO()):
        rc, _o, _e, mode = disp.run_guard("confidentiality-guard", b"{}")
    check("N2d confidentiality-guard subprocess CRASH (rc 1) after in-process failure -> rc 2",
          rc == 2 and mode == "failclosed", "rc=%s mode=%s" % (rc, mode))
    with redirect_stderr(io.StringIO()):
        rc, _o, _e, mode = disp.run_guard("destructive-git-guard", b"{}")
    check("N2e non-FAIL_CLOSED guard subprocess rc 1 is relayed unchanged (non-blocking)",
          rc == 1 and mode == "subprocess", "rc=%s mode=%s" % (rc, mode))
    disp = _load_dispatcher()
    _both_paths_fail(disp)
    real_stdin = sys.stdin
    try:
        sys.stdin = io.TextIOWrapper(io.BytesIO(b'{"tool_name":"Bash","tool_input":{}}'))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
            rc = disp._dispatch(["confidentiality-guard"], b"{}", "custom", ("", ""), [])
    finally:
        sys.stdin = real_stdin
    check("N2f chain run: confidentiality-guard unrunnable -> chain blocks (2)", rc == 2,
          "rc=%s %s" % (rc, err.getvalue()))
    check("N2g the block message names the guard and says it failed closed",
          "confidentiality-guard" in err.getvalue() and "fail" in err.getvalue().lower(),
          err.getvalue())


# ------------------------------------------------------------------ N3 WebFetch / WebSearch (M06)
def test_web_tools():
    expect("N3a WebFetch URL carrying the term", CONF, "WebFetch",
           {"url": "https://example.invalid/?q=" + TERM, "prompt": "summarize"}, 2)
    expect("N3a2 WebFetch URL carrying the term percent-encoded", CONF, "WebFetch",
           {"url": "https://example.invalid/?q=" + TERM.replace(" ", "%20")}, 2)
    expect("N3a3 WebFetch URL carrying the term plus-encoded", CONF, "WebFetch",
           {"url": "https://example.invalid/?q=" + TERM.replace(" ", "+")}, 2)
    expect("N3a4 WebFetch URL carrying the term as a hyphenated slug", CONF, "WebFetch",
           {"url": "https://example.invalid/" + TERM.lower().replace(" ", "-")}, 2)
    expect("N3a5 WebFetch URL carrying the term as an underscore/dot slug", CONF, "WebFetch",
           {"url": "https://example.invalid/" + TERM.replace(" ", "_") + "/" + TERM.replace(" ", ".")}, 2)
    expect("N3a6 WebFetch URL carrying the term double-percent-encoded", CONF, "WebFetch",
           {"url": "https://example.invalid/?q=" + TERM.replace(" ", "%2520")}, 2)
    for slug in ("quorb-lex-commons", "quorb_lex_commons", "Quorb-Lex-Commons", "ovarrow-yards", "o-varrow-yards", "blorvik-st-ames", "blorvik-st.-ames"):
        expect("N3a7 WebFetch slug of a punctuated term: %s" % slug, CONF, "WebFetch",
               {"url": "https://example.invalid/listing/" + slug}, 2)
    for sep in (",", ";", "|", "‐"):
        expect("N3a8 WebFetch URL with %s between term words" % ascii(sep), CONF, "WebFetch",
               {"url": "https://example.invalid/?q=" + TERM.replace(" ", sep)}, 2)
    expect("N3a9 WebSearch query with a punctuated term spelled without punctuation", CONF,
           "WebSearch", {"query": "ovarrow yards industrial sale"}, 2)
    expect("N3a10 WebFetch URL sharing only one word of a punctuated term", CONF, "WebFetch",
           {"url": "https://example.invalid/commons-park/yards"}, 0)
    expect("N3b WebFetch clean URL", CONF, "WebFetch",
           {"url": "https://example.invalid/industrial-market", "prompt": "summarize"}, 0)
    expect("N3c WebFetch prompt naming the term but a clean URL (prompt is not sent to the site)",
           CONF, "WebFetch", {"url": "https://example.invalid/x", "prompt": "find " + TERM}, 0)
    expect("N3d WebSearch query carrying the term", CONF, "WebSearch", {"query": TERM + " sale"}, 2)
    expect("N3e WebSearch clean query", CONF, "WebSearch",
           {"query": "Columbus industrial vacancy 2026"}, 0)
    expect("N3f WebSearch allowed_domains carrying the term", CONF, "WebSearch",
           {"query": "x", "allowed_domains": [TERM]}, 2)
    expect("N3g WebFetch non-string url fails closed", CONF, "WebFetch", {"url": [TERM]}, 2)
    expect("N3h WebSearch non-string query fails closed", CONF, "WebSearch", {"query": {"q": 1}}, 2)


# ------------------------------------------------------------------ N4 block message (M43)
def test_block_message_redacted():
    rc, err = run(CONF, "WebSearch", {"query": TERM})
    if rc != 2:
        rc, err = run(CONF, "Write", {"file_path": SITE_FILE, "content": TERM})
    check("N4a blocked", rc == 2, err)
    check("N4b block message does not echo the matched term", TERM.lower() not in err.lower(), err)
    check("N4c block message does not echo the deal label", "Synthetic Egress Deal" not in err, err)
    check("N4d block message carries a term id", "term-id" in err, err)
    check("N4e block message carries a next step", "Next step" in err, err)
    conf = _load_conf()
    tid = conf.term_id("Zephyr Corp Portfolio")
    check("N4f term id is stable and short", tid == conf.term_id("Zephyr Corp Portfolio")
          and 8 <= len(tid) <= 16 and TERM.lower() not in tid, tid)
    check("N4g term id in the message matches term_id()", tid in err, (tid, err))
    rc, err = run(CONF, "WebFetch", {"url": "https://example.invalid/ovarrow-yards"})
    check("N4h a folded web hit cites the ORIGINAL term's id",
          rc == 2 and conf.term_id("O'Varrow Yards") in err, err)
    rc, err = run(CONF, "WebFetch", {"url": "https://example.invalid/vexmoor-tal_landing"})
    check("N4i a folded web hit on an UNLABELED roster entry cites the original term's id",
          rc == 2 and conf.term_id("Vexmoor-Tal Landing") in err and "#2" in err, err)


def _load_conf():
    spec = importlib.util.spec_from_file_location("_conf_under_test", CONF)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ H4 override-mint wiring
def test_override_mint_wired():
    disp = _load_dispatcher()
    check("M1 override-mint-guard in the Edit/Write chain",
          "override-mint-guard" in disp.GUARD_CHAIN)
    check("M2 override-mint-guard in the Bash chain",
          "override-mint-guard" in disp.BASH_GUARD_CHAIN)
    check("M3 ascii-only-guard still LAST in the Edit/Write chain",
          disp.GUARD_CHAIN[-1] == "ascii-only-guard")
    check("M4 pipe-mask-guard still LAST in the Bash chain",
          disp.BASH_GUARD_CHAIN[-1] == "pipe-mask-guard")


# ------------------------------------------------------------------ R  RESIDUAL egress (#452 follow-up)
# Every tool #452's snapshot test listed as RESIDUAL is now routed and classified (or moved to a
# concrete exclusion). Names are the live harness forms (uuid connectors as captured in
# mcp_tool_snapshot.json; local servers by their server name). Each class: a roster term in the
# outbound text BLOCKS, clean text passes.
DRIVE = "mcp__45584658-e0ff-4b66-972a-09a41d9941d2__"
DESIGN = "mcp__7c55602a-d1ec-4c77-a92e-06ee3c786d3a__"
COMPOSIO = "mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__"
RUBE = "mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__"
GMAIL_DRAFT = ("mcp__8ac87555-f8a7-4acc-82c5-cb75e6b92ee3__"
               "gmail_create_draft-950737b91de8397144477ba94ad008e9")
QBO = "mcp__52fa80c0-fe01-4bd6-b488-39531b108fe4__"
MSDOCS = "mcp__5399b569-1d87-49ca-841c-ec4725b3f124__"
HUBSPOT = "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__"
APIFY = "mcp__Apify__"
WIN = "mcp__Windows-MCP__"
CU = "mcp__computer-use__"
FS = "mcp__Filesystem__"
MNEMO = "mcp__Mnemoverse_Memory__"
SLUG = TERM.lower().replace(" ", "-")


def _pair(name, tool, dirty, clean):
    expect(name + " (term)", CONF, tool, dirty, 2)
    expect(name + " (clean)", CONF, tool, clean, 0)


def test_residual_conf():
    _pair("R1 Drive create_file content", DRIVE + "create_file",
          {"title": "memo", "content": "re: " + TERM}, {"title": "memo", "content": "market note"})
    _pair("R1b Drive create_file title", DRIVE + "create_file",
          {"title": TERM, "content": "x"}, {"title": "market", "content": "x"})
    _pair("R2 Firefly board name", DESIGN + "create_firefly_board",
          {"name": TERM}, {"name": "moodboard"})
    _pair("R3 design fill_text", DESIGN + "fill_text", {"text": TERM}, {"text": "For Lease"})
    up = _tmpfile("r-upload.txt", "notes on " + TERM)
    ok = _tmpfile("r-upload-ok.txt", "plain notes")
    _pair("R3b design asset_add_file reads the local file", DESIGN + "asset_add_file",
          {"filePath": up}, {"filePath": ok})
    _pair("R3c design asset_initialize_file_upload name", DESIGN + "asset_initialize_file_upload",
          {"fileName": TERM + ".png"}, {"fileName": "site.png"})
    _pair("R3d design asset_finalize_file_upload", DESIGN + "asset_finalize_file_upload",
          {"uploadId": "u1", "title": TERM}, {"uploadId": "u1"})
    _pair("R3e document_merge_data_layout data", DESIGN + "document_merge_data_layout",
          {"data": {"title": TERM}}, {"data": {"title": "Flyer"}})
    _pair("R3f document_merge_data_vector data", DESIGN + "document_merge_data_vector",
          {"data": [TERM]}, {"data": ["Flyer"]})
    for pre, brand in ((COMPOSIO, "COMPOSIO"), (RUBE, "RUBE")):
        _pair("R4 %s_MULTI_EXECUTE_TOOL arguments" % brand, pre + brand + "_MULTI_EXECUTE_TOOL",
              {"tools": [{"tool_slug": "GMAIL_SEND_EMAIL", "arguments": {"body": TERM}}]},
              {"tools": [{"tool_slug": "GMAIL_SEND_EMAIL", "arguments": {"body": "hello"}}]})
        _pair("R4b %s_REMOTE_BASH_TOOL any command" % brand, pre + brand + "_REMOTE_BASH_TOOL",
              {"command": "echo " + TERM + " > notes.txt"}, {"command": "ls -la"})
        _pair("R4c %s_REMOTE_WORKBENCH code" % brand, pre + brand + "_REMOTE_WORKBENCH",
              {"code_to_execute": "x = '%s'" % TERM}, {"code_to_execute": "x = 1"})
    _pair("R4d RUBE_EXECUTE_RECIPE input", RUBE + "RUBE_EXECUTE_RECIPE",
          {"recipe_id": "r1", "input_data": {"subject": TERM}}, {"recipe_id": "r1"})
    _pair("R4e RUBE_CREATE_UPDATE_RECIPE body", RUBE + "RUBE_CREATE_UPDATE_RECIPE",
          {"name": TERM}, {"name": "weekly digest"})
    _pair("R5 Gmail draft body", GMAIL_DRAFT, {"to": "a@example.com", "body": TERM},
          {"to": "a@example.com", "body": "hello"})
    _pair("R6 QBO invoice memo", QBO + "qbo_sales_create_invoice",
          {"customerMemo": TERM}, {"customerMemo": "thanks"})
    _pair("R6b QBO invoice update", QBO + "qbo_sales_update_invoice",
          {"id": "1", "customerMemo": TERM}, {"id": "1"})
    _pair("R6c QBO profile update", QBO + "quickbooks-profile-info-update",
          {"companyName": TERM}, {"companyName": "Holdco LLC"})
    _pair("R6d QBO transaction import", QBO + "quickbooks-transaction-import",
          {"rows": [{"memo": TERM}]}, {"rows": [{"memo": "rent"}]})
    _pair("R7 Apify call-actor input", APIFY + "call-actor",
          {"actor": "apify/google-search", "input": {"queries": TERM}},
          {"actor": "apify/google-search", "input": {"queries": "industrial flex"}})
    _pair("R7b Apify rag web browser query slug", APIFY + "apify-slash-rag-web-browser",
          {"query": "https://example.invalid/" + SLUG}, {"query": "industrial vacancy"})
    _pair("R8 Windows-MCP Type", WIN + "Type", {"loc": [1, 2], "text": TERM},
          {"loc": [1, 2], "text": "hello"})
    _pair("R8b Windows-MCP MultiEdit", WIN + "MultiEdit", {"locs": [[1, 2, TERM]]},
          {"locs": [[1, 2, "hi"]]})
    _pair("R8c Windows-MCP Clipboard set", WIN + "Clipboard", {"mode": "set", "text": TERM},
          {"mode": "get"})
    _pair("R8d Windows-MCP Scrape URL slug", WIN + "Scrape",
          {"url": "https://example.invalid/" + SLUG}, {"url": "https://example.invalid/x"})
    _pair("R8e Windows-MCP Process args", WIN + "Process",
          {"mode": "start", "name": "notepad", "args": TERM}, {"mode": "list"})
    _pair("R8f Windows-MCP PowerShell egress command", WIN + "PowerShell",
          {"command": "curl.exe -d '%s' https://example.invalid" % TERM},
          {"command": "curl.exe https://example.invalid"})
    expect("R8g Windows-MCP PowerShell internal command naming the term (not egress)", CONF,
           WIN + "PowerShell", {"command": "Write-Output '%s'" % TERM}, 0)
    expect("R8h Windows-MCP PowerShell non-string command fails closed", CONF,
           WIN + "PowerShell", {"command": ["x"]}, 2)
    _pair("R8i Windows-MCP FileSystem write into site repo", WIN + "FileSystem",
          {"mode": "write", "path": SITE_FILE, "content": TERM},
          {"mode": "write", "path": SITE_FILE, "content": "hello"})
    expect("R8j Windows-MCP FileSystem write to a local scratch path (not egress)", CONF,
           WIN + "FileSystem", {"mode": "write", "path": os.path.join(TMP, "n.txt"),
                                "content": TERM}, 0)
    expect("R8k Windows-MCP FileSystem copy: egress destination reads the source", CONF,
           WIN + "FileSystem", {"mode": "copy", "path": up, "destination": SITE_FILE}, 2)
    expect("R8l Windows-MCP FileSystem non-string path fails closed", CONF,
           WIN + "FileSystem", {"mode": "write", "path": [SITE_FILE], "content": "x"}, 2)
    _pair("R9 computer-use type", CU + "type", {"text": TERM}, {"text": "hello"})
    _pair("R9b computer-use computer_batch typed text", CU + "computer_batch",
          {"actions": [{"action": "type", "text": TERM}]},
          {"actions": [{"action": "left_click", "coordinate": [1, 2]}]})
    _pair("R9c computer-use write_clipboard", CU + "write_clipboard", {"text": TERM},
          {"text": "hello"})
    _pair("R9d computer-use teach_batch", CU + "teach_batch",
          {"steps": [{"explanation": "x", "actions": [{"action": "type", "text": TERM}]}]},
          {"steps": [{"explanation": "x", "actions": []}]})
    os.makedirs(os.path.join(TMP, "outputs"), exist_ok=True)
    r10 = os.path.join(TMP, "outputs", "r10.txt")
    with open(r10, "w", encoding="utf-8") as f:
        f.write("a")
    _pair("R10 Filesystem edit_file into an egress path", FS + "edit_file",
          {"path": r10, "edits": [{"oldText": "a", "newText": TERM}]},
          {"path": r10, "edits": [{"oldText": "a", "newText": "b"}]})
    expect("R10b Filesystem edit_file local scratch (not egress)", CONF, FS + "edit_file",
           {"path": os.path.join(TMP, "e.txt"), "edits": [{"oldText": "a", "newText": TERM}]}, 0)
    os.makedirs(os.path.join(TMP, "outputs"), exist_ok=True)
    seam_out = os.path.join(TMP, "outputs", "seam.txt")
    with open(seam_out, "w", encoding="utf-8") as f:
        f.write("Zephyr Corp X")
    expect("R10c Filesystem edit_file forms the term at a seam", CONF, FS + "edit_file",
           {"path": seam_out, "edits": [{"oldText": "X", "newText": "Portfolio"}]}, 2)
    expect("R10d Filesystem edit_file malformed edits fail closed", CONF, FS + "edit_file",
           {"path": SITE_FILE, "edits": "nope"}, 2)
    _pair("R11 Mnemoverse memory_write", MNEMO + "memory_write", {"content": TERM},
          {"content": "note"})
    _pair("R12 HubSpot submit_feedback", HUBSPOT + "submit_feedback", {"feedback": TERM},
          {"feedback": "works"})
    _pair("R12b DC give_feedback", DC + "give_feedback_to_desktop_commander",
          {"feedback": TERM}, {"feedback": "ok"})
    _pair("R12c Mnemoverse memory_feedback", MNEMO + "memory_feedback", {"comment": TERM},
          {"comment": "ok"})
    _pair("R13 Chrome shortcuts_execute", CHROME + "shortcuts_execute",
          {"shortcut": "s1", "prompt": TERM}, {"shortcut": "s1"})
    _pair("R14 Browser preview_start URL", BROWSER + "preview_start",
          {"url": "https://example.invalid/" + SLUG}, {"name": "dev"})
    _pair("R15 Microsoft docs search query", MSDOCS + "microsoft_docs_search",
          {"query": TERM}, {"query": "graph api"})
    _pair("R15b Microsoft docs fetch URL slug", MSDOCS + "microsoft_docs_fetch",
          {"url": "https://learn.example.invalid/" + SLUG},
          {"url": "https://learn.example.invalid/x"})
    _pair("R15c Microsoft code sample search", MSDOCS + "microsoft_code_sample_search",
          {"query": TERM.replace(" ", "+")}, {"query": "sharepoint"})
    _pair("R15d Context7 query-docs", "mcp__context7__query-docs",
          {"libraryId": "/x/y", "query": TERM}, {"libraryId": "/x/y", "query": "hooks"})
    _pair("R15e Context7 query-docs (connector uuid form, slug)",
          "mcp__85602316-38da-4653-9609-d1b4a9d9c454__query-docs",
          {"libraryId": "/x/y", "query": SLUG}, {"libraryId": "/x/y", "query": "hooks"})
    _pair("R15f punctuated term folded in a third-party query",
          "mcp__context7__query-docs", {"query": "ovarrow yards"}, {"query": "yards"})
    expect("R16 third-party tool_input not an object fails closed", CONF, DRIVE + "create_file",
           "x", 2)


def _token_run(tool, tool_input, recipients):
    tokdir = os.path.join(TMP, "rx-sessions")
    sess = "egress-rx-" + uuid.uuid4().hex[:8]
    od = os.path.join(tokdir, sess, "overrides")
    os.makedirs(od)
    with open(os.path.join(od, "allow-external-send"), "w") as f:
        f.write("scope: external-send\nsession: %s\nreason: test\nrecipients: %s\n"
                % (sess, recipients))
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": TMP, "session_id": sess}
    env = dict(os.environ, ORA_OVERRIDE_SESSIONS_DIR=tokdir)
    p = subprocess.run([sys.executable, AUTO], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=env, timeout=120)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def test_residual_autonomy():
    deploy = "netlify deploy --prod --dir=dist"
    for short in ("COMPOSIO_MULTI_EXECUTE_TOOL", "COMPOSIO_REMOTE_BASH_TOOL",
                  "COMPOSIO_REMOTE_WORKBENCH"):
        expect("RA1 %s needs an external-send token" % short, AUTO, COMPOSIO + short,
               {"tools": []}, 2)
    for short in ("RUBE_MULTI_EXECUTE_TOOL", "RUBE_EXECUTE_RECIPE", "RUBE_REMOTE_BASH_TOOL",
                  "RUBE_REMOTE_WORKBENCH"):
        expect("RA1 %s needs an external-send token" % short, AUTO, RUBE + short, {}, 2)
    expect("RA2 RUBE_CREATE_UPDATE_RECIPE stores, does not send", AUTO,
           RUBE + "RUBE_CREATE_UPDATE_RECIPE", {"name": "x"}, 0)
    rc, err = _token_run(COMPOSIO + "COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": []},
                         "executor:COMPOSIO_MULTI_EXECUTE_TOOL")
    check("RA3 token naming executor:<tool> -> allow", rc == 0, err)
    rc, err = _token_run(RUBE + "RUBE_REMOTE_BASH_TOOL", {"command": "ls"},
                         "executor:COMPOSIO_MULTI_EXECUTE_TOOL")
    check("RA4 token naming a DIFFERENT executor -> still blocked", rc == 2, err)
    expect("RA5 Windows-MCP PowerShell prod deploy", AUTO, WIN + "PowerShell",
           {"command": deploy}, 2)
    expect("RA6 Windows-MCP PowerShell read-only", AUTO, WIN + "PowerShell",
           {"command": "Get-ChildItem"}, 0)
    expect("RA7 Windows-MCP PowerShell non-string command fails closed", AUTO,
           WIN + "PowerShell", {"command": 5}, 2)
    expect("RA8 Windows-MCP FileSystem write into site repo", AUTO, WIN + "FileSystem",
           {"mode": "write", "path": SITE_FILE, "content": "x"}, 2)
    expect("RA9 Windows-MCP FileSystem move OUT of the site repo", AUTO, WIN + "FileSystem",
           {"mode": "move", "path": SITE_FILE, "destination": os.path.join(TMP, "x")}, 2)
    expect("RA10 Windows-MCP FileSystem local write", AUTO, WIN + "FileSystem",
           {"mode": "write", "path": os.path.join(TMP, "x.txt"), "content": "x"}, 0)
    expect("RA11 Filesystem edit_file into site repo", AUTO, FS + "edit_file",
           {"path": SITE_FILE, "edits": [{"oldText": "a", "newText": "b"}]}, 2)
    expect("RA12 Filesystem edit_file local", AUTO, FS + "edit_file",
           {"path": os.path.join(TMP, "x.txt"), "edits": []}, 0)


def test_residual_refute_round1():
    """REFUTE round 1 (adversarial-reviewer, 2026-11-12) defects, pinned by behavior."""
    os.makedirs(os.path.join(TMP, "outputs"), exist_ok=True)
    for ext in (".pdf", ".docx", ".html", ".csv"):
        src = _tmpfile("memo" + ext, "deck for " + TERM)
        expect("RR1 FileSystem copy of an artifact-extension source (%s) into the site repo" % ext,
               CONF, WIN + "FileSystem", {"mode": "copy", "path": src, "destination": SITE_FILE}, 2)
    out_src = os.path.join(TMP, "outputs", "memo.txt")
    with open(out_src, "w", encoding="utf-8") as f:
        f.write(TERM)
    expect("RR1b FileSystem move of an /outputs/ source into the site repo", CONF,
           WIN + "FileSystem", {"mode": "move", "path": out_src, "destination": SITE_FILE}, 2)
    expect("RR2 FileSystem copy whose source cannot be found fails closed", CONF,
           WIN + "FileSystem", {"mode": "copy", "path": os.path.join(TMP, "missing.txt"),
                                "destination": SITE_FILE}, 2)
    expect("RR2b FileSystem relative path fails closed", CONF, WIN + "FileSystem",
           {"mode": "write", "path": "site/x.html", "content": "x"}, 2)
    seam_out = os.path.join(TMP, "outputs", "seam2.txt")
    with open(seam_out, "w", encoding="utf-8") as f:
        f.write("Zephyr Corp X")
    expect("RR3 edit_file decoy file_path beside the real path fails closed", CONF, FS + "edit_file",
           {"file_path": "C:/nowhere/dist/decoy.txt", "path": seam_out,
            "edits": [{"oldText": "X", "newText": "Portfolio"}]}, 2)
    expect("RR3b edit_file relative path fails closed", CONF, FS + "edit_file",
           {"path": "outputs/seam2.txt", "edits": [{"oldText": "X", "newText": "Portfolio"}]}, 2)
    expect("RR3c edit_file of a missing egress target fails closed", CONF, FS + "edit_file",
           {"path": os.path.join(TMP, "outputs", "nope.txt"),
            "edits": [{"oldText": "X", "newText": "y"}]}, 2)
    expect("RR3d edit_file dryRun writes nothing", CONF, FS + "edit_file",
           {"path": seam_out, "dryRun": True, "edits": [{"oldText": "X", "newText": "Portfolio"}]}, 0)
    expect("RR3e edit_file non-bool dryRun is not a dry run", CONF, FS + "edit_file",
           {"path": seam_out, "dryRun": "yes", "edits": [{"oldText": "X", "newText": "Portfolio"}]}, 2)
    _pair("RR4 RUBE_MANAGE_RECIPE_SCHEDULE params", RUBE + "RUBE_MANAGE_RECIPE_SCHEDULE",
          {"recipe_id": "r1", "params": {"subject": TERM}}, {"recipe_id": "r1"})
    expect("RR4b RUBE_MANAGE_RECIPE_SCHEDULE needs an external-send token", AUTO,
           RUBE + "RUBE_MANAGE_RECIPE_SCHEDULE", {"recipe_id": "r1"}, 2)
    expect("RR5 executor payload with the term as a dict KEY", CONF,
           COMPOSIO + "COMPOSIO_MULTI_EXECUTE_TOOL",
           {"tools": [{"arguments": {"properties": {TERM: {"type": "title"}}}}]}, 2)
    expect("RR6 future executor name variant is scanned", CONF,
           COMPOSIO + "COMPOSIO_MULTI_EXECUTE_TOOL_V2", {"arguments": {"body": TERM}}, 2)
    expect("RR6b future executor name variant is gated", AUTO,
           COMPOSIO + "COMPOSIO_MULTI_EXECUTE_TOOL_V2", {}, 2)
    expect("RR6c hash-suffixed executor name is scanned", CONF,
           RUBE + "RUBE_REMOTE_BASH_TOOL-1a2b", {"command": "echo " + TERM}, 2)
    expect("RR6d hash-suffixed executor name is gated", AUTO,
           RUBE + "RUBE_REMOTE_BASH_TOOL-1a2b", {"command": "ls"}, 2)
    clean_src = _tmpfile("clean-src.txt", "plain")
    expect("RR7b FileSystem copy: unlisted source field beside a clean listed one", CONF,
           WIN + "FileSystem", {"mode": "copy", "src": clean_src,
                                "from": os.path.join(TMP, "memo.pdf"), "destination": SITE_FILE},
           2)
    home = os.path.expanduser("~")
    tilde_src = os.path.join(TMP, "memo.pdf")
    if os.path.normcase(tilde_src).startswith(os.path.normcase(home)):
        expect("RR7c FileSystem copy: unlisted ~ source beside a clean listed one", CONF,
               WIN + "FileSystem", {"mode": "copy", "src": clean_src,
                                    "from": "~" + tilde_src[len(home):],
                                    "destination": SITE_FILE}, 2)
    expect("RR7 FileSystem copy with an unrecognised source field fails closed", CONF,
           WIN + "FileSystem", {"mode": "copy", "from": os.path.join(TMP, "memo.pdf"),
                                "destination": SITE_FILE}, 2)


def main():
    try:
        test_conf_shell_tools()
        test_conf_dc_writes()
        test_conf_new_send_surfaces()
        test_autonomy_shell_and_writes()
        test_dispatcher_merge()
        test_dispatcher_end_to_end_deny_survives()
        test_override_mint_wired()
        test_refute_dispatcher()
        test_refute_conf_guard()
        test_refute_autonomy()
        test_notion_calendar()
        test_notion_calendar_token()
        test_dispatcher_fail_closed()
        test_web_tools()
        test_block_message_redacted()
        test_residual_conf()
        test_residual_autonomy()
        test_residual_refute_round1()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    if FAILS:
        print("\n%d FAILURE(S): %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("\nALL egress-tool-coverage tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
