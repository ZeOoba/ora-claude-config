# Handoff → whoever moves the shared checkout off `feat/model-canary-probe-step25`

**From:** session `21c98da5` (host `local_c689f07f-d45a-473e-94d9-3f418c47e5cd`), 2026-08-09.
**Intended recipient:** session `633f8f1a` (host `local_112718cc-…`), which holds the
Gabriel-directed `repo-housekeeping` claim "move shared-checkout HEAD off merged
feat/model-canary-probe-step25 back to main".
**Status:** UNDELIVERED via `send_message` — that session is unattended (scheduled/dispatched),
and unattended sessions can neither send nor receive. Gabriel to relay, or whoever picks the
branch work up next.

## The point

**Do not treat `feat/model-canary-probe-step25` as "just the model-canary work."** It carries
**5 commits that exist only on this laptop** — 0 behind its own upstream, 5 ahead of it, and
8 behind `origin/main`. They are from at least three different sessions:

```
fb1edfa  fix(guard): revive 4 dead test assertions; close the C.3 subject-flip gap
f2d04f1  docs(memory): close OI-107 + OI-108; record the agent-vs-host session-id gotcha   <- 21c98da5
b9cabdb  memory(people): re-verify brokers against Outlook (59d stale); correct Catfish claim
8fca11d  Merge fix/claim-host-session-id: host id on claims + --paths accumulation          <- 21c98da5
369c62b  fix(hooks): record host_session_id on claims; make --paths accumulate              <- 21c98da5
```

Moving HEAD without carrying these forward strands them.

## How three of them got there (so you can judge the other two)

Reflog, unambiguous:

```
10:41:10  checkout: moving from main to feat/model-canary-probe-step25
11:20:30  merge fix/claim-host-session-id            -> 8fca11d
11:46:13  commit docs(memory): close OI-107 + OI-108 -> f2d04f1
```

Session `21c98da5` ran its pre-merge safety checks against `HEAD` but never verified that HEAD
*was* `main`, then labelled its own output "main HEAD". Its three commits landed here purely by
accident. **`b9cabdb` and `fb1edfa` are NOT from that session** — confirm with their authors
rather than assuming they were deliberate; the same accident is the likeliest explanation.

This is the gap session `1d88885d` is separately claimed to close: shared-checkout-guard warns
on dirty files but not on branch identity.

## What has and has not been done

- **Pushed** `feat/model-canary-probe-step25` to its own upstream as off-machine backup of all 5
  (Gabriel's call). It does not touch `main` and does not move local HEAD, so it does not
  interfere with the branch remediation. NOTE: the machine's DNS/IPv6 fault makes pushes flaky —
  the first attempt died on `Could not resolve host: github.com`. See
  `reference_machine_dns_ipv6_fault_stalls_network_tooling.md`; retry usually works.
- **NOT attempted:** landing any of these on `main`. That sits inside the `repo-housekeeping`
  claim and was deliberately left alone rather than raced.

## If it helps you decide how to carry them

`369c62b` + `8fca11d` are the `claim_work.py` fix — 2-round independent review
(`claude-fable-5`, APPROVED WITH NITS), full `hooks/tests` 44/44 green, review artifact recorded
against `eos-review-gate`. That fix is why claim broadcasts now print `(message it at <host id>)`.
`f2d04f1` is memory-only (OI-107 / OI-108 closures).

## One caution if you rebase rather than merge

`f2d04f1` was staged with the isolated-hunk splice against a specific parent, and
`open-items-tracker.md` / `event_log.md` **still hold three other sessions' uncommitted work in
the working tree**. A rebase touching those paths is exactly where uncommitted content gets
clobbered — OI-100's status was clobbered that way earlier today by a whole-file rewrite and was
caught only by diffing against HEAD before committing. Diff before you commit anything on those
two files.
