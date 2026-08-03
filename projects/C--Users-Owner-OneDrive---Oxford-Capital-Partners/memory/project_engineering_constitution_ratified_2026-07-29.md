---
name: project_engineering_constitution_ratified_2026-07-29
description: "RATIFIED — Engineering Constitution for the Oxford Intelligence Platform (docs/constitution/ENGINEERING_CONSTITUTION.md), merged to main 2026-07-29. Governs roadmap/ADRs/standards unless explicitly amended (§16)."
metadata: 
  node_type: memory
  type: project
  originSessionId: c6970a87-7654-4a7e-9900-819cd8cf0cad
  modified: 2026-07-29T04:28:57.898Z
---

Governing-principles document for the Intelligence Platform initiative, written 2026-07-29 as a follow-on to the ratified roadmap ([[project_intelligence_platform_roadmap_ratified_2026-07-29]]), then reviewed and merged by Gabriel same day.

- **PR:** [ZeOoba/oxford-command-center#247](https://github.com/ZeOoba/oxford-command-center/pull/247) — **MERGED** 2026-07-29T04:28:14Z, merge commit `16d9c26e`, verified via `gh pr view --json state,mergedAt,mergeCommit`.
- File now on `main`: `docs/constitution/ENGINEERING_CONSTITUTION.md` — 15 sections + 7 Immutable Principles + Amendment Process (§16, added independently of the brief) + mandatory self-critique. Each principle cites a real repo artifact (ADR-0001..0005, the reconcile-to-$0 gate, `docs/placeholder-data.md`, the 2026-07-05 registry-wipe incident) rather than generic language.
- Precedence rule it establishes: where roadmap/ADRs/standards conflict with the constitution, the constitution wins unless explicitly amended.
- Self-critique flagged one genuinely open gap left unresolved on purpose: no exemption path yet from the §9/§10/§12 rigor bar for fast/throwaway experimental work — noted, not quietly patched. Worth resolving before Phase 0 coding starts if it turns out to actually slow things down.
- Cross-linked into `docs/roadmap/intelligence-platform/README.md` and `docs/adr/README.md`; also fixed the roadmap README's stale "DRAFT" status (was still marked draft after PR #246 had already merged).
- Working branch/worktree (`docs/engineering-constitution`) deleted post-merge; local `main` fast-forwarded to `16d9c26e`.

**Next open action, unchanged from the roadmap's own pointer:** Phase 0 kickoff (`docs/roadmap/intelligence-platform/00-master-roadmap.md`, tasks `IP-0.1`–`IP-0.10`) is still the next real work — the constitution and roadmap are both now ratified; nothing is blocking implementation except someone starting it.
