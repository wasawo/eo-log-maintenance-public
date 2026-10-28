#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Send-EoSimulationRecord {
    [CmdletBinding()]
    param([hashtable]$Record, [string]$JournalRoot, [string]$PythonExecutable)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $PythonExecutable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot 'MoveJournalCommand.py'),'--journal-root',$JournalRoot)) {
        $start.ArgumentList.Add($argument)
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    try {
        [void]$process.Start()
        $started = $true
        $outputTask = $process.StandardOutput.ReadToEndAsync()
        $errorTask = $process.StandardError.ReadToEndAsync()
        $request = @{ protocol_version=1; request_id=$Record.record_id; simulation_only=$true; record=$Record }
        $writeTask = $process.StandardInput.WriteAsync(($request | ConvertTo-Json -Depth 20 -Compress))
        if (-not $writeTask.Wait(30000)) { throw 'move_simulation_journal_unconfirmed' }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) {
            $process.Kill($true); $process.WaitForExit()
            throw 'move_simulation_journal_unconfirmed'
        }
        [void]$errorTask.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'move_simulation_journal_unconfirmed' }
        $response = $outputTask.GetAwaiter().GetResult() | ConvertFrom-Json -AsHashtable -DateKind String
        if ($response -isnot [Collections.IDictionary] -or $response.Count -ne 5 -or
            @($response.Keys | Where-Object { $_ -cnotin @('protocol_version','request_id','ok','record','record_sha256') }).Count -ne 0 -or
            ($response.protocol_version -isnot [int] -and $response.protocol_version -isnot [long]) -or
            $response.protocol_version -ne 1 -or $response.ok -isnot [bool] -or -not $response.ok -or
            $response.request_id -isnot [string] -or $response.record_sha256 -isnot [string] -or $response.record.move_id -isnot [string] -or
            $response.request_id -cne $Record.record_id -or $response.record.record_id -cne $Record.record_id -or
            $response.record.run_id -cne $Record.run_id -or $response.record.event_kind -cne $Record.event_kind -or
            $response.record.machine_id -cne $Record.machine_id -or $response.record.route -cne $Record.route -or
            $response.record_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
            $response.record.move_id -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$') {
            throw 'move_simulation_journal_unconfirmed'
        }
        if ($response.record -isnot [Collections.IDictionary] -or $response.record.Count -ne $Record.Count -or
            @($response.record.Keys | Where-Object { $_ -cnotin @($Record.Keys) }).Count -ne 0) { throw 'move_simulation_journal_unconfirmed' }
        foreach ($key in $Record.Keys) {
            if ($key -ceq 'move_id' -and $Record.event_kind -ceq 'prepared') { continue }
            if ($key -ceq 'prior_record_refs' -and $Record.event_kind -ceq 'reconciliation') { continue }
            $expected = [Text.Json.Nodes.JsonNode]::Parse((ConvertTo-Json -InputObject $Record[$key] -Depth 20 -Compress))
            $actual = [Text.Json.Nodes.JsonNode]::Parse((ConvertTo-Json -InputObject $response.record[$key] -Depth 20 -Compress))
            if (-not [Text.Json.Nodes.JsonNode]::DeepEquals($expected,$actual)) { throw 'move_simulation_journal_unconfirmed' }
        }
        if ($Record.event_kind -ceq 'reconciliation') {
            $refs=$response.record.prior_record_refs
            if ($refs -isnot [Array] -or $refs.Count -lt 1 -or $refs.Count -gt 2) { throw 'move_simulation_journal_unconfirmed' }
            $expected=[Text.Json.Nodes.JsonNode]::Parse((ConvertTo-Json -InputObject $Record.prior_record_refs[0] -Compress))
            $actual=[Text.Json.Nodes.JsonNode]::Parse((ConvertTo-Json -InputObject $refs[0] -Compress))
            if (-not [Text.Json.Nodes.JsonNode]::DeepEquals($expected,$actual)) { throw 'move_simulation_journal_unconfirmed' }
        }
        return $response
    }
    catch {
        if ($started -and -not $process.HasExited) {
            try { $process.Kill($true); $process.WaitForExit() } catch { }
        }
        throw 'move_simulation_journal_unconfirmed'
    }
    finally { $process.Dispose() }
}

function New-EoSimulationPreparedRecord {
    [CmdletBinding()]
    param($Event, [string]$RunId)
    $prefix = if ($Event.LogType -eq 'BattleLog') { 'battleLog' } else { 'errorLog' }
    $localEndpoint = {
        param($Id,$Machine,$RootKey,$RelativePath)
        $hash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Id))).ToLowerInvariant()
        @{ kind='local'; machine_id=$Machine; root_key=$RootKey; relative_path=$RelativePath.Replace('\','/')
            identity=@{ volume_serial='0000000000000000'; file_id=$hash.Substring(0,32) } }
    }
    $cloudEndpoint = {
        param($Id,$RelativePath)
        $parts = $RelativePath.Replace('\','/').Split('/')
        $parent = if ($parts.Count -gt 1) { ($parts[0..($parts.Count-2)] -join '/') } else { 'root' }
        @{ kind='cloud'; root_key=($prefix+'Drive'); file_id=('simulation-'+$Id); parent_id=('simulation-'+$Event.LogType+'-'+$parent)
            name=$parts[-1]; version='1' }
    }
    if ($Event.Operation -eq 'Sync') {
        $source = & $localEndpoint $Event.SourceId $Event.MachineId ($prefix+'Local') $Event.RelativePath
        $destination = & $cloudEndpoint $Event.DestinationId $Event.DestinationName
        $route = 'local_to_cloud'; $method = 'drive_download'
    }
    else {
        $source = & $cloudEndpoint $Event.SourceId $Event.RelativePath
        $destination = & $localEndpoint $Event.DestinationId 'PC-A' ($prefix+'Archive') $Event.DestinationName
        $route = 'cloud_to_archive'; $method = 'windows_handle'
    }
    $content = @{ size=$Event.Size; sha256=$Event.Sha256 }
    $stamp = [datetime]::UtcNow.ToString('o')
    return @{ record_version=1; record_id=[guid]::NewGuid().ToString('D'); run_id=$RunId; move_id=[guid]::NewGuid().ToString('D')
        attempt_id=[guid]::NewGuid().ToString('D'); event_kind='prepared'; route=$route; machine_id=$Event.MachineId; log_type=$Event.LogType
        observed_at_utc=$stamp; recorded_at_utc=$stamp; prior_record_refs=@()
        event_data=@{ source=$source; destination=$destination; copy_content=$content; destination_content=$content; reused=$Event.Reused; destination_method=$method } }
}

function Save-EoSimulationOutcome {
    [CmdletBinding()]
    param($Prepared, [string]$Sha256, [string]$Outcome, [string]$Reason, [string]$RunId,
          [string]$JournalRoot, [string]$PythonExecutable)
    $record = @{}
    foreach ($key in $Prepared.Keys) { $record[$key] = $Prepared[$key] }
    $record.record_id = [guid]::NewGuid().ToString('D')
    $record.observed_at_utc = [datetime]::UtcNow.ToString('o')
    $record.recorded_at_utc = $record.observed_at_utc
    $record.prior_record_refs = @(@{record_id=$Prepared.record_id; path=($Prepared.record_id+'.json'); sha256=$Sha256})
    $localSource = $Prepared.event_data.source.kind -eq 'local'
    $sourceMethod = if ($localSource) { 'windows_handle' } else { 'drive_download' }
    $presenceMethod = if ($localSource) { 'windows_lookup' } else { 'provider_observation' }
    $data = @{ source=$Prepared.event_data.source; destination=$Prepared.event_data.destination
        destination_current=$Prepared.event_data.copy_content; destination_method=$Prepared.event_data.destination_method }
    if ($Reason -eq 'reconciled_completion') {
        $record.event_kind='reconciliation'; $record.run_id=$RunId; $record.attempt_id=[guid]::NewGuid().ToString('D')
        $data.source_current='absent'; $data.source_method=$presenceMethod; $data.decision='completed'
        $data.completion_basis='reconciled'; $data.reason_code='reconciled_completion'
    }
    else {
        $record.event_kind='deletion_result'; $data.source_before_delete=$Prepared.event_data.copy_content; $data.source_method=$sourceMethod
        $data.request_outcome='unknown'; $data.source_after_delete='unknown'; $data.source_after_method='unavailable'
        $data.decision='unknown'; $data.completion_basis='none'; $data.reason_code='verification_unknown'
        if ($Outcome -eq 'completed') {
            $data.request_outcome='succeeded'; $data.source_after_delete='absent'; $data.source_after_method=$presenceMethod
            $data.decision='completed'; $data.completion_basis='delete_confirmed'; $data.reason_code='delete_confirmed'
        }
        elseif ($Reason -eq 'delete_failed') {
            $data.request_outcome='failed'; $data.source_after_delete='present'; $data.source_after_method=$presenceMethod
            $data.decision='incomplete'; $data.reason_code='delete_failed'
        }
        elseif ($Reason -in @('source_changed','verification_unknown')) {
            $data.request_outcome='not_sent'; $data.source_before_delete=$null; $data.source_method='unavailable'
            $data.reason_code=if ($Reason -eq 'source_changed') { 'source_changed' } else { 'verification_unknown' }
        }
    }
    $record.event_data=$data
    return Send-EoSimulationRecord -Record $record -JournalRoot $JournalRoot -PythonExecutable $PythonExecutable
}
