---
name: project-lease-addendum-cache-orphaned-branch-2026-08-21
description: "RESOLVED — lease-addendum's ora_doc_qc.py retrofit landed in the Cowork runtime cache 2026-08-17 but its repo branch was never merged, ledgering it CACHE-AHEAD/DIVERGENT for 4 days until a 2026-08-21 fleet pass merged it"
metadata: 
  node_type: memory
  type: project
  originSessionId: d1847790-710f-4fd4-aa42-c57a6ef68ddc
  modified: 2026-08-21T22:17:59.396Z
---

✅ **RESOLVED 2026-08-21.** `lease-addendum` was ledgered in `ora-skills/_staging/STORE_AHEAD_OF_REPO.md` as DIVERGENT (`scripts/addendum_qc.py` matching a commit off this branch's ancestry; `scripts/ora_doc_qc.py` present in the cache with no repo counterpart at all) — pending since 2026-08-17T20:23Z, alongside `lease-form-qc` and `listing-agreement-qc` on the same timestamp.

**What actually happened (reconstructed from commit messages + [[project_ora_doc_qc_shared_module_pr48_2026-08-17]], since no contemporaneous writeup exists):** [ora-skills PR #48](https://github.com/ZeOoba/ora-skills/pull/48) (merged 2026-08-18, commit `5f8b65b`) retrofitted `pma-qc`, `listing-agreement-qc`, and `lease-form-qc` onto one shared `tools/ora_doc_qc.py` extraction module — closing a false-clean bug on scanned no-text-layer PDFs. `lease-addendum` was never part of PR #48's scope. Someone applied the same retrofit pattern to `lease-addendum` the same day (matching 2026-08-17T20:23Z cache timestamps), installed it into the Cowork runtime cache (create-skill / Save-skill / direct cache write), but the repo-side branch carrying that work was never merged to `main`. Net effect: one shared-module rollout, executed on two branches — one merged (PR #48), one left orphaned in the runtime cache for 4 days, invisible to `tools/hooks/post-commit`'s ledger because that hook only fires on a commit touching the skill, and none did.

**Resolution, 2026-08-21:** a same-day fleet of concurrent sessions (15 peers active in this working directory) ran `tools/repo_first_check.py`'s full sweep, which rescued the at-risk cache content to `_staging/repo-first-rescue/` before anything could clobber it, then reconciled it: commit `ab6ce5d` ("retrofit addendum_qc.py onto shared ora_doc_qc.py (merge from unmerged branch)") merged the orphaned branch's changes into `main`; commit `92fdd41` ("untrack vendored ora_doc_qc.py, matches sibling shared-dep skills") removed `lease-addendum`'s own copy of `ora_doc_qc.py` so it consumes the shared module the same way `lease-form-qc`/`listing-agreement-qc`/`pma-qc` do, instead of vendoring a duplicate. A fresh `repo_first_check.py` sweep afterward showed all 5 originally-ledgered skills (`debt-management`, `lease-addendum`, `loi-generation`, `lease-form-qc`, `listing-agreement-qc`) IN-SYNC; the ledger self-cleared and `STORE_AHEAD_OF_REPO.md` was deleted (derived file, nothing left to report).

**Unrelated but resolved in the same window:** `debt-management` (CACHE-AHEAD, SKILL.md only — the PAYOFF STATEMENTS workflow, via commit `27cb034` "v1.3 -- PAYOFF STATEMENTS workflow, repo-first reconciliation") and `loi-generation` (CACHE-AHEAD, now v1.7, past the v1.6 last recorded) were platform-side edits never committed — a different mechanism than the shared-module orphaned-branch story above, just ledgered on the same sweep and closed in the same pass. Don't conflate the two causes if this surfaces again.

**Not done:** nobody has confirmed *why* the lease-addendum retrofit branch specifically was never merged on 2026-08-17/18 alongside PR #48 — whether it was intentionally held back, forgotten, or blocked on something. If it recurs, that's the open question.
