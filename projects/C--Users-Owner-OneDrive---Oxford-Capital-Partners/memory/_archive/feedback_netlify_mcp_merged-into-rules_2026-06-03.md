---
name: Netlify MCP — intermittent; CLI is the safe fallback
description: Netlify MCP has had intermittent failures; as of 2026-04-14 it is working again. Try MCP first, fall back to npx netlify-cli on any error.
type: feedback
originSessionId: 78e7b6a7-c477-4a50-800a-8f1487747653
---

Netlify MCP (`mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-*`) has had two distinct failure modes in April 2026:
1. `selectSchema` ZodError — Anthropic MCP proxy serialized the schema param as a string instead of an object
2. "Connector's server isn't responding" — transient server outage

As of **2026-04-14** the MCP is responding correctly again (`get-user` returned clean JSON — Gabriel Goldberg, 3 sites).

**How to apply:**
- Try MCP first for Netlify operations.
- On any error, fall back to `npx netlify-cli` without retrying — the CLI is authenticated as ggoldberg@oxfordra.net.
- Key commands: `sites:list`, `deploy`, `status`.
- oxfordra.net Site ID: `95ac0a0f-a84d-4400-b919-b8d7a8526646`.
- Do not recommend "reconnect the connector on claude.ai/settings/connectors" as a fix — past failures were server-side, not auth-related.

## History
- 2026-04-09: Filed as hard failure (ZodError). CLI-only workflow.
- 2026-04-14 (AM): Sunday maintenance saw evolved error ("server not responding").
- 2026-04-14 (PM): Manual verification — MCP working again. Reframed as intermittent; CLI demoted to fallback. (reconciled 2026-04-17)
