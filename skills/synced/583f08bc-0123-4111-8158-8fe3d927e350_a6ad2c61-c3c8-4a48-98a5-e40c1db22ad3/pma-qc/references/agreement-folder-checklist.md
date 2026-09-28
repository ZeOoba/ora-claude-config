# Management-agreement folder checklist

Eleven artifacts. The agreement is not "complete" until every row is either
present in the property's deal folder or affirmatively recorded as not
applicable. The three marked ⚠ are the ones routinely missing.

| # | Artifact | Source | Notes |
|---|---|---|---|
| 1 | Executed management agreement, all pages, countersigned | Manager | A copy signed only by Owner is a draft. Confirm the manager's signature and date. |
| 2 | Exhibit A property schedule, current | ORA | Address range, parcel ID(s), building SF, owning entity per county string, service lines engaged (PM-17). Re-issue on every acquisition or disposition. |
| 3 | All addenda, fee-schedule letters, and renewal confirmations | Both | An auto-renewing agreement accumulates side letters. Absence of any is itself a finding worth stating. |
| 4 | ⚠ Certificate of fidelity bond | Manager | KRG requires a $250,000 bond and imposes no delivery obligation. Request annually (PM-8). |
| 5 | ⚠ Certificate of manager's E&O / professional liability | Manager | Not required by the KRG form at all. Request it; its absence is a live exposure, not a paperwork gap. |
| 6 | Certificate of manager's commercial general liability | Manager | Confirm limits and that Owner is named where applicable. |
| 7 | Owner's liability policy showing the manager as co-insured | ORA broker | Required by KRG §4(a). Verify it was actually endorsed. |
| 8 | Schedule of service contracts entered on Owner's behalf | Manager | KRG §3(c) makes Owner assume every one of these at termination. Request the schedule now, not at termination (PM-15). |
| 9 | Trust-account confirmation | Manager | Institution, account style, whether segregated per owner, whether interest-bearing and to whom interest accrues (PM-5). |
| 10 | Trailing 12-month fee detail by category | QuickBooks | Management, leasing, construction supervision, casualty, hourly. Feeds `scripts/fee_stack.py` and settles the per-property vs. per-agreement minimum question. |
| 11 | ⚠ Notice-address confirmation | Both | The KRG form specifies no notice address. Before any termination notice is drafted, confirm in writing where notice is to be delivered — an exit that turns on a written notice is only as good as the address it goes to (PM-14). |

## Register the renewal date

The day this checklist is completed, register a scheduled task for the
termination-notice deadline: 60 days before the renewal anniversary under the KRG
form, or whatever the reviewed agreement requires. Route via
`register-scheduled-task` (supervised `create_scheduled_task` on the target
surface only). An auto-renewing agreement with no calendared review is how a 2020
fee schedule reaches 2026.

## Notion

File the completed review under the property's record and log the decision
(renew / renegotiate / terminate) to the Knowledge Base via
`conversation-archival`. Record any departure from a PM position in the property's
deal-terms register.
