---
name: reference-onedrive-office-autosave-lock-no-owner-file
description: A OneDrive/SharePoint-backed Office file open with AutoSave ON holds a fluctuating lock and creates NO ~$ owner file — the standard owner-file check returns a false negative; query Word COM Documents to identify the real holder before concluding a lock is stale
metadata: 
  node_type: memory
  type: reference
  originSessionId: bd37c567-0ce0-42de-9898-75a48f0ed28b
  modified: 2026-08-03T19:20:01.692Z
---

**Symptom cluster.** A OneDrive/SharePoint-backed `.docx` that is open in Word with **AutoSave ON**:

- **grows or changes size with no edit you made** (Word re-saves continuously — one 754 memo went 30,007 → 42,514 bytes while its text was untouched),
- holds a **fluctuating** lock: a `cp`/read can succeed one minute and fail `[Errno 13] Permission denied` the next,
- fails writes with `Device or resource busy`,
- and — the trap — creates **no `~$<name>.docx` owner file**.

**Why the usual check fails.** The standard "is it open?" test is looking for a `~$` owner file in the same directory. For AutoSave/SharePoint-backed documents that file is absent, so the check reports "closed / stale lock" while Word very much has the document. `Get-Process WINWORD` only proves Word is running, not which files it holds — also insufficient.

**What actually identifies the holder** (read-only, does not launch Word):

```powershell
$word = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
foreach ($d in $word.Documents) { $d.Name; $d.FullName; $d.Saved; $d.AutoSaveOn }
```

`FullName` returns the **SharePoint URL**, not the local OneDrive path, which also tells you which account's drive backs it. `MK_E_UNAVAILABLE (0x800401E3)` from `GetActiveObject` means no Word instance is running — i.e. genuinely closed and safe to write. Excel/PowerPoint expose the same `Documents`/`Workbooks`/`Presentations` COM surface.

**Why you must not write anyway.** With the document open and AutoSave on, a file-level write to the local copy is either **silently reverted** by Word's in-memory copy at the next autosave, or produces a **OneDrive conflict copy**. Neither fails loudly — you would report the edit as landed and it would not be. Close the document first, then write, then re-verify by hashing the destination against the build you validated.

**Related:** [feedback_verified_null_vs_inferred_null.md](feedback_verified_null_vs_inferred_null.md) — "no `~$` file" is an *inferred* null, not a verified one. Case detail: [event_log.md](event_log.md) 2026-08-03 754 Old State memo-correction entry.

**Also on this machine:** LibreOffice is NOT installed, and the docx skill's `scripts/office/soffice.py` is POSIX-only (`socket.AF_UNIX`), so `--convert-to pdf` cannot run here at all. Visual page-render verification of a `.docx` is unavailable on this surface; fall back to XSD `validate.py --original`, paragraph-count parity, and a full extracted-text diff.
