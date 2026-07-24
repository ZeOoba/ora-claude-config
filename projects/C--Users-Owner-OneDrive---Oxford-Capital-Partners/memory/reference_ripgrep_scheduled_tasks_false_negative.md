---
name: reference-ripgrep-scheduled-tasks-false-negative
description: "rg/Grep silently returned ZERO matches for the whole scheduled-tasks SKILL.md corpus when the search ROOT was scheduled-tasks/ itself — anchored-negation quirk, not a config bug. Fixed 2026-07-16 with scheduled-tasks/.ignore. Search from ~/.claude, never trust a bare negative."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
  modified: 2026-07-24T23:36:59.723Z
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

**Related false-negative, different mechanism, same class — the `ora-skills` scan-root exclusion
(2026-07-09/10).** Not a ripgrep quirk this time: the doctrine-integrity-probe's skill check only
resolves a skill if it finds a `SKILL.md` under one of three hardcoded scan roots
(`~/.claude/skills`, `~/.claude/plugins`, `OneDrive…/Claude_Workspace`) — it never scans the
authoritative source-of-record repo `C:\Users\Owner\ora-skills` at all. A skill living only there
(or only in an archived clone with no redundant `outputs/` copy) reads as `[MISSING]` even though
it's alive and still serving via the plugin runtime — which is exactly what happened to 4 skills
(`acquisition-underwriting`, `loi-generation`, `psa-reconciliation`, `tenant-email`) after the
2026-07-09 clone-archival swept their last on-disk copy. Full detail:
[[reference_skill_home_loss_2026-07-09]]. **The generalized lesson this file's "how to apply"
already states holds across both:** a tool reporting "not found" over part of `~/.claude` (or its
satellite repos) is reporting its own scan-root/exclusion boundary, not ground truth — verify
against `git ls-files`, a different tool, or the actual repo before concluding something doesn't
exist.

**A third instance, same class, found 2026-07-24:** `Glob` returned "No files found" for
`hooks/sessions/*` in the live `~/.claude` checkout despite the directory holding hundreds of
per-session provenance folders (`hooks/sessions/<uuid>/touched-files.txt` etc., read by
`shared-checkout-guard.py`) — confirmed populated via plain `ls`/`find` over Bash immediately
after. Never rooted out to a specific ignore rule (unlike the two cases above), but the blind
Glob-negative-then-fallback-to-a-raw-shell-listing pattern is now the third confirmed case of this
failure mode inside `~/.claude`. When a Glob/rg negative over a `~/.claude` subtree matters (i.e.
you're about to act on "this doesn't exist"), cross-check with `ls`/`find`/`git ls-files` first —
don't assume the negative is reliable just because this specific path isn't one of the two
already-diagnosed exclusion mechanisms above.
