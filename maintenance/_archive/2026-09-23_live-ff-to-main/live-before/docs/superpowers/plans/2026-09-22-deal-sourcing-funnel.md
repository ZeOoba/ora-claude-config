# Deal-Sourcing Funnel Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the owner-outreach mail log, add a T2 call sheet and a monthly conversion report, and teach the passed-deal tracker to detect re-marketed passes from broker email.

**Architecture:** Three new single-purpose Python scripts beside the existing outreach pipeline (`reconstruct_pack_manifest.py`, `build_t2_callsheet.py`, `outreach_conversion_report.py`), one refactor of the `--released` path in `owner_outreach_weekly.py` into a testable function with a `--manifest` option and duplicate guard, and a prose Step 3b added to the `ora-passed-deal-tracker` scheduled-task SKILL.md. All logic is file-based (CSV/XLSX/DOCX); no script calls Notion or sends mail.

**Tech Stack:** Python 3 (stdlib `csv`, `json`, `re`, `datetime`), `python-docx`, `openpyxl`; plain-assert test runners matching `test_owner_outreach_ladder.py`.

**Spec:** `~/.claude/docs/superpowers/specs/2026-09-22-deal-sourcing-funnel-design.md`

## Global Constraints

- Pipeline folder (`$OO`): `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Investment Candidates -- 2026\` — NOT a git repo. Versioning = archive-first: copy every existing file to `$OO\_archive\2026-09-22_funnel-upgrades_checkpoint\` before its first modification. Never delete (Invariant 6).
- Nothing sends to owners (Invariant 1). Scripts never call Notion or email.
- Suppression single source of truth: `outreach-responses.csv` via `log_outreach_response.py`. Every logged outcome stops further letters.
- Ratified ladder (OR-2026-001, `outreach-ratification.json`): T2 call at +30 days from T1; call slice 5–8/week; `min_touch_gap_days` 21. Read these from the JSON, never hardcode.
- Backfill dates (Gabriel, 2026-09-22): pack-build dates — 2026-09-02, 2026-09-07, 2026-09-14.
- Existing test suite must stay green: `python test_owner_outreach_ladder.py` → `ALL LADDER TESTS PASS (70)`.
- Queue workbook: sheet `Queue`, header row 1: `Market Priority, Metro, County, Score, P1 %, Motivation, Verdict P1, Floor Result, Bldg SF, Modeled Mkt $, Parcel ID, Site Address, Owner, Mail Name, Owner Mailing (Tier-0), Tier-0 Ready, Cadence Status, Touch #, Next Touch`. `Motivation` is a numeric 0–10 score.
- Pack DOCX: one paragraph per letter beginning `Re:` listing site addresses separated by ` · ` (U+00B7) with the market name as the final token; header paragraph `Letters in pack: N owners · covering M Tier-0-ready properties`.
- Email routing (tracker): ggoldberg@oxfordra.net only via `send-via-outlook.ps1`.
- `~/.claude` and `ora-skills` are shared checkouts: gate with `python ~/.claude/maintenance/preflight-shared-checkout.py` and land via the `isolated-commit` skill; `git add <path>` only.

## File Map

| File | Action | Responsibility |
|---|---|---|
| `$OO\reconstruct_pack_manifest.py` | Create | DOCX pack + queue → manifest JSON (parcel list) |
| `$OO\test_reconstruct_pack_manifest.py` | Create | Tests for above |
| `$OO\owner_outreach_weekly.py` | Modify (`--released` block ~L465-484; arg parser ~L407; scan tail after L671) | `record_release()` + `--manifest`; wire call sheet + monthly report |
| `$OO\test_record_release.py` | Create | Tests for `record_release()` |
| `$OO\build_t2_callsheet.py` | Create | Eligible T2 parcels → call-sheet XLSX + `call-log.csv` |
| `$OO\test_t2_callsheet.py` | Create | Tests |
| `$OO\outreach_conversion_report.py` | Create | Mail × response × queue → markdown + CSV |
| `$OO\test_conversion_report.py` | Create | Tests |
| `C:\Users\Owner\ora-skills\owner-outreach\SKILL.md` | Modify | Document new flags/scripts; drop stale "T2–T4 pending" |
| `C:\Users\Owner\.claude\scheduled-tasks\ora-passed-deal-tracker\SKILL.md` | Modify | Add Step 3b + output section |

---

### Task 1: Archive checkpoint

**Files:** Create `$OO\_archive\2026-09-22_funnel-upgrades_checkpoint\`

- [ ] **Step 1: Snapshot files that will be modified or appended**

```bash
cd "/c/Users/Owner/OneDrive - Oxford Capital Partners/Business/Investment Candidates -- 2026"
D=_archive/2026-09-22_funnel-upgrades_checkpoint; mkdir -p "$D"
cp -p owner_outreach_weekly.py mail-log.csv _oo_pack_manifest.json "$D"/
ls "$D"
```
Expected: the three files listed.

- [ ] **Step 2: Baseline tests**

Run: `python test_owner_outreach_ladder.py` → `ALL LADDER TESTS PASS (70)`

---

### Task 2: Reconstruct pack manifests from DOCX

**Files:** Create `$OO\reconstruct_pack_manifest.py`, `$OO\test_reconstruct_pack_manifest.py`

**Interfaces:**
- Produces: `norm_addr(s: str) -> str`; `parse_pack(docx_path) -> tuple[list[list[str]], int|None]` (addresses per letter, declared property count); `reconstruct(docx_path, queue_path, touch=1) -> dict` with keys `built, queue, pack, touch, parcel_ids, reconstructed` — same shape as `_oo_pack_manifest.json` plus `reconstructed: true`. Raises `ValueError` on any unmatched/ambiguous address or count mismatch.

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for reconstruct_pack_manifest.py. Run: python test_reconstruct_pack_manifest.py"""
import tempfile
from pathlib import Path
import docx, openpyxl
import reconstruct_pack_manifest as r

FAIL, RUN = [], []
def check(n, got, want):
    RUN.append(n)
    if got != want: FAIL.append(f"{n}: expected {want!r}, got {got!r}")
def raises(n, fn):
    RUN.append(n)
    try: fn(); FAIL.append(f"{n}: no ValueError")
    except ValueError: pass

HDR = ["Market Priority","Metro","County","Score","P1 %","Motivation","Verdict P1","Floor Result",
       "Bldg SF","Modeled Mkt $","Parcel ID","Site Address","Owner","Mail Name",
       "Owner Mailing (Tier-0)","Tier-0 Ready","Cadence Status","Touch #","Next Touch"]
def queue(d, rows):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Queue"; ws.append(HDR)
    for pid, addr in rows:
        ws.append([1,"Columbus","Franklin",90,80,5,"T1","CLEAR",20000,1,pid,addr,"O","O","M","Y","Active",0,None])
    p = Path(d)/"20260902_Owner-Outreach-Queue_Phase1_v01.xlsx"; wb.save(p); return p
def pack(d, res, declared):
    doc = docx.Document()
    doc.add_paragraph(f"Letters in pack: {len(res)} owners \u00b7 covering {declared} Tier-0-ready properties")
    for addrs in res:
        doc.add_paragraph("Re:  " + " \u00b7 ".join(addrs + ["Columbus"]))
    p = Path(d)/"20260902_Owner-Outreach_T1-Letter-Pack_Phase1_v01.docx"; doc.save(p); return p

check("norm", r.norm_addr("1221 - 1225 Marion Rd."), r.norm_addr("1221 - 1225 MARION RD"))
with tempfile.TemporaryDirectory() as d:
    q = queue(d, [("A1","2073 REFUGEE RD"),("B2","960 W WALNUT ST"),("C3","5 MAIN ST")])
    p = pack(d, [["2073 Refugee Rd"], ["960 W Walnut St","5 Main St"]], 3)
    m = r.reconstruct(p, q)
    check("pids", m["parcel_ids"], ["A1","B2","C3"])
    check("built", m["built"], "2026-09-02")
    check("touch", m["touch"], 1)
    check("flag", m["reconstructed"], True)
    p2 = pack(d, [["2073 Refugee Rd"], ["99 Nowhere Ln"]], 2)
    raises("unmatched halts", lambda: r.reconstruct(p2, q))
    p3 = pack(d, [["2073 Refugee Rd"]], 5)
    raises("count mismatch halts", lambda: r.reconstruct(p3, q))
    q2 = queue(d, [("A1","2073 REFUGEE RD"),("A9","2073 REFUGEE RD")])
    p4 = pack(d, [["2073 Refugee Rd"]], 1)
    raises("ambiguous halts", lambda: r.reconstruct(p4, q2))

if FAIL: print("\n".join(FAIL)); raise SystemExit(1)
print(f"ALL RECONSTRUCT TESTS PASS ({len(RUN)})")
```

- [ ] **Step 2: Run — expect failure**

Run: `python test_reconstruct_pack_manifest.py` → `ModuleNotFoundError: No module named 'reconstruct_pack_manifest'`

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python
"""Rebuild an owner-outreach pack manifest from the pack DOCX + its queue.

_oo_pack_manifest.json is overwritten on every build, so a pack mailed but
never recorded with --released loses its parcel list. This recovers it:
each letter's "Re:" line lists site addresses (" · "-separated, market last);
each address is matched to exactly one Parcel ID in the same-date queue.
All-or-nothing: any unmatched/ambiguous address or a property count that
disagrees with the pack header raises -- a partial mail log is worse than none.

    python reconstruct_pack_manifest.py PACK.docx QUEUE.xlsx --out manifest.json
"""
import argparse, json, re, sys
from pathlib import Path
import docx, openpyxl

SEP = "\u00b7"

def norm_addr(s):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())).strip()

def parse_pack(docx_path):
    letters, declared = [], None
    for p in docx.Document(str(docx_path)).paragraphs:
        t = p.text.strip()
        m = re.search(r"covering (\d+) ", t)
        if t.startswith("Letters in pack:") and m:
            declared = int(m.group(1))
        elif t.startswith("Re:"):
            parts = [x.strip() for x in t[3:].split(SEP) if x.strip()]
            letters.append(parts[:-1])  # final token is the market name
    return letters, declared

def queue_index(queue_path):
    ws = openpyxl.load_workbook(str(queue_path), read_only=True)["Queue"]
    rows = ws.iter_rows(values_only=True)
    hdr = list(next(rows))
    ip, ia = hdr.index("Parcel ID"), hdr.index("Site Address")
    idx = {}
    for row in rows:
        if row[ip]:
            idx.setdefault(norm_addr(row[ia]), []).append(str(row[ip]))
    return idx

def reconstruct(docx_path, queue_path, touch=1):
    docx_path, queue_path = Path(docx_path), Path(queue_path)
    letters, declared = parse_pack(docx_path)
    idx = queue_index(queue_path)
    pids, errs = [], []
    for addrs in letters:
        for a in addrs:
            hits = idx.get(norm_addr(a), [])
            if len(hits) != 1:
                errs.append(f"{a!r}: {len(hits)} queue matches")
            else:
                pids.append(hits[0])
    if errs:
        raise ValueError("unresolved addresses:\n  " + "\n  ".join(errs))
    if declared is not None and len(pids) != declared:
        raise ValueError(f"matched {len(pids)} parcels, pack header declares {declared}")
    if len(set(pids)) != len(pids):
        raise ValueError("duplicate parcel in pack")
    stamp = docx_path.name[:8]
    return {"built": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}", "queue": queue_path.name,
            "pack": docx_path.name, "touch": touch, "parcel_ids": pids,
            "reconstructed": True}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack"); ap.add_argument("queue")
    ap.add_argument("--touch", type=int, default=1, choices=(1, 3, 4))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        man = reconstruct(a.pack, a.queue, a.touch)
    except ValueError as e:
        sys.exit(f"[FATAL] {e}")
    Path(a.out).write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    print(f"[RECONSTRUCTED] {len(man['parcel_ids'])} parcels -> {a.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run — expect pass**

Run: `python test_reconstruct_pack_manifest.py` → `ALL RECONSTRUCT TESTS PASS (8)`

- [ ] **Step 5: Real-data dry run (no writes to production files)**

```bash
S="/c/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner/27a75818-48b6-4fdb-ba77-ff8b54c8da86/scratchpad"
for d in 20260902 20260907 20260914; do
  python reconstruct_pack_manifest.py ${d}_Owner-Outreach_T1-Letter-Pack_Phase1_v01.docx ${d}_Owner-Outreach-Queue_Phase1_v01.xlsx --out "$S/manifest_$d.json"; done
python -c "import json;a=json.load(open(r'$S/manifest_20260914.json'.replace('/c/','C:/')))['parcel_ids'];b=json.load(open('_oo_pack_manifest.json'))['parcel_ids'];print('09-14 matches live manifest:',sorted(a)==sorted(b))"
```
Expected: three `[RECONSTRUCTED] 50 parcels` (09-02 header says 50 properties) and `09-14 matches live manifest: True` — this cross-check validates the reconstruction method against ground truth. If any pack FATALs, stop and report the unresolved addresses; do not hand-patch.

---

### Task 3: `record_release()` with `--manifest` and duplicate guard

**Files:** Modify `$OO\owner_outreach_weekly.py` (arg parser near L407; `if a.released:` block L465-484). Create `$OO\test_record_release.py`.

**Interfaces:**
- Consumes: manifest dict shape from Task 2 / live `_oo_pack_manifest.json`.
- Produces: `record_release(man: dict, mdate: str, maillog: Path) -> tuple[int, int]` returning `(logged, skipped_duplicates)`. CLI: `--released YYYY-MM-DD --manifest PATH`.

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for record_release(). Run: python test_record_release.py"""
import csv, tempfile
from pathlib import Path
import owner_outreach_weekly as m

FAIL, RUN = [], []
def check(n, got, want):
    RUN.append(n)
    if got != want: FAIL.append(f"{n}: expected {want!r}, got {got!r}")

with tempfile.TemporaryDirectory() as d:
    log = Path(d) / "mail-log.csv"
    man = {"pack": "P1.docx", "touch": 1, "parcel_ids": ["A", "B"]}
    check("first", m.record_release(man, "2026-09-02", log), (2, 0))
    check("rerun idempotent", m.record_release(man, "2026-09-02", log), (0, 2))
    man2 = {"pack": "P2.docx", "touch": 1, "parcel_ids": ["B", "C"]}
    check("partial overlap", m.record_release(man2, "2026-09-07", log), (1, 1))
    man3 = {"pack": "P3.docx", "touch": 3, "parcel_ids": ["A"]}
    check("new touch same parcel", m.record_release(man3, "2026-12-01", log), (1, 0))
    rows = list(csv.DictReader(open(log, encoding="utf-8")))
    check("header+rows", [(r["parcel_id"], r["touch_num"]) for r in rows],
          [("A","1"),("B","1"),("C","1"),("A","3")])
    check("legacy manifest defaults T1",
          m.record_release({"parcel_ids": ["Z"]}, "2026-09-14", log), (1, 0))

if FAIL: print("\n".join(FAIL)); raise SystemExit(1)
print(f"ALL RELEASE TESTS PASS ({len(RUN)})")
```

- [ ] **Step 2: Run — expect failure**

Run: `python test_record_release.py` → `AttributeError: module 'owner_outreach_weekly' has no attribute 'record_release'`

- [ ] **Step 3: Implement — add function above `def main():` (L400)**

```python
def record_release(man, mdate, maillog):
    """Append a mailed pack to the mail log. Returns (logged, skipped).

    Logs the manifest's LADDER STAGE (see 2026-08-16 note in main). A
    parcel+stage pair already in the log is skipped, so re-running a
    release -- or backfilling a pack that overlaps one already logged --
    can never double-count a touch."""
    stage = int(man.get("touch", 1))
    seen = set()
    if maillog.exists():
        with open(maillog, newline="", encoding="utf-8") as f:
            seen = {(r["parcel_id"], str(r["touch_num"])) for r in csv.DictReader(f)}
    new_log = not maillog.exists()
    logged = skipped = 0
    with open(maillog, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["parcel_id", "mailed_date", "touch_num", "pack"])
        for pid in man["parcel_ids"]:
            if (pid, str(stage)) in seen:
                skipped += 1
                continue
            w.writerow([pid, mdate, stage, man.get("pack", "")])
            seen.add((pid, str(stage)))
            logged += 1
    return logged, skipped
```

- [ ] **Step 4: Add the argument (after the `--released` add_argument)**

```python
    # 2026-09-22: record a release against an explicit manifest (e.g. one
    # rebuilt by reconstruct_pack_manifest.py for a pack mailed but never
    # logged). Omitted = the last-built _oo_pack_manifest.json, as before.
    ap.add_argument("--manifest", default=None, metavar="PATH",
                    help="with --released: manifest JSON to record instead of "
                         "_oo_pack_manifest.json")
```

- [ ] **Step 5: Replace the `if a.released:` body (L465-484) with**

```python
    if a.released:
        mpath = Path(a.manifest) if a.manifest else PACK_MANIFEST
        if not mpath.exists():
            sys.exit(f"[FATAL] --released but no manifest at {mpath} (run a scan "
                     "first, or pass --manifest).")
        man = json.loads(mpath.read_text(encoding="utf-8"))
        mdate = today if a.released == "TODAY" else a.released
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", mdate):
            sys.exit(f"[FATAL] --released date must be YYYY-MM-DD, got: {mdate}")
        logged, skipped = record_release(man, mdate, MAILLOG)
        print(f"[RELEASED] logged {logged} T{int(man.get('touch', 1))} letters as "
              f"mailed {mdate} (pack: {man.get('pack','?')}); {skipped} already "
              f"logged, skipped -> {MAILLOG.name}")
        return
```
Confirm `from pathlib import Path` is imported at the top of the file (`grep -n "^from pathlib\|import.*Path" owner_outreach_weekly.py`); add it if absent.

- [ ] **Step 6: Run both suites**

Run: `python test_record_release.py && python test_owner_outreach_ladder.py`
Expected: `ALL RELEASE TESTS PASS (6)` and `ALL LADDER TESTS PASS (70)`

---

### Task 4: Execute the A0 backfill (production data)

**Files:** Append `$OO\mail-log.csv`; write `$OO\_oo_manifest_20260902.json`, `_oo_manifest_20260907.json`, `_oo_manifest_20260914.json`.

- [ ] **Step 1: Materialize manifests beside the pipeline**

```bash
for d in 20260902 20260907 20260914; do
  python reconstruct_pack_manifest.py ${d}_Owner-Outreach_T1-Letter-Pack_Phase1_v01.docx ${d}_Owner-Outreach-Queue_Phase1_v01.xlsx --out _oo_manifest_$d.json || exit 1; done
```

- [ ] **Step 2: Record releases at pack dates (oldest first)**

```bash
python owner_outreach_weekly.py --released 2026-09-02 --manifest _oo_manifest_20260902.json
python owner_outreach_weekly.py --released 2026-09-07 --manifest _oo_manifest_20260907.json
python owner_outreach_weekly.py --released 2026-09-14 --manifest _oo_manifest_20260914.json
```
Expected: each prints `[RELEASED] logged N T1 ...`. Nonzero `skipped` is legitimate only if a parcel appeared in two packs — report it.

- [ ] **Step 3: Verify**

```bash
tail -n +2 mail-log.csv | cut -d, -f2 | sort | uniq -c
python test_owner_outreach_ladder.py
```
Expected: 2026-08-24 = 50, plus one line per backfilled date with counts equal to Step 2's `logged`. Ladder tests 70 PASS.

- [ ] **Step 4: Log responses (blocked on Gabriel's response details)**

For each response Gabriel reports, resolve the parcel from the manifests/queue, then:
```bash
python log_outreach_response.py --parcel <PID> --outcome <stop|responded|not-interested|returned|converted> --note "<what they said>" --date <YYYY-MM-DD>
python log_outreach_response.py --pending
```
Expected: `--pending` lists each as unsynced JSON for the Notion step.

---

### Task 5: T2 call sheet

**Files:** Create `$OO\build_t2_callsheet.py`, `$OO\test_t2_callsheet.py`. Writes `$OO\call-log.csv`, `$OO\YYYYMMDD_Owner-Outreach_T2-CallSheet_v01.xlsx`.

**Interfaces:**
- Consumes: `mail-log.csv` columns `parcel_id, mailed_date, touch_num, pack`; `log_outreach_response.suppressed_parcels()`; `log_outreach_response.OUTCOMES` keys; ratification JSON `ladder`.
- Produces: `load_mail(path) -> dict[pid, {"stage": int, "t1": date|None}]`; `load_meta(folder) -> dict[pid, dict]` (newest queue row per parcel); `eligible(mail, responded:set, called:set, today:date, gap:int) -> list[pid]`; `rank(pids, meta, cap:int) -> list[pid]`; `CALL_OUTCOMES: list[str]`.

- [ ] **Step 1: Confirm ratification keys**

Run: `python -c "import json;print(json.load(open('outreach-ratification.json'))['ladder'])"`
Record the exact keys for the t2 gap and call-slice bounds (spec: t2=30d, slice 5–8). Use those key names in Step 3's `ladder_params()`; if they differ from `cadence_days.t2` / `call_slice_per_week`, edit the two lookups accordingly.

- [ ] **Step 2: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for build_t2_callsheet.py. Run: python test_t2_callsheet.py"""
import datetime as dt, tempfile
from pathlib import Path
import build_t2_callsheet as c

FAIL, RUN = [], []
def check(n, got, want):
    RUN.append(n)
    if got != want: FAIL.append(f"{n}: expected {want!r}, got {got!r}")

T = dt.date(2026, 9, 23)
def mail(stage, days):
    return {"stage": stage, "t1": T - dt.timedelta(days=days)}

M = {"due": mail(1, 30), "early": mail(1, 29), "t3done": mail(3, 200),
     "resp": mail(1, 40), "called": mail(1, 40)}
check("eligibility", sorted(c.eligible(M, {"resp"}, {"called"}, T, 30)), ["due"])

meta = {"a": {"Score": 90, "Motivation": 3}, "b": {"Score": 95, "Motivation": 1},
        "c": {"Score": 90, "Motivation": 8}, "d": {"Score": None, "Motivation": None}}
check("rank score then motivation", c.rank(["a","b","c","d"], meta, 3), ["b","c","a"])
check("cap", len(c.rank(["a","b","c","d"], meta, 8)), 4)
check("outcomes include logger + call-only", {"no-answer","left-vm","stop"} <= set(c.CALL_OUTCOMES), True)

with tempfile.TemporaryDirectory() as d:
    p = Path(d)/"mail-log.csv"
    p.write_text("parcel_id,mailed_date,touch_num,pack\nX,2026-08-24,1,a\nX,2026-11-22,3,b\nY,2026-09-02,1,c\n", encoding="utf-8")
    got = c.load_mail(p)
    check("load stage", (got["X"]["stage"], got["Y"]["stage"]), (3, 1))
    check("load t1", got["X"]["t1"], dt.date(2026, 8, 24))

if FAIL: print("\n".join(FAIL)); raise SystemExit(1)
print(f"ALL CALLSHEET TESTS PASS ({len(RUN)})")
```

- [ ] **Step 3: Run — expect failure**

Run: `python test_t2_callsheet.py` → `ModuleNotFoundError`

- [ ] **Step 4: Implement**

```python
#!/usr/bin/env python
"""Build the weekly T2 call sheet (ratified ladder OR-2026-001: T2 = call).

Eligible: highest mailed stage is T1, T1 mailed >= t2 gap days ago, no logged
response (outreach-responses.csv), not on a prior call sheet (call-log.csv).
Ranked by Score, then Motivation; capped at the ratified call-slice maximum.
Calls are made by Gabriel. Outcomes other than no-answer/left-vm are logged
with log_outreach_response.py -- the one suppression source of truth.

    python build_t2_callsheet.py [--date YYYY-MM-DD] [--dry-run]
"""
import argparse, csv, datetime as dt, glob, json, os, sys
from pathlib import Path
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from log_outreach_response import OUTCOMES, suppressed_parcels

FOLDER = Path(__file__).resolve().parent
MAILLOG = FOLDER / "mail-log.csv"
CALLLOG = FOLDER / "call-log.csv"
RATIFICATION = FOLDER / "outreach-ratification.json"
CALL_OUTCOMES = sorted(OUTCOMES) + ["no-answer", "left-vm"]
COLS = ["Parcel ID", "Owner", "Mail Name", "Owner Mailing (Tier-0)", "Site Address",
        "Metro", "Score", "Motivation"]

def ladder_params(path=RATIFICATION):
    lad = json.loads(Path(path).read_text(encoding="utf-8"))["ladder"]
    gap = int(lad["cadence_days"]["t2"])
    cap = int(lad["call_slice_per_week"]["max"])
    return gap, cap

def load_mail(path=MAILLOG):
    out = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            e = out.setdefault(r["parcel_id"], {"stage": 0, "t1": None})
            stage = int(r["touch_num"])
            e["stage"] = max(e["stage"], stage)
            if stage == 1:
                d = dt.date.fromisoformat(r["mailed_date"])
                e["t1"] = min(e["t1"], d) if e["t1"] else d
    return out

def load_called(path=CALLLOG):
    if not Path(path).exists():
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {r["parcel_id"] for r in csv.DictReader(f)}

def load_meta(folder=FOLDER):
    meta = {}
    for q in sorted(glob.glob(str(Path(folder) / "*_Owner-Outreach-Queue_Phase1_v*.xlsx")),
                    key=os.path.getmtime):  # oldest first; newer rows overwrite
        ws = openpyxl.load_workbook(q, read_only=True)["Queue"]
        rows = ws.iter_rows(values_only=True)
        hdr = list(next(rows))
        for row in rows:
            d = dict(zip(hdr, row))
            if d.get("Parcel ID"):
                meta[str(d["Parcel ID"])] = d
    return meta

def eligible(mail, responded, called, today, gap):
    return [p for p, e in mail.items()
            if e["stage"] == 1 and e["t1"] and (today - e["t1"]).days >= gap
            and p not in responded and p not in called]

def rank(pids, meta, cap):
    def key(p):
        m = meta.get(p, {})
        return (-(m.get("Score") or 0), -(m.get("Motivation") or 0), p)
    return sorted(pids, key=key)[:cap]

def write_sheet(pids, meta, mail, out):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "T2 Calls"
    ws.append(COLS + ["T1 Mailed", "Phone", "Outcome", "Note"])
    for p in pids:
        m = meta.get(p, {})
        ws.append([p if c == "Parcel ID" else m.get(c) for c in COLS]
                  + [mail[p]["t1"].isoformat(), "", "", ""])
    dv = DataValidation(type="list", formula1='"' + ",".join(CALL_OUTCOMES) + '"')
    ws.add_data_validation(dv)
    col = openpyxl.utils.get_column_letter(len(COLS) + 3)
    dv.add(f"{col}2:{col}{max(2, len(pids) + 1)}")
    wb.save(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    gap, cap = ladder_params()
    mail = load_mail()
    picks = rank(eligible(mail, suppressed_parcels(), load_called(), today, gap),
                 load_meta(), cap)
    if not picks:
        print("[T2] no parcels due for a call this week.")
        return 0
    out = FOLDER / f"{today:%Y%m%d}_Owner-Outreach_T2-CallSheet_v01.xlsx"
    if a.dry_run:
        print(f"[T2 DRY-RUN] {len(picks)} due: {', '.join(picks)}")
        return 0
    write_sheet(picks, load_meta(), mail, out)
    new = not CALLLOG.exists()
    with open(CALLLOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["parcel_id", "sheet_date"])
        for p in picks: w.writerow([p, today.isoformat()])
    print(f"[T2] {len(picks)} calls -> {out.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests**

Run: `python test_t2_callsheet.py` → `ALL CALLSHEET TESTS PASS (6)`

- [ ] **Step 6: Real dry run**

Run: `python build_t2_callsheet.py --dry-run --date 2026-09-23`
Expected: `[T2 DRY-RUN] 8 due: ...` — all from the 2026-08-24 cohort (the only one ≥30 days old). Then run without `--dry-run` to produce the first real sheet and hand it to Gabriel.

---

### Task 6: Conversion report

**Files:** Create `$OO\outreach_conversion_report.py`, `$OO\test_conversion_report.py`.

**Interfaces:**
- Consumes: `build_t2_callsheet.load_meta`; mail-log; `outreach-responses.csv` (`parcel_id, logged_date, outcome, note, notion_synced`).
- Produces: `rows(mail_rows: list[dict], responses: dict[pid,str], meta: dict) -> list[dict]` with keys `pid, touch, metro, tier, motiv_band, cohort, outcome`; `cut(rows, key) -> list[tuple[group, mailed, resp, warm, conv]]`; `render(rows) -> str` markdown. `MIN_RESPONSES = 10`, `MIN_CELL = 20`.

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for outreach_conversion_report.py. Run: python test_conversion_report.py"""
import outreach_conversion_report as r

FAIL, RUN = [], []
def check(n, got, want):
    RUN.append(n)
    if got != want: FAIL.append(f"{n}: expected {want!r}, got {got!r}")

check("tier A", r.tier(92), "A"); check("tier B", r.tier(85), "B")
check("tier C", r.tier(70), "C"); check("tier D", r.tier(None), "D")
check("motiv bands", [r.motiv_band(x) for x in (0, 4, 7, None)], ["0-3", "4-6", "7-10", "n/a"])

mail = [{"parcel_id": f"P{i}", "mailed_date": "2026-08-24", "touch_num": "1"} for i in range(4)]
resp = {"P0": "responded", "P1": "converted", "P2": "stop"}
meta = {f"P{i}": {"Metro": "Columbus", "Score": 90, "Motivation": 5} for i in range(4)}
rs = r.rows(mail, resp, meta)
check("cut overall", r.cut(rs, "all"), [("all", 4, 3, 2, 1)])
md = r.render(rs)
check("small-sample banner", "INSUFFICIENT SAMPLE (n=3)" in md, True)
check("small cell suppressed", "n<20" in md, True)

if FAIL: print("\n".join(FAIL)); raise SystemExit(1)
print(f"ALL CONVERSION TESTS PASS ({len(RUN)})")
```

- [ ] **Step 2: Run — expect failure** (`ModuleNotFoundError`)

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python
"""Owner-outreach conversion report: mailed x responded, by cut.

Read-only. Never changes scoring weights -- findings go to Gabriel.
    python outreach_conversion_report.py [--out-md PATH] [--csv PATH]
"""
import argparse, csv, sys
from collections import defaultdict
from pathlib import Path
from build_t2_callsheet import load_meta

FOLDER = Path(__file__).resolve().parent
MAILLOG = FOLDER / "mail-log.csv"
RESPONSES = FOLDER / "outreach-responses.csv"
MIN_RESPONSES, MIN_CELL = 10, 20
WARM = {"responded", "converted"}

def tier(score):
    if score is None: return "D"
    return "A" if score >= 90 else "B" if score >= 85 else "C" if score >= 70 else "D"

def motiv_band(m):
    if m is None: return "n/a"
    return "0-3" if m <= 3 else "4-6" if m <= 6 else "7-10"

def read_csv(p):
    if not Path(p).exists(): return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def rows(mail_rows, responses, meta):
    first = {}
    for r in mail_rows:  # one row per parcel: its first mailing
        first.setdefault(r["parcel_id"], r)
    out = []
    for pid, r in first.items():
        m = meta.get(pid, {})
        out.append({"pid": pid, "all": "all", "touch": f"T{r['touch_num']}",
                    "metro": m.get("Metro") or "?", "tier": tier(m.get("Score")),
                    "motiv_band": motiv_band(m.get("Motivation")),
                    "cohort": r["mailed_date"], "outcome": responses.get(pid)})
    return out

def cut(rs, key):
    g = defaultdict(lambda: [0, 0, 0, 0])
    for r in rs:
        c = g[r[key]]; c[0] += 1
        if r["outcome"]:
            c[1] += 1
            c[2] += r["outcome"] in WARM
            c[3] += r["outcome"] == "converted"
    return [(k, *v) for k, v in sorted(g.items())]

def render(rs):
    n = sum(1 for r in rs if r["outcome"])
    lines = ["## Owner-outreach conversion", ""]
    if n < MIN_RESPONSES:
        lines += [f"**INSUFFICIENT SAMPLE (n={n})** — rates are directional only.", ""]
    for key, label in [("all", "Overall"), ("metro", "Metro"), ("motiv_band", "Motivation"),
                       ("tier", "Score tier"), ("touch", "First touch"), ("cohort", "Cohort")]:
        lines += [f"### {label}", "| Group | Mailed | Resp | Warm | Conv | Resp % |",
                  "|---|---|---|---|---|---|"]
        for grp, mailed, resp, warm, conv in cut(rs, key):
            rate = f"{resp / mailed:.1%}" if mailed >= MIN_CELL else "n<20"
            lines.append(f"| {grp} | {mailed} | {resp} | {warm} | {conv} | {rate} |")
        lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-md", default=str(FOLDER / "_oo_conversion_block.md"))
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()
    resp = {}
    for r in read_csv(RESPONSES):  # latest outcome per parcel wins
        resp[r["parcel_id"]] = r["outcome"]
    rs = rows(read_csv(MAILLOG), resp, load_meta())
    Path(a.out_md).write_text(render(rs), encoding="utf-8")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0]) if rs else ["pid"])
            w.writeheader(); w.writerows(rs)
    print(f"[CONVERSION] {len(rs)} parcels mailed, "
          f"{sum(1 for r in rs if r['outcome'])} responses -> {Path(a.out_md).name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests** → `ALL CONVERSION TESTS PASS (8)`

- [ ] **Step 5: Real run**

Run: `python outreach_conversion_report.py --csv outreach-conversion-202609.csv`
Expected: `[CONVERSION] ~200 parcels mailed, N responses` (N = responses logged in Task 4 Step 4). Read `_oo_conversion_block.md` and sanity-check totals against `mail-log.csv`.

---

### Task 7: Wire into the weekly run

**Files:** Modify `$OO\owner_outreach_weekly.py` — scan path, immediately after the `print(f"Ladder gate (T{a.touch}): ...")` statement (L671).

- [ ] **Step 1: Insert**

```python
    # 2026-09-22: T2 call sheet every run; conversion report on the first
    # run of each month. Both are advisory -- a failure WARNs and never
    # blocks the letter pack, which is already built at this point.
    for script, when in (("build_t2_callsheet.py", True),
                         ("outreach_conversion_report.py", today_d.day <= 7)):
        if not when:
            continue
        rc = subprocess.run([sys.executable, str(FOLDER / script)]).returncode
        if rc != 0:
            print(f"[WARN] {script} exited {rc}; pack unaffected.")
```
Check that `today_d` is defined in scope at that point (`grep -n "today_d =" owner_outreach_weekly.py`); if it is named differently, use that name.

- [ ] **Step 2: Verify**

Run: `python owner_outreach_weekly.py --self-check && python test_owner_outreach_ladder.py && python test_record_release.py && python test_t2_callsheet.py && python test_conversion_report.py`
Expected: self-check exit 0; all four suites PASS.

---

### Task 8: Document in owner-outreach SKILL.md

**Files:** Modify `C:\Users\Owner\ora-skills\owner-outreach\SKILL.md`

- [ ] **Step 1: Single-writer gate**

```bash
cd /c/Users/Owner/ora-skills && git log --oneline -1 && git status --short owner-outreach/
```
Expected: `owner-outreach/` clean. If dirty with changes not yours, STOP.

- [ ] **Step 2: Edit**
- Replace the "Still pending" T2–T4 rendering note (SKILL.md ~L139-143) with: "T3/T4 render via `--touch 3|4` (live since 2026-08-16). T2 is a call: `build_t2_callsheet.py` runs every weekly scan and writes `YYYYMMDD_Owner-Outreach_T2-CallSheet_v01.xlsx` (ratified call slice, ranked by Score then Motivation); outcomes are logged with `log_outreach_response.py`."
- Under the `--released` docs add: "`--released DATE --manifest PATH` records a pack mailed but never logged. Rebuild its manifest first: `python reconstruct_pack_manifest.py PACK.docx QUEUE.xlsx --out _oo_manifest_YYYYMMDD.json` (all-or-nothing; halts on any unmatched address). Duplicate parcel+touch pairs are skipped."
- Add a "Conversion report" subsection: first weekly run of each month writes `_oo_conversion_block.md`; include it in the run-summary email; INSUFFICIENT SAMPLE banner below 10 responses; read-only, no scoring changes without Gabriel.
- Bump version to v1.4 with a changelog line dated 2026-09-22.

- [ ] **Step 3: Commit via `isolated-commit` skill**

```bash
git add owner-outreach/SKILL.md
git commit -m "owner-outreach v1.4: T2 call sheet, conversion report, manifest backfill

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Passed-deal tracker Step 3b (re-marketing detection)

**Files:** Modify `C:\Users\Owner\.claude\scheduled-tasks\ora-passed-deal-tracker\SKILL.md` (insert after Step 3/3a, before Step 4; add an output section in `## Output` ~L323).

- [ ] **Step 1: Preflight**

```bash
python ~/.claude/maintenance/preflight-shared-checkout.py --repo ~/.claude --paths scheduled-tasks/ora-passed-deal-tracker/SKILL.md --since $(git -C ~/.claude rev-parse HEAD)
```
Expected exit 0. Nonzero → STOP and report.

- [ ] **Step 2: Insert Step 3b text**

```markdown
3b. **RE-MARKETED PASSES (added 2026-09-22).** For every watch-list row (after the
   duplicate-address merge), search the Outlook inbox with `outlook_email_search`
   over the trailing 35 days, once for the street address (street number + street
   name) and once for the property name if the row has one. Never open links.
   - Ignore messages sent from any @oxfordra.net address.
   - A hit requires the street number AND street name in subject or body; a
     name-only or partial match is **UNCONFIRMED** (listed, never escalated).
   - Extract an asking price only if stated as a dollar figure tied to the
     property; otherwise price = unknown.
   - Classify: **INSIDE-WALK** if ask ≤ `ORA Max Defensible Price` (confirmed
     hits only) · **PRICE-CUT x%** if ask < the row's last known ask · else
     **RE-MARKETED**.
   - Any INSIDE-WALK forces the email path even when zero trades were found.
   - Read-only: no Notion writes, no outreach drafts. A row with a blank
     `ORA Max Defensible Price` can be PRICE-CUT or RE-MARKETED, never INSIDE-WALK.
```

- [ ] **Step 3: Add output section** in `## Output`, email body order after LOI POST-MORTEMS:

```markdown
- **RE-MARKETED PASSES** — table: Property · Flag · Ask · Last ask · Max Defensible · Broker/sender · Email date. Omit the section when there are no hits; UNCONFIRMED hits are listed in a sub-table.
```

- [ ] **Step 4: Dry run (no send)**

Execute Step 3b manually in this session against the live inbox for the current watch list; write the table to the scratchpad only. Verify at least one known passed address returns the expected result (hit or no hit). If the inbox has no broker email for any passed deal, verify with one address you know appeared in a broker blast from `deal-flow-triage` history.

- [ ] **Step 5: Commit via `isolated-commit`**

```bash
git -C ~/.claude add scheduled-tasks/ora-passed-deal-tracker/SKILL.md docs/superpowers/specs/2026-09-22-deal-sourcing-funnel-design.md docs/superpowers/plans/2026-09-22-deal-sourcing-funnel.md
git -C ~/.claude commit -m "passed-deal-tracker: Step 3b re-marketed passes from broker email; funnel spec+plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Diagnose the missed 2026-09-21 outreach run (report only)

- [ ] **Step 1:** `grep -n "owner-outreach" ~/.claude/maintenance/_state/fleet-roster.md` — confirm id, fleet, enabled flag.
- [ ] **Step 2:** Load `mcp__scheduled-tasks__list_task_runs` and read runs for `ora-owner-outreach-queue-refresh` since 2026-09-14. Also check `$OO` for a dated run log from 09-21.
- [ ] **Step 3:** Classify cause (environment: Desktop closed / Keep-awake off · tooling · logic) per the scheduler doctrine. Report to Gabriel; any re-registration or catch-up run goes through `register-scheduled-task` with his approval. Do not re-run the pack unattended — generate the catch-up pack only on request.

---

## Self-review

- Spec coverage: A0 → Tasks 2–4, 10; A1 → 5, 7; A2 → 6, 7; A-docs → 8; B → 9; C → no build (decision). Spec "motivation signal" cut is implemented as the numeric Motivation band because the queue carries a 0–10 score, not signal text (verified 2026-09-22).
- Names consistent: `record_release`, `reconstruct`, `load_mail`, `load_meta`, `eligible`, `rank`, `CALL_OUTCOMES`, `rows`, `cut`, `render`.
- Open dependency: Task 4 Step 4 waits on Gabriel's response details; Task 5 Step 1 confirms ratification key names before use.
