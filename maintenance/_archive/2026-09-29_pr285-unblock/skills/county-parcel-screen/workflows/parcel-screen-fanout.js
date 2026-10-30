export const meta = {
  name: 'parcel-screen-fanout',
  description: 'Dynamic multi-county fan-out of the ORA county-parcel-screen: fetch the live pipeline guard, pull+score each county in parallel, verify finalists per-candidate, merge into one ranked call-list with pipeline-conflict exclusion. v2 (2026-06-09): adds the Notion Acquisition Pipeline guard + normalized address/owner matching.',
  phases: [
    { title: 'Pipeline Guard', detail: 'fetch live ORA Acquisition Pipeline (bcfe4a03) deal addresses + never-call counterparties' },
    { title: 'Pull & Score', detail: 'one agent per county: discover/pull industrial universe, exclude, calibrate auditor-to-market, score 0-100' },
    { title: 'Verify Finalists', detail: 'per-finalist: occupant check, archived-listing check, SOS principal lookup, pre-mortem' },
    { title: 'Merge & Rank', detail: 'pipeline-conflict exclude (exact-address + counterparty hard-drop; same-street flag-for-review), call-order doctrine' },
  ],
}

// -------------------------------------------------------------------------
// INVOCATION
//   Workflow({ scriptPath: ".../workflows/parcel-screen-fanout.js",
//              args: { market: "Maryland",
//                      counties: ["Anne Arundel MD", "Howard MD", "Baltimore Co MD"],
//                      topN: 10 } })
//   args may also be a bare string[] of counties.
//   Optional args.pipelineGuard = { deals:[{name,address}], counterparties:[...] }
//     supplies the exclusion list directly and SKIPS the Phase-0 Notion fetch.
//   args.neverCallNames (string[]) = the counterparty FLOOR — REQUIRED. Load it
//     before invoking from the CANONICAL ABSOLUTE PATH (2026-09-18; this tracked
//     file deliberately carries no deal counterparty names, 2026-06-11):
//       C:\Users\Owner\.claude\skills\county-parcel-screen\data\pipeline-guard.local.json
//     NEVER from a path relative to whichever copy of the skill is executing —
//     the file is untracked and absent from both the ora-skills repo checkout
//     and the AppData plugin bundle. Omitting it now THROWS; it used to degrade.
//
// PIPELINE GUARD (v2): the Notion Acquisition Pipeline Tracker (bcfe4a03) is
//   DEAL-level, not parcel-level — there is no parcel-ID to join on. So the
//   guard matches each finalist's site address / owner against the live deal
//   addresses + known never-call seller counterparties:
//     - exact-address match  -> HARD DROP (it's an asset we're already on)
//     - counterparty name     -> HARD DROP (never cold-call a live seller)
//     - same-street near-match-> KEEP but flag ROAD-REVIEW (the Shevers lesson:
//                                a shared road is not proof of the same asset)
//
// OUTPUT: structured ranked call-list (JSON). Workbook delivery (skill step 9,
//   ORA-style xlsx) is intentionally LEFT to a main-context follow-up using the
//   xlsx skill + recalc.py — a subagent must not ship a financial-style
//   deliverable without that QC gate.
// -------------------------------------------------------------------------

const SKILL = 'C:/Users/Owner/.claude/skills/county-parcel-screen/SKILL.md'
const PY = 'C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe'
const PIPELINE_DB = '46c8a5c68b374c53a10d0f55c97613e5' // Acquisition Pipeline Tracker (data source bcfe4a03-7e61-4ac1-a0bb-c44174fa138b)

// args may arrive as an object, a JSON string, a bare array, or a comma-list — coerce defensively.
let raw = args
if (typeof raw === 'string') {
  try { raw = JSON.parse(raw) }
  catch (e) { raw = { counties: raw.split(',').map((s) => s.trim()).filter(Boolean) } }
}
const cfg = Array.isArray(raw) ? { counties: raw } : (raw || {})
const counties = cfg.counties || []
const market = cfg.market || 'Cincinnati'
const topN = cfg.topN || 10
log(`parcel-screen-fanout v2 args → market=${market} · counties=[${counties.join(', ')}] · topN=${topN}`)
if (!counties.length) {
  throw new Error('Provide args.counties (string[]) or JSON string. Received args=' + JSON.stringify(args))
}

// ---- pipeline-conflict matcher (pure; mirrored in test-pipeline-match.mjs) ----
// Never-call floor is SUPPLIED via args.neverCallNames. The invoking session loads it
// from the CANONICAL ABSOLUTE PATH (counterparty names never live in this tracked file;
// externalized 2026-06-11):
//   C:\Users\Owner\.claude\skills\county-parcel-screen\data\pipeline-guard.local.json
// FAIL-LOUD since 2026-09-18: an omitted floor used to degrade to ORA-self-only with a
// warning. The same degraded-fallback shape in institutional_owners.py is what let the
// 2026-09-18 Jackson MO ring screen ship a call list screened on ORA-self patterns only.
// A degraded floor is no longer an allowed run mode here either — throw instead.
const GUARD_PATH =
  'C:\\Users\\Owner\\.claude\\skills\\county-parcel-screen\\data\\pipeline-guard.local.json'
const STOP_HINT =
  'Load never_call_names from ' + GUARD_PATH + ' (absolute path — NOT relative to ' +
  'whichever copy of this skill is executing; it is absent from the repo checkout and ' +
  'the plugin bundle) and pass it as args.neverCallNames. Record the guard path, UTC ' +
  'mtime and BOTH entry counts (never_call_names and never_call_patterns) in the ' +
  'deliverable. Degraded screening was removed 2026-09-18.'
if (!cfg.neverCallNames || !cfg.neverCallNames.length) {
  throw new Error(
    'STOP: args.neverCallNames not supplied — the never-call counterparty floor is ' +
    'UNAVAILABLE, so no call list may be produced. ' + STOP_HINT)
}
// The floor must come FROM THE GUARD FILE, never from the removed ORA-self pair.
// Mirrors the regression in test-pipeline-match.mjs so the production path is held
// to the same bar as the test harness.
if (cfg.neverCallNames.length <= 2
    && cfg.neverCallNames.every((n) => ['OXFORD', 'GOLDBERG'].includes(String(n).toUpperCase()))) {
  throw new Error(
    'STOP: args.neverCallNames is the degraded ORA-self pair — the removed fallback ' +
    'has returned, so this run would screen no counterparty at all. ' + STOP_HINT)
}
const NEVER_CALL_NAMES = cfg.neverCallNames

function norm(s) {
  return String(s || '').toUpperCase().replace(/[^A-Z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim()
}
function roadCore(addr) {
  let s = norm(addr)
  s = s.replace(/\b[A-Z]{2} \d{5}( \d{4})?\b.*$/, '') // cut at STATE ZIP tail
  s = s.replace(/^\d+[A-Z]? /, '')                    // drop leading house number
  s = s.replace(/\b\d{5}\b/g, ' ')                    // drop stray zips
  s = s.replace(/\bSTREET\b/g, 'ST').replace(/\bROAD\b/g, 'RD').replace(/\bDRIVE\b/g, 'DR')
    .replace(/\bAVENUE\b/g, 'AVE').replace(/\bPARKWAY\b/g, 'PKWY').replace(/\bBOULEVARD\b/g, 'BLVD')
    .replace(/\bHIGHWAY\b/g, 'HWY')
  s = s.replace(/\s+/g, ' ').trim()
  // truncate at the street suffix / route-number so trailing city/county tokens don't break matching
  const m = s.match(/^(.+?\b(?:ST|RD|DR|AVE|PKWY|BLVD|HWY|PIKE|CT|LN|CIR|WAY|TRL|TER|PL|SQ|LOOP|RUN|ROUTE \d+|SR \d+))\b/)
  return (m ? m[1] : s).trim()
}
function contains(a, b, minLen) {
  return a && b && b.length >= minLen && (a.includes(b) || b.includes(a))
}
// returns 'counterparty' | 'exact-address' | 'road-review' | null
function pipelineMatch(c, guard) {
  const owner = norm(c.owner)
  if ((guard.counterparties || []).some((n) => n && owner.includes(norm(n)) && norm(n).length >= 3)) return 'counterparty'
  const addrN = norm(c.siteAddress), addrR = roadCore(c.siteAddress)
  for (const d of (guard.deals || [])) {
    if (contains(addrN, norm(d.address), 12)) return 'exact-address'
  }
  for (const d of (guard.deals || [])) {
    if (contains(addrR, roadCore(d.address), 10)) return 'road-review'
  }
  return null
}

// ---- Phase 0: pipeline guard (fetch live, or take it from args) ----
phase('Pipeline Guard')
const guardPromise = cfg.pipelineGuard
  ? Promise.resolve(cfg.pipelineGuard)
  : agent(
    `Fetch the ORA Acquisition Pipeline Tracker from Notion (database ${PIPELINE_DB}, data source bcfe4a03-7e61-4ac1-a0bb-c44174fa138b). ` +
    `Use the Notion MCP (search ToolSearch for "notion fetch"/"notion search"). Return EVERY deal row's Deal Name + Address field across ALL stages (sourcing, under contract, dead — all of them), and any seller / counterparty entity or family surnames ORA must never cold-call that appear in the deals or their notes. ` +
    `This list excludes/flags parcels already in ORA's pipeline from an off-market call list — completeness matters more than precision.`,
    {
      label: 'pipeline-guard',
      phase: 'Pipeline Guard',
      schema: {
        type: 'object',
        required: ['deals'],
        properties: {
          deals: {
            type: 'array',
            items: {
              type: 'object',
              required: ['address'],
              properties: { name: { type: 'string' }, address: { type: 'string' } },
            },
          },
          counterparties: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  )

const CANDIDATE_SCHEMA = {
  type: 'object',
  required: ['factor', 'candidates'],
  properties: {
    factor: { type: 'number', description: 'derived auditor-to-market calibration factor' },
    n: { type: 'number', description: 'sample size behind the calibration factor' },
    caveats: { type: 'string', description: 'data gaps / honest rescale notes (e.g. no public SF → pre-SF 0-75 scale)' },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['owner', 'siteAddress', 'score', 'callBucket'],
        properties: {
          parcelId: { type: 'string' },
          owner: { type: 'string' },
          siteAddress: { type: 'string' },
          mailAddress: { type: 'string' },
          buildingSF: { type: 'number' },
          score: { type: 'number' },
          scoreBreakdown: { type: 'string', description: 'product/size/hold/basis/entity/absentee/multiparcel point split' },
          callBucket: { type: 'string', enum: ['estate', 'delinquent-entity', 'seller-in-motion', 'absentee', 'long-hold'] },
          flags: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['disqualified', 'preMortem'],
  properties: {
    disqualified: { type: 'boolean', description: 'true if occupant/use check kills it (auto-use, policy-blocked, Class A, non-industrial)' },
    occupantUse: { type: 'string' },
    listingSignal: { type: 'string', description: 'archived/delisted listing = motivated-seller signal' },
    principal: { type: 'string', description: 'entity principal per state SOS, if found' },
    preMortem: { type: 'string', description: 'single most likely reason this fails ORA underwriting' },
  },
}

phase('Pull & Score')
const perCounty = await pipeline(
  counties,
  // Stage 1 — pull + score one county (heavy; runs in the python sandbox)
  (county) => agent(
    `You are running the ORA county-parcel-screen for ONE county: ${county} (market: ${market}).\n` +
    `Read and follow ${SKILL} EXACTLY, steps 1-7: discover sources (use references/county-endpoints.md if this county is already mapped), pull the industrial universe, exclude (gov/exempt, institutional owners, ORA affiliates, parcels already in Notion pipeline bcfe4a03), calibrate auditor-to-market EMPIRICALLY (never guess), fix the hold score (nominal transfers are not purchases), and score 0-100.\n` +
    `Use the full python path ${PY}. Apply the CORRECTED estate-signal regex from references/market-status.md (canonical: outputs/fx/estate_v2.py) — never bare \\bESTATE\\b or \\bTR\\b. Save raw JSON before processing.\n` +
    `Return the top ${topN} A/B-tier candidates with full score breakdown, the derived auditor-to-market factor + its n, and any data-gap caveats. If the county publishes no commercial SF, rescale honestly and say so.`,
    { label: `pull:${county}`, phase: 'Pull & Score', schema: CANDIDATE_SCHEMA },
  ),
  // Stage 2 — verify this county's finalists, each in its own agent (no barrier vs other counties)
  (scored, county) => {
    if (!scored || !Array.isArray(scored.candidates) || !scored.candidates.length) {
      return { county, factor: scored && scored.factor, caveats: scored && scored.caveats, finalists: [] }
    }
    return parallel(scored.candidates.map((c) => () =>
      agent(
        `Verify this off-market industrial acquisition candidate before anyone calls (skill step 8): ${JSON.stringify(c)}.\n` +
        `Do an occupant web check (flag auto-use / policy-blocked tenancy), an archived/delisted listing check (motivated-seller signal), and identify the entity principal via the state SOS. Attach a one-line pre-mortem: the single most likely reason this fails ORA underwriting.`,
        { label: `verify:${county}:${c.parcelId || c.owner}`, phase: 'Verify Finalists', schema: VERDICT_SCHEMA },
      ).then((v) => ({ ...c, county, verification: v })),
    )).then((verified) => ({
      county, factor: scored.factor, caveats: scored.caveats, finalists: verified.filter(Boolean),
    }))
  },
)

phase('Merge & Rank')
const rawGuard = (await guardPromise) || {}
const guard = {
  deals: rawGuard.deals || [],
  counterparties: [...new Set([...NEVER_CALL_NAMES, ...(rawGuard.counterparties || [])])],
}
log(`pipeline guard (${cfg.pipelineGuard ? 'from args' : 'phase-0 fetch'}): ${guard.deals.length} deals · ${guard.counterparties.length} counterparties`)

const callOrder = { estate: 0, 'delinquent-entity': 1, 'seller-in-motion': 2, absentee: 3, 'long-hold': 4 }
const all = perCounty.filter(Boolean).flatMap((r) => r.finalists || [])
const tagged = all.map((c) => ({ ...c, pipelineMatch: pipelineMatch(c, guard) }))

const isHardDrop = (c) =>
  c.pipelineMatch === 'exact-address' ||
  c.pipelineMatch === 'counterparty' ||
  (c.verification && c.verification.disqualified)

const ranked = tagged
  .filter((c) => !isHardDrop(c))
  .map((c) => c.pipelineMatch === 'road-review'
    ? { ...c, pipelineConflict: 'ROAD-REVIEW — same street as a live ORA pipeline deal; confirm it is NOT the same asset/seller before any call' }
    : c)
  .sort((a, b) =>
    ((callOrder[a.callBucket] ?? 9) - (callOrder[b.callBucket] ?? 9)) ||
    ((b.score || 0) - (a.score || 0)),
  )

log(`${counties.length} counties → ${all.length} finalists → ${ranked.length} callable ` +
  `(dropped ${tagged.filter(isHardDrop).length}; ${ranked.filter((c) => c.pipelineConflict).length} flagged road-review)`)

return {
  market,
  counties,
  generated: 'parcel-screen-fanout v2',
  guardSource: cfg.pipelineGuard ? 'args' : 'phase-0 notion fetch',
  pipelineDealsLoaded: guard.deals.length,
  calibration: perCounty.filter(Boolean).map((r) => ({ county: r.county, factor: r.factor, caveats: r.caveats })),
  rankedCallList: ranked,
  pipelineFlaggedForReview: ranked.filter((c) => c.pipelineConflict)
    .map((c) => ({ owner: c.owner, siteAddress: c.siteAddress, note: c.pipelineConflict })),
  pipelineExcluded: tagged.filter((c) => c.pipelineMatch === 'exact-address' || c.pipelineMatch === 'counterparty')
    .map((c) => ({ owner: c.owner, siteAddress: c.siteAddress, reason: c.pipelineMatch })),
  disqualifiedAtVerify: tagged.filter((c) => c.verification && c.verification.disqualified)
    .map((c) => ({ owner: c.owner, reason: c.verification.preMortem })),
}
