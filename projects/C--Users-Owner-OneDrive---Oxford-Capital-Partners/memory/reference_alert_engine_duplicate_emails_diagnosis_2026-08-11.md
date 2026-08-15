---
name: alert-engine-duplicate-emails-diagnosis-2026-08-11
description: "The Command Center \"duplicate alert emails\" were NOT duplicates — same subject, different bodies (send-log `bytes=` proves it). Also: property_insurance_policies.property_id holds POLICY slugs, not property ids, matching 0 of 14 properties."
metadata: 
  node_type: memory
  type: reference
  originSessionId: caa2eb15-11e6-4635-a322-ad88c93c56db
  modified: 2026-08-12T20:31:10.078Z
---

Investigating the ORA send-log duplicate-email report (2026-08-11, oxford-command-center alert engine).

**⚠️ The 2026-06-21 evidence below is NO LONGER IN THE LIVE LOG.** `maintenance/ora-nightly-disk.ps1`
trims `send-log.txt` to the last 500 lines; it ran 2026-08-11 18:18 and cut the file from 602 to
504 lines, so it now starts 2026-07-10. The file is gitignored (`.gitignore:61`), so there is no
git recovery. The four verbatim lines below were captured from the live file at ~17:45 that same
day and are now the only surviving record. A REFUTE agent that read the file after 18:18
concluded the 06-21 incident "does not exist" — a rotation artifact, not a flaw in the evidence.
**Any forensic claim about this log needs its raw lines quoted at capture time; the window is
~500 sends wide and moves nightly.**

```
2026-06-21T10:58:56 ... subject="[ORA Command Center] CRITICAL: Policy expired — Sepich Portfolio (Several Locations, Columbus OH)" bytes=522
2026-06-21T10:58:57 ... subject="[ORA Command Center] CRITICAL: Policy expired — Sepich Portfolio (Several Locations, Columbus OH)" bytes=537
2026-06-21T10:58:58 ... subject="[ORA Command Center] CRITICAL: Policy expired — Airport Road, Easton MD 21601 (ETC POA)" bytes=512
2026-06-21T10:58:59 ... subject="[ORA Command Center] CRITICAL: Policy expired — Airport Road, Easton MD 21601 (ETC POA)" bytes=528
```

**`bytes=` in `_shared/send-log.txt` is the duplicate discriminator — subject equality is not.**
Four properties each produced two `CRITICAL: Policy expired — <property>` emails one second
apart on 2026-06-21, which read as a double-emit. They were not. The log's `bytes=` field
differed on every pair (522/537, 512/528, 505/522, 517/534): different bodies, same subject.
Root cause was a per-POLICY insight (`ins-lapsed-${p.id}` in `src/analytics/conditions.ts`)
carrying a title naming only the PROPERTY, and `renderAlert` builds the subject as
`[ORA Command Center] ${severity}: ${title}`. ORA properties routinely carry a Package (PCKG) +
Business Crime Liability (BCL) pair from Erie, so two genuinely lapsed policies arrived
indistinguishable. Decisive confirmation: the snapshot had 9 lapsed/cancelled rows and the run
sent exactly 9 emails, including 1851 South Club Dr — the only property with a single policy —
which sent once.

**Redacting a subject before grouping can manufacture a duplicate.** The 2026-07-12 "duplicate"
pair was `ins-1900broadway-bcl` vs `ins-1900broadway-**ufx**` and `ins-9050redbranch-bcl` vs
`-**pckg**` — four distinct subjects that a `INS-<n>BROADWAY` placeholder collapsed into two.
Group on the raw subject; redact only when reporting.

**`property_insurance_policies.property_id` holds POLICY-level slugs, not property ids.**
25 rows, 25 distinct values (`ins-fvc-pckg`, `ins-fvc-bcl`); **0 of 14** snapshot property ids
match it. Consequences, all verified by direct query, not inference: the per-property dedup
documented at the top of `server/warehouse/insurance-conditions.ts` was a no-op; raw slugs
reached Gabriel's subject line; and `insurance-gap` compared `coveredIds` (slugs) against
`prop.id`, so it claimed **every** property had no policy on file. The snapshot supplies the
missing join — `snapshot.insurance[].id` is the slug, `.property` is the property display name.

**But `insurance[].property` does NOT equal `properties[].name` — an exact name join resolves 0 of
25.** The two strings are independently maintained and differ in abbreviation and ZIP:
`"55 New Plant Court, Owings Mills MD 21117"` vs `"55 New Plant Ct, Owings Mills MD"`;
`"3540 E 5th Ave, Columbus OH 43219"` vs `"3540 E. 5th Ave, Columbus OH"`;
`"Sepich Portfolio (Several Locations, Columbus OH)"` vs `"Sepich Portfolio, Columbus OH (8 props)"`.
Normalizing case/whitespace does not close it. **Do NOT reach for the token/substring matcher in
`server/workbook/parse.ts:426` (`resolvePropertyId`)** — it resolves 24 of 25 but mis-attributes 4,
because the token `"columbus"` matches whichever Columbus property comes first, which would put a
WRONG property name into a CRITICAL alert subject (a fabricated fact in an alert — invariant 7).
An explicit 25-row slug→propertyId map is data and auditable; inference here is not.
Open work item: [open-items-tracker.md#OI-125](open-items-tracker.md#OI-125).

**Suppression usually exists and is mis-scoped — check before believing "there is no dedup".**
Both re-alert defects were reported as missing suppression; both had it.
`diffCriticalAlerts` did cross-run dedup but persisted `nextAlerted: [...currentCriticalIds]`,
overwriting the set every run, so a condition that transiently vanished was forgotten and
re-alerted on return. Proof it was flapping rather than a wiped state file: on 2026-07-24 the
14:00 run re-sent ONLY Granite Tops while CJ's/Hoodz/Sky Shield stayed quiet. Likewise
`scripts/lib/deploy-alert.ps1` had full streak/escalation/recovery machinery gated on
`Test-OfflineSignature` (`^git (fetch|pull)`) — so build/wrangler failures never entered it:
44 `Mirror deploy FAILED` sends against only 1 escalation and 3 recovery digests.
Consistent with [[feedback_absence_claims_need_verification_before_building]].

**A suppression streak must key on a failure CLASS, never the raw message.** `deploy-mirror.ps1`
embeds raw git stderr in the reason and the timeout reason embeds elapsed ms, so
`"...after 21038 ms"` and `"...after 74522 ms"` read as two different failures and reset the
streak every run — silently un-fixing the flood. Same trap for any dedup keyed on a rendered
string. Related: a partially-written PowerShell state file makes `$state.streakCount++` raise a
TERMINATING error, and `deploy-mirror.ps1` catches it bare — no email *and* no outbox fallback.
Both were found by adversarial review, not production.

**How to apply:** before treating same-subject emails as duplicates, compare `bytes=` in the
send log; equal subjects with unequal bytes mean a title that under-identifies its subject, not
a double-send. Before adding suppression anywhere in this repo, grep for the existing
mechanism and check what it is *keyed on* — twice here the machinery was sound and only its
key or its gate was wrong. Related: [[reference_command_center_mirror_deploy_gap]],
[[reference_parseleases_vacancy_block_phantom_leases_2026-08-03]].
