# Installation — psa-reconciliation Skill

## Destination

Copy the entire `psa-reconciliation/` directory to your Cowork skills folder:

```
[Cowork root]/.claude/skills/psa-reconciliation/
    SKILL.md
    references/
        psa-fact-schema.md
        exhibit-extraction-patterns.md
        downstream-cascade-targets.md
```

On Windows the root typically resolves to `%USERPROFILE%\.claude\skills\` (or the Cowork-session mount path). Confirm by listing existing user skills — the folder alongside `acquisition-underwriting/`, `rent-roll-qc/`, and `deal-execution/` is the correct target.

## Verification

After installation, in a new Cowork session, confirm the skill registers by typing:

> "list skills"

The response should include `psa-reconciliation` in the skills list. If it does not appear, restart the Cowork session to refresh the skill registry.

## First-run test

Trigger the skill with a sentence that includes one of the trigger phrases (see SKILL.md description). A low-stakes first run:

> "Extract the PSA facts from the E Fulton PSA and build a fact table — don't cascade yet."

Expected output: A single XLSX (`YYYYMMDD_E-Fulton_PSA-Facts_v01.xlsx`) in the Cowork workspace folder, with the 12-section Fact Table populated from the fully-executed PSA dated 4/21/2026. No downstream documents produced.

## Version

v1.0 — initial release, April 23, 2026.

## Next iteration candidates

Future versions should add:

1. **Automated cascade to Notion** via the scheduled-tasks runner so that every PSA execution triggers a Notion deal-record refresh automatically.
2. **PDF extraction pre-processor** that handles signed-PDF variations (DocuSign certificates, Adobe Sign wrappers) without flattening the signature-block timestamps.
3. **Amendment handling** — detect first-amendment or letter-agreement uploads and auto-promote the Fact Table to v02 with delta tracking.
4. **Cross-deal fact library** — accumulate canonical Fact Tables across the portfolio into a single master reference database for precedent analysis.
5. **Skill-to-skill handoff** — on completion, suggest invoking `rent-roll-qc` for the rent roll cascade output, `communication-intelligence` for the email summary, and `conversation-archival` to log the Fact Table build to the Notion Knowledge Base.
