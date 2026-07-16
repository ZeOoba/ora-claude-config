---
name: reference_skill_source_paths
description: "Where ORA's Cowork user-skills physically live on disk and how to edit them from Claude Code"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e59c389d-4fd4-49b1-a853-f127b7bb86b4
---

The ORA custom skills (deal-execution, rent-comp, tax-appeal, lease-abstraction-pipeline, etc.; `creatorType: user`) are installed read-only by Claude Desktop and have **no editable source repo on disk** — they are authored in the Cowork skill editor and synced.

The live runtime copies (what skills actually load) are at:
`C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\skills-plugin\583f08bc-…\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\skills\<skill>\SKILL.md`
(`C:\Users\Owner\AppData\Roaming\Claude\…` is a redirect into that MSIX LocalCache — same files.) The GUID dirs can change on reinstall; use Desktop Commander `start_search` (content) to find current paths rather than hand-typing GUIDs (ripgrep/Glob `**` time out on this tree; DC search works).

**These files ARE writable from Code and edits take effect immediately** — but they are the Cowork-synced copies: re-editing/re-syncing a skill in the Cowork app editor will REVERT direct file edits. For durable changes, mirror them in the Cowork skill editor too.

Manifest of installed skills: `…\a6ad2c61-…\manifest.json`. See [[project_active.md]] (skills library).
