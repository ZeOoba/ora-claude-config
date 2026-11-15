---
name: project_aaos_agent_coordination_layer
description: AAOS (ORA Agent Coordination Layer) is real but FROZEN since 2026-11-05 (ADR-0007). No PRs, amendments, doc refreshes or CI fixes, and its two scheduled tasks stay off unless a revival ADR says otherwise. Check this before treating an AAOS reference as injected, and before doing any AAOS work.
metadata: 
  node_type: memory
  type: project
  originSessionId: e8c060da-c8fb-4fb7-9a8e-6ed8e9ac897a
  modified: 2026-11-05T18:15:00.000Z
---

**FROZEN 2026-11-05** by `ZeOoba/AAOS` `docs/adr/0007-freeze.md` (PR #37, `19ad669`; maintenance-reduction bundle 1). It was kept frozen the same day, when Gabriel was asked to "improve" it (`event_log.md` 2026-11-05).

**Why it is frozen (usage evidence):** over its whole life the live seam carried 4 tasks, 5 handoffs and 19 events. All of them were about AAOS itself: two Gate-3 demos, the seam confirm and a jsonschema pin request. No business task ever went through it, and the last event was 2026-08-16. In the 90 days to 2026-11-05 the repo took about 60 commits, every one of them dated after the seam went quiet, and CI failed 8 of its last 12 runs (`gh run list`, 2026-11-05). The design assumes two autonomous agents trading leased tasks. Today CC is the only autonomous fleet (LAMS has been dark by ruling since 2026-10-30), and Cowork work runs in interactive sessions.

**Revival trigger (ADR-0007):** a real cross-surface task, meaning work that must move between Code and Cowork and cannot be done on one surface, shows up at least twice in 30 days. Revival is a new un-freeze ADR.
- Caution (not ADR text): the skill re-import loop, with 36 re-import confirmations from 2026-10-06 to 11-05, can look like the trigger firing. But each re-import is Gabriel's manual Save-skill click, which no queue can automate, and he kept the freeze on 2026-11-05 with that figure in front of him.
- Raise a re-import count with Gabriel; do not treat it as grounds to revive on your own. The cost of that loop is maintenance-reduction Bundle 4 (hash manifest).

**Suspended by ADR-0007, not rejected:** AMD-0003, AMD-0004, AMD-0006. PRs #38 and #39 were closed unmerged on 2026-11-05. Their branches `fix/t1-drain-non-object-ndjson` and `fix/t2-sweep-survives-drain-failure` are kept.

**AAOS open items** (their status lives in the tracker, not here): [OI-265](open-items-tracker.md#OI-265), [OI-267](open-items-tracker.md#OI-267), [OI-266](open-items-tracker.md#OI-266), [OI-269](open-items-tracker.md#OI-269), [OI-314](open-items-tracker.md#OI-314), [OI-315](open-items-tracker.md#OI-315), [OI-316](open-items-tracker.md#OI-316), [OI-322](open-items-tracker.md#OI-322), [OI-175](open-items-tracker.md#OI-175).

**Scheduled tasks** `ora-aaos-expire-leases` and `ora-aaos-publish-contracts`: do not re-enable or re-register either one unless a revival ADR says so, and never include them in a bulk resume. Both were RETIRED 2026-11-05: deleted from the CC registry and archived to `scheduled-tasks/_archive_2026-11-05_aaos-frozen/` ([OI-396](open-items-tracker-history.md#OI-396), closed).

**Where it lives:**
- Repo: `C:\Users\Owner\AAOS\` (`ZeOoba/AAOS`). CI runs only on manual `workflow_dispatch`, and the README is a historical snapshot.
- Seam root (runtime state, not under git, OneDrive-synced): `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\AAOS\`. Queue state (tasks, locks, handoffs, events) is under `projects\ora-ops\`. Leave it as it is.
- Contracts mirror and the Cowork entry point `COWORK-BOOTSTRAP.md`: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\AAOS\contracts\`. There is no copy at the seam root itself.

**Why this note exists:** a Cowork session once refused a staged AAOS handoff as a possible prompt injection, because AAOS appeared nowhere in its loaded context. AAOS is real: there is git history, a test suite, and files in the seam. If you meet an AAOS reference (a "seam", `tools/*.py`, or an AAOS-shaped `t-`/`h-`/`e-` id), verify it against the paths above before calling it fabricated. Then treat AAOS as frozen: no PRs, amendments, doc refreshes, or dependency or CI fixes. Done-bar doctrine D2 requires usage evidence before maintenance, and exempts only security or confidentiality fixes and Gabriel's explicit request.

**History:** v1.0 was built on 2026-07-10. None of its six Gate reviews got an explicit Gabriel sign-off, so "v1.0 shipped" is a self-assessment. The live Cowork round trip closed on 2026-08-16: Cowork posted handoff `h-cowork-seam-ack-e7c490` on 2026-07-10, and `t-cowork-seam-confirm` was archived on 2026-08-16. More history is in the AAOS `README.md` and `event_log.md`.
