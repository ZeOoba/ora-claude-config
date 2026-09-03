#!/usr/bin/env python3
"""ORA MCP connector LIVENESS probe (Health Guard Block C).

WHY THIS EXISTS
---------------
connector-drift-probe.py reconciles the documented roster against CONFIG presence
(a key in ~/.claude.json, an allow-prefix in settings.json). Config presence is not
liveness: a server can be registered, start, answer `initialize`, and surface ZERO
tools -- and every existing check reads that as healthy. Automation Audit Rev 21
(2026-09-02) asked for the missing check: actually connect, actually call
`tools/list`, and alarm when nothing comes back.

WHAT IT PROBES
--------------
Every entry under `mcpServers` in ~/.claude.json -- the set of locally-registered
stdio / Streamable-HTTP servers (as of 2026-09-03: excel, fred, context7). Each is
driven through the real MCP handshake: `initialize` -> `notifications/initialized`
-> `tools/list`, and the returned tool count is the liveness signal.

Cloud-managed connectors (Notion, HubSpot, M365, Netlify, plugins) are NOT reachable
from a subprocess -- they exist only inside a live Claude session -- so they are out
of scope BY CONSTRUCTION, not by omission. Health Guard B.1 covers them with real
in-session tool calls. This probe says so in its output rather than silently
narrowing the scan set (memory: reference_probe_scan_sets).

FINDING CLASSES (exit 1)
------------------------
  SPAWN        the configured command cannot be resolved/started from THIS process --
               an environment miss (PATH), never a server outage. Scheduled sessions
               carry a narrower PATH than an interactive shell (`uv` lives on the
               user-scope PATH only), so the probe also searches the user-scope registry PATH (HKCU / Environment / Path).
  DOWN         started/connected but cannot complete the handshake within --timeout
  PROTOCOL     connected but the reply is not valid JSON-RPC / MCP
  ZERO_TOOLS   handshake OK, `tools/list` returned an empty list
  UNSUPPORTED  transport type this probe cannot drive (reported, never skipped)
  NO_SERVERS   ~/.claude.json has no mcpServers at all (roster expects some)

Exit 0 = every server live with >= 1 tool; exit 1 = one or more findings;
exit 2 = probe error (unreadable/unparseable ~/.claude.json) -- fail loud.

Usage: python mcp-liveness-probe.py [--quiet] [--json] [--timeout=SECONDS]
       [--claude-json=PATH] [--only=NAME]
"""
import os
import sys
import json
import time
import queue
import shutil
import threading
import subprocess
import urllib.request
import urllib.error

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
DEFAULT_CLAUDE_JSON = os.path.join(HOME, ".claude.json")
DEFAULT_TIMEOUT = 45.0          # `uv run` cold-starts can take 10-20s on this laptop
PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "ora-mcp-liveness-probe", "version": "1.0"}
CLOUD_NOTE = ("cloud-managed connectors (Notion, HubSpot, M365, Netlify, plugins) are not "
              "reachable from a subprocess -- covered by Health Guard B.1 in-session calls, "
              "not by this probe")


def die(msg):
    print("[ACTION] mcp-liveness-probe: %s" % msg, file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    opts = {"claude_json": DEFAULT_CLAUDE_JSON, "quiet": False, "json": False,
            "timeout": DEFAULT_TIMEOUT, "only": None}
    for a in argv:
        if a == "--quiet":
            opts["quiet"] = True
        elif a == "--json":
            opts["json"] = True
        elif a.startswith("--claude-json="):
            opts["claude_json"] = a.split("=", 1)[1]
        elif a.startswith("--timeout="):
            try:
                opts["timeout"] = float(a.split("=", 1)[1])
            except ValueError:
                die("bad --timeout value: %s" % a)
        elif a.startswith("--only="):
            opts["only"] = a.split("=", 1)[1]
        else:
            die("unknown option: %s" % a)
    return opts


def read_servers(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception as e:
        die("cannot read/parse %s: %s" % (path, e))
    if not isinstance(obj, dict):
        die("%s is not a JSON object" % path)
    servers = obj.get("mcpServers") or {}
    if not isinstance(servers, dict):
        die("mcpServers in %s is not an object" % path)
    return servers


def _rpc(id_, method, params=None):
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def _init_params():
    return {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO}


def _tool_names(result):
    tools = (result or {}).get("tools")
    if not isinstance(tools, list):
        raise ValueError("tools/list result has no 'tools' list")
    return [str(t.get("name", "?")) for t in tools if isinstance(t, dict)]


# --------------------------------------------------------------------------
# stdio transport
# --------------------------------------------------------------------------
def _user_scope_path_dirs():
    """User-scope PATH entries from HKCU\\Environment\\Path (Windows). A scheduled
    session may inherit only the machine PATH, which lacks `uv`/python on this laptop."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, "Path")
        return [os.path.expandvars(x) for x in str(val).split(os.pathsep) if x.strip()]
    except Exception:
        return []


def _resolve_command(cmd0):
    """(resolved_path, note) or (None, None). Tries the literal path, this process's PATH,
    then the user-scope PATH so an environment miss is never read as a server outage."""
    if os.path.isabs(cmd0):
        return (cmd0, None) if os.path.exists(cmd0) else (None, None)
    found = shutil.which(cmd0)
    if found:
        return found, None
    extra = _user_scope_path_dirs()
    if extra:
        found = shutil.which(cmd0, path=os.pathsep.join([os.environ.get("PATH", "")] + extra))
        if found:
            return found, "resolved via user-scope PATH (HKCU\\Environment), not this process's PATH"
    return None, None


def probe_stdio(cfg, timeout):
    cmd = [cfg.get("command") or ""] + list(cfg.get("args") or [])
    if not cmd[0]:
        return {"class": "SPAWN", "error": "no command configured"}
    resolved, note = _resolve_command(cmd[0])
    if not resolved:
        return {"class": "SPAWN", "error": "command %r not found on this process's PATH nor the "
                "user-scope PATH -- environment miss, not a server outage" % cmd[0]}
    cmd[0] = resolved
    env = dict(os.environ)
    extra = _user_scope_path_dirs()
    if extra:  # let `uv run` etc. find their own tools even under a narrow PATH
        env["PATH"] = os.pathsep.join([env.get("PATH", "")] + [d for d in extra if d not in env.get("PATH", "")])
    for k, v in (cfg.get("env") or {}).items():
        env[str(k)] = str(v)
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, cwd=cfg.get("cwd") or None)
    except FileNotFoundError as e:
        return {"class": "SPAWN", "error": "spawn failed (not found): %s" % e}
    except Exception as e:
        return {"class": "DOWN", "error": "spawn failed: %s" % e}

    lines = queue.Queue()
    err_tail = []

    def _reader():
        try:
            for raw in proc.stdout:
                lines.put(raw)
        except Exception:
            pass
        lines.put(None)

    def _drain_err():
        try:
            for raw in proc.stderr:
                if len(err_tail) < 20:
                    err_tail.append(raw.decode("utf-8", "replace").rstrip())
        except Exception:
            pass

    threading.Thread(target=_reader, daemon=True).start()
    threading.Thread(target=_drain_err, daemon=True).start()

    def _send(msg):
        proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        proc.stdin.flush()

    def _recv(want_id):
        """Return the parsed response for want_id, or raise."""
        while True:
            remaining = timeout - (time.time() - t0)
            if remaining <= 0:
                raise TimeoutError("timeout after %.0fs waiting for id %s" % (timeout, want_id))
            try:
                raw = lines.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError("timeout after %.0fs waiting for id %s" % (timeout, want_id))
            if raw is None:
                try:
                    rc = proc.wait(timeout=2)   # EOF usually precedes reaping; get the real code
                except Exception:
                    rc = proc.poll()
                raise ConnectionError("server closed stdout before answering id %s (exit=%s)%s"
                                      % (want_id, rc, (" stderr: " + " | ".join(err_tail[-3:])) if err_tail else ""))
            text = raw.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                msg = json.loads(text)
            except ValueError:
                raise ValueError("non-JSON line on stdout: %r" % text[:120])
            if isinstance(msg, dict) and msg.get("id") == want_id:
                if "error" in msg:
                    raise ValueError("JSON-RPC error for id %s: %s" % (want_id, msg["error"]))
                return msg.get("result")
            # notifications / unrelated ids: keep reading

    try:
        try:
            _send(_rpc(1, "initialize", _init_params()))
            init = _recv(1)
            _send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            _send(_rpc(2, "tools/list", {}))
            res = _recv(2)
        except (TimeoutError, ConnectionError, BrokenPipeError, OSError) as e:
            return {"class": "DOWN", "error": str(e), "elapsed": round(time.time() - t0, 1)}
        except ValueError as e:
            return {"class": "PROTOCOL", "error": str(e), "elapsed": round(time.time() - t0, 1)}
        try:
            names = _tool_names(res)
        except ValueError as e:
            return {"class": "PROTOCOL", "error": str(e), "elapsed": round(time.time() - t0, 1)}
        server_name = ((init or {}).get("serverInfo") or {}).get("name")
        rec = {"class": "ZERO_TOOLS" if not names else "OK", "tools": len(names),
               "tool_names": names[:8], "server": server_name,
               "elapsed": round(time.time() - t0, 1)}
        if note:
            rec["note"] = note
        return rec
    finally:
        # Teardown order matters: close stdin (polite EOF), kill, WAIT so the handle is
        # reaped (kill is asynchronous on Windows), then close the pipes the reader
        # threads were on. Skipping the wait/close leaks the process handle and the
        # BufferedReaders -- visible under `python -W error` as ResourceWarnings.
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except Exception:
            pass
        for fh in (proc.stdout, proc.stderr):
            try:
                fh.close()
            except Exception:
                pass


# --------------------------------------------------------------------------
# Streamable-HTTP transport
# --------------------------------------------------------------------------
def _http_post(url, body, headers, timeout):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("MCP-Protocol-Version", PROTOCOL_VERSION)
    for k, v in headers.items():
        req.add_header(k, v)
    resp = urllib.request.urlopen(req, timeout=timeout)
    ctype = (resp.headers.get("Content-Type") or "").lower()
    sid = resp.headers.get("Mcp-Session-Id")
    raw = resp.read().decode("utf-8", "replace")
    return resp.status, ctype, sid, raw


def _parse_http_body(status, ctype, raw, want_id):
    if status == 202 or not raw.strip():
        return None
    candidates = []
    if "text/event-stream" in ctype:
        for line in raw.splitlines():
            if line.startswith("data:"):
                candidates.append(line[5:].strip())
    else:
        candidates.append(raw)
    for c in candidates:
        try:
            msg = json.loads(c)
        except ValueError:
            continue
        if isinstance(msg, dict) and msg.get("id") == want_id:
            if "error" in msg:
                raise ValueError("JSON-RPC error for id %s: %s" % (want_id, msg["error"]))
            return msg.get("result")
    raise ValueError("no JSON-RPC response for id %s in HTTP body (%s): %r"
                     % (want_id, ctype or "no content-type", raw[:120]))


def probe_http(cfg, timeout):
    url = cfg.get("url")
    if not url:
        return {"class": "DOWN", "error": "no url configured"}
    headers = {str(k): str(v) for k, v in (cfg.get("headers") or {}).items()}
    t0 = time.time()
    try:
        status, ctype, sid, raw = _http_post(url, _rpc(1, "initialize", _init_params()), headers, timeout)
        init = _parse_http_body(status, ctype, raw, 1)
        if sid:
            headers["Mcp-Session-Id"] = sid
        try:
            _http_post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers, timeout)
        except urllib.error.HTTPError:
            pass  # some servers 4xx a bare notification; tools/list is the real test
        status, ctype, _, raw = _http_post(url, _rpc(2, "tools/list", {}), headers, timeout)
        res = _parse_http_body(status, ctype, raw, 2)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        return {"class": "DOWN", "error": str(e), "elapsed": round(time.time() - t0, 1)}
    except ValueError as e:
        return {"class": "PROTOCOL", "error": str(e), "elapsed": round(time.time() - t0, 1)}
    try:
        names = _tool_names(res)
    except ValueError as e:
        return {"class": "PROTOCOL", "error": str(e), "elapsed": round(time.time() - t0, 1)}
    server_name = ((init or {}).get("serverInfo") or {}).get("name")
    return {"class": "ZERO_TOOLS" if not names else "OK", "tools": len(names),
            "tool_names": names[:8], "server": server_name,
            "elapsed": round(time.time() - t0, 1)}


# --------------------------------------------------------------------------
def probe_one(name, cfg, timeout):
    ttype = (cfg.get("type") or ("stdio" if cfg.get("command") else "http" if cfg.get("url") else "")).lower()
    if ttype == "stdio":
        r = probe_stdio(cfg, timeout)
    elif ttype in ("http", "streamable-http", "streamable_http"):
        r = probe_http(cfg, timeout)
    elif ttype == "sse":
        r = {"class": "UNSUPPORTED", "error": "legacy SSE transport not driven by this probe"}
    else:
        r = {"class": "UNSUPPORTED", "error": "unknown transport type %r" % ttype}
    r["name"] = name
    r["transport"] = ttype or "?"
    return r


def main():
    opts = parse_args(sys.argv[1:])
    servers = read_servers(opts["claude_json"])
    results = []
    if opts["only"]:
        if opts["only"] not in servers:
            die("--only=%s: no such mcpServers key in %s (have: %s)"
                % (opts["only"], opts["claude_json"], ", ".join(sorted(servers)) or "none"))
        servers = {opts["only"]: servers[opts["only"]]}
    if not servers:
        results.append({"name": "(none)", "transport": "-", "class": "NO_SERVERS",
                        "error": "no mcpServers configured in %s" % opts["claude_json"]})
    for name in sorted(servers):
        cfg = servers[name]
        if not isinstance(cfg, dict):
            results.append({"name": name, "transport": "?", "class": "PROTOCOL",
                            "error": "server config is not an object"})
            continue
        results.append(probe_one(name, cfg, opts["timeout"]))

    findings = [r for r in results if r["class"] != "OK"]
    verdict = "OK" if not findings else "FINDINGS"

    if opts["json"]:
        print(json.dumps({"verdict": verdict, "probed": len(results),
                          "findings": len(findings), "servers": results,
                          "scope_note": CLOUD_NOTE}, indent=1))
        sys.exit(1 if findings else 0)

    if findings:
        print("MCP LIVENESS: %d of %d locally-registered server(s) NOT healthy:"
              % (len(findings), len(results)))
    elif not opts["quiet"]:
        print("mcp-liveness-probe OK -- %d locally-registered MCP server(s) answered tools/list with >=1 tool."
              % len(results))
    for r in results:
        if r["class"] == "OK":
            line = "  [ OK ] %-12s %-6s tools=%d (%.1fs) %s" % (
                r["name"], r["transport"], r["tools"], r.get("elapsed", 0),
                ", ".join(r.get("tool_names", [])[:5]) + ("..." if r["tools"] > 5 else ""))
            if r.get("note"):
                line += "  [%s]" % r["note"]
        else:
            line = "  [%s] %-12s %-6s %s" % (r["class"], r["name"], r["transport"], r.get("error", ""))
            if "tools" in r:
                line += " tools=%d" % r["tools"]
        if r["class"] == "OK" and opts["quiet"]:
            continue
        print(line)
    if not opts["quiet"] or findings:
        print("  scope: %s" % CLOUD_NOTE)
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
