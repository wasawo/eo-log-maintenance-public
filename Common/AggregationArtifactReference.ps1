#requires -Version 7.6.7
Set-StrictMode -Version Latest

function Test-AggregationArtifactReference {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string] $RootPath,

        [Parameter(Mandatory)]
        [string] $RelativePath,

        [Parameter(Mandatory)]
        [string] $ExpectedSha256
    )

    function New-ReferenceResult([string]$Status, [string]$ReasonCode, [string]$Sha256 = $null) {
        [pscustomobject]@{
            Status = $Status
            ReasonCode = $ReasonCode
            Sha256 = $Sha256
        }
    }

    if ([string]::IsNullOrWhiteSpace($RelativePath) -or
        $RelativePath.StartsWith('/') -or
        $RelativePath.Contains('\') -or
        $RelativePath -match '^[A-Za-z]:' -or
        $RelativePath -match '[\x00-\x1f\x7f]' -or
        @($RelativePath -split '/').Where({ $_ -in @('', '.', '..') }).Count -gt 0) {
        return (New-ReferenceResult 'invalid_reference' 'unsafe_relative_path')
    }
    if ($ExpectedSha256 -cnotmatch '^[0-9a-f]{64}$') {
        return (New-ReferenceResult 'invalid_reference' 'invalid_expected_sha256')
    }

    try {
        $rootItem = Get-Item -LiteralPath $RootPath -Force -ErrorAction Stop
        if (-not $rootItem.PSIsContainer) {
            return (New-ReferenceResult 'invalid_reference' 'root_not_directory')
        }
        $rootFull = [System.IO.Path]::GetFullPath($rootItem.FullName).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
        $segments = @($RelativePath -split '/')
        $candidate = [System.IO.Path]::GetFullPath((Join-Path $rootFull ($segments -join [System.IO.Path]::DirectorySeparatorChar)))
        $prefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
        if (-not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return (New-ReferenceResult 'invalid_reference' 'path_escapes_root')
        }

        $current = $rootFull
        for ($i = 0; $i -lt $segments.Count; $i++) {
            $current = Join-Path $current $segments[$i]
            $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                return (New-ReferenceResult 'invalid_reference' 'reparse_point_not_allowed')
            }
            if ($i -lt ($segments.Count - 1) -and -not $item.PSIsContainer) {
                return (New-ReferenceResult 'unavailable' 'parent_component_not_directory')
            }
            if ($i -eq ($segments.Count - 1) -and $item.PSIsContainer) {
                return (New-ReferenceResult 'unavailable' 'reference_is_directory')
            }
        }

        $stream = [System.IO.File]::Open(
            $candidate,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::Read
        )
        try {
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try {
                $digestBytes = $sha.ComputeHash($stream)
                $actual = [Convert]::ToHexString($digestBytes).ToLowerInvariant()
            }
            finally {
                $sha.Dispose()
            }
        }
        finally {
            $stream.Dispose()
        }

        if ($actual -cne $ExpectedSha256) {
            return (New-ReferenceResult 'mismatch' 'sha256_mismatch' $actual)
        }
        return (New-ReferenceResult 'verified' 'sha256_match' $actual)
    }
    catch [System.Management.Automation.ItemNotFoundException] {
        return (New-ReferenceResult 'unavailable' 'artifact_not_found')
    }
    catch [System.IO.FileNotFoundException] {
        return (New-ReferenceResult 'unavailable' 'artifact_not_found')
    }
    catch [System.IO.DirectoryNotFoundException] {
        return (New-ReferenceResult 'unavailable' 'artifact_not_found')
    }
    catch [System.UnauthorizedAccessException] {
        return (New-ReferenceResult 'unavailable' 'artifact_access_denied')
    }
    catch {
        return (New-ReferenceResult 'unavailable' 'artifact_read_failed')
    }
}
