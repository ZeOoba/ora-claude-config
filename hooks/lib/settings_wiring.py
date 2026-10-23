"""Single settings.json hook-wiring table: parser, renderer, differ (R-08 / M63 / W2-08).

THE PROBLEM (audit M63): the PreToolUse wiring has TWO authorities that must stay in
step by hand -- the `hooks` block of settings.json and the dispatcher chains
(GUARD_CHAIN / BASH_GUARD_CHAIN in hooks/pretooluse-dispatcher.py). A guard added to one
and not the other either never runs or runs twice.

THE FIX: hooks/wiring/settings-wiring.toml declares every hook entry (one `[[row]]`
each) and every dispatcher chain (`[[chain]]`). This module turns the table into the
exact `hooks` object settings.json carries, and diffs it against a real settings file
and the real dispatcher. It is a PURE library: nothing here opens a file for writing.
The CLI is maintenance/render-settings-wiring.py.

Stdlib only (tomllib needs Python 3.11+). ASCII-only. Windows (`python`).
"""
import collections
import copy
import importlib.util
import json
import os
import re
import tomllib

TABLE_VERSION = 1
ROW_KEYS = {"id", "event", "matcher", "kind", "script", "args", "command",
            "timeout", "async", "status", "note", "min_binary"}
# Key order inside one rendered hook object. Fixed so rendering is deterministic and
# matches the order settings.json has carried since 2026-08 (type, command, then at
# most one of timeout/async, then statusMessage).
HOOK_FIELD_ORDER = ("type", "command", "timeout", "async", "statusMessage")
EVENTS = ("UserPromptSubmit", "PostToolUse", "PreToolUse", "SessionStart", "Stop",
          "SessionEnd")
_REF = re.compile(r"@\{([A-Za-z0-9_]+)\}")
_VER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class TableError(Exception):
    """The table (or a file it is checked against) cannot be evaluated."""


def _version_tuple(s):
    m = _VER.match(s or "")
    if not m:
        raise TableError("bad version %r (want X.Y.Z)" % (s,))
    return tuple(int(x) for x in m.groups())


def _expand(text, names, where):
    def sub(m):
        if m.group(1) not in names:
            raise TableError("%s: unknown reference @{%s}" % (where, m.group(1)))
        return names[m.group(1)]
    out = text
    for _ in range(4):  # references may nest one level (hooks_dir -> claude_dir)
        new = _REF.sub(sub, out)
        if new == out:
            return out
        out = new
    raise TableError("%s: reference expansion did not settle" % where)


def load_table(path):
    try:
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise TableError("cannot read table %s: %s" % (path, exc))
    return validate_table(raw)


def validate_table(raw):
    if raw.get("version") != TABLE_VERSION:
        raise TableError("table version must be %d" % TABLE_VERSION)
    paths = dict(raw.get("paths") or {})
    for need in ("python", "claude_dir"):
        if not isinstance(paths.get(need), str) or not paths[need]:
            raise TableError("[paths] needs a non-empty %r" % need)
    paths["hooks_dir"] = paths["claude_dir"] + "/hooks"
    matchers = dict(raw.get("matchers") or {})
    names = dict(paths)
    for k, v in matchers.items():
        names[k] = _expand(v, dict(paths, **{n: x for n, x in matchers.items() if n != k}),
                           "matcher " + k)
    order = list(raw.get("event_order") or [])
    if sorted(order) != sorted(EVENTS) or len(set(order)) != len(order):
        raise TableError("event_order must list each of %s exactly once" % ", ".join(EVENTS))
    rows, seen = [], set()
    for i, r in enumerate(raw.get("row") or []):
        where = "row[%d]" % i
        extra = set(r) - ROW_KEYS
        if extra:
            raise TableError("%s: unknown key(s) %s (renderer supports %s)"
                             % (where, sorted(extra), sorted(ROW_KEYS)))
        rid = r.get("id")
        if not isinstance(rid, str) or not re.match(r"^[a-z0-9][a-z0-9._-]*$", rid):
            raise TableError("%s: bad or missing id %r" % (where, rid))
        if rid in seen:
            raise TableError("duplicate row id %r" % rid)
        seen.add(rid)
        where = "row %s" % rid
        if r.get("event") not in EVENTS:
            raise TableError("%s: event must be one of %s" % (where, ", ".join(EVENTS)))
        kind = r.get("kind")
        if kind == "py":
            if not r.get("script") or "command" in r:
                raise TableError("%s: kind py needs `script` and no `command`" % where)
        elif kind == "shell":
            if not r.get("command") or "script" in r or "args" in r:
                raise TableError("%s: kind shell needs `command` and no script/args" % where)
        else:
            raise TableError("%s: kind must be py or shell" % where)
        if "timeout" in r and not (isinstance(r["timeout"], int) and r["timeout"] > 0):
            raise TableError("%s: timeout must be a positive integer (seconds)" % where)
        if "async" in r and r["async"] is not True:
            raise TableError("%s: async, when present, must be true" % where)
        if "min_binary" in r:
            _version_tuple(r["min_binary"])
        row = dict(r)
        if "matcher" in row:
            row["matcher"] = _expand(row["matcher"], names, where)
            try:
                re.compile(row["matcher"])
            except re.error as exc:
                raise TableError("%s: matcher does not compile: %s" % (where, exc))
        if "command" in row:
            row["command"] = _expand(row["command"], names, where)
        rows.append(row)
    chains, cseen = collections.OrderedDict(), set()
    for c in raw.get("chain") or []:
        name = c.get("name")
        guards = c.get("guards")
        if not name or name in cseen or not isinstance(guards, list) or not guards:
            raise TableError("chain needs a unique name and a non-empty guards list")
        if len(set(guards)) != len(guards):
            raise TableError("chain %s lists a guard twice" % name)
        cseen.add(name)
        chains[name] = list(guards)
    return {"paths": paths, "event_order": order, "rows": rows, "chains": chains}


def row_command(table, row):
    if row["kind"] == "shell":
        return row["command"]
    p = table["paths"]
    cmd = '%s "%s/%s"' % (p["python"], p["hooks_dir"], row["script"])
    return cmd + (" " + row["args"] if row.get("args") else "")


def render_entry(table, row):
    hook = {"type": "command", "command": row_command(table, row)}
    if "timeout" in row:
        hook["timeout"] = row["timeout"]
    if row.get("async"):
        hook["async"] = True
    if "status" in row:
        hook["statusMessage"] = row["status"]
    ordered = collections.OrderedDict((k, hook[k]) for k in HOOK_FIELD_ORDER if k in hook)
    entry = collections.OrderedDict()
    if "matcher" in row:
        entry["matcher"] = row["matcher"]
    entry["hooks"] = [ordered]
    return entry


def render_hooks(table):
    out = collections.OrderedDict()
    for ev in table["event_order"]:
        entries = [render_entry(table, r) for r in table["rows"] if r["event"] == ev]
        if entries:
            out[ev] = entries
    return out


def parse_settings_text(text):
    try:
        return json.loads(_strip_bom(text), object_pairs_hook=collections.OrderedDict)
    except ValueError as exc:
        raise TableError("settings is not valid JSON: %s" % exc)


def dump_settings(obj):
    """The canonical text of settings.json (LF; a Windows checkout adds CRLF)."""
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def render_settings(table, settings_obj):
    """A NEW object: `settings_obj` with only its `hooks` value replaced."""
    new = copy.deepcopy(settings_obj)
    new["hooks"] = render_hooks(table)
    return new


def lf(text):
    return text.replace("\r\n", "\n")


def _entry_key(entry):
    return json.dumps(entry, sort_keys=False)


def _cmd(entry):
    return " ".join(h.get("command", "") for h in entry.get("hooks", []))


def diff_hooks(table, live_hooks):
    """Findings between the rendered table and a live `hooks` object.

    kinds: UNWIRED   in the table, absent from the file (an unexpected removal)
           UNTRACKED in the file, absent from the table (a hand edit)
           CHANGED   same command, different matcher/timeout/other fields
           ORDER     same entries, different sequence (order is load-bearing)
    """
    want = render_hooks(table)
    rows_for = collections.defaultdict(list)
    for r in table["rows"]:
        rows_for[r["event"]].append(r)
    findings = []
    for ev in table["event_order"]:
        w = want.get(ev, [])
        wrows = rows_for.get(ev, [])
        l = list((live_hooks or {}).get(ev, []))
        w_left = list(zip(w, wrows))
        l_left = list(l)
        matched = []
        for we, wr in list(w_left):
            k = _entry_key(we)
            for le in l_left:
                if _entry_key(le) == k:
                    matched.append((we, le))
                    l_left.remove(le)
                    w_left.remove((we, wr))
                    break
        for we, wr in list(w_left):
            cmd = _cmd(we)
            twin = next((le for le in l_left if _cmd(le) == cmd), None)
            if twin is not None:
                l_left.remove(twin)
                w_left.remove((we, wr))
                findings.append({"kind": "CHANGED", "event": ev, "id": wr["id"],
                                 "table": we, "live": twin})
        for we, wr in w_left:
            findings.append({"kind": "UNWIRED", "event": ev, "id": wr["id"], "table": we})
        for le in l_left:
            findings.append({"kind": "UNTRACKED", "event": ev, "id": None, "live": le})
        if not w_left and not l_left:
            seq_w = [_entry_key(e) for e in w]
            seq_l = [_entry_key(e) for e in l]
            if seq_w != seq_l and sorted(seq_w) == sorted(seq_l):
                findings.append({"kind": "ORDER", "event": ev, "id": None})
    for ev in (live_hooks or {}):
        if ev not in table["event_order"]:
            findings.append({"kind": "UNTRACKED", "event": ev, "id": None,
                             "live": live_hooks[ev]})
    return findings


def diff_chains(table, dispatcher_chains):
    """CHAIN findings: table chains vs the dispatcher's CHAINS (name and order)."""
    out = []
    names = set(table["chains"]) | set(dispatcher_chains)
    for n in sorted(names):
        t, d = table["chains"].get(n), dispatcher_chains.get(n)
        if t is None:
            out.append({"kind": "CHAIN", "chain": n, "detail": "in dispatcher, not in table"})
        elif d is None:
            out.append({"kind": "CHAIN", "chain": n, "detail": "in table, not in dispatcher"})
        elif list(t) != list(d):
            out.append({"kind": "CHAIN", "chain": n,
                        "detail": "table-only=%s dispatcher-only=%s order-differs=%s" % (
                            [g for g in t if g not in d], [g for g in d if g not in t],
                            sorted(t) == sorted(d))})
    return out


def check_references(table, hooks_dir):
    """REFERENCE findings: a py row whose script is missing makes CPython exit 2 and
    blocks every call that row routes -- the failure R-06 calls out. Also a row naming
    an undeclared dispatcher chain."""
    out = []
    for r in table["rows"]:
        if r["kind"] != "py":
            continue
        if not os.path.isfile(os.path.join(hooks_dir, r["script"])):
            out.append({"kind": "REFERENCE", "id": r["id"],
                        "detail": "script hooks/%s does not exist" % r["script"]})
        m = re.search(r"--chain\s+(\S+)", r.get("args", ""))
        if m and m.group(1) not in table["chains"]:
            out.append({"kind": "REFERENCE", "id": r["id"],
                        "detail": "chain %r is not declared in the table" % m.group(1)})
    return out


def check_capability(table, lowest_binary):
    """CAPABILITY findings: a row whose min_binary exceeds the lowest binary that loads
    settings.json (R-09 stages onFailure:block behind this)."""
    if not lowest_binary:
        return []
    low = _version_tuple(lowest_binary)
    return [{"kind": "CAPABILITY", "id": r["id"],
             "detail": "needs >= %s, lowest binary is %s" % (r["min_binary"], lowest_binary)}
            for r in table["rows"]
            if "min_binary" in r and _version_tuple(r["min_binary"]) > low]


def _strip_bom(text):
    """Strip exactly one leading BOM (a double BOM is not a valid settings file)."""
    return text[1:] if text.startswith("\ufeff") else text


def load_dispatcher_chains(hooks_dir):
    path = os.path.join(hooks_dir, "pretooluse-dispatcher.py")
    try:
        spec = importlib.util.spec_from_file_location("_wiring_dispatcher", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {k: list(v) for k, v in mod.CHAINS.items()}
    except BaseException as exc:  # noqa: BLE001  SystemExit at import must fail closed (exit 2)
        if isinstance(exc, KeyboardInterrupt):
            raise
        raise TableError("cannot load dispatcher chains from %s: %s" % (path, exc))


def first_text_difference(a, b):
    la, lb = a.split("\n"), b.split("\n")
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<EOF>"
        y = lb[i] if i < len(lb) else "<EOF>"
        if x != y:
            return i + 1, x, y
    return None


def run_check(table, settings_text, hooks_dir, lowest_binary=None, dispatcher_chains=None):
    """Everything check mode reports. Returns (findings, rendered_text). Reads nothing
    itself: callers pass the settings text, so this is trivially testable."""
    live = parse_settings_text(settings_text)
    findings = diff_hooks(table, live.get("hooks"))
    rendered = dump_settings(render_settings(table, live))
    if not findings and _strip_bom(lf(settings_text)) != rendered:
        line, got, want = first_text_difference(_strip_bom(lf(settings_text)), rendered)
        findings.append({"kind": "FORMAT", "detail": "hooks match structurally but the text "
                         "differs at line %d: file=%r rendered=%r" % (line, got[:80], want[:80])})
    if dispatcher_chains is None:
        dispatcher_chains = load_dispatcher_chains(hooks_dir)
    findings += diff_chains(table, dispatcher_chains)
    findings += check_references(table, hooks_dir)
    findings += check_capability(table, lowest_binary)
    return findings, rendered
