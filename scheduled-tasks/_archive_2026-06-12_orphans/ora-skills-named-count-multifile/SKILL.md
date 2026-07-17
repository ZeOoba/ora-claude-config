---
name: ora-skills-named-count-multifile
description: Extend check_named_counts in package_skills.py to scan reference files alongside SKILL.md
---

Extend the `check_named_counts` function in `C:\Users\Owner\ora-skills\tools\package_skills.py` to scan all Markdown files in a skill directory — not just SKILL.md — so that reference files like `loi-generation/references/qc-gate.md` are also validated.

## Context

The function was added in commit b54a291 (2026-06-11). It finds Markdown headers matching `\d+-[Pp]oint` or `\d+-[Ii]tem`, counts the checklist items in the section below, and fails packaging if the header's stated count is wrong. Currently `validate_frontmatter` calls it with only the SKILL.md text, so any named-count headers in `references/` subdirectories are silently skipped.

Known gap: `loi-generation/references/qc-gate.md` contains a "22-point QC Gate" header whose item count is unvalidated.

## Task

1. Read `C:\Users\Owner\ora-skills\tools\package_skills.py` in full.
2. Modify `check_named_counts(skill, text)` — or restructure how it is called — so that every `.md` file under the skill directory is scanned, not just SKILL.md. The simplest approach: change the call site in `validate_frontmatter` (or `package`) to iterate over all `.md` files and call `check_named_counts` for each, printing the filename alongside any findings.
3. Run `python tools/package_skills.py C:\Temp\ora-skill-test` (all skills) to confirm zero failures and that the loi-generation 22-Point check now fires and reports a result.
4. Commit to `main` in `C:\Users\Owner\ora-skills` with a clear message referencing the gap identified 2026-06-11.

## Constraints

- Do not modify the `check_named_counts` logic itself — only the call site / file iteration.
- Keep the output readable: prefix each finding with the relative file path (e.g. `loi-generation/references/qc-gate.md: 22-Point (22 items) OK`).
- No new dependencies; stdlib only.
- Follow the Engineering OS: smallest surgical change, verify with actual command output before claiming done.
- Repo is at `C:\Users\Owner\ora-skills` on branch `main`.