<#
.SYNOPSIS
  Convert a .docx (or .doc/.rtf) to PDF via Word COM, with a real extractable
  text layer. Windows fallback for the docx skill's scripts/office/soffice.py,
  which cannot run here (see NOTES).

.DESCRIPTION
  ORA deliverables must carry an extractable text layer -- no Print-to-PDF
  (CLAUDE.md, Conventions & deliverables). Word's ExportAsFixedFormat produces
  one; a print driver does not. This wraps that call and cleans up after itself.

  Exit codes:
    0  converted
    1  usage error (missing/!exists input, unwritable output dir)
    2  Word COM unavailable (not installed, or COM registration broken)
    3  conversion failed

.PARAMETER In
  Path to the source document. Required.

.PARAMETER Out
  Path to the PDF to write. Defaults to <In> with a .pdf extension.

.PARAMETER KeepOpen
  Leave the automation Word instance running (debugging only).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File docx-to-pdf.ps1 -In memo.docx

.NOTES
  Why this exists (2026-08-03): the docx skill ships
  scripts/office/soffice.py, whose own docstring scopes it to "environments
  where AF_UNIX [is blocked]" -- it calls socket.AF_UNIX, which does not exist
  on Windows, so it dies with AttributeError before reaching LibreOffice. And
  LibreOffice is not installed on LAPTOP-CSHSCBE6 anyway (verified: winget, a
  recursive Program Files sweep, and scoop all negative), nor is Poppler, so
  pdftoppm page rendering is unavailable too. Word IS present and is already
  the sanctioned COM surface for the mail path.

  This converts and gives you a page count. It does NOT rasterise pages -- with
  no Poppler there is still no way to LOOK at a rendered page on this machine.
  Verify docx edits by XSD validation + paragraph parity + text extraction, and
  treat a clean Word round-trip as structural (not visual) evidence.

  Cleanup: only the Word PID this script started is stopped. A Word instance
  the user already had open is never touched.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$In,
    [string]$Out,
    [switch]$KeepOpen
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $In)) {
    Write-Error "input not found: $In"; exit 1
}
$src = (Resolve-Path -LiteralPath $In).Path
if (-not $Out) { $Out = [System.IO.Path]::ChangeExtension($src, '.pdf') }
$outDir = Split-Path -Parent $Out
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    Write-Error "output directory does not exist: $outDir"; exit 1
}

# PIDs alive before we start, so we only ever stop the instance we created.
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)

try {
    $word = New-Object -ComObject Word.Application
} catch {
    Write-Error "Word COM unavailable: $($_.Exception.Message)"; exit 2
}

$after = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$ours  = @($after | Where-Object { $_ -notin $before })

$doc = $null
$rc  = 3
try {
    $word.Visible = $false
    $word.DisplayAlerts = 0

    # Open(FileName, ConfirmConversions, ReadOnly) -- ReadOnly so a copy the
    # user has open elsewhere is not locked or dirtied.
    $doc = $word.Documents.Open($src, $false, $true)

    # 17 = wdExportFormatPDF. $false = do not open after export. 0 = wdExportAllDocument.
    $doc.ExportAsFixedFormat($Out, 17, $false, 0)

    # 2 = wdStatisticPages
    $pages = $doc.ComputeStatistics(2)
    Write-Output "converted: $Out"
    Write-Output "pages: $pages"
    $rc = 0
} catch {
    Write-Error "conversion failed: $($_.Exception.Message)"
    $rc = 3
} finally {
    # Close(0) = wdDoNotSaveChanges. Quit() takes ref params in some Word
    # builds, so $word.Quit(0) throws NonRefArgumentToRefParameterMsg -- call it
    # bare, and fall back to stopping only our own PID.
    if ($doc) { try { $doc.Close(0) } catch { } }
    if (-not $KeepOpen) {
        try { $word.Quit() } catch { }
        try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) } catch { }
        Start-Sleep -Milliseconds 500
        foreach ($p in $ours) {
            if (Get-Process -Id $p -ErrorAction SilentlyContinue) {
                Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

exit $rc
