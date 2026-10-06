---
name: feedback-ora-skills-tests-zero-tests-rule
description: ora-skills tools/test_*.py must be stdlib unittest with a __main__ runner — pytest-style bare `def test_*` runs ZERO tests under run_suite.sh yet exits 0 "ok"; run_suite.sh's zero-empty rule (PR #80) now fails EMPTY/BARE files
metadata:
  type: feedback
---

Every `tools/test_*.py` in `ora-skills` must be a stdlib `unittest.TestCase` file ending in `if __name__ == '__main__': unittest.main(...)`, and must print `Ran N tests` with N ≥ 1. `tools/run_suite.sh` (local README step 7 and CI `tools-tests.yml`) runs each file as plain `python <file>`: no pytest is installed or invoked.

**Why:** `test_reimport_cycle.py` (bf724aa) shipped 7 pytest-style module-level `def test_*` functions. Under `python <file>` they never executed. The file exited 0, and run_suite.sh reported it `ok` with an empty summary. The zero-skip baseline could not see this, because nothing reports as skipped. This is the same silent-pass family as the rent-comp skip ([[project-rent-comp-retirement-process-gap-2026-08-13]]) and a "zero that could mean couldn't look" ([[feedback-verified-null-vs-inferred-null]]). The adversarial merge gate on ora-skills PR #79 caught it on 2026-09-23. It was fixed in PR #80, which was open on 2026-09-23.

**How to apply:**
- **Zero-empty rule:** run_suite.sh fails a file as **EMPTY** if it exits 0 without `Ran N tests` with N ≥ 1. It fails a file as **BARE** if the file has any column-0 `def test_*`, meaning a stray function beside a TestCase that never runs. `Ran 0` under `unittest.main()` already exits 5 on Python 3.12+ and shows as FAIL.
- **A whole-module skip stays EMPTY.** `setUpModule` raising SkipTest prints `Ran 0 … skipped=1`. Never route it to `ALLOWED_SKIPS`: that list counts individual test skips, and the census `=1` entry would let a module that ran nothing pass on ubuntu. Opus re-review caught this on the PR #80 follow-up.
- **Only exemption:** exact paths in `NON_UNITTEST` (currently just `test_description_budget.py`). Those must print `all checks passed` instead. An unlisted file that prints the marker still fails.
- **Checking a test file:** "suite green" is not proof the tests ran. Read that file's `Ran N` row in the summary. For a new test, mutate the target in a scratch copy and confirm each test fails.
