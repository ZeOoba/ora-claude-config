# Automation Audit Rev 10 — Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Every subagent is pinned `model: sonnet` unless a task card says otherwise. The integrator (main session, Fable) reviews between tasks — reviewer ≥ implementer holds everywhere.

**Goal:** Execute every actionable verdict from ORA Automation Audit Revision 10 (plus the approved carried items) across four isolated surfaces — ora-skills repo, `~/.claude` local surface, plugin/marketplace registry, scheduled-task registry — without colliding with the 14 other active sessions or any single-writer protocol.

**Architecture:** Four phases. Phase 0 is inline preflight (claims + freshness re-verification — every Rev 10 measurement is hours old and findings decay). Phase 1 fans out two parallel Sonnet agents on disjoint surfaces (ALPHA: ora-skills worktree; BRAVO: marketplace CLI). Phase 2 is integration on `~/.claude` (mirror sync, settings pins, efficacy-task registration) — serialized because it touches guarded/shared files. Phase 3 is one careful agent on MEMORY.md (jointly-authored file, additive protocol). Phase 4 is verification, event-log, artifact outcome update, final report.

**Tech Stack:** git worktrees, `claude plugin marketplace` CLI, `create_scheduled_task` MCP (via register-scheduled-task skill), `append-event-log.py`, `claim_work.py`, Artifact republish.

## Global Constraints

- **Nothing here touches** the buy-box governor, DSCR/LTV constants, confidential-terms.json, oxfordra.net, or any external send. No Hard Invariant is in play. If any step unexpectedly reaches one of those surfaces, STOP and surface it.
- **Single-writer surfaces:** `~/ora-skills` (worktree only, never the shared checkout), the scheduled-task registries (supervised MCP tool only, check `~/.claude/maintenance/_state/registry-membership.log` first), `event_log.md` (append only via `python ~/.claude/maintenance/append-event-log.py`, one writer at a time), MEMORY.md (currently jointly authored by sessions `db37f7b8`/`f6b9d0b7` — re-read immediately before every write, additive edits only).
- **Foreign WIP is untouchable:** `~/ora-skills` has `M README.md` belonging to another session — never stage, commit, or revert it. The `~/.claude` main checkout has ~25 uncommitted foreign changes — never run repo-wide `git add`/`checkout`/`reset` there.
- **config-write-guard:** any Bash command whose text names `settings.json`, `hooks/**`, or `CLAUDE.md` with a write-shaped verb gets blocked. Reads go through Read/Grep/Glob tools (never gated). The one live settings.json edit in this plan (Task 7) is integrator-only, via the documented override token, citing Gabriel's approval of this plan.
- **Snapshot before edit:** before modifying ANY file outside a fresh worktree, copy it to the scratchpad (`C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner-OneDrive---Oxford-Capital-Partners\45d2365e-19e9-49c5-b25f-261bcb840fcf\scratchpad\backups\`). That copy is the rollback for non-git surfaces.
- **Evidence before claims:** every task ends with a verification command and its expected output. A task without its expected output is FAILED, not "probably fine."
- **Unattended-run rule does not apply:** Gabriel explicitly approved execution of all findings in-turn (2026-08-14). Items marked GABRIEL-ONLY below are excluded because they are physically his (store clicks, credentials), not because approval is missing.

## Decision Record (integrator's calls, made 2026-08-14 — veto at plan review, all reversible)

1. **R10-3 scope: remove all three zero-plugin marketplaces** (`karpathy-skills`, `obsidian-skills`, `anthropic-agent-skills`), including the `extraKnownMarketplaces` pins for the latter two — a pin without a registration is exactly the re-clone vector that produced the 1.8GB incident. Gated by the Task 0.4 resolution-independence check; rollback is one `claude plugin marketplace add` per repo.
2. **R10-2 mechanism: `.gitignore` + `git rm --cached summary.csv`, baselines stay tracked.** Minimal diff; `.gitignore` never untracks already-tracked files, so the two static baseline JSONs keep working from a fresh clone while the daily poll JSONs and the ever-growing summary.csv become local-only.
3. **Rev 9 skill-size recommendations: verbatim-move-only.** Any recommendation that requires paraphrasing or rewriting procedure prose is SKIPPED and reported, not attempted — mechanical agents must not compress ratified procedures.
4. **R10-11 MEMORY.md: index-line compression only.** No files move to `_archive`, no markdown link is ever dropped (that preserves `memory-integrity-probe` invariants and the documented 07-28 blockers). Target ≤ 20.5KB.
5. **GABRIEL-ONLY residuals** (staged to one click where possible, never executed): capex-budgeting store check (R10-12), Save-skill clicks for staged `.skill` packages, HUBSPOT_TOKEN/OI-019.

## Out of Scope (queued as follow-ups, NOT tasked here)

- Extending `repo_first_check.py`/`setup-self-audit.py` to detect repo↔`~/.claude/skills` mirror drift (root-cause class of R10-1). Blast-radius surface (`maintenance/` wired into guards) — needs its own TDD + adversarial REFUTE cycle per the Done Bar, not a mechanical fan-out task.
- `fleet-advisory-remediation` reverse-dark-task check (registry entry → `_archive_*` path), flagged in event_log 08-14. Same reason.
- The unexplained fleet-composition drift (Rev 8) — nothing mechanical to diff against; stays `ask`.

---

## Phase 0 — Preflight (INTEGRATOR, inline, no subagents)

### Task 0: Claims, freshness, and gates

**Files:** none modified. Scratchpad backups created.

- [ ] **Step 0.1: Check for competing claims and sessions.**

```bash
python C:/Users/Owner/.claude/hooks/lib/claim_work.py claim repo-housekeeping "Rev10 remediation: ora-setup-audit mirror sync + MEMORY.md compaction + marketplace dereg (Gabriel-approved plan 2026-08-14)" --paths "C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md" "C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md" "C:/Users/Owner/.claude/plugins/known_marketplaces.json"
```

Expected: claim acquired. **If exit 3 (another session holds it):** apply the polling-claim loop — wait 2–4 min, retry twice. Still held → report the holder and STOP Phases 2–3 (Phase 1 may proceed; it touches neither path).

- [ ] **Step 0.2: Re-verify the four ground truths this plan depends on** (Rev 10's reads are hours old):

```bash
md5sum C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md
```
Expected: `676b56aaac9d2aec3bb338077afcefbd` (repo) vs `7c4ee88b57e2a4d9feaccf76c3e274d6` (mirror). If they now MATCH, mark Task 6 `no_change_needed` and continue.

```bash
cd C:/Users/Owner/ora-skills && git log --oneline -1 && git status --porcelain
```
Expected: HEAD `2bc0727` (or newer — if newer, read the new commits before proceeding); dirty set contains ONLY `M README.md`, `M acquisition-underwriting-eval-harness/runs/summary.csv`, `?? acquisition-underwriting-eval-harness/runs/2026-08-14T*.json` (possibly a newer date), `?? .worktrees/`. Any OTHER dirty path → foreign WIP has expanded; note it, touch nothing outside the worktree.

Read (Read tool, never Bash) `C:\Users\Owner\.claude\plugins\known_marketplaces.json` — expected 5 entries — and `C:\Users\Owner\.claude\plugins\installed_plugins.json` — expected plugins from only `superpowers-marketplace` and `claude-plugins-official`. If a plugin now references one of the three removal targets, EXCLUDE that marketplace from Task 4 and report.

```bash
wc -c "C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md"
```
Expected: ~21,811 bytes (jointly authored — may have moved; record the live number as Task 9's baseline).

- [ ] **Step 0.3: Snapshot rollback copies to scratchpad.**

```bash
mkdir -p "C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-OneDrive---Oxford-Capital-Partners/45d2365e-19e9-49c5-b25f-261bcb840fcf/scratchpad/backups" && cp "C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md" "C:/Users/Owner/.claude/plugins/known_marketplaces.json" "C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md" "C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-OneDrive---Oxford-Capital-Partners/45d2365e-19e9-49c5-b25f-261bcb840fcf/scratchpad/backups/"
```
Expected: 3 files copied, verified with `ls`.

- [ ] **Step 0.4: Resolution-independence gate for anthropic-agent-skills + obsidian-skills** (decides Task 4's scope). Using Grep tool (not Bash) search `C:\Users\Owner\.claude` for the string `anthropic-agent-skills` in `*.json`, excluding `plugins/known_marketplaces.json` and `settings.json` (whose entries we already know). Also Grep the Desktop log if present (`%APPDATA%\Claude\logs\main.log`, pattern `marketplaces\\anthropic-agent-skills`) for load-path references.

Expected: zero live references outside the two known registration files. The `anthropic-skills:` prefix in session skill listings is the Cowork/store namespace, NOT this marketplace — `installed_plugins.json` is the CC authority and lists nothing from it. **If any live reference is found:** remove `karpathy-skills` only in Task 4; leave the other two; report the reference verbatim.

---

## Phase 1 — Parallel fan-out (2 Sonnet subagents, disjoint surfaces)

Dispatch: `subagent-driven-development` · both agents `model: sonnet` · run concurrently — ALPHA touches only a fresh ora-skills worktree; BRAVO touches only `plugins/` via the CLI. Zero shared files.

### Task 1 (ALPHA): Stop the eval-harness dirtying ora-skills daily (R10-2)

**Files:**
- Create: `~/ora-skills/.worktrees/rev10/` (worktree, branch `rev10-remediation`)
- Create: `.gitignore` entries in worktree root
- Modify: `acquisition-underwriting-eval-harness/SKILL.md` (changelog note)
- Untrack: `acquisition-underwriting-eval-harness/runs/summary.csv`

**Interfaces:** Produces branch `rev10-remediation` with 1+ commits; Task 3 continues on the same branch; Task 5 merges it.

- [ ] **Step 1.1: Create the worktree** (never work in the shared checkout):

```bash
cd C:/Users/Owner/ora-skills && git worktree add .worktrees/rev10 -b rev10-remediation origin/main
```
Expected: `Preparing worktree (new branch 'rev10-remediation')`.

- [ ] **Step 1.2: Read before deciding.** Read `acquisition-underwriting-eval-harness/SKILL.md` (worktree copy) and `C:\Users\Owner\.claude\scheduled-tasks\ora-acquisition-underwriting-eval-harness\SKILL.md` (read-only — the task spec, NOT edited by this task). Confirm: the harness writes `runs/<timestamp>_*.json` + appends `runs/summary.csv`, and reads its baseline(s) by explicit filename. If the baseline is read via a glob over ALL of `runs/` (not explicit filenames), STOP this task and report — the ignore approach would still work, but confirm no logic depends on committed poll files.

- [ ] **Step 1.3: Add the ignore rules.** Append to the worktree's root `.gitignore`:

```gitignore
# eval-harness daily poll output — local-only ledger; scheduled task writes here
# every fire (Rev 10 finding R10-2). Baseline JSONs committed 2026-08-14 remain
# tracked (gitignore never untracks); future baselines need `git add -f`.
acquisition-underwriting-eval-harness/runs/*
!acquisition-underwriting-eval-harness/runs/*baseline*.json
```

- [ ] **Step 1.4: Untrack the daily-modified ledger** (in the worktree):

```bash
cd C:/Users/Owner/ora-skills/.worktrees/rev10 && git rm --cached acquisition-underwriting-eval-harness/runs/summary.csv
```
Expected: `rm 'acquisition-underwriting-eval-harness/runs/summary.csv'`. NOTE: this removes it from the branch's index only; the live file in the MAIN checkout stays on disk and keeps accumulating — correct.

- [ ] **Step 1.5: Changelog the harness SKILL.md.** Append to its Changelog section (create the entry matching the file's existing changelog style):

```markdown
- **v1.1 (2026-08-14):** `runs/` is now git-ignored except `*baseline*.json` (Automation Audit R10-2 — the daily scheduled poll was dirtying the single-writer checkout on every fire and would have committed ~365 JSONs/yr). `summary.csv` is a local-only ledger from this date; new baselines require `git add -f`.
```

- [ ] **Step 1.6: Verify the ignore works:**

```bash
cd C:/Users/Owner/ora-skills/.worktrees/rev10 && touch acquisition-underwriting-eval-harness/runs/2099-01-01T000000Z_test-poll.json && git status --porcelain acquisition-underwriting-eval-harness/runs/ && rm acquisition-underwriting-eval-harness/runs/2099-01-01T000000Z_test-poll.json
```
Expected: status shows the summary.csv deletion staged (`D`), does NOT show the test JSON as `??`. Baselines still listed by `git ls-files acquisition-underwriting-eval-harness/runs/` (2 files).

- [ ] **Step 1.7: Commit:**

```bash
git add .gitignore acquisition-underwriting-eval-harness/SKILL.md && git commit -m "fix(eval-harness): gitignore runs/ poll output, untrack summary.csv (audit R10-2)"
```

### Task 2 (ALPHA): Backfill insurance-renewal-review into the repo (Rev 10 flagged: store-only, no source)

**Files:**
- Create (if source found): `insurance-renewal-review/SKILL.md` (+ any reference files) in the worktree

- [ ] **Step 2.1: Hunt for a local cache copy.** Glob these, in order, stopping at the first hit containing a full SKILL.md with frontmatter `name: insurance-renewal-review`:
  - `C:\Users\Owner\.claude\**\insurance-renewal-review\**`
  - `C:\Users\Owner\AppData\Roaming\Claude\**\insurance-renewal-review\**\SKILL.md`
  - `C:\Users\Owner\OneDrive - Oxford Capital Partners\**\insurance-renewal-review\**\SKILL.md`
  - Grep fallback: search `C:\Users\Owner\AppData\Roaming\Claude` for the literal string `insurance renewal review — OCR scanned Erie/Selective` in any file.

- [ ] **Step 2.2 (if found): Copy into the worktree, verbatim, with provenance:**

Copy the whole skill directory to `C:/Users/Owner/ora-skills/.worktrees/rev10/insurance-renewal-review/`. Do not edit the skill body. Commit:

```bash
git add insurance-renewal-review/ && git commit -m "chore(insurance-renewal-review): backfill v1.0 repo copy from local cache (audit Rev 10 — was store-only, no rebuildable source)"
```

- [ ] **Step 2.3 (if NOT found):** Create nothing. Report `BLOCKED-no-local-source` with the exact paths searched. (Integrator adds a GABRIEL-ONLY line: export it from the Cowork surface.)

### Task 3 (ALPHA): Rev 9 top-skill size recommendations — verbatim-move-only

**Files:**
- Modify (candidates, per Rev 9's actual text): `register-scheduled-task/SKILL.md`, `daily-brief/SKILL.md`, `package-and-stage-skill/SKILL.md` in the worktree; possibly create `references/` files under those dirs.

- [ ] **Step 3.1: Read the authoritative recommendations.** Read `C:\Users\Owner\.claude\artifacts\ora-automation-audit.html`, section headed **"Skill usage ranking — Revision 9"** and the recommendation rows/callouts that follow it for `register-scheduled-task`, `daily-brief`, `package-and-stage-skill`. Those recommendations — not this plan — define the edits. This plan defines the HARD LIMITS below.

- [ ] **Step 3.2: Apply, under these limits, one skill per commit:**
  - Allowed: moving text verbatim from SKILL.md into a new `references/<topic>.md` with a one-line pointer left behind; moving changelog tails out of frontmatter descriptions into the body; deleting text ONLY if Rev 9 identifies it as duplicated verbatim elsewhere in the same skill.
  - Forbidden: paraphrasing, summarizing, reordering procedure steps, touching frontmatter `name:`, or any edit to a section CLAUDE.md's tie-breaks reference by behavior (e.g. register-scheduled-task's dual-fleet/RETIRE-order doctrine may move to a reference file intact, never shrink).
  - Each edited skill gets a changelog line: `- **vX.Y (2026-08-14): size refactor per Automation Audit Rev 9 — content moved verbatim to references/, no procedural change.`
  - If a Rev 9 recommendation requires anything on the Forbidden list → SKIP it, record `skipped-editorial: <skill> — <one line why>`.

- [ ] **Step 3.3: Verify no content loss per skill:** word count of (new SKILL.md + its new references files) must be ≥ 97% of the old SKILL.md word count (allows only pointer-line dedup). Record before/after counts.

- [ ] **Step 3.4: Commit per skill:** `refactor(<skill>): move <what> to references/ per audit Rev 9 (verbatim, no procedural change)`.

### Task 4 (BRAVO): Deregister the zero-plugin marketplaces (R10-3)

**Files:** `~/.claude/plugins/known_marketplaces.json` + `~/.claude/plugins/marketplaces/{karpathy-skills,obsidian-skills,anthropic-agent-skills}` — all via the CLI, never hand-edited.

**Interfaces:** Consumes Task 0.4's gate verdict (full-scope vs karpathy-only). Produces the end-state Task 8's efficacy check asserts.

- [ ] **Step 4.1: Confirm current registration** (evidence for the report):

```bash
claude plugin marketplace list
```
Expected: 5 marketplaces including the 3 targets.

- [ ] **Step 4.2: Remove, one at a time, verifying after each:**

```bash
claude plugin marketplace remove karpathy-skills
```

```bash
claude plugin marketplace remove obsidian-skills
```

```bash
claude plugin marketplace remove anthropic-agent-skills
```
(Skip the latter two if Task 0.4 said karpathy-only.) After each: `claude plugin marketplace list` no longer shows it, AND the directory `C:\Users\Owner\.claude\plugins\marketplaces\<name>` is gone (`ls`). If the CLI removes the registry entry but leaves the directory, remove the directory is FORBIDDEN under invariant 6 — instead move it: `mv C:/Users/Owner/.claude/plugins/marketplaces/<name> C:/Users/Owner/.claude/_archive/2026-08-14_marketplace-dereg/<name>` and note it.

- [ ] **Step 4.3: Check whether the CLI also cleaned the settings pins.** Read (Read tool) `C:\Users\Owner\.claude\settings.json` → `extraKnownMarketplaces`. Expected end-state: only `claude-plugins-official` remains. **If `anthropic-agent-skills`/`obsidian-skills` pins persist: do NOT edit settings.json yourself** — report `pins-remain` to the integrator (Task 7 handles it, guarded).

- [ ] **Step 4.4: Verify installed plugins untouched:**

```bash
claude plugin list
```
Expected: same 5 entries as Task 0.2 (superpowers, claude-md-management, code-review, commit-commands, pr-review-toolkit), unchanged enabled/disabled states.

**Rollback:** `claude plugin marketplace add forrestchang/andrej-karpathy-skills` / `kepano/obsidian-skills` / `anthropics/skills` — public clones, nothing unique lost.

---

## Phase 2 — Integration (INTEGRATOR inline, serialized; then one Sonnet agent)

### Task 5 (INTEGRATOR): Land the ora-skills branch

- [ ] **Step 5.1: Review ALPHA's branch** — `git log -p origin/main..rev10-remediation` from the main checkout. Check: no README.md hunk, no foreign file swept, Task 3 diffs are pure moves (spot-check two moved blocks are byte-identical).
- [ ] **Step 5.2: Re-check single-writer immediately before merging** (claims/HEAD can move in minutes):

```bash
cd C:/Users/Owner/ora-skills && git fetch origin && git log --oneline origin/main -1 && git status --porcelain
```
If origin/main moved past `2bc0727`: rebase the branch in the WORKTREE (`cd .worktrees/rev10 && git rebase origin/main`), re-run Task 1.6's verify, then proceed.
- [ ] **Step 5.3: Merge + push:**

```bash
cd C:/Users/Owner/ora-skills && git merge --ff-only rev10-remediation && git push origin main
```
(The shared checkout is on main with only foreign unstaged WIP; `merge --ff-only` moves HEAD without touching the working tree's foreign files. If ff fails, push the branch and merge via `git push origin rev10-remediation:main` after re-verifying status.)
- [ ] **Step 5.4: Clean up:** `git worktree remove .worktrees/rev10`. Record final sha(s).
- [ ] **Step 5.5: Post-merge dirt check:** `git status --porcelain` shows ONLY `M README.md` (+ any new ignored-but-present runs files as untracked NOTHING — they're ignored now). Expected: summary.csv no longer appears as `M`. **This is R10-2's actual success test.**

### Task 6 (INTEGRATOR): Sync the ora-setup-audit mirror (R10-1)

- [ ] **Step 6.1:** Copy canonical over mirror:

```bash
cp C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md && md5sum C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md
```
Expected: both md5 `676b56aaac9d2aec3bb338077afcefbd` (or both equal to the repo's current hash if the repo copy moved past v1.3 — equality is the test, not the literal hash).
- [ ] **Step 6.2:** Commit just this file in the `~/.claude` repo if a clean isolated commit is possible (dirty-tree-triage's `commit_isolated_replacement()` path); if the shared-tree state makes that contentious, leave it uncommitted and record that explicitly in the Task 11 event-log entry — mirror CONTENT is what the harness loads; the commit is hygiene, not function.

### Task 7 (INTEGRATOR): Settings pins — only if BRAVO reported `pins-remain`

- [ ] **Step 7.1:** Mint the override token exactly as config-write-guard's error message specifies: write `C:\Users\Owner\.claude\hooks\sessions\45d2365e-19e9-49c5-b25f-261bcb840fcf\overrides\allow-config-write` with content `scope: config-write` / `session: 45d2365e-19e9-49c5-b25f-261bcb840fcf` / `reason: Gabriel-approved Rev 10 remediation plan (this session, 2026-08-14) — remove extraKnownMarketplaces pins for deregistered marketplaces`.
- [ ] **Step 7.2:** Edit `settings.json` `extraKnownMarketplaces` with the Edit tool: delete the `anthropic-agent-skills` and `obsidian-skills` objects, keep `claude-plugins-official`. Validate: read back, confirm valid JSON via a scratchpad script (`python <scratchpad>/validate.py` that json.loads the file — do not name settings.json in a Bash command line; pass the path from inside the script file).
- [ ] **Step 7.3:** Delete the override token file (single-purpose, don't leave a 60-min write window open).

### Task 8 (CHARLIE, Sonnet): Register the one-time efficacy check (R10-4 + R10-3 watch)

**Interfaces:** Consumes end-states from Tasks 4/5/6. Route through the **register-scheduled-task skill** (CLAUDE.md tie-break: all registration goes through it; supervised `create_scheduled_task` only, CC fleet).

- [ ] **Step 8.1:** Pre-check `~/.claude/maintenance/_state/registry-membership.log` — latest timestamp must be explainable (this plan's own activity or older). Foreign in-flight activity → wait per polling-claim loop.
- [ ] **Step 8.2:** Register one-time CC task `ora-rev10-remediation-efficacy-check`, fireAt **2026-08-20 14:30 ET**, with a SKILL.md instructing exactly four asserts and a report-only output (memory note `reference_rev10_efficacy_2026-08-20.md` + loud flag on any FAIL; no email):
  1. CC registry shows `ora-psa-drift-watch` `lastRunAt` ≥ 2026-08-19 (its first-ever fire; retime efficacy — R10-4).
  2. `claude plugin marketplace list` still lacks the removed marketplaces AND `plugins/marketplaces/` contains no re-cloned directory for them (re-clone watch — the failure mode that reversed Rev 7's fix within hours).
  3. `cd ~/ora-skills && git status --porcelain acquisition-underwriting-eval-harness/runs/` is empty despite the eval task having fired since 08-19 (R10-2 held under live fire).
  4. `md5sum` equality of `~/ora-skills/ora-setup-audit/SKILL.md` and `~/.claude/skills/ora-setup-audit/SKILL.md` (mirror still synced).
- [ ] **Step 8.3:** Run the skill's own registration QC gate; verify the task appears in `list_scheduled_tasks` output.

### Task 8b (ALPHA or INTEGRATOR): Package edited store-installed skills

- [ ] **Step 8b.1:** For each skill Task 3 edited that is store-installed (`register-scheduled-task`, `daily-brief`, `package-and-stage-skill`) **plus `lease-addendum`** (built 08-13, never yet installed on Cowork — Rev 9 in-flight item): follow the **package-and-stage-skill** skill end-to-end through its STAGING step (`tools/package_skills.py`, never Compress-Archive). Produces `.skill` files + PENDING_REIMPORT entries. **Stage copies of all four packages to the fixed handoff folder** `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\outputs\2026-08-14_rev10-skill-packages\` (create it) — Gabriel's Cowork prompt reads from exactly that path.
- [ ] **Step 8b.2:** GABRIEL-ONLY: the Save-skill clicks. List every staged package path in the final report.

---

## Phase 3 — Memory (DELTA, one Sonnet agent, serialized after Phases 1–2)

### Task 9 (DELTA): MEMORY.md back under the WARN gate (R10-11) + Rev 10 outcome updates

**Files:**
- Modify: `memory/MEMORY.md` (compress), `memory/project_automation_audit_rev10_2026-08-14.md` (append outcomes)

**Hard rules:** never delete a markdown link; never move a file; compress prose around links only; re-read MEMORY.md immediately before writing (jointly authored); two reads ≥60s apart must be byte-identical before you start (else wait and retry, max 3 cycles, then report `contended` and stop).

- [ ] **Step 9.1:** Baseline: `wc -c` MEMORY.md (expect ~21,811B; use the live number).
- [ ] **Step 9.2:** Compress, targeting ≤ 20,500B, in this priority order (all links preserved verbatim):
  1. The `CLOSED (detail in each file)` line: strip every parenthetical/clause after each link, keeping `[title](file) · [title](file) …` — the files self-describe.
  2. Entries marked RESOLVED/FIXED/MERGED/FULLY CLOSED (e.g. Rev 8, deal-join redesign, parseLeases, portfolio.json regression, annual-debt-service): reduce to `[Title](file.md) — <status word> <date>` single clause.
  3. Superseded entries (Intelligence Platform Master Plan): `[Title](file.md) — SUPERSEDED`.
  4. Do NOT touch: ⛔/⚠️ entries, OPEN/BLOCKED block, PENDING block, the header policy lines, the size-gate footnote, or anything under "Rules & governance".
- [ ] **Step 9.3:** Verify: `wc -c` ≤ 20,500; every `.md` filename present in the pre-edit copy (scratchpad backup) is still present post-edit — compare with a scratchpad script diffing the two files' extracted link targets; expected: zero links lost.
- [ ] **Step 9.4:** Run `python C:/Users/Owner/.claude/maintenance/memory-integrity-probe.py`; expected: orphan/missing counts NO WORSE than the pre-edit run (run it before editing too, for the baseline — known pre-existing findings exist).
- [ ] **Step 9.5:** Append an **Outcomes (2026-08-14 remediation)** section to `project_automation_audit_rev10_2026-08-14.md`: one line per finding — R10-1 fixed (mirror md5 …), R10-2 fixed (sha …), R10-3 fixed/partial (which marketplaces), R10-4 fixed (task id), R10-11 fixed (size before→after), R10-12 still GABRIEL-ONLY, insurance backfill done/BLOCKED, Rev 9 recs applied/skipped list, staged .skill packages awaiting clicks.

---

## Phase 4 — Verification & closeout (INTEGRATOR inline)

### Task 10: Verification battery

- [ ] Mirror: `md5sum` both ora-setup-audit copies → equal.
- [ ] ora-skills: `git status --porcelain` → only foreign `M README.md`; `git log --oneline -3` shows the remediation commits on main.
- [ ] Marketplaces: `claude plugin marketplace list` → 2 (or 4 if Task 0.4 forced karpathy-only); `ls C:/Users/Owner/.claude/plugins/marketplaces/` matches.
- [ ] Registry: `list_scheduled_tasks` (or `python C:/Users/Owner/.claude/maintenance/fleet-status.py`) shows `ora-rev10-remediation-efficacy-check` pending one-time; total CC count = 33 (32 + 1).
- [ ] MEMORY.md ≤ 20,500B; probe no-worse.
- [ ] settings.json (Read tool): `extraKnownMarketplaces` = 1 entry (if Task 7 ran); `enabledPlugins` untouched at 5 keys.
- [ ] Release the Task 0.1 claim: `python C:/Users/Owner/.claude/hooks/lib/claim_work.py release repo-housekeeping`.

### Task 11: Event log + artifact + report

- [ ] **Step 11.1:** One event-log append via `python C:/Users/Owner/.claude/maintenance/append-event-log.py` summarizing: Rev 10 remediation executed per Gabriel-approved plan; per-finding outcomes with shas/task-ids; anything left uncommitted (Task 6.2) or blocked; efficacy check registered for 08-20.
- [ ] **Step 11.2:** Update `C:\Users\Owner\.claude\artifacts\ora-automation-audit.html`: add an outcome chip per R10 row in the verdict table (`fixed` / `skipped` / `no_change_needed` styling reuses `.chip` classes), add a short "Revision 10 — same-day remediation" callout above the verdict table naming this plan file, republish via Artifact with `url: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7`.
- [ ] **Step 11.3:** Final report to Gabriel: done (with evidence), skipped-editorial list, GABRIEL-ONLY queue (capex store check · Save-skill clicks for each staged package · HUBSPOT_TOKEN), and the 08-20 efficacy check as the standing verification.

## Failure/rollback appendix

- **Any git step in ora-skills:** `git revert <sha>` on main; worktree is disposable.
- **Marketplace removal:** re-add commands in Task 4. If a removal breaks skill resolution (detected: a Task-10 `ListSkills`/session listing missing a previously-listed skill), re-add immediately and report.
- **Mirror sync:** restore scratchpad backup copy.
- **MEMORY.md:** restore scratchpad backup, report `contended`.
- **settings.json:** the Edit tool's old_string is recoverable from the scratchpad `validate.py` read; re-insert the deleted pin objects verbatim.
- **Efficacy task mis-registered:** `delete_scheduled_task` FIRST, then archive the folder (CC RETIRE order — registry-only delete leaves the folder; guard.ps1 resurrects archived-but-registered files).
