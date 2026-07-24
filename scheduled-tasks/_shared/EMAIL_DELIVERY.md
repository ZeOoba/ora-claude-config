# Shared: Email Delivery Procedure

**Added:** 2026-04-16
**Applies to:** Every ORA scheduled task that references this file.
**Destination:** ggoldberg@oxfordra.net (Gabriel's Outlook inbox).
**Transport:** Desktop Outlook via COM automation (`send-via-outlook.ps1`) is the **SOLE send path** (the Composio fallback was removed 2026-06-11 — the connector no longer exists). On a non-zero COM exit: retry once, then flag the failure loudly (see Step 4) — do NOT route through Composio (gone), Rube (EOL 2026-05-15), Gmail, or Zapier. There is no second send mechanism by design; silent-send detection lives in the automation-health-monitor producer-beacon check.

---

## Contract

Every scheduled task that includes the reference block (see `REFERENCE_BLOCK_SNIPPET` below) MUST, as its final step, deliver the full report as an email via this procedure — **in addition to** every existing output destination (Notion pages, Email Response Queue entries, draft emails to other recipients, Critical Deadlines Tracker entries, SharePoint logs, etc.). This delivery is additive, never a replacement.

## Steps

### 1. Compose the email body as HTML

Include the **complete report content** that was posted to Notion or displayed elsewhere — all headers, tables, bullet lists, status flags (🔴🟡🟢), action items. Do NOT summarize. Do NOT send a link-only email.

Structure:

```html
<html>
<body style="font-family: -apple-system, 'Segoe UI', Arial, sans-serif; font-size: 14px; color: #1B2A4A;">
  <h1 style="color: #1B2A4A;">[ORA] &lt;Task Display Name&gt; — YYYY-MM-DD</h1>
  <p><em>Automated report from &lt;task-id&gt; at HH:MM America/New_York.</em></p>

  <!-- Full report content here: sections, tables, action items -->

  <hr>
  <p style="font-size: 12px; color: #666;">
    <strong>Canonical copy:</strong> &lt;Notion URL if one was created&gt;<br>
    <strong>Task:</strong> &lt;task-id&gt; · <strong>Run started:</strong> YYYY-MM-DD HH:MM ET
  </p>
</body>
</html>
```

### 2. Write the body to a temp file

Use the Write tool:

- **Path:** `C:/Users/Owner/AppData/Local/Temp/ora-<task-id>-email-body.html`
- Replace `<task-id>` with this task's identifier (e.g., `ora-morning-brief`, `ora-eod-wrap`).

### 3. Send via Outlook COM

Call the helper from Bash. One line, use backticks to escape newlines in PowerShell:

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] <Display Name> - $(date +%Y-%m-%d)" -BodyFile "C:/Users/Owner/AppData/Local/Temp/ora-<task-id>-email-body.html" -BodyFormat html
```

Replace `<Display Name>` with the task's human-readable name (see mapping in REFERENCE_BLOCK_SNIPPET).

### 4. Verify exit code

- **Exit 0 → success.** Add a line to your Notion completion log: `Email delivered to ggoldberg@oxfordra.net`.
- **Exit 1 → usage error.** Check the Write step produced a file. Retry once.
- **Exit 2 → Outlook COM failure.** Retry once. If it still fails, there is **NO send fallback** (Composio was removed 2026-06-11): append `⚠️ EMAIL DELIVERY FAILED (COM, no fallback)` to your Notion "Automation Health" completion row, include the last 20 lines of `C:/Users/Owner/.claude/scheduled-tasks/_shared/send-log.txt`, and ensure the task's primary output beacon (its Notion page / digest) is produced or visibly flagged — `ora-automation-health-monitor`'s producer-beacon check is what surfaces a silent send to Gabriel. Do NOT halt the task. Recipients stay `ggoldberg@oxfordra.net` only (2026-05-15 directive re-ratified 2026-06-10; only the Daily Brief cc's Eric). Never route through Composio (gone), Rube (EOL), or Gmail.

### 5. Error-case coverage

If the task encountered a critical failure (Notion unreachable, data source down) and would have drafted an alert email, ALSO send that alert via this same procedure — use subject prefix `[ORA ERROR]` and include the error details in the body. Failures must not go silent to Gabriel's inbox.

---

## Task ID → Display Name mapping

| taskId | Display Name (for subject line) |
|---|---|
| ora-morning-brief | Morning Brief |
| ora-email-queue-am | Email Queue (AM) |
| ora-email-queue-pm | Email Queue (PM) |
| ora-eod-wrap | EOD Wrap |
| ora-site-health | Site Health |
| ora-monday-sync | Monday Sync |
| ora-friday-closeout | Friday Closeout |
| ora-sunday-maintenance | System Maintenance |
| ora-mid-month-ops | Mid-Month Ops |
| ora-monthly-kickoff | Monthly Kickoff |
| ora-quarterly-review | Quarterly Review |
| ora-covenant-watch | Covenant Watch |
| daily-deal-screening | Deal Screen |
| ora-fulton-deadline-alert | Fulton Deadline |
| ora-hubspot-sync | HubSpot Sync |
| ora-tooling-intel | Tooling Intel |
| ora-qb-export-watcher | QB Export Watcher |

---

## REFERENCE_BLOCK_SNIPPET (what goes in each task's SKILL.md)

```markdown
---

## 📬 EMAIL DELIVERY TO ggoldberg@oxfordra.net (mandatory final step)

Before exiting, deliver the full report as an Outlook email to **ggoldberg@oxfordra.net** — in addition to every existing output destination above (Notion, Email Response Queue, drafts to other recipients, SharePoint logs). This is additive, never a replacement.

Follow the procedure in `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md`:

1. Compose the **full report** as HTML (not a summary).
2. Write it to `C:/Users/Owner/AppData/Local/Temp/ora-<TASK_ID>-email-body.html`.
3. Invoke `C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1` via Bash with:
   - `-To "ggoldberg@oxfordra.net"`
   - `-Subject "[ORA] <DISPLAY_NAME> - YYYY-MM-DD"`
   - `-BodyFile` pointing at the temp file
   - `-BodyFormat html`
4. On non-zero exit: retry once, then log `⚠️ EMAIL DELIVERY FAILED` in Automation Health and continue.
5. On any task-level error you would have drafted to ggoldberg@oxfordra.net, also send via this helper with subject prefix `[ORA ERROR]` so failures don't stay silent.

**This task's values:** `TASK_ID=<task-id>`, `DISPLAY_NAME=<Display Name>`
```

---

## Rationale

- Outlook desktop is already authenticated under Gabriel's M365 profile — COM automation uses that context automatically.
- No Gmail (Ze uses Outlook only).
- No Zapier (account out of space as of 2026-04-16).
- No Graph API app registration (zero admin overhead).
- Sends from Gabriel's account, appears in Sent folder AND Inbox (since To: is the same account = self-copy).

## When to update this file

- Ze or Gabriel changes destination email → update `To:` argument in all task references.
- Outlook COM stops working (e.g., Outlook uninstalled, switched to new machine) → swap helper implementation in `send-via-outlook.ps1`. Task SKILL.md files do not need to change because they all call through the shared helper path.
- Add a new scheduled task → add its reference block and update the mapping table above.
