// Tests for the parameterized cc-audit-army workflow.
// Usage: node test.mjs snapshot   -> capture cc-mode prompts from the CURRENT script (run BEFORE editing)
//        node test.mjs            -> run all tests (cc-mode byte-identical regression + generic mode)
import { runWorkflow } from './harness.mjs';
import { readFileSync, writeFileSync } from 'node:fs';

const SCRIPT = 'C:/Users/Owner/.claude/workflows/cc-audit-army.js';
const SNAP = new URL('cc-mode-prompts.snapshot.json', import.meta.url);

const failures = [];
function check(name, cond, detail) {
  if (cond) { console.log('  PASS ' + name); }
  else { failures.push(name); console.log('  FAIL ' + name + (detail ? ' — ' + detail : '')); }
}

if (process.argv[2] === 'snapshot') {
  const { calls } = await runWorkflow(SCRIPT, undefined);
  writeFileSync(SNAP, JSON.stringify(calls, null, 2));
  console.log('Snapshot written: ' + calls.length + ' agent calls captured (cc mode, no args).');
  process.exit(0);
}

// --- Test A: cc-mode regression — prompts byte-identical to the snapshot + refresh-scout wiring ---
console.log('Test A: cc-mode (no args) prompts byte-identical to snapshot + cc-refresh scout wiring');
{
  const snap = JSON.parse(readFileSync(SNAP, 'utf8'));
  const { calls, phases, result } = await runWorkflow(SCRIPT, undefined);
  check('same call count', calls.length === snap.length, calls.length + ' vs ' + snap.length);
  const n = Math.min(calls.length, snap.length);
  for (let i = 0; i < n; i++) {
    const same = calls[i].label === snap[i].label && calls[i].model === snap[i].model && calls[i].prompt === snap[i].prompt;
    if (!same) check('call[' + i + '] ' + snap[i].label + ' identical', false,
      calls[i].label !== snap[i].label ? 'label ' + calls[i].label + ' vs ' + snap[i].label
        : calls[i].model !== snap[i].model ? 'model ' + calls[i].model + ' vs ' + snap[i].model
        : 'prompt diverged at index ' + [...calls[i].prompt].findIndex((c, j) => c !== snap[i].prompt[j]));
  }
  check('all prompts identical', calls.slice(0, n).every((c, i) => c.prompt === snap[i].prompt && c.label === snap[i].label && c.model === snap[i].model));
  const refreshCalls = calls.filter((c) => c.label === 'cc-refresh');
  const auditCalls = calls.filter((c) => c.label.startsWith('audit:'));
  check('cc mode: Orient phase runs', phases.includes('Orient'));
  check('cc mode: exactly one cc-refresh scout, dispatched first', refreshCalls.length === 1 && calls[0].label === 'cc-refresh');
  check('cc mode: no generic orient call', !calls.some((c) => c.label === 'orient'));
  check('cc mode: refreshed baseline reaches audit prompts', auditCalls.length === 9 && auditCalls.every((c) => c.prompt.includes('BASELINE = main @ fresh123')));
  check('cc mode: newer already-done reaches audit prompts', auditCalls.every((c) => c.prompt.includes('CC-REFRESH-NEWER')));
  check('cc mode: stale sha no longer presented as baseline', auditCalls.every((c) => !c.prompt.includes('BASELINE = origin/main @ 823574d')));
  check('cc mode: curated already-done retained', auditCalls.every((c) => c.prompt.includes('reconcile-noi.ts')));
  check('cc mode: baked focus paths retained', auditCalls.some((c) => c.label === 'audit:correctness' && c.prompt.includes('server/warehouse')));
  check('cc mode: result still has reportMarkdown/ranked/counts', !!(result && result.reportMarkdown !== undefined && result.ranked && result.counts));
  check('cc mode: result reports mode=cc', !!result && result.mode === 'cc');
  // Rank-phase fix (2026-07-16): the single-string synthesize-report design blew the StructuredOutput
  // retry cap at 32 findings; the agent now emits only a compact ranking and code renders the markdown.
  check('cc mode: rank phase uses rank-findings label', calls.some((c) => c.label === 'rank-findings'));
  check('cc mode: synthesize-report label retired', !calls.some((c) => c.label === 'synthesize-report'));
  check('cc mode: reportMarkdown is code-rendered from ranked findings', typeof result.reportMarkdown === 'string' && result.reportMarkdown.includes('# Audit Report'));
}

// --- Test B: generic mode — Orient scout feeds ground truth + per-dimension focus ---
console.log('Test B: generic mode (args.worktree + args.brief)');
{
  const args = { worktree: 'C:/tmp/ora-pm', brief: 'ORA property-management app: React + Supabase, tenant portal.' };
  const { calls, phases, result } = await runWorkflow(SCRIPT, args);
  const orientCalls = calls.filter((c) => c.label === 'orient');
  const auditCalls = calls.filter((c) => c.label.startsWith('audit:'));
  check('Orient phase runs', phases.includes('Orient'));
  check('exactly one orient scout, dispatched first', orientCalls.length === 1 && calls[0].label === 'orient');
  check('orient scout sees the operator brief', orientCalls.length === 1 && orientCalls[0].prompt.includes(args.brief));
  check('still 9 audit dimensions', auditCalls.length === 9);
  check('audit prompts target the new worktree', auditCalls.every((c) => c.prompt.includes('C:/tmp/ora-pm')));
  check('no cc ground truth leaks (823574d)', calls.every((c) => !c.prompt.includes('823574d')));
  check('no cc focus paths leak (server/warehouse)', auditCalls.every((c) => !c.prompt.includes('server/warehouse')));
  check('scout ground truth reaches audit prompts', auditCalls.every((c) => c.prompt.includes('ORIENT-SUMMARY')));
  const corr = auditCalls.find((c) => c.label === 'audit:correctness');
  check('scout focus reaches the matching dimension', !!corr && corr.prompt.includes('FOCUS-correctness'));
  check('dedup does not cite cc master-plan paths', calls.filter((c) => c.label === 'dedup-reconcile').every((c) => !c.prompt.includes('docs/superpowers/specs')));
  check('governor clause retained in generic mode', auditCalls.every((c) => c.prompt.includes('DSCR 1.25')));
  check('result reports mode=generic', !!result && result.mode === 'generic');
  check('generic mode: rank phase also uses rank-findings label', calls.some((c) => c.label === 'rank-findings'));
}

// --- Test C: malformed brief fails closed (never silently degrades to cc ground truth) ---
console.log('Test C: malformed args.brief fails closed');
for (const bad of ['   ', 42, null]) {
  let threw = false;
  try { await runWorkflow(SCRIPT, { worktree: 'C:/tmp/ora-pm', brief: bad }); } catch { threw = true; }
  check('brief=' + JSON.stringify(bad) + ' throws (no cc fallback)', threw);
}

// --- Test D: forceModel pins every dispatch when set; no-op (cc byte-identity intact) when unset ---
console.log('Test D: args.forceModel overrides every dispatch model');
{
  const args = { worktree: 'C:/tmp/website-canonical', brief: 'ORA public marketing site: Next.js on Netlify.', forceModel: 'opus' };
  const { calls } = await runWorkflow(SCRIPT, args);
  check('every dispatch forced to opus', calls.length > 0 && calls.every((c) => c.model === 'opus'));
  check('sonnet-tier dimensions (e.g. dead-duplicate) also forced', calls.some((c) => c.label === 'audit:dead-duplicate' && c.model === 'opus'));
}
{
  // unset forceModel in generic mode: dimension defaults (mixed opus/sonnet) still apply
  const args = { worktree: 'C:/tmp/ora-pm', brief: 'ORA property-management app.' };
  const { calls } = await runWorkflow(SCRIPT, args);
  const deadDup = calls.find((c) => c.label === 'audit:dead-duplicate');
  check('forceModel unset: dimension default (sonnet) preserved', !!deadDup && deadDup.model === 'sonnet');
}

// --- Test E2: stringified args is parsed; garbage args fails closed (never the default worktree) ---
// The harness delivers args as a JSON-ENCODED STRING (proven runs wf_ae4150f2-651, wf_514f9699-d33):
// pre-guard it slipped past `typeof args === 'object'` and silently audited the default checkout.
// The script now self-parses a JSON string and still fails closed on anything else.
console.log('Test E2: stringified args parsed, garbage args fails closed');
{
  const { calls, result } = await runWorkflow(SCRIPT, '{"worktree": "C:/tmp/stringified-wt"}');
  const auditCalls = calls.filter((c) => c.label.startsWith('audit:'));
  check('JSON-string args: audits the passed worktree', auditCalls.length === 9 && auditCalls.every((c) => c.prompt.includes('C:/tmp/stringified-wt')));
  check('JSON-string args: still cc mode', !!result && result.mode === 'cc' && result.worktree === 'C:/tmp/stringified-wt');
}
for (const bad of ['not json', '"just-a-string"', 42]) {
  let threw = false;
  try { await runWorkflow(SCRIPT, bad); } catch { threw = true; }
  check('args=' + JSON.stringify(bad) + ' throws (no default-worktree fallback)', threw);
}

// --- Test E: cc-refresh scout death fails closed (never audits on the stale baked baseline) ---
console.log('Test E: cc-refresh scout death fails closed');
{
  let threw = false;
  try { await runWorkflow(SCRIPT, undefined, { 'cc-refresh': null }); } catch { threw = true; }
  check('cc-refresh=null throws (no stale-baked fallback)', threw);
}

console.log(failures.length === 0 ? '\nALL TESTS PASSED' : '\nFAILURES: ' + failures.length);
process.exit(failures.length === 0 ? 0 : 1);
