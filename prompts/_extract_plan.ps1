$ErrorActionPreference = 'Stop'
$o = 'C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-\a87ee512-2ea9-49e6-8f01-9181fc28c793\tasks\wn685cgjv.output'
$wt = 'C:\Users\Owner\oxford-cc-wt-audit-20260613'
$j = (Get-Content $o -Raw | ConvertFrom-Json).result

Set-Content -Path (Join-Path $wt '_run\EVALUATION.md') -Value $j.evaluation.scorecardMarkdown -Encoding UTF8
Set-Content -Path (Join-Path $wt '_run\HARDENED-PLAN.md') -Value $j.plan.hardenedPlanMarkdown -Encoding UTF8
$j.plan.initiatives | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $wt '_run\plan-initiatives.json') -Encoding UTF8
Set-Content -Path (Join-Path $wt '_run\flywheel-design.md') -Value $j.plan.flywheelDesign -Encoding UTF8
Write-Output "SAVED: EVALUATION.md, HARDENED-PLAN.md, plan-initiatives.json, flywheel-design.md"
Write-Output ("eval chars: " + $j.evaluation.scorecardMarkdown.Length + " | plan chars: " + $j.plan.hardenedPlanMarkdown.Length)
Write-Output ""
Write-Output "===== DIMENSION SCORES ====="
foreach ($d in $j.evaluation.dimensionScores) { Write-Output ("  " + $d.dimension + " = " + $d.score) }
Write-Output ""
Write-Output ("===== PRE-MORTEM: " + $j.premortem.objectionCount + " objections =====")
$j.premortem.objections | Group-Object severity | ForEach-Object { Write-Output ("  " + $_.Name + ": " + $_.Count) }
Write-Output ""
Write-Output "===== VALIDATION DEFECTS ====="
if ($j.validation.defects.Count -eq 0) { Write-Output "  NONE - plan + Tier-A selection PASSED both validators" }
else { foreach ($d in $j.validation.defects) { Write-Output ("  [" + $d.severity + "] " + $d.title + " : " + $d.fix) } }
Write-Output ""
Write-Output ("===== INITIATIVES: " + $j.plan.initiatives.Count + " (by tier) =====")
$j.plan.initiatives | Group-Object tier | ForEach-Object { Write-Output ("  " + $_.Name + ": " + $_.Count) }
Write-Output ""
Write-Output "===== TIER-A TARGETS (this run) ====="
$n = 0
foreach ($t in $j.tierATargets) {
  $n++
  Write-Output ("--- Target " + $n + " [" + $t.tier + "] " + $t.id + " : " + $t.title)
  Write-Output ("    files: " + ($t.files -join ', '))
  Write-Output ("    addresses: " + ($t.addressesFindings -join ', '))
  Write-Output ("    change: " + $t.changeSketch)
  Write-Output ("    testPlan: " + $t.testPlan)
  Write-Output ("    whySafe: " + $t.whySafe)
}
Write-Output ""
Write-Output "===== RESIDUAL RISKS ====="
foreach ($r in $j.plan.residualRisks) { Write-Output ("  - " + $r) }
