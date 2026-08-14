---
name: reference_ora_skills_claim_protocol_pointer_stale
description: "The session-start hook's 'Full claim protocol: tech.md §2' pointer for the ora-skills single-writer rule is stale -- §2 is skills-library locations, not a claim mechanism. No claim/lock system exists for ora-skills; only the git-log-diff check does."
metadata: 
  node_type: memory
  type: reference
  originSessionId: db37f7b8-944c-4f81-bd75-c94d1aa35a19
  modified: 2026-08-14T22:09:41.919Z
---

Found 2026-08-14 while building the `lease-addendum` skill: the SessionStart hook context states
"ora-skills single-writer rule ... Full claim protocol: tech.md §2" but `tech.md`'s actual
`## 2. Skills libraries` section documents the three skills-library filesystem locations
(nominal user path, AppData runtime cache, Cowork Desktop) — it contains no claim, lock, or
registration mechanism of any kind. Searched all of `tech.md` for any ora-skills claim system;
none exists. Unlike `~/.claude` (which has `hooks/lib/claim_work.py` with named slugs —
`hooks-override-auth`, `open-items-tracker`, `oxford-command-center-data`, `repo-housekeeping`
per [[reference_concurrent_session_duplicate_hardening_work]]), `ora-skills` has ONLY the
git-log-diff check the same hook line states inline: run `git log --oneline -1` + `git status`
before editing any SKILL.md; if HEAD is newer than session-start or uncommitted changes aren't
yours, stop and surface the conflict.

**This check worked correctly in practice.** During the `lease-addendum` build, another
concurrent session merged unrelated eval-harness work into `ora-skills` main mid-task (three
separate HEAD advances observed across the session: `d4a03e3` → `c9d642e` → `899b10b`). The
git-log-diff check caught nothing anomalous each time because there genuinely was no conflict —
verified via `git merge-base --is-ancestor` that every `lease-addendum` commit stayed an ancestor
of the advancing HEAD, and `ahead/behind` against `origin/main` was 0/0 throughout (commits were
landing pushed, not staying local-only). So the lightweight check sufficed here — but it depends
entirely on the session doing the diligence every time, with no structural backstop if a session
skips it.

**Open question for the next `ora-setup-audit` pass, not fixed ad hoc here:** either (a) correct
the stale `tech.md §2` pointer to describe the actual (git-log-diff-only) protocol, or (b) decide
whether `ora-skills` — now visibly under heavy concurrent multi-session traffic, evidenced by 3
HEAD advances and 7 concurrent `git.exe` processes observed in one afternoon — warrants a real
claim mechanism analogous to `claim_work.py`. This wasn't decided here because designing a claim
system is a real doctrine decision, not a pointer fix, and is out of scope for a skill-build
session.

**Also fixed same session, unrelated:** a stale `refs/stash.lock` (0 bytes, dated 2026-08-01,
predating every running git.exe process by 13 days — confirmed via `Get-Process git | StartTime`
before removal) was blocking `git stash` operations in the repo. Removed; `git stash list` and
`git status` both clean afterward.
