#requires -Version 7.6.7

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')

$script:Passed = 0
$script:Failed = 0

function Assert-Equal {
    param(
        [string]$Name,
        [object]$Expected,
        [object]$Actual
    )

    if ($Expected -ne $Actual) {
        $script:Failed++
        Write-Host "FAIL: $Name (expected=$Expected, actual=$Actual)" -ForegroundColor Red
    }
    else {
        $script:Passed++
        Write-Host "PASS: $Name"
    }
}

function Assert-Throws {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    try {
        & $Action
        $script:Failed++
        Write-Host "FAIL: $Name (expected an exception)" -ForegroundColor Red
    }
    catch {
        $script:Passed++
        Write-Host "PASS: $Name"
    }
}

# The shared module performs the live-runtime guard before the tests execute.
Assert-SupportedPowerShellVersion

# Simulated versions exercise the guard's fail-closed decision independently
# of the PowerShell version running this test process.
$acceptedVersionResult = 'rejected'
try {
    Assert-SupportedPowerShellVersion -Version ([version]'7.6.7')
    $acceptedVersionResult = 'accepted'
}
catch {
    $acceptedVersionResult = 'rejected'
}
Assert-Equal 'PowerShell 7.6.7 accepted' 'accepted' $acceptedVersionResult
Assert-Throws 'PowerShell 7.0 rejected' {
    Assert-SupportedPowerShellVersion -Version ([version]'7.0.0')
}
Assert-Throws 'PowerShell 7.6.6 rejected' {
    Assert-SupportedPowerShellVersion -Version ([version]'7.6.6')
}
Assert-Throws 'PowerShell 7.6.8 rejected because exact version is required' {
    Assert-SupportedPowerShellVersion -Version ([version]'7.6.8')
}
Assert-Throws 'Unavailable PowerShell version rejected' {
    Assert-SupportedPowerShellVersion -Version $null
}
Assert-Throws 'Malformed PowerShell version rejected' {
    Assert-SupportedPowerShellVersion -Version 'not-a-version'
}

$referenceDate = [datetime]::new(2026, 10, 20)

# Filename parsing
Assert-Equal 'BattleLog date parsing' `
    ([datetime]::new(2026, 9, 30)) `
    (Get-LogFileDate -LogType BattleLog -FileName '20260930_12345678@Example.txt')

Assert-Equal 'ErrorReport date parsing' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogFileDate -LogType ErrorReport -FileName '20251231_12345678.txt')

Assert-Throws 'BattleLog unexpected filename' {
    Get-LogFileDate -LogType BattleLog -FileName 'unexpected.txt'
}

Assert-Throws 'ErrorReport unexpected suffix' {
    Get-LogFileDate -LogType ErrorReport -FileName '20251231_12345678@Example.txt'
}

Assert-Throws 'Impossible calendar date' {
    Get-LogFileDate -LogType ErrorReport -FileName '20260230_12345678.txt'
}

Assert-Throws 'Invalid leap day' {
    Get-LogFileDate -LogType ErrorReport -FileName '20250229_12345678.txt'
}

Assert-Equal 'Valid leap day accepted' `
    ([datetime]::new(2024, 2, 29)) `
    (Get-LogFileDate -LogType ErrorReport -FileName '20240229_12345678.txt')

Assert-Throws 'Invalid month rejected' {
    Get-LogFileDate -LogType ErrorReport -FileName '20261301_12345678.txt'
}

Assert-Throws 'BattleLog missing underscore rejected' {
    Get-LogFileDate -LogType BattleLog -FileName '2026093012345678@Example.txt'
}

Assert-Throws 'BattleLog wrong extension rejected' {
    Get-LogFileDate -LogType BattleLog -FileName '20260930_12345678@Example.log'
}

Assert-Throws 'BattleLog uppercase extension rejected' {
    Get-LogFileDate -LogType BattleLog -FileName '20260930_12345678@Example.TXT'
}

Assert-Throws 'ErrorReport uppercase extension rejected' {
    Get-LogFileDate -LogType ErrorReport -FileName '20251231_12345678.TXT'
}

$currentCulture = [Globalization.CultureInfo]::CurrentCulture
try {
    [Globalization.CultureInfo]::CurrentCulture = [Globalization.CultureInfo]::GetCultureInfo('th-TH')
    Assert-Equal 'Filename date parsing uses invariant culture' `
        ([datetime]::new(2026, 9, 30)) `
        (Get-LogFileDate -LogType BattleLog -FileName '20260930_12345678@Example.txt')
}
finally {
    [Globalization.CultureInfo]::CurrentCulture = $currentCulture
}

Assert-Throws 'BattleLog empty suffix rejected' {
    Get-LogFileDate -LogType BattleLog -FileName '20260930_12345678@.txt'
}

# Sync cutoffs: reference date 2026-10-20
Assert-Equal 'BattleLog sync cutoff' `
    ([datetime]::new(2026, 9, 30)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $referenceDate)

Assert-Equal 'ErrorReport sync cutoff' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogSyncCutoffDate -LogType ErrorReport -ReferenceDate $referenceDate)

Assert-Equal 'BattleLog last eligible sync date' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260930_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $referenceDate
)

Assert-Equal 'BattleLog next day excluded from sync' $false (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20261001_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $referenceDate
)

Assert-Equal 'ErrorReport last eligible sync date' $true (
    Test-LogFileEligible -LogType ErrorReport `
        -FileName '20251231_12345678.txt' `
        -Operation Sync -ReferenceDate $referenceDate
)

Assert-Equal 'ErrorReport next year excluded from sync' $false (
    Test-LogFileEligible -LogType ErrorReport `
        -FileName '20260101_12345678.txt' `
        -Operation Sync -ReferenceDate $referenceDate
)

# Archive cutoffs: selection only; no archive operation is performed.
Assert-Equal 'BattleLog archive cutoff' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogArchiveCutoffDate -LogType BattleLog -ReferenceDate $referenceDate)

Assert-Equal 'ErrorReport archive cutoff' `
    ([datetime]::new(2024, 12, 31)) `
    (Get-LogArchiveCutoffDate -LogType ErrorReport -ReferenceDate $referenceDate)

Assert-Equal 'BattleLog last eligible archive date' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20251231_12345678@Example.txt' `
        -Operation Archive -ReferenceDate $referenceDate
)

Assert-Equal 'BattleLog next year excluded from archive' $false (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260101_12345678@Example.txt' `
        -Operation Archive -ReferenceDate $referenceDate
)

Assert-Equal 'ErrorReport last eligible archive date' $true (
    Test-LogFileEligible -LogType ErrorReport `
        -FileName '20241231_12345678.txt' `
        -Operation Archive -ReferenceDate $referenceDate
)

Assert-Equal 'ErrorReport next year excluded from archive' $false (
    Test-LogFileEligible -LogType ErrorReport `
        -FileName '20250101_12345678.txt' `
        -Operation Archive -ReferenceDate $referenceDate
)

# Month-end cutoff coverage across 28/29/30/31-day months.
$nonLeapFebruaryReference = [datetime]::new(2025, 3, 15)
Assert-Equal 'Non-leap February cutoff is February 28' `
    ([datetime]::new(2025, 2, 28)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $nonLeapFebruaryReference)

$leapFebruaryReference = [datetime]::new(2024, 3, 15)
Assert-Equal 'Leap February cutoff is February 29' `
    ([datetime]::new(2024, 2, 29)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $leapFebruaryReference)

$thirtyDayMonthReference = [datetime]::new(2026, 5, 15)
Assert-Equal 'April cutoff is April 30' `
    ([datetime]::new(2026, 4, 30)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $thirtyDayMonthReference)

$thirtyOneDayMonthReference = [datetime]::new(2026, 7, 15)
Assert-Equal 'June cutoff is June 30' `
    ([datetime]::new(2026, 6, 30)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $thirtyOneDayMonthReference)

Assert-Equal 'April 30 is eligible at May reference date' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260430_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $thirtyDayMonthReference
)
Assert-Equal 'May 1 is excluded at May reference date' $false (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260501_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $thirtyDayMonthReference
)
Assert-Equal 'June 30 is eligible at July reference date' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260630_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $thirtyOneDayMonthReference
)
Assert-Equal 'July 1 is excluded at July reference date' $false (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260701_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $thirtyOneDayMonthReference
)

# January rollover and calendar-boundary regression cases.
$janReferenceDate = [datetime]::new(2026, 1, 15)
Assert-Equal 'January BattleLog sync cutoff crosses year' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $janReferenceDate)
Assert-Equal 'January ErrorReport sync cutoff is prior calendar year end' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogSyncCutoffDate -LogType ErrorReport -ReferenceDate $janReferenceDate)
Assert-Equal 'January BattleLog archive cutoff is prior calendar year end' `
    ([datetime]::new(2025, 12, 31)) `
    (Get-LogArchiveCutoffDate -LogType BattleLog -ReferenceDate $janReferenceDate)
Assert-Equal 'January ErrorReport archive cutoff is two calendar years back' `
    ([datetime]::new(2024, 12, 31)) `
    (Get-LogArchiveCutoffDate -LogType ErrorReport -ReferenceDate $janReferenceDate)

Assert-Equal 'January rollover prior-year BattleLog eligible for sync' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20251231_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $janReferenceDate
)
Assert-Equal 'January rollover current-year BattleLog excluded from sync' $false (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20260101_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $janReferenceDate
)
Assert-Equal 'Older historical BattleLog remains sync eligible' $true (
    Test-LogFileEligible -LogType BattleLog `
        -FileName '20200101_12345678@Example.txt' `
        -Operation Sync -ReferenceDate $referenceDate
)

$leapReferenceDate = [datetime]::new(2024, 2, 29)
Assert-Equal 'Leap-year February BattleLog sync cutoff' `
    ([datetime]::new(2024, 1, 31)) `
    (Get-LogSyncCutoffDate -LogType BattleLog -ReferenceDate $leapReferenceDate)
Assert-Equal 'Leap-year February ErrorReport sync cutoff' `
    ([datetime]::new(2023, 12, 31)) `
    (Get-LogSyncCutoffDate -LogType ErrorReport -ReferenceDate $leapReferenceDate)

Write-Host ''
Write-Host "Results: $script:Passed passed, $script:Failed failed"

if ($script:Failed -gt 0) {
    exit 1
}
