#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'LogFunctions.ps1')
. (Join-Path $PSScriptRoot 'MachineConfiguration.ps1')
. (Join-Path $PSScriptRoot 'LogMoveSimulationJournal.ps1')
. (Join-Path $PSScriptRoot 'SimulationRunReport.ps1')

function Invoke-EoLogMoveSimulation {
    <# Model sources/destinations only; optional journal I/O, never live file/Drive operations. #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ConfigurationJson,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$MachineId,
        [Parameter(Mandatory)][ValidateSet('Sync', 'Archive')][string]$Operation,
        [Parameter(Mandatory)][hashtable]$State,
        [Parameter(Mandatory)][datetime]$ReferenceDate,
        [hashtable]$Faults = @{},
        [switch]$DryRun,
        [string]$JournalRoot = '',
        [string]$ReportRoot = '',
        [string]$PythonExecutable = 'python',
        [guid]$RunId = [guid]::NewGuid()
    )

    $config = ConvertFrom-EoMachineConfigurationJson -Json $ConfigurationJson -ExpectedMachineId $MachineId
    # Role/configuration failure is global, before reading or mutating model state.
    if ($Operation -eq 'Archive' -and ($MachineId -ne 'PC-A' -or -not $config.allowArchive)) {
        throw 'move_archive_role_denied'
    }
    if ($State.Files -isnot [Collections.Generic.List[object]] -or
        $State.Events -isnot [Collections.Generic.List[object]]) {
        throw 'move_simulation_state_invalid'
    }
    foreach ($fault in $Faults.Values) {
        if ($fault -cnotin @('copy_failed', 'destination_changed', 'record_failed', 'source_changed',
            'source_replaced', 'verification_unknown', 'delete_failed', 'delete_unknown_absent',
            'delete_unknown_present', 'result_record_failed', 'presence_unknown')) {
            throw 'move_simulation_fault_invalid'
        }
    }
    $ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($file in $State.Files) {
        if ($file -isnot [hashtable] -or $file.Id -isnot [string] -or
            [string]::IsNullOrWhiteSpace($file.Id) -or -not $ids.Add($file.Id) -or
            $file.Location -cnotin @('PC-A', 'PC-B', 'Cloud', 'Archive') -or
            $file.LogType -cnotin @('BattleLog', 'ErrorReport') -or
            $file.Bytes -isnot [byte[]] -or
            $null -eq (ConvertTo-SafeDiagnosticRelativePath -Path $file.RelativePath)) {
            throw 'move_simulation_state_invalid'
        }
    }
    foreach ($event in $State.Events) {
        if ($event -isnot [hashtable] -or $event.Kind -cnotin @('prepared', 'delete_result', 'reconciled') -or
            $event.SourceId -isnot [string] -or $event.MachineId -cnotin @('PC-A', 'PC-B') -or
            $event.Operation -cnotin @('Sync', 'Archive') -or $event.LogType -cnotin @('BattleLog', 'ErrorReport') -or
            $null -eq (ConvertTo-SafeDiagnosticRelativePath -Path $event.RelativePath)) {
            throw 'move_simulation_record_invalid'
        }
    }
    $sourceLocation = if ($Operation -eq 'Sync') { $MachineId } else { 'Cloud' }
    $destinationLocation = if ($Operation -eq 'Sync') { 'Cloud' } else { 'Archive' }
    $currentRun = $RunId.ToString('D')
    $journalEnabled = -not [string]::IsNullOrWhiteSpace($JournalRoot)
    $reportEnabled = -not [string]::IsNullOrWhiteSpace($ReportRoot)
    $inventoryCount = @($State.Files | Where-Object { $_.Location -ceq $sourceLocation }).Count
    if ($reportEnabled -and -not $DryRun) {
        if (-not (Test-Path -LiteralPath $ReportRoot -PathType Container)) { throw 'move_simulation_report_root_invalid' }
        if ($journalEnabled) {
            $journalPath=[IO.Path]::GetFullPath($JournalRoot).TrimEnd('\','/')
            $reportPath=[IO.Path]::GetFullPath($ReportRoot).TrimEnd('\','/')
            if ($reportPath -eq $journalPath -or $reportPath.StartsWith($journalPath+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
                $journalPath.StartsWith($reportPath+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'move_simulation_report_root_invalid' }
        }
    }
    if ($journalEnabled -and -not $DryRun -and -not (Test-Path -LiteralPath $JournalRoot -PathType Container)) {
        throw 'move_simulation_journal_root_invalid'
    }
    $journalState = @{ Failed=$false }
    $journalPrepared = @{}
    $outcomes = @{}
    $reportDetails = [Collections.Generic.List[object]]::new()
    $results = [Collections.Generic.List[object]]::new()
    $hashBytes = {
        param([byte[]]$Bytes)
        [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant()
    }
    $addResult = {
        param($Source, [string]$Outcome, [string]$Reason, $DestinationId)
        if ($journalEnabled -and $journalPrepared.ContainsKey($Source.Id) -and $Reason -ne 'result_record_failed') {
            $binding = $journalPrepared[$Source.Id]
            try {
                [void](Save-EoSimulationOutcome -Prepared $binding.JournalRecord -Sha256 $binding.JournalSha256 `
                    -Outcome $Outcome -Reason $Reason -RunId $currentRun -JournalRoot $JournalRoot -PythonExecutable $PythonExecutable)
            }
            catch { $Outcome='unknown'; $Reason='result_record_failed'; $journalState.Failed=$true }
        }
        $outcomes[$Source.Id] = $Outcome
        $results.Add([pscustomobject]@{
            SourceId = $Source.Id; RelativePath = $Source.RelativePath; LogType = $Source.LogType
            DestinationId = $DestinationId; Outcome = $Outcome; Reason = $Reason
        })
        if ($reportEnabled -and -not $DryRun) {
            $reference = { param([string]$Id) [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Id))).ToLowerInvariant() }
            $name=($Source.RelativePath.Replace('\','/') -split '/')[-1]
            $candidates=@($State.Files | Where-Object {
                $_.Location -ceq $destinationLocation -and $_.LogType -ceq $Source.LogType -and
                (($null -ne $DestinationId -and $_.Id -ceq $DestinationId) -or
                 ($null -eq $DestinationId -and ($_.RelativePath.Replace('\','/') -split '/')[-1] -ceq $name))
            } | ForEach-Object { @{target_ref=(& $reference $_.Id);relative_path=$_.RelativePath.Replace('\','/')} })
            $nextAction=switch ($Reason) {
                {$_ -in @('retention_period','delete_confirmed','reconciled_completion')} {'none';break}
                'filename_invalid' {'inspect_source';break}
                {$_ -in @('destination_ambiguous','content_conflict')} {'resolve_conflict';break}
                'destination_mismatch' {'inspect_destination';break}
                {$_ -in @('record_failed','result_record_failed','record_missing')} {'inspect_records';break}
                {$_ -in @('copy_failed','source_changed','delete_failed')} {'retry_move';break}
                default {'reobserve'}
            }
            $reportDetails.Add(@{source_ref=(& $reference $Source.Id);source_relative_path=$Source.RelativePath.Replace('\','/');
                log_type=$Source.LogType;outcome=$Outcome;reason_code=$Reason;next_action=$nextAction;destination_candidates=$candidates})
        }
    }
    foreach ($source in @($State.Files | Where-Object { $_.Location -ceq $sourceLocation })) {
        if ($journalState.Failed) {
            & $addResult $source 'retained' 'record_failed' $null
            continue
        }
        $name = ($source.RelativePath.Replace('\', '/') -split '/')[-1]
        try {
            $eligible = Test-LogFileEligible -LogType $source.LogType -FileName $name `
                -Operation $Operation -ReferenceDate $ReferenceDate
        }
        catch {
            & $addResult $source 'retained' 'filename_invalid' $null
            continue
        }
        if (-not $eligible) {
            & $addResult $source 'not_eligible' 'retention_period' $null
            continue
        }
        if ($DryRun) {
            & $addResult $source 'planned' 'dry_run_no_effects' $null
            continue
        }
        $fault = if ($Faults.ContainsKey($source.Id)) { $Faults[$source.Id] } else { '' }
        # Staging is a private byte snapshot, not a reference to mutable source bytes.
        $originalSource = @{ Id = $source.Id; RelativePath = $source.RelativePath; LogType = $source.LogType }
        $staged = [byte[]]$source.Bytes.Clone()
        $baseline = & $hashBytes $staged
        $candidates = @($State.Files | Where-Object {
            $_.Location -ceq $destinationLocation -and $_.LogType -ceq $source.LogType -and
            $_.RelativePath -ceq $name
        })
        if ($candidates.Count -gt 1) {
            & $addResult $source 'retained' 'destination_ambiguous' $null
            continue
        }
        $reused = $candidates.Count -eq 1
        if ($reused) {
            $destination = $candidates[0]
            if ((& $hashBytes $destination.Bytes) -cne $baseline) {
                & $addResult $source 'retained' 'content_conflict' $destination.Id
                continue
            }
        }
        else {
            if ($fault -eq 'copy_failed') {
                & $addResult $source 'retained' 'copy_failed' $null
                continue
            }
            $destination = @{
                Id = [guid]::NewGuid().ToString('D'); Location = $destinationLocation
                LogType = $source.LogType; RelativePath = $name; Bytes = $staged.Clone()
            }
            $State.Files.Add($destination)
        }
        if ($fault -eq 'destination_changed') { $destination.Bytes = [byte[]]@(255) }
        if ((& $hashBytes $destination.Bytes) -cne $baseline) {
            & $addResult $source 'retained' 'destination_mismatch' $destination.Id
            continue
        }
        if ($fault -eq 'record_failed') {
            & $addResult $source 'retained' 'record_failed' $destination.Id
            continue
        }
        # Candidate model events are not persisted records or manifest-v1 fields.
        $prepared = @{
            Kind = 'prepared'; MachineId = $MachineId; Operation = $Operation
            SourceId = $source.Id; SourceLocation = $sourceLocation
            RelativePath = $source.RelativePath; LogType = $source.LogType
            DestinationId = $destination.Id; DestinationLocation = $destinationLocation
            DestinationName = $name; Sha256 = $baseline; Size = $staged.LongLength
            Reused = $reused
        }
        if ($journalEnabled) {
            try {
                $candidate = New-EoSimulationPreparedRecord -Event $prepared -RunId $currentRun
                $ack = Send-EoSimulationRecord -Record $candidate -JournalRoot $JournalRoot -PythonExecutable $PythonExecutable
                $prepared.JournalRecord = $ack.record
                $prepared.JournalSha256 = $ack.record_sha256
                $journalPrepared[$source.Id] = $prepared
            }
            catch {
                $journalState.Failed=$true
                & $addResult $source 'retained' 'record_failed' $destination.Id
                continue
            }
        }
        $State.Events.Add($prepared)
        if ($fault -eq 'source_changed') { $source.Bytes = [byte[]]@(254) }
        if ($fault -eq 'source_replaced') { $source.Id = [guid]::NewGuid().ToString('D') }
        $sameSource = @($State.Files | Where-Object { $_.Id -ceq $prepared.SourceId })
        if ($sameSource.Count -ne 1 -or $source.Id -cne $prepared.SourceId -or
            (& $hashBytes $source.Bytes) -cne $baseline -or $source.Bytes.LongLength -ne $staged.LongLength) {
            & $addResult $originalSource 'retained' 'source_changed' $destination.Id
            continue
        }
        if ($fault -eq 'verification_unknown') {
            & $addResult $source 'retained' 'verification_unknown' $destination.Id
            continue
        }
        # In-memory atomic comparison/removal is a MODEL capability, not FS/Drive evidence.
        if ($fault -eq 'delete_failed') {
            & $addResult $source 'retained' 'delete_failed' $destination.Id
            continue
        }
        if ($fault -ne 'delete_unknown_present') { [void]$State.Files.Remove($source) }
        $outcome = if ($fault -in @('delete_unknown_absent', 'delete_unknown_present', 'result_record_failed')) { 'unknown' } else { 'completed' }
        & $addResult $source $outcome $(if ($fault -eq 'result_record_failed') { 'result_record_failed' } elseif ($outcome -eq 'completed') { 'delete_confirmed' } else { 'delete_unknown' }) $destination.Id
        if ($fault -ne 'result_record_failed') {
            $resultEvent = @{
                Kind = 'delete_result'; SourceId = $prepared.SourceId
                DestinationId = $destination.Id; Outcome = $outcomes[$source.Id]; MachineId = $MachineId
                Operation = $Operation; RelativePath = $source.RelativePath; LogType = $source.LogType
            }
            if ($journalEnabled) {
                $resultEvent.JournalPreparedId=$prepared.JournalRecord.record_id
                $resultEvent.MoveId=$prepared.JournalRecord.move_id
            }
            $State.Events.Add($resultEvent)
        }
    }
    # Preserve unresolved prior attempts even when this run enumerates zero sources.
    $pendingEvents = @($State.Events | Where-Object {
        $_.Kind -eq 'prepared' -or ($_.Kind -eq 'delete_result' -and $_.Outcome -eq 'unknown')
    })
    foreach ($pending in $pendingEvents) {
        if ($pending.MachineId -cne $MachineId -or $pending.Operation -cne $Operation) { continue }
        if (@($results | Where-Object { $_.SourceId -ceq $pending.SourceId }).Count -gt 0) { continue }
        $pendingMove = if ($pending.ContainsKey('JournalRecord')) { $pending.JournalRecord.move_id }
            elseif ($pending.ContainsKey('MoveId')) { $pending.MoveId } else { $null }
        if (@($State.Events | Where-Object {
            $_.Kind -in @('delete_result', 'reconciled') -and $_.SourceId -ceq $pending.SourceId -and
            $_.Outcome -eq 'completed' -and $_.MachineId -ceq $MachineId -and $_.Operation -ceq $Operation -and
            ($null -eq $pendingMove -or ($_.ContainsKey('MoveId') -and $_.MoveId -ceq $pendingMove))
        }).Count -gt 0) { continue }
        $records = @($State.Events | Where-Object {
            $_.Kind -eq 'prepared' -and $_.SourceId -ceq $pending.SourceId -and
            $_.DestinationId -ceq $pending.DestinationId -and $_.MachineId -ceq $MachineId -and
            $_.Operation -ceq $Operation
        })
        if ($pending.ContainsKey('JournalRecord')) {
            $records = @($records | Where-Object { $_.ContainsKey('JournalRecord') -and $_.JournalRecord.record_id -ceq $pending.JournalRecord.record_id })
        }
        elseif ($pending.ContainsKey('JournalPreparedId')) {
            $records = @($records | Where-Object { $_.ContainsKey('JournalRecord') -and $_.JournalRecord.record_id -ceq $pending.JournalPreparedId })
        }
        if ($records.Count -eq 0) {
            $unbound = @{ Id = $pending.SourceId; RelativePath = $pending.RelativePath; LogType = $pending.LogType }
            & $addResult $unbound 'unknown' 'record_missing' $pending.DestinationId
            continue
        }
        $record = $records[0]
        $reported = @{ Id = $record.SourceId; RelativePath = $record.RelativePath; LogType = $record.LogType }
        $destination = @($State.Files | Where-Object { $_.Id -ceq $record.DestinationId })
        $recreated = @($State.Files | Where-Object {
            $_.Location -ceq $sourceLocation -and $_.LogType -ceq $record.LogType -and
            $_.RelativePath -ceq $record.RelativePath
        })
        $canReconcile = $records.Count -eq 1 -and $destination.Count -eq 1 -and $recreated.Count -eq 0 -and
            $record.SourceLocation -ceq $sourceLocation -and $record.DestinationLocation -ceq $destinationLocation -and
            $record.Sha256 -cmatch '^[a-f0-9]{64}$' -and $record.Size -ge 0
        if ($canReconcile) {
            $target = $destination[0]
            $canReconcile = $target.Location -ceq $destinationLocation -and $target.LogType -ceq $record.LogType -and
                $target.RelativePath -ceq $record.DestinationName -and $target.Bytes.LongLength -eq $record.Size -and
                (& $hashBytes $target.Bytes) -ceq $record.Sha256
        }
        if ($DryRun -or $Faults.ContainsKey($record.SourceId) -or $journalState.Failed) { $canReconcile = $false }
        if ($journalEnabled -and -not $record.ContainsKey('JournalRecord')) { $canReconcile = $false }
        if ($canReconcile) {
            if ($journalEnabled) { $journalPrepared[$record.SourceId] = $record }
            & $addResult $reported 'completed' 'reconciled_completion' $record.DestinationId
            $reconciledEvent = @{
                Kind = 'reconciled'; SourceId = $record.SourceId; Outcome = $outcomes[$record.SourceId]
                MachineId = $MachineId; Operation = $Operation
                RelativePath = $record.RelativePath; LogType = $record.LogType
            }
            if ($journalEnabled) { $reconciledEvent.MoveId=$record.JournalRecord.move_id }
            $State.Events.Add($reconciledEvent)
        }
        else { & $addResult $reported 'unknown' 'reconciliation_unconfirmed' $record.DestinationId }
    }
    $completed = @($results | Where-Object { $_.Outcome -eq 'completed' }).Count
    $unresolved = @($results | Where-Object { $_.Outcome -in @('retained', 'unknown') }).Count
    $journalSummary = $null
    $journalUnresolved = $null
    $journalReadStatus = if ($journalEnabled) { 'not_read' } else { 'disabled' }
    if ($journalEnabled -and -not $DryRun) {
        try {
            $journalSummary = & (Join-Path $PSScriptRoot '../scripts/Show-MoveRun.ps1') -JournalRoot $JournalRoot `
                -RunId $currentRun -MachineId $MachineId -Operation $Operation -PythonExecutable $PythonExecutable -AsJson 2>$null |
                ConvertFrom-Json -AsHashtable -DateKind String
            $journalUnresolved = $journalSummary.unresolved_source_count
            $journalReadStatus = 'confirmed'
        }
        catch { $journalState.Failed=$true; $journalReadStatus='unconfirmed' }
    }
    $status = if ($unresolved -gt 0 -or $journalState.Failed -or ($null -ne $journalUnresolved -and $journalUnresolved -gt 0)) {
        if ($completed -gt 0) { 'partial_failure' } else { 'failure' }
    }
    elseif ($DryRun) { 'dry_run' }
    elseif ($completed -gt 0) { 'success' }
    else { 'no_work' }
    $reportSaveStatus=if ($reportEnabled) {'not_written'}else{'disabled'}
    $runReportSummary=$null
    if ($reportEnabled -and -not $DryRun) {
        $route=if ($Operation -eq 'Sync') {'local_to_cloud'}else{'cloud_to_archive'}
        $pendingRefs=if ($null -ne $journalSummary) { @($journalSummary.details | Where-Object {$_.state -cne 'completed'} | ForEach-Object {$_.move_ref}) }else{@()}
        $report=@{report_version=1;simulation_only=$true;run_id=$currentRun;machine_id=$MachineId;route=$route;
            inventory_complete=$true;inventory_source_count=$inventoryCount;journal_read_status=$journalReadStatus;
            journal_unresolved_move_refs=@($pendingRefs);results=$reportDetails.ToArray()}
        try {
            $runReportSummary=Save-EoSimulationRunReport -Report $report -ReportRoot $ReportRoot -PythonExecutable $PythonExecutable
            if ($runReportSummary.status -cne $status) { throw 'simulation_report_unconfirmed' }
            $reportSaveStatus='confirmed'
        }
        catch { $runReportSummary=$null; $reportSaveStatus='unconfirmed' }
    }
    return [pscustomobject]@{
        SimulationOnly = $true; MachineId = $MachineId; Operation = $Operation
        RunId = $currentRun; JournalEnabled = $journalEnabled
        JournalReadStatus = $journalReadStatus; JournalUnresolvedSourceCount = $journalUnresolved; JournalSummary = $journalSummary
        Status = $status; CompletedSourceCount = $completed; UnresolvedSourceCount = $unresolved
        ReportSaveStatus=$reportSaveStatus; RunReportSummary=$runReportSummary
        Results = $results.ToArray()
    }
}
