"""R-08 wiring table tests: the table must render the tracked settings.json exactly, and
every way settings.json or the dispatcher can drift from the table must be caught.

Plain runner (house convention): python hooks/tests/test-settings-wiring.py ; exit 0 = pass.
Stdlib only. ASCII-only. Windows (`python`).
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HOOKS_DIR)
CLI = os.path.join(REPO, "maintenance", "render-settings-wiring.py")
TABLE = os.path.join(HOOKS_DIR, "wiring", "settings-wiring.toml")
SETTINGS = os.path.join(REPO, "settings.json")
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
import settings_wiring as sw  # noqa: E402

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def cli(*args):
    p = subprocess.run([sys.executable, CLI] + list(args), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def kinds(findings):
    return sorted(f["kind"] for f in findings)


TABLE_TEXT = read(TABLE)
TABLE_OBJ = sw.load_table(TABLE)
SETTINGS_TEXT = read(SETTINGS)
OBJ = sw.parse_settings_text(SETTINGS_TEXT)
CHAINS = {k: list(v) for k, v in TABLE_OBJ["chains"].items()}


def run(text, table=TABLE_OBJ, chains=None):
    return sw.run_check(table, text, HOOKS_DIR, dispatcher_chains=chains or CHAINS)[0]


def mutated(fn):
    o = copy.deepcopy(OBJ)
    fn(o)
    return sw.dump_settings(o)


tmp = tempfile.mkdtemp(prefix="wiring-test-")
try:
    # ---- A. adoption is a no-op: the table renders the tracked file exactly -------------
    rc, out, err = cli("--check")
    check("A1 tracked settings.json is CLEAN against the table (exit 0)", rc == 0, out + err)
    check("A2 rendered text equals settings.json text, LF-normalized",
          sw.lf(SETTINGS_TEXT) == sw.dump_settings(sw.render_settings(TABLE_OBJ, OBJ)))
    check("A3 dispatcher CHAINS equal the table chains (no CHAIN finding)",
          not [f for f in sw.run_check(TABLE_OBJ, SETTINGS_TEXT, HOOKS_DIR)[0]
               if f["kind"] == "CHAIN"])
    check("A4 every py row script exists under hooks/ (no REFERENCE finding)",
          not sw.check_references(TABLE_OBJ, HOOKS_DIR))
    crlf = SETTINGS_TEXT.replace("\r\n", "\n").replace("\n", "\r\n")
    check("A5 a CRLF checkout compares clean", not run(crlf))
    check("A6 a BOM-prefixed file compares clean", not run("\ufeff" + sw.lf(SETTINGS_TEXT)))
    check("A7 24+ rows, every event present",
          len(TABLE_OBJ["rows"]) >= 24 and
          set(r["event"] for r in TABLE_OBJ["rows"]) == set(sw.EVENTS))

    # ---- B. drift is caught (the failing-first cases) -----------------------------------
    pre = lambda o: o["hooks"]["PreToolUse"]
    bad = mutated(lambda o: pre(o)[2]["hooks"][0].__setitem__("timeout", 99))
    f = run(bad)
    check("B1 changed timeout -> one CHANGED", kinds(f) == ["CHANGED"], repr(kinds(f)))
    check("B1b CHANGED names the table row", f and f[0]["id"] == "pre.ora-autonomy-gate")
    bad = mutated(lambda o: pre(o).pop(5))
    f = run(bad)
    check("B2 entry deleted from settings -> UNWIRED (unexpected removal)",
          kinds(f) == ["UNWIRED"] and f[0]["id"] == "pre.registry-write-guard", repr(f))
    bad = mutated(lambda o: pre(o).append({"matcher": "Bash", "hooks": [
        {"type": "command", "command": "echo hand-edit"}]}))
    f = run(bad)
    check("B3 hand-added entry -> UNTRACKED", kinds(f) == ["UNTRACKED"], repr(kinds(f)))
    bad = mutated(lambda o: pre(o).insert(0, pre(o).pop(1)))
    f = run(bad)
    check("B4 reordered entries -> ORDER only", kinds(f) == ["ORDER"], repr(kinds(f)))
    bad = mutated(lambda o: pre(o)[0]["hooks"][0].__setitem__("onFailure", "block"))
    f = run(bad)
    check("B5 hand-added onFailure key -> CHANGED (R-09 must come through the table)",
          kinds(f) == ["CHANGED"], repr(kinds(f)))
    bad = mutated(lambda o: pre(o)[3].__setitem__("matcher", "Edit|Write|NotebookEdit"))
    check("B6 changed matcher on the inline blocker -> CHANGED", kinds(run(bad)) == ["CHANGED"])
    reindented = json.dumps(OBJ, indent=4) + "\n"
    f = run(reindented)
    check("B7 same hooks, different formatting -> FORMAT", kinds(f) == ["FORMAT"], repr(kinds(f)))
    bad = mutated(lambda o: o.__setitem__("model", "claude-opus-5-5"))
    check("B8 a NON-hooks edit is not drift (the table owns only `hooks`)", not run(bad))
    bad = mutated(lambda o: o["hooks"].__setitem__("PreCompact", [{"hooks": [
        {"type": "command", "command": "echo x"}]}]))
    check("B9 a hook event the table does not know -> UNTRACKED",
          "UNTRACKED" in kinds(run(bad)), repr(kinds(run(bad))))
    bad = mutated(lambda o: o["hooks"].pop("Stop"))
    check("B10 whole event removed -> UNWIRED", kinds(run(bad)) == ["UNWIRED"])
    rc, out, err = cli("--check", "--settings", os.path.join(tmp, "nope.json"))
    check("B11 unreadable settings -> exit 2, never 0", rc == 2 and "ERROR:" in err, out + err)
    with open(os.path.join(tmp, "notjson.json"), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    rc, out, err = cli("--check", "--settings", os.path.join(tmp, "notjson.json"))
    check("B12 settings that is not JSON -> exit 2", rc == 2 and "ERROR:" in err, out + err)
    drift_path = os.path.join(tmp, "drift.json")
    with open(drift_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mutated(lambda o: pre(o).pop(5)))
    rc, out, err = cli("--check", "--settings", drift_path)
    check("B13 CLI exit 1 and prints UNWIRED on drift",
          rc == 1 and "UNWIRED" in out and "pre.registry-write-guard" in out, out + err)

    # ---- C. chains and references -------------------------------------------------------
    c = copy.deepcopy(CHAINS)
    c["editwrite"].append("extra-guard")
    f = sw.diff_chains(TABLE_OBJ, c)
    check("C1 dispatcher chain gained a guard -> CHAIN finding",
          len(f) == 1 and "dispatcher-only=['extra-guard']" in f[0]["detail"], repr(f))
    c = copy.deepcopy(CHAINS)
    c["bash"].reverse()
    f = sw.diff_chains(TABLE_OBJ, c)
    check("C2 same guards, different order -> CHAIN (order is load-bearing)",
          len(f) == 1 and "order-differs=True" in f[0]["detail"], repr(f))
    c = copy.deepcopy(CHAINS)
    c["third"] = ["x"]
    check("C3 a chain only the dispatcher has -> CHAIN",
          len(sw.diff_chains(TABLE_OBJ, c)) == 1)
    empty_hooks = os.path.join(tmp, "hooks-empty")
    os.makedirs(empty_hooks)
    f = sw.check_references(TABLE_OBJ, empty_hooks)
    check("C4 missing script files -> one REFERENCE per py row",
          len(f) == len([r for r in TABLE_OBJ["rows"] if r["kind"] == "py"]))
    t2 = sw.validate_table(__import__("tomllib").loads(
        TABLE_TEXT.replace("args = '--chain bash'", "args = '--chain nope'")))
    check("C5 a row naming an undeclared chain -> REFERENCE",
          any("nope" in x["detail"] for x in sw.check_references(t2, HOOKS_DIR)))
    # selfcheck still agrees the dispatcher files exist
    p = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py"),
                        "--selfcheck"], capture_output=True, text=True)
    check("C6 dispatcher --selfcheck exits 0", p.returncode == 0, p.stdout[-200:] + p.stderr[-200:])

    # ---- D. the table itself is validated -----------------------------------------------
    def bad_table(replace_from, replace_to, label, count=1):
        try:
            sw.validate_table(__import__("tomllib").loads(
                TABLE_TEXT.replace(replace_from, replace_to, count)))
        except sw.TableError:
            check(label, True)
            return
        check(label, False, "no TableError")

    bad_table("kind = \"py\"\nscript = 'engineering-router.py'",
              "kind = \"py\"\nscript = 'engineering-router.py'\nbogus = 1", "D1 unknown row key rejected")
    bad_table("id = 'post.dispatcher'", "id = 'ups.engineering-router'", "D2 duplicate id rejected")
    bad_table("kind = \"py\"\nscript = 'engineering-router.py'", "kind = \"perl\"", "D3 bad kind rejected")
    bad_table("matcher = 'Write|Edit|Skill'", "matcher = 'Write|(Edit'", "D4 uncompilable matcher rejected")
    bad_table("@{dc_write}", "@{nope}", "D5 unknown @{ref} rejected")
    bad_table("timeout = 360", "timeout = 0", "D6 non-positive timeout rejected")
    bad_table('event_order = ["UserPromptSubmit", ', 'event_order = [', "D7 event_order missing an event rejected")
    bad_table("version = 1", "version = 2", "D8 wrong table version rejected")
    bad_table("async = true", "async = false", "D9 async=false rejected (omit the key instead)")
    badt = os.path.join(tmp, "bad.toml")
    with open(badt, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(TABLE_TEXT.replace("version = 1", "version = 9"))
    rc, out, err = cli("--check", "--table", badt)
    check("D10 invalid table via CLI -> exit 2", rc == 2 and "ERROR:" in err, out + err)

    # ---- E. check mode writes nothing; --render is new-file-only -------------------------
    snap = {p: sha(p) for p in (SETTINGS, TABLE, CLI)}
    before = sorted(os.listdir(REPO))
    cli("--check")
    cli("--check", "--json")
    check("E1 --check leaves settings.json, the table and the CLI byte-identical",
          snap == {p: sha(p) for p in snap})
    check("E2 --check creates nothing in the repo root", before == sorted(os.listdir(REPO)))
    out_path = os.path.join(tmp, "rendered.json")
    rc, out, err = cli("--render", out_path)
    check("E3 --render writes a new file equal to settings.json (LF)",
          rc == 0 and os.path.exists(out_path) and read(out_path) == sw.lf(SETTINGS_TEXT),
          out + err)
    rc, out, err = cli("--render", out_path)
    check("E4 --render refuses an existing file (exit 2)", rc == 2 and "ERROR:" in err, out + err)
    rc, out, err = cli("--render", SETTINGS)
    check("E5 --render refuses the settings file itself (exit 2)", rc == 2 and "ERROR:" in err, out + err)
    check("E6 settings.json untouched by --render", snap[SETTINGS] == sha(SETTINGS))
    rc, out, err = cli("--check", "--settings", SETTINGS, "--live")
    check("E7 --settings with --live is a usage error (exit 2)", rc == 2 and "ERROR:" in err)

    # ---- F. capability gate (R-09 stages onFailure:block behind it) -----------------------
    t3 = sw.validate_table(__import__("tomllib").loads(TABLE_TEXT.replace(
        "script = 'ora-autonomy-gate.py'", "script = 'ora-autonomy-gate.py'\nmin_binary = '2.1.295'")))
    check("F1 min_binary above the lowest binary -> CAPABILITY",
          kinds(sw.check_capability(t3, "2.1.278")) == ["CAPABILITY"])
    check("F2 min_binary satisfied -> nothing", not sw.check_capability(t3, "2.1.295"))
    check("F3 no --lowest-binary -> not evaluated", not sw.check_capability(t3, None))

    # ---- G. R-06 Task 7: the two new rows and the chain edits ----------------------------
    DELETE_MATCHER = ("mcp__.*__.*([Dd]elete|DELETE|[Tt]rash|TRASH|[Rr]emove|REMOVE|[Pp]urge"
                      "|PURGE|[Dd]iscard|DISCARD).*|mcp__.*__(clean_up_worktrees|"
                      "notion-calendar-cancel-events|sharepoint_move_item|manage_segment|"
                      "manage_campaign_objects)")
    SENS_MATCHER = "NotebookEdit|mcp__.*__(write_file|edit_block|move_file|write_pdf)"
    # The two rows and their settings entries are now ON main (R-06 Task 7 landed). Group G
    # rebuilds the PRE-landing state from the real files, then replays the landing on it.
    t06 = sw.validate_table(__import__("tomllib").loads(TABLE_TEXT))
    row_ids = [r["id"] for r in t06["rows"]]
    g0_want = ["pre.scheduled-task-update-preguard", "pre.mcp-delete-guard",
               "pre.sensitive-file-guard-nb-dc", "start.session-context-cat"]
    g0_at = row_ids.index(g0_want[0]) if g0_want[0] in row_ids else -1
    check("G0 the real table carries both R-06 rows, in order, between the preguard row and "
          "start.session-context-cat", g0_at >= 0 and row_ids[g0_at:g0_at + 4] == g0_want,
          repr(row_ids))
    PRE_OBJ = copy.deepcopy(OBJ)
    del PRE_OBJ["hooks"]["PreToolUse"][-2:]
    PRE_TEXT = sw.dump_settings(PRE_OBJ)
    r06_chains = copy.deepcopy(CHAINS)  # R-06 Task 6 already put its chain edits on main
    t06["chains"] = r06_chains
    fake = os.path.join(tmp, "hooks-r06")
    os.makedirs(fake)
    for r in t06["rows"]:
        if r["kind"] == "py":
            open(os.path.join(fake, r["script"]), "w").close()
    f, _ = sw.run_check(t06, PRE_TEXT, fake, dispatcher_chains=r06_chains)
    check("G1 table gains the 2 R-06 rows, settings not yet edited -> exactly 2 UNWIRED",
          kinds(f) == ["UNWIRED", "UNWIRED"] and
          sorted(x["id"] for x in f) == ["pre.mcp-delete-guard", "pre.sensitive-file-guard-nb-dc"],
          repr(f))
    plan_edit = copy.deepcopy(PRE_OBJ)
    p = plan_edit["hooks"]["PreToolUse"]
    p.append({"matcher": DELETE_MATCHER, "hooks": [{"type": "command", "command":
              PRE_OBJ["hooks"]["PreToolUse"][-1]["hooks"][0]["command"].replace(
                  "scheduled-task-update-preguard.py", "mcp-delete-guard.py"), "timeout": 30}]})
    p.append({"matcher": SENS_MATCHER, "hooks": [{"type": "command", "command":
              PRE_OBJ["hooks"]["PreToolUse"][-1]["hooks"][0]["command"].replace(
                  "scheduled-task-update-preguard.py", "sensitive-file-guard.py"), "timeout": 10}]})
    f, _ = sw.run_check(t06, sw.dump_settings(plan_edit), fake, dispatcher_chains=r06_chains)
    check("G2 R-06 plan's two entries appended at the PreToolUse tail -> CLEAN",
          not f, repr(f))
    check("G3 the rendered R-06 settings equal the plan's hand-edit byte for byte",
          sw.dump_settings(sw.render_settings(t06, PRE_OBJ)) == sw.dump_settings(plan_edit))
    import mcp_delete_tiers as tiers  # hooks/lib, on sys.path above
    check("G3b the delete-gate row matcher equals mcp_delete_tiers.SETTINGS_MATCHER",
          DELETE_MATCHER == tiers.SETTINGS_MATCHER)
    import session_kind  # hooks/lib: classify() may run up to HARD_JOIN_SECONDS before it answers
    g3c_timeout = next(r["timeout"] for r in t06["rows"] if r["id"] == "pre.mcp-delete-guard")
    check("G3c the delete-gate hook timeout exceeds classify's hard wall (a hook timeout is "
          "non-blocking: the delete would proceed unchecked)",
          g3c_timeout > session_kind.HARD_JOIN_SECONDS, repr((g3c_timeout, session_kind.HARD_JOIN_SECONDS)))
    stale = copy.deepcopy(CHAINS)
    stale["editwrite"].remove("sensitive-file-guard")
    stale["bash"].remove("commit-hygiene-guard")
    f, _ = sw.run_check(t06, SETTINGS_TEXT, fake, dispatcher_chains=stale)
    check("G4 a dispatcher chain edit without the matching table edit -> CHAIN findings",
          kinds(f).count("CHAIN") == 2, repr(kinds(f)))
    check("G4b the table chains equal the real dispatcher chains (no pinned guard count)",
          sw.load_dispatcher_chains(HOOKS_DIR) == CHAINS and "sensitive-file-guard" in CHAINS["editwrite"],
          repr({k: len(v) for k, v in CHAINS.items()}))
    mid = os.path.join(tmp, "g5.json")
    with open(mid, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(PRE_TEXT)
    tpath = os.path.join(tmp, "r06.toml")
    with open(tpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(TABLE_TEXT)
    rc, out, err = cli("--check", "--table", tpath, "--settings", mid, "--hooks-dir", fake,
                       "--expect-delta", "pre.mcp-delete-guard,pre.sensitive-file-guard-nb-dc")
    # the CLI loads the real dispatcher from --hooks-dir; fake has none, so exit 2 is the
    # correct fail-closed answer here -- G2 covers the lib path
    check("G5 --expect-delta with an unloadable dispatcher fails closed (exit 2)",
          rc == 2 and "cannot load dispatcher" in err, out + err)
    # ---- H. review hardening (Opus REFUTE) ------------------------------------------------
    stubdir = os.path.join(tmp, "hooks-exit")
    os.makedirs(stubdir)
    with open(os.path.join(stubdir, "pretooluse-dispatcher.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\nsys.exit(0)\n")
    rc, out, err = cli("--check", "--settings", drift_path, "--hooks-dir", stubdir)
    check("H1 dispatcher that sys.exit(0)s at import -> exit 2, never 0", rc == 2 and "ERROR:" in err,
          out + err)
    for i, shape in enumerate(("[]", "null", '{"hooks": "x"}', '{"hooks": {"PreToolUse": "x"}}')):
        sp = os.path.join(tmp, "shape%d.json" % i)
        with open(sp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(shape)
        rc, out, err = cli("--check", "--settings", sp)
        check("H2.%d malformed settings shape %s -> exit 2 (not a traceback exit 1)" % (i, shape),
              rc == 2 and "ERROR:" in err and "Traceback" not in err, out + err)
    try:
        run("\ufeff\ufeff" + sw.lf(SETTINGS_TEXT))
        check("H3 a double BOM is not stripped twice (TableError, exit 2)", False, "no error")
    except sw.TableError:
        check("H3 a double BOM is not stripped twice (TableError, exit 2)", True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nsettings-wiring tests: %d failure(s)" % len(_failures))
sys.exit(1 if _failures else 0)
