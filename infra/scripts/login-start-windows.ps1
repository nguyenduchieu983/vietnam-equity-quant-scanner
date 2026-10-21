param([switch]$SkipRefresh)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$startupMutex = [Threading.Mutex]::new($false, 'Local\VietnamQuantScannerLogin')
if (!$startupMutex.WaitOne(0)) { exit 0 }
try {
    Set-Location -LiteralPath $projectRoot
    New-Item -ItemType Directory -Path '.runtime' -Force | Out-Null
    Start-Transcript -Path '.runtime/login-start.log' -Append | Out-Null
    $ready = $false
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/dev-start-windows.ps1" -SkipBuild
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 10
    }
    if (!$ready) { throw 'Startup failed; inspect .runtime logs' }
    Write-Host 'Daily desk ready: http://localhost:5173'
    if (!$SkipRefresh) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/paper-refresh-windows.ps1"
        if ($LASTEXITCODE -ne 0) { throw 'EOD refresh failed. App remains available with its dated previous snapshot.' }
        & node "$PSScriptRoot/daily-paper.mjs"
        if ($LASTEXITCODE -ne 0) { throw 'Paper processing failed; inspect approval ledger.' }
    }
} finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
    $startupMutex.ReleaseMutex()
    $startupMutex.Dispose()
}
