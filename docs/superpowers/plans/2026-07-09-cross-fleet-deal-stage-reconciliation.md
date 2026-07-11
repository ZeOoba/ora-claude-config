# Cross-Fleet Deal-Stage Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap where deal-pipeline stage changes made outside `ora-open-sessions-board`'s own decision flow (e.g. 511 Industrial Mile Rd's reset, 470 McCormick Blvd's pass) never get logged to this machine's `event_log.md`, by adding a daily Notion-vs-snapshot reconciliation step that's root-cause-agnostic to which fleet or session made the change.

**Architecture:** A new pure/offline-testable `maintenance/deal-stage-reconciler.py` diffs live-fetched Notion Acquisition Pipeline Tracker Stage values against a rolling local snapshot and formats `event_log.md` entries + `deal-decision-ledger.md` rows. A new STEP 4.5 in `ora-open-sessions-board/SKILL.md` calls it daily. The script never touches Notion, `event_log.md`, or `deal-decision-ledger.md` directly — fetching, appending, and editing stay the agent's job; the script is pure diff/format logic plus its own snapshot-file I/O.

**Tech Stack:** Python 3.13 stdlib only (`argparse`, `json`, `os`, `sys`, `datetime`, `tempfile`/`subprocess` for tests). Existing `append-event-log.py` (collision-safe `event_log.md` appender) is reused as-is. Notion MCP (`mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__*`) for live reads. No new dependencies.

## Global Constraints

- `event_log.md` writes go **only** through `python C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file <path>` — never stdin (Windows cp1252 stdin decoding mangles em-dashes/arrows — see `feedback_append_event_log_stdin_encoding.md`), never a raw Edit-tool replacement on that file (single-writer collision history, 2026-06-11).
- `deal-decision-ledger.md` writes use a plain Edit-tool append — no lock mechanism (no observed concurrent-writer history on this file; revisit only if that changes).
- `deal-stage-reconciler.py` must never call MCP tools, `subprocess`, or do network I/O — pure functions plus its own snapshot-file I/O only. Notion fetching is the calling agent's job, always via a `--current-file` JSON path (never piped through stdin, for the same Windows-encoding reason as above).
- Snapshot writes are atomic: write to `<path>.tmp-write` then `os.replace()`.
- Never fabricate a ledger "reason" — when unknown, use the standing fallback text verbatim: `"Notion Stage → <value>; reason not logged elsewhere — reconcile manually"`.
- Terminal disposition tokens are exactly these six (matching `deal-decision-ledger.md`'s existing Verdict vocabulary): `PASS`, `SKIP`, `DROP`, `PARK`, `CLOSE`, `TERMINATE`.
- Additive-only in the `~/.claude` git tree: do not modify any file already showing as modified in `git status` (a known same-day uncommitted pile, unrelated to this work, flagged in `event_log.md` 2026-07-08 as "for Gabriel to decide how to commit"). Do not commit anything unless explicitly asked.
- Test files follow this codebase's established stdlib-only convention for hyphenated maintenance scripts (see `test-registry-membership-probe.py`, `test-governor-drift-probe.py`): `importlib.util.spec_from_file_location` to load the module under test, a simple `expect(label, cond, detail)` accumulator, `sys.exit(0 if passed==len(results) else 1)` — **not** pytest.
- `--bootstrap` mode must produce **zero** log entries — it only seeds the snapshot.
- Notion Acquisition Pipeline Tracker data source id: `bcfe4a037e614ac1a0bbc44174fa138b`.
- Script output on stdout is JSON; explicit UTF-8 reconfigure of stdout/stderr at the top of the script (mirrors `governor-drift-probe.py`) since deal names/entries may contain non-ASCII characters on a Windows cp1252 console.

---

### Task 1: Snapshot I/O + diff detection

**Files:**
- Create: `C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py`
- Test: `C:\Users\Owner\.claude\maintenance\test-deal-stage-reconciler.py`

**Interfaces:**
- Produces: `load_snapshot(path: str) -> dict`, `save_snapshot(path: str, current: dict) -> None`, `diff_stages(current: dict, snapshot: dict) -> list[dict]`. Snapshot/current shape: `{page_id: {"deal": str, "stage": str}}`. `diff_stages` returns `[{"page_id": str, "deal": str, "old_stage": str|None, "new_stage": str}, ...]` — one entry per `page_id` in `current` whose stage differs from (or is absent from) `snapshot`. `old_stage` is `None` for a `page_id` never seen before. A `page_id` present in `snapshot` but missing from `current` is **not** reported (disappearance ≠ a stage change).

- [ ] **Step 1: Write the failing tests**

Create `C:\Users\Owner\.claude\maintenance\test-deal-stage-reconciler.py`:

```python
#!/usr/bin/env python3
"""Tests for deal-stage-reconciler.py (TDD).

Pure-function unit tests, mirroring test-registry-membership-probe.py's pattern.
No Notion/network access anywhere in this file or the module under test -- the module
only ever receives already-fetched JSON (see the 2026-07-09 cross-fleet
deal-stage-reconciliation design spec).

Run: python test-deal-stage-reconciler.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "deal-stage-reconciler.py")

spec = importlib.util.spec_from_file_location("dsr", MOD_PATH)
dsr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsr)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


tmpdir = tempfile.mkdtemp(prefix="dsr-test-")

# --- load_snapshot / save_snapshot --------------------------------------------------
missing_path = os.path.join(tmpdir, "does-not-exist.json")
expect("load_snapshot: missing file -> {}", dsr.load_snapshot(missing_path) == {})

corrupt_path = os.path.join(tmpdir, "corrupt.json")
with open(corrupt_path, "w", encoding="utf-8") as f:
    f.write("{not valid json")
expect("load_snapshot: corrupt file -> {}", dsr.load_snapshot(corrupt_path) == {})

not_dict_path = os.path.join(tmpdir, "not-dict.json")
with open(not_dict_path, "w", encoding="utf-8") as f:
    json.dump([1, 2, 3], f)
expect("load_snapshot: non-dict JSON -> {}", dsr.load_snapshot(not_dict_path) == {})

roundtrip_path = os.path.join(tmpdir, "snap.json")
sample = {"pg1": {"deal": "511 Industrial Mile Rd", "stage": "Candidate"}}
dsr.save_snapshot(roundtrip_path, sample)
expect("save_snapshot: round-trips via load_snapshot",
       dsr.load_snapshot(roundtrip_path) == sample)
expect("save_snapshot: no leftover tmp-write file",
       not os.path.exists(roundtrip_path + ".tmp-write"))

# --- diff_stages ----------------------------------------------------------------------
current = {
    "pg1": {"deal": "511 Industrial Mile Rd", "stage": "Under Review"},
    "pg2": {"deal": "470 McCormick Blvd", "stage": "Passed"},
    "pg3": {"deal": "754 Old State Route 74", "stage": "In Negotiation"},
}
snapshot = {
    "pg1": {"deal": "511 Industrial Mile Rd", "stage": "Candidate"},
    "pg3": {"deal": "754 Old State Route 74", "stage": "In Negotiation"},
    "pg4": {"deal": "Old Removed Deal", "stage": "Passed"},
}
transitions = dsr.diff_stages(current, snapshot)
by_id = {t["page_id"]: t for t in transitions}
expect("diff_stages: unchanged stage produces no transition", "pg3" not in by_id)
expect("diff_stages: changed stage produces a transition", "pg1" in by_id)
expect("diff_stages: changed transition has correct old/new",
       by_id.get("pg1", {}).get("old_stage") == "Candidate"
       and by_id["pg1"]["new_stage"] == "Under Review")
expect("diff_stages: brand-new page_id has old_stage None",
       by_id.get("pg2", {}).get("old_stage") is None)
expect("diff_stages: page removed from current is not reported", "pg4" not in by_id)
expect("diff_stages: exactly 2 transitions", len(transitions) == 2, transitions)

# --- summary ----------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ndeal-stage-reconciler tests: %d/%d passed" % (passed, len(results)))
raise SystemExit(0 if passed == len(results) else 1)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: fails immediately with `ModuleNotFoundError`/`FileNotFoundError`-style error, since `deal-stage-reconciler.py` doesn't exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py`:

```python
#!/usr/bin/env python3
"""ORA deal-stage reconciler.

Diffs live Notion Acquisition Pipeline Tracker Stage values (supplied by the caller as
already-fetched JSON -- this module never calls Notion, subprocess, or the network
itself) against a rolling local snapshot, and formats event_log.md entries +
deal-decision-ledger.md rows for anything that changed. Writing those files is the
calling agent's job (append-event-log.py for event_log.md, an Edit-tool append for
deal-decision-ledger.md) -- this module only owns its own snapshot file.

See: docs/superpowers/specs/2026-07-09-cross-fleet-deal-stage-reconciliation-design.md

Usage:
  python deal-stage-reconciler.py --current-file <path.json> --stage-map-file <path.json> \\
      [--snapshot-file <path>] [--bootstrap] [--date YYYY-MM-DD]

--current-file / --stage-map-file are always files, never stdin -- Windows cp1252 stdin
decoding mangles UTF-8 em-dashes/arrows (see feedback_append_event_log_stdin_encoding.md).
Exit 0 = ran fine (transitions may be zero). Exit 2 = could not read an input file
(fail loud, not silent).
"""
import argparse
import datetime as dt
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SNAPSHOT = os.path.join(os.path.expanduser("~"), ".claude", "maintenance",
                                 "_state", "deal-stage-snapshot.json")

DISPOSITION_TOKENS = {"PASS", "SKIP", "DROP", "PARK", "CLOSE", "TERMINATE"}


def load_snapshot(path):
    """Read the snapshot JSON file. Returns {} if missing or unparseable -- never
    raises; the CLI decides what "fail loud" means for its own inputs, not this
    internal state file."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_snapshot(path, current):
    """Atomically write `current` ({page_id: {"deal":..., "stage":...}}) to `path`."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp-write"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)


def diff_stages(current, snapshot):
    """Compare current live Notion state against the last-seen snapshot.
    current / snapshot: {page_id: {"deal": str, "stage": str}}.
    Returns a list of transition dicts, one per page_id whose stage differs from (or is
    absent from) the snapshot: {"page_id", "deal", "old_stage", "new_stage"}.
    old_stage is None for a page_id not present in the snapshot (first time seen).
    A page_id present in the snapshot but missing from current (e.g. archived in
    Notion) is NOT reported -- disappearance is not a stage change."""
    transitions = []
    for page_id, info in current.items():
        deal = info.get("deal", "")
        new_stage = info.get("stage", "")
        prior = snapshot.get(page_id)
        old_stage = prior.get("stage") if prior else None
        if old_stage != new_stage:
            transitions.append({
                "page_id": page_id,
                "deal": deal,
                "old_stage": old_stage,
                "new_stage": new_stage,
            })
    return transitions
```

Leave `classify_disposition`, `format_event_log_entry`, `format_ledger_row`, and `main` for Tasks 2-3 — this task stops here so its test file only exercises what exists so far.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: `deal-stage-reconciler tests: 11/11 passed`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Owner\.claude"
git add maintenance/deal-stage-reconciler.py maintenance/test-deal-stage-reconciler.py
git commit -m "feat(maintenance): deal-stage-reconciler snapshot I/O + diff detection"
```

---

### Task 2: Disposition classification + entry formatting

**Files:**
- Modify: `C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py` (append functions)
- Modify: `C:\Users\Owner\.claude\maintenance\test-deal-stage-reconciler.py` (append tests before the summary block)

**Interfaces:**
- Consumes: `DISPOSITION_TOKENS` (set, from Task 1).
- Produces: `classify_disposition(new_stage: str, stage_map: dict) -> str|None`, `format_event_log_entry(transition: dict, date: str) -> str`, `format_ledger_row(transition: dict, disposition: str, date: str, reason: str|None = None) -> str`.

- [ ] **Step 1: Write the failing tests**

Insert into `test-deal-stage-reconciler.py`, directly above the `# --- summary ---` block:

```python
# --- classify_disposition -------------------------------------------------------------
stage_map = {"Passed": "PASS", "Killed": "TERMINATE", "Under Review": "NOT_A_TOKEN"}
expect("classify_disposition: mapped stage returns its token",
       dsr.classify_disposition("Passed", stage_map) == "PASS")
expect("classify_disposition: unmapped stage returns None",
       dsr.classify_disposition("Candidate", stage_map) is None)
expect("classify_disposition: mapped-but-invalid-token returns None (never guesses)",
       dsr.classify_disposition("Under Review", stage_map) is None)

# --- format_event_log_entry / format_ledger_row ----------------------------------------
t = {"page_id": "pg2", "deal": "470 McCormick Blvd", "old_stage": "In Negotiation",
     "new_stage": "Passed"}
entry = dsr.format_event_log_entry(t, "2026-07-08")
expect("format_event_log_entry: starts with dated header",
       entry.startswith("## 2026-07-08 — Deal-stage sync: 470 McCormick Blvd"),
       entry)
expect("format_event_log_entry: mentions both stages",
       "In Negotiation" in entry and "Passed" in entry)

t_new = {"page_id": "pg2", "deal": "470 McCormick Blvd", "old_stage": None,
         "new_stage": "Passed"}
entry_new = dsr.format_event_log_entry(t_new, "2026-07-08")
expect("format_event_log_entry: None old_stage renders as (none), not the word None",
       "(none)" in entry_new and "None" not in entry_new)

row = dsr.format_ledger_row(t, "PASS", "2026-07-08")
expect("format_ledger_row: correct column count", row.count("|") == 6, row)
expect("format_ledger_row: uses the standing fallback reason when none given",
       "reason not logged elsewhere" in row)

row_with_reason = dsr.format_ledger_row(t, "PASS", "2026-07-08",
                                         reason="LOI lapsed, Gabriel killed in-session")
expect("format_ledger_row: uses supplied reason when given",
       "LOI lapsed" in row_with_reason
       and "reason not logged elsewhere" not in row_with_reason)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: `AttributeError: module 'dsr' has no attribute 'classify_disposition'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `deal-stage-reconciler.py` (after `diff_stages`):

```python
def classify_disposition(new_stage, stage_map):
    """Map a live Notion Stage string to a terminal-disposition token using `stage_map`
    ({notion_stage_string: disposition_token}). Returns the token only if `new_stage` is
    a key in `stage_map` AND the mapped value is a real DISPOSITION_TOKENS member;
    otherwise None -- never guesses. None means "log to event_log only, no ledger row"."""
    token = stage_map.get(new_stage)
    if token in DISPOSITION_TOKENS:
        return token
    return None


def format_event_log_entry(transition, date):
    """Render the dated event_log.md entry body for one transition. `date` is a
    'YYYY-MM-DD' string supplied by the caller -- never computed inside this pure
    function (no datetime.today() here, so it stays trivially testable)."""
    deal = transition["deal"]
    old = transition["old_stage"] if transition["old_stage"] is not None else "(none)"
    new = transition["new_stage"]
    return (
        "## %s — Deal-stage sync: %s — %s → %s (Notion)\n\n"
        "Detected by ora-open-sessions-board's reconciliation step; no corresponding "
        "entry existed. Tripwire only — see Notion for the actual decision context."
        % (date, deal, old, new)
    )


def format_ledger_row(transition, disposition, date, reason=None):
    """Render one deal-decision-ledger.md markdown table row: | Date | Deal | Verdict |
    One-line reason | Buy-box rule validated / refined |. `reason` is the one-line
    rationale if known; when None, uses the standing fallback rather than fabricating
    one."""
    if reason is None:
        reason = ("Notion Stage → %s; reason not logged elsewhere — "
                   "reconcile manually" % transition["new_stage"])
    return "| %s | %s | %s | %s | — |" % (date, transition["deal"], disposition,
                                                 reason)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: `deal-stage-reconciler tests: 20/20 passed`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Owner\.claude"
git add maintenance/deal-stage-reconciler.py maintenance/test-deal-stage-reconciler.py
git commit -m "feat(maintenance): deal-stage-reconciler disposition classification + entry formatting"
```

---

### Task 3: CLI wrapper (bootstrap mode, exit codes)

**Files:**
- Modify: `C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py` (append `main`)
- Modify: `C:\Users\Owner\.claude\maintenance\test-deal-stage-reconciler.py` (append E2E tests)

**Interfaces:**
- Consumes: everything from Tasks 1-2.
- Produces: `main(argv=None) -> int`; stdout JSON contract `{"transitions": [{"page_id","deal","old_stage","new_stage","disposition","event_log_entry","ledger_row"}, ...], "count": N}` (normal mode) or `{"bootstrap": true, "count": N}` (`--bootstrap` mode); exit 0 = ran fine, exit 2 = could not read `--current-file`/`--stage-map-file`.

- [ ] **Step 1: Write the failing tests**

Insert into `test-deal-stage-reconciler.py`, directly above the `# --- summary ---` block (and add `import subprocess, sys` to the top-of-file imports):

```python
# --- CLI (E2E via subprocess, mirroring test-governor-drift-probe.py's pattern) --------
def run_cli(args):
    return subprocess.run([sys.executable, MOD_PATH] + args,
                           capture_output=True, text=True)

cli_current_path = os.path.join(tmpdir, "cli-current.json")
with open(cli_current_path, "w", encoding="utf-8") as f:
    json.dump(current, f)
cli_map_path = os.path.join(tmpdir, "cli-map.json")
with open(cli_map_path, "w", encoding="utf-8") as f:
    json.dump({"Passed": "PASS"}, f)
cli_snapshot_path = os.path.join(tmpdir, "cli-snapshot.json")
dsr.save_snapshot(cli_snapshot_path, snapshot)

proc = run_cli(["--current-file", cli_current_path, "--stage-map-file", cli_map_path,
                "--snapshot-file", cli_snapshot_path, "--date", "2026-07-10"])
expect("CLI: exit 0 on normal run", proc.returncode == 0, proc.stderr)
payload = json.loads(proc.stdout) if proc.returncode == 0 else {}
expect("CLI: reports 2 transitions", payload.get("count") == 2, payload)
expect("CLI: 470 transition carries a PASS disposition + non-null ledger_row",
       any(x["deal"] == "470 McCormick Blvd" and x["disposition"] == "PASS"
           and x["ledger_row"] for x in payload.get("transitions", [])),
       payload)
expect("CLI: 511 transition has no disposition (not in stage_map) and null ledger_row",
       any(x["deal"] == "511 Industrial Mile Rd" and x["disposition"] is None
           and x["ledger_row"] is None for x in payload.get("transitions", [])),
       payload)
expect("CLI: snapshot file updated to current state",
       dsr.load_snapshot(cli_snapshot_path) == current)

bootstrap_snapshot_path = os.path.join(tmpdir, "bootstrap-snapshot.json")
proc2 = run_cli(["--current-file", cli_current_path, "--stage-map-file", cli_map_path,
                 "--snapshot-file", bootstrap_snapshot_path, "--bootstrap"])
expect("CLI --bootstrap: exit 0", proc2.returncode == 0, proc2.stderr)
bootstrap_payload = json.loads(proc2.stdout) if proc2.returncode == 0 else {}
expect("CLI --bootstrap: reports bootstrap true, no transitions key",
       bootstrap_payload.get("bootstrap") is True
       and "transitions" not in bootstrap_payload)
expect("CLI --bootstrap: snapshot seeded to current state",
       dsr.load_snapshot(bootstrap_snapshot_path) == current)

proc3 = run_cli(["--current-file", os.path.join(tmpdir, "nope.json"),
                 "--stage-map-file", cli_map_path])
expect("CLI: missing --current-file exits 2 (fail loud)", proc3.returncode == 2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: `subprocess` invocation fails or returns a non-JSON/non-zero result, since `main`/`__main__` don't exist yet (argparse error / SystemExit noise on stderr, `json.loads` raising).

- [ ] **Step 3: Write the minimal implementation**

Append to `deal-stage-reconciler.py`:

```python
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Deal-stage reconciler: diff live Notion stage values against the "
                     "last snapshot.")
    ap.add_argument("--current-file", required=True,
                     help="JSON file: {page_id: {\"deal\":..., \"stage\":...}} (live "
                          "Notion state, written by the caller -- never stdin, see "
                          "feedback_append_event_log_stdin_encoding.md)")
    ap.add_argument("--stage-map-file", required=True,
                     help="JSON file: {notion_stage_string: disposition_token}")
    ap.add_argument("--snapshot-file", default=DEFAULT_SNAPSHOT,
                     help="path to the rolling snapshot (default: canonical _state path)")
    ap.add_argument("--bootstrap", action="store_true",
                     help="seed the snapshot from --current-file with ZERO diff output "
                          "(first-run only -- never logs pre-existing state as a change)")
    ap.add_argument("--date", default=None,
                     help="YYYY-MM-DD to stamp entries with (default: today)")
    a = ap.parse_args(argv)

    try:
        with open(a.current_file, encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write("cannot read --current-file: %s\n" % e)
        return 2
    if not isinstance(current, dict):
        sys.stderr.write("--current-file must contain a JSON object\n")
        return 2

    if a.bootstrap:
        save_snapshot(a.snapshot_file, current)
        print(json.dumps({"bootstrap": True, "count": len(current)}))
        return 0

    try:
        with open(a.stage_map_file, encoding="utf-8") as f:
            stage_map = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write("cannot read --stage-map-file: %s\n" % e)
        return 2
    if not isinstance(stage_map, dict):
        sys.stderr.write("--stage-map-file must contain a JSON object\n")
        return 2

    date = a.date or dt.date.today().isoformat()
    snapshot = load_snapshot(a.snapshot_file)
    transitions = diff_stages(current, snapshot)
    out = []
    for t in transitions:
        disposition = classify_disposition(t["new_stage"], stage_map)
        out.append({
            "page_id": t["page_id"],
            "deal": t["deal"],
            "old_stage": t["old_stage"],
            "new_stage": t["new_stage"],
            "disposition": disposition,
            "event_log_entry": format_event_log_entry(t, date),
            "ledger_row": (format_ledger_row(t, disposition, date)
                            if disposition else None),
        })
    save_snapshot(a.snapshot_file, current)
    print(json.dumps({"transitions": out, "count": len(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\Users\Owner\.claude\maintenance && python test-deal-stage-reconciler.py`
Expected: `deal-stage-reconciler tests: 29/29 passed`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Owner\.claude"
git add maintenance/deal-stage-reconciler.py maintenance/test-deal-stage-reconciler.py
git commit -m "feat(maintenance): deal-stage-reconciler CLI wrapper with bootstrap mode"
```

---

### Task 4: Backfill the two known gaps (511, 470)

**Files:**
- Modify (append only, via the sanctioned script): `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\event_log.md`
- Modify (Edit-tool append): `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\deal-decision-ledger.md`

**Interfaces:** None from earlier tasks (this is a one-time content backfill, hand-composed to match this file's existing richer narrative style rather than the terse auto-detected-tripwire template from Task 2 — these two events already have full documented context, unlike a future auto-detected gap that won't). Produces facts Task 5 will read live from Notion (current Stage values) to seed the snapshot.

- [ ] **Step 1: Confirm current live Notion Stage values for both deals**

Using the Notion MCP (`mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-fetch` or `notion-query-data-sources` against data source `bcfe4a037e614ac1a0bbc44174fa138b`), look up the current `Stage` property and page ID for **511 Industrial Mile Rd, Columbus OH** and **470 McCormick Blvd, Columbus OH**. Record both page IDs — Task 5 needs them to seed the snapshot correctly. Per `projects.md`, expect roughly `Candidate` for 511 and `Passed` for 470, but confirm live rather than assuming.

- [ ] **Step 2: Write the event_log.md entry for 511's reset**

Write a temp file (e.g. `C:\Users\Owner\.claude\_confidential-staging\dsr-backfill-511.md` — not confidential content, just using an existing scratch location; any temp path is fine) containing:

```
## 2026-07-09 — Deal-stage sync (backfill): 511 Industrial Mile Rd reset to Candidate

Cross-fleet logging gap found by the 2026-07-09 setup audit (see
project_claude-setup-audit-2026-07-09.md) and closed by this entry, backfilled as part
of building the deal-stage-reconciliation mechanism (see the 2026-07-09
cross-fleet-deal-stage-reconciliation design spec). Per Gabriel via the open-sessions
board: LOI v02 (submitted 5/15, ack'd 5/18) went 30 days without ever resolving
executed/countered/open, so the deal was reset back to re-screening rather than carried
forward as "keep open." Notion's "LOI Status" field still literally read "Submitted" at
the time of reset — not yet reconciled, per projects.md's own flag. This is a
non-terminal state change (re-screen, not a PASS/SKIP/DROP/PARK/CLOSE/TERMINATE
disposition) — logged here only, no deal-decision-ledger.md row.
```

Then run: `python C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file C:\Users\Owner\.claude\_confidential-staging\dsr-backfill-511.md`
Expected: `appended: ## 2026-07-09 — Deal-stage sync (backfill): 511 Industrial Mile Rd reset to Candidate`, exit 0.

- [ ] **Step 3: Write the event_log.md entry for 470's pass**

Write a second temp file containing:

```
## 2026-07-08 — Deal-stage sync (backfill): 470 McCormick Blvd, Columbus OH — PASSED / CLOSED

Cross-fleet logging gap found by the 2026-07-09 setup audit (see
project_claude-setup-audit-2026-07-09.md) and closed by this entry, backfilled as part
of building the deal-stage-reconciliation mechanism (see the 2026-07-09
cross-fleet-deal-stage-reconciliation design spec). LOI FINAL v2 (adversarial-review
hardened 6/10) was never shipped to broker KRG; its 6/17/2026 expiration lapsed 21 days
before Gabriel made an explicit in-session kill decision on 7/8. No counterparty was
ever contacted, so nothing needed to be retracted. HB 126 note and the IOS land thesis
are now moot. Terminal disposition — see the companion deal-decision-ledger.md row
added in the next step.
```

Then run: `python C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file <path to the second temp file>`
Expected: `appended: ## 2026-07-08 — Deal-stage sync (backfill): 470 McCormick Blvd, Columbus OH — PASSED / CLOSED`, exit 0. **Note:** `append-event-log.py` always inserts as the newest entry regardless of the date in the header, so this 7/8-dated entry will land physically above the 7/9-dated 511 entry from Step 2 if run second — that's expected and matches the log's existing "newest insertion, not strictly newest date" behavior elsewhere in the file (e.g. multiple same-day entries are not internally date-sorted either). Run Step 2 and this step in either order; both are correct once both exist.

- [ ] **Step 4: Add the deal-decision-ledger.md row for 470**

Read `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\deal-decision-ledger.md` first (required before any Edit). Using the Edit tool, insert a new row immediately after the table header's separator row (so it becomes the newest/top data row, matching this file's existing top-down-by-recency ordering — the 2026-07-09 E. Fulton row is currently first):

```
| 2026-07-08 | 470 McCormick Blvd, Columbus OH | PASS | LOI FINAL v2's 6/17/2026 expiration lapsed 21 days unshipped to broker KRG; Gabriel made an explicit in-session kill decision 7/8 rather than let it drift further | — |
```

- [ ] **Step 5: Verify both files**

Read both files back and confirm: `event_log.md` contains both new headers verbatim; `deal-decision-ledger.md`'s new row parses as a valid table row (same `|`-column count as its neighbors) and sits above the 2026-07-09 E. Fulton row. No commit needed (`memory/` is gitignored, not tracked).

---

### Task 5: Discover the Stage vocabulary + bootstrap the live snapshot

**Files:**
- Create: `C:\Users\Owner\.claude\maintenance\deal-stage-map.json`
- Create (via the CLI, not hand-written): `C:\Users\Owner\.claude\maintenance\_state\deal-stage-snapshot.json`

**Interfaces:**
- Consumes: Task 3's CLI (`--bootstrap` mode), Task 4's confirmed page IDs.
- Produces: `deal-stage-map.json` — `{notion_stage_string: disposition_token}`, real values discovered live (not guessed); `deal-stage-snapshot.json` seeded with every current Acquisition Pipeline Tracker row.

- [ ] **Step 1: Pull the live Notion Stage property schema**

Using the Notion MCP against data source `bcfe4a037e614ac1a0bbc44174fa138b` (e.g. `mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__search_properties` or the data source's own schema call — inspect what's available via `ToolSearch` for `notion` if unloaded), list every option value the `Stage` property actually supports. Do not assume the option list documented anywhere in memory is current — memory says "Recently resolved" statuses seen so far are "Passed"/"Killed"/"Dropped for now"/"Closed"/"Parked" (from `projects.md`'s "Recently resolved" line and `deal-decision-ledger.md`'s Verdict column) plus in-flight ones like "Candidate"/"Under Review"/"In Negotiation"/"Reviewing" — but treat all of this as a hypothesis to confirm against the live schema, not a given.

- [ ] **Step 2: Write `deal-stage-map.json`**

Map every Stage option that represents a terminal disposition to one of the six tokens; every non-terminal Stage option (Candidate, Under Review, In Negotiation, etc.) is simply omitted from the map (an omitted key naturally classifies as `None` via `classify_disposition`, per Task 2 — no need to enumerate non-terminal stages). Example shape (populate with the REAL discovered option strings from Step 1, not this placeholder set):

```json
{
  "Passed": "PASS",
  "Killed": "TERMINATE",
  "Dropped for now": "DROP",
  "Parked": "PARK",
  "Closed": "CLOSE"
}
```

If a live Stage option's terminal-vs-not classification is genuinely ambiguous, leave it out of the map (defaults to event_log-only logging, never guess a disposition) and note the ambiguity in the run summary for Gabriel to resolve later.

- [ ] **Step 3: Pull current live Stage values for every Acquisition Pipeline Tracker row**

Query every row (not just 511/470) in data source `bcfe4a037e614ac1a0bbc44174fa138b`; build `{page_id: {"deal": <name>, "stage": <live Stage value>}}` for all of them — including 511 and 470, using the page IDs confirmed in Task 4 Step 1. Write this to a temp JSON file (e.g. `C:\Users\Owner\.claude\_confidential-staging\dsr-bootstrap-current.json`).

- [ ] **Step 4: Run the bootstrap**

Run: `python C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py --current-file C:\Users\Owner\.claude\_confidential-staging\dsr-bootstrap-current.json --stage-map-file C:\Users\Owner\.claude\maintenance\deal-stage-map.json --bootstrap`
Expected: stdout `{"bootstrap": true, "count": N}` where N is the total row count, exit 0.

- [ ] **Step 5: Verify**

Read `C:\Users\Owner\.claude\maintenance\_state\deal-stage-snapshot.json` and confirm it contains an entry for every Acquisition Pipeline Tracker row, with 511 showing `stage: "Candidate"` (or whatever Task 4 Step 1 actually confirmed) and 470 showing `stage: "Passed"`.

---

### Task 6: Wire STEP 4.5 into `ora-open-sessions-board`

**Files:**
- Modify: `C:\Users\Owner\.claude\scheduled-tasks\ora-open-sessions-board\SKILL.md` (not git-tracked; no commit step for this file)

**Interfaces:**
- Consumes: `deal-stage-reconciler.py`'s CLI contract (Task 3), `deal-stage-map.json` (Task 5).

- [ ] **Step 1: Read the current file**

Read `C:\Users\Owner\.claude\scheduled-tasks\ora-open-sessions-board\SKILL.md` in full (required before any Edit — it was already read once during brainstorming, but re-read now in case another session touched it since).

- [ ] **Step 2: Insert STEP 4.5 between STEP 4 and STEP 5**

Using the Edit tool, insert this new step directly after STEP 4's closing paragraph (which ends `"...Never present a stale deal decision as live."`) and before the `STEP 5 — RENDER + NOTIFY.` line:

```
STEP 4.5 — DEAL-STAGE RECONCILIATION (Notion diff; closes the cross-fleet logging gap
documented 2026-07-09 — see docs/superpowers/specs/2026-07-09-cross-fleet-deal-stage-reconciliation-design.md).
Query the Notion Acquisition Pipeline Tracker (data source bcfe4a037e614ac1a0bbc44174fa138b)
for every row's live Stage value + page ID; write {page_id: {"deal":..., "stage":...}}
to a temp JSON file (never pipe through stdin -- see feedback_append_event_log_stdin_encoding.md).
Run:
  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\deal-stage-reconciler.py --current-file <temp.json> --stage-map-file C:\Users\Owner\.claude\maintenance\deal-stage-map.json
For each transition in its JSON stdout: append event_log_entry via
  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file <temp entry file>
and, if disposition is non-null, append ledger_row as a new top row in
C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\deal-decision-ledger.md
via the Edit tool (read the file first). If the script exits non-zero (Notion
unreachable or a malformed temp file), do NOT halt the board -- note
"deal-stage reconciliation: SKIPPED (<reason>)" for the run summary and continue to
STEP 5; it self-heals on tomorrow's run.
```

- [ ] **Step 3: Extend the RUN SUMMARY line**

Using the Edit tool, change the existing RUN SUMMARY line from:

```
RUN SUMMARY (always, last line, for the health guard): "ora-open-sessions-board: probed [N] unarchived / [M] actionable / board [rendered|clear|markdown-fallback] / email [sent|skipped|FAILED] / errors [none|list]".
```

to:

```
RUN SUMMARY (always, last line, for the health guard): "ora-open-sessions-board: probed [N] unarchived / [M] actionable / board [rendered|clear|markdown-fallback] / email [sent|skipped|FAILED] / deal-stage reconciliation [K transitions logged|SKIPPED (reason)] / errors [none|list]".
```

- [ ] **Step 4: Verify**

Read the file back and confirm STEP 4.5 sits between STEP 4 and STEP 5, references the exact `deal-stage-reconciler.py` and `append-event-log.py` paths used elsewhere in this same file (matching its own established full-python-path convention, stated at the top: `"Use the FULL python path for any python: ..."`), and that the RUN SUMMARY line is valid single-line text (no stray line breaks).

---

### Task 7: Live dry-run end-to-end verification

**Files:** None created; this task only verifies the wiring built in Tasks 1-6 and leaves the real snapshot correct afterward.

**Interfaces:** Consumes everything from Tasks 1-6.

- [ ] **Step 1: Confirm a real no-op first pass**

Run the same live-Notion-query + CLI invocation described in STEP 4.5 (Task 6) once, for real, using the actual snapshot seeded in Task 5. Expected: `count: 0` (nothing changed since the Task 5 bootstrap moments ago) — this is the "no false positives on a freshly-seeded snapshot" check the design spec calls for.

- [ ] **Step 2: Force one synthetic transition**

Read `C:\Users\Owner\.claude\maintenance\_state\deal-stage-snapshot.json`, note 511 Industrial Mile Rd's current recorded stage (`"Candidate"` per Task 5), then temporarily Edit just that one entry's `"stage"` value to a different string (e.g. `"TEST-PRIOR-STAGE"`) — simulating "the snapshot is stale, a real change happened."

- [ ] **Step 3: Re-run the reconciliation step**

Re-run the same live Notion query + CLI invocation. Expected: exactly one transition reported for 511's page_id, with `old_stage: "TEST-PRIOR-STAGE"` and `new_stage` equal to whatever 511's real live Stage value is; `disposition: null` (Candidate/Under-Review-class stages aren't in the map) confirming the event-log-only path. Manually carry out what STEP 4.5 instructs: append the `event_log_entry` via `append-event-log.py`, confirm no ledger row is added (disposition was null).

- [ ] **Step 4: Restore true state**

Confirm the CLI's own snapshot write already corrected `deal-stage-snapshot.json` back to 511's real live stage (Step 3's run overwrites the snapshot with `current`, so this should already be true — verify by reading the file). Since Step 3 produced a real (if synthetic-triggered) `event_log.md` entry documenting a fabricated "TEST-PRIOR-STAGE → real stage" transition, follow up with one more real `append-event-log.py` entry noting this was a deliberate verification exercise, e.g.:

```
## <today> — Note: prior entry was a deliberate dry-run verification artifact

The immediately-preceding "Deal-stage sync" entry for 511 Industrial Mile Rd (showing
old_stage "TEST-PRIOR-STAGE") was produced by Task 7's live dry-run verification of the
deal-stage-reconciler mechanism (see the 2026-07-09 cross-fleet-deal-stage-reconciliation
design spec + implementation plan) — a deliberately forced synthetic transition, not a
real Notion event. Logged for continuity so a future reader isn't confused by the
fabricated old_stage value.
```

- [ ] **Step 5: Final verification**

Read `event_log.md`'s top entries and `deal-stage-snapshot.json` to confirm: the real 511/470 backfill entries from Task 4 are present, the synthetic-transition entry and its explanatory follow-up from this task are present and clearly labeled as a verification artifact, and the snapshot file's every entry matches genuinely live Notion state (no leftover `"TEST-PRIOR-STAGE"` value anywhere). Report the full picture back — this closes the plan.
