#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'LogMoveSimulation.ps1')

function Invoke-EoOwnedLogMoveSimulation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ConfigurationJson,
        [Parameter(Mandatory)][ValidateSet('PC-A','PC-B')][string]$MachineId,
        [Parameter(Mandatory)][ValidateSet('Sync','Archive')][string]$Operation,
        [Parameter(Mandatory)][hashtable]$State,
        [Parameter(Mandatory)][datetime]$ReferenceDate,
        [Parameter(Mandatory)][string]$LifecycleRoot,
        [Parameter(Mandatory)][string]$JournalRoot,
        [Parameter(Mandatory)][string]$ReportRoot,
        [string]$PythonExecutable='python',
        [guid]$RunId=[guid]::NewGuid(),
        [hashtable]$Faults=@{},
        [switch]$DryRun
    )
    $config=ConvertFrom-EoMachineConfigurationJson -Json $ConfigurationJson -ExpectedMachineId $MachineId
    if ($Operation -eq 'Archive' -and ($MachineId -ne 'PC-A' -or -not $config.allowArchive)) { throw 'move_archive_role_denied' }
    $arguments=@{ConfigurationJson=$ConfigurationJson;MachineId=$MachineId;Operation=$Operation;State=$State;
        ReferenceDate=$ReferenceDate;JournalRoot=$JournalRoot;ReportRoot=$ReportRoot;PythonExecutable=$PythonExecutable;
        RunId=$RunId;Faults=$Faults}
    # Keep Dry Run outside ordinary ownership/start/cleanup paths.
    if ($DryRun) {
        $result=Invoke-EoLogMoveSimulation @arguments -DryRun
        $result | Add-Member -NotePropertyName LifecycleStatus -NotePropertyValue 'not_started'
        return $result
    }
    $route=if ($Operation -eq 'Sync') {'local_to_cloud'}else{'cloud_to_archive'}
    $start=[Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$PythonExecutable
    $start.UseShellExecute=$false
    $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true
    $start.RedirectStandardOutput=$true
    $start.RedirectStandardError=$true
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot 'SimulationRunOwner.py'),'--lifecycle-root',$LifecycleRoot,
        '--journal-root',$JournalRoot,'--report-root',$ReportRoot,'--run-id',$RunId.ToString('D'),'--machine-id',$MachineId,'--route',$route)) {
        $start.ArgumentList.Add($argument)
    }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start
    $started=$false; $result=$null
    $validAck={
        param($Value,[string]$Phase)
        $Value -is [Collections.IDictionary] -and $Value.Count -eq 3 -and
        @($Value.Keys|Where-Object {$_ -cnotin @('protocol_version','phase','run_id')}).Count -eq 0 -and
        ($Value.protocol_version -is [int] -or $Value.protocol_version -is [long]) -and $Value.protocol_version -eq 1 -and
        $Value.phase -is [string] -and $Value.run_id -is [string] -and
        $Value.phase -ceq $Phase -and $Value.run_id -ceq $RunId.ToString('D')
    }
    try {
        [void]$process.Start(); $started=$true
        $stderr=$process.StandardError.ReadToEndAsync()
        $ready=$process.StandardOutput.ReadLineAsync()
        if (-not $ready.Wait(30000)) { throw 'owned_simulation_unconfirmed' }
        $ack=$ready.GetAwaiter().GetResult() | ConvertFrom-Json -AsHashtable
        if (-not (& $validAck $ack 'ready')) { throw 'owned_simulation_unconfirmed' }
        $result=Invoke-EoLogMoveSimulation @arguments
        $request=@{protocol_version=1;run_id=$RunId.ToString('D');operation_status=$result.Status;report_save_status=$result.ReportSaveStatus}
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $write=$process.StandardInput.WriteLineAsync(($request|ConvertTo-Json -Compress))
        if (-not $write.Wait(30000)) { throw 'owned_simulation_unconfirmed' }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'owned_simulation_unconfirmed' }
        [void]$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'owned_simulation_unconfirmed' }
        $ack=$stdout.GetAwaiter().GetResult() | ConvertFrom-Json -AsHashtable
        if (-not (& $validAck $ack 'finished')) { throw 'owned_simulation_unconfirmed' }
        $result | Add-Member -NotePropertyName LifecycleStatus -NotePropertyValue 'confirmed'
    }
    catch {
        if ($null -eq $result) { throw 'owned_simulation_interrupted' }
        $result | Add-Member -NotePropertyName LifecycleStatus -NotePropertyValue 'unconfirmed'
    }
    finally {
        if ($started -and -not $process.HasExited) {
            # EOF asks the owner to record interruption, without an invented result.
            try { $process.StandardInput.Close() } catch {}
            if (-not $process.WaitForExit(30000)) { try { $process.Kill($true); $process.WaitForExit() } catch {} }
        }
        $process.Dispose()
    }
    return $result
}
