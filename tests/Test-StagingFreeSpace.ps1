#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/MachineConfigurationRootInspection.ps1')
. (Join-Path $PSScriptRoot '../Common/LogFunctions.ps1')
$checks = 0
$skipped = 0
function Assert-Observation([object]$Result, [bool]$Observed) {
    if ($Result.FreeSpaceReliable -or $Result.MayCreateStaging -or $Result.MayUpload) {
        throw 'Free-space observation became authority.'
    }
    if ($Observed) {
        if ($Result.Status -cne 'requires_runtime_evidence' -or
            $Result.ReasonCode -cne 'staging_free_space_metadata_observed' -or
            $Result.AvailableFreeBytes -isnot [bigint] -or $Result.AvailableFreeBytes -lt 0) {
            throw 'Expected free-space metadata observation.'
        }
    }
    elseif ($Result.Status -cne 'held' -or $Result.ReasonCode -cne 'staging_free_space_unavailable' -or
            $null -ne $Result.AvailableFreeBytes) { throw 'Expected held free-space observation.' }
    $script:checks++
}

$parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar)
$root = Join-Path $parent ('eo-free-space-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root) | Out-Null
$marker = Join-Path $root 'sentinel.txt'
[IO.File]::WriteAllText($marker, 'synthetic-preserve')
$junction = Join-Path $root 'alias'
$originalQuery = (Get-Item Function:Get-EoDirectoryAvailableBytes).ScriptBlock
$originalCanonical = (Get-Item Function:Get-EoExistingDirectoryCanonicalPath).ScriptBlock
try {
    $result = Get-EoStagingFreeSpaceObservation $root
    Assert-Observation $result $true
    if (($result | ConvertTo-Json -Compress).Contains($root)) { throw 'Path leaked into result.' }
    $capacity = Get-EoStagingCapacityObservation 1 $result.AvailableFreeBytes $result.FreeSpaceReliable
    if ($capacity.Status -cne 'held' -or $capacity.ReasonCode -cne 'staging_capacity_unconfirmed') {
        throw 'Unqualified metadata bypassed the capacity gate.'
    }
    $checks++
    foreach ($path in @($null, '', 'relative', '\\synthetic-server\share', '\\?\C:\synthetic',
                         (Join-Path $root 'missing'), $marker)) {
        Assert-Observation (Get-EoStagingFreeSpaceObservation $path) $false
    }
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) throw 'synthetic-private-detail' }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) [ulong]::MaxValue }
    $large = Get-EoStagingFreeSpaceObservation $root
    Assert-Observation $large $true
    if ($large.AvailableFreeBytes -ne [bigint]::Parse('18446744073709551615')) { throw 'UInt64 truncated.' }
    $checks++
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) 'not-a-count' }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    $script:canonicalCalls = 0
    Set-Item Function:Get-EoExistingDirectoryCanonicalPath -Value {
        param($LiteralPath)
        $script:canonicalCalls++
        return 'synthetic-canonical-' + $script:canonicalCalls
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoExistingDirectoryCanonicalPath -Value $originalCanonical
    $target = Join-Path $root 'target'
    [IO.Directory]::CreateDirectory($target) | Out-Null
    & $env:ComSpec /d /c mklink /J $junction $target 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Assert-Observation (Get-EoStagingFreeSpaceObservation $junction) $false
    }
    else { $skipped++ }
    if ([IO.File]::ReadAllText($marker) -cne 'synthetic-preserve') { throw 'Original bytes changed.' }
    $checks++
}
finally {
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    Set-Item Function:Get-EoExistingDirectoryCanonicalPath -Value $originalCanonical
    $resolved = [IO.Path]::GetFullPath($root)
    if ([IO.Path]::GetDirectoryName($resolved).TrimEnd([IO.Path]::DirectorySeparatorChar) -cne $parent -or
        -not [IO.Path]::GetFileName($resolved).StartsWith('eo-free-space-') -or
        ([IO.File]::GetAttributes($resolved) -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        [IO.File]::ReadAllText($marker) -cne 'synthetic-preserve') { throw 'Unexpected cleanup root.' }
    if ([IO.Directory]::Exists($junction)) { [IO.Directory]::Delete($junction) }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Host "PASS: $checks free-space observations; $skipped unavailable junction checks skipped."
