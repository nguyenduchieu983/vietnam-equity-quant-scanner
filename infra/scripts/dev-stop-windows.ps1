param([string]$Distro = 'Ubuntu-22.04')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pidPath = Join-Path $projectRoot '.runtime/web-windows.pid'
if (Test-Path -LiteralPath $pidPath) {
    $taskProcessId = [int](Get-Content -LiteralPath $pidPath)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId"
    if ($existing) {
        if (!$existing.CommandLine.Contains($projectRoot) -or !$existing.CommandLine.Contains('vite')) {
            throw 'PID belongs to another application; refusing to stop it.'
        }
        Stop-Process -Id $taskProcessId
    }
    Remove-Item -LiteralPath $pidPath
}
$wslInputPath = $projectRoot.Replace('\', '/')
$linuxRoot = & wsl.exe -d $Distro -- wslpath -a "$wslInputPath"
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve workspace in WSL' }
$linuxRoot = $linuxRoot.Trim()
& wsl.exe -d $Distro -- bash "$linuxRoot/infra/scripts/dev-stop.sh"
if ($LASTEXITCODE -ne 0) { throw 'Backend stop failed' }
$hostPidPath = Join-Path $projectRoot '.runtime/wsl-host.pid'
if (Test-Path -LiteralPath $hostPidPath) {
    $hostProcessId = [int](Get-Content -LiteralPath $hostPidPath)
    $hostProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$hostProcessId"
    if ($hostProcess -and $hostProcess.CommandLine.Contains("$linuxRoot/infra/scripts/dev-start-wsl.sh")) {
        Stop-Process -Id $hostProcessId
    }
    Remove-Item -LiteralPath $hostPidPath
}
Write-Host 'Project frontend, API and worker stopped. Shared PostgreSQL/Redis remain running.'
