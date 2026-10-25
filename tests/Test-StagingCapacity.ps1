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

# An explicit remaining-size snapshot is summed without selecting file states.
$sumCases = @(
    @{ Sizes = [object[]]@(); Total = [bigint]0; Count = 0; Required = [bigint]100000000 },
    @{ Sizes = [int[]]@(1, 9); Total = [bigint]10; Count = 2; Required = [bigint]100000011 },
    @{ Sizes = [long[]]@(1, 1, 1); Total = [bigint]3; Count = 3; Required = [bigint]100000004 },
    @{ Sizes = [object[]]@([int]0, [long]11, [bigint]99); Total = [bigint]110; Count = 3; Required = [bigint]100000121 },
    @{ Sizes = [bigint[]]@($large, $large); Total = $large*2; Count = 2; Required = ($largeRequired*2)-100000001 }
)
foreach ($case in $sumCases) {
    $result = Get-EoStagingCapacityFromSizes -RemainingTargetSizes $case.Sizes `
        -AvailableFreeBytes $case.Required -FreeSpaceReliable $true
    Assert-Capacity $result 'requires_runtime_evidence' 'staging_capacity_observed_sufficient' $case.Required
    if ($result.RemainingTargetBytes -isnot [bigint] -or $result.RemainingTargetBytes -ne $case.Total -or
        $result.TargetCount -ne $case.Count) { throw 'Remaining-target total mismatch.' }
    Assert-Capacity (Get-EoStagingCapacityFromSizes $case.Sizes ($case.Required-1) $true) `
        'held' 'staging_capacity_insufficient' $case.Required
}
foreach ($bad in @($null, $true, -1, 1.0, '1', [decimal]1)) {
    $result = Get-EoStagingCapacityFromSizes -RemainingTargetSizes ([object[]]@(10, $bad)) `
        -AvailableFreeBytes 200000000 -FreeSpaceReliable $true
    Assert-Capacity $result 'rejected' 'staging_target_sizes_invalid' $null
    if ($null -ne $result.RemainingTargetBytes -or $null -ne $result.TargetCount) {
        throw 'An invalid member produced a partial total.'
    }
}
foreach ($invalidSet in @(@{ value = 10 }, @{ value = '10' }, @{ value = $null },
                          @{ value = [Array]::CreateInstance([int], 1, 1) })) {
    Assert-Capacity (Get-EoStagingCapacityFromSizes -RemainingTargetSizes $invalidSet.value `
        -AvailableFreeBytes 200000000 -FreeSpaceReliable $true) `
        'rejected' 'staging_target_sizes_invalid' $null
}
$initialSizes = [object[]]@(10, 20)
$initialCopy = $initialSizes.Clone()
$initial = Get-EoStagingCapacityFromSizes $initialSizes 100000033 $true
$next = Get-EoStagingCapacityFromSizes ([object[]]@(20)) 100000021 $true
Assert-Capacity $initial 'requires_runtime_evidence' 'staging_capacity_observed_sufficient' ([bigint]100000033)
Assert-Capacity $next 'held' 'staging_capacity_insufficient' ([bigint]100000022)
if (($initialSizes -join ',') -cne ($initialCopy -join ',')) { throw 'Input sizes changed.' }
Assert-Capacity (Get-EoStagingCapacityFromSizes ([object[]]@(1)) 200000000 $false) `
    'held' 'staging_capacity_unconfirmed' ([bigint]100000002)
Assert-Capacity (Get-EoStagingCapacityFromSizes ([object[]]@(1)) $null $true) `
    'rejected' 'staging_available_bytes_invalid' $null
Write-Host "PASS: $checks total capacity observations including explicit target-size snapshots."
