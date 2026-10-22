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
        if ($_.Exception.Message -ceq 'Diagnostic record rejected by schema-v1 finalizer.' -or
            $_.Exception.Message -ceq 'Diagnostic record serialization failed.') {
            $script:Passed++
            Write-Host "PASS: $Name"
        }
        else {
            $script:Failed++
            Write-Host "FAIL: $Name (unexpected error shape)"
        }
    }
}

$templates = [ordered]@{
    enumeration_failed       = 'Source enumeration failed.'
    invalid_filename         = 'Target filename does not satisfy the naming rules.'
    file_access_denied       = 'Access to the target entry was denied.'
    file_read_failed         = 'Target file content could not be read.'
    file_metadata_failed     = 'Required target metadata could not be read.'
    hash_failed              = 'Target content digest could not be computed.'
    source_mutation_detected = 'Source entry changed during inventory validation.'
    manifest_invalid         = 'Manifest validation failed.'
    evidence_invalid         = 'Run-input evidence validation failed.'
    validation_failed        = 'Input contract validation failed.'
    serialization_failed     = 'Report serialization failed.'
    aggregation_failed       = 'Aggregation failed.'
    publication_failed       = 'Report publication failed.'
    unknown_error            = 'An unclassified processing error occurred.'
}
$validPairs = @(
    @{ phase = 'enumeration'; operation = 'enumerate_entries' },
    @{ phase = 'classification'; operation = 'classify_target' },
    @{ phase = 'metadata'; operation = 'read_metadata' },
    @{ phase = 'content_read'; operation = 'read_content' },
    @{ phase = 'hashing'; operation = 'compute_hash' },
    @{ phase = 'metadata'; operation = 'detect_source_mutation' },
    @{ phase = 'manifest_validation'; operation = 'validate_manifest' },
    @{ phase = 'evidence_validation'; operation = 'validate_evidence' },
    @{ phase = 'evidence_finalization'; operation = 'finalize_evidence' },
    @{ phase = 'aggregation'; operation = 'aggregate_results' },
    @{ phase = 'report_serialization'; operation = 'serialize_report' },
    @{ phase = 'report_publication'; operation = 'publish_report' },
    @{ phase = 'unknown'; operation = 'unknown' }
)

function New-TestRecord {
    param(
        [string]$ErrorCode = 'enumeration_failed',
        [string]$Phase = 'enumeration',
        [string]$Operation = 'enumerate_entries',
        [AllowNull()][object]$Path = 'BattleLog/20260930_12345678@Example.txt',
        [AllowNull()][object]$Message
    )
    if ($PSBoundParameters.ContainsKey('Message')) {
        $resolvedMessage = $Message
    }
    else {
        $resolvedMessage = $templates[$ErrorCode]
    }
    return [ordered]@{
        schema_version       = 1
        error_id             = 'ERR-000001'
        error_code           = $ErrorCode
        phase                = $Phase
        operation            = $Operation
        target_relative_path = $Path
        message              = $resolvedMessage
    }
}

Assert-SupportedPowerShellVersion

# One valid record for every exact C-49 code and C-52 message template.
foreach ($code in $templates.Keys) {
    $record = New-TestRecord -ErrorCode $code
    $json = ConvertTo-FinalizedDiagnosticJson -Record $record
    $parsed = ConvertFrom-Json -InputObject $json -AsHashtable
    Assert-Equal "allowlisted error code and exact template: $code" $templates[$code] $parsed.message
    Assert-Equal "schema version emitted as integer: $code" '1' ([string]$parsed.schema_version)
}

# Every allowed phase/operation pair is accepted, and the full field set is retained.
foreach ($pair in $validPairs) {
    $record = New-TestRecord -Phase $pair.phase -Operation $pair.operation
    $parsed = ConvertFrom-Json -InputObject (ConvertTo-FinalizedDiagnosticJson -Record $record) -AsHashtable
    Assert-Equal "valid phase-operation pair: $($pair.phase)/$($pair.operation)" $pair.phase $parsed.phase
    Assert-Equal "valid operation preserved: $($pair.operation)" $pair.operation $parsed.operation
}

$valid = New-TestRecord
$json1 = ConvertTo-FinalizedDiagnosticJson -Record $valid
$json2 = ConvertTo-FinalizedDiagnosticJson -Record $valid
Assert-Equal 'serialization deterministic byte-for-byte' $json1 $json2
$originalCulture = [System.Globalization.CultureInfo]::CurrentCulture
try {
    [System.Globalization.CultureInfo]::CurrentCulture = [System.Globalization.CultureInfo]::GetCultureInfo('tr-TR')
    $cultureJson = ConvertTo-FinalizedDiagnosticJson -Record $valid
}
finally {
    [System.Globalization.CultureInfo]::CurrentCulture = $originalCulture
}
Assert-Equal 'serialization invariant across culture' $json1 $cultureJson
$parsedValid = ConvertFrom-Json -InputObject $json1 -AsHashtable
Assert-Equal 'event identity preserved' 'ERR-000001' $parsedValid.error_id
Assert-Equal 'classification preserved' 'enumeration_failed' $parsedValid.error_code
Assert-Equal 'all seven exact schema keys emitted' 7 $parsedValid.Count
Assert-Equal 'safe relative path emitted' 'BattleLog/20260930_12345678@Example.txt' $parsedValid.target_relative_path

# Unsafe optional paths become literal JSON null; identity and classification remain.
$unsafe = New-TestRecord -Path 'logs/../secret.txt'
$unsafeJson = ConvertTo-FinalizedDiagnosticJson -Record $unsafe
$unsafeParsed = ConvertFrom-Json -InputObject $unsafeJson -AsHashtable
Assert-Equal 'unsafe path becomes explicit JSON null' $null $unsafeParsed.target_relative_path
Assert-Equal 'unsafe path does not change event ID' 'ERR-000001' $unsafeParsed.error_id
Assert-Equal 'unsafe path does not change classification' 'enumeration_failed' $unsafeParsed.error_code
Assert-Equal 'unsafe input not disclosed in JSON' $false ($unsafeJson.Contains('secret.txt'))
$nullPath = New-TestRecord -Path $null
$nullParsed = ConvertFrom-Json -InputObject (ConvertTo-FinalizedDiagnosticJson -Record $nullPath) -AsHashtable
Assert-Equal 'missing optional path remains explicit JSON null' $null $nullParsed.target_relative_path

# C-47 selected path limit: 1024 Unicode scalar values; over-limit becomes null.
$path1024 = 'a' * 1024
$path1025 = 'a' * 1025
Assert-Equal '1024 scalar path accepted' $path1024 (ConvertTo-SafeDiagnosticRelativePath $path1024)
Assert-Equal '1025 scalar path rejected' $null (ConvertTo-SafeDiagnosticRelativePath $path1025)
$emoji = [string][char]::ConvertFromUtf32(0x1F600)
$scalar1024 = $emoji * 1024
$scalar1025 = $emoji * 1025
Assert-Equal '1024 supplementary Unicode scalars accepted' $scalar1024 (ConvertTo-SafeDiagnosticRelativePath $scalar1024)
Assert-Equal '1025 supplementary Unicode scalars rejected' $null (ConvertTo-SafeDiagnosticRelativePath $scalar1025)

# Schema, identity, enum, pair, template, and exact-field failures reject closed.
Assert-Throws 'null record rejected' { ConvertTo-FinalizedDiagnosticJson -Record $null }
Assert-Throws 'non-map record rejected' { ConvertTo-FinalizedDiagnosticJson -Record 'not a record' }
Assert-Throws 'unknown field rejected' {
    $r = New-TestRecord; $r['extra'] = 'unexpected'; ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'missing field rejected' {
    $r = New-TestRecord; $r.Remove('message'); ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'wrong-case field name rejected' {
    $r = [ordered]@{ Schema_Version = 1; error_id = 'ERR-000001'; error_code = 'enumeration_failed'; phase = 'enumeration'; operation = 'enumerate_entries'; target_relative_path = $null; message = $templates.enumeration_failed }
    ConvertTo-FinalizedDiagnosticJson -Record $r
}
foreach ($badVersion in @($null, '1', 1.5, 0, -1, 2, $true)) {
    Assert-Throws "invalid schema_version rejected: $badVersion" {
        $r = New-TestRecord; $r['schema_version'] = $badVersion; ConvertTo-FinalizedDiagnosticJson -Record $r
    }
}
foreach ($badId in @('ERR-1', 'err-000001', 'ERR-000001x', 'ERR-0000001', 'ERR-000000', '')) {
    Assert-Throws "invalid error_id rejected: $badId" {
        $r = New-TestRecord; $r['error_id'] = $badId; ConvertTo-FinalizedDiagnosticJson -Record $r
    }
}
foreach ($badCode in @('Enumeration_failed', 'not_known', '', $null)) {
    Assert-Throws "invalid error_code rejected: $badCode" {
        $r = New-TestRecord; $r['error_code'] = $badCode; ConvertTo-FinalizedDiagnosticJson -Record $r
    }
}
Assert-Throws 'invalid phase-operation pair rejected' {
    $r = New-TestRecord -Phase 'enumeration' -Operation 'read_content'; ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'phase aliases rejected' {
    $r = New-TestRecord -Phase 'Enumeration'; ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'message mismatch rejected' {
    $r = New-TestRecord -Message 'Raw exception: secret-value'; ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'null message rejected for known code' {
    $r = New-TestRecord -Message $null; ConvertTo-FinalizedDiagnosticJson -Record $r
}
Assert-Throws 'control character in message rejected' {
    $r = New-TestRecord -Message ([string]::Concat('Source enumeration failed.', [char]9)); ConvertTo-FinalizedDiagnosticJson -Record $r
}

if ($script:Failed -gt 0) {
    throw "$($script:Failed) diagnostic finalizer test(s) failed; $($script:Passed) passed."
}
Write-Host "Diagnostic finalizer tests passed: $($script:Passed)"
