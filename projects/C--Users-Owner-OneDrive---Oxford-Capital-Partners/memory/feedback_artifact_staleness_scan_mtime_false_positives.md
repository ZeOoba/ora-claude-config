---
name: artifact-staleness-scan-mtime-false-positives
description: "The artifact staleness scan flags live-read artifacts by file mtime, which is a guaranteed false positive — and it misread a skill-folder count as a task count"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c6332772-1656-4e6d-b9ba-0b6554f9988c
  modified: 2026-07-27T01:10:14.288Z
---

The Artifact Staleness Scan (ora-weekly-hygiene Block D) produced two distinct defect classes on its 2026-07-26 run. Both were confirmed by direct verification; neither artifact was actually stale.

**Defect 1 — mtime is not a freshness signal for live-read artifacts.** Cowork artifacts that fetch their data through `window.cowork.callMcpTool(...)` on open re-query on every view. Their file mtime only moves when the *instrument* is edited, never when the *data* changes. Flagging them by mtime mis-flags them permanently and the flag can never be cleared by any amount of correct behavior. Both artifacts flagged on 2026-07-26 (`motivation-calibration-tracker`, `ora-cowork-setup-audit-dashboard`) were live-read and current.

**Why:** a staleness heuristic that can't be satisfied trains you to dismiss the whole report. `motivation-calibration-tracker` will re-trip every scan forever — its response rate is 0% by design (T1 letters are drafted, never sent, under Hard Invariant 1), so no data movement is even possible until Gabriel authorizes a send.

**How to apply:** before flagging an artifact stale, grep its body for `callMcpTool` / a live-query path. If present, it is an instrument — verify the *underlying data source* moved, or don't flag it. Give such artifacts a visible disposition block stating explicit retire-criteria, so the next scan gets a deterministic answer instead of re-deciding from scratch. Both artifacts now carry one.

**Defect 2 — the scan compared two unrelated counts and reported drift.** It read "live 43-folder listing" from the setup-audit dashboard and concluded drift because "the fleet has grown to 55 registered tasks." The 43 counted **skill folders in the `ora-skills` git repo** (commit b71722b), not scheduled tasks. The two numbers measure different things; there was no drift to report. Verified 2026-07-26: `ora-skills` holds 57 top-level dirs, README already superseded by commit bd0ed3b; live dual-fleet total is ~53 (CC/MCP 30 + LAMS/Cowork 23), not 55.

**How to apply:** when a scan quotes a bare number out of an artifact body, resolve *what the number counts* before declaring drift against a different number. Cite the unit, not just the digits.

Related: [[verify-probe-findings-before-acting]] (a probe finding is a hypothesis, not a verdict), [[artifact-citation-requirement]], [[fleet-status-dual-read]] (a single `list_scheduled_tasks` call returns ONE fleet — the dashboard's live table was mislabeled "LAMS / Cowork" and now self-labels its source).

## The disposition-block convention (adopted 2026-07-26)

Every Cowork artifact declares its freshness type in both its `cowork-artifact-meta` description and a visible disposition block in the body. Three types, and the scan classifies before it flags:

- **LIVE** — every figure re-queried on open. mtime is meaningless; judge by probing the data source. Flagging one on age creates a defect no correct behaviour can clear.
- **FROZEN** — deliberate point-in-time record. Age alone is not a defect; flag only if presented as current, or if content is now wrong/unsafe.
- **HYBRID** — static content wrapped around a live element. Judge each half by its own rule and say which is which.

A disposition block states the type, what was last verified and when, and explicit **retire-criteria** — so the next scan reads a stated answer instead of re-deriving a verdict. All three current artifacts carry one: `motivation-calibration-tracker` (LIVE), `ora-cowork-setup-audit-dashboard` (HYBRID), `loans-external-register` (HYBRID — static loan terms, live SharePoint freshness check only).

**Fixed in the scan, 2026-07-26.** Block D of `ora-weekly-hygiene/SKILL.md` was rebuilt: classification now gates flagging (step 3), a new **Unprobed** status stops an unrunnable connector probe from reporting as "0 Broken" (step 5), the local-folder fallback carries a mandatory scope disclaimer (step 1), and a quoted-number unit check was added (step 7). Done under a `ora-weekly-hygiene-spec` claim after a concurrent session released it — see [[concurrent-session-duplicate-hardening-work]].
