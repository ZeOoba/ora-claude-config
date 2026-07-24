---
name: project-setup-self-audit-frontmatter-probe-2026-07-24
description: "CLOSED 2026-07-24 — setup-self-audit skill-frontmatter probe overclaimed assurance and excluded 53 fleet SKILL.md; fixed wording, a false positive, and coverage."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T15:02:18.374Z
---

**CLOSED 2026-07-24.** `ora-health-guard` Probe 6 reported *"all 57 SKILL.md parse
cleanly."* Three defects behind that one line, all in
`~/.claude/maintenance/setup-self-audit.py`:

1. **Overclaim.** The check never parsed YAML — it is a structural line-wise test. "Parse
   cleanly" asserted far more than it verified. See [[skill-frontmatter-lenient-parse]]
   for why strict YAML is deliberately *not* enforced.
2. **Coverage gap.** The 57 = 4 cli skills + 53 Cowork-mirror skills. It globbed only
   `~/.claude/skills/*/` and the Cowork mirror — **53 scheduled-task SKILL.md files
   (30 CC + 23 LAMS) were outside the scan set entirely**, including every file touched
   by the 2026-07-08 deletion incident the check is meant to detect.
3. **Latent false positive.** `"## name:" in text` was a substring test over the first 80
   lines of the *whole file*, so body prose merely quoting the pattern scored as malformed
   frontmatter. Live case: `sched-lams/ora-skill-text-audit` line 41. It had never fired
   only because scheduled tasks were unscanned — adding them would have turned the probe
   CRIT on day one.

**Fix (remedy (b) — honest wording, not a stricter parser):** collapsed-heading match
anchored to line start inside the fence only, and `##`+ required (a single `#` is a legal
YAML comment); `name:`/`description:` must now be *inside* the fence, not anywhere in the
first 80 lines; both fleet roots added via `_sd.skill_folder_root` (fail-open); OK text
now states what was checked and that it is **not** a strict YAML parse.

**Zero SKILL.md files were edited** — so no risk to how the harness reads any
`name`/`description`. Verified: tests 11/11 → 20/20 pass; live probe `0 critical, 0 warn`,
coverage 57 → 110 files.

Left uncommitted in the shared `~/.claude` checkout (2 files, `maintenance/`); another
session was concurrently sweeping backlogs — see [[reference_commit_provenance_guard]].
