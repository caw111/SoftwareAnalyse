param(
    [string]$ApiUrl = 'http://127.0.0.1:8080',
    [string]$Doi = '10.1038/nphys1170'
)
$ErrorActionPreference = 'Stop'
$endpoint = [Uri]$ApiUrl
if (!$endpoint.IsAbsoluteUri -or !$endpoint.IsLoopback) { throw 'This single-record functional check only permits a local demo API.' }
$root = Split-Path $PSScriptRoot
$outputDir = Join-Path $root 'artifacts/verification-v0.3'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$headers = $null
try {
    $login = Invoke-RestMethod "$ApiUrl/api/auth/login" -Method Post -ContentType 'application/json' -Body '{"username":"admin","password":"DemoPass2026!"}' -TimeoutSec 10
    $headers = @{Authorization = 'Bearer ' + $login.token}
    $sources = Invoke-RestMethod "$ApiUrl/api/admin/crawl/sources" -Headers $headers -TimeoutSec 10
    $source = $sources | Where-Object id -eq 'crossref'
    if (!$source.enabled -or $source.scheduleEnabled) { throw 'Requires an enabled Crossref source with automatic scheduling disabled.' }
    $summaries = @()
    $stableId = $null
    $firstRevision = $null
    foreach ($run in 1..2) {
        # Exactly one DOI per task, sequential; this is not a load or throughput test.
        $body = @{sourceId='crossref';doi=$Doi;mode='BOUNDED';maxRecords=1;pageSize=1;maxPages=1} | ConvertTo-Json -Compress
        $task = Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks" -Headers $headers -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10
        $action = @{version=$task.version;action='START'} | ConvertTo-Json -Compress
        $task = Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$($task.id)/actions" -Headers $headers -Method Post -ContentType 'application/json' -Body $action -TimeoutSec 10
        $deadline = (Get-Date).AddSeconds(150)
        do {
            Start-Sleep -Seconds 2
            $task = Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$($task.id)" -Headers $headers -TimeoutSec 10
        } until ($task.state -in @('SUCCESS','FAILED','STOPPED') -or (Get-Date) -gt $deadline)
        if ($task.state -ne 'SUCCESS') {
            $task | ConvertTo-Json -Depth 15 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $outputDir 'live-crawl-failure.json')
            throw "Single DOI crawl ended in $($task.state): $($task.errorCode) $($task.errorMessage). See live-crawl-failure.json."
        }
        $query = [Uri]::EscapeDataString($Doi)
        $catalog = Invoke-RestMethod "$ApiUrl/api/works?dataset=real&q=$query&size=5" -TimeoutSec 10
        if ($catalog.total -ne 1) { throw 'Expected one canonical result for the exact DOI.' }
        $work = $catalog.items[0]
        if ($run -eq 1) { $stableId = $work.id; $firstRevision = $catalog.revision }
        elseif ($work.id -ne $stableId -or $task.inserted -ne 0 -or $task.updated -ne 0 -or $task.unchanged -ne 1 -or $catalog.revision -ne $firstRevision) { throw 'Identical repeated crawl must preserve ID/release and count unchanged=1.' }
        $raw = Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$($task.id)/pages/1" -Headers $headers -TimeoutSec 10
        $summaries += [pscustomobject]@{run=$run;taskId=$task.id;state=$task.state;mode=$task.mode;completionReason=$task.completionReason;received=$task.received;inserted=$task.inserted;updated=$task.updated;unchanged=$task.unchanged;conflicts=$task.conflicts;workId=$work.id;title=$work.title;revision=$catalog.revision;httpStatus=$raw.httpStatus;responseChecksum=$raw.responseChecksum}
    }
    $result = [pscustomobject]@{ok=$true;checkedAt=(Get-Date).ToUniversalTime().ToString('o');source='https://api.crossref.org';doi=$Doi;runs=$summaries;note='Two sequential tasks for one DOI; no load test.'}
    $result | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $outputDir 'live-crawl.json')
    $result | ConvertTo-Json -Depth 10
} finally {
    if ($headers) { try { $null = Invoke-RestMethod "$ApiUrl/api/auth/logout" -Method Post -ContentType 'application/json' -Body '{}' -Headers $headers -TimeoutSec 5 } catch { Write-Warning 'Session logout failed; token was not written to disk.' } }
}
