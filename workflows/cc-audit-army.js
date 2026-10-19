export const meta = {
  name: 'cc-audit-army',
  description: 'Phase 1: 9-dimension read-only audit of a target repo/worktree (default oxford-command-center; to audit any other repo pass args.brief naming the repo and its purpose, plus args.worktree = its path if it is a git worktree/checkout the scouts should ground against) → mechanical verify → root-cause dedup → ranked Audit Report',
  phases: [
    { title: 'Orient', detail: 'a scout grounds the audit: cc mode refreshes the baseline sha + newly-landed already-done onto the curated ground truth; generic mode derives full ground truth + per-dimension focus' },
    { title: 'Audit', detail: '9 dimension agents fan out read-only over the worktree' },
    { title: 'Dedup', detail: 'merge findings by root cause, drop already-done' },
    { title: 'Verify', detail: 'independent agents re-open every cited file:line' },
    { title: 'Rank', detail: 'synthesize the ranked Audit Report' },
  ],
}

// Reusable: pass the repo/worktree path via Workflow args, e.g. { worktree: 'C:/path/to/wt' }.
// Two modes:
//   CC (default, no args.brief): curated oxford-command-center ground truth + baked focus paths
//     (descended from the pipeline that produced PR #28), with a Phase-0 refresh scout that re-derives
//     the baseline sha + newly-landed already-done each run — the curated list was compiled @ 823574d
//     and rots as main advances. Use for every command-center audit.
//   GENERIC (args.brief present): audits ANY repo. args.brief = 1-3 operator sentences (what the repo
//     is + audit intent). A Phase-0 Orient scout reads the repo and derives the ground truth +
//     per-dimension focus that are baked in for cc. E.g.
//     Workflow({ name: 'cc-audit-army', args: { worktree: 'C:/Users/Owner/ora-pm', brief: 'ORA property-management app: React + Supabase tenant portal.' } })
// Some harnesses deliver args as a JSON-ENCODED STRING (proven 2026-07-16, runs wf_ae4150f2-651 /
// wf_514f9699-d33): pre-guard it slipped past `typeof args === 'object'` and silently audited the
// default worktree. Self-parse a JSON string; fail closed on anything else.
if (typeof args === 'string') {
  try { args = JSON.parse(args); } catch (e) {
    throw new Error('args string is not valid JSON (' + e.message + ') — refusing to fall back to the default worktree (fail closed).');
  }
}
if (args !== undefined && args !== null && typeof args !== 'object') {
  throw new Error('args must be a JSON object, got ' + typeof args + ' — refusing to fall back to the default worktree (fail closed).');
}
const WT = (typeof args === 'object' && args && args.worktree) || 'C:/Users/Owner/oxford-command-center';
const BRIEF = (typeof args === 'object' && args && typeof args.brief === 'string' && args.brief.trim()) || null;
if (typeof args === 'object' && args && 'brief' in args && !BRIEF) {
  throw new Error('args.brief must be a non-empty string (got ' + typeof args.brief + ') — refusing to fall back to the baked oxford-command-center ground truth against ' + WT + ' (fail closed).');
}
const GENERIC = !!BRIEF;
// Report-header label only (prompts/reads still use WT). In brief mode without an explicit args.worktree the
// default command-center path is not the audited target, so label it from the brief instead of mislabelling.
const TARGET_LABEL = (GENERIC && !(typeof args === 'object' && args && args.worktree))
  ? '(target per args.brief; no args.worktree given, default path ' + WT + ' is NOT the audited target) ' + BRIEF.replace(/[\p{Cc}\p{Zl}\p{Zp}]+/gu, ' ').slice(0, 160)
  : WT;
// Optional model floor: e.g. { forceModel: 'opus' } pins every dispatch (orient/audit/dedup/verify/rank)
// to one model regardless of each dimension's default — for standing per-repo model-tier overrides
// (e.g. website-canonical work requires opus-only, never sonnet/haiku dispatch). No-op if omitted.
const FORCE_MODEL = (typeof args === 'object' && args && typeof args.forceModel === 'string' && args.forceModel.trim()) || null;
const modelFor = (m) => FORCE_MODEL || m;

const CONTRACT = [
  'UNATTENDED, READ-ONLY AUDIT. You are an audit subagent. Rules:',
  GENERIC
    ? '- You operate ONLY by reading files under the worktree ' + WT + ' (use Read/Grep/Glob). Do NOT write, edit, start any server or dev/preview process, run build/test/install commands, or run git mutations. Read-only git is fine (log/show/diff/status).'
    : '- You operate ONLY by reading files under the worktree ' + WT + ' (use Read/Grep/Glob). Do NOT write, edit, run the warehouse, start any server (npm run dev/preview is forbidden — WAL lock), or run git mutations. Read-only git is fine (log/show/diff/status).',
  '- NEVER pause/ask a human; NEVER act on a gated item — just REPORT it as a finding. Never paste a verbatim line containing an active confidential-deal term; redact/hash any deal identifier.',
  '- Every finding MUST carry a real file path (relative to the worktree root, e.g. ' + (GENERIC ? 'src/billing/invoice.ts' : 'server/warehouse/acquisition.ts') + '), a line number or range, and a VERBATIM excerpt you actually read at that location. A finding asserting ABSENCE of something must cite the exact Grep/Glob you ran that returned nothing. No finding without file-backed evidence.',
  '- Quality over quantity. Do not pad. Prefer fewer, real, high-signal findings over many speculative ones.',
].join('\n');

const GOVERNOR_CLAUSE = 'GOVERNOR/FINANCIAL discipline: DSCR 1.25 / LTV 40 / hurdle / scoring weights are governor constants — if you find a place that hardcodes or could mutate one, that is a HIGH finding, but you only REPORT it.';

// The curated cc ground truth was compiled at this sha. Only the baseline line and the NEWER line are
// refreshed per run (cc-refresh scout); the rest (delta-only framing, governor-surface intent) is
// hand-written knowledge a scout cannot re-derive — keep it curated.
const CC_CURATED_SHA = '823574d';
const ccGroundTruth = (refresh) => [
  'BASELINE = ' + refresh.baseline + ' (the worktree HEAD). This is the authoritative current state. The repo is a TS/React+Vite command center over a server/warehouse SQLite (WAL) layer for Oxford Realty Advisors (private-family-office industrial real estate; goals in priority order: acquisition velocity > ops optimization > institutional quality > comms/brand > knowledge capture; ~$60M AUM heading to $700-800M).',
  'Orient with: architecture/system-overview.md, architecture/coding-standards.md, architecture/database-schema.md, architecture/api-contracts.md, and the ratified master plan docs/superpowers/specs/2026-06-13-ora-intelligence-platform-master-plan.md.',
  'RATIFIED BASELINE: the 2026-06-13 master plan already encodes current-state, the F1-F13 value matrix, the gap list, and a pre-mortem. This audit is DELTA-ONLY: find what the master plan MISSED or what is actually WRONG in the code — NOT a re-derivation of the plan.',
  'ALREADY-DONE (do NOT report these as gaps/bugs-of-omission; they are DONE on this baseline): (a) F1 NOI A<->B reconciliation — server/warehouse/reconcile-noi.ts (CHANGELOG Phase 1c); (b) get_macro FRED agent tool — server/macro/ + server/ai (Phase 1b); (c) the acquisition scorecard contract + deterministic engine — server/warehouse/acquisition.ts, src/contracts/acquisition.ts, config/acquisition-ruleset.v1.proposed.json (fail-closed; scorecard v1.0 RATIFIED @ 31d872e — the commit after the curated sha — and the 8% unlevered-IRR hurdle governor ratified @ 3538282; verified 2026-07-16). The acquisition ruleset is the GOVERNOR SURFACE — do NOT propose changing ratified values; flag only real defects in the engine mechanism, fail-closed behavior, or contract.',
  'ALREADY-DONE — NEWER (landed after the curated list above, per the refresh scout; same rule, do NOT re-report as gaps): ' + refresh.newerAlreadyDone,
  GOVERNOR_CLAUSE,
].join('\n');

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          id: { type: 'string', description: 'short kebab slug unique within this agent' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          file: { type: 'string', description: 'path relative to worktree root' },
          line: { type: 'string', description: 'line number or range' },
          excerpt: { type: 'string', description: 'verbatim code read at that location, or the grep that returned nothing for an absence claim' },
          evidence: { type: 'string', description: 'why this is a real defect' },
          goalImpact: { type: 'string', description: 'which ORA goal it helps or hurts' },
          fix: { type: 'string', description: 'fix sketch' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['id', 'title', 'severity', 'file', 'line', 'excerpt', 'evidence', 'goalImpact', 'fix', 'confidence'],
      },
    },
    coverageNote: { type: 'string', description: 'what you covered and any area you could NOT cover (explicit gaps)' },
  },
  required: ['findings', 'coverageNote'],
};

// Each dimension carries two briefs: `cc` (verbatim, the proven oxford-command-center lens with baked
// focus paths) and `gen` (repo-agnostic lens; focus paths are supplied by the Orient scout at runtime).
const DIMENSIONS = [
  {
    key: 'correctness', model: 'opus',
    cc: 'Correctness & logic bugs: wrong conditionals, off-by-one, error-swallowing, unhandled nulls/NaN, race conditions, incorrect async, mis-wired data flow, broken invariants. Focus on server/warehouse, server/ai, server/alerts, src/analytics, src/data, src/modules.',
    gen: 'Correctness & logic bugs: wrong conditionals, off-by-one, error-swallowing, unhandled nulls/NaN, race conditions, incorrect async, mis-wired data flow, broken invariants.',
  },
  {
    key: 'dead-duplicate', model: 'sonnet',
    cc: 'Dead code, unused exports/vars, unreachable branches, and DUPLICATION / copy-paste drift across modules, contracts, charts, and the warehouse parsers. Identify concrete consolidation targets (same logic in 2+ places).',
    gen: 'Dead code, unused exports/vars, unreachable branches, and DUPLICATION / copy-paste drift across modules. Identify concrete consolidation targets (same logic in 2+ places).',
  },
  {
    key: 'performance', model: 'sonnet',
    cc: 'Inefficiency & performance: needless React re-renders, missing mem_o/keys, N+1 or repeated SQLite queries, full-table scans, repeated parsing, large synchronous work on the main path, bundle weight, and any WAL write-contention risk. Focus on src (render paths) and server/warehouse (query paths).',
    gen: 'Inefficiency & performance: needless recomputation or re-renders, N+1 or repeated queries, full scans, repeated parsing, large synchronous work on hot paths, blocking I/O, bundle/asset weight.',
  },
  {
    key: 'data-pipeline', model: 'opus',
    cc: 'Data-pipeline & contract integrity: schema/contract drift between src/contracts and the warehouse/workbook parsers, basis/units mismatches ($/SF, ownership %, NOI spine A vs B), silent coercions, provenance/staleness handling, migration ordering, ingest idempotency. This is financial data — be rigorous. Focus server/warehouse (ingest, parse, raw-store, migrations), server/workbook, src/contracts.',
    gen: 'Data & contract integrity: schema/contract drift between producers and consumers, basis/units mismatches, silent coercions, provenance/staleness handling, migration ordering, ingest/write idempotency. Wherever financial data flows, be rigorous.',
  },
  {
    key: 'financial-math', model: 'opus',
    cc: 'ADVERSARIAL FINANCIAL-MATH REFUTER: try to BREAK every financial computation — NOI, cap rate, DSCR, LTV, yield, scoring, acquisition ranking, reconciliation tolerances, drift attribution. Look for sign errors, denominator/zero-division, rounding that compounds, basis mixing (100% vs Oxford-share), tolerance thresholds that mislabel, and any path where the engine could rank/score on un-ratified or empty governor values instead of failing closed. Focus server/warehouse/acquisition.ts, reconcile-noi.ts, ingest.ts, src/analytics, src/contracts/acquisition.ts.',
    gen: 'ADVERSARIAL FINANCIAL-MATH REFUTER: try to BREAK every financial, numeric, or scoring computation — sign errors, denominator/zero-division, rounding that compounds, basis mixing, tolerance thresholds that mislabel, and any path that computes on empty/un-ratified/default config instead of failing closed. If the repo has little or no financial code, audit whatever numeric/scoring/date logic exists and say so in coverageNote.',
  },
  {
    key: 'security-confidential', model: 'opus',
    cc: 'Security, secrets & confidentiality egress: secrets/keys in source or committed config, unsafe env handling, the deploy/mirror/bake path (scripts/bake-mirror.ts, build:mirror) leaking sensitive data to a static surface, any place active-deal/confidential terms could reach a committed file, log, snapshot, or the mirror, missing redaction, unsafe HTML/injection, overbroad CORS/headers. Focus server/*, scripts/bake-mirror.ts, functions/, server/ai (prompt-injection of agent tools).',
    gen: 'Security, secrets & confidentiality egress: secrets/keys in source or committed config, unsafe env handling, any deploy/publish/export path leaking sensitive or confidential-deal data to an external or static surface, missing redaction, unsafe HTML/injection, overbroad CORS/headers, prompt-injection of any agent/LLM tooling.',
  },
  {
    key: 'test-coverage', model: 'sonnet',
    cc: 'Test-coverage gaps that matter: financial-decision code paths (acquisition scoring, NOI reconcile, DSCR/LTV, drift) lacking tests, untested error/edge branches, tests that assert on mocks rather than behavior, missing fail-closed assertions on governor emptiness. Map gaps to risk. Focus tests/unit, tests/e2e vs server/warehouse + src/analytics.',
    gen: 'Test-coverage gaps that matter: decision-critical code paths lacking tests, untested error/edge branches, tests that assert on mocks rather than behavior, missing fail-closed assertions. Map gaps to risk.',
  },
  {
    key: 'architecture', model: 'opus',
    cc: 'Architecture & coupling smells: god-files, leaky abstractions, modules reaching across boundaries, business logic in UI components, duplicated source-of-truth, inconsistent data-access patterns, fragile cross-layer coupling that will impede the master-plan roadmap (acquisitions/debt/leasing/forecast/capital-allocation). Assess whether the structure can ABSORB the planned engines. Focus the whole tree, esp. src/modules, src/data, server/warehouse, server/brain.',
    gen: 'Architecture & coupling smells: god-files, leaky abstractions, modules reaching across boundaries, business logic in UI components, duplicated source-of-truth, inconsistent data-access patterns, fragile cross-layer coupling that will impede planned growth. Assess whether the structure can ABSORB what the operator brief says is coming.',
  },
  {
    key: 'analytics-ux', model: 'sonnet',
    cc: 'Analytics & UX quality vs the digestibility bar (answer-first -> why -> do -> supporting KPIs, with confidence + provenance). Find analytics that dump tables without a verdict, numbers without provenance/confidence, narration that could be computing values instead of reading deterministic ones, inconsistent design tokens (non-tokenized colors/fonts vs src/tokens/theme.css), and modules that bury the decision. Focus src/modules, src/analytics, src/charts, src/primitives, src/tokens.',
    gen: 'Output & UX quality: user-facing surfaces that dump data without a verdict, numbers without provenance/confidence, inconsistent design tokens or ad-hoc styling vs the repo\'s own token/style system, flows that bury the decision. If the repo has no UI, audit CLI/report/log output quality instead and say so in coverageNote.',
  },
];

let GROUND_TRUTH;
let FOCUS = null;
phase('Orient');
if (GENERIC) {
  const ORIENT_SCHEMA = {
    type: 'object', additionalProperties: false,
    properties: {
      repoSummary: { type: 'string', description: '2-4 sentences: what the repo is, stack, entry points, how it is built/run/tested' },
      baseline: { type: 'string', description: 'current HEAD as "branch @ short-sha" from read-only git log' },
      orientationDocs: { type: 'string', description: 'comma-separated repo-relative paths auditors should read first (README, architecture docs, specs, CHANGELOG); "none found" if none' },
      alreadyDone: { type: 'string', description: 'work already implemented/specced on this baseline that auditors must NOT re-report as gaps (from CHANGELOG/specs/recent commits); "none identified" if none' },
      focus: {
        type: 'object', additionalProperties: false,
        properties: {
          correctness: { type: 'string' }, 'dead-duplicate': { type: 'string' }, performance: { type: 'string' },
          'data-pipeline': { type: 'string' }, 'financial-math': { type: 'string' }, 'security-confidential': { type: 'string' },
          'test-coverage': { type: 'string' }, architecture: { type: 'string' }, 'analytics-ux': { type: 'string' },
        },
        required: ['correctness', 'dead-duplicate', 'performance', 'data-pipeline', 'financial-math', 'security-confidential', 'test-coverage', 'architecture', 'analytics-ux'],
        description: 'per-dimension: concrete repo-relative paths/areas that dimension should concentrate on; "n/a — <why>" where a dimension barely applies',
      },
      cautions: { type: 'string', description: 'repo-specific hazards for read-only auditors (locks, generated/vendored dirs to skip, huge files); "none"' },
    },
    required: ['repoSummary', 'baseline', 'orientationDocs', 'alreadyDone', 'focus', 'cautions'],
  };
  const orient = await agent(
    CONTRACT + '\n\nYou are the ORIENT scout for a repo-generic audit. The audit army (9 read-only dimension agents: ' + DIMENSIONS.map((d) => d.key).join(', ') + ') knows NOTHING about this repo yet — your output is their entire ground truth, so report only what you actually read; never guess.\n\nOPERATOR BRIEF: ' + BRIEF + '\n\nRead the repo at ' + WT + ' — README, package/build manifests, docs/, CHANGELOG, spec/architecture files, directory structure, and read-only git log — then return the structured orientation fields, including a focus entry for EVERY dimension.',
    { label: 'orient', phase: 'Orient', model: modelFor('opus'), schema: ORIENT_SCHEMA }
  );
  if (!orient) throw new Error('Orient scout failed/skipped — refusing to audit ' + WT + ' without repo ground truth (fail closed).');
  FOCUS = orient.focus || {};
  GROUND_TRUTH = [
    'OPERATOR BRIEF: ' + BRIEF,
    'BASELINE = ' + orient.baseline + ' (the worktree HEAD). This is the authoritative current state. ' + orient.repoSummary,
    'Orient with: ' + orient.orientationDocs,
    'ALREADY-DONE (do NOT report these as gaps/bugs-of-omission; they are DONE on this baseline): ' + orient.alreadyDone,
    GOVERNOR_CLAUSE,
    'CAUTIONS: ' + orient.cautions,
  ].join('\n');
} else {
  // CC refresh: the curated ground truth rots as oxford-command-center main advances (every merge makes
  // the baked baseline staler and the already-done list less complete → auditors re-report non-gaps).
  // Refresh baseline + newly-landed work per run; curated knowledge and focus paths stay baked.
  const CC_REFRESH_SCHEMA = {
    type: 'object', additionalProperties: false,
    properties: {
      baseline: { type: 'string', description: 'current worktree HEAD as "branch @ short-sha" from read-only git log' },
      newerAlreadyDone: { type: 'string', description: 'work implemented/specced after the curated-list sha (from CHANGELOG/specs/read-only git log), plus corrections to any curated claim no longer true on this HEAD; "none newer" if none' },
    },
    required: ['baseline', 'newerAlreadyDone'],
  };
  const refresh = await agent(
    CONTRACT + '\n\nYou are the CC REFRESH scout. The audit army\'s curated command-center ground truth was compiled at origin/main @ ' + CC_CURATED_SHA + ' and goes stale as work merges — refresh ONLY (1) the current baseline and (2) work landed since. From the worktree at ' + WT + ': (1) run read-only git log to report the worktree HEAD as "branch @ short-sha"; (2) read CHANGELOG.md, docs/superpowers/specs/, and read-only git log ' + CC_CURATED_SHA + '..HEAD to list work implemented/specced AFTER ' + CC_CURATED_SHA + ' that auditors must NOT re-report as gaps/bugs-of-omission. Do NOT re-list the curated items (F1 NOI reconcile, get_macro FRED tool, acquisition scorecard engine) — but if a curated claim is no longer true on this HEAD (e.g. the acquisition ruleset has since been ratified), note the correction. Report only what you actually read; never guess. If ' + CC_CURATED_SHA + ' is not an ancestor of HEAD, say so and derive what you can from the last 30 commits.',
    { label: 'cc-refresh', phase: 'Orient', model: modelFor('opus'), schema: CC_REFRESH_SCHEMA }
  );
  if (!refresh) throw new Error('CC refresh scout failed/skipped — refusing to audit ' + WT + ' against the stale curated baseline @ ' + CC_CURATED_SHA + ' (fail closed).');
  GROUND_TRUTH = ccGroundTruth(refresh);
}

const briefFor = (d) => GENERIC
  ? d.gen + '\nFocus areas for THIS repo (from the Orient scout): ' + ((FOCUS && FOCUS[d.key]) || 'none provided — derive them from the repo structure yourself.')
  : d.cc;

phase('Audit');
const audits = await parallel(DIMENSIONS.map((d) => () =>
  agent(
    CONTRACT + '\n\n=== GROUND TRUTH ===\n' + GROUND_TRUTH + '\n\n=== YOUR DIMENSION: ' + d.key + ' ===\n' + briefFor(d) + '\n\nWorktree root: ' + WT + '\nReturn structured findings (file-backed, verbatim excerpts) + a coverageNote.',
    { label: 'audit:' + d.key, phase: 'Audit', model: modelFor(d.model), schema: FINDINGS_SCHEMA }
  ).then((r) => ({ dimension: d.key, ...(r || { findings: [], coverageNote: 'AGENT FAILED' }) }))
));
const rawFindings = audits.flatMap((a) => (a.findings || []).map((f) => ({ ...f, dimension: a.dimension })));
const coverageNotes = audits.map((a) => a.dimension + ': ' + (a.coverageNote || 'none'));
log('Audit army returned ' + rawFindings.length + ' raw findings across ' + audits.length + ' dimensions.');

phase('Dedup');
const DEDUP_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    merged: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          file: { type: 'string' }, line: { type: 'string' }, excerpt: { type: 'string' },
          evidence: { type: 'string' }, goalImpact: { type: 'string' }, fix: { type: 'string' },
          contributingDimensions: { type: 'array', items: { type: 'string' } },
          alreadyDone: { type: 'boolean', description: 'true if this is already implemented/specced on the baseline (then exclude from new work)' },
        },
        required: ['id', 'title', 'severity', 'file', 'line', 'excerpt', 'evidence', 'goalImpact', 'fix', 'contributingDimensions', 'alreadyDone'],
      },
    },
    droppedAlreadyDone: { type: 'array', items: { type: 'string' }, description: 'titles dropped as already-done/already-specced' },
  },
  required: ['merged', 'droppedAlreadyDone'],
};
const DEDUP_CROSSCHECK = GENERIC
  ? 'cross-check the ALREADY-DONE list in the ground truth; you may Read the worktree at ' + WT + ' to confirm'
  : 'cross-check the ALREADY-DONE list + docs/superpowers/specs/* + the master plan; you may Read the worktree at ' + WT + ' to confirm';
const dedup = await agent(
  CONTRACT + '\n\n=== GROUND TRUTH ===\n' + GROUND_TRUTH + '\n\nYou are the DEDUP/RECONCILE pass. Below are raw findings from 9 audit dimensions. MERGE findings that share a root cause (same file-range + same defect) into ONE entry, recording contributingDimensions. Then mark alreadyDone=true for any finding that is actually implemented/specced on the baseline (' + DEDUP_CROSSCHECK + '). Keep every distinct real defect. Do not invent new findings.\n\n=== RAW FINDINGS (JSON) ===\n' + JSON.stringify(rawFindings),
  { label: 'dedup-reconcile', phase: 'Dedup', model: modelFor('opus'), schema: DEDUP_SCHEMA }
);
if (!dedup) throw new Error('Dedup/reconcile agent failed — aborting rather than ranking unmerged raw findings (fail closed).');
const candidates = (dedup.merged || []).filter((f) => !f.alreadyDone);
log('Deduped to ' + candidates.length + ' candidate findings (' + (dedup.droppedAlreadyDone || []).length + ' dropped as already-done).');

phase('Verify');
const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          id: { type: 'string' },
          status: { type: 'string', enum: ['confirmed', 'killed', 'adjusted'] },
          adjustedSeverity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'none'] },
          note: { type: 'string', description: 'what you found when you re-opened the cited file:line' },
        },
        required: ['id', 'status', 'adjustedSeverity', 'note'],
      },
    },
  },
  required: ['verdicts'],
};
function chunk(arr, n) { const out = []; for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n)); return out; }
const batches = chunk(candidates, 6);
const verifyResults = await parallel(batches.map((b, i) => () =>
  agent(
    CONTRACT + '\n\nYou are an INDEPENDENT mechanical VERIFIER (you did not write these findings). For EACH finding below, re-open the cited file:line in the worktree ' + WT + ' and confirm the quoted excerpt actually exists there and the defect is real. status=confirmed only if reproduced from the file; status=killed if the excerpt/line cannot be located or the claim is false; status=adjusted if real but mis-severitied (give adjustedSeverity). Be skeptical — default to killed if you cannot reproduce it. For absence-claims, run the cited search yourself.\n\n=== FINDINGS BATCH ' + (i + 1) + ' (JSON) ===\n' + JSON.stringify(b),
    { label: 'verify:batch-' + (i + 1), phase: 'Verify', model: modelFor('opus'), schema: VERIFY_SCHEMA }
  )
));
const verdictMap = {};
verifyResults.forEach((v, i) => {
  if (!v) { log('WARNING: verify batch ' + (i + 1) + ' agent died — its ' + batches[i].length + ' candidate(s) are UNVERIFIED and dropped (not killed by evidence); re-run to verify them.'); return; }
  v.verdicts.forEach((x) => { verdictMap[x.id] = x; });
});
const confirmed = candidates
  .map((f) => ({ ...f, verdict: verdictMap[f.id] }))
  .filter((f) => f.verdict && f.verdict.status !== 'killed')
  .map((f) => ({ ...f, severity: (f.verdict.status === 'adjusted' && f.verdict.adjustedSeverity !== 'none') ? f.verdict.adjustedSeverity : f.severity }));
const unverified = candidates.filter((f) => !verdictMap[f.id]).length;
const killed = candidates.length - confirmed.length - unverified;
log('Verification: ' + confirmed.length + ' confirmed, ' + killed + ' killed' + (unverified ? ', ' + unverified + ' UNVERIFIED (verifier agent death)' : '') + '.');

phase('Rank');
// LLM ranks, code renders: the previous single-agent design demanded the entire report as one
// structured string and blew the StructuredOutput retry cap at 32 findings (~53KB JSON). The agent
// now emits only a compact ranking + summary; the markdown is assembled deterministically below.
// Proven 2026-07-16 (wf_f70c9ac8-4d3 site-repo re-run): resumed from cache, only Rank re-ran live,
// succeeded on attempt 1 against the same 32-finding payload that exhausted the retry cap before.
const RANK_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    ranked: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          rank: { type: 'number' },
          id: { type: 'string' },
          riskTierHint: { type: 'string', enum: ['GREEN', 'YELLOW', 'RED'], description: 'GREEN additive+safe / YELLOW touches financial mechanism / RED governor-constant|confidential|external|deploy|destructive' },
          rationale: { type: 'string', description: 'one line: why this rank and tier' },
        },
        required: ['rank', 'id', 'riskTierHint', 'rationale'],
      },
    },
    summary: { type: 'string', description: '4-6 sentence executive summary of the codebase health vs ORA goals' },
  },
  required: ['ranked', 'summary'],
};
const slim = confirmed.map((f) => ({ id: f.id, title: f.title, severity: f.severity, file: f.file, line: f.line, goalImpact: f.goalImpact, fix: f.fix }));
const rank = await agent(
  CONTRACT + '\n\n=== GROUND TRUTH ===\n' + GROUND_TRUTH + '\n\nYou are the SYNTHESIS pass. Below are the CONFIRMED, deduped findings (each already re-verified against the file; slimmed to decision fields). Rank EVERY finding by (severity, then goal-priority impact: acquisition velocity > ops > institutional quality > comms > knowledge) and assign each a riskTierHint (GREEN additive-safe / YELLOW touches financial mechanism / RED governor-constant|confidential|external|deploy|destructive) with a one-line rationale — every input id must appear exactly once in ranked. Also write a 4-6 sentence executive summary of codebase health vs ORA goals, accounting for these audit COVERAGE NOTES (gaps in the audit itself):\n' + coverageNotes.join('\n') + '\n\n=== CONFIRMED FINDINGS (JSON, slimmed) ===\n' + JSON.stringify(slim),
  { label: 'rank-findings', phase: 'Rank', model: modelFor('opus'), schema: RANK_SCHEMA }
);
if (!rank) throw new Error('Rank agent failed — findings are verified but unranked; re-run the Rank phase (fail closed).');

const byId = {}; confirmed.forEach((f) => { byId[f.id] = f; });
const rankById = {}; (rank.ranked || []).forEach((r) => { rankById[r.id] = r; });
const orderedRanked = (rank.ranked || []).filter((r) => byId[r.id]).slice().sort((a, b) => a.rank - b.rank);
const unranked = confirmed.filter((f) => !rankById[f.id]);
const ordered = orderedRanked.map((r) => byId[r.id]).concat(unranked);
const SEV_ORDER = ['critical', 'high', 'medium', 'low'];
let md = '# Audit Report — ' + TARGET_LABEL + '\n\n' + rank.summary + '\n\n**Counts:** ' + confirmed.length + ' confirmed (' + SEV_ORDER.map((s) => confirmed.filter((f) => f.severity === s).length + ' ' + s).join(' / ') + ')' + (unranked.length ? ' — ' + unranked.length + ' finding(s) missing from the ranking, appended last' : '') + '\n';
for (const sev of SEV_ORDER) {
  const group = ordered.filter((f) => f.severity === sev);
  if (!group.length) continue;
  md += '\n## ' + sev.toUpperCase() + ' (' + group.length + ')\n';
  for (const f of group) {
    const r = rankById[f.id] || {};
    md += '\n### ' + (r.rank != null ? r.rank + '. ' : '') + f.title + '\n'
      + '- **id:** `' + f.id + '` · **file:** `' + f.file + ':' + f.line + '` · **risk:** ' + (r.riskTierHint || 'UNRATED') + ' · **goal:** ' + f.goalImpact + '\n'
      + (r.rationale ? '- **rank rationale:** ' + r.rationale + '\n' : '')
      + '- **evidence:** ' + f.evidence + '\n'
      + '- **excerpt:** `' + String(f.excerpt || '').replace(/`/g, "'").replace(/\s+/g, ' ').slice(0, 400) + '`\n'
      + '- **fix:** ' + f.fix + '\n'
      + '- **contributing dimensions:** ' + (f.contributingDimensions || []).join(', ') + '\n';
  }
}
md += '\n---\n\n## Audit coverage notes\n\n' + coverageNotes.map((c) => '- ' + c).join('\n') + '\n';

return {
  mode: GENERIC ? 'generic' : 'cc',
  worktree: WT,
  summary: rank.summary,
  reportMarkdown: md,
  ranked: orderedRanked.map((r) => ({ rank: r.rank, id: r.id, riskTierHint: r.riskTierHint, rationale: r.rationale, title: (byId[r.id] || {}).title, severity: (byId[r.id] || {}).severity, file: (byId[r.id] || {}).file, line: (byId[r.id] || {}).line, fix: (byId[r.id] || {}).fix, goalImpact: (byId[r.id] || {}).goalImpact })),
  counts: { raw: rawFindings.length, deduped: candidates.length, confirmed: confirmed.length, killed, unverified, droppedAlreadyDone: (dedup.droppedAlreadyDone || []).length },
  coverageNotes,
  confirmedFindings: confirmed,
};
