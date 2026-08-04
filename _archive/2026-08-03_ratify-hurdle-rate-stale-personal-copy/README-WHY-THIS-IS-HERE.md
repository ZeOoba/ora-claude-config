Archived 2026-08-03 (Gabriel's call, in-turn).

This was `~/.claude/skills/ratify-hurdle-rate/SKILL.md` — a personal-scope (unprefixed)
skill duplicate, byte-identical to `ora-skills`' v1.2 state as of commit `a66612a`
(2026-07-09). It was accidentally captured two days later by a broad "catch up on
uncommitted work" commit (`6a4d097`, 2026-07-11) and never touched again, so it missed
every subsequent fix in the canonical copy — including the 2026-08-03 title correction
(`edc9fa1`, "Principal" -> "VP Acquisitions").

Risk it created: this repo's `skills/*` directory and the `ora-skills`-sourced
"anthropic-skills:*" plugin catalog both registered a skill named `ratify-hurdle-rate`,
under different prefixes, pointing at different (and drifted) content. An invocation
that resolved to the bare name would have silently run the stale v1.2 logic — including
stamping the wrong title into a live capital-ratification audit memo.

Canonical source of truth is, and remains, `C:\Users\Owner\ora-skills\ratify-hurdle-rate\`
(currently v1.3). Nothing else in `~/.claude/skills/` had this fork pattern — the other
4 personal skills (`county-parcel-screen`, `evidence-dossier-drafting`,
`external-artifact-intake`, `security-and-hardening`) have no `ora-skills` counterpart.

Rollback: `git mv _archive/2026-08-03_ratify-hurdle-rate-stale-personal-copy/SKILL.md
skills/ratify-hurdle-rate/SKILL.md` restores the prior state exactly (git history intact
via the rename). Not recommended — the copy was stale the moment it existed.
