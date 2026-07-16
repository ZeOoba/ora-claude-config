---
name: reference-memory-scope-fragmentation
description: "ROOT CAUSE CONFIRMED 2026-07-08: the '--1-' suffixed memory scope maps 1:1 to a SEPARATE, incomplete physical OneDrive folder ('...Partners (1)\\'), not a Claude Code hash artifact. Memory consolidated into this (canonical, complete) scope. RESOLVED 2026-07-09: guard scripts + CLAUDE.md pointer repointed. CONSOLIDATION EXECUTED (Claude-system scope) 2026-07-09 evening: all live hardcoded '(1)' paths repointed, '(1)' Claude trees emptied+tombstoned; BUSINESS BULK DEFERRED — '(1)' is NOT fully stale (live Attachments inflow, two OneDrive sync clients) — see the 2026-07-09 evening section + bulk manifest in 01_Workspace/outputs. ACCOUNT QUESTION RATIFIED 2026-07-10 (Gabriel): the no-suffix folder (`OneDrive - Oxford Capital Partners`) syncs egoldberg@oxfordra.net (registry `Business1`) and is the ratified MAIN/canonical account going forward; `(1)` syncs ggoldberg@oxfordra.net (`Business2`) and stays non-canonical. Business-bulk unlink-vs-consolidate for `(1)` is still open — see the 2026-07-10 section below."
metadata:
  node_type: memory
  type: reference
  originSessionId: 006ecde9-8f07-4a02-8e6b-5927591bda0d
---

Discovered 2026-07-08 while evaluating the Claude Code setup after an Item E fix session; root-caused later the same day while executing a separate workflow-optimization task.

## What it looked like initially

There appeared to be at least three distinct memory-directory scopes on this machine:

1. `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\` — this session's own stated scope (per system prompt), effectively empty until this session started writing to it.
2. `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-\memory\` — a richly-populated store (firm.md, people.md, rules.md, tech.md, dozens of project/deal files, accumulating since 2026-06-03) that CLAUDE.md's own text names as canonical.
3. `C:\Users\Owner\.claude\projects\C--Users-Owner-oxford-command-center\memory\` — a SEPARATE, repo-specific store that only loads for sessions whose project directory IS `C:\Users\Owner\oxford-command-center` directly.

## Root cause (confirmed 2026-07-08)

Claude Code's project-directory naming is a straight sanitization of the absolute cwd (non-alphanumeric chars → `-`). Reconstructing both candidate paths character-for-character:

- `C:\Users\Owner\OneDrive - Oxford Capital Partners` → `C--Users-Owner-OneDrive---Oxford-Capital-Partners` (scope #1 above)
- `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)` → `C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-` (scope #2 above)

**These are two different physical folders on disk**, both present at `C:\Users\Owner\`:

| | `OneDrive - Oxford Capital Partners` | `OneDrive - Oxford Capital Partners (1)` |
|---|---|---|
| Top-level item count | 197 | 87 |
| `Investment Candidates -- 2026\` (active deal files, e.g. today's DollarGeneral-Cincinnati v03) | present | **absent** |
| `Claude_Workspace\01_Workspace\` (CLAUDE.md's own documented "active deals & contacts" path) | present | **absent** |
| `Claude_Workspace\01_Cowork_OS\`, `02_Outputs\`, `03_Code\` | present | **absent** (only `00_Governance\` + `_Archive\`) |
| Property folders (1100 Rarig, 1851 South Club Solar LLC, etc.) | present | absent |
| Most recent content | today (2026-07-08) | 2026-07-07 16:31, sparse, with OneDrive-style internal `(1)` duplicate-named files (e.g. two copies of a lease draft) suggesting an interrupted/partial resync |

The system prompt's own "Primary working directory" for every session so far has been the plain (no-suffix) folder — confirmed complete, current, and matching CLAUDE.md's documented paths. The `(1)` folder looks like a stale or partially-resynced duplicate, plausibly connected to the 2026-07-05 Desktop app reinstall documented in `oxford-cc-repo-health.md` (that incident is independently confirmed to have disrupted other local Claude/OneDrive-adjacent state on this machine). This is inference, not confirmed — the actual OneDrive-client mechanics (why two folders exist, whether `(1)` is still being written by anything, whether Windows/OneDrive will reconcile them automatically) were NOT investigated further, since touching the OneDrive folders themselves requires Gabriel's permission (CLAUDE.md invariant 5 / rules.md §1: non-Claude OneDrive business folders — read fine, write/move/delete needs permission).

## What was done (2026-07-08, safe/reversible only)

- Copied every file from the `--1-` scope into this (plain, no-suffix) scope. **Non-destructive** — nothing in `--1-` was deleted or modified; this was a straight `cp`.
- Merged the two `MEMORY.md` indexes into one, here, combining both link sets.
- Did NOT touch: the `(1)` OneDrive folder itself, CLAUDE.md's `Memory:` pointer line, or any maintenance/guard script.

## RESOLVED 2026-07-09 — verified by direct inspection

A prior sweep (below, kept for history) found 6 live maintenance scripts plus CLAUDE.md hardcoding the `--1-` scope. Direct inspection on 2026-07-09 (as part of a full Claude Code setup audit) confirmed:

- `~/.claude/maintenance/governor-drift-probe.py` (line 36), `~/.claude/maintenance/doctrine-integrity-probe.py` (line 96), `~/.claude/maintenance/registry-membership-probe.py` (line 56) — all three now reference the canonical no-suffix scope. Grep for `--1-`/`Partners (1)` across all three returns nothing.
- `~/.claude/CLAUDE.md`'s `Memory:` pointer — confirmed reading the plain, no-suffix path in the version loaded this session.
- `~/.claude/maintenance/append-event-log.py` — already using the canonical scope (see original note below).
- `~/.claude/maintenance/cc-verifier-probe.py` and `~/.claude/maintenance/setup-self-audit.py` — still NOT independently checked for this pattern; treat as unverified, not as confirmed-broken or confirmed-fixed.

No repointing action was taken by this audit beyond confirming current state — if the two unchecked scripts are later found to still hardcode `--1-`, that repointing still needs the same care described below (governor/confidentiality blast-radius).

### Original 2026-07-08 finding (history)

A repo-wide grep for the `--1-` scope path turned up **6 live maintenance scripts** plus CLAUDE.md itself still hardcoding it as the target:

- `~/.claude/maintenance/append-event-log.py` — the sanctioned single-writer event-log appender (its `LOG` constant). *Used this session before the root cause was known — today's Item 1 entry landed correctly in `--1-`/event_log.md, now also copied here.*
- `~/.claude/maintenance/governor-drift-probe.py` — **enforces hard invariant 4** (DSCR ≥1.25x / LTV ≤40% must appear nowhere else in config/memory/skills). Currently scans `--1-` only — any governor-constant drift written into files under THIS (plain) scope since the fork would not be caught.
- `~/.claude/maintenance/doctrine-integrity-probe.py` — **confidentiality egress scanner** (hard invariant 3). Same blind-spot risk: scans `--1-` memory only.
- `~/.claude/maintenance/registry-membership-probe.py` — generates the live-fleet roster banner loaded into every session's context.
- `~/.claude/maintenance/cc-verifier-probe.py`, `~/.claude/maintenance/setup-self-audit.py` — not yet inspected for the same pattern.
- `~/.claude/CLAUDE.md` line ~70 — the `Memory:` pointer itself. *(Already reads the plain, no-suffix path as of the version loaded 2026-07-08 sessions — appears fixed since this file was written; not independently re-verified line-by-line.)*

**Do not repoint any of these** without Gabriel's explicit confirmation of which physical OneDrive folder (and therefore which memory scope) is meant to be canonical going forward — governor-drift-probe and doctrine-integrity-probe are exactly the "governor constant" / "confidentiality" blast-radius category the Engineering OS section flags as requiring the highest care, and getting the direction wrong here (e.g. if `(1)` turns out to be the one OneDrive intends to keep, or if both get reconciled by OneDrive automatically) would mean rewriting them twice.

### 8th instance found and fixed, 2026-07-08 (evening) — `Claude_Workspace\01_Workspace\CLAUDE.md`

Not on the original grep list above (that grep ran against `~/.claude`; this file lives on OneDrive and wasn't scanned). This is the **thin-pointer CLAUDE.md that every Cowork session on this workspace loads as context** — its `Memory:` line hardcoded the `--1-` path, meaning Cowork sessions have been directed at the stale/incomplete scope since at least 2026-06-10 (when the thin-pointer was written) through today. Root-caused this after a Cowork session's Skill Text Audit remediation hit a "couldn't find the file" wall on an unrelated task (CC-fleet verification), which led back here.

**Unlike the 6 scripts above, this one was corrected immediately, not left OPEN** — it's a documentation pointer, not a governor-enforcement or confidentiality-scan script, so the "getting the direction wrong is costly" caution above doesn't apply with the same force, and the plain (no-suffix) scope is already the de facto working assumption everywhere else (this file's own "How to apply" section, the 2026-07-08 MEMORY.md scope-consolidation note, and every session's actual cwd). Repointed to the plain path; see that file's own changelog line.

## How to apply

- Before starting non-trivial work in `oxford-command-center` (or any other sub-repo with its own `.claude/projects/C--Users-Owner-<repo>/memory/` scope) from an OneDrive-scoped session, proactively Read that repo's own `MEMORY.md` index first.
- Until Gabriel confirms which OneDrive folder is canonical, treat **this** (plain, no-suffix) scope as the working one — it's what the session's actual cwd resolves to and it's the complete/current copy — but be aware the governor and confidentiality guards are not yet watching it.

## 2026-07-09 (evening) — Task 12 consolidation executed (Claude-system scope); business bulk DEFERRED with evidence

ONEDRIVE_CONSOLIDATION=EXECUTE was ratified on the premise that "(1)" is a stale pre-migration
duplicate. Direct inspection PARTIALLY falsified that: (a) `(1)\Attachments\` receives LIVE
inflow (July 2026 Allentown Portfolio deal files); (b) TWO OneDrive.exe sync clients run
concurrently — local moves out of "(1)" propagate as cloud deletions in whatever account it
syncs; (c) but the `(1)` Claude trees WERE stale residue (last writes 07-07/07-08, from
since-corrected hardcoded paths), and `(1)` has NO `eric spreadsheets` or `Property Financials`
folders — several code defaults pointing there were dead traps.

Executed: every live hardcoded "(1)" path repointed — 4 ora-ops plugin command pointers (plus
retired-Composio/egoldberg text cleaned), oxford-command-center PR #199 (workbookPath default,
3 warehouse-script fallbacks, README; .env already carried canonical WORKBOOK_PATH so runtime
behavior was already canonical). `(1)` Claude trees (3 files) archived to canonical
(`Scheduled\_archive_2026-07-09_onedrive-1-residue\` + `01_Workspace\_archive\...`) with
MOVE-MANIFEST + tombstones; canonical `Documents\Claude\{Outputs,Workspace}` mirrors created.
DEFERRED to Gabriel: the business bulk (loose lease/LOI/PSA docs, Attachments, Desktop, Meetings,
Pictures, Recordings, Whiteboards, rest of Documents) — inventory at
`01_Workspace\outputs\2026-07-09_OneDrive-1-BulkMove_Manifest_v01.md`; the OneDrive account
question (which account syncs "(1)"; unlink vs consolidate) must be answered first.

## 2026-07-10 — OneDrive account question answered + ratified (ledger-restore incident)

Discovered mid-task while restoring a damaged governance ledger (`2026-06-10_fleet-disposition-
ledger.md` — see `event_log.md` same date): OneDrive Version History for the canonical
(no-suffix) folder's file was NOT reachable under Gabriel's own signed-in browser session at
`oxfordraeg-my.sharepoint.com/personal/ggoldberg_oxfordra_net/...` — that account's cloud copy
of `Claude_Workspace` matched the SPARSE, already-flagged-stale `(1)`-folder content (just
`_Archive` + an empty `Scheduled` + `MOVED-SEE-CANONICAL.md`), not the rich canonical workspace.

Root-caused via the local OneDrive client's own registry state (`HKCU\Software\Microsoft\
OneDrive\Accounts\{Business1,Business2}`, read via `Get-ItemProperty`):

| Registry key | `UserFolder` | `UserEmail` | `ServiceEndpointUri` |
|---|---|---|---|
| `Business1` | `OneDrive - Oxford Capital Partners` (no suffix — canonical) | **egoldberg@oxfordra.net** | `.../personal/egoldberg_oxfordra_net/_api` |
| `Business2` | `OneDrive - Oxford Capital Partners (1)` (non-canonical) | **ggoldberg@oxfordra.net** | `.../personal/ggoldberg_oxfordra_net/_api` |

I.e. the canonical, no-suffix `Claude_Workspace` folder that every session's doctrine already
treated as "the" workspace is physically synced under **Eric's** OneDrive account, not
Gabriel's own — the opposite of what the naming (`Business1` = first-added, no suffix) would
suggest without checking `UserEmail`. Gabriel has delegate/shared access to Eric's personal
SharePoint site, so pointing the browser at `.../personal/egoldberg_oxfordra_net/...` (not
`ggoldberg_oxfordra_net`) worked immediately for the Version History restore.

**Ratified (Gabriel, 2026-07-10):** Eric's account (`Business1`, the no-suffix folder) is the
MAIN/canonical account for `Claude_Workspace` going forward — this closes the "which account
syncs which folder" half of the open question above. The account itself does not need to
change; this is a confirmation of already-de-facto behavior (every session's cwd already
resolved to the no-suffix folder), not a migration. The business-bulk unlink-vs-consolidate
question for `(1)`/Gabriel's own account (manifest referenced above) is still open and
unaffected by this ratification.

**How to apply:** if a future OneDrive-Version-History (or any other Eric-account-specific
SharePoint/Graph) action is needed on a canonical `Claude_Workspace` file, browse/query under
`egoldberg_oxfordra_net`, not `ggoldberg_oxfordra_net` — Gabriel's own account only fronts the
non-canonical `(1)` folder's content.
