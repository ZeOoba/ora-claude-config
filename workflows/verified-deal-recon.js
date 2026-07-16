export const meta = {
  name: 'verified-deal-recon',
  description: 'Adversarially-verified acquisition pre-screen for Oxford Realty Advisors: deal-recon research -> 3 independent Explore verifiers (comps/basis, functional/environmental, demand/lease-up) -> PURSUE/PASS/NEEDS-MORE synthesis with a pre-mortem. Use for any real pursue/pass decision (the bare deal-recon agent is for instant first-looks only). Pass the property brief as args (a PLAIN STRING).',
  whenToUse: 'A single acquisition target needs a rigorous, adversarially-verified pre-screen before underwriting. args = property description string.',
  phases: [
    { title: 'Recon', detail: 'deal-recon fan-out research' },
    { title: 'Verify', detail: '3 independent Explore agents challenge the decision-drivers' },
    { title: 'Synthesize', detail: 'final PURSUE / PASS / NEEDS-MORE pre-screen brief + pre-mortem' },
  ],
}

// Property brief arrives via args. Prefer a plain string; tolerate {property:"..."} or undefined.
const PROPERTY =
  (typeof args === 'string' && args.trim()) ? args.trim()
  : (args && typeof args === 'object' && args.property) ? String(args.property).trim()
  : ''
if (!PROPERTY) {
  return { error: 'No property brief provided. Invoke with args = a property description STRING, e.g. Workflow({name:"verified-deal-recon", args:"123 Main St, City ST — 30,000 SF flex, $3M asking, ..."}).' }
}

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

// ---- Phase 1: deal-recon fan-out ----
phase('Recon')
const recon = await agent(
  `Pre-screen this acquisition target for Oxford Realty Advisors. Do your full fan-out (rent comps, sale comps, submarket fundamentals, demographics/demand, parcel/condition signal, and basis-vs-replacement) and return your consolidated pre-screen brief. Cite every external figure with source + date; mark anything unconfirmed [UNVERIFIED]. Apply ORA basis discipline (basis-buyer: prefer >=25% below MARKET-SPECIFIC replacement cost, >8% stabilized yield-on-cost; do not call PURSUE on a fair-basis deal with no value-add path, and do not hard-kill on basis alone when a real value-add path exists).\n\n${PROPERTY}`,
  { agentType:'deal-recon', schema:RECON_SCHEMA, phase:'Recon', label:'deal-recon' }
)
if (!recon) {
  return { verdict:'NEEDS_MORE', oneLineThesis:'deal-recon returned no output — re-run.', killRisks:[], preMortem:'n/a', openItems:['re-run deal-recon'], confidence:'low' }
}
const reconStr = JSON.stringify(recon, null, 2)

// ---- Phase 2: 3 adversarial verifiers (Explore = read-only web research) ----
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

return { property: PROPERTY.split('\n')[0], reconSoloVerdict: recon.recommendation && recon.recommendation.verdict, verifierCount: verifs.length, anyFlip: verifs.some(v => v && v.flipsRecommendation), brief }
