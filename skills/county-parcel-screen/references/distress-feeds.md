# Distress feeds - foreclosure and tax-lien sources by market (added v1.4, 2026-10-02)

Companion to SKILL.md step 7. Scope: the markets where ORA owns (Franklin OH; Baltimore Co, Baltimore City,
Howard, Talbot, Wicomico, Dorchester MD; Jackson MO). Every row was checked on 2026-10-02 by three read-only
research passes (robots.txt and terms read per host; no logins, accounts, CAPTCHAs or contact). Items tagged
[UNVERIFIED] were inferred or came from search snippets, not read on the primary page.

Mortgage-maturity mining via county recorders is NOT a feed here: ruled out 2026-09-18 (no bulk recorder access
in any ORA market; Ohio's index carries no maturity date). Do not re-propose it as a bulk feed. (v1.5 adds a finalist-only manual
recorder look-up in SKILL.md step 8 — a per-document check on tens of rows, not a feed; this ruling is unchanged.)

## Rules for using these feeds
- A feed row is a LEAD INPUT, never a score input and never a call list on its own. Join to the parcel screen,
  verify (step 8), then apply the never-call floor (`data/pipeline-guard.local.json`) and ORA-affiliate flags.
- Honor each host's robots.txt and terms. A host marked MANUAL-ONLY or BLOCKED stays that way: do not script it,
  rotate user agents, or solve CAPTCHAs. The compliant routes are a person browsing, a paid export, or a
  public-records request.
- Lien and sale lists are late-stage and attrite fast (owners redeem). Early signal is still Auditor/Treasurer
  delinquency (step 7). These feeds add the "already in the legal process" tier.
- Industrial yield is low everywhere (see signal notes). Expect tens of buy-box-adjacent rows per cycle, not
  hundreds.

## Verdict key
AUTOMATABLE = official public file/API, access permitted | MANUAL-ONLY = a person browses | PAID | BLOCKED.

## Franklin OH (Columbus)
| Signal | Source | Verdict | Notes |
|---|---|---|---|
| Tax liens | Treasurer Final Tax Lien List CSV: treasurer.franklincountyohio.gov/files/assets/treasurer/v/1/documents/final-tax-lien-list-2025.csv (linked from /Delinquent-Taxes/Tax-Lien-Sale) | AUTOMATABLE | Annual; 2025 sale was 2025-11-03; the 2026 list was not posted as of 2026-10-02. 926 rows, ~87% residential. Fields: Dist/Parc/Ext #, address, improvements/land, LUC, owner, mail address, first delinquent year, net tax due, net lien value. No building SF. Join key: first 10 characters of the Treasurer ID (`010-000034-00` -> `010-000034`) vs the screen's `Parcel ID` (3-digit district + 6-digit parcel). Excludes parcels on payment plans, in bankruptcy, already in sheriff sale, or exempt, so it is a late-stage subset; only 1 of 926 overlapped the 1,154-row v04 screen even though 171 screened parcels carry Auditor delinquency [mechanism UNVERIFIED]. |
| Lien sale itself | Treasurer bulk lien sale | not a channel | Sold as a single block; the Treasurer states it is not designed for individual investors. |
| Sheriff sales | franklin.sheriffsaleauction.ohio.gov (RealAuction); schedule page sheriff.franklincountyohio.gov/Services/Real-Estate-Sales | MANUAL-ONLY | Weekly Friday 9:00 a.m. online sale; opening bid 2/3 of appraised value. Auction host returns 403 to scripted clients; ToS not reviewed. A person scans the listing weekly for commercial/industrial addresses (a few minutes). |
| Foreclosure dockets | Clerk Case Information Online: fcdcfcjs.co.franklin.oh.us/CaseInformationOnline/ | MANUAL-ONLY | 403 to scripted clients. Search excerpts say not for bulk download and that data files go through a Public Records Request [UNVERIFIED: page text not read]. Bulk route = ORC 149.43 request through clerk.franklincountyohio.gov/publicRecords/recordsRequest (draft: Claude_Workspace/02_Outputs/2026-10-02_FranklinClerk_ORC14943Request_v01.md; NOT SENT as of 2026-10-02). |
| Aggregators | SheriffIQ, foreclosure.com, ohiosheriffsales.com | PAID | Not evaluated; no commercial filter seen. |

2025-list proof pull: 93 commercial/industrial non-apartment parcels, 3 LUC 3xx. Only 6661 Huntley Rd (20,600 SF,
$95.1K lien, first delinquent 2024) is in the screen and fits the buy-box. 1444 Joyce Av (LUC 399, $72.2K lien)
is not in the screen; SF unknown.

## Maryland
Cycle status on 2026-10-02: every 2026 tax sale is complete (Baltimore City 05-18, Talbot 05-20, Dorchester 05-19,
Anne Arundel 06-03, Wicomico 06-09, Baltimore Co 08-27; Howard 06-03 per dat.maryland.gov vs 06-10 per the county
site [UNVERIFIED which is right]). Next lists: Baltimore City ~March 2027, Talbot/Dorchester/Wicomico/Anne
Arundel/Howard ~mid-April to mid-May 2027, Baltimore Co ~May-July 2027. Oct 2026 to mid-2027 is the window when
2026 certificates are in redemption; unredeemed certificates become Circuit Court right-of-redemption cases
(Case Search is blocked).

| Jurisdiction | Signal | Source | Verdict |
|---|---|---|---|
| Baltimore City | 2026 tax sale list | Daily Record PDF thedailyrecord.com/files/2026/03/TDR_20260325_C_1-64.pdf (64 pp, 2026-03-25), joined on block-lot to City RealProperty_OB (baltegis.baltimorecity.gov) | AUTOMATABLE (one PDF GET; 3-column layout, parse completeness not proven - treat counts as lower bounds) |
| Baltimore City | 2019-2023 sale history | City ArcGIS layer `Tax_Lien_Certificate_Sale_Properties1` (43,736 rows, last edit 2023-06) | AUTOMATABLE, stale after 2023. Parcels on BOTH the old layer and the 2026 list are the stronger signal (32 industrial parcels). |
| Baltimore City | Vacant Building Notices | DHCD Open Baltimore FeatureServer/1 (11,402 open notices, newest 2026-10-01) | AUTOMATABLE, live; secondary distress signal |
| Baltimore County | Tax sale | baltimorecountymd.gov | BLOCKED (CloudFront 403, not circumvented). Source manually from the county tax-sale page or the Sun legal notice, or request the file. |
| Howard | Tax sale | taxsale.howardcountymd.gov/Public/Propertylist.aspx | AUTOMATABLE (static HTML, 324 parcels) |
| Anne Arundel | Tax sale | aacounty.org 2026-tax-sale-results.pdf (958 parcels) plus list-of-liens.pdf (91 remaining liens as of 2026-09-14) | AUTOMATABLE. The remaining-liens PDF is the freshest MD distress list. |
| Wicomico | Tax sale | wicomicocounty.org DocumentCenter/View/14099 (PDF) | AUTOMATABLE |
| Talbot | Tax sale | talbotcountymd.gov 2026_TAX_SALE_RESULTS.pdf | PDF, results only |
| Dorchester | Tax sale | dorchestermd.gov DocumentCenter/View/209 (PDF) | AUTOMATABLE |
| All | Foreclosure filings | Maryland Judiciary Case Search | BLOCKED (DataDome CAPTCHA, even on robots.txt) |
| All | Foreclosure notices of sale | mddcpublicnotices.com (ToS bars scraping; liquidated damages $100/notice, $10,000/incident) | MANUAL-ONLY |
| All | Foreclosure notices | Daily Record public-notice search | PAID/manual (free view only 30 days) |
| All | State Notice-of-Intent data | Maryland open data | Residential and aggregate only; not usable |
| All | Per-parcel owner names | sdat.dat.maryland.gov | BLOCKED by Cloudflare challenge; stays a browser task |
| Anne Arundel, Baltimore City, Talbot | Sale portals `*.marylandtaxsale.com` | 403 to scripted clients | BLOCKED; use county-hosted PDFs |

Join keys: SDAT account-id prefixes are Anne Arundel 02, Baltimore Co 04, Dorchester 10, Howard 14, Talbot 21,
Wicomico 23; Baltimore City has none (ward/section/block/lot). Tax-sale list parcel numbers join as prefix +
district + account; the Anne Arundel list account is left-padded to 13 digits. Join rates were 100% on every
list. The statewide universe (SDAT via Socrata `ed4q-f8tm`, free, PUBLIC_DOMAIN, updated 2026-09-04) gives
structure SF (`sqftstrc`): 2,256 parcels at 10-50K SF (Baltimore City 773, Baltimore Co 595, Anne Arundel 332,
Howard 249, Wicomico 162, Talbot 78, Dorchester 67). The Cloudflare WAF rejects `IS NOT NULL` and long `$select`;
use IN lists and range predicates; honor Crawl-delay 1.

Proof-pull buy-box fit (10-50K SF, rows on the lists): Baltimore City 2026 15 industrial plus 109 commercial-use;
Baltimore City 2019-23 56; vacant-building 15; Howard 3; Anne Arundel 14 (6 industrial, 8 commercial); Wicomico 1
industrial (34520 Main St, 11,920 SF) plus 6 commercial; Dorchester 2 industrial (1 Washington St, 18,000 SF;
5115 Clark Canning House Rd, 13,942 SF) plus 4 commercial; Talbot 1 industrial below the band plus 2 commercial.
These are list rows, not unique properties, except the Baltimore City 2026 count.

Traps:
- Baltimore City `USEGROUP` M = apartments, NOT industrial. Industrial flag = USEGROUP I or zoning I-1/I-2/MI/IMU-1/
  IMU-2. Several USEGROUP I parcels are zoned R-8 (legacy use code); verify.
- Baltimore City liens are mostly trivial (one 18,956 SF parcel carried $767). Weight by lien size and repeat
  appearance, not presence.
- SDAT conveyance code 4 decodes to "Private non-arms-length transfer such as a foreclosure, gift or auction (4)".
  This resolves the undocumented `CONVEY1=4` note in county-endpoints.md. It lumps gifts and intra-family transfers
  with foreclosures: a "transferred under non-market terms" screen, NOT a foreclosure flag.
- Never-screened jurisdictions: Baltimore City (773 parcels in band) and Wicomico (162) are worth a screen;
  Talbot (78) and Dorchester (67) only opportunistically alongside their annual list.

## Jackson MO (Kansas City / Raytown)
Missouri foreclosure is largely non-judicial (trustee's sale), so there is no court case to search.

| Signal | Source | Verdict |
|---|---|---|
| Delinquent land tax (DLT) | 2026 Delinquent Tax Petition PDF: molawyersmedia.com/files/2026/06/2026-Jackson-County-Delinquent-Tax-Petition.pdf | AUTOMATABLE, one annual file. Suit no., amount due, legal description, owner, 23-char parcel no. Join to the CAMA table on `parcel_number`. |
| DLT results | 16thcircuit.org/delinquent-land-tax (`/courtapps/dlt/browseall.asp?index=N`) | AUTOMATABLE but post-sale only; holds 97 sold records (Aug 2024/2025), 0 industrial |
| Trustee's-sale notices | Daily Record real-estate notices (molawyersmedia.com/public-notice) | MANUAL-ONLY; CSV export is PAID. Best source for commercial foreclosures. |
| Trustee's-sale notices | mopublicnotices.com | MANUAL-ONLY (ToS bars scraping and commercial use) |
| Court cases | Missouri Case.net | BLOCKED (robots `/cnet/`, scraper prohibition, Cloudflare); adds nothing for non-judicial sales |
| Collector tax bills | mo-jackson.publicaccessnow.com/Collector/TaxSearch.aspx | MANUAL-ONLY, per-parcel finalist check |
| Assessor property record card (building SF, year built, grade) | publicaccess.jacksongov.org/search/commonsearch.aspx?mode=realprop (Commercial section of the parcel record) | MANUAL-ONLY, per-parcel finalist check. Search is gated by a disclaimer that waives claims, indemnifies the county and prohibits "applications designed to mine, gather or extract data". Gabriel clicks Agree himself in the shared browser pane (an automated Agree click is not authorized); then read the one parcel's card on screen. No bulk pull. No robots.txt rules, terms silent on scripted access beyond the disclaimer. This is the only public source of Jackson building SF (`Total Under Roof`). |
| Secondary distress | KCMO Dangerous Buildings (Socrata `ax3m-jhxx`, Crawl-delay 1) | AUTOMATABLE; join to CAMA by address (PIN does not match `property_id`) |
| Clay / Platte MO | Collector certificate sales (claycountymo.tax/tax-sale; plattecountycollector.com/taxsale7.php) | [UNVERIFIED], search snippets only; both 2026 sales were 2026-08-24 |

Status 2026-10-02: the August 2026 DLT sale was CANCELED by County Executive order (announced 2026-07-13) while
the county re-verifies tax-bill calculations (2022 figures in doubt); no new date. The 2026 petition is a stale
pre-cancellation snapshot and amounts may be restated [re-publication UNVERIFIED]. Jackson DLT is a court-run
(16th Circuit) suit-based sale of parcels 3+ years delinquent, not a Collector certificate sale. Watch
jacksongov.org (Delinquent Land Tax Sale page) and 16thcircuit.org for a new date, then re-pull the petition.

Proof pull (2026 petition): 579 suits / 579 parcels / $6.52M due; 566 joined to CAMA, 13 unmatched (suits
I2026-00362 to -00365, ~$204.8K; likely retired or replatted numbers - check the Collector). Only 56 rows (9.7%)
commercial/industrial, 2 industrial. The bulk CAMA table carries NO building SF (`total_sqft` is land SF), so
the <50K SF test cannot run in bulk; fit counts use a proxy (industrial 32xx or flex-adjacent 2262/2235/2240/2241
with `Comm_Impr` $150K-$7M) and are [UNVERIFIED] until the per-parcel record card is read (see the Assessor
portal row above). One true industrial passes: I2026-00443, 6104 Arlington Ave, Raytown (3216 wholesale trade,
land 35,286 SF, improvements $592.6K, owner L & M Real Estate LLC, $106.5K due).

Worked example, 2026-10-02: the record card for 6104 Arlington Ave shows structure 398 warehouse, one building,
Total Under Roof 12,000 SF, built 1978 (effective 1990), grade C, improvement name "Progressive Electronics"
(possible occupant; verify). Confirmed under the 50K SF cap.
- Values tab: 2026 market $813,624 (income approach; land $121,284, building $692,340), assessed $260,360;
  history 2025 $813,624, 2024/2023 $707,500, 2022 $566,000. Total market value is about $68/SF over the 12,000 SF
  building (building component alone about $58/SF). These are county ASSESSMENTS in a non-disclosure state, not
  prices; the 2024 CAMA figure used earlier ($707,500, about $59/SF total) is superseded.
- Sales tab: one recorded sale, 2004-03-31, $350,000, trustee's deed, land and building, valid sale (certificate
  of value), from a trust (Meyers trustees) to L & M Real Estate LLC. About a 22.5-year hold at 2026-10-02.
- Checks: the never-call/affiliate guard (`data/pipeline-guard.local.json`, last modified 2026-06-11),
  institutional-owner screen, Notion, HubSpot and Outlook all returned no hit by name and address; those are
  name-based checks only.
- Reading: long-hold, trust-sourced owner with a delinquency, which is the capacity-and-motivation profile the
  screen targets; it still measures capacity, not willingness (F10). The county doubts its 2022 bill
  calculations, so the amount due may be restated.

KCMO Dangerous Buildings: 375 cases, 277 address-matched, 4 industrial-coded.

Wyandotte KS: layer 1 'Tax Sale Eligible' re-pulled 2026-10-02 = 2,668 parcels (county-endpoints.md recorded 2,819
earlier); 30 industrial/warehouse use; no values or SF in the layer.

## Standing manual routines (no compliant automation exists)
1. Weekly: scan the Franklin sheriff-sale listing (Fridays) for commercial/industrial addresses.
2. Weekly: review Daily Record real-estate notices for Jackson/KC trustee's sales; filter to Raytown/KC commercial
   addresses. Judge after a month of use whether the paid CSV is worth it.
3. Annual: pull Franklin Treasurer lien CSV after the fall posting; MD lists in Mar-Jul; Jackson petition when the
   DLT sale is rescheduled.
4. Bulk docket data (Franklin foreclosures) only via a public-records request; commercial-solicitation exposure
   under ORC 149.43(B)(6) applies (see the Recorder request outcome, still pending as of 2026-10-02).
