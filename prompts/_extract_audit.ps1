$ErrorActionPreference = 'Stop'
$o = 'C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-\a87ee512-2ea9-49e6-8f01-9181fc28c793\tasks\wxye0dvgm.output'
$wt = 'C:\Users\Owner\oxford-cc-wt-audit-20260613'
$j = (Get-Content $o -Raw | ConvertFrom-Json).result
# Save the full audit report markdown to scratch (untracked)
$dest = Join-Path $wt '_run\AUDIT-REPORT.md'
Set-Content -Path $dest -Value $j.reportMarkdown -Encoding UTF8
Write-Output ("SAVED report -> " + $dest + " (" + $j.reportMarkdown.Length + " chars)")
Write-Output ("COUNTS: " + ($j.counts | ConvertTo-Json -Compress))
Write-Output ""
Write-Output "===== RANKED FINDINGS (rank | sev | tier | id | file:line) ====="
foreach ($r in $j.ranked) {
  Write-Output ("{0,2} | {1,-8} | {2,-6} | {3} | {4}:{5}" -f $r.rank, $r.severity, $r.riskTierHint, $r.id, $r.file, $r.line)
}
Write-Output ""
Write-Output "===== TIER TALLY ====="
$j.ranked | Group-Object riskTierHint | ForEach-Object { Write-Output ($_.Name + ": " + $_.Count) }
Write-Output ""
Write-Output "===== SEVERITY TALLY ====="
$j.ranked | Group-Object severity | ForEach-Object { Write-Output ($_.Name + ": " + $_.Count) }
Write-Output ""
Write-Output "===== COVERAGE NOTES ====="
$j.coverageNotes | ForEach-Object { Write-Output ("- " + $_) }
# Also dump the structured confirmed findings to scratch JSON for downstream phases
$cf = Join-Path $wt '_run\confirmed-findings.json'
$j.confirmedFindings | ConvertTo-Json -Depth 8 | Set-Content -Path $cf -Encoding UTF8
Write-Output ("SAVED confirmed findings -> " + $cf)
