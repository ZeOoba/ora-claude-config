# EOS Reliability Hardening — Design Spec

**Date:** 2026-06-05 · **Owner:** Gabriel Goldberg · **Surface:** Claude Code (lean CLI)
**Builds on:** `2026-06-05-engineering-operating-system-design.md`

---

## 1. Goal & honest ceiling

Make the Engineering Operating System fail less by (a) converting the few highest-consequence soft rules into **hard, deterministic gates**, and (b) instrumenting the soft layer so its failures become **measurable** and feed the Calibrate loop. 

**Honest ceiling (non-negotiable framing):** a model-driven system cannot reach 100% compliance; any rule not mechanically enforced is violated some fraction of the time. The target is therefore: *high-consequence rules mechanically enforced; everything else measured so residual failures surface and get corrected.* This spec does not claim perfection; it claims a lower, **observable** failure rate.

## 2. Spike findings that shaped the design (sourced from the CC hooks docs, 2026-06-05)

- All hook events receive `session_id`, `transcript_path`, `cwd`, `permission_mode` on stdin. Stop/SessionEnd can parse `transcript_path` (JSONL) for the full tool-call history. → telemetry is feasible.
- PreToolUse blocks via `exit 2` (stderr→Claude) or JSON `{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":...}}` + exit 0. Non-blocking context = plain stdout + exit 0.
- `session_id` is available **only** via the stdin JSON field (NOT the `CLAUDE_CODE_SESSION_ID` env var). Stateful hooks must read stdin.
- **`/code-review ultra` is NOT interceptable** — a built-in command dispatcher, uploads to cloud, no local tool call; the slash command never reaches a UserPromptSubmit hook. ① cannot be a hard gate.

## 3. THE SAFETY INVARIANT (applies to every blocking hook)

**Fail OPEN on any error.** Each blocking hook wraps its entire body in try/except; on *any* exception, missing field, unreadable file, or unexpected state, it prints nothing and `exit 0` (allow). It emits a block **only** for its single, explicitly-matched condition. A bug in a guard must never be able to halt legitimate work — including the subagents building this very plan. Each blocking hook ships with a test that asserts malformed/empty input → exit 0, no output.

## 4. The six fixes (final mechanisms)

### ① Confidentiality on cloud review — soft mitigation (cannot hard-gate)
- Keep the existing doctrine rule (cloud review forbidden on `confidential-repos.json` repos).
- Add to the **router** (`engineering-router.py`): if the prompt text matches cloud/ultra-review intent (`code-review ultra`, `ultrareview`, `cloud review`) AND (mentions a confidential repo name OR the cwd is a confidential repo), inject a strong non-blocking warning naming the rule.
- **Residual risk documented in doctrine:** a direct `/code-review ultra` slash command on a confidential repo is blockable by no local mechanism. Mitigation is the doctrine reminder + the fact that Claude cannot launch ultra itself (only Gabriel can).

### ② Doctrine-integrity probe — `~/.claude/maintenance/doctrine-integrity-probe.py`
- Parse the "Engineering Operating System" section of `CLAUDE.md`. Extract referenced: command names (`/plan /build …` → `commands/<name>.md`), skill names (`superpowers:*`), file paths (`scripts/deploy-mirror.ps1`, `confidential-repos.json`, `hooks/confidential-terms.json`), repo names (`oxford-command-center`, …).
- Assert each resolves: command file exists; referenced local file exists; repo dir exists at its known path; skill name is in the known skill set (best-effort). Print a report; `exit 1` if any referenced artifact is missing (drift detected), else `exit 0`. Report-only for skills it can't verify (warn, don't fail).
- Mirrors `memory-integrity-probe.py` / `governor-drift-probe.py`. Runnable standalone; optional later wire-in to the daily Health Guard.

### ③ Compliance telemetry — `~/.claude/hooks/eos-telemetry.py` (SessionEnd) + `~/.claude/maintenance/eos-telemetry-rollup.py`
- SessionEnd hook: read `session_id` + `transcript_path` from stdin; if the transcript shows no code activity (no Edit/Write/Bash on code), exit 0 silently. Else parse the JSONL and emit ONE JSON line to `~/.claude/telemetry/lane-telemetry.jsonl`: `{ts, session_id, edits, files[], bash_test_ran (bool — any Bash cmd matching test/gate/pytest/vitest/npm test), task_dispatched (bool — any Task tool), lane_declared (bool — assistant text contains "Dispatch:" or "lane L"), verification_seen (bool — assistant text contains evidence markers)}`.
- **Fail-open + never block:** wrap everything; exit 0 always; telemetry failure must never affect the session.
- Rollup script: read the JSONL, print compliance rate (% code-sessions with lane_declared AND bash_test_ran AND task/review) + the most-frequently-missing signal. Run manually or weekly.

### ④ Plan-gate (hard, overridable) + evidence-gate (soft)
**Plan-gate** `~/.claude/hooks/eos-plan-gate.py` (PreToolUse: Edit|Write|MultiEdit):
- Read `session_id` + `tool_input.file_path`. Maintain `~/.claude/hooks/sessions/<sid>/`: increment a counter only for **code paths** (skip `docs/**`, `*.md` memory, `_smoke*`, scratch, the brainstorm dir). 
- If counter > 3 AND no `plan-approved` marker AND no `override` marker → **deny** (JSON permissionDecision deny) with reason: "4+ code files edited with no plan this session. Run /plan or /build, or `touch ~/.claude/hooks/sessions/<sid>/override` to proceed." Else allow (exit 0).
- `plan-approved` marker auto-set by a companion **PostToolUse** (`eos-plan-marker.py`, matches Write) when a file under `docs/superpowers/plans/` is written.
- **Fail-open**: any error → allow.
**Evidence-gate** `~/.claude/hooks/eos-evidence-gate.py` (PreToolUse: Bash):
- If the command is a `git commit` of code AND no `gate-green` sentinel exists for the session → emit a **non-blocking** reminder (plain stdout, exit 0): "No green gate recorded this session — run the repo gate before claiming done." (Non-blocking by design: hard-blocking commits across heterogeneous repos is too risky.) The `gate-green` sentinel is set by a PostToolUse when a Bash gate/test command exits 0.

### ⑤ Router de-noise — edit `engineering-router.py` (+ tests)
- Add a **negative-context guard**: if the prompt matches non-coding contexts (`calendar`, `meeting`, `remind`, `email`, `lunch`, `explain why`, `assume`, `suggest improvements`, question-framing without a build verb) → suppress the nudge or require a strong coding signal.
- Require the lane keyword to be a genuine action, not part of an analytical/meta question (e.g., "explain why X **fails**" must NOT fire L2).
- Regression tests: this prompt-class ("explain why … fails / assume it isn't perfect / suggest improvements") → silent; plus keep all existing routing + the ASCII-only assertion.

### ⑥ Dispatch honesty — edit `CLAUDE.md` Engineering OS section
- Model-tier note: "model-tier selection applies to spawned subagents/Workflow; for inline execution the model is the fixed session model — route genuinely tier-sensitive work to subagent-driven-development rather than assuming inline can switch tiers."
- ① note: "Cloud `/code-review ultra` cannot be blocked by a local hook (built-in cloud dispatcher); it is a doctrine rule only — never run it on a `confidential-repos.json` repo."
- Pointer: doctrine-integrity probe + telemetry exist (where).

## 5. Files

Create: `maintenance/doctrine-integrity-probe.py` (+test), `hooks/eos-telemetry.py` (+test), `maintenance/eos-telemetry-rollup.py`, `hooks/eos-plan-gate.py` (+test), `hooks/eos-plan-marker.py`, `hooks/eos-evidence-gate.py` (+test). 
Modify: `hooks/engineering-router.py` (+ `test-engineering-router.py`), `CLAUDE.md`, `settings.json` (register: SessionEnd telemetry; PreToolUse plan-gate + evidence-gate; PostToolUse plan-marker + gate-green-sentinel).

## 6. Build order & execution mode

**Dispatch: subagent-driven-development for the isolated hook scripts; coordinator (me) owns integration.** Each hook/probe is built + **unit-tested in isolation, NOT registered**, by a subagent (independent, code-heavy → good fan-out from this lean CLI). The **coordinator personally** does the safety-critical, single-file, sequenced steps last: `settings.json` registration (with backup), `CLAUDE.md` edits, and the end-to-end integration test — because a buggy blocking hook has maximal blast radius (could brick editing). Order: build+test all scripts → verify each fails-open on malformed input → register in settings.json → integration test (induce each gate, confirm fail-open, confirm router silent on this prompt-class) → backups retained.

## 7. Risks
- **R1 — A blocking hook bricks editing.** Mitigated by the §3 fail-open invariant + isolation testing before registration + register-last + backups.
- **R2 — Plan-gate friction.** Mitigated by threshold (>3), code-paths-only, trivial override, fail-open.
- **R3 — ① residual exposure.** Accepted + documented; no local mechanism exists. Doctrine + human discipline only.
- **R4 — Telemetry transcript format drift.** The probe parses JSONL defensively (best-effort field access); failure → silent exit 0.
