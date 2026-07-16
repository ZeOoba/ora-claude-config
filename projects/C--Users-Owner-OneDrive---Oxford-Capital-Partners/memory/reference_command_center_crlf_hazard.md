---
name: reference-command-center-crlf-hazard
description: oxford-command-center stores CRLF blobs with autocrlf=true and no .gitattributes — script-based file edits (Node/Python writeFileSync) silently flip EOL and bloat the commit diff to the whole file
metadata: 
  node_type: memory
  type: reference
  originSessionId: 28ce3336-c487-472e-97db-01cdb70154b3
---

`oxford-command-center` has `core.autocrlf=true` and **no `.gitattributes`**, yet its committed blobs are stored **CRLF** (e.g. `server/index.ts` = 364 LF / 364 CRLF). This combination is a trap when editing files programmatically.

**The hazard:** A Node/Python script that does `readFileSync(utf8)` → `writeFileSync` and inserts a line break with `\n` makes that one line LF while the rest stay CRLF (mixed EOL). On `git add`/commit, autocrlf=true normalizes the working-tree CRLF→LF for the *new* blob, so a blob-to-blob diff against the old CRLF blob churns **every line** — a 2-line change shows as `+365 / -364`. The PR diff becomes unreviewable and blame is destroyed.

**Detect:** after a scripted edit, `git commit` prints `LF will be replaced by CRLF`, and the commit stat shows ~full-file ins/del. Confirm the *real* change with `git diff --ignore-all-space --stat` (shows the true 2-line change).

**Fix / clean recipe:**
1. Restore exact original bytes: `git show HEAD~1:path > path` (verbatim CRLF, bypasses smudge).
2. Re-apply the edit with `\r\n` for any inserted line break; verify pure-CRLF (`LF count === CRLF count`).
3. Stage + commit with autocrlf off so the blob stays CRLF: `git -c core.autocrlf=false add path` then commit (or `--amend`).
4. Verify `git diff --cached HEAD~1 --stat` is the intended small diff before pushing.

**The Edit tool is immune** — it preserves existing EOL. Prefer Edit for surgical changes. Only fall back to a script when the target contains bytes you can't type (e.g. raw control chars) — and then use the CRLF recipe above. See [[reference-worktree-node-modules-junction-hazard]] for the sibling worktree gotcha in this repo.
