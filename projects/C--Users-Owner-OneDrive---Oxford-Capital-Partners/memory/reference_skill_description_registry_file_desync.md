---
name: reference-skill-description-registry-file-desync
description: "CORRECTED 2026-08-12 — the 'description lives in TWO stores' premise is FALSE. Neither registry JSON stores description or prompt; SKILL.md is the sole store and list_scheduled_tasks renders from it, so a file-only edit IS durable and there is no drift to resync. What remains true: update_scheduled_task rewrites the whole SKILL.md from its arguments and drops non-owned frontmatter keys — so that call is the risk, not the cure."
metadata: 
  node_type: memory
  type: reference
  originSessionId: deb373ac-940f-41f2-b5e3-b47443e7bb33
  modified: 2026-08-12T22:45:55.903Z
---

**This file previously asserted the opposite. That assertion was wrong and is corrected here — the earlier version is what caused a downstream session to avoid a safe frontmatter edit and to report a non-existent "registry stale by two bumps" drift on 2026-08-12.**

## The corrected fact

A scheduled task's `description` is stored in **ONE** place: the `SKILL.md` frontmatter. `list_scheduled_tasks` renders its `description` by reading the SKILL.md at the entry's `filePath`. There is no second copy and therefore no drift.

**Verified 2026-08-12 by direct structural inspection of both registry JSONs** (read-only; recursive glob found exactly ONE registry file per fleet, so this is not a wrong-file artifact):

| | CC/MCP | LAMS/Cowork |
|---|---|---|
| entries | 32 | 30 |
| `description` key present | **no** | **no** |
| `prompt` key present | **no** | **no** |
| description text found in raw file | **no** | **no** |

LAMS entry keys are exactly: `id, cronExpression, enabled, filePath, createdAt, lastRunAt, lastScheduledFor, userSelectedFolders, userSelectedFiles, approvedPermissions, notifySessionId`. CC/MCP adds `cwd, fireAt, model, useWorktree`. No description anywhere. The decisive test was searching each raw registry file for literal description substrings (`"Weekday 3x/day"`, `"ORA automation fleet health check"`) — absent from both registries, present in the SKILL.md.

## Why the original "verification" passed vacuously

The prior version proved sync by comparing the SKILL.md `description:` length+sha against `list_scheduled_tasks`'s `description` (recorded: `ora-lease-snapshot-refresh` 5199 chars / `18bacbbefffa`). Those two values are **the same string read twice** — `list_scheduled_tasks` sources it from the file. The comparison cannot fail, so it is not evidence of a second store. (The 5199 reconciles exactly with the 5200 measured here; the difference is the leading space after `description:`. Same file, same content — which is the point.)

**Generalizable lesson:** a consistency check between two views of the SAME source always passes. Before trusting one, prove the two reads have independent origins. See [[feedback_verified_null_vs_inferred_null]] — and note the symmetric error made the same day: grepping a registry for a version string, finding nothing, and concluding "stale" when the FIELD does not exist.

## What remains TRUE and still matters

`update_scheduled_task` **rewrites the entire SKILL.md** from its arguments. It drops non-owned frontmatter keys ([[reference_update_scheduled_task_drops_frontmatter_keys]], OI-109 — a `description` retag silently deleted `output_contract`) and rewrites line endings to LF (expect `LF will be replaced by CRLF` on the next commit touching that path; diff with `--strip-trailing-cr`). Frontmatter is parsed line-wise, not strict YAML ([[reference_skill_frontmatter_lenient_parse]]), so a long single-line description with colons and quotes is fine.

## How to apply

- **Editing `description` or body prose directly in SKILL.md is safe and durable.** Do it with Edit. No follow-up `update_scheduled_task` is needed to "sync" anything.
- **Do NOT call `update_scheduled_task` merely to propagate a description.** That call is the hazard (whole-file rewrite + key drop), not the remedy. Reserve it for what it actually owns: `cronExpression`, `enabled`, `fireAt`, `notifyOnCompletion`.
- If you must call it for a real scheduling change, take a pre-call copy of the SKILL.md and diff after — per the key-drop reference above.
- A LAMS task's SKILL.md is editable from the CC/MCP surface (it is an ordinary file on disk); only the *registry* write needs the matching fleet's MCP. Scheduling changes to a LAMS task still require Cowork.
