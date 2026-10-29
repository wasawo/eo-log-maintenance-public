#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-EoDriveApiFixture {
    [CmdletBinding()]
    param([string]$PythonExecutable, [hashtable]$Request, [string]$ConnectionConfig, [Diagnostics.Stopwatch]$RunClock)
    $requestId = [guid]::NewGuid().ToString('D')
    $timeout = if ($ConnectionConfig) { 120000 } else { 30000 }
    if ($ConnectionConfig -and $null -ne $RunClock) {
        $timeout = [int][Math]::Min($timeout, 600000 - $RunClock.Elapsed.TotalMilliseconds)
        if ($timeout -le 0) { throw 'drive_api_unconfirmed' }
    }
    $Request.request_id = $requestId
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$PythonExecutable; $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    $worker = if ($ConnectionConfig) { 'IsolatedDriveRunner.py' } else { '../tests/drive_adapter_fixture_worker.py' }
    if ($ConnectionConfig) { $Request.connection_config = $ConnectionConfig }
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot $worker))) { $start.ArgumentList.Add($argument) }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start; $started=$false
    $callClock=[Diagnostics.Stopwatch]::StartNew()
    try {
        [void]$process.Start(); $started=$true
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        $write=$process.StandardInput.WriteAsync(($Request|ConvertTo-Json -Depth 8 -Compress))
        if (-not $write.Wait([int][Math]::Min(30000,$timeout))) { throw 'drive_api_unconfirmed' }
        $process.StandardInput.Close()
        $remaining=[int]($timeout-$callClock.Elapsed.TotalMilliseconds)
        if ($remaining -le 0 -or -not $process.WaitForExit($remaining)) { throw 'drive_api_unconfirmed' }
        [void]$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'drive_api_unconfirmed' }
        $response=$stdout.GetAwaiter().GetResult()|ConvertFrom-Json -AsHashtable -DateKind String
        if ($response -isnot [Collections.IDictionary] -or $response.Count -ne 4 -or
            $response.protocol_version -ne 1 -or $response.request_id -cne $requestId -or
            $response.ok -isnot [bool] -or -not $response.ok -or $response.result -isnot [Collections.IDictionary]) {
            throw 'drive_api_unconfirmed'
        }
        return $response.result
    }
    catch { throw 'drive_api_unconfirmed' }
    finally {
        if ($started -and -not $process.HasExited) { try {$process.Kill($true);$process.WaitForExit()} catch {} }
        $process.Dispose()
    }
}
