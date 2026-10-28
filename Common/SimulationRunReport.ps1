#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Save-EoSimulationRunReport {
    [CmdletBinding()]
    param([hashtable]$Report,[string]$ReportRoot,[string]$PythonExecutable)
    $start=[Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$PythonExecutable
    $start.UseShellExecute=$false
    $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true
    $start.RedirectStandardOutput=$true
    $start.RedirectStandardError=$true
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot 'SimulationRunReport.py'),'--report-root',$ReportRoot)) { $start.ArgumentList.Add($argument) }
    $process=[Diagnostics.Process]::new()
    $process.StartInfo=$start
    $started=$false
    try {
        [void]$process.Start(); $started=$true
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        $write=$process.StandardInput.WriteAsync((ConvertTo-Json -InputObject $Report -Depth 20 -Compress))
        if (-not $write.Wait(30000)) { throw 'simulation_report_unconfirmed' }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'simulation_report_unconfirmed' }
        [void]$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'simulation_report_unconfirmed' }
        $response=$stdout.GetAwaiter().GetResult() | ConvertFrom-Json -AsHashtable -DateKind String
        $keys=@('report_version','run_id','machine_id','route','simulation_only','status','inventory_source_count',
            'result_source_count','deleted_source_count','reconciled_source_count','unresolved_source_count',
            'journal_unresolved_source_count','journal_read_status')
        if ($response -isnot [Collections.IDictionary] -or $response.Count -ne 2 -or
            @($response.Keys|Where-Object {$_ -cnotin @('ok','summary')}).Count -ne 0 -or
            $response.ok -isnot [bool] -or -not $response.ok) { throw 'simulation_report_unconfirmed' }
        $summary=$response.summary
        if ($summary -isnot [Collections.IDictionary] -or $summary.Count -ne $keys.Count -or
            @($summary.Keys|Where-Object {$_ -cnotin $keys}).Count -ne 0 -or
            $summary.report_version -isnot [long] -and $summary.report_version -isnot [int]) { throw 'simulation_report_unconfirmed' }
        foreach ($key in @('inventory_source_count','result_source_count','deleted_source_count','reconciled_source_count',
            'unresolved_source_count','journal_unresolved_source_count')) {
            if (($summary[$key] -isnot [int] -and $summary[$key] -isnot [long]) -or $summary[$key] -lt 0) { throw 'simulation_report_unconfirmed' }
        }
        if ($summary.report_version -ne 1 -or $summary.simulation_only -isnot [bool] -or -not $summary.simulation_only -or
            $summary.run_id -cne $Report.run_id -or $summary.machine_id -cne $Report.machine_id -or $summary.route -cne $Report.route -or
            $summary.inventory_source_count -ne $Report.inventory_source_count -or $summary.result_source_count -ne $Report.results.Count -or
            $summary.journal_read_status -cne $Report.journal_read_status -or
            $summary.journal_unresolved_source_count -ne $Report.journal_unresolved_move_refs.Count -or
            $summary.deleted_source_count -ne @($Report.results|Where-Object {$_.reason_code -ceq 'delete_confirmed'}).Count -or
            $summary.reconciled_source_count -ne @($Report.results|Where-Object {$_.reason_code -ceq 'reconciled_completion'}).Count -or
            $summary.unresolved_source_count -ne @($Report.results|Where-Object {$_.outcome -cin @('retained','unknown')}).Count -or
            $summary.status -cnotin @('success','no_work','partial_failure','failure')) { throw 'simulation_report_unconfirmed' }
        return $summary
    }
    catch { throw 'simulation_report_unconfirmed' }
    finally {
        if ($started -and -not $process.HasExited) { try { $process.Kill($true); $process.WaitForExit() } catch {} }
        $process.Dispose()
    }
}
