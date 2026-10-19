---
name: ora-memory-commit-sweep
description: Sweep memory/ for settled uncommitted changes and commit them, closing the head_orphans() index/content gap [MODEL: claude-sonnet-5-5 | set 2026-10-06]
---

Run this exact command and report only if it errors or exits non-zero:

python "C:\Users\Owner\.claude\maintenance\memory-commit-sweep.py"

Context (do not re-derive, do not improvise around this): this script performs a bounded, self-contained commit-cadence sweep of the ORA memory/ directory (C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\). memory/ is git-tracked but has no write gate the way event_log.md has (append-event-log.py's mtime-guard + atomic-replace + spool-on-lock) -- with 5-6 concurrent Claude Code/Cowork sessions editing memory files directly, a session can commit an index edit (a new pointer in MEMORY.md or a sub-index) without git-adding the file it points to, in a different commit or not at all. memory-integrity-probe.py's head_orphans() check DETECTS this (a committed pointer with no committed target -- broken for any reader but the authoring machine); this script CLOSES it, on a cadence, instead of leaving it for someone to notice and hand-fix (happened live 2026-08-14 and again 2026-08-16, see reference_memory_dir_not_in_single_writer_list_2026-08-14.md).

The script is entirely self-contained and requires no judgment calls from you:
- Scoped strictly to the memory/ directory via absolute pathspecs -- it can never stage or commit hooks/, settings.json, or any path outside memory/.
- Only sweeps a changed file once its mtime is 120+ seconds old (leaves anything another session may still be actively mid-editing for the next cycle).
- Never auto-commits deletions or renames -- those are reported, never swept, and need a human to look.
- Verifies its staged git-index set matches exactly what it intended to add before ever calling `git commit` -- if a concurrent `git add` from another process changed the index in the meantime, it skips this cycle without unstaging anything (never interferes with another process's in-flight staging).
- Skips the entire cycle cleanly if a `.git/index.lock` is present (never forces through a lock).
- Never pushes, never switches branches, never runs reset/rebase/checkout -- purely additive local commits on whatever branch is currently checked out.
- Exit 0 = committed something or there was nothing to do (both healthy, normal outcomes -- do NOT treat "nothing to commit" as a failure). Exit 1 = transient skip (lock contention or a staging race) -- also non-fatal, it retries automatically at the next scheduled run (registry cron `0 19 * * *`, i.e. once daily, ~24h later -- not 15 minutes; corrected 2026-09-13 per ground-truth audit), no action needed. Exit 2 = a real error (memory dir missing, or not a git repo) -- this is the ONLY case that needs a human's attention.

Do not inspect, second-guess, or override what the script decides to commit -- it already embeds all the safety logic (quiet-window, no-deletes, staged-set verification). Your job is only to run it and flag exit 2. On exit 2, or on a Python traceback/crash, write one line to the completion notes describing the exact error text -- do not attempt to diagnose or fix it yourself. On exit 0 or 1, no report is needed; a silent successful run is the expected, common case.

Do not send any email or Outlook message for this task under any circumstances -- it is a silent background maintenance sweep, not a reporting task. Do not touch Notion. Do not touch any file other than what the script itself touches.