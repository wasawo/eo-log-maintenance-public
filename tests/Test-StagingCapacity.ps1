#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/LogFunctions.ps1')

$checks = 0
function Assert-Capacity {
    param([object] $Result, [string] $Status, [string] $Reason, [object] $Required)
    if ($Result.Status -cne $Status -or $Result.ReasonCode -cne $Reason -or
        $Result.RequiredFreeBytes -ne $Required -or $Result.MayCreateStaging -or $Result.MayUpload) {
        throw 'Capacity observation mismatch.'
    }
    if ($null -ne $Required -and $Result.RequiredFreeBytes -isnot [bigint]) {
        throw 'Capacity arithmetic lost integer precision.'
    }
    $script:checks++
}

$cases = @(
    @(0, 100000000), @(1, 100000002), @(9, 100000010), @(10, 100000011),
    @(11, 100000013), @(99, 100000109), @(100, 100000110)
)
foreach ($case in $cases) {
    $remaining = [bigint]$case[0]
    $required = [bigint]$case[1]
    Assert-Capacity (Get-EoStagingCapacityObservation $remaining $required $true) `
        'requires_runtime_evidence' 'staging_capacity_observed_sufficient' $required
    Assert-Capacity (Get-EoStagingCapacityObservation $remaining ($required-1) $true) `
        'held' 'staging_capacity_insufficient' $required
}

# Beyond Int64 and IEEE-754 exact integers: remainder 1 requires rounding up.
$large = [bigint]::Parse('100000000000000000000000000000000000000000000000001')
$largeRequired = [bigint]::Parse('110000000000000000000000000000000000000000100000002')
Assert-Capacity (Get-EoStagingCapacityObservation $large $largeRequired $true) `
    'requires_runtime_evidence' 'staging_capacity_observed_sufficient' $largeRequired
Assert-Capacity (Get-EoStagingCapacityObservation $large ($largeRequired-1) $true) `
    'held' 'staging_capacity_insufficient' $largeRequired

foreach ($bad in @($null, $true, $false, -1, 1.0, [decimal]1, '1', [double]::NaN, [double]::PositiveInfinity)) {
    Assert-Capacity (Get-EoStagingCapacityObservation $bad 200000000 $true) `
        'rejected' 'staging_remaining_bytes_invalid' $null
    Assert-Capacity (Get-EoStagingCapacityObservation 1 $bad $true) `
        'rejected' 'staging_available_bytes_invalid' $null
}
foreach ($unconfirmed in @($null, $false, 1, 'true')) {
    Assert-Capacity (Get-EoStagingCapacityObservation 1 200000000 $unconfirmed) `
        'held' 'staging_capacity_unconfirmed' ([bigint]100000002)
}
foreach ($remaining in @([int]10, [long]10, [bigint]10)) {
    Assert-Capacity (Get-EoStagingCapacityObservation $remaining ([long]100000011) $true) `
        'requires_runtime_evidence' 'staging_capacity_observed_sufficient' ([bigint]100000011)
}

# Start and per-file observations are independent, never a capacity reservation.
$first = Get-EoStagingCapacityObservation 100 100000110 $true
$later = Get-EoStagingCapacityObservation 100 100000109 $true
Assert-Capacity $first 'requires_runtime_evidence' 'staging_capacity_observed_sufficient' ([bigint]100000110)
Assert-Capacity $later 'held' 'staging_capacity_insufficient' ([bigint]100000110)
if ($first.MayCreateStaging -or $later.MayCreateStaging) { throw 'Observation became a permit.' }
Write-Host "PASS: $checks capacity observations; no staging or upload authority."
