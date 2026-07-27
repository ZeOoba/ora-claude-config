---
name: feedback-verified-null-vs-inferred-null
description: "A check's \"found nothing\" is only trustworthy if it positively confirmed the absence; an empty result that could equally mean \"couldn't look\" is a failure, not a null result"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f02a7c04-1dae-43c4-8776-04cbbe39e27a
  modified: 2026-07-27T01:13:20.309Z
---

When any check, probe, scan, or report arm returns **zero**, ask which zero it is:

- **Verified null** — the check positively confirmed absence. Trustworthy. It asserts something concrete: rows show `effectiveDate` or later; the baseline is exactly 296 rows; the file does not exist.
- **Inferred null** — the check returned nothing and *nobody established it could have returned something*. A wrong path, a wrong shape, a swallowed exception, a renamed field, or a truncated fetch all produce this. **Treat it as a FAILURE, not a null result.**

The tell: if a broken lookup and a genuinely clean result produce identical output, the check cannot tell you anything when it comes back empty.

**Why:** the failure is invisible by construction. An OR-armed check whose broken arm returns zero still looks fully populated, because the surviving arm fills the report. Confirmed instances, all 2026-07-26:
- `answered.json` is a dict keyed by sessionId; the consumer iterated it as a list, got bare key strings, and reported "0 decided entries" while the file held 61 current entries. The section still looked complete because every candidate qualified on the other arm.
- `eos-telemetry-rollup.load_records` collapsed absent / all-lines-corrupt / mid-read I/O error / non-ASCII mangling into one bare `[]`, and the spec instructed the caller to treat the resulting message as valid. The `except: return []` also discarded already-collected records.
- A two-consecutive-week alert that treats an unparseable state marker as "no prior" can never fire at all if the marker writer breaks. **A suppressor that cannot report its own failure is indistinguishable from having no problem.**
- Domain instance, same shape: [[reference_delinquency_report_collection_status_blindspot]] — "no action taken" inferred from a static 90+ balance, wrong for 4 of 6 tenants.

**How to apply:** when writing or reviewing a check, make the empty cases discriminable — return a status alongside the data (`absent` / `ok` / `unreadable` / `corrupt`), never a bare empty collection. Reserve the benign "nothing found" message for the one branch that positively established absence, and emit a loud, differently-worded banner for the rest. Never let a bare `except` return an empty collection; preserve whatever was salvaged. When auditing existing specs, grep for reassuring phrasings — "is a VALID result, not a failure", "contributed nothing this run", "treat as no prior", "first-run safe" — each is a candidate, though some are legitimately verified nulls and should be ruled safe rather than churned. Related: [[feedback_fixture_shaped_tests_certify_dead_branches]] (0%/100% ⇒ suspect the emitter), [[feedback_verify_probe_findings_before_acting]].
