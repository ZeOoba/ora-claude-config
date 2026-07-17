---
name: ora-fulton-deadline-alert
description: Daily E. Fulton Street DD deadline scanner — surfaces items due within 3 business days
---

You are the E. Fulton Street DD deadline scanner for Oxford Realty Advisors. Check the current date and compare it against these critical deadlines. Surface any items due within 3 business days.

DEADLINES (PSA Execution: April 15, 2026):
- Apr 15: Resolve §26 Offer Expiration (McGrath confirmation); Finalize PSA Counter-Redline; Request Estoppels
- Apr 16: PSA Counter-Redline send deadline; Engage Phase II Consultant (August Mack) window opens
- Apr 21: Phase II engagement must be executed by this date
- Apr 21-24: Commission Roof IR Scan + Structural Engineer
- Apr 22: DEPOSIT DUE ($200K wire to Newmark Title); Seller Doc Delivery deadline; Order Title Commitment
- Apr 27: Title Commitment Due from Seller (10 CD from PSA, Apr 25 Sat → Mon)
- Apr 28: Resolve Vector Security Mechanics Lien
- Apr 29: Whitehall CCD Zoning Verification
- May 14: Phase II Results Expected (GATING — 5-BD review clock starts)
- May 15: Feasibility Period Earliest Expiry (30-day); LLC + Insurance complete
- May 20: GO/NO-GO Decision (deposit goes hard after 5-BD Phase II review)
- Jun 5: Request Settlement Statement
- Jun 12: Feasibility Period Hard Outer Limit (capped at Closing §9.1); CLOSING — Hard Deadline ($4M)

OUTPUT FORMAT:
🔴 OVERDUE: [items past deadline]
🟡 DUE WITHIN 3 BD: [items approaching]
🟢 NEXT UP: [next 2 items on the horizon]

If nothing is due within 3 BD, just report the next upcoming milestone. Keep it under 10 lines.

---

## 📬 EMAIL DELIVERY TO ggoldberg@oxfordra.net (mandatory final step — added 2026-04-16)

Deliver the full Fulton deadline report as an Outlook email to **ggoldberg@oxfordra.net** on every run, regardless of whether anything is due. This keeps the DD calendar visible even on quiet days.

Follow the procedure in `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md`:

1. Compose the **full alert output** as HTML (🔴 overdue, 🟡 due within 3 BD, 🟢 next up). Keep it tight — this is intentionally a short report.
2. Write it to `C:/Users/Owner/AppData/Local/Temp/ora-fulton-deadline-alert-email-body.html`.
3. Send via Bash:
   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] Fulton Deadline - $(date +%Y-%m-%d)" -BodyFile "C:/Users/Owner/AppData/Local/Temp/ora-fulton-deadline-alert-email-body.html" -BodyFormat html
   ```
4. **Any 🔴 OVERDUE finding:** prefix subject with `[ORA URGENT]` instead of `[ORA]` so Gabriel notices immediately.
5. On non-zero exit: retry once, then report `⚠️ EMAIL DELIVERY FAILED` in chat and continue.

**This task's values:** `TASK_ID=ora-fulton-deadline-alert` · `DISPLAY_NAME=Fulton Deadline`
