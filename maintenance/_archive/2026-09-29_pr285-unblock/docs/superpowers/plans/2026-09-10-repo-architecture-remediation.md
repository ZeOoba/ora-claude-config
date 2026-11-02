# Cross-Repo Architecture Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the nine findings (OI-254 … OI-262) from the 2026-09-10 cross-repo architecture-diagram review, so that every financial-decision code path carries a mechanical gate, every mirror either self-heals or is deleted, and no documented access path is dead.

**Architecture:** Six independent workstreams, one per subsystem. Each is separately shippable and separately reviewable — **there is no cross-workstream dependency anywhere in this plan**, so they can run in any order or in parallel across sessions. Within a workstream, tasks are ordered. Nothing here changes application behaviour except Workstream D (one model id); everything else adds gates, schedules, or documentation.

**Tech Stack:** TypeScript/Node 22-24 (ora-pm, oxford-command-center, Website), Python 3.13 + stdlib + `jsonschema` (AAOS, `~/.claude` maintenance), GitHub Actions, Cloudflare Pages, Netlify, Windows Task Scheduler, the ORA CC/MCP scheduled-task fleet.

## Global Constraints

Every task's requirements implicitly include this section.

- **Hard Invariant 2 — oxfordra.net.** No build, edit, or deploy of `website-canonical` / `oxford-site` / live Netlify without Gabriel's explicit per-deploy confirmation. Previews are the default; production is always a separate in-turn ask. Workstream D is written to obey this — it reaches production only at an explicit gate.
- **Hard Invariant 4 — governor constants.** No task in this plan may change DSCR 1.25, LTV 40% aggregate / 65% per-property, or any scorecard weight. Nothing here should touch one; if a task appears to, stop and ask.
- **Hard Invariant 6 — never delete.** Move to `/archive/`. Never overwrite a config (`settings.json`, `CLAUDE.md`, hooks) without reading it first.
- **Scheduled tasks: `register-scheduled-task` is the SOLE path.** Register/update/retire only via the supervised `create_scheduled_task` / `update_scheduled_task` MCP tools on the target surface. **Never splice registry JSON** (proven-harmful 2026-06-09). Before registering anything, check `~/.claude/maintenance/_state/registry-membership.log` for concurrent activity you did not generate.
- **Shared single-writer checkouts.** `~/.claude`, `ora-skills`, `website-canonical`, `oxford-command-center` are edited from multiple concurrent sessions. Before editing any of them: `git fetch origin` + `git status -sb`, and claim via `python ~/.claude/hooks/lib/claim_work.py claim <slug> "<why>" --paths <files>`. Stage explicit paths, never `git add -A` or `git commit -a`.
- **Email routing canon.** Any automated mail this plan creates goes to `ggoldberg@oxfordra.net` ONLY, via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Outlook COM is the sole automated send path). No cc. No other recipient.
- **Engineering OS done-bar.** Tasks A2 and B1 touch financial-gate code; both require the mandatory adversarial REFUTE pass before landing, reviewer model ≥ implementer, never below Fable for financial/governor code. Pin an explicit `model` per dispatch.
- **Event log.** Any append to `event_log.md` goes through `python ~/.claude/maintenance/append-event-log.py` ONLY — never an Edit against the header anchor.
- **OI ids.** These nine already exist (OI-254…OI-262). If a task surfaces a NEW finding, allocate with `python ~/.claude/maintenance/allocate-oi-id.py --session $CLAUDE_CODE_SESSION_ID --note "<why>"` — never hand-compute max+1.
- **Commit trailer.** End every commit message with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## File Structure

| Workstream | Repo | Files created | Files modified |
|---|---|---|---|
| A | `ora-pm` | `eslint.config.js`, `scripts/check-refute-required.ts`, `tests/scripts/check-refute-required.test.ts` | `package.json`, `.github/workflows/ci.yml`, `README.md` |
| B | `~/.claude`, `oxford-command-center` | `~/.claude/scheduled-tasks/ora-occ-full-gate/SKILL.md` | `oxford-command-center/.github/workflows/full-gate-selfhosted.yml` (comment only) |
| C | `AAOS`, `~/.claude` | `AAOS/requirements.txt`, `AAOS/.github/workflows/ci.yml` | `~/.claude/scheduled-tasks/ora-aaos-publish-contracts/SKILL.md` |
| D | `website-canonical` | — | `netlify/edge-functions/chat.ts` |
| E | `~/.claude`, `ora-skills` | `~/.claude/scheduled-tasks/ora-skills-mirror-republish/SKILL.md` | `ora-skills/README.md`, `~/.claude/README.md`, `ora-skills/register-scheduled-task/SKILL.md` |
| F | `oxford-command-center` | — | `README.md` + whichever docs name the subdomain |

Design notes locking in decomposition:

- **A2's `check-refute-required.ts` is a port, not a rewrite.** `oxford-command-center/scripts/check-refute-required.ts` is 171 lines and already correctly structured: pure exported predicates (`isFinancialSourcePath`, `hasRefuteApproval`), a `git()` helper, and a `main()` behind an executed-directly guard so the predicates unit-test without `process.exit` side effects. Copy that shape; replace only the path predicate. Do not redesign it.
- **B1 is a scheduled-task spec, not code.** The whole deliverable is one `SKILL.md` plus one supervised registration call. Nothing is built.
- **C1 and C2 are split** because C1 is a repo change reviewable on its own (a PR against AAOS) and C2 is a fleet-registry change on a different surface with a different blast radius. A reviewer could reasonably approve one and reject the other.

---

## Workstream A — ora-pm gate hardening (OI-255, OI-261)

Closes the estate's worst risk asymmetry: the only repo that debits bank accounts has the weakest gate.

### Task A1: Add a real linter to ora-pm

**Files:**
- Create: `C:\Users\Owner\ora-pm\eslint.config.js`
- Modify: `C:\Users\Owner\ora-pm\package.json` (scripts block), `C:\Users\Owner\ora-pm\.github\workflows\ci.yml`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: an `npm run lint` that actually lints, and a CI step named `Lint` between `Type check` and `Run tests`. Task A2 adds a separate CI job and does not depend on this one.

Context an implementer needs: ora-pm is ESM (`"type": "module"` in `package.json`), TypeScript 5.6, and has **no ESLint of any kind installed** — `"lint": "tsc --noEmit"` is an alias for `typecheck`, so today the CI "lint" concept does not exist. `oxford-command-center` runs `eslint . --max-warnings 0`; match that strictness.

- [ ] **Step 1: Install ESLint and the TypeScript plugin**

```bash
cd C:/Users/Owner/ora-pm
npm install --save-dev eslint@^9 @eslint/js@^9 typescript-eslint@^8 globals@^15
```

- [ ] **Step 2: Create the flat config**

Create `C:\Users\Owner\ora-pm\eslint.config.js`:

```javascript
// Flat config (ESLint 9). Deliberately narrow: this repo had NO linter until 2026-09-10
// (OI-255), so a maximalist ruleset would produce hundreds of pre-existing violations and
// get switched off. Start at recommended + the rules that catch the failure classes this
// repo has actually hit, and tighten later.
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: ['dist/**', '.wrangler/**', 'node_modules/**', 'coverage/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      // A floating promise in a Worker route silently drops the operation and returns 200.
      '@typescript-eslint/no-floating-promises': 'off', // needs type-aware linting; see Task A1 note
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      'no-console': 'off', // cron routes log deliberately
    },
  },
);
```

Note on `no-floating-promises`: it requires type-aware linting (`parserOptions.project`), which materially slows the run and needs its own tsconfig wiring. It is left off here on purpose rather than half-configured. Enabling it is a good follow-up, not part of this task.

- [ ] **Step 3: Point `lint` at ESLint and run it**

In `C:\Users\Owner\ora-pm\package.json`, replace the `lint` line:

```json
    "lint": "eslint . --max-warnings 0",
```

Run: `cd C:/Users/Owner/ora-pm && npm run lint`
Expected: either clean, or a finite list of real violations.

- [ ] **Step 4: Fix or explicitly silence every violation**

Fix real ones. For anything pre-existing that is genuinely fine, add a scoped `// eslint-disable-next-line <rule> -- <why>` with a reason — never a blanket file-level disable, and never by loosening the rule globally.

Re-run: `npm run lint`
Expected: exits 0, no output.

- [ ] **Step 5: Wire it into CI**

In `C:\Users\Owner\ora-pm\.github\workflows\ci.yml`, insert between the `Type check` and `Run tests` steps:

```yaml
      - name: Lint
        run: npm run lint
```

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Owner/ora-pm
git add eslint.config.js package.json package-lock.json .github/workflows/ci.yml
git commit -m "chore(ci): add real ESLint to ora-pm and gate CI on it (OI-255)

lint was an alias for tsc --noEmit; the repo had no linter at all. Flat
config at recommended + typescript-eslint recommended, --max-warnings 0,
matching oxford-command-center's strictness.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task A2: Port the refute gate to ora-pm and block deploys on it

**Files:**
- Create: `C:\Users\Owner\ora-pm\scripts\check-refute-required.ts`, `C:\Users\Owner\ora-pm\tests\scripts\check-refute-required.test.ts`
- Modify: `C:\Users\Owner\ora-pm\package.json`, `C:\Users\Owner\ora-pm\.github\workflows\ci.yml`
- Read first (do not modify): `C:\Users\Owner\oxford-command-center\scripts\check-refute-required.ts`

**Interfaces:**
- Consumes: nothing from Task A1.
- Produces: `export function isFinancialSourcePath(p: string): boolean` and `export function hasRefuteApproval(messageBlob: string): boolean`, plus an `npm run check:refute` accepting `--strict` and `--base=<ref>`. Nothing later in this plan consumes them.

**This task touches a financial gate — it requires the mandatory adversarial REFUTE pass before landing (Global Constraints), reviewer model never below Fable.**

- [ ] **Step 1: Write the failing test**

Create `C:\Users\Owner\ora-pm\tests\scripts\check-refute-required.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { isFinancialSourcePath, hasRefuteApproval } from '../../scripts/check-refute-required';

describe('isFinancialSourcePath', () => {
  it('flags the money-moving paths', () => {
    expect(isFinancialSourcePath('server/lib/billing.ts')).toBe(true);
    expect(isFinancialSourcePath('server/routes/cron.ts')).toBe(true);
    expect(isFinancialSourcePath('server/routes/stripe.ts')).toBe(true);
    expect(isFinancialSourcePath('server/lib/cam.ts')).toBe(true);
    expect(isFinancialSourcePath('server/lib/ar-aging.ts')).toBe(true);
    expect(isFinancialSourcePath('server/lib/iif-export.ts')).toBe(true);
    expect(isFinancialSourcePath('server/lib/stripe-events.ts')).toBe(true);
    expect(isFinancialSourcePath('server/routes/payments.ts')).toBe(true);
    expect(isFinancialSourcePath('server/routes/charges.ts')).toBe(true);
    expect(isFinancialSourcePath('server/routes/webhook.ts')).toBe(true);
  });

  it('does not flag UI, tests, or non-financial routes', () => {
    expect(isFinancialSourcePath('src/pages/billing/BillingPage.tsx')).toBe(false);
    expect(isFinancialSourcePath('tests/lib/billing.test.ts')).toBe(false);
    expect(isFinancialSourcePath('server/routes/properties.ts')).toBe(false);
    expect(isFinancialSourcePath('README.md')).toBe(false);
  });

  it('normalises Windows path separators', () => {
    expect(isFinancialSourcePath('server\\lib\\billing.ts')).toBe(true);
  });
});

describe('hasRefuteApproval', () => {
  it('accepts either trailer, case-insensitively, only at line start', () => {
    expect(hasRefuteApproval('feat: x\n\nRefute-Reviewed: wf_abc123\n')).toBe(true);
    expect(hasRefuteApproval('fix: y\n\nrefute-skip: docs-only change\n')).toBe(true);
  });

  it('rejects a commit with no trailer', () => {
    expect(hasRefuteApproval('feat: change billing math\n\nNo attestation here.\n')).toBe(false);
  });

  it('does not match the phrase mid-sentence', () => {
    expect(hasRefuteApproval('mentions Refute-Reviewed: inline, not as a trailer')).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:/Users/Owner/ora-pm && npx vitest run tests/scripts/check-refute-required.test.ts`
Expected: FAIL — `Failed to resolve import "../../scripts/check-refute-required"`.

- [ ] **Step 3: Write the implementation**

Create `C:\Users\Owner\ora-pm\scripts\check-refute-required.ts`:

```typescript
// scripts/check-refute-required.ts
//
// Ported from oxford-command-center/scripts/check-refute-required.ts (OI-255). ora-pm is the
// only ORA repo that debits real bank accounts, and until 2026-09-10 it had no gate forcing an
// adversarial pass on the code that does it. This turns the Engineering-OS done-bar into a
// mechanical check.
//
// Default mode WARNS and exits 0 (local dev — never blocks WIP). `--strict` EXITS 1 on a
// violation (wired into CI for PRs). Fails OPEN on any git/tooling gap.
//
// Usage: tsx scripts/check-refute-required.ts [--strict] [--base=<ref>]
//   base defaults to $REFUTE_BASE, else 'origin/main'.
//
// Exported functions are pure (no I/O) so they unit-test without the process.exit side effects —
// the bottom-of-file guard runs main() only when executed directly.
import { execFileSync } from 'node:child_process';

// Enumerated, not prefix-matched. `server/` is mostly CRUD plumbing; enumerating keeps the gate
// credible (a gate that fires on every PR gets bypassed). Each entry is a file that either moves
// money, decides an amount, or produces an accounting artifact:
//   billing.ts        generates the monthly charge set
//   cron.ts           fires ACH autopay debits and posts late fees; carries AUTOPAY_BATCH_LIMIT
//   stripe.ts         creates PaymentIntents (the actual debit)
//   stripe-events.ts  interprets webhook state into ledger truth
//   webhook.ts        the ingestion boundary for those events
//   payments.ts       records payments against the ledger
//   charges.ts        the charge ledger itself
//   cam.ts            pro-rata CAM true-up math
//   ar-aging.ts       AR bucket derivation, which delinquency decisions read
//   iif-export.ts     the QuickBooks IIF artifact that reaches the books
export const FINANCIAL_SOURCE_PATHS: ReadonlySet<string> = new Set([
  'server/lib/billing.ts',
  'server/lib/cam.ts',
  'server/lib/ar-aging.ts',
  'server/lib/iif-export.ts',
  'server/lib/stripe.ts',
  'server/lib/stripe-events.ts',
  'server/routes/cron.ts',
  'server/routes/stripe.ts',
  'server/routes/webhook.ts',
  'server/routes/payments.ts',
  'server/routes/charges.ts',
]);

/** True when the path is financial-decision source requiring a refute attestation. */
export function isFinancialSourcePath(p: string): boolean {
  return FINANCIAL_SOURCE_PATHS.has(p.replace(/\\/g, '/'));
}

/** True when a refute attestation trailer appears anywhere in the commit-message blob. */
export function hasRefuteApproval(messageBlob: string): boolean {
  return /(^|\n)\s*Refute-(Reviewed|Skip):/i.test(messageBlob);
}

function git(args: string[]): string {
  return execFileSync('git', args, { encoding: 'utf8' });
}

function main(): void {
  const argv = process.argv.slice(2);
  const strict = argv.includes('--strict');
  const base =
    argv.find((a) => a.startsWith('--base='))?.slice('--base='.length) ??
    process.env.REFUTE_BASE ??
    'origin/main';

  let changed: string[];
  let messageBlob: string;
  try {
    changed = git(['diff', '--name-only', `${base}...HEAD`]).split('\n').map((s) => s.trim()).filter(Boolean);
    messageBlob = git(['log', `${base}..HEAD`, '--format=%B']);
  } catch (err) {
    // No usable base ref (shallow clone, detached HEAD, fresh repo) — never block on a tooling gap.
    console.warn(`check:refute — skipped: could not diff against '${base}' (${(err as Error).message.split('\n')[0]}).`);
    return;
  }

  const financial = changed.filter(isFinancialSourcePath);
  if (financial.length === 0) {
    console.log('check:refute — OK: no financial-decision source files changed in this range.');
    return;
  }
  if (hasRefuteApproval(messageBlob)) {
    console.log(`check:refute — OK: ${financial.length} financial file(s) changed; a Refute-Reviewed/Skip trailer is present.`);
    return;
  }

  const msg = [
    `check:refute — ${financial.length} financial-decision source file(s) changed WITHOUT a refute attestation:`,
    ...financial.map((f) => `    ${f}`),
    '',
    'Run an adversarial REFUTE pass on the change, then add a commit trailer:',
    '    Refute-Reviewed: <reviewer/run ref>        (or, with justification)  Refute-Skip: <reason>',
    `(checked range: ${base}..HEAD)`,
  ].join('\n');

  if (strict) {
    console.error(msg);
    process.exit(1);
  }
  console.warn(msg);
}

if (process.argv[1] && process.argv[1].replace(/\\/g, '/').endsWith('check-refute-required.ts')) {
  main();
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:/Users/Owner/ora-pm && npx vitest run tests/scripts/check-refute-required.test.ts`
Expected: PASS — 5 tests.

- [ ] **Step 5: Verify the enumerated path list against reality**

The enumerated set is only correct if those files exist and no other file in `server/` moves money. Run:

```bash
cd C:/Users/Owner/ora-pm
for f in server/lib/billing.ts server/lib/cam.ts server/lib/ar-aging.ts server/lib/iif-export.ts server/lib/stripe.ts server/lib/stripe-events.ts server/routes/cron.ts server/routes/stripe.ts server/routes/webhook.ts server/routes/payments.ts server/routes/charges.ts; do [ -f "$f" ] || echo "MISSING: $f"; done
grep -rln "stripe\.\|paymentIntent\|amount\b" server/ --include="*.ts" | grep -v -F -f <(printf '%s\n' server/lib/billing.ts server/lib/cam.ts server/lib/ar-aging.ts server/lib/iif-export.ts server/lib/stripe.ts server/lib/stripe-events.ts server/routes/cron.ts server/routes/stripe.ts server/routes/webhook.ts server/routes/payments.ts server/routes/charges.ts)
```

Expected: no `MISSING:` lines. The second command lists candidates NOT in the set — review each and either add it to `FINANCIAL_SOURCE_PATHS` with a one-line reason comment, or leave it out deliberately. Record the decision in the commit body.

- [ ] **Step 6: Add the npm script**

In `C:\Users\Owner\ora-pm\package.json` scripts block, add:

```json
    "check:refute": "tsx scripts/check-refute-required.ts",
```

Run: `cd C:/Users/Owner/ora-pm && npm run check:refute`
Expected: `check:refute — OK: no financial-decision source files changed in this range.` (or a warning naming this task's own files, which is correct behaviour).

- [ ] **Step 7: Add the CI job and make the deploy depend on it**

In `C:\Users\Owner\ora-pm\.github\workflows\ci.yml`, add a second job at the same level as `ci:`:

```yaml
  # A change to money-moving source (billing math, ACH autopay, late fees, CAM true-up, the
  # QuickBooks export) must carry a `Refute-Reviewed:`/`Refute-Skip:` commit trailer attesting
  # an adversarial pass ran on it. Separate job → its own check; make it REQUIRED via branch
  # protection to hard-enforce. PR-only — it needs a base ref to diff.
  refute-required:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: git fetch --no-tags origin "${{ github.base_ref }}"
      - run: npm run check:refute -- --strict --base="origin/${{ github.base_ref }}"
```

- [ ] **Step 8: Commit**

```bash
cd C:/Users/Owner/ora-pm
git add scripts/check-refute-required.ts tests/scripts/check-refute-required.test.ts package.json .github/workflows/ci.yml
git commit -m "feat(ci): require a refute attestation on ora-pm financial source (OI-255)

Ports oxford-command-center's check-refute-required.ts. ora-pm is the only
repo that debits real bank accounts and had no equivalent gate. Enumerated
11 financial paths (see FINANCIAL_SOURCE_PATHS comment for the per-file
reason); PR-only strict job.

Refute-Skip: gate tooling; changes no financial math

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 9: Make it a required check (manual, Gabriel)**

The job runs but does not block until branch protection requires it. On GitHub: `ZeOoba/ora-pm` → Settings → Branches → `main` → Require status checks → add `refute-required`. **This is Gabriel's call, not an agent action** — flag it and stop.

---

### Task A3: Document the CRON_SECRET rotation (OI-261)

**Files:**
- Modify: `C:\Users\Owner\ora-pm\README.md`

**Interfaces:** none. Documentation only, no code.

- [ ] **Step 1: Re-verify all four locations still exist**

```bash
cd C:/Users/Owner/ora-pm
grep -rn "ORA_PM_CRON_SECRET\|CRON_SECRET" scripts/trigger-billing.ps1 .github/workflows/monthly-billing-backup.yml
ls -la C:/Users/Owner/ora-pm-cron/cron-secret.txt
```

Expected: the env-var read in `trigger-billing.ps1`, the repo-secret reference in the backup workflow, and the plaintext file present. If any has moved, correct the runbook below to match what you actually find — do not copy this list blind.

- [ ] **Step 2: Add the runbook to the README**

Insert immediately after the existing "Adding a new admin (OI-036)" paragraph in `C:\Users\Owner\ora-pm\README.md`:

```markdown
**Rotating `CRON_SECRET` (OI-261):** the secret exists in **four** places and a partial rotation
fails silently — the server returns 401 to a caller nobody is watching, and the symptom surfaces
later as a billing run that did not happen. Change them in this order so the old value keeps
working until every caller is updated:

1. `$env:ORA_PM_CRON_SECRET` (machine env var) — read by `scripts/trigger-billing.ps1` for the
   `ora-pm-monthly-billing` fleet task.
2. `C:\Users\Owner\ora-pm-cron\cron-secret.txt` (plaintext file) — read by `ping-crons.ps1` for
   the `ora-pm-daily-crons` fleet task.
3. GitHub repo secret `ORA_PM_CRON_SECRET` (`ZeOoba/ora-pm` → Settings → Secrets) — used by
   `.github/workflows/monthly-billing-backup.yml`.
4. **Last:** the Cloudflare Pages secret — `wrangler pages secret put CRON_SECRET`. This is the
   validating side; changing it first breaks all three callers until they catch up.

After rotating, confirm each path independently rather than waiting for the next scheduled fire:
run `scripts/trigger-billing.ps1` and `ping-crons.ps1` by hand and check for a non-401 response,
and re-run the backup workflow via `workflow_dispatch`.
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Owner/ora-pm
git add README.md
git commit -m "docs: add CRON_SECRET four-location rotation runbook (OI-261)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Workstream B — Command Center financial gate and ops (OI-254, OI-258)

### Task B1: Register a fleet task that runs the full gate

**Files:**
- Create: `C:\Users\Owner\.claude\scheduled-tasks\ora-occ-full-gate\SKILL.md`
- Modify: `C:\Users\Owner\oxford-command-center\.github\workflows\full-gate-selfhosted.yml` (header comment only)

**Interfaces:**
- Consumes: nothing.
- Produces: a registered CC/MCP fleet task id `ora-occ-full-gate`. Nothing later depends on it.

Why a fleet task and not the runner: `full-gate-selfhosted.yml` needs `runs-on: [self-hosted, linux, ora-data]`, and `gh api repos/ZeOoba/oxford-command-center/actions/runners` returns `total_count: 0`. Provisioning, hardening and maintaining a self-hosted runner with the confidential data corpus mounted is a much larger decision than restoring the check. The laptop already has the workbook and the 32 Property Financials files mounted; run it there.

- [ ] **Step 1: Confirm the gate actually passes right now**

Before scheduling anything, establish the baseline. A recurring task that starts red on day one is noise.

```bash
cd C:/Users/Owner/oxford-command-center
git fetch origin && git status -sb
npm run gate
```

Expected: exit 0. **If it fails, STOP** — you have found a live defect, not a scheduling gap. Allocate a new OI id for it and report before continuing; scheduling a failing gate is not the deliverable.

- [ ] **Step 2: Check for concurrent registry activity**

```bash
tail -5 C:/Users/Owner/.claude/maintenance/_state/registry-membership.log
```

Expected: nothing in the last few minutes that you did not generate. If another session is mid-registration, stop and reconcile ownership first (session-context single-writer rule).

- [ ] **Step 3: Write the task spec**

Create `C:\Users\Owner\.claude\scheduled-tasks\ora-occ-full-gate\SKILL.md`:

```markdown
---
name: ora-occ-full-gate
description: Oxford Command Center full-gate runner (CC/MCP fleet, filesystem tool) — runs `npm run gate` in the canonical oxford-command-center checkout, which is the ONLY thing that executes reconcile:noi-crosscheck (Spine A vs Spine B NOI), reconcile, warehouse:verify and warehouse:drift. gate:ci cannot run these (GitHub runners have no Master Workbook or warehouse DB) and the intended self-hosted runner was never provisioned — see open-items-tracker.md#OI-254. Silent on success; emails ggoldberg only on failure. Weekly, Monday 07:40 ET. v1.0 (2026-09-10)
---

Run the Oxford Command Center full gate.

Step 1 — make the checkout current. The canonical checkout has no auto-update mechanism
(open-items-tracker.md#OI-183), so a stale tree would gate against stale logic:

    cd C:\Users\Owner\oxford-command-center
    git fetch origin
    git status -sb

If the checkout is behind `origin/main` AND the working tree is clean, fast-forward it
(`git merge --ff-only origin/main`). **If the working tree is dirty, do NOT stash, reset, or
force anything** — Gabriel co-develops this tree and other sessions write to it. Run the gate
against the tree as-is and say so in the failure email if it fails.

Step 2 — run the gate:

    npm run gate

Guard conditions — read the exit code before doing anything else:
- Exit 0: normal. Do NOT email, do NOT post anywhere. A clean gate is silent.
- Non-zero: send exactly one email via
  `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to
  ggoldberg@oxfordra.net ONLY — subject "OCC full gate FAILED", body = the failing step's name
  plus its stderr verbatim (quote it exactly; do not summarise or interpret). Include the
  `git status -sb` line from Step 1 so the reader knows whether the tree was dirty.
- Do NOT retry a failed gate. Unlike a network publish, a gate failure is a real signal — a
  retry either wastes ~4 minutes reproducing it or masks a flake that itself needs reporting.
- Do nothing else: no code changes, no commits, no registry changes, no other files touched.
  This task diagnoses; it never fixes.

Why this exists: `reconcile:noi-crosscheck` compares `Property.noi` (Spine A, workbook formula
cell) against the warehouse ledger NOI (Spine B, Σ revenue + recovery − opex). CLAUDE.md §1 names
the absence of reconciliation between the two spines as the repo's "one critical defect." Before
this task, that cross-check ran only when a human typed it.
```

- [ ] **Step 4: Register it via the supervised tool**

**Never splice the registry JSON.** Use `register-scheduled-task`'s path — the `create_scheduled_task` MCP tool on the CC/MCP surface, with id `ora-occ-full-gate` and cron `40 7 * * 1` (Monday 07:40 ET). Confirm no id collision on either fleet first, and confirm the 07:40 Monday slot is free per `~/.claude/maintenance/_state/fleet-roster.md`.

- [ ] **Step 5: Verify registration and fire once**

```bash
python C:/Users/Owner/.claude/maintenance/fleet-status.py --summary
```

Expected: `ora-occ-full-gate` present, enabled, on the CC/MCP fleet, with the expected cron. Then trigger one manual run and confirm it exits silently on a green gate.

- [ ] **Step 6: Correct the misleading comment in the dead workflow**

In `C:\Users\Owner\oxford-command-center\.github\workflows\full-gate-selfhosted.yml`, replace the header lines that say a schedule will be added after burn-in:

```yaml
# workflow_dispatch ONLY. NOTE (2026-09-10, OI-254): the self-hosted runner this targets has
# never been provisioned — `gh api repos/ZeOoba/oxford-command-center/actions/runners` returns
# total_count 0, and this workflow has zero runs. It will queue forever if dispatched. The full
# gate now runs on the laptop as the CC/MCP fleet task `ora-occ-full-gate` (weekly, Mon 07:40 ET).
# Do NOT add a `schedule:` trigger here until a runner with the `ora-data` label actually exists.
on:
  workflow_dispatch:
```

- [ ] **Step 7: Commit both halves**

```bash
cd C:/Users/Owner/oxford-command-center
git add .github/workflows/full-gate-selfhosted.yml
git commit -m "docs(ci): mark full-gate-selfhosted as unprovisioned; gate moved to fleet (OI-254)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

For `~/.claude` (shared checkout — claim first, stage explicit paths only):

```bash
cd C:/Users/Owner/.claude
python hooks/lib/claim_work.py claim repo-housekeeping "register ora-occ-full-gate task spec" --paths scheduled-tasks/ora-occ-full-gate/SKILL.md
git add scheduled-tasks/ora-occ-full-gate/SKILL.md
git commit -m "feat(fleet): add ora-occ-full-gate weekly financial-gate task (OI-254)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```

---

### Task B2: Restore the Brain Server autostart and diagnose the classifier (OI-258)

**Files:**
- Modify: none in git. This task changes Windows Task Scheduler state and produces a diagnosis.

**Interfaces:** none.

- [ ] **Step 1: Establish why the Brain Server task is missing before re-registering**

```bash
powershell -NoProfile -Command "Get-ScheduledTask | Where-Object { $_.TaskName -like 'ORA*' } | Select-Object TaskName, State | Format-Table -AutoSize"
powershell -NoProfile -Command "Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational -MaxEvents 200 -ErrorAction SilentlyContinue | Where-Object { $_.Message -match 'Brain Server' } | Select-Object TimeCreated, Id, Message | Format-List"
```

Expected: `ORA Command Center - Brain Server` absent from the first command. The second either shows a deletion/registration history or returns nothing. **A machine migration that dropped it is a different story from something actively removing it — only the second recurs.** Record which you found; if the event log is empty, say "no evidence either way" rather than assuming migration.

- [ ] **Step 2: Re-register the Brain Server task**

```bash
cd C:/Users/Owner/oxford-command-center
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register-brain-server-task.ps1
```

Expected: `Registered 'ORA Command Center - Brain Server': starts <script> at every logon, auto-restarts on crash, no execution time limit.`

- [ ] **Step 3: Verify it is registered and the server actually binds**

```bash
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'ORA Command Center - Brain Server' | Get-ScheduledTaskInfo | Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8911/api/health
```

Expected: the task present, and `200` from the health endpoint. If the server does not bind, note that `dev:server` (tsx watch) hangs before binding ~2/5 trials on this machine and the launcher is supposed to use `dev:server:once` — check which the registered action invokes.

- [ ] **Step 4: Diagnose the classifier termination**

`ORA Mirror Deploy Classifier` last exited `3221225786` = `0xC000013A` = `STATUS_CONTROL_C_EXIT`. That is a **termination**, not an exception the script raised — so do not start by debugging `mirror-run-classify.ps1`'s logic.

```bash
powershell -NoProfile -Command "$t = Get-ScheduledTask -TaskName 'ORA Mirror Deploy Classifier'; $t.Settings | Format-List ExecutionTimeLimit, MultipleInstances, StopIfGoingOnBatteries, RestartCount, RestartInterval"
powershell -NoProfile -Command "Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational -MaxEvents 400 -ErrorAction SilentlyContinue | Where-Object { $_.Message -match 'Mirror Deploy Classifier' } | Select-Object -First 20 TimeCreated, Id, LevelDisplayName, Message | Format-List"
```

Look specifically for: an `ExecutionTimeLimit` shorter than the classifier's real runtime (event id 4102/4103 — "task terminated because it exceeded its time limit"), and `StopIfGoingOnBatteries` being true on a laptop.

- [ ] **Step 5: Apply the fix the diagnosis indicates, then re-run**

If it is the time limit, raise it via `Set-ScheduledTask` with an `ExecutionTimeLimit` comfortably above the observed runtime. If it is battery policy, clear that setting. **If the diagnosis is inconclusive, stop and report — do not guess at a fix.**

```bash
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'ORA Mirror Deploy Classifier'"
```

Then, after it completes:

```bash
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'ORA Mirror Deploy Classifier' | Get-ScheduledTaskInfo | Format-List LastRunTime, LastTaskResult"
```

Expected: `LastTaskResult = 0`.

- [ ] **Step 6: Record the outcome in the event log**

```bash
python C:/Users/Owner/.claude/maintenance/append-event-log.py --note "OI-258: re-registered 'ORA Command Center - Brain Server' (absent since <finding from Step 1>); classifier 0xC000013A root cause: <finding from Step 4>, fix: <what was changed>, verified LastTaskResult=0."
```

---

## Workstream C — AAOS CI and drift verification (OI-259, closes OI-175)

### Task C1: Give AAOS a CI workflow and a pinned dependency manifest

**Files:**
- Create: `C:\Users\Owner\AAOS\requirements.txt`, `C:\Users\Owner\AAOS\.github\workflows\ci.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: a `requirements.txt` that Task C2 and `docs/COWORK-BOOTSTRAP.md` can point at. No code interface.

Context: AAOS has 216 unittest tests (~31 seconds), one non-stdlib import (`jsonschema`, 4.26.0 in the active environment), no `requirements.txt`/`pyproject.toml`, and **no `.github/` directory at all**. Repo is `ZeOoba/AAOS`, default branch `main`, Python 3.13.

- [ ] **Step 1: Confirm the suite is green before wiring CI to it**

```bash
cd C:/Users/Owner/AAOS
python -m unittest discover -s tests -p "test_*.py"
```

Expected: `OK` with 216 tests, ~31s. **If it fails, STOP and report** — you have found a real regression, and wiring CI to a red suite means it starts disabled in practice.

- [ ] **Step 2: Create the pinned manifest**

Create `C:\Users\Owner\AAOS\requirements.txt`:

```
# AAOS runtime + test dependencies.
#
# The codebase is stdlib-only except for jsonschema, used by tools/validate.py and by
# _aaos_common's schema-validation glue. Pinned to a floor rather than an exact version:
# Draft202012Validator (which COWORK-BOOTSTRAP.md's Probe X needs) landed in 4.18, and the
# 2026-07-10 Cowork session that hit an ImportError was on an older build with no manifest to
# install from — see open-items-tracker.md#OI-175.
jsonschema>=4.18
```

- [ ] **Step 3: Create the CI workflow**

Create `C:\Users\Owner\AAOS\.github\workflows\ci.yml`:

```yaml
# AAOS CI. Until 2026-09-10 this repo had no CI at all (open-items-tracker.md#OI-259) — its 216
# tests ran only when a human typed the command. AAOS owns the lease/lock discipline that stops
# two agents clobbering each other's task state, and its one documented Critical bug (two
# near-simultaneous appends to aaos-events.ndjson silently clobbering each other, see
# docs/GATE3-REVIEW.md) is regression-guarded by those tests alone.
#
# No secrets, no data access, no self-hosted runner: the suite is pure local-filesystem work
# against tmpdirs, and nothing here touches the live OneDrive seam.
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        # 3.13 is what the operating machine runs; 3.11 guards against accidentally depending on
        # a very recent stdlib addition that a Cowork sandbox might not have.
        python-version: ['3.11', '3.13']
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run test suite
        run: python -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 4: Verify the workflow file parses before pushing**

```bash
cd C:/Users/Owner/AAOS
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('workflow YAML parses')"
```

Expected: `workflow YAML parses`.

- [ ] **Step 5: Commit and push, then confirm the run went green**

```bash
cd C:/Users/Owner/AAOS
git add requirements.txt .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions test workflow and pin jsonschema (OI-259, OI-175)

216 tests previously ran only by hand. No secrets, no data access — the suite
is pure tmpdir filesystem work. requirements.txt gives COWORK-BOOTSTRAP.md's
Probe X something durable to install from.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
gh run list --repo ZeOoba/AAOS --limit 3
```

Expected: a `CI` run appears and concludes `success` on both matrix legs. **Do not claim this task done until you have seen a green conclusion**, not merely a queued run.

- [ ] **Step 6: Point COWORK-BOOTSTRAP.md at the manifest (closes OI-175)**

In `C:\Users\Owner\AAOS\docs\COWORK-BOOTSTRAP.md` §2, replace the ad-hoc `pip install jsonschema` guidance with `pip install -r requirements.txt` (path relative to the AAOS git tree, or the seam `contracts/` mirror if the session cannot reach git). Read the surrounding paragraph first and match its wording — do not paste a generic instruction.

```bash
cd C:/Users/Owner/AAOS
git add docs/COWORK-BOOTSTRAP.md
git commit -m "docs: install Probe X deps from requirements.txt (OI-175)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

Then update OI-175's row in the tracker to CLOSED with the commit sha — claim `open-items-tracker` first.

---

### Task C2: Make the contracts publisher verify its own publish

**Files:**
- Modify: `C:\Users\Owner\.claude\scheduled-tasks\ora-aaos-publish-contracts\SKILL.md`

**Interfaces:** none.

Context: `tools/publish-contracts.py` runs as the registered `ora-aaos-publish-contracts` task, **1×/day, weekdays 09:15 ET** (v1.2 collapsed it from 2×/day on 2026-08-05; the spec explicitly accepts up to ~24h of mirror lag). `tools/check-contract-drift.py` — the read-only auditor written to prove a publish worked, hash-comparing every published file's bytes against what the git tree would currently produce — is invoked by nothing.

- [ ] **Step 1: Confirm the drift checker's exit codes before depending on them**

```bash
cd C:/Users/Owner/AAOS
python tools/check-contract-drift.py; echo "exit=$?"
grep -n "sys.exit\|return [0-9]" tools/check-contract-drift.py | head -20
```

Expected: a clean run (exit 0) plus a readable list of the exit codes the tool actually uses. **Write the guard conditions in Step 2 against what you observe here, not against the codes assumed below** — if they differ, correct them.

- [ ] **Step 2: Add the verify step to the task spec**

In `C:\Users\Owner\.claude\scheduled-tasks\ora-aaos-publish-contracts\SKILL.md`, immediately after the existing guard-conditions block and before the "Background if you need it" line, insert:

```markdown
Step 2 — verify the publish actually landed (added 2026-09-10, open-items-tracker.md#OI-259).
Only run this if Step 1 exited 0:

    python "C:\Users\Owner\AAOS\tools\check-contract-drift.py"

This is read-only and never writes anything — it hash-compares every published file's bytes
against what the git tree would currently produce, and separately checks `PUBLISHED.json`'s
`source_commit` stamp against HEAD. It catches two things the publisher itself cannot: a publish
that half-succeeded, and a hand-edit made directly on the seam mirror (a write-scope violation —
no agent-registry.json entry's `write_scope` includes `contracts/`).

Guard conditions:
- Exit 0: normal. Stay silent.
- Non-zero: send exactly one email via
  `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to
  ggoldberg@oxfordra.net ONLY — subject "AAOS contracts mirror DRIFT after publish", body = the
  tool's stdout and stderr verbatim. Do NOT re-run publish-contracts.py to "fix" it: a publish
  that just ran and still reports drift is a real defect, and re-publishing would erase the
  evidence. Report, do not remediate.
```

- [ ] **Step 3: Bump the spec's version and changelog**

In the same file's frontmatter `description`, change the trailing version marker to `v1.5`, and append to the changelog block at the bottom:

```markdown
- **v1.5 (2026-09-10, OI-259): added Step 2 — `check-contract-drift.py` runs after a successful publish. The publisher had been automated since 2026-07-10 while the auditor written to prove it worked was wired to nothing, so a half-successful publish looked identical to a clean one. Report-only: drift never triggers an automatic re-publish.
```

- [ ] **Step 4: Verify the whole sequence by hand exactly as the task will run it**

```bash
cd C:/Users/Owner/AAOS
python tools/publish-contracts.py; echo "publish exit=$?"
python tools/check-contract-drift.py; echo "drift exit=$?"
```

Expected: both exit 0. A non-zero drift immediately after a successful publish is itself a finding — allocate an OI id and report rather than proceeding.

- [ ] **Step 5: Commit (shared checkout — claim first)**

```bash
cd C:/Users/Owner/.claude
python hooks/lib/claim_work.py claim repo-housekeeping "add drift-verify step to ora-aaos-publish-contracts" --paths scheduled-tasks/ora-aaos-publish-contracts/SKILL.md
git fetch origin && git status -sb
git add scheduled-tasks/ora-aaos-publish-contracts/SKILL.md
git commit -m "feat(fleet): verify the AAOS contracts publish with check-contract-drift (OI-259)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```

**Note:** editing this `SKILL.md` changes what the live task does at its next fire — the scheduler resolves the registry `filePath` against the live working tree (OI-170), so this takes effect on disk immediately, before any commit. Verify the file on disk is what you intend.

---

## Workstream D — Website chat model (OI-256)

**Hard Invariant 2 applies to every step here. Nothing reaches production without Gabriel's explicit per-deploy confirmation.**

### Task D1: Prove the newer model on a preview before changing any code

**Files:** none modified in this task.

**Interfaces:**
- Produces: a dated eval result run under `evals/` and a go/no-go recommendation that Task D2 depends on.

Key fact that makes this cheap: `netlify/edge-functions/chat.ts:209` reads `Deno.env.get('CHAT_MODEL') || MODEL_DEFAULT`. **The model is already env-overridable**, so the newer model can be evaluated on a preview with zero code change.

- [ ] **Step 1: Capture the current baseline**

```bash
cd C:/Users/Owner/website-canonical
ls -la evals/
```

Identify the most recent dated result run — that is the `claude-sonnet-4-5` baseline you will compare against. If none exists or it is stale, run the eval against the current production origin first to establish one.

- [ ] **Step 2: Deploy a preview (NOT production) and set the override**

Ask Gabriel to confirm a **deploy preview** build, then set `CHAT_MODEL=claude-sonnet-5` as an environment variable scoped to that deploy context in Netlify. A preview deploy is still a deploy — confirm it, do not assume it.

- [ ] **Step 3: Run the eval against the preview**

```bash
cd C:/Users/Owner/website-canonical
npm run eval:chat -- --base=https://<preview-id>.netlify.app
```

Expected: a completed run written into `evals/` as a dated snapshot. This spends real model tokens per case — that is why it is deliberately excluded from `npm run verify`.

- [ ] **Step 4: Diff the run against the baseline and decide**

Compare the new dated run against the baseline from Step 1, case by case. Report: which cases improved, which regressed, and which are unchanged. **A model bump is not automatically an improvement** — if any case regresses on factual accuracy about the firm (markets, leadership, deal parameters, contact routing), say so plainly and recommend against, rather than treating "newer" as "better."

Output of this step is a written go/no-go. Task D2 runs only on a go.

---

### Task D2: Hoist the model id into a constant and bump it

**Files:**
- Modify: `C:\Users\Owner\website-canonical\netlify\edge-functions\chat.ts`

**Interfaces:**
- Consumes: Task D1's go decision.
- Produces: nothing later consumes this.

- [ ] **Step 1: Change the default**

In `C:\Users\Owner\website-canonical\netlify\edge-functions\chat.ts`, line 17:

```typescript
// Bumped 2026-09-10 (OI-256): this was `claude-sonnet-4-5` while the sibling broker extractor
// in netlify/functions/_shared/broker-llm-extract.js was already on sonnet-5. Overridable per
// deploy context via the CHAT_MODEL env var (read at line 209) — that override is how this bump
// was evaluated on a preview before landing. Eval evidence: evals/<dated run>.
const MODEL_DEFAULT = 'claude-sonnet-5';
```

- [ ] **Step 2: Run the full local gate**

```bash
cd C:/Users/Owner/website-canonical
npm run verify
```

Expected: all five stages pass (build → jsonld → unit → CSP → functions runtime). This does not exercise the chat model — D1's eval is what covers that — but it proves nothing else broke.

- [ ] **Step 3: Commit (do NOT deploy)**

```bash
cd C:/Users/Owner/website-canonical
git add netlify/edge-functions/chat.ts
git commit -m "feat(chat): bump the assistant default to claude-sonnet-5 (OI-256)

The public chat assistant was a generation behind broker-llm-extract.js in
the same repo. Evaluated on a deploy preview via the existing CHAT_MODEL
env override before landing; eval evidence in evals/<dated run>.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 4: STOP — production deploy is Gabriel's call**

Report that the change is committed and preview-verified, and ask explicitly for the production deploy. **Do not run `netlify deploy --prod` or any indirected equivalent** — `scripts/netlify-guard.js` blocks obfuscated attempts, and Hard Invariant 2 requires in-turn confirmation regardless.

- [ ] **Step 5 (separate, optional follow-up): audit the other four pins**

The wider half of OI-256 is that five model ids sit hard-coded across three repos with no shared constant. Once D2 lands, propose (do not unilaterally implement) a single exported constant per repo: `oxford-command-center/server/ai/models.ts` and an ora-pm equivalent. That is a separate change with its own review.

---

## Workstream E — Mirror and scheduling policy (OI-257, OI-260)

### Task E1: Make the ora-skills → AppData mirror self-heal

**Files:**
- Create: `C:\Users\Owner\.claude\scheduled-tasks\ora-skills-mirror-republish\SKILL.md`

**Interfaces:** none.

Context, verified: `ora-skills/tools/sync_appdata_mirror.py` already supports a **full** sync — invoked with no arguments it iterates every skill directory in the repo and syncs each into whichever AppData runtime-cache mirrors already have it installed. Only `--check-staged` restricts it to staged files. **No new code is needed** — this task is a scheduled invocation of an existing tool, applying the AAOS shape (scheduled one-way republish) to the estate's worst detect-only mirror.

- [ ] **Step 1: Dry-run the full sync and read what it reports**

```bash
cd C:/Users/Owner/ora-skills
git fetch origin && git status -sb
python tools/repo_first_check.py
python tools/sync_appdata_mirror.py
```

**This stop-condition is live right now, not hypothetical.** As of 2026-09-10 a full sweep reports **two** CACHE-AHEAD skills:

```
!! REPO-FIRST CACHE-AHEAD: pma-qc
     SKILL.md -- runtime cache holds content that was never committed on ANY branch
!! REPO-FIRST CACHE-AHEAD: vendor-contract-qc
     SKILL.md -- runtime cache holds content that was never committed on ANY branch
```

Rescue copies of the about-to-be-clobbered cache content are already staged at
`_staging/repo-first-rescue/pma-qc/` and `_staging/repo-first-rescue/vendor-contract-qc/`.

**So Task E1 has a prerequisite: reconcile those two first.** For each, diff the rescued cache copy against the committed `SKILL.md`, decide which content is correct (the cache copy is a real edit somebody made — do not discard it because it is untracked), commit the reconciled version to the repo, and re-run `python tools/repo_first_check.py` until it reports no CACHE-AHEAD skills. Only then proceed to Step 2. This is a live instance of OI-164, not a new finding — record the reconciliation against that item rather than allocating a new id.

Expected after reconciliation: `repo_first_check.py` reports no `CACHE-AHEAD`/`DIVERGENT` findings, and `sync_appdata_mirror.py` runs clean.

- [ ] **Step 2: Write the task spec**

Create `C:\Users\Owner\.claude\scheduled-tasks\ora-skills-mirror-republish\SKILL.md`:

```markdown
---
name: ora-skills-mirror-republish
description: ora-skills → AppData runtime-cache republisher (CC/MCP fleet, filesystem tool) — re-syncs every git-tracked skill's shipped files into the installed AppData mirrors, so repo→cache divergence self-heals on a cadence instead of waiting for a human to run repo_first_check.py. Applies the ora-aaos-publish-contracts shape to the estate's worst detect-only mirror (open-items-tracker.md#OI-164, #OI-257). Refuses to run if the cache is AHEAD of the repo. Silent on success; emails ggoldberg only on a refusal or failure. Daily, 08:30 ET. v1.0 (2026-09-10)
---

Republish the ora-skills repo into the AppData runtime-cache mirrors.

Step 1 — make the repo current and check direction FIRST:

    cd C:\Users\Owner\ora-skills
    git fetch origin
    git status -sb
    python tools/repo_first_check.py

`repo_first_check.py` hashes every bundled file against the live runtime cache and derives
direction from git ancestry.

**If it reports ANY `CACHE-AHEAD` or `DIVERGENT` skill, STOP. Do not run Step 2.** A cache-ahead
skill means some session edited the runtime cache directly and never committed it; republishing
would silently clobber that work — the exact failure `_staging/STORE_AHEAD_OF_REPO.md` exists to
record. Send exactly one email via
`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net
ONLY — subject "ora-skills mirror republish REFUSED — cache ahead", body = the tool's output
verbatim plus the names of the affected skills. Then do nothing else.

Step 2 — only if Step 1 found no cache-ahead/divergent skill, republish everything:

    python tools/sync_appdata_mirror.py

Invoked with no arguments this syncs every skill directory in the repo. The sync is
additive-only (it never deletes anything already in a mirror) and only touches mirrors that
already have that skill installed.

Guard conditions:
- Exit 0: normal. Stay silent.
- Non-zero: retry once. If it fails again, send exactly one email (same path, same recipient) —
  subject "ora-skills mirror republish FAILED", body = stderr verbatim.
- Never hand-edit anything under the AppData cache. Never commit anything from this task — it
  writes to the cache only, never to the repo.
- Do nothing else: no git writes, no registry changes, no other files touched.

Why this exists: the repo and the AppData cache are two independently-writable copies of every
skill, previously reconciled only by after-the-fact detection. `masterlease-jurisdiction-rebase`
drifted cache-ahead three times in a single session (2026-08-04), twice caught only by manual
diffing. Detection bounds how long a divergence survives; a scheduled republish makes the common
direction (repo ahead of cache) heal itself.
```

- [ ] **Step 3: Register it via the supervised tool**

Same discipline as Task B1 Step 4: check `registry-membership.log` for concurrent activity, confirm no id collision on either fleet and that the 08:30 daily slot is free, then register id `ora-skills-mirror-republish`, cron `30 8 * * *`, on the CC/MCP fleet via `create_scheduled_task`. **Never splice registry JSON.**

- [ ] **Step 4: Verify and fire once**

```bash
python C:/Users/Owner/.claude/maintenance/fleet-status.py --summary
```

Expected: the task present and enabled on CC/MCP with cron `30 8 * * *`. Trigger one manual run; confirm silent exit and that `python tools/repo_first_check.py` still reports clean afterwards.

- [ ] **Step 5: Update OI-164 and OI-257, and commit the spec**

Update OI-164's tracker row to note the republish task now covers the repo-ahead direction, leaving `repo_first_check.py` as confirmation rather than sole defense — **it does not close OI-164**, because the cache-ahead direction is still only detected, never prevented. Claim `open-items-tracker` before editing.

```bash
cd C:/Users/Owner/.claude
python hooks/lib/claim_work.py claim repo-housekeeping "register ora-skills-mirror-republish" --paths scheduled-tasks/ora-skills-mirror-republish/SKILL.md
git add scheduled-tasks/ora-skills-mirror-republish/SKILL.md
git commit -m "feat(fleet): scheduled ora-skills → AppData republish (OI-164, OI-257)

Applies the ora-aaos-publish-contracts shape to the estate's worst detect-only
mirror. Refuses to run when the cache is ahead — republishing then would
clobber uncommitted cache edits.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```

---

### Task E2: Settle `_scheduled_tasks_backup/` (OI-257)

**Files:**
- Modify: `C:\Users\Owner\.claude\README.md`, and either the directory itself or whatever writes it.

**Interfaces:** none.

- [ ] **Step 1: Establish whether anything writes it**

```bash
cd C:/Users/Owner/.claude
grep -rn "_scheduled_tasks_backup" --include="*.py" --include="*.ps1" --include="*.md" --include="*.json" . | grep -v "^./_archive/" | head -20
git log --oneline -5 -- _scheduled_tasks_backup/
ls _scheduled_tasks_backup/ | wc -l
```

Expected: this tells you whether it is written by a script, written by hand, or abandoned. The README calls it "a second, redundant-by-design snapshot of task SKILL.md specs (107 entries observed)"; the live `scheduled-tasks/` directory has a different count, so also compare:

```bash
ls scheduled-tasks/ | wc -l
```

- [ ] **Step 2: Take one of two actions, based on what Step 1 found**

**If a writer exists and it is current:** leave it, and add a line to `~/.claude/README.md`'s row for it naming the writer and its cadence, so the next audit does not re-flag it.

**If no writer exists (the expected case):** it is a stale snapshot presenting as coverage. Per Hard Invariant 6, do not delete — move it:

```bash
cd C:/Users/Owner/.claude
git mv _scheduled_tasks_backup _archive/_scheduled_tasks_backup_stale_2026-09-10
```

Then correct the `~/.claude/README.md` directory table row so it no longer describes a live backup, and state plainly that `scheduled-tasks/*/SKILL.md` in git history is the real durable copy.

- [ ] **Step 3: Commit (shared checkout — claim first)**

```bash
cd C:/Users/Owner/.claude
python hooks/lib/claim_work.py claim repo-housekeeping "settle _scheduled_tasks_backup (OI-257)" --paths README.md _scheduled_tasks_backup
git status -sb
git add README.md _archive/_scheduled_tasks_backup_stale_2026-09-10 _scheduled_tasks_backup
git commit -m "chore: archive the unwritten _scheduled_tasks_backup snapshot (OI-257)

A backup nothing writes to reads as coverage in exactly the moment coverage
is being counted. Archived rather than deleted (Hard Invariant 6); git
history of scheduled-tasks/*/SKILL.md is the real durable copy.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```

---

### Task E3: Encode the lateness rule in the registration gate (OI-260)

**Files:**
- Modify: `C:\Users\Owner\ora-skills\register-scheduled-task\SKILL.md`

**Interfaces:** none.

**This task proposes a standing rule, it does not register any automation.** Per this audit's own boundary: registering new unattended automation that did not exist before is a bigger decision than fixing visibility for something already running — surface it as a choice.

- [ ] **Step 1: Read the existing QC gate before adding to it**

```bash
cd C:/Users/Owner/ora-skills
git fetch origin && git log --oneline -1 && git status -sb
grep -n "QC gate\|QC Gate" register-scheduled-task/SKILL.md | head
```

**Single-writer rule applies:** if HEAD is newer than session start, or uncommitted changes in this repo are not yours, STOP and surface the conflict.

- [ ] **Step 2: Add the question to the registration QC gate**

Add one numbered item to the existing QC-gate list in `register-scheduled-task/SKILL.md`, matching the surrounding numbering and voice:

```markdown
N. **Lateness class (added 2026-09-10, open-items-tracker.md#OI-260).** Ask, and record the
   answer in the task's spec: *does this task being LATE — not failing, just late — have a
   consequence outside this machine?* Both Claude fleets fire only while the Desktop app is
   open; otherwise the whole chain catches up in a burst at next open. A task that merely
   reports or monitors can absorb that. A task whose lateness reaches a counterparty, a tenant,
   a lender or a payment rail cannot.
   - **Externally-consequential:** it needs an off-box backup drain (a GitHub Actions cron
     hitting the same idempotent endpoint, offset well after the on-fleet slot). The worked
     precedent is `ora-pm/.github/workflows/monthly-billing-backup.yml`, added after the
     2026-09-01 laptop outage deferred charge posting to the next app open; the upsert is
     idempotent, so a double fire posts nothing.
   - **Not externally-consequential:** stays on-fleet, and the spec should say so explicitly so
     the next audit does not re-ask.
   Registering the backup workflow is a separate decision requiring Gabriel's go-ahead — this
   gate item forces the question to be asked at registration time, it does not answer it.
```

- [ ] **Step 3: Bump the skill version and changelog**

Update the version marker in the frontmatter `description` (currently v2.21) to v2.22 and add a dated changelog line in the body stating what was added and why, matching the file's existing changelog format.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Owner/ora-skills
git add register-scheduled-task/SKILL.md
git commit -m "feat(register-scheduled-task): add the lateness-class QC gate item (OI-260)

Both fleets fire only while the Desktop app is open. That exposure has been
mitigated exactly once (ora-pm billing backup). This makes the question part
of registration rather than something rediscovered after an outage.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 5: Republish to the runtime cache**

```bash
cd C:/Users/Owner/ora-skills
python tools/repo_first_check.py
python tools/sync_appdata_mirror.py register-scheduled-task
```

Expected: clean check, then a sync line for `register-scheduled-task`. (Once Task E1 is live this happens on a cadence anyway, but do it now so the edited gate is in effect immediately.)

---

## Workstream F — The dead subdomain (OI-262)

### Task F1: Make every document agree about `brain.oxfordra.net`

**Files:**
- Modify: `C:\Users\Owner\oxford-command-center\README.md` and whichever documents Step 1 finds.

**Interfaces:** none.

- [ ] **Step 1: Find every place the hostname is named, and confirm it is still dead**

```bash
nslookup brain.oxfordra.net 2>&1 | tail -6
grep -rn "brain.oxfordra.net" C:/Users/Owner/oxford-command-center --include="*.md" --include="*.ts" --include="*.json" --include="*.ps1" | grep -v node_modules
grep -rn "brain.oxfordra.net" C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/
```

Expected: the DNS lookup confirms it resolves to nothing routable (if it now resolves correctly, the finding is stale — say so and close OI-262 instead of editing anything), plus a list of every file naming it.

- [ ] **Step 2: Take the decision to Gabriel**

Two options, and this is his call, not an agent's:

- **(a) Retire it.** Strike the hostname from every file found in Step 1, replacing each mention with the Cloudflare Pages mirror URL that actually works. Lowest effort; the mirror behind Cloudflare Access already serves the away-from-desk case the subdomain was meant to.
- **(b) Fix it.** Move the DNS record for that subdomain from NS1/Netlify to Cloudflare so the tunnel CNAME resolves. This is a DNS change on the firm's domain — it needs Gabriel's explicit go-ahead and is adjacent to Hard Invariant 2's territory.

- [ ] **Step 3: Execute the chosen option and make the docs agree**

If (a): edit each file from Step 1. In `oxford-command-center/README.md` §6, replace the "does not currently route anywhere usable" bullet with a plain statement that the subdomain is retired and the Pages mirror is the remote-access path — a dead hostname explained is still a dead hostname someone will try.

If (b): make the DNS change, verify with `nslookup` and an end-to-end request through the tunnel, then update §6 to describe it as working.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Owner/oxford-command-center
git add README.md
git commit -m "docs: settle brain.oxfordra.net — <retired | now routing> (OI-262)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Recommended sequencing

No workstream depends on another, so this is a value/effort ordering, not a dependency graph:

| Order | Work | Why here | Rough effort |
|---|---|---|---|
| 1 | **C1** (AAOS CI) | No secrets, no data access, no decisions to make. Highest safety-per-minute in the plan. | ~20 min |
| 2 | **D1** (chat eval on preview) | Cheap, reversible, no code change, and it produces the evidence D2 needs. | ~30 min + eval tokens |
| 3 | **A1 + A2** (ora-pm gate) | Closes the estate's worst risk asymmetry. A2 needs a REFUTE pass, so start it early. | ~half a day |
| 4 | **B1** (OCC full-gate task) | Restores a financial-integrity check. Gated on the gate being green today (B1 Step 1). | ~1 hour |
| 5 | **B2** (Brain Server + classifier) | Ops, but B2 Step 4 is a real diagnosis and may not resolve in one pass. | ~1 hour |
| 6 | **C2, E1** (self-healing mirrors) | Both are scheduled invocations of tools that already exist. | ~1 hour each |
| 7 | **A3, E2, E3, F1** (docs and policy) | Real, but none is urgent and each is small. | ~30 min each |
| 8 | **D2** (model bump) | Runs only on D1's go, and ends at a production-deploy gate that is Gabriel's call. | ~15 min + deploy |

## Self-review notes

- **Coverage:** OI-254→B1; OI-255→A1+A2; OI-256→D1+D2; OI-257→E1+E2 (and E1 partially serves OI-164, which it explicitly does not close); OI-258→B2; OI-259→C1+C2 (C1 Step 6 closes OI-175); OI-260→E3; OI-261→A3; OI-262→F1. All nine covered.
- **Deliberate non-goals:** unifying the seven mirrors (rewrites seven working pipelines for no gain); provisioning the self-hosted runner (B1 chooses the cheaper correct path and says why); registering any new off-box backup workflow (E3 adds the question, not the automation); enabling type-aware linting in ora-pm (A1 Step 2 says why it is left off rather than half-configured).
- **Stop-and-report points are load-bearing, not hedges.** B1 Step 1, C1 Step 1, E1 Step 1 and B2 Step 5 each halt the task rather than proceed on an assumption. A green-looking gate scheduled over a red one, or a republish over a cache-ahead skill, would each do real damage.
