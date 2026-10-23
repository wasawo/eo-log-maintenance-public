#requires -Version 7.6.7
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$builder = Join-Path $repoRoot '.github/scripts/Build-ReleasePackage.ps1'
if (-not (Test-Path -LiteralPath $builder -PathType Leaf)) {
    throw "Package builder not found: $builder"
}

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('eo-package-tests-' + [guid]::NewGuid().ToString('N'))
$fixture = Join-Path $tempRoot 'source'
$output = Join-Path $tempRoot 'output'

try {
    $paths = @(
        'Config',
        'scripts',
        'Common',
        'docs',
        'tests',
        '.github/workflows',
        'runtime/manifests',
        '_maintenance/recovery-private/synthetic',
        'contracts'
    )
    foreach ($path in $paths) {
        New-Item -ItemType Directory -Path (Join-Path $fixture $path) -Force | Out-Null
    }

    Set-Content (Join-Path $fixture 'README.md') '# Fixture'
    Set-Content (Join-Path $fixture 'CHANGELOG.md') '# Changes'
    Set-Content (Join-Path $fixture 'VERSION') '1.2.3'
    Set-Content (Join-Path $fixture 'requirements-runtime.txt') 'jsonschema>=4.23,<5'
    Set-Content (Join-Path $fixture 'contracts/aggregation-report-v1.schema.json') '{}'
    Set-Content (Join-Path $fixture 'contracts/manifest-v1.schema.json') '{}'
    Set-Content (Join-Path $fixture 'contracts/run-input-evidence-v1.schema.json') '{}'
    Set-Content (Join-Path $fixture 'contracts/private-recovery-evidence-v1.schema.json') '{}'
    Set-Content (Join-Path $fixture 'Config/PC-A.example.json') '{"machineId":"PC-A","role":"primary","runtimeRoot":"C:\\Example\\PCA\\Runtime","battleLogLocal":"C:\\Example\\PCA\\Source\\BattleLog","errorLogLocal":"C:\\Example\\PCA\\Source\\ErrorReport","battleLogDrive":"G:\\ExampleDrive\\SharedLogs\\BattleLog","errorLogDrive":"G:\\ExampleDrive\\SharedLogs\\ErrorReport","maintenanceDrive":"G:\\ExampleDrive\\SharedLogs\\_maintenance","battleLogArchive":"C:\\Example\\PCA\\Archive\\BattleLog","errorLogArchive":"C:\\Example\\PCA\\Archive\\ErrorReport","allowArchive":false,"maintenanceLocal":"C:\\Example\\PCA\\Maintenance"}'
    Set-Content (Join-Path $fixture 'Config/PC-B.example.json') '{"machineId":"PC-B","role":"secondary","runtimeRoot":"C:\\Example\\PCB\\Runtime","battleLogLocal":"C:\\Example\\PCB\\Source\\BattleLog","errorLogLocal":"C:\\Example\\PCB\\Source\\ErrorReport","battleLogDrive":"G:\\ExampleDrive\\SharedLogs\\BattleLog","errorLogDrive":"G:\\ExampleDrive\\SharedLogs\\ErrorReport","maintenanceDrive":"G:\\ExampleDrive\\SharedLogs\\_maintenance","maintenanceLocal":"C:\\Example\\PCB\\Maintenance"}'
    Set-Content (Join-Path $fixture 'scripts/README.md') '# Scripts'
    Set-Content (Join-Path $fixture 'Common/README.md') '# Common'
    Set-Content (Join-Path $fixture 'scripts/ArchiveAndUploadLogs.ps1') 'Write-Output "legacy"'
    Set-Content (Join-Path $fixture 'scripts/ArchiveLogs.ps1') 'Write-Output "archive fixture"'
    Set-Content (Join-Path $fixture 'Common/Hash-File.ps1') 'Get-FileHash -Algorithm SHA256'
    Set-Content (Join-Path $fixture 'Common/LogFunctions.ps1') '# Log filename and period functions'
    Set-Content (Join-Path $fixture 'Common/MachineConfiguration.ps1') '# Read-only configuration structure loader'
    Set-Content (Join-Path $fixture 'Common/MachineConfigurationBootstrap.ps1') '# Create-only configuration helper'
    Set-Content (Join-Path $fixture 'Common/MachineConfigurationRootInspection.ps1') '# Read-only existing-root inspector'
    Set-Content (Join-Path $fixture 'Common/AggregationReportValidation.ps1') '# Aggregation report validation functions'
    Set-Content (Join-Path $fixture 'Common/AggregationArtifactReference.ps1') '# Aggregation artifact reference verification functions'
    Set-Content (Join-Path $fixture 'Common/AggregationReferencedArtifacts.ps1') '# Referenced artifact schema validation entry point'
    Set-Content (Join-Path $fixture 'Common/validate_aggregation_artifacts.py') '# referenced artifact validator'
    Set-Content (Join-Path $fixture 'Common/RunInputEvidenceIntegrity.py') '# A2/B2 evidence integrity validator'
    Set-Content (Join-Path $fixture 'Common/LatestManifestSelection.py') '# Latest manifest selection core'
    Set-Content (Join-Path $fixture 'Common/ManifestDirectoryReader.py') '# Read-only directory reader'
    Set-Content (Join-Path $fixture 'Common/RecoveryDiagnostic.py') '# Pure diagnosis result model'
    Set-Content (Join-Path $fixture 'Common/RecoveryDiagnosticMutex.py') '# Record-free diagnostic mutex'
    Set-Content (Join-Path $fixture 'Common/PrivateRecoveryEvidence.py') '# Private metadata byte-binding'
    Set-Content (Join-Path $fixture 'Common/PrivateEvidenceAclProfile.py') '# Pure restrictive ACL profile'
    Set-Content (Join-Path $fixture 'Common/PrivateFileSecurityDescriptor.ps1') '# Internal descriptor normalizer'
    Set-Content (Join-Path $fixture 'docs/design.md') 'must not ship'
    Set-Content (Join-Path $fixture 'tests/test.ps1') 'must not ship'
    Set-Content (Join-Path $fixture '.github/workflows/validate.yml') 'must not ship'
    Set-Content (Join-Path $fixture '.env') 'TOKEN=not-a-real-secret'
    Set-Content (Join-Path $fixture 'runtime/manifests/run.json') '{}'
    Set-Content (Join-Path $fixture '_maintenance/recovery-private/synthetic/lock-record.bin') 'synthetic private original'
    Set-Content (Join-Path $fixture '_maintenance/recovery-private/synthetic/evidence.json') '{}'

    # The retired legacy entry point alone must never make a package deployable.
    $legacyOnlyBlocked = $false
    try {
        & $builder -SourceRoot $fixture -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'legacy-only-output') | Out-Null
    }
    catch {
        $legacyOnlyBlocked = $_.Exception.Message -match 'scripts/SyncLogs.ps1'
    }
    Assert-True $legacyOnlyBlocked 'The legacy ArchiveAndUploadLogs.ps1 must not make a package deployable.'

    Set-Content (Join-Path $fixture 'scripts/SyncLogs.ps1') 'Write-Output "official fixture"'
    $result = & $builder -SourceRoot $fixture -TargetRole PC-A -OutputDirectory $output
    Assert-True ($result.Status -eq 'deployable') 'PC-A fixture with both official entry points should be deployable.'
    Assert-True ($result.TargetRole -eq 'PC-A') 'Package result must report its target role.'
    Assert-True (Test-Path -LiteralPath $result.PackagePath) 'ZIP package was not created.'
    Assert-True (Test-Path -LiteralPath $result.ChecksumPath) 'Checksum manifest was not created.'
    Assert-True (Test-Path -LiteralPath $result.LatestMetadataPath) 'Latest metadata was not created.'
    $metadata = Get-Content -LiteralPath $result.LatestMetadataPath -Raw | ConvertFrom-Json
    Assert-True ($metadata.sourceRepository -eq 'wasawo/eo-log-maintenance-public') 'Package metadata must identify the current public repository.'

    $hash = (Get-FileHash -LiteralPath $result.PackagePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $checksumLine = (Get-Content -LiteralPath $result.ChecksumPath -Raw).Trim()
    Assert-True ($checksumLine.StartsWith($hash)) 'Checksum manifest does not match the ZIP hash.'

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($result.PackagePath)
    try {
        $entries = @($archive.Entries | ForEach-Object { $_.FullName })
    }
    finally {
        $archive.Dispose()
    }

    foreach ($expected in @(
        'README.md',
        'CHANGELOG.md',
        'VERSION',
        'requirements-runtime.txt',
        'contracts/aggregation-report-v1.schema.json',
        'contracts/manifest-v1.schema.json',
        'contracts/run-input-evidence-v1.schema.json',
        'contracts/private-recovery-evidence-v1.schema.json',
        'Config/PC-A.example.json',
        'Config/PC-B.example.json',
        'scripts/README.md',
        'scripts/SyncLogs.ps1',
        'scripts/ArchiveLogs.ps1',
        'Common/README.md',
        'Common/Hash-File.ps1',
        'Common/LogFunctions.ps1',
        'Common/MachineConfiguration.ps1',
        'Common/MachineConfigurationBootstrap.ps1',
        'Common/MachineConfigurationRootInspection.ps1',
        'Common/AggregationReportValidation.ps1',
        'Common/AggregationArtifactReference.ps1',
        'Common/AggregationReferencedArtifacts.ps1',
        'Common/validate_aggregation_artifacts.py',
        'Common/RunInputEvidenceIntegrity.py',
        'Common/LatestManifestSelection.py'
        'Common/ManifestDirectoryReader.py'
        'Common/RecoveryDiagnostic.py'
        'Common/RecoveryDiagnosticMutex.py'
        'Common/PrivateRecoveryEvidence.py'
        'Common/PrivateEvidenceAclProfile.py'
        'Common/PrivateFileSecurityDescriptor.ps1'
    )) {
        Assert-True ($expected -in $entries) "Expected allowlisted file missing from ZIP: $expected"
    }

    foreach ($excluded in @(
        'scripts/ArchiveAndUploadLogs.ps1',
        'docs/design.md',
        'tests/test.ps1',
        '.github/workflows/validate.yml',
        'Config/PC-A.json',
        '.env',
        'runtime/manifests/run.json',
        '_maintenance/recovery-private/synthetic/lock-record.bin',
        '_maintenance/recovery-private/synthetic/evidence.json'
    )) {
        Assert-True ($excluded -notin $entries) "Excluded file leaked into ZIP: $excluded"
    }

    # PC-B must omit ArchiveLogs.ps1 even when the source tree contains it.
    $pcBResult = & $builder -SourceRoot $fixture -TargetRole PC-B -OutputDirectory (Join-Path $tempRoot 'pc-b-output')
    Assert-True ($pcBResult.Status -eq 'deployable') 'PC-B package with SyncLogs.ps1 should be deployable without ArchiveLogs.ps1.'
    Assert-True ($pcBResult.TargetRole -eq 'PC-B') 'PC-B package result must report its target role.'
    $pcBArchive = [System.IO.Compression.ZipFile]::OpenRead($pcBResult.PackagePath)
    try {
        $pcBEntries = @($pcBArchive.Entries | ForEach-Object { $_.FullName })
    }
    finally {
        $pcBArchive.Dispose()
    }
    Assert-True ('scripts/SyncLogs.ps1' -in $pcBEntries) 'PC-B package must include SyncLogs.ps1.'
    Assert-True ('scripts/ArchiveLogs.ps1' -notin $pcBEntries) 'PC-B package must exclude ArchiveLogs.ps1.'

    # Example configuration semantics are fixed by C-20/C-21/C-28 and must fail closed.
    # Mutate a valid baseline so each case fails for the intended semantic rule, not missing unrelated fields.
    $invalidConfigCases = @(
        @{ Name = 'pc-a-allow-delete'; Path = 'Config/PC-A.example.json'; Mutation = { param($c) $c | Add-Member -NotePropertyName allowDelete -NotePropertyValue $false } },
        @{ Name = 'pc-a-wrong-role'; Path = 'Config/PC-A.example.json'; Mutation = { param($c) $c.role = 'secondary' } },
        @{ Name = 'pc-b-wrong-machine-id'; Path = 'Config/PC-B.example.json'; Mutation = { param($c) $c.machineId = 'PC-A' } },
        @{ Name = 'pc-a-archive-enabled-template'; Path = 'Config/PC-A.example.json'; Mutation = { param($c) $c.allowArchive = $true } },
        @{ Name = 'pc-a-archive-missing'; Path = 'Config/PC-A.example.json'; Mutation = { param($c) $c.PSObject.Properties.Remove('allowArchive') } },
        @{ Name = 'pc-b-archive-property'; Path = 'Config/PC-B.example.json'; Mutation = { param($c) $c | Add-Member -NotePropertyName allowArchive -NotePropertyValue $false } },
        @{ Name = 'pc-b-allow-delete'; Path = 'Config/PC-B.example.json'; Mutation = { param($c) $c | Add-Member -NotePropertyName allowDelete -NotePropertyValue $false } },
        @{ Name = 'pc-a-unknown-property'; Path = 'Config/PC-A.example.json'; Mutation = { param($c) $c | Add-Member -NotePropertyName unexpected -NotePropertyValue $true } },
        @{ Name = 'pc-b-missing-path'; Path = 'Config/PC-B.example.json'; Mutation = { param($c) $c.PSObject.Properties.Remove('runtimeRoot') } },
        @{ Name = 'pc-b-relative-path'; Path = 'Config/PC-B.example.json'; Mutation = { param($c) $c.runtimeRoot = 'relative\runtime' } }
    )

    foreach ($exampleRole in @('PC-A', 'PC-B')) {
        $fixtureConfig = Get-Content (Join-Path $fixture "Config/$exampleRole.example.json") -Raw | ConvertFrom-Json
        $rootProperties = @($fixtureConfig.PSObject.Properties.Name | Where-Object { $_ -notin @('machineId', 'role', 'allowArchive', 'maintenanceLocal') })
        foreach ($pathProperty in $rootProperties) {
            $capturedProperty = $pathProperty
            $invalidConfigCases += @{
                Name = "$exampleRole-maintenance-overlap-$pathProperty"
                Path = "Config/$exampleRole.example.json"
                Mutation = { param($c) $c.maintenanceLocal = $c.$capturedProperty }.GetNewClosure()
            }
        }
        $invalidConfigCases += @(
            @{ Name = "$exampleRole-maintenance-missing"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.PSObject.Properties.Remove('maintenanceLocal') } },
            @{ Name = "$exampleRole-maintenance-relative"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = 'relative\maintenance' } },
            @{ Name = "$exampleRole-maintenance-wrong-type"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = 123 } },
            @{ Name = "$exampleRole-maintenance-child"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = $c.runtimeRoot + '\child' } },
            @{ Name = "$exampleRole-maintenance-parent"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = [IO.Path]::GetDirectoryName($c.runtimeRoot) } },
            @{ Name = "$exampleRole-maintenance-case-trailing"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = $c.runtimeRoot.ToUpperInvariant() + '\' } },
            @{ Name = "$exampleRole-maintenance-normalized"; Path = "Config/$exampleRole.example.json"; Mutation = { param($c) $c.maintenanceLocal = $c.runtimeRoot + '\child\..' } }
        )
    }

    foreach ($case in $invalidConfigCases) {
        $invalidRoot = Join-Path $tempRoot $case.Name
        New-Item -ItemType Directory -Path $invalidRoot -Force | Out-Null
        Copy-Item -Path (Join-Path $fixture '*') -Destination $invalidRoot -Recurse -Force
        $configPath = Join-Path $invalidRoot $case.Path
        $baselineConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        $invalidConfig = $baselineConfig | ConvertTo-Json -Depth 10 | ConvertFrom-Json
        & $case.Mutation $invalidConfig
        Set-Content -LiteralPath $configPath -Value ($invalidConfig | ConvertTo-Json -Depth 10)
        $configRejected = $false
        try {
            & $builder -SourceRoot $invalidRoot -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot "$($case.Name)-output") | Out-Null
        }
        catch {
            $configRejected = $_.Exception.Message -match 'Example configuration'
        }
        Assert-True $configRejected "Invalid example config was not rejected: $($case.Name)"
    }


    # A common string prefix without a directory boundary is not containment.
    $siblingRoot = Join-Path $tempRoot 'maintenance-sibling-root'
    New-Item -ItemType Directory -Path $siblingRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $fixture '*') -Destination $siblingRoot -Recurse -Force
    $siblingConfigPath = Join-Path $siblingRoot 'Config/PC-A.example.json'
    $siblingConfig = Get-Content -LiteralPath $siblingConfigPath -Raw | ConvertFrom-Json
    $siblingConfig.maintenanceLocal = $siblingConfig.runtimeRoot + '-data'
    Set-Content -LiteralPath $siblingConfigPath -Value ($siblingConfig | ConvertTo-Json -Depth 10)
    $siblingResult = & $builder -SourceRoot $siblingRoot -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'maintenance-sibling-output')
    Assert-True ($siblingResult.Status -eq 'deployable') 'A separate sibling prefix must be accepted.'


    # PC-A must not be treated as deployable without its archive entry point.
    $pcAWithoutArchive = Join-Path $tempRoot 'pc-a-without-archive'
    New-Item -ItemType Directory -Path $pcAWithoutArchive -Force | Out-Null
    Copy-Item -Path (Join-Path $fixture '*') -Destination $pcAWithoutArchive -Recurse -Force
    Remove-Item -LiteralPath (Join-Path $pcAWithoutArchive 'scripts/ArchiveLogs.ps1') -Force
    $pcAArchiveBlocked = $false
    try {
        & $builder -SourceRoot $pcAWithoutArchive -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'pc-a-missing-archive-output') | Out-Null
    }
    catch {
        $pcAArchiveBlocked = $_.Exception.Message -match 'scripts/ArchiveLogs.ps1'
    }
    Assert-True $pcAArchiveBlocked 'PC-A package must be rejected when ArchiveLogs.ps1 is missing.'

    # The builder must reject active machine-specific configuration, not silently package around it.
    $activeConfigPath = Join-Path $fixture 'Config/PC-A.json'
    Set-Content -LiteralPath $activeConfigPath -Value '{"secret":"must never ship"}'
    $activeConfigBlocked = $false
    try {
        & $builder -SourceRoot $fixture -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'active-config-output') | Out-Null
    }
    catch {
        $activeConfigBlocked = $_.Exception.Message -match 'Active machine-specific configuration'
    }
    Assert-True $activeConfigBlocked 'Active machine-specific configuration must block package generation.'
    Remove-Item -LiteralPath $activeConfigPath -Force
    $noRuntimeFixture = Join-Path $tempRoot 'no-runtime'
    New-Item -ItemType Directory -Path $noRuntimeFixture -Force | Out-Null
    Copy-Item -Path (Join-Path $fixture '*') -Destination $noRuntimeFixture -Recurse -Force
    Remove-Item -LiteralPath (Join-Path $noRuntimeFixture 'scripts/SyncLogs.ps1') -Force
    Remove-Item -LiteralPath (Join-Path $noRuntimeFixture 'scripts/ArchiveAndUploadLogs.ps1') -Force
    $blocked = $false
    try {
        & $builder -SourceRoot $noRuntimeFixture -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'blocked-output') | Out-Null
    }
    catch {
        $blocked = $_.Exception.Message -match 'scripts/SyncLogs.ps1'
    }
    Assert-True $blocked 'A deployable package without a runtime script must be rejected.'

    # Explicitly permitted review-only artifact must be marked non-deployable.
    $reviewResult = & $builder -SourceRoot $noRuntimeFixture -TargetRole PC-A -OutputDirectory (Join-Path $tempRoot 'review-output') -AllowNonDeployable
    Assert-True ($reviewResult.Status -eq 'non-deployable-review-artifact') 'Review-only package status is incorrect.'

    Write-Host 'PASS: role-specific entry points, package allowlist, exclusions, checksum, active-config guard, and non-deployable guard.'
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
