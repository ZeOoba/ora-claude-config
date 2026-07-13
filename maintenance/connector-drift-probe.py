#!/usr/bin/env python3
"""ORA connector-drift probe.

Reconciles the machine-readable CONNECTOR ROSTER in memory/tech.md against live
registration state, so the doctrine docs can't silently drift from reality again.
This is the standing backstop for the 2026-07-12 audit finding, where FRED
(documented dead, actually live) and 3 connectors (Grain / Windows-MCP /
Claude Preview -- documented alive, actually dead) drifted simultaneously,
undetected, until a manual audit caught them.

LIVE SOURCES (local, unambiguous -- precision over recall):
  * ~/.claude.json  top-level `mcpServers` keys  (self-registered stdio servers)
  * ~/.claude/settings.json  `permissions.allow`  mcp__<prefix>__ entries

ROSTER FORMAT (between the markers in tech.md; one connector per line):
  - <name> | state=<active|retired> | verify=<signal>
  verify signals:
    json:<key>     liveness = <key> present in .claude.json mcpServers
    allow:<prefix> liveness = an mcp__<prefix>__ entry exists in settings.json allow
    cloud          claude.ai-managed; NOT locally verifiable -> never liveness-asserted

FINDINGS (exit 1):
  * state=active  but NOT live   -> documented-alive-but-dead (Grain class)
  * state=retired but live       -> documented-dead-but-alive (FRED class)
  * a .claude.json mcpServers key with NO `verify=json:<key>` roster line -> undocumented live connector

Exit 0 = consistent; exit 1 = drift; exit 2 = probe error (missing markers,
unknown verify scheme, unreadable/unparseable source -- fail loud, never silent).

Usage: python connector-drift-probe.py [--quiet]
       [--roster=PATH] [--claude-json=PATH] [--settings=PATH]   (testing overrides)
"""
import os
import sys
import json

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
MEM = os.path.join(CLAUDE, "projects",
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")

DEFAULT_ROSTER = os.path.join(MEM, "tech.md")
DEFAULT_CLAUDE_JSON = os.path.join(HOME, ".claude.json")
DEFAULT_SETTINGS = os.path.join(CLAUDE, "settings.json")

BEGIN_MARKER = "<!--BEGIN-CONNECTOR-ROSTER-->"
END_MARKER = "<!--END-CONNECTOR-ROSTER-->"


def die(msg):
    """Fail loud: print an [ACTION] line and exit 2 (probe error)."""
    print("[ACTION] connector-drift-probe: %s" % msg, file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    opts = {"roster": DEFAULT_ROSTER, "claude_json": DEFAULT_CLAUDE_JSON,
            "settings": DEFAULT_SETTINGS, "quiet": False}
    for a in argv:
        if a == "--quiet":
            opts["quiet"] = True
        elif a.startswith("--roster="):
            opts["roster"] = a.split("=", 1)[1]
        elif a.startswith("--claude-json="):
            opts["claude_json"] = a.split("=", 1)[1]
        elif a.startswith("--settings="):
            opts["settings"] = a.split("=", 1)[1]
        else:
            die("unknown option: %s" % a)
    return opts


def read_text(path, label):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception as e:
        die("cannot read %s (%s): %s" % (label, path, e))


def read_json(path, label):
    txt = read_text(path, label)
    try:
        return json.loads(txt)
    except ValueError as e:
        die("%s is not valid JSON (%s): %s" % (label, path, e))


def extract_roster_block(text):
    b = text.find(BEGIN_MARKER)
    if b == -1:
        die("roster BEGIN marker not found (%s)" % BEGIN_MARKER)
    if text.find(BEGIN_MARKER, b + len(BEGIN_MARKER)) != -1:
        die("roster BEGIN marker appears more than once")
    e = text.find(END_MARKER, b)
    if e == -1:
        die("roster END marker not found after BEGIN (%s)" % END_MARKER)
    return text[b + len(BEGIN_MARKER):e]


def parse_roster(block):
    """Return [(name, state, verify)] for each `- ...` line. Malformed line -> die."""
    entries = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue  # comment / blank lines inside the block
        body = line[2:]
        fields = {}
        name = None
        for i, part in enumerate(p.strip() for p in body.split("|")):
            if i == 0:
                name = part
                continue
            if "=" not in part:
                die("roster line malformed (field without '='): %r" % line)
            k, v = part.split("=", 1)
            fields[k.strip().lower()] = v.strip()
        state = fields.get("state")
        verify = fields.get("verify")
        if not name or state not in ("active", "retired") or not verify:
            die("roster line malformed (need name, state=active|retired, verify=..): %r" % line)
        entries.append((name, state, verify))
    if not entries:
        die("roster block contains no connector lines")
    return entries


def allow_prefixes(settings_obj):
    """Set of server prefixes from settings.json permissions.allow mcp__<prefix>__ entries."""
    out = set()
    allow = (settings_obj.get("permissions") or {}).get("allow") or []
    for a in allow:
        if isinstance(a, str) and a.startswith("mcp__"):
            rest = a[len("mcp__"):]
            seg = rest.split("__", 1)[0]
            if seg:
                out.add(seg.lower())
    return out


def is_live(verify, json_keys, prefixes):
    """(live_or_None, error). live_or_None is None for cloud (unknowable)."""
    if verify == "cloud":
        return None, None
    if verify.startswith("json:"):
        return verify[len("json:"):].lower() in json_keys, None
    if verify.startswith("allow:"):
        return verify[len("allow:"):].lower() in prefixes, None
    return None, "unknown verify scheme %r" % verify


def main():
    opts = parse_args(sys.argv[1:])
    roster_text = read_text(opts["roster"], "roster (tech.md)")
    entries = parse_roster(extract_roster_block(roster_text))

    cj = read_json(opts["claude_json"], ".claude.json")
    if not isinstance(cj, dict):
        die(".claude.json is not a JSON object")
    json_keys = {str(k).lower() for k in (cj.get("mcpServers") or {}).keys()}

    settings_obj = read_json(opts["settings"], "settings.json")
    if not isinstance(settings_obj, dict):
        die("settings.json is not a JSON object")
    prefixes = allow_prefixes(settings_obj)

    findings = []
    documented_json_keys = set()
    for name, state, verify in entries:
        if verify.startswith("json:"):
            documented_json_keys.add(verify[len("json:"):].lower())
        live, err = is_live(verify, json_keys, prefixes)
        if err:
            die("connector %r: %s" % (name, err))
        if live is None:
            continue  # cloud -- informational only
        if state == "active" and not live:
            findings.append("%s: documented ACTIVE but NOT live (verify=%s) -- "
                            "documented-alive-but-dead" % (name, verify))
        elif state == "retired" and live:
            findings.append("%s: documented RETIRED but STILL LIVE (verify=%s) -- "
                            "documented-dead-but-alive" % (name, verify))

    # Orphan check: any live .claude.json mcpServers key with no json: roster line.
    for key in sorted(json_keys):
        if key not in documented_json_keys:
            findings.append("mcpServers key '%s' is live in .claude.json but has NO "
                            "roster line (verify=json:%s) -- undocumented live connector"
                            % (key, key))

    if findings:
        print("CONNECTOR DRIFT DETECTED (%d) -- roster in %s disagrees with live state:"
              % (len(findings), opts["roster"]))
        for f in findings:
            print("  " + f)
        sys.exit(1)

    if not opts["quiet"]:
        print("connector-drift-probe OK -- %d roster entries consistent with live state "
              "(%d mcpServers keys, %d allow-prefixes)."
              % (len(entries), len(json_keys), len(prefixes)))
    sys.exit(0)


if __name__ == "__main__":
    main()
