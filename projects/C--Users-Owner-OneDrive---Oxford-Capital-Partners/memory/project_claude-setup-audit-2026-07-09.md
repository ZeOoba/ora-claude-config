---
name: project-claude-setup-audit-2026-07-09
description: "9-agent audit of the ORA Claude Code setup (connectors/skills/hooks/memory/filing/terminal/tokens), 2026-07-09. 8 safe fixes applied + 2 exclusions caught on re-verification; 21 items await Gabriel's decision, headlined by the machine-migration status. Full report: artifact https://claude.ai/code/artifact/202c6ca3-05e2-4ded-991c-cbbaa326ece2"
metadata:
  node_type: memory
  type: project
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
---

# Claude Code Setup Audit — 2026-07-09

Full report (artifact, structured): https://claude.ai/code/artifact/202c6ca3-05e2-4ded-991c-cbbaa326ece2

## Headline finding — B4 RESOLVED 2026-07-11, B3 still open

This session ran on **LAPTOP-CSHSCBE6** (ASUS Zenbook S14, 32GB RAM) — Gabriel confirmed in-session "this is the new computer." But `session-context.md` (regenerated 2026-07-09T11:10 by `registry-membership-probe.py`) and multiple 07-05→07-08 event_log entries still asserted "Phase B migration — new machine has NOT arrived." Evidence read: this was very likely a **wholesale folder copy** of `~/.claude` (full git history + continuously-dated files back to mid-June + already-populated AppData scheduled-task registries), not the from-scratch reinstall `docs/MIGRATION_RUNBOOK.md`'s Phase B (B1) describes.

**B4 (old-machine decommission) — RESOLVED 2026-07-11:** Gabriel confirmed the old machine is no longer needed; safe to proceed toward physical decommission. `session-context.md` HALT note updated same day. The physical decommission step itself is manual (not Code-executable).

**B3 (48h burn-in checklist) — still open, needs Gabriel:** not confirmed complete. Next step: run the B3 burn-in checklist per `docs/MIGRATION_RUNBOOK.md`. Do NOT auto-run B2 fleet re-registration — both fleets are already live on this machine; re-registration would duplicate tasks.

**Why:** the stale HALT note actively risks a future session STOPping on legitimate work here, and several old-box-tuned thresholds (RAM watchdog, lean-RAM toolkit) were never re-verified against 32GB until this audit.

## What was fixed this session (safe, reversible, Claude-owned paths only)
- Doc corrections: composio-ora removal status (`00_system_of_record.md`), local-MCP/fred-registration wording (`tech.md`), OneDrive-scope guard-script resolution status (`MEMORY.md` + `reference_memory_scope_fragmentation.md`), event_log line-count (`memory-policy.md`), dead skill-name reference (`agents/lease-sweep.md`), rate-limit-vs-RAM split note (`reference_lean_ram_toolkit.md`).
- Scaffolded [deal-decision-ledger.md](deal-decision-ledger.md), seeded from projects.md's current "Recently resolved" entries — directly serves the self-reinforcing-learning ask.
- Archive sweep: `~/.claude/_archive/2026-07-09_root-scratch-sweep/` (23 loose files, 6 scratch dirs, 3 orphaned worktree stubs, `.git.broken-inplace`, duplicate `.claude.json.backup.*` snapshots) + Claude_Workspace (`_CLAUDE_REVIEW_DELETE_`, Reports consolidation, 19 legacy 2026-Q1 templates → `01_Workspace/_archive/legacy-templates-2026-03/`). All moves, no deletes. `~/.claude` git status verified clean before/after (see [[feedback_verify_subagent_safe_claims]]).

## What was deliberately NOT touched despite being flagged "safe-now"
See [[feedback_verify_subagent_safe_claims]] for the general lesson. Specifically this session:
- `chip-claims.log` — live claim-lock file, rules.md §8. Archiving would have silently reset in-flight chip claims.
- `daily-setup-audit-prompt.md` — canonical, live prompt the `ora-ops:ora-setup-audit` command opens by exact path daily at 06:30. Archiving would have broken it.
- The "12 empty `backups/` subfolders" claim — disproven on direct inspection; all 15 subfolders contain real files (1–304 each). Only the 5 duplicate `.claude.json.backup.*` snapshots (verified real) were consolidated.

## Resolution status — 2026-07-09 (same-day close-out, all 25 approved action items)

Gabriel reviewed every open item as multiple-choice questions same-day; all approved items were executed. Remaining genuinely open:
- **fred MCP**: RESOLVED 2026-07-09 — Gabriel pasted a real `FRED_API_KEY` into `.claude.json` and restarted; confirmed working in a fresh session.
- **Cowork skill reimport**: RESOLVED 2026-07-09 — Gabriel imported all 8 (monthly-close, acquisition-underwriting, loi-generation, deal-comparison, portfolio-growth, portfolio-reporting, conversation-archival, website-perfection) via Settings → Capabilities.
- **Connectors**: RESOLVED 2026-07-09 — Gabriel screenshotted the real Connectors list. Guru/Linear/Monday/Slack/ClickUp/Atlassian were never actually connected (the `mcp-needs-auth-cache.json` entries reflected an attempted/never-authorized plugin-bundle browse, not live connections) — nothing to disconnect. GitHub was already connected ("GitHub Integration," Web). No action needed.
- **`cowork-settings` skill**: RESOLVED 2026-07-09 — diffed canonical (06-11) against the stashed 07-08 draft, merged the real content each had that the other lacked (canonical: Scheduler section + "Register scheduled task" trigger + correct QC-gate name; 07-08 draft: correct "Principal" title + LOI trigger + Knowledge Base DB id + Design Rationale section; dropped the 07-08 draft's reintroduced dead `institutional-output-standards` reference). Ratified as `ora-skills/cowork-settings/versions/20260709_ORA_CoworkGlobalSettings_v2_1.md` (commit `44b5e01`), pasted into Cowork → Settings → Preferences by Gabriel, both prior v2.0 files retired to `versions/_archive/`. Live-test of the pasted block (Daily Brief/routing/Evaluate/Register-scheduled-task triggers) still outstanding per the doc's own Deployment Steps — not independently confirmed.
- **Replacement Cost Range row in standards.md**: RESOLVED 2026-07-09 — verified via a fresh Excel read (RCT v03: Columbus POINT $138.73/band $124.86–152.60, Cincinnati POINT $137.20/band $123.48–150.92; no v04 exists) and refreshed the row + a full source note. 754 Old State's $160/SF was confirmed real (`754-Inputs` C18) but is a genuine outlier above the RCT Cincinnati band with no per-cell source note — flagged for Gabriel, not folded into the range.
- **511 Industrial Mile / 470 McCormick**: Cowork/LAMS-side stage changes (511→Candidate reset, 470→Passed) aren't mirrored in this machine's event_log.md — a cross-fleet logging gap, not a data error. Informational only, no automation proposed (would need to clear the automation-budget bar).
- **Business/Personal OneDrive split**: proposal still exists at `Claude_Workspace/00_Governance/outputs/2026-07-09_OneDrive-Business-Personal-Split_Proposal_v01.md` (nothing moved) but is now SUPERSEDED IN PRACTICE by [[reference_onedrive_business_scope]] — a non-destructive classification reference (same Business/Personal/Ambiguous lists) that `rules.md` §1 now points every session at before broad business-focused OneDrive-root searches. Physical move only still needed if Gabriel wants the folder itself to look clean when browsed directly.

Also fixed along the way (found via B3 burn-in, not originally scoped): an unexplained active `allow-website-change` override sentinel that was bypassing oxfordra.net protection (removed); a governor-drift-probe.py skip-list gap for dated event_log archive rotations (fixed); target-markets.json packaging gap affecting 5 skills (fixed — added `SHARED_ROOT_DEPS` to package_skills.py); 3 factual defects in the newly-filed ratify-hurdle-rate skill (wrong migration number, stale branch pointer, title mismatch — fixed in both copies).

standards.md's underwriting-defaults table is now populated from 5 real deal models with full cell-level citation (754/511/470/275/DG-adjacent) — 2040 S Hamilton and the true DG 3-pack have no models and were correctly left blank, not fabricated. Divergent conventions (LC: $2/SF flat vs 6% of rent) were recorded as real divergence, not papered over.

## Top open items (needs-approval, not yet actioned) — see artifact for full detail + recommendations
- Cowork skill cache is materially stale: monthly-close (v1.0 vs canonical v2.0, drops the Restoration Church Trust ~$982,753 balloon alert due 2027-02-20) and acquisition-underwriting (v3.3 vs v3.5, missing Louisville KY cluster + Stage 2.6 DD checklist + bear-mode rules) — top priority repackage/reimport.
- A third ora-skills git clone (`Claude_Workspace/01_Workspace/.claude/skills/`) is 45 commits behind canonical + has its own uncommitted edits.
- `code-debugging-optimizations` skill claims "no approval gates" for oxfordra.net — conflicts with Hard Invariant 2, no tie-break resolves it.
- fred MCP documented active, registered nowhere (likely lost in the 2026-07-05 Desktop reinstall).
- `ora-autonomy-gate.py` false-blocks read-only Bash via bare `>` matching `2>&1`; `shared-checkout-guard.py` doesn't cover `~/.claude` itself despite it being named a covered surface and being dirty right now.
- Acquisition-learning loop not accreting: `standards.md` underwriting-defaults table blank despite 6 underwritten deals; pipeline table 28 days stale against its own 14-day rule; monthly consolidation shows no July run.
- OneDrive business-folder root: undifferentiated 198-entry dump mixing deal paper with personal/estate files; firm-name collision (`ORA/` vs `Oxford Realty Advisors/`); E. Fulton docs scattered 4+ places post-closeout.
- rules.md §9 automation budget lapses 2026-07-11 (2 days after this audit) unless re-ratified.
- Plugin-bundle reintroduced doctrine-retired Guru + 6 unused connectors (Cowork side, 2026-07-08); Zapier stuck needing re-auth since 2026-06-22.

## 2026-07-09 (late evening) — remediation session executed the ratified master prompt v02
All 13 tasks dispositioned in one session: T1/T2/T3/T4/T5(a-c)/T5d/T7/T8/T9/T10/T11 fully closed (several verified already-fixed by the same-day morning session — the pre-flight already-fixed check caught 5a, 5b, 9a, 13, and PR #197 for T4); T6 dead-man BUILT + committed (149a21f) with 3 Gabriel-gated activation steps (pre-push doctrine-gate drift, heartbeat-push schtask registration, workflow smoke); T12 executed for the Claude-system scope + all live "(1)" repoints, business bulk DEFERRED with a falsified-premise evidence manifest. Per-task detail: event_log entries "Setup-audit remediation T1…T12" (2026-07-09). Flagged-for-Gabriel checklist: in the session's closing report.
