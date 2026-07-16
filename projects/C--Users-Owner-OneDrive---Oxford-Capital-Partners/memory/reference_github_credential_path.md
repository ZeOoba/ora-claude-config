---
name: reference-github-credential-path
description: GitHub push/auth path on this machine — gh.exe outage, GCM fallback one-liner, token retrieval for API calls
metadata:
  type: reference
---

**GitHub credential architecture (this machine):** global `~/.gitconfig` scopes `credential.https://github.com.helper` to GitHub CLI (`'C:\Program Files\GitHub CLI\gh.exe' auth git-credential`), with an empty `helper =` line first that RESETS the helper list — so the system-level `manager` (Git Credential Manager) is bypassed for github.com. If gh.exe is missing or unauthenticated, plain `git push/fetch` to github.com fails with "could not read Username".

**Working fallback (no config edit needed):** Windows Credential Manager holds a valid ZeOoba github.com credential. One-off override:
`git -c credential.https://github.com.helper= -c credential.https://github.com.helper=manager <push|fetch|ls-remote> ...`

**Token retrieval for GitHub REST API calls** (used to open/merge PRs when gh absent):
`printf "protocol=https\nhost=github.com\n\n" | git -c credential.https://github.com.helper= -c credential.https://github.com.helper=manager credential fill` → `password=` line is the token.

**History:** gh.exe found missing 2026-07-07 (no trace anywhere on disk, gh auth store also gone); reinstalled via `winget install GitHub.cli` same night, auth restored, end-to-end verified (plain `git ls-remote`, `git credential fill`, `gh api user`, `gh pr view` all pass).

**Auth re-seed recipe (what actually works):** `gh auth login --with-token` REJECTS the GCM token (missing `read:org` scope — token has `repo`,`gist`,`workflow`; enough for all real work on this personal account). Instead write `%APPDATA%\GitHub CLI\hosts.yml` directly:
```yaml
github.com:
    users:
        ZeOoba:
            oauth_token: <token>
    git_protocol: https
    oauth_token: <token>
    user: ZeOoba
```
`gh auth status` then shows logged-in with a cosmetic read:org warning — ignore it.

**Defense in depth (added 2026-07-07):** `~/.gitconfig` github.com + gist sections now chain `helper = manager` AFTER the gh helper, so plain git works even if gh is missing/unauthenticated again. Pre-edit backup: `~/.claude/archive/gitconfig-backup-2026-07-07.txt`. Related: [[oxford-cc-repo-health]].
