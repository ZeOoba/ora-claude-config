---
name: verified-deal-recon
description: "Adversarially-verified acquisition pre-screen for Oxford Realty Advisors — the SINGLE-TARGET PRE-SCREEN DEFAULT. Recon fan-out research, then three independent Explore verifiers that try to REFUTE it (comps/basis · functional/environmental · demand/lease-up), then a PURSUE / PASS / NEEDS_MORE brief with a mandatory pre-mortem. Use whenever ONE named acquisition target — a street address, a property name, or a single offering memorandum — needs a real pursue/pass decision before underwriting. Trigger on: pre-screen this, screen this property, is this worth underwriting, first look, recon this deal, verified deal recon, should we pursue, worth a look. NOT for batch-triaging a broker inbox and NOT for off-market owner lead-lists. Does NOT underwrite — hands off to acquisition-underwriting. v1.2 (2026-08-22: cross-surface port — runs on Cowork and Code)"
---

# Verified Deal Recon — ORA single-target pre-screen

Runs the `verified-deal-recon` workflow: one recon pass, three adversarial verifiers working independently, one synthesized brief. The verifiers do their own research and are instructed to refute the recon — that adversarial step is the whole point, and it is what separates this from the bare `deal-recon` agent (instant first-look only).

## Why this is a skill and not a bare workflow

Workflows live in `.claude/workflows/` and custom subagents in `.claude/agents/`. **Neither directory syncs to Cowork — only `.claude/skills/` does.** From 2026-07-09 until 2026-08-22 this pre-screen was a Code-surface workflow calling a Code-surface agent, which meant the User Preferences named it "the single-target pre-screen default" while on Cowork it silently resolved to nothing. Packaging it as a skill that carries its own script is what makes one canonical copy work on both surfaces.

## How to run it

Invoke the Workflow tool against this skill's own bundled script — do **not** rely on `{name:"verified-deal-recon"}`, which only resolves where `.claude/workflows/` happens to hold a copy:

```
Workflow({
  scriptPath: "<this skill's directory>/references/verified-deal-recon.js",
  args: { property: "<full property brief as a string>", today: "<YYYY-MM-DD>" }
})
```

`args` also accepts a plain string (the property brief), in which case the ledger date is emitted as the literal token `<STAMP-DATE>` for the calling session to fill in.

**Workflow opt-in:** invoking this skill IS the opt-in. The Workflow tool requires explicit user authorisation before fanning out agents; a skill whose instructions direct a Workflow call satisfies that. Do not additionally ask for permission.

**Cost:** five agents (1 recon + 3 verifiers + 1 synthesis). The recon runs on opus; the verifiers run as `Explore`. Budget accordingly on a batch.

## Writing the property brief

The brief is the only input. Put everything known into it — address, SF, acreage, asking price, tenancy, vintage, broker, and anything from the OM. The recon agent cannot ask questions mid-run; gaps become `[UNVERIFIED]` tags rather than clarifications. First line of the brief becomes the deal name in the ledger row, so lead with the address.

## What comes back

A `brief` object: verdict, one-line thesis, snapshot, verified rent and sale comps, basis read, submarket demand, kill risks, pre-mortem, open items, confidence. Plus `reconSoloVerdict` (what the recon said before verification), `verifierCount`, and `anyFlip` — **`anyFlip: true` means at least one verifier flipped the recommendation, which is the single most informative field in the return.** Read it first.

## After the run — three standing rules

1. **Hand off, do not underwrite.** A PURSUE or NEEDS_MORE goes to `acquisition-underwriting` (SCREEN or FULL). This skill deliberately computes no DSCR, LTV or IRR.
2. **Ledger row is a DRAFT.** `ledgerRowDraft` is never written by the workflow and must never be appended on a provisional result. Append it to `memory/deal-decision-ledger.md` only after Gabriel ratifies the verdict in-turn, and stamp the real date if it reads `<STAMP-DATE>`. The 6-column schema is `Date | Deal | Verdict | one-line reason | buy-box rule validated/refined | FORT`; write `—` for FORT unless Stage 2.8 actually ran.
3. **Dedupe before logging.** Check both the Notion Deal Sourcing Log (`9a6ae219`) and the Acquisition Pipeline Tracker (`bcfe4a03`) for an existing row on this parcel; update in place rather than creating a duplicate, and stamp `Last Activity` = today on any row you touch.

## Confidentiality

The recon prompt carries ORA's standing rule verbatim: never put an active ORA deal name or identifier into an external `WebSearch`/`WebFetch` query, and never include not-yet-closed ORA deal data in output. The authoritative roster is `~/.claude/hooks/confidential-terms.json` (keys with `active: true`). On any surface where that file is unreachable, treat an uncertain name as confidential and keep it out of external queries.

## Port notes (v1.2)

Two changes from v1.1, both required for Cowork; behaviour is otherwise identical.

1. **`agentType:'deal-recon'` removed.** The agent's system prompt (`.claude/agents/deal-recon.md`, 2026-07-17) is inlined verbatim into the Phase 1 prompt with `model:'opus'` matching its frontmatter. The `Explore` verifiers are unchanged — `Explore` is a built-in agent type available on both surfaces.
2. **`new Date()` removed.** Workflow scripts throw on argless `new Date()`, `Date.now()` and `Math.random()` — they would break resume. The ledger date now arrives via `args.today` or falls back to a `<STAMP-DATE>` token.

If `.claude/agents/deal-recon.md` is later edited on the Code surface, re-inline it here — the two copies are not linked.
