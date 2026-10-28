#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'LogFunctions.ps1')

function Read-EoSimulationFileSnapshot {
    [CmdletBinding()]
    param([object[]]$Roots,[string[]]$ExcludedRoots,[string]$MachineId,[string]$Operation,[guid]$RequestId,[string]$PythonExecutable)
    $route=if ($Operation -eq 'Sync') {'local_to_cloud'}else{'cloud_to_archive'}
    $request=@{protocol_version=1;simulation_only=$true;request_id=$RequestId.ToString('D');machine_id=$MachineId;route=$route;
        roots=$Roots;excluded_roots=$ExcludedRoots}
    $start=[Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$PythonExecutable; $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot 'SimulationFileSnapshot.py'))) { $start.ArgumentList.Add($argument) }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start; $started=$false
    try {
        [void]$process.Start(); $started=$true
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        $write=$process.StandardInput.WriteAsync(($request|ConvertTo-Json -Depth 10 -Compress))
        if (-not $write.Wait(30000)) { throw 'simulation_snapshot_unconfirmed' }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'simulation_snapshot_unconfirmed' }
        [void]$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'simulation_snapshot_unconfirmed' }
        $response=$stdout.GetAwaiter().GetResult()|ConvertFrom-Json -AsHashtable -DateKind String
        if ($response -isnot [Collections.IDictionary] -or $response.Count -ne 2 -or
            @($response.Keys|Where-Object {$_ -cnotin @('ok','snapshot')}).Count -ne 0 -or
            $response.ok -isnot [bool] -or -not $response.ok) { throw 'simulation_snapshot_unconfirmed' }
        $snapshot=$response.snapshot
        $keys=@('protocol_version','simulation_only','request_id','machine_id','route','enumeration_complete','file_count','total_bytes','files')
        if ($snapshot -isnot [Collections.IDictionary] -or $snapshot.Count -ne $keys.Count -or
            @($snapshot.Keys|Where-Object {$_ -cnotin $keys}).Count -ne 0 -or
            ($snapshot.protocol_version -isnot [int] -and $snapshot.protocol_version -isnot [long]) -or $snapshot.protocol_version -ne 1 -or
            $snapshot.simulation_only -isnot [bool] -or -not $snapshot.simulation_only -or
            $snapshot.enumeration_complete -isnot [bool] -or -not $snapshot.enumeration_complete -or
            $snapshot.request_id -isnot [string] -or $snapshot.request_id -cne $request.request_id -or
            $snapshot.machine_id -isnot [string] -or $snapshot.machine_id -cne $MachineId -or
            $snapshot.route -isnot [string] -or $snapshot.route -cne $route -or $snapshot.files -isnot [Array]) { throw 'simulation_snapshot_unconfirmed' }
        foreach ($key in @('file_count','total_bytes')) {
            if (($snapshot[$key] -isnot [int] -and $snapshot[$key] -isnot [long]) -or $snapshot[$key] -lt 0) { throw 'simulation_snapshot_unconfirmed' }
        }
        if ($snapshot.file_count -ne $snapshot.files.Count -or $snapshot.file_count -gt 4096 -or $snapshot.total_bytes -gt 4194304) { throw 'simulation_snapshot_unconfirmed' }
        $files=[Collections.Generic.List[object]]::new(); $ids=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal); $total=0L
        $locations=if ($Operation -eq 'Sync') {@($MachineId,'Cloud')}else{@('Cloud','Archive')}
        foreach ($file in $snapshot.files) {
            $keys=@('id','location','log_type','relative_path','size','sha256','content_base64')
            if ($file -isnot [Collections.IDictionary] -or $file.Count -ne $keys.Count -or
                @($file.Keys|Where-Object {$_ -cnotin $keys}).Count -ne 0 -or
                $file.id -isnot [string] -or $file.id -cnotmatch '^snapshot-[a-f0-9]{64}$' -or -not $ids.Add($file.id) -or
                $file.location -isnot [string] -or $file.location -cnotin $locations -or
                $file.log_type -isnot [string] -or $file.log_type -cnotin @('BattleLog','ErrorReport') -or
                $null -eq (ConvertTo-SafeDiagnosticRelativePath -Path $file.relative_path) -or
                ($file.size -isnot [int] -and $file.size -isnot [long]) -or $file.size -lt 0 -or $file.size -gt 1048576 -or
                $file.sha256 -isnot [string] -or $file.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $file.content_base64 -isnot [string] -or
                $file.content_base64.Length -gt 1398104) { throw 'simulation_snapshot_unconfirmed' }
            $bytes=[Convert]::FromBase64String($file.content_base64)
            $total+=$bytes.LongLength
            if ($bytes.LongLength -ne $file.size -or $total -gt 4194304 -or
                [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne $file.sha256) { throw 'simulation_snapshot_unconfirmed' }
            $files.Add(@{Id=$file.id;Location=$file.location;LogType=$file.log_type;RelativePath=$file.relative_path;Bytes=$bytes})
        }
        if ($total -ne $snapshot.total_bytes) { throw 'simulation_snapshot_unconfirmed' }
        return @{Files=$files;Events=[Collections.Generic.List[object]]::new()}
    }
    catch { throw 'simulation_snapshot_unconfirmed' }
    finally {
        if ($started -and -not $process.HasExited) { try {$process.Kill($true);$process.WaitForExit()}catch{} }
        $process.Dispose()
    }
}
