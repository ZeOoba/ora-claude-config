---
name: reference-ora-skills-post-commit-syncs-live-cache
description: "ora-skills' post-commit hook raw-syncs the edited SKILL.md into the LIVE runtime cache on every commit — including from an unmerged branch in a worktree"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7266cf63-8e62-4f7d-a402-093d39839318
  modified: 2026-08-03T19:08:09.964Z
---

Committing a skill change in `C:\Users\Owner\ora-skills` fires a `post-commit` hook that immediately copies the changed files into the **live** platform runtime cache
(`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\583f08bc-…\a6ad2c61-…\skills\<skill>\`) and records the skill in `_staging\PENDING_REIMPORT.md`.

Confirmed 2026-08-03 (acquisition-underwriting v4.6 pull + v4.7 patch, [PR #28](https://github.com/ZeOoba/ora-skills/pull/28)): it fired on **both** commits, from a `git worktree` on an **unmerged** branch. Output line to watch for: `<skill>: synced N file(s) -> C:\Users\Owner\AppData\Roaming\Claude\…`.

**Why it matters:** "branch + PR, never merge unreviewed" does NOT keep the content off the live surface. The moment you commit on any branch, the next session that loads that skill reads the new text. Isolation via worktree protects the shared checkout, not the runtime cache. This is a raw sync — it closes content drift but not import-path registration, so `ora-skill-store-drift-check` step 2g will read it REIMPORT-PENDING (index-unregistered) until a confirmed Save-skill click; see [[reference_skill_reimport_sync_lag]].

**How to apply:** treat a skill commit as going live. Do the verification pass BEFORE committing, not between commit and merge. If a change must stay off the live surface pending review, don't commit it — stage it as a patch file. Related: [[reference_skill_surfaces]], [[reference_skill_home_loss_2026-07-09]].
