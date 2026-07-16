---
name: ar-aging-parser-completion
description: Complete the AR aging import pipeline (feat/ar-aging-parser) — CLI, overlay write, refute pass, gate, PR
---

Complete the AR aging import pipeline for Oxford Realty Advisors. All work goes in the existing worktree at C:\Users\Owner\oxford-command-center\.claude\worktrees\ar-aging-parser on branch feat/ar-aging-parser.

## Context (do not re-implement — already done)
- server/ar/ar-aging.ts — parser core (yardi-aging + appfolio-aged-receivable formats, validated on real exports)
- server/ar/match-tenant.ts — fuzzy tenant→Lease.id matcher (review-then-write, confidence-tiered)
- server/ar/mapping-cache.ts — confirmed-mapping cache (data/ar-mapping-cache.json, gitignored)
- tests/unit/ar-aging.test.ts, tests/unit/match-tenant.test.ts — 24 passing tests

## Remaining work (implement in this order)

### 1. scripts/ar-import.ts — CLI import script
A tsx-runnable script (npx tsx scripts/ar-import.ts <pdf-path>) that does the full review-then-write pipeline:

a) PDF→text extraction: spawn Python subprocess running pdfplumber to extract text page by page. If extraction returns mostly CID garbage (>30% non-ASCII in the first 500 chars), print a clear error: "This PDF has no text layer (image/scanned). Re-export from Yardi/AppFolio as a text PDF." Exit with code 1. Do NOT silently return empty rows.

b) Parse: call parseArAging(text) from server/ar/ar-aging.ts. If format==='unknown' or unsupportedReason is set, print the reason and exit 1.

c) Load leases: GET http://localhost:3000/api/snapshot, extract leases array, map to LeaseLite[] (id, tenantName, company).

d) Load cache: loadCache() from server/ar/mapping-cache.ts.

e) Match + review table: for each ArAgingRow:
   - Check cache first (by cacheKey(row.tenant)) — if hit and not 'SKIP', use cached leaseId directly (print "[cached]")
   - Otherwise run matchTenantToLease(row.tenant, leases)
   - exact/high confidence + not ambiguous → auto-accept (print as "✓ auto")
   - low/none/ambiguous → print the row with proposed match and prompt: "Accept [leaseId: candidate]? (y/n/skip/manual)":
     - y → accept proposed
     - n → re-prompt "Enter leaseId manually:"
     - skip → mark as 'SKIP' (omit from write, cache the skip)
     - manual → prompt for leaseId

f) After review: print a summary table of all confirmed mappings (leaseId, tenant, d30, d60, d90, d90plus).

g) Confirm write: prompt "Write [N] arrears records to overlay? (y/n)". On y:
   - For each confirmed (non-SKIP) mapping: POST http://localhost:3000/api/actions/tenant-arrears with {leaseId, arrears: {d30, d60, d90, d90plus}}
   - On any non-2xx response: print the error and continue (never halt mid-write)
   - Save updated cache via saveCache()
   - Print "Done — [N] records written, [M] skipped, cache saved."

h) Error handling: if server is not running (ECONNREFUSED), print "Start the Command Center server first (npm run dev) and re-run." Exit 1.

### 2. Update server/ar/ar-aging.ts module header comment
Add 'yardi-aging' and 'appfolio-aged-receivable' as the two supported formats (was incorrectly labeled 'rent-manager-aging' in an earlier version — already corrected in the code).

### 3. Tests for the image-PDF detection logic
Add a unit test in tests/unit/ar-aging.test.ts: detectArFormat on a string of >30% CID-style non-ASCII should return 'unknown' with an appropriate unsupportedReason path. (The detection is in the CLI script, not the parser — test the parser's 'unknown' branch which the script delegates to.)

### 4. Mandatory refute-financial-change adversarial pass
Per coding-standards.md (added by PR #79): any financial-attribution code (the overlay write path, the matching logic, the bucket mapping) MUST get a refute-financial-change adversarial pass before the PR opens. Run the skill: /refute-financial-change, targeting:
- server/ar/ar-aging.ts — bucket extraction logic
- server/ar/match-tenant.ts — tenant attribution
- scripts/ar-import.ts — the write path

The refute pass must converge before proceeding to gate.

### 5. Full gate
Run: npm run gate (from the worktree root)
Fix any failures. Do NOT bypass with --no-verify.

### 6. Open PR
gh pr create --base main --head feat/ar-aging-parser with title:
"feat(ar): AR-aging import pipeline — collections data feed (audit Fix #2)"

PR body should cover:
- What: a CLI tool (scripts/ar-import.ts) that parses Yardi + AppFolio AR-aging PDFs, fuzzy-matches tenant names to Lease.ids with human review for low-confidence rows, caches confirmed mappings, and writes TenantArrears to the overlay via the existing POST /api/actions/tenant-arrears route
- Why: activates the dormant collections/AR-aging alert from audit Fix #2 — the alert was built but had no data feed
- Formats supported: yardi-aging (29000 + 9050), appfolio-aged-receivable (Northwood); rent-manager-delinquency (Sepich) detected and rejected with clear guidance
- Image-only PDFs: detected and rejected with clear guidance (9050 current export is image-only)
- Tests: 24 existing + any new tests
- Gate: green at all steps
- Deferred: Sepich charge-date aging format (no buckets in current export), automated QB feed

## Routing
Email a completion summary to ggoldberg@oxfordra.net via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 when done.
