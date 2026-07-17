---
name: ora-skill-text-audit
description: Monthly skill-body grep for stale references (13 pattern classes) — day 15 of each month, 9:45 AM local. Clean pass → Notion log only; findings → email Gabriel, [ACTION REQUIRED] prefix for CRITICAL. v1.9 2026-07-16. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

**[MCP ROUTING — corrected 2026-06-11]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path (Composio removed 2026-06-11; there is NO fallback; on a non-zero COM exit retry once, then flag — do not halt). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper and Rube `d6315173` are retired — never reference either. ORA does not use Google Workspace.

Run ORA Skill Text Audit v1.9 (monthly cadence).

## Process

1. List all installed skills via `mcp__skills__list_skills`.
2. For each skill in `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\...\skills` (and any user-skills folder), read SKILL.md.
3. Grep each SKILL.md body for the **THIRTEEN stale-reference classes** below.
4. For each finding, capture: skill name, line number, snippet, finding class (a-m), severity, and recommended remediation.
5. Apply conditional notification (see §Notification).

## Pattern Library — THIRTEEN classes (v1.9)

**a. Legacy email.** `ze@oxfordra.net` — superseded by ggoldberg@/egoldberg@ per CLAUDE.md.

**b. Rube references.** `Rube`, `rube`, `Composio Rube`, any `RUBE_*` tool slug, `mcp__d6315173-...__RUBE_*` namespace. Sunset 2026-05-15. Allow past-tense historical references in changelogs (e.g., "was retired 2026-05-15"); flag forward-looking guidance.

**c. Orphaned skill cross-references (v1.9, 2026-07-16 — mirror-union + platform-gated fix).** Cross-check every backticked kebab-case identifier in each SKILL.md against ALL of: (1) the installed-skill folder list (Cowork skills-plugin catalog — what the original check scanned), (2) scheduled-task homes — the UNION of `Documents\Claude\Scheduled\<name>\` and `Claude_Workspace\00_Governance\Scheduled\<name>\` (these two mirrors are NOT symmetric — verified 2026-07-16 at 33 vs. 91 folders respectively, the larger one carrying more retired/archived entries; check BOTH, a miss in one does not imply a miss in the other), and (3) `C:\Users\Owner\.claude\skills\<name>\` PLUS installed plugin marketplace skill folders (e.g. `C:\Users\Owner\.claude\plugins\cache\<marketplace>\<plugin>\skills\<name>\`) for both bare and `namespace:name`-prefixed references (Code-surface skills, never mirrored into Cowork's catalog). Only flag a reference as orphaned if it is absent from ALL locations AND the available-skills listing AND does not match the platform-gated allow-list below. If a location genuinely cannot be reached this run (sandbox/permissions boundary), log that as a COVERAGE GAP on the finding, not a confirmed absence — never assert "does not exist" from a location you couldn't check.

Allow-list (do not flag):
  - Historical context: "formerly" / "subsumed" / "replaced by" / changelog sections.
  - False-positive guards: CLI commands (e.g., `extract-text`), JS libraries (e.g., `docx-js`), and illustrative examples in skill-creator.
  - **Platform-gated, no-filesystem-home skills (added v1.9).** A small set of real skills exist only as account-gated platform features with no filesystem footprint on ANY surface by design — e.g. `setup-writing-style`/`my-writing-style` (per `reference_writing_style_platform_skill.md`). These will never resolve in locations (1)-(3); do not flag. A skill body defensively handling "if not available in this session, skip the offer" (as `setup-cowork` already does) is itself evidence of this category, not a bug.

Root-cause history: F9 (`ora-skill-store-drift-check`, resolves at location 2) and F5 (`county-parcel-screen`, resolves at location 3) were false positives from the v1.7 single-location check, fixed v1.8. The v1.8 verification run (2026-07-16, all 52 skills, zero new false positives, zero missed genuine orphans) additionally surfaced the mirror-asymmetry and platform-gated gaps closed here in v1.9.

**d. Hardcoded dates that have passed.** Any ISO date `YYYY-MM-DD` more than 60 days old that appears in active guidance (NOT changelog or version-history sections). Strip "## CHANGELOG" / "## Change Log" / "## Version History" / "## Revision History" sections before scanning.

**e. Outdated MCP server IDs.** Any `mcp__<uuid>__*` reference whose UUID does not match a currently-active MCP server. Build the live-UUID set from this session's tool list.

**f. ORA File-Naming Standard version drift.** References to a specific dated version of the file-naming standard (e.g., `ORA File-Naming Standard 2026-05-14`) that no longer matches the current canonical version. Before flagging, read the canonical reference at `Claude_Workspace/00_Governance/References/Standards/` to determine the current version. If the canonical file cannot be located, log this as a finding itself.

**g. Intra-file version mismatch.** The skill's frontmatter `description` (or its inline `## name:` line) often ends with a version like `v2.0`. The CHANGELOG section's top entry should match. Flag where they diverge — usually a sign the editor bumped one but forgot the other.

**h. Placeholder-text survivors.** Literal `YYYY-MM-DD` outside of format-spec context, `[insert ___]`, `TODO`, `FIXME`, `<placeholder>`, `lorem ipsum`. Distinguish from format documentation (e.g., a sentence saying "file naming follows `[Description] [Property] [YYYY-MM-DD].ext`" is documentation, not a survivor). Heuristic: if the placeholder appears inside backticks AND inside a sentence describing a format, treat as documentation; otherwise flag.

**i. Plugin-namespace drift (v1.9, 2026-07-16 — cross-surface fix).** References to plugin-prefixed skill names (e.g., `anthropic-skills:skill-name`, `cowork-plugin-management:skill-name`, `ora-operations-extensions:skill-name`, `superpowers:skill-name`) where either (i) the plugin is no longer installed, or (ii) the prefixed name no longer matches the actual install path. Cross-check against the available-skills list in THIS session, AND directly check `C:\Users\Owner\.claude\plugins\cache\<marketplace>\<plugin>\skills\<name>\` for the referenced skill — this audit typically runs on the Cowork surface, which cannot see Code-only plugin marketplace skills through the available-skills list alone (e.g. `superpowers:*`), but the plugin cache path is a plain filesystem check reachable regardless of surface. A plugin-prefixed reference that resolves via either check is NOT drift. If truly absent from both AND the plugin cache path can't be reached this run, log as a COVERAGE GAP, not a confirmed absence. Root cause (2026-07-16 full run): F23 (`superpowers:dispatching-parallel-agents` in oxford-cc-strategic-audit) was wrongly flagged stale by a Code-hosted audit run that relied only on its own available-skills list rather than also checking the plugin cache directly. The correct call was to leave the reference alone, not "fix" it as if broken.

**j. Target-market parity drift.** The CANONICAL target-market roster is `skills/target-markets.json` (v1.1+). Load it and build the authoritative set: the `clusters[].market` names, plus `acceptable_states`. Then verify parity across every consumer the JSON lists under `consumers`:
  - **Skill bodies** — `acquisition-underwriting` (Markets hard filter), `deal-comparison` (Market Cluster Fit note), `market-monitor` (TARGET MARKET PROFILES — every cluster must have a profile), `rent-comp` (OXFORD MARKET BENCHMARKS table rows), `daily-brief` (Sections 1/2 news+transaction scope and the §7-equivalent law scope). Flag any consumer missing a canonical market, listing a market not in the JSON, or mis-tiering an established vs. entry-phase cluster.
  - **Scheduled tasks** — buy-box + Metro options tasks and the daily-brief equivalent scope must contain all canonical markets/states. (NOTE 2026-07-07: `ora-distress-signal-monitor` and `ora-daily-brief-6am` — the two tasks originally named here — are retired/superseded; check the current live roster instead: `ora-am-brief` and any live market-scanning task.)
  - **Notion Pipeline "Market" field** — fetch data source `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b` and confirm its `Market` select options ⊇ the canonical cluster names (plus the existing operational options "Cleveland OH" and "Other"). Note: Notion auto-creates select options on write, but curated board views (e.g., "🌎 By Market") do NOT back-fill option colors — so also flag any canonical market present as an option but missing a non-default color as a 🟢 LOW cosmetic finding.
  - **Notion Owner Outreach Queue "Metro" select (added v1.5, 2026-07-12)** — fetch data source `caa809b7-1da3-49d5-ab92-bcd7f36ca43e` and confirm its `Metro` select options ⊇ the canonical cluster names, using this alias map (this database uses short operational labels, not the JSON's full names — do NOT flag these as mismatches):
    | Canonical (target-markets.json) | Owner Outreach Queue option |
    |---|---|
    | Columbus OH | Columbus |
    | Kansas City MO/KS | Kansas City |
    | Indianapolis IN | Indianapolis |
    | Maryland (Baltimore/DC) | Baltimore-MD |
    | Cincinnati OH | Cincinnati |
    | Madison WI | Madison |
    | Grand Rapids MI | Grand Rapids |
    | Richmond VA | Richmond |
    | Des Moines IA | Des Moines |
    Backstory: Cincinnati and Kansas City were silently missing from this select for weeks (added 2026-07-12) because this database was outside class (j)'s scope entirely — it checked only the Acquisition Pipeline select. Treat a missing canonical alias here as the SAME severity as a missing Acquisition Pipeline option (🟠 HIGH), since owner-outreach promotion silently fails/misfiles without the option existing.
  Report each divergence as: consumer, what's missing/extra, and the one-line remediation (add/remove/re-tier). Treat the JSON as ground truth — if a skill or Notion select diverges, the skill/select is wrong. If `target-markets.json` itself cannot be located or fails to parse, log THAT as a 🔴 CRITICAL finding (the whole parity check is blind without it).

**k. Unregistered scheduled-task references (v1.7, 2026-07-16 — dual-fleet fix).** Any skill description or body that claims to "power", "consume outputs from", or otherwise depend on an `ora-*` scheduled task must reference a task LIVE ON EITHER FLEET. Build the authoritative roster via `python C:\Users\Owner\.claude\maintenance\fleet-status.py` — it reads BOTH the CC/MCP and LAMS/Cowork registries directly off disk and works from any surface. Do NOT rely on `mcp__scheduled-tasks__list_scheduled_tasks` alone: that tool only reaches the fleet matching the current session's surface, and in the 2026-07-16 full run, 4 of 5 class-k findings (F6, F8, F12, F15) were false positives caused by exactly this gap — a task genuinely live on the OTHER fleet read as "unregistered" because only one fleet was checked. (The GENERATED block in `C:\Users\Owner\.claude\session-context.md` may also exist — cross-check if available, but treat a fresh `fleet-status.py` read as authoritative since that block can itself be stale.) Flag any referenced `ora-*` task id absent from BOTH fleets. Allow historical context ("retired", "archived", "formerly", changelog sections) and the doctrine RETIRED list itself. Severity 🟠 HIGH.

**l. Routing-canon violation (v1.4, 2026-07-09).** Grep every SKILL.md body for `egoldberg` and flag any LIVE send instruction, recipient list, or cc that routes to egoldberg@oxfordra.net outside the sole sanctioned exception: the `ora-am-brief` Daily Brief cc (CLAUDE.md routing canon). Allow: historical/changelog context ("removed", "rescinded", "corrected", "retired"), and text that merely STATES the canon/exception (e.g. "only Daily Brief retains egoldberg cc") rather than routing to it. As of 2026-07-09 `ora-am-brief` is the ONLY sanctioned exception — if Gabriel ratifies another (e.g. a repaired Command Center Daily Brief), add it to this class FIRST, then to the canon statement. Severity 🔴 CRITICAL — these hits ride the [ACTION REQUIRED] email.

**m. Bare user-misaddress (v1.6, 2026-07-16).** Grep every SKILL.md body for "Ze" or "Ze Ooba" used as a form of address to the user in prose (e.g., "present to Ze", "sign as Ze Ooba", "ask Ze for approval") — CLAUDE.md's identity invariant requires "Gabriel"/"Gabriel Goldberg" (formal: "Mr. Goldberg"). This is distinct from class (a), which only catches the legacy email `ze@oxfordra.net`: the bare-name form has already caused two CRITICAL production incidents that class (a) missed — communication-intelligence's Standard Signature Block (found 2026-07-08, fixed v1.1) and document-assembly's user-address references (found 2026-07-15, fixed v1.3) — both caught only by ad hoc manual review because this was never a codified pattern. Allow historical/changelog context ("was 'Ze Ooba', corrected to Gabriel") and genuine unrelated proper nouns after context review. Severity 🔴 CRITICAL — same tier as class (a): both risk outbound mail signed with the wrong name.

## Severity Matrix

| Severity | Definition |
|----------|------------|
| 🔴 CRITICAL | Stale routing guidance that will cause production failures (e.g., references to MCP servers / tool slugs that no longer exist; orphaned skill references that route to a non-existent handler in a hot path); **routing-canon violation (class l) — any live egoldberg recipient/cc outside the sanctioned ora-am-brief exception**; **bare user-misaddress (class m) — "Ze"/"Ze Ooba" used to address the user instead of "Gabriel"**. |
| 🟠 HIGH | Orphaned cross-references in non-hot paths; intra-file version mismatches that compromise auditability; file-naming standard drift in active guidance; **target-market parity drift (class j) — a consumer (skill, scheduled task, OR either Notion select) missing or mis-tiering a canonical market** (a JSON parse/locate failure is 🔴 CRITICAL). |
| 🟡 MEDIUM | Stale forward-looking guidance now historical; placeholder-text survivors in non-output sections; plugin-namespace drift where the underlying skill still resolves correctly. |
| 🟢 LOW | Changelog-only artifacts; cosmetic drift; debris files in skills root. |

## Notification — Conditional (v1.1)

- **Clean pass (0 findings).** Write a single-line Notion log entry under Operations Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) titled `Skill Text Audit — [Date] — CLEAN PASS`. Page body must include: list of thirteen pattern classes scanned, file count, total runtime, "no findings" verdict. **NO email** — this avoids inbox pollution as the corpus stabilizes.
- **Findings present (≥1).** Create full Notion page titled `Skill Text Audit — [Date]` with findings table, methodology, and recommended next steps. Email Gabriel (ggoldberg@oxfordra.net). (Eric removed per Gabriel directive 2026-05-15 — only Daily Brief retains egoldberg cc.) Subject: `ORA Skill Text Audit — [Date]`. If any finding is CRITICAL, prefix subject with `[ACTION REQUIRED]`.

## Output formatting

ORA Institutional Style Guide v1.0+ (Oxford Navy #1B2A4A, Gold #C9A96E, Parchment #F5F3EF; EB Garamond / DM Sans / IBM Plex Mono). Run the 16-point QC Gate on findings emails before sending.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

Apply these five steps every time this skill calls `notion-create-pages`.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, perform a `notion-fetch(id=publishedId)` as a fallback verification step before declaring failure (search index can lag 30–60s). If both search and fetch fail → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (write the body to a temp file via Desktop Commander `write_file`, then `-BodyFile`): `-To "ggoldberg@oxfordra.net"`, `-Subject "❌ ora-skill-text-audit PUBLICATION FAILED — <YYYY-MM-DD>"`, body = what the page WOULD have contained verbatim, plus the Notion API error verbatim, plus the line `AUTO-SENT — meta-failure path, no human-in-loop available`. On a non-zero COM exit retry once, then record the failure. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

## Changelog

- **v1.9 (2026-07-16):** Hardened classes (c) and (i) after a full-corpus verification run of v1.8 (all 52 installed skills, zero new false positives, zero missed genuine orphans) surfaced two non-blocking gaps: (1) class (c)'s scheduled-task-home check assumed the two mirror directories were identical — verified they are NOT (33 vs. 91 folders); now explicitly checks the UNION of both. (2) Added a "platform-gated, no-filesystem-home skills" allow-category, covering account-gated platform features like `setup-writing-style`/`my-writing-style` that will never resolve on any filesystem location by design — previously would have required tribal memory to avoid a false positive. (3) Class (i) now also directly checks the plugin marketplace cache path (`~/.claude/plugins/cache/<marketplace>/<plugin>/skills/<name>/`) rather than relying solely on the current session's available-skills list, which is itself surface-scoped. No new pattern classes; still THIRTEEN (a-m).
- **v1.8 (2026-07-16):** Fixed classes (c) and (i) — same shape of bug as v1.7's class-k fix: checking only one catalog/surface produces false "orphaned"/"drift" findings. Class (c) now checks scheduled-task home mirrors and the Code-surface skills folder, not just the Cowork skills-plugin catalog, before flagging a cross-reference as orphaned. Class (i) now treats a Code-only plugin reference as cross-surface-unverifiable rather than stale when the audit runs on Cowork. Root cause: the 2026-07-16 full v1.7 run's own F5, F9, and F23 findings were all false positives of exactly this shape — 7 of that run's 23 total findings (30%) traced back to a wrong-catalog/wrong-fleet/wrong-surface check (F6, F8, F9, F12, F15 for class k; F5, F23 for classes c/i). No new pattern classes added; still THIRTEEN (a-m).
- **v1.7 (2026-07-16):** Fixed class (k) — switched from `mcp__scheduled-tasks__list_scheduled_tasks` (single-fleet, surface-scoped) to `fleet-status.py` (dual-fleet, disk-read, surface-independent) as the authoritative roster source. Root cause: the 2026-07-16 full v1.6 run's own class-k findings were 4/5 false positives (F6, F8, F12, F15) — each cited a task that was genuinely live, just on the LAMS/Cowork fleet rather than whichever fleet the running session's surface happened to reach. Only F22 (`ora-dashboard-refresh`, `ora-week-ahead-briefing` in oxford-cc-strategic-audit) was a real finding, confirmed dead on both fleets and fixed the same day.
- **v1.6 (2026-07-16):** Added class (m) bare user-misaddress — greps for "Ze"/"Ze Ooba" used as a form of address, distinct from class (a)'s legacy-email-only check. Added after a review found this pattern had caused two CRITICAL findings (communication-intelligence 2026-07-08, document-assembly 2026-07-15) that were only ever caught ad hoc, never by a codified class — and found three more stale "Ze Ooba" copies sitting outside this skill's scan path entirely (dead artifact/archive copies under `Claude_Workspace\01_Workspace\outputs\` and an old project archive), now remediated separately. Also corrected this skill's own stale self-documentation: frontmatter claimed "10 AM local" but the actually-registered cron is 9:45 AM (`45 9 15 * *`) — `_REGISTRY.md` also corrected.
- **v1.5 (2026-07-12):** Extended class (j) to also check the Notion Owner Outreach Queue "Metro" select (`caa809b7-1da3-49d5-ab92-bcd7f36ca43e`), after Cincinnati and Kansas City were found silently missing from it for weeks — undetected because this database was outside class (j)'s scope (it only checked the Acquisition Pipeline select). Added an explicit alias map since this database uses short operational labels rather than the JSON's full cluster names. Missing aliases here are now 🟠 HIGH, same as the Acquisition Pipeline gap. `target-markets.json` bumped to v1.1 with this database added under `consumers`.
- **v1.4 (2026-07-09):** Added class (l) routing-canon violation — greps all skill bodies for `egoldberg` outside the ora-am-brief Daily Brief cc exception; 🔴 CRITICAL, rides the [ACTION REQUIRED] email. (Setup-audit remediation Task 9a.)
- **v1.3 (2026-06-11):** Added class (k) unregistered scheduled-task references; retired the dead Composio send fallback from this spec's own routing.
- **v1.2 (2026-05-30):** Added pattern class (j) target-market parity — checks the five consuming skills, two scheduled tasks, and the Notion Pipeline "Market" select field against the canonical `skills/target-markets.json`; JSON is ground truth, parse/locate failure is CRITICAL.
- **v1.1 (2026-05-15):** Expanded pattern library from 5 to 9 classes — added (f) file-naming standard version drift, (g) intra-file version mismatch, (h) placeholder-text survivors, (i) plugin-namespace drift. Adopted conditional notification.
- **v1.0 (~2026-04):** Initial 5-class pattern library. Always emailed regardless of findings.