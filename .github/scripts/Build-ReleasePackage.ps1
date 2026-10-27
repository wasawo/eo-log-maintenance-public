#requires -Version 7.6.7
[CmdletBinding()]
param(
    [string]$SourceRoot = (Join-Path $PSScriptRoot '..\..'),
    [string]$OutputDirectory = (Join-Path ([System.IO.Path]::GetTempPath()) 'eo-log-maintenance-release'),
    [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$TargetRole,
    [switch]$AllowNonDeployable
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\..\Common\LogFunctions.ps1')
. (Join-Path $PSScriptRoot '..\..\Common\MachineConfiguration.ps1')

function Get-RelativePath {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Path
    )
    return [System.IO.Path]::GetRelativePath($Root, $Path).Replace('\', '/')
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
$sourcePrefix = $source.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if ($output.Equals($source, [System.StringComparison]::OrdinalIgnoreCase) -or
    $output.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must be outside SourceRoot: $output"
}

$requiredFiles = @(
    'README.md',
    'CHANGELOG.md',
    'VERSION',
    'Config/PC-A.example.json',
    'Config/PC-B.example.json',
    'scripts/README.md',
    'Common/README.md',
    'requirements-runtime.txt',
    'contracts/aggregation-report-v1.schema.json',
    'contracts/manifest-v1.schema.json',
    'contracts/run-input-evidence-v1.schema.json',
    'contracts/private-recovery-evidence-v1.schema.json',
    'contracts/move-record-v1.schema.json',
    'contracts/completion-wait-checkpoint-v1.schema.json'
)

foreach ($relative in $requiredFiles) {
    $path = Join-Path $source ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required package source file is missing: $relative"
    }
}

$version = (Get-Content -LiteralPath (Join-Path $source 'VERSION') -Raw).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+$') {
    throw "VERSION must use MAJOR.MINOR.PATCH format; found: '$version'"
}

foreach ($activeConfig in @('Config/PC-A.json', 'Config/PC-B.json')) {
    $path = Join-Path $source ($activeConfig.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    if (Test-Path -LiteralPath $path) {
        throw "Active machine-specific configuration must not be present in the source tree: $activeConfig"
    }
}

# Explicit allowlist: never package the whole repository and then filter it.
$relativeFiles = [System.Collections.Generic.List[string]]::new()
foreach ($relative in $requiredFiles) {
    $relativeFiles.Add($relative)
}

foreach ($directory in @('scripts', 'Common')) {
    $absoluteDirectory = Join-Path $source $directory
    $candidateFiles = @(Get-ChildItem -LiteralPath $absoluteDirectory -File -Recurse -Force)
    foreach ($file in $candidateFiles) {
        if (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse points are not allowed in package source directories: $($file.FullName)"
        }

        $relative = Get-RelativePath -Root $source -Path $file.FullName
        if ($relative -eq "$directory/README.md" -or $relative -eq 'scripts/ArchiveAndUploadLogs.ps1') {
            continue
        }
        if ($TargetRole -eq 'PC-B' -and $relative -eq 'scripts/ArchiveLogs.ps1') {
            continue
        }
        if ($file.Extension -notin @('.ps1', '.py')) {
            throw "Unexpected file under '$directory' is not allowlisted: $relative"
        }
        $relativeFiles.Add($relative)
    }
}

$relativeFiles = @($relativeFiles | Sort-Object -Unique)
# Deployability is role-specific. PC-A requires both official entry points; PC-B must never receive the archive entry point.
$requiredRuntimeScripts = if ($TargetRole -eq 'PC-A') {
    @('scripts/SyncLogs.ps1', 'scripts/ArchiveLogs.ps1')
}
else {
    @('scripts/SyncLogs.ps1')
}
$missingRuntimeScripts = @($requiredRuntimeScripts | Where-Object { $_ -notin $relativeFiles })

if ($missingRuntimeScripts.Count -gt 0 -and -not $AllowNonDeployable) {
    throw "Required runtime entry point(s) for $TargetRole are missing: $($missingRuntimeScripts -join ', '). A deployable release cannot be built yet. Use -AllowNonDeployable only for a clearly marked review artifact."
}

foreach ($exampleRole in @('PC-A', 'PC-B')) {
    $relative = "Config/$exampleRole.example.json"
    $path = Join-Path $source ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    try {
        $rawConfiguration = Get-Content -LiteralPath $path -Raw
        $config = ConvertFrom-EoMachineConfigurationJson -Json $rawConfiguration -ExpectedMachineId $exampleRole
    }
    catch {
        throw "Example configuration $relative failed structural validation."
    }
    $expectedRole = if ($exampleRole -eq 'PC-A') { 'primary' } else { 'secondary' }
    if ($config.machineId -ne $exampleRole -or $config.role -ne $expectedRole) {
        throw "Example configuration $relative must identify machineId '$exampleRole' and role '$expectedRole'."
    }

    $propertyNames = @($config.PSObject.Properties.Name)
    $commonProperties = @(
        'machineId', 'role', 'runtimeRoot', 'battleLogLocal', 'errorLogLocal',
        'battleLogDrive', 'errorLogDrive', 'maintenanceDrive', 'maintenanceLocal'
    )
    $allowedProperties = if ($exampleRole -eq 'PC-A') {
        @($commonProperties + @('battleLogArchive', 'errorLogArchive', 'allowArchive'))
    }
    else {
        $commonProperties
    }
    $unknownProperties = @($propertyNames | Where-Object { $_ -notin $allowedProperties })
    if ($unknownProperties.Count -gt 0) {
        throw "Example configuration $relative contains unknown property/properties: $($unknownProperties -join ', ')."
    }

    $requiredProperties = if ($exampleRole -eq 'PC-A') {
        @($commonProperties + @('battleLogArchive', 'errorLogArchive', 'allowArchive'))
    }
    else {
        $commonProperties
    }
    $missingProperties = @($requiredProperties | Where-Object { $_ -notin $propertyNames })
    if ($missingProperties.Count -gt 0) {
        throw "Example configuration $relative is missing required property/properties: $($missingProperties -join ', ')."
    }

    foreach ($pathProperty in @($requiredProperties | Where-Object { $_ -notin @('machineId', 'role', 'allowArchive') })) {
        $pathValue = $config.$pathProperty
        if ($pathValue -isnot [string] -or [string]::IsNullOrWhiteSpace($pathValue) -or $pathValue -notmatch '^[A-Za-z]:\\') {
            throw "Example configuration $relative property '$pathProperty' must be a non-empty absolute Windows drive path."
        }
    }


    # Template-level lexical separation only; runtime must also validate actual
    # volume, reparse/alias, access and point-of-use identity constraints.
    try {
        $localRoot = [System.IO.Path]::GetFullPath($config.maintenanceLocal).TrimEnd([char[]]'\/')
        foreach ($otherProperty in @($requiredProperties | Where-Object { $_ -notin @('machineId', 'role', 'allowArchive', 'maintenanceLocal') })) {
            $otherRoot = [System.IO.Path]::GetFullPath($config.$otherProperty).TrimEnd([char[]]'\/')
            $comparison = [System.StringComparison]::OrdinalIgnoreCase
            if ($localRoot.Equals($otherRoot, $comparison) -or
                $localRoot.StartsWith($otherRoot + '\', $comparison) -or
                $otherRoot.StartsWith($localRoot + '\', $comparison)) {
                throw 'root_overlap'
            }
        }
    }
    catch {
        throw "Example configuration $relative maintenanceLocal must be a separate absolute root."
    }

    if ('allowDelete' -in $propertyNames) {
        throw "Example configuration $relative must not contain allowDelete."
    }

    if ($exampleRole -eq 'PC-A') {
        if ($config.allowArchive -isnot [bool] -or $config.allowArchive) {
            throw 'Example configuration Config/PC-A.example.json must include boolean allowArchive: false as its safe default.'
        }
    }
    elseif ('allowArchive' -in $propertyNames) {
        throw 'Example configuration Config/PC-B.example.json must omit allowArchive.'
    }
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$stage = Join-Path $output ('.stage-' + [guid]::NewGuid().ToString('N'))
$zipPath = Join-Path $output "eo-log-maintenance-v$version.zip"
$checksumPath = Join-Path $output 'SHA256SUMS.txt'
$latestPath = Join-Path $output 'latest.json'

try {
    New-Item -ItemType Directory -Path $stage -Force | Out-Null

    foreach ($relative in $relativeFiles) {
        $sourceFile = Join-Path $source ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        $stageFile = Join-Path $stage ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        New-Item -ItemType Directory -Path (Split-Path -Parent $stageFile) -Force | Out-Null
        Copy-Item -LiteralPath $sourceFile -Destination $stageFile
    }

    if ($missingRuntimeScripts.Count -gt 0) {
        Set-Content -LiteralPath (Join-Path $stage 'PACKAGE-STATUS.txt') -Encoding utf8 -Value @(
            'STATUS: NON-DEPLOYABLE REVIEW ARTIFACT'
            "Target role: $TargetRole"
            "Missing required runtime entry point(s): $($missingRuntimeScripts -join ', ')"
            'This artifact is not deployable. Do not apply it to PC-A or PC-B.'
        )
    }

    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zipPath -CompressionLevel Optimal

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath $checksumPath -Encoding ascii -Value "$zipHash  $(Split-Path -Leaf $zipPath)"

    $status = if ($missingRuntimeScripts.Count -eq 0) { 'deployable' } else { 'non-deployable-review-artifact' }
    [ordered]@{
        version = $version
        targetRole = $TargetRole
        sourceRepository = 'wasawo/eo-log-maintenance-public'
        sourceRef = 'local-build'
        package = (Split-Path -Leaf $zipPath)
        sha256Manifest = (Split-Path -Leaf $checksumPath)
        sha256 = $zipHash
        status = $status
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $latestPath -Encoding utf8

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $actualEntries = @($archive.Entries | ForEach-Object { $_.FullName.TrimEnd('/') } | Where-Object { $_ })
        $expectedEntries = @($relativeFiles)
        if ($missingRuntimeScripts.Count -gt 0) {
            $expectedEntries += 'PACKAGE-STATUS.txt'
        }
        $unexpected = @($actualEntries | Where-Object { $_ -notin $expectedEntries })
        $missing = @($expectedEntries | Where-Object { $_ -notin $actualEntries })
        if ($unexpected.Count -gt 0 -or $missing.Count -gt 0) {
            throw "Archive entry validation failed. Unexpected=[$($unexpected -join ', ')]; Missing=[$($missing -join ', ')]"
        }
    }
    finally {
        $archive.Dispose()
    }

    [pscustomobject]@{
        Version = $version
        Status = $status
        TargetRole = $TargetRole
        PackagePath = $zipPath
        ChecksumPath = $checksumPath
        LatestMetadataPath = $latestPath
        SHA256 = $zipHash
        IncludedFileCount = $expectedEntries.Count
    }
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
