---
name: ora-skill-text-audit
description: Monthly skill-body grep for stale references (12 pattern classes) — day 15 of each month, 10 AM local. Clean pass → Notion log only; findings → email Gabriel, [ACTION REQUIRED] prefix for CRITICAL. v1.5 2026-07-12. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

**[MCP ROUTING — corrected 2026-06-11]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path (Composio removed 2026-06-11; there is NO fallback; on a non-zero COM exit retry once, then flag — do not halt). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper and Rube `d6315173` are retired — never reference either. ORA does not use Google Workspace.

Run ORA Skill Text Audit v1.5 (monthly cadence).

## Process

1. List all installed skills via `mcp__skills__list_skills`.
2. For each skill in `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\...\skills` (and any user-skills folder), read SKILL.md.
3. Grep each SKILL.md body for the **TWELVE stale-reference classes** below.
4. For each finding, capture: skill name, line number, snippet, finding class (a-l), severity, and recommended remediation.
5. Apply conditional notification (see §Notification).

## Pattern Library — TWELVE classes (v1.5)

**a. Legacy email.** `ze@oxfordra.net` — superseded by ggoldberg@/egoldberg@ per CLAUDE.md.

**b. Rube references.** `Rube`, `rube`, `Composio Rube`, any `RUBE_*` tool slug, `mcp__d6315173-...__RUBE_*` namespace. Sunset 2026-05-15. Allow past-tense historical references in changelogs (e.g., "was retired 2026-05-15"); flag forward-looking guidance.

**c. Orphaned skill cross-references.** Cross-check every backticked kebab-case identifier in each SKILL.md against the installed-skill folder list and the available-skills listing. Allow "formerly" / "subsumed" / "replaced by" historical context. False-positive guards: CLI commands (e.g., `extract-text`), JS libraries (e.g., `docx-js`), and illustrative examples in skill-creator.

**d. Hardcoded dates that have passed.** Any ISO date `YYYY-MM-DD` more than 60 days old that appears in active guidance (NOT changelog or version-history sections). Strip "## CHANGELOG" / "## Change Log" / "## Version History" / "## Revision History" sections before scanning.

**e. Outdated MCP server IDs.** Any `mcp__<uuid>__*` reference whose UUID does not match a currently-active MCP server. Build the live-UUID set from this session's tool list.

**f. ORA File-Naming Standard version drift.** References to a specific dated version of the file-naming standard (e.g., `ORA File-Naming Standard 2026-05-14`) that no longer matches the current canonical version. Before flagging, read the canonical reference at `Claude_Workspace/00_Governance/References/Standards/` to determine the current version. If the canonical file cannot be located, log this as a finding itself.

**g. Intra-file version mismatch.** The skill's frontmatter `description` (or its inline `## name:` line) often ends with a version like `v2.0`. The CHANGELOG section's top entry should match. Flag where they diverge — usually a sign the editor bumped one but forgot the other.

**h. Placeholder-text survivors.** Literal `YYYY-MM-DD` outside of format-spec context, `[insert ___]`, `TODO`, `FIXME`, `<placeholder>`, `lorem ipsum`. Distinguish from format documentation (e.g., a sentence saying "file naming follows `[Description] [Property] [YYYY-MM-DD].ext`" is documentation, not a survivor). Heuristic: if the placeholder appears inside backticks AND inside a sentence describing a format, treat as documentation; otherwise flag.

**i. Plugin-namespace drift.** References to plugin-prefixed skill names (e.g., `anthropic-skills:skill-name`, `cowork-plugin-management:skill-name`, `ora-operations-extensions:skill-name`) where either (i) the plugin is no longer installed, or (ii) the prefixed name no longer matches the actual install path. Cross-check against the available-skills list in this session.

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

**k. Unregistered scheduled-task references (v1.3, 2026-06-11).** Any skill description or body that claims to "power", "consume outputs from", or otherwise depend on an `ora-*` scheduled task must reference a LIVE task. Build the authoritative roster from `mcp__scheduled-tasks__list_scheduled_tasks` directly (the GENERATED block in `C:\Users\Owner\.claude\session-context.md` may also exist — cross-check both if available). Flag any referenced `ora-*` task id absent from the live roster. Allow historical context ("retired", "archived", "formerly", changelog sections) and the doctrine RETIRED list itself. Severity 🟠 HIGH.

**l. Routing-canon violation (v1.4, 2026-07-09).** Grep every SKILL.md body for `egoldberg` and flag any LIVE send instruction, recipient list, or cc that routes to egoldberg@oxfordra.net outside the sole sanctioned exception: the `ora-am-brief` Daily Brief cc (CLAUDE.md routing canon). Allow: historical/changelog context ("removed", "rescinded", "corrected", "retired"), and text that merely STATES the canon/exception (e.g. "only Daily Brief retains egoldberg cc") rather than routing to it. As of 2026-07-09 `ora-am-brief` is the ONLY sanctioned exception — if Gabriel ratifies another (e.g. a repaired Command Center Daily Brief), add it to this class FIRST, then to the canon statement. Severity 🔴 CRITICAL — these hits ride the [ACTION REQUIRED] email.

## Severity Matrix

| Severity | Definition |
|----------|------------|
| 🔴 CRITICAL | Stale routing guidance that will cause production failures (e.g., references to MCP servers / tool slugs that no longer exist; orphaned skill references that route to a non-existent handler in a hot path); **routing-canon violation (class l) — any live egoldberg recipient/cc outside the sanctioned ora-am-brief exception**. |
| 🟠 HIGH | Orphaned cross-references in non-hot paths; intra-file version mismatches that compromise auditability; file-naming standard drift in active guidance; **target-market parity drift (class j) — a consumer (skill, scheduled task, OR either Notion select) missing or mis-tiering a canonical market** (a JSON parse/locate failure is 🔴 CRITICAL). |
| 🟡 MEDIUM | Stale forward-looking guidance now historical; placeholder-text survivors in non-output sections; plugin-namespace drift where the underlying skill still resolves correctly. |
| 🟢 LOW | Changelog-only artifacts; cosmetic drift; debris files in skills root. |

## Notification — Conditional (v1.1)

- **Clean pass (0 findings).** Write a single-line Notion log entry under Operations Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) titled `Skill Text Audit — [Date] — CLEAN PASS`. Page body must include: list of twelve pattern classes scanned, file count, total runtime, "no findings" verdict. **NO email** — this avoids inbox pollution as the corpus stabilizes.
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

- **v1.5 (2026-07-12):** Extended class (j) to also check the Notion Owner Outreach Queue "Metro" select (`caa809b7-1da3-49d5-ab92-bcd7f36ca43e`), after Cincinnati and Kansas City were found silently missing from it for weeks — undetected because this database was outside class (j)'s scope (it only checked the Acquisition Pipeline select). Added an explicit alias map since this database uses short operational labels rather than the JSON's full cluster names. Missing aliases here are now 🟠 HIGH, same as the Acquisition Pipeline gap. `target-markets.json` bumped to v1.1 with this database added under `consumers`.
- **v1.4 (2026-07-09):** Added class (l) routing-canon violation — greps all skill bodies for `egoldberg` outside the ora-am-brief Daily Brief cc exception; 🔴 CRITICAL, rides the [ACTION REQUIRED] email. (Setup-audit remediation Task 9a.)
- **v1.3 (2026-06-11):** Added class (k) unregistered scheduled-task references; retired the dead Composio send fallback from this spec's own routing.
- **v1.2 (2026-05-30):** Added pattern class (j) target-market parity — checks the five consuming skills, two scheduled tasks, and the Notion Pipeline "Market" select field against the canonical `skills/target-markets.json`; JSON is ground truth, parse/locate failure is CRITICAL.
- **v1.1 (2026-05-15):** Expanded pattern library from 5 to 9 classes — added (f) file-naming standard version drift, (g) intra-file version mismatch, (h) placeholder-text survivors, (i) plugin-namespace drift. Adopted conditional notification.
- **v1.0 (~2026-04):** Initial 5-class pattern library. Always emailed regardless of findings.