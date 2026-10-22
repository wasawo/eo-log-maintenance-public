Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-SupportedPowerShellVersion {
    [CmdletBinding()]
    param(
        [Parameter()]
        [AllowNull()]
        [object]$Version
    )

    if (-not $PSBoundParameters.ContainsKey('Version')) {
        try {
            $Version = $PSVersionTable.PSVersion
        }
        catch {
            throw 'Unable to determine the running PowerShell version. Required version: 7.6.7.'
        }
    }

    if ($null -eq $Version) {
        throw 'Unable to determine the running PowerShell version. Required version: 7.6.7.'
    }

    try {
        $actualVersion = [version]$Version
    }
    catch {
        throw "Unable to parse the running PowerShell version '$Version'. Required version: 7.6.7."
    }

    $requiredVersion = [version]'7.6.7'
    if ($actualVersion -ne $requiredVersion) {
        throw "Unsupported PowerShell version '$actualVersion'. Exactly PowerShell 7.6.7 is required."
    }
}

# Fail closed before defining or invoking any log-processing function.
Assert-SupportedPowerShellVersion

function Get-LogFileDate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('BattleLog', 'ErrorReport')]
        [string]$LogType,

        [Parameter(Mandatory)]
        [string]$FileName
    )

    $pattern = switch ($LogType) {
        'BattleLog' {
            '^(?<Date>\d{8})_\d{8}@.+\.txt$'
        }
        'ErrorReport' {
            '^(?<Date>\d{8})_\d{8}\.txt$'
        }
    }

    if ($FileName -cnotmatch $pattern) {
        throw "Unexpected $LogType filename: $FileName"
    }

    $dateText = $Matches['Date']
    $parsedDate = [datetime]::MinValue

    $valid = [datetime]::TryParseExact(
        $dateText,
        'yyyyMMdd',
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::None,
        [ref]$parsedDate
    )

    if (-not $valid) {
        throw "Invalid date in filename: $FileName"
    }

    return $parsedDate.Date
}

function Get-LogSyncCutoffDate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('BattleLog', 'ErrorReport')]
        [string]$LogType,

        [datetime]$ReferenceDate = (Get-Date).Date
    )

    $today = $ReferenceDate.Date

    switch ($LogType) {
        'BattleLog' {
            return [datetime]::new($today.Year, $today.Month, 1).AddDays(-1)
        }
        'ErrorReport' {
            return [datetime]::new($today.Year - 1, 12, 31)
        }
    }
}

function Get-LogArchiveCutoffDate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('BattleLog', 'ErrorReport')]
        [string]$LogType,

        [datetime]$ReferenceDate = (Get-Date).Date
    )

    $today = $ReferenceDate.Date

    switch ($LogType) {
        'BattleLog' {
            return [datetime]::new($today.Year - 1, 12, 31)
        }
        'ErrorReport' {
            return [datetime]::new($today.Year - 2, 12, 31)
        }
    }
}

function Test-LogFileEligible {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('BattleLog', 'ErrorReport')]
        [string]$LogType,

        [Parameter(Mandatory)]
        [string]$FileName,

        [Parameter(Mandatory)]
        [ValidateSet('Sync', 'Archive')]
        [string]$Operation,

        [datetime]$ReferenceDate = (Get-Date).Date
    )

    $fileDate = Get-LogFileDate -LogType $LogType -FileName $FileName

    $cutoff = if ($Operation -eq 'Sync') {
        Get-LogSyncCutoffDate -LogType $LogType -ReferenceDate $ReferenceDate
    }
    else {
        Get-LogArchiveCutoffDate -LogType $LogType -ReferenceDate $ReferenceDate
    }

    return ($fileDate -le $cutoff)
}

function ConvertTo-SafeDiagnosticRelativePath {
    [CmdletBinding()]
    param(
        [Parameter()]
        [AllowNull()]
        [object]$Path
    )

    # Optional diagnostic paths fail closed. Never include rejected input in an error.
    if ($null -eq $Path -or $Path -isnot [string] -or $Path.Length -eq 0) {
        return $null
    }

    # Reject unpaired UTF-16 surrogates; valid surrogate pairs represent Unicode scalars.
    $invalidSurrogatePattern = '[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'
    if ([regex]::IsMatch($Path, $invalidSurrogatePattern)) {
        return $null
    }

    # C-53 permits separator-direction canonicalization only. Do not repair other syntax.
    $candidate = $Path.Replace('\', '/')
    if (
        $candidate.Length -eq 0 -or
        $candidate.StartsWith('/', [StringComparison]::Ordinal) -or
        $candidate -match '^[A-Za-z]:' -or
        $candidate.Contains(':')
    ) {
        return $null
    }

    foreach ($character in $candidate.ToCharArray()) {
        if ([char]::IsControl($character)) {
            return $null
        }
    }

    $segments = $candidate.Split([char[]]@('/'))
    # C-47 approved maximum: 1024 Unicode scalar values after separator normalization.
    # Valid surrogate pairs count as one scalar; unpaired surrogates were rejected above.
    $scalarCount = 0
    for ($index = 0; $index -lt $candidate.Length; $index++) {
        $current = [int][char]$candidate[$index]
        if ($current -ge 0xD800 -and $current -le 0xDBFF) {
            # The paired low surrogate is guaranteed by the validation above.
            $index++
        }
        $scalarCount++
        if ($scalarCount -gt 1024) {
            return $null
        }
    }

    foreach ($segment in $segments) {
        if ($segment.Length -eq 0 -or $segment -ceq '.' -or $segment -ceq '..') {
            return $null
        }
    }

    $fixedSensitiveNames = @(
        '.env', '.npmrc', '.pypirc', '.netrc', '.dockerconfigjson',
        '.aws', '.ssh', '.gnupg', 'secrets', 'secret', 'credentials', 'credential'
    )
    $sensitiveTokensPattern = '(?<![A-Za-z0-9])(?:[tT][oO][kK][eE][nN]|[pP][aA][sS][sS][wW][oO][rR][dD]|[pP][aA][sS][sS][wW][dD]|[sS][eE][cC][rR][eE][tT][sS]?|[cC][rR][eE][dD][eE][nN][tT][iI][aA][lL][sS]?|[aA][pP][iI][kK][eE][yY]|[aA][pP][iI]-[kK][eE][yY]|[pP][rR][iI][vV][aA][tT][eE]-[kK][eE][yY]|[aA][cC][cC][eE][sS][sS]-[kK][eE][yY]|[cC][lL][iI][eE][nN][tT]-[sS][eE][cC][rR][eE][tT]|[aA][uU][tT][hH][oO][rR][iI][zZ][aA][tT][iI][oO][nN]|[bB][eE][aA][rR][eE][rR])(?![A-Za-z0-9])'

    # These expressions are the exact C-54-approved .NET-compatible grammars.
    $secretValuePatterns = @(
        '(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^:/@\s][^/@\s]*:[^/@\s]+@',
        '(?i)(?<![A-Za-z0-9_-])Bearer[ \t]+[A-Za-z0-9._~+/-]+=*(?![A-Za-z0-9._~+/-])',
        '(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{20,}(?![A-Za-z0-9])',
        '(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])',
        '(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}(?![A-Za-z0-9])',
        '-----BEGIN PRIVATE KEY-----',
        '-----BEGIN RSA PRIVATE KEY-----',
        '-----BEGIN EC PRIVATE KEY-----',
        '-----BEGIN DSA PRIVATE KEY-----',
        '-----BEGIN OPENSSH PRIVATE KEY-----'
    )

    foreach ($segment in $segments) {
        foreach ($sensitiveName in $fixedSensitiveNames) {
            if ([StringComparer]::OrdinalIgnoreCase.Equals($segment, $sensitiveName)) {
                return $null
            }
        }

        if ([regex]::IsMatch($segment, $sensitiveTokensPattern)) {
            return $null
        }
    }

    $valuesToInspect = @($candidate) + $segments
    foreach ($value in $valuesToInspect) {
        foreach ($pattern in $secretValuePatterns) {
            if ([regex]::IsMatch($value, $pattern)) {
                return $null
            }
        }
    }

    return $candidate
}

function ConvertTo-FinalizedDiagnosticJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Record
    )

    # Accept an already-structured map, not raw JSON or exception objects.
    # All failures are generic and never echo rejected field values.
    $rejectMessage = 'Diagnostic record rejected by schema-v1 finalizer.'
    if ($null -eq $Record -or $Record -isnot [System.Collections.IDictionary]) {
        throw $rejectMessage
    }

    $expectedKeys = @(
        'schema_version', 'error_id', 'error_code', 'phase',
        'operation', 'target_relative_path', 'message'
    )
    if ($Record.Count -ne $expectedKeys.Count) {
        throw $rejectMessage
    }

    foreach ($key in $Record.Keys) {
        if ($key -isnot [string]) {
            throw $rejectMessage
        }
        $known = $false
        foreach ($expectedKey in $expectedKeys) {
            if ([StringComparer]::Ordinal.Equals($key, $expectedKey)) {
                $known = $true
                break
            }
        }
        if (-not $known) {
            throw $rejectMessage
        }
    }

    foreach ($expectedKey in $expectedKeys) {
        $found = $false
        foreach ($key in $Record.Keys) {
            if ($key -is [string] -and [StringComparer]::Ordinal.Equals([string]$key, $expectedKey)) {
                $found = $true
                break
            }
        }
        if (-not $found) {
            throw $rejectMessage
        }
    }

    $version = $Record['schema_version']
    if ($null -eq $version -or $version -is [bool]) {
        throw $rejectMessage
    }
    $versionTypeName = $version.GetType().FullName
    if ($versionTypeName -notin @(
        'System.Byte', 'System.SByte', 'System.Int16', 'System.UInt16',
        'System.Int32', 'System.UInt32', 'System.Int64', 'System.UInt64'
    ) -or $version -ne 1) {
        throw $rejectMessage
    }

    $errorId = $Record['error_id']
    if ($errorId -isnot [string] -or $errorId -cnotmatch '^ERR-(?!000000)[0-9]{6}$') {
        throw $rejectMessage
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

    $errorCode = $Record['error_code']
    if ($errorCode -isnot [string]) {
        throw $rejectMessage
    }
    $templateFound = $false
    $expectedMessage = $null
    foreach ($templateCode in $templates.Keys) {
        if ([StringComparer]::Ordinal.Equals($errorCode, [string]$templateCode)) {
            $templateFound = $true
            $expectedMessage = [string]$templates[$templateCode]
            break
        }
    }
    if (-not $templateFound) {
        throw $rejectMessage
    }

    $phase = $Record['phase']
    $operation = $Record['operation']
    if ($phase -isnot [string] -or $operation -isnot [string]) {
        throw $rejectMessage
    }

    $validPairs = @(
        'enumeration|enumerate_entries',
        'classification|classify_target',
        'metadata|read_metadata',
        'content_read|read_content',
        'hashing|compute_hash',
        'metadata|detect_source_mutation',
        'manifest_validation|validate_manifest',
        'evidence_validation|validate_evidence',
        'evidence_finalization|finalize_evidence',
        'aggregation|aggregate_results',
        'report_serialization|serialize_report',
        'report_publication|publish_report',
        'unknown|unknown'
    )
    $pair = "$phase|$operation"
    $pairFound = $false
    foreach ($validPair in $validPairs) {
        if ([StringComparer]::Ordinal.Equals($pair, $validPair)) {
            $pairFound = $true
            break
        }
    }
    if (-not $pairFound) {
        throw $rejectMessage
    }

    # C-52 messages are fixed by the validated code and must match exactly.
    # Do not trim, interpolate, sanitize, or serialize caller-provided text.
    $message = $Record['message']
    if ($message -isnot [string] -or -not [StringComparer]::Ordinal.Equals($message, $expectedMessage)) {
        throw $rejectMessage
    }
    if ($message.Length -gt 512) {
        throw $rejectMessage
    }
    foreach ($character in $message.ToCharArray()) {
        if ([char]::IsControl($character)) {
            throw $rejectMessage
        }
    }

    $safePath = $null
    $candidatePath = $Record['target_relative_path']
    if ($null -ne $candidatePath) {
        $safePath = ConvertTo-SafeDiagnosticRelativePath -Path $candidatePath
    }

    # Build a fresh ordered record: no unknown fields or caller-owned references survive.
    $finalRecord = [ordered]@{
        schema_version       = 1
        error_id             = $errorId
        error_code           = $errorCode
        phase                = $phase
        operation            = $operation
        target_relative_path = $safePath
        message              = $expectedMessage
    }

    try {
        return ConvertTo-Json -InputObject $finalRecord -Compress -Depth 3 -WarningAction Stop
    }
    catch {
        # Never include serialization exception text or input values in the diagnostic.
        throw 'Diagnostic record serialization failed.'
    }
}

function New-DiagnosticErrorId {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ref]$NextSequence
    )

    # The caller owns one counter per run and calls this once per distinct event.
    # Event IDs must then be copied unchanged through wrappers and later observers.
    # Never wrap, reuse, or include rejected sequence values in an error message.
    $sequence = $NextSequence.Value
    if ($null -eq $sequence) {
        throw 'Diagnostic event ID sequence is invalid or exhausted.'
    }

    $sequenceTypeName = $sequence.GetType().FullName
    if ($sequenceTypeName -notin @('System.Int32', 'System.Int64')) {
        throw 'Diagnostic event ID sequence is invalid or exhausted.'
    }
    if ($sequence -lt 1 -or $sequence -gt 999999) {
        throw 'Diagnostic event ID sequence is invalid or exhausted.'
    }

    $errorId = [string]::Format(
        [Globalization.CultureInfo]::InvariantCulture,
        'ERR-{0:D6}',
        [int]$sequence
    )
    $NextSequence.Value = [int]($sequence + 1)
    return $errorId
}


function Resolve-DiagnosticErrorCode {
    [CmdletBinding()]
    param([Parameter(Mandatory)][AllowEmptyString()][AllowNull()][object]$Condition)
    # C-50 Option A: trusted producer supplies one exact condition token.
    # Never inspect exception text/classes, stack traces, paths, or arbitrary metadata.
    if ($Condition -isnot [string]) { throw 'Diagnostic condition rejected by C-50 classifier.' }
    switch -CaseSensitive ($Condition) {
        'manifest_readable_invalid' { return 'manifest_invalid' }
        'evidence_readable_invalid' { return 'evidence_invalid' }
        'source_mutation_observed' { return 'source_mutation_detected' }
        'target_filename_invalid' { return 'invalid_filename' }
        'access_denied_observed' { return 'file_access_denied' }
        'directory_enumeration_failed' { return 'enumeration_failed' }
        'target_metadata_failed' { return 'file_metadata_failed' }
        'target_content_read_failed' { return 'file_read_failed' }
        'content_digest_failed' { return 'hash_failed' }
        'general_contract_validation_failed' { return 'validation_failed' }
        'report_serialization_failed' { return 'serialization_failed' }
        'aggregation_failed' { return 'aggregation_failed' }
        'report_publication_failed' { return 'publication_failed' }
        'unmatched_failure' { return 'unknown_error' }
        default { throw 'Diagnostic condition rejected by C-50 classifier.' }
    }
}

function Resolve-DiagnosticPhaseOperation {
    [CmdletBinding()]
    param([Parameter(Mandatory)][AllowEmptyString()][AllowNull()][object]$Operation)

    # C-51 approved Option C: the trusted producer supplies the operation
    # that actually failed. Derive phase centrally; never infer from exceptions
    # or from a later observer/wrapper context.
    if ($Operation -isnot [string]) {
        throw 'Diagnostic operation rejected by C-51 resolver.'
    }

    $phase = switch -CaseSensitive ($Operation) {
        'enumerate_entries' { 'enumeration'; break }
        'classify_target' { 'classification'; break }
        'read_metadata' { 'metadata'; break }
        'read_content' { 'content_read'; break }
        'compute_hash' { 'hashing'; break }
        'detect_source_mutation' { 'metadata'; break }
        'validate_manifest' { 'manifest_validation'; break }
        'validate_evidence' { 'evidence_validation'; break }
        'finalize_evidence' { 'evidence_finalization'; break }
        'aggregate_results' { 'aggregation'; break }
        'serialize_report' { 'report_serialization'; break }
        'publish_report' { 'report_publication'; break }
        'unknown' { 'unknown'; break }
        default { throw 'Diagnostic operation rejected by C-51 resolver.' }
    }

    return [pscustomobject]@{
        phase = [string]$phase
        operation = $Operation
    }
}
