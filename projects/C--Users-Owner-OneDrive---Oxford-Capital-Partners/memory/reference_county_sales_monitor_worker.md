---
name: reference-county-sales-monitor-worker
description: "Location, IDs and ops commands for the hosted County Sales Monitor Notion Worker (deployed 2026-10-01) and its two managed databases"
metadata:
  node_type: memory
  type: reference
---

County Sales Monitor runs as a Notion Worker, not a local script.

- Repo: `C:\Users\Owner\ora-county-sales-monitor` (local git only, no remote). Worker name `county-sales-monitor`, id `01a0fa61-6ca4-78f2-895d-5aafe648dbbf`. Deploy/ops from native Windows via `ntn` (npm global; WSL2 is not installed). Runbook = the repo README.
- Databases (under Knowledge Base `3386ecd8`): Comps (Worker) db `3ed6ecd8-9e59-8168-a367-df08b6ff6d3b`, ds `28bae38c-f495-4c9e-9edc-b86c0ae2c413`; Coverage (Worker) db `3ed6ecd8-9e59-81b1-947b-dff540312cfc`, ds `f26e704a-9191-436b-85cf-fd64258928be`. The legacy pilot DB `311cf712…` is separate and untouched.
- Rollback: `ntn workers capabilities disable countySalesSync` / `countySalesCoverageSync`. **Why:** never delete the worker or the databases; schema edits in `src/index.ts` migrate managed DBs and can drop data. **How to apply:** disable first, ask Gabriel before any redeploy that touches `schema.properties`, rules constants or use-code lists.
- Skill context: [[county-sales-monitor]] v0.6; history in `event_log.md` 2026-10-01.
