---
name: project-county-sales-monitor-skill-draft
description: "New county-sales-monitor skill drafted 2026-08-15 — recurring industrial sales/transfer digest into a Notion comps database; scope ratified, pilot build not yet started"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8d81172d-418c-4581-9f86-f4150895dff7
  modified: 2026-08-15T23:02:18.185Z
---

Gabriel asked (2026-08-15) for a way to track ALL industrial sales <150,000 SF
recorded weekly/month in ORA's target-market counties — distinct from
[[county-parcel-screen]]'s off-market owner-outreach screen. Built as a new
sibling skill, `county-sales-monitor` (v0.2 DRAFT, opus-drafted at Gabriel's
request for "high intelligence model"), at
`~/.claude/skills/county-sales-monitor/SKILL.md`. It imports
county-parcel-screen's `references/county-endpoints.v1.json` +
`county-endpoints.md` read-only rather than forking endpoint state.

Gabriel ratified four scope decisions the same day:
- **Cadence: monthly** (30-day trailing window), not weekly — recording lag
  makes a 7-day window too thin to trust.
- **Delivery: Notion database**, not a workbook — comps accumulate row-over-row
  and become queryable, rather than resetting each run. Exact placement
  (proposed: new `County Sales Comps` DB under Knowledge Base parent
  `3386ecd8`) still needs Gabriel's confirmation before `notion-create-database`
  is called for real.
- **Launch scope: Tier A only** — Franklin OH, Baltimore Co MD, Polk IA are the
  only counties with CONFIRMED live sale-date/price fields (validated by
  county-parcel-screen's `market-status.md`). The other ~13 documented counties
  (Tier B, provisional) and 3 structurally-impossible ones (Tier C: Warren OH,
  Johnson Co KS + Platte Co MO non-disclosure states, Kent MI) are a later
  expansion pass, not built in v0.2.
- **Louisville / Jefferson Co KY: deferred** — no discovered endpoints yet;
  adding it means running county-parcel-screen's Step 1 discovery first,
  which is separate work. Don't let it block the 9 existing clusters.

Three questions remain genuinely open (see the skill's own "Open before this
is buildable" section): first-run lookback depth for the Tier A pilot
(recommended: 12 months), KC cluster handling once Tier B expansion reaches it
(non-disclosure state = no price, ever — deferred, not urgent), and whether
validated comps should ALSO flow into `markets.md` automatically or stay
Notion-only until promoted by hand (recommended: Notion-only for now).

**Why:** this exists to answer "what's actually trading" as market awareness/
comp accumulation — it never scores, ranks, or initiates outreach, which is
what keeps it from duplicating or fighting county-parcel-screen's triggering.

**UPDATE 2026-08-15 (same day): pilot run EXECUTED, not just spec'd.** Gabriel
ratified the remaining 4 open questions (Notion DB under Knowledge Base
`3386ecd8` confirmed; 12-month first-run lookback; Notion-only persistence, no
auto-flow to markets.md; build the pilot directly rather than skill-creator's
eval loop). Live Notion database created: `County Sales Comps`,
https://app.notion.com/p/311cf71222d14a56aa33da354cb3a1ea, data source
`63a5e6b3-2655-4e0c-9843-3102d78adc0d`. Three parallel agents pulled the 3 Tier
A counties for the 2025-08-15→2026-08-15 window: **304 transactions written**
(Franklin OH 179, Polk IA 80, Baltimore Co MD 45), zero endpoint drift, but all
three independently found real UNDOCUMENTED fields in county-parcel-screen's
`county-endpoints.md` (Franklin's usable validity signal is the transfer
file's `IsValid`, not the null-populated GIS `VALID`; Polk's `quality` DOR
validity column; Baltimore's `CONVEY1=4` code driving ~half its "transfers").
None of that was patched into county-parcel-screen — flagged for Gabriel to
decide, since it's a shared/actively-used skill file. Full pilot detail lives
in the skill's own v0.4 changelog entry — read there, not here, before acting.

**How to apply:** the skill is no longer purely speculative — it has a proven
first pull with real numbers. Remaining decisions as of this update: whether
to patch county-endpoints.md with the 3 discovered fields, whether to send an
email digest of this pilot to ggoldberg@oxfordra.net, and whether to register
it as a recurring monthly task via [[register-scheduled-task]] now that the
pilot succeeded (deliberately NOT done automatically — Step 9 of the skill
excludes scheduling from its own scope on purpose).
