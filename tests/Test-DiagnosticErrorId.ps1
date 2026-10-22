#requires -Version 7.6.7

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')

$script:Passed = 0
$script:Failed = 0

function Assert-Equal {
    param([string]$Name, [object]$Expected, [object]$Actual)
    if ([object]::Equals($Expected, $Actual)) {
        $script:Passed++
        Write-Host "PASS: $Name"
    }
    else {
        $script:Failed++
        Write-Host "FAIL: $Name"
    }
}

function Assert-Throws {
    param([string]$Name, [scriptblock]$Action)
    try {
        & $Action | Out-Null
        $script:Failed++
        Write-Host "FAIL: $Name (expected rejection)"
    }
    catch {
        if ($_.Exception.Message -ceq 'Diagnostic event ID sequence is invalid or exhausted.') {
            $script:Passed++
            Write-Host "PASS: $Name"
        }
        else {
            $script:Failed++
            Write-Host "FAIL: $Name (unexpected error shape)"
        }
    }
}

Assert-SupportedPowerShellVersion

# A per-run monotonic counter yields one fixed-width ID per call.
$next = 1
$first = New-DiagnosticErrorId -NextSequence ([ref]$next)
$second = New-DiagnosticErrorId -NextSequence ([ref]$next)
$third = New-DiagnosticErrorId -NextSequence ([ref]$next)
Assert-Equal 'first ID has canonical format' 'ERR-000001' $first
Assert-Equal 'second ID increments once' 'ERR-000002' $second
Assert-Equal 'third ID increments once' 'ERR-000003' $third
Assert-Equal 'counter advances monotonically' 4 $next
Assert-Equal 'allocated IDs are distinct' 3 (@($first, $second, $third) | Select-Object -Unique).Count

# The last representable ID is allocated, then the next call fails closed.
$lastSequence = 999998
$penultimate = New-DiagnosticErrorId -NextSequence ([ref]$lastSequence)
$last = New-DiagnosticErrorId -NextSequence ([ref]$lastSequence)
Assert-Equal 'penultimate representable ID' 'ERR-999998' $penultimate
Assert-Equal 'last representable ID' 'ERR-999999' $last
Assert-Equal 'exhaustion sentinel is one past maximum' 1000000 $lastSequence
Assert-Throws 'exhausted sequence rejected without wrap' {
    New-DiagnosticErrorId -NextSequence ([ref]$lastSequence)
}
Assert-Equal 'exhausted sequence remains unchanged' 1000000 $lastSequence

# Invalid counters reject without disclosing or mutating the rejected value.
foreach ($badValue in @($null, 0, -1, 1000000, '1', 1.5, $true)) {
    $state = $badValue
    $before = $state
    Assert-Throws "invalid sequence rejected: $badValue" {
        New-DiagnosticErrorId -NextSequence ([ref]$state)
    }
    Assert-Equal "invalid sequence unchanged: $badValue" $before $state
}

# Invariant formatting is stable under a non-English culture.
$originalCulture = [System.Globalization.CultureInfo]::CurrentCulture
try {
    [System.Globalization.CultureInfo]::CurrentCulture = [System.Globalization.CultureInfo]::GetCultureInfo('ar-SA')
    $cultureSequence = 42
    $cultureId = New-DiagnosticErrorId -NextSequence ([ref]$cultureSequence)
}
finally {
    [System.Globalization.CultureInfo]::CurrentCulture = $originalCulture
}
Assert-Equal 'ID format invariant across culture' 'ERR-000042' $cultureId

Write-Host "Diagnostic event ID allocation tests passed: $($script:Passed)"
if ($script:Failed -gt 0) {
    throw "$($script:Failed) diagnostic event ID allocation test(s) failed; $($script:Passed) passed."
}
