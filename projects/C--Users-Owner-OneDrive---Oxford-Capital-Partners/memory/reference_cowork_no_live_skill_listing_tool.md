---
name: reference_cowork_no_live_skill_listing_tool
description: "Cowork sessions have no tool equivalent to a live account 'ListSkills' call — package-and-stage-skill's bridge-first freshness screen part (a) can't run from Cowork; always fall through to the full post-install CreationTime/hash verify."
metadata:
  node_type: memory
  type: reference
  modified: 2026-08-24T15:30:00.000Z
---

package-and-stage-skill's "bridge-first freshness screen" (v1.18(a)) is defined as two
independent signals: (a) a live `ListSkills` account call showing the target skill's
description/version already current and enabled, and (b) a Desktop-Commander SHA256
compare of the AppData cache against the repo. Only BOTH matching is supposed to let a
session skip presenting an already-installed package.

**Finding (2026-08-24, Entry Point B 8-skill install session):** no tool reachable from
a Cowork session provides (a). `mcp__skills__list_skills` exists but is a **user-facing
render tool** ("Render the user's installed slash-menu skills as an interactive widget"),
truncates to 5 with an expander, and is documented for showing the user their own skills —
not a data source for a session to programmatically verify a specific skill's installed
version. Using it that way would also misuse a UI-rendering tool as a silent data call.

**Consequence:** from Cowork, the freshness screen degrades to hash-compare only, which
package-and-stage-skill's own doctrine (v1.13 incident) already distrusts as
"hash-match-by-construction" — `sync_appdata_mirror.py`'s pre-commit hook copies repo
content into every existing cache mirror on every commit, so a hash match proves the
mirror-sync hook ran, not that anyone clicked Save-skill. Confirmed live this session:
3 of 8 skills (settlement-basis-extraction, disposition-analysis, owner-outreach)
hash-matched their cache pre-click with stale CreationTimes (08-21, 08-03, 08-24-earlier)
— exactly the pattern the doctrine warns about — so all 8 were presented rather than
silently skipped.

**Working substitute, same session:** capture each target skill's cache-directory
CreationTime as a baseline BEFORE presenting, then after Gabriel confirms the click,
re-check whether CreationTime moved (real re-import tears down and recreates the
directory) and hash the resulting cache files against the packaged `.skill` (not just
the repo). This is strictly step 7's post-install verify, just also used as a stand-in
for the part-(a) screen. It costs one extra script pass but is the only reliable signal
available from this surface.

**Practical implication:** on Cowork, don't attempt the bridge-first freshness screen's
ListSkills half and don't spend time looking for an equivalent tool — go straight to
presenting + the CreationTime/hash post-install verify. If a genuine account-level skill
query tool is ever exposed to Cowork, revisit this note.

Related: [package-and-stage-skill](../../../../ora-skills/package-and-stage-skill/SKILL.md)
(repo, not memory — see its Entry Point B / step 2 / step 7 sections), [reference_skill_surfaces.md](reference_skill_surfaces.md).
