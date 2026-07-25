---
name: feedback-workingset-sum-overcounts-shared-ram
description: "Summing Get-Process WorkingSet across many processes double-counts shared/mapped pages and overstates true RAM pressure or headroom — use the `\\Memory\\Available MBytes` perf counter for the real system-wide number instead."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: eb5c118f-b719-4492-9dfa-5df5122de7b6
  modified: 2026-07-24T17:17:27.133Z
---

Never judge RAM urgency by summing `WorkingSet`/`WorkingSet64` across `Get-Process` results, especially for many instances of the same or Electron-family binaries (heavy shared DLL/asar/mapped-file pages). Each process's WorkingSet includes shared pages it maps, so the same physical page gets counted once per process — summing overstates the true distinct memory in use.

**Why:** On 2026-07-24, investigating whether the machine's RAM was tight enough to warrant `/heavy`, a first pass summed `Get-Process claude`'s WorkingSet (9.49GB) against a ratified 24GB internal ceiling and concluded "comfortable headroom, not urgent." A follow-up summed WorkingSet across *every* process on the box (claude + everything else) and got 37.7GB — on a 32.1GB machine. That's mathematically impossible without double-counting, which falsified the whole methodology retroactively. The one number that turned out to be trustworthy was the OS-computed `\Memory\Available MBytes` perf counter (confirmed to agree closely with `Win32_OperatingSystem.FreePhysicalMemory`, ruling out a Free-vs-Available metric-choice error as the flaw) — it showed genuinely available memory at ~3.2–3.4GB, ~10.7% of the box, a materially different and more concerning picture than the WorkingSet-sum comfort story.

**How to apply:** For "is this machine actually under memory pressure" — always start with `(Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue`, not a per-process WorkingSet sum. A per-app WorkingSet figure (e.g. "claude.exe uses X GB") is fine for relative/comparative framing ("claude is the biggest single consumer") but is NOT reliable for "would closing X actually free Y GB" — for that, use Private Working Set (`Get-Counter '\Process(name)\Working Set - Private'`) or Win32_Process's private-bytes-adjacent counters, which exclude shared pages. If a sum of WorkingSet across all processes ever exceeds total physical RAM, that's a built-in falsification check — the summation approach is broken, not the machine.

Related: [[reference_lean_ram_toolkit]] (the ratified 24GB ceiling doctrine this session was checking against).
