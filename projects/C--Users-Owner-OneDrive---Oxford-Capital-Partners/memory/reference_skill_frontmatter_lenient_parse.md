---
name: skill-frontmatter-lenient-parse
description: "The Claude Code SKILL.md frontmatter reader is line-wise/lenient, not strict YAML — ~82/110 ORA SKILL.md fail yaml.safe_load by design; do not \"fix\" them."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T15:02:03.925Z
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

Related: [[feedback_verify_subagent_safe_claims]], [[reference_cc_scheduler_filepath_mechanism]].
