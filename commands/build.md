# /build — Lane L3 (Feature / new behavior)

Use when constructing something new. Size it first.

## Size
- **Small** (one component, < ~1 day): light inline brainstorm → `/plan` → TDD → LOCAL review → land.
- **Large:** full chain below.

## Chain (large)
0. **Capability audit — BEFORE any design.** Inventory what the target repo already does for this behavior by reading its **code**, not its docs, memory, or skill descriptions. Produce a component→owner map: for each thing you intend to build, name the existing module that implements it, or record it verified-absent with the grep that proves it. A spec written from docs alone re-specifies working code — on 2026-08-16 this cost three successive re-scopes of one approved plan (`_pipeline`, then `server/ar/`, then `conditions.ts`, each invalidating it). Absence is a claim that needs evidence; skipping this step is what step 1 will then design around.
1. **superpowers:brainstorming** — design before code (scale to complexity). For any service/runtime component (applies to the Small path's inline brainstorm too), the design presentation must also include: (a) a **load/bottleneck derivation** with visible arithmetic — stated scale → active → peak RPS → first component to fail and at what multiple of baseline; "nothing bottlenecks at this scale" is an acceptable answer — never invent problems; (b) a **3-item production pre-mortem** — failure mode + what detects it (software twin of the deal pipeline's mandatory pre-mortem). Skip both for scripts, hooks, and CLI tools (no load profile). When a service/runtime component is in scope, elicit expected scale/SLO as one clarifying question during brainstorming — the derivation needs a stated figure, never an invented one.
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
- Read before writing; check if it already exists — in the **target repo's code**, not only skills/commands/project. "Nothing does X" almost always means it exists and is disconnected, or exists and was never invoked.
- Exact output path + naming: formal docs `ORA_[DocType]_[Topic]_v[X.Y].[ext]`; deal files `[Address] [Purpose] [MM-YYYY]`; outputs to `/outputs/` with `YYYY-MM-DD_` prefix.
- No placeholder content; no features beyond what was asked (YAGNI).
- Code: no hardcoded secrets, no external CDN.
- Hard guardrails: no website, no business-OneDrive writes, no email/money without permission.
