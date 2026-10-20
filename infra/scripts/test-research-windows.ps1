param([string]$Distro = "Ubuntu-22.04", [switch]$SkipBrowser)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $root
try {
    foreach ($task in @("lint", "typecheck", "build", "test")) {
        & npm.cmd run $task
        if ($LASTEXITCODE -ne 0) { throw "npm $task failed" }
    }
    $linuxRoot = (& wsl -d $Distro -- wslpath -a ($root.Replace('\','/'))).Trim()
    & wsl -d $Distro -- bash "$linuxRoot/infra/scripts/test-research-wsl.sh"
    if ($LASTEXITCODE -ne 0) { throw "Python checks failed" }
    $env:API_URL = "http://127.0.0.1:5173"
    foreach ($suite in @("m0-smoke", "m1-smoke", "m2-smoke")) {
        & node --import dotenv/config "tests/e2e/$suite.mjs"
        if ($LASTEXITCODE -ne 0) { throw "$suite failed" }
    }
    Write-Host "Allowing the configured API throttle window to reset..."
    Start-Sleep -Seconds 60
    & node tests/e2e/m3-smoke.mjs
    if ($LASTEXITCODE -ne 0) { throw "M3 API checks failed" }
    if (-not $SkipBrowser) {
        Start-Sleep -Seconds 60
        foreach ($suite in @("m2-browser", "m3-browser")) {
            & node "tests/e2e/$suite.mjs"
            if ($LASTEXITCODE -ne 0) { throw "$suite failed" }
        }
    }
    Write-Host "PASS: local research checks. See docs/TEST_REPORT.md for acceptance boundaries."
} finally { Pop-Location }
