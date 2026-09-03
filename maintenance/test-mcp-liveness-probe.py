#!/usr/bin/env python3
"""Tests for mcp-liveness-probe.py (TDD).

Runs the probe as a subprocess against a synthetic ~/.claude.json whose mcpServers
point at (a) a fake stdio MCP server (this file, re-invoked with FAKE_MCP_MODE) and
(b) a fake Streamable-HTTP MCP server started in-process. Asserts the exit-code
contract (0 all live / 1 finding / 2 probe error) and the finding classes:
DOWN (connect/handshake failure), ZERO_TOOLS (connected, tools/list empty),
PROTOCOL (malformed reply), plus an unsupported transport type.

Run: python test-mcp-liveness-probe.py
Pure stdlib. ASCII-only output.
"""
import os
import sys
import json
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
        import time
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

    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        if "id" not in body:
            self.send_response(202); self.end_headers(); return
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


def _start_http(ntools, sse):
    cls = type("H", (_FakeHttp,), {"ntools": ntools, "sse": sse})
    srv = HTTPServer(("127.0.0.1", 0), cls)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    return srv, "http://127.0.0.1:%d/mcp" % srv.server_address[1]


def _stop_http(srv):
    srv.shutdown()
    srv.server_close()   # release the listening socket (ResourceWarning under -W error otherwise)


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------
_failures = []


def _write_claude_json(servers):
    fd, path = tempfile.mkstemp(prefix="mlp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
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


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if (detail and not cond) else ""))
    if not cond:
        _failures.append(name)


def main():
    rc, out = _run({"good": _stdio("ok", 3)})
    check("stdio ok -> exit 0", rc == 0, out)
    check("stdio ok reports tool count", "tools=3" in out, out)

    rc, out = _run({"empty": _stdio("ok", 0)})
    check("stdio zero tools -> exit 1", rc == 1, out)
    check("stdio zero tools -> ZERO_TOOLS class", "ZERO_TOOLS" in out, out)

    rc, out = _run({"dead": _stdio("crash")})
    check("stdio crash -> exit 1", rc == 1, out)
    check("stdio crash -> DOWN class", "DOWN" in out, out)

    rc, out = _run({"hung": _stdio("hang")}, extra=["--timeout=3"])
    check("stdio hang -> exit 1 within timeout", rc == 1, out)
    check("stdio hang -> DOWN class (timeout)", "DOWN" in out and "timeout" in out.lower(), out)

    rc, out = _run({"garbage": _stdio("garbage")})
    check("stdio garbage reply -> exit 1", rc == 1, out)
    check("stdio garbage reply -> PROTOCOL class", "PROTOCOL" in out, out)

    rc, out = _run({"nocmd": {"type": "stdio", "command": "definitely-not-a-real-binary-xyz", "args": []}})
    check("stdio missing binary -> exit 1 SPAWN (environment miss, never DOWN)",
          rc == 1 and "SPAWN" in out and "DOWN" not in out, out)

    cj = _write_claude_json({"good": _stdio("ok", 1)})
    r = subprocess.run([sys.executable, PROBE, "--claude-json=" + cj, "--only=nope"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    check("--only unknown name -> exit 2 naming the key", r.returncode == 2 and "nope" in (r.stdout + r.stderr), r.stdout + r.stderr)

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

    rc, out = _run({"webdown": {"type": "http", "url": "http://127.0.0.1:9/mcp"}})
    check("http refused -> exit 1 DOWN", rc == 1 and "DOWN" in out, out)

    rc, out = _run({"weird": {"type": "carrier-pigeon", "url": "x"}})
    check("unsupported transport -> exit 1 finding, not crash", rc == 1 and "UNSUPPORTED" in out, out)

    rc, out = _run({"good": _stdio("ok", 3), "empty": _stdio("ok", 0)})
    check("mixed: one finding -> exit 1 and the good one still reported", rc == 1 and "good" in out and "ZERO_TOOLS" in out, out)

    rc, out = _run({})
    check("no servers configured -> exit 1 finding", rc == 1 and "NO_SERVERS" in out, out)

    # probe error: unreadable claude.json
    r = subprocess.run([sys.executable, PROBE, "--claude-json=" + os.path.join(tempfile.gettempdir(), "does-not-exist-mlp.json")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("missing claude.json -> exit 2", r.returncode == 2, r.stdout + r.stderr)

    # --json output is machine-readable
    cj = _write_claude_json({"good": _stdio("ok", 1)})
    r = subprocess.run([sys.executable, PROBE, "--claude-json=" + cj, "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        j = json.loads(r.stdout)
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
