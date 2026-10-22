#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')
$script:Passed = 0
$script:Failed = 0
function Assert-Equal {
    param([string]$Name,[object]$Expected,[object]$Actual)
    if ([object]::Equals($Expected,$Actual)) { $script:Passed++; Write-Host "PASS: $Name" }
    else { $script:Failed++; Write-Host "FAIL: $Name" }
}
function Assert-Rejected {
    param([string]$Name,[scriptblock]$Action)
    try { & $Action | Out-Null; $script:Failed++; Write-Host "FAIL: $Name (accepted)" }
    catch {
        if ($_.Exception.Message -ceq 'Diagnostic condition rejected by C-50 classifier.') { $script:Passed++; Write-Host "PASS: $Name" }
        else { $script:Failed++; Write-Host "FAIL: $Name (unexpected error shape)" }
    }
}
$cases = @(
    @{ Condition='manifest_readable_invalid'; Code='manifest_invalid' },
    @{ Condition='evidence_readable_invalid'; Code='evidence_invalid' },
    @{ Condition='source_mutation_observed'; Code='source_mutation_detected' },
    @{ Condition='target_filename_invalid'; Code='invalid_filename' },
    @{ Condition='access_denied_observed'; Code='file_access_denied' },
    @{ Condition='directory_enumeration_failed'; Code='enumeration_failed' },
    @{ Condition='target_metadata_failed'; Code='file_metadata_failed' },
    @{ Condition='target_content_read_failed'; Code='file_read_failed' },
    @{ Condition='content_digest_failed'; Code='hash_failed' },
    @{ Condition='general_contract_validation_failed'; Code='validation_failed' },
    @{ Condition='report_serialization_failed'; Code='serialization_failed' },
    @{ Condition='aggregation_failed'; Code='aggregation_failed' },
    @{ Condition='report_publication_failed'; Code='publication_failed' },
    @{ Condition='unmatched_failure'; Code='unknown_error' }
)
foreach ($case in $cases) { Assert-Equal "exact C-50 mapping: $($case.Condition)" $case.Code (Resolve-DiagnosticErrorCode -Condition $case.Condition) }
Assert-Rejected 'null condition rejected' { Resolve-DiagnosticErrorCode -Condition $null }
Assert-Rejected 'empty condition rejected' { Resolve-DiagnosticErrorCode -Condition '' }
Assert-Rejected 'unknown token rejected' { Resolve-DiagnosticErrorCode -Condition 'some_exception_message' }
Assert-Rejected 'case variant rejected' { Resolve-DiagnosticErrorCode -Condition 'Manifest_readable_invalid' }
Assert-Rejected 'non-string input rejected' { Resolve-DiagnosticErrorCode -Condition 5 }
Assert-Rejected 'collection input rejected' { Resolve-DiagnosticErrorCode -Condition @('manifest_readable_invalid') }
Assert-Rejected 'exception message cannot be used as a condition' { Resolve-DiagnosticErrorCode -Condition 'Access denied at C:\private\secret.txt' }
Write-Host "C-50 classifier tests: $($script:Passed) passed; $($script:Failed) failed."
if ($script:Failed -gt 0) { throw 'C-50 classifier tests failed.' }
