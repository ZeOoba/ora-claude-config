---
name: skill-frontmatter-lenient-parse
description: "The Claude Code SKILL.md frontmatter reader is line-wise/lenient, not strict YAML — ~82/110 ORA SKILL.md fail yaml.safe_load by design; do not \"fix\" them."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-08-05T20:20:15.900Z
---

The Claude Code harness parses SKILL.md frontmatter **line-wise** ("first colon splits
key from value"), **not** with a real YAML parser. Descriptions containing `": "` —
the trailing `[MODEL: <id> | checked <date>]` convention (44 fleet files), and ordinary
`Use when the user mentions: ...` trigger lists — are unquoted YAML plain scalars that
`yaml.safe_load` rejects with `ScannerError: mapping values are not allowed here`, yet
the harness loads them **correctly and in full**.

Measured 2026-07-24 across all four roots (110 files): 82 fail strict YAML — 0/4 cli
skills, 7/53 Cowork mirror, 24/30 sched-cc, 23/23 sched-lams. Empirical proof the
leniency is real, not luck: `debt-management` is a strict-YAML failure and its complete
description still renders in the loaded skill list.

**Do not mass-quote description strings to satisfy a strict parser the harness does not
use.** Description text is load-bearing for skill routing; editing it to appease an
external linter risks routing regressions for zero functional gain. Escalate only if the
harness's own reader ever becomes strict.

`maintenance/setup-self-audit.py`'s `skill-frontmatter` probe is therefore a
**structural** check by design (fence + `name:`/`description:` inside it + no collapsed
`## name:` heading) — its purpose is the collapsed-frontmatter corruption class, not YAML
validity. Its output says so explicitly; see [[project-setup-self-audit-frontmatter-probe-2026-07-24]].

**Re-verified 2026-08-05 (2nd recurrence — a session raised this as a fresh "pre-existing
defect" despite this memory existing).** Counts on the two fleet roots: **97/147 fail**
strict YAML — 25 of 50 live in `scheduled-tasks/`, 72 in `_scheduled_tasks_backup/`.
Failure modes: `COLON_SPACE` 91, `LEADING_BRACKET` 6 (`description: [ONE-TIME 2026-05-31] ...`,
which YAML reads as a flow sequence). Two additions to the case:

- **The leniency is regression-tested, not merely tolerated.** `maintenance/test-setup-self-audit.py`
  asserts *both* that a `[MODEL: ...]` description passes `_frontmatter_ok` *and* that
  `yaml.safe_load` rejects the identical string, labelled "so the leniency here is
  load-bearing, not an oversight." A strict-YAML migration breaks that test **on purpose**.
- **Quoting is actively risky, not just unnecessary.** A first-colon-split reader does not
  strip surrounding quotes, so quoting would likely inject literal `"` into the routing
  text. There is no live precedent to reason from: the only fleet SKILL.md with a quoted
  description is `scheduled-tasks/_draft-ora-cc-model-canary-sweep/` — an underscore-prefixed
  draft that is never registered or routed.

**Scale claim to sanity-check before repeating it:** the 2026-08-05 report described "a 40KB
description." That is the **file** size misread as the scalar's. Descriptions run 1.8–7.8KB —
`ora-task-integrity-guard` = 7,751 B in a 42,972 B file; `ora-health-guard` = 1,833 B in 51,653 B.

**Why it keeps recurring:** this pointer lives in [[INDEX_reference]], which is *not*
auto-loaded per session, so a session that greps the files before reading the sub-index
rediscovers 97 "failures" and reasonably concludes it found something. Read the sub-index
before filing any strict-YAML finding against SKILL.md.

Related: [[feedback_verify_subagent_safe_claims]], [[reference_cc_scheduler_filepath_mechanism]].
