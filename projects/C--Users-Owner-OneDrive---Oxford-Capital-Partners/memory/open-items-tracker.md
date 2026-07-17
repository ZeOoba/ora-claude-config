---
name: open-items-tracker
description: "Single canonical open-items / punch-list tracker for the ORA system — one entry per open/residual/TODO item across memory, fleet, and repo state. Other files POINT here; item text lives in exactly one place."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1624855d-d36d-4c3e-9761-0250482b1d31
---

**Purpose:** every open/residual/TODO item anywhere in the ORA system (memory files, `oxford-cc-repo-health.md`-style incident writeups, `event_log.md` follow-ups, fleet punch lists) gets exactly ONE row here. Other files reference an item by pointer — `[open-items-tracker.md#OI-003](open-items-tracker.md#OI-003)` — and never restate its description, evidence, or status inline. A restated copy is the thing that rotted in the 2026-07-16/17 incident (see [[event_log]] and [[oxford-cc-repo-health]]): a forward-pointer to `session-context.md` "carrying the live list" went dead the instant that file's content moved on, because the item text lived in two places and only one of them got updated when the item closed.

**Why a new file, not an existing one:** checked against [memory-policy.md](memory-policy.md)'s fixed 13-doc set first. `ops_decision_log.md` is the closest existing candidate but is scoped to *already-decided* yes/no operational questions (one row per resolved question, answer never changes shape); this tracker is scoped to items with a *mutable open→closed lifecycle* that need to be found and closed, not re-derived. Different purpose, so a new file is the "real new domain" memory-policy.md requires before adding to the set.

## Convention

- **ID:** `OI-NNN`, zero-padded, monotonic, never reused. The ID lives on its own `### OI-NNN` header line so the anchor is stable (`open-items-tracker.md#OI-NNN`) — do not put the title on the header line itself.
- **Fields per item:** `Status` (OPEN / CLOSED), `Opened`, `Closed` (if closed), `Source` (the file/incident that raised it — link, not restated text), `Description` (one line), `Evidence` (closure only — what was actually checked, not "should be fine"), and an optional `Auto-check` line (see below).
- **Pointing in:** any other memory file that wants to mention this item links to `open-items-tracker.md#OI-NNN` and says nothing else about it — no paraphrase, no "as of DATE it's still open," nothing that can drift out of sync with the row here.
- **Closing an item:** flip `Status` to CLOSED, add `Closed:` date and `Evidence:` (what was mechanically checked, with the command/tool used), move it to the Closed table below. Never delete a row (append-only in spirit, same as `event_log.md` — a closed item stays as a record).

### Auto-check (optional, machine-checked)

An OPEN item may carry a single-line `**Auto-check:**` field in a small closed vocabulary that `memory-integrity-probe.py` can evaluate against live `fleet-status.py --json` output — no arbitrary code execution, just a bounded comparison against the dual-fleet scheduled-task registries:

- `kind=registry_disabled_count fleet=<cc|lams|all> expect=<N>` — the count of `enabled:false` tasks in that fleet must equal N for the item to read as resolved.
- `kind=registry_field_equals fleet=<cc|lams> task_id=<id> field=<cron|enabled> expect=<value>` — a named task's field must equal the given value.

When an OPEN item's auto-check matches, the probe emits a WARN (report-only, never auto-closes — a human still confirms and flips the status) on its next scheduled run (`ora-health-guard`, daily 05:15, or `ora-cc-schematic-refresh`, twice weekly). The probe also flags any `open-items-tracker.md#OI-NNN` reference elsewhere in `memory/*.md` whose ID doesn't resolve to a row here (dead pointer) — that one fails hard (matches the existing "orphan index link" severity), since a dead pointer into this file is exactly the failure mode this tracker exists to prevent. Detail: `~/.claude/maintenance/memory-integrity-probe.py`.

## Open

*(none as of 2026-07-17 — table appears once the first item opens)*

## Closed

| ID | Opened | Closed | Source | One-line |
|----|--------|--------|--------|----------|
| [OI-001](#OI-001) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Purge 2 dangling disabled LAMS scheduled-task entries |
| [OI-002](#OI-002) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Decide `ora-cam-reconciliation-annual` year-round vs. seasonal timing |

### OI-001
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Purge 2 dangling disabled LAMS scheduled-task entries left over from the fleet-recovery near-misses.
**Evidence:** `fleet-status.py` (run 2026-07-16) — zero disabled entries anywhere in the LAMS fleet. The one fleet-wide disabled task (`check-code-audit-image-pass`) is CC/MCP, unrelated to this item. Nothing was left to purge; the entries had already been cleared by an earlier pass that never logged closure here.
**Auto-check:** kind=registry_disabled_count fleet=lams expect=0

### OI-002
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Decide whether `ora-cam-reconciliation-annual` should run year-round or seasonally.
**Evidence:** Live LAMS registry cron for `ora-cam-reconciliation-annual` is `0 7 15 1 *` (fires once yearly, Jan 15) — confirms the seasonal decision was made and implemented; nothing further to decide.
**Auto-check:** kind=registry_field_equals fleet=lams task_id=ora-cam-reconciliation-annual field=cron expect="0 7 15 1 *"

---
*Both entries above were discovered already-closed during the 2026-07-16/17 dead-pointer incident (the `oxford-cc-repo-health.md` → `session-context.md` chain had gone stale) rather than closed in the normal course of work — hence identical opened/closed dates and no intermediate history. See [[event_log]] 2026-07-16 for the full incident writeup.*
