# GIS Endpoint Directory — verified 2026-06-09 (V = verified, U = unverified pattern)

## National
| Layer | URL | Status | Note |
|---|---|---|---|
| FEMA NFHL REST | https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer | V | Layer 28 = Flood Hazard Zones; 3 FIRM panels; 16 BFEs; 23 levees |
| FEMA MSC search | https://msc.fema.gov/portal/search?AddressQuery={addr} | U | JS app — browser only |
| Census geocoder | https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={addr}&benchmark=Public_AR_Current&format=json | U | Standard pattern |

## Columbus OH
| City of Columbus zoning REST | https://maps2.columbus.gov/arcgis/rest/services/Schemas/BuildingZoning/MapServer | V | Also Schemas/Development |
| Columbus zoning code | https://library.municode.com/oh/columbus | V | JS shell — browser |
| Franklin Co GIS | https://gis.franklincountyohio.gov/ | U | REST path not discoverable; use auditor GIS UI + NFHL/ODNR for flood |
| Gahanna code | https://codelibrary.amlegal.com/codes/gahanna/latest/overview | U | Cloudflare challenge — browser only; IM front-yard overlay applies |
| Ohio DNR floodplain | https://gis.ohiodnr.gov/arcgis/rest/services | V | DSW_Services folder |

## Cincinnati OH
| CAGIS (Hamilton Co + city) | https://cagisonline.hamilton-co.org/arcgis/rest/services | V | CINC_PLANNING = zoning; COUNTYWIDE folder |
| Cincinnati code | https://library.municode.com/oh/cincinnati | U | Browser |
| Clermont Co GIS | https://gis.clermontcountyohio.gov | U | Verify on first 754-area use |
| Butler Co GIS | https://www.butlercountyauditor.org/gis | U | Liberty/West Chester deals |

## Kansas City
| Johnson Co KS AIMS | https://maps.jocogov.org/arcgis/rest/services | V | City folders incl. Olathe-adjacent |
| KCMO open data | https://data.kcmo.org | U | No working ArcGIS REST found; Socrata fallback |
| KCMO / Olathe / Lenexa codes | library.municode.com/mo/kansas_city · /ks/olathe · /ks/lenexa | U | Browser |
| Jackson Co MO GIS | https://jacksongov.org | U | REST host unresponsive 2026-06-09 |
| KS DASC / MO SEMA flood | https://www.kansasgis.org · msdis.missouri.edu | U | State fallbacks |

## Indianapolis
| xmaps REST | https://xmaps.indy.gov/arcgis/rest/services | V | DMDPortal = zoning; Assessor = parcels |
| Indy code | https://library.municode.com/in/indianapolis_-_marion_county | U | Browser |
| INFIP (state flood) | https://infip.dnr.in.gov/ | V | Redirects to ArcGIS Experience viewer — browser |

## Maryland (BWI corridor)
| Anne Arundel REST | https://gis.aacounty.org/arcgis/rest/services | V | OPZ + OPZ_LongRange = planning/zoning |
| AA Co code | https://library.municode.com/md/anne_arundel_county | U | Browser |
| Howard Co data | https://data.howardcountymd.gov | U | — |
| MDE flood | https://mdfloodmaps.net/ | V | Portal |

## Madison WI
| Dane Co DCiMap | https://map.countyofdane.com | U | REST unresponsive; use viewer |
| Madison code | https://library.municode.com/wi/madison | U | Browser |
| WI DNR SWDV flood | https://dnrmaps.wi.gov/H5/?Viewer=SWDV | V | Geocortex — browser; /H5V2/ path is dead |

## Louisville / Jefferson County KY

LOJIC (Louisville/Jefferson County Information Consortium) — keyless ArcGIS REST, verified live 2026-08-24 via direct point/envelope queries against both subject parcels (4652 Knopp Ave, 8301 Cane Run Rd). No Kentucky-outside-Cincinnati entries existed in this file before this pass; Louisville became a live target market 2026-08-05.

| Layer | URL | Status | Note |
|---|---|---|---|
| LOJIC Parcels (PVA) | https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataPVA/MapServer/1 | V | Jefferson Co KY Parcels — use for parcel bbox/geometry validation against the Census geocoder's interpolated point (see Step 1 — Census geocoder can place a point outside the parcel on irregular/corner lots) |
| LOJIC Address Points | https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataAddresses/MapServer/0 | V | Jefferson Co KY Address Points — assigned site-address point, more reliable than the Census geocoder for irregular lots |
| LOJIC Zoning | https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataDevelopment/MapServer/15 | V | Zoning district polygons — query at the validated site-address point, not the raw geocode |
| LOJIC Open Data Portal | https://data.lojic.org/ | V | Browser portal mirroring the same REST layers; useful for visual QA of a query result |
| LOJIC services root | https://gis.lojic.org/maps/rest/services | V | Folder listing — other LojicSolutions services (OpenDataBase, OpenDataSociety, OpenDataHistoricAddressing) exist but were not needed this pass |
| Louisville Metro LDC (zoning code) | https://codelibrary.amlegal.com/codes/louisville/latest | U | JS shell — browser only; internal site search sometimes needs a direct-coordinate click rather than an element-ref click to register text entry |
| FEMA NFHL | (see National section above) | V | Same national endpoint; Jefferson Co KY has no state-level flood-map substitute needed — NFHL point/envelope queries resolved cleanly for both subject parcels |

## Entry markets (unverified wholesale — no satellites until first closed deal per 2026-06-09 ruling)
| Kent Co MI | https://www.accesskent.com/GIS/ | U | GR zoning: codelibrary.amlegal.com/codes/grandrapids |
| Henrico VA | https://gis.henrico.gov | U | — |
| Chesterfield VA | https://www.chesterfield.gov/gis | U | — |
| Polk Co IA | https://gis.polkcountyiowa.gov | U | — |
