---
name: ora-portfolio-desk-refresh
description: Weekly Monday 12:05 ET — rebuilds the ORA Portfolio Desk dashboard's five datasets from oxford-command-center origin/main data/snapshots/portfolio.json (read-only; landed by ora-cc-snapshot-refresh Mon 06:15) and re-uploads only the changed ones to https://claude.ai/artifact/5cFq6uQEcwXaMoESDoQUPy. No email on success or no-change; alert to ggoldberg@ only on failure. [MODEL: UNVERIFIABLE | set 2026-11-06]
---

CONNECTOR SCOPE: no connectors — this task uses only local Bash, the built-in Artifact tool and the built-in ArtifactData tool. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7, Claude Code Remote, or any other connector, even if they are available in this session.

ORA Portfolio Desk refresh. You keep the ORA Portfolio Desk dashboard (https://claude.ai/artifact/5cFq6uQEcwXaMoESDoQUPy, a Dashboard-type artifact) current with the Oxford Command Center snapshot. You have no memory of prior runs. Never fabricate figures, dates or blob URLs: every value you write comes from the builder's manifest or a tool result in this run.

RUN DATE: compute once at start with `date '+%A %Y-%m-%d'` and reuse that exact value everywhere below.

SIBLINGS (do not duplicate their work): `ora-cc-snapshot-refresh` (Mon 06:15) regenerates portfolio.json from the Master Workbook and lands it on origin/main by PR. This task only reads that result. Never run `npm run extract`, never write inside C:\Users\Owner\oxford-command-center, never touch its working tree.

PY = C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe (bare `python` is not on PATH in scheduled sessions)
BUILDER = C:/Users/Owner/.claude/scheduled-tasks/ora-portfolio-desk-refresh/build_datasets.py
OUT = C:/Users/Owner/AppData/Local/Temp/ora-portfolio-desk

DOUBLE-FIRE ENTRY GUARD (added 2026-11-14; run FIRST, before step 1; see scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md):
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-portfolio-desk-refresh --block main --run-id <session run_id> --ttl-min 30 --period week
- Exit 0 (PROCEED): this run owns the claim and MUST end in `complete` or `fail` below.
- Exit 10 (SKIP_ALREADY_COMPLETE): this week's run already completed. Skip the whole task (no writes, no email) and report a normal skip.
- Exit 11 (STAND_DOWN_IN_PROGRESS): another run holds the claim. Stand down and report it.
- Exit 12 or anything else: stop, run none of the steps, and report the exit and output.
Terminal call, after step 6 (or after the FAILURE alert):
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-portfolio-desk-refresh --block main --run-id <run_id> --period week
(append `--email-sent-at <ISO time>` when the FAILURE alert was sent).
If the run cannot finish (any step fails and the task stops), release the claim instead:
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-portfolio-desk-refresh --block main --run-id <run_id> --period week --error "<one line>"
Never pass --force from a scheduled fire.

STEPS
1. Build: run `"$PY" "$BUILDER" --out "$OUT"` and read stdout + exit code.
   - Exit 10: nothing changed since the last upload. Report "no change; snapshot asOf <asOf>, generatedAt <generatedAt>" in your final summary and STOP. No uploads, no writes, no email.
   - Exit 1: go to FAILURE.
   - Exit 0: continue. Read "$OUT/manifest.json". `changed` lists the dataset ids to refresh (subset of: properties, leases, ar-aging, loans, cash).
2. Read the artifact once before any publish: Artifact tool, action "read", url https://claude.ai/artifact/5cFq6uQEcwXaMoESDoQUPy (a publish to an artifact this session has not read is refused).
3. For EACH id in `changed`: upload its file as an asset — Artifact tool, action "publish", url https://claude.ai/artifact/5cFq6uQEcwXaMoESDoQUPy, asset true, file_path = manifest.datasets[id].file (one call per file; JSON files cannot be batched). Take the returned "/_blob/<id>" url verbatim. If any upload fails, go to FAILURE without touching the store.
4. ArtifactData tool, url as above: for each changed id, `get` collection "datasets", doc_id <id>, and note its `version`. Then ONE `batch` of `update` writes, one per changed id, each pinned with if_version = that version, data =
   {"source": {"kind": "file", "url": "<new /_blob url>", "name": manifest.datasets[id].name, "format": "json"}, "updated": manifest.datasets[id].updated, "edit": {"via": "claude", "at": "<current UTC ISO time>"}}
   Change nothing else: never rewrite files/index.html, dash/meta, titles or descriptions. If the batch is refused for a version conflict, re-get those docs once and redo the batch once; a second refusal goes to FAILURE.
5. Record the upload: write {"<id>": "<new /_blob url>", ...} for exactly the ids written in step 4 to "$OUT/uploads.json", then run `"$PY" "$BUILDER" --out "$OUT" --record "$OUT/uploads.json"`. Skip this step if step 4 did not commit (so the next run retries).
6. Final summary (session output only, no email): run date, snapshot asOf/generatedAt, which datasets were refreshed with their row counts, and that superseded blobs were left in place (never delete assets).

FAILURE
Email an alert via the SOLE send path: write the body to a temp file, then run
`powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ALERT] ora-portfolio-desk-refresh — <one-line reason> — <run date>" -BodyFile "<temp file>"`
TO ggoldberg@oxfordra.net ONLY, no cc. Body: which step failed, the exact error text quoted verbatim, what was and was not written to the artifact, and a QUESTIONS FOR GABRIEL list for anything needing his call. Retry only on exit 2 or 4, once, then flag in the summary; never resend after any other exit (send state unknown), and flag that loudly. Do not halt on a send failure — report it in the final summary.

GUARDS
- If the Artifact or ArtifactData tool is unavailable or a call is refused for permissions, that is a FAILURE (say so plainly); do not improvise another upload path.
- The Potomac residence and intercompany notes are excluded by the builder by design (Gabriel rulings); do not add them back.
- Never edit the builder script, this SKILL.md, or the dashboard page during a run.