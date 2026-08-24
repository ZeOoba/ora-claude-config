---
name: git-status-short-hides-branch-use-sb
description: git status --short omits the branch line; use -sb (or -b) before any commit in a shared checkout
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b8041321-02f8-4c99-ad04-edf8e6a8241d
  modified: 2026-08-24T16:24:50.043Z
---

Always use `git status -sb` (or `git status -b`), never bare `git status --short`, when checking repo state before a commit in any of the four shared checkouts named in CLAUDE.md's Shared-checkout = SINGLE-WRITER section: `~/.claude` itself (covering `CLAUDE.md`/`settings.json`), `ora-skills`, `oxford-command-center`. Same scriptable short format, same cost — `-sb`'s first line is `## <branch>...<upstream>`, which `--short` alone omits entirely. Plain `git status` (no flags) also shows the branch, but loses the short/scriptable format.

**Why:** 2026-08-24 — committed a widened section-shrink guard to `~/.claude/scheduled-tasks/*/SKILL.md` without checking which branch the checkout was on, because every pre-commit check that session used `git status --short` (sometimes further scoped with a pathspec). The checkout was on `feat/model-canary-probe-step25` — a live multi-session shared staging branch — not `main`. The commit itself was harmless (additive, no destructive intent, content-safe either way), and this repo's `SKILL.md` content is live off disk regardless of branch, so nothing broke — but the branch identity was invisible to me until a `git push` landed on the wrong-sounding branch name and forced a re-check.

**Not a new problem — an existing rule that needed generalizing, now done.** [[rules.md §14]] already mandated `git fetch origin` + `git status -sb` before any `ora-skills` commit batch, ratified 2026-07-16 after three real same-day collisions there. This incident was the identical hazard class (shared checkout, concurrent writers, branch/HEAD assumptions going stale) surfacing in `~/.claude` itself. **Gabriel ratified generalizing it in-turn, 2026-08-24** — §14 now covers all four items from CLAUDE.md's Shared-checkout = SINGLE-WRITER list (`CLAUDE.md`, `settings.json` — both within the `~/.claude` checkout — `ora-skills`, `oxford-command-center`; three distinct git checkouts) under one Tier-1 habit, with the `~/.claude` incident recorded as its own dated "Why" alongside the original `ora-skills` narrative, not replacing it.

**How to apply:** before any commit, in any of the three shared checkouts backing those four items, run `git fetch origin` + `git status -sb` (not `--short` alone) as the FIRST step of the pre-commit check — read the branch off that line before doing anything else — then inspect the staged index (`git diff --cached --stat`) before committing. Full current text: `rules.md` §14.
