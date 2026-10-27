#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'LogFunctions.ps1')
. (Join-Path $PSScriptRoot 'MachineConfiguration.ps1')

function Invoke-EoLogMoveSimulation {
    <# In-memory integration model only. No filesystem, Drive, or live adapter. #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ConfigurationJson,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$MachineId,
        [Parameter(Mandatory)][ValidateSet('Sync', 'Archive')][string]$Operation,
        [Parameter(Mandatory)][hashtable]$State,
        [Parameter(Mandatory)][datetime]$ReferenceDate,
        [hashtable]$Faults = @{},
        [switch]$DryRun
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
    $results = [Collections.Generic.List[object]]::new()
    $hashBytes = {
        param([byte[]]$Bytes)
        [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant()
    }
    $addResult = {
        param($Source, [string]$Outcome, [string]$Reason, $DestinationId)
        $results.Add([pscustomobject]@{
            SourceId = $Source.Id; RelativePath = $Source.RelativePath; LogType = $Source.LogType
            DestinationId = $DestinationId; Outcome = $Outcome; Reason = $Reason
        })
    }
    foreach ($source in @($State.Files | Where-Object { $_.Location -ceq $sourceLocation })) {
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
        if ($fault -ne 'result_record_failed') {
            $State.Events.Add(@{
                Kind = 'delete_result'; SourceId = $prepared.SourceId
                DestinationId = $destination.Id; Outcome = $outcome; MachineId = $MachineId
                Operation = $Operation; RelativePath = $source.RelativePath; LogType = $source.LogType
            })
        }
        & $addResult $source $outcome $(if ($outcome -eq 'completed') { 'delete_confirmed' } else { 'delete_unknown' }) $destination.Id
    }
    # Preserve unresolved prior attempts even when this run enumerates zero sources.
    $pendingEvents = @($State.Events | Where-Object {
        $_.Kind -eq 'prepared' -or ($_.Kind -eq 'delete_result' -and $_.Outcome -eq 'unknown')
    })
    foreach ($pending in $pendingEvents) {
        if ($pending.MachineId -cne $MachineId -or $pending.Operation -cne $Operation) { continue }
        if (@($results | Where-Object { $_.SourceId -ceq $pending.SourceId }).Count -gt 0) { continue }
        if (@($State.Events | Where-Object {
            $_.Kind -in @('delete_result', 'reconciled') -and $_.SourceId -ceq $pending.SourceId -and
            $_.Outcome -eq 'completed'
        }).Count -gt 0) { continue }
        $records = @($State.Events | Where-Object {
            $_.Kind -eq 'prepared' -and $_.SourceId -ceq $pending.SourceId -and
            $_.DestinationId -ceq $pending.DestinationId -and $_.MachineId -ceq $MachineId -and
            $_.Operation -ceq $Operation
        })
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
        if ($DryRun -or $Faults.ContainsKey($record.SourceId)) { $canReconcile = $false }
        if ($canReconcile) {
            $State.Events.Add(@{
                Kind = 'reconciled'; SourceId = $record.SourceId; Outcome = 'completed'
                MachineId = $MachineId; Operation = $Operation
                RelativePath = $record.RelativePath; LogType = $record.LogType
            })
            & $addResult $reported 'completed' 'reconciled_completion' $record.DestinationId
        }
        else { & $addResult $reported 'unknown' 'reconciliation_unconfirmed' $record.DestinationId }
    }
    $completed = @($results | Where-Object { $_.Outcome -eq 'completed' }).Count
    $unresolved = @($results | Where-Object { $_.Outcome -in @('retained', 'unknown') }).Count
    $status = if ($unresolved -gt 0) {
        if ($completed -gt 0) { 'partial_failure' } else { 'failure' }
    }
    elseif ($DryRun) { 'dry_run' }
    elseif ($completed -gt 0) { 'success' }
    else { 'no_work' }
    return [pscustomobject]@{
        SimulationOnly = $true; MachineId = $MachineId; Operation = $Operation
        Status = $status; CompletedSourceCount = $completed; UnresolvedSourceCount = $unresolved
        Results = $results.ToArray()
    }
}
