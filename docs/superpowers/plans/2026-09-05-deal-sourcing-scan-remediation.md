# Deal-Sourcing Scan 2026-09-05 — Remediation Plan

**Goal:** close what's fixable from the 2026-09-05 `ora-deal-sourcing-scan` run's Benchmark Honesty and Coverage Gap findings. Four coverage-gap findings (#5, #8, #9, #10 below) are now fixed directly in `SKILL.md` (see Landing note for provenance) — three (#5, #8, #9) close recurring, structural gaps in submarket/procedure coverage; the fourth (#10) closes a dispatch-design gap this run's own tooling created, not a pre-existing doctrine absence. The rest are either one-off verification follow-ups, already-correct behavior, or a cross-skill item owned elsewhere.

**Scope note:** this is not a code plan — `ora-deal-sourcing-scan` is a prompt/doctrine skill (Markdown), not a program. "Implementation" here means SKILL.md text edits, not TDD workstreams.

---

## Finding coverage

| # | Finding | Disposition |
|---|---|---|
| 1 | [PROXY] denominators — Madison/Milwaukee, Grand Rapids/Detroit, Richmond/Baltimore, Des Moines/Minneapolis; Grand Rapids weakest | **Not fixable in this skill.** Owned by `acquisition-underwriting`'s RCT v03 table. See "Cross-skill, not actioned here" below. |
| 2 | Basis = price×1.02 excludes CapEx/lease-up carry | **By design, already documented** (SKILL.md STEP 3A + BENCHMARK HONESTY). No fix — the scan already flags capex-heavy candidates (did so this run on 1809 & 1815 Commerce Rd). No task. |
| 3 | 5 near-line T2 WATCH deals (722 Ketcham St <1%, 1945 Jackson Rd 2.9%, 8301 Cane Run Rd 9.4%, 15665 S Keeler St ~10%, 2201 Advance Ave 10.6%) | **Action item**, not a skill fix — see Action Items §1. |
| 4 | 1809 & 1815 Commerce Rd — unpriced roof-replacement CapEx behind a headline $20.15/SF | **Action item** — see Action Items §2. |
| 5 | Construction-photo analysis (Step 1 v2.4 procedure) skipped this run | **W-A, DONE** (SKILL.md edited this session) — Gabriel ratified restoring it; see W-A below. |
| 6 | Crexi/LoopNet 403 on WebFetch | **No task** — expected, already mitigated (CommercialSearch/CommercialCafe primary, search-snippet fallback). Working as designed. |
| 7 | Montgomery County MD skipped | **No task** — correct per existing monthly-cadence doctrine. |
| 8 | Curtis Bay/Dundalk/Rosedale/Glen Burnie MD — aggregate counts only, no addressable listings | **W-B, DONE** (SKILL.md edited this session). |
| 9 | Whiteland IN / Beech Grove IN under-covered (folded into Noblesville query) | **W-C, DONE** (SKILL.md edited this session). |
| 10 | 7 JS-rendered brokerage sites unreachable via WebFetch (NAI Wisinski, Colliers West MI, C&W\|Thalhimer, NAI Iowa, Hubbell Realty, R&R Realty, Commercial Kentucky) | **W-D, DONE** (SKILL.md edited this session) — root cause was this run's own dispatch design (WebSearch/WebFetch-only agents, no browser tool), not a pre-existing doctrine gap. Fixed by adding a standing browser-tool requirement to the dispatch guardrail. |
| 11 | 10 Hill St, Kansas City KS — possible raise to $2,300,000, conflicting snippets | **Action item** — see Action Items §3. Correctly NOT written to Notion this run. |
| 12 | 1320 E Washington St, Louisville KY — stale LoopNet snippet ($1,295,000) vs. live price ($1,050,000) | **No task** — already correctly handled (read as aggregator lag, no update made). This is the same failure class as the already-documented 3255 N 7th St Trafficway precedent (STEP 4); existing doctrine already covers it. |

---

## W-B, W-C, W-D — DONE this session

All three are additive text edits to `~/.claude/scheduled-tasks/ora-deal-sourcing-scan/SKILL.md`, made directly (Hard Invariant 5 — Claude-system paths are free working surface; no permission needed to edit). Diffs:

- **W-B — Baltimore submarket coverage bullet** (Step 1): added explicit per-submarket query requirements for Curtis Bay, Dundalk, Rosedale, and Glen Burnie MD — mirroring the existing Howard County / KC-Kansas-side pattern, so these stop getting silently folded into a broader "Baltimore" metro query.
- **W-C — Indianapolis submarket coverage bullet** (Step 1): added the same explicit per-submarket query requirement for Whiteland IN / Beech Grove IN, so they stop getting folded into a combined Noblesville-area query.
- **W-D — Subagent dispatch guardrail** (Step 1): added a standing rule that a per-market dispatch given only WebSearch/WebFetch cannot read JS-rendered broker sites, and must either get browser-pane/Claude-in-Chrome access or explicitly flag "text-only pass attempted" rather than reporting a false "no crawlable inventory."

**Landing note (provenance, 2026-09-06):** this plan and the SKILL.md edits it describes were first committed locally on the shared `~/.claude` checkout's `feat/model-canary-probe-step25` branch on 2026-09-05, but that commit was never pushed to origin — the branch was a stale copy whose base (PR #156) had already been separately merged into `main` days earlier via a different route, and it sat unpushed until the branch was deleted 2026-09-06. Both files were then extracted from that local commit and landed on top of current `main` in a fresh isolated worktree (`extract-deal-sourcing-doc`), reviewed independently against current `main`, and committed there.

---

## W-A — Construction-photo-analysis procedure — RATIFIED 2026-09-05: restore, DONE

**Decided (Gabriel, 2026-09-05): restore it.** SKILL.md amended in this session to close the
loophole that let this run skip it — the procedure itself was never removed from SKILL.md,
the 2026-09-05 run simply chose not to execute it "for scope reasons," a discretionary call
the doctrine didn't explicitly forbid. Added a mandatory-compliance clause immediately after
the Step 1 "HOW TO ACTUALLY DETERMINE CONSTRUCTION TYPE" procedure header (the v2.4-added
inline instructions, not the top-of-file v2.4 changelog entry): skipping this step is now a
**reportable coverage gap** (same standing as an unsearched submarket), never a silent scope
trade-off a run makes on its own judgment.

Recap of the tradeoff that drove the decision:

- **Cost:** a browser-pane pass (resize viewport, extract `.property-details-gallery` images, download, classify) per candidate whose construction type isn't stated in listing text. Skipped entirely this run for scope.
- **Measured yield (2026-08-04 baseline, the one time it ran):** ~1 in 5 candidates resolvable from photos (3 of 15) — construction-score impact is small (2 points per resolved candidate, PEMB vs. confirmed masonry/block/tilt-up).
- **The real value is the by-product, not the score points:** every resolved listing that run surfaced something the listing text never disclosed — a taproom/arcade build-out, an in-place credit tenant, a separate marketed parcel, a poor-circulation site plan, a cell tower. SKILL.md's own v2.4 note says this explicitly: "THE BY-PRODUCTS OUTWEIGH THE 3 POINTS."
- **This run's actual impact:** 5 of 25 candidates had a real construction signal anyway, read straight from listing text (concrete, block+steel, hybrid, steel-frame) — the text-only fallback is not zero-yield.

---

## Action items (one-off / recurring manual follow-ups — not skill edits)

**§1 — Soft price-test the 5 near-line T2 WATCH deals, in order:**
1. 722 Ketcham St, Indianapolis IN — fails basis by <1% (~$5,500). Test whether the seller would take ~$989,500.
2. 1945 Jackson Road, Columbus OH — fails by 2.9%; clears at ≤~$1,453,800.
3. 8301 Cane Run Rd, Louisville KY — fails by 9.4%; clears at ≤~$4,095,800.
4. 15665 S Keeler St, Olathe KS — fails by ~10%, mezzanine SF unverified; clears at ≤~$1,955,000 on current assumptions.
5. 2201 Advance Ave, Columbus OH — fails by 10.6%; clears at ≤~$4,475,400. Land-value allocation (income trailer yard) may be the lever.

**§2 — 1809 & 1815 Commerce Rd, Louisville KY:** get a GC/roofer quote for replacing both roofs (54,152 SF combined) before treating the nominal $20.15/SF basis as clean. Re-test basis net of that CapEx once quoted; do not advance to OM on the headline number alone (Notion Next Action already says this).

**§3 — Price verification, no Notion update until confirmed:**
- 10 Hill St, Kansas City KS — confirm $2.1M vs. $2.3M directly (broker call or a fresh browser-pane load of the LoopNet listing).
- 1320 E Washington St, Louisville KY — no action needed; already correctly resolved as aggregator lag.

---

## Cross-skill, not actioned here

**[PROXY] denominator retirement (Madison/Milwaukee, Grand Rapids/Detroit, Richmond/Baltimore, Des Moines/Minneapolis).** This is `acquisition-underwriting`'s RCT v03 table, not `ora-deal-sourcing-scan` — the scan only mirrors it. The fix is sourcing one GC/lender hard-cost quote per proxy market to replace the cross-metro substitute; Grand Rapids is the standing highest-priority target (RSMeans shows it well below the national average while Detroit, its proxy, is a high-cost union market — the proxy is flagged as too generous, meaning Grand Rapids passes may be looking cleaner than they are). Flagging as an end-of-session systematization candidate rather than building it here — it is out of this skill's scope and touches the acquisition-underwriting governor-adjacent RCT table, which itself has an open, unresolved defect (`Replacement Cost Ratio` still computing against a stale RCT v01-era $95/SF denominator per the pipeline tracker's Step 5B note) that should probably be resolved in the same pass.
