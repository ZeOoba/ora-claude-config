export const meta = {
  name: 'cc-eval-plan-premortem',
  description: 'Phases 2-4: evaluation vs goals + master-plan matrix → extended improvement plan (tiered + data-flywheel) → adversarial pre-mortem → hardened plan + pressure-tested Tier-A selection',
  phases: [
    { title: 'Evaluate', detail: 'big-picture scorecard vs ORA goals, validate the master-plan matrix' },
    { title: 'Plan', detail: 'extend the roadmap; tier every item; design-only data flywheel' },
    { title: 'PreMortem', detail: '3 red-teamers attack plan + architecture' },
    { title: 'Harden', detail: 'revise into the hardened plan + Tier-A targets' },
    { title: 'Validate', detail: '2 validators pressure-test the plan and the Tier-A safety' },
  ],
}

// Reusable: pass the repo/worktree path via Workflow args, e.g. { worktree: 'C:/path/to/wt' }.
const WT = (typeof args === 'object' && args && args.worktree) || 'C:/Users/Owner/oxford-command-center';
const ARTIFACTS = 'Read these from the worktree before answering: ' + WT + '/_run/AUDIT-REPORT.md (the ranked 37-finding audit), ' + WT + '/_run/confirmed-findings.json (structured findings w/ file:line, severity, riskTierHint), and the ratified master plan ' + WT + '/docs/superpowers/specs/2026-06-13-ora-intelligence-platform-master-plan.md. Also available: the PFI architecture spec, acquisition-scorecard-contract, calibration-log-design, hurdle-rate-governor-proposal in the same specs/ dir, and architecture/{system-overview,coding-standards,database-schema}.md.';

const GROUND = [
  'BASELINE = origin/main @ 823574d (worktree ' + WT + '). ORA = private-family-office shallow-bay industrial; goals in PRIORITY order: acquisition velocity > ops optimization > institutional quality > comms/brand > knowledge capture; ~$60M AUM → $700-800M over 30-40 yrs. Governor surface = config/acquisition-ruleset.v1.proposed.json (un-ratified, fail-closed; DSCR 1.25 / LTV 40 are governor constants). ALREADY-DONE (do not re-plan): F1 NOI A↔B reconcile, get_macro FRED tool, acquisition scorecard engine, parser-version re-ingest.',
  'The 2026-06-13 master plan is the RATIFIED BASELINE (current-state, F1-F13 value matrix, gap list, pre-mortem PFR-1..7). Work is DELTA-ONLY: VALIDATE/EXTEND it, do not re-derive or silently overwrite it. A material contradiction with the ratified matrix is a DEFER-and-surface event.',
  'ANALYTICS CONTRACT (the digestibility bar): every analytic = answer-first → why → do → supporting KPIs, with confidence + provenance(inputs_version), computed by a pure tested deterministic function (LLM narrates, never computes). DESIGN CONTRACT: conform to src/tokens/theme.css + ORA style guide (Navy #1B2A4A / Gold #C9A96E / Parchment #F5F3EF; EB Garamond / DM Sans / IBM Plex Mono); no ad-hoc colors/fonts.',
  'RISK TIERS: GREEN = additive-only, zero governor/financial-constant/confidential/external/deploy surface, fully test-coverable. YELLOW = touches financial math/mechanism but not a frozen constant/ratified slot. RED = governor constant, confidential, external send, deploy/mirror, destructive/irreversible, or architecture-breaking.',
].join('\n');

phase('Evaluate');
const EVAL_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    scorecardMarkdown: { type: 'string' },
    dimensionScores: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      dimension: { type: 'string' }, score: { type: 'string', description: '0-10 with one-line basis' }, rationale: { type: 'string' } },
      required: ['dimension', 'score', 'rationale'] } },
    topGaps: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      gap: { type: 'string' }, goalImpact: { type: 'string' }, evidence: { type: 'string' }, leverage: { type: 'string', enum: ['high', 'medium', 'low'] } },
      required: ['gap', 'goalImpact', 'evidence', 'leverage'] } },
    matrixAdjustments: { type: 'string', description: 'how the audit validates/adjusts the master-plan F1-F13 matrix; flag any now-stale item' },
  },
  required: ['scorecardMarkdown', 'dimensionScores', 'topGaps', 'matrixAdjustments'],
};
const evalRes = await agent(
  'You are the Phase-2 EVALUATION pass for the ORA command center. ' + ARTIFACTS + '\n\n=== GROUND ===\n' + GROUND + '\n\nSynthesize a holistic assessment of the SETUP + CODE vs the ORA goals. Score the architecture 0-10 on EXACTLY these 5 dimensions: acquisition-velocity, ops-optimization, institutional-quality, analytics-digestibility, learn-from-data. VALIDATE/ADJUST the master plan F1-F13 value matrix against the 37 audit findings (do not re-derive it). Name the 5-8 HIGHEST-LEVERAGE gaps (cross-checked against ALREADY-DONE — anything on origin/main is not a gap). Output an Evaluation Scorecard (markdown) + the structured fields.',
  { label: 'evaluate', phase: 'Evaluate', model: 'opus', schema: EVAL_SCHEMA }
);
log('Evaluation done: ' + evalRes.dimensionScores.map((d) => d.dimension + '=' + d.score).join(' · '));

phase('Plan');
const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    planMarkdown: { type: 'string' },
    initiatives: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      id: { type: 'string' }, title: { type: 'string' }, goal: { type: 'string' },
      value: { type: 'string', enum: ['high', 'medium', 'low'] }, effort: { type: 'string', enum: ['S', 'M', 'L', 'XL'] },
      dependsOn: { type: 'array', items: { type: 'string' } }, successCriteria: { type: 'string' },
      testStrategy: { type: 'string' }, tier: { type: 'string', enum: ['GREEN', 'YELLOW', 'RED'] },
      addressesFindings: { type: 'array', items: { type: 'string' } } },
      required: ['id', 'title', 'goal', 'value', 'effort', 'dependsOn', 'successCriteria', 'testStrategy', 'tier', 'addressesFindings'] } },
    flywheelDesign: { type: 'string', description: 'the DESIGN-ONLY self-improvement/data-flywheel: telemetry, recurring re-audit, calibration loop (build on calibration-log-design), feedback capture, insight layer — with the closed-loop done-definition (append-only verdict log w/ inputs_version → outcome resolution → predicted-vs-actual measurement → re-ratification PROPOSAL that stops for Gabriel, never auto-applies). This run DESIGNS it; does not build/register it.' },
  },
  required: ['planMarkdown', 'initiatives', 'flywheelDesign'],
};
const planRes = await agent(
  'You are the Phase-3 PLAN pass (writing-plans discipline). ' + ARTIFACTS + '\n\n=== GROUND ===\n' + GROUND + '\n\n=== EVALUATION (just produced) ===\n' + JSON.stringify({ dimensionScores: evalRes.dimensionScores, topGaps: evalRes.topGaps, matrixAdjustments: evalRes.matrixAdjustments }) + '\n\nProduce an EXTENSIVE phased improvement roadmap that EXTENDS the master plan (does not replace it). Every initiative: tied to a goal, value+effort, dependency order, success criteria, test strategy, and pre-classified GREEN/YELLOW/RED. Sequence by dependency and value/effort. Fold the 37 audit findings into initiatives (reference finding ids). Include the DESIGN-ONLY data-flywheel workstream with its closed-loop done-definition. Output planMarkdown + structured initiatives + flywheelDesign.',
  { label: 'plan', phase: 'Plan', model: 'opus', schema: PLAN_SCHEMA }
);
log('Plan: ' + planRes.initiatives.length + ' initiatives (' + planRes.initiatives.filter((i) => i.tier === 'GREEN').length + ' GREEN).');

phase('PreMortem');
const REDTEAM_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { objections: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    target: { type: 'string', description: 'which initiative/phase/assumption' },
    failureMode: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }, fix: { type: 'string' } },
    required: ['target', 'failureMode', 'severity', 'fix'] } } },
  required: ['objections'],
};
const redLenses = [
  { k: 'sequencing-deps', b: 'Attack sequencing & dependencies: wrong order, missing prerequisite, an initiative that needs the predecessor branch (feat/pfi-phase-b3) or a not-yet-built engine, the migration-002 collision between local main and origin/main, and any plan item that collides with another writer or the active parallel session.' },
  { k: 'governor-confidential', b: 'Attack governor/confidentiality/invariant tripwires: any initiative that would (even accidentally) write a governor constant, ratify a weight, consume live confidential-deal data, or egress to an external/deploy surface. Verify the flywheel telemetry truly never persists confidential terms. Verify no Tier classification is too lenient.' },
  { k: 'value-realism-alreadydone', b: 'Attack value/effort realism and already-done collisions: initiatives that re-build something already on origin/main, over-estimated value, under-estimated effort/blast-radius, or that contradict the ratified master-plan matrix without surfacing it. Also: does the plan actually move the priority-1 goal (acquisition velocity) and deliver digestible+decision-grade analytics + a REAL closed-loop flywheel (not write-only)?' },
];
const redteam = await parallel(redLenses.map((l) => () =>
  agent('You are a Phase-4 RED-TEAMER. ' + ARTIFACTS + '\n\n=== GROUND ===\n' + GROUND + '\n\nLENS: ' + l.b + '\n\n=== PLAN UNDER ATTACK ===\n' + JSON.stringify({ initiatives: planRes.initiatives, flywheelDesign: planRes.flywheelDesign }) + '\n\nReturn concrete objections (target, failureMode, severity, fix). Be adversarial; find real failure modes, not nitpicks.',
    { label: 'redteam:' + l.k, phase: 'PreMortem', model: 'opus', schema: REDTEAM_SCHEMA })
));
const objections = redteam.filter(Boolean).flatMap((r) => r.objections);
log('Pre-mortem: ' + objections.length + ' objections (' + objections.filter((o) => o.severity === 'critical' || o.severity === 'high').length + ' crit/high).');

phase('Harden');
const HARDENED_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    hardenedPlanMarkdown: { type: 'string', description: 'the full hardened improvement plan, ready to commit to docs/superpowers/plans/' },
    residualRisks: { type: 'array', items: { type: 'string' } },
    tierATargets: { type: 'array', description: 'the ≤2 implementation targets for THIS run — additive-only GREEN OR a single-location correctness fix with a written-first failing test; NEVER a governor constant/confidential/external; one-review-sized', items: { type: 'object', additionalProperties: false, properties: {
      id: { type: 'string' }, title: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
      tier: { type: 'string', enum: ['GREEN', 'YELLOW'] }, changeSketch: { type: 'string' }, testPlan: { type: 'string' },
      whySafe: { type: 'string', description: 'why this is additive/safe, touches no governor/confidential/external surface, fits one review' }, addressesFindings: { type: 'array', items: { type: 'string' } } },
      required: ['id', 'title', 'files', 'tier', 'changeSketch', 'testPlan', 'whySafe', 'addressesFindings'] } },
  },
  required: ['hardenedPlanMarkdown', 'residualRisks', 'tierATargets'],
};
const hardened = await agent(
  'You are the Phase-4 HARDENING pass. ' + ARTIFACTS + '\n\n=== GROUND ===\n' + GROUND + '\n\nRevise the plan to resolve EVERY critical/high objection (and as many med/low as cheaply possible). Then SELECT the Tier-A implementation targets for THIS unattended run under a HARD scope ceiling: AT MOST 2 items, one-review-sized PR, additive-only GREEN OR a single-location correctness fix with a written-first failing test that survives an adversarial refute pass; NEVER a governor constant, never confidential, never external/deploy. The two strongest candidates from the audit are likely (a) additive characterization/branch TESTS for the governor-surface acquisition engine and the NOI reconcile DB-join layer (rank12/rank13 — pure additive, zero behavior change, hardens financial-decision code), and (b) a tight YELLOW correctness fix such as the noi-variance phantom-shortfall (H5) or scenario-value basis-mix (H4) IF it can be fully test-gated. Pick the best ≤2; justify each. Everything else (incl. all RED items H1/rank8/governor) goes to a HUMAN-RATIFICATION-REQUIRED backlog inside the plan. Output hardenedPlanMarkdown + tierATargets + residualRisks.\n\n=== OBJECTIONS TO RESOLVE ===\n' + JSON.stringify(objections),
  { label: 'harden', phase: 'Harden', model: 'opus', schema: HARDENED_SCHEMA }
);

phase('Validate');
const VAL_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { verdict: { type: 'string', enum: ['PASS', 'DEFECTS'] }, defects: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    title: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }, fix: { type: 'string' } }, required: ['title', 'severity', 'fix'] } } },
  required: ['verdict', 'defects'],
};
const valLenses = [
  { k: 'tierA-safety', b: 'ONLY validate the tierATargets. For EACH: re-open the cited files in the worktree and confirm the change is genuinely additive/safe (GREEN) or a correctly-scoped single-location fix with a real written-first failing test (YELLOW), touches NO governor constant/ratified slot/confidential/external/deploy surface, and fits one review. DEFECT if any target is mis-tiered, too large, or unsafe.' },
  { k: 'plan-completeness', b: 'Validate the hardened plan: does it resolve the crit/high objections, extend (not overwrite) the master plan, move acquisition-velocity first, and design a REAL closed-loop flywheel (verdict-log + outcome-resolution + measurement + stop-for-Gabriel proposal, not write-only)? Are all RED items (H1, rank8, governors) correctly in the ratification backlog and NOT in tierATargets?' },
];
const validations = await parallel(valLenses.map((v) => () =>
  agent('You are a Phase-4 VALIDATOR. ' + ARTIFACTS + '\n\nLENS: ' + v.b + '\n\nDefault to DEFECTS if you find any real problem; PASS only if genuinely clean.\n\n=== HARDENED PLAN + TIER-A TARGETS ===\n' + JSON.stringify({ tierATargets: hardened.tierATargets, residualRisks: hardened.residualRisks, planMarkdownHead: hardened.hardenedPlanMarkdown.slice(0, 6000) }),
    { label: 'validate:' + v.k, phase: 'Validate', model: 'opus', schema: VAL_SCHEMA })
));
const defects = validations.filter(Boolean).flatMap((v) => v.defects || []);
log('Validation: ' + defects.length + ' residual defects (' + defects.filter((d) => d.severity === 'critical' || d.severity === 'high').length + ' crit/high).');

return {
  evaluation: { scorecardMarkdown: evalRes.scorecardMarkdown, dimensionScores: evalRes.dimensionScores, topGaps: evalRes.topGaps, matrixAdjustments: evalRes.matrixAdjustments },
  plan: { hardenedPlanMarkdown: hardened.hardenedPlanMarkdown, initiatives: planRes.initiatives, flywheelDesign: planRes.flywheelDesign, residualRisks: hardened.residualRisks },
  tierATargets: hardened.tierATargets,
  premortem: { objectionCount: objections.length, objections },
  validation: { defects },
};
