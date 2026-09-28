# Daily Brief — live source test (2026-09-19)

Evidence behind the **FIXED SOURCE LIST** in `SKILL.md` (v2.14). Not loaded at run time.

- **Run:** 2026-09-19 (Saturday), ~13:45–15:30 ET, from the ORA workstation (same host the scheduled `ora-am-brief` task runs on).
- **Method:** every candidate fetched two ways where reachable — `curl -L -A <desktop Chrome UA>` (status, size, date-marker extraction) and the **WebFetch** tool (the tool the scheduled run actually uses; it converts to markdown and cannot execute JavaScript). A source is **KEPT** only if it returned HTTP 200, no bot challenge, **and** items carrying an explicit publication date/time that could be read back verbatim. Otherwise **DROPPED** with the reason.
- **Why two paths:** they disagree on some hosts. WebFetch refuses `bizjournals.com`, `dispatch.com` and `cincinnati.com` outright (`unable to fetch from <host>`) though `curl` gets a body; the NY Fed / Treasury endpoints are the reverse (403 or timeout via WebFetch, clean via curl — see `ora-am-brief` Block A).
- **Date reference:** every "newest" below is measured against 2026-09-19.

## KEPT — news (Sections 1, 2, 9)

| Source | URL | Result | Notes |
|---|---|---|---|
| REBusinessOnline (feed) | `https://rebusinessonline.com/feed/` | curl 200 / WebFetch OK. 20 items, full RFC-822 timestamps (`+0000`), newest 2026-09-18 14:49 UTC, oldest 13:03 UTC; 8 of 20 industrial-ish | **National**, not market-filtered (TX, IL, GA, NJ, CA in the sample) — keep only target-market items. Feed depth is ~2 hours on a busy day |
| REBusinessOnline (industrial category) | `https://rebusinessonline.com/category/industrial/` | WebFetch OK. Day-granular dates ("September 18, 2026"), newest 09-18, oldest 09-17 in first 10 | Use when the feed's window is too shallow. Day-only dates |
| ConnectCRE (feed) | `https://www.connectcre.com/feed/` | curl 200 / WebFetch OK. 10 items, timestamps, newest 2026-09-18 22:13 UTC, oldest 20:07 UTC; 2 of 10 industrial | Thin (≈2 h depth); NYC/CA-heavy |
| Commercial Observer (feed) | `https://commercialobserver.com/feed/` | curl 200 / WebFetch OK. 17 items, timestamps, newest 09-18 21:24 UTC, oldest 09-17 17:35 UTC; 7 of 17 industrial/logistics | Best depth (~1.5 days). NYC/LA/FL-heavy |
| Bisnow (feed) | `https://www.bisnow.com/rss` | curl 200 / WebFetch OK. 10 items, timestamps in **-0400**, each with Market + Category tags, newest 09-18 18:44 | Convert to ET is a no-op; convert `+0000` sources to ET |
| Bisnow D.C. | `https://www.bisnow.com/washington-dc` | curl 200 (`datetime=` attrs) / WebFetch OK. Newest 09-18, day-granular | **Not date-sorted** — an 08-13 item sat at position 4 among 09-14…09-18 items. Filter per item, never by position. Only DC/NoVA/MD source that works |
| Indianapolis Business Journal | `https://www.ibj.com/real-estate` | curl 200 (100 date markers) / WebFetch OK. Newest 09-18, oldest 09-02 in first 10 | Indianapolis only. Its RSS (`/rss`) is DROPPED (newest item 2022) |
| Richmond BizSense (feed) | `https://richmondbizsense.com/feed/` | curl 200 / WebFetch OK. 11 items, timestamps, newest 09-18 13:40 UTC | Richmond; commercial-RE roundup ("The Pipeline") published ~06:00 UTC daily |
| Business Record, Des Moines (feed) | `https://www.businessrecord.com/feed/` | curl 200 / WebFetch OK. 10 items, timestamps, newest 09-18 20:26 UTC | General business, not RE-only — filter |
| BizTimes (feed) | `https://www.biztimes.com/feed/` | curl 200 / WebFetch OK. 10 items, timestamps, newest 2026-09-19 04:32 UTC | **Milwaukee**, not Madison — a Wisconsin proxy only; label it so |
| Basis Industrial (competitor, Section 9) | `https://basisindustrial.com/` | curl 200 / WebFetch OK. Home page carries a dated news list (`M.D.YY`): 9.4.26, 8.20.26, 7.6.26, 6.24.26, 5.22.26, 4.23.26 | Sparse (~1 item/month) and South-Florida/Atlanta/NJ-centric. `/news/` (index) is 404 — use the home page |

## KEPT — legislation / regulation (Section 7)

| Source | URL | Result | Notes |
|---|---|---|---|
| Kansas Legislature bill-status API | `https://www.kslegislature.gov/li/api/v13/rev-1/bill_status/` | **curl only** (200, ~8 MB JSON, 1,522 bills). Every bill carries `HISTORY[].occurred_datetime`. WebFetch not attempted — 8 MB exceeds what a markdown converter should be handed | Newest recorded action anywhere: **2026-05-05** (session over) → a 7-day window is empty outside session. That is a verified null, not a fetch failure. Filter locally with Python |
| Federal Register API | `https://www.federalregister.gov/api/v1/documents.json?per_page=N&order=newest&conditions%5Bterm%5D=<term>&conditions%5Bpublication_date%5D%5Bgte%5D=<YYYY-MM-DD>` | **curl only, percent-encode the brackets.** `term=warehouse&gte=2026-09-12` → 43 results, every one with `publication_date` (newest 2026-09-18) | Dated and reliable but **low precision** — the sample was trade-remedy notices (steel wire rod, rebar), not CRE law. The same window with a multi-term `OR`/quoted-phrase query returned 0 through WebFetch; not tested equivalently via curl, so do not assume either way |

## DROPPED — with reason

| Source | Result |
|---|---|
| GlobeSt (`/property-type/industrial/`, `/sectors/industrial/`, `/feed/`) | **403 + bot challenge** on every path via both curl and WebFetch |
| All `bizjournals.com` (Columbus, Cincinnati, Baltimore, Kansas City, Louisville, Washington) | curl **403 + challenge**; WebFetch refuses the domain. This is every Business First / Business Courier / Business Journal in the target markets |
| `dispatch.com` (Columbus), `cincinnati.com` (Enquirer) | WebFetch refuses the domain; curl returns 200 but pages have no machine-readable dates |
| ConnectCRE `/stories/category/industrial/` | 200, but its only date markers are **2018** — the page is not a live index |
| IBJ RSS (`/rss`), Madison.com RSS, The Real Deal feed | 200, but newest items 2021–22 / 2023-10 / 2022 → stale feeds |
| Baltimore Daily Record | 403 |
| Baltimore Banner business feed, Nashville Post real-estate feed, CRE Daily feed | 200 but 770 / 772 / 988 bytes — valid RSS envelope, **no items** |
| Insider Louisville feed, Columbus CEO feed, Bisnow `/national/industrial`, Basis `/news/`, Business Record `/category/real-estate/` | 404 |
| Grand Rapids Business Journal | `SEC_E_CERT_EXPIRED` — expired TLS certificate. Reachable only with `curl -k`, which this skill will not instruct |
| MLive (Grand Rapids), Daily Reporter (WI) | 403 |
| Kansas City Star, Kansas City Business Journal alternative | connection timeout / reset |
| **CoStar, LoopNet, Crexi** | **403 Access Denied / Cloudflare challenge** (confirmed 2026-09-19) — as expected, paywalled/blocked. **Not built on.** |
| Ohio (`legislature.ohio.gov`, Register of Ohio) | curl 200 but the 873-byte body is a "Planned Website Maintenance" page; WebFetch fails TLS verification; the LIS API host is unreachable |
| Maryland (`mgaleg.maryland.gov`) | bill index loads (200) but WebFetch found **no action dates** — sponsor and title only. The RSS URL is a 404-in-200 |
| Indiana (`iga.in.gov`) | JS shell / bot challenge — no content |
| Missouri (`house.mo.gov/BillList.aspx`) | WebFetch **404**; curl 200 (2.2 MB) but the only dates are bill *effective* dates ("August 28, 2026"), not activity |
| Wisconsin (`docs.legis.wisconsin.gov`) | navigation hub, no dated list; alternate paths return 503 |
| Tennessee (`wapp.capitol.tn.gov`) | per-bill lookup only; the landing URL returns "Bill Not Found". No feed |
| congress.gov most-viewed RSS | dated, but `pubDate` is the **feed generation date**, not any bill action (WebFetch confirmed) |
| LegiScan, Plural/OpenStates | 403 + challenge |

## Coverage by target market (what the KEPT list actually covers)

| Market | Local source that works | Gap |
|---|---|---|
| OH (Columbus, Cincinnati, Cleveland, Dayton) | none | **Gap** — national feeds only |
| MD / DC / NoVA | Bisnow D.C. | Baltimore metro: **gap** |
| IN (Indianapolis) | IBJ | — |
| MO/KS (Kansas City) | none | **Gap** |
| WI (Madison) | BizTimes (Milwaukee proxy) | Madison itself: **gap** |
| MI (Grand Rapids) | none | **Gap** |
| VA (Richmond) | Richmond BizSense | — |
| IA (Des Moines) | Business Record | — |
| KY (Louisville) | none | **Gap** |
| TN | none | **Gap** |

Five of ten target clusters have no working local news source (OH, MO/KS, MI, KY, TN) and two are only partly covered (MD: DC/NoVA via Bisnow, no Baltimore; WI: Milwaukee proxy, no Madison). The national feeds (REBO, ConnectCRE, Commercial Observer, Bisnow, plus Basis for competitor news) carry them. This is a real limit of what is fetchable, not a skill defect.

## Legislature coverage — result

Only **Kansas** exposes a dated, filterable machine source. OH, MD, IN, MO, WI, TN expose no dated recent-activity surface reachable by plain fetch. In September nearly every one of these bodies is out of session regardless, so even a working feed would return empty. Section 7 therefore stays WebSearch-led, with the Federal Register API and the Kansas API as the only directly-fetched dated inputs, and with mandatory date tagging.

## Section 2 stays thin by design

Closed-sale price / SF / cap rate / buyer / seller data lives on LoopNet, CoStar and Crexi. All three return 403 to this host. The kept feeds carry press-release-style sale items (SF and buyer, usually no price or cap rate). Sub-$10M shallow-bay closings in the target markets will usually not appear. The brief must say so rather than pad.
