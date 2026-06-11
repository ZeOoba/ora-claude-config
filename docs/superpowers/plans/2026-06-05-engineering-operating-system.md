# ORA Engineering Operating System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a self-routing engineering doctrine for ORA: a CLAUDE.md "law" block, six lane commands (4 upgraded + 2 new), one non-blocking router hook, and a confidential-repos guard — so every complex coding session runs the right skills in the right order.

**Architecture:** Three control-plane artifacts orchestrate existing tools. CLAUDE.md holds the always-loaded law (triage, quality bar, guardrails). Slash commands are the lanes; each explicitly invokes the (user-invocable-only) superpowers skills. One `UserPromptSubmit` hook classifies each request and *suggests* a lane (never blocks). Nothing claims to be more automatic than the mechanism delivers.

**Tech Stack:** Markdown (CLAUDE.md, `.claude/commands/*.md`), Python 3 (the hook, following the existing hook style), JSON (`confidential-repos.json`, `settings.json`).

**Spec:** `~/.claude/docs/superpowers/specs/2026-06-05-engineering-operating-system-design.md`

**Working surface (all inside `~/.claude`, the free working surface — NOT the business OneDrive folders):**
- `~/.claude/CLAUDE.md`
- `~/.claude/commands/{plan,build,debug,refactor,research,ship}.md`
- `~/.claude/hooks/engineering-router.py` + `~/.claude/hooks/test-engineering-router.py`
- `~/.claude/confidential-repos.json`
- `~/.claude/settings.json`

**Verification note:** Most artifacts are markdown/JSON — their "test" is a behavioral verification (does it load? does it route correctly? no placeholders? no confidential leak?), not a unit test. The **one code artifact (the hook) gets real test-first TDD** (Task 9).

---

## Execution & Model Dispatch — decision for THIS plan

This plan also *installs* the dispatch policy (Task 2) so future sessions choose automatically. Applying that policy to this plan now:

> **Dispatch: Inline (`executing-plans`) · `claude-opus-4-8`.**

**Why (factors, highest-weight first):**
1. **Precision/importance dominates.** The high-blast-radius tasks edit always-loaded `CLAUDE.md` and `settings.json` (a malformed settings file breaks the harness) and encode the confidentiality + guardrail rules. That argues for the most-capable model and careful in-session verification → **opus throughout, no downgrade**. The plan is small, so there is no cost case for cheaper tiers.
2. **Doc/config-dominant, not code-heavy.** 9 of 11 artifacts are markdown/JSON whose full content is already specified in the plan; subagent per-task isolation + 2-stage review would add ~30 agents for negligible correctness gain.
3. **Small & coupled.** 11 tasks, all referencing one doctrine — inline keeps them coherent.
4. **RAM-constrained (5.7 GB).** Inline is the low-footprint choice; it dogfoods the resource rule.

The one place rigor matters most — the hook — already carries real test-first TDD (Task 9).

*Counterfactual (shows the policy discriminates):* a multi-file feature in the brain repo (code-heavy · independent · high-precision) would instead select **subagent-driven from a lean CLI**, with **opus** for design/review, **sonnet** for integration, **haiku** for mechanical tasks.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `CLAUDE.md` (new "Engineering Operating System" section) | The always-loaded law: triage ladder, blast-radius test, definition-of-done, hard guardrails, confidentiality-gates-review, resource rule, release targets, Calibrate. Terse — points to commands/spec for detail. |
| `commands/plan.md` | L-plan: map ORA planning onto superpowers:writing-plans. |
| `commands/debug.md` | L2 chain. |
| `commands/build.md` | L3 chain. |
| `commands/refactor.md` | L4 chain. |
| `commands/research.md` | L5 chain (NEW). |
| `commands/ship.md` | L7 chain, per-target (NEW). |
| `hooks/engineering-router.py` | Non-blocking `UserPromptSubmit` lane classifier. |
| `hooks/test-engineering-router.py` | Test harness for the router. |
| `confidential-repos.json` | Repos forbidden from cloud review. |
| `settings.json` | Register the `UserPromptSubmit` hook (additive). |

---

## Phase 1 — Foundation (guard data + the law)

### Task 1: Seed `confidential-repos.json`

**Files:**
- Create: `C:/Users/Owner/.claude/confidential-repos.json`

- [ ] **Step 1: Write the file**

```json
{
  "confidential_repos": [
    "oxford-command-center",
    "website-canonical",
    "oxford-site",
    "ora-pm"
  ],
  "rule": "Cloud '/code-review ultra' is FORBIDDEN on these repos (they embed confidential deal figures, public-site content under the never-touch guardrail, or tenant PII + secrets). Default review everywhere = superpowers:requesting-code-review (LOCAL subagent). Maintain alongside hooks/confidential-terms.json.",
  "updated": "2026-06-05"
}
```

- [ ] **Step 2: Verify it parses**

Run: `python -c "import json;print(json.load(open(r'C:/Users/Owner/.claude/confidential-repos.json'))['confidential_repos'])"`
Expected: `['oxford-command-center', 'website-canonical', 'oxford-site', 'ora-pm']`

- [ ] **Step 3: (No commit — `~/.claude` is intentionally untracked; see spec §12/R4.)**

---

### Task 2: Add the "Engineering Operating System" section to `CLAUDE.md`

**Files:**
- Modify: `C:/Users/Owner/.claude/CLAUDE.md` (append one new section; **read the whole file first**, do not disturb existing sections)

- [ ] **Step 1: Back up, then read the current file**

Run: `cp "C:/Users/Owner/.claude/CLAUDE.md" "C:/Users/Owner/.claude/CLAUDE.md.bak-20260605"` (high-blast-radius file — back up first per the dispatch precision factor). Then Read `C:/Users/Owner/.claude/CLAUDE.md` in full. Confirm the existing "Skill precedence" section exists (the doctrine will *reference* it, not restate it).

- [ ] **Step 2: Append this section verbatim at the end**

```markdown
## Engineering Operating System (coding sessions)

Every non-trivial coding request runs through a **LANE**. Triage first, then run the lane's command. Full design: `~/.claude/docs/superpowers/specs/2026-06-05-engineering-operating-system-design.md`.

**Triage (before acting):** clarify if vague → split if compound → state the lane + one-line why → let me veto (anything above L1). First match wins:
- Not code? → **L6 Domain** (use the "Skill precedence" section above — it is authoritative) · or **L5 Research** (`/research`) if investigating
- Trivial **and** passes the blast-radius test → **L1 Fast** (no command)
- Broken → **L2** `/debug` · New behavior → **L3** `/build` · Restructure only → **L4** `/refactor` · Ship/deploy → **L7** `/ship`

**Blast-radius test** (disqualifies L1 → must use a real lane): path matches `hooks/**`, `*.env*`, `*credentials*`, `confidential-terms.json`, `settings.json`, CSP/headers, or financial-constant/governor files (DSCR 1.25 / LTV 40). Even L1 runs the cheapest verify.

**Definition of done** (all, scaled to lane): TDD (test written first & watched to fail; exceptions = config/throwaway/generated, ask) · typecheck 0 · lint 0 · full suite green + new tests · repo gate passes · independent **LOCAL** review (`superpowers:requesting-code-review`) before merge · **evidence (command output) before any "done" claim** (`superpowers:verification-before-completion`) · no confidential term on any egress surface · Karpathy: smallest surgical change, no over-engineering, assumptions surfaced.

**Hard guardrails — stop & ask, never without explicit permission:** touch oxfordra.net (edit/build/deploy; `website-canonical`/`oxford-site`/live site) · write/move/delete in the non-Claude Oxford Capital OneDrive business folders (reading for analysis is fine) · send email · move/transfer money · modify financial models. The confidentiality guard is hook-enforced & fail-closed (reads `confidential-terms.json`).

**Review tool is confidentiality-gated:** default = `superpowers:requesting-code-review` (LOCAL subagent). Cloud `/code-review ultra` ONLY on repos NOT in `~/.claude/confidential-repos.json` AND with explicit opt-in.

**Resource rule:** `/ram` gauges only. Reclaim: `/solo` (move this session, ~130 MB), `/handoff` (move + quit GUI, ~1.3 GB), `/heavy` (fresh lean CLI), `/cleardisk` (~2.5 GB disk). Gauge before a big fan-out; run heavy multi-agent work from a lean CLI. `subagent-driven-development` is sequential; keep `Workflow`/parallel concurrency modest (≤ a few; ceiling is 5.7 GB RAM).

**Execution & model dispatch — choose automatically, then announce `Dispatch: <mode> · <model> — <top factors>`.** Decide by these factors, highest-weight first: (1) correctness/precision risk (financial · confidential · security · irreversible), (2) blast radius / importance, (3) code-heavy vs doc-config, (4) task independence & scale, (5) RAM — a *modifier only*; never trade correctness for RAM, move to a lean CLI instead.
- **Mode (first match):** trivial single-file → just do it inline · small (≤~4 tasks) / coupled / doc-config-dominant / RAM-tight-and-non-critical → **inline** (`executing-plans`) · code-heavy + mostly-independent + (high importance/precision OR >~4 tasks) → **subagent-driven-development** (from a lean CLI if RAM tight) · large independent fan-out (audit/migration/many files) + explicit opt-in → **Workflow**.
- **Model (default `claude-opus-4-8`):** **opus** = architecture/design · financial/confidential/security/precision · final review + verification; **sonnet** = multi-file integration · debugging · standard implementation; **haiku** = mechanical, well-specified 1–2 file tasks. Invariants: reviewer ≥ implementer in capability; **never below opus for confidential/financial/governor code**; when unsure, go up a tier.

**Release (`/ship`):** brain mirror → `npm run gate` then `scripts/deploy-mirror.ps1`; oxfordra.net → never without explicit per-deploy permission; ora-pm → `vitest`+build then manual `wrangler pages deploy dist`. Each: gate → QC → confirm → post-verify → rollback.

**Calibrate:** when a lane misses (bug shipped, gate failed late, misroute), append to `memory/event_log.md` and fix the doctrine/command that failed.
```

- [ ] **Step 3: Verify no existing section was altered**

Run: `git -C "C:/Users/Owner/website-canonical" status` is N/A here; instead diff by eye — confirm the only change is the appended section and the file still opens with the original "Oxford Realty Advisors — Operating Prompt" header and retains the "Skill precedence" section.

- [ ] **Step 4: Verify length budget**

Run: `wc -l "C:/Users/Owner/.claude/CLAUDE.md"`
Expected: the new section adds ~30 lines (it is a reference, not a manual). If it ballooned, tighten — it loads every session on a RAM-constrained machine.

---

## Phase 2 — The lane commands

> Pattern for each command task: (1) Read the current file, (2) overwrite with the new content, (3) verify it has no placeholders and names only real skills/commands, (4) dry-run trigger check.

### Task 3: Upgrade `/plan`

**Files:**
- Modify: `C:/Users/Owner/.claude/commands/plan.md`

- [ ] **Step 1: Read the current `plan.md`** (preserve its objective/constraints/steps/risk/file-inventory structure — it is good).

- [ ] **Step 2: Overwrite with**

```markdown
# /plan

Structure any multi-step problem before executing. For multi-step **coding** work this maps onto **superpowers:writing-plans** (bite-sized TDD tasks); for ops/docs use the structure below.

## Trigger
Any task with >3 steps or any irreversible action.

## Output structure
1. **Objective** — one sentence: what does success look like?
2. **Constraints** — what must be preserved/avoided (hard guardrails: no website, no business-OneDrive writes, no email/money without permission; no confidential data on external surfaces).
3. **Steps** — ordered; each: what happens · what could go wrong · how to verify.
4. **Risk assessment** — reversible or not? blast radius if step N fails? confirmation required?
5. **File inventory** — to create / to modify / **must not be touched**.

## Rules
- Never skip step 4 for financial models or external communications.
- Always show the file inventory before writing anything.
- Flag CONFIDENTIAL if any step involves a `confidential-terms.json` term.
- For coding plans, hand the result to **superpowers:writing-plans** so tasks are TDD-shaped.
```

- [ ] **Step 3: Verify** — no "TBD/TODO"; references `superpowers:writing-plans` (a real skill). `grep -n "superpowers:writing-plans" plan.md` returns a line.

---

### Task 4: Upgrade `/debug` (Lane L2)

**Files:**
- Modify: `C:/Users/Owner/.claude/commands/debug.md`

- [ ] **Step 1: Read the current `debug.md`** (keep its ORA failure-mode checklist).

- [ ] **Step 2: Overwrite with**

```markdown
# /debug — Lane L2 (Bug)

Use when something is broken. Run this chain; do not guess-fix.

## Chain
1. **superpowers:systematic-debugging** — find the root cause before any fix. No guessing.
2. **Reproduce with a failing test first** (**superpowers:test-driven-development**): write a test that captures the bug; watch it fail. If it won't reproduce, instrument / add logging first — do not fix blind.
3. **Fix** minimally at the root cause. Do not refactor while fixing.
4. **Run the FULL suite** (not just the new test) to catch collateral breakage.
5. **Escalate** if root cause reveals a multi-file/behavioral change → switch to `/build` (L3) or `/refactor` (L4).
6. **Review trigger:** if the fix touched a protected path, >~40 lines, or a public API → **superpowers:requesting-code-review** (LOCAL).
7. **superpowers:verification-before-completion** — paste the passing output before claiming fixed.

## Check the obvious first (ORA failure modes)
- Netlify MCP broken → `npx netlify-cli` (do not "reconnect the connector").
- MCP auth expired → re-auth — **never** for QuickBooks (Desktop-only; Intuit QBO MCP is dead).
- Hook blocking a tool call → check PreToolUse in `settings.json`.
- Wrong cwd · skill frontmatter · node `--env-file` won't override an already-set empty var (the agent-harness shadow footgun).

## Document
Recurring failure mode → `memory/event_log.md`; MCP issue → `memory/tech.md`.
```

- [ ] **Step 3: Verify** — `grep -nE "systematic-debugging|test-driven-development|requesting-code-review|verification-before-completion" debug.md` returns 4+ lines; no placeholders.

---

### Task 5: Upgrade `/build` (Lane L3)

**Files:**
- Modify: `C:/Users/Owner/.claude/commands/build.md`

- [ ] **Step 1: Read the current `build.md`** (keep its ORA output/naming/quality rules).

- [ ] **Step 2: Overwrite with**

```markdown
# /build — Lane L3 (Feature / new behavior)

Use when constructing something new. Size it first.

## Size
- **Small** (one component, < ~1 day): light inline brainstorm → `/plan` → TDD → LOCAL review → land.
- **Large:** full chain below.

## Chain (large)
1. **superpowers:brainstorming** — design before code (scale to complexity).
2. **/plan** → **superpowers:writing-plans** — bite-sized TDD tasks; show the file inventory.
3. **superpowers:using-git-worktrees** — isolate (never build a feature on main).
4. **superpowers:subagent-driven-development** — one task at a time (sequential implementer + 2-stage spec/quality review each), under **superpowers:test-driven-development** (test first, watched to fail).
5. Pull IMPLEMENT skills as needed (frontend-design, mcp-builder, skill-creator, xlsx/docx/pdf/pptx) and **context7** before any library/API work.
6. **superpowers:verification-before-completion** + the repo gate.
7. **superpowers:requesting-code-review** (LOCAL). Cloud `/code-review ultra` ONLY if the repo is not in `confidential-repos.json` AND you explicitly opt in.
8. **superpowers:receiving-code-review** → fix Critical/Important.
9. **superpowers:finishing-a-development-branch** → merge / PR / keep / discard.
10. PERSIST → `memory/event_log.md`; `conversation-archival` if institutional.

## ORA rules (kept)
- Read before writing; check if it already exists (skills/commands/project).
- Exact output path + naming: formal docs `ORA_[DocType]_[Topic]_v[X.Y].[ext]`; deal files `[Address] [Purpose] [MM-YYYY]`; outputs to `/outputs/` with `YYYY-MM-DD_` prefix.
- No placeholder content; no features beyond what was asked (YAGNI).
- Code: no hardcoded secrets, no external CDN.
- Hard guardrails: no website, no business-OneDrive writes, no email/money without permission.
```

- [ ] **Step 3: Verify** — `grep -nE "brainstorming|using-git-worktrees|subagent-driven-development|finishing-a-development-branch" build.md` returns 4+ lines; the cloud-review gate references `confidential-repos.json`; no placeholders.

---

### Task 6: Upgrade `/refactor` (Lane L4)

**Files:**
- Modify: `C:/Users/Owner/.claude/commands/refactor.md`

- [ ] **Step 1: Read the current `refactor.md`** (keep its strict one-concern rules + ORA refactor targets).

- [ ] **Step 2: Overwrite with**

```markdown
# /refactor — Lane L4 (restructure, no behavior change)

## Precondition
- Read the file first; define the ONE concern (performance / clarity / duplication / size).
- **Coverage check:** if the target lacks tests, decide cheaply whether characterization-test cost is worth it; if not, reroute as `/build` (L3) and say so.

## Chain
1. **Characterization tests first** (**superpowers:test-driven-development**) — capture current behavior; watch them pass on the unchanged code.
2. **superpowers:using-git-worktrees** for anything multi-file.
3. Refactor — one concern, no speculative changes, no feature additions.
4. Keep tests green; **superpowers:verification-before-completion**.
5. **superpowers:requesting-code-review** (LOCAL).

## Honest guarantee
Behavior preserved **within the captured suite + named invariants**. NOT guaranteed: performance, memory, timing, error text. State explicitly what changed and what did NOT, and the verification method.

## Common ORA targets
Skills (dedupe sections, standardize Output Format, fix stale paths) · settings.json hooks (simplify pipelines, remove dead hooks) · oxfordra.net CSS/HTML **(read-only unless explicit permission — hard guardrail)** · financial models (named assumption cells, remove dead branches).
```

- [ ] **Step 3: Verify** — `grep -nE "test-driven-development|using-git-worktrees|requesting-code-review" refactor.md` returns 3+ lines; the "identical" overclaim is gone (replaced by "within the captured suite + named invariants").

---

### Task 7: Create `/research` (Lane L5)

**Files:**
- Create: `C:/Users/Owner/.claude/commands/research.md`

- [ ] **Step 1: Write the file**

```markdown
# /research — Lane L5 (investigate / compare / decide)

Produces a DECISION, not a diff. No merge.

## Confidentiality FIRST
Strip every `confidential-terms.json` term (deal names, addresses) from any EXTERNAL query (web / firecrawl). ORA-internal questions stay on internal sources only (Excel / Notion / memory / HubSpot / M365). Never egress a confidential term.

## Chain
1. **Internal first:** memory, Notion, Excel, HubSpot, M365/SharePoint.
2. **External:** `deep-research` skill, or `firecrawl` + **context7** (live library docs). **Workflow only on explicit opt-in** (it fans out many agents — RAM).
3. **Adversarial verify** — confirm key claims against ≥2 independent sources (deep-research does this natively).
4. **Synthesize** → cite every source.
5. **PERSIST** → memory + `conversation-archival` (Notion) for institutional findings.

## Resource
Gauge `/ram` before a fan-out; run heavy multi-agent research from a lean CLI (`/solo` or `/handoff`). Keep concurrency modest.
```

- [ ] **Step 2: Verify** — file exists; `grep -nE "confidential-terms.json|deep-research|context7" research.md` returns 3 lines; no placeholders.

---

### Task 8: Create `/ship` (Lane L7)

**Files:**
- Create: `C:/Users/Owner/.claude/commands/ship.md`

- [ ] **Step 1: Write the file**

```markdown
# /ship — Lane L7 (release / deploy)

Target-aware. The confidentiality guard hard-wraps every path. **NEVER deploy without explicit per-deploy permission.**

## Pre-flight (all targets)
1. **superpowers:verification-before-completion** — evidence the build is green.
2. Run the target's gate (below).
3. Run the target's QC sub-agent.
4. **Ask for explicit permission**, naming the target and exactly what will change.

## Targets
- **Brain mirror (`oxford-command-center`):** gate `npm run gate` (typecheck · lint · test · reconcile $0) → deploy `scripts/deploy-mirror.ps1` (redacted, behind Cloudflare Access) → post-verify: curl apex + a `*.pages.dev` hash → expect **302**; confirm **0 confidential terms** in `dist` → rollback: redeploy the previous build.
- **oxfordra.net:** ⛔ HARD GUARDRAIL — never edit/build/deploy without explicit permission. gate PageSpeed/CSP + **site-qc-reviewer** sub-agent → deploy Netlify MCP → `npx netlify-cli` fallback → post-verify curl 200 + visual → rollback: Netlify "publish previous deploy".
- **ora-pm:** gate `vitest run` + build → deploy `npx wrangler pages deploy dist --project-name ora-pm` (**MANUAL** — no git auto-deploy) → post-verify: hit `/api` health → rollback: redeploy prior; crons run via the Windows Task.

## After
Append the release (target, what shipped, verification result) to `memory/event_log.md`.
```

- [ ] **Step 2: Verify** — file exists; all three targets present; `grep -n "HARD GUARDRAIL" ship.md` returns the oxfordra.net line; no placeholders.

---

## Phase 3 — The router hook (real TDD) + registration + end-to-end

### Task 9: The `UserPromptSubmit` router hook (test-first)

**Files:**
- Create: `C:/Users/Owner/.claude/hooks/test-engineering-router.py`
- Create: `C:/Users/Owner/.claude/hooks/engineering-router.py`

- [ ] **Step 1: Write the failing test**

```python
# test-engineering-router.py — run: python test-engineering-router.py
import subprocess, json, sys, os
HOOK = os.path.join(os.path.dirname(__file__), "engineering-router.py")

def run(prompt):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": prompt}),
                       capture_output=True, text=True)
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}"
    return p.stdout

cases = [
    ("there's a bug, the rent roll parser is failing", "/debug"),
    ("build a new dashboard widget for WALT", "/build"),
    ("refactor the overlay module, it's too big", "/refactor"),
    ("research which charting library is fastest", "/research"),
    ("ship the brain mirror to production", "/ship"),
]
for prompt, expected in cases:
    out = run(prompt)
    assert expected in out, f"prompt {prompt!r} should suggest {expected}, got: {out!r}"

# Silence on non-work prompts and empty prompts (no false nudges)
assert run("what's the weather") == "", "should stay silent on non-coding prompts"
assert run("") == "", "should stay silent on empty prompt"
print("ALL ROUTER TESTS PASS")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python "C:/Users/Owner/.claude/hooks/test-engineering-router.py"`
Expected: FAIL — the hook file does not exist yet (FileNotFoundError / non-zero from subprocess).

- [ ] **Step 3: Write the hook**

```python
# engineering-router.py — UserPromptSubmit hook. Non-blocking lane suggester. Always exits 0.
import sys, json

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt = (data.get("prompt") or "").lower()
    if not prompt.strip():
        return

    def has(*words):
        return any(w in prompt for w in words)

    lanes = []
    if has("deploy", "ship", "release", "publish", "go live", "to production", "to prod"):
        lanes.append(("L7", "/ship", "release/deploy — target-aware, confirm before deploy"))
    if has("bug", "broken", "error", "failing", "fails", "doesn't work",
           "not working", "crash", "stack trace", "regression", "fix the"):
        lanes.append(("L2", "/debug", "root-cause via systematic-debugging + a failing test first"))
    if has("refactor", "clean up", "restructure", "simplify", "tidy", "extract", "rename"):
        lanes.append(("L4", "/refactor", "characterization tests first; behavior preserved"))
    if has("research", "compare", "investigate", "find out", "which library",
           "options for", "look into", "evaluate", "best way to"):
        lanes.append(("L5", "/research", "internal-first; scrub confidential terms from web queries"))
    if has("build", "add", "create", "implement", "feature", "make a",
           "write a", "scaffold", "new "):
        lanes.append(("L3", "/build", "brainstorm -> /plan -> worktree -> TDD -> local review -> land"))

    if not lanes:
        return

    order = {"L7": 0, "L2": 1, "L4": 2, "L5": 3, "L3": 4}  # most-specific intent wins
    lanes.sort(key=lambda x: order[x[0]])
    lane, cmd, why = lanes[0]
    others = "".join(f" {l[1]}" for l in lanes[1:])
    tail = f" Other possible:{others}." if others else ""
    print(f"[Engineering OS] Looks like lane {lane} -> run {cmd} ({why}).{tail} "
          f"Triage first: clarify if vague, split if compound, state the lane, then proceed. Not a match? Ignore.")

if __name__ == "__main__":
    main()
    sys.exit(0)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python "C:/Users/Owner/.claude/hooks/test-engineering-router.py"`
Expected: `ALL ROUTER TESTS PASS`

- [ ] **Step 5: Manual smoke test (the exit-0 + context-injection contract)**

Run: `echo '{"prompt":"fix the failing CAM reconciliation"}' | python "C:/Users/Owner/.claude/hooks/engineering-router.py"; echo "exit=$?"`
Expected: a line containing `/debug` then `exit=0`.

---

### Task 10: Register the hook in `settings.json`

**Files:**
- Modify: `C:/Users/Owner/.claude/settings.json` (add a `UserPromptSubmit` key inside `hooks`; **read first**, additive only)

- [ ] **Step 1: Back up, then read `settings.json`**

Run: `cp "C:/Users/Owner/.claude/settings.json" "C:/Users/Owner/.claude/settings.json.bak-20260605"` (a malformed settings file breaks the harness — back up first). Then read it and confirm there is no existing `UserPromptSubmit` key under `hooks` (verified absent 2026-06-05).

- [ ] **Step 2: Add this block inside the `"hooks"` object** (sibling of `PreToolUse`/`PostToolUse`)

```json
"UserPromptSubmit": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python \"C:/Users/Owner/.claude/hooks/engineering-router.py\""
      }
    ]
  }
]
```

- [ ] **Step 3: Verify JSON validity**

Run: `python -c "import json;json.load(open(r'C:/Users/Owner/.claude/settings.json'));print('settings.json OK')"`
Expected: `settings.json OK`

- [ ] **Step 4: Confirm no other key changed** — diff by eye: the only addition is the `UserPromptSubmit` array; `permissions`, `skillOverrides`, existing `PreToolUse`/`PostToolUse` untouched.

---

### Task 11: End-to-end verification (the acceptance gate)

**Files:** none (verification only).

- [ ] **Step 1: Router routes correctly** — `python "C:/Users/Owner/.claude/hooks/test-engineering-router.py"` → `ALL ROUTER TESTS PASS`.

- [ ] **Step 2: All six commands load** — Run: `ls C:/Users/Owner/.claude/commands/{plan,build,debug,refactor,research,ship}.md` → all six listed. In a fresh session, `/build` and `/ship` appear in the command list.

- [ ] **Step 3: No placeholders anywhere** — Run: `grep -rniE "TODO|TBD|FIXME|fill in|implement later" C:/Users/Owner/.claude/commands/ C:/Users/Owner/.claude/CLAUDE.md` → no matches.

- [ ] **Step 4: Confidential-review gate is real** — Confirm `confidential-repos.json` lists `oxford-command-center`, and `/build` step 7 + CLAUDE.md both gate cloud review on it. (Behavioral: when asked to "ultra-review oxford-command-center," the doctrine says use LOCAL review instead.)

- [ ] **Step 5: No confidential leak in the new artifacts** — confirm none of the deal tokens in `hooks/confidential-terms.json` appear in `commands/`, the appended `CLAUDE.md` section, `confidential-repos.json`, or `docs/`. (The system references `confidential-terms.json` by filename only — never a deal name. Check by iterating the term list, not by hardcoding a token, so this very step stays token-free.)

- [ ] **Step 6: Guardrails + dispatch policy present in the law** — Run: `grep -nE "oxfordra.net|business OneDrive|move/transfer money" C:/Users/Owner/.claude/CLAUDE.md` → the hard-guardrails line is present. Run: `grep -n "Execution & model dispatch" C:/Users/Owner/.claude/CLAUDE.md` → the dispatch policy is present.

- [ ] **Step 7: Update memory** — Append a dated line to `memory/event_log.md` recording the Engineering OS install; add a one-line pointer in `memory/projects.md`. (PERSIST phase.)

---

## Self-Review (run after writing; fix inline)

- **Spec coverage:** §3 three artifacts → Tasks 1/2 (doctrine+guard), 3-8 (commands), 9-10 (hook). §4 spine → encoded in CLAUDE.md + commands. §5 triage → CLAUDE.md + Task 9 hook. §6 lanes → Tasks 3-8 (all fixes: L1 blast-radius in CLAUDE.md; L2 escalation/full-suite; L3 small/large + gated review; L4 honest invariants; L5 scrub; L7 per-target). §7 quality bar → CLAUDE.md "Definition of done". §8 confidentiality-gates-review → Task 1 + CLAUDE.md + /build. §9 resource → CLAUDE.md. §10 hook → Tasks 9-10. §11 work breakdown → all tasks. §1.1 guardrails → CLAUDE.md + /ship + /build/refactor. Calibrate → CLAUDE.md + Task 11/7. **No gaps.**
- **Placeholder scan:** none (Task 11/3 enforces).
- **Type/name consistency:** command names (`/plan /build /debug /refactor /research /ship`) and skill names (`superpowers:*`) are identical across all tasks and match the live inventory; hook filename identical in Tasks 9/10/11.
```

