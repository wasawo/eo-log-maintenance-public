#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/DriveResponseSemantics.ps1')

$script:Passed = 0
$script:Failed = 0
$script:EffectCalls = 0
$requestId = 'abcdefab-2222-4333-8444-555555555555'

function Assert-True([string] $Name, [bool] $Condition) {
    if ($Condition) { $script:Passed++; Write-Host "PASS: $Name" }
    else { $script:Failed++; Write-Host "FAIL: $Name" }
}

function New-SuccessResponse([string] $Operation = 'list_files') {
    return @{
        schema_version = '1.0'; request_id = $requestId; operation = $Operation
        success = $true; result = @{ synthetic = 'synthetic_private_detail' }; error = $null
    }
}

function New-FailureResponse([string] $Code = 'DRIVE_TRANSIENT_FAILURE', [bool] $Retryable = $true) {
    $value = New-SuccessResponse
    $value.success = $false
    $value.result = $null
    $value.error = @{ code = $Code; message = 'synthetic_private_detail'; retryable = $Retryable }
    return $value
}

function Invoke-Case {
    param(
        [string] $Name, [AllowNull()] [object] $Response, [AllowNull()] [object] $ExitCode,
        [string] $ExpectedReason = 'correlation_exit_mapping_consistent',
        [AllowNull()] [object] $Id = $requestId, [AllowNull()] [object] $Operation = 'list_files'
    )
    $before = ConvertTo-Json -InputObject $Response -Depth 20 -Compress
    $results = @(Test-DriveResponseSemantics -ExpectedRequestId $Id -ExpectedOperation $Operation -Response $Response -ExitCode $ExitCode)
    $expectedStatus = if ($ExpectedReason -ceq 'correlation_exit_mapping_consistent') { 'consistent' } else { 'rejected' }
    $valid = $results.Count -eq 1
    if ($valid) {
        $result = $results[0]
        $keys = @($result.PSObject.Properties.Name | Sort-Object)
        $valid = ($result.Status -ceq $expectedStatus -and $result.ReasonCode -ceq $ExpectedReason -and
            ($keys -join ',') -ceq 'ReasonCode,Status' -and
            (ConvertTo-Json $result -Compress) -notmatch 'synthetic_private_detail|abcdefab|list_files')
    }
    $valid = $valid -and $before -ceq (ConvertTo-Json -InputObject $Response -Depth 20 -Compress)
    Assert-True $Name $valid
}

# Any attempt to execute these operational commands during a value check fails
# a positive case and records the attempt even if the helper catches the error.
foreach ($effectCommand in @('Start-Process', 'Start-Sleep', 'Invoke-WebRequest', 'Invoke-RestMethod',
                              'Get-Content', 'Set-Content', 'New-Item', 'Remove-Item')) {
    Set-Item -Path "Function:local:$effectCommand" -Value { $script:EffectCalls++; throw 'unexpected_effect' }
}

foreach ($operation in @('list_files', 'get_file_metadata', 'upload_file', 'download_file')) {
    Invoke-Case 'matched operation success' (New-SuccessResponse $operation) 0 -Operation $operation
}

# Independent contract table, not imported from the implementation.
$mapping = @(
    @(2, 'INVALID_REQUEST', $false), @(3, 'AUTHENTICATION_FAILED', $false), @(4, 'DRIVE_PERMISSION_DENIED', $false),
    @(5, 'DRIVE_RESOURCE_NOT_FOUND', $false), @(6, 'DRIVE_TRANSIENT_FAILURE', $true), @(7, 'VERIFICATION_FAILED', $false),
    @(8, 'INTERNAL_ERROR', $false), @(9, 'OPERATION_TIMEOUT', $false), @(10, 'CONFLICT_OR_AMBIGUOUS', $false)
)
for ($index = 0; $index -lt $mapping.Count; $index++) {
    $pair = $mapping[$index]
    foreach ($operation in @('list_files', 'get_file_metadata', 'upload_file', 'download_file')) {
        $response = New-FailureResponse $pair[1] $pair[2]
        $response.operation = $operation
        Invoke-Case "approved retryable value for $($pair[1]) / $operation" $response $pair[0] -Operation $operation
        $response.error.retryable = -not $pair[2]
        Invoke-Case "contradictory retryable value for $($pair[1]) / $operation" $response $pair[0] 'retryable_error_code_mismatch' -Operation $operation
    }
    $wrongExit = $mapping[($index + 1) % $mapping.Count][0]
    Invoke-Case 'wrong exit and known error code rejected' (New-FailureResponse $pair[1] $pair[2]) $wrongExit 'exit_error_code_mismatch'
}

$response = New-SuccessResponse
$response.request_id = $requestId.ToUpperInvariant()
Invoke-Case 'UUID case difference is not normalized' $response 0 'request_id_mismatch'
$response = New-SuccessResponse
$response.request_id = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
Invoke-Case 'different request ID rejected' $response 0 'request_id_mismatch'
$response = New-SuccessResponse 'upload_file'
Invoke-Case 'different allowed operation rejected' $response 0 'operation_mismatch'
foreach ($operation in @('LIST_FILES', 'delete_file', '', $null, 1)) {
    $response = New-SuccessResponse
    $response.operation = $operation
    Invoke-Case 'unknown or wrong typed response operation rejected' $response 0 'response_operation_invalid'
}
foreach ($character in @([char]0, [char]173, [char]8203)) {
    $operation = 'list_' + $character + 'files'
    $response = New-SuccessResponse $operation
    Invoke-Case 'same altered operation on both sides is outside ordinal allowlist' $response 0 'expected_operation_invalid' -Operation $operation
    Invoke-Case 'altered response operation is outside ordinal allowlist' $response 0 'response_operation_invalid'
    $response = New-FailureResponse
    $response.error.code = 'DRIVE_TRANSIENT_' + $character + 'FAILURE'
    Invoke-Case 'altered error code is outside ordinal allowlist' $response 6 'error_code_unknown'
}
foreach ($version in @('2.0', '1.0 ', 1, [double]1.0, $null)) {
    $response = New-SuccessResponse
    $response.schema_version = $version
    Invoke-Case 'unknown or wrong typed version rejected' $response 0 'schema_version_unsupported'
}
foreach ($id in @($null, 1, [guid]$requestId, @())) {
    $response = New-SuccessResponse
    $response.request_id = $id
    Invoke-Case 'response ID is not coerced' $response 0 'response_request_id_type_invalid'
}
foreach ($id in @($null, '', [guid]$requestId, 1)) {
    Invoke-Case 'expected ID is not coerced' (New-SuccessResponse) 0 'expected_request_id_invalid' -Id $id
}
foreach ($operation in @($null, 'LIST_FILES', 'delete_file', 1)) {
    Invoke-Case 'expected operation validated' (New-SuccessResponse) 0 'expected_operation_invalid' -Operation $operation
}
foreach ($exitCode in @($null, $true, $false, [double]0.0, '0')) {
    Invoke-Case 'exit type is not coerced' (New-SuccessResponse) $exitCode 'exit_code_type_invalid'
}
foreach ($exitCode in @(-1, 1, 11, [bigint]::Parse('100000000000000000000000000000000000001'))) {
    Invoke-Case 'unknown integer exit rejected without arbitrary integer ceiling' (New-SuccessResponse) $exitCode 'exit_code_unknown'
}
Invoke-Case 'BigInteger zero exit accepted' (New-SuccessResponse) ([bigint]0)
foreach ($response in @($null, 'synthetic_private_detail', 1, [pscustomobject]@{})) {
    Invoke-Case 'non-dictionary response rejected' $response 0 'response_object_required'
}
foreach ($field in @('schema_version', 'request_id', 'operation', 'success', 'result', 'error')) {
    $response = New-SuccessResponse
    $response.Remove($field)
    Invoke-Case 'missing envelope field rejected' $response 0 'response_fields_missing'
}
foreach ($success in @($null, 'true', 0, 1)) {
    $response = New-SuccessResponse
    $response.success = $success
    Invoke-Case 'success must be boolean' $response 0 'success_type_invalid'
}
Invoke-Case 'failure cannot use zero exit' (New-FailureResponse) 0 'exit_envelope_mismatch'
Invoke-Case 'success cannot use error exit' (New-SuccessResponse) 6 'exit_envelope_mismatch'
foreach ($result in @($null, 'synthetic_private_detail', @(), 1)) {
    $response = New-SuccessResponse
    $response.result = $result
    Invoke-Case 'successful result must be object' $response 0 'exit_envelope_mismatch'
}
$response = New-SuccessResponse
$response.error = @{}
Invoke-Case 'successful error must be null' $response 0 'exit_envelope_mismatch'
$response = New-FailureResponse
$response.result = @{}
Invoke-Case 'failure result must be null' $response 6 'exit_envelope_mismatch'
foreach ($errorValue in @($null, 'synthetic_private_detail', @(), 1)) {
    $response = New-FailureResponse
    $response.error = $errorValue
    Invoke-Case 'failure error must be object' $response 6 'error_object_required'
}
foreach ($field in @('code', 'message', 'retryable')) {
    $response = New-FailureResponse
    $response.error.Remove($field)
    Invoke-Case 'missing error field rejected' $response 6 'error_fields_missing'
}
foreach ($code in @('drive_transient_failure', 'SYNTHETIC_UNKNOWN', $null, 6)) {
    $response = New-FailureResponse
    $response.error.code = $code
    Invoke-Case 'unknown case or type error code rejected' $response 6 'error_code_unknown'
}
foreach ($flag in @($null, 'false', 0, 1)) {
    $response = New-FailureResponse
    $response.error.retryable = $flag
    Invoke-Case 'retryable must be boolean without coercion' $response 6 'retryable_type_invalid'
}
$response = New-FailureResponse
$response.error.message = @{ secret = 'synthetic_private_detail' }
Invoke-Case 'message object rejected without echo' $response 6 'error_message_type_invalid'

$json = '{"schema_version":"1.0","request_id":"abcdefab-2222-4333-8444-555555555555","operation":"list_files","success":true,"result":{},"error":null,"exit_code":0}'
$decoded = ConvertFrom-Json -InputObject $json -AsHashtable
$rawExit = $decoded.exit_code
$decoded.Remove('exit_code')
Assert-True 'raw JSON integer decoded as long' ($rawExit -is [long])
Invoke-Case 'raw JSON long exit accepted' $decoded $rawExit
$missing = Test-DriveResponseSemantics
Assert-True 'missing arguments return fixed rejection without prompt' ($missing.Status -ceq 'rejected' -and $missing.ReasonCode -ceq 'expected_request_id_invalid')
Assert-True 'no operational effect command called including true retryable cases' ($script:EffectCalls -eq 0)

function Invoke-RetryCase {
    param($Response, $ExitCode, $Attempt, [string] $Operation, [string] $Status,
        [string] $Reason, $Next = $null, $Delay = $null)
    $before = ConvertTo-Json -InputObject $Response -Depth 20 -Compress
    $results = @(Get-DriveRetryObservation -ExpectedRequestId $requestId -ExpectedOperation $Operation `
        -Response $Response -ExitCode $ExitCode -AttemptNumber $Attempt)
    $valid = $results.Count -eq 1
    if ($valid) {
        $result = $results[0]
        $valid = $result.Status -ceq $Status -and $result.ReasonCode -ceq $Reason -and
            $result.NextAttemptNumber -eq $Next -and $result.DelaySeconds -eq $Delay -and
            $result.MayRetry -is [bool] -and $result.MayRetry -eq $false -and
            (($result.PSObject.Properties.Name | Sort-Object) -join ',') -ceq
                'AttemptNumber,DelaySeconds,MayRetry,NextAttemptNumber,ReasonCode,Status' -and
            (ConvertTo-Json $result -Compress) -notmatch 'synthetic_private_detail|abcdefab|upload_file'
        if ($Status -cne 'rejected') { $valid = $valid -and $result.AttemptNumber -eq $Attempt }
    }
    $valid = $valid -and $before -ceq (ConvertTo-Json -InputObject $Response -Depth 20 -Compress)
    # Keep passing matrix rows quiet; print concrete failures only.
    if ($valid) { $script:Passed++ }
    else { $script:Failed++; Write-Host "FAIL: retry matrix $Operation / $Attempt / $ExitCode / $Reason" }
}

foreach ($operation in @('list_files', 'get_file_metadata', 'upload_file', 'download_file')) {
    foreach ($attempt in 1..4) {
        Invoke-RetryCase (New-SuccessResponse $operation) 0 $attempt $operation 'no_retry' 'retry_response_success_requires_validation'
        foreach ($pair in $mapping) {
            $response = New-FailureResponse $pair[1] $pair[2]
            $response.operation = $operation
            $next = $null; $delay = $null
            if ($pair[0] -eq 9) {
                $status = 'reconciliation_required'; $reason = 'retry_timeout_outcome_unknown'
            } elseif ($pair[0] -ne 6) {
                $status = 'no_retry'; $reason = 'retry_error_not_transient'
            } elseif ($operation -ceq 'upload_file') {
                $status = 'reconciliation_required'; $reason = 'retry_upload_outcome_unverified'
            } elseif ($attempt -eq 4) {
                $status = 'exhausted'; $reason = 'retry_attempt_limit_reached'
            } else {
                $status = 'candidate'; $next = $attempt + 1; $delay = @(60, 300, 900)[$attempt - 1]
                $reason = if ($operation -ceq 'download_file') { 'retry_candidate_requires_fresh_staging' } else { 'retry_candidate_requires_runtime_evidence' }
            }
            Invoke-RetryCase $response $pair[0] $attempt $operation $status $reason $next $delay
            $response.error.retryable = -not $pair[2]
            Invoke-RetryCase $response $pair[0] $attempt $operation 'rejected' 'retry_response_invalid'
        }
    }
}
foreach ($invalid in @($null, $true, $false, '1', 1.0, 0, -1, 5, [bigint]::Pow(10, 40))) {
    Invoke-RetryCase (New-FailureResponse) 6 $invalid 'list_files' 'rejected' 'retry_attempt_invalid'
}
foreach ($attempt in @([long]1, [bigint]3)) {
    $delay = if ($attempt -eq 1) { 60 } else { 900 }
    Invoke-RetryCase (New-FailureResponse) 6 $attempt 'list_files' 'candidate' 'retry_candidate_requires_runtime_evidence' ($attempt + 1) $delay
}
$response = New-FailureResponse
$response.request_id = 'different'
Invoke-RetryCase $response 6 1 'list_files' 'rejected' 'retry_response_invalid'
Invoke-RetryCase $null 9 1 'upload_file' 'rejected' 'retry_response_invalid'
$missing = Get-DriveRetryObservation
Assert-True 'missing retry arguments reject without prompt' ($missing.ReasonCode -ceq 'retry_attempt_invalid')
Assert-True 'retry observation never invokes process/file/network/sleep commands' ($script:EffectCalls -eq 0)

Write-Host "Drive correlation/exit/retry observation: $script:Passed passed; $script:Failed failed."
if ($script:Failed -gt 0) { exit 1 }
