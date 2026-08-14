# Handoff 2026-08-12 — OI-128 filing + hook-tests-gate timeout evidence

**Author:** session `f4c30f1b-408b-4c0c-aff4-8e031671bca3` (ora-task-integrity-guard scheduled run, resumed interactively by Gabriel).
**Why this file exists:** Gabriel asked for two OI items to be filed. One was already claimed by another session; the other could not be written because `open-items-tracker` was under a live claim by session `e0f8485e` (host `local_381972fe`, "File the pre-push hook-tests-gate 180s timeout budget as an OI item"). `claim_work.py claim` refused (exact path overlap) and I did **not** `--force` — the holder was actively working the same file. I also could not `send_message` them: this session is unattended, and that tool is unavailable in unattended sessions. Parking the content here so it survives.

---

## 1. OI-128 — READY TO FILE, id already allocated

Allocated via `allocate-oi-id.py --session f4c30f1b` (do **not** hand-compute or re-allocate — use OI-128, or `--backfill OI-128` if filed by hand).

> **OI-128 — `model-canary-probe.py`: add a guarded `--apply` mode for model-tag retags.**
>
> Every model-tag sweep since 2026-07-13 (07-13, 07-15, 07-22, 07-24, 08-09, 08-12) has hand-applied a retag that is entirely mechanical — the probe already computes task → observed id and applies the scope filter. The 2026-08-12 sweep retagged 17 in-scope CC/MCP tasks `UNVERIFIABLE` → observed id by hand. Leaving it manual has guaranteed recurrence six times running.
>
> Apply mode must:
> - **(a)** write by **direct SKILL.md frontmatter edit**, never `update_scheduled_task` — that tool drops every top-level frontmatter key it does not own, and would have destroyed `output_contract` on **6 of the 17** (OI-109). Verified 2026-08-12: the CC/MCP registry JSON holds zero `description` fields, so the frontmatter edit is the effective path and shows up in the next `list_scheduled_tasks`.
> - **(b)** never write a task bucketed `NO_OBSERVATION` — an inferred null is a failure, not a clean result.
> - **(c)** always emit the dated form `[MODEL: <id> observed | checked YYYY-MM-DD via <method>]`, and never the `[1m]`-suffixed id, whose nested bracket severs the date half on re-read.
> - **(d)** re-verify off `list_scheduled_tasks` after writing and print the confirmed tag — a task whose final act is a write has no witness that it landed (the 2026-08-03 lost-write class).

## 2. Evidence for the hook-tests-gate item (session `e0f8485e` owns the filing)

Three consecutive **blocked** pushes to `ora-claude-config` on 2026-08-12 (~16:00–16:40 ET), from worktree `.claude/worktrees/model-tag-retag`, branch `task/model-tags-observed-main`:

| Attempt | Result | Failing tests |
|---|---|---|
| 1 | 2 FAIL | `test-eos-review-gate.py`, `test-git-prepush-scan.py` |
| 2 | 1 FAIL (76/77 pass) | `test-eos-review-gate.py` |
| 3 | 2 FAIL (75/77 pass) | `test-eos-review-gate.py`, `test-memory-orphan-link-guard.py` |

Every failure was `exit 124, TIMEOUT after 180s`, **after** the doubled-budget retry — never an assertion failure.

- **The victim test rotates between runs**, and a different set passes only on the doubled-budget rerun each time (`test-claim-work-lib`, `test-confidentiality-guard`, `test-config-write-guard`, `test-git-prepush-doctrine-gate-worktree`, `test-commit-hygiene-guard`, `test-git-prepush-scan` have each appeared).
- Machine state: **63 node/claude processes, CPU pegged at 100%**.
- Signature is **CPU starvation against a fixed per-test budget**, not flaky tests. This matters for the fix: raising the budget alone just moves the threshold; a serial fallback or load-gated budget addresses the cause.
- **Diagnostic trap:** git's failure was masked on the first two attempts because the command piped into `tail`, so the shell reported exit 0 while the push had failed (`feedback_piped_gate_exit_masking`). Only an unpiped run gave `REAL_EXIT=1`. Anyone reading this from a piped transcript will wrongly conclude the push succeeded.

## 3. Related loose end from the same session

`ora-appsec-sweep` is now **CONTRADICTED** by `model-canary-probe`: tag asserts `claude-opus-5` (checked 2026-08-03), newest sample reads `claude-fable-5` — first fable sighting in a canary on this fleet. **Not retagged**: its session was still running when observed, so the transcript was not final. Re-observe at its next completed fire. Not filed as an OI item; recorded in `reference_scheduled_task_model_standard.md`.
