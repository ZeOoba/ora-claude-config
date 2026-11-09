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

// v1.1 (2026-07-18, setup-improvement Plan 1 — deal-decision-ledger flywheel): this workflow
// does NOT write memory/deal-decision-ledger.md itself and never will from inside a Workflow
// script — ledger rows only get appended by a session AFTER Gabriel confirms the verdict
// in-turn (never on a provisional/unconfirmed PURSUE/PASS/NEEDS_MORE result). The return value
// below carries a pre-formatted `ledgerRowDraft` in the ledger's existing schema
// (Date | Deal | Verdict | one-line reason | buy-box rule validated/refined) purely as a
// convenience for the calling session to append verbatim once Gabriel ratifies the verdict.

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
    basisClearsFloor:{type:'string', enum:['YES','NO','UNKNOWN']},
    killRisks:{type:'array', items:{type:'string'}},
    preMortem:{type:'string'},
    openItems:{type:'array', items:{type:'string'}},
    confidence:{type:'string', enum:['low','medium','high']}
  }, required:['verdict','oneLineThesis','snapshot','basisRead','basisClearsFloor','killRisks','preMortem','openItems','confidence']
}

// ---- Phase 1: deal-recon fan-out ----
phase('Recon')
const recon = await agent(
  `Pre-screen this acquisition target for Oxford Realty Advisors. Do your full fan-out (rent comps, sale comps, submarket fundamentals, demographics/demand, parcel/condition signal, and basis-vs-replacement) and return your consolidated pre-screen brief. Cite every external figure with source + date; mark anything unconfirmed [UNVERIFIED]. Apply ORA basis discipline (basis-buyer: the all-in basis (price + 2% closing + CapEx + lease-up carry; [est] where unknown) should clear the vintage-ramp floor (65% at/below 1995 -> 60% at/above 2005, linear between, as a discount below the construction-type-adjusted MARKET-SPECIFIC replacement LOW), with >8% stabilized yield-on-cost; a floor miss caps the recommendation at NEEDS_MORE regardless of value-add upside, but is not an automatic kill: do not call PURSUE unless the all-in basis clears the floor, and do not hard-kill on basis alone when a real value-add path exists).\n\n${PROPERTY}`,
  { agentType:'deal-recon', schema:RECON_SCHEMA, phase:'Recon', label:'deal-recon' }
)
if (!recon) {
  return { verdict:'NEEDS_MORE', oneLineThesis:'deal-recon returned no output — re-run.', killRisks:[], preMortem:'n/a', openItems:['re-run deal-recon'], confidence:'low' }
}
const reconStr = JSON.stringify(recon, null, 2)

// ---- Phase 2: 3 adversarial verifiers (Explore = read-only web research) ----
phase('Verify')
const lenses = [
  { key:'comps-basis', focus:`COMPS & BASIS. Independently web-search recent LIKE-KIND rent comps (NNN $/SF) and sale comps ($/SF, cap rate) for the subject's submarket and asset profile. Scrutinize comparability: SF, lot coverage (yard vs no-yard), buyer type (owner-user vs investor), vintage — a yard-heavy owner-user comp does NOT support a no-yard box. Then judge the recon's BASIS claim against a MARKET-SPECIFIC replacement cost: does the all-in basis (price + 2% closing + CapEx + lease-up carry; [est] where unknown) clear ORA's vintage-ramp floor (65% at/below 1995 -> 60% at/above 2005, linear between, as a discount below the construction-type-adjusted MARKET-SPECIFIC replacement LOW), or is it merely fair? A floor miss caps the verdict at NEEDS_MORE but is not an automatic kill. Confirm or refute the recon's comp set with your own sources.` },
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
const synth = await agent(
  `You are the lead acquisitions analyst. Synthesize the FINAL one-page pre-screen from the recon brief and the independent adversarial verifications below. Weight verifiers over the recon where they conflict (they did their own research).

Apply ORA basis discipline to the verdict. Clearing the floor is NECESSARY for PURSUE; value-add upside never substitutes for it. Rules: basis at/above MARKET-SPECIFIC replacement AND no credible value-add path to >8% stabilized yield-on-cost -> PASS; all-in basis (price + 2% closing + CapEx + lease-up carry; [est] where unknown) that clears the vintage-ramp floor (65% at/below 1995 -> 60% at/above 2005, linear between, as a discount below the construction-type-adjusted MARKET-SPECIFIC replacement LOW) -> PURSUE, unless the kill-risks warrant a lower verdict; all-in basis that misses the vintage-ramp floor -> NEEDS_MORE at most, regardless of value-add upside (with a credible value-add path, say what re-priced basis would clear the floor and underwrite the upside). A floor miss caps the verdict but is not an automatic kill: do NOT hard-kill on basis alone when a real value-add path exists. Set basisClearsFloor to YES only when the all-in basis clears the floor on the evidence, NO when it misses, UNKNOWN when replacement cost or basis cannot be established; any answer other than YES caps the verdict at NEEDS_MORE. Give the basis read explicitly, the kill-risks, the single most-likely failure mode (pre-mortem), and concrete open items to confirm before underwriting (clear height, environmental/Phase I, zoning, lot/yard, authoritative SF). Be concise — Gabriel reads fast. Do NOT underwrite (no DSCR/LTV/IRR) — this is a screen.

=== RECON BRIEF ===
${reconStr}

=== INDEPENDENT VERIFICATIONS ===
${JSON.stringify(verifs, null, 2)}`,
  { schema:BRIEF_SCHEMA, phase:'Synthesize', label:'synthesis' }
)

// ---- Vintage-ramp floor cap (v1.2, decision 2026-11-08) ----
// A floor miss caps the verdict at NEEDS_MORE regardless of value-add upside. The synthesis prompt
// says so, but the prompt is advisory: enforce it here so a PURSUE that does not affirmatively
// clear the floor (NO, UNKNOWN, or the field missing) can never reach Gabriel as PURSUE. The cap
// only lowers PURSUE; PASS and NEEDS_MORE pass through. The agent's raw object is not mutated.
let verdictCap = null
// Verdict compared case/space-insensitively: the schema enum should prevent 'pursue', but the
// cap must not depend on the runtime enforcing it.
if (synth && String(synth.verdict || '').trim().toUpperCase() === 'PURSUE' && synth.basisClearsFloor !== 'YES') {
  const floorState = synth.basisClearsFloor === undefined ? 'MISSING' : String(synth.basisClearsFloor)
  verdictCap = {
    from: 'PURSUE', to: 'NEEDS_MORE',
    reason: 'All-in basis not shown to clear the vintage-ramp floor (basisClearsFloor=' + floorState + '); a floor miss caps the verdict at NEEDS_MORE regardless of value-add upside.',
  }
}
const brief = verdictCap
  ? { ...synth, verdict: 'NEEDS_MORE', openItems: [...(Array.isArray(synth.openItems) ? synth.openItems : []), 'Re-test all-in basis against the vintage-ramp floor (synthesis said PURSUE; capped at NEEDS_MORE because basisClearsFloor=' + (synth.basisClearsFloor === undefined ? 'MISSING' : synth.basisClearsFloor) + ').'] }
  : synth

// ---- Ledger-row draft (v1.1) — NOT written to disk; the calling session appends this only
// after Gabriel confirms the verdict in-session. See the file-header note above.
const dealName = PROPERTY.split('\n')[0].trim()
// Date.now()/new Date() are unavailable in workflow scripts (breaks resume); the calling
// session stamps the date when it appends the ledger row.
const todayISO = 'YYYY-MM-DD'
const ledgerRowDraft = brief
  ? `| ${todayISO} | ${dealName} | ${brief.verdict} | ${brief.oneLineThesis || brief.preMortem || ''} | — |`
  : null

return {
  property: dealName,
  reconSoloVerdict: recon.recommendation && recon.recommendation.verdict,
  verifierCount: verifs.length,
  anyFlip: verifs.some(v => v && v.flipsRecommendation),
  brief,
  verdictCap,
  ledgerRowDraft,
  ledgerAppendInstruction: 'DRAFT ONLY — on any PURSUE/PASS/NEEDS_MORE verdict Gabriel confirms in-session, append `ledgerRowDraft` (Date | Deal | Verdict | one-line reason | buy-box rule validated/refined) as one row to memory/deal-decision-ledger.md using the existing schema. This workflow never appends it itself.',
}
