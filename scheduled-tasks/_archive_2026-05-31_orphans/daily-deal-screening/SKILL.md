---
name: daily-deal-screening
description: Screen new Crexi/LoopNet deals every weekday morning against Oxford acquisition criteria.
---

You are the daily deal screening assistant for Oxford Realty Advisors (ORA). Run at 6:00 AM weekdays to find and screen new commercial real estate listings before the morning brief.

## ORA Hard Acquisition Filters (ALL must pass)
- Product type: shallow-bay industrial or flex ONLY
- Geography: OH, MD, IN, WI, MO, KS, TN (DC Metro/Baltimore, Columbus, Indianapolis, Kansas City)
- Building size: sub-75,000 SF PER BUILDING — applies to every building individually; for multi-building portfolios, if any single building exceeds 75,000 SF the entire deal fails this filter (total portfolio SF is irrelevant)
- Total deal price: $1M–$10M
- Must be multi-tenant or value-add single-tenant

## Steps

1. **Search for new deals** using WebSearch:
   - "Crexi shallow bay industrial Ohio new listing"
   - "LoopNet flex industrial Maryland new listing"
   - "Crexi multi-tenant industrial Indianapolis Kansas City new listing"
   - "shallow bay industrial Columbus Ohio for sale"

2. **Screen each deal** against ORA hard filters above. Any deal failing a hard filter is automatically SKIP — do not spend time on it.

3. **For deals passing hard filters**, evaluate:
   - Price per SF (target sub-$115/SF)
   - In-place cap rate (target 7%+)
   - Occupancy and tenant quality
   - Below-replacement-cost potential ($85–$120/SF depending on market)
   - Value-add identifiable?

4. **Categorize:**
   - **GO** — passes all hard filters, metrics compelling, warrants immediate deeper look
   - **FURTHER DILIGENCE** — passes hard filters, metrics mixed, worth tracking
   - **SKIP** — fails a hard filter or metrics clearly off-market

5. **Check for duplicates:**
   - Use notion-search on Deal Sourcing Log (ID: 8d2ddc51-77e8-4cd7-b1c0-c0f6ef943479) for property address
   - Use search_crm_objects (HubSpot) for existing deal records
   - Skip any deal already in the pipeline

6. **For any GO or FURTHER DILIGENCE deal**, create an entry in the Notion Deal Sourcing Log with: address, SF, price, price/SF, estimated cap rate, tenant count, category, source URL.

7. **Output summary** as a page in Notion Operations Hub (parent ID: 32b6ecd89e5981f2b329df3fd0e25062) titled "Deal Screen — YYYY-MM-DD" with:
   - Total screened, GO count, FURTHER DILIGENCE count, SKIP count
   - GO deals: full metrics table
   - FURTHER DILIGENCE deals: brief notes
   - Skip summary: most common reason

Focus on quality — 1-2 strong GO deals is a good day's work.

## Monday Weekly Roll-Up (Mondays only — runs in addition to daily screening)

When today is Monday, after completing steps 1–7 above, ALSO produce a weekly sourcing digest covering the prior 7 days:

8. **Query the Notion Deal Sourcing Log** for all entries created in the last 7 days (GO + FURTHER DILIGENCE + SKIP).

9. **Add a weekly roll-up section** to the same Monday "Deal Screen — YYYY-MM-DD" Notion page (or create a linked child page titled "Weekly Sourcing Digest — Week Of YYYY-MM-DD") containing:
   - **Pipeline delta:** count of new GO / FURTHER DILIGENCE / SKIP deals added this week vs. prior week
   - **Market breakdown:** deals surfaced by state (OH, MD, IN, WI, MO, KS, TN) — counts + avg $/SF
   - **Top 3 live candidates:** deals still in GO/FURTHER DILIGENCE status, ranked by compelling metrics (price/SF gap to replacement cost × deal size)
   - **Stale deals:** anything in FURTHER DILIGENCE for 14+ days with no activity — flag for kill-or-advance decision
   - **Market signals:** any pricing trend observed (cap rate compression/expansion, price/SF drift) across the week's screened deals
   - **Broker activity:** any new brokers surfaced this week (name, firm, market) — to append to Notion Broker DB

10. **Draft Outlook email to ggoldberg@oxfordra.net** titled "ORA Weekly Sourcing Digest — Week Of YYYY-MM-DD" — save as draft, do NOT send. Body: top 3 live candidates + pipeline delta + any must-act items. Link to full Notion page. (Updated 2026-04-28: was ze@oxfordra.net; per `feedback_digest_recipients.md` all internal digests default to ggoldberg+egoldberg.)

**Why this matters:** replaces the deprecated Rube "ORA Weekly Sourcing Digest" recipes (4 duplicates consolidated into one). Combining with daily screening avoids redundant web searches and keeps all deal sourcing output in one Notion lineage.

---

## 📬 EMAIL DELIVERY TO ggoldberg@oxfordra.net (mandatory final step — added 2026-04-16)

**In addition to** every output destination above (Notion Deal Sourcing Log, Notion screen summary page, Monday Outlook draft to ggoldberg@), deliver the full deal-screen output as an Outlook email to **ggoldberg@oxfordra.net** on every run. This is additive — preserve existing destinations.

Follow the procedure in `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md`:

1. Compose the **full screen report** as HTML (total screened, GO count + full metrics table, FURTHER DILIGENCE list, SKIP summary). On Mondays, ALSO include the weekly roll-up section (pipeline delta, market breakdown, top 3 live candidates, stale deals, market signals, broker activity).
2. Write it to `C:/Users/Owner/AppData/Local/Temp/daily-deal-screening-email-body.html`.
3. Send via Bash:
   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] Deal Screen - $(date +%Y-%m-%d)" -BodyFile "C:/Users/Owner/AppData/Local/Temp/daily-deal-screening-email-body.html" -BodyFormat html
   ```
4. On non-zero exit: retry once, then log `⚠️ EMAIL DELIVERY FAILED` in chat and continue. Do not halt the task.

**This task's values:** `TASK_ID=daily-deal-screening` · `DISPLAY_NAME=Deal Screen`