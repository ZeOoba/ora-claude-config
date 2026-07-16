---
name: reference-machine-resources
description: "Gabriel's laptop hardware constraints and Claude disk/memory footprint — the levers for freeing space and RAM"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0d802c3a-8cc3-4df8-a094-8af95ac55191
---

Gabriel's primary laptop (Windows 11 Home, win32). Profiled 2026-06-03.

## Hardware constraints
- **RAM: 5.69 GB usable, NOT UPGRADEABLE (resolved 2026-06-03).** Machine is **Lenovo 83BS** (IdeaPad). Memory is **soldered LPDDR5-6400** (Win32_PhysicalMemory: Type=LPDDR5, 4 channels P0 CHANNEL A/B/C/D, FormFactor=0, identical Micron part MT62F512M32D2DR-031). LPDDR5 = no socket; there is no RAM stick to add. **The only path to >5.7 GB is a new machine.** The SMBIOS "4 slots / 64 GB max" reading is a firmware placeholder, not real sockets — ignore it.
- **8 GB physical, only 5.69 GB visible** — ~2.3 GB is carved off at firmware level (almost certainly the iGPU UMA frame buffer). No BCD/msconfig cap exists (verified — no `truncatememory`/`maxmem`), so the only place that ~2.3 GB might be reclaimed is a **BIOS "UMA Frame Buffer Size" setting — usually locked to Auto on IdeaPads** [SPECULATIVE]; worth one look but don't count on it.
- **Live state runs HOT: 95.4% used, ~0.26 GB free (measured 2026-06-03, worse than the earlier ~81%).** Pagefile (18 GB on C:) actively holding 5.5 GB, peak 6.2 GB; Memory Compression 445–717 MB. The machine is at its ceiling and paging heavily to the SSD. Do NOT shrink the pagefile — it's what prevents OOM. 16 GB would transform it; this unit can't get there. [[user-gabriel]]
- **Disk: single C: volume (~475 GB, Windows-SSD).** No second volume — so "archiving" files to another folder frees no drive space; only deletion or compression does. Conflicts with the ORA no-delete rule, so NTFS compression (`compact /c`) is the rule-compliant way to reclaim space on text data. [[feedback-workflow]]

## Claude disk footprint (the big levers)
- `AppData\Roaming\Claude` ≈ 18 GB total, dominated by:
  - **`vm_bundles\claudevm.bundle` ≈ 14 GB** — the Claude Code SANDBOX VM runtime (created 4/21, refreshed 5/31/2026). Single biggest item on the machine. Deleting it frees 14 GB but forces a full re-download on next sandboxed run and may break sandbox/Cowork-VM execution. Only remove if sandboxed execution is genuinely unused. Needs Gabriel's explicit call.
  - **`local-agent-mode-sessions\a6ad2c61-…` ≈ 2.5 GB** — ⚠️ contains the CANONICAL live scheduler registry (`scheduled-tasks.json`). Do NOT bulk-delete; the registry file is tiny, the bulk is session artifacts. See active-context note.
- **Safe, regenerable caches (~6 GB, clear anytime):** npm-cache (`%LOCALAPPDATA%\npm-cache`, ~3.7 GB → `npm cache clean --force`, leaves ~1.6 GB floor), `%TEMP%` (~1.9 GB), Claude Desktop Electron caches (`Code Cache`/`Cache`/`GPUCache`, ~0.4 GB), node-gyp (~60 MB). Tier-1 cleanup on 2026-06-03 reclaimed **+4.4 GB** this way.
- `.claude\projects` transcripts ≈ 97 MB across ~89 JSONL — marginal; held open by live sessions so can't be compressed in place while running.
- ⚠️ Clearing all of `%TEMP%` while Claude Code runs deletes its own live output-capture files (under `%TEMP%\claude\…`). Exclude that subfolder when scripting Temp cleanup.

## Memory footprint
- ~48 Claude helper processes typical (14 `claude` + 18 `node` + 16 `python`), ~1.6 GB. **All trace to a live parent — no orphans to kill.** RAM is held by the active Claude Desktop + Claude Code tree and its MCP servers, not zombies.
- Only **3 LOCAL MCP servers** configured in `.claude.json`: `excel` (.exe), `fred` (uv/python), `context7` (remote http). The dozens of other connectors (Notion, HubSpot, Composio, M365, Grain, UUID-named) are REMOTE/cloud — they don't consume local RAM. So trimming local MCP barely helps.
- Memory levers, in order: close concurrent apps (Chrome, Obsidian, **msedgewebview2 ~154 MB across 20 procs — new Outlook/Teams/Widgets**) → restart Claude when the active session balloons (one live `claude` proc measured 920 MB; full stack 1.77 GB / 49 procs) → `/clear`+`/compact` between tasks → cap parallel subagents/workflows. **RAM upgrade is NOT available (soldered) — replace the machine to fix permanently.**

Reusable cleanup script left at `C:\Users\Owner\oxford-perfection\_cleanup_tier1.ps1`.
