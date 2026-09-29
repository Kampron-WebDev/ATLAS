<#
.SYNOPSIS
  Runs ATLAS, your Chief Engineer. Examples:
    .\atlas.ps1                 full review
    .\atlas.ps1 next            your next lesson
    .\atlas.ps1 gate python     gate pre-check for your current Python unit
    .\atlas.ps1 --open          review, then open the dashboard
#>
$ErrorActionPreference = 'Stop'
$py = Join-Path $env:USERPROFILE 'Desktop\Python-Engineering-Mastery\.venv\Scripts\python.exe'
$pre = @()
if (-not (Test-Path $py)) { $py = 'py'; $pre = @('-3.13') }
$env:PYTHONUTF8 = '1'
Push-Location $PSScriptRoot
try { & $py @pre -m atlas @args; $code = $LASTEXITCODE } finally { Pop-Location }
exit $code
