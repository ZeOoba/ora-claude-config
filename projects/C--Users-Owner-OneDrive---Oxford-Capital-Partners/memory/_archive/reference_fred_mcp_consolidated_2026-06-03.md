---
name: reference-fred-mcp
description: "FRED economic-data MCP server — self-authored, wired into Claude Code user config; how to use, extend, and rotate the key"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9a03b20e-6e9e-45ac-b663-4cc7c3691d10
---

Live FRED (St. Louis Fed) economic-data MCP, wired 2026-05-31. Feeds live macro
into underwriting (DSCR/cap-rate/replacement-cost) and the `market-monitor` skill,
replacing manually-tracked Treasury/SOFR figures in [[market_general]].

**Server:** `C:\Users\Owner\.claude\mcp-servers\fred\server.py` — single self-authored
file (official `mcp` SDK + `httpx` only; no third-party server code, fully auditable).
Runs via `uv run --directory <dir> --with mcp --with httpx python server.py`.

**Config:** registered in `C:\Users\Owner\.claude.json` (user scope) under `mcpServers.fred`
via `claude mcp add`. The free API key is stored there as env `FRED_API_KEY` (NOT in this
memory). Backup of pre-change config: `.claude.json.bak-fred`. Key source / rotation:
https://fredaccount.stlouisfed.org/apikeys

**Tools:** `fred_search_series(text, limit)`, `fred_series_info(id)`,
`fred_observations(id, start_date, end_date, frequency, units, sort_order, limit)`,
`fred_latest(id)`.

**Series IDs used in ORA work:** DGS10/DGS5/DGS2 (Treasuries), SOFR, T10Y2Y (spread),
CPIAUCSL (CPI; use units="pc1" for YoY%), MORTGAGE30US, FEDFUNDS; state payrolls
OHNA/MDNA/INNA/WINA/MONA/KSNA/TNNA.

**Verified live 2026-05-31:** DGS10 4.45%, SOFR 3.62%, MORTGAGE30US 6.53%, CPI YoY 3.78%.

To add the parallel ATTOM property-data MCP later, ATTOM ships its own official MCP
server (launched 2026-01-29) — only credentials needed, no custom server. Pilot data
quality first via Property Navigator ($499/yr or 7-day trial) before API spend.
