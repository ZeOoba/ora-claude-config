# ORA scheduled-task email send pattern (canonical)

> **RETIRED 2026-07-29 (Phase 3, approved blueprint):** `Send-OraReport.ps1` and `Send-OutreachQueueEmail.ps1` are archived in `_archive_2026-07-29_run-residue/` — zero live callers (verified by fleet-wide grep, both fleets). `send-via-outlook.ps1` is the SOLE send path (canon). Examples below referencing the retired wrappers are historical.


Last updated 2026-06-15. Applies to EVERY scheduled task that emails a report.

## The rule
Build the body as a FILE, then send it with ONE non-interactive process call.
NEVER type a multi-line HTML here-string into a persistent interactive shell
(Desktop Commander `interact_with_process`). Doing so leaves PowerShell in `>>`
continuation and silently buffers the send until a stray blank line flushes it
— observed 2026-06-15 on ora-owner-outreach-queue-refresh.

## Do this
1. Write the HTML body to a file with a DIRECT file write
   (Desktop Commander `write_file`), e.g. `%TEMP%\ora-<task>-<date>.html`.
   This never crosses a shell quoting/continuation boundary.
2. Send via the generic wrapper, invoked ONE-SHOT (`start_process`, runs and exits):

   ```
   powershell.exe -NoProfile -ExecutionPolicy Bypass `
     -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\Send-OraReport.ps1" `
     -Subject "ORA <Report> -- <date>" `
     -BodyFile "C:\...\ora-<task>-<date>.html"
   ```
   Add `-Cc "egoldberg@oxfordra.net"` ONLY for the Daily Brief (routing-canon
   exception). `-To` defaults to ggoldberg@oxfordra.net. Use `-DryRun` to validate
   the body build without sending. The wrapper prints `SENDEXIT=<code>` and exits
   with it: 0 = sent OK, 1 = usage, 2 = Outlook COM failure.

3. On non-zero exit: retry once, then flag loudly per the task's own failure path
   (Notion Operations Hub completion row). Do NOT halt.

## Don't do this
- Don't paste `$body = @" ... "@` into `interact_with_process` (the `>>` trap).
- Don't call `Mail.Send` from the Outlook drafting pane (Mail.Send not held).
- Don't add a `-Cc` to anything except the Daily Brief.

## Scripts in this folder
- `send-via-outlook.ps1`     — canonical Outlook COM sender (do not modify; the SOLE send path).
- `Send-OraReport.ps1`       — generic one-shot wrapper over the sender (-BodyFile/-BodyHtml, -Cc, -DryRun).
- `Send-OutreachQueueEmail.ps1` — task-specific wrapper that builds the owner-outreach body from scalar args.

## Fleet send-path status
**Composio fallbacks swept fleet-wide 2026-06-15.** Every active emailing task now names
`send-via-outlook.ps1` as the SOLE send path (no `mcp__composio-ora__*` / Rube / `8a611864`
send route remains). Surviving "Composio"/"Rube" strings are intentional keepers only:
doctrine "retired — never reference" notes, the two auditors' pattern definitions
(`ora-skill-text-audit`, `ora-skill-store-drift-check`), and tooling-sweep search topics.

Wrapper adoption (preferred invocation; the rest call `send-via-outlook.ps1 -BodyFile` directly):
- [x] ora-owner-outreach-queue-refresh — Send-OutreachQueueEmail.ps1 (2026-06-15).
- [x] ora-am-brief — Block B Send-OraReport.ps1; Blocks A/C/D on send-via-outlook.ps1 (2026-06-15).
- [ ] remaining emailing tasks — already file-based `-BodyFile`; move to Send-OraReport.ps1
      opportunistically on next touch. Execution-time `>>` risk is eliminated by this pattern.
