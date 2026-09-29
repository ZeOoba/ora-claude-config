# county-parcel-screen — engineering notes

Moved out of `SKILL.md` on 2026-09-22 (body split). Hard-won; read before running any pull.

## Engineering notes (hard-won - read before running)
- bash sandbox: 45s per call. Use scripts/dl_resume.py (resumable ranged
  downloader) for files >40MB. Unzip into a NEW subdirectory - the sandbox
  cannot overwrite or delete files written by previous calls. Stream-parse
  100MB+ files with csv.reader straight from zipfile.open().
- Parcel-ID formats differ between a county's GIS layer and its tax files
  (Franklin: '010-104049' vs '"010-104049-00"') - normalize before joining,
  verify the join produced matches (a silent 0-match join cost an hour once).
- Excel bulk files: pip install python-calamine, pandas engine="calamine"
  (10x faster than openpyxl; openpyxl times out on 250K-row files).
- Some county report servers WAF-gate downloads: send full browser headers
  (User-Agent + Accept(html) + Referer + Sec-Fetch-*) - Butler 403s without.
- Census ACS by ZCTA: the API now requires a key; key-free path is the
  table-based Summary File FTP (acsdt5y2023-bXXXXX.dat, estimate = column 1).
- GIS layers are often thin mirrors: physical fields (year built, height,
  condition) may be 0% populated - the bulk appraisal/building extract is the
  real source (Franklin Build.txt: YRBLT/WALLHGT/PHYCOND = 100% coverage).
  Conversely some counties (all 4 Cincinnati counties) publish NO commercial
  SF anywhere public - use footprint spatial joins or per-parcel scrapes.
- Owner-scrubbed GIS != owner-inaccessible: counties on Oracle APEX/ORDS CAMA
  front-ends (Henrico VA pattern - <host>/ords/<schema>/f?p=...) yield owners
  to a scripted wwv_flow.accept POST. Use scripts/apex_owner_pull.py (county
  config registry + resumable bulk + --smoke test; Henrico validated 279/279
  at ~0.85s/parcel). Probe for /ords/ before declaring a county data-hostile;
  add each validated county to the module's COUNTIES dict.
- Canonical classifiers live in scripts/: estate_v2.py (estate signals; '&'
  trailing-TRUST patch 2026-06-09), institutional_owners.py (institutional/
  ORA/never-call). Import these - never re-implement inline regex per run.
