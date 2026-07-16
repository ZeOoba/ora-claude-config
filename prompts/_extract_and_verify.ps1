$ErrorActionPreference = 'SilentlyContinue'
$o = 'C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-\a87ee512-2ea9-49e6-8f01-9181fc28c793\tasks\wayyxkk0q.output'
$dest = 'C:\Users\Owner\.claude\prompts\command-center-autonomous-review-v2.md'
New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
$j = Get-Content $o -Raw | ConvertFrom-Json
Set-Content -Path $dest -Value $j.result.finalPrompt -Encoding UTF8
Write-Output ("WROTE: " + $dest)
Write-Output ("PROMPT CHARS: " + $j.result.finalPrompt.Length)
Write-Output ("FAILURE COUNT: " + $j.result.failureCount)

$p = 'C:\Users\Owner\oxford-command-center'
Set-Location $p
Write-Output "=== pre-push hook installed? ==="
Write-Output ("  .git/hooks/pre-push exists: " + (Test-Path (Join-Path $p '.git\hooks\pre-push')))
Write-Output ("  hooks/git-prepush-confidential-scan.py in repo: " + (Test-Path (Join-Path $p 'hooks\git-prepush-confidential-scan.py')))
Write-Output "=== divergence left=origin/main right=main ==="
git rev-list --left-right --count origin/main...main
Write-Output "=== acquisition engine on origin/main ==="
git cat-file -e origin/main:server/warehouse/acquisition.ts; if ($?) { Write-Output "  acquisition.ts EXISTS on origin/main" } else { Write-Output "  acquisition.ts ABSENT on origin/main" }
git cat-file -e "origin/main:config/acquisition-ruleset.v1.proposed.json"; if ($?) { Write-Output "  acquisition-ruleset.v1.proposed.json EXISTS on origin/main" } else { Write-Output "  ruleset ABSENT on origin/main" }
Write-Output "=== capital-config on origin/main ==="
git cat-file -e origin/main:server/warehouse/capital-config.ts; if ($?) { Write-Output "  capital-config.ts EXISTS on origin/main" } else { Write-Output "  capital-config.ts ABSENT on origin/main" }
Write-Output "=== gate-related scripts ==="
($j2 = (Get-Content (Join-Path $p 'package.json') -Raw | ConvertFrom-Json)) | Out-Null
$j2.scripts.PSObject.Properties | Where-Object { $_.Name -match 'gate|reconcile|warehouse|bundle' } | ForEach-Object { Write-Output ("  " + $_.Name + " = " + $_.Value) }
Write-Output "=== playwright webServer.command ==="
Select-String -Path (Join-Path $p 'playwright.config.ts') -Pattern 'command' | ForEach-Object { Write-Output ("  " + $_.Line.Trim()) }
