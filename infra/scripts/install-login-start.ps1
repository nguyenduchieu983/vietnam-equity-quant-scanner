param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name = 'VietnamEquityQuantScanner'
if ($Uninstall) {
    Remove-ItemProperty -LiteralPath $key -Name $name -ErrorAction SilentlyContinue
    Write-Host 'Removed Quant Scanner login startup for this Windows user.'
    exit 0
}
$script = (Resolve-Path (Join-Path $PSScriptRoot 'login-start-windows.ps1')).Path
$powershellPath = (Get-Command powershell.exe).Source
$command = "`"$powershellPath`" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
New-Item -Path $key -Force | Out-Null
New-ItemProperty -LiteralPath $key -Name $name -Value $command -PropertyType String -Force | Out-Null
if ((Get-ItemPropertyValue -LiteralPath $key -Name $name) -ne $command) { throw 'Startup registration verification failed' }
Write-Host 'Installed per-user Windows login startup. Open http://localhost:5173 after sign-in.'
