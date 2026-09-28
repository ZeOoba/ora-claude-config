---
name: acquisition-underwriting-eval-harness
description: "Golden-set regression harness for the acquisition-underwriting skill — replays a frozen set of 6 past SCREEN-mode deals against CURRENT SKILL.md doctrine, diffs the resulting Combined score against a re-baselined golden snapshot, flags deltas beyond tolerance, and writes a dated re-runnable snapshot. Use after any material doctrine edit to acquisition-underwriting (a scorecard-weight amendment, a new QC-gate rule, a ruling/amendment) to check whether the change actually moved scores and by how much — not a live deal-evaluation tool, never invoke this for an actual acquisition screen. PILOT — piloted on one skill only; registered 2026-08-14 as a daily-polling scheduled task."
---

# Acquisition-Underwriting Eval Harness (pilot, v1.0 — 2026-08-14)

Companion to `acquisition-underwriting/SKILL.md`, not a replacement for it. This skill answers
one question the firm previously had no way to answer: **after a doctrine edit, did the skill's
scoring actually change, and by how much?** It does not evaluate real deals and must never be
invoked for one — its inputs are deliberately frozen historical facts, not live research.

Built 2026-08-14 per Gabriel's ratified scope (`memory/reference_skill_eval_harness_gap_2026-08-14.md`):
pilot on `acquisition-underwriting` only, no extension to other skills this pass. The original
scope was harness-only; Gabriel ratified scheduled-task registration later the same day, and the
task went live 2026-08-14 (CC/MCP fleet, `ora-acquisition-underwriting-eval-harness`, daily
poll) — see Limitations.

## When to invoke

- After editing `acquisition-underwriting/SKILL.md` (a scorecard weight, a Stage 1 floor, a
  QC-gate rule, an RCT table revision) — run this BEFORE and AFTER the edit and compare the two
  dated snapshots in `runs/` to see what moved.
- Periodically, as a sanity check that the skill still reproduces its own documented scoring
  mechanics against known cases (catches an accidental doctrine regression even absent an
  intentional edit).

## What it is NOT

- Not a live deal-evaluation tool. Frozen replay subagents are explicitly forbidden from
  fetching live data (Notion, market-monitor, web, comp pulls) — see the replay prompt below.
- Not a judgment on whether a doctrine edit was "right." It only reports whether the score
  changed and by how much; whether that change is an improvement is Gabriel's call.
- Not a headless/standalone script. It IS wired into a scheduled task (CC/MCP fleet,
  `ora-acquisition-underwriting-eval-harness`, daily poll — live 2026-08-14), but that task still
  drives the Agent-tool orchestration below from inside an authenticated Claude Code session; a
  bare `claude -p` subprocess cannot run it. See LIMITATIONS.

## Data-quality findings (read before trusting any delta)

**1. RCT v03 date-boundary finding (the important one — discovered running the first baseline
2026-08-14).** All 6 golden deals were screened 2026-06-09/06-20, **before** the 2026-07-14
RCT v03 replacement-cost recalibration — a deliberate, ratified, large tightening of the Basis
floor (old RCT v02 + 30%/25% ramp → RCT v03 + 65%/60% ramp; SKILL.md's own text: the old ramp
"would have set the Columbus floor at a price at which every candidate in the buy-box
clears"). The first replay attempt diffed today's doctrine directly against each deal's
pre-recalibration archived Notion score and got large "deltas" on every scored deal (e.g. Port
Sheldon's Basis went from clearing comfortably pre-v03 to breaching post-v03, at an unchanged
price/SF) — all of them the already-ratified v03 effect, not a regression. **Comparing across a
known doctrine-version boundary defeats the purpose of a regression harness.** Fixed by
re-baselining: **`golden` in every file is now the 2026-08-14 replay's own output under current
doctrine** (`baselined_date`, `baselined_against_skill_sha`), not the archived pre-v03 Notion
score. The original archived score is preserved under the sibling key `archived_pre_v03_reference`
for historical context only and is never read by `diff_verdict.py`. **Practical consequence:**
this harness cannot yet detect a *regression that happened between 2026-06-09 and today* (it
never had a doctrine-consistent baseline to compare that period against) — it can only detect
drift from **today's baseline forward**. That is the correct and only honest scope for a first
run; a golden set assembled from deals screened after 2026-07-14 would not have this limitation,
and none exist yet in the Deal Sourcing Log (confirmed via a dedicated research pass, 2026-08-14).

**2. Archived pre-v03 tier/arithmetic inconsistencies (historical context only, no longer
diffed against).** 3 of the 6 deals' `archived_pre_v03_reference` blocks show a Notion-recorded
verdict tier that doesn't match what VERDICT BANDS + the STAGE 2.5 DD-Critical-ceiling rule would
predict from the archived Combined score, and 2 of those also show archived Quality + Economics
not summing to the archived Combined. Cause not determinable from the archive. Irrelevant to
today's pass/fail (see finding 1 — that block is never diffed), but kept because it's a real,
otherwise-undocumented gap in the Deal Sourcing Log's own internal consistency.

**3. Frozen-input-packet incompleteness.** Even against the re-baselined golden values, most
baseline replays left 2-3 of the 7 scorecard categories `null` (Product & Physical, Seller &
Motivation, Tenancy & Lease most often) because the input packet — reconstructed from Notion's
*structured* fields — doesn't capture the physical/site/comp detail the *original* live-tooled
screens evidently had. 2196 Port Sheldon and Liberty Office Park resolved cleanly (zero nulls) from
the start; E Fulton St Portfolio was enriched 2026-08-14 (Gabriel's request — see "E Fulton
enrichment" below) to 1 null (Tenancy & Lease only). All three are `confidence: HIGH`/`MEDIUM` and
`scored: true`. The remaining 3 deals are `confidence: LOW`, run and report, but are
`scored: false` / `informational_only: true` — excluded from the strict pass/fail tally until their
input packets can be enriched the same way. **Because of both findings above, the harness's primary
and only pass/fail-gating signal is the Combined-score delta — never the tier label** (see
`golden_set/SCHEMA.md` and each deal's `diff_policy`).

**4. E Fulton enrichment (2026-08-14, Gabriel's request) — closed the Economics-blind-spot.**
Before this, both scored deals (Port Sheldon, Liberty) breach both the Basis and Yield floors,
pinning Economics at 0.0 — a future edit to the Basis scale, Yield slope, or RCT top-of-scale would
move neither one unless it flipped a floor from breach to clear, the exact class of edit that
motivated this build. Enriching E Fulton's input packet with real, sourced physical specs (Robert
Weiler Co. OM, Crexi listing, Franklin County Auditor CAMA, pre-6/9 Morning Brief pages — full
citations in the golden file's `known_gaps`) resolved 6 of 7 scorecard categories and produced a
Basis of 25.0/25 (full points, CapEx-supported) — E Fulton is now `confidence: MEDIUM`, `scored:
true`, and the harness's only scored deal with nonzero Economics. Tenancy & Lease stays null by
design, not by gap: occupancy was a confirmed unknown at the 6/9 screen date ("rent roll
unreconciled"), and backfilling it with later data would violate the frozen-snapshot discipline —
this is why the deal is MEDIUM rather than HIGH. The enrichment also surfaced a genuine finding the
original screen could not have caught: per-building SF (previously totally unknown) shows the North
Main Building breaches the 50,000 SF/building gate under every plausible reading — all 3 repeatability
runs independently flagged this as GATE-FLAGGED.

**5. One replay agent can emit two conflicting completions (2026-09-12 scheduled-poll).** The
Hamilton r3 subagent sent two completion notifications under the same task-id with different final
json blocks (Combined 15.0, then 11.0). A runner that records the first notification per slot and
moves on would have silently kept 15.0 — nothing in the first result looked wrong. Per Step 2's
never-guess rule both were excluded and Hamilton aggregated at n=2. Guarded by Step 1.5 (wait for
all completions; differing blocks from one task-id = failed replay). A first draft of that step
instead rejected identical answers across DIFFERENT agents; that version was withdrawn the same day
because it misses this failure mode entirely and would have discarded 4 genuine replays from the
same run (see Step 1.5 item 4).

## Golden set

`golden_set/*.json` — 6 frozen deals, schema documented in `golden_set/SCHEMA.md`. `golden` =
the 2026-08-15 re-baseline (see the "Fourth pass" Limitations entry); confidence reflects how many
of a replay's 7 scorecard categories are null (finding 3), except where a null is structurally
irreducible rather than a research gap (finding 4 — E Fulton's Tenancy & Lease):

| Deal | Confidence | Scored (gates PASS/FLAG)? | Golden Combined | Observed range |
|---|---|---|---|---|
| 2196 Port Sheldon St, Jenison MI | HIGH (0 nulls) | Yes | 26.81 (mean of 8, leaked run excluded) | 3.5 pts (n=8 clean) |
| Liberty Office Park, West Chester OH | HIGH (0 nulls) | Yes | 28.11 (mean of 9) | 2.0 pts (n=9) |
| E Fulton St Portfolio, Columbus OH | MEDIUM (1 null, irreducible — see finding 4) | Yes | 56.79 (mean of 7) | 4.0 pts (n=7) |
| 11850 Hamilton Ave, Cincinnati OH | LOW (Basis null by v4.21 rule; 1-3 Quality nulls) | No — informational only | 17.0 (mean of 3 under v4.21, rebaselined 2026-09-12; all pre-v4.21 runs excluded) | **7.0 pts (n=3) — exceeds tolerance** |
| 1333 Research Rd, Gahanna OH | LOW (3 nulls) | No — informational only | 11.75 (mean of 4) | **6.0 pts (n=4) — exceeds tolerance** |
| 470 McCormick Blvd, Columbus OH | LOW (2-3 nulls, Quality mostly null) | No — informational only | 16.5 (mean of 3, lower-bound run excluded — see caveat below) | **6.0 pts (n=3 clean) — exceeds tolerance** |

`golden.combined` for every deal is now a repeatability-checked mean, not a single unreplicated
run — the 2026-08-15 rebaseline (Gabriel-directed forced run, see the "Fourth pass" Limitations
entry) extended this to all 6 deals, including the 3 that previously had no repeatability data at
all. Port Sheldon and McCormick each exclude one non-comparable sample; Hamilton excludes all four
pre-v4.21 runs (rebaselined under v4.21 on 2026-09-12) — see the leakage findings above and each
file's `known_gaps` for why. 470 McCormick's original 20.0-pt
4-run range was NOT ordinary replay noise: it was an artifact of pooling its 2026-08-14 single run
(an explicitly documented lower bound, most categories null) into the mean alongside 3 comparable
full replays — that run is now excluded from the golden per the 2026-09-12 rebaseline (same
treatment as Port Sheldon's and Hamilton's excluded runs), leaving a 3-run 6.0-pt range and golden
Combined of 16.5 — see that file's `known_gaps` for the full rationale. 1333 Research Rd's 6.0-pt
range appears to be genuine judgment variance, consistent with its null-heavy input packet. Both
LOW-confidence deals are informational_only regardless, so neither dispersion finding gates
anything, but both are recorded rather than smoothed over.

**Every run gates on the MEAN of 3 replays per deal, never a single draw** (Steps 1–3 below).
This is the direct consequence of the n=6 finding: at the time, Port Sheldon's single-draw range
was 7.0 pts against a 5.0-pt tolerance, so one replay could false-FLAG on noise alone. (That
figure was itself partly a leakage artifact, fixed 2026-08-15 — see "Limitations"; the clean
range is now 3.5 pts. The mean-of-3 gate stays regardless, since even 3.5 pts of genuine
judgment variance benefits from averaging.) See "Limitations".

**`runs/` is git-ignored** (2026-08-14) — snapshots are machine-local run state, not source of
truth, and a daily fire writing into a tracked directory inside a single-writer checkout
manufactured a daily false "uncommitted work that isn't yours" signal. Snapshots still get
written and are still the durable local record; they are just not versioned. **The tracked
evidence trail is each golden file's `repeatability` block**, which carries the individual
per-replay samples the goldens were computed from.

The **first genuine replay-to-golden diff this harness ever ran** was the 2026-08-14
scheduled-poll (3 scored, 3 PASS, 0 FLAG, doctrine unchanged; snapshot
`2026-08-14T215119Z_scheduled-poll.json`, local-only). Every earlier snapshot fed each golden
block back in as its own observed value and so passed by construction — see "Limitations".

**If you still have that snapshot locally, read it with two caveats — it predates the changes it
motivated.** (1) Its `combined_observed` values are SINGLE replays, not 3-replay means; the
mean-of-3 gate was adopted *because* of what that run measured, so it is the last single-draw
run, not an example of current procedure. Under the new gate the same replay data gives Port
Sheldon −1.25 rather than the −4.33 recorded there. (2) Its per-category deltas resolve rather
than showing `None` only because the runner hand-normalized the display-name keys in a scratch
driver; that normalization now lives in `aggregate_replays.py`, so later snapshots get it
automatically. Its Port Sheldon and Liberty rows also diff against the pre-rebaseline goldens
(29.33 / 28.67).

## Procedure

**Step 0 — provenance.** Capture the current `acquisition-underwriting/SKILL.md` git commit hash
(the hash of the most recent commit that touched this file, not a git blob hash) so the
snapshot can be attributed to an exact doctrine revision:
```
git -C <ora-skills repo root> log -1 --format=%H -- acquisition-underwriting/SKILL.md
```

**Step 1 — for each `golden_set/*.json` file**, spawn **3 independent subagents** (Agent tool,
`model: "fable"` — this replays scored/financial logic and must never run below the Fable
floor), each with the SAME prompt built from the template below. Three, not one: a single replay
is not a stable measurement (n=6 finding — Port Sheldon's single-draw range was 7.0 pts at the
time against a 5.0-pt tolerance, since partly attributable to leakage now fixed — see
Limitations), and the gate compares the mean of the 3 in Step 3.

Send all 3 in one message so they run concurrently, and do NOT vary the prompt between them —
identical prompts are what make them samples of one distribution rather than three different
questions. For a 6-deal set that is 18 agents per run.

Prompt template (used verbatim for every replay of every deal, substituting only the frozen
facts):

```
You are running a FROZEN REPLAY of the acquisition-underwriting skill's SCREEN mode, for a
regression-test harness — NOT a real deal evaluation.

Read the skill's scoring mechanics from: <path to acquisition-underwriting/SKILL.md>
(STAGE -1 through STAGE 2.2 govern SCREEN mode; VERDICT BANDS defines tier labels;
UNDERWRITING CONVENTIONS + the Replacement Cost Table supply RCT v03 figures.)

Apply SCREEN mode's Stage -1 through Stage 2.2 mechanics to ONLY the frozen facts below.
Do NOT fetch live data of any kind — no Notion query, no market-monitor query, no web search,
no comp pull, no county/GIS lookup, and no read of ANY file under `memory/` or any other
session-context/memory store (this specifically includes `memory/deal-decision-ledger.md` and
any Notion-mirrored deal-decision or event log — these can record this exact deal's actual
historical outcome, which is an answer key, not a live-data source, but is exactly as
contaminating). Stage -1 item 5's "ledger precedent check" is NOT PERFORMABLE in frozen-replay
mode for this reason — skip it and say so in `notes`; do not read the ledger to answer it. Where
the documented procedure calls for a live check you cannot perform in frozen-replay mode (e.g.
Stage 2.1 bear-mode via market-monitor, Stage 2.3 concentration check via live portfolio
composition), apply the skill's own DOCUMENTED FALLBACK for that case (e.g. "If BOTH sources are
unavailable: record bear-mode state as UNKNOWN, proceed with bear-mode OFF for scoring... cap the
screen at T2 WATCH") and state which fallback you used in `notes`. Do not invent a value a live
check would have supplied.

If the SKILL.md text you just read discusses THIS EXACT property (by street address) anywhere
outside the frozen facts below — e.g. as a worked example, a validation case for a rule, or a
price-watch/re-engage citation — you MUST disregard that discussion entirely for scoring
purposes. Score using ONLY the frozen facts below; do not award points, assumptions, or
characterizations (e.g. seller motivation, occupancy status, condition) that come from SKILL.md's
own narrative text about this address rather than from the frozen facts. If you noticed such a
citation and excluded it, say so explicitly in `notes`; if you are not sure whether something you
used came from the frozen facts or from SKILL.md's own text about this address, treat it as
inadmissible and drop it.

FROZEN FACTS:
<paste the golden file's "inputs" block verbatim>

Compute Quality, Economics, Combined (=Quality+Economics), Expected Score (=Combined x P(exec)),
P(exec) %, the verdict tier per VERDICT BANDS, the Floor Result, and a category_breakdown
(Basis/Yield/Product & Physical/Market & Location/Seller & Motivation/Tenancy & Lease/Value-Add
Optionality) if you can derive each component from the frozen facts (use null for any component
you cannot support from the given facts alone — never guess).

End your response with EXACTLY ONE fenced json block, no other json blocks anywhere in your
response, matching this shape:
```json
{"combined": <float>, "quality": <float|null>, "economics": <float|null>,
 "expected_score": <float|null>, "p_exec_pct": <float|null>, "verdict_tier": "<string>",
 "floor_result": "<string>", "category_breakdown": {<string>: <float>, ...} | null,
 "notes": "<one paragraph: fallbacks used, assumptions made, anything the frozen facts left
 genuinely unresolvable>"}
```
```

**Step 1.5 — completion attribution + multi-completion check (2026-09-12 — see Data-quality
finding 5).** With up to 18 agents dispatched concurrently, completions arrive out of order, and a
single agent can emit MORE THAN ONE completion notification (same task-id, later notification).
1. **Attribute by task-id, never by arrival order.** Match every completion to its own spawn
   (task-id / agentId + description) from Step 1; never assign a completion to "the next open slot."
2. **Do not finalize any slot until every agent in the run has completed.** Record each completion
   as provisional, keyed by task-id. A slot is final only once all dispatched agents have reported
   and no further notification for that task-id arrived after its first one.
3. **Two or more completions from ONE task-id:** extract the fenced json block from each. If the
   parsed blocks are identical (a re-notification of the same answer), accept it once. If they
   DIFFER in any field, that replay FAILED — treat it under Step 2's failure rule; never pick the
   first, the last, or the more plausible one.
4. **Identical answers from DIFFERENT task-ids are NOT a failure.** SCREEN scores are coarse integer
   judgments and independent replays legitimately agree: the 2026-09-12 run produced
   byte-identical `combined` + `category_breakdown` pairs for Port Sheldon r2/r3 (29.0) and E Fulton
   r2/r3 (55.0) from separate agents. Rejecting agreement would have cut both scored deals to n=1.
   Only a task-id mismatch (a completion whose description names a different deal/slot than its
   spawn) indicates mis-attribution.
State in the Step 5 report every task-id that emitted more than one completion, and whether the
blocks matched.

**Steps 2–4 in one command (2026-09-13 — use this; never hand-copy scores into a driver script).**
Once every agent in Step 1 has completed, run from the harness root:
```
python lib/parse_replays.py --subagents-dir <~/.claude/projects/<project>/<session-id>/subagents> \
    --agent-ids <the 18 task-ids from Step 1> [--failed-agent-ids <ids flagged in Step 1.5>] \
    --record --skill-sha <Step 0 hash> --run-label <label>
```
It reads each agent's on-disk transcript (`agent-<id>.jsonl`), applies the Step 2 one-block rule
below, fails any agent whose transcript shows more than one completion with differing blocks, and
attributes each replay to its golden deal by the FROZEN FACTS block in its own prompt (never by
description or arrival order), then aggregates, diffs and snapshots.
- **Always pass `--agent-ids`.** Without it every replay transcript in the session is pooled — a
  session that also ran rebaseline replays silently inflates `n` (09-12 session: Hamilton n=5).
- **The transcript cannot see every Step 1.5 failure.** A differing earlier completion notification
  can leave no trace on disk (09-12 Hamilton r3: the 15.0 block exists only in the notification).
  Keep watching notifications per Step 1.5 and pass any such task-id via `--failed-agent-ids`.
- **Completion is inferred from transcript structure, not `stop_reason`** — ~5% of real completed
  replays carry no `end_turn` stamp (09-12 E Fulton r2).
- **Exit codes:** **0** = every deal has ≥1 parsed replay, none failed. **4** = every deal has ≥1
  parsed replay but ≥1 replay failed (degraded `n`, listed per deal; snapshot still recorded; the
  scheduled task's deal-level Step 4 rule may still advance). **3** = a deal has no result or could
  not be aggregated, a requested agent-id has no transcript, or a requested agent could not be
  attributed — nothing recorded, do not advance state.

Verified 2026-09-13 against that day's 18 real transcripts: identical `combined_observed`,
`category_deltas` and status to the hand-copied run (exit 0); and against the 09-12 session, where
it recovers the no-`end_turn` E Fulton replay (n=3, 54.67, matching the recorded run).

**Step 2 — parse.** Extract the single fenced `json` block from each subagent's final response.
If a response contains zero or more than one fenced json block, that replay FAILED — report it
as an error, do not guess which block was intended. A failed replay is **never** silently
dropped from its deal's sample set: report it, and if fewer than 3 replays parsed for a deal,
say so explicitly in Step 5 (`aggregate.n` records what actually went into the mean).

**Step 2.5 — aggregate.** For each deal, pass its list of parsed replays to
`lib.aggregate_replays.aggregate_replays(replays)`. This returns ONE observed dict whose
`combined` is the **mean** across replays, plus an `aggregate` block carrying `n`,
`combined_samples`, `combined_stdev`, `combined_sem`, `combined_range`, and
`category_null_counts`. It also normalizes the replay prompt's display-name category keys
("Product & Physical") to the golden files' snake_case ("product_physical") — without that,
`diff_verdict`'s per-category deltas silently return `None` on every real replay.

**Step 3 — diff.** For each deal's aggregated observed result, call
`lib.diff_verdict.diff_verdict(golden_json, observed_json)`. The gate compares the 3-replay mean
against `golden.combined` — never a single draw.

If a deal's own `aggregate.combined_range` exceeds its `diff_policy.tolerance_combined_pts`,
report that alongside the verdict: the replays disagreed with each other by more than the gate's
own width, so that deal's PASS/FLAG is weakly supported this run regardless of which way it
landed. Port Sheldon had a range of 7.0 vs the 5.0 tolerance at n=6 (partly a leakage artifact,
fixed 2026-08-15 — clean range is now 3.5, see Limitations). As of the fix, a >5.0-pt range on
Port Sheldon in a single 3-replay run is NOT expected to be routine — treat it as worth
investigating, not as the known-noisy row it used to be.

**Step 4 — snapshot.** Collect all `diff_verdict()` results into a list and call
`lib.record_run.record_run(results, run_dir="runs/", skill_sha=<Step 0 hash>, run_label=<your
choice, e.g. "baseline" or "post-<doctrine-change>">)`.

**Step 5 — report.** Print a summary table (deal_id, status, scored, combined_golden,
combined_observed, combined_delta, plus `n` and `combined_range` from the aggregate block) and
call out any `status == "FLAG"` among `scored: true` rows prominently — that is the harness's
actual regression signal. `informational_only` rows are shown for completeness but are not
evidence of a regression by themselves (see Data-quality finding above). Also report any deal
where fewer than 3 replays parsed, or where `combined_range` exceeded tolerance.

**Before treating any FLAG as doctrine drift, check Step 0's SHA against the previous run's.**
If the doctrine SHA is UNCHANGED, a FLAG cannot be a regression by construction — it is noise, a
golden-set edit, or an input-packet change. Check `git log` on the golden file before escalating.

## Self-test (regression-detection proof)

Never run this against a real `golden_set/*.json` file — always against a copy in `fixtures/`.

`fixtures/regression_test_mutation.json` (mutated copy of the Port Sheldon golden file,
`asking_price` cut ~50%, $1,995,000 → $995,000) and `fixtures/self_test_result.py` are kept as
permanent, re-runnable self-test assets — not scratch output. Re-run anytime with
`python fixtures/self_test_result.py` (no live calls; it re-derives the diff from a
already-captured mutated-replay result and asserts `status == "FLAG"`). Nothing under
`fixtures/` is ever written to `runs/` — the two stay clearly separated.

To reproduce the full self-test from scratch (e.g. after changing `diff_verdict.py`):
1. Copy a `golden_set/*.json` file to `fixtures/regression_test_mutation.json` and mutate ONE
   frozen input meaningfully.
2. Run Steps 1–2 above against the mutated fixture only (skip Steps 4/5 — a fixture run must
   never land in `runs/`).
3. Diff the mutated replay's result against the REAL (unmutated) golden file's `golden` block
   — not against the mutated fixture's own `golden` block, which is a straight copy and would
   trivially self-match.
4. Confirm `combined_delta` from `diff_verdict()` exceeds the 5.0-pt tolerance and `status ==
   "FLAG"`. This proves the load → replay → diff → flag pipeline works end to end.

**Caught in this build:** running this self-test surfaced a real bug — a 2026-08-14 golden-set
rebaseline renamed the tier key from `archived_verdict_tier` to `verdict_tier`, but
`diff_verdict.py` (and its own unit-test fixture) still read the old name, so `archived_tier`
silently came back `None` for every real file. The unit suite didn't catch it because its
synthetic fixture had drifted to match the same stale key; the self-test did, because it ran
against a REAL golden file. Fixed, and a dedicated regression test added
(`test_reads_golden_verdict_tier_key_not_archived_verdict_tier`) so a future key rename can't
silently reintroduce the same desync. This is itself evidence the self-test mechanism works,
not just its designed-in mutation case.

This test perturbs an INPUT, not doctrine — by design (frozen inputs never change between real
re-runs of the actual golden set). The mechanism that isolates skill-logic drift from
external-data drift is the freezing discipline itself (the same `golden_set/*.json` fed every
time), not anything the diff engine infers — the diff engine only needs to catch an output
delta given an IDENTICAL input, which is exactly what a real doctrine edit produces.

## Limitations / follow-ups (not built this pass)

Found by two mandatory adversarial REFUTE passes (2026-08-14, both Fable-pinned) — the first
against the original 6-deal build, the second against the E Fulton enrichment + scheduled-task
registration — listed here rather than silently fixed where fixing would have meant fabricating
data this harness doesn't actually have:

**Fourth pass (2026-08-15, forced repeatability run, Gabriel-directed) — 2 leakage findings, both
fixed same-day, plus a full rebaseline:**
1. **Second answer-key surface: the deal-decision-ledger.** The replay prompt's "do not fetch
   live data" list enumerated Notion/market-monitor/web/comp-pull/county-GIS but never named
   local memory files. One 2026-08-15 replay of 11850 Hamilton Ave read
   `memory/deal-decision-ledger.md` (visible as an extra tool_use versus every other replay of the
   same deal) and cited the ledger row recording this exact property's real 2026-07-09 outcome
   (PARKED, "out-of-box standing retail") — an answer key, structurally identical to the
   SKILL.md-citation leakage below, just a different file. It returned the sample's low outlier
   (18.4 vs. 23.4/21.0 for the two clean replays). **Fixed:** the prompt template (see "Prompt
   template" above) now explicitly bars reading `memory/` or any session-context/memory store,
   names the ledger file directly, and instructs replays to treat Stage -1 item 5 (ledger
   precedent check) as NOT PERFORMABLE rather than reading the ledger to answer it. Hamilton's
   golden was rebaselined excluding the contaminated sample — see golden_set file — the same
   treatment already established for Port Sheldon's SKILL.md-citation leak (finding 2 below), for
   the same reason: a future clean-prompt replay population no longer contains this failure mode,
   so the golden should reflect the corrected process, not the contaminated one.
2. **SKILL.md-citation leakage, re-confirmed and now guarded against.** Previously documented
   (see "SKILL.md-citation leakage" under Data-quality findings) as a standing, unfixed 1-in-6
   risk on Port Sheldon specifically, because SKILL.md's own text cites that address by name as a
   worked validation example. Rather than continuing to just document the risk, the prompt
   template now instructs every replay to disregard any SKILL.md narrative text about the exact
   frozen address and score from the frozen facts only, flagging in `notes` if it noticed and
   excluded such a citation. The 3 replays run 2026-08-15 under the fixed prompt showed no
   leakage (Seller & Motivation scored 0.0 in all three, vs. the 5.0 the original leaked run
   awarded) — consistent with, though not proof against, the fix working; the failure mode was
   probabilistic (~1-in-6) even before the fix, so a 3-sample clean run is expected either way.
3. **Full rebaseline, 2026-08-15.** All 6 goldens updated to the mean of every same-doctrine,
   non-contaminated sample now on file (Port Sheldon n=8 of 9, excluding the one leaked run;
   Hamilton n=3 of 4, excluding the one ledger-read run; Liberty n=9; E Fulton n=7 for
   Combined/Quality/Economics, n=4 for category-level detail — the original 3 baseline runs never
   recorded per-category breakdowns; 1333 Research Rd and 470 McCormick n=4 each — each pools its
   original 2026-08-14 single baseline run with 3 new 2026-08-15 replays, its first-ever
   repeatability check). See each golden_set file's `known_gaps` for the deal-specific numbers
   and `baselined_method`. Both LOW-confidence deals' NEW 2026-08-15 samples came in noisier than
   the scored set on their own (1333 Research Rd's 3 new replays ranged 9.0-15.0; 470 McCormick's
   ranged 14.0-20.0), and both files' full n=4 range (6.0 and 20.0 pts respectively) exceeds the
   5.0-pt harness-wide tolerance — consistent with their null-heavy input packets; this is
   evidence for, not against, keeping them out of the strict pass/fail gate. 470 McCormick's
   20.0-pt range is additionally inflated by its original run being a documented lower-bound
   construction rather than a comparable full replay — see that file's `known_gaps`.

**Second REFUTE pass (E Fulton enrichment + scheduled task) — 2 HIGH-severity findings, both
fixed same-day, not deferred:**
1. **The scheduled task's target checkout didn't have the enrichment yet.** The task's prompt
   points at `C:\Users\Owner\ora-skills` (the primary checkout), but the enrichment commit
   (`c7527d9`) had only been pushed to `origin/main` — the primary checkout was still on the
   pre-enrichment golden set (and its own unpushed local commits from an unrelated concurrent
   session). Had this shipped as-is, the first scheduled run would have replayed the STALE golden
   set, and an Economics-side regression — the exact blind spot this enrichment exists to close —
   would have passed silently. Fixed via a plain `git merge origin/main` on the primary checkout
   (clean, no conflicts, left the other session's unpushed commits and dirty `README.md` fully
   intact — merge is additive, not destructive, so this was safe under the single-writer
   discipline without waiting on that session to finish).
2. **An all-error harness run would have silently marked itself "checked" forever.** The original
   scheduled-task design advanced `last_checked_sha` unconditionally and only posted to Notion on
   a scored FLAG — so if every replay subagent errored (model unavailable, parse failure), the run
   would produce zero FLAGs, post nothing, advance its state anyway, and the doctrine edit would
   never actually get evaluated by anyone. Fixed: state now advances only on a fully clean run
   (every deal parsed, regardless of PASS/FLAG); Step 3 now also posts to Notion on ANY parse
   failure, not just a FLAG, specifically so a malfunctioning run is never indistinguishable from
   a healthy no-op. Also switched the poll from a commit-SHA check to a `git hash-object` content
   hash, since a commit-SHA check would never see an uncommitted doctrine edit — and this
   environment routinely carries uncommitted WIP for weeks (see `project_primary_checkout_main_move_blocked_2026-08-12.md`).

**Lower-severity findings from the same pass, fixed inline in the golden file:** the enrichment's
"physical specs are time-invariant" framing was overstated (narrowed to a freeze-to-source-date
window, not "any point in time" — condition-dependent sub-scores and the OM's "active" rail-spur
claim were carved out as NOT covered by the invariance argument); E Fulton's repeatability stdev
used population variance (0.85) where the other two HIGH-confidence deals used sample variance —
corrected to 1.04 for consistency; `SCHEMA.md` updated to document the irreducible-null vs.
recoverable-gap distinction that got E Fulton to MEDIUM; a P(exec) mean-of-3-discrete-bands value
flagged as informational-only, not a real band placement.

**First REFUTE pass (original 6-deal build) — replay nondeterminism is real and now measured, not assumed.** A 3-run repeatability check
  on the 2 HIGH-confidence deals (identical frozen inputs, identical doctrine, 3 independent
  subagent replays each) found a 4.5-point Combined-score range on Port Sheldon and a 1.0-point
  range on Liberty — see each deal's `repeatability` block in `golden_set/*.json`. The original
  3.0-pt tolerance would have produced false FLAGs from LLM run-to-run noise alone. Tolerance
  widened to 5.0 pts harness-wide as a direct, cited response (not an arbitrary round number —
  see `diff_policy.tolerance_rationale` in each file). **That n=3 estimate has since been
  superseded — see the n=6 finding below.**

**Third pass (2026-08-14 scheduled-poll run) — the n=3 dispersion estimate was too low, and two
latent defects surfaced on the first real diff:**
1. **n=3 understated the noise; the fix is averaging, not a wider tolerance.** The scheduled-poll
   run added 3 more replays per HIGH deal. At n=6, Port Sheldon's range is **7.0 pts** (samples
   25.0/27.0/27.5/28.5/28.5/32.0, stdev 2.31) — it EXCEEDS the 5.0-pt tolerance, so two honest
   same-doctrine replays could false-FLAG each other. Liberty (2.0 pts, n=6) and E Fulton (2.0
   pts, n=4) are tight; the noise is concentrated in one deal. Response (Gabriel-ratified): (a)
   Port Sheldon's golden rebaselined to the n=6 mean **28.08** (was 29.33), and (b) **every run
   now gates on the mean of 3 replays** via `lib/aggregate_replays.py`, which cuts that mean's
   standard error to ~1.33. The gate diffs it against a golden that is itself an estimate (mean
   of 6, SEM ~0.94), so the honest dispersion of the delta is √(2.31²/3 + 2.31²/6) ≈ **1.63** —
   a ±2σ band of ~±3.3 pts inside the 5.0-pt tolerance, i.e. a false-FLAG probability of ~0.2%
   (z = 3.06). Quoting the 3-replay SEM alone (±2.7) understates that by ~10× in probability
   terms; both clear the tolerance, but ±3.3 is the number to reason with. Widening the
   tolerance to ~7.0 was explicitly rejected — it masks noise instead of averaging it, and
   blunts detection of real drift.
2. **Every snapshot before `2026-08-14T215119Z_scheduled-poll.json` passed by construction.**
   `run_baseline_2026-08-14.py` fed each golden block back in as its own `observed` value, so
   the diff was golden-vs-itself and could only ever return delta 0.0. The "2 PASS" / "3 PASS"
   on those baselines was therefore not evidence the harness works. The scheduled-poll run is
   the first true replay-to-golden diff.
3. **Per-category deltas were silently dead** (masked by defect 2). The replay prompt asks for
   display-name keys ("Product & Physical"); golden files store snake_case
   ("product_physical"); `diff_verdict` matches keys exactly — so on a real replay every
   per-category delta returned `None`. Golden-vs-golden trivially matched, which is why it went
   unnoticed. Fixed by normalization in `aggregate_replays.py`, with a test asserting every
   golden-set category key is a reachable normalization target.
4. **Concurrency hazard, observed live.** A concurrent session rebaselined E Fulton's golden
   mid-run (LOW/47.0 → MEDIUM/57.17), so replays launched against the old input packet diffed
   against a new golden and produced a −12.17 "FLAG" that was pure artifact. Re-check
   `git log`/mtimes on `golden_set/` immediately before Step 4 and discard any deal whose golden
   moved mid-run — do not record or alert on it. `ora-skills` is a single-writer checkout;
   prefer an isolated worktree for any harness edit.
- **SKILL.md-citation leakage on named-example deals — MITIGATED 2026-08-15 (was: unfixed
  standing risk).** Port Sheldon is cited by address in SKILL.md's own text as the worked
  validation example for the price-watch trigger. The original baseline run (measured at n=6)
  found one replay drew on that citation (awarding Seller & Motivation points for an
  owner-user-vacating characterization not present in the frozen `inputs`) while all five other
  replays declined to — a leakage rate of 1-in-6, and that single leaked run was also the high
  outlier (32.0) inflating this deal's dispersion. This was originally documented as "only
  partially mitigable" because fixing it looked like it required either stripping the citation
  from SKILL.md (out of scope, read-only) or excluding self-citing deals from the golden set. The
  2026-08-15 fourth pass (see Limitations, "Fourth pass" finding 2) found a third option: the
  replay prompt itself can instruct the subagent to disregard SKILL.md's own narrative discussion
  of the exact frozen address. The leaked sample was excluded from Port Sheldon's golden
  (rebaselined to n=8 of 9, see golden_set file) on the same reasoning already used for the
  2026-08-15 deal-decision-ledger leak: a fixed-prompt replay population no longer produces this
  draw, so the golden should reflect the corrected process. No golden deal in this set other than
  Port Sheldon has ever shown this failure mode (checked: none of the others are cited by address
  in SKILL.md) — the fix is general (any future self-citing deal is covered), but only Port
  Sheldon has evidence either way.
- **RESOLVED 2026-08-14 — the strict-scoring gate could not previously see an Economics-side
  doctrine edit.** Both HIGH deals (Port Sheldon, Liberty) breach both the Basis and Yield floors,
  pinning Economics at 0.0 in every run; a future edit to the Basis linear scale, the Yield slope,
  or the RCT top-of-scale would have moved neither scored deal unless it happened to flip a floor
  from breach to clear — the exact class of edit (a replacement-cost/floor recalibration) that
  motivated this whole build. Closed by enriching E Fulton's input packet with real, sourced
  physical facts (see "E Fulton enrichment" above) rather than sourcing a new 7th golden deal —
  E Fulton is now `scored: true` with Basis 25.0/25 (full points), the harness's only scored deal
  with nonzero Economics. **Residual gap:** this closes the blind spot for edits that move the
  Basis scale/RCT floor near E Fulton's 90%+ discount (still comfortably clear of the ≥76%
  top-of-scale threshold, so a moderate recalibration might not move it either) — a broader edit
  stress-test would benefit from a 4th scored deal nearer its own floor boundary; not pursued this
  pass since none of the remaining LOW-confidence candidates have recoverable enough facts
  (confirmed 2026-08-14).
- **No unattended re-run path — investigated 2026-08-14, headless CLI confirmed non-viable in
  this environment.** Re-running today requires a Claude Code session to drive the Agent-tool
  orchestration in Steps 1–2. Tried a headless `claude -p` subprocess wrapper (the natural
  candidate) and it fails immediately: a nested CLI invocation from within a running session's
  Bash tool has no persisted auth (`claude auth status` reports `loggedIn: false`, no
  `ANTHROPIC_API_KEY`, and the parent session's OAuth token does not carry over — confirmed by
  direct test, not assumption). This isn't a scripting bug to fix; it's how this environment's
  credential model works. **The actual unattended path ORA already has is `register-scheduled-task`**
  — the CC/MCP and LAMS/Cowork fleets run scheduled SKILL.md procedures inside the authenticated
  Desktop app, not as bare subprocess calls, so this harness's SKILL.md (Steps 1–2's Agent-tool
  orchestration) is already shaped correctly to become a scheduled task once a cadence/trigger is
  ratified — see the next bullet. No separate headless-script build is needed or was pursued
  further.
- **RESOLVED 2026-08-14 — scheduled-task registration.** Gabriel ratified: event-driven trigger
  (approximated via daily polling of `acquisition-underwriting/SKILL.md`'s git SHA — the fleet has
  no true git-hook trigger, so a cheap daily SHA check that only runs the full 6-deal replay on an
  actual change is the closest fit) and Notion Operations Hub posting, but ONLY when a scored deal
  FLAGs (silent no-op on PASS, to avoid noise). Registered as `ora-acquisition-underwriting-eval-harness`
  on the CC/MCP fleet, `14 12 * * *` (~12:23 PM ET daily with jitter), verified via
  `list_scheduled_tasks`. The task is a thin wrapper — it reads and follows this SKILL.md's Steps
  0–5 rather than duplicating them, per the registration skill's own single-source-of-truth
  guidance. State (`last_checked_sha`) lives in the task's own folder
  (`~/.claude/scheduled-tasks/ora-acquisition-underwriting-eval-harness/state.json`), not in the
  `ora-skills` repo, specifically to avoid a daily write to the shared single-writer checkout.
- **Not extended to other skills.** Gabriel's explicit call, 2026-08-14: stay pilot-only for now —
  prove out `acquisition-underwriting`'s harness across a few real doctrine-edit cycles (the
  scheduled task above will surface these) before replicating the pattern elsewhere.
- **3 of 6 golden deals are LOW-confidence / informational-only** (input-packet incompleteness —
  2-3 of 7 scorecard categories null in the replay) — a 4th scored golden deal (beyond the 3 now
  scored: Port Sheldon, Liberty, E Fulton) would further strengthen the strict-scoring set; none of
  the remaining 3 candidates (Hamilton, 1333 Research Rd, 470 McCormick) currently have complete
  enough facts to enrich the same way E Fulton was (confirmed via the same research pass that
  enriched E Fulton, 2026-08-14 — Hamilton and 470 McCormick both lack any NOI/price basis at all,
  not just physical specs; 1333 Research Rd's underlying arithmetic inconsistency, per finding 2
  above, is a deeper archive problem physical enrichment wouldn't fix).
- **The re-baselined golden values are themselves unverified LLM judgment**, not ground truth —
  the numeric floor/YoC/discount components were independently recomputed and verified correct
  during the REFUTE pass, but the judgment-scored categories (Product & Physical, Market &
  Location, Value-Add) are enshrined as the harness's reference point without independent
  human sign-off. Acceptable for a pilot establishing the pattern; worth flagging explicitly
  rather than implying more certainty than exists.
