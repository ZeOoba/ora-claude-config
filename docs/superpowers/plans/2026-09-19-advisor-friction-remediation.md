# Advisor-session friction remediation — plan (2026-09-19)

Lane L5 investigation -> plan only. Nothing here has been executed. All three workstreams touch blast-radius surfaces (`settings.json`, `maintenance/` gate, `CLAUDE.md`/skills), so each needs its own confirmation before execution.

## Findings (evidence, all measured 2026-09-19)

### F1 — the preflight gate cannot tell an orphaned owner from a live one
- `maintenance/preflight-shared-checkout.py` defines "stale" ONLY by git: `_split_stale()` (L567) marks an owner stale when the file was *committed* at/after their last touch. There is no time-based or session-activity test.
- Consequence: an owner whose edit never got committed is "live" forever. Session `b6521d5d` touched `settings.json` at 2026-09-17 13:43 (touched-files.txt), its transcript `projects/C--Users-Owner/b6521d5d-*.jsonl` was last written 2026-09-17 13:47, nothing has been committed since — yet the gate reported it as a live owner two days later and returned CONTESTED (exit 1).
- The data needed already exists: `_scan_provenance()` reads a per-owner touch timestamp (currently used only for the stale test and never printed), and every session leaves a transcript whose mtime is a direct last-activity signal.
- Relevant prior art in the docstring (L59-69): `--accept-stale` cannot clear a zero-live-owner file; that limitation was known and left for a "hooks/** change tracked separately".

### F2 — the "uncommitted orphan edit" is a LIVE hook, not dormant WIP
- The 10-line hunk adds a `PostToolUse` / `Bash` hook running `ora-skills/tools/catch_up_main.py --hook` (timeout 360). Claude Code reads `settings.json` live, so it is firing today in every session.
- Script is real: ora-skills PR #62 (30f02af, 2026-09-17), 8.8 KB, committed one hour before the settings edit. The settings hunk is the second half of that same change and was never committed.
- Risk read of the script: LOW. `--hook` acts only on a Bash `gh pr merge` aimed at ZeOoba/ora-skills, always exits 0, only merges when on `main`, conflict-free (merge-tree dry run), preflight-clear, HEAD unmoved; never pushes/resets. Cost on every other Bash call = Python startup + payload parse.
- The `~/.claude` main checkout is on `feat/model-canary-probe-step25` (not main), with 564 dirty files across many sessions — committing there would land the hunk on an unrelated branch.

### F3 — advisor cost: my "trim CLAUDE.md and skills" premise is weaker than I stated
- Measured: the `claude -p --advisor` test run had ~213K tokens of context (advisor input 214,064; executor cache_creation 213,309). An interactive session's FIRST turn is ~92K (this session: 91,968; now 144K after 70 turns).
- Measured static contributors: CLAUDE.md 14.7 KB (~3.7K tokens) and already word-gated (WARN 1700 / FAIL 1850 by `doctrine-integrity-probe.py`); skill descriptions 130 SKILL.md = 75.5K chars (~19K tokens); SessionStart/hook context ~26K chars (~6.5K tokens); MCP instructions ~8K chars. Sum is roughly 30-35K tokens — about 15% of 213K.
- **CORRECTED 2026-09-19 (this bullet previously claimed "MCP = 197K = 94% of a headless call" — WRONG).** WS-C Phase 0 ran 5 one-word `claude -p --tools ""` calls: 210,592 tokens default; `--strict-mcp-config` 13,289; `--disable-slash-commands` 210,589; both 13,290; `--advisor opus` 211,927. The `--tools ""` flag ALSO removes ToolSearch, so MCP schemas cannot defer and load eagerly: those numbers are an artifact of my own measurement setup. Control run with default tools: 70,819 tokens (session 084e68ac independently measured 71,133). ORA scheduled tasks are not headless: Desktop-spawned sessions, first turn median ~107.7K, of which MCP is only ~10K (memory: `reference_headless_context_footprint.md`).
- Consequence: the "scope MCP servers on headless runs" lever does NOT apply (decision: do not scope the fleets; ~$3.70/wk saving with real break risk). "Trim CLAUDE.md/skills" remains a small lever (each a minority of ~71K-108K; CLAUDE.md already word-gated). The advisor consult cost is roughly the session's context (~71K default headless, ~92K+ interactive), not 214K.
- `ora-setup-audit` Thread 4 ("Token-bloat sources") already exists and gates CLAUDE.md word count — extend it; do NOT build a parallel skill (CLAUDE.md tie-break). I read its header and grep hits, not Thread 4 in full.

## Workstreams (recommended order: WS-B -> WS-A -> WS-C)

### WS-B — resolve the `catch_up_main.py` hook (hygiene; do first, ~30 min)
Decision needed from Gabriel: COMMIT (recommended) or DISCARD. Discarding kills a working, reviewed automation whose script is already merged.
1. Dry-run the hook: pipe a fake `gh pr merge --repo ZeOoba/ora-skills` PostToolUse payload and a non-matching one into `--hook`; confirm exit 0 and no-op on the non-match.
2. Claim: `python hooks/lib/claim_work.py claim hooks-override-auth "commit catch_up_main hook wiring" --paths settings.json`.
3. Isolated worktree off `main` (never the dirty `feat/model-canary-probe-step25` checkout); apply exactly the 10-line hunk; commit with the `isolated-commit` skill; PR to ZeOoba/ora-claude-config (private). Blast-radius PR -> real adversarial review, not a bot check (Merge gate).
4. After merge, reconcile the live checkout's working-tree hunk (it will duplicate main's) without touching other sessions' hunks — `git diff settings.json` must show only this hunk before any restore. STOP and ask if it shows more.
5. Release the claim; log to `event_log.md` via `append-event-log.py`.
Rollback: revert the PR; remove the hook block.

### WS-A — orphan/liveness reporting in `preflight-shared-checkout.py` (friction; ~half day)
Treat as gate code: adversarial REFUTE pass mandatory, reviewer >= implementer, pin model per dispatch. Work in a worktree; `maintenance/` is not `hooks/**` but is the single-writer gate.
1. Compute `last_activity` per owner = max(touch ts, `projects/*/<sid>.jsonl` mtime); tolerate missing transcript (fall back to touch ts; unknown stays LIVE — same fail-safe as today's `None`).
2. Print the age on every foreign-owner line: `settings.json [b6521d5d] last active 2d 0h ago`. This alone fixes the "manual search" cost.
3. Classify ORPHANED = every non-stale foreign owner has `last_activity` older than a threshold (default 12 h, `--orphan-hours N`; claims TTL is 2 h, sessions can idle overnight, so do not reuse 2 h). New verdict text `CONTESTED (ORPHANED owner)`. KEEP exit nonzero — CLAUDE.md defines any nonzero as STOP; an orphan label informs the human, it never auto-clears.
4. Add `--adopt-orphan PATH` that clears only ORPHANED-only files, prints the exact `git diff HEAD -- PATH` for review, and requires that diff to be non-empty and reviewed in-turn; never used by unattended callers (catch_up_main and other hooks must keep failing closed).
5. Tests (extend the existing preflight test suite — locate it first; do not assume path): old-transcript orphan, fresh-transcript live, missing-transcript (stays live), None-timestamp (stays live), mixed orphan+live (stays CONTESTED, live wins), junction/8.3 spellings (existing hostile-path fixtures), `--adopt-orphan` refuses when a live owner exists.
6. Replay today's case as an acceptance test: must print ~2d age + ORPHANED, exit nonzero.
Success: an operator reading one CONTESTED output can tell orphaned vs live without opening another tool. Rollback: revert; behavior returns to today's.

### WS-C — advisor / session-context cost (knowledge; measure BEFORE trimming)
STATUS 2026-09-19: Phase 0 DONE, but its headline result was a `--tools ""` ARTIFACT (see the CORRECTED bullet in F3). Phase 1 is CANCELLED: the MCP-scoping audit is moot (session 084e68ac already inventoried headless callers and measured the fleet; decision was not to scope). What survives: (a) an optional `ora-setup-audit` Thread 4 line reporting the always-loaded context budget from REAL first-turn transcripts (`python ~/.claude/maintenance/fleet-token-footprint.py`), not from `-p --tools ""`; (b) the lesson recorded in memory: never use `--tools ""` when measuring context. Original Phase 0 plan below kept for the record.
Phase 0 — attribution (~1 h, small subscription cost, needs go-ahead because each `claude -p` call spends limits):
- Run 4 headless one-shot calls (no advisor) from the scratchpad dir and record `usage`: (a) default; (b) `--strict-mcp-config` with an empty config; (c) `--disable-slash-commands`; (d) both. Diff cache_creation totals to attribute: MCP tool schemas vs skills listing vs everything else. Repeat (a) once WITH `--advisor opus` to confirm the advisor sees the same context as the executor.
- Also read this session's first-turn 92K against (a) to test the eager-MCP-schema hypothesis.
Phase 1 — only if Phase 0 shows a lever worth pulling:
- Extend `ora-setup-audit` Thread 4 with an "always-loaded context budget" table (system prompt / CLAUDE.md / skills listing / agents / MCP schemas+instructions / hook injections / memory index) plus an "advisor consult multiplier" line. Source of truth for the skill is the ora-skills repo (single-writer; run `git log -1` + `git status` first; bump version + changelog; mirror to `~/.claude/skills`).
- Candidate levers, unvalidated: duplicate skill trees (`skills/` and `skills/synced/<org>_<id>/` both carry e.g. county-parcel-screen), MCP servers not needed in `-p`/advisor sessions, SessionStart hook output size. CLAUDE.md itself is a poor target (~3.7K tokens, already gated).
Phase 2 — correct the record: update `reference_advisor_opt_in.md` (done in this session) so it no longer claims the setup's CLAUDE.md/skills explain the 214K.
Success: a measured per-component table and a yes/no on whether any trim is worth doing. Rollback: n/a (measurement only).

## Open questions for Gabriel
1. WS-B: commit (recommended) or discard the `catch_up_main` hook?
2. WS-C Phase 0: OK to spend ~4 small `claude -p` calls of subscription limits to attribute the 213K?
3. WS-A orphan threshold: default 12 h acceptable?

## Sequencing / dispatch (when executed)
WS-B inline (small, one hunk). WS-A via subagent-driven-development with a REFUTE reviewer (gate code). WS-C Phase 0 inline. Announce `Dispatch:` line and pin explicit models per dispatch; confidential/gate code never below Fable.
