# Double-fire guard — shared entry guard for ORA scheduled tasks

Built 2026-08-09. Two helpers in this directory, meant to be used together:

| Helper | Layer | What it answers |
|---|---|---|
| `block-sentinel.py` | 1 (primary) | "Has this block already run today?" — a per-block, per-ET-date claim file |
| `outlook-sent-probe.ps1` | 2 (backstop) | "Is today's email already in Sent Items?" — asks the mail store itself |

Neither is sufficient alone. Layer 1 is authoritative but its state lives on OneDrive
and can be lost or rolled back; Layer 2 survives that but only covers blocks that
send email, and only after the message is actually in the store.

---

## Why this exists

**2026-08-09 (Sunday).** The machine was offline overnight. `ora-health-guard` reported
waking **219 minutes late** and the whole fleet fired in a catch-up burst.

`ora-am-brief` fired twice. The first fire published Notion page
`3b76ecd8-9e59-8160-bb0f-c6b5c925a278` and sent *"ORA Daily Brief - Sunday, August 9
2026"* to ggoldberg cc egoldberg at **09:06:58 ET**. A second fire landed at **09:11 ET**
(registry `lastRunAt 2026-08-09T13:11:04Z`). It only avoided re-sending the email and
overwriting the page because the session happened to read the artifact first and stood
down **by hand**. Nothing in the spec made it do that.

Root cause: no entry guard. The only dedup was the `daily-brief` skill's *Patch 3*
pre-create check, which dedups the **Notion page only** (the COM send is unconditional)
and, on "exactly 1 match", issues `notion-update-page replace_content` — it **overwrites**,
because it assumes any same-day match is its own retry artifact rather than a completed
prior run's published output.

**The burst is not the bug.** Both fleets fire only while the Desktop app is open, so a
catch-up burst after downtime is documented, intended behavior. Do **not** "fix" a
double-fire by retiming a cron or suppressing catch-up. The guard belongs at each task's
own entry.

---

## What else was firing twice

Audit of the shared COM send log (`_shared/send-log.txt`, 439 records / 33 days),
grouping same-day sends by normalized subject stem:

**Confirmed unintended duplicate sends by fleet tasks**

| Task | Dates | Note |
|---|---|---|
| `ora-deal-aging-sla` | 2026-07-20, **2026-08-09** | Two separate incidents. On 08-09 it sent at 08:59:11 and again at 09:20:09. **This one actually duplicated** — unlike am-brief, nothing stood it down. |
| `ora-monday-sync` | 2026-07-13 | Sent **three times** (12:36:40, 12:42:47, 12:43:32). |
| `ora-open-sessions-board` | 2026-07-09 | 14:07 and 17:17, with different counts — two full runs. |
| `ora-health-guard` (connector pre-flight) | 2026-07-24 | Known/documented; the two sends had different subject encodings. |
| `ora-am-brief` Block B | **2026-08-09** | Near-miss — two fires, one send, manual stand-down. |

**Deliberate, not defects** — excluded: anything tagged `[CORRECTION]` or
`(corrected resend)` (lease-expiration 07-13, daily brief 07-27, health guard 07-29),
and `ora-owner-outreach` 07-21 where the first send was an `[ALERT]` halt notice.

**Out of scope — different mechanism, not a scheduled-task double-fire**

- `[ORA Command Center] Mirror deploy FAILED` repeats **per deploy attempt** (16x on
  2026-08-05). That is a retry loop alerting each failure, not a task firing twice.
  It may deserve alert coalescing, but not this guard.
- `[ORA Command Center] CRITICAL: …` lease/insurance alerts repeat **per tenant per
  engine run** (26x on 2026-07-12). That engine re-alerts the same tenant every run —
  a separate dedup question, tracked separately.

**Conclusion: factor into a shared helper, don't reimplement per task.** Four blocks in
`ora-am-brief` plus at least four other tasks have demonstrated the same exposure, and
the fiddly parts — ET-vs-UTC date keying, the TTL in both directions, atomic write under
OneDrive, subject normalization — are exactly what gets re-derived slightly wrong each
time it is hand-rolled.

---

## Layer 1 — `block-sentinel.py`

```
python block-sentinel.py claim    --task <task> --block <blockId> --run-id <id> [--ttl-min 30] [--force]
python block-sentinel.py complete --task <task> --block <blockId> --run-id <id> [--notion-page-id ID] [--email-sent-at ISO] [--adopt]
python block-sentinel.py fail     --task <task> --block <blockId> --run-id <id> [--error "..."] [--adopt]
python block-sentinel.py status   --task <task> --block <blockId>          # read-only, creates nothing
```

Write each invocation on ONE line. `^` is cmd.exe continuation and hard-fails in
both shells this host offers — in Bash it splits into two commands, in PowerShell it
is a parse error. Neither produces a decision the caller can act on.

State file defaults to
`<Claude_Workspace>\_state\<task>-block-completion.json`, overridable with `--state`.
Shape:

```json
{ "2026-08-09": { "blockB": { "status": "COMPLETE", "runId": "...",
                              "claimedAt": "...", "notionPageId": "...",
                              "emailSentAt": "..." } } }
```

For `ora-am-brief` that path matters specifically: `Claude_Workspace\_state\` is the one
location its NON-MUTATION GUARANTEE already permits it to write, so the guard adds no new
write surface. Tasks with a different envelope should pass `--state` to a path inside
theirs.

### Exit codes — the whole contract

| Exit | Decision | Caller does |
|---|---|---|
| 0 | `PROCEED` | Claimed. Run the block. |
| 10 | `SKIP_ALREADY_COMPLETE` | Skip the block. Log `BLOCK_<X>_ALREADY_COMPLETE_TODAY`. Record a **NORMAL skip**. |
| 11 | `STAND_DOWN_IN_PROGRESS` | Another fire is live. Skip. Log `BLOCK_<X>_IN_PROGRESS_ELSEWHERE`. Record a **NORMAL skip**. |
| 12 | `REFUSED_*` | `complete`/`fail` only. This run does not own the block; **nothing was written**. See ownership below. |
| any other | tooling failure | **Fail open — run the block**, and surface the code verbatim. Exit 2 is a malformed command (usually a missing `--task`); 9009/127 is a missing interpreter. Never read these as "already done". |

JSON is written to stdout in every case, including `logToken`, `etDate`, the prior
`record`, `persisted`, and `stateFileError`.

### Ownership — who may close a claim

`complete` and `fail` are **owner-only**, and this is load-bearing in both directions:

- `complete` on a block that was never claimed would fabricate a COMPLETE record, and
  every later fire that ET date would then be suppressed — silently, reported as a
  NORMAL skip. That is the design's only real false-suppression path, so it is refused
  (exit 12, nothing written).
- `fail` from a run that STOOD DOWN would release the *live* run's claim and let a third
  fire start while the first is still generating. Also refused.

So: **claim exit 0 → you must finish with `complete` or `fail`. Claim exit 10 or 11 → you
own nothing, call NEITHER.** A stood-down fire is not a failed fire.

`--adopt` is the one sanctioned no-prior-claim path: the Sent-Items probe reports
ALREADY_SENT after the state file was lost, and the run records COMPLETE so Layer 1
re-converges with reality. It must be asked for explicitly, never inferred.

### Two things that are load-bearing

**The TTL cuts both ways.** A `COMPLETE`-only sentinel does not stop two *overlapping*
fires — fire #2 arrives while fire #1 is still generating, when no COMPLETE record exists
yet. An `IN_PROGRESS` sentinel with **no** expiry permanently wedges the task after any
crash. Both halves are tested separately, including the boundary.

**Skips are NORMAL, not misses.** `ora-health-guard` and `automation-health-monitor` read
each task's run summary. A guard-suppressed duplicate must be reported in the same class
as a weekend skip, citing the earlier fire's artifact. Class it as a failure and you train
a false alarm into the fleet — and invite someone to "fix" it by removing the guard.

### Fail-open, by design

A corrupt/unreadable state file, an untakeable lock, or any internal error yields
`PROCEED` with the problem in `stateFileError`. Surface that string in the run summary:
because the guard fails open, a degraded Layer 1 looks exactly like a normal run, and
that string is the only early warning.

### `--force`

Overrides a `COMPLETE` record (`BLOCK_<X>_FORCED_OVERRIDE`). Deliberate manual runs are
real and must stay possible — one happened on 2026-08-09 at 10:51 ET, a human-directed
all-blocks verification run that legitimately re-ran every block on a Sunday. **`--force`
is for a human asking in-session; a scheduled fire must never pass it.**

A forced re-run must bypass **both** layers or it cannot re-send: Layer 2 would still find
the earlier message in Sent Items, so the run would re-publish Notion and silently skip the
email. Pass `-Force` to `outlook-sent-probe.ps1` too (returns `FORCED`/exit 0 without
touching Outlook). Same rule — human-directed only.

---

## Layer 2 — `outlook-sent-probe.ps1`

Run immediately before any COM send:

```
powershell -ExecutionPolicy Bypass -File outlook-sent-probe.ps1 -SubjectFile "<temp .txt>"
```

| Exit | Meaning | Caller does |
|---|---|---|
| 0 | `NOT_SENT` | Proceed with the send. |
| 10 | `ALREADY_SENT` | **Skip the send.** Log it, record a NORMAL skip, and still call `block-sentinel.py complete` so Layer 1 re-converges with reality. |
| 1 | `PROBE_ERROR` | **Fail open — send anyway**, and record the gap. Layer 1 already said PROCEED; suppressing a real report because a probe broke is worse than a duplicate. |
| 0 | `FORCED` | `-Force` was passed; the check was bypassed. Human-directed re-runs only. |

**False positives are rejected, not just tolerated.** A false positive here suppresses a
real report, which is worse than the duplicate the probe exists to stop, so replies
(`Re:`), forwards (`Fw:`/`Fwd:`) and manual corrections (`[CORRECTION]`,
`(corrected resend)`) are rejected outright before matching — each of those carries the
stem verbatim, and corrections are a recurring class in the send log (2026-07-13,
07-27, 07-29). Benign automation tags (`[ORA]`, `[ALERT]`, `[ORA Command Center]`) are
*stripped* instead, because the same producer varies them run to run; after stripping,
the stem must sit at **position 0**, so another producer that merely contains the stem
later in its subject does not match.

### Choosing the probe subject — this is where it goes wrong

- **Use a dated stem, not the full subject.** Many tasks put live counts in the tail
  (`— 6 for triage, 1 RED`), and those legitimately differ between two runs of the same
  day. Probing the full string fails to match the earlier send and waves the duplicate
  through. `ora-deal-aging-sla` is the worst case: its spec lets the run compose the
  headline, so its two 08-09 subjects differed in both the leading tag and the trailing
  text. Matching is **substring**, not prefix, precisely so a dated stem still matches a
  subject that grew a `[ORA]`/`[ALERT]` prefix.
- **But keep the date in the stem**, or every day matches every day.
- **Make it specific enough to be unambiguous.** On 2026-08-09 Sent Items held both
  `ORA Daily Brief - Sunday, August 9 2026` (this task) and `[ORA Command Center] Daily
  Brief — 2026-08-09` (a different producer) seven minutes apart. A stem loose enough to
  match the wrong one would suppress a real report.
- **Always `-SubjectFile`, never a literal `-Subject`** on the command line — non-ASCII
  subject characters are mangled in transit (`send-via-outlook.ps1` documents the same
  hazard).

Matching is normalization-tolerant by default: dash family folded to `-`, smart quotes
folded, non-ASCII dropped, whitespace collapsed, casefolded. That default is evidence-driven
— `ora-am-brief`'s spec subject uses an em-dash but the message actually in the store uses
a plain hyphen, so an exact match would have missed the real sent item.

---

## Rolling this out to another task

1. Pick block ids. A single-purpose task can use one, e.g. `--block main`.
2. Add the `claim` call as the **first** action, before any generation work, and act on
   the exit code per the table above.
3. If the task emails, add the pre-send probe with a **dated stem**.
4. Add `complete` (or `fail`) after the durable outputs land.
5. Make the run summary report guard skips as NORMAL, citing the earlier artifact.

Wired so far:

| Task | Fleet | Block ids | TTL | Notes |
|---|---|---|---|---|
| `ora-am-brief` | CC/MCP | `blockA`-`blockD` | 30 | Both layers on B and D |
| `ora-deal-aging-sla` | CC/MCP | `main` | 30 | Both layers |
| `ora-open-sessions-board` | CC/MCP | `main` | **45** | Longer TTL: STEP 5 renders an interactive board and STEP 6 waits on Gabriel, so the claim is closed at the end of STEP 5, before that wait |
| `ora-monday-sync` | **LAMS** | `main` | 30 | Both layers. See the caveat below |

**`ora-monday-sync` lives on the LAMS/Cowork fleet**, whose SKILL.md files sit under
`OneDrive.../Documents/Claude/Scheduled/` and are **NOT in this git repo** — so that
edit has no version history or backup here, only a dated `.bak` beside it. The helpers
are invoked by absolute path under `~/.claude`, so they work from either fleet unchanged;
it is only the *spec* that is unversioned. Any LAMS task wired later has the same gap.

Not yet wired, exposure demonstrated above: `ora-health-guard` (connector pre-flight,
2026-07-24 — its two sends differed only in subject encoding, so verify the probe stem
matches both forms before wiring).

## Tests

```
python  scheduled-tasks/_shared/test-block-sentinel.py
powershell -ExecutionPolicy Bypass -File scheduled-tasks/_shared/outlook-sent-probe.ps1 -SelfTest
```

The PowerShell self-test exercises the subject-matching predicate without touching
Outlook, and carries the real 2026-08-09 subject pairs as regression cases.
`outlook-sent-probe.ps1` is deliberately **ASCII-only**: PowerShell reads a BOM-less
`.ps1` as cp1252, so literal em-dashes in the *source* are mangled before the regex runs.
An earlier revision hit exactly that and the em-dash case silently matched nothing.
