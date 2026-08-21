---
name: reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity
description: "ora-cc-snapshot-refresh Step 5(b) used to email on data-quality flag COUNT > 0; FIXED 2026-08-11 to gate on severity >= warn — one info flag is permanent, so the old rule alerted on every clean run"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1de11c79-1c29-4ad7-8e6b-20c60c5f8279
  modified: 2026-08-16T19:08:13.077Z
---

`ora-cc-snapshot-refresh`'s Step 5(b) escalates to email on **any** `Data-quality flags: N` where N > 0. There is **no severity gate**. The extract's flag list carries a `severity` field (`info` / `warn`), and Step 5(b) ignores it.

One flag is **permanent and intentional**:

> `severity: "warn"` (**was** `info` when this note was written — see the 2026-08-16 correction below) · `loans · name` — "Loan Index row 24 is tombstoned in the workbook and was skipped, so it cannot claim a snapshot id or warehouse key", `rawValue: "⚠ DUPLICATE OF ROW 22 — DO NOT USE"`

That raw value is a deliberate annotation Eric put in the workbook, correctly honored by the tombstone-row guard. It is not a defect and will not go away.

**⛔ CORRECTION 2026-08-16 — the `info` severity above was ALREADY STALE when this file was written, and it invalidates the fix recorded below.** The tombstone flag was bumped `info` → `warn` in `490d89f` (2026-08-11 18:15:14 -0400, "fix(deals): close the seed-wipe hole on portfolio.json's third writer"), deliberately: skipping the row removes its balance from aggregate debt, moving portfolio LTV in the **falsely-clearing** direction against Hard Invariant 4's 40% ceiling, and `info` is "too quiet for that" (`server/workbook/parse.ts:655-658`). The severity-gate fix `1706bc2` landed **2026-08-12 15:42:50 -0400 — ~21 hours LATER** — yet was written around the belief that the permanent flag was `info`.

**Consequence: the gate is INEFFECTIVE for its own motivating case.** `SKILL.md:53` says "Email only if at least one entry is `severity: "warn"`"; the permanent flag *is* `warn`; therefore a clean exit-0 no-drift run **still emails `[ALERT]` every Monday**. The alert fatigue this fix was created to eliminate was never actually eliminated. Verified 2026-08-16 by reading `data/snapshots/portfolio.json` → `dataQuality[]` directly (single entry, `severity: "warn"`) and `/api/health` → `flagCount: 1`.

Gabriel ruled 2026-08-16 (in-turn, multiple-choice): **leave the parse.ts flag as-is** — the `warn` is accurate, the row carries no balance (`C24:G24` are all `='Portfolio Summary — Internal'!#REF!`), and one standing amber flag is the correct price of never silently dropping a loan row. That ruling covers the PARSER only; the downstream alert gate above is a separate open question. Do NOT "fix" this by downgrading parse.ts back to `info` — that re-opens the governor-guard hole `490d89f` closed.

**Consequence:** a clean exit-0, no-drift run still fires an `[ALERT]` email every Monday. First observed 2026-08-11 (run at 22:40:40Z, a catch-up fire; Notion note `3b96ecd8-9e59-81ee-b03b-d5423f8762a7`).

**Do not read `Data-quality flags: 1` as an exception.** Open `data/snapshots/portfolio.json` → `dataQuality[]` and check `severity` before characterizing it. Compare against the prior snapshot too — on 2026-08-11 the count *fell* (2 → 1): the `warn`-severity `610 Northampton St. LLC · annualDebtService` "I16 has no cached value" flag cleared after [PR #267](https://github.com/ZeOoba/oxford-command-center/pull/267) (`b9a58c2`). A raw count going 2 → 1 while the alert still fires is exactly the failure mode here.

**FIXED 2026-08-11 (Gabriel ruled same day, in-turn: "amend the SKILL.md to gate on severity >= warn").** Step 5(b) now reads "at least one data-quality flag of severity `warn` or higher"; a raw count > 0 is explicitly NOT the trigger. Exits 1 and 3 and the `asOf`/unreachable-workbook branches unchanged. A `DATA-QUALITY FLAG SEVERITY GATE` block was added under Step 5 covering: severity must be read from the snapshot JSON (stdout prints the count and flag text but NOT severity, and the `⚠` glyph appears on info flags too), info-only ⇒ Notion note and no email, the gate applies to exits 0/2 only (on exit 1 the file was not written so `dataQuality[]` still describes the previous snapshot), and prior-snapshot comparison before characterizing any flag.

Landed as commit `1706bc2` in `~/.claude` (one file, 82 insertions). Frontmatter `description` bumped to v1.1 via `update_scheduled_task` — the OI-109 check passed clean: no frontmatter keys dropped, trailing MODEL tag preserved, prompt body untouched (only line 3 changed at content level). Side effect: the tool rewrote the file LF, so git warns `LF will be replaced by CRLF` on this path.

**`eos-review-gate` blocks pathspec commits on OTHER sessions' staged files.** Landing this needed a Gabriel-approved single-use override, for a commit carrying zero blast-radius files. The gate computes its key from the whole shared index, not from what the commit actually lands — a concurrent session had staged `scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py`, and a pathspec commit does not include staged files. `eos-review-gate.py --key --cmd '<exact invocation>'` returning `"paths": []` is the mechanical proof of scope; the hook does NOT apply that scoping itself at runtime (verified: identical key `03b8fb93055b` across two different commit messages). Do **not** clear this by recording an approved verdict — the artifact would key an approval covering the other session's in-flight code and clear the gate for THEIR commit. Same class as OI-120 (config-write-guard index-state gap). Related: [[reference_update_scheduled_task_drops_frontmatter_keys]].

**SUPERSEDED 2026-08-12 — the runtime-scoping claim in the paragraph above is wrong, and its own author retracted it later in the same session.** `scope_for_cmd()` *does* compute correct pathspec scoping, and `main()` uses it. The real defect is upstream, in tokenization: `hooks/lib/git_commit_parse.py:315` tokenizes the command **line by line** — a deliberate 2026-07 hardening that closed a real bypass — so a **multi-line** `-m` message splits the invocation across many "lines" and `find_commit_segment()` loses the trailing `-- <pathspec>`, silently falling back to whole-repo scope. Both blocked attempts recorded above used multi-line messages; the `--key --cmd` probe that returned `"paths": []` used a single-line one. That is why the same key `03b8fb93055b` appeared twice, and why the "it ignores the pathspec at runtime" inference was drawn — the observation was real, the conclusion was not.

**Consequences worth carrying forward.** The practical workaround needs no override at all: use a **single-line** `-m` for pathspec commits in `~/.claude`, amending the body afterward if needed. The failure is fail-closed — a parse miss *widens* scope, so nothing unreviewed slips through; it is friction, not a hole. Do **not** "fix" it by reverting to whole-string `shlex.split()`, which reintroduces the documented bypass; teach the line-wise tokenizer that an unterminated quote continues across lines instead. And do not clear it by recording a review verdict over another session's staged code — that remains true.

Tracked as [OI-122](open-items-tracker.md#OI-122), **filed 2026-08-12** with the corrected root cause and an independently re-run differential. The id had sat as an orphan reservation from 2026-08-11 until then, which is why this note originally named it in plain text only.

A gotcha that cost a round-trip and will recur: `memory-integrity-probe.py` matches the tracker-anchor **string**, not the intent. An earlier revision of this paragraph spelled out the anchor form in prose *to warn against using it while the row was missing*, and the probe correctly flagged that prose as a dead pointer. While a row does not exist, describe the form — never write it. Same shape as OI-099 and OI-120, where a matcher scanning command text tripped on a note merely *describing* the gap.

The allocation-ledger note under OI-122 was corrected the same day by its reserving session and now retracts both earlier theories, so the ledger, the tracker row, and this file agree. Note the row's own account narrowed twice: a heredoc-fed or single-line `-m` scopes correctly, and only a **directly-quoted** multi-line `-m` strands the pathspec — the tokenizer is not defective, and changing it was ruled out after two attempts shipped false ALLOWs.

Related: [[reference_command_center_snapshot_is_tracked_not_ignored]] · [[reference_alert_engine_duplicate_emails_diagnosis_2026-08-11]] · [[feedback_verified_null_vs_inferred_null]]
