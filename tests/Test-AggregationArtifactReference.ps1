#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\AggregationArtifactReference.ps1')

$script:Passed = 0
$script:Failed = 0
function Assert-Equal([string]$Name, [object]$Actual, [object]$Expected) {
    if ($Actual -ceq $Expected) { $script:Passed++; Write-Host "PASS: $Name" }
    else { $script:Failed++; Write-Host "FAIL: $Name (expected '$Expected', got '$Actual')" -ForegroundColor Red }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('eo-artifact-reference-tests-' + [guid]::NewGuid().ToString('N'))
try {
    $root = Join-Path $tempRoot 'maintenance'
    New-Item -ItemType Directory -Path (Join-Path $root '_maintenance/manifests/PC-A') -Force | Out-Null
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes('synthetic manifest bytes')
    $file = Join-Path $root '_maintenance/manifests/PC-A/run.json'
    [System.IO.File]::WriteAllBytes($file, $bytes)
    $expected = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()

    $match = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance/manifests/PC-A/run.json' -ExpectedSha256 $expected
    Assert-Equal 'exact referenced bytes verify' $match.Status 'verified'
    Assert-Equal 'verified result returns lowercase actual digest' $match.Sha256 $expected

    $mismatch = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance/manifests/PC-A/run.json' -ExpectedSha256 ('0' * 64)
    Assert-Equal 'different expected digest fails closed' $mismatch.Status 'mismatch'
    Assert-Equal 'digest mismatch has stable reason' $mismatch.ReasonCode 'sha256_mismatch'

    $missing = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance/manifests/PC-A/missing.json' -ExpectedSha256 $expected
    Assert-Equal 'missing artifact is unavailable' $missing.Status 'unavailable'

    $traversal = Test-AggregationArtifactReference -RootPath $root -RelativePath '../outside.json' -ExpectedSha256 $expected
    Assert-Equal 'parent traversal is rejected' $traversal.Status 'invalid_reference'
    Assert-Equal 'parent traversal reason is stable' $traversal.ReasonCode 'unsafe_relative_path'

    $absolute = Test-AggregationArtifactReference -RootPath $root -RelativePath 'C:/outside.json' -ExpectedSha256 $expected
    Assert-Equal 'drive-qualified path is rejected' $absolute.Status 'invalid_reference'

    $backslash = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance\manifests\PC-A\run.json' -ExpectedSha256 $expected
    Assert-Equal 'backslash path is rejected' $backslash.Status 'invalid_reference'

    $badHash = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance/manifests/PC-A/run.json' -ExpectedSha256 ('A' * 64)
    Assert-Equal 'uppercase expected digest is rejected' $badHash.Status 'invalid_reference'

    $directory = Test-AggregationArtifactReference -RootPath $root -RelativePath '_maintenance/manifests/PC-A' -ExpectedSha256 $expected
    Assert-Equal 'directory cannot be used as artifact' $directory.Status 'unavailable'

    Write-Host "Aggregation artifact reference tests: $script:Passed passed; $script:Failed failed."
    if ($script:Failed -gt 0) { exit 1 }
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
