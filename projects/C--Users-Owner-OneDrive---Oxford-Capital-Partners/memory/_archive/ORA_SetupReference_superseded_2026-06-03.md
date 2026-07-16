# ORA Cowork — Setup Reference & Specifications
*Companion to CLAUDE.md. Contains deployment instructions, templates, and the full System Check spec. Not loaded every session — read on demand.*

Last updated: 2026-04-09

────────────────────────────────────────
SECTION A: WEEKLY SELF-AUDIT — FULL SPECIFICATION
────────────────────────────────────────

Triggered by "System Check" or automatically via ora-sunday-maintenance (Sunday 8pm).

PHASE 1 — INFRASTRUCTURE INTEGRITY
- Verify all 6 Cowork Projects exist and are accessible (Acquisitions Pipeline, Portfolio Operations, oxfordra.net, Technology Platform, Personal Portfolio, Legal & Compliance)
- Verify folder structure integrity: OneDrive/ORA/{Acquisitions, Operations, Website, Tech, Personal, Legal, Briefs} all present
- Confirm CLAUDE.md and ORA_SetupReference.md exist in C:\Users\Owner\.claude\ and are current
- Confirm .cowork-instructions.md exists in every project subfolder
- Confirm change-log.md exists in every project subfolder
- Check that /outputs subfolders exist in each project directory
- Flag any orphaned files (files in root that should be in a project subfolder)
- Flag any files violating naming convention (missing ISO date prefix or ORA_ prefix)

PHASE 2 — CONNECTOR & INTEGRATION HEALTH
Test each enabled connector with a lightweight read operation:
  • Outlook: fetch inbox count or most recent subject line
  • Google Calendar: fetch next 3 upcoming events
  • HubSpot: confirm CRM access, count open deals/contacts
  • Notion: confirm workspace access, list recent pages
  • Netlify: confirm site status for oxfordra.net
  • QuickBooks: confirm company connection status
  • Zapier: confirm connection is active
For any connector that fails: log it, explain the likely cause, provide exact re-auth steps.
Check if NEW connectors have become available that would benefit ORA workflows.

PHASE 3 — SKILL & PLUGIN AUDIT
- Verify core ORA skills are installed and triggerable: acquisition-underwriting, re-operations, lease-abstraction, tenant-intelligence, daily-brief, monthly-close, document-assembly, communication-intelligence
- Active plugin packs: finance, legal, data, operations, productivity, pdf-viewer, enterprise-search, cowork-plugin-management
- Check if any custom skills need updating based on changes in ORA's investment criteria, markets, or workflows
- Check if any new Cowork plugins have been released that would benefit ORA workflows
- Test each skill with a dry-run prompt to confirm it loads correctly

PHASE 4 — SCHEDULED TASK VERIFICATION
Confirm all 16 active ora-* tasks are enabled and have fired on schedule:
  Core (12):
  • ora-morning-brief — Weekdays 7:02am
  • ora-email-queue-am — Weekdays 9:01am
  • ora-email-queue-pm — Weekdays 2:01pm
  • ora-eod-wrap — Weekdays 5:06pm
  • ora-site-health — Daily 7:06am
  • ora-monday-sync — Monday 7:39am
  • ora-friday-closeout — Friday 4:05pm
  • ora-sunday-maintenance — Sunday 8:03pm
  • ora-mid-month-ops — 1st and 15th 9am
  • ora-monthly-kickoff — 1st of month 8am
  • ora-quarterly-review — Jan/Apr/Jul/Oct 1st 10am
  • ora-covenant-watch — 1st of month 9:30am
  Supplemental (4):
  • daily-deal-screening — Weekdays 6am
  • ora-qb-export-watcher — Daily 8:46am
  • ora-catchup-monitor — Every 30 minutes
  • ora-fulton-deadline-alert — Weekdays 7:57am (TEMPORARY)
For each: check last execution timestamp and expected output. If not fired, diagnose and log the gap.

PHASE 5 — CONTEXT FRESHNESS & DRIFT DETECTION
- Review CLAUDE.md: does it still reflect Ze's current tools, priorities, and working style? Flag anything stale.
- Review each .cowork-instructions.md: flag outdated status fields, closed deals, changed contacts.
- Scan change-log.md files: flag any project with zero activity in 14+ days as potentially dormant.
- Check if new active deals, tenants, or priorities have emerged that are NOT yet in context files.

PHASE 6 — PRODUCTIVITY OPTIMIZATION
- Review last 7 days of task history: identify 3 most token-heavy task patterns
- For each: propose a more efficient approach (new skill, batched workflow, better prompt, connector)
- Identify any tasks done manually that could be automated
- Propose ONE new scheduled task, skill, or automation that would save the most time in the coming week

PHASE 7 — OUTPUT REPORT
Generate report saved to OneDrive/ORA/Briefs/YYYY-MM-DD_SystemCheck.md:

  # ORA Cowork System Check — [Date]
  ## Status: [GREEN / YELLOW / RED]
  ## Infrastructure: [✅ / ⚠️ / ❌]
  ## Connectors: [✅ / ⚠️ / ❌] — [X/Y operational]
  ## Skills & Plugins: [✅ / ⚠️ / ❌]
  ## Scheduled Tasks: [✅ / ⚠️ / ❌] — [X/Y firing on schedule]
  ## Context Freshness: [✅ / ⚠️ / ❌]
  ## Optimization Recommendations
  ## Action Items for Ze
  ## Action Items for Claude (Auto-Execute)

Auto-execute all "Action Items for Claude" that don't require Ze's approval. Present report with summary of auto-fixes and items requiring manual action.

────────────────────────────────────────
SECTION B: PROJECT-LEVEL FOLDER TEMPLATES
────────────────────────────────────────

## Template: Acquisition Project (.cowork-instructions.md)

# Project: [Property Name] Acquisition
**Status:** [Pipeline / LOI / PSA / Due Diligence / Closing]
**Address:** [Full address]
**SF:** [Total SF] | **Buildings:** [Count] | **Ask:** $[Amount]
**Seller:** [Name/Entity] | **Broker:** [Name/Firm]
**Transaction Counsel:** Philip Collins
**Key Dates:** [LOI expiry, inspection period end, closing target]

## Active Tasks
- [ ] [Current task 1]
- [ ] [Current task 2]

## Key Contacts
| Role | Name | Email | Phone |
|------|------|-------|-------|

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|

## File Naming
All files: ORA_[DocType]_[PropertyShortName]_v[X.Y].[ext]

---

## Template: Operations (.cowork-instructions.md)

# Project: Portfolio Operations
**Scope:** Monthly accounting, tenant management, lease administration
**PM Systems:** Yardi, AppFolio, Rent Manager, QuickBooks
**Tenant Count:** ~140 across 4 markets

## Current Month Focus
- [ ] Payment Dashboard completion (due 1st)
- [ ] QuickBooks journal entries (11 properties)
- [ ] Reconciliations
- [ ] HubSpot escalations and lease expiration tracking

## Recurring Cadence
- Monthly: All Payment Dashboard items
- Quarterly (Jan/Apr/Jul/Oct): Asset Management Fees, CAM accruals
- Annual: COI audits, budget reforecasts, rent roll reconciliation

---

## Template: Website / Technology (.cowork-instructions.md)

# Project: oxfordra.net Redesign & Tech Platform
**Stack:** Static HTML/CSS/vanilla JS on Netlify
**Design System:** See ORA_DesignDirection_MasterPrompt.md v2.1
**Target:** PageSpeed 100/100 mobile + desktop

## Design Tokens
- Display: EB Garamond | UI: DM Sans | Mono: IBM Plex Mono
- Oxford Navy: #1B2A4A | Oxford Gold: #C9A96E | Parchment: #F5F0E8

────────────────────────────────────────
SECTION C: RECOMMENDED COWORK PROJECTS
────────────────────────────────────────

| # | Project Name            | Folder               | Purpose |
|---|-------------------------|----------------------|---------|
| 1 | Acquisitions Pipeline   | ~/ORA/Acquisitions/  | All deal evaluation, LOIs, PSAs, IC memos, due diligence |
| 2 | Portfolio Operations    | ~/ORA/Operations/    | Monthly checklist, tenant comms, lease admin, accounting |
| 3 | oxfordra.net            | ~/ORA/Website/       | Site redesign, performance, analytics, content |
| 4 | Technology Platform     | ~/ORA/Tech/          | Internal platform build, integrations, automation design |
| 5 | Personal Portfolio      | ~/ORA/Personal/      | Roth IRA, HSA, 529, Rarig property, lending, AMCPX migration |
| 6 | Legal & Compliance      | ~/ORA/Legal/         | Leases, estoppels, solar agreements, loan documents |

────────────────────────────────────────
SECTION D: RECOMMENDED CONNECTORS
────────────────────────────────────────

| Connector        | Use Case |
|------------------|----------|
| Outlook          | Tenant communications, broker correspondence, counsel coordination |
| Google Calendar  | Closing deadlines, inspection periods, lease expirations, meeting prep |
| HubSpot          | Tenant CRM, lease expiration pipeline, escalation tracking |
| Notion           | Deal pipeline tracking, knowledge base, SOPs |
| Netlify          | Website deployment, build monitoring |
| Zapier           | Cross-platform automations (QB → HubSpot, email → Notion, etc.) |
| QuickBooks       | Financial reporting, journal entries, reconciliation |
| SharePoint       | Document storage, shared files with counsel and brokers |

────────────────────────────────────────
SECTION E: SCHEDULED TASKS — FULL SPECIFICATIONS
────────────────────────────────────────

16 active recurring tasks (ora-* prefix). Skill files at:
C:\Users\Owner\.claude\scheduled-tasks\

### Core Cadence Tasks (12)

| Task ID               | Schedule                    | Description |
|-----------------------|-----------------------------|-------------|
| ora-morning-brief     | Weekdays 7:02am             | Consolidated morning brief — deadline alerts, calendar, email triage, deal pipeline, CRE news, market pulse, daily priorities |
| ora-email-queue-am    | Weekdays 9:01am             | Email response queue AM — scan Outlook, enrich context from Notion/HubSpot, draft replies, post to Email Response Queue DB |
| ora-email-queue-pm    | Weekdays 2:01pm             | Email response queue PM — same as AM run |
| ora-eod-wrap          | Weekdays 5:06pm             | End-of-day wrap — inbox metrics, Email Response Queue audit, deadline urgency check, tomorrow prep |
| ora-site-health       | Daily 7:06am                | oxfordra.net health check — availability, SSL, Netlify deploy status, PageSpeed, broken link scan |
| ora-monday-sync       | Monday 7:39am               | Portfolio sync — HubSpot→Notion tenant sync, deal pipeline review, lease expiration pipeline, occupancy metrics |
| ora-friday-closeout   | Friday 4:05pm               | Week close-out — pipeline digest, week accomplishments, automation health review, next-week prep |
| ora-sunday-maintenance| Sunday 8:03pm               | Consolidated 5-phase system audit: task verification, connector health, output verification, knowledge extraction, context freshness |
| ora-mid-month-ops     | 1st and 15th 9am            | Module A: delinquency scan (4-stage escalation). Module B: QB Desktop CSV processing. Module C: PM A/R aging |
| ora-monthly-kickoff   | 1st of month 8am            | 31-item Monthly Checklist, COI compliance scan, lease renewal drafts (90-180 day window), prior-month financial review |
| ora-quarterly-review  | Jan/Apr/Jul/Oct 1st 10am    | 7-section review: NOI by market, occupancy/WALT, acquisition pipeline, debt metrics, CapEx vs budget, market research, personal portfolio |
| ora-covenant-watch    | 1st of month 9:30am         | Loan maturity alerts, DSCR covenant monitoring, LTV ceiling check, rate step-up flags, debt summary |

### Supplemental Tasks (4)

| Task ID               | Schedule                    | Description |
|-----------------------|-----------------------------|-------------|
| daily-deal-screening  | Weekdays 6am                | Screen new Crexi/LoopNet deals against ORA acquisition criteria |
| ora-qb-export-watcher | Daily 8:46am                | Check SharePoint QB Exports folder for new files, send Outlook confirmation |
| ora-catchup-monitor   | Every 30 minutes            | Detect scheduled tasks that missed their window while computer was off, and execute them |
| ora-fulton-deadline-alert | Weekdays 7:57am          | E. Fulton Street DD deadline scanner — surfaces items due within 3 business days (TEMPORARY — remove after closing) |

### Retired / One-Time (disabled, safe to delete)

| Task ID                           | Status   | Notes |
|-----------------------------------|----------|-------|
| ora-monthly-kickoff-apr-catchup   | Disabled | Fired 2026-04-08, one-time |
| ora-covenant-watch-apr-catchup    | Disabled | Fired 2026-04-08, one-time |
| ora-quarterly-review-q2-catchup   | Disabled | Fired 2026-04-08, one-time |
| ora-mid-month-ops-apr-catchup     | Disabled | Was erroneously recurring; disabled 2026-04-09 |

────────────────────────────────────────
SECTION F: CUSTOM SKILL TEMPLATES
────────────────────────────────────────

## Skill: Deal Screener

name: deal-screener
description: Screens incoming broker packages and OMs against Oxford Realty Advisors investment criteria.

1. EXTRACT: address, SF, building count, year built, asking price, in-place NOI, occupancy, tenant roster, lease terms, zoning
2. SCREEN against ORA criteria:
   - Sub-50,000 SF per building? (HARD FILTER)
   - Sub-$10M total? (HARD FILTER)
   - Target market (OH, MD, IN, WI, MO, KS, TN)? (HARD FILTER)
   - Shallow-bay industrial or flex? (HARD FILTER)
   - Below replacement cost? (estimate $85-$120/SF depending on market)
   - Value-add opportunity identifiable?
3. CALCULATE: implied cap rate, $/SF, replacement cost ratio, estimated DSCR at 65% LTV
4. OUTPUT one-page screening memo: Go / Further Diligence / Pass with explicit reasoning
5. If GO or FURTHER DILIGENCE: outline top 5 risks and top 5 value drivers

---

## Skill: Lease Abstractor

name: lease-abstractor
description: Extracts and structures key terms from commercial lease documents.

Extract and output as structured markdown:
PARTIES / PREMISES / TERM / RENT / EXPENSES / SECURITY / TENANT IMPROVEMENTS /
ASSIGNMENT-SUBLETTING / DEFAULT / TERMINATION / SPECIAL (ROFR, ROFO, options) /
INSURANCE / ESTOPPEL

Flag unusual, missing, or tenant-favorable terms with ⚠️

---

## Skill: Tenant Communication Drafter

name: tenant-comms
description: Drafts professional tenant communications for Oxford Realty Advisors.

Draft in ORA brand voice:
- Professional, direct, respectful
- Reference specific lease provisions
- Include relevant dates, amounts, deadlines
- Delinquency: escalate tone progressively (reminder → formal notice → demand → legal referral)
- Renewals: lead with value proposition, present terms clearly, include response deadline
- Always specify the correct landlord entity for the property
- Output as both email body text and .docx letter on ORA letterhead

────────────────────────────────────────
SECTION G: DEPLOYMENT CHECKLIST
────────────────────────────────────────

☐ Copy the Global Instructions block into Settings → Cowork → Global Instructions
☐ Create folder structure: OneDrive/ORA/{Acquisitions, Operations, Website, Tech, Personal, Legal, Briefs}
☐ Create Cowork Projects for each workstream (6 total — see Section C)
☐ Place CLAUDE.md and ORA_SetupReference.md in C:\Users\Owner\.claude\
☐ Place .cowork-instructions.md in each project subfolder (customize from Section B templates)
☐ Create change-log.md in each project subfolder (empty, Claude will populate)
☐ Enable all recommended connectors (see Section D)
☐ Verify all 16 ora-* scheduled tasks are active (see Section E)
☐ Confirm active plugin packs: finance, legal, data, operations, productivity, pdf-viewer, enterprise-search, cowork-plugin-management
☐ Run a test task in each project to verify context loading
☐ Run "System Check" manually once to establish baseline report (see Section A)
