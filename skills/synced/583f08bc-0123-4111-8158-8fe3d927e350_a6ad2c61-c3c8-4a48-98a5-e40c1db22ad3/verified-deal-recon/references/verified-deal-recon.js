export const meta = {
  name: 'verified-deal-recon',
  description: 'Adversarially-verified acquisition pre-screen for Oxford Realty Advisors: recon research -> 3 independent Explore verifiers (comps/basis, functional/environmental, demand/lease-up) -> PURSUE/PASS/NEEDS-MORE synthesis with a pre-mortem. Use for any real pursue/pass decision. Pass the property brief as args (a PLAIN STRING), or {property, today}.',
  whenToUse: 'A single acquisition target needs a rigorous, adversarially-verified pre-screen before underwriting. args = property description string.',
  phases: [
    { title: 'Recon', detail: 'recon fan-out research' },
    { title: 'Verify', detail: '3 independent Explore agents challenge the decision-drivers' },
    { title: 'Synthesize', detail: 'final PURSUE / PASS / NEEDS-MORE pre-screen brief + pre-mortem' },
  ],
}

// v1.2 (2026-08-22) — CROSS-SURFACE PORT. Two changes from v1.1, both required to run on Cowork:
//   1. Phase 1 no longer uses agentType:'deal-recon'. Custom subagents live in .claude/agents/,
//      which has no sync path to Cowork (only .claude/skills/ syncs). The deal-recon system
//      prompt is inlined below verbatim instead, with model:'opus' matching its frontmatter.
//      Behaviour is unchanged; the dependency is removed.
//   2. `new Date()` removed. Workflow scripts throw on argless `new Date()`, Date.now() and
//      Math.random() (they would break resume). The ledger row's date is now supplied by the
//      caller via args.today, or left as a token for the calling session to stamp.
// Unchanged from v1.1: this workflow does NOT write memory/deal-decision-ledger.md and never
// will from inside a Workflow script — ledger rows are appended by a session ONLY after Gabriel
// confirms the verdict in-turn. `ledgerRowDraft` below is a convenience for that session.

const PROPERTY =
  (typeof args === 'string' && args.trim()) ? args.trim()
  : (args && typeof args === 'object' && args.property) ? String(args.property).trim()
  : ''
const TODAY =
  (args && typeof args === 'object' && args.today) ? String(args.today).trim() : '<STAMP-DATE>'

if (!PROPERTY) {
  return { error: 'No property brief provided. Invoke with args = a property description STRING, e.g. Workflow({name:"verified-deal-recon", args:"123 Main St, City ST — 30,000 SF flex, $3M asking, ..."}), or {property:"...", today:"YYYY-MM-DD"}.' }
}

// ---- Inlined deal-recon agent prompt (was .claude/agents/deal-recon.md, verbatim) ----
const RECON_SYSTEM = `You are an acquisitions research analyst for Oxford Realty Advisors (ORA). ORA targets sub-$10M, sub-50K SF, Class B/C shallow-bay industrial/flex assets in OH, MD, IN, WI, MO, KS, and TN (DSCR >= 1.25x, LTV <= 40%). Your job is fast, broad reconnaissance on a candidate so Gabriel can decide in minutes whether it's worth underwriting.

## What you produce
A single, tight pre-screen brief (one page). Do the legwork across all lanes below, then synthesize — do not dump raw search results.

### Lanes to cover
1. Rent comps — NNN asking/effective rents ($/SF) for truly comparable shallow-bay industrial/flex (match SF, vintage, clear height, yard); note vacancy and concessions. For a vacant asset, estimate realistic lease-up time, effective NNN, and concession load — the return rides on it.
2. Sale comps — recent (~24 mo) sales of like-kind assets: price/SF, cap rate, buyer type. For each comp record SF, lot coverage (yard vs no-yard), and buyer type (owner-user vs investor), and adjust — a yard-heavy owner-user trade (where land is much of the price) does NOT support a no-yard box. If no like-kind comp exists, say so plainly — never anchor the basis read to a dissimilar trade.
3. Submarket fundamentals — vacancy, absorption, supply pipeline, rent trend direction.
4. Demographics & demand drivers — population/in-migration, employment, highway/intermodal/last-mile access, major nearby occupiers.
5. Property/parcel signal — anything public on ownership, age, condition, prior listings, tax assessment. Pull authoritative SF from the county assessor; if SF is disputed across sources, show the resulting $/SF range.
6. Basis vs. replacement — estimate a market-specific replacement cost ($/SF new-build for THIS region — Northeast/MD runs higher than the Midwest; cite the figure + source), then state the implied discount/premium to it. ORA is a basis buyer (doctrine: prefer >=25% below replacement and >8% stabilized yield-on-cost; basis beats cap rate). This is doctrine, NOT the DSCR/LTV governor — do not compute the governor here.

## Rules
- Confidentiality: if this target has since become (or is) an active ORA deal, never include ORA's own internal deal data (LOI/PSA status, negotiated terms, DD findings) in any external search query or in your output — research the property's public market context only. Categorically: never include ANY of ORA's own not-yet-closed deal data in your output, and never put an ORA deal name into any external WebSearch/WebFetch query — this holds for every active ORA deal, not just the target in front of you. The authoritative roster of confidential deals is ~/.claude/hooks/confidential-terms.json (each key with active: true); when in doubt whether a name is a live ORA deal, treat it as confidential and keep it out of external queries and output.
- Cite every external figure with its source and date. Mark anything you couldn't confirm as [UNVERIFIED].
- Do NOT underwrite, build models, or compute IRR — that's the acquisition-underwriting skill's job. Hand off cleanly.
- You cannot ask questions mid-task; work with what's given and note gaps.
- Be concise. Gabriel reads fast.`

const RECON_SCHEMA = {
  type:'object', additionalProperties:false,
  properties:{
    snapshot:{type:'string'}, fitVsBox:{type:'string'},
    rentComps:{type:'string'}, saleComps:{type:'string'}, submarket:{type:'string'},
    demand:{type:'array', items:{type:'string'}},
    basisRead:{type:'string'},
    redFlags:{type:'array', items:{type:'string'}},
    recommendation:{type:'object', additionalProperties:false, properties:{
      verdict:{type:'string', enum:['PURSUE','PASS','NEEDS_MORE']}, oneLineWhy:{type:'string'}
    }, required:['verdict','oneLineWhy']},
    sources:{type:'array', items:{type:'string'}}
  }, required:['snapshot','fitVsBox','rentComps','saleComps','submarket','demand','redFlags','recommendation']
}

const VERIFY_SCHEMA = {
  type:'object', additionalProperties:false,
  properties:{
    lens:{type:'string'},
    claimsChecked:{type:'array', items:{type:'object', additionalProperties:false, properties:{
      claim:{type:'string'}, holds:{type:'boolean'},
      severity:{type:'string', enum:['none','minor','major','critical']}, evidence:{type:'string'}
    }, required:['claim','holds','severity','evidence']}},
    independentFindings:{type:'string'},
    flipsRecommendation:{type:'boolean'},
    lensVerdict:{type:'string'}
  }, required:['lens','claimsChecked','flipsRecommendation','lensVerdict']
}

const BRIEF_SCHEMA = {
  type:'object', additionalProperties:false,
  properties:{
    verdict:{type:'string', enum:['PURSUE','PASS','NEEDS_MORE']},
    oneLineThesis:{type:'string'}, snapshot:{type:'string'},
    verifiedRentComps:{type:'string'}, verifiedSaleComps:{type:'string'},
    basisRead:{type:'string'}, submarketDemand:{type:'string'},
    killRisks:{type:'array', items:{type:'string'}},
    preMortem:{type:'string'},
    openItems:{type:'array', items:{type:'string'}},
    confidence:{type:'string', enum:['low','medium','high']}
  }, required:['verdict','oneLineThesis','snapshot','basisRead','killRisks','preMortem','openItems','confidence']
}

// ---- Phase 1: recon fan-out ----
phase('Recon')
const recon = await agent(
  `${RECON_SYSTEM}

---

Pre-screen this acquisition target for Oxford Realty Advisors. Do your full fan-out (rent comps, sale comps, submarket fundamentals, demographics/demand, parcel/condition signal, and basis-vs-replacement) and return your consolidated pre-screen brief. Cite every external figure with source + date; mark anything unconfirmed [UNVERIFIED]. Apply ORA basis discipline (basis-buyer: prefer >=25% below MARKET-SPECIFIC replacement cost, >8% stabilized yield-on-cost; do not call PURSUE on a fair-basis deal with no value-add path, and do not hard-kill on basis alone when a real value-add path exists).

${PROPERTY}`,
  { schema:RECON_SCHEMA, phase:'Recon', label:'recon', model:'opus' }
)
if (!recon) {
  return { verdict:'NEEDS_MORE', oneLineThesis:'recon returned no output — re-run.', killRisks:[], preMortem:'n/a', openItems:['re-run recon'], confidence:'low' }
}
const reconStr = JSON.stringify(recon, null, 2)

// ---- Phase 2: 3 adversarial verifiers (Explore = read-only research) ----
phase('Verify')
const lenses = [
  { key:'comps-basis', focus:`COMPS & BASIS. Independently web-search recent LIKE-KIND rent comps (NNN $/SF) and sale comps ($/SF, cap rate) for the subject's submarket and asset profile. Scrutinize comparability: SF, lot coverage (yard vs no-yard), buyer type (owner-user vs investor), vintage — a yard-heavy owner-user comp does NOT support a no-yard box. Then judge the recon's BASIS claim against a MARKET-SPECIFIC replacement cost: is asking $/SF genuinely below replacement (ORA basis-buyer floor ~>=25% discount), or merely fair? Confirm or refute the recon's comp set with your own sources.` },
  { key:'functional-environmental', focus:`FUNCTIONAL & ENVIRONMENTAL. Assess functional leasability as modern shallow-bay industrial: clear height, loading/docks, truck court/yard, parking, column spacing, footprint vs realistic tenant pool — flag functional obsolescence. Assess environmental risk: pre-~1980 vintage or prior industrial/manufacturing use => Phase I warranted, possible REC. Be concrete about whether physical/environmental issues KILL or merely gate the deal.` },
  { key:'demand-leaseup', focus:`SUBMARKET DEMAND & LEASE-UP. Web-search the subject's specific submarket: vacancy, absorption, supply pipeline, asking rents for comparable small space, tenant demand. If the asset is vacant or low-occupancy the return rides on lease-up — estimate realistic lease-up velocity, effective NNN, and concession load. Is demand real and durable at THIS micro-location, or is the vacancy structural?` },
]
const verifs = await parallel(lenses.map(L => () =>
  agent(
    `You are an independent, skeptical acquisitions verifier for Oxford Realty Advisors. Do your OWN web research — do not trust the recon's figures. Try to REFUTE the recon where you can.\n\nYOUR LENS: ${L.focus}\n\n=== TARGET ===\n${PROPERTY}\n\n=== THE RECON BRIEF UNDER REVIEW ===\n${reconStr}\n\nReturn the claims you checked (holds true/false + severity + evidence with sources), your own independent findings, whether your lens FLIPS the PURSUE/PASS recommendation, and a one-line lens verdict.`,
    { agentType:'Explore', schema:VERIFY_SCHEMA, phase:'Verify', label:`verify:${L.key}` }
  )
)).then(rs => rs.filter(Boolean))

// ---- Phase 3: synthesize ----
phase('Synthesize')
const brief = await agent(
  `You are the lead acquisitions analyst. Synthesize the FINAL one-page pre-screen from the recon brief and the independent adversarial verifications below. Weight verifiers over the recon where they conflict (they did their own research).

Apply ORA basis discipline to the verdict: basis at/above MARKET-SPECIFIC replacement AND no credible value-add path to >8% stabilized yield-on-cost -> PASS; merely-fair basis WITH a credible value-add path -> NEEDS_MORE (underwrite the upside); below-replacement OR clear value-add upside -> PURSUE. Do NOT hard-kill on basis alone when a real value-add path exists; do NOT call PURSUE on a fair-basis deal with no upside path. Give the basis read explicitly, the kill-risks, the single most-likely failure mode (pre-mortem), and concrete open items to confirm before underwriting (clear height, environmental/Phase I, zoning, lot/yard, authoritative SF). Be concise — Gabriel reads fast. Do NOT underwrite (no DSCR/LTV/IRR) — this is a screen.

=== RECON BRIEF ===
${reconStr}

=== INDEPENDENT VERIFICATIONS ===
${JSON.stringify(verifs, null, 2)}`,
  { schema:BRIEF_SCHEMA, phase:'Synthesize', label:'synthesis' }
)

const dealName = PROPERTY.split('\n')[0].trim()
const ledgerRowDraft = brief
  ? `| ${TODAY} | ${dealName} | ${brief.verdict} | ${brief.oneLineThesis || brief.preMortem || ''} | — | — |`
  : null

return {
  property: dealName,
  reconSoloVerdict: recon.recommendation && recon.recommendation.verdict,
  verifierCount: verifs.length,
  anyFlip: verifs.some(v => v && v.flipsRecommendation),
  brief,
  ledgerRowDraft,
  ledgerAppendInstruction: 'DRAFT ONLY — on any PURSUE/PASS/NEEDS_MORE verdict Gabriel confirms in-session, append `ledgerRowDraft` (Date | Deal | Verdict | one-line reason | buy-box rule validated/refined | FORT) as one row to memory/deal-decision-ledger.md. If TODAY reads <STAMP-DATE>, stamp the real date before appending. This workflow never appends it itself.',
}
