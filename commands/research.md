# /research — Lane L5 (investigate / compare / decide)

Produces a DECISION, not a diff. No merge.

## Confidentiality FIRST
Strip every `confidential-terms.json` term (deal names, addresses) from any EXTERNAL query (web / firecrawl). ORA-internal questions stay on internal sources only (Excel / Notion / memory / HubSpot / M365). Never egress a confidential term.

## Chain
1. **Internal first:** memory, Notion, Excel, HubSpot, M365/SharePoint.
2. **External:** `deep-research` skill, or `firecrawl` + **context7** (live library docs). **Workflow only on explicit opt-in** (it fans out many agents — RAM).
3. **Adversarial verify** — confirm key claims against ≥2 independent sources (deep-research does this natively).
4. **Synthesize** → cite every source.
5. **PERSIST** → memory + `conversation-archival` (Notion) for institutional findings.

## Resource
Gauge `/ram` before a fan-out; run heavy multi-agent research from a lean CLI (`/solo` or `/handoff`). Keep concurrency modest.
