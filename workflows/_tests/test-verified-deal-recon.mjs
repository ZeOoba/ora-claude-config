// Regression harness for verified-deal-recon.js — same mock-DSL technique as cc-audit-army's
// _tests/harness.mjs, kept self-contained (own mini-runner) rather than sharing that file, since
// its canned() dispatch table is keyed to cc-audit-army's own labels.
// Usage: node test-verified-deal-recon.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// The script in THIS checkout (worktree or live), not a hardcoded live path: a hardcoded
// C:/Users/Owner/.claude path made the suite test the live branch's copy from every worktree,
// so origin/main's ratified-floor script was never what this file exercised (audit 2026-11-08).
const SCRIPT = fileURLToPath(new URL('../verified-deal-recon.js', import.meta.url));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

async function runWorkflow(scriptPath, args, canned) {
  let src = readFileSync(scriptPath, 'utf8');
  src = src.replace(/^export\s+/m, '');
  const calls = [];
  const phases = [];
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || '?';
    calls.push({ label, agentType: opts.agentType || null, prompt });
    const resp = canned(label);
    if (resp === undefined) throw new Error('no canned response for label: ' + label);
    return resp;
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

const failures = [];
function check(name, cond, detail) {
  if (cond) { console.log('  PASS ' + name); }
  else { failures.push(name); console.log('  FAIL ' + name + (detail ? ' — ' + detail : '')); }
}

const PROPERTY = '123 Main St, Columbus OH — 28,000 SF flex, $2.8M asking, 3 tenants.';

function standardCanned(overrides = {}) {
  const base = {
    'deal-recon': {
      snapshot: 'S', fitVsBox: 'fits', rentComps: 'rc', saleComps: 'sc', submarket: 'sub',
      demand: ['d1'], basisRead: 'below replacement', redFlags: [],
      recommendation: { verdict: 'PURSUE', oneLineWhy: 'good basis' }, sources: ['src1'],
    },
    'verify:comps-basis': { lens: 'comps-basis', claimsChecked: [], independentFindings: 'ok', flipsRecommendation: false, lensVerdict: 'holds' },
    'verify:functional-environmental': { lens: 'functional-environmental', claimsChecked: [], independentFindings: 'ok', flipsRecommendation: true, lensVerdict: 'flip: Phase I needed' },
    'verify:demand-leaseup': null, // simulate a dead verifier agent
    synthesis: {
      verdict: 'NEEDS_MORE', oneLineThesis: 'confirm Phase I', snapshot: 'S', basisRead: 'below replacement',
      basisClearsFloor: 'NO',
      killRisks: ['env'], preMortem: 'REC found post-close', openItems: ['Phase I'], confidence: 'medium',
    },
  };
  return (label) => (label in overrides ? overrides[label] : base[label]);
}

// --- Test 1: happy path — full 3-phase dispatch shape ---
console.log('Test 1: happy path dispatch shape (Recon -> 3 Verify -> Synthesize)');
{
  const { calls, phases, result } = await runWorkflow(SCRIPT, PROPERTY, standardCanned());
  const recon = calls.filter((c) => c.label === 'deal-recon');
  const verifies = calls.filter((c) => c.label.startsWith('verify:'));
  const synth = calls.filter((c) => c.label === 'synthesis');

  check('Recon dispatched exactly once', recon.length === 1);
  check('Recon uses agentType deal-recon', recon[0] && recon[0].agentType === 'deal-recon');
  check('Recon prompt carries the property brief', recon[0] && recon[0].prompt.includes(PROPERTY));
  // Ratified doctrine (RCT v03, 2026-07-14; memory standards.md Part A): all-in basis
  // (price + 2% closing + CapEx + lease-up carry) vs the vintage-ramp floor, 65% at/below 1995 ->
  // 60% at/above 2005, as a discount below the RCT LOW. The retired ~25% floor must not return.
  const RAMP = ['65% at/below 1995', '60% at/above 2005', 'replacement LOW', 'price + 2% closing + CapEx + lease-up carry'];
  check('Recon prompt states the ratified vintage-ramp floor + >8% yield', recon[0] && RAMP.every((s) => recon[0].prompt.includes(s)) && recon[0].prompt.includes('>8%'));
  check('Recon prompt does not carry the retired 25% floor', recon[0] && !/25\s*%|25 percent/.test(recon[0].prompt));
  {
    const lens = calls.find((c) => c.label === 'verify:comps-basis');
    check('comps-basis lens states the ratified vintage-ramp floor', !!lens && RAMP.every((s) => lens.prompt.includes(s)));
    check('comps-basis lens does not carry the retired 25% floor', !!lens && !/25\s*%|25 percent/.test(lens.prompt));
  }

  check('exactly 3 verify lenses dispatched', verifies.length === 3);
  check('verify lenses use agentType Explore', verifies.every((c) => c.agentType === 'Explore'));
  check('verify labels are the 3 named lenses', ['verify:comps-basis', 'verify:functional-environmental', 'verify:demand-leaseup'].every((l) => verifies.some((c) => c.label === l)));
  check('verify prompts carry the recon brief JSON', verifies.every((c) => c.prompt.includes('"verdict": "PURSUE"')));
  check('verify prompts carry the property brief', verifies.every((c) => c.prompt.includes(PROPERTY)));
  check('verify prompts instruct refuting, not trusting, the recon', verifies.every((c) => /refute/i.test(c.prompt)));

  check('Synthesis dispatched exactly once, after Verify', synth.length === 1);
  check('Synthesis prompt carries recon brief + verifications JSON', synth[0] && synth[0].prompt.includes('"verdict": "PURSUE"') && synth[0].prompt.includes('lensVerdict'));
  check('Synthesis prompt states basis discipline for the final verdict', synth[0] && /replacement/.test(synth[0].prompt));
  check('Synthesis PURSUE rule keys on clearing the vintage-ramp floor, not any below-replacement basis',
    synth[0] && /clears the vintage-ramp floor \(65% at\/below 1995 -> 60% at\/above 2005/.test(synth[0].prompt)
      && !/below-replacement OR/i.test(synth[0].prompt) && !/25\s*%/.test(synth[0].prompt));
  // Decision 2026-11-08 (Gabriel): missing the floor caps the deal at NEEDS_MORE regardless of
  // upside. Value-add upside is no longer an alternative route to PURSUE.
  check('Synthesis prompt no longer offers value-add upside as an alternative route to PURSUE',
    synth[0] && !/OR clear value-add upside/i.test(synth[0].prompt) && !/OR[^.;]{0,40}value-add[^.;]{0,40}-> PURSUE/i.test(synth[0].prompt));
  check('Synthesis prompt states a floor miss caps the verdict at NEEDS_MORE regardless of upside',
    synth[0] && /misses the vintage-ramp floor[^.]*NEEDS_MORE[^.]*regardless of (any )?value-add upside/i.test(synth[0].prompt));
  check('Recon prompt does not invite PURSUE on a floor miss with value-add',
    recon[0] && /floor miss caps the recommendation at NEEDS_MORE/i.test(recon[0].prompt));

  check('phases fired Recon, Verify, Synthesize in order', JSON.stringify(phases) === JSON.stringify(['Recon', 'Verify', 'Synthesize']));

  check('dead verifier (null) dropped from verifierCount', result.verifierCount === 2);
  check('anyFlip true when a surviving verifier flips', result.anyFlip === true);
  check('reconSoloVerdict reflects the recon-only recommendation', result.reconSoloVerdict === 'PURSUE');
  check('final brief is the synthesis output verbatim', result.brief && result.brief.verdict === 'NEEDS_MORE');
  check('no cap recorded when the synthesis is not PURSUE', result.verdictCap === null);
  check('property field is the brief\'s first line only', result.property === PROPERTY.split('\n')[0]);
}

// --- Test 1b: deterministic floor cap on the synthesized verdict ---
// The prompt is advisory; the cap is enforced in code so a synthesizer that still says PURSUE on
// a floor miss (or without establishing the floor) cannot reach Gabriel as PURSUE.
console.log('Test 1b: PURSUE without a cleared vintage-ramp floor is capped at NEEDS_MORE');
{
  const synthWith = (verdict, basisClearsFloor) => standardCanned({
    synthesis: {
      verdict, oneLineThesis: 'value-add story', snapshot: 'S', basisRead: 'fair, short of floor',
      ...(basisClearsFloor === undefined ? {} : { basisClearsFloor }),
      killRisks: [], preMortem: 'paid up for upside', openItems: ['rent comps'], confidence: 'medium',
    },
  });
  for (const floor of ['NO', 'UNKNOWN', undefined]) {
    const { result } = await runWorkflow(SCRIPT, PROPERTY, synthWith('PURSUE', floor));
    const tag = 'basisClearsFloor=' + JSON.stringify(floor);
    check(tag + ': PURSUE capped to NEEDS_MORE', result.brief && result.brief.verdict === 'NEEDS_MORE');
    check(tag + ': cap is recorded (from/to/reason)', !!result.verdictCap && result.verdictCap.from === 'PURSUE'
      && result.verdictCap.to === 'NEEDS_MORE' && /floor/i.test(result.verdictCap.reason || ''));
    check(tag + ': ledger row draft carries the capped verdict', typeof result.ledgerRowDraft === 'string'
      && result.ledgerRowDraft.includes('| NEEDS_MORE |') && !result.ledgerRowDraft.includes('| PURSUE |'));
    check(tag + ': cap opens an item to re-test basis against the floor', result.brief && result.brief.openItems.some((i) => /floor/i.test(i)));
  }
  {
    const { result } = await runWorkflow(SCRIPT, PROPERTY, synthWith('PURSUE', 'YES'));
    check('basisClearsFloor=YES: PURSUE stands', result.brief && result.brief.verdict === 'PURSUE');
    check('basisClearsFloor=YES: no cap recorded', result.verdictCap === null);
  }
  for (const v of ['PASS', 'NEEDS_MORE']) {
    const { result } = await runWorkflow(SCRIPT, PROPERTY, synthWith(v, 'NO'));
    check(v + ' on a floor miss is left untouched (cap only lowers PURSUE)', result.brief && result.brief.verdict === v && result.verdictCap === null);
  }
  {
    const { calls } = await runWorkflow(SCRIPT, PROPERTY, standardCanned());
    const synth = calls.find((c) => c.label === 'synthesis');
    check('Synthesis prompt asks for basisClearsFloor', !!synth && /basisClearsFloor/.test(synth.prompt));
  }
  {
    const src = readFileSync(SCRIPT, 'utf8');
    check('BRIEF_SCHEMA requires basisClearsFloor (YES/NO/UNKNOWN)',
      /basisClearsFloor:\{type:'string', enum:\['YES','NO','UNKNOWN'\]\}/.test(src)
        && /required:\[[^\]]*'basisClearsFloor'[^\]]*\]/.test(src.slice(src.indexOf('const BRIEF_SCHEMA'))));
  }
  {
    // the original synthesis object must not be mutated (it is the agent's raw output)
    const raw = { verdict: 'PURSUE', oneLineThesis: 't', snapshot: 'S', basisRead: 'b', basisClearsFloor: 'NO',
      killRisks: [], preMortem: 'p', openItems: [], confidence: 'low' };
    const { result } = await runWorkflow(SCRIPT, PROPERTY, standardCanned({ synthesis: raw }));
    check('raw synthesis object not mutated by the cap', raw.verdict === 'PURSUE' && raw.openItems.length === 0 && result.brief !== raw);
  }
}

// --- Test 2: args as {property: "..."} object form ---
console.log('Test 2: object-form args ({ property }) accepted equivalently to a plain string');
{
  const { calls } = await runWorkflow(SCRIPT, { property: PROPERTY }, standardCanned());
  const recon = calls.find((c) => c.label === 'deal-recon');
  check('object-form args still reaches the recon prompt', !!recon && recon.prompt.includes(PROPERTY));
}

// --- Test 3: empty/missing args short-circuits with zero agent dispatches ---
console.log('Test 3: empty args short-circuits before any dispatch');
for (const bad of ['', '   ', undefined, {}]) {
  const { calls, result } = await runWorkflow(SCRIPT, bad, standardCanned());
  check('args=' + JSON.stringify(bad) + ': zero agent calls dispatched', calls.length === 0);
  check('args=' + JSON.stringify(bad) + ': returns an error object', !!result && typeof result.error === 'string');
}

// --- Test 4: recon agent death short-circuits before Verify/Synthesize ---
console.log('Test 4: recon agent death short-circuits the rest of the pipeline');
{
  const { calls, result } = await runWorkflow(SCRIPT, PROPERTY, standardCanned({ 'deal-recon': null }));
  check('only the recon call was dispatched', calls.length === 1 && calls[0].label === 'deal-recon');
  check('fallback verdict is NEEDS_MORE', result.verdict === 'NEEDS_MORE');
  check('fallback carries a re-run instruction', /re-run/i.test(result.preMortem) === false && Array.isArray(result.openItems) && result.openItems.some((i) => /re-run/i.test(i)));
}

console.log(failures.length === 0 ? '\nALL TESTS PASSED' : '\nFAILURES: ' + failures.length);
process.exit(failures.length === 0 ? 0 : 1);
