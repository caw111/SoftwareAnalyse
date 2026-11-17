param([string]$ApiUrl = 'http://127.0.0.1:8080')
$ErrorActionPreference = 'Stop'
$uri = [Uri]$ApiUrl
if (!$uri.IsAbsoluteUri -or !$uri.IsLoopback) { throw 'This four-record functional check only permits a local demo API.' }
$root = Split-Path $PSScriptRoot
$outputDir = Join-Path $root 'artifacts/verification-v0.4'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$cases = @(
    @{Source='lynu-patents';Identifier='CN202420753596.1';Year=2025;Type='PATENT'},
    @{Source='nsfc-projects';Identifier='3193000529';Year=2019;Type='PROJECT'},
    @{Source='most-awards';Identifier='Z-102-1-01';Year=2023;Type='AWARD'},
    @{Source='cnipa-patents';Identifier='CN202111257655.3';Year=$null;Type='PATENT'}
)
$headers=$null; $summary=@(); $activeTask=$null
try {
    $login=Invoke-RestMethod "$ApiUrl/api/auth/login" -Method Post -ContentType 'application/json' -Body '{"username":"admin","password":"DemoPass2026!"}' -TimeoutSec 10
    $headers=@{Authorization='Bearer '+$login.token}
    $sources=Invoke-RestMethod "$ApiUrl/api/admin/crawl/sources" -Headers $headers -TimeoutSec 10
    foreach ($case in $cases) {
        $source=$sources | Where-Object id -eq $case.Source
        if (!$source.enabled -or $source.scheduleEnabled -or $source.batches.Count -lt 1) { throw "Source $($case.Source) must be enabled, registered and not scheduled." }
        $firstId=$null
        foreach ($run in 1..2) {
            # One processed record per task; two sequential observations prove idempotence. No load test.
            $body=@{sourceId=$case.Source;batchId=$source.batches[0].id;mode='BOUNDED';maxRecords=1;pageSize=1;maxPages=1} | ConvertTo-Json -Compress
            $task=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks" -Headers $headers -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10
            $activeTask=$task.id
            $action=@{version=$task.version;action='START'} | ConvertTo-Json -Compress
            $null=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$activeTask/actions" -Headers $headers -Method Post -ContentType 'application/json' -Body $action -TimeoutSec 10
            $deadline=(Get-Date).AddSeconds(150)
            do {
                Start-Sleep -Seconds 2
                $task=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$activeTask" -Headers $headers -TimeoutSec 10
            } until ($task.state -in @('SUCCESS','FAILED','STOPPED') -or (Get-Date) -gt $deadline)
            if ($task.state -ne 'SUCCESS' -or $task.received -ne 1 -or $task.excluded -ne 0) {
                $task | ConvertTo-Json -Depth 15 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $outputDir 'registered-live-failure.json')
                throw "$($case.Source): $($task.state) / $($task.errorCode) $($task.errorMessage); see registered-live-failure.json."
            }
            $activeTask=$null
            $q=[Uri]::EscapeDataString($case.Identifier)
            $catalog=Invoke-RestMethod "$ApiUrl/api/works?dataset=real&type=$($case.Type)&q=$q&size=5" -TimeoutSec 10
            if ($catalog.total -ne 1) { throw "Expected one canonical result for $($case.Identifier)." }
            $work=$catalog.items[0]
            if ($work.year -ne $case.Year) { throw "Wrong business year for $($case.Source): $($work.year)." }
            if ($run -eq 1) { $firstId=$work.id }
            elseif ($firstId -ne $work.id -or $task.inserted -ne 0 -or $task.updated -ne 0 -or $task.unchanged -ne 1) { throw 'Repeated observation must keep the canonical ID and count unchanged=1.' }
            $raw=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$($task.id)/pages/1" -Headers $headers -TimeoutSec 10
            if (!$raw.byteChecksum -or !$raw.sliceMetadata -or !$raw.parserVersion) { throw 'Document evidence metadata is incomplete.' }
            if ($raw.bodyEncoding -eq 'base64') {
                $hasher=[Security.Cryptography.SHA256]::Create()
                try { $hash=([BitConverter]::ToString($hasher.ComputeHash([Convert]::FromBase64String($raw.rawJson)))).Replace('-','').ToLowerInvariant() }
                finally { $hasher.Dispose() }
                if ($hash -ne $raw.byteChecksum) { throw 'Original PDF bytes checksum mismatch.' }
            }
            $summary += [pscustomobject]@{sourceId=$case.Source;batchId=$task.batchId;run=$run;taskId=$task.id;state=$task.state;completionReason=$task.completionReason;received=$task.received;inserted=$task.inserted;updated=$task.updated;unchanged=$task.unchanged;conflicts=$task.conflicts;identifier=$case.Identifier;type=$work.type;year=$work.year;workId=$work.id;title=$work.title;revision=$catalog.revision;documentRows=$raw.recordCount;contentType=$raw.contentType;bodyEncoding=$raw.bodyEncoding;byteChecksum=$raw.byteChecksum;responseChecksum=$raw.responseChecksum;parserVersion=$raw.parserVersion;httpStatus=$raw.httpStatus}
            Write-Host "$($case.Source) observation ${run}: PASS ($($task.completionReason))"
        }
    }
    $result=[pscustomobject]@{ok=$true;checkedAt=(Get-Date).ToUniversalTime().ToString('o');runs=$summary;note='4 sources, one processed record per task, repeated once sequentially; no load test.'}
    $result | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $outputDir 'registered-live.json')
} finally {
    if ($activeTask -and $headers) {
        try { $current=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$activeTask" -Headers $headers -TimeoutSec 5
            if ($current.state -notin @('SUCCESS','STOPPED')) { $body=@{version=$current.version;action='STOP'} | ConvertTo-Json -Compress; $null=Invoke-RestMethod "$ApiUrl/api/admin/crawl/tasks/$activeTask/actions" -Headers $headers -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5 }
        } catch { Write-Warning 'Could not cancel this verification task; inspect its recorded task ID.' }
    }
    if ($headers) { try { $null=Invoke-RestMethod "$ApiUrl/api/auth/logout" -Headers $headers -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 5 } catch { Write-Warning 'Session logout failed; no token was written to disk.' } }
}
