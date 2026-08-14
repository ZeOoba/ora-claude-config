---
name: ora-doctrine-integrity-guard
description: Daily doctrine/governor integrity guard (CC/MCP fleet) — push-independent backstop running doctrine-integrity-probe.py, governor-drift-probe.py (Hard Invariant 4, DSCR>=1.25/LTV<=40), eos-telemetry-rollup.py, and (v1.1) ora-skills repo_first_check.py --all; writes _state/doctrine-status.json, emails+posts to Notion ONLY on drift; clean run is silent. Supersedes retired "ORA EOS Health" Windows task. v1.1 2026-08-03 (Gabriel-directed): added a 4th engine — the REPO-FIRST cache-ahead sweep. ora-skills' pre-commit Check 5 catches a cache-ahead skill at commit time (when the mirror sync would clobber it), but a violation that never sees a commit previously waited on the weekly LAMS ora-skill-store-drift-check; this closes that gap to <=24h. The sweep ALWAYS exits 0 — alarm on its OUTPUT (`!! REPO-FIRST` lines, verdicts CACHE-AHEAD/DIVERGENT), never its exit code; script absent = SKIPPED, never an alarm. Four violations of this class surfaced in the nine days to 2026-08-03. v1.2 2026-08-10 (Gabriel-directed): added a 5th engine — the session-context backup (backup-session-context.py). v1.0 2026-07-08. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
output_contract:
  version: 1
  blocks:
    - id: block-doctrine-status-json
      artifact:
        type: file
        path: "C:\\Users\\Owner\\.claude\\maintenance\\_state\\doctrine-status.json"
      freshness_window_hours: 30
      expected_on:
        cron: "55 12 * * *"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Internal state file written every run via write-doctrine-status.py's write_status(), atomically overwriting this exact path (STEP 2 of this SKILL.md, path verified verbatim against the STEP 2 body text) — written on BOTH the clean path (STEP 4: source='scheduled', doctrine_rc=0, governor_rc=0) and the alarm path, so it is the correct primary signal for a guard that is silent-by-design on a clean run (STEP 4: 'send NOTHING — no email, no Notion post'). Checking the conditional alarm email/Notion post instead would false-alarm every healthy day. RESTORED 2026-08-10: this block was silently dropped when a description retag rewrote the frontmatter on 2026-08-09 09:41 — the documented OI-109 failure mode (update_scheduled_task drops non-owned frontmatter keys). Restored verbatim from commit 20a184d. A guard that is silent by design has NO other liveness signal, so losing this block makes its death undetectable. Diff this file against HEAD after ANY update_scheduled_task call."
---

You are the ORA doctrine/governor integrity guard, on the Claude Code (CC/MCP) fleet — this surface has native Bash/shell access, use it. You start fresh with no memory of prior runs; everything you need is below.

WHY THIS TASK EXISTS: two report-only probes guard the firm's doctrine and its financial governor, but until 2026-07-08 neither had a scheduled runner. `doctrine-integrity-probe.py` is now also wired into a git pre-push blocking gate — but that only fires when someone pushes to the `~/.claude` repo, which can be rare. `governor-drift-probe.py` had NO live wiring anywhere. This task is the push-independent daily backstop for BOTH: it runs them on a cadence regardless of push activity, and it preserves the lane-compliance telemetry rollup that the now-retired weekly "ORA EOS Health" email was the only consumer of (that raw-Windows-Task mechanism bypassed the dual-fleet scheduler doctrine and was found dead/unregistered when replaced — see `~/.claude/maintenance/_archive/README.txt`). This guard DETECTS drift; it NEVER corrects it.

---

STEP 1 — Execute all five engines via Bash, using the FULL interpreter path (bare `python` is NOT on PATH in a scheduled context). Run each, and capture its EXIT CODE and full STDOUT separately:

  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/doctrine-integrity-probe.py"
then
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/governor-drift-probe.py"
then
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/eos-telemetry-rollup.py"
then (added 2026-08-03, Gabriel-directed — REPO-FIRST sweep; skip silently if the script is absent, e.g. before PR #30 merges)
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/ora-skills/tools/repo_first_check.py" --all
then (added 2026-08-10, Gabriel-directed — SESSION-CONTEXT BACKUP; skip silently if the script is absent, e.g. before PR #47 merges)
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/backup-session-context.py"

Run it with NO arguments — its defaults already resolve to the live source, the local rotation, the OneDrive mirror and the scrub. Do NOT pass paths; a hand-typed path is how this silently starts backing up the wrong file.

Exit-code semantics (do NOT reimplement or second-guess the probes — they are AUTHORITATIVE, report-only, pure-stdlib):
- doctrine-integrity-probe.py: exit 0 = clean; non-zero = doctrine drift / a hard [MISSING] (a referenced slash-command/file/skill absent, CLAUDE.md word-budget breach, a bare dated annotation, or a confidential-term leak). No CLI flags — a bare live-mode run is correct. `[WARN]` lines are fail-OPEN (they never flip the exit code) — count them and surface the count, but they do not by themselves constitute an alarm.
- governor-drift-probe.py: exit 0 = clean; exit 1 = governor DRIFT found (a DSCR threshold != 1.25x or LTV ceiling != 40% somewhere, or the 1.75 regression sentinel) with the offending file:line; exit 2 = PROBE ERROR (the probe itself could not run cleanly — fail loud, investigate the probe, do not treat as "clean").
- eos-telemetry-rollup.py: always exits 0; handles empty/missing telemetry gracefully. Capture its short lane-compliance summary for the run log / alarm body.
- repo_first_check.py --all (added 2026-08-03): **ALWAYS exits 0 by design — its exit code carries no information; read its OUTPUT.** It sweeps every ora-skills skill against the AppData runtime cache and classifies the direction of any difference. A finding is any line beginning `!! REPO-FIRST` on stderr (verdict `CACHE-AHEAD` = cache content committed nowhere, i.e. a platform-side edit never committed; `DIVERGENT` = cache matches a commit off HEAD's ancestry). Both are REPO-FIRST violations and both ALARM per STEP 3. `IN-SYNC` / `REPO-AHEAD` / `NOT-INSTALLED` lines are normal — never alarm on them (REPO-AHEAD just means a committed change awaits reimport, which is `package-and-stage-skill`'s job, not this guard's). The script rescues each about-to-be-clobbered cache copy to `C:\Users\Owner\ora-skills\_staging\repo-first-rescue\<skill>\` — name that path in the alarm body so the content can be reconciled. **If the script does not exist, note "repo-first sweep: SKIPPED (script absent)" and continue — never treat its absence as an alarm or an engine error.** Why this runs here: `ora-skills`' own pre-commit Check 5 catches a cache-ahead skill at commit time (the moment the mirror sync would overwrite it), but a violation that never sees a commit needs a periodic sweep, and the only other one is the weekly LAMS `ora-skill-store-drift-check`. This closes that gap to ≤24h. Four violations of this class surfaced in the nine days to 2026-08-03.

- backup-session-context.py (added 2026-08-10): exit 0 = a snapshot was taken OR the content was unchanged (a no-op is the NORMAL result most days — `session-context.md` changes maybe once a day, and an unchanged run is success, not a miss). exit 1 = the source is MISSING or EMPTY, or the local snapshot could not be written — **this ALARMS per STEP 3**: `session-context.md` is auto-loaded into every session and is git-IGNORED, so it has no history to restore from; missing-or-truncated is a live incident, not a backup inconvenience. exit 2 = a usage error (argparse rejected a flag) — also alarm, it means this SKILL.md's invocation is wrong. **If the script does not exist, note "session-context backup: SKIPPED (script absent)" and continue — never an alarm or an engine error** (same contract as the repo-first sweep above).
  Two sub-results to SURFACE in the run log but NOT alarm on: (i) a `WARN -- mirror FAILED` line means OneDrive was offline/locked and only the local copy exists — routine and self-healing, since the next run's unchanged path performs a catch-up copy; if it persists for several consecutive days the off-machine leg is dead and that IS worth raising with Gabriel. (ii) a scrub verdict of `UNVERIFIED` means the confidentiality scan could not actually run (roster unreachable, target unreadable, or the scrub crashed) — the snapshot is still taken, but it is recorded as "nobody looked", never as clean. `HITS` means the snapshot carries active confidential terms: that is EXPECTED whenever a deal is live, is not drift, and must never be echoed — name only the verdict, never a term.

CONFIDENTIALITY (doctrine probe check 8): the probe deliberately references any confidential-term-leak finding by INDEX ONLY and never echoes the term itself. When you summarize or reproduce its output anywhere (Notion, email, run log), NEVER add or reconstruct a deal name or term — if check 8 flags (or WARNs on an unreadable terms file), note only that check 8 fired and point to the probe's own index reference. Never echo a term.

STEP 2 — Write the shared status file (best-effort, NON-FATAL). `C:\Users\Owner\.claude\maintenance\_shared\write-doctrine-status.py` exposes `write_status(source, doctrine_rc, doctrine_summary, governor_rc=None, governor_summary=None, guard_orphans=None, path=None)`, which atomically overwrites `C:\Users\Owner\.claude\maintenance\_state\doctrine-status.json`. AFTER both probes have run, invoke it with `source="scheduled"` and BOTH probes' real exit codes and terse one-line summaries:

  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" -c "import importlib.util as u; s=u.spec_from_file_location('wds', r'C:\Users\Owner\.claude\maintenance\_shared\write-doctrine-status.py'); m=u.module_from_spec(s); s.loader.exec_module(m); m.write_status(source='scheduled', doctrine_rc=<D>, doctrine_summary='<terse>', governor_rc=<G>, governor_summary='<terse>')"

Substitute `<D>`/`<G>` with the real exit codes and `<terse>` with short summaries (e.g. doctrine `"clean"` or `"DRIFT: N [MISSING], M [WARN]"`; governor `"clean"` / `"DRIFT exit1: file:line"` / `"PROBE ERROR exit2"`) — never a confidential term. If the import fails, LOG a one-line note and CONTINUE — a missing status-writer must NOT block the alarm/email logic below.

STEP 3 — ALARM CONDITION: an alarm fires if EITHER probe exits non-zero (doctrine != 0, OR governor != 0 — governor exit 2 is a probe error and ALSO alarms), OR the repo-first sweep printed one or more `!! REPO-FIRST` findings (its exit code is always 0 — read the output, not the code), OR the session-context backup exited non-zero (missing/empty source, unwritable snapshot, or a usage error — NOT a mirror warning and NOT an UNVERIFIED verdict, neither of which alarms). On an alarm, do BOTH (a) and (b); a failure of one does not skip the other:

  (a) POST a status page to the Notion Operations Hub. Parent page ID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. Title `Doctrine/Governor Integrity — [today's YYYY-MM-DD]`. Body: which probe(s) alarmed with exit codes; the doctrine probe's summarized [MISSING]/[WARN] findings (check 8 by index only, never a term); the governor probe's summarized finding; and the eos-telemetry lane-compliance one-liner. Publication + verification discipline:
      1. Call `notion-create-pages`; capture `pages[0].id` and `pages[0].url`.
      2. If the response is missing/errored/empty-id, retry ONCE with the same content.
      3. Verify via a DIRECT `notion-fetch` on the returned page id — confirm the title matches AND the ancestor path includes parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. NEVER verify via `notion-search` (documented search-index lag / same-title false-negatives).
      4. If publication still fails after the retry (or the fetch verification fails), treat Notion as FAILED and fall back to (c).

  (b) SEND a best-effort alarm email via the SOLE send path — Outlook COM:
      C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -BodyFile "<temp html>" -BodyFormat html
      TO `ggoldberg@oxfordra.net` ONLY — never cc `egoldberg@oxfordra.net`; never `ze@`. Subject e.g. `ORA Doctrine/Governor Integrity — [YYYY-MM-DD]: <e.g. governor DRIFT + doctrine 2 MISSING>`. On a non-zero exit from the send script: retry ONCE, then do NOT suppress the alarm (leave the condition unhandled so the next run re-alarms). Exit-code doctrine: exit 2 (COM failure) or 4 (timeout) → retry once then flag loudly; exit 1 (usage) or 3 (stuck Outlook wizard) → do NOT retry, flag immediately.
      GOVERNOR URGENCY: if governor-drift-probe.py alarmed (exit 1 drift OR exit 2 probe error), the email subject AND body MUST say so explicitly and up front — this is Hard-Invariant-4-adjacent (the DSCR>=1.25x / LTV<=40% governor). Never bury a financial-governor finding under generic "integrity drift" phrasing; name it as a governor issue with urgency.

  (c) NOTION-FAIL FALLBACK: if (a) failed after its retry, state clearly in the email body (b) that Notion publication FAILED (include the API error and the parent-id verification result), so the alarm still reaches Gabriel by email even with no Notion page.

STEP 4 — CLEAN RUN (both probes exit 0 AND the repo-first sweep printed no `!! REPO-FIRST` finding AND the session-context backup exited 0): send NOTHING — no email, no Notion post (a clean run is silent, matching `ora-task-integrity-guard`). Still write the status file per STEP 2 (`source="scheduled"`, doctrine_rc=0, governor_rc=0). Then print ONE line to the run log, e.g.:
  `GUARD OK — doctrine clean (N warnings), governor clean, repo-first clean (N skills swept), backup <snapshot NAME | unchanged> (scrub VERDICT), telemetry: <eos-rollup one-line summary>`
Report the backup's real result verbatim — `unchanged` is the expected result most days and must be printed as such, never smoothed into "backed up". If the mirror warned, append `| mirror FAILED (local-only)`; if the scrub verdict was UNVERIFIED, print it as `UNVERIFIED`, never as clean.
If STEP 2's status write failed for a benign reason, append `| status-write skipped: <reason>` to that same line — it does not turn a clean run into an alarm.

STEP 5 — On an ENGINE ERROR you cannot classify (e.g. the interpreter path is wrong, a probe crashes before producing an exit code you can read): write a short failure note to `C:\Users\Owner\.claude\maintenance\_state\doctrine-guard-failure-[YYYY-MM-DD].md` describing what failed, and continue running the other engines — never let one engine's failure abort the others. A probe that itself exits non-zero is NOT an engine error; that is the STEP 3 alarm path.

---

HARD GUARDRAILS:
- READ-ONLY on doctrine: this guard DETECTS drift; it NEVER edits CLAUDE.md, memory, skills, the governor constants, financial models, hooks, settings, or the probes themselves. Anything requiring a fix is reported, never auto-applied.
- Never touch oxfordra.net or any website repo/deploy.
- Never modify financial models or the governor constants (DSCR 1.25x / LTV 40%) — a governor-drift finding is escalated with urgency, not silently corrected.
- Send path is Outlook COM (`_shared/send-via-outlook.ps1`) ONLY — no fallback connector exists. Never reference Rube/Composio/Zapier as a live send path (all retired).
- Routing: `ggoldberg@oxfordra.net` ONLY — never cc `egoldberg@oxfordra.net`, never `ze@`.
- Confidential-term discipline: never echo or reconstruct a deal name/term when summarizing check 8 — index reference only.
- A clean run is silent (no email, no Notion). Only drift/probe-error alarms.
- Never fabricate a probe result — if an engine cannot run, say so (STEP 5), do not invent a verdict.