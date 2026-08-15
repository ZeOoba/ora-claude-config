---
name: reference-powershell-git-show-corrupts-nonascii
description: "In PowerShell, `& git show` output is decoded via [Console]::OutputEncoding (IBM437 in unattended -NoProfile runs), silently corrupting every non-ASCII character — never use it to read a blob you intend to write to disk or hash."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1d24d6a4-676c-4fa5-9cd5-5d98e7d12064
  modified: 2026-08-09T14:54:47.615Z
---

`& git show "HEAD:path"` in PowerShell does **not** return the blob's bytes. PowerShell decodes
the child process's stdout using `[Console]::OutputEncoding`, which in an unattended
`powershell.exe -NoProfile` run on this machine is **IBM437**, not UTF-8. Every non-ASCII byte is
mangled before your code ever sees it.

Measured 2026-08-09 on LAPTOP-CSHSCBE6:

```
Console::OutputEncoding = IBM437 / OEM United States
committed codepoints : 65,8212,66,8594,67,10        <- "A—B→C"
git-show codepoints  : 65,915,199,246,66,915,229,198,67
committed bytes=10   via-PowerShell bytes=15        ROUND-TRIPS INTACT? False
```

Two consequences, both silent:
1. **Writing it back corrupts the file.** Every ORA SKILL.md is dense with `—  →  “ ”  ≥  ·`, so a
   git-sourced restore writes garbage over all of them.
2. **Hashing it can never match a file hash**, so any "is the working file the same as HEAD?"
   comparison built this way is permanently false — dead code that looks live. Line-joining
   (`-join "\`n"`) separately drops the trailing newline, which breaks the comparison even for
   pure-ASCII files.

**Do instead** — read the raw stream, never the decoded string:

```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'git'; $psi.Arguments = "-C `"$Repo`" show `"HEAD:$Rel`""
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
$p = [System.Diagnostics.Process]::Start($psi)
$errTask = $p.StandardError.ReadToEndAsync()     # drain stderr or risk deadlock
$ms = New-Object System.IO.MemoryStream
$p.StandardOutput.BaseStream.CopyTo($ms)          # BaseStream = undecoded bytes
$p.WaitForExit(); if ($p.ExitCode -ne 0) { return $null }
```

Then check `ExitCode` **and** a non-zero length before writing — a failed `git show` yields `$null`,
and `$null -join "..."` is `""`, so an unchecked write produces a **zero-byte file**.

Related traps found in the same pass:
- `$ErrorActionPreference='Stop'` makes a native command's **stderr** a terminating error, so an
  ordinary git autocrlf warning aborts the script — even with `2>$null`.
- `Set-Content -Encoding UTF8` emits a **BOM** on Windows PowerShell 5.1. Use
  `[System.IO.File]::WriteAllBytes`, or `WriteAllText` with `New-Object System.Text.UTF8Encoding($false)`.
- A 0-byte file hashes to the SHA of the empty string — a *valid* hash. Treat 0 bytes as
  "no usable content" explicitly, or truncation gets adopted as real content.

Found while fixing `ora-task-integrity-guard/guard.ps1` (see [[reference-tech]]); the corruption was
introduced by a fix and caught only by an independent review, because every test in the suite had
disabled the git path. See also [[feedback-refute-pass-proactive-default]].
