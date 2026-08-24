---
name: claim-work-paths-comma-vs-space
description: claim_work.py --paths silently mis-parses a comma-joined path string instead of erroring
metadata: 
  node_type: memory
  type: reference
  originSessionId: b8041321-02f8-4c99-ad04-edf8e6a8241d
  modified: 2026-08-24T15:32:33.003Z
---

`hooks/lib/claim_work.py claim <slug> "<desc>" --paths` takes **space-separated** paths (argparse `nargs='*'`), not comma-separated. Passing `--paths "a.ts,b.ts"` does not error — it silently stores the whole comma-joined string as ONE bogus path, so the claim covers neither file and looks successful (`covering 1 path(s)`).

**Why:** discovered 2026-08-17 while claiming two files for the OI-137 fix — the claim "succeeded" with `covering 1 path(s)` when 2 were expected, and the stored path in the JSON was the literal comma-joined string. Re-running with space-separated args (`--paths "a.ts" "b.ts"`) fixed it and reported `covering 2 path(s)`.

**How to apply:** always pass multiple `--paths` values space-separated, one shell-quoted path per value. After any multi-path claim, `cat` the resulting JSON in `~/.claude/hooks/active-work/<slug>.json` and verify the `paths` array has the expected element count before trusting the claim.
