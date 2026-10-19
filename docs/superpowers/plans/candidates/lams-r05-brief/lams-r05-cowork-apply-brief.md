# LAMS/Cowork R-05 retry wording: apply brief for a native Cowork session

DRAFT. Nothing here has been applied. Companion files in this directory: `lams-r05-edits-table.md` (exact old/new text, sha base/new, flags), `edits.json` (same data, machine-readable), `lams-r05-pre-apply-checklist.md`. Method and wording follow the CC batch guide (`r05-spec-batch/.superpowers/sdd/spec-batch-guide.md`, sections 1, 3B, 4, 6-8).

## 0. Who runs this and what it may touch

- Run in a native on-device Cowork session (it must carry the scheduled-tasks MCP tools; a cloud sandbox does not). A Claude Code session cannot register on this fleet.
- Surface: `update_scheduled_task` with `taskId` and `prompt` ONLY. Never pass `cronExpression`, `fireAt`, `enabled`, `description` or any other field. Never `create_scheduled_task`, `delete_scheduled_task`, the Scheduled-sidebar trash icon, or JSON edits to the registry.
- Scope: the specs in the edits table. Do not touch the CC fleet (`~/.claude/scheduled-tasks`) or any LAMS dir not in the table.
- Stop and ask Gabriel for anything in section 8.

## 1. Read these facts first (they differ from the CC batch)

1. Every LAMS recurring task is currently `enabled:false` in the LAMS registry (2026-10-19). The only enabled row is `ora-counsel-review-standard-positions-2027` (one-time, fireAt 2027-08). So nothing fires during the apply and risk is low, but `update_scheduled_task` must not flip `enabled`. The snapshot in step 2 and the check in step 4e exist to prove that.
2. Line endings are mixed: LF for 18 of the targets, CRLF for `ora-dd-critical-tracker`, `ora-lease-expiration-brief`, `ora-monday-sync`, `ora-skill-text-audit`. Hashes are CRLF-normalized, so either is fine, but the update must not convert a file from one to the other beyond what the tool does uniformly; see the canary.
3. The registry row holds only `filePath` (no embedded prompt): the SKILL.md on disk is the thing that changes, and the tool's write is what you verify by re-reading the file.
4. Three specs are ASCII-only style (`ora-dd-critical-tracker`, `ora-health-guard-fail-aging-nudge`, `ora-underwrite-doctrine-staleness-check`): their new text already uses `--` and `section 2`, no em dash or section sign.
5. `ora-health-guard-fail-aging-nudge` is marked RETIRED 2026-09-22 in `automation-health-monitor` l.267 (retire-pending) and `ora-lams-fleet-resume-20260911` already ran (2026-09-11). Skip both unless Gabriel says otherwise.

## 2. Before anything: snapshot (section 3 of the checklist must be green)

1. `list_scheduled_tasks`: save the full output (id, cron/fireAt, enabled, lastRunAt) for every id in the edits table to `lams-r05-snapshot-before.json` in the session scratch folder. Also record the registry file's own sha and the latest line of `maintenance/_state/registry-membership.log` (read-only).
2. For each target, compute sha base (command in section 5) and compare with the table. Any mismatch: STOP for that spec (live drifted since 2026-10-19); re-base the replacement on the live text and show Gabriel the diff before any write. Never overwrite a drifted spec.

## 3. Order (one spec at a time, smallest risk first)

0. Canary: `ora-gis-endpoint-liveping` (disabled, `lastRunAt` null, one hunk, LF). Run the full per-spec loop (section 4) and answer three questions before continuing: (a) does the tool write exactly the `prompt` text to `SKILL.md` (sha new matches)? (b) does it preserve front matter / line endings as expected? (c) does `enabled` stay false? Any "no": STOP and report; do not proceed to spec 2.
1. Mechanical, reminder-style first: `ora-ar-export-freshness-nudge`, `ora-capex-idea-stage-nudge`, `ora-consolidate-memory-monthly`, `ora-exit-cap-spotcheck`, `ora-bearmode-refresh`, `ora-replacement-cost-refresh`, `ora-loan-terms-reconciliation`, `ora-dd-critical-tracker`, `ora-underwrite-doctrine-staleness-check`, `ora-ic-memo-pipeline-reconciliation`, `ora-insurance-renewal-monitor`.
2. Mechanical, Variant B and multi-hunk: `ora-friday-closeout`, `ora-lease-expiration-brief`, `ora-monday-sync`, `ora-om-intake-ocr` (2 hunks), `ora-owner-outreach-queue-refresh`.
3. The only enabled row: `ora-counsel-review-standard-positions-2027` (confirm fireAt `1817211600000` unchanged after).
4. Skip unless told otherwise: `ora-health-guard-fail-aging-nudge`, `ora-lams-fleet-resume-20260911`.
5. Design-call specs, ONLY after Gabriel ratifies the proposed wording in the edits table: `ora-skill-text-audit`, then `automation-health-monitor` last (it audits the fleet; also see the ora-skills sync note in its table row).
6. `ora-stale-pipeline-nudge`: no edit, no write.

## 4. Per-spec loop (never batch; finish and verify one before starting the next)

a. Re-read the live SKILL.md; compute sha base; must equal the table. (Mismatch: stop, section 2.2.)
b. Create the backup beside it: copy to `SKILL.md.bak-r05-20261019` in the same folder (same bytes; create-only, never overwrite an existing .bak). Compute and record its sha: it must equal sha base.
c. Build the new prompt text: take the live file bytes and apply the table's old->new replacement(s). Each old string must match exactly once in the live text; if a count is not exactly 1, STOP. The result's CRLF-normalized sha must equal `sha new` before it is sent anywhere. (The edits.json file lets this be scripted; the scratch method is how `sha new` was produced.)
d. Supervised `update_scheduled_task` with `taskId` and the full new text as `prompt`; nothing else. Gabriel approves each call in the tool's own prompt.
e. Verify, in this order: (1) re-read the file from disk (let OneDrive settle, hydrated copy), CRLF-normalized sha == sha new; (2) `list_scheduled_tasks` row for the id: cron/fireAt, enabled, description identical to the snapshot (enabled must still be false, except counsel-2027 which stays true); (3) no other row changed (diff the whole listing against the snapshot); (4) the .bak still hashes to sha base.
f. Log one line per spec to `lams-r05-apply-log.md`: id, sha base, sha new, verified yes/no, time.
g. On any failure in (e): do not continue. Roll back this spec (section 6), report, wait.

If `update_scheduled_task` flips `enabled` to true on any row: immediately call it again with `enabled:false` for that row only, record the incident, and stop the batch.

## 5. Hash command (read-only)

```
python -c "import sys,hashlib;b=open(sys.argv[1],'rb').read();print(hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()[:12])" "<path to SKILL.md>"
```

## 6. Rollback

Per spec (any failure, or Gabriel says revert): `update_scheduled_task` with `prompt` = the .bak content (sha must be the table's sha base), then repeat 4e and confirm the sha reads sha base. Keep the .bak until the whole batch is signed off.

Whole batch, order matters: revert the SPECS first, in reverse apply order (design-call specs, then variant B and multi-hunk, then the early mechanical ones, the canary last), each via the loop above. Only after every spec is reverted, and only if needed, revert the R-05 send script through its own branch / PR / merge gate (`git revert` of the R-05 merge). Never revert the script while a per-code spec is live on this fleet: a per-code spec expects exit 5/6 semantics from the new script. The specs here are legacy-mode (per-code), not contract mode, so reverting them is safe at any time; reverting the script first is the unsafe direction.

## 7. After the last spec

1. Final `list_scheduled_tasks` vs `lams-r05-snapshot-before.json`: only content hashes differ; cron/fireAt/enabled/description identical for all 23.
2. Run `python maintenance/_tests/test_send_contract_spec_lint.py` from a checkout that has it: the LAMS INFO section should list none of the edited specs (the design-call and skipped ones may still show until done).
3. Mirror `automation-health-monitor` into github.com/ZeOoba/ora-skills if Gabriel ratified that edit (see section 8 item 2); otherwise the next skill sync can undo it.
4. Expect fleet monitor noise only after re-enable: nothing fires while the rows are disabled. Note the LAMS fleet's COM reach is historically unreliable (loan-terms and stale-pipeline-nudge say so); the wording change does not alter that.
5. Return the apply log and the after-snapshot to Gabriel; do not delete the .bak files (archive per invariant 6 if cleanup is ever wanted).

## 8. Stop and ask Gabriel

1. Any sha base mismatch, any old string that does not match exactly once, any canary "no".
2. The two design-call specs. Open points are stated per spec in the edits table: `automation-health-monitor` (three send sentences, l.10 / l.425 / the Step 3 meta-failure send that has no retry text today; exit-6 audit wording; ora-skills mirror; changelog line) and `ora-skill-text-audit` (the `Publish:` log enum has no state-unknown value).
3. Whether to apply to the retired / spent specs at all.
4. Anything that would require changing cron, enabled, fireAt or description, or touching a script or the CC fleet.
5. Any concurrent registry activity (`registry-membership.log` newer than the snapshot you did not generate): stop and reconcile ownership first.
