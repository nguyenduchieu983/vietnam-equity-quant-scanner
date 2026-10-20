param([string]$Distro = 'Ubuntu-22.04', [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
if ($Distro -notmatch '^[A-Za-z0-9_.-]+$') { throw 'Invalid WSL distro name' }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $projectRoot
if (!(Test-Path -LiteralPath '.env')) { throw 'Missing .env. Run node infra/scripts/init-demo-env.mjs once.' }
if (!(Test-Path -LiteralPath 'node_modules')) { throw 'Run npm ci first.' }
if (!$SkipBuild) {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
}
$wslInputPath = $projectRoot.Replace('\', '/')
$linuxRoot = & wsl.exe -d $Distro -- wslpath -a "$wslInputPath"
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve workspace in WSL' }
$linuxRoot = $linuxRoot.Trim()
& wsl.exe -d $Distro -u root -- systemctl start postgresql redis-server
if ($LASTEXITCODE -ne 0) { throw 'Native WSL database services failed to start' }
$hostPidPath = Join-Path $projectRoot '.runtime/wsl-host.pid'
$hostRunning = $false
if (Test-Path -LiteralPath $hostPidPath) {
    $hostProcessId = [int](Get-Content -LiteralPath $hostPidPath)
    $hostProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$hostProcessId"
    $hostRunning = $hostProcess -and $hostProcess.CommandLine.Contains("$linuxRoot/infra/scripts/dev-start-wsl.sh")
}
if (!$hostRunning) {
    $hostArguments = "-d $Distro --exec /bin/bash $linuxRoot/infra/scripts/dev-start-wsl.sh --hold"
    $hostProcess = Start-Process -FilePath (Get-Command wsl.exe).Source -ArgumentList $hostArguments `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $projectRoot '.runtime/wsl-host.log') `
        -RedirectStandardError (Join-Path $projectRoot '.runtime/wsl-host-error.log')
    Set-Content -LiteralPath $hostPidPath -Value $hostProcess.Id
}
$pidPath = Join-Path $projectRoot '.runtime/web-windows.pid'
$running = $false
if (Test-Path -LiteralPath $pidPath) {
    $taskProcessId = [int](Get-Content -LiteralPath $pidPath)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId"
    if ($existing -and $existing.CommandLine.Contains($projectRoot) -and $existing.CommandLine.Contains('vite')) { $running = $true }
}
if (!$running) {
    $viteScript = Join-Path $projectRoot 'node_modules/vite/bin/vite.js'
    $webRoot = Join-Path $projectRoot 'apps/web'
    $configPath = Join-Path $webRoot 'vite.config.ts'
    $arguments = "`"$viteScript`" `"$webRoot`" --config `"$configPath`" --host 127.0.0.1 --strictPort"
    $process = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList $arguments `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $projectRoot '.runtime/web-windows.log') `
        -RedirectStandardError (Join-Path $projectRoot '.runtime/web-windows-error.log')
    Set-Content -LiteralPath $pidPath -Value $process.Id
}
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $ready = Invoke-RestMethod 'http://127.0.0.1:5173/api/v1/health/ready' -TimeoutSec 3
        if ($ready.data.status -eq 'UP') {
            Write-Host 'Ready: http://127.0.0.1:5173'
            Write-Host 'Login password: SMOKE_ADMIN_PASSWORD in the local .env file.'
            exit 0
        }
    } catch { Start-Sleep -Seconds 1 }
}
throw 'Frontend/proxy readiness failed; inspect .runtime/web-windows*.log'
