---
name: ora-ground-truth-auditor
description: Nightly re-derivation audit of the previous 24h of scheduled-task runs across both fleets. Dispatches one verifier agent per side-effecting run (side-effect-free runs get a cheap deterministic stamp, no agent) to re-derive every factual claim from PRIMARY SOURCES ONLY -- never a prior summary, log line, or finding. Reports on four axes: IDEMPOTENCY, CLAIM ACCURACY, STALENESS, FRESHNESS OF INPUTS. Emails one morning digest to ggoldberg@oxfordra.net; any retraction or published-page edit is drafted and named in the digest, never sent or applied. Full design: docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md. [MODEL: claude-opus-5 | set 2026-09-10]
---

# ORA Ground-Truth Auditor

Full design rationale, verified ground-truth facts about the substrate, and every risk
this run must respect: `docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md`.
Read it if anything below is ambiguous -- do not improvise around a gap, the spec's own
Sec 9 exists to close exactly that kind of gap.

## STEP 0 -- self-exclusion sanity check

Before anything else, confirm your OWN task id is `ora-ground-truth-auditor`. Stage 0
excludes this id from its own index automatically -- if you ever see this task's own
run listed as something to audit, STOP. That means self-exclusion broke, and auditing
your own run trivially "passes" every axis, which is worse than not auditing at all.

## STEP 1 -- build the run index (Stage 0, deterministic, no judgment)

```
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-run-index.py" --out "C:/Users/Owner/.claude/maintenance/_state/ground-truth/run-index-<today's date, YYYY-MM-DD>.json"
```

This script decides its own window (default 24h, auto-widened for a catch-up burst or a
gap in the auditor's own last run). Read the `window_reason` field in the JSON document
it wrote to `--out` (not printed to stdout in this invocation). It joins every run to
its transcript, flags duplicates, and asserts the join-rate floor.

**Exit code decides what happens next -- the two non-zero codes mean different things,
never treat them the same:**

- **Exit 1 (JOIN-RATE FLOOR BREACHED on stderr):** the run-index file WAS written. Do
  not silently continue past this without noting it, but proceed through every step
  below -- this means the join mechanism itself may be degraded, not that the run is
  unusable. Include the exact stderr line in the digest's own status section regardless
  of what else the run finds (a broken floor is a finding, not a reason to abort).
- **Exit 2 (`GROUND-TRUTH AUDITOR COULD NOT START:` on stderr):** neither registry could
  be read at all -- no run-index file exists. **STOP here.** STEP 2 onward has nothing to
  read. Skip directly to STEP 8 and send a digest whose ONLY content is this failure: the
  exact stderr line, and nothing else (no runs audited, no axes, no duplicate section --
  there is no data to report on). Do not attempt to synthesize a normal-shaped digest
  around a missing run-index.

## STEP 2 -- extract side effects (Stage 1, deterministic, no judgment)

```
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-side-effects.py" --run-index "<the file STEP 1 wrote>"
```

Read its stdout line (`N runs: M to verifier, K stamped clean`) -- this is the
`side_effect_stats` figure the digest's Runs Audited section reports verbatim, and the
gated/ungated trend that Sec 9 R3 exists to make visible.

## STEP 3 -- dispatch one verifier per side-effecting run

For every run in the annotated index where `needs_verifier` is `true` (i.e. every run
in the index MINUS the `stamped_clean` count from STEP 2), dispatch one subagent.

**Model floor for each dispatch** -- resolve with:

```python
import sys
sys.path.insert(0, r"C:\Users\Owner\.claude\maintenance")
import importlib.util
spec = importlib.util.spec_from_file_location("gmr", r"C:\Users\Owner\.claude\maintenance\ground-truth-model-resolve.py")
gmr = importlib.util.module_from_spec(spec); spec.loader.exec_module(gmr)
verifier_model, reasoning = gmr.resolve_verifier_model(task_record, skill_md_text, session_record)
agent_tool_model = gmr.to_agent_tool_model_name(verifier_model)
```

`resolve_verifier_model` returns a full model id (e.g. `"claude-opus-5"`) -- the Agent
tool's `model` parameter does NOT accept full ids, only the short names
`sonnet | opus | haiku | fable`. Always call `to_agent_tool_model_name` on the resolved
id and dispatch the Agent tool with `agent_tool_model` (the short name), never with
`verifier_model` (the full id) directly. `to_agent_tool_model_name` raises `ValueError`
loudly if `verifier_model` is somehow outside the known four -- do not catch and
default it silently; a raised error here means the model ladder itself is broken and
the dispatch must stop, not proceed with a guessed model name.

For each run needing a verifier, build the ladder's inputs directly from the run-index
record -- no separate registry or session-record fetch is needed:

- `task_record` = `{"model": run.get("model")}` (the run's own `model` field, if the
  registry carried one -- rung 1 of the ladder)
- `skill_md_text` = the contents of the file at `run["file_path"]`, read directly
  (rung 2 -- the `[MODEL: ...]` tag in that file's frontmatter)
- `session_record` = `{"model": run.get("session_model")}` (rung 3, from the joined
  session record Stage 0 already resolved)

If `run["file_path"]` is absent or unreadable, pass `skill_md_text=None` and let the
ladder fall through to rung 3 (never fail the dispatch over a missing SKILL.md read).

**Runs touching financial data, governor
constants (DSCR/LTV), or a confidential deal never verify below Fable regardless of what
the ladder returns** -- round up explicitly for those, per CLAUDE.md's Dispatch
invariants (round up before converting with `to_agent_tool_model_name`, so the
short name passed to the Agent tool reflects the rounded-up floor). Pin the resolved
model explicitly on every dispatch; never omit it.

### Unjoined runs need a different locator strategy

An unjoined run (`joined: false` in its run-index record) has no transcript to extract
locators from -- `side_effects` is necessarily empty. This is NOT the same as "nothing
to investigate": the task itself may still have sent an email, written a Notion page, or
pushed a commit; Stage 0/1 simply couldn't confirm which. For an unjoined run, build the
verifier's locators from EXTERNAL enumeration instead of the (empty) transcript:

- Search Outlook Sent Items for messages sent around the run's `last_run_at` timestamp
  (a window of the task's own cron period is a reasonable start) whose subject plausibly
  matches the task -- most ORA scheduled tasks have a predictable subject prefix
  (`[ORA] <topic>`).
- If the run's `file_path` names a SKILL.md whose description mentions Notion, search the
  relevant Notion database (per CLAUDE.md's Notion canon) for a page edited/created near
  `last_run_at`.
- If the task is known (from its own SKILL.md) to push commits, check `git log` on the
  relevant repo for a commit near `last_run_at`.

Give the verifier these SEARCH INSTRUCTIONS as its locator input (not a pre-resolved
locator list, since none exists) -- its first job is to find what, if anything, this run
actually did, before it can verify any claim. If the search finds nothing after a genuine
attempt, the correct verdict is UNVERIFIABLE for every axis, not SUPPORTED and not silence.
Report explicitly what was searched and found nothing, so this is distinguishable from a
verifier that didn't try.

**The verifier's prompt is assembled from ONLY the following** -- this is the input-starvation
mechanism (spec Sec 6.1), the primary defence for the absolute rule. Do NOT include the
run's own summary, the body of what it emailed, or any prior finding about it:

- the run's `run_id`, `task_id`, `fleet`, `last_scheduled_for`
- primary-source LOCATORS ONLY. For a joined run, derive these from the run's
  side_effects and transcript -- a Notion page id, an Outlook message subject+date to
  search Sent Items for, a commit sha, a file path, a parcel/lease identifier. Extract
  these by grep'ing the transcript for the same patterns STEP 2's script matched (Notion
  page ids appear near `notion-create-pages`/`notion-update-page` calls; commit shas
  follow `git push` output; file paths follow `Write`/`Edit` tool_use blocks). For an
  UNJOINED run (`joined: false`), use the external-enumeration SEARCH INSTRUCTIONS above
  instead -- there is no transcript to grep.
- the four axes below, verbatim
- the absolute rule, verbatim: "Never treat a prior summary, log line, or finding as
  evidence. Re-derive every claim from the primary source you just read yourself."

**Verifier task prompt template** (fill the bracketed fields, dispatch via the Agent tool,
`subagent_type: general-purpose`, the resolved `agent_tool_model` (the SHORT name from
`to_agent_tool_model_name`, never the full `verifier_model` id), in parallel across all
side-effecting runs in one message so they run concurrently):

> You are READ-ONLY for this task. You may search, read, and query any source (Notion,
> Outlook, git, the filesystem) but you must NEVER write, send, edit, delete, or commit
> anything, anywhere, for any reason. If you believe a correction is needed, describe it
> in your report -- do not attempt to make it.
>
> You are an independent verifier auditing one prior scheduled-task run. You have NO
> access to and must NOT trust any summary, email body, log line, or finding this run
> produced. Every claim you report must be re-derived by YOU, right now, from the actual
> primary source: read the raw file, the actual current Notion page contents, the git
> history, the lease document -- not a description of it.
>
> Run under audit: `[run_id]`, task `[task_id]`, fleet `[fleet]`, scheduled for
> `[last_scheduled_for]`.
>
> Primary-source locators for this run (go read these yourself; do not ask for more
> context about the run itself):
> `[locator list -- for an unjoined run (joined: false), this is the external-enumeration
> SEARCH INSTRUCTIONS block above, not a pre-resolved list; your first job is to find
> what, if anything, this run did, and UNVERIFIABLE-on-every-axis after a genuine search
> is a valid, expected outcome -- not evidence the run was clean]`
>
> Report on all four axes:
>
> **IDEMPOTENCY** -- read the actual target(s) named above. Are there two Notion pages
> for one logical cycle? Two emails with the same subject on the relevant date in Sent
> Items? Two commits with identical content? (Cron/trigger double-fire detection was
> already done deterministically upstream -- you are checking the ACTUAL TARGET STATE
> for doubles, not re-deriving the cron analysis.)
>
> **CLAIM ACCURACY** -- enumerate every factual assertion in the published artifact,
> read AT ITS SOURCE (the live Notion page, the actual Sent Items message) -- never from
> a transcript's account of what was published. For each claim, cite the primary source
> you personally read that supports or contradicts it, and mark it SUPPORTED,
> CONTRADICTED, or UNVERIFIABLE. UNVERIFIABLE means the primary source was unreachable --
> report that plainly, never upgrade it to SUPPORTED because you couldn't check.
>
> **STALENESS** -- for each plan item, pin, or config value this run acted on, compare
> the state AT RUN TIME (use `git log` / `git show` to reconstruct it precisely) against
> the CURRENT state. Flag anything that was a no-op, or that reverted a newer state.
>
> **FRESHNESS OF INPUTS** -- for every upstream data source this run depended on, report
> its actual last-updated timestamp (read it yourself) and state whether a staleness
> alarm should have fired but did not. The ORA Master Workbook mirror is STALE past 7
> days -- if this run used it, check its age explicitly.
>
> Compile your findings as a numbered facts dossier (F-1, F-2, ...) per the
> evidence-dossier-drafting skill's VERIFY step -- every fact carries the exact command
> or read you ran to establish it. Every axis verdict above must cite at least one F-id.
> A verdict with no F-id, or citing an F-id whose source does not actually support it,
> will be dropped before publication -- so do not write one.

## STEP 4 -- F-id discipline and the refuter pass (Sec 6.2, 6.3)

After every verifier returns, drop any verdict that cites no F-id or whose cited F-id's
source text does not actually support the claim made (read the F-id's evidence yourself
-- do not take the verifier's word that its own citation is valid).

For every surviving **CONTRADICTED** verdict, dispatch a second agent (same or higher
model tier as the verifier that produced it -- resolve via `gmr.to_agent_tool_model_name(...)`
exactly as in STEP 3; never dispatch this Agent-tool call with a full model id) with this brief:

> You are READ-ONLY for this task. You may search, read, and query any source (Notion,
> Outlook, git, the filesystem) but you must NEVER write, send, edit, delete, or commit
> anything, anywhere, for any reason. If you believe a correction is needed, describe it
> in your report -- do not attempt to make it.
>
> Re-read the exact primary source at `[locator]` yourself. A prior verifier concluded
> the claim "`[claim text]`" is CONTRADICTED, citing `[F-id and its evidence]`. Argue
> the ORIGINAL claim was actually right. If you cannot construct a good-faith argument
> that the original claim holds, say so and explain why the contradiction survives.

A contradiction that survives this refuter pass goes to the digest. One that does not
survive is downgraded to UNVERIFIABLE (not silently dropped) and logged in the run's own
notes for STEP 6's systemic-cause review.

## STEP 5 -- STALENESS and FRESHNESS roll-up

Independent of the per-run verifiers, using the `recorded_skips` field already present
on every run in the index (no re-derivation needed -- Stage 0 read this from the
registry directly): for every run with a non-empty `recorded_skips` list, note the skip
reasons and dates in the digest's Runs Audited section as context, not as a separate
axis finding.

## STEP 6 -- approval gate for corrections (Hard Invariant 1, spec Sec 7)

For any CONTRADICTED claim (post-refuter) or duplicate side effect whose fix would mean
sending a retraction email or editing a published page:

1. Draft the full correction (email body or page edit) to
   `C:\Users\Owner\.claude\maintenance\_state\ground-truth-pending-approval\<today's date>\<run_id>\`.
2. Name it in the digest with a one-line summary of what it would change.
3. **Do NOT send it. Do NOT apply it.** No exception -- this is an outbound
   counterparty send or a live-page edit, both of which require Gabriel's explicit
   in-turn confirmation regardless of how confident the verifier+refuter pair was.

## STEP 7 -- systemic-cause open items

For any finding that points at a systemic cause (not a one-off) -- a cron collision that
will recur nightly, a join mechanism that is silently degrading, a skill that
structurally cannot avoid duplicating a side effect -- file an open item:

```
ID=$("C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/allocate-oi-id.py" --session $CLAUDE_CODE_SESSION_ID --note "<why>")
```

Never hand-compute the next OI-NNN. Reference the allocated id in the digest's Open
Items section.

## STEP 8 -- compose and send the morning digest

One HTML email, `ggoldberg@oxfordra.net` **only** -- no cc (the ora-am-brief Eric-cc
exception does not extend here). Sections, in this exact order:

1. **Runs audited** -- total count, fleet split, `side_effect_stats` from STEP 2
   verbatim (verifiers dispatched vs stamped clean), the join-rate floor result from
   STEP 1 (state the window actually used and why, per its `window_reason`), and any
   run skipped entirely with the reason. **Every run with `joined: false` in the run
   index must be listed BY NAME (`run_id`, `task_id`) in this section with the tag
   `UNVERIFIABLE (unjoined)`, regardless of what its verifier concluded** -- this is
   the "digest says so explicitly for that run" requirement (spec Sec 9 R1a); an
   unjoined run can never be silently folded into a clean-looking aggregate count.
2. **CONTRADICTED claims** -- highest priority. For each: the claim, the F-id evidence
   that contradicts it, and the drafted correction's location from STEP 6 (never its
   content inline if it's a page edit -- link the path).
3. **Duplicate side effects** -- from STEP 1's `duplicate_flags` plus anything a
   verifier found at the target itself (STEP 3's IDEMPOTENCY axis). Remediation steps
   for each.
4. **Open items filed** -- the OI-NNN ids from STEP 7, one line each.

Send via:

```
powershell -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] Ground-Truth Audit -- <today's date>" -BodyFile "<path to the composed HTML>" -BodyFormat html
```

Exit-code handling (canon): exit 2 (COM failure) or 4 (timeout) -- retry once, then flag
loudly if it fails again (do not halt the task over a send failure once the digest is
drafted and saved). Exit 1 (usage error) or 3 (stuck wizard) -- do not retry, flag
immediately with the exact exit code and stderr.

## STEP 9 -- completion note

Do not email a second time. Report in the task's own completion notification: runs
audited, verifiers dispatched, CONTRADICTED count (pre- and post-refuter), duplicate
flags, OI ids filed, and the join-rate floor's pass/fail state per fleet.
