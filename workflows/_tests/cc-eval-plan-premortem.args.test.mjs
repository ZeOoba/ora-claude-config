// Args-handling tests for cc-eval-plan-premortem.js (mock Workflow DSL, no agents spawned).
// Run: node workflows/_tests/cc-eval-plan-premortem.args.test.mjs
// CC_SCRIPT=<path> runs the same tests against another copy of the script (used for mutation checks).
// Legacy snapshot: UPDATE_SNAPSHOT=1 (with CC_SCRIPT pointing at the PRE-change original) regenerates
// cc-eval-plan-premortem.legacy.snapshot.json. The snapshot is the byte-identity contract for legacy mode
// (prompts AND schemas).
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import assert from 'node:assert/strict';

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const SCRIPT = process.env.CC_SCRIPT || new URL('../cc-eval-plan-premortem.js', import.meta.url);
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

// Runs the whole workflow with stubbed globals; returns every dispatched prompt and schema in order.
async function runFull(args) {
  const prompts = [];
  const schemas = [];
  const agent = async (p, opts) => { prompts.push(p); schemas.push(JSON.stringify(opts && opts.schema)); return canned((opts && opts.label) || ''); };
  const parallel = async (fns) => Promise.all(fns.map((f) => f()));
  const fn = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', src);
  await fn(args, agent, parallel, () => {}, () => {});
  return { prompts, schemas };
}
const runAll = async (args) => (await runFull(args)).prompts;

// Fail-closed check: must reject AND must not have dispatched a single agent first.
async function rejectsBeforeAgents(args, re, msg) {
  let dispatched = 0;
  const agent = async () => { dispatched++; return {}; };
  const fn = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', src);
  await assert.rejects(() => fn(args, agent, async (f) => Promise.all(f.map((x) => x())), () => {}, () => {}), re, msg);
  assert.equal(dispatched, 0, msg + ' (no agent may be dispatched before failing closed)');
}

// --- legacy: byte-identical prompts + schemas (snapshot taken from the pre-change script) ---
const legacyNoArgs = await runFull(undefined);
if (process.env.UPDATE_SNAPSHOT === '1') {
  const other = await runFull({ worktree: 'C:/other/wt' });
  writeFileSync(SNAP, JSON.stringify({ noArgs: legacyNoArgs.prompts, otherWt: other.prompts, noArgsSchemas: legacyNoArgs.schemas }, null, 1));
  console.log('snapshot written');
}
assert.ok(existsSync(SNAP), 'legacy snapshot missing (run once with UPDATE_SNAPSHOT=1 on the pre-change script)');
const snap = JSON.parse(readFileSync(SNAP, 'utf8'));
assert.deepEqual(legacyNoArgs.prompts, snap.noArgs, 'legacy (no args) prompts must be byte-identical to snapshot');
assert.deepEqual(legacyNoArgs.schemas, snap.noArgsSchemas, 'legacy schemas (incl. descriptions) must be byte-identical to snapshot');
assert.deepEqual(await runAll({ worktree: 'C:/Users/Owner/oxford-command-center' }), snap.noArgs, 'explicit default worktree must equal no-args prompts');
assert.deepEqual(await runAll(JSON.stringify({ worktree: 'C:/Users/Owner/oxford-command-center' })), snap.noArgs, 'JSON-string args must equal object args');
assert.deepEqual(await runAll({ worktree: 'C:/other/wt' }), snap.otherWt, 'legacy args.worktree prompts must be byte-identical to snapshot');
assert.ok(legacyNoArgs.prompts[0].includes('oxford-command-center/_run/AUDIT-REPORT.md'), 'legacy default must read the command-center audit report');
assert.equal(legacyNoArgs.prompts.length, 8, 'legacy run dispatches 8 agents');

// --- legacy mode must NOT silently swallow generic-mode keys (the wrong-repo incident) ---
for (const [k, v] of [['brief', 'audit ~/.claude'], ['target', 'C:/t'], ['artifacts', ['C:/a.md']], ['ground', 'g'], ['dimensions', ['d']]]) {
  await rejectsBeforeAgents({ [k]: v }, /mode.*generic/s, 'legacy mode with args.' + k + ' must throw and name mode:"generic"');
  await rejectsBeforeAgents({ worktree: 'C:/wt', [k]: v }, /mode.*generic/s, 'legacy mode with worktree + args.' + k + ' must throw');
}
// allowlist: ANY key other than worktree/mode throws in legacy mode (typos, case variants, unknown names)
for (const bad of [{ Brief: 'x' }, { repo: 'C:/.claude' }, { path: 'C:/p' }, { worktree: 'C:/wt', extra: 1 }, { mode: 'legacy', foo: 1 }, { Worktree: 'C:/wt' }]) {
  await rejectsBeforeAgents(bad, new RegExp('args\.' + Object.keys(bad).find((k) => k !== 'worktree' && k !== 'mode') + '.*mode.*generic', 's'), 'legacy mode must reject unexpected key in ' + JSON.stringify(bad));
}
// inputs that must stay legacy and byte-identical
for (const ok of [{}, null, '{}', { mode: 'legacy' }, { mode: '' }, { mode: undefined }, JSON.stringify({ mode: 'legacy' })]) {
  assert.deepEqual(await runAll(ok), snap.noArgs, 'legacy-equivalent args must be byte-identical: ' + JSON.stringify(ok));
}
// inherited prototype keys are not own keys and must not trip the guard
assert.deepEqual(await runAll(Object.create({ brief: 'inherited' })), snap.noArgs, 'inherited keys are ignored');
await rejectsBeforeAgents({ brief: 'Audit C:/Users/Owner/.claude config repo' }, /mode.*generic/s, 'exact incident reproducer {brief} must throw');
await rejectsBeforeAgents(JSON.stringify({ brief: 'Audit C:/Users/Owner/.claude config repo' }), /mode.*generic/s, 'incident reproducer as JSON string must throw');

// --- generic mode ---
const G = { mode: 'generic', target: 'C:/Users/Owner/.claude', artifacts: ['C:/x/audit-report.md', 'C:/x/capability-research.md'], ground: 'EXTRA-GROUND-MARKER' };
const generic = await runFull(G);
const BLOCK = ['oxford-command-center', '_run/', 'F1-F13', 'master plan', 'master-plan', 'calibration-log-design', 'ALREADY-DONE', 'docs/superpowers/plans/'];
assert.equal(generic.prompts.length, legacyNoArgs.prompts.length, 'generic mode must run the same phase/agent count');
for (const [i, p] of generic.prompts.entries()) {
  assert.ok(p.includes('C:/x/audit-report.md') && p.includes('C:/x/capability-research.md'), 'prompt ' + i + ' must read the supplied artifacts');
  assert.ok(p.includes('C:/Users/Owner/.claude'), 'prompt ' + i + ' must name the supplied target');
  for (const b of BLOCK) assert.ok(!p.includes(b), 'generic prompt ' + i + ' must not contain command-center text: ' + b);
}
for (const [i, s] of generic.schemas.entries()) {
  for (const b of BLOCK) assert.ok(!s.includes(b), 'generic schema ' + i + ' must not contain command-center text: ' + b);
}
assert.ok(generic.prompts[0].includes('EXTRA-GROUND-MARKER'), 'args.ground must be appended to GROUND');
// target wins over worktree: A in every prompt, B in none
const both = await runAll({ mode: 'generic', target: 'C:/TARGET-A', worktree: 'C:/WORKTREE-B', artifacts: ['C:/a.md'] });
for (const [i, p] of both.entries()) {
  assert.ok(p.includes('C:/TARGET-A'), 'prompt ' + i + ' must name args.target');
  assert.ok(!p.includes('WORKTREE-B'), 'prompt ' + i + ' must not use args.worktree in generic mode');
}
// dimensions override
const dims = await runAll({ mode: 'generic', target: 'C:/t', artifacts: ['C:/a.md'], dimensions: ['alpha-dim', 'beta-dim'] });
assert.ok(dims[0].includes('EXACTLY these 2 dimensions: alpha-dim, beta-dim') && !dims[0].includes('acquisition-velocity,'), 'args.dimensions must replace the default dimension list');
// ground is optional
const noGround = await runAll({ mode: 'generic', target: 'C:/t', artifacts: ['C:/a.md'] });
assert.ok(!noGround[0].includes('EXTRA-GROUND-MARKER') && noGround[0].includes('C:/a.md'));
// JSON-string delivery works in generic mode too
assert.deepEqual(await runAll(JSON.stringify(G)), generic.prompts, 'generic mode via JSON string must equal object args');

// --- fail closed (generic) ---
const base = { mode: 'generic', target: 'C:/t', artifacts: ['C:/a.md'] };
await rejectsBeforeAgents({ mode: 'generic', artifacts: ['C:/a.md'] }, /target/, 'generic without target must throw');
await rejectsBeforeAgents({ mode: 'generic', target: 'C:/t' }, /artifacts/, 'generic without artifacts must throw');
await rejectsBeforeAgents({ ...base, artifacts: [] }, /artifacts/, 'generic with empty artifacts must throw');
await rejectsBeforeAgents({ ...base, artifacts: 'C:/a.md' }, /artifacts/, 'generic with non-array artifacts must throw');
await rejectsBeforeAgents({ ...base, artifacts: [''] }, /artifacts/, 'generic with blank artifact entry must throw');
await rejectsBeforeAgents({ mode: 'generic', worktree: 'C:/t', artifacts: ['C:/a.md'] }, /target/, 'generic must not silently use args.worktree as target');
await rejectsBeforeAgents({ ...base, ground: 5 }, /ground/, 'non-string ground must throw');
await rejectsBeforeAgents({ ...base, dimensions: [] }, /dimensions/, 'empty dimensions must throw');
await rejectsBeforeAgents({ ...base, dimensions: 'x' }, /dimensions/, 'string dimensions must throw');
await rejectsBeforeAgents({ mode: 'bogus' }, /mode/, 'unknown mode must throw');

console.log('PASS cc-eval-plan-premortem args');
