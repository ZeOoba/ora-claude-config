import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type {
  Decision,
  FleetSnap,
  PeerDecisions,
  TrackerDecision,
  TrackerSnap,
} from '../types'

// ---------------------------------------------------------------- constants

const PLUGIN = 'ora-ops-panel'
const PANE = 'ora-ops'
const TITLE = 'Ops'

const HOME = 'C:/Users/Owner'
// Absolute path only (review 2026-11-14): a bare `python` resolves through the session's cwd
// first on Windows, so a repo with its own python.exe would run in every session.
const PYTHON = `${HOME}/AppData/Local/Programs/Python/Python313/python.exe`
const FLEET_SCRIPT = `${HOME}/.claude/maintenance/fleet-status.py`
const TRACKER = `${HOME}/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md`
// One file per session, each written only by its own session (single writer).
const DECISION_DIR = `${HOME}/.claude/ora-ops-panel/decisions`

const FLEET_EVERY_MS = 10 * 60_000
const TRACKER_EVERY_MS = 15 * 60_000
const PEERS_EVERY_MS = 60_000
const PEER_MAX_AGE_MS = 3 * 24 * 3600_000

// Change a tag when that value's fields change: it declines what an earlier
// version stored, which outlives a reload.
const fleet = atom({ plugin: 'ora-ops-panel', key: 'fleet' } as const, null, { shape: 'fleet-1' })
const decisions = atom({ plugin: 'ora-ops-panel', key: 'decisions' } as const, [], { shape: 'dec-1' })
const peers = atom({ plugin: 'ora-ops-panel', key: 'peers' } as const, [], { shape: 'peers-1' })
const tracker = atom({ plugin: 'ora-ops-panel', key: 'tracker' } as const, null, { shape: 'trk-1' })
const busy = atom({ plugin: 'ora-ops-panel', key: 'busy' } as const, false)

// ---------------------------------------------------------------- pure helpers

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)
/** One line, no control characters: what the pane shows is what a press submits. */
export const oneLine = (s: string) => s.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s{2,}/g, ' ').trim()
/** Hard cap on a decision's question. The pane shows it whole (never clipped), so a press can
 * never submit text Gabriel did not see (review 2026-11-14, finding 1). */
export const QUESTION_MAX = 120
export const OPTION_MAX = 60
export const CONTEXT_MAX = 200

/** A decision from any source (this session's tool call or a peer's file), validated and
 * normalized; null when it is not a usable decision. */
export function validDecision(d: any): Decision | null {
  if (!d || typeof d !== 'object') return null
  if (typeof d.id !== 'string' || typeof d.question !== 'string' || !Array.isArray(d.options)) return null
  const question = clip(oneLine(d.question), QUESTION_MAX)
  const options = d.options.filter((o: unknown) => typeof o === 'string')
    .map((o: string) => clip(oneLine(o), OPTION_MAX)).filter(Boolean).slice(0, 4)
  if (!question || options.length === 0) return null
  return {
    id: clip(oneLine(d.id), 40),
    question,
    options,
    context: typeof d.context === 'string' && d.context ? clip(oneLine(d.context), CONTEXT_MAX) : undefined,
    postedAt: Number.isFinite(d.postedAt) ? d.postedAt : 0,
    outcome: typeof d.outcome === 'string' ? d.outcome : undefined,
  }
}

/** The exact text a pane press submits: a fixed template, every model-written part quoted. */
export const decisionPrompt = (d: Decision, choice: string) =>
  `[Ops pane] Chose ${JSON.stringify(choice)} (option ${d.options.indexOf(choice) + 1} of ${d.options.length}) ` +
  `for decision ${d.id}: ${JSON.stringify(d.question)}`
const strip = (s: string) => s.replace(/\*\*|`|\\\|/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').trim()
const ago = (ms: number) => {
  const m = Math.round((Date.now() - ms) / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  return h < 48 ? `${h}h ago` : `${Math.round(h / 24)}d ago`
}
const list = (ids: string[], n = 3) =>
  ids.length <= n ? ids.join(', ') : `${ids.slice(0, n).join(', ')} +${ids.length - n}`

/** Reduces fleet-status.py --json to the lines the pane shows. */
export function reduceFleet(d: any): Omit<FleetSnap, 'fetchedAt'> {
  const verdict = String(d?.verdict ?? 'UNKNOWN')
  const [level, ...rest] = verdict.split(' -- ')
  const flags: string[] = []
  const missingFleets = [...(d?.fleets_missing ?? []), ...(d?.fleets_unreadable ?? [])]
  if (missingFleets.length) flags.push(`registry unreadable: ${missingFleets.join(', ')} (view is PARTIAL)`)
  const missed: any[] = d?.missed_cycle ?? []
  if (missed.length)
    flags.push(`missed cycle: ${list(missed.map(m => `${m.id} (${Math.round(m.effective_gap_hours ?? m.gap_hours)}h)`))}`)
  const overdue: string[] = d?.never_ran_overdue ?? []
  if (overdue.length) flags.push(`never-ran overdue (${overdue.length}): ${list(overdue)}`)
  const expired: any[] = d?.expired_needs_attention ?? []
  if (expired.length) flags.push(`stuck one-time (${expired.length}): ${list(expired.map(x => x.id ?? String(x)))}`)
  const skips = Number(d?.recent_skip_events_24h ?? 0)
  if (skips) flags.push(`throttle skips last 24h: ${skips}`)
  const dupes = Object.keys(d?.cross_fleet_duplicates ?? {})
  const coll = Object.keys(d?.collisions ?? {}).length
  if (dupes.length || coll)
    flags.push(`${coll} same-time collision(s) · ${dupes.length} cross-fleet dupe(s)${dupes.length ? `: ${list(dupes, 2)}` : ''}`)
  return {
    generatedAt: String(d?.generated_at ?? ''),
    level: (level ?? '').trim() || 'UNKNOWN',
    detail: rest.join(' -- ').trim(),
    enabledCc: Number(d?.per_fleet_enabled?.cc ?? 0),
    enabledLams: Number(d?.per_fleet_enabled?.lams ?? 0),
    flags,
  }
}

// Phrases that mark a row as waiting on Gabriel. A phrase followed by a date
// ("Gabriel's call 2026-07-24: ...") or led by "per"/"given" records a
// decision already made, so it does not count.
const ASK = /needs gabriel|gabriel'?s (?:call|decision|merge|confirmation|approval|go-ahead|ruling|answer|sign-off)|awaiting (?:real review\/)?gabriel|decision needed|pending gabriel|gabriel (?:to|must|should) (?:decide|confirm|approve|choose|pick|rule)|blocked on gabriel/gi
const DONE_LEAD = /^\s*\*{0,2}\s*(RESOLVED|CLOSED|DONE|MERGED|PARKED|SUPERSEDED)/i

/** Lifts open rows that wait on a decision from the tracker's ## Open table. */
export function parseTracker(md: string): TrackerDecision[] {
  const start = md.indexOf('\n## Open')
  if (start < 0) return []
  const after = md.slice(start + 8)
  const end = after.indexOf('\n## ')
  const section = end < 0 ? after : after.slice(0, end)
  const out: TrackerDecision[] = []
  for (const line of section.split('\n')) {
    const m = /^\| \[(OI-\d+)\]\(#OI-\d+\) \| ([\d-]+) \| (.*?) \| (.*) \|\s*$/.exec(line)
    if (!m) continue
    const oi = m[1] ?? '', opened = m[2] ?? '', body = m[4] ?? ''
    if (DONE_LEAD.test(body)) continue
    let hit: RegExpExecArray | null = null
    ASK.lastIndex = 0
    for (let r = ASK.exec(body); r; r = ASK.exec(body)) {
      const before = body.slice(Math.max(0, r.index - 7), r.index).toLowerCase()
      const tail = body.slice(r.index + r[0].length, r.index + r[0].length + 8)
      if (/\b(per|given)\s+$/.test(before) || /^[\s,]+\d{4}-/.test(tail)) continue
      hit = r
      break
    }
    if (!hit) continue
    const boldTitle = /^\s*\*\*(.+?)\*\*/.exec(body)
    out.push({
      oi,
      opened,
      title: clip(strip(boldTitle?.[1] ?? body), 140),
      ask: clip(strip(body.slice(hit.index, hit.index + 200)), 160),
    })
  }
  return out.sort((a, b) => b.opened.localeCompare(a.opened))
}

// ---------------------------------------------------------------- register

// Set at session.start (which a reload runs again).
let sessionId = ''
let label = ''
const ownFile = () => `${DECISION_DIR}/${sessionId}.json`

async function persistOwn($: any) {
  if (!sessionId) return
  const mine = await read($, decisions)
  const open = mine.filter(d => !d.outcome)
  await $.fs.write(ownFile(), JSON.stringify({ sessionId, label, updatedAt: Date.now(), decisions: open }, null, 1))
}

async function refreshFleet($: any) {
  // One run at a time per session: Refresh, /ops and the timer used to stack concurrent runs.
  if (await read($, busy)) return
  await update($, busy, () => true)
  let snap: FleetSnap
  try {
    const r = await $.process.run([PYTHON, FLEET_SCRIPT, '--json'], { timeoutMs: 60_000 })
    snap = { ...reduceFleet(JSON.parse(r.stdout)), fetchedAt: Date.now() }
  } catch (err) {
    snap = {
      generatedAt: '',
      level: 'UNKNOWN',
      detail: '',
      enabledCc: 0,
      enabledLams: 0,
      flags: [],
      error: `fleet-status.py did not run: ${String((err as Error)?.message ?? err).slice(0, 160)}`,
      fetchedAt: Date.now(),
    }
  } finally {
    await update($, busy, () => false)
  }
  await update($, fleet, () => snap)
}

async function refreshTracker($: any) {
  let snap: TrackerSnap
  try {
    snap = { items: parseTracker(await $.fs.read(TRACKER)), fetchedAt: Date.now() }
  } catch (err) {
    snap = { items: [], error: `tracker unreadable: ${String((err as Error)?.message ?? err).slice(0, 120)}`, fetchedAt: Date.now() }
  }
  await update($, tracker, () => snap)
}

async function refreshPeers($: any) {
  let out: PeerDecisions[] = []
  try {
    if (!(await $.fs.exists(DECISION_DIR))) return update($, peers, () => [])
    const entries = await $.fs.list(DECISION_DIR)
    for (const f of entries) {
      if (f.kind !== 'file' || !f.name.endsWith('.json')) continue
      if (f.name === `${sessionId}.json`) continue
      if (Date.now() - f.mtimeMs > PEER_MAX_AGE_MS) continue
      try {
        const j = JSON.parse(await $.fs.read(`${DECISION_DIR}/${f.name}`))
        // Peer files are untrusted input: validate every field before it reaches the pane.
        const raw = Array.isArray(j?.decisions) ? j.decisions : []
        const open = raw.map(validDecision).filter((d: Decision | null): d is Decision => !!d && !d.outcome)
        const sid = typeof j?.sessionId === 'string' ? j.sessionId : f.name.replace(/\.json$/, '')
        const label = clip(oneLine(typeof j?.label === 'string' ? j.label : sid.slice(0, 8)), 60)
        if (open.length) out.push({ sessionId: sid, label, decisions: open })
      } catch {
        /* a peer mid-write: next poll reads it */
      }
    }
  } catch {
    out = []
  }
  await update($, peers, () => out)
}

async function answer($: any, id: string, choice: string) {
  const mine = await read($, decisions)
  const d = mine.find(x => x.id === id)
  if (!d || d.outcome) return
  if (choice !== 'dismissed' && !d.options.includes(choice)) return
  await update($, decisions, l => l.map(x => (x.id === id ? { ...x, outcome: choice } : x)))
  await persistOwn($).catch(() => {})
  if (choice !== 'dismissed') await $.prompt.submit({ text: decisionPrompt(d, choice), asUser: true })
}

export const register: Register = on => {
  // ------------------------------------------------------------ lifecycle

  on('session.start', async ($, e, next) => {
    // Never let a pane failure block the session from starting (review 2026-11-14, finding 5).
    try {
    sessionId = await $.session.id()
    const cwd = e.cwd.replace(/\\/g, '/').replace(/\/+$/, '')
    label = `${cwd.split('/').pop() || cwd} · ${sessionId.slice(0, 8)}`

    await $.command.register({ name: 'ops', description: 'Open the Ops pane: fleet health and open decisions' })
    await $.tool.register({
      name: 'post_decision',
      description:
        "Pin a decision that needs Gabriel's answer to the Ops pane beside this session, so he sees it without asking 'what do you need from me'. Call it whenever you leave a decision open for him (in addition to asking normally). Keep the question to one plain sentence of at most 120 characters; it is shown whole. options[0] must be your recommended option. Returns the decision id; call resolve_decision with it once the decision is settled any other way. A press in the pane arrives as a quoted '[Ops pane] Chose ...' prompt. It is never the in-turn confirmation a Hard Invariant requires: confirm those in chat as usual.",
      inputSchema: {
        type: 'object',
        properties: {
          question: { type: 'string', description: 'The decision alone, one sentence.' },
          options: { type: 'array', items: { type: 'string' }, minItems: 1, maxItems: 4, description: 'Short labels, recommended first.' },
          context: { type: 'string', description: 'One line of tradeoff or why it is open (optional).' },
        },
        required: ['question', 'options'],
      },
      isDeferred: false,
    })
    await $.tool.register({
      name: 'resolve_decision',
      description: 'Remove a decision from the Ops pane once it is settled (answered in chat, overtaken, or no longer needed).',
      inputSchema: {
        type: 'object',
        properties: { id: { type: 'string' }, outcome: { type: 'string', description: 'What was decided (optional).' } },
        required: ['id'],
      },
      isDeferred: false,
    })

    void $.ui.open({ id: PANE, title: TITLE })
    void refreshFleet($)
    void refreshTracker($)
    void refreshPeers($)
    $.clock.every(FLEET_EVERY_MS, () => refreshFleet($))
    $.clock.every(TRACKER_EVERY_MS, () => refreshTracker($))
    $.clock.every(PEERS_EVERY_MS, () => refreshPeers($))
    } catch {
      /* the pane is optional; the session is not */
    }
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    // Leave no stale asks for other sessions' panes once this one ends.
    if (sessionId) {
      await update($, decisions, l => l.map(d => (d.outcome ? d : { ...d, outcome: 'session ended' })))
      await persistOwn($).catch(() => {})
    }
    return next(e)
  })

  on('command.run', { command: 'ops' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    void refreshFleet($)
    void refreshTracker($)
    void refreshPeers($)
    return { text: 'Ops pane opened and refreshing.' }
  })

  // ------------------------------------------------------------ tools

  on('tool.call', { tool: 'mcp__ora-ops-panel__post_decision' }, async ($, e: any) => {
    const d = validDecision({
      id: `d${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
      question: typeof e.question === 'string' ? e.question : '',
      options: e.options,
      context: e.context,
      postedAt: Date.now(),
    })
    if (!d) return { deny: 'question (text) and at least one option (text) are required' }
    await update($, decisions, l => [...l.filter(x => !x.outcome), d].slice(-12))
    try {
      await persistOwn($)
    } catch (err) {
      return { result: `Pinned to this session's pane as ${d.id}; not shared with other sessions (${String((err as Error)?.message ?? err).slice(0, 80)}).` }
    }
    // Plugin tools answer a string result (the engine refuses an object).
    return { result: `Pinned to the Ops pane as ${d.id}.` }
  })

  on('tool.call', { tool: 'mcp__ora-ops-panel__resolve_decision' }, async ($, e: any) => {
    const id = String(e.id ?? '')
    const mine = await read($, decisions)
    if (!mine.some(d => d.id === id && !d.outcome)) return { result: `No open decision ${id}.` }
    await update($, decisions, l => l.map(d => (d.id === id ? { ...d, outcome: String(e.outcome ?? 'resolved') } : d)))
    await persistOwn($)
    return { result: `Cleared ${id} from the Ops pane.` }
  })

  // ------------------------------------------------------------ drawing

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const width = Math.max(30, e.props.bodyColumns ?? 60)
    const f = await read($, fleet)
    const mine = (await read($, decisions)).filter(d => !d.outcome)
    const others = await read($, peers)
    const trk = await read($, tracker)
    const isBusy = await read($, busy)

    const levelColor = (l: string) => (l === 'OK' ? 'success' : l === 'ATTENTION' || l === 'PARTIAL' ? 'warning' : 'error')

    const decisionBlock = (d: Decision, answerable: boolean) => (
      <Box key={d.id} flexDirection="column" marginBottom={1}>
        <Text bold>{d.question}</Text>
        {d.context ? <Text dimColor>{clip(d.context, width * 2)}</Text> : null}
        {answerable ? (
          <Box flexDirection="row" flexWrap="wrap" gap={1}>
            {d.options.map((o, i) => (
              <Button
                key={`${d.id}-${i}`}
                label={i === 0 ? `${o} (Rec)` : o}
                variant={i === 0 ? 'primary' : 'secondary'}
                onPress={() => answer($, d.id, o)}
              />
            ))}
            <Button key={`${d.id}-x`} label="Dismiss" plain onPress={() => answer($, d.id, 'dismissed')} />
          </Box>
        ) : (
          <Text dimColor>{d.options.map((o, i) => (i === 0 ? `${o} (Rec)` : o)).join(' · ')}</Text>
        )}
      </Box>
    )

    const peerCount = others.reduce((n, p) => n + p.decisions.length, 0)

    return (
      <Box flexDirection="column">
        {/* ---- fleet */}
        <Box flexDirection="row" justifyContent="space-between">
          <Text bold>FLEET</Text>
          <Button key="refresh" label={isBusy ? 'Refreshing…' : 'Refresh'} plain onPress={() => { void refreshFleet($); void refreshTracker($); void refreshPeers($) }} />
        </Box>
        {!f ? (
          <Text dimColor>Running fleet-status.py…</Text>
        ) : f.error ? (
          <Text color="error">{f.error}</Text>
        ) : (
          <Box flexDirection="column">
            <Text>
              <Text bold color={levelColor(f.level)}>● {f.level}</Text>
              <Text dimColor>{`  enabled cc ${f.enabledCc} · lams ${f.enabledLams} · ${ago(f.fetchedAt)}`}</Text>
            </Text>
            {f.flags.length === 0 ? <Text dimColor>No flags.</Text> : f.flags.map((fl, i) => <Text key={`fl${i}`}>{`· ${clip(fl, width * 2)}`}</Text>)}
            <Text dimColor>Snapshot, not live state — re-run before acting on a flag.</Text>
          </Box>
        )}

        {/* ---- this session */}
        <Box marginTop={1}>
          <Text bold>{`NEEDS YOU — THIS SESSION (${mine.length})`}</Text>
        </Box>
        {mine.length === 0 ? <Text dimColor>Nothing pending from this session.</Text> : mine.map(d => decisionBlock(d, true))}

        {/* ---- other sessions */}
        <Box marginTop={1}>
          <Text bold>{`OTHER SESSIONS (${peerCount})`}</Text>
        </Box>
        {peerCount === 0 ? (
          <Text dimColor>No other session has a decision pinned.</Text>
        ) : (
          others.map(p => (
            <Box key={p.sessionId} flexDirection="column">
              <Text color="suggestion">{`session ${p.label}`}</Text>
              {p.decisions.map(d => decisionBlock(d, false))}
            </Box>
          ))
        )}

        {/* ---- tracker */}
        <Box marginTop={1}>
          <Text bold>{`STANDING — OPEN-ITEMS TRACKER (${trk?.items.length ?? 0})`}</Text>
        </Box>
        {!trk ? (
          <Text dimColor>Reading tracker…</Text>
        ) : trk.error ? (
          <Text color="error">{trk.error}</Text>
        ) : trk.items.length === 0 ? (
          <Text dimColor>No open row waits on a decision.</Text>
        ) : (
          trk.items.map(t => (
            <Box key={t.oi} flexDirection="column" marginBottom={1}>
              <Button
                key={`trk-${t.oi}`}
                plain
                onPress={() => $.prompt.fill({ text: `Let's settle ${t.oi} (open-items tracker): `, mode: 'replace' })}
              >
                {t.oi} <Text dimColor>{t.opened}</Text>
              </Button>
              <Text>{clip(t.title, width * 2)}</Text>
              <Text dimColor>{`asks: ${clip(t.ask, width * 2)}`}</Text>
            </Box>
          ))
        )}
        <Text dimColor>Tracker rows matched by phrase (heuristic) — click an id to draft a prompt.</Text>
      </Box>
    )
  })
}
