"""settings.json wiring check for hooks/mcp-delete-guard.py (R-06, C14 stub for Task 7).

Task 7 (adding the PreToolUse entry to settings.json) is deferred. Until it lands this
file prints SKIP for the live settings.json and exits 0. Once an entry exists it asserts:
  * exactly ONE PreToolUse entry references mcp-delete-guard.py;
  * that entry's matcher equals mcp_delete_tiers.SETTINGS_MATCHER byte for byte;
  * the guard is not duplicated (one command hook in that entry, no repeated
    matcher+command pair anywhere in PreToolUse), and no other guard named in
    EXPECTED_ONCE (override-mint-guard.py) appears in more than one PreToolUse entry.
A self-test over temp settings files (matching entry: pass; drifted matcher: fail;
duplicate entry: fail) always runs, to prove the check itself can fail.

Run: python test-mcp-delete-matcher-wiring.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import shutil
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HOOKS_DIR)
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
import mcp_delete_tiers as tiers  # noqa: E402

GUARD = "mcp-delete-guard.py"
EXPECTED_ONCE = ("override-mint-guard.py",)
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def load(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def pretooluse(settings):
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    entries = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    return entries if isinstance(entries, list) else []


def commands(entry):
    out = []
    for h in entry.get("hooks", []) if isinstance(entry, dict) else []:
        if isinstance(h, dict) and isinstance(h.get("command"), str):
            out.append(h["command"])
    return out


def guard_entries(settings):
    return [e for e in pretooluse(settings) if any(GUARD in c for c in commands(e))]


def problems(settings):
    """List of wiring problems for a loaded settings dict; None when the guard is unwired."""
    entries = guard_entries(settings)
    if not entries:
        return None
    out = []
    if len(entries) != 1:
        out.append("expected exactly one %s entry, found %d" % (GUARD, len(entries)))
    for e in entries:
        if e.get("matcher") != tiers.SETTINGS_MATCHER:
            out.append("matcher drifted from mcp_delete_tiers.SETTINGS_MATCHER: %r"
                       % (e.get("matcher"),))
        n = sum(1 for c in commands(e) if GUARD in c)
        if n != 1:
            out.append("entry references %s %d times in one hook list" % (GUARD, n))
    seen = set()
    for e in pretooluse(settings):
        for c in commands(e):
            key = (e.get("matcher"), c)
            if key in seen:
                out.append("duplicate PreToolUse matcher+command pair: %r" % (c[-80:],))
            seen.add(key)
    for name in EXPECTED_ONCE:
        n = sum(1 for e in pretooluse(settings) if any(name in c for c in commands(e)))
        if n > 1:
            out.append("%s appears in %d PreToolUse entries" % (name, n))
    return out


def _settings(entries):
    return {"hooks": {"PreToolUse": entries}}


def _entry(matcher, script):
    return {"matcher": matcher,
            "hooks": [{"type": "command", "command": 'python "C:/x/hooks/%s"' % script}]}


def selftest():
    tmp = tempfile.mkdtemp(prefix="mdw-")
    try:
        def write(name, obj):
            p = os.path.join(tmp, name)
            with open(p, "w", encoding="ascii") as fh:
                json.dump(obj, fh)
            return p
        good = write("good.json", _settings([
            _entry("Bash", "pretooluse-dispatcher.py"),
            _entry(tiers.SETTINGS_MATCHER, GUARD),
            _entry("Bash", "override-mint-guard.py")]))
        drift = write("drift.json", _settings([_entry(tiers.SETTINGS_MATCHER + "|x", GUARD)]))
        dup = write("dup.json", _settings([_entry(tiers.SETTINGS_MATCHER, GUARD),
                                           _entry(tiers.SETTINGS_MATCHER, GUARD)]))
        mint2 = write("mint2.json", _settings([
            _entry(tiers.SETTINGS_MATCHER, GUARD),
            _entry("Bash", "override-mint-guard.py"),
            _entry("Edit", "override-mint-guard.py")]))
        none = write("none.json", _settings([_entry("Bash", "pretooluse-dispatcher.py")]))
        check("W-S1 matching entry passes", problems(load(good)) == [],
              repr(problems(load(good))))
        p = problems(load(drift))
        check("W-S2 drifted matcher fails", bool(p) and "drifted" in p[0], repr(p))
        p = problems(load(dup))
        check("W-S3 duplicated guard entry fails", bool(p) and "exactly one" in p[0], repr(p))
        p = problems(load(mint2))
        check("W-S4 duplicated override-mint-guard fails",
              bool(p) and any("override-mint-guard" in x for x in p), repr(p))
        check("W-S5 unwired settings reports None (SKIP path)", problems(load(none)) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    selftest()
    live = problems(load(os.path.join(REPO, "settings.json")))
    if live is None:
        print("SKIP: mcp-delete-guard is not wired in settings.json yet (R-06 Task 7 deferred)")
    else:
        check("W1 settings.json wiring of %s" % GUARD, live == [], "; ".join(live))
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        return 1
    print("\nALL mcp-delete-matcher-wiring checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
