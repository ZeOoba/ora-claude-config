# R-08 Single Settings Wiring Table + Renderer (Check Mode First) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close audit finding M63 (two hand-synchronized wiring authorities): add ONE declarative table, `hooks/wiring/settings-wiring.toml`, that is the source of truth for the `hooks` block of `settings.json` and a checked mirror of the dispatcher chains, plus a renderer that ships in CHECK MODE ONLY and reports every difference between the table and a settings file without writing anything. Adoption is a byte-for-byte no-op: this plan changes no hook behavior, no `settings.json`, no dispatcher logic.

**Lane:** L3 `/build`. Touches `hooks/**` (new files plus one docstring edit in the dispatcher), so blast radius is RED even though no live behavior changes. Ratified by Gabriel 2026-10-18 as R-08 (M63, W2-08); R-09 (staged `onFailure:block`) depends on it.

**Dispatch:** `subagent-driven-development · Sonnet 5.5 implementer per task, Opus 5.5 REFUTE reviewer` (hook/settings-adjacent code; reviewer >= implementer). No financial, governor or confidential code is touched.

**Architecture:** A TOML table (stdlib `tomllib`, Python 3.11+) holds `[[row]]` entries (one per `settings.json` hook entry, in file order) and `[[chain]]` entries (mirror of `pretooluse-dispatcher.py` `CHAINS`). A pure library (`hooks/lib/settings_wiring.py`) validates the table, renders the exact `hooks` object, and diffs it against a settings file and the real dispatcher. A thin CLI (`maintenance/render-settings-wiring.py`) exposes `--check` (default, read-only), `--render OUT` (new file only) and exit codes. The tracked-file check also runs inside the pre-push gate as `hooks/tests/test-settings-wiring.py`, so drift between table and tracked `settings.json` turns the gate red. The dispatcher stays the RUNTIME chain authority; the table is a checked mirror (see Design decision D2).

**Tech Stack:** Python 3.13 stdlib only (`tomllib`, `json`, `importlib`), plain-runner tests (`python <file>`, exit 0 = pass, house `check()` convention) auto-discovered by `hooks/git-prepush-hook-tests-gate.py`.

## Global Constraints

- READ-ONLY toward the live checkout `C:/Users/Owner/.claude`. All edits happen in an isolated worktree cut from `origin/main`. This plan itself edits nothing but its own file.
- NEVER overwrite `settings.json` (hard invariant 6: read before overwrite). R-08 contains no code path that writes `settings.json`; `--render` refuses an existing file and the settings file itself. The live file changes only through git (PR, merge, supervised merge-forward).
- One `settings.json` change in flight (settings queue). R-08 changes no `settings.json` byte, so it does not consume the slot.
- Never touch `hooks/confidential-terms.json`, `_confidential-staging/`, oxfordra.net, or governor constants.
- No deletions. Anything retired moves to an `_archive/` folder.
- Event log only via `python C:/Users/Owner/.claude/maintenance/append-event-log.py --entry-file <file>`; OI ids only via `allocate-oi-id.py`.
- Commits: `git commit -F <message file>`; message files live OUTSIDE the worktree in `C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/`. Trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Commits touching `hooks/**` need an Opus review recorded first (`python hooks/eos-review-gate.py --help` for the exact `--record` syntax; record and commit in SEPARATE shell calls).
- All new `.py` files are ASCII-only and say so in their docstring (`ascii-only-guard` enforces it). Write a BOM as the escape `"\ufeff"`, never the raw character.
- Shell state does not persist between tool calls: every command block re-exports `WT` and `BASE` itself.
- Rollback always names a commit.

---

## Verified ground truth (read 2026-10-23; origin/main = `d39d5306abcf120578e034e2e08c63ee3744fa18`, PR #338 merged)

| Fact | Evidence |
|---|---|
| `settings.json` hooks = 26 entries over 6 events, one handler per entry | UserPromptSubmit 1, PostToolUse 6, PreToolUse 12, SessionStart 4, Stop 1, SessionEnd 2 (counted from the parsed file). Event key order in the file: UserPromptSubmit, PostToolUse, PreToolUse, SessionStart, Stop, SessionEnd (NOT alphabetical). |
| Entry/hook key order is fixed | entry = `matcher`?, `hooks`; hook = `type`, `command`, then at most one of `timeout` / `async`, then `statusMessage`. Eight entries (the UserPromptSubmit, SessionStart, Stop and SessionEnd ones) have no `matcher` key at all. |
| The whole file is canonical JSON | `json.dumps(obj, indent=2) + newline`, two-space indent, no BOM, no non-ASCII characters; the index stores LF, a Windows checkout stores CRLF (`.gitattributes` `text=auto`, `git ls-files --eol` = `i/lf w/crlf`). A render compared LF-normalized is therefore byte-exact. |
| Wiring authorities today | `settings.json` `hooks` block and `hooks/pretooluse-dispatcher.py` `CHAINS` (`editwrite`, `bash`). After R-06 Tasks 1-6 (PR #338) each chain has 13 guards: `override-mint-guard` joined both; `sensitive-file-guard` joined `editwrite`. `hooks/tests/test-matcher-coverage.py` reads both and pins routing, via `hooks/tests/lib/settings_proposal.py` (the R-02 one-shot proposal state machine, state `applied`). |
| R-06 Task 7 is NOT landed | `mcp-delete-guard.py` and `sensitive-file-guard.py` exist on main, but `settings.json` has no entry for either (`grep -c "mcp-delete-guard" settings.json` = 0). Task 7 waits for R-08 (R-06 plan, Global Constraints and Task 7 precondition). |
| No wiring table exists | `git ls-tree -r origin/main | grep -i wiring` = nothing before this plan. |
| Governance of the new files | `hooks/config-write-guard.py` `_classify`: everything under `<root>/hooks/**` (except `sessions/`, `state/`, `active-work/`) and `<root>/settings.json` is governance. `hooks/wiring/` and `hooks/lib/settings_wiring.py` are therefore gated automatically; worktree copies are not gated. `maintenance/` is not governance. |
| Other readers of the hooks block | `maintenance/doctrine-integrity-probe.py` (walks every hook `command`), `maintenance/cc-verifier-probe.py`, `maintenance/setup-self-audit.py`. The renderer emits the identical JSON structure, so none changes. |
| Binaries | PATH CLI `2.1.278`; Desktop bundles `2.1.295` / `2.1.299`; Cowork/LAMS sessions read synced skills, not `~/.claude/settings.json`, and run no hooks (R-06 plan, "Scheduled callers" row). `maintenance/config-capability-baseline.py --json` reports the lowest binary. |
| Prototype dry-run (this plan's code, 2026-10-23) | table bootstrapped mechanically from the tracked `settings.json`; render == file LF-normalized; `--check` exit 0 on the tracked file AND on the live checkout's file (R-02 is live); 54 test checks pass; see "Dry-run evidence". |

## Design decisions

- **D1 - TOML, not JSON or a bespoke DSL.** Matchers are long regexes with `|`, `.*`, `[]`; a TSV or pipe-delimited row would need escaping. TOML literal strings (`'...'`) take them verbatim, support comments, and `tomllib` is stdlib on the pinned Python 3.13. *Cost:* Python 3.11+ required for the check (the CLI exits 2 with a clear message otherwise). *Closest alternative:* JSON lines (no comments, escaping noise).
- **D2 - The dispatcher stays the runtime authority for chains; the table mirrors it and check mode fails on any difference.** Making the dispatcher read the table would put a TOML parse and a new failure path inside security-gate code that runs on every Edit/Write/Bash call (65 ms budget, fails closed on a missing guard). *Cost:* two copies remain, but a mismatch is now a failing test at push time instead of a silent never-runs/runs-twice defect. *Closest alternative:* generate the dispatcher lists from the table (deferred to a later decision, R-08c).
- **D3 - Check mode owns `hooks` only.** Every non-`hooks` key (permissions, env, plugins, model) is outside the table: edits there are not drift (test B8). The table never grows permission rows in R-08. *Cost:* no single table for the whole file. *Reason:* M63 is about wiring.
- **D4 - Byte-exact means LF-normalized text equality of `json.dumps(indent=2, ensure_ascii=False) + "\n"`.** CRLF and a BOM are tolerated on read (reported as info); anything else that changes text without changing structure is its own finding kind, `FORMAT`.
- **D5 - Finding kinds are distinct and greppable:** `UNWIRED` (in table, missing from file: an unexpected removal), `UNTRACKED` (in file, not in table: a hand edit), `CHANGED` (same command, different fields), `ORDER` (same entries, different sequence: order is load-bearing), `FORMAT`, `CHAIN`, `REFERENCE`, `CAPABILITY`. Exit 1 on any; exit 2 means "could not evaluate" and is never treated as clean.
- **D6 - A missing script is a REFERENCE finding.** A row naming a nonexistent `hooks/<script>.py` makes CPython exit 2, which blocks every call that row routes (R-06 plan, Task 9 Step 1). Check mode verifies every `py` row's script exists in the hooks dir being checked, so the table cannot name a script the same PR does not ship.
- **D7 - Unknown row keys are errors.** A hand-typed `onFailure` on a hook is `CHANGED` (test B5); a table row with `on_failure` is a `TableError` until R-09 adds the key together with its binary canary. This is how R-09 is forced through the table.
- **D8 - No in-place writer in R-08.** `--render OUT` writes a NEW file only. Promotion to "authoritative" (a future `--apply`) is specified as a protocol in "Migration path" but not built here, because the safe route never needs it: the renderer writes into a worktree copy, git carries the change, merge-forward lands it.

## Row syntax (the table format)

File: `hooks/wiring/settings-wiring.toml`. Parsed by `settings_wiring.load_table`; any deviation is a `TableError` (CLI exit 2).

```
version     = 1                                  # must be 1
event_order = ["UserPromptSubmit", ...]          # each of the 6 events exactly once; rendered key order

[paths]
python      = 'C:/.../python.exe'                # interpreter written into every kind="py" command
claude_dir  = 'C:/Users/Owner/.claude'           # hooks_dir is derived: claude_dir + "/hooks"

[matchers]                                       # optional named fragments, referenced as @{name}
dc_write    = 'mcp__Desktop_Commander__write_file|...'

[[chain]]                                        # mirror of pretooluse-dispatcher.py CHAINS
name   = "bash"                                  # dispatcher chain name
guards = ["ora-autonomy-gate", ...]              # ordered; no duplicates

[[row]]                                          # ONE settings.json hook entry (one handler)
id        = 'pre.mcp-delete-guard'               # required, unique, [a-z0-9][a-z0-9._-]*; stable; names findings
event     = 'PreToolUse'                         # required, one of the 6 events
matcher   = 'regex or @{name} fragments'         # optional; omitted -> no "matcher" key in the entry
kind      = "py"                                 # required: "py" or "shell"
script    = 'mcp-delete-guard.py'                # kind=py: file under hooks/ (checked to exist)
args      = '--chain bash'                       # kind=py, optional: appended after the quoted script
command   = 'cat "@{claude_dir}/x.md"'           # kind=shell: verbatim command ("@{python}" / "@{claude_dir}" expand)
timeout   = 15                                   # optional positive integer seconds
async     = true                                 # optional; only `true` is legal (omit the key otherwise)
status    = 'Checking ...'                       # optional -> "statusMessage"
note      = 'free text'                          # optional, never rendered
min_binary = '2.1.295'                           # optional X.Y.Z, never rendered; check mode flags it when
                                                 #   --lowest-binary is lower (R-09 uses it)
```

Rendering rules (deterministic): rows are grouped by `event` in `event_order`, keeping table order within an event (this IS settings order, which is load-bearing). `kind="py"` renders `<python> "<hooks_dir>/<script>"` plus `" " + args` when present. The entry is `{"matcher"?, "hooks": [{"type": "command", "command", "timeout"?, "async"?, "statusMessage"?}]}` in exactly that key order. `@{name}` expands `[paths]` then `[matchers]` values; `@{` is reserved. Every matcher must compile as a Python regex (a sanity check only: the harness uses JavaScript regex, and routing semantics stay pinned by `test-matcher-coverage.py`'s anchored and documented models).

## File Structure

| Path (in the worktree) | Action | Responsibility |
|---|---|---|
| `hooks/wiring/settings-wiring.toml` | Create | The table: 26 rows + 2 chains, byte-exact with tracked `settings.json` |
| `hooks/lib/settings_wiring.py` | Create | Pure library: validate, render, diff, cross-checks. Never opens a file for writing |
| `maintenance/render-settings-wiring.py` | Create | CLI: `--check` (default), `--render OUT`, `--json`, `--expect-delta`, `--lowest-binary`, `--live` |
| `hooks/tests/test-settings-wiring.py` | Create | Adoption no-op, drift (failing-first), chains, references, table validation, no-write, capability, R-06 Task 7 simulation |
| `hooks/pretooluse-dispatcher.py` | Modify (docstring only) | Header note: chains are mirrored in the table, edit both |

No change to `settings.json`, `hooks/tests/test-matcher-coverage.py`, `hooks/tests/lib/settings_proposal.py` or any guard.

---

## Task 0: Preconditions, worktree, baseline

**Files:** none (read-only checks, one worktree, one claim).

- [ ] **Step 1: Create the implementation worktree and record the base**

```bash
git -C C:/Users/Owner/.claude fetch origin
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
git -C C:/Users/Owner/.claude worktree add "$WT" -b r08-wiring-table origin/main
BASE=$(git -C "$WT" rev-parse HEAD); echo "$BASE"
mkdir -p C:/Users/Owner/ora-claude-config-worktrees/r08-msgs
```
Expected: a 40-hex sha. Record it as `BASE` in the PR body. If `origin/main` has moved past `d39d5306`, re-run Step 3 (the ground-truth rows depend on it).

- [ ] **Step 2: Gate and claim**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
BASE=$(git -C "$WT" rev-parse HEAD)
python C:/Users/Owner/.claude/maintenance/preflight-shared-checkout.py --repo "$WT" --paths hooks/wiring/settings-wiring.toml hooks/lib/settings_wiring.py maintenance/render-settings-wiring.py hooks/tests/test-settings-wiring.py hooks/pretooluse-dispatcher.py --since "$BASE"
python "$WT/hooks/lib/claim_work.py" claim r08-settings-wiring-table "R-08 wiring table + check-mode renderer (M63)" --paths hooks/wiring/settings-wiring.toml hooks/lib/settings_wiring.py maintenance/render-settings-wiring.py hooks/tests/test-settings-wiring.py hooks/pretooluse-dispatcher.py
```
Expected: preflight exit 0 (anything else: STOP); claim recorded. Do not claim `settings.json`: R-08 does not edit it.

- [ ] **Step 3: Re-verify the two facts the whole plan rests on**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
git -C "$WT" show HEAD:settings.json | python -c "import json,sys;t=sys.stdin.buffer.read().decode('utf-8');o=json.loads(t);print('canonical json.dumps(indent=2):', json.dumps(o,indent=2,ensure_ascii=False)+'\n'==t)"
python "$WT/hooks/pretooluse-dispatcher.py" --selfcheck | grep "chain"
grep -c "mcp-delete-guard" "$WT/settings.json"
```
Expected: `canonical json.dumps(indent=2): True`; `chain 'bash' OK -- 13 guards present` and `chain 'editwrite' OK -- 13 guards present`; the grep prints `0`. If the first is `False`, STOP: the byte-for-byte premise is gone and D4 must be redesigned (a different dump format) before any code is written.

- [ ] **Step 4: Baseline the suites this plan must not disturb**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
for t in test-matcher-coverage test-write-guard-coverage test-ascii-only-guard; do python "$WT/hooks/tests/$t.py" > "C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/baseline-$t.log" 2>&1; echo "$t exit=$?"; done
```
Expected: all `exit=0`. A suite red on base must be named in the PR body, not hidden.

---

## Task 1: Library, table and tests (failing-first)

**Files:**
- Create: `hooks/tests/test-settings-wiring.py`
- Create: `hooks/lib/settings_wiring.py`
- Create: `hooks/wiring/settings-wiring.toml`

**Interfaces:**
- Produces (library): `TableError`; `load_table(path) -> dict`; `validate_table(raw) -> dict` (keys `paths`, `event_order`, `rows`, `chains`); `render_hooks(table) -> OrderedDict`; `render_settings(table, settings_obj) -> OrderedDict`; `dump_settings(obj) -> str` (LF); `parse_settings_text(text) -> OrderedDict`; `lf(text)`; `diff_hooks(table, live_hooks) -> list[dict]`; `diff_chains(table, dispatcher_chains) -> list[dict]`; `check_references(table, hooks_dir)`; `check_capability(table, lowest_binary)`; `load_dispatcher_chains(hooks_dir)`; `run_check(table, settings_text, hooks_dir, lowest_binary=None, dispatcher_chains=None) -> (findings, rendered_text)`. Findings are dicts with `kind` in `UNWIRED|UNTRACKED|CHANGED|ORDER|FORMAT|CHAIN|REFERENCE|CAPABILITY`.
- Produces (table): row ids used later by R-06 Task 7: `pre.scheduled-task-update-preguard` is the last PreToolUse row today.

- [ ] **Step 1: Write the failing test**

**File: `hooks/tests/test-settings-wiring.py`**
```python
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
    r06_rows = ("\n[[row]]\nid = 'pre.mcp-delete-guard'\nevent = 'PreToolUse'\n"
                "matcher = '%s'\nkind = \"py\"\nscript = 'mcp-delete-guard.py'\ntimeout = 15\n"
                "\n[[row]]\nid = 'pre.sensitive-file-guard-nb-dc'\nevent = 'PreToolUse'\n"
                "matcher = '%s'\nkind = \"py\"\nscript = 'sensitive-file-guard.py'\ntimeout = 10\n"
                % (DELETE_MATCHER, SENS_MATCHER))
    ins = TABLE_TEXT.index("[[row]]\nid = 'start.session-context-cat'")
    t06 = sw.validate_table(__import__("tomllib").loads(
        TABLE_TEXT[:ins] + r06_rows.lstrip("\n") + "\n" + TABLE_TEXT[ins:]))
    r06_chains = copy.deepcopy(CHAINS)  # R-06 Task 6 already put its chain edits on main
    t06["chains"] = r06_chains
    fake = os.path.join(tmp, "hooks-r06")
    os.makedirs(fake)
    for r in t06["rows"]:
        if r["kind"] == "py":
            open(os.path.join(fake, r["script"]), "w").close()
    f, _ = sw.run_check(t06, SETTINGS_TEXT, fake, dispatcher_chains=r06_chains)
    check("G1 table gains the 2 R-06 rows, settings not yet edited -> exactly 2 UNWIRED",
          kinds(f) == ["UNWIRED", "UNWIRED"] and
          sorted(x["id"] for x in f) == ["pre.mcp-delete-guard", "pre.sensitive-file-guard-nb-dc"],
          repr(f))
    plan_edit = copy.deepcopy(OBJ)
    p = plan_edit["hooks"]["PreToolUse"]
    p.append({"matcher": DELETE_MATCHER, "hooks": [{"type": "command", "command":
              OBJ["hooks"]["PreToolUse"][-1]["hooks"][0]["command"].replace(
                  "scheduled-task-update-preguard.py", "mcp-delete-guard.py"), "timeout": 15}]})
    p.append({"matcher": SENS_MATCHER, "hooks": [{"type": "command", "command":
              OBJ["hooks"]["PreToolUse"][-1]["hooks"][0]["command"].replace(
                  "scheduled-task-update-preguard.py", "sensitive-file-guard.py"), "timeout": 10}]})
    f, _ = sw.run_check(t06, sw.dump_settings(plan_edit), fake, dispatcher_chains=r06_chains)
    check("G2 R-06 plan's two entries appended at the PreToolUse tail -> CLEAN",
          not f, repr(f))
    check("G3 the rendered R-06 settings equal the plan's hand-edit byte for byte",
          sw.dump_settings(sw.render_settings(t06, OBJ)) == sw.dump_settings(plan_edit))
    import mcp_delete_tiers as tiers  # hooks/lib, on sys.path above
    check("G3b the delete-gate row matcher equals mcp_delete_tiers.SETTINGS_MATCHER",
          DELETE_MATCHER == tiers.SETTINGS_MATCHER)
    stale = copy.deepcopy(CHAINS)
    stale["editwrite"].remove("sensitive-file-guard")
    stale["bash"].remove("override-mint-guard")
    f, _ = sw.run_check(t06, SETTINGS_TEXT, fake, dispatcher_chains=stale)
    check("G4 a dispatcher chain edit without the matching table edit -> CHAIN findings",
          kinds(f).count("CHAIN") == 2, repr(kinds(f)))
    check("G4b the chains on main carry the R-06 guards (13 per chain)",
          len(CHAINS["editwrite"]) == 13 and len(CHAINS["bash"]) == 13
          and "override-mint-guard" in CHAINS["bash"], repr({k: len(v) for k, v in CHAINS.items()}))
    mid = os.path.join(tmp, "g5.json")
    with open(mid, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(SETTINGS_TEXT)
    tpath = os.path.join(tmp, "r06.toml")
    with open(tpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(TABLE_TEXT[:ins] + r06_rows.lstrip("\n") + "\n" + TABLE_TEXT[ins:])
    rc, out, err = cli("--check", "--table", tpath, "--settings", mid, "--hooks-dir", fake,
                       "--expect-delta", "pre.mcp-delete-guard,pre.sensitive-file-guard-nb-dc")
    # the CLI loads the real dispatcher from --hooks-dir; fake has none, so exit 2 is the
    # correct fail-closed answer here -- G6 covers the lib path
    check("G5 --expect-delta with an unloadable dispatcher fails closed (exit 2)",
          rc == 2 and "cannot load dispatcher" in err, out + err)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nsettings-wiring tests: %d failure(s)" % len(_failures))
sys.exit(1 if _failures else 0)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `python hooks/tests/test-settings-wiring.py`
Expected: exit 1 with `ModuleNotFoundError: No module named 'settings_wiring'` (the library does not exist yet).

- [ ] **Step 3: Write the library**

**File: `hooks/lib/settings_wiring.py`**
```python
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
        return json.loads(text.lstrip("\ufeff"), object_pairs_hook=collections.OrderedDict)
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


def load_dispatcher_chains(hooks_dir):
    path = os.path.join(hooks_dir, "pretooluse-dispatcher.py")
    try:
        spec = importlib.util.spec_from_file_location("_wiring_dispatcher", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {k: list(v) for k, v in mod.CHAINS.items()}
    except Exception as exc:  # noqa: BLE001
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
    if not findings and lf(settings_text).lstrip("\ufeff") != rendered:
        line, got, want = first_text_difference(lf(settings_text).lstrip("\ufeff"), rendered)
        findings.append({"kind": "FORMAT", "detail": "hooks match structurally but the text "
                         "differs at line %d: file=%r rendered=%r" % (line, got[:80], want[:80])})
    if dispatcher_chains is None:
        dispatcher_chains = load_dispatcher_chains(hooks_dir)
    findings += diff_chains(table, dispatcher_chains)
    findings += check_references(table, hooks_dir)
    findings += check_capability(table, lowest_binary)
    return findings, rendered
```

- [ ] **Step 4: Write the table**

The table below was generated mechanically from the tracked `settings.json` and then curated (row ids, the `dc_write` fragment, the two chain blocks, one `note`). The round-trip test is the acceptance gate, so any transcription slip shows up as `FAIL A1/A2`.

**File: `hooks/wiring/settings-wiring.toml`**
```toml
# R-08 single settings wiring table. SOURCE OF TRUTH for the `hooks` block of settings.json
# and a checked mirror of the pretooluse-dispatcher chains. Row syntax: see
# docs/superpowers/plans/2026-10-23-r08-settings-wiring-table.md (Row syntax section).
# Rendered and diffed by maintenance/render-settings-wiring.py (check mode first).
# One [[row]] = one settings.json hook entry (one handler). Order inside an event is
# load-bearing and is the file order. @{name} expands [paths] and [matchers] values.
version = 1
event_order = ["UserPromptSubmit", "PostToolUse", "PreToolUse", "SessionStart", "Stop", "SessionEnd"]

[paths]
python = 'C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe'
claude_dir = 'C:/Users/Owner/.claude'

[matchers]
dc_write = 'mcp__Desktop_Commander__write_file|mcp__Desktop_Commander__edit_block|mcp__plugin_desktop-commander_desktop-commander__write_file|mcp__plugin_desktop-commander_desktop-commander__edit_block'

# Mirror of hooks/pretooluse-dispatcher.py CHAINS. The dispatcher stays the runtime
# authority; check mode fails on any difference in membership or order.
[[chain]]
name = "editwrite"
guards = ["ora-autonomy-gate", "confidentiality-guard", "eos-plan-gate", "shared-checkout-guard", "registry-write-guard", "config-write-guard", "eos-claude-md-guard", "memory-index-guard", "rules-md-guard", "lint-config-guard", "sensitive-file-guard", "override-mint-guard", "ascii-only-guard"]

[[chain]]
name = "bash"
guards = ["ora-autonomy-gate", "confidentiality-guard", "config-write-guard", "lint-config-guard", "workbook-write-guard", "eos-evidence-gate", "eos-review-gate", "commit-provenance-guard", "worktree-isolation-guard", "destructive-git-guard", "memory-orphan-link-guard", "commit-hygiene-guard", "override-mint-guard"]

[[row]]
id = 'ups.engineering-router'
event = 'UserPromptSubmit'
kind = "py"
script = 'engineering-router.py'

[[row]]
id = 'post.dispatcher'
event = 'PostToolUse'
matcher = 'Bash'
kind = "py"
script = 'posttooluse-dispatcher.py'
timeout = 360

[[row]]
id = 'post.fleet-session-hook'
event = 'PostToolUse'
matcher = 'Bash|Task|TaskCreate|TaskUpdate|Edit|Write|MultiEdit'
kind = "py"
script = 'fleet-session-hook.py'
async = true

[[row]]
id = 'post.eos-plan-marker'
event = 'PostToolUse'
matcher = 'Write|Edit|Skill'
kind = "py"
script = 'eos-plan-marker.py'

[[row]]
id = 'post.commit-provenance-recorder'
event = 'PostToolUse'
matcher = 'Edit|Write|MultiEdit|@{dc_write}'
kind = "py"
script = 'commit-provenance-recorder.py'

[[row]]
id = 'post.memory-nag-correction'
event = 'PostToolUse'
matcher = 'Edit|Write|MultiEdit|@{dc_write}'
kind = "py"
script = 'memory-nag-correction.py'

[[row]]
id = 'post.scheduled-task-update-postguard'
event = 'PostToolUse'
matcher = 'mcp__scheduled-tasks__update_scheduled_task'
kind = "py"
script = 'scheduled-task-update-postguard.py'

[[row]]
id = 'pre.dispatcher-editwrite'
event = 'PreToolUse'
matcher = 'Edit|Write|MultiEdit'
kind = "py"
script = 'pretooluse-dispatcher.py'

[[row]]
id = 'pre.dispatcher-bash'
event = 'PreToolUse'
matcher = 'Bash'
kind = "py"
script = 'pretooluse-dispatcher.py'
args = '--chain bash'

[[row]]
id = 'pre.ora-autonomy-gate'
event = 'PreToolUse'
matcher = 'NotebookEdit|mcp__.*netlify.*-updater|mcp__.*__(outlook_(send_mail|send_draft|update_draft|forward_mail|create_event|update_event|delete_event|respond_to_event|set_vacation|create_filter)|teams_(send_chat_message|send_channel_message|reply_channel_message|create_chat)|manage_(blog_post|landing_page|website_page))'
kind = "py"
script = 'ora-autonomy-gate.py'

[[row]]
id = 'pre.inline-sensitive-file-blocker'
note = 'M65 soak: stays until the separate R-06 removal PR (>= 14 days after landing)'
event = 'PreToolUse'
matcher = 'Edit|Write'
kind = "shell"
command = "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | @{python} -c \"import sys,json; print(json.load(sys.stdin).get(\\\"tool_input\\\",{}).get(\\\"file_path\\\",\\\"\\\"))\" 2>/dev/null || echo \"\"); if echo \"$FILE\" | grep -qiE \"(credentials|\\.env|password)\"; then echo \"BLOCKED: Cannot edit sensitive file: $FILE\" >&2; exit 2; fi'"

[[row]]
id = 'pre.confidentiality-guard'
event = 'PreToolUse'
matcher = 'NotebookEdit|mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY).*|mcp__.*notion[-_]?(create|update|append|duplicate|move|comment).*|mcp__.*outlook_(send|create_draft|send_draft|forward|reply).*|mcp__.*outlook_(send_mail|send_draft|forward_mail|create_draft|create_reply_draft|create_reply_all_draft|update_draft|set_vacation).*|mcp__.*outlook_(create_event|update_event|respond_to_event|delete_event).*|mcp__.*teams_(send_chat_message|send_channel_message|reply_channel_message|create_chat).*|mcp__.*sharepoint_(upload_file|update_file).*|mcp__.*__manage_(crm_objects|blog_post|landing_page|website_page|campaign_objects|segment|aeo_prompts).*|mcp__.*notion-(send-message-to-session|spawn-session).*'
kind = "py"
script = 'confidentiality-guard.py'

[[row]]
id = 'pre.registry-write-guard'
event = 'PreToolUse'
matcher = '@{dc_write}'
kind = "py"
script = 'registry-write-guard.py'

[[row]]
id = 'pre.ascii-only-guard'
event = 'PreToolUse'
matcher = '@{dc_write}'
kind = "py"
script = 'ascii-only-guard.py'

[[row]]
id = 'pre.config-write-guard'
event = 'PreToolUse'
matcher = 'NotebookEdit|mcp__excel__.*|mcp__.*(write_file|edit_block|move_file|start_process|interact_with_process|write_pdf)'
kind = "py"
script = 'config-write-guard.py'

[[row]]
id = 'pre.lint-config-guard'
event = 'PreToolUse'
matcher = 'NotebookEdit|mcp__.*(write_file|edit_block|move_file|start_process|interact_with_process|write_pdf)'
kind = "py"
script = 'lint-config-guard.py'

[[row]]
id = 'pre.workbook-write-guard'
event = 'PreToolUse'
matcher = 'Write|Edit|MultiEdit|NotebookEdit|mcp__excel__.*|mcp__.*(write_file|edit_block|move_file|start_process|interact_with_process|write_pdf)'
kind = "py"
script = 'workbook-write-guard.py'

[[row]]
id = 'pre.memory-index-guard'
event = 'PreToolUse'
matcher = '@{dc_write}'
kind = "py"
script = 'memory-index-guard.py'

[[row]]
id = 'pre.scheduled-task-update-preguard'
event = 'PreToolUse'
matcher = 'mcp__scheduled-tasks__update_scheduled_task'
kind = "py"
script = 'scheduled-task-update-preguard.py'

[[row]]
id = 'start.session-context-cat'
event = 'SessionStart'
kind = "shell"
command = 'cat "@{claude_dir}/session-context.md"'

[[row]]
id = 'start.repo-freshness'
event = 'SessionStart'
kind = "py"
script = 'repo-freshness.py'
timeout = 25
status = 'Checking oxford-command-center freshness'

[[row]]
id = 'start.active-work-broadcast'
event = 'SessionStart'
kind = "py"
script = 'active-work-broadcast.py'
timeout = 10
status = 'Checking for cross-session claims'

[[row]]
id = 'start.fleet-session-hook'
event = 'SessionStart'
kind = "py"
script = 'fleet-session-hook.py'
async = true

[[row]]
id = 'stop.fleet-session-hook'
event = 'Stop'
kind = "py"
script = 'fleet-session-hook.py'
async = true

[[row]]
id = 'end.fleet-session-hook'
event = 'SessionEnd'
kind = "py"
script = 'fleet-session-hook.py'
async = true

[[row]]
id = 'end.eos-telemetry'
event = 'SessionEnd'
kind = "py"
script = 'eos-telemetry.py'
```

- [ ] **Step 5: Run the test again**

Run: `python hooks/tests/test-settings-wiring.py`
Expected: the library-level checks PASS. The only FAIL lines are `A1`, `B11`, `B12`, `B13` and `D10` (they shell out to the CLI), followed by a `FileNotFoundError` traceback at `E1` (the test hashes the CLI file, which does not exist yet); Task 2 clears all of it. If any other check fails, fix the library or the table, not the test.

- [ ] **Step 6: Commit (after the Task 2 review gate)**

Library and CLI are reviewed together; commit them as C1 (library + table + test) and C2 (CLI) so a reviewer can reject one and keep the other. Message file `r08-msgs/01.txt`:

```
feat(r08): settings wiring table + pure render/diff library (check mode groundwork)

hooks/wiring/settings-wiring.toml declares the 26 hook entries and the 2 dispatcher
chains; hooks/lib/settings_wiring.py renders and diffs them. Byte-exact with the
tracked settings.json today; no settings or hook behavior change.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

---

## Task 2: Check-mode CLI

**Files:**
- Create: `maintenance/render-settings-wiring.py`

**Interfaces:**
- Consumes: everything Task 1 produces.
- Produces: CLI exit codes `0` clean, `1` drift, `2` cannot evaluate; flags `--table`, `--settings`, `--live`, `--hooks-dir`, `--check`, `--render OUT`, `--json`, `--expect-delta IDS`, `--lowest-binary X.Y.Z`. `--json` output keys: `settings`, `table`, `crlf`, `findings`, `expect_delta_ok`.

- [ ] **Step 1: Write the CLI**

**File: `maintenance/render-settings-wiring.py`**
```python
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
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
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
```

- [ ] **Step 2: Run the full test**

Run: `python hooks/tests/test-settings-wiring.py`
Expected: exit 0, last line `settings-wiring tests: 0 failure(s)`, 54 PASS lines.

- [ ] **Step 3: Run the CLI on the tracked file and read the output**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
python "$WT/maintenance/render-settings-wiring.py" --check; echo "exit=$?"
```
Expected:
```
settings: <WT>\settings.json  (CRLF checkout, compared LF-normalized)
table:    <WT>\hooks\wiring\settings-wiring.toml  (26 rows, 2 chains)
RESULT: CLEAN -- table renders settings.json exactly
exit=0
```

- [ ] **Step 4: Demonstrate a real failure (then undo it)**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
cp "$WT/settings.json" C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/settings.pre-drift.json
python - <<'PY'
p = r"C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table/settings.json"
s = open(p, newline="").read()
open(p, "w", newline="").write(s.replace('"timeout": 25', '"timeout": 26', 1))
PY
python "$WT/maintenance/render-settings-wiring.py" --check; echo "exit=$?"
cp C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/settings.pre-drift.json "$WT/settings.json"
git -C "$WT" status --short settings.json
```
Expected: one `CHANGED   SessionStart start.repo-freshness ...` line, `RESULT: 1 finding(s)`, `exit=1`; after the restore `git status --short settings.json` prints nothing. This edits the worktree copy only, never the live checkout.

- [ ] **Step 5: Commit (C2)**

Message file `r08-msgs/02.txt`:
```
feat(r08): render-settings-wiring.py check mode (read-only; --render writes new files only)

Exit 0 clean / 1 drift / 2 cannot evaluate. Findings: UNWIRED, UNTRACKED, CHANGED,
ORDER, FORMAT, CHAIN, REFERENCE, CAPABILITY. No in-place writer.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

---

## Task 3: Dispatcher header note (docstring only)

**Files:**
- Modify: `hooks/pretooluse-dispatcher.py` (module docstring, after the "IF YOU ADD A GUARD" paragraph, ~l.65-66)

- [ ] **Step 1: Make the edit**

Replace exactly:
```
IF YOU ADD A GUARD to the Edit/Write path, add it to GUARD_CHAIN here -- NOT as
a new settings.json PreToolUse entry -- or it will run twice on Edit/Write.
```
with:
```
IF YOU ADD A GUARD to the Edit/Write path, add it to GUARD_CHAIN here -- NOT as
a new settings.json PreToolUse entry -- or it will run twice on Edit/Write.

R-08: hooks/wiring/settings-wiring.toml mirrors CHAINS (its [[chain]] blocks) and
declares every settings.json hook entry. Adding, removing or reordering a guard
here means editing the table in the SAME commit; `python
maintenance/render-settings-wiring.py --check` and hooks/tests/test-settings-wiring.py
(pre-push gate) fail on any difference.
```

- [ ] **Step 2: Prove it is docstring-only and nothing else moved**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
git -C "$WT" diff --stat -- hooks/pretooluse-dispatcher.py
python "$WT/hooks/pretooluse-dispatcher.py" --selfcheck | grep chain
python "$WT/hooks/tests/test-settings-wiring.py" | tail -1
python "$WT/hooks/tests/test-matcher-coverage.py" | tail -1
```
Expected: `1 file changed, 6 insertions(+)`; both chains `OK -- 13 guards`; `settings-wiring tests: 0 failure(s)`; `ALL matcher-coverage tests passed.` If the dispatcher has changed on main since `BASE` (another session editing the same docstring region), re-anchor on the live text; do not force.

- [ ] **Step 3: Commit (C3)**

Message file `r08-msgs/03.txt` (subject `docs(r08): dispatcher header points at the wiring table`, same trailer). Record the Opus review first (separate shell call), then commit.

---

## Task 4: Full suite, REFUTE, merge gate, PR

- [ ] **Step 1: Pre-push-equivalent run**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
fails=0; for f in "$WT"/hooks/tests/test-*.py; do python "$f" > /dev/null 2>&1 || { echo "RED $(basename "$f")"; fails=$((fails+1)); }; done; echo "red=$fails"
python "$WT/hooks/pretooluse-dispatcher.py" --selfcheck > /dev/null; echo "selfcheck=$?"
```
Expected: `red=0`, `selfcheck=0`. Compare against the Task 0 baseline; a suite red on base and still red is named in the PR body.

- [ ] **Step 2: Adversarial REFUTE (hook-adjacent, blast-radius PR)**

Invoke `adversarial-merge-gate` on the pinned branch head with Opus 5.5 reviewers on a read-only worktree. Mandates beyond the skill's five: (a) make `--check` exit 0 while the file differs from the table (try: trailing whitespace, key order inside a hook, duplicate entries, an extra event, a BOM or CRLF-only difference, `ensure_ascii` escapes, a second hook inside one entry); (b) make any code path write `settings.json` (try `--render` with relative paths, symlinks, case variants of the same path on Windows, a path that is a hard link); (c) make the dispatcher load in `load_dispatcher_chains` do something other than read `CHAINS` (import side effects); (d) get exit 0 from a table that names a script that does not exist or a chain that does not exist; (e) prove a commit-message claim false. Fix confirmed findings only, then rerun on the patched diff.

- [ ] **Step 3: Push and open the PR**

```bash
WT=C:/Users/Owner/ora-claude-config-worktrees/r08-wiring-table
git -C "$WT" push -u origin r08-wiring-table
gh pr create -R ZeOoba/ora-claude-config --head r08-wiring-table --base main --title "R-08: settings wiring table + check-mode renderer (M63)" --body-file C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/pr-body.md
```
`pr-body.md` holds: BASE sha, C1-C3 shas, baseline exit lines, Step 1 output, the REFUTE findings table, the Row syntax section, the Migration path and Rollback sections of this plan, and ends with the Claude Code attribution line. State plainly: "No `settings.json` byte and no hook behavior changes; the table renders the tracked file exactly; check mode writes nothing." Do not merge; Gabriel merges.

- [ ] **Step 4: Release the claim after merge**

`python hooks/lib/claim_work.py release r08-settings-wiring-table`.

---

## Task 5: Live landing check and canary wiring (after merge; read-only)

- [ ] **Step 1: Supervised merge-forward, then check the live file with the live checkout's own copy**

```bash
python C:/Users/Owner/.claude/maintenance/checkout-merge-forward.py --repo C:/Users/Owner/.claude --json
python C:/Users/Owner/.claude/maintenance/render-settings-wiring.py --check --live --json
```
Expected: a merged/ok verdict (any `BLOCKED_*`: STOP and use `branch-catchup`; never force); then a JSON report with `"findings": []`. The `--live` flag expands `~/.claude/settings.json` inside the script, so the command line names no governance path (config-write-guard matches command text). A non-empty `findings` list is a true finding about the live file (a hand edit or a lagging merge-forward): report it, do not "fix" it from here.

- [ ] **Step 2: Record the rendered sha as the canary's pre-image**

```bash
python C:/Users/Owner/.claude/maintenance/render-settings-wiring.py --check --live --json > C:/Users/Owner/ora-claude-config-worktrees/r08-msgs/live-check-after-landing.json
```
Attach it to the PR as the proof that adoption was a no-op. Event-log the landing via `append-event-log.py` and nothing else.

---

## R-06 Task 7: the explicit table rows (finalizes R-06 plan R8)

R-06 Tasks 1-6 are on main (PR #338): the dispatcher already carries `sensitive-file-guard` + `override-mint-guard` (13/13), so the table's chain rows already match. What remains for R-06 Task 7 is the two PreToolUse entries and the pins. With R-08 on main, replace R-06 Task 7 Step 3 (the hand edit of `settings.json`) with these steps. They are verified by `test-settings-wiring.py` group G, which builds exactly this state.

**Rows to append** to `hooks/wiring/settings-wiring.toml`, immediately after the `pre.scheduled-task-update-preguard` row and before `start.session-context-cat` (settings order is file order, and R-06 appends at the PreToolUse tail):

```toml
[[row]]
id = 'pre.mcp-delete-guard'
event = 'PreToolUse'
matcher = 'mcp__.*__.*([Dd]elete|DELETE|[Tt]rash|TRASH|[Rr]emove|REMOVE|[Pp]urge|PURGE|[Dd]iscard|DISCARD).*|mcp__.*__(clean_up_worktrees|notion-calendar-cancel-events|sharepoint_move_item|manage_segment|manage_campaign_objects)'
kind = "py"
script = 'mcp-delete-guard.py'
timeout = 15
note = 'R-06: MCP-only, NOT in any dispatcher chain; matcher == mcp_delete_tiers.SETTINGS_MATCHER'

[[row]]
id = 'pre.sensitive-file-guard-nb-dc'
event = 'PreToolUse'
matcher = 'NotebookEdit|mcp__.*__(write_file|edit_block|move_file|write_pdf)'
kind = "py"
script = 'sensitive-file-guard.py'
timeout = 10
note = 'R-06/M65: NotebookEdit + Desktop Commander writes; Edit/Write/MultiEdit reach the guard via the editwrite chain'
```

**Replacement steps for R-06 Task 7 Step 3:**

1. Append the two rows. Run `python maintenance/render-settings-wiring.py --check --expect-delta pre.mcp-delete-guard,pre.sensitive-file-guard-nb-dc`. Expected: exit 0 (the file lacks exactly those two rows and nothing else differs; test G1).
2. Render into a NEW scratch file and copy it over the worktree's `settings.json` (a worktree copy is not gated; the live file is never touched):
   `python maintenance/render-settings-wiring.py --render C:/Users/Owner/ora-claude-config-worktrees/r06-msgs/settings.rendered.json` then `cp` it over `<worktree>/settings.json`.
3. Run `python maintenance/render-settings-wiring.py --check` (no flags). Expected: exit 0, `CLEAN`. Then `git diff origin/main -- settings.json` shows only the two appended entries (the previous last entry's closing `}` becomes `},`), identical to the JSON R-06 Task 7 Step 3 prints (test G3 asserts byte equality with that hand edit).
4. Commit `settings.json` + the table in the SAME commit (C7). The pre-push test then keeps table and file locked together.

Chain note: R-06 Task 10 (removing the inline `Edit|Write` blocker after the 14-day soak) becomes: delete the `pre.inline-sensitive-file-blocker` row, re-render, `--check`, and replace test W6 as R-06 specifies.

## Migration path (adoption, never an overwrite)

| Phase | What happens | `settings.json` bytes | Gate to leave |
|---|---|---|---|
| A - this plan | Table + library + check-mode CLI + pre-push test land. Table is bootstrapped FROM the tracked file and proven equal by the round-trip test. | unchanged | PR merged; Task 5 shows `findings: []` on the live file |
| B - first real use | R-06 Task 7 adds two rows, proves `--expect-delta`, renders to a scratch file, copies into a worktree copy, commits through the normal PR. R-09 does the same later. | changes only through git | A real settings change landed this way with a clean `--check` before and after, plus >= 7 days with no `UNTRACKED`/`CHANGED` finding on the live check |
| C - authoritative (future plan R-08b, needs Gabriel's go) | The table is declared authoritative: hand edits to the `hooks` block are rejected in review. Optional `--apply`, if ever built, is bound by the protocol below. | changes only through git | Gabriel ratifies after B |

**Read-before-overwrite protocol for any future writer (R-08b), already part of the contract:** (1) read the target and record `S0 = sha256(bytes read)`; (2) run the full check; refuse while any `UNTRACKED` or `CHANGED` finding exists, because absorbing a hand edit into the table is a human decision; (3) require `--expect-sha S0`, which the operator copies from the output they inspected; (4) write the render to a temp file in the same directory; (5) re-read the target and abort if its sha is not `S0` (compare-and-swap against a concurrent session); (6) archive the pre-image to an `_archive/` file, then `os.replace`; (7) re-run the check and require exit 0. In practice the writer targets a WORKTREE copy; live is changed by merge-forward only, so config-write-guard (which gates a Bash write to the live governance path and wants Gabriel's `allow-config-write` token) is never bypassed or minted around.

## Rollback

- **Phase A is additive and inert:** nothing imports the table or library except the new test and CLI. Rollback is `git revert <C1,C2,C3 merge or commit shas>` through a PR (the PR body lists the shas); the dispatcher change is a docstring. If the new pre-push test is red on main and blocks unrelated pushes, revert C1-C3 first and investigate after: do NOT bypass the pre-push gate.
- **Local immediate path (live checkout):** after `preflight-shared-checkout.py`, `git -C C:/Users/Owner/.claude checkout <pre-image sha> -- hooks/pretooluse-dispatcher.py` and move the three new files to `_archive/`. `settings.json` needs no rollback in Phase A because it never changed.
- **Phase B rollbacks** belong to the change that used the table: they restore `settings.json` and the table together from the same pre-image commit (R-06 Task 9's `LIVE_PRE_IMAGE_SHA` procedure), then re-run `--check --live`.

## Interaction with the canary, per binary

The canary protocol (master plan, Landing protocol step 6) is unchanged: after any settings or hook landing, in a fresh live session, one fixture call that must be denied and one that must be scanned, both visible in guard telemetry, and `claude doctor` / schema validation clean on EVERY binary that loads `~/.claude/settings.json`. R-08 contributes two things to it and changes nothing else:

- **CLI (PATH `2.1.278`):** loads `settings.json` at session start. R-08 itself needs no canary (no settings or hook behavior change). For R-06 Task 7 and R-09, add `render-settings-wiring.py --check --live` as canary step 0 (live equals the table's pre-image) and as the last step (live equals the table's new render): it proves the file the binary will load is the file the table renders. Sessions started before the landing keep the old wiring until restarted.
- **Desktop (`2.1.295` / `2.1.299`):** same file, same canary. The extra obligation is R-09's: `min_binary = '2.1.295'` on any `on_failure` row plus `--lowest-binary <value from config-capability-baseline.py --json>` makes check mode report a `CAPABILITY` finding while the CLI is below 2.1.295, so the table cannot silently carry a key the PATH CLI ignores.
- **Cowork / LAMS:** Cowork sessions read synced skills, not `~/.claude/settings.json`, and run no PreToolUse/PostToolUse hooks. The table is therefore a Claude Code (CLI + Desktop Code tab) artifact. It contains no Cowork rows and must never be cited as Cowork coverage; any control Cowork needs stays a skill-level or spec-level rule.
- **config-write-guard:** the new files sit under `hooks/**` (governance) so edits in the LIVE checkout are token-gated, and worktree edits stay free. `--check` and `--render` write no governance path. `--live` exists so the check never needs a command line that names the live `settings.json`, which the guard would match. No step in this plan mints, requests or bypasses an override token.

## Order relative to R-09 and R-06

1. **R-08 Phase A (this plan)** merges first. It is additive, changes no live behavior, and does not use the settings queue slot.
2. **R-06 Task 7** (already planned, already unblocked on everything except this) then ships as the first real change through the table (Phase B), using the section above. R-06 Task 9's live canary follows.
3. **R-09** (staged `onFailure:block`) comes after both: it needs R-08 (table + `min_binary` + `CAPABILITY`), W0-00b (binary baseline; the PATH CLI must reach >= 2.1.295 or be retired), W1-02 (guards < 120 ms p50), and its own soak. R-09's work inside this framework: add `on_failure` to `ROW_KEYS` and a position in `HOOK_FIELD_ORDER` (the first change to the renderer after Phase A, with its own failing-first test), add rows with `min_binary`, run the 7-day report-only stage, then the Bash chain only.
4. Whichever of R-06 / R-08 merges second: if R-06's PR lands before R-08, R-08's `[[chain]]` blocks already reflect the 13/13 chains (they were written against `d39d5306`); if any later PR edits a chain, test G4 fails until the table is edited in the same commit. That is the intended coupling.

## Pre-mortem: top failure modes

| # | Failure | Likelihood / impact | Mitigation in this plan |
|---|---|---|---|
| 1 | The table is not byte-exact with `settings.json` (transcription slip, key order, escapes), so "adoption is a no-op" is false | Medium / High | Table is generated from the file; Task 0 Step 3 proves the file is canonical `json.dumps`; tests A1/A2 gate it; a `FORMAT` finding catches structure-equal/text-different |
| 2 | False drift from line endings, BOM, or a tool (Claude Code UI, plugin toggles) rewriting `settings.json` | Medium / Medium | LF-normalized comparison; BOM tolerated (A5/A6); non-`hooks` edits are not drift (B8). If a harness rewrite ever changes hook text formatting, `FORMAT` is greppable and a `--structural-only` flag is a one-test follow-up; this is open question 4 |
| 3 | The table becomes a THIRD copy nobody checks (dual authority becomes triple) | Medium / High | Tracked-file check is in the pre-push gate (`test-settings-wiring.py`), chains are mirrored with an order-sensitive check (C1-C3), the dispatcher docstring points at the table, and Task 5 checks the live file once after landing |
| 4 | A table row names a script that does not exist, so CPython exits 2 and blocks every routed call once rendered | Low / Critical | `REFERENCE` finding (D6, C4); R-06 Task 9's "guard files and settings in one commit" rule stays |
| 5 | Check mode loads the dispatcher module and an import side effect misbehaves or hides a failure | Low / Medium | Same load `test-matcher-coverage.py` already performs; failure is exit 2 (`TableError`), never clean; REFUTE mandate (c) |
| 6 | Someone later adds a writer that overwrites `settings.json` | Low / High | No writer in R-08; `--render` refuses existing/settings paths (E4/E5); the protocol above is the contract for R-08b; REFUTE mandate (b) |
| 7 | Python < 3.11 on some interpreter (`tomllib` missing) | Low / Low | Pinned interpreter is 3.13; CLI exits 2 with a message; test runs under the pre-push gate's interpreter |
| 8 | Merge race with R-06 or another session editing the same chains/docstring | Medium / Low | G4 turns any one-sided chain edit into a failing test; Task 3 re-anchors on live text; claim on the file set |
| 9 | Python-vs-JavaScript regex differences make the matcher "compile" check misleading | Low / Medium | Documented as a sanity check only; routing semantics stay pinned by `test-matcher-coverage.py` (anchored + documented models) |
| 10 | Scope creep: permissions, env, plugins pulled into the table | Medium / Medium | D3 and test B8 pin `hooks`-only; anything else is a separate ratification |

## Open questions for Gabriel

1. **Format (D1):** TOML table in `hooks/wiring/` (recommended) versus JSON lines. TOML is stdlib on 3.13, supports comments, takes regexes verbatim.
2. **Chain authority (D2):** keep the dispatcher as runtime authority with the table as a checked mirror (recommended, no new failure path in security-gate code), or have the dispatcher read the table later (R-08c).
3. **Landing order:** merge R-08 Phase A before R-06 Task 7's PR opens (recommended; R-06 is otherwise ready), or let R-06 Task 7 hand-edit and backfill the rows afterwards.
4. **FORMAT strictness:** keep byte-for-byte as the pass criterion (recommended and what was asked), or add a `--structural-only` mode for the live check if the Desktop app ever rewrites the file with different formatting.
5. **Live-drift watch:** pre-push covers the tracked file only. Run `--check --live` only at landings (recommended, no new mechanism per retire-to-add), or fold a one-line check into an existing health task (R-23-style)?
6. **Promotion to authoritative (Phase C):** acceptable bar = one real change landed through the table plus 7 clean days, then a separate R-08b ratification.
7. **`settings_proposal.py`:** it stays untouched (R-02 pins it via test L0). Retire it into `_archive/` in a later cleanup once R-08 is authoritative? Not part of this plan.

## Self-Review

- **Spec coverage:** table format and location (Row syntax, File Structure); renderer, check mode, exit codes, output (Task 2, CLI docstring, Step 3 sample); byte-for-byte today (D4, Task 0 Step 3, tests A1/A2, Dry-run evidence); migration without overwrite (Migration path, D8, protocol); rollback (Rollback); tests including failing-first drift (Task 1 Steps 1-2, Task 2 Step 4, group B); canary per binary, Cowork, config-write-guard (Interaction section); R-06 Task 7 explicit rows (dedicated section, group G); pre-mortem and order vs R-09 (their sections). No gap found.
- **Placeholder scan:** every code step embeds the complete file; the only non-code elisions are PR/commit body text, whose mandatory contents are listed.
- **Type consistency:** `run_check`, `diff_hooks`, `diff_chains`, `check_references`, `check_capability`, `load_dispatcher_chains`, `render_settings`, `dump_settings`, `lf`, `TableError` are named identically in Interfaces, library, CLI and tests; row ids `pre.mcp-delete-guard` and `pre.sensitive-file-guard-nb-dc` match between the Task 7 section and test group G.
- **Known residuals:** the pre-push test covers the tracked file, not the live checkout; the regex compile check is Python-flavored; the dispatcher/table pair is two copies by design (D2).

## Dry-run evidence (2026-10-23; evidence, not a claim)

Method (same as the R-06 plan): `git archive origin/main` (`d39d5306`) into a scratchpad directory, every `**File:**` code block of this plan extracted mechanically from this document into it (not retyped), the Task steps run in order. Nothing was written to either repo; the live checkout was only read once (`--check --live`, below).

| Step | Result |
|---|---|
| Task 0 Step 3 | `canonical json.dumps(indent=2): True`; chains `bash` 13 and `editwrite` 13; `grep -c mcp-delete-guard settings.json` = 0 |
| Task 1 Step 2 (red) | `ModuleNotFoundError: No module named 'settings_wiring'` |
| Task 1 Step 5 | FAIL exactly `A1`, `B11`, `B12`, `B13`, `D10`, then `FileNotFoundError` at `E1` (CLI absent) - as stated in the step |
| Task 2 Step 2 | `settings-wiring tests: 0 failure(s)`, 54 PASS |
| Task 2 Step 3 | `RESULT: CLEAN -- table renders settings.json exactly`, 26 rows, 2 chains |
| Task 2 Step 4 (real drift on a copy: `timeout` 25 -> 26) | one `CHANGED SessionStart start.repo-freshness`, exit 1; restored, `git status` clean |
| Task 3 | the "Replace exactly" text applied once by exact match, 6 lines added, ASCII-only; selfcheck 13 + 13; `test-settings-wiring` and `test-matcher-coverage` green |
| R-06 Task 7 section | rows appended from this plan's TOML block: `--check --expect-delta pre.mcp-delete-guard,pre.sensitive-file-guard-nb-dc` exit 0 (28 rows); `--render` to a new file, copied over the scratch `settings.json`; `--check` CLEAN; the diff is exactly the two appended entries (previous tail `}` -> `},`); `test-matcher-coverage` still green |
| Mutation check | with `diff_hooks` forced to return `[]` the drift tests fail (B1 sees only `FORMAT`; B1b crashes); with a real one-field edit to the tracked file `--check` exits 1 and the test run goes red on A1, A2, A5, A6, B1-B8, B10, E3, G1-G3 |
| Live read (once, read-only) | `render-settings-wiring.py --check --live` against `~/.claude/settings.json`: `CLEAN` (R-02 is live) |
| Suites on scratch vs pristine `origin/main` archive | `test-matcher-coverage`, `test-ascii-only-guard` exit 0 on both; `test-confidentiality-guard` and `test-git-prepush-scan` are red in the scratch archive (no `confidential-terms.json` / no git history) and `test-confidentiality-guard` is red identically on the pristine archive; a real worktree baselines these in Task 0 Step 4/Task 4 Step 1 |

Defects the dry-run found and fixed in this plan: raw U+FEFF characters in the sources (now the escape `"\ufeff"`, ASCII-only); exit-2 checks that passed vacuously when the CLI was missing (now also require `ERROR:` on stderr); a first table whose chain blocks predated PR #338 (13/13 now, and test G4 proves a one-sided chain edit fails); the Task 1 Step 5 expectation (corrected to the real failing set). Not dry-run here: the pre-push gate itself, `adversarial-merge-gate`, and the live canary (they need a real worktree, reviewers and Gabriel).

