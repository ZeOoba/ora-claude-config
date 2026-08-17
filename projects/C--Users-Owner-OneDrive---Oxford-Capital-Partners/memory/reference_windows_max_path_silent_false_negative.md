---
name: reference-windows-max-path-silent-false-negative
description: "Windows MAX_PATH (260 chars): Python's os.path.exists/Path.is_file return False for a file that exists, while os.listdir still returns its name and git/ls read it fine -- a silent false negative that has now broken two different ORA tools. Prefer a SHORT checkout root over the \\?\ prefix."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 30b5a31f-00a4-42f8-b9ea-87f07de2c74b
  modified: 2026-08-16T18:12:23.366Z
---

**The rule.** On Windows, any path at or beyond **260 characters** is invisible to Python's stdlib path calls unless it carries the `\\?\` extended-length prefix (or long paths are enabled OS-wide, which they are not here). `os.path.exists()`, `Path.is_file()`, and `open()` all report the file as **absent**. Nothing raises; the check simply comes back False.

**The tell — a listing and an existence check that disagree.** `os.listdir(parent)` returns the filename (it never builds the full path), so the file is plainly there, and the very next `os.path.exists(os.path.join(parent, name))` on that same name is False. If you see that contradiction, stop looking for a rename, a race, or a permissions problem and measure `len(path)`.

**Why it hides so well: the surrounding tools are long-path aware and Python is not.** `ls`, `tail`, `grep`, and every `git` command read the file normally, so a shell-level sanity check "proves" the file exists and sends you hunting for a bug in your own logic. Both instances below burned time on exactly that.

**It has now bitten twice, in unrelated tools:**

1. **2026-08-03 — `ora-skills` drift detector.** `tools/pending_reimport.py`'s `skill_drifted()` did `if not cache_file.is_file(): return True`, so `masterlease-jurisdiction-rebase`'s bundled fixture (**265 chars**) reported **drifted forever** — byte-identical to the repo, unclearable by any amount of reinstalling, because every sweep failed the same way. Fixed with a `_win_long` prefix helper. Full account in `event_log.md` (2026-08-03).
2. **2026-08-16 — memory edits in a scratchpad worktree.** A git worktree created under the session scratchpad put the memory files at **275 chars** (scratchpad root ~152 + `projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/` 66 + a 50-62 char memory filename). `MEMORY.md` (228) wrote fine; every longer filename failed. Three attempts lost, including one where the `\\?\` prefix was itself built wrong through a bash heredoc and produced `\?\` (one leading backslash), which fails identically and looks like the prefix "not working".

**How to apply — prefer a short root; treat the prefix as the fallback.** When a task needs Python to write into this repo, put the worktree/checkout at a **short path** (`C:/Users/Owner/wt-mem`, ~21 chars, lands these same files at ~144) rather than under the session scratchpad. That removes the whole class with no string surgery. Reach for `\\?\` only in library code that cannot control where it is pointed (the `_win_long` case) — and if you do, verify the built string starts with exactly two backslashes before blaming the API, because shell quoting layers eat one silently.

**This repo is unusually exposed:** the doubled `projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/` segment costs 66 chars before any filename, and ORA memory filenames routinely run 50-62. Roughly 190 characters of budget are spent before the interesting part of the path begins.

Same silent-false-negative family as [[feedback_regex_silently_fails_in_python_dash_c]] (compiles, never matches). Related Windows path hazards: [[feedback_sed_windows_path_escapes]], [[feedback_bash_unquoted_windows_paths_collapse]]. The 2026-08-16 instance surfaced alongside the CRLF/LF trap in [[reference_isolated_commit_repair_wrapper_2026-08-13]].
