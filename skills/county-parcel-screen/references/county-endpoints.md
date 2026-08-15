# Verified county data endpoints (append new counties after each market run)

## Franklin County OH (Columbus) — FULL STACK, best-in-class
- REST: https://gis.franklincountyohio.gov/hosting/rest/services/ParcelFeatures/Parcel_Features/MapServer/0
  Fields: PARCELID ('010-104049'), CLASSCD (DTE), BLDGAREA (commercial SF — RARE), OWNERNME1,
  PSTLNME1/PSTLADDRES/PSTLCITYSTZIP (tax mail), SALEDATE/SALEPRICE, LNDVALUEBASE/BLDVALUEBASE/TOTVALUEBASE,
  ACRES, TOTVALUETIF, RENTAL. maxRecordCount 3000, pagination yes. HEIGHT/COND/GRADE = 0% filled (ignore).
- Bulk: https://apps.franklincountyauditor.com/Outside_User_Files/{YYYY}/
  Monthly 'Appraisal' (Build.txt: YRBLT/WALLHGT/PHYCOND/CONSTR/GRADE; Parcel/Land/Permit) and
  'Tax Accounting' (TaxDetail.txt: TotPrior/TotPenalty = delinquency; Transfer*.txt: per-parcel
  transfer history w/ OwnerName grantees; Sa.txt: special assessments; RentalContact.txt: OWNER PHONES;
  Payment2022-24: payment velocity — UNUSED yet). Tax-file IDs are '"010-104049-00"' — strip quotes, first 10 chars.
- Calibration: 1.65 county-flat (n=57, 2024-26); ZIP-level ratios 1.04-1.99 — prefer ZIP-level.
- Tax Accounting vintage: **CORRECTED 2026-07-24** — the 2026 folder does NOT lag any more. Live listing that day:
  `2026/2026-07-15 Tax Accounting/` present (9 days old), alongside 05-15/06-15/07-15 Appraisal. The prior note
  ("latest seen 2025-07-15") was stale by a full year and would have sent a run to the 2025 files. ALWAYS list
  `/Outside_User_Files/{YYYY}/` and read the newest dated folder rather than trusting this doc's date.
- Tax Accounting file set (2026-07-15 drop, sizes as pulled): TaxDetail.xlsx 86MB (506,988 rows — `Parcel Id`
  '010-000001-00' + TotPrior/TotPenalty/TotInterest/TotSA/TotTotal; delinquency = TotPrior>0 or TotPenalty>0),
  Transfer010.xlsx 43MB (Columbus 010- series, sellers-in-motion), Tab-Delimited.zip 117MB (all files),
  RentalContact.xlsx 6MB (`PARCEL ID`/Owner_Name/Owner_BusinessName/Owner_Address* — NOTE: overwhelmingly
  residential; only 20 of 1,154 industrial parcels matched, so do not plan on it for owner phones),
  Sa.xlsx 6MB, Payment2023/24/25.xlsx, Parcel/Value/TaxDistribution.xlsx.
- Join: GIS `PARCELID` '010-104049' vs tax `Parcel Id` '010-104049-00' → strip quotes, take first 10 chars.
  Verified 1,154/1,154 = 100% on the 2026-07-24 run. Assert the match rate and abort below ~90%.
- Parse with python-calamine (`CalamineWorkbook.from_path`); openpyxl is unusable on the 507K-row TaxDetail.
- Franklin delinquency base rate (2026-07-15): 41,659 of 506,988 county parcels carry prior/penalty > 0 (~8.2%);
  industrial 10–80K SF ran 171/1,154 (14.8%) — elevated vs the county base but not dramatically.
- **Validity signal (found via county-sales-monitor pilot, 2026-08-15):** the GIS parcel layer's `VALID` field
  exists in the live schema but was null on 100% of a 205-parcel industrial pull — not usable. The Transfer*.txt
  files carry an `IsValid` field ('T'/'F') that IS well-populated and is the usable non-arms-length signal.
- **Bulk-file recording lag (same pilot):** the live GIS layer's SALEDATE can run ~1 month ahead of the newest
  Tax Accounting transfer-file drop (e.g. GIS showed sales through 08-14 while the newest Transfer* folder was
  still the 07-15 drop) — a windowed pull against Transfer*.txt alone will miss the most recent weeks' deeds
  until the next monthly folder posts. Not a bug, a recurring gap to diff against on repeat runs.

## Hamilton County OH (Cincinnati) — RICH REST, NO COMMERCIAL SF
- REST: https://services.arcgis.com/JyZag7oO4NteHGiq/arcgis/rest/services/Open_Data/FeatureServer/51
  (mirror: cagisonline.hamilton-co.org/arcgis/rest/services/Countywide_Layers/QueryLayers/MapServer/1)
  Fields: PARCELID (12-digit), CLASS (DTE as INTEGER), OWNNM1, MLNM1/MLADR1/MLADR2,
  MKTLND/MKTIMP/MKT_TOTAL_VAL, SALDAT(epoch ms)/SALAMT/VALID, ACREDEED,
  ANNUAL_TAXES/DELQ_TAXES/DLNQDT/FORECL_FLAG/RENT_REG_FLAG — DELINQUENCY IN-LAYER, county-current.
  maxRecordCount 2000. NO building SF / year built anywhere in REST.
- Bulk: https://hcauditor.org/download/revalue/ — Monthly_tax_information.xlsx (115MB),
  bldginfo.xlsx (RESIDENTIAL ONLY — useless for industrial), HistoricSalesExport.xlsx (59MB,
  transfer history — sellers-in-motion source, UNPROCESSED yet).
- Commercial SF paths: CAGIS Building Footprints spatial join (data-cagisportal.opendata.arcgis.com)
  or per-parcel hcauditor.org pages. Calibration: 1.61 (n=182, 2023-06+).

## Butler County OH (West Chester/Liberty Twp) — CSV GOLD, WAF-GATED  [v01 RUN 2026-06-09]
- REST: https://maps.butlercountyauditor.org/arcgis/rest/services/PARCELSEARCH/MapServer/0
  (layer name CURRENTPARCELS, maxRec 1000, pagination OK w/ resultOffset+orderByFields=OBJECTID).
  Fields: PIN ('A0700005000027'), OWNER, LOCATION, LUC (string), CLASS ('I' for all 300-399),
  ACRES, MAILNAM1/2/MAILADR1-3, CA31_YRBLT (REAL year built — YRBLT/SFLA are RESIDENTIAL ONLY, 0
  for industrial), LANDVAL (LAND value only), SALEDT ('DD-MON-YY')/PRICE + VSALEDT/VPRICE (valid
  sale)/VSALEVAL ('0'=valid arm's-length), ASR (auditor assessment-sales ratio %, ~59 median),
  TIF_PARCEL/ABT_PARCEL/EXM_PARCEL ('Y'). CRITICAL: VALUE20 (total-value field) is NULL for ALL
  industrial — NO total/improvement value and NO building SF in REST. Use bulk Owners CSV for value.
  Industrial universe: LUC 300-399 = 2,293 parcels (350 wh/dist 916, 340 heavy 313, 370 mining 151
  EXCLUDE, 300 vacant 445 EXCLUDE, 330 light 142, 320 320 wh 92, others).
- Bulk CSVs (current path 2026-06: https://auditor.bcohio.gov/Documents/Real%20Estate/Reports/ —
  index moved to /real_estate/real_estate_reports/index.php; scrape it for current date-stamped names):
  'Owners Report {M-D-YYYY}.CSV' (46MB, 35 cols: PARCEL,OWNER1/2,MAILNAME1/2,MAILADR1-3,SALEDATE,
  PRICE,YRBLT,SFLA,TAXABLE LAND,TAXABLE BLDG,ABATED VALUE,EXEMPT VALUE,TIFVALUE,OOC,HOM — THE value
  source: market=(TAXABLE LAND+BLDG+ABATED+EXEMPT+TIF)/0.35),
  'Delinquent Tax List {M-D-YYYY}.CSV' (PARID,CURRENTYEARDUE,LUC,PRIORYEARDUE),
  '{M-D-YYYY} Property Sale.CSV' (23 cols: Deed Transfer Number,Sale Date,Price,No Of Parcels,
  NEW OWN1/2,Grantor1/2,PARID,TOT_VALUE25 [=taxable@35%],LUC,CLASS — DIRECT grantor/grantee, the
  sellers-in-motion source).
  403 unless FULL browser headers: UA + Accept(text/html) + Referer(.../real_estate_reports/index.php)
  + Sec-Fetch-Dest/Mode/Site/User + Upgrade-Insecure-Requests.
- CALIBRATION (EMPIRICAL): auditor-to-market factor 0.648 (n=33 valid arm's-length sales). UNLIKE
  Franklin/Hamilton (1.6x), Butler's grossed market (taxable/0.35) OVERSTATES sale prices ~1.5x ->
  modeled_market = grossed*0.648. 3-way validated: REST valid-sale 0.648; price/TOT_VALUE25 1.904x0.35=
  0.666; ASR 59.08%->0.593. NO commercial SF anywhere -> pre-SF 0-95 scale (basis on age+impr/acre proxy).
- Also: files.bcohio.gov Nextcloud shares — BOR.zip (Board of Revision complaints = distress signal).

## Clermont County OH (Batavia; 754 deal county) — THIN
- REST: https://maps.clermontauditor.org/arcgis/rest/services/Parcels/ParcelsWM/MapServer/0
  Fields: PIN (dotted '413215F117.' — opaque string), FULLADDR, OWN1/OWN2, MAIL1/MADDR1-3, LUC, ACRES.
  NO values/SF/sales in layer. Sales join: .../Sales/ParSales/MapServer/12 (PIN,PRICE,SALEDATE,SALETYPE).
- No public bulk tax extract. Values/SF: ClermontParcels.zip DBF (81MB, untested) at
  maps.clermontcountyohio.gov/gis/, or CAMA extract by request from auditor GIS dept, or
  per-parcel scrape (370 industrial parcels — small). Delinquency: PDF-only (MH list).

## Warren County OH (Lebanon/Mason) — THINNEST
- REST: https://maps.co.warren.oh.us/arcgis/rest/services/Dynamic/ParcelLabelsAddr/MapServer/0
  Fields: SDWLL_NBR (10-digit), OWNER_NAME, ADDRESS_LINE_1/2, MAIL_NAME/MAIL_ADDRESS_1-3/MAIL_ZIP,
  USE_CODE_DSC ('350-INDUSTRIAL WAREHOUSE' — filter LIKE '3%' on THIS field, NOT CLASS_CODE), ACREAGE.
  NO values/SF/sales public. Enrich: scrape auditor.warrencountyohio.gov/PropertySearch/ (481 parcels)
  or order CAMA extract (GIS dept 513-695-1000). FTP public/public has only stale 2010 BOR file.

# === MARYLAND (run 2026-06-09) ===

## Anne Arundel County, MD (Mid-Atlantic / BW corridor) — SDAT statewide, OWNER NAMES STRIPPED  [v01 RUN 2026-06-09]
- REST (PRIMARY — MdProperty View parcel points, statewide CAMA, one service covers ALL MD counties):
  https://mdgeodata.md.gov/imap/rest/services/PlanningCadastre/MD_PropertyData/MapServer/0
  (NOTE host = mdgeodata.md.gov, NOT geodata.md.gov which 406s. Discover service URLs via ArcGIS Online
  item lookup: org `mdimapdatacatalog`, item id d34ee04f... 'Maryland Property Data'.) maxRec 2000,
  pagination resultOffset+orderByFields=OBJECTID. Filter by JURSCODE (Anne Arundel = 'ANNE'; 4-char codes
  e.g. WORC=Worcester — NOT 'AACO'). 222,817 ANNE parcels; 17,146 with CIUSE.
- Key fields: ACCTID (15-digit acct), ADDRESS/CITY/ZIPCODE (situs), OWNADD1/OWNADD2/OWNCITY/OWNSTATE/OWNERZIP
  (owner MAILING addr), LU/DESCLU (land-use: I=Industrial, C=Commercial, EC/E=Exempt), CIUSE/DESCCIUSE
  (commercial-industrial use code + desc), SQFTSTRC (BUILDING SF — populated!), YEARBLT, ACRES/LANDAREA,
  ZONING, TRADATE (YYYYMMDD)/CONSIDR1 (sale price)/CONVEY1 (how-conveyed, no public domain), GR1LIBR1
  (grantor liber), NFMLNDVL/NFMIMPVL/NFMTTLVL (New Appraised land/impr/FULL value — near full market),
  EXCLASS/DESCEXCL (exemption), SDATWEBADR (per-parcel SDAT link), MDPVDATE/SDATDATE (vintage, 2026FEB).
- *** OWNER NAMES NOT PUBLISHED *** — MdProperty View public extract strips owner names; ONLY owner mailing
  ADDRESS is public. Names sometimes leak in 'C/O <name>' lines of OWNADD1. CONSEQUENCES: entity-owner 10-pt
  component uncomputable (rescale 90->100); estate_v2 fires only on C/O names (0 hits != 0 estates);
  institutional-NAME exclusion runs on C/O text only -> add a PORTFOLIO-SIZE proxy (>=10 parcels at one
  mailing addr = VERIFY-INSTITUTIONAL). RECOVER names Stage 2: SDAT Real Property Search (SDATWEBADR) or
  mdlandrec.net (MD Land Records). St John Properties + 2560/2066 Lord Baltimore Dr = BW-corridor industrial
  portfolios caught by the portfolio proxy.
- Industrial product CIUSE: 50000 Warehouse, 50710 WH Condominium, 51000 WH Distribution, 52000 WH
  (Loft/R&D/Flex), 55000 Manufacturing = 1,263 product parcels. EXCLUDE 53000 Mini-Storage, 56000 Tank Farm,
  57000 Cement, 54000 Truck Terminal. (LU='I' alone over-pulls vacant/yard — filter on product CIUSE.)
- CALIBRATION (EMPIRICAL): factor = median(CONSIDR1/NFMTTLVL), product arm's-length (>=100k,<=3yr,ratio 0.5-4)
  = 1.093 (n=104). MD assesses ~full market so factor ~1.0-1.1 (NOT OH 1.6x). ZIP factors (n>=3): 21012=1.77
  21060=1.04 21061=1.95 21076=1.07 21090=1.39 21108=1.41 21113=1.00 21226=1.27 21401=1.84 21403=2.32.
- Other MD CAMA services (same org mdimapdatacatalog, host mdgeodata): MD_ComputerAssistedMassAppraisal
  MapServer/1 CAMA Core (PR_ENCSQFT cumulative enclosed SF, CM_CIUSE — sparse), /0 Detailed Building Char,
  /2 Land, /3 Building Subarea. Howard='HOWA', Baltimore Co='BACO' (verify codes) — SAME service, same method.
- Delinquency: NOT pulled this pass. Stage 2 = Anne Arundel County tax-sale list (annual, realtaxdeed/
  official county site) + SDAT per-parcel. No in-layer delinquency field.

## Howard County, MD (BWI/DC corridor)  [v01 RUN 2026-06-09]
- SAME mdgeodata MD_PropertyData service as Anne Arundel; filter JURSCODE='HOWA'. 751 industrial product
  parcels (CIUSE 50000/50710/51000/52000/55000). Same field set; **owner names SDAT-scrubbed (mailing addr
  only)** — same consequences as Anne Arundel (entity 10-pt dropped, estate_v2 can't fire, institutional via
  mail/portfolio proxy). SF coverage 59% (440/751; warehouse-condo CIUSE 50710 has null SQFTSTRC → score
  NO-SF size 7/basis 10 neutral).
- CALIBRATION: factor 1.79 (n=60 product-only arm's-length) — use product-only, NOT the broad-industrial
  1.49 (n=97). Strong ZIP spread: 20723~1.07, 21075~2.34, 21046~2.05 (apply ZIP where n>=3). MD SDAT
  'new appraised full value' understates Howard industrial market ~1.8x.
- Institutional leakage is HEAVY in the Jessup/Dorsey BWI corridor (Prologis, Link Logistics/Blackstone) —
  28 parcels caught by the mail-address screen; without it they rank A (F8). SDATWEBADR per-parcel SDAT
  Real Property page is WAF/session-gated (403 to urllib AND WebFetch) — Stage-2 BROWSER task for owner names.
- Delinquency: no public Howard feed pulled; Stage 2 = Howard County tax-sale list.

## Baltimore County, MD (Baltimore metro)  [v01 RUN 2026-06-09] — NAMES RECOVERABLE
- mdgeodata MD_PropertyData service, JURSCODE='BACO'. *** KEY: unlike the name-scrubbed state extract,
  Baltimore County publishes OWNER NAMES on its OWN GIS — join the state ACCTID to county
  `https://bcgis.baltimorecountymd.gov/.../Property/MapServer/1` on ACCTID[4:]=TAXPIN (1,274/1,276 matched).
  This restores the FULL 0-100 scale (entity-owner + named estate_v2 + named institutional/ORA-self exclusion).
  Check every MD county for a county-level GIS that re-publishes names before falling back to SDAT browser pulls.
- FULL disclosure once joined: SQFTSTRC (SF, 89% pop), CONSIDR1/TRADATE (sale price/date), NFMTTLVL
  (full appraised value) all public in one layer. estate_v2 → 17 genuine fiduciary hits, 0 FP. Institutional
  by name: First Industrial Realty Trust, EQT Exeter funds, STAG. ORA-self: Eric Goldberg Family LLC excluded.
- CALIBRATION + F2 WARNING: ≤3yr factor 1.639 (n=73), but 5yr factor only 1.211 (n=169) — recent 2023-26
  industrial sales run ~64% above the triennial-lagged assessed value, i.e. assessments are STALE in a hot
  market. Deep modeled discounts (0.4-0.8) are PARTLY an assessment-lag artifact, not verified bargains —
  confirm true $/SF against the actual recent sale price per finalist. ZIP factors range wildly 0.85-3.46
  (21227=2.24, 21030=1.06, 21222=3.46); county 1.639 is fallback only. HOLD-FIX F1: MD records consideration
  cleanly — only 1 nominal <$25K transfer in the universe (far fewer $0 re-titlings than Ohio).
- **CONVEY1 code (found via county-sales-monitor pilot, 2026-08-15):** a `CONVEY1` conveyance-type field exists
  on the layer and correlates strongly with null CONSIDR1 — in a 50-parcel industrial pull, `CONVEY1=4` accounted
  for 23 of 25 no-consideration "transfers." The code's meaning is genuinely undocumented anywhere public found
  so far (likely deeds of trust / corrective deeds / distributions / foreclosure-related, not sham sales — true
  $0/<$25K nominal sales stayed rare, 0 of 50). Treat CONVEY1=4 as a strong null-consideration correlate, not a
  confirmed non-sale-type classification, until the code is actually decoded.
- **Seller/grantor name gap:** neither the state MdProperty layer nor the county `Property/MapServer/1` join
  exposes prior-owner/grantor — both are current-owner-only. Grantor-based nominal-transfer tests (shared
  surname) cannot run for Baltimore Co on this data; don't assume they can.
- Delinquency: none in-layer; Stage 2 = Baltimore County tax-sale/delinquent-tax list (separate pull).

## Census ACS (any market)
ZCTA median income B19013 / population B01003: key-free via
https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-{table}.dat
(pipe-delimited; GEO_ID startswith '860Z200US'+ZIP; estimate = column index 1). API requires key.

# === KANSAS CITY (run 2026-06-05) ===
KC constants: NO county publishes sale price/date (Missouri & Kansas = NON-DISCLOSURE states —
calibration from public data is structurally impossible; use CoStar/broker comps). NO county
publishes commercial building SF. Score on reduced observable scales and say so.
ALL-MARKET LESSON (caught in KC, applies everywhere): the estate regex \bESTATE\b false-positives
on corporate 'X REAL ESTATE LLC' names (~45% of KC estate hits were bogus). Fix: negative
lookbehind (?<!REAL\s) + negative lookahead for (LLC|INC|CORP|CO|GROUP|HOLDINGS|INVESTMENT) —
preserves 'ESTATE OF JOHN SMITH'/'SMITH ESTATE', kills 'WENDL REAL ESTATE LLC'. Re-audit
Columbus/Cincinnati estate lists for the same contamination on next pass.

## Jackson County MO (KCMO core) — RICH CAMA TABLE, QUERY QUIRK
- REST (CAMA table, THE source): https://jcgis.jacksongov.org/arcgis/rest/services/ParcelViewer/ParcelsAscendRelate/FeatureServer/2
  (Ascend_GisInfo standalone table; layer 1 = parcel geometry w/ TIFproject/TIFdistrict/CID/TDD).
  CRITICAL QUIRK: attribute queries on table 2 FAIL ('Unable to perform query operation') unless
  orderByFields=OBJECTID is supplied. returnIdsOnly also fails. Distinct/count queries work without it.
  maxRecordCount 2000 (pull 1000/page to be safe).
- Fields: parcel_number ('29-320-30-03-00-0-00-000' 23-char dashed), property_id, situs_address/_city/_zip,
  landuse_cd/_descr, total_sqft (= LAND SF, NOT building — verified), year_built (0% for commercial),
  Market_Value_Total + 4 past years (Ascend pastyr1-4), Comm_Impr/Comm_Land, Assessed_Val_*,
  owner_info ('OWNER1 | OWNER2' pipe-joined), address_compl (tax mail, pipe-joined), Exemption
  ('E__'=exempt, 'D__'=abatement/EZ — D05/D06/D09 common), tax_year, mtgco_name (3% filled).
- Use codes (Ascend landuse_cd): 3200 Industrial/Loft, 3201 Light Mfg, 3202 Heavy Mfg,
  3215 Warehouse-Storage, 3216 Wholesale-Trade, 3299 Misc Industrial; 3210/3211 = UNDERGROUND
  (SubTropolis caves — exclude, not ORA product); 2290 mini-warehouse (exclude).
  Table has duplicate rows per parcel (identical) — dedupe on parcel_number (3,182 rows -> 2,420).
- Delinquency: DLT (Delinquent Land Tax) judicial sale lists = seasonal PDFs at jacksongov.org
  Court Administration; site WAF-blocks plain urllib (works w/ full browser headers but pages move).
  Manual pull each Aug/Sep. KCMO Socrata (data.kcmo.org): Dangerous Buildings ax3m-jhxx +
  Property Violations tezm-fh2e (live, PIN-keyed) = secondary distress; Parcels 6g4y-sh3m
  (2023, assessed values, landusecode) covers KCMO city limits incl. Clay/Platte slivers.

## Clay County MO (North KC / Liberty) — LIVE LAYER THIN, VALUES STUCK IN 2020
- Live REST: https://services7.arcgis.com/3c8lLdmDNevrTlaV/ArcGIS/rest/services/ClayCountyParcelService/FeatureServer/0
  (Parcels: parcel_id, current_owner, situs_*, owner_addr_* — NO use code, NO values).
- Values+use snapshot (2020-10!): .../3c8lLdmDNevrTlaV/ArcGIS/rest/services/parcels_2_view/FeatureServer/0
  Fields: parcelid (14-digit), ParcelNumber (int), property_u (2-digit use code), land_val/imprv_val/
  appraised_/assessed_v, current_ow, owner_addr/owner_city/owner_stat/owner_zip, situs_disp
  (contains '\r\n', no city), acres_calc. maxRec 2000.
- property_u scheme: NO public dictionary. Empirically: 33 = industrial mfg (verified via owners);
  31 = improved industrial/comm corridor; 30/32/36/37/40 = mixed comm (include only w/ owner-name
  industrial hint). Flag every row USE-CODE-INFERRED + VALUES-2020.
- County GIS domains (gis./maps.claycountymo.gov) return HTTP 525 — dead to public.
- No delinquency feed found.

## Wyandotte County KS (KCK Unified Government) — LIVE DELQ SIGNALS, NO VALUES
- Parcels REST: https://gisweb.wycokck.org/arcgis/rest/services/UGMAPS/UGMAPS_4_V02_Parcels/MapServer/7
  Fields: PARCEL/PARCEL_NBR (6-digit int), OWNER_NAME ('LAST, FIRST ' w/ trailing space),
  NUMB/DIR/ST_NAME/SUFX/CITY/STATE/ZIP (situs — NO tax-mail published anywhere),
  DELQ_CODE (P/Y/2/3/S/SD/V/O — meanings unpublished, any non-null = distress-adjacent),
  VACANT (Y/null), LAND_USE (verbose text ~200 values), ACRE, ORIONID. maxRec 2000.
- Layer 1 of SAME service = 'Tax Sale Eligible' (identical schema) — judicial tax-sale pipeline,
  2,819 parcels, LIVE motivated-seller list. AGOL mirror of parcels (geometry only):
  services1.arcgis.com/Qo2HHQp8vgPs2wg3/.../parcel_py. Landbank layer also on AGOL.
- LAND_USE industrial core: 'Warehouse distribution / storage facility', 'Warehouse-office
  combination'/'strip / complex', 'Cold storage warehouse', 'Transit warehouse / truck terminal',
  'Industrial highest and best use', 'Miscellaneous manufacturing' + mfg subtypes. Exclude
  'Mini-storage', auto dealers, manufactured-home, utility/extraction.
- Historic delinquency snapshot (~2018): .../Qo2HHQp8vgPs2wg3/arcgis/rest/services/Delq_1Y_py/FeatureServer/0
  (First_Year/Last_Year/Total_Tax/Total_Due (comma-formatted strings!)/Appr_Value) — chronic-flag only.
- Values: APPRAISERPARCELS011123 layer = geometry only. Appraiser data on Landsweb (bot-gated
  per-parcel). EZ_Parcels_SaleVAppr = 65 parcels 2014-18, useless.
- AGOL org Qo2HHQp8vgPs2wg3 has 683 services incl. Building_Footprint (SF spatial-join path).

## Johnson County KS (Olathe/Lenexa/OP) — DATA-HOSTILE (paid gate)
- AIMS open-data portal (jocogov-aims.opendata.arcgis.com, dcat = 89 datasets): NO parcel layer.
  Parcels gated behind AIMS Data Subscription (ADS, paid). maps.jocogov.org/arcgis FreeData2
  MapServer (283 layers): boundaries/utilities only, no parcels. arcgis.com search: nothing public.
  Kansas DASC/ORKA = licensed. PATH FORWARD: buy ADS extract, or county appraiser records request.
  Beware AGOL red herring: services.arcgis.com/seTexOicoRXDvRsJ 'Parcels_Enriched' = Douglas Co COLORADO.

## Platte County MO (KCI corridor) — DATA-HOSTILE
- County GIS domains do not resolve. Only public layers are municipal:
  Platte_City_MO_Property_view (services2.arcgis.com/ji2hJlB9RmHn0um4) layer 1 'Platte County
  Parcels' = 43,875 geometry-only (TRC/SEC/BNUM/PNUM, no owner/use/value). Parkville layers similar.
  PATH FORWARD: assessor extract request or per-parcel via integritygis viewer. Small county; optional.

# === MADISON (run 2026-06-09) ===

# Dane County, WI (Madison market) — County Data Endpoints Reference
ORA county-parcel-screen pipeline · verified 2026-06-09

## 1. WI DOA Statewide Parcel Layer (V12, 2026 tax roll) — PRIMARY county-wide universe
- **Service (CORRECTED 2026-07-19 — see URL DRIFT note below):** `https://services3.arcgis.com/n6uYoouQZW75n5WI/arcgis/rest/services/Wisconsin_Statewide_Parcels_DB/FeatureServer/0`
  (layer name `V1200_WisconsinParcels_2026`; owner `djvogel2_WI_DOA` — official)
- **URL DRIFT (caught 2026-07-19):** the original service name `Wisconsin_Statewide_Parcels` (layer `V1100_WisconsinParcels_2025_0925_2`) verified 2026-06-09 now 400s (`Invalid URL`) — WI DOA renamed the service to `Wisconsin_Statewide_Parcels_DB` and rolled the layer to the 2026 vintage. Live-tested via county-endpoints.v1.json build; corrected URL above confirmed live. Re-verify this endpoint at least quarterly — it has already moved once in ~6 weeks.
- **Filter for Dane:** `CONAME='DANE'` → 218,093 parcels. Class 2 (commercial) ~13,605; class 3 (manufacturing) 459 (`PROPCLASS LIKE '%2%'` etc. — PROPCLASS is a comma list, e.g. `4,5M`; split on comma before testing).
- **Key fields:** `PARCELID` (12-digit, no dashes — joins 1:1 to City of Madison `Parcel`), `OWNERNME1/2`, `PSTLADRESS` (single string: `street, CITY ST  ZIP`), `SITEADRESS`, `PLACENAME`, `ZIPCODE`, `CNTASSDVALUE`, `LNDVALUE`, `IMPVALUE`, `ESTFMKVALUE` (DOR-equalized fair market est.), `PROPCLASS`, `AUXCLASS`, `DEEDACRES`, `LONGITUDE/LATITUDE`.
- **Quirks:** maxRecordCount 2000 (page with `resultOffset` + `orderByFields=OBJECTID`); **no building SF, no sale date/price**; some Dane owner names = `NOT AVAILABLE` (~37 in industrial universe); `ESTFMKVALUE` null on ag/MFL parcels; values are 2024 roll (Madison city ran a 2025 reval — use city layer for current values inside Madison).

## 2. City of Madison Assessor — Tax Parcels (open data) — detailed use codes + commercial SF
- **Service:** `https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA2/FeatureServer/0` ("Tax Parcels (Assessor Property Information)")
- 9,900 non-residential parcels (`PropertyClass NOT IN ('Residential')`; classes: Commercial / Manufacturing / Exempt / AG…).
- **Key fields:** `Parcel` (12-digit), `PropertyUse` (135 detailed commercial uses — warehouse split into `Warehouse & office`, `Warehouse 1 story`, `Warehouse 2+ stories`, `Warehouse, small`, `Warehse cold storage`, `Shop & warehouse`, `Condominium-Warehouse`, `Warehouse, mini type` (=self-storage), `Terminal, truck`), `PropertyUseCode`, `TotalLivingArea`/`FirstFloor` (**populated with gross building SF for commercial**), `YearBuilt`, `CurrentLand/Impr/Total` (2025/26 values), `NetTaxes`, `SpecialAssmnt`, `LotSize` (SF), `AssessmentArea`, `ExemptionType`, `MoreThanOneBuild`.
- **Quirks:** **no owner fields** (join to statewide layer on parcel id); `OwnerChangeDate` exists but is NULL on every row; `Zoning1` mostly null (use `ZoningAll`); maxRecordCount 2000.

## 3. City of Madison Assessor — per-parcel conveyance history (sale dates + prices + grantor/grantee)
- **URL pattern:** `https://www.cityofmadison.com/assessor/property/additionalpropertydata.cfm?ParcelN={12-digit}&Type=S`
  (other tabs: `Type=L` legal, `Type=T` tax, `Type=SA` special assessments, `Type=TR` tax referenda; main page `propertydata.cfm?ParcelN=…` shows current owner + mail address)
- HTML scrape; blocks of `Grantor / Grantee / Date of Conveyance (M/YYYY) / Conveyance Price / Conveyance Type`.
- **Quirks:** conveyances from ~mid-2023 forward have **blank grantor/grantee/type** (date+price only) — kills grantor-based seller-in-motion detection for the recent window; duplicate rows occur (dedupe on date+price); ~0.4 s/page, 660 pages ≈ 5 min (run chunked).
- **Sales-by-area form** (`property/salesbyarea.cfm` → POST `AssessmentArea`,`sortBy`,`search=salesByArea` to `salesbyarearesults.cfm`): works but commercial areas (89xx/99xx) return mixed retail/apartment sales — NOT useful for industrial calibration. Use per-parcel Type=S instead.

## 4. CARPC Current Land Use inventory — suburban industrial classification
- **Service:** `https://services1.arcgis.com/4NZ4Ghri2AQmNOuO/arcgis/rest/services/Current_Land_Use/FeatureServer/0` (layer `CLU`, 564 dissolved multipolygons, one per LUCODE)
- SLUCM-style codes: `2xxx-3xxx` MANUFACTURING; `6371/6373/6376/6379/6381` INDUSTRIAL (warehousing; `6375` = mini-storage — exclude); `51xx` wholesale; `4929` trucking; `9996` industrial under construction.
- Pull industrial codes as GeoJSON (`outSR=4326`, page 25/req — geometries are large), then point-in-polygon with parcel `LONGITUDE/LATITUDE`. 618 suburban class-2 parcels classified industrial this way.
- `DC_2020_LandUseInventory/FeatureServer` is **dead** (400 Invalid URL).

## 5. Dane County Treasurer — tax-deed / delinquency
- **Tax-deed auction page:** `https://treasurer.danecounty.gov/taxdeedauction` — ~146 parcel ids embedded as AccessDane links (`accessdane.countyofdane.com/Parcel/Index/{12-digit}`). Scrapeable.
- **No bulk delinquency file found** on county open data or treasurer site. Parcel-level delinquency visible on AccessDane parcel pages (per-parcel lookup only — use in Stage 2 for finalists).
- Sheriff foreclosure sales: `https://danesheriff.com/Services/Foreclosure-Sales` (not harvested this pass).

## 6. WI DOR RETR (real-estate transfer return) — sales/grantor data
- `revenue.wi.gov/Pages/ERETR/data-home.aspx` and `propertyinfo.revenue.wi.gov` both redirect to **GenTax** (`tap.revenue.wi.gov/mta/?Link=RETRHistoric`) — cookie/JS-gated heavy app, **not scriptable via urllib** in this environment. County-year RETR extracts exist behind it. Gap: suburban sale prices + grantor names. Workaround used: Madison assessor conveyance pages (city only) + DOR-equalized `ESTFMKVALUE` (county-wide).

## 7. Dead / empty endpoints (do not retry blindly)
- `https://services6.arcgis.com/Tu5JcmtrRRLVaRlf/.../TaxParcel_7663a4a9.../FeatureServer/0` — Dane County hub "TaxParcel": schema present (statewide-style fields incl. `bldgarea`!), **0 features**. If county ever populates it, it would carry building SF county-wide.
- `gis.countyofdane.com`, `maps.countyofdane.com` — domains do not resolve. `dcimapapps.countyofdane.com` hosts JS viewers only (no exposed `/arcgis/rest`).
- City of Madison `OPEN_DB_TABLES/MapServer/4` ("Property Tax Roll") — returns empty metadata; unusable.

## Parcel-ID format
12 digits, `TTPPSSQQQNNN`-style (town-range-section based), identical across statewide layer, Madison assessor, AccessDane, and treasurer links. Madison city parcels start `0608-0710`; format with dashes (`0709-154-0701-5`) appears in some city UIs — strip dashes to join.

# === GRAND RAPIDS (run 2026-06-09) ===

# Grand Rapids Market (Kent + Ottawa County, MI) — Verified Data Endpoints
Stage 1 county-parcel-screen reference. Verified 2026-06-09. Style per county-endpoints reference.

---

## KENT COUNTY, MI (core market)

### Parcel layer (PRIMARY — owner, class, SEV/taxable, acreage; NO sale fields, NO building SF)
- **REST root:** `https://gis.kentcountymi.gov/agisprod/rest/services` (folders: Hosted, OpenData, Utilities)
  - Discovered via the CMV viewer config at `https://gis.kentcountymi.gov/public/publicviewerjs/config/viewer.js` — the REST root is NOT linked anywhere obvious; the bare host 404s on `/arcgis/rest/services`.
- **Layer:** `ParcelsWithCondos/FeatureServer/0` ("Parcels With Condos"), also mirrored at `OpenData/Parcel_Related_Layers/MapServer/0`
- **maxRecordCount:** 1000, supportsPagination: true. Plain urllib with browser UA works (no WAF).
- **Count query verified:** `PROPERTYCLASS IN ('301  ','302  ')` → 2,933; `'201  '` → 12,156
- **Fields (verified):** `PNUM` (text PIN `41-XX-XX-XXX-XXX`), `PPN` (numeric), `OWNERNAME1`, `OWNERNAME2`, `OWNERCAREOF`, `OWNERADDRESS`, `OWNERCITY`, `OWNERZIPCODE` (NO owner-state field — infer out-of-state from non-48/49 ZIP), `PROPERTYADDRESS`, `PROPADDRESSCITY`, `PROPADDRESSSTATE_ZIPCODE` (e.g. `MI49343`), `PROPERTYCLASS` (**5-char padded** — `'301  '` with two trailing spaces; unpadded equality returns 0), `GOVERNMENTALUNIT` (code only), `SCHOOLDISTRICT`, `SEVTRIBUNAL1/2`, `TAXABLETRIBUNAL1/2`, `ACREAGE`, `TAXPARCEL_FLAG`
- **Quirks:** All text fields space-padded to fixed width — strip everything. No sale date/price, no improvement-value split, no building SF, no use-description. Geometry pulls fine at 500/page with `outSR=4326&geometryPrecision=6`.
- The City of Grand Rapids mirror (`https://maps.grcity.us/arcgis/rest/services/ArcGIS_Online/ENG_CGR_Sidewalks/MapServer/4`, "ArcGIS.GDBO.PARCELS_WITH_CONDOS") adds `OWNERSTATE`, `TAXPAYERNAME`, `LEGAL_DESC` but is county-wide same data.

### Building SF (proxy)
- **USA Structures (FEMA/ORNL):** `https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/USA_Structures_View/FeatureServer/0`
  - `FIPS='26081'` → 255,664 structures; `AND SQFEET>=5000` → 14,359 (pulled). Fields: `SQFEET`, `HEIGHT`, `OCC_CLS`, `PRIM_OCC`, `LONGITUDE`, `LATITUDE`. maxRecordCount 2000.
  - Centroid-in-parcel spatial join → 1,300 of 2,933 industrial parcels matched. SQFEET is footprint-derived (single-story assumption OK for shallow-bay).

### Sales / calibration
- **NONE public at parcel level.** Kent open-data hub (`data.kentcountymi.gov`) is defunct (DCAT 404 / empty). Kent Property Search (`https://app.kentcountymi.gov/PropertySearch/appStart`) is reCAPTCHA-gated — per-parcel enrichment only, do not scrape at volume.
- **2026 Tentative Equalization Ratios** (empirical, unit-level, from L-4018 sales/appraisal studies): `https://www.kentcountymi.gov/DocumentCenter/View/9196/2026-Tentative-Ratios-and-Multipliers-PDF`. Industrial ratios 42.2–49.95% (GR City 46.76, Wyoming 48.81, Kentwood 45.24, Walker 43.37, Grandville 47.20).
- Equalization document archives: `https://www.kentcountymi.gov/Archive.aspx?AMID=36|37|38` → `/ArchiveCenter/ViewFile/Item/{ADID}` (328 = 2025 Apportionment Report etc.; untitled in listing — fetch to identify).

### Motivation signals
- **Treasurer delinquency/foreclosure:** no public parcel list before ~July 1 each year; auction results only post-sale (`kentcountymi.gov/861/Auction`, tax-sale.info). Per-parcel delinquent tax via accesskent — gated. GAP.
- Kent County Land Bank dissolved (2020) — no land-bank inventory feed.

---

## OTTAWA COUNTY, MI

### Parcel layer (PRIMARY)
- **REST root:** `https://gis.miottawa.org/arcgis/rest/services` (folders: Hosted, HostedServices, Utilities)
- **Layer:** `HostedServices/ParcelsPublic/FeatureServer/0` ("Ottawa County Parcels (Public)")
- **maxRecordCount:** 2000. Plain urllib OK.
- **Count verified:** `PropertyClass IN ('301','302')` → 1,809; `'201'` → 4,960
- **Fields (verified):** `FinalPIN` (`70-XX-XX-XXX-XXX`), `FinalPackedPIN` (12-digit, joins to footprints), `OwnerName` (SINGLE owner field — no owner2), `PropertyAddress/City/State/Zip`, `MailingAddress/City/State/Zip`, `PropertyClass` (**unpadded** 3-char), `PropertyClassDescription`, `GovernmentUnit(+Description)`, `AssessedValue`, `SEVValue`, `CappedValue`, `TaxableValue`, `Acreage`, `StatedArea`, `PrincipalResidenceExemption`, `BSA_UID` (BS&A link)
- **Quirks:** no sale date/price fields. ~Some parcels have empty PropertyClass.

### Building SF
- **`HostedServices/BuildingFootprints/FeatureServer/0`** — 168k footprints with `PackedPIN` (joins FinalPackedPIN), `Status`, `Type`, `NumberofFloors`. No area field served in attribute-only mode; pull geometry `outSR=4326` and compute shoelace area × cos(lat). **Validated vs assessor SF in ECF study: ratio 1.00–1.09** (slight eave overcount). 1,918 footprints matched the 1,809-parcel industrial universe.

### Sales / calibration (BEST-IN-MARKET SOURCE)
- **Equalization reports hub:** `https://miottawa.org/equalization/reports/`
- **ECF Analysis (annual, parcel-level improved sales with SF):** `https://miottawa.org/wp-content/uploads/2025-ECF-Analysis.pdf` (no 2026 edition posted as of 2026-06). Sections `3001: INDUSTRIAL- OVER 15,000 SQUARE FOOT` (27 sales) and `3002: INDUSTRIAL- UNDER 15,000` (13 sales), sales 4/2023–3/2025, columns: parcel, address, date, price, land value, residual, cost manual, ECF, **Bldg SF**, $/SF. Adopted ECFs: 3001 → 1.170, 3002 → 1.580.
- **Land Analysis (vacant sales):** `https://miottawa.org/wp-content/uploads/2025-Land-Analysis.pdf`
- **Tentative ratios:** `https://miottawa.org/wp-content/uploads/2026-Tentative-Ratios-and-Multipliers.pdf`

### Motivation signals
- **Foreclosure list (live):** `https://miottawa.org/wp-content/uploads/Foreclosure_List2026.pdf` (from `https://miottawa.org/treasurer/delinquent/`) — 7 parcels 2026, PIN + unit + legal + situs. Also `Ottawa-County-Surplus-Properties-Not-Purchased-at-Foreclosure-Auction.pdf`.
- Property app `https://app.miottawa.org/Property/` — per-parcel sale history incl. delinquency; bot-gated, enrichment path only.

---

## Tried / dead ends
- `data.kentcountymi.gov` — DNS dead in sandbox, empty via proxy fetch; hub retired.
- ArcGIS Hub DCAT feeds: gis-michigan (no statewide parcels w/ sales), grdata-grandrapids (parcels mirror only, no assessor sales), gisdata-miottawa (404).
- Michigan statewide parcel layer with sale fields: not found on any public AGOL org.
- BS&A Online (bsaonline.com): hosts per-municipality assessing for most Kent/Ottawa units incl. sale history — bot-gated per-parcel; volume scraping prohibited. Enrichment path for Stage 2.

# === RICHMOND (run 2026-06-09) ===

# Richmond VA market (Henrico / Chesterfield / Richmond City / Hanover) — Endpoints Reference
ORA county-parcel-screen pipeline · verified 2026-06-09

## 1. HENRICO COUNTY — portal.henrico.gov hosted ArcGIS (official)
- **Parcels+CAMA (PRIMARY):** `https://portal.henrico.gov/mapping/rest/services/Layers/Tax_Parcels_and_CAMA_Data_External/FeatureServer/0` — 124,077 parcels, maxRec 5000.
- **Key fields:** `GPIN` (xxx-xxx-xxxx with dashes), `PID`, `FULL_ADDRESS`, `ZIP_CODE`, `USE_CODE`/`USE_DESCRIPTION` (74 commercial codes), `RESIDENTIAL_COMMERCIAL` (R/C), `LAND_VALUE_CURRENT`, `IMPROVEMENTS_VALUE_CURRENT` (TAX_YEAR 2026 roll), `LAST_SALE_DATE` (epoch ms) / `LAST_SALE_PRICE`, `SQFT_FINISHED` (**populated for commercial — building SF**), `PARCEL_ACREAGE`, `YEAR_BUILT`, `TAX_TYPE_CODE` ('7'/'8' = exempt/gov).
- **Industrial use codes:** 406 Warehouse (331), 675 Office/Warehouse (203), 453 Ind'l Flex (123), 495 Ind'l Manufacturing (71), 670 Construction Svcs, 470/472 equipment, 326/328 storage garage/hangar; 386 Mini-Warehouse = self-storage (excluded); 703 = Vacant Industrial M1-M3.
- **CRITICAL QUIRK — NO OWNER/MAIL FIELDS in any public layer.** External FeatureServer + MapServer + `Layers/Data_Tables/MapServer/0` (CAMA_DATA, 124,035 rows) are all owner-scrubbed. Exception: `Layers/County_and_County_School_Owned_Properties/MapServer/0` (794 rows) carries OWNER_CURRENT + MAILING_ADDRESS_01-04 — used as gov-owned exclusion list. Per-parcel owner lookup = `https://realestate.henrico.gov/ords/cam/f?p=510101` (Oracle APEX; GET with P50_GPIN returns PDF — needs browser automation in Stage 2).
- AGOL org `services.arcgis.com/LxWK4CxNTBBlLshT`: `Henrico_County_Tax_Parcels_0322` = stale 3/2022 snapshot filtered to 735 rows (has OWNER schema; useless). `gis.henrico.us` does not resolve from this environment.

## 2. CHESTERFIELD COUNTY — AGOL org TsynfzBSE6sXfoLq (official `Chesterfield_County`)
- **Parcels (PRIMARY):** `https://services3.arcgis.com/TsynfzBSE6sXfoLq/arcgis/rest/services/Cadastral_ProdA/FeatureServer/3` ("ParcelsEnriched") — 149,809 parcels, maxRec 2000. (Non-ProdA `Cadastral/FeatureServer/3` = older copy, 146,864, maxRec 1000, no TaxID/YearBuilt.)
- **Key fields:** `GPIN` (10-digit), `TaxID`, `OwnerName`, `OwnerAddress/City/State/Zip`, `Address`, `Zip`, `UseCode`, `FinishedArea` (**building SF**), `UnfinishedArea`, `YearBuilt`, `DeededAcres`, `FairMarketValue`, `LandUseValue`, `ImprovementValue`, `TotalAssessment`, `Exempt` ('E'=exempt), `SaleDate` (string 'YYYY-MM-DD…'), `SalePrice`, `NumberLots`, `Stories`.
- **VALUE QUIRK:** `FairMarketValue` = LAND at market only. Market-basis assessed total = `FairMarketValue + ImprovementValue`. `TotalAssessment` = taxable (uses deferred `LandUseValue` for land-use-program parcels) — do NOT use for calibration.
- **Use codes** (dictionary NOT in layer domain; harvested from READ API `https://api.chesterfield.gov/api/RealEstate/V1.2/MasterData/AllBuildingUseCodes` — saved `chesterfield/use_codes.json`): 510/511/512 OFFICE/WAREHOUSE, 660 STORAGE WAREHOUSE, 270 DISTRIBUTION WAREHOUSE, 380 MANUF <50K, 390 MANUF >50K, 370 INDUSTRIAL ENGINEERING, 275 EQUIPMENT STORAGE, 700 TRUCK TERMINAL, 450 MINI WAREHOUSE (excluded), 600 SERVICE GARAGE (auto — excluded). 511/512 absent from dictionary; verified office/warehouse by sampling (Whitepine Rd / Trade Rd corridors).
- READ per-parcel API (Stage-2 enrichment): `api.chesterfield.gov/api/RealEstate/V1.2/Details/{Search,Details,OwnershipHistory,CommercialBuildings,AssessmentHistory}` + `api/Tax/V1.2/History/TaxHistory` (per-parcel delinquency!). Needs Referer/Origin chesterfield.gov headers.

## 3. RICHMOND CITY — AGOL org k3vhq11XkBNeeOfM (`richmondvagis`, 779 services)
- **Parcels (owner/value):** `.../services/Parcels/FeatureServer/0` — 76,879; `PIN` (e.g. C0030086020), `ParcelID` (numeric), `OwnerName`, `MailAddress/City/State/Zip`, `LandValue`/`DwellingValue`/`TotalValue` (2026), `PropertyClass` (text, e.g. 'B Storage Warehouse'), `PropertyClassID`, `LandUse`, `TaxExemptCode`, `LandSqFt`. **No situs street name** (`AsrLocationBldgNo` = house number only) and no situs ZIP — take street from AsrImp `prop_street`.
- **Building SF:** `.../AssessorProVaGPINlImpDataPublish/FeatureServer/0` — 69,384 rows; `parcel_id` (pad-stripped = PIN), `total_comm_area` (**commercial building SF**, 7,510 rows >0), `comm_bldg_type`, `year_built`, `prop_street`.
- **Sales/transfers:** `.../AssessorProValGPINRecTransPublish/FeatureServer/0` — 13,938 recent transfers; `sale_date` (epoch ms), `sale_price`, `val_code_1` ('1 - VALID SALE' = arm's-length screen), `ratio`, assessed `tot`. Older sales: `Parcels_Database/FeatureServer/0` (2018 vintage; `SaleDate1/SaleAmt1`).
- **Delinquency (motivation):** Socrata `https://data.richmondgov.com/resource/83t5-hbac.json?$limit=50000` — "Delinquent Real Estate Taxes 6+ months", 3,864 rows: `property_code` (=PIN), `current_owner_name_1`, `total_due`, `total_years_del`.
- Industrial classes used: B Storage Warehouse (373), B Distribution Warehouse (186), B Light Industrial (132), B Industrial Flex (29), B Transit Warehouse (24), B Industrial Misc (51), B Heavy Industrial (34), B Industrial Shell (10). Excluded: B Mini Warehouse, B Tank Farm, B Railroad, P Public Service Corp, B Industrial Vacant Land/Paved Parking.

## 4. HANOVER COUNTY — AGOL org sKZWgJlU6SekCzQV (`hanovercounty`)
- **Parcels (PRIMARY, live):** `https://services2.arcgis.com/sKZWgJlU6SekCzQV/arcgis/rest/services/Hanover_Parcels/FeatureServer/0` — 52,552; `GPIN`, `OWN_NAME1/2`, `MAIL_ADDRESS/CITY/STATE/ZIP`, `ADDRESS/CITY/ZIP`, `LOT_ACRES`, `LAND_VALUE`, `IMPROVEMENTS_VALUE`, `ZONING_LIST`, `LEGAL_DESCRIPTION`, deed book/page. (`Hanover_County_Parcels` = older 51,608-row copy; yearly archives 2021-2025 also published.)
- **ATTRIBUTE GAPS: no use code, no building SF, no sale date/price.** Industrial universe inferred from `ZONING_LIST IN ('M-1','M-2','M-3')` (978 parcels). `Buildings` footprint layer (86,997) has no GPIN — spatial join only. County GIS server `gis.hanovercounty.gov/arcgis/rest` exposes only Geocode/Utilities/CrimeStats.
- Per-parcel assessment/sales: Hanover "Parcel Information" web lookup (Stage-2, browser).

## 5. Statewide / motivation
- **VGIN parcels** `vginmaps.vdem.virginia.gov/arcgis/rest/services/VA_Base_Layers/VA_Parcels` — alive; attribute-thin (not needed; all four localities had richer local layers).
- **taxva.com (TACS judicial tax sales** — covers many VA localities incl. Richmond-area): site is JS-rendered, list not reachable via urllib in this environment — Stage-2 browser task.
- Chesterfield/Henrico/Hanover bulk delinquency files: none found public; Chesterfield per-parcel via READ Tax/V1.2 API; Henrico via online tax-bill app (per-parcel).

# === DES MOINES (run 2026-06-09) ===

# Des Moines, IA market (Polk + Dallas counties) — County Data Endpoints Reference
ORA county-parcel-screen pipeline · verified 2026-06-09

## POLK COUNTY

### 1. Polk County Assessor bulk commercial exports — PRIMARY (best assessor data of any county screened to date)
- **Commercial inventory (countywide, one row per parcel):**
  `https://web.assess.co.polk.ia.us/info/web/exports/comm/inven/polk/POLKCOUNTY.csv` (~10 MB, 13,181 rows)
  Discovered via `https://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=downloads/comm` (also per-jurisdiction and per-occupancy slices; parallel `downloads/res`, `downloads/ag` pages).
- **Key inventory fields:** `dp` (14-digit district/parcel — primary key), `gp` (12-digit GIS geoparcel), `occupancy_group` (WHS/OFF/RTL/APT/LND/ATO/…), `occupancy` + `occupancy_descr` (46 Warehouse, 25C Office & Warehouse, 20A Industrial Light, 48 Warehouse Condo, 44 Warehouse Transit, 35C Retail & Warehouse, 47 Warehouse Mini = self-storage, 37 Auto Repair, 20B Industrial Heavy…), `class` (B Commercial / I Industrial / C Commercial Exempt / M Res3+ / combos), `land_full/bldg_full/total_full` (assessed @100% market), `*_adj` (post-board), `gross_area` (building SF — populated), `year_built`, `bldg_class`, `grade`, `condition`, `air_cond_area`, `sprinkle_area`, `land_area` (lot SF), `title_holder1/2`, `contract_buyer1/2` (Iowa contract sales — live contract purchasers), `transfer_th1` (current-owner deed date) + `book/pg`, full mail address block (`mail_name`, `mail_line1`, `mail_city/state/zip`), `occupant` (DBA), `x,y` (IA State Plane N, ft), `tif`, `zoning`, `school_district`, `jurisdiction`.
- **Commercial sales (countywide, 1987→current, refreshed continuously):**
  `https://web.assess.co.polk.ia.us/info/web/exports/comm/sales/polk/POLKCOUNTY.csv` (~13 MB, 21,324 rows)
  Fields: `dp`, `gp`, `sale_date`, `price`, `instrument` (**Deed | Contract** — Iowa contract sales explicit), `seller`, `buyer`, `book/pg`, `quality` (Iowa DOR standard sale-validity classification — Arms Length / Landlord to Tenant / Family / Adjoining or Non-Res Adjacent Land / Partial Assessment / No Consideration / Foreclosure / Estate Transfer / etc. — **found via county-sales-monitor pilot, 2026-08-15, not previously documented here; a strong non-arms-length signal, use it before falling back to price/ratio heuristics**), plus the full CAMA snapshot of the sold parcel (`total_full`, `gross_area`, occupancy…), `dps`/`gps` (all parcels in multi-parcel sales), `initial_entry_date`.
- **`gps` multi-parcel rollup gap (same pilot):** member parcel IDs in `gps` sometimes don't exist in the *current*
  inventory CSV snapshot (3 of 18 multi-parcel deeds in a 12-month pull) — Iowa assessors appear to retire old
  parcel IDs after combining them post-acquisition. A naive SF sum across `gps` members can silently undercount;
  treat an incomplete `gps` join as SF-unknown, not zero.
- **Quirks:** occupancy codes carry trailing spaces — strip; inventory has **no sale price** (join sales on `dp`); `transfer_th1` dates exist pre-1987 with no matching sale row (NO-PRICE); WAF (Akamai/boomerang) tolerates python urllib with a plain UA; per-parcel pages at `/cgi-bin/web/tt/form.cgi?tt=cinvenform` (queryable web API forms also exist under `query.cgi`).

### 2. Polk County GIS
- `gis.polkcountyiowa.gov` **does not resolve** from this environment. Not needed — assessor CSV carries x/y coordinates and full attributes. (County ArcGIS hub exists per references; re-probe in a browser pass if geometry needed.)

### 3. Polk County Treasurer (delinquency / tax sale)
- 2026 annual tax sale: **June 15, 2026** (news: polkcountyiowa.gov/treasurer/news/2026-property-tax-sale-takes-place-june-15/). Terms PDF: `/media/hldayqk0/2026-tax-sale-terms-conditions.pdf`.
- **No public delinquent-parcel list found on the county site.** Sale is run through SRI's `iowataxauction.com` — parcel lists are behind registration/login (JS DataTables app). GAP — Stage-2 item (register or pull legal-notice publication).

## DALLAS COUNTY

### 4. Dallas County ArcGIS Server — open, no token
- Root: `https://gis.dallascountyiowa.gov/arcgis/rest/services` (10.91; folders: Assessor, Auditor, Cadastral, Hosted, Planning, Public…)
- **Public/Parcels/FeatureServer/0** — PRIMARY parcel universe. 57,440 parcels, maxRecordCount 2000 (page resultOffset+orderByFields=OBJECTID).
  Fields: `PARCELID` (10-digit pin), `PropertyClass` (comma list: R/A/C/I/M/AD — **I = 79 pure + 3 mixed; C = 2,842**), `OwnerName`, `MailOwnerName`, `MailLine1/2`, `MailCity/State/PostalCode`, `FullSitus`, `SitusCityName`, `SitusPostalCode` (often blank), `FullLandValue/FullBuildingValue/FullTotalValue` (assessed @100%), `DeededAcres/NetAcres`, `Legal`, levy/TIF strings. **No building SF, no use codes, no sale data.**
- **Assessor/Sales/FeatureServer** layers 83=2025, 78=2024, 79=2023, 80=2022, 81=2021 (~1.2–2.6K/yr): `ParcelPin`, `SaleYear`, `Sale1..Sale4` (prices). **No sale date, no parties, no instrument.**
- **Assessor/GeneralParcelInfo2/FeatureServer**: 64 DBA (occupant names), 73 Permits, 85 Sales Analysis - Current Year (assessment-ratio ranges), 86 MapArea.
- Assessor/ResidentialParcelInfo = residential CAMA only; no commercial twin published.
- County sales spreadsheets (`edocs.dallascountyiowa.gov/landsales/*.xlsx`) are **land-only** comps.
- **Beacon** (beacon.schneidercorp.com AppID=909 LayerID=17429) bot-gated 403 — per-parcel only; Stage-2 browser work.

### 5. FEMA/ORNL USA Structures — Dallas SF + occupancy proxy
- `https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/USA_Structures_View/FeatureServer/0`
- `where=FIPS='19049' AND SQFEET>=4000`, outFields `SQFEET,HEIGHT,OCC_CLS,PRIM_OCC,LONGITUDE,LATITUDE` → 4,815 structures; centroid point-in-polygon into county parcel rings. OCC_CLS Industrial = 272 structures. Footprint SF (1-story assumption) — flag `SF-FOOTPRINT`.

## Parcel-ID formats
- Polk: `dp` 14-digit district/parcel (e.g. 25200010004000) = screen key; `gp` 12-digit geoparcel (e.g. 812414400007) for GIS joins.
- Dallas: `PARCELID` 10-digit pin (e.g. 1425201010), identical in Public/Parcels, Sales layers, DBA, Beacon.

## Blocked / dead
- `gis.polkcountyiowa.gov`, `maps.dallascountyiowa.gov` — DNS fail in sandbox.
- Overpass API (overpass-api.de 406, kumi.systems timeout) — OSM landuse unavailable this pass.
- iowataxauction.com (SRI) — login-gated lists.
- waukee.org GIS 403; maps.wdm.iowa.gov 404 at /arcgis.
