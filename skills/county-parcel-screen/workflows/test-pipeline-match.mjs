// Unit test for the parcel-screen-fanout v2 pipeline-conflict matcher.
// Helpers are mirrored from parcel-screen-fanout.js (the workflow sandbox can't
// import local modules, so they live inline there). KEEP IN SYNC.
// Run:  node test-pipeline-match.mjs
//
// Counterparty/deal fixtures live in the UNTRACKED data/pipeline-guard.local.json
// (externalized 2026-06-11 — deal names never live in this tracked file). If the
// file is absent, deal-specific cases are SKIPPED loudly and the floor degrades.

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

let G = null
try {
  G = JSON.parse(readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '..', 'data', 'pipeline-guard.local.json'),
    'utf8'))
} catch {
  console.log('⚠ data/pipeline-guard.local.json missing — deal-specific cases SKIPPED; floor degraded to ORA-self.')
}
const NEVER_CALL_NAMES = G?.never_call_names ?? ['OXFORD', 'GOLDBERG']

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
  deals: G?.test_deals ?? [],
  counterparties: NEVER_CALL_NAMES,
}

// Deal-specific cases come from the local guard file; generic cases stay inline.
const cases = [
  ...(G?.mjs_guard_cases ?? []),
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
