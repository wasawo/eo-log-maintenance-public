#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')
$script:Passed = 0
$script:Failed = 0

function Assert-Equal {
    param([string]$Name,[object]$Expected,[object]$Actual)
    if ([object]::Equals($Expected,$Actual)) { $script:Passed++; Write-Host "PASS: $Name" }
    else { $script:Failed++; Write-Host "FAIL: $Name (expected '$Expected'; got '$Actual')" }
}
function Assert-Rejected {
    param([string]$Name,[scriptblock]$Action)
    try { & $Action | Out-Null; $script:Failed++; Write-Host "FAIL: $Name (accepted)" }
    catch {
        if ($_.Exception.Message -ceq 'Diagnostic operation rejected by C-51 resolver.') {
            $script:Passed++; Write-Host "PASS: $Name"
        }
        else { $script:Failed++; Write-Host "FAIL: $Name (unexpected error shape)" }
    }
}

$cases = @(
    @{ Operation='enumerate_entries'; Phase='enumeration' },
    @{ Operation='classify_target'; Phase='classification' },
    @{ Operation='read_metadata'; Phase='metadata' },
    @{ Operation='read_content'; Phase='content_read' },
    @{ Operation='compute_hash'; Phase='hashing' },
    @{ Operation='detect_source_mutation'; Phase='metadata' },
    @{ Operation='validate_manifest'; Phase='manifest_validation' },
    @{ Operation='validate_evidence'; Phase='evidence_validation' },
    @{ Operation='finalize_evidence'; Phase='evidence_finalization' },
    @{ Operation='aggregate_results'; Phase='aggregation' },
    @{ Operation='serialize_report'; Phase='report_serialization' },
    @{ Operation='publish_report'; Phase='report_publication' },
    # Only a trusted producer with genuinely unavailable context may choose this token.
    @{ Operation='unknown'; Phase='unknown' }
)

foreach ($case in $cases) {
    $actual = Resolve-DiagnosticPhaseOperation -Operation $case.Operation
    Assert-Equal "exact C-51 phase: $($case.Operation)" $case.Phase $actual.phase
    Assert-Equal "operation preserved exactly: $($case.Operation)" $case.Operation $actual.operation
    $repeat = Resolve-DiagnosticPhaseOperation -Operation $case.Operation
    Assert-Equal "deterministic repeated phase: $($case.Operation)" $actual.phase $repeat.phase
    Assert-Equal "deterministic repeated operation: $($case.Operation)" $actual.operation $repeat.operation
}

Assert-Rejected 'null operation rejected' { Resolve-DiagnosticPhaseOperation -Operation $null }
Assert-Rejected 'empty operation rejected' { Resolve-DiagnosticPhaseOperation -Operation '' }
Assert-Rejected 'unknown operation token rejected' { Resolve-DiagnosticPhaseOperation -Operation 'made_up_operation' }
Assert-Rejected 'case variant rejected' { Resolve-DiagnosticPhaseOperation -Operation 'Enumerate_entries' }
Assert-Rejected 'non-string operation rejected' { Resolve-DiagnosticPhaseOperation -Operation 42 }
Assert-Rejected 'collection operation rejected' { Resolve-DiagnosticPhaseOperation -Operation @('enumerate_entries') }
Assert-Rejected 'exception text rejected as operation' { Resolve-DiagnosticPhaseOperation -Operation 'Access denied at C:\private\secret.txt' }

Write-Host "C-51 resolver tests: $($script:Passed) passed; $($script:Failed) failed."
if ($script:Failed -gt 0) { throw 'C-51 resolver tests failed.' }
