# Maintenance Reduction Bundle 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze AAOS, replace hand-maintained counts and registries with auto-discovery or checks across five repos, and add the stop-when-unused doctrine.

**Architecture:** There are seven independent tasks, one PR or isolated commit per repo concern, and no shared code between repos. Ordering: Task 1 (doctrine) lands first, Task 3 depends on Task 2, Task 7 depends on Tasks 1 and 3 (same checkout), and Task 6 (Website) ships last behind Gabriel's per-deploy confirmation. Tasks 2, 4 and 5 run in parallel.

**Tech Stack:** Python 3 stdlib unittest (ora-skills), TypeScript + vitest (oxford-command-center), Node 20 `node:test` ESM (Website), Markdown/YAML (AAOS, `~/.claude`), scheduled-tasks MCP.

**Spec:** `C:\Users\Owner\.claude\docs\superpowers\specs\2026-11-05-maintenance-reduction-bundle-1-design.md`. §11 lists the corrections made while writing this plan.

## Global Constraints

- **Shared checkouts are single-writer:** `~/.claude`, ora-skills, oxford-command-center and website-canonical. Before any edit, run `python ~/.claude/maintenance/preflight-shared-checkout.py --repo <checkout> --paths <files> --since <HEAD sha at task start>` (exit 0 means go; any nonzero means STOP). Then claim with `python ~/.claude/hooks/lib/claim_work.py claim repo-housekeeping "<what>" --paths <files>`. Do the work in a worktree (`git worktree add`) cut from `origin/main`.
- **Stage explicit paths only. Never `git add -A`.**
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Invariant 2:** a merge to website-canonical `main` is a production deploy of oxfordra.net. It needs Gabriel's in-turn confirmation. Previews are the default.
- **Never `delete_scheduled_task` without the `register-scheduled-task` skill loaded.** The CC/MCP retire order is registry delete first, then archive the folder.
- **Don't touch:** financial-decision code, governor constants, `config/*.json`, `data/overlay.json`, `finance.sqlite`, `confidential-terms.json`.
- **Outward-facing actions need Gabriel's in-turn yes:** deleting remote branches (Task 2) and the Website prod merge (Task 6).
- Doctrine D1 applies as soon as Task 1 lands: review-round fixes in this bundle are committed to the same PR branch and never open a new PR.

---

### Task 1: Stop-when-unused doctrine (D1–D3)

**Files:**
- Modify: `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\reference_engineering_os_done_bar.md`. Insert a new section before the final `## Non-trivial technical recommendations` heading.

**Interfaces:**
- Produces: section heading `## Stop-when-unused (D1–D3, added 2026-11-05)`, which Tasks 2–7 follow.

- [ ] **Step 1: Preflight and claim**

```bash
cd /c/Users/Owner/.claude
S=$(git rev-parse HEAD)
python maintenance/preflight-shared-checkout.py --repo . --paths projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_engineering_os_done_bar.md --since $S
python hooks/lib/claim_work.py claim repo-housekeeping "bundle-1 doctrine D1-D3" --paths projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_engineering_os_done_bar.md
```
Expected: `PREFLIGHT CLEAR` and the claim succeeds (exit 0). On exit 3 (a live claim exists), STOP and report it.

- [ ] **Step 2: Insert the section.** Use Edit with the anchor `## Non-trivial technical recommendations (moved from CLAUDE.md 2026-10-30)` and put this text immediately before it:

```markdown
## Stop-when-unused (D1–D3, added 2026-11-05)
Source: maintenance-reduction bundle 1 (`docs/superpowers/specs/2026-11-05-maintenance-reduction-bundle-1-design.md`). Five repo surveys found most maintenance load is sessions generating follow-up work for each other, not content volume.

- **D1 — Follow-ups ride the parent PR.** Fixes from a review round, QC pass or "residuals" commit to the same branch as the change they fix. Never open a separate PR for them. If the parent has already merged, the follow-up PR title must name it (`follow-up to #N`).
- **D2 — Usage evidence before maintenance.** Before amending, re-tuning the cadence of, or adding tests/docs to a system, scheduled task or skill, cite usage from the last 30 days (task runs, seam traffic, invocations, page reads). With none, propose freeze or retirement instead. Exempt: security and confidentiality fixes, and explicit requests from Gabriel.
- **D3 — Wording-only edits wait for the next real change.** A wording-only or changelog-only edit to a SKILL.md or task spec gets no version bump or PR of its own. It ships with the next behavior change. Exempt: factual errors in doctrine, and anything a gate blocks.
```

- [ ] **Step 3: Verify placement**

Run: `grep -n "^## " projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_engineering_os_done_bar.md`
Expected: `## Stop-when-unused (D1–D3, added 2026-11-05)` is listed directly above `## Non-trivial technical recommendations`.

- [ ] **Step 4: Commit and release**

```bash
git add -- projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_engineering_os_done_bar.md
git commit -m "doctrine(done-bar): add stop-when-unused rules D1-D3 (bundle 1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```
Expected: one file changed. Native pre-push (the doctrine-drift gate) passes when this is pushed with the rest of the `~/.claude` commits.

---

### Task 2: Freeze AAOS

**Files (repo `C:\Users\Owner\AAOS`, worktree `C:\Users\Owner\AAOS-worktrees\freeze`):**
- Modify: `README.md` (banner inserted after line 1)
- Create: `docs/adr/0007-freeze.md`
- Modify: `.github/workflows/ci.yml` (the `on:` block only)

**Interfaces:**
- Produces: `docs/adr/0007-freeze.md` on `origin/main`. Task 3's event-log entry cites it by path.

- [ ] **Step 1: Worktree**

```bash
cd /c/Users/Owner/AAOS && git fetch origin
git worktree add ../AAOS-worktrees/freeze -b chore/freeze-adr-0007 origin/main
cd ../AAOS-worktrees/freeze
```

- [ ] **Step 2: Capture the branch table for the ADR**

Run:
```bash
git for-each-ref --format='| `%(refname:lstrip=3)` | `%(objectname)` | %(committerdate:short) |' refs/remotes/origin/ | grep -v -E '`(HEAD|main)`'
```
Expected: about 31 rows (every remote branch except `main`/`HEAD`; 3 of them are `amd/*`). Paste the output verbatim into the ADR table in Step 3.

- [ ] **Step 3: Write `docs/adr/0007-freeze.md`**

```markdown
# ADR-0007: Freeze AAOS

- **Status:** Accepted (Gabriel, 2026-11-05, maintenance-reduction bundle 1)
- **Supersedes in effect:** AMD-0003, AMD-0004, AMD-0006 are **suspended by this ADR**. They are not rejected; they resume only on revival.

## Context
- The live seam (`Claude_Workspace\AAOS\projects\ora-ops\`) shows no task, lock or event activity after 2026-08-16. The last cross-surface handoff was 2026-07-10.
- Both scheduled callers (`ora-aaos-expire-leases`, `ora-aaos-publish-contracts`) have been disabled since September 2026 (last runs 2026-09-14 and 2026-09-22).
- Even so, the repo took about 60 commits in the 90 days to 2026-11-05 (ADR and amendment loops, review passes, Python-version chasing), and CI failed 7 of its last 12 runs.

## Decision
- The repo is FROZEN. No amendments, refactors, doc refreshes or dependency chasing.
- CI runs only on manual `workflow_dispatch`.
- Every non-`main` remote branch is deleted. Their head SHAs are recorded below so any of them can be restored with `git push origin <sha>:refs/heads/<name>`.
- Both scheduled tasks are retired (registry entry deleted, spec folder archived) in `~/.claude`.

## Revival trigger
A real cross-surface task, meaning work that must move between Claude Code and Cowork and cannot be done on one surface, shows up at least twice in 30 days. Revival is a new ADR that un-freezes, re-registers the tasks via `register-scheduled-task`, and re-enables push/PR CI.

## Deleted branches (restorable by SHA)
| Branch | Head SHA | Last commit |
|---|---|---|
<PASTE STEP 2 OUTPUT HERE, VERBATIM>
```

Replace the `<PASTE …>` line with the Step 2 output. The step 5 check fails if the line is left in.

- [ ] **Step 4: README banner.** Insert immediately after line 1 (`# AAOS — Agent-to-Agent Operating Substrate`):

```markdown

> **FROZEN (2026-11-05) — see [`docs/adr/0007-freeze.md`](docs/adr/0007-freeze.md).** No live seam traffic since 2026-08-16; both scheduled callers retired. This README is a historical snapshot as of 2026-10-28: its counts (tests, scripts, ADRs) are not maintained. Revive only via a new ADR when the revival trigger in ADR-0007 is met.
```

- [ ] **Step 5: CI trigger.** In `.github/workflows/ci.yml`, replace

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```
with
```yaml
# FROZEN 2026-11-05 (docs/adr/0007-freeze.md): manual runs only.
on:
  workflow_dispatch:
```

- [ ] **Step 6: Verify**

```bash
grep -c "PASTE STEP 2" docs/adr/0007-freeze.md            # expect 0
python -c "import yaml,sys;d=yaml.safe_load(open('.github/workflows/ci.yml'));print(list(d[True].keys()))"   # expect ['workflow_dispatch']
python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3   # expect OK (suite uses tmpdir seams)
```
If PyYAML is missing, check with `grep -n -A2 "^on:" .github/workflows/ci.yml` instead. The expected output is the `workflow_dispatch:` line.

- [ ] **Step 7: Commit, push, open the PR**

```bash
git add -- README.md docs/adr/0007-freeze.md .github/workflows/ci.yml
git commit -m "chore: freeze AAOS (ADR-0007) - banner, manual-only CI, branch SHA record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin chore/freeze-adr-0007
gh pr create --repo ZeOoba/AAOS --title "Freeze AAOS (ADR-0007)" --body "Freezes AAOS per ADR-0007 (maintenance-reduction bundle 1). README banner, CI to workflow_dispatch only, deleted-branch SHA record. Branch deletion happens after merge, on Gabriel's confirmation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 8: Review and merge.** Dispatch `pr-review-toolkit:code-reviewer` (model sonnet) on the PR diff. Apply fixes on this same branch (D1). Merge only on Gabriel's go-ahead (`merge-ready` skill).

- [ ] **Step 9: Delete branches (outward-facing; ask Gabriel first).** Show Gabriel the ADR table and ask: "Delete these N remote AAOS branches? SHAs are recorded in ADR-0007." Only on a yes:

```bash
cd /c/Users/Owner/AAOS && git fetch origin --prune
git for-each-ref --format='%(refname:lstrip=3)' refs/remotes/origin/ | grep -v -E '^(HEAD|main)$' | xargs -r -n1 git push origin --delete
git fetch origin --prune && git branch -r
```
Expected: only `origin/HEAD -> origin/main` and `origin/main` remain.

- [ ] **Step 10: Clean up the worktree**

```bash
cd /c/Users/Owner/AAOS && git worktree remove ../AAOS-worktrees/freeze
```

---

### Task 3: Retire the two AAOS scheduled tasks

**Depends on:** Task 2 merged, so ADR-0007 is on `origin/main`.

**Files (`C:\Users\Owner\.claude`):**
- Move: `scheduled-tasks/ora-aaos-expire-leases/` → `scheduled-tasks/_archive_2026-11-05_aaos-frozen/ora-aaos-expire-leases/`
- Move: `scheduled-tasks/ora-aaos-publish-contracts/` → `scheduled-tasks/_archive_2026-11-05_aaos-frozen/ora-aaos-publish-contracts/`
- Append: `projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md` (via `maintenance/append-event-log.py` only)

**Interfaces:**
- Consumes: ADR-0007 path from Task 2.
- Produces: neither task id appears in `list_scheduled_tasks`.

- [ ] **Step 1: Load the skill.** Invoke `register-scheduled-task` and follow its RETIRE procedure for the CC/MCP fleet. The steps below are that procedure as it applies here. If the skill differs, the skill wins.

- [ ] **Step 2: Registry single-writer check**

```bash
tail -5 /c/Users/Owner/.claude/maintenance/_state/registry-membership.log
```
Expected: no entries from another session in the last 2h. If there are any, STOP and reconcile.

- [ ] **Step 3: Delete the registry entries first** (CC/MCP order; `guard.ps1` would otherwise resurrect them). Call the MCP tool `delete_scheduled_task` with `taskId: "ora-aaos-expire-leases"`, then again with `taskId: "ora-aaos-publish-contracts"`.

- [ ] **Step 4: Verify the registry**

Call `list_scheduled_tasks` and search the saved result for `ora-aaos`.
Expected: no matches.

- [ ] **Step 5: Preflight, claim, archive the folders**

```bash
cd /c/Users/Owner/.claude
S=$(git rev-parse HEAD)
P="scheduled-tasks/ora-aaos-expire-leases scheduled-tasks/ora-aaos-publish-contracts scheduled-tasks/_archive_2026-11-05_aaos-frozen"
python maintenance/preflight-shared-checkout.py --repo . --paths $P --since $S
python hooks/lib/claim_work.py claim repo-housekeeping "retire AAOS tasks (ADR-0007)" --paths $P
A=scheduled-tasks/_archive_2026-11-05_aaos-frozen
mkdir -p $A/ora-aaos-expire-leases $A/ora-aaos-publish-contracts
git mv scheduled-tasks/ora-aaos-expire-leases/SKILL.md $A/ora-aaos-expire-leases/SKILL.md
git mv scheduled-tasks/ora-aaos-publish-contracts/SKILL.md $A/ora-aaos-publish-contracts/SKILL.md
# untracked leftovers (.bak file, _state-history/) move too -- never deleted (Invariant 6)
mv scheduled-tasks/ora-aaos-expire-leases/* $A/ora-aaos-expire-leases/ 2>/dev/null; rmdir scheduled-tasks/ora-aaos-expire-leases
mv scheduled-tasks/ora-aaos-publish-contracts/* $A/ora-aaos-publish-contracts/ && rmdir scheduled-tasks/ora-aaos-publish-contracts
```
`publish-contracts` also holds untracked files (`SKILL.md.bak-2026-10-26-fwdslash`, `_state-history/`). They move with plain `mv`, are not deleted (Invariant 6), and stay untracked.

Expected: `ls scheduled-tasks | grep aaos` prints only `_archive_2026-11-05_aaos-frozen`.

- [ ] **Step 6: Event-log entry**

```bash
python maintenance/append-event-log.py <<'EOF'
## 2026-11-05 -- AAOS frozen; ora-aaos-expire-leases + ora-aaos-publish-contracts RETIRED
- **Why:** AAOS frozen per `ZeOoba/AAOS` `docs/adr/0007-freeze.md` (no seam traffic since 2026-08-16; both tasks disabled since Sept). Maintenance-reduction bundle 1.
- **Done:** registry entries deleted (CC/MCP order), spec folders archived to `scheduled-tasks/_archive_2026-11-05_aaos-frozen/`.
- **⛔ Do NOT re-register** either id unless AAOS is revived by a new ADR meeting ADR-0007's revival trigger.
EOF
```
Expected: exit 0 and the entry at the top of `event_log.md`.

- [ ] **Step 7: Commit and release**

```bash
git add -- scheduled-tasks/_archive_2026-11-05_aaos-frozen scheduled-tasks/ora-aaos-expire-leases scheduled-tasks/ora-aaos-publish-contracts projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md
git status --short -- scheduled-tasks projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md
git commit -m "chore(fleet): retire ora-aaos-expire-leases + ora-aaos-publish-contracts (AAOS ADR-0007)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```
Expected: `git status` shows only renames plus the `event_log.md` modification. The untracked `.bak` file and `_state-history/` are not staged.

- [ ] **Step 8: Next-day check.** On the next run of `ora-task-integrity-guard` (Mondays), confirm it did not restore either folder: `ls /c/Users/Owner/.claude/scheduled-tasks | grep -c "^ora-aaos"` should print `0`.

---

### Task 4: ora-skills — auto-discover skill test suites

**Review tier:** `tools/skill_ci_gates.py` is a CI gate. Before merge, dispatch `adversarial-reviewer` with `model: opus`. Prompt it to refute: "the discovered gated set equals the old GATED∪EXCLUDED partition, and no test file can silently drop out of CI."

**Files (repo `C:\Users\Owner\ora-skills`, worktree `C:\Users\Owner\ora-skills-wt-suite-discovery`):**
- Modify: `tools/skill_ci_gates.py`. Replace the `GATED_SKILL_SUITES` / `EXCLUDED_SKILL_SUITES` block, `_expand` and `suite_coverage`, and the `suites` branch of `main()`. Update the module docstring line for `suites`.
- Modify: `tools/test_skill_ci_gates.py`, class `SuiteCoverage`.
- Modify: `acquisition-underwriting-eval-harness/lib/test_parse_replays.py`. Add the `CI_EXCLUDE` marker.
- Modify: `tools/run_skill_suites.sh` lines 6-8 (comment), `CLAUDE.md:18`, `README.md:332-335`, `README.md:46` (count), `repo-architecture/SKILL.md:17` (gotcha line plus a changelog line).

**Interfaces:**
- Produces:
  - `skill_ci_gates.ci_exclude_reason(path: Path) -> str | None`
  - `skill_ci_gates.excluded_suites(repo: Path = REPO) -> dict[str, str]` (repo-relative posix path → reason)
  - `skill_ci_gates.suite_coverage(repo: Path = REPO) -> tuple[list[str], list[str]]` (gated_files, errors). The `gated=`/`excluded=` kwargs are removed.
  - The `suites` CLI output is unchanged in format: gated paths, one per line, on stdout.

- [ ] **Step 1: Worktree, then record the baseline set**

```bash
cd /c/Users/Owner/ora-skills && git fetch origin
git worktree add ../ora-skills-wt-suite-discovery -b chore/suite-autodiscovery origin/main
cd ../ora-skills-wt-suite-discovery
python tools/skill_ci_gates.py suites | tr -d '\r' | sort > "$TEMP/suites-before.txt"; wc -l "$TEMP/suites-before.txt"
```
Expected: about 20 lines, exit 0. Keep this file for Step 7.

- [ ] **Step 2: Replace the tests.** In `tools/test_skill_ci_gates.py`, replace the five list-based tests in `class SuiteCoverage` (`test_gated_files_are_returned`, `test_ungated_skill_test_file_is_flagged`, `test_excluded_file_is_not_flagged_or_returned`, `test_glob_matching_nothing_is_flagged`, `test_both_gated_and_excluded_is_flagged`) and `test_real_repo_every_skill_test_file_is_covered` with:

```python
class SuiteCoverage(TempRepo):
    def test_every_discovered_file_is_gated(self):
        _skill(self.root, 'a', files={'tests/test_a.py': '', 'lib/test_b.py': ''})
        files, errors = g.suite_coverage(self.root)
        self.assertEqual(files, ['a/lib/test_b.py', 'a/tests/test_a.py'])
        self.assertEqual(errors, [])

    def test_ci_exclude_marker_keeps_file_out(self):
        _skill(self.root, 'a', files={'tests/test_a.py': 'CI_EXCLUDE = "linux case folding"\n',
                                      'tests/test_b.py': ''})
        files, errors = g.suite_coverage(self.root)
        self.assertEqual((files, errors), (['a/tests/test_b.py'], []))
        self.assertEqual(g.excluded_suites(self.root), {'a/tests/test_a.py': 'linux case folding'})

    def test_single_quoted_marker_counts(self):
        _skill(self.root, 'a', files={'tests/test_a.py': "CI_EXCLUDE = 'why'\n"})
        self.assertEqual(g.suite_coverage(self.root), ([], []))

    def test_blank_reason_is_an_error_and_not_excluded_silently(self):
        _skill(self.root, 'a', files={'tests/test_a.py': 'CI_EXCLUDE = "   "\n'})
        files, errors = g.suite_coverage(self.root)
        self.assertEqual(files, [])
        self.assertTrue(any('empty reason' in e for e in errors), errors)

    def test_indented_marker_does_not_count(self):
        _skill(self.root, 'a', files={'tests/test_a.py': 'def f():\n    CI_EXCLUDE = "x"\n'})
        self.assertEqual(g.suite_coverage(self.root), (['a/tests/test_a.py'], []))

    def test_archive_and_non_skill_dirs_ignored(self):
        (self.root / '_archive' / 'old' / 'tests').mkdir(parents=True)
        (self.root / '_archive' / 'old' / 'SKILL.md').write_text('x', encoding='utf-8')
        (self.root / '_archive' / 'old' / 'tests' / 'test_x.py').write_text('', encoding='utf-8')
        (self.root / 'notaskill').mkdir()
        (self.root / 'notaskill' / 'test_y.py').write_text('', encoding='utf-8')
        self.assertEqual(g.discover_skill_test_files(self.root), [])

    def test_real_repo_gates_known_suites_and_excludes_parse_replays(self):
        files, errors = g.suite_coverage()
        self.assertEqual(errors, [])
        self.assertIn('lease-form-qc/tests/test_lease_qc.py', files)
        self.assertIn('acquisition-underwriting-eval-harness/lib/test_parse_replays.py',
                      g.excluded_suites())
        self.assertNotIn('acquisition-underwriting-eval-harness/lib/test_parse_replays.py', files)
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `python tools/test_skill_ci_gates.py 2>&1 | tail -5`
Expected: FAIL/ERROR. The failures are `TypeError`/`AttributeError` for `excluded_suites`, plus the list-based `suite_coverage` returning errors for unlisted files.

- [ ] **Step 4: Implement.** In `tools/skill_ci_gates.py`, delete the block from the `# Skill-level test suites (F1).` comment banner through the end of `EXCLUDED_SKILL_SUITES` (the closing `}`), and delete the `_expand` and old `suite_coverage` functions. Insert after `discover_skill_test_files`:

```python
# ---------------------------------------------------------------------------
# Skill-level test suites (F1; auto-discovery since 2026-11-05, maintenance-reduction
# bundle 1 -- the hand-kept GATED/EXCLUDED lists were a recurring follow-up-commit source).
# Every test_*.py under a skill directory is gated automatically. To keep one out of CI,
# put a top-level line in that file:
#     CI_EXCLUDE = "<reason>"
# An exclusion is a follow-up, not a permanent exemption: fix the cause, delete the line.
# ---------------------------------------------------------------------------
_CI_EXCLUDE = re.compile(r'^CI_EXCLUDE\s*=\s*([\'"])(.*?)\1\s*(?:#.*)?$', re.M)


def ci_exclude_reason(path: Path) -> str | None:
    """The stripped CI_EXCLUDE reason declared at column 0 of `path`, or None if absent."""
    m = _CI_EXCLUDE.search(path.read_text(encoding='utf-8', errors='replace'))
    return m.group(2).strip() if m else None


def excluded_suites(repo: Path = REPO) -> dict[str, str]:
    """Skill test files carrying a CI_EXCLUDE marker -> their (possibly empty) reason."""
    out = {}
    for rel in discover_skill_test_files(repo):
        reason = ci_exclude_reason(repo / rel)
        if reason is not None:
            out[rel] = reason
    return out


def suite_coverage(repo: Path = REPO) -> tuple[list[str], list[str]]:
    """Return (gated_files, errors). Gated = every discovered skill test file without a
    CI_EXCLUDE marker. errors lists any marker whose reason is empty -- an exclusion must
    say why, or it is indistinguishable from an accident."""
    excluded = excluded_suites(repo)
    errors = [f'{rel}: CI_EXCLUDE has an empty reason -- state why it is excluded, or delete '
              f'the line to gate it' for rel, reason in excluded.items() if not reason]
    gated = [rel for rel in discover_skill_test_files(repo) if rel not in excluded]
    return gated, errors
```

Replace the `suites` branch in `main()` with:

```python
    if cmd == 'suites':
        files, errors = suite_coverage()
        for e in errors:
            print(e, file=sys.stderr)
        if errors:
            return 1
        for rel, reason in sorted(excluded_suites().items()):
            print(f'excluded (CI_EXCLUDE): {rel} -- {reason}', file=sys.stderr)
        print('\n'.join(files))
        return 0
```

In the module docstring, replace the `suites` entry's text with:
```
  suites                   print the gated skill test files (repo-relative, one per line) for
                           tools/run_suite.sh: every test_*.py under a skill dir, minus any
                           file declaring a top-level CI_EXCLUDE = "<reason>" (listed on stderr).
```

- [ ] **Step 5: Mark the one existing exclusion.** In `acquisition-underwriting-eval-harness/lib/test_parse_replays.py`, insert after the closing `"""` of the module docstring (before `import json`):

```python

# Passes on Windows (2026-10-03) and fails on ubuntu-latest: duplicate_agent_ids expects
# case-folding from Windows' case-insensitive filesystem. Fix, then delete this line.
CI_EXCLUDE = "case-sensitive filesystem: duplicate_agent_ids expects case-folding"
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python tools/test_skill_ci_gates.py 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 7: The gated set must be unchanged**

```bash
python tools/skill_ci_gates.py suites 2>"$TEMP/suites-stderr.txt" | tr -d '\r' | sort > "$TEMP/suites-after.txt"
diff "$TEMP/suites-before.txt" "$TEMP/suites-after.txt" && echo IDENTICAL; cat "$TEMP/suites-stderr.txt"
```
Expected: `IDENTICAL`, and stderr shows one `excluded (CI_EXCLUDE): acquisition-underwriting-eval-harness/lib/test_parse_replays.py -- …` line. Any diff means STOP; the change is no longer behavior-preserving.

- [ ] **Step 8: Full gates**

```bash
bash tools/run_suite.sh 2>&1 | tail -2
bash tools/run_skill_suites.sh 2>&1 | tail -2
```
Expected: both end with `failed: 0  unallowed skips: 0  ran no/bare tests: 0  unmatched globs: 0` and exit 0.

- [ ] **Step 9: Docs that named the old lists**
  - `CLAUDE.md:18`: replace the sentence `A new skill-level test suite must be listed in \`tools/skill_ci_gates.py\` (\`GATED_SKILL_SUITES\` or \`EXCLUDED_SKILL_SUITES\`).` with `Skill-level test suites (\`test_*.py\` under a skill dir) are gated automatically; to keep one out of CI, add a top-level \`CI_EXCLUDE = "<reason>"\` line to that file.`
  - `README.md:332-335`: replace `test suites listed in \`GATED_SKILL_SUITES\` in \`tools/skill_ci_gates.py\` through \`tools/run_suite.sh\`` with `test suites (every \`test_*.py\` under a skill dir, auto-discovered) through \`tools/run_suite.sh\``. Replace the sentence starting `\`skill_ci_gates.py suites\` refuses to list suites if any` through `cannot silently go ungated.` with `A file opts out only with a top-level \`CI_EXCLUDE = "<reason>"\` line; an empty reason fails the gate.`
  - `README.md:46`: replace `"SHARED_ROOT_DEPS inject at package time (5 skills)"` with `"SHARED_ROOT_DEPS inject at package time"`.
  - `tools/run_skill_suites.sh` lines 6-8: replace with `# The gated set is auto-discovered by tools/skill_ci_gates.py: every test_*.py under a skill dir,\n# minus files declaring a top-level CI_EXCLUDE = "<reason>" (an empty reason fails).`
  - `repo-architecture/SKILL.md:17`: replace `new \`test_*.py\` under a skill must be added to \`GATED_SKILL_SUITES\` or \`EXCLUDED_SKILL_SUITES\`` with `new \`test_*.py\` under a skill is gated automatically (opt out only via a top-level \`CI_EXCLUDE = "<reason>"\`)`. In its `## Changelog`, add as the first bullet: `- v1.0.2 (2026-11-05): ora-skills suite gating is now auto-discovered (CI_EXCLUDE marker); updated the gotcha line. Wording only; NO change to scored or governor constants.` Bump the `v1.0.1` in its `# Repo architecture map (v1.0.1)` title to `v1.0.2`.

Then: `git grep -n "GATED_SKILL_SUITES\|EXCLUDED_SKILL_SUITES"`. Expected: no output.

- [ ] **Step 10: Frontmatter gate, then commit**

```bash
python tools/skill_ci_gates.py frontmatter | tail -1
git add -- tools/skill_ci_gates.py tools/test_skill_ci_gates.py tools/run_skill_suites.sh acquisition-underwriting-eval-harness/lib/test_parse_replays.py CLAUDE.md README.md repo-architecture/SKILL.md
git commit -m "ci(skill-gates): auto-discover skill test suites; CI_EXCLUDE marker replaces GATED/EXCLUDED lists

Gated set verified identical to the old list (diff of 'suites' output before/after).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: frontmatter shows `0 error(s)` and every finding count is 0. The pre-commit hook passes.

- [ ] **Step 11: PR, reviews, merge**

```bash
git push -u origin chore/suite-autodiscovery
gh pr create --repo ZeOoba/ora-skills --title "ci(skill-gates): auto-discover skill test suites (CI_EXCLUDE marker)" --body "Replaces hand-maintained GATED_SKILL_SUITES/EXCLUDED_SKILL_SUITES with discovery plus an in-file CI_EXCLUDE marker (maintenance-reduction bundle 1). The gated set is byte-identical before and after (sorted diff of \`skill_ci_gates.py suites\`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Run `pr-review-toolkit:code-reviewer` (model sonnet) and `adversarial-reviewer` (model opus, prompt as given under **Review tier**). Fixes go on this branch (D1). Merge on Gabriel's go-ahead via `merge-ready`, then `git worktree remove ../ora-skills-wt-suite-discovery`.

---

### Task 5: oxford-command-center — gate list test and CLAUDE.md de-count

**Ownership:** `CLAUDE.md` is Architect-only. Before editing, add an `architecture/status.json` entry for this task with `review_needed: true` (CLAUDE.md §0 checklist), as the repo's own protocol requires. `package.json` is NOT touched.

**Files (repo `C:\Users\Owner\oxford-command-center`, worktree under `C:\Users\Owner\oxford-command-center-worktrees\gate-list-test`):**
- Create: `tests/unit/gate-scripts.test.ts`
- Modify: `CLAUDE.md` line 6 (Last-verified note), line 52 (Gate row), §6 lines 151-175 (the step list and the paragraph after it)
- Modify: `architecture/status.json` (one entry, per repo protocol)

**Interfaces:**
- Consumes: `package.json` `scripts.gate`, `scripts["gate:ci"]`; `CLAUDE.md` §6 fenced block.
- Produces: the test file only. No runtime code.

- [ ] **Step 1: Worktree and status entry.** Follow CLAUDE.md §5 (Worktree Setup Protocol) to create `oxford-command-center-worktrees/gate-list-test` on branch `chore/gate-list-test` from `origin/main`. Add the `architecture/status.json` entry using the existing entry shape. Copy an existing entry's keys exactly. The task is "Gate-list drift test + CLAUDE.md de-count (bundle 1)", the files are `CLAUDE.md` and `tests/unit/gate-scripts.test.ts`, and `review_needed: true`.

- [ ] **Step 2: Write the failing test** `tests/unit/gate-scripts.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// Maintenance-reduction bundle 1 (2026-11-05): the gate step list used to be hand-copied into
// CLAUDE.md ("11 steps") and drifted when check:css-tokens was added. package.json is the
// source of truth; this test pins the two intentional facts that docs used to restate by hand.
const root = process.cwd(); // vitest runs from the repo root (npm run test / gate)
const scripts: Record<string, string> = JSON.parse(
  readFileSync(resolve(root, 'package.json'), 'utf8'),
).scripts;

const steps = (name: string): string[] =>
  scripts[name]!.split('&&').map((s) => s.trim().replace(/^npm run /, ''));

// CI runners have no live workbook / FINANCIALS_DIR, so these run only in the local gate.
const LOCAL_ONLY = ['reconcile', 'reconcile:noi-crosscheck', 'warehouse:verify', 'warehouse:drift'];
// CI builds and size-checks the bundle; the local gate does not.
const CI_ONLY = ['build', 'check:bundle'];

describe('gate scripts', () => {
  it('gate:ci is exactly gate minus LOCAL_ONLY plus CI_ONLY, in order', () => {
    const expected = [...steps('gate').filter((s) => !LOCAL_ONLY.includes(s)), ...CI_ONLY];
    expect(steps('gate:ci')).toEqual(expected);
  });

  it('every LOCAL_ONLY step is actually in gate', () => {
    for (const s of LOCAL_ONLY) expect(steps('gate')).toContain(s);
  });

  it('CLAUDE.md §6 describes every gate step', () => {
    const md = readFileSync(resolve(root, 'CLAUDE.md'), 'utf8');
    const section = md.slice(md.indexOf('## 6. Gate Requirements'));
    const block = section.slice(section.indexOf('```') + 3, section.indexOf('```', section.indexOf('```') + 3));
    const described = block.split('\n').map((l) => l.trim().split(/\s+/)[0]).filter(Boolean);
    for (const s of steps('gate')) expect(described, `CLAUDE.md §6 is missing "${s}"`).toContain(s);
  });
});
```

- [ ] **Step 3: Run it and confirm it fails**

Run: `npx vitest run tests/unit/gate-scripts.test.ts`
Expected: tests 1 and 2 PASS (they pin today's real divergence). Test 3 FAILS with `CLAUDE.md §6 is missing "check:css-tokens"`, which is the drift the survey found.

- [ ] **Step 4: Fix CLAUDE.md.**
  - In the §6 fenced block, insert after the `check:dev-css` entry's two lines:
    ```
    check:css-tokens → every var(--name) under src/ has a definition under src/ (an undefined
                    custom property fails silently in the browser; scripts/check-css-tokens.ts)
    ```
  - Replace the paragraph `(This is the true 11-step \`package.json\` \`gate\` script as of 2026-09-27 — … used for CI, not local commits.)` with:
    ```
    (`package.json` is the source of truth for both scripts. `tests/unit/gate-scripts.test.ts`
    fails if this list omits a `gate` step, or if `gate:ci` stops being exactly `gate` minus the
    four local-only steps (reconcile, reconcile:noi-crosscheck, warehouse:verify, warehouse:drift)
    plus build and check:bundle — so neither this list nor that relationship can drift silently.)
    ```
  - In the `warehouse:verify` line of the block, replace `fresh SQLite in tmpdir + 32 file ingest + assertions` with `fresh SQLite in tmpdir + full file ingest + assertions`.
  - Line 52 Gate row: replace the cell with `` `npm run gate` — steps listed in §6 (source of truth: `package.json`; drift-checked by `tests/unit/gate-scripts.test.ts`). CI runs `gate:ci`. ``
  - Line 6: replace `§6 gate list last checked against \`package.json\` 2026-09-27` with `§6 gate list drift-checked by tests/unit/gate-scripts.test.ts since 2026-11-05`.

- [ ] **Step 5: Run it and confirm it passes**

Run: `npx vitest run tests/unit/gate-scripts.test.ts`
Expected: 3 passed.

- [ ] **Step 6: Full gate.** Run: `npm run gate:ci`. If the live workbook is present, also run `npm run gate`.
Expected: green. `governance` validates CLAUDE.md and status.json; on failure, fix the format and do not bypass.

- [ ] **Step 7: Commit, PR, review**

```bash
git add -- tests/unit/gate-scripts.test.ts CLAUDE.md architecture/status.json
git commit -m "test(gate): pin gate vs gate:ci relationship; CLAUDE.md gate list drift-checked, counts removed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin chore/gate-list-test
gh pr create --repo ZeOoba/oxford-command-center --title "test(gate): drift-check gate list; de-count CLAUDE.md" --body "Bundle 1 (maintenance reduction). Adds tests/unit/gate-scripts.test.ts; CLAUDE.md §6 gains the missing check:css-tokens entry and drops hand-typed counts. No package.json, financial or config change. Architect-owned file: status.json entry review_needed=true.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
No financial-decision code is touched, so no `Refute-Reviewed` trailer is needed. Confirm `check:refute` passes in CI. If it requires the trailer for CLAUDE.md, STOP and ask Gabriel rather than forging one. Review with `pr-review-toolkit:code-reviewer` (model sonnet). Merge on Gabriel's go-ahead. Then set the status.json entry to its completed state, on this branch before merge (D1).

---

### Task 6: Website — auto-discover site tests; drop README count (ships LAST)

**Deploy gate:** merging to `main` deploys oxfordra.net. Merge only after a preview check and Gabriel's explicit in-turn "yes, deploy" (Invariant 2). Use `/ship` for the release chain.

**Files (repo `C:\Users\Owner\website-canonical`, worktree `C:\Users\Owner\website-canonical-worktrees\site-test-discovery`):**
- Create: `scripts/run-site-tests.mjs`
- Create: `tests/run-site-tests.test.js` (a unit test; picked up automatically by `run-unit-tests.mjs`)
- Modify: `package.json` `scripts["test:site"]` only
- Modify: `README.md:235` (the "explicit list of 25" cell)

**Interfaces:**
- Produces: `listSiteTests(root: string): Promise<string[]>`, exported from `scripts/run-site-tests.mjs`. It returns sorted repo-relative posix paths.

- [ ] **Step 1: Worktree, then capture the current list**

```bash
cd /c/Users/Owner/website-canonical && git fetch origin
git worktree add ../website-canonical-worktrees/site-test-discovery -b chore/site-test-discovery origin/main
cd ../website-canonical-worktrees/site-test-discovery
npm ci
node -e "console.log(require('./package.json').scripts['test:site'].split(/\s+/).slice(2).sort().join('\n'))"
```
Expected: 26 paths. Save this list for Step 6. The 4 files on disk that are not in it should be exactly `functions-smoke`, `leak-gate`, `netlify-guard` and `netlify-shim-patch`, each run by its own npm script. Confirm by listing `tests/site/*.test.mjs` (30). If the 4 differ, STOP and add the real set to `SEPARATE` below.

- [ ] **Step 2: Write the failing unit test** `tests/run-site-tests.test.js`. This is CommonJS, matching the other `tests/**/*.test.js` files:

```js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const load = () => import(require('node:url').pathToFileURL(path.join(__dirname, '..', 'scripts', 'run-site-tests.mjs')).href);

function fixture(names) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'site-tests-'));
  fs.mkdirSync(path.join(root, 'tests', 'site'), { recursive: true });
  for (const n of names) fs.writeFileSync(path.join(root, 'tests', 'site', n), '');
  return root;
}

test('lists every tests/site/*.test.mjs except the separately-run four, sorted', async () => {
  const { listSiteTests } = await load();
  const root = fixture(['b.test.mjs', 'a.test.mjs', 'leak-gate.test.mjs', 'functions-smoke.test.mjs',
    'netlify-guard.test.mjs', 'netlify-shim-patch.test.mjs', 'helper.mjs', 'x.test.js']);
  assert.deepStrictEqual(await listSiteTests(root), ['tests/site/a.test.mjs', 'tests/site/b.test.mjs']);
});

test('real repo: discovers the browser suite and none of the separate four', async () => {
  const { listSiteTests, SEPARATE } = await load();
  const files = await listSiteTests(path.join(__dirname, '..'));
  assert.ok(files.includes('tests/site/csp-smoke.test.mjs'));
  for (const s of SEPARATE) assert.ok(!files.includes(`tests/site/${s}`), s);
});
```

- [ ] **Step 3: Run it and confirm it fails**

Run: `node --test tests/run-site-tests.test.js`
Expected: FAIL with `Cannot find module …run-site-tests.mjs`.

- [ ] **Step 4: Implement** `scripts/run-site-tests.mjs`:

```js
/**
 * run-site-tests.mjs — enumerate tests/site/*.test.mjs and hand `node --test` an explicit list.
 *
 * Replaces the hand-maintained 26-file list that `test:site` carried in package.json
 * (maintenance-reduction bundle 1, 2026-11-05): a new site test now runs with no config edit.
 * Enumerated here, not globbed, for the Node 20-vs-21+ reason in run-unit-tests.mjs.
 * SEPARATE files have their own npm scripts (test:functions, test:shim, test:leak-gate) and
 * different prerequisites, so they stay out of test:site.
 *
 * Run: npm run test:site      List only: node scripts/run-site-tests.mjs --list
 */
import { promises as fs } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import url from 'node:url';

export const SEPARATE = [
  'functions-smoke.test.mjs',
  'leak-gate.test.mjs',
  'netlify-guard.test.mjs',
  'netlify-shim-patch.test.mjs',
];

export async function listSiteTests(root) {
  const dir = path.join(root, 'tests', 'site');
  return (await fs.readdir(dir))
    .filter((n) => n.endsWith('.test.mjs') && !SEPARATE.includes(n))
    .sort()
    .map((n) => `tests/site/${n}`);
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === url.fileURLToPath(import.meta.url);
if (isMain) {
  const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');
  const files = await listSiteTests(ROOT);
  if (files.length === 0) {
    console.error('[run-site-tests] FAIL: no tests/site/*.test.mjs found — refusing a vacuous pass.');
    process.exit(1);
  }
  if (process.argv.includes('--list')) {
    console.log(files.join('\n'));
    process.exit(0);
  }
  console.log(`[run-site-tests] ${files.length} test file(s)`);
  const r = spawnSync(process.execPath, ['--test', ...files], { cwd: ROOT, stdio: 'inherit' });
  process.exit(r.status === null ? 1 : r.status);
}
```

- [ ] **Step 5: Run it and confirm it passes**

Run: `node --test tests/run-site-tests.test.js`
Expected: 2 pass.

- [ ] **Step 6: Same set as before**

Run: `node scripts/run-site-tests.mjs --list`
Expected: identical to the 26 paths saved in Step 1.

- [ ] **Step 7: Wire `package.json`.** Change only `"test:site"` to `"node scripts/run-site-tests.mjs"`.

- [ ] **Step 8: README line 235.** Replace `the explicit list of 25 \`tests/site/*.test.mjs\` files in \`package.json\`:` with `every \`tests/site/*.test.mjs\` file, enumerated by \`scripts/run-site-tests.mjs\` (except the four with their own scripts: functions-smoke, leak-gate, netlify-guard, netlify-shim-patch):`. The rest of the cell is unchanged.

- [ ] **Step 9: Full verify, then prove the build output is identical**

```bash
git stash -u && npm run build && find dist -type f -exec sha256sum {} + | sort -k2 > "$TEMP/dist-before.txt"; git stash pop
npm run verify
find dist -type f -exec sha256sum {} + | sort -k2 > "$TEMP/dist-after.txt"
diff "$TEMP/dist-before.txt" "$TEMP/dist-after.txt" && echo DIST-IDENTICAL
```
Expected: `npm run verify` is green, and `DIST-IDENTICAL`. If `build-dist.mjs` fails on the new `scripts/` file being unclassified, classify `scripts/run-site-tests.mjs` alongside `scripts/run-unit-tests.mjs` in `scripts/build-dist.mjs` (excluded from dist) and re-run.

- [ ] **Step 10: Commit, PR, preview**

```bash
git add -- scripts/run-site-tests.mjs tests/run-site-tests.test.js package.json README.md
git commit -m "test(site): enumerate tests/site via run-site-tests.mjs instead of a hand list

dist/ byte-identical before/after; no served change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin chore/site-test-discovery
gh pr create --repo ZeOoba/Website --title "test(site): auto-enumerate site tests" --body "Bundle 1 (maintenance reduction). test:site enumerates tests/site/*.test.mjs instead of a 26-file hand list. dist/ is byte-identical before and after, so nothing served changes. Merging deploys prod: needs Gabriel's in-turn confirmation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Run `site-qc-reviewer` and `pr-review-toolkit:code-reviewer` (model sonnet). Confirm the Netlify deploy preview builds green.

- [ ] **Step 11: Prod (Gabriel's in-turn yes only).** Ask: "Website PR is green, dist byte-identical, preview OK. Merge to main (deploys oxfordra.net)?" Only on a yes, merge via `/ship`, then run `node scripts/verify-live-csp.mjs`. Expected: pass. Then `git worktree remove ../website-canonical-worktrees/site-test-discovery`.

---

### Task 7: `~/.claude` README — remove hand-typed counts

**Depends on:** Tasks 1 and 3 committed (same checkout; separate isolated commit).

**Files:**
- Modify: `C:\Users\Owner\.claude\README.md` lines 13-14, 47, 88, 95-101, 106, 108 (current numbering; re-locate by text if lines have moved).

- [ ] **Step 1: Preflight and claim**

```bash
cd /c/Users/Owner/.claude
S=$(git rev-parse HEAD)
python maintenance/preflight-shared-checkout.py --repo . --paths README.md --since $S
python hooks/lib/claim_work.py claim repo-housekeeping "bundle-1 README de-count" --paths README.md
```

- [ ] **Step 2: Write the failing check** in the scratchpad (not the repo):

```bash
grep -n -E "\b[0-9]{2,4}\b (top-level|slash-command|custom sub-agent|task folders|dated|\`test-|files at|design specs|implementation plans|shared modules|task folders \+)" README.md
```
Expected now: about 10 matching lines (41 hook scripts, 19 modules, 61 suites, 13 commands, 17 agents, 91 scripts, 96 test files, 65 and 28 task folders, 139 folders, 421 files, 8 specs + 19 plans).

- [ ] **Step 3: Edit.** Use Edit for each item. Every replacement keeps the description and drops only the number:
  - Lines 13-14 (the "Point-in-time doc, verified … counts in §3 re-run on 2026-10-06 …" blockquote): replace the whole blockquote with `> Structure and paths are maintained here; **counts are not** — for current numbers see \`docs/system-inventory.md\` (weekly regenerated) or run \`git ls-files <dir> | wc -l\`.`
  - Line 47: `41 top-level hook scripts:` becomes `top-level hook scripts:`.
  - Line 88: delete the sentence `Verified against \`git ls-files\` at \`origin/main\` (2026-10-03; counts re-run 2026-10-06 at …).` (through its closing parenthesis and period).
  - Line 95: `41 top-level hook scripts` → `top-level hook scripts`; `(19 shared modules:` → `(shared modules:`; `(61 \`test-*.py\` suites plus` → `(\`test-*.py\` suites plus`.
  - Line 96: `13 slash-command definitions` → `slash-command definitions`.
  - Line 97: `17 custom sub-agent definitions (` plus the 17-name list → `custom sub-agent definitions (one \`.md\` per agent; see \`agents/\`)`. The name list was itself a stale hand registry; the tree has 22.
  - Line 99: `91 top-level scripts/configs` → `top-level scripts/configs`; `and 96 \`test-*\`/\`test_*\` files across` → `and \`test-*\`/\`test_*\` files across`; `the 8 off-fleet Windows tasks` → `the off-fleet Windows tasks`.
  - Line 100: `65 task folders, 28 dated \`_archive_*\` folders` → `task folders, dated \`_archive_*\` folders`.
  - Line 101: `(139 task folders + one archive folder)` → `(task folders + archive folders)`.
  - Line 106: `(8 design specs + 19 implementation plans for` → `(design specs and implementation plans for`.
  - Line 108: `(421 files at 2026-10-06 and growing daily:` → `(growing daily:`.

- [ ] **Step 4: Re-run the check**

Run the Step 2 grep again. Expected: no output. Run `grep -n "diagram-verified" README.md`. These stamps stay, because they date diagrams, not counts.

- [ ] **Step 5: Commit and release**

```bash
git add -- README.md
git commit -m "docs(readme): drop hand-typed counts; point to docs/system-inventory.md (bundle 1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
python hooks/lib/claim_work.py release repo-housekeeping
```

---

### Task 8: Bundle close-out

- [ ] **Step 1: Done-criteria sweep.** Run the grep from the spec §7 done criteria across the five READMEs/CLAUDE.md files:

```bash
for f in /c/Users/Owner/.claude/README.md /c/Users/Owner/ora-skills/README.md /c/Users/Owner/ora-skills/CLAUDE.md /c/Users/Owner/oxford-command-center/CLAUDE.md /c/Users/Owner/website-canonical/README.md; do git -C "$(dirname $f)" fetch -q origin; MSYS_NO_PATHCONV=1 git -C "$(dirname $f)" show "origin/main:$(basename $f)" | grep -n -E "\b[0-9]{2,4}\b (tests?|hooks?|skills?|agents?|steps?|suites?|test files)\b" | sed "s|^|$f: |"; done
```
Expected: no hand-typed inventory counts remain. Lines that are performance budgets or dates are acceptable; note any you keep. The AAOS README is exempt as a historical snapshot (ADR-0007).

- [ ] **Step 2: Push the `~/.claude` commits.** Push via the checkout's normal path (native pre-push gates run). Never force.

- [ ] **Step 3: Offer the 30-day check.** Ask Gabriel whether to register the one-time 2026-12-05 success check (spec §8) via `register-scheduled-task`. Do not register it without a yes.
