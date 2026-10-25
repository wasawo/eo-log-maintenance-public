#requires -Version 7.6.7
Set-StrictMode -Version Latest

function Test-DriveResponseSemantics {
    <#
    .SYNOPSIS
    Checks in-memory correlation, exit/envelope mapping and retryable policy.
    .DESCRIPTION
    Response/result/error objects must be IDictionary values (for example,
    ConvertFrom-Json -AsHashtable). Expected identity comes from the caller's
    actual request. No parsing, UUID syntax/unknown-field schema validation,
    result-content verification,
    retry decision or transport is supplied. Only DRIVE_TRANSIENT_FAILURE may
    have retryable=true. Consistent grants no authority to retry an operation.
    #>
    [CmdletBinding()]
    param(
        [AllowNull()] [AllowEmptyString()] [object] $ExpectedRequestId,
        [AllowNull()] [AllowEmptyString()] [object] $ExpectedOperation,
        [AllowNull()] [object] $Response,
        [AllowNull()] [object] $ExitCode
    )

    # These scriptblocks emit fixed metadata only, never input values.
    $rejected = {
        param([string] $Reason)
        [pscustomobject]@{ Status = 'rejected'; ReasonCode = $Reason }
    }
    $hasFields = {
        param([System.Collections.IDictionary] $Value, [string[]] $Fields)
        foreach ($field in $Fields) {
            $found = $false
            foreach ($key in $Value.Keys) {
                if ($key -is [string] -and [string]::Equals($key, $field, [StringComparison]::Ordinal)) {
                    $found = $true
                    break
                }
            }
            if (-not $found) { return $false }
        }
        return $true
    }

    try {
        $operations = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($operation in @('list_files', 'get_file_metadata', 'upload_file', 'download_file')) {
            [void]$operations.Add($operation)
        }
        if ($ExpectedRequestId -isnot [string] -or $ExpectedRequestId.Length -eq 0) {
            return (& $rejected 'expected_request_id_invalid')
        }
        if ($ExpectedOperation -isnot [string] -or -not $operations.Contains($ExpectedOperation)) {
            return (& $rejected 'expected_operation_invalid')
        }
        if ($ExitCode -isnot [int] -and $ExitCode -isnot [long] -and $ExitCode -isnot [bigint]) {
            return (& $rejected 'exit_code_type_invalid')
        }
        $codeByExit = [ordered]@{
            2 = 'INVALID_REQUEST'
            3 = 'AUTHENTICATION_FAILED'
            4 = 'DRIVE_PERMISSION_DENIED'
            5 = 'DRIVE_RESOURCE_NOT_FOUND'
            6 = 'DRIVE_TRANSIENT_FAILURE'
            7 = 'VERIFICATION_FAILED'
            8 = 'INTERNAL_ERROR'
            9 = 'OPERATION_TIMEOUT'
            10 = 'CONFLICT_OR_AMBIGUOUS'
        }
        $knownErrorCodes = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($code in $codeByExit.Values) { [void]$knownErrorCodes.Add($code) }
        $expectedErrorCode = $null
        foreach ($entry in $codeByExit.GetEnumerator()) {
            if ([bigint]$ExitCode -eq [bigint]$entry.Key) {
                $expectedErrorCode = $entry.Value
                break
            }
        }
        if ([bigint]$ExitCode -ne [bigint]0 -and $null -eq $expectedErrorCode) {
            return (& $rejected 'exit_code_unknown')
        }
        if ($Response -isnot [System.Collections.IDictionary]) {
            return (& $rejected 'response_object_required')
        }
        if (-not (& $hasFields $Response @('schema_version', 'request_id', 'operation', 'success', 'result', 'error'))) {
            return (& $rejected 'response_fields_missing')
        }
        if ($Response.schema_version -isnot [string] -or
            -not [string]::Equals($Response.schema_version, '1.0', [StringComparison]::Ordinal)) {
            return (& $rejected 'schema_version_unsupported')
        }
        if ($Response.request_id -isnot [string]) {
            return (& $rejected 'response_request_id_type_invalid')
        }
        if (-not [string]::Equals($Response.request_id, $ExpectedRequestId, [StringComparison]::Ordinal)) {
            return (& $rejected 'request_id_mismatch')
        }
        if ($Response.operation -isnot [string] -or -not $operations.Contains($Response.operation)) {
            return (& $rejected 'response_operation_invalid')
        }
        if (-not [string]::Equals($Response.operation, $ExpectedOperation, [StringComparison]::Ordinal)) {
            return (& $rejected 'operation_mismatch')
        }
        if ($Response.success -isnot [bool]) {
            return (& $rejected 'success_type_invalid')
        }
        if ([bigint]$ExitCode -eq [bigint]0) {
            if ($Response.success -ne $true -or $null -ne $Response.error -or
                $Response.result -isnot [System.Collections.IDictionary]) {
                return (& $rejected 'exit_envelope_mismatch')
            }
        }
        else {
            if ($Response.success -ne $false -or $null -ne $Response.result) {
                return (& $rejected 'exit_envelope_mismatch')
            }
            if ($Response.error -isnot [System.Collections.IDictionary]) {
                return (& $rejected 'error_object_required')
            }
            if (-not (& $hasFields $Response.error @('code', 'message', 'retryable'))) {
                return (& $rejected 'error_fields_missing')
            }
            if ($Response.error.code -isnot [string] -or -not $knownErrorCodes.Contains($Response.error.code)) {
                return (& $rejected 'error_code_unknown')
            }
            if ($Response.error.message -isnot [string]) {
                return (& $rejected 'error_message_type_invalid')
            }
            if ($Response.error.retryable -isnot [bool]) {
                return (& $rejected 'retryable_type_invalid')
            }
            if (-not [string]::Equals($Response.error.code, $expectedErrorCode, [StringComparison]::Ordinal)) {
                return (& $rejected 'exit_error_code_mismatch')
            }
            $expectedRetryable = [string]::Equals($Response.error.code, 'DRIVE_TRANSIENT_FAILURE', [StringComparison]::Ordinal)
            if ($Response.error.retryable -ne $expectedRetryable) {
                return (& $rejected 'retryable_error_code_mismatch')
            }
        }
        return [pscustomobject]@{ Status = 'consistent'; ReasonCode = 'correlation_exit_mapping_consistent' }
    }
    catch {
        return (& $rejected 'response_value_invalid')
    }
}

function Get-DriveRetryObservation {
    <#
    .SYNOPSIS
    Observes the approved four-attempt budget without sending or sleeping.
    .DESCRIPTION
    AttemptNumber is the completed attempt, including the first (1..4).
    Candidate delays are minimum waits after that failure, not an authorization
    or a durable counter. Real response parsing/schema, request/counter binding,
    elapsed time, current execution conditions and operation-specific safety
    remain caller obligations. Upload uncertainty is never cleared by a bool.
    #>
    [CmdletBinding()]
    param(
        [AllowNull()] [AllowEmptyString()] [object] $ExpectedRequestId,
        [AllowNull()] [AllowEmptyString()] [object] $ExpectedOperation,
        [AllowNull()] [object] $Response,
        [AllowNull()] [object] $ExitCode,
        [AllowNull()] [object] $AttemptNumber
    )

    $makeResult = {
        param([string] $Status, [string] $Reason, $Attempt, $Next, $Delay)
        [pscustomobject]@{
            Status = $Status; ReasonCode = $Reason; AttemptNumber = $Attempt
            NextAttemptNumber = $Next; DelaySeconds = $Delay; MayRetry = $false
        }
    }
    try {
        if (($AttemptNumber -isnot [int] -and $AttemptNumber -isnot [long] -and $AttemptNumber -isnot [bigint]) -or
            $AttemptNumber -lt 1 -or $AttemptNumber -gt 4) {
            return (& $makeResult 'rejected' 'retry_attempt_invalid' $null $null $null)
        }
        $attempt = [int]$AttemptNumber
        $semantics = Test-DriveResponseSemantics -ExpectedRequestId $ExpectedRequestId `
            -ExpectedOperation $ExpectedOperation -Response $Response -ExitCode $ExitCode
        if ($semantics.Status -cne 'consistent') {
            return (& $makeResult 'rejected' 'retry_response_invalid' $attempt $null $null)
        }
        if ($Response.success) {
            return (& $makeResult 'no_retry' 'retry_response_success_requires_validation' $attempt $null $null)
        }
        if ($Response.error.code -ceq 'OPERATION_TIMEOUT') {
            return (& $makeResult 'reconciliation_required' 'retry_timeout_outcome_unknown' $attempt $null $null)
        }
        if ($Response.error.code -cne 'DRIVE_TRANSIENT_FAILURE') {
            return (& $makeResult 'no_retry' 'retry_error_not_transient' $attempt $null $null)
        }
        # A transient upload error does not establish whether creation happened.
        # No caller-provided "safe to resend" flag can bypass reconciliation.
        if ($ExpectedOperation -ceq 'upload_file') {
            return (& $makeResult 'reconciliation_required' 'retry_upload_outcome_unverified' $attempt $null $null)
        }
        if ($attempt -eq 4) {
            return (& $makeResult 'exhausted' 'retry_attempt_limit_reached' $attempt $null $null)
        }
        $delay = @(60, 300, 900)[$attempt - 1]
        $reason = if ($ExpectedOperation -ceq 'download_file') {
            'retry_candidate_requires_fresh_staging'
        } else {
            'retry_candidate_requires_runtime_evidence'
        }
        return (& $makeResult 'candidate' $reason $attempt ($attempt + 1) $delay)
    }
    catch {
        return (& $makeResult 'rejected' 'retry_input_invalid' $null $null $null)
    }
}
