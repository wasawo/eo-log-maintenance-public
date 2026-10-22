#requires -Version 7.6.7
Set-StrictMode -Version Latest

function Test-AggregationReferencedArtifacts {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string] $TrustedRootPath,

        [Parameter(Mandatory)]
        [string] $ReportPath,

        [Parameter(Mandatory)]
        [string] $ContractsPath,

        [string] $PythonExecutable = 'python',

        [string] $ValidatorPath = (Join-Path $PSScriptRoot 'validate_aggregation_artifacts.py')
    )

    function New-ArtifactValidationResult([string]$Status, [string]$ReasonCode) {
        [pscustomobject]@{
            Status = $Status
            ReasonCode = $ReasonCode
            Artifacts = @{}
        }
    }

    foreach ($path in @($TrustedRootPath, $ReportPath, $ContractsPath, $ValidatorPath)) {
        if ([string]::IsNullOrWhiteSpace($path)) {
            return (New-ArtifactValidationResult 'rejected' 'missing_input_path')
        }
    }
    if (-not (Test-Path -LiteralPath $TrustedRootPath -PathType Container)) {
        return (New-ArtifactValidationResult 'rejected' 'trusted_root_unavailable')
    }
    if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
        return (New-ArtifactValidationResult 'rejected' 'report_unavailable')
    }
    if (-not (Test-Path -LiteralPath $ContractsPath -PathType Container)) {
        return (New-ArtifactValidationResult 'rejected' 'contracts_unavailable')
    }
    if (-not (Test-Path -LiteralPath $ValidatorPath -PathType Leaf)) {
        return (New-ArtifactValidationResult 'rejected' 'validator_unavailable')
    }

    try {
        $output = @(& $PythonExecutable $ValidatorPath --root $TrustedRootPath --report $ReportPath --contracts $ContractsPath 2>$null)
        $exitCode = $LASTEXITCODE
        if ($output.Count -ne 1) {
            return (New-ArtifactValidationResult 'rejected' 'validator_output_invalid')
        }
        $result = $output[0] | ConvertFrom-Json -AsHashtable -ErrorAction Stop
        if ($exitCode -notin @(0, 2) -or $result -isnot [System.Collections.IDictionary] -or
            $result.status -notin @('verified', 'rejected') -or
            [string]::IsNullOrWhiteSpace([string]$result.reason_code)) {
            return (New-ArtifactValidationResult 'rejected' 'validator_execution_failed')
        }
        return [pscustomobject]@{
            Status = [string]$result.status
            ReasonCode = [string]$result.reason_code
            Artifacts = $result.artifacts
        }
    }
    catch {
        return (New-ArtifactValidationResult 'rejected' 'validator_execution_failed')
    }
}
