"""Throwaway adversarial harness for hooks/ora-autonomy-gate.py. Spawns the hook
as a subprocess with each payload on stdin and checks exit code (2=block, 0=pass)."""
import json, subprocess, sys, os

PY = sys.executable
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ora-autonomy-gate.py")

def run(name, payload, expect):
    p = subprocess.run([PY, HOOK], input=json.dumps(payload).encode(),
                       capture_output=True)
    got = "BLOCK" if p.returncode == 2 else ("PASS" if p.returncode == 0 else f"ERR{p.returncode}")
    flag = "OK " if got == expect else ">>> MISMATCH"
    print(f"{flag} got={got:5} expect={expect:5} | {name}")
    return got == expect

E = "broker" + "@cbre.com"          # external
L = "lawyer" + "@external.com"      # external
I = "ggoldberg" + "@oxfordra.net"   # internal

cases = [
 # GATE 1 — email
 ("ext -To",                {"tool_name":"Bash","tool_input":{"command":f"send-via-outlook.ps1 -To {E} -Subject hi"}}, "BLOCK"),
 ("internal -To",           {"tool_name":"Bash","tool_input":{"command":f"send-via-outlook.ps1 -To {I}"}}, "PASS"),
 ("internal To + ext Cc",   {"tool_name":"Bash","tool_input":{"command":f"send-via-outlook.ps1 -To {I} -Cc {L}"}}, "BLOCK"),
 ("ADV ext -Bcc, NO -To",   {"tool_name":"Bash","tool_input":{"command":f"send-via-outlook.ps1 -Bcc {E} -Subject x"}}, "BLOCK"),
 # GATE 2 — netlify prod
 ("netlify deploy --prod",  {"tool_name":"Bash","tool_input":{"command":"netlify deploy --prod"}}, "BLOCK"),
 ("npx netlify-cli --prod", {"tool_name":"Bash","tool_input":{"command":"npx netlify-cli deploy --prod --dir=dist"}}, "BLOCK"),
 ("preview (no --prod)",    {"tool_name":"Bash","tool_input":{"command":"netlify deploy --dir=dist"}}, "PASS"),
 ("echo phrase only",       {"tool_name":"Bash","tool_input":{"command":"echo run netlify deploy --prod later"}}, "PASS"),
 # GATE 2 — site writes
 ("Write website-canonical",{"tool_name":"Write","tool_input":{"file_path":"C:/Users/Owner/website-canonical/index.html"}}, "BLOCK"),
 ("Edit oxford-site",       {"tool_name":"Edit","tool_input":{"file_path":"C:/Users/Owner/oxford-site/i.html"}}, "BLOCK"),
 ("ADV Bash write to site",  {"tool_name":"Bash","tool_input":{"command":"echo x > C:/Users/Owner/website-canonical/index.html"}}, "BLOCK"),
 ("ADV MCP netlify deploy", {"tool_name":"mcp__x__netlify-deploy-services-updater","tool_input":{"production":True}}, "BLOCK"),
 ("MCP netlify project upd", {"tool_name":"mcp__x__netlify-project-services-updater","tool_input":{}}, "BLOCK"),
 ("MCP netlify READER ok",   {"tool_name":"mcp__x__netlify-project-services-reader","tool_input":{}}, "PASS"),
 ("MCP non-netlify ok",      {"tool_name":"mcp__x__notion-create-pages","tool_input":{}}, "PASS"),
 ("ADV site write via cp",   {"tool_name":"Bash","tool_input":{"command":"cp /tmp/x.html C:/Users/Owner/oxford-site/index.html"}}, "BLOCK"),
 ("read site file ok",       {"tool_name":"Bash","tool_input":{"command":"cat C:/Users/Owner/website-canonical/index.html"}}, "PASS"),
 ("chained && prod deploy",  {"tool_name":"Bash","tool_input":{"command":"cd /c/x && netlify deploy --prod --dir deploy"}}, "BLOCK"),
 ("powershell -File ext send",{"tool_name":"Bash","tool_input":{"command":f'powershell.exe -File "send-via-outlook.ps1" -To "{E}"'}}, "BLOCK"),
 ("log mention no trip",     {"tool_name":"Bash","tool_input":{"command":"append-event-log.py \"blocks netlify deploy --prod via hook\""}}, "PASS"),
 # fail-open
 ("malformed input",        "NOT_A_DICT_SENTINEL", "PASS"),
]

ok = 0
for name, payload, expect in cases:
    if payload == "NOT_A_DICT_SENTINEL":
        p = subprocess.run([PY, HOOK], input=b"not json", capture_output=True)
        got = "BLOCK" if p.returncode==2 else ("PASS" if p.returncode==0 else f"ERR{p.returncode}")
        good = got==expect; print(f"{'OK ' if good else '>>> MISMATCH'} got={got:5} expect={expect:5} | {name}")
    else:
        good = run(name, payload, expect)
    ok += good
print(f"\n{ok}/{len(cases)} as-expected")
sys.exit(0 if ok == len(cases) else 1)
