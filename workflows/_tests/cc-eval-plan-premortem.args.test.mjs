// Args-handling tests for cc-eval-plan-premortem.js (mock Workflow DSL, no agents spawned).
// Run: node workflows/_tests/cc-eval-plan-premortem.args.test.mjs
// Legacy snapshot: set UPDATE_SNAPSHOT=1 to (re)generate cc-eval-plan-premortem.legacy.snapshot.json
// from the CURRENT script. Only do that deliberately: the snapshot is the byte-identity contract.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import assert from 'node:assert/strict';

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const SCRIPT = new URL('../cc-eval-plan-premortem.js', import.meta.url);
const SNAP = new URL('./cc-eval-plan-premortem.legacy.snapshot.json', import.meta.url);
// The script is an ES-module-flavoured Workflow body: strip the `export` so it parses as a function body.
const src = readFileSync(SCRIPT, 'utf8').replace(/^export const meta/m, 'const meta');

function canned(label) {
  if (label === 'evaluate') return { scorecardMarkdown: 'S', dimensionScores: [{ dimension: 'd', score: '5', rationale: 'r' }], topGaps: [], matrixAdjustments: 'm' };
  if (label === 'plan') return { planMarkdown: 'P', initiatives: [], flywheelDesign: 'f' };
  if (label.startsWith('redteam:')) return { objections: [] };
  if (label === 'harden') return { hardenedPlanMarkdown: 'H', residualRisks: [], tierATargets: [] };
  if (label.startsWith('validate:')) return { verdict: 'PASS', defects: [] };
  return {};
}

// Runs the whole workflow with stubbed globals; returns every dispatched prompt in order.
async function runAll(args) {
  const prompts = [];
  const agent = async (p, opts) => { prompts.push(p); return canned((opts && opts.label) || ''); };
  const parallel = async (fns) => Promise.all(fns.map((f) => f()));
  const fn = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', src);
  await fn(args, agent, parallel, () => {}, () => {});
  return prompts;
}

// --- legacy: byte-identical prompts (snapshot taken from the pre-change script) ---
const legacyNoArgs = await runAll(undefined);
const legacyWt = await runAll({ worktree: 'C:/Users/Owner/oxford-command-center' });
const legacyJsonString = await runAll(JSON.stringify({ worktree: 'C:/Users/Owner/oxford-command-center' }));
if (process.env.UPDATE_SNAPSHOT === '1') {
  writeFileSync(SNAP, JSON.stringify({ noArgs: legacyNoArgs, otherWt: await runAll({ worktree: 'C:/other/wt' }) }, null, 1));
  console.log('snapshot written');
}
assert.ok(existsSync(SNAP), 'legacy snapshot missing (run once with UPDATE_SNAPSHOT=1 on the pre-change script)');
const snap = JSON.parse(readFileSync(SNAP, 'utf8'));
assert.deepEqual(legacyNoArgs, snap.noArgs, 'legacy (no args) prompts must be byte-identical to snapshot');
assert.deepEqual(legacyWt, snap.noArgs, 'explicit default worktree must equal no-args prompts');
assert.deepEqual(legacyJsonString, snap.noArgs, 'JSON-string args must equal object args');
assert.deepEqual(await runAll({ worktree: 'C:/other/wt' }), snap.otherWt, 'legacy args.worktree prompts must be byte-identical to snapshot');
assert.ok(legacyNoArgs[0].includes('oxford-command-center/_run/AUDIT-REPORT.md'), 'legacy default must read the command-center audit report');

// --- generic mode ---
const G = { mode: 'generic', target: 'C:/Users/Owner/.claude', artifacts: ['C:/x/audit-report.md', 'C:/x/capability-research.md'], ground: 'EXTRA-GROUND-MARKER' };
const generic = await runAll(G);
assert.equal(generic.length, legacyNoArgs.length, 'generic mode must run the same phase/agent count');
for (const [i, p] of generic.entries()) {
  assert.ok(p.includes('C:/x/audit-report.md') && p.includes('C:/x/capability-research.md'), 'prompt ' + i + ' must read the supplied artifacts');
  assert.ok(p.includes('C:/Users/Owner/.claude'), 'prompt ' + i + ' must name the supplied target');
  assert.ok(!p.includes('oxford-command-center'), 'prompt ' + i + ' must not fall back to the command-center default');
  assert.ok(!p.includes('_run/AUDIT-REPORT.md'), 'prompt ' + i + ' must not hard-code command-center _run paths');
}
assert.ok(generic[0].includes('EXTRA-GROUND-MARKER'), 'args.ground must be appended to GROUND');
// ground is optional
const noGround = await runAll({ mode: 'generic', target: 'C:/t', artifacts: ['C:/a.md'] });
assert.ok(!noGround[0].includes('EXTRA-GROUND-MARKER') && noGround[0].includes('C:/a.md'));
// JSON-string delivery works in generic mode too
const viaString = await runAll(JSON.stringify(G));
assert.deepEqual(viaString, generic, 'generic mode via JSON string must equal object args');

// --- fail closed ---
const rejects = async (args, re, msg) => assert.rejects(() => runAll(args), re, msg);
await rejects({ mode: 'generic', artifacts: ['C:/a.md'] }, /target/, 'generic without target must throw');
await rejects({ mode: 'generic', target: 'C:/t' }, /artifacts/, 'generic without artifacts must throw');
await rejects({ mode: 'generic', target: 'C:/t', artifacts: [] }, /artifacts/, 'generic with empty artifacts must throw');
await rejects({ mode: 'generic', target: 'C:/t', artifacts: 'C:/a.md' }, /artifacts/, 'generic with non-array artifacts must throw');
await rejects({ mode: 'generic', target: 'C:/t', artifacts: [''] }, /artifacts/, 'generic with blank artifact entry must throw');
await rejects({ mode: 'generic', worktree: 'C:/t', artifacts: ['C:/a.md'] }, /target/, 'generic must not silently use args.worktree as target');
await rejects({ mode: 'bogus' }, /mode/, 'unknown mode must throw');

console.log('PASS cc-eval-plan-premortem args');
