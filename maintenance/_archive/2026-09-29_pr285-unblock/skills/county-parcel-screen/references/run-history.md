# county-parcel-screen — run history and incident narratives

Moved out of `SKILL.md` on 2026-09-22 (body split). Provenance and rationale only — every operative rule is restated in `SKILL.md`, which is authoritative.

## Counterparty floor — why the guard path is absolute (2026-09-18 Jackson MO / Howard MD)

(override only via the `ORA_PIPELINE_GUARD` env var). The file is UNTRACKED and
gitignored on purpose — counterparty names never live in tracked files — so it exists
in exactly ONE place on this machine. It is NOT in the `ora-skills` repo checkout and
NOT in the AppData plugin bundle. Every consumer's old `<skill>/../data/` RELATIVE path
therefore resolves to nothing whenever the skill executes from any copy other than
`~/.claude/skills/` — which is precisely how the 2026-09-18 Jackson MO run came to
screen against ORA-self patterns only. It did warn; the warning was not acted on and
the list shipped anyway (`…JacksonMO_Summary_v01.md`, honest-limits item on the
degraded floor). The same-day Howard MD run loaded the file explicitly and recorded
in its QC paragraph that "the module's own
relative path resolves into the plugin cache, where the file does not exist, and would
have degraded the floor silently."

## Scoring sub-bands — provenance (pinned 2026-09-18 from the Franklin OH pilot)

Until 2026-09-18 this skill published only the component WEIGHTS (plus the basis
bands and the 16-point UNKNOWN-HOLD value). On that day the Franklin OH pilot had to
infer the rest, and its choices became the de-facto spec that the same-day Howard MD
and Jackson MO runs then reproduced rather than re-derived. They are pinned here,
verbatim from that pilot's workbook README
(`2026-09-18_RingScreen-FranklinOH_CallList_v01.xlsx`, SCORING block) and its summary.

**These sub-bands were pinned FROM A RUN, not derived from first principles. They are
Gabriel's to amend.** Any run that diverges from them MUST say so on the face of its
summary and workbook README, with the reason — otherwise successive runs stop being
comparable, which is the failure these three runs hit.

## Sibling-parcel consolidation — the three 2026-09-18 runs that flagged F6

One owner holding several adjacent parcels on one old deed is ONE relationship
and ONE phone call, but v1.2 scored it as N independent rows. All three
2026-09-18 runs hit this and all three flagged it unresolved: Franklin (D&A
Berwick 2 parcels / 46,000 SF, DINOVO 3, AIRPORT PLAZA 4), Howard (RUMSEY ROAD
3 parcels / 120,060 SF on one deed liber), Jackson (DEEVIC 4 contiguous parcels
/ ~60,400 SF — "seven names collapse to roughly four conversations").
