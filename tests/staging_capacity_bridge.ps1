#requires -Version 7.6.7
# TEST ONLY: fixed stdin data bridge, not an IPC/runtime entry point.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/LogFunctions.ps1')

try {
    $cases = ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd()) -AsHashtable -NoEnumerate
    if ($cases -isnot [Array]) { throw 'invalid' }
    $results = [Collections.Generic.List[object]]::new()
    foreach ($case in $cases) {
        if ($case -isnot [Collections.IDictionary] -or $case.Count -ne 3) { throw 'invalid' }
        foreach ($key in @('target_sizes', 'available_free_bytes', 'free_space_reliable')) {
            if (-not $case.Contains($key)) { throw 'invalid' }
        }
        $result = Get-EoStagingCapacityFromSizes -RemainingTargetSizes $case.target_sizes `
            -AvailableFreeBytes $case.available_free_bytes -FreeSpaceReliable $case.free_space_reliable
        $results.Add($result)
    }
    [pscustomobject]@{
        PowerShellVersion = $PSVersionTable.PSVersion.ToString()
        Observations = $results.ToArray()
    } | ConvertTo-Json -Depth 6 -Compress
}
catch {
    [Console]::Error.WriteLine('fixture_capacity_bridge_invalid')
    exit 2
}
