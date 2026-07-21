---
name: reference_skill_description_version_extraction_gotcha
description: "A bare 'vX.Y' token in a skill's frontmatter description is not reliably the skill FILE version — for heavily-revised skills it can be a sub-component/schema version instead. Regex/automated version extraction must prefer the body H1 heading and changelog, falling back to the description only when no H1 version marker exists."
metadata:
  node_type: memory
  type: reference
  originSessionId: cowork-2026-07-21-skill-install-batch
  modified: 2026-07-21T20:50:18.651Z
---

# Skill description version tokens can lie — check the body H1 first

Diagnosed 2026-07-21, package-and-stage-skill Entry point B install session (15-skill batch). A
naive `re.findall(r'vX\.Y', frontmatter_description)` pull, used to log confirmed-install versions
to event_log.md, correctly extracted 13 of 15 skill versions from their frontmatter description
(the standing convention: description ends "... vX.Y (YYYY-MM-DD: changelog note)").

**acquisition-underwriting broke this.** Its frontmatter description read "...Buy Box & Scorecard
v1.1 (Rulings 1-5 + Amendments A-G ratified 2026-06-09)..." — a real `vX.Y (` pattern match, but
`v1.1` there names the **Buy Box & Scorecard schema revision**, a sub-component that has stayed at
v1.1 since early in the skill's life while the skill FILE itself has iterated to v4.3 (stated only
in the body H1: `# Acquisition Underwriting — Oxford Realty Advisors (v4.3 — Buy Box & Scorecard
v1.1)`, and confirmed via the changelog paragraphs beneath it). A regex trusting the description
alone would have logged v1.1 to event_log.md as the confirmed-installed version — wrong by three
major revisions.

**Root cause:** most skills only ever carry one version number, so the description-tail convention
and the "true" file version are the same token by coincidence, not by any enforced rule. Skills
with an internal sub-schema (buy-box scorecards, doctrine rulings, template libraries) can carry a
second, independently-versioned token that also matches `vX\.Y` — and for acquisition-underwriting
specifically, the sub-component token happens to appear FIRST/tighter to the start of the
description, right where a naive "first vX.Y(" grab would look.

**Fix applied 2026-07-21:** acquisition-underwriting's description changed `v1.1` → `schema rev
1.1` (997/1024 chars, packager-validated) — removes the false regex match entirely without
touching any ruling/governor content.

**Full-repo sweep completed 2026-07-21** (Code-surface handoff prompt from this session, run
against all 51 `SKILL.md` files). One more instance found: **deal-retirement** carried a different
variant of the same underlying risk — not a sub-component/schema version colliding with the file
version, but two genuine file-version notes stacked back-to-back in the description (`v1.1
(2026-07-16: ...)`. `v1.2 (2026-07-18: ...)`), with no body changelog section to disambiguate.
A naive first-match regex would have logged the superseded v1.1, not the true current v1.2 (visible
only via `[v1.2]` tags inline in the Standard Workflows steps). Fixed the same way — reworded the
superseded entry to `Prior rev 1.1 (...)` so it no longer matches a bare `vX.Y(` token, leaving
v1.2 as the sole marker (925/1024 chars, packager-validated, commit `d701493`). The other 20
skills whose description carried a `vX.Y(` token were checked against their changelog's latest
entry (or, absent one, confirmed there was only ever a single token to begin with) and are clean —
`register-scheduled-task` is the one case where the H1 itself also states the version (`v2.7`),
consistent with the description. No skill's ruling, scorecard weight, governor constant, or
substantive logic was touched by this sweep — description wording only.

**Rule going forward:** any tool or session extracting a skill's "version" for logging (event_log.md,
drift-check, package-and-stage-skill step 7) should look for a version marker in the body H1
heading FIRST (pattern `# .*\(v(\d+\.\d+(?:\.\d+)?)\b` — the token immediately after `v` and before
` —` or a closing paren, not any later `vX.Y` reference to another skill or sub-component inside
the same heading), and only fall back to the frontmatter description's trailing `vX.Y (` pattern
when the body has no H1 version marker at all (true for most single-purpose skills — most lack an
H1 entirely, e.g. conversation-archival, deal-comparison, portfolio-growth, tenant-intelligence all
checked `H1: None` this session). Never trust the FIRST `vX.Y` match in the description blind;
if multiple `vX.Y(` matches exist in one description, that itself is a signal to inspect the body
before logging.

Related: [[event_log]] · [[reference_skill_reimport_sync_lag]]
