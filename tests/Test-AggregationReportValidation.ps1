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

$empty = New-Report
$empty.periods = @()
$empty.inventory_ref.eligible_target_count = 0
$empty.run_aggregation.status = 'success'
$empty.run_aggregation.outcome = 'no_work'
$empty.run_aggregation.verified_count = 0
$empty.run_aggregation.failed_count = 0
Assert-True 'zero-work empty periods accepted' (@(Test-AggregationReportInternalConsistency -Report $empty).Count -eq 0)
foreach ($invalidPeriods in @($null, 'invalid', @{ period = '2026-09' })) {
    $invalid = New-Report
    $invalid.periods = $invalidPeriods
    Assert-True 'null or non-array periods rejected' ((Test-AggregationReportInternalConsistency -Report $invalid) -contains 'invalid_periods')
}

# Pass actual pure-builder output through this independent PowerShell validator.
$builderProbe = @'
import json, sys
sys.path.insert(0, 'tests')
from test_aggregation_report_builder import fixture, build, error
reports = []
for outcomes, options in [
    ((), {}), (((8, 'verified'), (9, 'unknown')), {}),
    (((9, 'verified'),), {'errors': [error()]}),
    (((9, 'verified'),), {'enumeration': 'failed'}),
    (((9, 'verified'),), {'errors': [error()], 'validation': 'incomplete'}),
]:
    m, e = fixture(outcomes, **options)
    reports.append(json.loads(build(m, e)))
print(json.dumps(reports))
'@
Push-Location (Join-Path $PSScriptRoot '..')
try {
    $builderOutput = $builderProbe | & python -B -
    if ($LASTEXITCODE -ne 0) { throw 'synthetic_builder_fixture_failed' }
    $builderReports = ConvertFrom-Json -InputObject ($builderOutput -join "`n") -AsHashtable -NoEnumerate
    foreach ($builderReport in $builderReports) {
        $builderIssues = @(Test-AggregationReportInternalConsistency -Report $builderReport)
        if ($builderIssues.Count -gt 0) { Write-Host ('Builder fixture issues: ' + ($builderIssues -join ',')) }
        Assert-True 'pure builder output internally consistent' ($builderIssues.Count -eq 0)
    }
}
finally { Pop-Location }

$jsonIntegers = New-Report | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable
Assert-True 'raw JSON long integers accepted' (@(Test-AggregationReportInternalConsistency -Report $jsonIntegers).Count -eq 0)

$largeCount = [bigint]::Parse('100000000000000000000000000000000000001')
$large = New-Report
$large.inventory_ref.eligible_target_count = $largeCount + [bigint]1
$large.run_aggregation.verified_count = $largeCount
$large.periods[0].eligible_count = $largeCount + [bigint]1
$large.periods[0].verified_count = $largeCount
Assert-True 'BigInteger counts aggregate exactly' (@(Test-AggregationReportInternalConsistency -Report $large).Count -eq 0)
foreach ($delta in @([bigint](-1), [bigint]1)) {
    $large.run_aggregation.verified_count = $largeCount + $delta
    Assert-True 'BigInteger run count one-unit mismatch rejected' ((Test-AggregationReportInternalConsistency -Report $large) -contains 'run_verified_count_mismatch')
    $large.run_aggregation.verified_count = $largeCount
    $large.inventory_ref.eligible_target_count = $largeCount + [bigint]1 + $delta
    Assert-True 'BigInteger inventory one-unit mismatch rejected' ((Test-AggregationReportInternalConsistency -Report $large) -contains 'period_inventory_count_mismatch')
    $large.inventory_ref.eligible_target_count = $largeCount + [bigint]1
}

foreach ($notInteger in @($true, [double]1.0, '1')) {
    $invalid = New-Report
    $invalid.run_aggregation.verified_count = $notInteger
    Assert-True 'bool double string run count rejected' ((Test-AggregationReportInternalConsistency -Report $invalid) -contains 'invalid_run_count:verified_count')
    $invalid = New-Report
    $invalid.report_schema_version = $notInteger
    Assert-True 'bool double string version rejected' ((Test-AggregationReportInternalConsistency -Report $invalid) -contains 'unsupported_report_schema_version')
    $invalid = New-Report
    $invalid.periods[0].verified_count = $notInteger
    Assert-True 'bool double string period count rejected' ((Test-AggregationReportInternalConsistency -Report $invalid) -contains 'invalid_period_count:2026-09.verified_count')
    $invalid = New-Report
    $invalid.inventory_ref.eligible_target_count = $notInteger
    Assert-True 'bool double string inventory count rejected' ((Test-AggregationReportInternalConsistency -Report $invalid) -contains 'invalid_inventory_target_count')
}

Write-Host "Aggregation report internal validator: $script:Passed passed; $script:Failed failed."
if ($script:Failed -gt 0) { exit 1 }
