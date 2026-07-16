"""
ORA FRED MCP Server
-------------------
Minimal, auditable Model Context Protocol server exposing the St. Louis Fed
FRED API (https://fred.stlouisfed.org) to Claude. Single file, no third-party
code beyond the official `mcp` SDK and `httpx`.

Authored for Oxford Realty Advisors. Feeds live macro (Treasury yields, SOFR,
CPI, employment) into underwriting (DSCR / cap-rate / replacement-cost) and the
market-monitor skill, replacing manually-tracked figures in market_general.

Requires env var FRED_API_KEY (free key: https://fredaccount.stlouisfed.org/apikeys).

Run:  uv run --with mcp --with httpx python server.py

Useful series IDs for ORA workflows:
  DGS10  10-Yr Treasury        DGS5   5-Yr Treasury     DGS2   2-Yr Treasury
  SOFR   Secured Overnight Fin Rate                     T10Y2Y 10Y-2Y spread
  CPIAUCSL  CPI (all urban)    PAYEMS National payrolls MORTGAGE30US 30Y mortgage
  FEDFUNDS  Fed Funds rate     GDP    Gross Domestic Product
  State payrolls: OHNA, MDNA, INNA, WINA, MONA, KSNA, TNNA
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

FRED_BASE = "https://api.stlouisfed.org/fred"
API_KEY = os.environ.get("FRED_API_KEY", "").strip()

mcp = FastMCP("fred")


def _get(path: str, params: dict) -> dict:
    """Call a FRED endpoint with the API key and JSON output, return parsed JSON."""
    if not API_KEY:
        return {"error": "FRED_API_KEY is not set. Get a free key at "
                         "https://fredaccount.stlouisfed.org/apikeys and add it "
                         "to the server's env config."}
    q = dict(params)
    q["api_key"] = API_KEY
    q["file_type"] = "json"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{FRED_BASE}/{path}", params=q)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"FRED API HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"FRED request failed: {type(e).__name__}: {e}"}


@mcp.tool()
def fred_search_series(search_text: str, limit: int = 10) -> list:
    """Search FRED for economic data series by keyword. Returns series id, title,
    frequency, units, and the available date range. Use this to discover the
    series_id for an indicator before pulling observations.

    Args:
        search_text: Keywords, e.g. "10-year treasury", "SOFR", "Ohio payrolls".
        limit: Max results (default 10).
    """
    data = _get("series/search", {"search_text": search_text, "limit": limit,
                                  "order_by": "popularity", "sort_order": "desc"})
    if "error" in data:
        return [data]
    out = []
    for s in data.get("seriess", []):
        out.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "frequency": s.get("frequency_short"),
            "units": s.get("units_short"),
            "seasonal_adjustment": s.get("seasonal_adjustment_short"),
            "observation_start": s.get("observation_start"),
            "observation_end": s.get("observation_end"),
        })
    return out or [{"note": f"No series found for '{search_text}'."}]


@mcp.tool()
def fred_series_info(series_id: str) -> dict:
    """Return metadata for a FRED series (title, units, frequency, date range,
    last updated, notes)."""
    data = _get("series", {"series_id": series_id})
    if "error" in data:
        return data
    arr = data.get("seriess", [])
    if not arr:
        return {"note": f"No series with id '{series_id}'."}
    s = arr[0]
    return {
        "id": s.get("id"),
        "title": s.get("title"),
        "units": s.get("units"),
        "frequency": s.get("frequency"),
        "seasonal_adjustment": s.get("seasonal_adjustment"),
        "observation_start": s.get("observation_start"),
        "observation_end": s.get("observation_end"),
        "last_updated": s.get("last_updated"),
        "notes": s.get("notes"),
    }


@mcp.tool()
def fred_observations(series_id: str, start_date: str = "", end_date: str = "",
                      frequency: str = "", units: str = "",
                      sort_order: str = "desc", limit: int = 25) -> dict:
    """Pull observations (the actual data points) for a FRED series.

    Args:
        series_id: e.g. "DGS10", "SOFR", "CPIAUCSL".
        start_date: YYYY-MM-DD (optional).
        end_date: YYYY-MM-DD (optional).
        frequency: optional resampling: d,w,bw,m,q,sa,a (lower freq only).
        units: optional transform: lin (level), chg, ch1, pch, pc1 (YoY % change), etc.
        sort_order: "desc" (newest first, default) or "asc".
        limit: max observations (default 25).
    """
    params = {"series_id": series_id, "sort_order": sort_order, "limit": limit}
    if start_date:
        params["observation_start"] = start_date
    if end_date:
        params["observation_end"] = end_date
    if frequency:
        params["frequency"] = frequency
    if units:
        params["units"] = units
    data = _get("series/observations", params)
    if "error" in data:
        return data
    obs = [{"date": o.get("date"), "value": o.get("value")}
           for o in data.get("observations", [])]
    return {"series_id": series_id, "count": len(obs), "observations": obs}


@mcp.tool()
def fred_latest(series_id: str) -> dict:
    """Convenience: return the single most recent observation for a series —
    e.g. 'what is the 10-Yr Treasury right now' -> fred_latest("DGS10")."""
    data = _get("series/observations",
                {"series_id": series_id, "sort_order": "desc", "limit": 1})
    if "error" in data:
        return data
    obs = data.get("observations", [])
    if not obs:
        return {"note": f"No observations for '{series_id}'."}
    return {"series_id": series_id, "date": obs[0].get("date"),
            "value": obs[0].get("value")}


if __name__ == "__main__":
    mcp.run()
