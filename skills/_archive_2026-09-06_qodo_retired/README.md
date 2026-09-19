# Qodo skills — RETIRED 2026-09-06

Gabriel's ruling (interactive decision, 2026-09-06): **Claude-native review only.**
Qodo's trial ended 2026-09-06 and is NOT being renewed.

These five skills all route through the `qodo` CLI against a workspace whose trial
has ended. Left installed they would trigger on their descriptions and silently
under-deliver — returning nothing useful while looking like a real review.

Archived, not deleted. To restore: move the directories back to `skills/` and
re-authenticate the CLI at `~/.qodo/bin/qodo`.

## Why the ruling went this way

Qodo had a real track record — 10/10 inline findings accepted on ora-claude-config
PR #158, and a genuine concurrency catch on PR #153 (an age-based scratch sweep that
could delete a live sibling process's files). But ORA runs ~200 PRs/month across four
repos, so the free tier's 30 reviews/month covers ~15% of volume, and the paid tier
was declined under the procurement stance (below $150M AUM, the marginal tooling
dollar compounds the Claude/agent layer rather than third-party SaaS).

The replacement is NOT "nothing": CLAUDE.md's Engineering OS section now requires a
real review verdict — an adversarial subagent pass, reviewer >= implementer — before
any blast-radius PR merges. That rule exists because on 2026-09-06 PR #160 merged a
function-deleting regression while CI was green and both bots were silent.

The `qodo` CLI itself is left in place at `~/.qodo/` (harmless, and re-enabling later
is cheaper than reinstalling).
