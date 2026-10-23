#!/usr/bin/env python3
"""render-settings-wiring.py -- R-08 wiring table renderer. CHECK MODE FIRST.

  python maintenance/render-settings-wiring.py --check                 (default)
  python maintenance/render-settings-wiring.py --check --live          (~/.claude/settings.json)
  python maintenance/render-settings-wiring.py --check --json
  python maintenance/render-settings-wiring.py --check --expect-delta ID[,ID]
  python maintenance/render-settings-wiring.py --check --lowest-binary 2.1.278
  python maintenance/render-settings-wiring.py --render OUT.json       (NEW file only)

--check writes NOTHING and never touches settings.json. Exit codes:
  0  table renders settings.json exactly (text, LF-normalized) and every cross-check passes
     (with --expect-delta: the findings are exactly UNWIRED for the named ids)
  1  DRIFT: at least one finding (UNWIRED / UNTRACKED / CHANGED / ORDER / FORMAT / CHAIN /
     REFERENCE / CAPABILITY)
  2  cannot evaluate (table invalid, settings unreadable or not JSON, dispatcher unloadable,
     bad arguments). Fail closed: 2 is never "fine".

--render OUT writes the rendered settings to OUT. It refuses (exit 2) when OUT exists or
resolves to the settings file under check; there is deliberately no in-place mode in R-08.

Stdlib only. ASCII-only. Windows (`python`).
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True  # check mode must write nothing, not even .pyc

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "hooks", "lib"))
try:
    import settings_wiring as sw  # noqa: E402
except ImportError as exc:  # tomllib needs Python 3.11+
    print("ERROR: cannot import settings_wiring (%s); need Python 3.11+" % exc, file=sys.stderr)
    sys.exit(2)

DEFAULT_TABLE = os.path.join(REPO, "hooks", "wiring", "settings-wiring.toml")


def _read_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8")
    except OSError as exc:
        raise sw.TableError("cannot read %s: %s" % (path, exc))
    except UnicodeDecodeError as exc:
        raise sw.TableError("%s is not UTF-8: %s" % (path, exc))


def _same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _describe(f):
    k = f["kind"]
    if k == "UNWIRED":
        return "UNWIRED   %-10s %s  (in table, missing from settings.json)" % (f["event"], f["id"])
    if k == "UNTRACKED":
        live = f.get("live")
        what = json.dumps(live)[:160] if live is not None else "?"
        return "UNTRACKED %-10s not in table: %s" % (f["event"], what)
    if k == "CHANGED":
        return "CHANGED   %-10s %s  table=%s live=%s" % (
            f["event"], f["id"], json.dumps(f["table"])[:110], json.dumps(f["live"])[:110])
    if k == "ORDER":
        return "ORDER     %-10s same entries, different sequence" % f["event"]
    if k == "CHAIN":
        return "CHAIN     %s: %s" % (f["chain"], f["detail"])
    if k in ("REFERENCE", "CAPABILITY"):
        return "%-9s %s: %s" % (k, f["id"], f["detail"])
    return "%-9s %s" % (k, f.get("detail", ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--table", default=DEFAULT_TABLE)
    ap.add_argument("--settings", help="settings file to check (default: <repo>/settings.json)")
    ap.add_argument("--live", action="store_true", help="check ~/.claude/settings.json")
    ap.add_argument("--hooks-dir", help="hooks dir for dispatcher/script checks (default <repo>/hooks)")
    ap.add_argument("--check", action="store_true", help="(default mode)")
    ap.add_argument("--render", metavar="OUT")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--expect-delta", metavar="IDS",
                    help="exit 0 iff the only findings are UNWIRED for exactly these row ids")
    ap.add_argument("--lowest-binary", metavar="X.Y.Z")
    a = ap.parse_args(argv)
    try:
        if a.settings and a.live:
            raise sw.TableError("--settings and --live are mutually exclusive")
        settings_path = (os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
                         if a.live else a.settings or os.path.join(REPO, "settings.json"))
        hooks_dir = a.hooks_dir or os.path.join(REPO, "hooks")
        table = sw.load_table(a.table)
        text = _read_text(settings_path)
        if a.render:
            if os.path.exists(a.render) or _same_path(a.render, settings_path):
                raise sw.TableError("--render refuses to overwrite an existing file or "
                                    "the settings file: %s" % a.render)
            out = sw.dump_settings(sw.render_settings(table, sw.parse_settings_text(text)))
            with open(a.render, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(out)
            print("rendered %s -> %s (%d bytes)" % (a.table, a.render, len(out.encode("utf-8"))))
            return 0
        findings, _ = sw.run_check(table, text, hooks_dir, a.lowest_binary)
    except sw.TableError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        print("ERROR: cannot evaluate (%s: %s)" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    expected = sorted(x for x in (a.expect_delta or "").split(",") if x)
    got = sorted(f["id"] for f in findings if f["kind"] == "UNWIRED")
    delta_ok = bool(expected) and all(f["kind"] == "UNWIRED" for f in findings) \
        and got == expected
    if a.json:
        print(json.dumps({"settings": settings_path, "table": a.table,
                          "crlf": "\r\n" in text, "findings": findings,
                          "expect_delta_ok": delta_ok if expected else None},
                         indent=2))
    else:
        print("settings: %s%s" % (settings_path, "  (CRLF checkout, compared LF-normalized)"
                                  if "\r\n" in text else ""))
        print("table:    %s  (%d rows, %d chains)" % (a.table, len(table["rows"]),
                                                    len(table["chains"])))
        for f in findings:
            print(_describe(f))
        print("RESULT: %s" % ("CLEAN -- table renders settings.json exactly" if not findings
                              else "%d finding(s)" % len(findings)))
    if expected:
        if not delta_ok:
            print("expect-delta MISMATCH: wanted UNWIRED=%s only, got UNWIRED=%s and %d "
                  "other finding(s)" % (expected, got, len(findings) - len(got)),
                  file=sys.stderr)
        return 0 if delta_ok else 1
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
