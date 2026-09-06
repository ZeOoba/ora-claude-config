---
name: project-regression-root-cause-audit-2026-08-28
description: "Cross-repo audit of the fix-creates-a-new-bug cycle across 6 active repos (.claude, oxford-command-center, ora-skills, Website, AAOS, ora-pm) — 3 shared structural mechanisms identified, report-only, no code changed"
metadata: 
  node_type: memory
  type: project
  originSessionId: a721d00e-5c7e-4c76-8e86-82b0a06d6dfd
  modified: 2026-08-28T16:29:53.694Z
---

Gabriel asked (2026-08-28, via `/code-review`) for a root-cause investigation into a recurring pattern: a bug gets fixed, the fix creates a new bug, repeating. Since this spans 6 separate GitHub repos rather than one diff, the native `/code-review` skill didn't fit — 6 parallel read-only agents instead mined each repo's `git log`/`git show` history (~300 commits/repo) for fix→refix chains and diagnosed a structural cause per hotspot. Repo set chosen by Gabriel: top-4-by-recent-push (ora-claude-config, oxford-command-center, ora-skills, Website) plus AAOS and ora-pm substituted/added by his explicit answer. Scope, also by his explicit answer: **root-cause report only — no code changed, no commits made.**

Full findings (27 hotspots, commit SHAs, file:line citations, per-repo detail): [Regression Root-Cause Audit artifact](https://claude.ai/code/artifact/24cabf38-d976-4312-819e-691492696132).

**Headline finding:** all 6 repos — independently, no shared code between them — exhibit the same 3 structural mechanisms behind the whack-a-mole cycle:
1. **No single source of truth** — data/logic duplicated across writers/consumers/docs, kept in sync by hand (e.g. CC's `portfolio.json` had 3 independent writers; ora-pm's `Charge`/`Lease` types drifted 4 ways in 48 hours).
2. **Heuristics standing in for structure** — regex/allowlist/filename-prefix matching used where a real parser, schema, or opaque ID belongs (e.g. `.claude`'s `governor-drift-probe.py`, 25+ commits teaching a regex to read intent; CC's deals were joined by normalized name before switching to an opaque Deal ID).
3. **No gate reproduces the real failure** — tests pass locally, the bug only manifests under the actual production runtime/external state/full input space (Website has **zero CI** at all — no test/lint/build script exists; ora-pm's N+1 cron bug only surfaced at real Cloudflare Workers scale).

**Why:** this isn't a hygiene problem isolated to one project — it's a single authoring/patching habit (verification scoped to the specific instance found, not the invariant it violated) reproduced independently across every codebase Gabriel's sessions touch.

**How to apply:** the artifact's "Where to start" section gives a prioritized 5-item next-phase list (Website CI first — cheapest, highest severity single gap; then CC's `portfolio.json` writer consolidation; then retiring the two regex-based `.claude` guards; then giving `register-scheduled-task`/`package-and-stage-skill` a real test oracle; then routing actual implementation through `qodo-review`/`qodo-review-resolver` once a fix is picked). No code has been touched yet — before starting remediation on any of these, re-verify the cited commit SHAs and current file state, since this snapshot is dated 2026-08-28 and several of these repos (`.claude`, `ora-skills`) are under this file's own single-writer rules ([[reference_memory_dir_not_in_single_writer_list_2026-08-14]] doesn't cover this, but the standing shared-checkout rule in CLAUDE.md does).

Two flagged, not investigated further here: `oxford-command-center`'s `deploy-mirror.smoke-test.ps1` exists but is confirmed absent from every CI workflow and from `npm run gate` — a real, narrow, low-risk fix on its own. `.claude`'s financial-code refute-required gate is enumerated as an allowlist of known paths (not a denylist of exemptions) and has silently missed newly-added financial paths 3 times (`src/contracts` 07-24, `server/workbook` 08-11 — wait, that's CC not `.claude`; the `.claude` equivalent is the pre-push override token used 5× by 3 sessions on one governor-drift false positive before the regex was fixed).
