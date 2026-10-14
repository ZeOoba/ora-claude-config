---
name: project-automation-audit-rev28-plugins-connectors-2026-09-30
description: R28 (2026-09-30) scoped plugins/connectors pass with Cowork second opinion; Desktop Commander KEEP (19,310 calls), Claude Docs KEEP, pdf-viewer retire pending, Notion trial lapses ~10-02, send-tool guard gap
metadata:
  type: project
---

Scoped Thread 1 pass (plugins and connectors) plus a Cowork second-opinion review. No Automation Audit artifact was published; nothing live was changed. Chains [[project-automation-audit-rev27-2026-09-22]]. Fix to the method landed in `ora-setup-audit` v1.16 (uncommitted in `~/ora-skills` until Gabriel approves the commit).

**Verdicts (reconciled Code + Cowork):**
- Desktop Commander Extension: **KEEP**. First called dead on skill counts alone; wrong. `get_usage_stats` 19,310 calls, 97% success (re-read by me 09-30; Cowork's earlier snapshot said 19,190); 23 live task specs reference it (10 CC/MCP, 13 LAMS, both grepped). Only path from Cowork to `C:\Users\Owner\...`, and the NY Fed SOFR fetch needs it (hosted fetch gets 403). The Code plugin form is not installed; `settings.json:96` and five hooks carry a dual-prefix matcher that is harmless.
- Claude Docs: **KEEP**, one live doc, platform-native, nothing to retire. visualize: KEEP (soft). excel, census, fred, context7: KEEP; `underwriting-checker` and `noi-opportunity-scout` use `mcp__excel__*`.
- pdf-viewer: retire (Gabriel ruled, account-store action, not yet done). cowork-plugin-management: keep.
- Dropped: `skillOverrides` proposals and per-agent deny. `anthropic-skills:*` override keys are inert; the 8 built-in `user-invocable-only` keys are NOT inert (absent from the live listing; the probe only reports UNVERIFIED).
- Gabriel ruled: no registry pilots; skip unpublishing google-workspace.

**Open items Gabriel owns:**
- **Notion: DONE 2026-09-30.** Gabriel upgraded to Plus; a live `notion-create-pages` call succeeded the same day (private draft test page `3eb6ecd8-9e59-8161-838b-fffb56dc4235`, titled "OI-288 block-cap verification", safe to delete), so the 1,000-block cap no longer applies. Still open: close OI-288 in `open-items-tracker.md` (needs a `sched-open-items-tracker` claim) and set `_state/notion-publish-degraded.json` `trial_expiry_risk` to resolved. Not done by me.
- **Send/CMS write guard gap:** `confidentiality-guard.py:74,366` scans outlook send/draft/forward/reply payloads for confidential terms only. It does not block `teams_send_*` or HubSpot `manage_blog_post`/`manage_landing_page`/`manage_website_page`. No hook found covering either. Guard hook needs worktree, claim, adversarial pass, Gabriel OK.
- **Fleet:** nearly all CC tasks are OFF (am-brief and pr-land-watch on); `fleet-roster.md` is stale (generated 09-23). Do not run `registry-membership-probe.py` to refresh it during an investigation.

**Send/CMS gate: LIVE 2026-09-30.** Extends `hooks/ora-autonomy-gate.py` (Gate 1b ms365 email, 1c Teams, 3 HubSpot CMS; new token `allow-hubspot-cms-write`). ora-claude-config PR 292 merged as `b401c08`; live `~/.claude` (`live/primary-checkout`) fast-forwarded 781bf6b -> b401c08 with Gabriel's approval (the `allow-config-write` token was minted for that one command and archived to `overrides-used/`). Proved live: 8/8 crafted payloads via the live script, and a real `outlook_send_draft` call with a nonexistent id was blocked by the hook in-session. Reviews were Opus 5.5 (Fable at its monthly spend limit, disclosed in the PR). ora-skills PR 94 (v1.16) was open at the time of writing; merge state not re-checked. Residuals and follow-ups: calendar/vacation/filter gating (session b0bb92, branch `feat/mcp-calendar-gate`), Bash/file-tool parse-failure fail-open (session a50341, `fix/autonomy-gate-parse-failclosed`), draft-token binds the draft id not its contents, hooks never run in Cowork, stale confidentiality-guard matcher (hooks-audit-0930). Worktree `.claude/worktrees/mcp-send-gate` left in place (archive, never delete).

**Before trusting this:** Cowork's LAMS transcript window is ~2 weeks (85 of 525 sessions retained); absence there is a 2-week statement. See [[reference_skilloverrides_ignored_for_plugin_skills]].
