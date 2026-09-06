#!/usr/bin/env python3
"""Tests for mcp-liveness-probe.py (TDD).

Runs the probe as a subprocess against a synthetic ~/.claude.json whose mcpServers
point at (a) a fake stdio MCP server (this file, re-invoked with FAKE_MCP_MODE) and
(b) a fake Streamable-HTTP MCP server started in-process. Asserts the exit-code
contract (0 all live / 1 finding / 2 probe error) and the finding classes:
SPAWN (environment miss), DOWN (connect/handshake failure, refused redirect),
ZERO_TOOLS (connected, tools/list empty), PROTOCOL (malformed envelope, bad
InitializeResult, 202/empty body to a request, non-JSON line), UNSUPPORTED
(transport / URL scheme), plus CLI validation and the single-deadline rule.

Every generated config lives in one TemporaryDirectory that is removed at exit.

Run: python test-mcp-liveness-probe.py
Pure stdlib. ASCII-only output.
"""
import os
import sys
import json
import time
import tempfile
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "mcp-liveness-probe.py")

# --------------------------------------------------------------------------
# Fake stdio MCP server (runs when FAKE_MCP_MODE is set in the environment)
# --------------------------------------------------------------------------
def _fake_stdio_server():
    mode = os.environ.get("FAKE_MCP_MODE", "ok")
    ntools = int(os.environ.get("FAKE_MCP_TOOLS", "3"))
    if mode == "crash":
        sys.exit(3)
    if mode == "hang":
        time.sleep(600)
    out = sys.stdout.buffer
    for raw in sys.stdin.buffer:
        try:
            msg = json.loads(raw.decode("utf-8"))
        except ValueError:
            continue
        if "id" not in msg:
            continue  # notification
        if msg.get("method") == "initialize":
            if mode == "garbage":
                out.write(b"this is not json\n"); out.flush(); continue
            if mode == "badinit":      # right id, wrong shape: no protocolVersion / serverInfo
                resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {"hello": "world"}}
            elif mode == "badenvelope":  # no jsonrpc member at all
                resp = {"id": msg["id"], "result": {
                    "protocolVersion": "2025-03-26", "capabilities": {}, "serverInfo": {"name": "fake"}}}
            elif mode == "bothfields":   # result AND error
                resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {}, "error": {"code": 1, "message": "x"}}
            else:
                resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {
                    "protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake", "version": "0"}}}
        elif msg.get("method") == "tools/list":
            tools = [{"name": "tool_%d" % i, "inputSchema": {"type": "object"}}
                     for i in range(ntools)]
            resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}
        else:
            resp = {"jsonrpc": "2.0", "id": msg["id"],
                    "error": {"code": -32601, "message": "unknown"}}
        out.write((json.dumps(resp) + "\n").encode("utf-8")); out.flush()


# --------------------------------------------------------------------------
# Fake Streamable-HTTP MCP server
# --------------------------------------------------------------------------
class _FakeHttp(BaseHTTPRequestHandler):
    ntools = 2
    sse = False
    init_202 = False      # answer initialize with 202 + empty body (valid only for notifications)
    redirect = False      # answer every POST with 302
    delay = 0.0           # seconds to sleep before answering each request

    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        if self.delay:
            time.sleep(self.delay)
        if self.redirect:
            self.send_response(302); self.send_header("Location", "http://127.0.0.1:9/elsewhere")
            self.send_header("Content-Length", "0"); self.end_headers(); return
        if "id" not in body or (self.init_202 and body.get("method") == "initialize"):
            self.send_response(202); self.send_header("Content-Length", "0"); self.end_headers(); return
        if body.get("method") == "initialize":
            result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fake-http", "version": "0"}}
        else:
            result = {"tools": [{"name": "t%d" % i} for i in range(self.ntools)]}
        payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
        self.send_response(200)
        self.send_header("Mcp-Session-Id", "sess-1")
        if self.sse:
            self.send_header("Content-Type", "text/event-stream")
            data = ("event: message\ndata: %s\n\n" % payload).encode("utf-8")
        else:
            self.send_header("Content-Type", "application/json")
            data = payload.encode("utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class _QuietServer(HTTPServer):
    """When the probe's deadline closes the socket mid-reply (the slow-server test), the
    handler thread sees a connection reset; that is the expected outcome, not a failure."""
    def handle_error(self, request, client_address):
        import sys as _sys
        exc = _sys.exc_info()[1]
        if isinstance(exc, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def _start_http(ntools=2, sse=False, **attrs):
    cls = type("H", (_FakeHttp,), dict({"ntools": ntools, "sse": sse}, **attrs))
    srv = _QuietServer(("127.0.0.1", 0), cls)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    return srv, "http://127.0.0.1:%d/mcp" % srv.server_address[1]


def _stop_http(srv):
    srv.shutdown()
    srv.server_close()   # release the listening socket (ResourceWarning under -W error otherwise)


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------
_failures = []
_TMP = None   # tempfile.TemporaryDirectory; every generated config lives here and dies with it
_seq = [0]


def _write_claude_json(servers):
    _seq[0] += 1
    path = os.path.join(_TMP.name, "claude-%03d.json" % _seq[0])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"mcpServers": servers}, fh)
    return path


def _stdio(mode="ok", tools=3):
    return {"type": "stdio", "command": sys.executable,
            "args": [os.path.abspath(__file__)],
            "env": {"FAKE_MCP_MODE": mode, "FAKE_MCP_TOOLS": str(tools)}}


def _run(servers, extra=()):
    cj = _write_claude_json(servers)
    r = subprocess.run([sys.executable, PROBE, "--claude-json=" + cj, "--timeout=8"] + list(extra),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120)
    return r.returncode, r.stdout + r.stderr


def _run_raw(args):
    r = subprocess.run([sys.executable, PROBE] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return r.returncode, r.stdout + r.stderr


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if (detail and not cond) else ""))
    if not cond:
        _failures.append(name)


def main():
    global _TMP
    _TMP = tempfile.TemporaryDirectory(prefix="mlp-")
    try:
        _main()
    finally:
        _TMP.cleanup()


def _main():
    rc, out = _run({"good": _stdio("ok", 3)})
    check("stdio ok -> exit 0", rc == 0, out)
    check("stdio ok reports tool count", "tools=3" in out, out)

    rc, out = _run({"empty": _stdio("ok", 0)})
    check("stdio zero tools -> exit 1", rc == 1, out)
    check("stdio zero tools -> ZERO_TOOLS class", "ZERO_TOOLS" in out, out)

    rc, out = _run({"dead": _stdio("crash")})
    check("stdio crash -> exit 1", rc == 1, out)
    check("stdio crash -> DOWN class with real exit code", "DOWN" in out and "exit=3" in out, out)

    rc, out = _run({"hung": _stdio("hang")}, extra=["--timeout=3"])
    check("stdio hang -> exit 1 within timeout", rc == 1, out)
    check("stdio hang -> DOWN class (timeout)", "DOWN" in out and "timeout" in out.lower(), out)

    rc, out = _run({"garbage": _stdio("garbage")})
    check("stdio garbage reply -> exit 1", rc == 1, out)
    check("stdio garbage reply -> PROTOCOL class", "PROTOCOL" in out, out)

    rc, out = _run({"badinit": _stdio("badinit")})
    check("stdio InitializeResult without protocolVersion/serverInfo -> PROTOCOL, not OK",
          rc == 1 and "PROTOCOL" in out and "protocolVersion" in out, out)

    rc, out = _run({"badenv": _stdio("badenvelope")})
    check("stdio response without jsonrpc=2.0 -> PROTOCOL", rc == 1 and "PROTOCOL" in out and "jsonrpc" in out, out)

    rc, out = _run({"both": _stdio("bothfields")})
    check("stdio response with result AND error -> PROTOCOL", rc == 1 and "PROTOCOL" in out and "exactly one" in out, out)

    rc, out = _run({"nocmd": {"type": "stdio", "command": "definitely-not-a-real-binary-xyz", "args": []}})
    check("stdio missing binary -> exit 1 SPAWN (environment miss, never DOWN)",
          rc == 1 and "SPAWN" in out and "DOWN" not in out, out)

    cj = _write_claude_json({"good": _stdio("ok", 1)})
    rc, out = _run_raw(["--claude-json=" + cj, "--only=nope"])
    check("--only unknown name -> exit 2 naming the key", rc == 2 and "nope" in out, out)

    for bad in ("0", "-5", "nan", "inf", "abc", "9999"):
        rc, out = _run_raw(["--claude-json=" + cj, "--timeout=" + bad])
        check("--timeout=%s -> exit 2 (range/format validation)" % bad, rc == 2 and "timeout" in out.lower(), out)

    srv, url = _start_http(2, sse=False)
    rc, out = _run({"web": {"type": "http", "url": url}})
    check("http json ok -> exit 0", rc == 0, out)
    check("http json ok reports tools=2", "tools=2" in out, out)
    _stop_http(srv)

    srv, url = _start_http(4, sse=True)
    rc, out = _run({"websse": {"type": "http", "url": url}})
    check("http SSE ok -> exit 0 tools=4", rc == 0 and "tools=4" in out, out)
    _stop_http(srv)

    srv, url = _start_http(0, sse=False)
    rc, out = _run({"webzero": {"type": "http", "url": url}})
    check("http zero tools -> exit 1 ZERO_TOOLS", rc == 1 and "ZERO_TOOLS" in out, out)
    _stop_http(srv)

    srv, url = _start_http(2, init_202=True)
    rc, out = _run({"web202": {"type": "http", "url": url}})
    check("http 202/empty body to initialize -> PROTOCOL, never OK", rc == 1 and "PROTOCOL" in out and "202" in out, out)
    _stop_http(srv)

    srv, url = _start_http(2, redirect=True)
    rc, out = _run({"webredir": {"type": "http", "url": url}})
    check("http redirect -> DOWN (redirect refused, headers not replayed)", rc == 1 and "DOWN" in out and "redirect" in out.lower(), out)
    _stop_http(srv)

    srv, url = _start_http(2, delay=4.0)
    t0 = time.time()
    rc, out = _run({"webslow": {"type": "http", "url": url}}, extra=["--timeout=3"])
    elapsed = time.time() - t0
    check("http single deadline: 3 slow requests under --timeout=3 finish in ~3s, not 9s",
          rc == 1 and "DOWN" in out and elapsed < 7.5, "%s elapsed=%.1fs" % (out, elapsed))
    _stop_http(srv)

    rc, out = _run({"webdown": {"type": "http", "url": "http://127.0.0.1:9/mcp"}})
    check("http refused -> exit 1 DOWN", rc == 1 and "DOWN" in out, out)

    rc, out = _run({"ftp": {"type": "http", "url": "ftp://127.0.0.1/mcp"}})
    check("http with non-http scheme -> UNSUPPORTED, no request made", rc == 1 and "UNSUPPORTED" in out and "scheme" in out, out)

    rc, out = _run({"weird": {"type": "carrier-pigeon", "url": "x"}})
    check("unsupported transport -> exit 1 finding, not crash", rc == 1 and "UNSUPPORTED" in out, out)

    rc, out = _run({"good": _stdio("ok", 3), "empty": _stdio("ok", 0)})
    check("mixed: one finding -> exit 1 and the good one still reported", rc == 1 and "good" in out and "ZERO_TOOLS" in out, out)

    rc, out = _run({})
    check("no servers configured -> exit 1 finding", rc == 1 and "NO_SERVERS" in out, out)

    rc, out = _run_raw(["--claude-json=" + os.path.join(_TMP.name, "does-not-exist.json")])
    check("missing claude.json -> exit 2", rc == 2, out)

    cj = _write_claude_json({"good": _stdio("ok", 1)})
    rc, out = _run_raw(["--claude-json=" + cj, "--json"])
    try:
        j = json.loads(out)
        ok = j["servers"][0]["tools"] == 1 and j["verdict"] == "OK"
    except Exception as e:
        ok = False; j = str(e)
    check("--json emits parseable summary", ok, str(j)[:300])

    print("-" * 60)
    if _failures:
        print("FAILED: %d -- %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    if os.environ.get("FAKE_MCP_MODE"):
        _fake_stdio_server()
    else:
        main()
