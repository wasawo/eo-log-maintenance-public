#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\AggregationReportValidation.ps1')

$script:Passed = 0
$script:Failed = 0
function Assert-True([string]$Name, [bool]$Condition) {
    if ($Condition) { $script:Passed++; Write-Host "PASS: $Name" }
    else { $script:Failed++; Write-Host "FAIL: $Name" -ForegroundColor Red }
}

function New-Report {
    return @{
        report_schema_version = 1
        run_id = '11111111-2222-4333-8444-555555555555'
        pc_id = 'PC-A'
        log_type = 'BattleLog'
        manifest_ref = @{ path = '_maintenance/manifests/PC-A/run.json'; schema_version = 1; sha256 = ('a' * 64) }
        evidence_ref = @{ path = '_maintenance/run-input-evidence/PC-A/run.json'; schema_version = 1; sha256 = ('b' * 64) }
        generated_at_utc = '2026-10-21T00:00:00Z'
        inventory_ref = @{ kind = 'b2_run_input_evidence_inventory'; eligible_target_count = 2; inventory_sha256 = ('c' * 64) }
        run_aggregation = @{
            status = 'partial_failure'; outcome = $null
            verified_count = 1; failed_count = 1; unknown_count = 0; run_scope_error_count = 0
            enumeration_complete = $true; validation_complete = $true
        }
        periods = @(@{
            period = '2026-09'; completion = 'incomplete'; eligible_count = 2
            verified_count = 1; failed_count = 1; unknown_count = 0; relevant_error_count = 0
        })
        run_scope_errors = @()
    }
}

$valid = New-Report
Assert-True 'valid synthetic report accepted' (@((Test-AggregationReportInternalConsistency -Report $valid)).Count -eq 0)

$duplicate = New-Report
$duplicate.periods = @($duplicate.periods[0], $duplicate.periods[0])
Assert-True 'duplicate period rejected' ((Test-AggregationReportInternalConsistency -Report $duplicate) -contains 'duplicate_period:2026-09')

$unsafe = New-Report
$unsafe.manifest_ref.path = '../outside.json'
Assert-True 'parent traversal reference rejected' ((Test-AggregationReportInternalConsistency -Report $unsafe) -contains 'unsafe_relative_path:manifest_ref')

$hashCase = New-Report
$hashCase.evidence_ref.sha256 = ('A' * 64)
Assert-True 'uppercase digest rejected' ((Test-AggregationReportInternalConsistency -Report $hashCase) -contains 'invalid_sha256:evidence_ref')

$complete = New-Report
$complete.run_aggregation.status = 'success'
$complete.run_aggregation.failed_count = 0
$complete.periods[0].completion = 'complete'
$complete.periods[0].failed_count = 0
$complete.periods[0].verified_count = 2
$complete.run_aggregation.verified_count = 1
$complete.inventory_ref.eligible_target_count = 2
Assert-True 'complete period with unverified count rejected when arithmetic mismatches' ((Test-AggregationReportInternalConsistency -Report $complete) -contains 'run_verified_count_mismatch')

$noWork = New-Report
$noWork.run_aggregation.outcome = 'no_work'
Assert-True 'no_work with eligible targets rejected' ((Test-AggregationReportInternalConsistency -Report $noWork) -contains 'no_work_outcome_inconsistent')

Write-Host "Aggregation report internal validator: $script:Passed passed; $script:Failed failed."
if ($script:Failed -gt 0) { exit 1 }
