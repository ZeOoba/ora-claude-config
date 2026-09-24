---
name: ora-754-flaute-escalation-check
description: One-time 2026-08-28 08:00 ET tickler -- checks whether Union Township's approved PD site plan for 754 Old State Route 74 (rear-parking minor-amendment filing) has arrived; if not, flags the Craig Flaute escalation for Gabriel same-day. DEAL-TERMS-REGISTER.md Item 23 / DD Tracker v05 #122. Auto-disables after firing. One-time CC/MCP task = MODEL-N/A (one-time), exempt from the [MODEL:] tag per memory/reference_scheduled_task_model_standard.md.
---

You are running a one-time reminder check for Oxford Realty Advisors. Do not fabricate any status -- if you cannot verify something, say so explicitly rather than guessing.

CONTEXT: 754 Old State Route 74 (Cincinnati, OH) is under contract. Register Item 23 in `754 Old State/DEAL-TERMS-REGISTER.md` (in the OneDrive Business folder) requires Union Township's approved PD (Planned Development) site plan for the rear-parking minor-amendment filing. Gabriel Goldberg is the named ORA tracking owner (assigned 2026-08-24). If the approved site plan is not in hand by Friday 2026-08-28, the escalation path is to contact Craig Flaute (Union Township Dir. of Planning & Zoning) directly. This gates Register Item 12's contingency close-out and Item 13's PSA §4.1/§31 redraft -- also tracked in DD Tracker v05 #122.

STEPS:
1. Read `754 Old State/DEAL-TERMS-REGISTER.md` in the OneDrive Business folder (`C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\754 Old State\DEAL-TERMS-REGISTER.md`) and check the current status of Item 23 -- has it been updated since 2026-08-24 to reflect the site plan or the filed application arriving?
2. Also check the deal folder root and any `outputs/` subfolder for a dated file that looks like the Union Township approved site plan or a minor-amendment filing confirmation, received on or after 2026-08-24.
3. Do not guess from silence -- if you find no evidence either way, say so plainly rather than inferring resolution or non-resolution.

OUTPUT: draft (do not send without checking convention below) a short email via Outlook COM (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` -- the sole send path) to ggoldberg@oxfordra.net ONLY (no cc):
- Subject: "[ACTION] 754 Old State -- Flaute escalation check (Item 23)" if the site plan/filing is still not in hand as of today, or "754 Old State -- Item 23 status check (site plan may be in hand)" if you found evidence it arrived.
- Body: state plainly what you found (or didn't find) in Register Item 23 and the deal folder, and if not yet in hand, remind Gabriel that today (2026-08-28) is the escalation date he set for contacting Craig Flaute directly, per Register Item 23 and DD Tracker v05 #122.

On any send-via-outlook.ps1 non-zero exit: retry once, then note the failure plainly in your final summary rather than silently failing.

This is a single-step check-and-notify task (no progress-marker calls needed). Auto-disables after firing -- this is intentionally one-time, not recurring.