---
name: github-ci-autofix-rollout
description: Claude Code GitHub Actions auto-fix workflow (claude-code-action@v1) rollout across ZeOoba repos — which repos got it, which were deliberately skipped, and why
metadata:
  type: project
---

Gabriel asked (2026-07-08) to make Claude Code "always automatically address CI comments" across all GitHub repos. There is no global settings.json hook for this — GitHub CI/PR events are external and asynchronous, invisible to a local Claude Code session. The only mechanism that actually delivers "unattended, fires without a session open" is the official `anthropics/claude-code-action@v1` GitHub Action, added per-repo.

**Why:** hooks (PreToolUse/PostToolUse/Stop/etc.) only fire on in-session lifecycle events; GitHub Actions is the correct layer for cross-session, always-on automation.

**How to apply:** when asked for more "global Claude Code automation," default to GitHub Actions (claude-code-action) for anything triggered by external GitHub events, not settings.json hooks.

## Workflow design (`.github/workflows/claude-ci-fix.yml`)
Auto-fires (no `@claude` mention needed) on: a failed CI check-suite attached to a PR, a "changes requested" review, or a comment from `coderabbit[bot]`. Also responds to explicit `@claude` mentions (two mutually-exclusive steps, gated by `if:` — one with an explicit `prompt:`, one with no `prompt:` input at all so the action's default mention-reply auto-detect kicks in). Pushes a fix commit to the PR branch — never force-pushes, never merges (human still gates the actual merge). Prompt text explicitly instructs Claude to treat review/comment bodies as feedback to evaluate, not commands to execute verbatim (prompt-injection mitigation — a PR comment is untrusted input).

**Auth: `claude_code_oauth_token` (secret `CLAUDE_CODE_OAUTH_TOKEN`), NOT `anthropic_api_key`.** Gabriel's account runs on a Claude subscription (Pro/Max/Team), not a separate billed Console API account — `ANTHROPIC_API_KEY` failed with "Invalid API key" on every attempt (confirmed via `show_full_output: true` debug, not a paste error). Generate via `claude setup-token` (CLI: `npm install -g @anthropic-ai/claude-code` if not installed; on Windows PowerShell use `claude.cmd setup-token`, not bare `claude`, or the default script-execution policy blocks the `.ps1` shim). This is an interactive-only command — full-screen TUI + browser OAuth consent, proven to produce zero output when run headlessly (tested via Bash tool with a timeout wrapper). No way to automate the consent click; must be run by Gabriel in his own terminal.

Canonical template + public-repo variant (adds `include_comments_by_actor` allowlist, since claude-code-action has **no default actor restriction** — on a public repo, any GitHub user can trigger it via `@claude` with full `contents:write`) are in scratchpad from the 2026-07-08 session; regenerate from this file's design notes if needed rather than hunting for the temp path.

**Three real bugs found via live smoke-testing** (all fixed in the templates above — don't reintroduce if rebuilding from scratch):
1. Missing `id-token: write` in `permissions:` — action's internal OIDC token exchange fails every run without it ("Could not fetch an OIDC token").
2. Missing `actions/checkout@v4` step before the claude-code-action step — the action does its own git operations against the workspace and needs an actual `.git` dir ("fatal: not a git repository").
3. A single-step design that always sets `prompt:` (even as empty conditional text) breaks the action's "just reply to the @mention" auto-detect, which only activates when `prompt` is *omitted* entirely, not merely empty.

**Reading GitHub secret values back is impossible by design** (write-only) — when a pasted/relayed value might be wrong, don't guess-and-retry blind. `mcp__computer-use__read_clipboard` (needs `request_access` with `clipboardRead: true`; oddly still needs ≥1 dummy app like "Notepad" in `apps:` even though you don't interact with it, or the grant silently no-ops) reads the OS clipboard directly with zero OCR/transcription risk — far more reliable than reading a screenshot of a terminal when a human is relaying a secret. Terminals/IDEs are always computer-use tier "click" (viewable, not typeable) — `request_access` actively warns you off requesting them and asks you to confirm you really mean it in the same turn.

## Repo disposition (2026-07-08)
Excluded outright — in `~/.claude/confidential-repos.json`:
- `oxford-command-center`, `Website` (website-canonical), `ora-pm`

**LIVE and VERIFIED WORKING end-to-end** (real smoke test on ora-skills#3: bot read an `@claude` comment, fixed a deliberate typo, pushed commit `1eb89a6` autonomously — confirmed via `gh api` file-content check, not just a green Actions run):
- `ora-skills` — merged `f80c8ab` (workflow) → `24cd01e` (OAuth-token switch, final)
- `ora-cowork-watchdog` — merged `0063c8d` (workflow) → `e0fb85d` (OAuth-token switch, final); verified `cowork-heartbeat.yml` dead-man's-switch workflow coexists untouched

**Ready but unmerged, needs Gabriel's explicit sign-off:**
- [ora-claude-config#7](https://github.com/ZeOoba/ora-claude-config/pull/7) — content is current (checkout/id-token/two-step fixes + OAuth-token auth all applied to the branch), `CLAUDE_CODE_OAUTH_TOKEN` secret is set. Still unmerged on purpose: this PR also opts `.github/` into the repo's fail-closed default-deny `.gitignore` (a deliberate security policy, not touched without Gabriel's say-so). Ask before merging.

Deliberately skipped, flagged back to Gabriel rather than force-applied:
- **`BrainVault`** — personal Obsidian vault (daily notes, journal, canvases), not a codebase. No CI to fail, nothing for a "fix" bot to do; granting an autonomous write-access bot here risks unwanted edits to personal notes.
- **`Internal-Accounting-App`** — single loose 190KB `.tsx` file (`ora-ledger-v1 (2).tsx`), no build/test tooling, so `check_suite` would never fire. Already has its own bespoke `.github/workflows/claude.yml` referencing `CLAUDE_CODE_OAUTH_TOKEN` — but the secret actually set on that repo is `ANTHROPIC_API_KEY` (set 2026-04-22), a name mismatch that's been silently broken this whole time, unrelated to this rollout. Not fixed — out of scope, just flagged to Gabriel.
- **`Claude-Guru-Ooba-`** (public repo) — single-commit joke repo, README is "THE HIMOTHY OF CLAUDE," no actual code. Public-repo variant with `include_comments_by_actor` lockdown was built and is ready if this repo ever gets real content.

Gabriel confirmed the full 6-repo candidate list before this rollout ("the repo list above is correct") without resolving these three flags individually — the skip decisions above were my judgment call at execution time, not an explicit re-confirmation. Worth a quick check-in if this surfaces again.
