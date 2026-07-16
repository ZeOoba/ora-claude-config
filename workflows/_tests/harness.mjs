// Mock Workflow-DSL harness: executes a workflow script with stubbed agent()/parallel()/phase()
// and captures every dispatched prompt, so script logic is testable without spawning agents.
import { readFileSync } from 'node:fs';

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function canned(label) {
  if (label.startsWith('audit:')) {
    return {
      findings: [{ id: 'f-' + label.slice(6), title: 'T', severity: 'high', file: 'src/a.ts', line: '1', excerpt: 'x', evidence: 'e', goalImpact: 'g', fix: 'f', confidence: 'high' }],
      coverageNote: 'cov',
    };
  }
  if (label === 'cc-refresh') {
    return { baseline: 'main @ fresh123', newerAlreadyDone: 'CC-REFRESH-NEWER' };
  }
  if (label === 'orient') {
    return {
      repoSummary: 'ORIENT-SUMMARY',
      baseline: 'main @ abc1234',
      orientationDocs: 'README.md',
      alreadyDone: 'none identified',
      focus: {
        correctness: 'FOCUS-correctness', 'dead-duplicate': 'FOCUS-dead', performance: 'FOCUS-perf',
        'data-pipeline': 'FOCUS-data', 'financial-math': 'FOCUS-fin', 'security-confidential': 'FOCUS-sec',
        'test-coverage': 'FOCUS-test', architecture: 'FOCUS-arch', 'analytics-ux': 'FOCUS-ux',
      },
      cautions: 'none',
    };
  }
  if (label === 'dedup-reconcile') {
    return {
      merged: [{ id: 'm1', title: 'T', severity: 'high', file: 'src/a.ts', line: '1', excerpt: 'x', evidence: 'e', goalImpact: 'g', fix: 'f', contributingDimensions: ['correctness'], alreadyDone: false }],
      droppedAlreadyDone: [],
    };
  }
  if (label.startsWith('verify:')) {
    return { verdicts: [{ id: 'm1', status: 'confirmed', adjustedSeverity: 'none', note: 'ok' }] };
  }
  if (label === 'rank-findings') {
    return { ranked: [{ rank: 1, id: 'm1', riskTierHint: 'YELLOW', rationale: 'r' }], summary: 'S' };
  }
  throw new Error('no canned response for label: ' + label);
}

// overrides: { [label]: response } — force a specific agent's return value (null simulates agent death).
export async function runWorkflow(scriptPath, args, overrides = {}) {
  let src = readFileSync(scriptPath, 'utf8');
  src = src.replace(/^export\s+/m, ''); // meta stays a plain const inside the wrapper fn

  const calls = [];
  const phases = [];
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || '?';
    calls.push({ label, model: opts.model || null, prompt });
    return label in overrides ? overrides[label] : canned(label);
  };
  const parallel = (thunks) => Promise.all(thunks.map((t) => t().catch(() => null)));
  const pipeline = async () => { throw new Error('pipeline not mocked'); };
  const phase = (t) => phases.push(t);
  const log = () => {};
  const budget = { total: null, spent: () => 0, remaining: () => Infinity };
  const workflow = () => { throw new Error('nested workflow not mocked'); };

  const fn = new AsyncFunction('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow', src);
  const result = await fn(agent, parallel, pipeline, phase, log, args, budget, workflow);
  return { calls, phases, result };
}
