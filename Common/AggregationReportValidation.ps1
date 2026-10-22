#requires -Version 7.6.7
Set-StrictMode -Version Latest

function Test-AggregationReportInternalConsistency {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [System.Collections.IDictionary] $Report
    )

    $issues = [System.Collections.Generic.List[string]]::new()
    $requiredRoot = @(
        'report_schema_version', 'run_id', 'pc_id', 'log_type',
        'manifest_ref', 'evidence_ref', 'inventory_ref',
        'run_aggregation', 'periods', 'run_scope_errors'
    )
    foreach ($field in $requiredRoot) {
        if (-not $Report.Contains($field)) {
            $issues.Add("missing_root_field:$field")
        }
    }
    if ($issues.Count -gt 0) { return @($issues) }

    if ($Report.report_schema_version -isnot [int] -or $Report.report_schema_version -ne 1) {
        $issues.Add('unsupported_report_schema_version')
    }
    if ([string]::IsNullOrWhiteSpace([string]$Report.run_id) -or
        [string]$Report.run_id -match '[\\/\x00-\x1f]') {
        $issues.Add('invalid_run_id')
    }
    if (@('PC-A', 'PC-B') -notcontains [string]$Report.pc_id) {
        $issues.Add('invalid_pc_id')
    }
    if (@('BattleLog', 'ErrorReport') -notcontains [string]$Report.log_type) {
        $issues.Add('invalid_log_type')
    }

    foreach ($refName in @('manifest_ref', 'evidence_ref')) {
        $ref = $Report[$refName]
        if ($ref -isnot [System.Collections.IDictionary]) {
            $issues.Add("invalid_ref:$refName")
            continue
        }
        foreach ($field in @('path', 'schema_version', 'sha256')) {
            if (-not $ref.Contains($field)) { $issues.Add("missing_ref_field:$refName.$field") }
        }
        if (-not $ref.Contains('path') -or -not $ref.Contains('schema_version') -or -not $ref.Contains('sha256')) { continue }
        $path = [string]$ref.path
        if ([string]::IsNullOrWhiteSpace($path) -or $path.StartsWith('/') -or
            $path.Contains('\') -or $path -match '^[A-Za-z]:' -or
            @($path -split '/').Where({ $_ -in @('', '.', '..') }).Count -gt 0) {
            $issues.Add("unsafe_relative_path:$refName")
        }
        if ($ref.schema_version -isnot [int] -or $ref.schema_version -ne 1) {
            $issues.Add("unsupported_ref_schema_version:$refName")
        }
        if ([string]$ref.sha256 -cnotmatch '^[0-9a-f]{64}$') {
            $issues.Add("invalid_sha256:$refName")
        }
    }

    $aggregation = $Report.run_aggregation
    if ($aggregation -isnot [System.Collections.IDictionary]) {
        $issues.Add('invalid_run_aggregation')
        return @($issues)
    }
    foreach ($field in @('verified_count', 'failed_count', 'unknown_count', 'run_scope_error_count')) {
        if (-not $aggregation.Contains($field) -or $aggregation[$field] -isnot [int] -or $aggregation[$field] -lt 0) {
            $issues.Add("invalid_run_count:$field")
        }
    }
    if (-not $aggregation.Contains('status') -or @('success', 'partial_failure', 'failure') -cnotcontains [string]$aggregation.status) {
        $issues.Add('invalid_run_status')
    }
    if (-not $aggregation.Contains('outcome') -or
        ($null -ne $aggregation.outcome -and [string]$aggregation.outcome -cne 'no_work')) {
        $issues.Add('invalid_run_outcome')
    }
    if (-not $Report.periods -or $Report.periods -isnot [array]) {
        $issues.Add('invalid_periods')
    }
    else {
        $seenPeriods = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($period in $Report.periods) {
            if ($period -isnot [System.Collections.IDictionary] -or -not $period.Contains('period')) {
                $issues.Add('invalid_period_row')
                continue
            }
            $periodName = [string]$period.period
            if ($periodName -cnotmatch '^\d{4}-(0[1-9]|1[0-2])$') { $issues.Add("invalid_period:$periodName") }
            if (-not $seenPeriods.Add($periodName)) { $issues.Add("duplicate_period:$periodName") }
            if (@('complete', 'incomplete', 'indeterminate') -cnotcontains [string]$period.completion) {
                $issues.Add("invalid_period_completion:$periodName")
            }
            foreach ($field in @('eligible_count', 'verified_count', 'failed_count', 'unknown_count', 'relevant_error_count')) {
                if (-not $period.Contains($field) -or $period[$field] -isnot [int] -or $period[$field] -lt 0) {
                    $issues.Add("invalid_period_count:$periodName.$field")
                }
            }
            if ($period.completion -ceq 'complete' -and
                ($period.verified_count -ne $period.eligible_count -or
                 $period.failed_count -ne 0 -or $period.unknown_count -ne 0 -or
                 $period.relevant_error_count -ne 0)) {
                $issues.Add("complete_period_has_unverified_or_errors:$periodName")
            }
            if ($period.completion -ceq 'incomplete' -and
                ($period.failed_count + $period.unknown_count + $period.relevant_error_count -eq 0)) {
                $issues.Add("incomplete_period_without_known_failure:$periodName")
            }
        }
    }
    if ($Report.run_scope_errors -isnot [array]) {
        $issues.Add('invalid_run_scope_errors')
    }
    elseif ($aggregation.run_scope_error_count -ne $Report.run_scope_errors.Count) {
        $issues.Add('run_scope_error_count_mismatch')
    }

    if ($Report.inventory_ref -isnot [System.Collections.IDictionary] -or
        -not $Report.inventory_ref.Contains('eligible_target_count') -or
        $Report.inventory_ref.eligible_target_count -isnot [int] -or
        $Report.inventory_ref.eligible_target_count -lt 0) {
        $issues.Add('invalid_inventory_target_count')
    }
    elseif ($Report.periods -is [array] -and
        @($Report.periods | Where-Object { $_ -is [System.Collections.IDictionary] -and $_.Contains('eligible_count') } |
            Measure-Object -Property eligible_count -Sum).Sum -ne $Report.inventory_ref.eligible_target_count) {
        $issues.Add('period_inventory_count_mismatch')
    }

    $runVerified = 0; $runFailed = 0; $runUnknown = 0
    if ($Report.periods -is [array]) {
        foreach ($period in $Report.periods) {
            if ($period -is [System.Collections.IDictionary]) {
                if ($period.verified_count -is [int]) { $runVerified += $period.verified_count }
                if ($period.failed_count -is [int]) { $runFailed += $period.failed_count }
                if ($period.unknown_count -is [int]) { $runUnknown += $period.unknown_count }
            }
        }
    }
    if ($aggregation.verified_count -is [int] -and $aggregation.verified_count -ne $runVerified) {
        $issues.Add('run_verified_count_mismatch')
    }
    if ($aggregation.failed_count -is [int] -and $aggregation.failed_count -ne $runFailed) {
        $issues.Add('run_failed_count_mismatch')
    }
    if ($aggregation.unknown_count -is [int] -and $aggregation.unknown_count -ne $runUnknown) {
        $issues.Add('run_unknown_count_mismatch')
    }

    if ($aggregation.status -ceq 'success' -and
        ($aggregation.failed_count -ne 0 -or $aggregation.unknown_count -ne 0 -or
         $aggregation.run_scope_error_count -ne 0 -or $aggregation.enumeration_complete -ne $true -or
         $aggregation.validation_complete -ne $true)) {
        $issues.Add('success_status_inconsistent')
    }
    if ($aggregation.outcome -ceq 'no_work' -and
        ($Report.inventory_ref.eligible_target_count -ne 0 -or $aggregation.status -cne 'success' -or
         $aggregation.enumeration_complete -ne $true -or $aggregation.validation_complete -ne $true)) {
        $issues.Add('no_work_outcome_inconsistent')
    }
    return @($issues)
}

