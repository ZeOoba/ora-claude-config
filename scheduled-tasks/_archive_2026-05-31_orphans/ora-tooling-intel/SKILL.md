---
name: ora-tooling-intel
description: Monday 10:30 AM weekly automation/tooling intel sweep — MCP releases, Claude updates, CRE-tech releases, internal-platform-relevant tools → Notion digest
---

ORA Weekly Tooling Intel Sweep. Runs Monday 10:30 AM.

**Context.** Ze is building an internal operating platform (1–2 year horizon) to replace Yardi, Argus, Juniper Square, Box, Salesforce. He wants a weekly signal scan — what tooling shipped this week that could accelerate or obsolete current ORA builds.

**Scope — scan 4 lanes:**

1. **AI & Agent Infra (highest priority)**
   - Anthropic releases (model cards, Claude Code changelog, Agent SDK, skills): https://docs.claude.com/en/release-notes/claude-code and https://www.anthropic.com/news
   - New / notable MCP servers released in the last 7 days — search: `site:github.com "model context protocol" MCP server` and MCP registry
   - Claude skill ecosystem updates

2. **CRE Tech & PropTech**
   - New releases / funding rounds / major product updates from: Yardi, AppFolio, Rent Manager, Buildium, MRI, RealPage, Leasecake, VTS, Dealpath, Juniper Square, Argus, Northspyre, Cherre, Reonomy, Honest Buildings
   - Any new entrants in shallow-bay industrial PM or underwriting tooling

3. **Integration & Workflow**
   - HubSpot, Notion, Zapier, Microsoft Graph, Netlify — new APIs, workflow features, or breaking changes affecting ORA stack

4. **Automation-adjacent**
   - New document-AI / OCR / lease-abstraction tools
   - QuickBooks + CData MCP ecosystem updates
   - Vector DB / RAG tooling with CRE-document use cases

**Method:**
- Use Firecrawl + WebSearch for each lane (parallel).
- Use `context7` for any specific library docs the sweep surfaces.
- Filter: only items from the **last 7 days**. Drop anything older.
- For each item, capture: Source, Date, Title, URL, One-line Why-It-Matters-To-ORA (tie explicitly to Ze's stack — internal platform build, PM consolidation, portfolio ops, or acquisitions workflow).

**Output:**
1. Create a Notion page in the "Tooling Intel" database (create DB if missing — schema: Week Of, Lane, Item, Source URL, Why It Matters, Action (None / Watch / Evaluate / Adopt)).
2. Draft an Outlook summary email to ggoldberg@oxfordra.net — top 5 items only, ranked by Why-It-Matters. Save as draft, do not send. (Updated 2026-04-28: was ze@oxfordra.net.)
3. If **zero items** surface across all 4 lanes, that's a signal — report the null result, don't fabricate.

**Guardrails:**
- Never hallucinate releases. If you can't verify a date or URL, drop the item.
- Flag any item with [SPECULATIVE] if the "why it matters" requires reasoning Ze should double-check.
- Keep total runtime under 10 minutes.

---

## 📬 EMAIL DELIVERY TO ggoldberg@oxfordra.net (mandatory final step — added 2026-04-16)

**In addition to** every output destination above (Notion Tooling Intel DB, Outlook draft to ze@), deliver the full intel sweep as an Outlook email to **ggoldberg@oxfordra.net**. This is additive — preserve the Notion entries and the draft to Ze.

Follow the procedure in `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md`:

1. Compose the **full intel report** as HTML — all 4 lanes (AI & Agent Infra, CRE Tech & PropTech, Integration & Workflow, Automation-adjacent). Include every item surfaced, not just top 5. For each: Source, Date, Title, URL, Why-It-Matters-To-ORA, Action (None / Watch / Evaluate / Adopt).
2. Write it to `C:/Users/Owner/AppData/Local/Temp/ora-tooling-intel-email-body.html`.
3. Send via Bash:
   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] Tooling Intel - Week Of $(date +%Y-%m-%d)" -BodyFile "C:/Users/Owner/AppData/Local/Temp/ora-tooling-intel-email-body.html" -BodyFormat html
   ```
4. If zero items surface across all 4 lanes: still send the email with body "No new releases surfaced this week across any lane." (null result is still signal).
5. On non-zero exit: retry once, then note `⚠️ EMAIL DELIVERY FAILED` and continue.

**This task's values:** `TASK_ID=ora-tooling-intel` · `DISPLAY_NAME=Tooling Intel`