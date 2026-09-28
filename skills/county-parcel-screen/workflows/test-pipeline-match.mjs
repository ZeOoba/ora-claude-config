// Unit test for the parcel-screen-fanout v2 pipeline-conflict matcher.
// Helpers are mirrored from parcel-screen-fanout.js (the workflow sandbox can't
// import local modules, so they live inline there). KEEP IN SYNC.
// Run:  node test-pipeline-match.mjs
//
// Counterparty/deal fixtures live in the UNTRACKED pipeline-guard.local.json
// (externalized 2026-06-11 — deal names never live in this tracked file).
//
// FAIL-LOUD, hardened 2026-09-18. This used to resolve the guard RELATIVE to this
// file and, when absent, skip the deal cases and let the suite pass on a degraded
// ORA-self floor — so the suite went green on exactly the installs where the floor
// was broken. It now loads the CANONICAL ABSOLUTE PATH and exits non-zero if the
// guard is missing or empty. Set ORA_PIPELINE_GUARD to override the path.

import { readFileSync, statSync } from 'node:fs'
import { env, exit } from 'node:process'

const GUARD_FILE = env.ORA_PIPELINE_GUARD
  ?? 'C:\\Users\\Owner\\.claude\\skills\\county-parcel-screen\\data\\pipeline-guard.local.json'

let G = null
try {
  G = JSON.parse(readFileSync(GUARD_FILE, 'utf8'))
} catch (e) {
  console.error(`FAIL  never-call counterparty floor UNAVAILABLE — cannot load ${GUARD_FILE}\n      ${e.message}`)
  console.error('      The guard is untracked and lives ONLY at the canonical absolute path above;')
  console.error('      it is absent from the ora-skills repo checkout and the AppData plugin bundle.')
  console.error('      Degraded ORA-self-only screening was removed 2026-09-18 — this is a STOP.')
  exit(1)
}
const NEVER_CALL_NAMES = G.never_call_names ?? []
if (!NEVER_CALL_NAMES.length) {
  console.error(`FAIL  guard ${GUARD_FILE} carries zero never_call_names — it screens nothing. STOP.`)
  exit(1)
}
// Guard evidence, as every deliverable must record it (SKILL.md rule 4): path,
// UTC mtime, and BOTH counts. never_call_names is what this workflow screens on;
// never_call_patterns is what institutional_owners.py screens on — different
// lists, so citing only one can look screened while the other is empty. Matches
// institutional_owners.guard_evidence() byte for byte on the same file.
console.log(`GUARD ${GUARD_FILE}  modified=${statSync(GUARD_FILE).mtime.toISOString()}`
  + `  never_call_names=${NEVER_CALL_NAMES.length}`
  + `  never_call_patterns=${(G.never_call_patterns ?? []).length}\n`)

function norm(s) {
  return String(s || '').toUpperCase().replace(/[^A-Z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim()
}
function roadCore(addr) {
  let s = norm(addr)
  s = s.replace(/\b[A-Z]{2} \d{5}( \d{4})?\b.*$/, '')
  s = s.replace(/^\d+[A-Z]? /, '')
  s = s.replace(/\b\d{5}\b/g, ' ')
  s = s.replace(/\bSTREET\b/g, 'ST').replace(/\bROAD\b/g, 'RD').replace(/\bDRIVE\b/g, 'DR')
    .replace(/\bAVENUE\b/g, 'AVE').replace(/\bPARKWAY\b/g, 'PKWY').replace(/\bBOULEVARD\b/g, 'BLVD')
    .replace(/\bHIGHWAY\b/g, 'HWY')
  s = s.replace(/\s+/g, ' ').trim()
  const m = s.match(/^(.+?\b(?:ST|RD|DR|AVE|PKWY|BLVD|HWY|PIKE|CT|LN|CIR|WAY|TRL|TER|PL|SQ|LOOP|RUN|ROUTE \d+|SR \d+))\b/)
  return (m ? m[1] : s).trim()
}
function contains(a, b, minLen) {
  return a && b && b.length >= minLen && (a.includes(b) || b.includes(a))
}
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

// Live pipeline shape (deal-level addresses + counterparty floor), as the Phase-0 guard returns it.
const guard = {
  deals: G.test_deals ?? [],
  counterparties: NEVER_CALL_NAMES,
}

// Regression for the 2026-09-18 fail-loud hardening: the floor must come from the
// guard file, never from the old hardcoded ORA-self pair. If these two are all we
// have, the degraded fallback is back and every "no match" below is meaningless.
const degraded = NEVER_CALL_NAMES.length <= 2
  && NEVER_CALL_NAMES.every((n) => ['OXFORD', 'GOLDBERG'].includes(String(n).toUpperCase()))
if (degraded) {
  console.error('FAIL  counterparty floor is the degraded ORA-self pair — the removed fallback has returned. STOP.')
  exit(1)
}

// Deal-specific cases come from the local guard file; generic cases stay inline.
const cases = [
  ...(G.mjs_guard_cases ?? []),
  ['Self-owned Oxford entity → hard drop',
    { owner: 'OXFORD INDUSTRIAL HOLDINGS LLC', siteAddress: '9 Anywhere Dr, Carlisle OH' }, 'counterparty'],
  ['Clean unrelated industrial parcel → no match',
    { owner: 'PAC HOLDINGS LLC', siteAddress: '300 Industry Drive, Carlisle OH 45005' }, null],
  ['Different route number, same county → no false road match',
    { owner: 'RF&T PROPERTIES LLC', siteAddress: 'STATE ROUTE 132, Clermont County OH' }, null],
]

let pass = 0, fail = 0
for (const [label, cand, expected] of cases) {
  const got = pipelineMatch(cand, guard)
  const ok = got === expected
  console.log(`${ok ? 'PASS' : 'FAIL'}  [${label}]  expected=${expected} got=${got}`)
  ok ? pass++ : fail++
}
console.log(`\n${pass}/${pass + fail} passed`)
process.exit(fail ? 1 : 0)
