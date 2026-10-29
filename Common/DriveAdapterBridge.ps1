#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-EoDriveApiFixture {
    [CmdletBinding()]
    param([string]$PythonExecutable, [hashtable]$Request)
    $requestId = [guid]::NewGuid().ToString('D')
    $Request.request_id = $requestId
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$PythonExecutable; $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($argument in @('-B',(Join-Path $PSScriptRoot '../tests/drive_adapter_fixture_worker.py'))) { $start.ArgumentList.Add($argument) }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start; $started=$false
    try {
        [void]$process.Start(); $started=$true
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        $write=$process.StandardInput.WriteAsync(($Request|ConvertTo-Json -Depth 8 -Compress))
        if (-not $write.Wait(30000)) { throw 'drive_api_unconfirmed' }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'drive_api_unconfirmed' }
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
