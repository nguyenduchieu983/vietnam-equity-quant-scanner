param([string]$Cutoff, [string]$Distro = 'Ubuntu-22.04')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (!$Cutoff) {
    $vnNow = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow, 'SE Asia Standard Time')
    if ($vnNow.Hour -lt 17) { $vnNow = $vnNow.AddDays(-1) }
    $Cutoff = $vnNow.ToString('yyyy-MM-dd')
}
if ($Cutoff -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'Expected YYYY-MM-DD' }
Push-Location $projectRoot
try {
    & node infra/scripts/fetch-vndirect-research.mjs $Cutoff
    if ($LASTEXITCODE -ne 0) { throw 'Provider fetch failed; no paper ledger was advanced.' }
    $linuxRoot = (& wsl.exe -d $Distro -- wslpath -a $projectRoot.Replace('\','/')).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve WSL path' }
    $snapshot = "$linuxRoot/.runtime/vndirect-s1-$($Cutoff.Replace('-',''))"
    & wsl.exe -d $Distro -- bash "$linuxRoot/infra/scripts/paper-import.sh" $snapshot
    if ($LASTEXITCODE -ne 0) { throw 'Paper import failed; no paper ledger was advanced.' }
    Write-Host 'Real EOD snapshot ready. Open Paper Portfolio, preview and approve both accounts together.'
} finally { Pop-Location }
