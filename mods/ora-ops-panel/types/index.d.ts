/** One fleet-status.py --json snapshot, reduced to what the pane draws. */
export type FleetSnap = {
  /** fleet-status.py's own generated_at (local time, ISO). */
  generatedAt: string
  /** First word of the verdict: OK, ATTENTION, FAIL, PARTIAL ... */
  level: string
  /** The verdict line after its level word. */
  detail: string
  enabledCc: number
  enabledLams: number
  /** One line per flagged condition, most urgent first. */
  flags: string[]
  /** Set when the probe could not run or its output did not parse. */
  error?: string
  /** Epoch ms the pane fetched it. */
  fetchedAt: number
}

/** A decision a session posted for Gabriel through post_decision. */
export type Decision = {
  id: string
  question: string
  /** options[0] is the recommended one. */
  options: string[]
  context?: string
  postedAt: number
  /** Unset while open; the chosen option (or "dismissed"/"resolved") once closed. */
  outcome?: string
}

/** Another session's open decisions, read from its file. */
export type PeerDecisions = {
  sessionId: string
  label: string
  decisions: Decision[]
}

/** A standing decision row lifted from the open-items tracker. */
export type TrackerDecision = {
  oi: string
  opened: string
  title: string
  ask: string
}

export type TrackerSnap = {
  items: TrackerDecision[]
  error?: string
  fetchedAt: number
}

declare module 'claude-code' {
  interface PluginState {
    'ora-ops-panel': {
      fleet: Shaped<FleetSnap | null>
      decisions: Shaped<Decision[]>
      peers: Shaped<PeerDecisions[]>
      tracker: Shaped<TrackerSnap | null>
      busy: boolean
    }
  }
}
