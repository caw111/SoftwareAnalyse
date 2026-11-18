# Optional legacy SSH entry point. Normal desktop use connects directly over HTTPS.
param(
    [string]$SshHost = 'SoftwareAnalysis',
    [ValidateRange(1024, 65535)][int]$LocalPort = 18080,
    [switch]$NoDesktop,
    [switch]$Stop
)
$ErrorActionPreference = 'Stop'
if ($SshHost -notmatch '^[A-Za-z0-9_.-]+$') { throw 'Use a configured SSH host alias.' }
$projectRoot = Split-Path $PSScriptRoot
$artifactDir = Join-Path $projectRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$pidFile = Join-Path $artifactDir "server-tunnel-$LocalPort.json"
$forward = "127.0.0.1:${LocalPort}:127.0.0.1:18081"
$legacyForward = "127.0.0.1:${LocalPort}:127.0.0.1:8080"
function Get-RecordedTunnelForward($Process, $Record, [string]$HostAlias, [int]$Port) {
    if (!$Process -or $Process.Name -ne 'ssh.exe' -or $Record.sshHost -ne $HostAlias -or [int]$Record.localPort -ne $Port) { return $null }
    $command = [string]$Process.CommandLine
    if ($command -notmatch '(?:^|\s)-N(?:\s|$)' -or $command -notmatch ('(?:^|\s)"?' + [regex]::Escape($HostAlias) + '"?\s*$')) { return $null }
    if ($Record.processCreatedAt -and (!$Process.CreationDate -or $Process.CreationDate.ToUniversalTime().ToString('o') -ne $Record.processCreatedAt)) { return $null }
    foreach ($candidate in @("127.0.0.1:${Port}:127.0.0.1:18081", "127.0.0.1:${Port}:127.0.0.1:8080")) {
        $pattern = '(?:^|\s)-L\s+"?' + [regex]::Escape($candidate) + '"?(?:\s|$)'
        if ($command -match $pattern -and (!$Record.forward -or $Record.forward -eq $candidate)) { return $candidate }
    }
    return $null
}
$existing = $null
$existingForward = $null
if (Test-Path -LiteralPath $pidFile) {
    $record = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$record.processId)"
    if ($existing) {
        $existingForward = Get-RecordedTunnelForward $existing $record $SshHost $LocalPort
        if (!$existingForward) { throw 'The recorded PID belongs to another process or tunnel; it was not changed.' }
    }
}
if ($Stop) {
    if ($existing) { Stop-Process -Id $existing.ProcessId }
    Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
    Write-Host 'This project SSH tunnel is stopped; the server continues running.'
    return
}
if ($existing -and $existingForward -eq $legacyForward) {
    # Retire only the verified old target; its port now serves TLS instead of the API.
    Stop-Process -Id $existing.ProcessId
    Wait-Process -Id $existing.ProcessId -Timeout 5 -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
    $existing = $null
    Write-Host 'The verified legacy tunnel was stopped; reconnecting to the backend on port 18081.'
}
if (!$existing) {
    if (Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue) { throw "Local port $LocalPort is already occupied by another service." }
    $arguments = @('-N', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=12', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3', '-L', $forward, $SshHost)
    $tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $artifactDir "server-tunnel-$LocalPort.stderr.log")
    $started = Get-CimInstance Win32_Process -Filter "ProcessId=$($tunnel.Id)"
    $createdAt = if ($started -and $started.CreationDate) { $started.CreationDate.ToUniversalTime().ToString('o') } else { $null }
    @{ processId=$tunnel.Id; sshHost=$SshHost; localPort=$LocalPort; forward=$forward; processCreatedAt=$createdAt } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
}
$apiUrl = "http://127.0.0.1:$LocalPort"
$ready = $false
$deadline = (Get-Date).AddSeconds(25)
do {
    if ($tunnel -and $tunnel.HasExited) { throw "SSH exited. Inspect artifacts/server-tunnel-$LocalPort.stderr.log." }
    try { $null = Invoke-RestMethod "$apiUrl/api/reference" -TimeoutSec 3; $ready = $true } catch { Start-Sleep -Milliseconds 500 }
} until ($ready -or (Get-Date) -ge $deadline)
if (!$ready) { throw 'The tunnel was started, but the remote API did not become ready.' }
Write-Host "Server API connected through SSH: $apiUrl"
if (!$NoDesktop) {
    $exe = Join-Path $projectRoot 'artifacts/windows-x64/AcademicDesktop.exe'
    if (!(Test-Path -LiteralPath $exe)) { throw 'Publish the desktop EXE first with scripts/publish-desktop.ps1.' }
    $previousApi = $env:ACADEMIC_API_URL
    try {
        $env:ACADEMIC_API_URL = $apiUrl
        # This script is explicitly used to open the interactive Windows client.
        Start-Process -FilePath $exe
    } finally {
        if ($null -eq $previousApi) { Remove-Item Env:ACADEMIC_API_URL -ErrorAction SilentlyContinue }
        else { $env:ACADEMIC_API_URL = $previousApi }
    }
}
