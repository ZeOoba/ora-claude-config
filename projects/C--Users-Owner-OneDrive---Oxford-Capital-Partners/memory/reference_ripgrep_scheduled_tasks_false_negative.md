---
name: reference-ripgrep-scheduled-tasks-false-negative
description: "rg/Grep silently returned ZERO matches for the whole scheduled-tasks SKILL.md corpus when the search ROOT was scheduled-tasks/ itself — anchored-negation quirk, not a config bug. Fixed 2026-07-16 with scheduled-tasks/.ignore. Search from ~/.claude, never trust a bare negative."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

**Symptom (2026-07-16):** `rg -l "Tenant" ~/.claude/scheduled-tasks` → **zero matches**, no error —
while the files demonstrably contained the string. Nearly produced a false "no sync writer exists"
root cause during the Notion Tenant DB investigation.

**Precise shape (measured, not inferred):**

| Search ROOT | Result |
|---|---|
| `~/.claude` | **finds** the files ✓ |
| `~/.claude/scheduled-tasks` (via any route: relative, absolute, or `cd` inside) | **zero matches** ✗ |
| `git check-ignore` on the same file | exit 1 = **NOT ignored** — git tracks it correctly ✓ |

**Root cause — a ripgrep quirk, NOT a broken .gitignore.** `~/.claude/.gitignore` §2b correctly
opts these in via *anchored* negations (`!/scheduled-tasks/`, `!/scheduled-tasks/*/`,
`!/scheduled-tasks/*/SKILL.md`) against the fail-closed `/*` default-deny. git applies them
correctly — 24 SKILL.mds are tracked. ripgrep does **not** when the search *root* is
`scheduled-tasks/` itself: the anchored negation no longer matches the relative path it computes,
so the broad exclusion wins and files vanish silently.

**Fix applied:** `~/.claude/scheduled-tasks/.ignore` (rg-only — git never reads `.ignore`) with
`!*/` + `!*/SKILL.md`. Verified: all 3 previously-blind roots now resolve; `git ls-files` count
unchanged at 446 (zero git impact); the `.ignore` is itself ignored by `.gitignore:55` so it can't
be committed; runtime state (`_state/`, `.bak`, `.log`) stays hidden from rg. The fail-closed
`.gitignore` was NOT touched.

**Caveat:** the `.ignore` is untracked, so it does NOT propagate to another machine or the
`ora-claude-config` backup. If the fleet corpus goes silently unsearchable on a new machine,
recreate it. Deliberate tradeoff — opting it in means touching a security boundary
(see [[rules]] §10) to fix a search-ergonomics quirk.

**Why this matters / how to apply:** DO NOT "fix" this by adding `!/scheduled-tasks/` to
`.gitignore` — it is already there (line 54), and loosening that fail-closed default-deny is how
a secret or a confidential deal term gets auto-staged. More generally: a bare `rg`/Grep negative
over any `~/.claude` subtree is **not** evidence of absence. Cross-check with `--no-ignore`, plain
`grep -r`, or `git ls-files` before concluding something does not exist. Generalizes
[[feedback_verify_negative_glob_results]] — that one was about Glob; this is the same failure mode
in content search, with a concrete mechanism. Related: [[project_tenant_db_no_sync_rootcause]].
