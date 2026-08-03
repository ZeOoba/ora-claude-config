---
name: docx-verification-windows-gap
description: "The docx skill's render-and-look verification step cannot run on this machine — soffice.py is Unix-only and LibreOffice/Poppler are absent; use maintenance/docx-to-pdf.ps1 (Word COM) and accept structural, not visual, evidence"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ebb67ffe-c6aa-4b85-aeff-a2edf57cf1eb
  modified: 2026-08-03T19:14:44.347Z
---

The `docx` skill tells you to verify output by rendering it and looking at it:
`scripts/office/soffice.py --headless --convert-to pdf` → `pdftoppm` → Read the
images. **That whole chain is unavailable on LAPTOP-CSHSCBE6.** Don't discover
this again mid-task.

## Three independent blockers, all verified 2026-08-03

1. **`soffice.py` is Unix-only.** It calls `socket.AF_UNIX`, which does not exist
   on Windows — it dies with `AttributeError: module 'socket' has no attribute
   'AF_UNIX'` before it ever looks for LibreOffice. Its own docstring scopes it
   to "environments where AF_UNIX [is blocked]"; it is a Linux-sandbox shim, not
   a general converter.
2. **LibreOffice is not installed.** Verified null, not inferred: `winget list
   --name LibreOffice` → no package, recursive `soffice.exe` sweep of both
   Program Files trees (depth 4) → nothing, scoop apps dir → absent.
3. **Poppler is not installed**, so `pdftoppm` is missing and the Read tool's own
   PDF page rendering fails with "pdftoppm is not installed". There is currently
   **no way to look at a rendered page on this machine.**

## What to do instead

`python ~/.claude/maintenance/docx-to-pdf.ps1 -In <doc> [-Out <pdf>]` — Word COM
wrapper, written for this gap. Uses `ExportAsFixedFormat` (wdExportFormatPDF),
so the PDF carries a real extractable text layer, satisfying CLAUDE.md's
no-Print-to-PDF rule. Opens read-only, prints a page count, exits 0/1/2/3
(converted / usage / Word COM unavailable / conversion failed).

Two Word COM footguns it already handles, both hit live:
- **`$word.Quit(0)` throws** `NonRefArgumentToRefParameterMsg` — Quit takes ref
  params in some builds. Call `$word.Quit()` bare.
- **A failed Quit orphans a headless WINWORD process.** The script snapshots
  WINWORD PIDs before starting and stops *only* the one it created, so a Word
  window the user already has open is never killed. Never blanket
  `Stop-Process -Name WINWORD` — Gabriel routinely has deal documents open.

## The honest verification bar, absent a renderer

For a surgical `word/document.xml` edit, treat these four as sufficient and say
plainly that no visual check was possible:

1. `scripts/office/validate.py <new> --original <old>` — XSD clean.
2. Paragraph parity in that same output (`238 → 238`) — catches structural damage.
3. Text extraction showing the intended strings present and the old ones gone.
4. A clean Word round-trip (opens with no repair prompt, exports N pages with a
   `/Font` entry present).

That is structural evidence, not visual. Don't claim you looked at the document.

## Related gotcha: a docx open in Word can't be opened by `zipfile`

`PermissionError: [Errno 13]` on `zipfile.ZipFile(path)` usually means Word has
the file open, not that permissions are wrong. `cp` the file first and work on
the copy — same app-handle-lock pattern as
[[event-log-app-handle-lock]]. Also set `PYTHONIOENCODING=utf-8` before dumping
extracted document text, or `—`/`→` crash the cp1252 console
([[windows-hook-stdin-cp1252-encoding-gap]]).

Do not "fix" this by editing the skill: `docx` lives in the plugin cache
(`~/.claude/plugins/cache/anthropic-agent-skills/...` and the Cowork
skills-plugin mirror) and any edit there is clobbered on the next plugin sync.
