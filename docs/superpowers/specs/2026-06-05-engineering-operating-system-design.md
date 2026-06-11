# ORA Engineering Operating System — Design Spec

**Date:** 2026-06-05
**Owner:** Gabriel Goldberg (VP Acquisitions, ORA)
**Status:** Design — approved foundation (Approach A + one router hook), pending final spec review
**Author surface:** Claude Code

---

## 1. Goal

Turn ORA's existing inventory — ~70 skills, ~15 MCP connectors, ~10 sub-agents, 9 custom slash commands, the superpowers process plugin — from *a library you must remember to use* into *a pipeline that routes itself*: every complex session flows through the right skills/agents/connectors in the right order, so code is high-quality, minimally buggy, efficient, well-designed, and organized to a standard a world-class engineer could not fault.

**Success criteria (how we know it worked):**
- Any coding request is classified into a lane and run through that lane's chain without ad-hoc improvisation.
- No "done" claim is ever made without verification evidence (command output).
- No confidential term ever crosses an egress surface — including the *review* and *research* steps.
- The system is honest about its own enforcement: nothing claims to be more automatic than the mechanism delivers.
- The system *learns*: when a lane misses, the doctrine or command is updated (Calibrate loop).

### 1.1 Non-negotiable guardrails (Gabriel, 2026-06-05)

These override every lane, gate, and convenience. Any lane that would cross one **stops and asks**:
1. **Never touch oxfordra.net** — repos `website-canonical` / `oxford-site` and the live Netlify site. No edit, build, or deploy without explicit **per-action** permission. (Broader than the prior "never deploy" rule: also no edits.)
2. **Never modify the Oxford Capital non-Claude OneDrive business folders** — the deal/financial/ops folders under `OneDrive - Oxford Capital Partners (1)/`. **Reading for analysis is fine; any write/move/delete requires explicit permission.** The Claude-system paths (Cowork OS, Claude_Workspace, the brain repo, `~/.claude`) are the working surface; the business folders are not.
3. **Never send an email or move/transfer money** without explicit permission — drafts only; the human sends.

These join the always-hard confidentiality guard as the system's hard stops.

---

## 2. Mechanism reality (the honest foundation)

This drove every design choice. Three verified facts about this environment:

1. **The process skills do not auto-fire.** `settings.json → skillOverrides` sets `superpowers:systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `verification-before-completion`, `receiving-code-review` to `user-invocable-only`, and `andrej-karpathy-skills:karpathy-guidelines` to `off`. Gabriel deliberately prefers **explicit, deliberate invocation** over noisy auto-triggering. → The lanes/commands must invoke these skills *explicitly*.
2. **A skill cannot programmatically drive another skill.** A skill/command is instruction text loaded into context; it does not mechanically call other skills. "The pipeline runs itself" is therefore true only to the degree that (a) a command body sequences the steps and I follow it, and (b) a hook injects routing. The one mechanism that gives *true* deterministic multi-agent ordering is `Workflow` (opt-in, heavier).
3. **`superpowers:requesting-code-review` is already local & private** — it dispatches a `general-purpose` sub-agent inside the session, never the cloud. The *only* cloud-egress review path is the separate `/code-review ultra` skill.

**Enforcement model chosen: Approach A + one router hook.**
- **Doctrine (CLAUDE.md)** = always-loaded law. Soft (I comply because I read it every session).
- **Commands** = explicit lane entry points that sequence the real skills.
- **One `UserPromptSubmit` hook** = the only auto-trigger we add — **non-blocking**: it classifies the request and *suggests* the lane + command. It never blocks (respects the low-friction preference). A stricter blocking PreToolUse variant is documented as a future opt-in, not built now.

---

## 3. Architecture — three artifacts (control plane), everything else orchestrated

```
CONTROL PLANE (what we build/modify)
  1. CLAUDE.md "Engineering OS" block ....... the law (triage, lanes, quality bar, release table, rules)
  2. Slash commands ......................... the lanes
        upgrade: /plan /build /debug /refactor
        add:     /research /ship
        keep:    /ram /handoff /solo /heavy /cleardisk  (resource lifecycle — unchanged)
  3. One UserPromptSubmit hook .............. the router (non-blocking lane suggestion)

EXECUTION PLANE (existing, invoked by the lanes)
  PROCESS   superpowers: brainstorming · writing-plans · TDD · systematic-debugging ·
            verification-before-completion · requesting/receiving-code-review ·
            using-git-worktrees · subagent-driven-development · finishing-a-development-branch
  IMPLEMENT frontend-design · mcp-builder · skill-creator · xlsx/docx/pdf/pptx · ORA deal & ops skills
  QUALITY   requesting-code-review (LOCAL) · /code-review ultra (cloud, gated) · QC sub-agents
            (site-qc-reviewer, underwriting-checker, rent-roll-qc) · repo gates · /verify · /review
  SCALE     dispatching-parallel-agents · Workflow (opt-in) · Explore agent  (RAM-aware)
  KNOWLEDGE memory + MEMORY.md · event_log.md · conversation-archival → Notion

DATA & DOCS PLANE
  Excel (source of truth) · Notion · HubSpot · M365 · FRED · context7 (live lib docs) ·
  Desktop Commander / Windows-MCP · Claude-in-Chrome / Preview
```

**Explicitly NOT built:** a new "conductor skill." It would duplicate the commands and collide with the superpowers skills' triggers. The commands + doctrine + hook *are* the conductor.

---

## 4. The phase spine (the lifecycle a lane walks through)

```
0  TRIAGE        classify → clarify-if-vague → decompose-if-compound → state lane + why → veto
0.5 CHEAPEST     "should we even? what's the smallest correct change?" (YAGNI / Karpathy gate)
1  DESIGN        brainstorming → /plan (writing-plans)        [features/refactors]
2  ISOLATE       using-git-worktrees                          [multi-file/risky]
3  BUILD         TDD always; subagent-driven-development for large plans; pull IMPLEMENT skills + context7
4  DEBUG         systematic-debugging                         [when stuck/broken]
5  VERIFY        verification-before-completion + repo gate
6  REVIEW        requesting-code-review (LOCAL) + QC sub-agent; /code-review ultra only if non-confidential + opt-in
7  LAND          finishing-a-development-branch
8  PERSIST       memory / event_log / conversation-archival
9  CALIBRATE     on any miss → append event_log + update the doctrine/command that failed
```

Phases 0, 0.5, 5, 9 are the additions that most move quality: deliberate routing, a YAGNI gate against over-engineering, evidence-before-done, and a learning loop.

---

## 5. Triage — the router

**Preamble (runs before lane selection):**
1. **Clarify if vague** — if intent is ambiguous, ask rather than guess a lane.
2. **Decompose if compound** — "fix X, add Y, ship Z" splits into ordered lanes, not one.
3. **State lane + one-line why**, then **let Gabriel veto** for anything above L1.

**Ladder (first match wins, with dominant-intent tie-break, not pure phrasing):**
| # | Question | Lane |
|---|----------|------|
| 1 | Not code? investigate/compare vs do | L5 Research / L6 Domain |
| 2 | Trivial **and** passes the blast-radius test? | L1 Fast |
| 3 | Something broken? | L2 Bug |
| 4 | New behavior? | L3 Feature |
| 5 | Restructure only (no behavior change)? | L4 Refactor |
| 6 | Ship/deploy? | L7 Release |

**Always-on wrappers (honest about enforcement strength):**
- **Confidentiality guard** — *hard-enforced* (PreToolUse `confidentiality-guard.py`, fail-closed). Reads `confidential-terms.json`.
- **Resource rule** — *soft*: `/ram` to gauge; reclaim via `/solo` (move this session, keep others, ~130 MB), `/handoff` (move + quit GUI, ~1.3 GB), `/heavy` (fresh lean CLI), `/cleardisk` (~2.5 GB disk). Run heavy multi-agent work from a lean CLI.
- **Tool hierarchy** — *soft*: dedicated MCP → Chrome → computer-use.
- **Hard guardrails (§1.1) + confirm-before-irreversible** — never touch oxfordra.net, write to the Oxford Capital business OneDrive folders, deploy, send email, move money, or modify financial models without explicit confirm. Confidentiality + sensitive-file paths are hook-enforced; the rest are stop-and-ask.

---

## 6. The seven lanes (final chains, with all review fixes folded in)

### L1 — Fast (command: none; doctrine-governed)
*Trivial, reversible, single-file.*
- **Blast-radius test (objective, replaces "trivial" self-assessment):** a change is **disqualified from L1** if the path matches any protected glob — `hooks/**`, `*.env*`, `*credentials*`, `confidential-terms.json`, `settings.json`, CSP/headers, or files holding financial constants/governor values (DSCR `1.25`, LTV `40`). Disqualified → L2/L3/L4.
- Even L1 runs the **cheapest relevant verification** (typecheck/lint/the one test). "No plan" ≠ "no verify."
- Aligns with TDD's config-file exception (config edits need no test-first).

### L2 — Bug (command: `/debug`, upgraded)
- Invoke **`superpowers:systematic-debugging`** (root-cause, no guessing).
- **TDD reproducing test first** (failing test that captures the bug) before any fix.
- **Not-reproducible branch:** if it doesn't reproduce, instrument/add logging first (defense-in-depth) — do not guess-fix.
- **Escalation:** if root cause reveals a multi-file/behavioral fix → escalate to L3/L4.
- After fix: **run the full suite** (not just the new test) to catch collateral breakage.
- **Review trigger (objective):** review if it touched a protected path, >~40 lines, or a public API.
- *Keeps* the existing `/debug` ORA failure-mode checklist (Netlify→CLI, MCP auth, hook blocks, cwd, skill frontmatter).

### L3 — Feature (command: `/build`, upgraded; split by size)
- **L3-small** (one component, < ~1 day): inline light brainstorm → `/plan` → TDD → local review → land.
- **L3-large:** `brainstorming` → `/plan` (writing-plans) → `using-git-worktrees` → **`subagent-driven-development`** (sequential implementer + 2-stage spec/quality review per task — the skill forbids parallel implementers) under **TDD** → `verification-before-completion` → `requesting-code-review` (LOCAL) → `receiving-code-review` → `finishing-a-development-branch` → PERSIST.
- Pull **IMPLEMENT** skills as needed (frontend-design, mcp-builder, xlsx…) and **context7** before any library/API work.
- **Confidentiality gates the review tool** (see §8). **RAM:** subagent-driven is sequential; for any *parallel* fan-out, gauge `/ram` and prefer a lean CLI.
- *Keeps* `/build`'s ORA rules: read-before-write, exact output path + naming convention, no placeholder/extra features, change-log.

### L4 — Refactor (command: `/refactor`, upgraded)
- **Coverage precondition:** if the target's test coverage is low, first decide (cheap) whether characterization-test cost is worth it; if not, reroute as L3 with explicit acknowledgment.
- **Characterization tests first** (TDD), then `using-git-worktrees`, then `executing-plans`/inline, then `verification-before-completion`, then local review.
- **Honest guarantee:** behavior preserved *within the captured characterization suite + named invariants*. **Not guaranteed:** performance, memory, timing, error-text. (Replaces the false "provably identical.")
- *Keeps* `/refactor`'s strict rules: one concern, no speculative changes, state what changed and what did **not**.

### L5 — Research (command: `/research`, NEW)
- `deep-research` skill, or `firecrawl` + `context7`; **`Workflow` only on explicit opt-in** (not a silent default).
- **Confidential-term scrub:** strip any `confidential-terms.json` term (deal names, addresses) from every external query; keep ORA-internal research on internal sources (Excel/Notion/memory) only.
- **Adversarial verify** via the deep-research harness's own verify stage; synthesize → persist to memory / `conversation-archival`.
- Produces a **decision, not a diff** — no merge.

### L6 — Domain/Ops (no new command; existing precedence is authoritative)
- The **global CLAUDE.md skill-precedence is the authority** inside L6 (deal-screen→underwriting→…; re-operations→tenant-intelligence→…; legal-intelligence→deal-execution). The Engineering OS **references, never restates** it (restating invites drift — ORA's most-documented failure).
- The lane only adds bookends: **QC** (matching sub-agent if one exists — underwriting-checker / rent-roll-qc / site-qc-reviewer — else the skill's own gate, e.g. loi-generation's 16-point gate) and **PERSIST**.
- Send-path / financial-confirm rules remain in CLAUDE.md/rules.md; not duplicated here.

### L7 — Release (command: `/ship`, NEW; target-aware)
Per-target recipe table (no single `npm run gate` assumption):

| Target | Gate | Deploy | Confirm | Post-verify | Rollback |
|--------|------|--------|---------|-------------|----------|
| Brain mirror (`oxford-command-center`) | `npm run gate` (typecheck·lint·test·reconcile $0) | `scripts/deploy-mirror.ps1` (redacted, behind Access) | explicit | curl apex + a `*.pages.dev` hash → expect 302; 0 confidential terms in dist | redeploy previous build |
| oxfordra.net | PageSpeed/CSP + `site-qc-reviewer` | Netlify MCP → `npx netlify-cli` fallback | **explicit, every time** | curl 200 + visual | Netlify rollback to prior deploy |
| ora-pm | `vitest run` + build | `npx wrangler pages deploy dist` (**manual**, no git auto-deploy) | explicit | hit `/api` health | redeploy prior; crons via Windows Task |

Confidentiality guard hard-wraps all three.

---

## 7. Quality bar — definition of "done" (the "no expert could fault it" gate)

A unit of work is **done** only when ALL hold (scaled to lane):
1. **TDD Iron Law** — production code has a test that was written first and watched to fail. Exceptions (config, throwaway, generated) require explicit permission.
2. **Static clean** — typecheck 0, lint 0.
3. **Tests green** — full suite passes; new behavior has new tests; output pristine (no stray warnings).
4. **Repo gate passes** where one exists (§6 L7 table).
5. **Independent review** — `requesting-code-review` (LOCAL sub-agent) before merge; two-stage spec+quality review for subagent-driven work; act on Critical/Important.
6. **Evidence before claim** — `verification-before-completion`: paste the command output; never assert success from memory.
7. **Confidentiality** — no `confidential-terms.json` term on any egress surface; cloud review forbidden on confidential repos.
8. **Karpathy checklist** (skill is `off`, so applied as a manual gate): smallest surgical change; no over-engineering/speculative generality; assumptions surfaced; success criteria stated and verifiable.

### 7.1 Execution & model dispatch (auto-selected, not asked)

The system **chooses its own** execution mode and model and announces the choice (`Dispatch: <mode> · <model> — <top factors>`), rather than asking. Decision factors, highest-weight first:
1. **Correctness/precision risk** — financial, confidential, security, irreversible. (Highest weight: ORA can't afford a wrong DSCR or a leaked deal.)
2. **Blast radius / importance.**
3. **Code-heavy vs doc/config.**
4. **Task independence & scale.**
5. **RAM/resource state** — a *modifier only*; never trade correctness for RAM — move to a lean CLI (`/handoff`, `/solo`) instead.

**Execution mode (first match):** trivial single-file → just do it inline · small (≤~4 tasks)/coupled/doc-config-dominant/RAM-tight-non-critical → **inline** (`executing-plans`) · code-heavy + mostly-independent + (high importance/precision OR >~4 tasks) → **subagent-driven-development** (from a lean CLI if RAM tight) · large independent fan-out (audit/migration/many files) + explicit opt-in → **Workflow**.

**Model tier (default `claude-opus-4-8`):** opus = architecture/design · financial/confidential/security/precision · final review+verify; sonnet = multi-file integration · debugging · standard implementation; haiku = mechanical, well-specified 1–2 file tasks. **Invariants:** reviewer ≥ implementer in capability; never below opus for confidential/financial/governor code; when unsure, go up a tier. (Tier→task mapping follows `subagent-driven-development`'s own Model Selection guidance.)

This rule lives in the CLAUDE.md doctrine (always-loaded) and is applied at the writing-plans→execute handoff.

---

## 8. Confidentiality gates the review tool (fix for finding 🔴1)

- **Default everywhere:** `superpowers:requesting-code-review` → LOCAL `general-purpose` sub-agent. Private; safe on any repo.
- **Cloud `/code-review ultra`:** allowed **only** when the repo is **not** on the `confidential-repos` list **and** Gabriel opts in explicitly.
- **`confidential-repos` (initial):** `oxford-command-center` (embeds confidential deal figures in `src/data/seed-deals.ts`); `website-canonical` / `oxford-site` (public site — never-touch per §1.1, never cloud-reviewed); `ora-pm` (tenant PII + Supabase/Stripe secrets); plus any repo flagged in `confidential-terms.json` context. Maintained alongside that file.
- Rationale: a quality gate must never become an egress vector.

---

## 9. Resource & parallelism rule (fix for the `/ram` etc. misread)

- `/ram` **measures only** (baseline ~1,860 MB). The reclaimers: `/solo` (this session → lean CLI, others untouched, ~130 MB), `/handoff` (this session → lean CLI + quit GUI, ~1.3 GB), `/heavy` (fresh lean CLI), `/cleardisk` (quit GUI + npm/CLI caches, ~2.5 GB).
- **Doctrine:** gauge `/ram` before a large sub-agent/Workflow run; on pressure, move heavy multi-agent work to a lean CLI via `/solo` or `/handoff`. Machine ceiling is 5.7 GB, single C: volume — every change reduces, not grows, footprint.
- **Parallelism cap:** `subagent-driven-development` is sequential by design. For `dispatching-parallel-agents` / `Workflow`, keep concurrency modest (Workflow self-caps at `min(16, cores−2)`; on this machine prefer ≤ a few and run from a lean CLI). No silent truncation — `log()` anything dropped.

---

## 10. The router hook (the one piece of real enforcement)

- **Event:** `UserPromptSubmit` (currently unused → no collision).
- **Behavior:** lightweight keyword/intent classifier → emits a **non-blocking** suggestion to stdout, e.g. *"Looks like an L3 Feature → run `/build` (chains brainstorm→/plan→worktree→TDD→local review→finish). Not a feature? Ignore."* Never exits non-zero; never blocks.
- **Pattern:** `bash -c` + `python3` JSON parse on stdin, matching the existing hook style. Idempotent, fast, no network.
- **Out of scope (future opt-in):** a stricter `PreToolUse(Edit|Write)` variant that warns when a multi-file change starts with no `/plan` in the session. Documented, not built — consistent with the low-friction preference.

---

## 11. Work breakdown (for the implementation plan)

1. **CLAUDE.md "Engineering OS" block** — author the law: phase spine, triage ladder+preamble, the 7-lane table (→ commands), quality bar, §8 confidentiality-gates-review, §9 resource/parallelism, §6 L7 release table, Calibrate loop. Insert as one new section; **read the file first**, do not disturb existing sections.
2. **Upgrade `/debug`** → L2 chain (systematic-debugging, TDD repro, not-repro branch, escalation, full-suite, objective review trigger) while keeping its ORA checklist.
3. **Upgrade `/build`** → L3 chain (small/large split, superpowers sequence, confidentiality-gated review) while keeping its ORA output/naming rules.
4. **Upgrade `/refactor`** → L4 chain (coverage precondition, characterization TDD, honest invariants).
5. **Upgrade `/plan`** → map onto `writing-plans` output while keeping risk + file-inventory rules.
6. **Create `/research`** (L5) and **`/ship`** (L7, target table).
7. **Create the `UserPromptSubmit` router hook** + register in `settings.json` (read-first, additive).
8. **Seed `confidential-repos`** alongside `confidential-terms.json`.
9. **Calibrate loop** — document the retro-on-miss step; wire its output to `event_log.md`.
10. **Verification:** dry-run each lane on a representative task; confirm the hook suggests correctly; confirm cloud-review is blocked on a confidential repo; confirm no confidential term leaks from `/research`.

---

## 12. Risks & open decisions

- **R1 — Soft enforcement.** Most wrappers are conventions I follow, not hard gates. Mitigation: the router hook + the always-loaded doctrine + the one hard confidentiality hook. Accepted, and labeled honestly. *(Decided 2026-06-05: defer the stricter PreToolUse plan-gate — not built now.)*
- **R2 — Doctrine drift.** If a referenced skill/command changes, the doctrine can go stale. Mitigation: reference don't restate; Calibrate loop; periodic `consolidate-memory`-style pass.
- **R3 — Command/skill trigger overlap.** Commands are user-invocable-only or explicit; superpowers process skills are user-invocable-only — so the only auto-trigger is the router hook. Low collision risk by construction.
- **R4 — Spec location & git. Decided 2026-06-05: do NOT `git init` `~/.claude`.** It holds secrets (`.claude.json` env, `claude_desktop_config.json` api-key) and `confidential-terms.json` (deal names) — a repo there risks committing them. The brainstorming "commit the spec" step is therefore skipped. If version control is wanted later, scope a repo to `docs/` + `commands/` + the doctrine only, with a strict `.gitignore`.
- **D1 — `/triage` command? Deferred 2026-06-05.** Triage stays in doctrine + the router hook; no `/triage` command for now (YAGNI).
- **D2 — Router classifier scope. Decided 2026-06-05: keyword heuristic v1** (cheap, good-enough; revisit only if misroutes are frequent).

---

## 13. What this explicitly does NOT do (YAGNI)

- No new "conductor" skill. No marketplace/`/plugin` mechanisms (don't exist). No auto-sending of anything. No re-enabling of auto-trigger on the process skills (respects your setting). No blocking hooks in v1. No changes to the resource commands (they're already correct).
