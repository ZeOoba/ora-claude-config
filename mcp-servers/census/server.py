"""
ORA Census MCP Server
---------------------
Minimal, auditable Model Context Protocol server exposing the U.S. Census Bureau
Data API (https://api.census.gov) to Claude. Single file, no third-party code
beyond the official `mcp` SDK and `httpx`. Read-only; only network target is
api.census.gov.

Authored for Oxford Realty Advisors. Feeds primary-source demographics and
industry-mix demand drivers (population, income, labor force, manufacturing /
wholesale / transportation-warehousing employment, rent, vacancy) into
deal-recon, market-monitor and acquisition-underwriting market context.

Requires env var CENSUS_API_KEY (free key: https://api.census.gov/data/key_signup.html).
The Census API rejects keyless calls (verified 2026-09-19: 302 -> missing_key.html).

Run:  uv run --with "mcp<2" --with httpx python server.py   (mcp 2.x renamed FastMCP)

Defaults to ACS 5-year (acs/acs5), the only ACS product covering every county.
Geography here is state / county only.
"""

import logging
import os
import httpx
from mcp.server.fastmcp import FastMCP

# httpx logs full request URLs at INFO, and the Census key travels in the query
# string -- silence it so the key never reaches stderr / MCP server logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

CENSUS_BASE = "https://api.census.gov/data"
API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
MAX_ROWS = 200
MAX_VARS = 40  # Census caps at 50 variables per call; keep headroom.

mcp = FastMCP("census")

_catalog_cache: dict = {}

# Verified against the 2023 ACS5 variable catalog (2026-09-19).
PROFILE_VARS = {
    "B01003_001E": "population",
    "B01002_001E": "median_age",
    "B19013_001E": "median_household_income",
    "B23025_003E": "civilian_labor_force",
    "B23025_005E": "unemployed",
    "B25064_001E": "median_gross_rent",
    "B25077_001E": "median_home_value",
    "B25002_003E": "vacant_housing_units",
    "C24050_001E": "employed_total",
    "C24050_004E": "employed_manufacturing",
    "C24050_005E": "employed_wholesale",
    "C24050_007E": "employed_transport_warehousing_utilities",
    "C24050_003E": "employed_construction",
}

# ACS suppression / not-available sentinels (-666666666 estimate not computable,
# -222222222 too few sample cases, ... -999999999). They are never real values, so
# anything at or below this ceiling is nulled before it can reach a derived metric.
SENTINEL_CEILING = -100_000_000


def _get(url: str, params: dict | None = None) -> dict | list:
    """GET a Census endpoint with the API key, return parsed JSON or {'error': ...}."""
    if not API_KEY:
        return {"error": "CENSUS_API_KEY is not set. Get a free key at "
                         "https://api.census.gov/data/key_signup.html and add it "
                         "to the server's env config."}
    q = dict(params or {})
    q["key"] = API_KEY
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            r = client.get(url, params=q)
            if r.status_code in (301, 302, 303, 307, 308):
                # Deliberately not echoing the Location header: it is server-controlled
                # and could carry the query string (and with it the key).
                return {"error": "Census API rejected the key or request (HTTP redirect). "
                                 "Check CENSUS_API_KEY is activated (the key email link must be clicked)."}
            r.raise_for_status()
            if not r.content.strip():
                return {"error": "Census returned an empty response -- no data for this "
                                 "query (check state/county FIPS, variable ids and year)."}
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Census API HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Census request failed: {type(e).__name__}: {e}"}


def _rows(table: list) -> list[dict]:
    """Census returns [header_row, *data_rows]; convert to list of dicts."""
    if not table:  # a bare [] body would otherwise raise on unpacking
        return []
    header, *data = table
    return [dict(zip(header, row)) for row in data]


def _catalog(year: int, dataset: str) -> dict:
    key = (year, dataset)
    if key not in _catalog_cache:
        res = _get(f"{CENSUS_BASE}/{year}/{dataset}/variables.json")
        if isinstance(res, dict) and "error" in res:
            return res
        _catalog_cache[key] = res["variables"]
    return _catalog_cache[key]


@mcp.tool()
def census_search_variables(keyword: str, year: int = 2023, dataset: str = "acs/acs5",
                            limit: int = 15) -> list | dict:
    """Search the Census variable catalog by keyword in the variable label or table
    concept (e.g. 'median gross rent', 'manufacturing', 'commute'). Returns variable
    id, label and concept. Use this to discover variable ids before census_get.

    Args:
        keyword: Case-insensitive text; all whitespace-separated terms must match.
        year: ACS vintage (e.g. 2023).
        dataset: Census dataset path, default 'acs/acs5'.
        limit: Max results (default 15, cap 50).
    """
    cat = _catalog(year, dataset)
    if isinstance(cat, dict) and "error" in cat:
        return cat
    terms = keyword.lower().split()
    out = []
    for vid, meta in cat.items():
        text = f"{meta.get('label', '')} {meta.get('concept', '')}".lower()
        if vid.endswith("E") and all(t in text for t in terms):
            out.append({"id": vid, "label": meta.get("label"), "concept": meta.get("concept")})
            if len(out) >= min(limit, 50):
                break
    return out


@mcp.tool()
def census_resolve_county(name: str, state_fips: str, year: int = 2023) -> list | dict:
    """Resolve a county name to FIPS codes within a state.

    Args:
        name: County name or fragment, e.g. 'Franklin' or 'Baltimore'.
        state_fips: 2-digit state FIPS (OH 39, MD 24, IN 18, WI 55, MO 29, KS 20, TN 47).
        year: ACS vintage.
    """
    res = _get(f"{CENSUS_BASE}/{year}/acs/acs5",
               {"get": "NAME", "for": "county:*", "in": f"state:{state_fips}"})
    if isinstance(res, dict):
        return res
    needle = name.lower()
    return [r for r in _rows(res) if needle in r["NAME"].lower()]


@mcp.tool()
def census_get(variables: list[str], for_geo: str, in_geo: str | None = None,
               year: int = 2023, dataset: str = "acs/acs5") -> list | dict:
    """Fetch Census estimates. Output capped at 200 rows. Values are returned raw:
    Census suppression sentinels (large negatives such as -666666666) are NOT real
    numbers -- treat any value <= -100000000 as unavailable.

    Args:
        variables: Variable ids, e.g. ['B01003_001E', 'B19013_001E'] (max 40). NAME is added automatically.
        for_geo: Census 'for' clause, e.g. 'county:049' or 'county:*' or 'state:39'.
        in_geo: Census 'in' clause, e.g. 'state:39'. Required for county-level queries.
        year: ACS vintage.
        dataset: Census dataset path, default 'acs/acs5'.
    """
    if not variables or len(variables) > MAX_VARS:
        return {"error": f"Provide 1-{MAX_VARS} variables."}
    params = {"get": ",".join(["NAME", *variables]), "for": for_geo}
    if in_geo:
        params["in"] = in_geo
    res = _get(f"{CENSUS_BASE}/{year}/{dataset}", params)
    if isinstance(res, dict):
        return res
    rows = _rows(res)
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS] + [{"_truncated": f"{len(rows)} rows total, showing {MAX_ROWS}"}]
    return rows


@mcp.tool()
def census_market_profile(state_fips: str, county_fips: str, year: int = 2023) -> dict:
    """ORA market-context profile for one county: population, median age and household
    income, labor force and unemployment, rent, home value, housing vacancy, and
    employment in industrial-demand sectors (manufacturing, wholesale, transportation/
    warehousing/utilities, construction). Adds derived unemployment rate and industrial
    employment share. ACS 5-year estimates carry sampling error and lag ~1-2 years.

    Args:
        state_fips: 2-digit state FIPS (OH 39, MD 24, IN 18, WI 55, MO 29, KS 20, TN 47).
        county_fips: 3-digit county FIPS (use census_resolve_county to find it).
        year: ACS vintage.
    """
    res = _get(f"{CENSUS_BASE}/{year}/acs/acs5",
               {"get": "NAME," + ",".join(PROFILE_VARS), "for": f"county:{county_fips}",
                "in": f"state:{state_fips}"})
    if isinstance(res, dict):
        return res
    rows = _rows(res)
    if not rows:
        return {"error": f"No Census row for state {state_fips} county {county_fips} "
                         f"(ACS5 {year}) -- check the FIPS codes."}
    row = rows[0]
    prof = {"name": row["NAME"], "source": f"ACS 5-year {year}, api.census.gov"}
    for vid, label in PROFILE_VARS.items():
        try:
            v = float(row[vid]) if row[vid] not in (None, "") else None
        except ValueError:
            v = None
        prof[label] = None if v is not None and v <= SENTINEL_CEILING else v
    lf, un = prof.get("civilian_labor_force"), prof.get("unemployed")
    emp = prof.get("employed_total")
    if lf and un is not None:
        prof["unemployment_rate_pct"] = round(100 * un / lf, 2)
    sectors = [prof.get(k) for k in ("employed_manufacturing", "employed_wholesale",
                                     "employed_transport_warehousing_utilities")]
    if emp and all(s is not None for s in sectors):  # never deflate the share on a missing sector
        prof["industrial_employment_share_pct"] = round(100 * sum(sectors) / emp, 2)
    unavailable = [label for label in PROFILE_VARS.values() if prof.get(label) is None]
    if unavailable:
        prof["unavailable_fields"] = unavailable  # suppressed/missing by Census; derived metrics omitted
    return prof


if __name__ == "__main__":
    mcp.run()
