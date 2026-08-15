---
name: reference_memory_dir_not_in_single_writer_list_2026-08-14
description: "CLAUDE.md's shared-checkout single-writer list omits memory/ living docs (rules.md, projects.md, MEMORY.md) — flagged for the next ora-setup-audit, not fixed ad hoc"
metadata: 
  node_type: memory
  type: reference
  originSessionId: aaca643c-9e99-4ebe-940a-7c81b182eeaf
  modified: 2026-08-14T18:31:09.441Z
---

# memory/ living docs missing from the single-writer list

**Finding (2026-08-14, from an external-artifact-intake review of the `task-observer`/"one-skill-to-rule-them-all" repo):** CLAUDE.md's "Shared-checkout = SINGLE-WRITER" rule names `CLAUDE.md`, `settings.json`, `ora-skills`, `oxford-command-center` as files/repos requiring a `git status`/`git log -1` check before editing. It does not name the `memory/` directory. `event_log.md` gets script-enforced single-writer safety (`append-event-log.py` — mtime-guard, atomic replace, spool-on-lock); hooks/repo housekeeping gets `claim_work.py`. The other living docs (`rules.md`, `projects.md`, `people.md`, `markets.md`, `tech.md`, `standards.md`, `MEMORY.md` itself) are edited directly via the Edit tool with no equivalent gate — a same-turn overwrite from two concurrent sessions is a live risk, not a hypothetical one (confirmed live 2026-08-14: the `.claude` main checkout showed 173 uncommitted changes from other active sessions at the moment this file was written).

**Why this wasn't fixed immediately:** Gabriel's ruling (2026-08-14) was to route this into the next `ora-setup-audit` run rather than patch CLAUDE.md ad hoc off a single external-repo comparison — the audit skill is the canonical place to scope and verify a change like this against the rest of the concurrency/hygiene surface (`dirty-tree-triage`, the ora-skills claim protocol, `memory-integrity-probe.py`) rather than adding a narrow carve-out in isolation.

**How to apply:** when the next `ora-setup-audit` (or a dedicated concurrency review) runs, evaluate whether `memory/` needs (a) inclusion in the CLAUDE.md single-writer list, (b) a lighter-weight script analogous to `append-event-log.py` for the append-style files, or (c) no change if the actual collision rate across 14+ concurrent sessions is negligible in practice. Close this reference once ruled on.

**Not adopted from the source artifact:** its own concurrency-safety mechanism (numbering discipline via inline bash `grep -oP` snippets, archival re-read-merge, structural-invariant counts) — worth knowing as a reference pattern, but ORA's existing script-based approach (`append-event-log.py`, `allocate-oi-id.py`) is already more robust than embedding unverified bash in a skill file. See [external-artifact disposition](event_log.md) for the full ruling.
