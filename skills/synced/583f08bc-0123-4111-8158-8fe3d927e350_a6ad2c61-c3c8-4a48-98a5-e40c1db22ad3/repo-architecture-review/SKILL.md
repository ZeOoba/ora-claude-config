---
name: repo-architecture-review
description: Cross-repo architecture-diagram audit for Oxford Realty Advisors' GitHub repos — reads each repo's embedded architecture diagrams (mermaid in README/docs, .drawio, .puml) and surrounding prose, then screens findings against failure patterns already proven costly here: unbounded per-row loops that blow a platform's rate limit, automation running outside the ORA scheduled-task fleet, dual-write data with only after-the-fact drift detection, a manual build step that can go stale silently, dead links documented as live, missing CI gates on financial-decision code, and unproven coordination-layer infrastructure between systems. Produces a prioritized, evidence-cited punch list — does not implement fixes. Use when Gabriel says: review my repos, audit my architecture, review the diagrams in my repos, cross-repo review, how do my systems talk to each other, find inefficiencies across my apps. Distinct from `ora-setup-audit` (audits the Claude Code/Cowork setup itself, not application repos). v1.0.
license: ORA Internal
---

# Repo Architecture Review

Finds cross-cutting inefficiencies by reading the architecture diagrams repos already carry (most ORA repos document a mermaid `flowchart`/data-flow diagram in their README, kept current as part of normal maintenance) rather than re-deriving system structure from scratch. The diagrams plus the prose around them are usually enough — this skill rarely needs to read implementation source directly except to verify a suspected finding.

## Scope

Every repo under the `ZeOoba` GitHub account (or whichever org is current — confirm with `gh repo list` rather than assuming a stale list). Not scoped to any one repo; the value is in the cross-repo pattern, not a single deep audit (that's what `ora-setup-audit`, `deal-execution`, or a plain `/debug` session are for on one target).

## Standard Workflow

0. **Check prior art before enumerating anything.** Grep `open-items-tracker.md` (`~/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md`) for the repo names and failure-pattern keywords from Step 5 below (e.g. `subrequest`, `Windows Task Scheduler`, `dual-write`, `drift`, `round-trip`) before reading a single diagram. A stale-but-still-relevant OI should be re-verified and its status updated in place, never silently re-filed as a fresh finding. This is a proof step, not a memory jog: a 2026-08-21 run of this skill nearly re-derived four already-closed findings (OI-162/163/164/165) before catching itself mid-run. State in the final output which prior OIs were checked and what was ruled out (still open / already fixed / not applicable) — see Outputs.
1. **Enumerate repos**: `gh repo list <org> --json name,description,updatedAt,visibility,isArchived`. Don't assume the list from a prior session — repos get added/archived.
2. **Locate local clones** for each repo (check `C:\Users\Owner\<repo-name>` first; ask Gabriel for any not found rather than skipping them silently — a repo with no local clone still needs its diagram read via `gh api` if it matters).
3. **Find diagram-bearing files**: grep every local clone for `` ```mermaid `` fences (README.md and docs/** are the usual locations) and for `.drawio`/`.puml` files. A repo with zero diagrams isn't a skip — note it and read the README/docs prose directly instead.
4. **Read each diagram plus its surrounding "Reading the diagram" prose** (most ORA repos write one) — this is almost always sufficient; only fall back to reading actual source when a diagram's claim needs verifying (e.g., "is this cron actually registered" needs checking `list_scheduled_tasks`/`schtasks`, not just trusting the diagram).
5. **Screen every finding against this checklist** — these are the specific failure patterns that have actually cost real time/risk in this codebase, not a generic list:
   - **Unbounded per-item loops**: a query, insert, or external-API call issued once per row/lease/record with no batching — scales badly and can silently exceed a platform limit (Cloudflare Workers' subrequest cap is the proven example; watch for the same shape against any rate-limited or metered API).
   - **Off-fleet automation**: a cron/scheduled job driven by a standalone OS-level scheduler (Windows Task Scheduler, cron, systemd timer) instead of the project's own registered-task system — invisible to whatever monitors the registered fleet.
   - **Dual-write without prevention**: two independently-writable copies of the same data/config (a git repo + a runtime cache, two databases, a source-of-record + a mirror) reconciled only by after-the-fact drift *detection*, not structural prevention. Detection tooling bounds how long a divergence survives; it doesn't stop one occurring.
   - **Disconnected build step**: a generation/build script that only runs when someone remembers to run it by hand, instead of being wired into the actual CI/deploy pipeline — the artifact it produces can silently drift from source.
   - **Dead links documented as live**: a subdomain, endpoint, or integration point the docs describe as working that a quick check shows is actually broken or misconfigured (DNS on the wrong provider is the proven example here).
   - **Missing gate on financial-decision code**: a reconciliation/cross-check script that exists but isn't wired into CI or a pre-push hook, so a regression can merge silently. If a fix here is warranted, `AUTOPAY_BATCH_LIMIT`-style subrequest/scale math and a real production run's numbers matter more than eyeballing "should be fine."
   - **Unproven coordination infrastructure**: a system built specifically to let two other systems hand off work (a task queue, a message format, a sync protocol) that has real tests but has never had a live end-to-end round-trip between the actual two systems it connects.
6. **Prioritize and cite evidence** — every finding needs a file path (and line/section where relevant), not a general impression. Rank by real stakes (financial/data-integrity risk first, cosmetic/dead-doc issues last), and note the pattern connecting multiple findings if one exists (e.g., "every repo invented its own bespoke sync mechanism" is itself a finding, not just a list of six unrelated ones).
7. **Hand off fixes, don't build them inline as part of this skill** — report the punch list, then let Gabriel pick what to act on. Route each accepted fix through the normal Engineering OS lane triage (`/debug`, `/build`, etc. per CLAUDE.md), not as an extension of this skill's own scope. A fix that touches financial/security-gate code still needs the mandatory adversarial REFUTE pass regardless of how it was discovered.
8. **File real findings as OI items** (`python ~/.claude/maintenance/allocate-oi-id.py`) so they're tracked even if Gabriel doesn't act on them immediately — a finding that only exists in chat scrollback is a finding that gets re-discovered next audit.

## Boundaries

- Read-only by design: this skill diagnoses, it does not modify application code. Any code change is a separate, explicitly-scoped follow-up.
- Writing to a repo under Hard Invariant 2 (oxfordra.net / website-canonical / oxford-site) still needs Gabriel's per-write confirmation even for a fix that came out of this audit — the audit finding it is not itself authorization.
- Don't re-derive a finding this skill (or a prior run of it) already filed and is tracked in `open-items-tracker.md` — this is Step 0 of Standard Workflow, not optional; see there for the concrete check.
- Registering new unattended automation (a fleet cron, a CI gate that blocks pushes) that didn't exist before is a bigger decision than fixing visibility for something already running — surface it as a choice, don't silently flip it on, even if the audit made the gap obvious.

## Outputs

A prioritized punch list (chat response, or an artifact if Gabriel wants it shareable) with: the pattern, file/line evidence, stakes, and a fix direction — plus OI-tracker filings for anything worth tracking past the conversation. Must also state a "prior-art checked" line: which existing OIs were grepped for in Step 0, and what was found (still open / already fixed / not applicable) — proof the check ran, not just that it exists in the procedure.
