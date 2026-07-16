---
name: feedback-subagent-anti-delegation
description: Tools:* subagents (general-purpose) given open-ended multi-source research prompts will sometimes recursively call Agent/Task instead of doing the work — always forbid it explicitly.
metadata:
  type: feedback
---

When dispatching `general-purpose` (or any `Tools:*`) subagents for open-ended, multi-step research/fan-out work (e.g. "scout listings across many submarkets and sources"), roughly half will reach for the `Agent`/`Task` tool themselves instead of doing the work directly, then return a status narration ("the agent is running, I'll report back") as their final answer instead of actual findings.

**Why:** confirmed via a controlled comparison during the 2026-07-07 `ora-deal-sourcing-scan` run — 9 parallel `general-purpose` agents dispatched with no anti-delegation instruction: 4/9 recursed (made only 1-2 tool calls total, ~30s, then narrated a status update). Re-dispatching the same 7 markets with one added clause — "STRICTLY FORBIDDEN from using the Agent or Task tool; your final message must be the findings themselves, never a status update" — produced 0/7 recursion, all returning real, verified, substantive data (24-49 tool calls each). Same model/agent-type/task, only the explicit prohibition changed. Root cause: `general-purpose` has `Tools:*` (includes `Agent`), and nothing screens out the sub-agent applying "this looks parallelizable" reflexively one level deeper than intended.

**Cost of not doing this:** ~65k tokens burned per recursing agent for zero usable output — roughly doubles total spend on the affected markets since they have to be re-run anyway.

**How to apply:** any time dispatching a `Tools:*` subagent (general-purpose especially) for multi-source/multi-step research — deal-sourcing scans, market-monitor sweeps, county-parcel-screen fan-outs, distress-signal-monitor, or any similar ORA multi-market skill — always include in the prompt: (1) an explicit line forbidding it from calling `Agent`/`Task`/`Workflow` itself, and (2) a statement that its final message must be the actual findings, never a progress/status update. Verify by checking tool-call counts on the returned notification — under ~5 calls for a "scout many sources" task is a red flag worth re-dispatching with the guardrail even before reading the content.
