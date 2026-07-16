---
name: reference_skill_home_loss_2026-07-09
description: 4 skills lost their live on-disk home in the 2026-07-09 clone archival; doctrine probe scan roots exclude the ora-skills repo
metadata: 
  node_type: memory
  type: reference
  originSessionId: fcd65ebd-12ec-4780-b0bb-7d973fb9fb7a
---

The doctrine-integrity-probe's skill check resolves a skill only if a `SKILL.md`-containing directory exists under one of its scan roots: `~/.claude/skills`, `~/.claude/plugins`, or `OneDrive…/Claude_Workspace` (with `_archive`, `backups`, `02_outputs`, etc. pruned). It does **NOT** scan the authoritative source-of-record repo `C:\Users\Owner\ora-skills`. So a skill that lives only in that repo (or only in an archived clone) reads as `[MISSING]` even though it is alive.

**2026-07-10 incident:** doctrine probe went exit 1 on 4 skills — `acquisition-underwriting`, `loi-generation`, `psa-reconciliation`, `tenant-email`. Root cause: the 2026-07-09 "third-ora-skills-clone" consolidation archived the source clone into `01_Workspace/_archive/2026-07-09_third-ora-skills-clone/skills/` but, unlike their ~11 siblings (which retained a live copy under `01_Workspace/outputs/`), these 4 had **no redundant `outputs/` copy** — so the sweep removed their last live on-disk home. They still served via the `anthropic-skills:*` plugin runtime, which is why 3 of 4 were visible in the session skill list, masking the on-disk gap.

**Fix applied:** restored all 4 (full dirs — loi-generation carries `references/`+`templates/`, psa-reconciliation `references/`+`INSTALLATION.md`) from the clean `ora-skills` repo into `01_Workspace/outputs/`. Probe returned to exit 0.

**Recurrence guard:** `01_Workspace/outputs/<skill>/` is the probe-recognized live Cowork skill home (blessed in the probe's own SKILL_PRUNE_DIRS comment). Any future skill clone-archival must leave a live `outputs/` copy, or the skill must be added to the probe's `PLUGIN_SKILL_ALLOWLIST` if it is genuinely intended to be plugin-only. See [[reference_skill_surfaces.md]].
