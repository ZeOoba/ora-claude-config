---
name: reference-claude-code-setups
description: "Best publicly available Claude Code setups/frameworks (deep-research verified 2026-06-06) — superpowers flagship, Anthropic docs baseline, disler hooks, steipete moved repos"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d65ce792-c08a-4a9e-9c1d-e106a2d54356
---

Best publicly available Claude Code setups, deep-research-verified 2026-06-06 (23/25 claims confirmed via 3-vote adversarial check). Star/date figures are mid-2026 snapshots (~2026-06-07) and **drift fast** — re-verify and check `archived` status before adopting.

**Flagship — obra/superpowers (Jesse Vincent / @obra):** the de facto community standard. Agentic skills framework + dev methodology, MIT, ~220k ★ (was ~89k Mar→~220k Jun 2026), actively maintained (push 2026-06-03, v5.1.0), in Anthropic's official plugin marketplace. This is what ORA already runs. Repo https://github.com/obra/superpowers · origin https://blog.fsck.com/2025/10/09/superpowers/

**Authoritative baseline — Anthropic first-party:**
- Best practices (explore→plan→code→commit; CLAUDE.md; keep concise): https://code.claude.com/docs/en/best-practices
- Agent Skills / SKILL.md authoring (progressive disclosure, <500-line body, 3rd-person description): https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices
- "How Anthropic teams use Claude Code": https://claude.com/blog/how-anthropic-teams-use-claude-code

**Best hooks specialist — disler / IndyDevDan:** claude-code-hooks-mastery (~3.7k ★, hook lifecycle + meta-agent + 8 output styles + status lines) https://github.com/disler/claude-code-hooks-mastery · multi-agent-observability (~1.4k ★, SQLite+WebSocket+Vue3 dashboard) https://github.com/disler/claude-code-hooks-multi-agent-observability

**Component catalogs (parts bins, not methodologies):** hesreallyhim/awesome-claude-code (canonical awesome list) · rohitg00/awesome-claude-code-toolkit (~2k ★; "most comprehensive" self-billing was refuted 0-3).

**Corrections vs. prior assumptions:**
- **steipete (Peter Steinberger):** old `agent-rules` repo is ARCHIVED/deprecated (2026-05-03, "old stuff I used mid 2025 when I was still using Cursor"). Live successor = **steipete/agent-scripts** (~4.3k ★) https://github.com/steipete/agent-scripts — cite this, not agent-rules.
- **Geoffrey Huntley, Harper Reed, Simon Willison:** no verifiable current *Claude-Code-specific* framework/dotfiles repo surfaced — good general agentic-coding reading, but not adoptable CC setups. Do not rank as "best CC setups."

Caveat: stars = bookmarking, not verified production adoption; no independent usage benchmark distinguishes these. Relates to [[projects]] (ORA React brain / EOS) and the user's own hook-enforced confidentiality guard + LAMS scheduler + memory brain, which is more advanced than most public setups but private.
