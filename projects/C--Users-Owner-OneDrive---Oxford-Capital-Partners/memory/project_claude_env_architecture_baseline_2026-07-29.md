---
name: claude-env-architecture-baseline-2026-07-29
description: Forensic architectural baseline of the full Claude Code environment (2026-07-29) — official reference for future architecture decisions; optimization NOT yet approved
metadata: 
  node_type: memory
  type: project
  originSessionId: 46a85dfc-a400-4abf-91ca-96d829f85eca
  modified: 2026-07-29T15:58:43.125Z
---

**Baseline report:** `Claude_Workspace/02_Outputs/2026-07-29_Claude-Environment_Architecture-Baseline_v01.md` — Gabriel commissioned a description-only forensic audit (Lane L5) of every behavior-influencing component; the report is the ratifiable baseline. **No optimization/refactor was approved as of 2026-07-29** — any consolidation work must wait for Gabriel's explicit go-ahead against this document.

**Target-architecture design (same day):** `Claude_Workspace/02_Outputs/2026-07-29_Claude-Environment_Target-Architecture_v01.md` — A/B/C/D classification of every component, authority hierarchy, 13-item defect remediation plan (P0: Fleet Dead-Man repair + heartbeat-push registration), 5-phase migration, ~5–8k/session [EST] token levers. **Phase 1 EXECUTED 2026-07-29 (Gabriel-approved in-turn); Phases 2–5 await approval.** Journal: `~/.claude/docs/2026-07-29_phase1-migration-journal.md`. Milestone surfaced 3 NEW pre-existing defects (governor-drift-probe decimal-percent false positives · memory-integrity-probe live-path bleed into test sandboxes · open-items-tracker OI-032/033 orphans + 5 missing sections) — these currently FAIL the ~/.claude pre-push test gate, so pushes (incl. the 07:30 heartbeat push) are blocked until fixed; slot into Phase 2. All Category-A redundancy (governor multi-home, health twins, dual invariant enforcement, 3-layer confidentiality) explicitly preserved.

Headline facts verified 2026-07-29: 30 hook bindings → 24 live Python guards + 5 inline bash hooks + 3 git pre-push gates; dual 29-task fleets (both registries parsed); 4 Windows Task Scheduler jobs (ClaudeFleetMirror, Mirror Deploy, Dead-Man, Stuck-Session Watchdog); 10 plugins / 7 marketplaces; 3-tier MCP (user-scope json / desktop extensions / claude.ai connectors); ~95 skills from 5 origins; memory store 220 files / 3.2 MB.

Open findings recorded in the report (described, not fixed): inline-hook naming convention conflicts ratified three-schema doctrine (settings.json lines ~218/284) · `FRED_API_KEY` plaintext in `~/.claude.json` · `anthropic-key.dat`/`netlify-token.dat` in `scheduled-tasks/_shared/` · ORA Fleet Dead-Man exit 0x800704A0 on 2026-07-29 · `model-currency-probe.py` runs with no discoverable caller · documented "ORA Fleet Heartbeat Push" Windows task not registered · dead `additionalDirectories` → absent `oxford-perfection` · 3 stale keybindings target subsumed skills · `hooks/state/` referenced but absent.

**Why:** future architecture/optimization sessions must start from this baseline instead of re-discovering, and must not treat the audit as approval to change anything.
**How to apply:** read the report first; verify volatile counts (fleet, hooks) against live sources before acting — the baseline is point-in-time. Related: [[oxford-cc-repo-health]], [[project_claude-setup-audit-2026-07-16]].
