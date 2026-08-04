---
name: feedback_regex_silently_fails_in_python_dash_c
description: "Regex inside python -c run from the Bash tool is mangled by shell quoting — the pattern compiles but never matches, producing silent false negatives"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3a21fa0c-1eb5-4c06-b0c0-b5dce4253d70
  modified: 2026-08-04T00:31:32.712Z
---

A regex written inside `python -c "…"` and run through the Bash tool passes through **two** unescaping layers (bash double quotes, then the Python string literal) before `re` sees it. Sequences like `\$`, `\d`, `\\\$`, and `{1,2}` survive inconsistently. The result is the worst possible failure: **a pattern that compiles cleanly and matches nothing.** There is no error — just an empty result set that reads as a confident negative finding.

**Why this matters.** On 2026-08-03 this produced two false "0 references" scans while auditing the Master Workbook — one claiming nothing referenced `External Loans Summary` rows 6–11, another claiming nothing referenced `Portfolio Summary — Internal` rows 5–11. Both were wrong: `EXPORT_Loans` and `EXPORT_Loans_Internal` reference those rows directly, one cell per column. Acting on either "finding" would have meant deleting rows whose mirrors silently under-report afterwards. It was caught only because a later count didn't reconcile — 137 export rows cannot contiguously mirror 141 source rows — not because anything flagged the scan as broken.

**How to apply:** put regex work in a `.py` file and run `python file.py`. Never inline a pattern in `python -c` from the Bash tool. If a one-liner is genuinely unavoidable, include a **known-positive control** in the same run and assert it matches — a scan that cannot demonstrate a true positive cannot be trusted for a negative. This is the same discipline as [[feedback_verify_negative_glob_results]] (cross-check a negative `Glob` against `git ls-files`): a zero result must be earned, not assumed. Related: [[feedback_sed_windows_path_escapes]], [[feedback_bash_unquoted_windows_paths_collapse]], [[feedback_verified_null_vs_inferred_null]].
