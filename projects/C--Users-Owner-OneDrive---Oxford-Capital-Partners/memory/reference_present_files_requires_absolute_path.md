---
name: reference_present_files_requires_absolute_path
description: "Cowork's present_files tool rejects relative filenames (e.g. 'foo.skill') even when the file physically exists at the documented outputs path — pass the full absolute Windows path instead."
metadata:
  node_type: memory
  type: reference
  modified: 2026-08-24T15:30:00.000Z
---

**Finding (2026-08-24, Entry Point B 8-skill install session):** `mcp__cowork__present_files`
returned "not accessible on the user's computer" for all 8 `.skill` files when called with
bare relative filenames (`{"file_path": "acquisition-underwriting.skill"}`), even though the
files had just been copied (via Desktop Commander, confirmed by `Get-ChildItem`) into the
exact outputs directory the tool's own error message named as valid.

Re-calling with the **full absolute Windows path** for each file
(`C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\<outer-uuid>\<inner-uuid>\
local_<session-uuid>\outputs\<file>.skill`) succeeded immediately, no other change made.

**Practical implication:** always pass `present_files` the full absolute outputs path, not a
bare filename — even when the tool description and prior sessions' successful calls suggest
a relative name should resolve. This is one failed round-trip to avoid, not a capability gap:
once the absolute path is used it works cleanly, including for files placed via Desktop
Commander bridge writes rather than the Write tool.

Related: [reference_cowork_no_live_skill_listing_tool.md](reference_cowork_no_live_skill_listing_tool.md)
(same session, same install pass).
