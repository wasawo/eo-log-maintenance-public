#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/MachineConfigurationRootInspection.ps1')
. (Join-Path $PSScriptRoot '../Common/LogFunctions.ps1')
$checks = 0
$skipped = 0
function Assert-Observation([object]$Result, [bool]$Observed) {
    if ($Result.FreeSpaceReliable -or $Result.MayCreateStaging -or $Result.MayUpload) {
        throw 'Free-space observation became authority.'
    }
    if ($Observed) {
        if ($Result.Status -cne 'requires_runtime_evidence' -or
            $Result.ReasonCode -cne 'staging_free_space_metadata_observed' -or
            $Result.AvailableFreeBytes -isnot [bigint] -or $Result.AvailableFreeBytes -lt 0) {
            throw 'Expected free-space metadata observation.'
        }
    }
    elseif ($Result.Status -cne 'held' -or $Result.ReasonCode -cne 'staging_free_space_unavailable' -or
            $null -ne $Result.AvailableFreeBytes) { throw 'Expected held free-space observation.' }
    $script:checks++
}

$parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar)
$root = Join-Path $parent ('eo-free-space-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root) | Out-Null
$marker = Join-Path $root 'sentinel.txt'
[IO.File]::WriteAllText($marker, 'synthetic-preserve')
$junction = Join-Path $root 'alias'
$originalQuery = (Get-Item Function:Get-EoDirectoryAvailableBytes).ScriptBlock
$originalChain = (Get-Item Function:Get-EoExistingDirectoryChainObservation).ScriptBlock
try {
    $result = Get-EoStagingFreeSpaceObservation $root
    Assert-Observation $result $true
    if (($result | ConvertTo-Json -Compress).Contains($root)) { throw 'Path leaked into result.' }
    $capacity = Get-EoStagingCapacityObservation 1 $result.AvailableFreeBytes $result.FreeSpaceReliable
    if ($capacity.Status -cne 'held' -or $capacity.ReasonCode -cne 'staging_capacity_unconfirmed') {
        throw 'Unqualified metadata bypassed the capacity gate.'
    }
    $checks++
    foreach ($path in @($null, '', 'relative', '\\synthetic-server\share', '\\?\C:\synthetic',
                         (Join-Path $root 'missing'), $marker)) {
        Assert-Observation (Get-EoStagingFreeSpaceObservation $path) $false
    }
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) throw 'synthetic-private-detail' }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) [ulong]::MaxValue }
    $large = Get-EoStagingFreeSpaceObservation $root
    Assert-Observation $large $true
    if ($large.AvailableFreeBytes -ne [bigint]::Parse('18446744073709551615')) { throw 'UInt64 truncated.' }
    $checks++
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) 'not-a-count' }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    $script:canonicalCalls = 0
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
        param($LiteralPath)
        $script:canonicalCalls++
        return [EoLogMaintenance.DirectoryObservation]::new(('synthetic-canonical-' + $script:canonicalCalls), 1, 2, 3, 4, 5, 6)
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value $originalChain
    foreach ($field in @('VolumeSerial', 'IndexHigh', 'IndexLow')) {
        $script:identityCalls = 0
        $script:identityField = $field
        Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
            param($LiteralPath)
            $script:identityCalls++
            $volume = [uint32]1; $high = [uint32]2; $low = [uint32]3
            if ($script:identityCalls -eq 2) {
                switch ($script:identityField) {
                    'VolumeSerial' { $volume++ }
                    'IndexHigh' { $high++ }
                    'IndexLow' { $low++ }
                }
            }
            return [EoLogMaintenance.DirectoryObservation]::new('same-canonical', $volume, $high, $low, 4, 5, 6)
        }
        Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    }
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value $originalChain
    # Preserve all UInt64 bits of volume ID and both halves of FILE_ID_128.
    foreach ($field in @('VolumeId', 'IdPart0', 'IdPart1')) {
        $script:extendedCalls = 0
        $script:extendedField = $field
        Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
            param($LiteralPath)
            $script:extendedCalls++
            $volume = [ulong]::MaxValue; $part0 = [ulong]::MaxValue; $part1 = [ulong]::MaxValue
            $changed = [ulong]::Parse('18446744073709551614')
            if ($script:extendedCalls -eq 2) {
                switch ($script:extendedField) {
                    'VolumeId' { $volume = $changed }
                    'IdPart0' { $part0 = $changed }
                    'IdPart1' { $part1 = $changed }
                }
            }
            return [EoLogMaintenance.DirectoryObservation]::new('same-canonical', 1, 2, 3, $volume, $part0, $part1)
        }
        Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    }
    $script:queryCalls = 0
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value { param($LiteralPath) $script:queryCalls++; return [ulong]0 }
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
        param($LiteralPath)
        return [EoLogMaintenance.DirectoryObservation]::new('same-canonical', 1, 2, 3)
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    if ($script:queryCalls -ne 0) { throw 'Missing extended identity reached free-space query.' }
    $checks++
    $script:extendedCalls = 0
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
        param($LiteralPath)
        $script:extendedCalls++
        if ($script:extendedCalls -eq 1) {
            return [EoLogMaintenance.DirectoryObservation]::new('same-canonical', 1, 2, 3, 4, 5, 6)
        }
        return [EoLogMaintenance.DirectoryObservation]::new('same-canonical', 1, 2, 3)
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    if ($script:queryCalls -ne 1) { throw 'Unexpected query count in post-observation rejection.' }
    $checks++
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value { param($LiteralPath) throw 'synthetic-identity-unavailable' }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value $originalChain
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    $native = Get-EoExistingDirectoryObservation -LiteralPath $root
    if (-not $native.HasExtendedIdentity -or $native.VolumeId -isnot [ulong] -or
        $native.IdPart0 -isnot [ulong] -or $native.IdPart1 -isnot [ulong]) {
        throw 'Native extended identity missing or truncated.'
    }
    $checks++
    $script:chainCalls = 0
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
        param($LiteralPath)
        $script:chainCalls++
        $leaf = [EoLogMaintenance.DirectoryObservation]::new('leaf', 1, 2, 3, 4, 5, 6)
        if ($script:chainCalls -eq 1) { return @($leaf, $leaf) }
        return $leaf
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value { param($LiteralPath) return @() }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    $script:chainCalls = 0
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value {
        param($LiteralPath)
        $script:chainCalls++
        $leaf = [EoLogMaintenance.DirectoryObservation]::new('leaf', 1, 2, 3, 4, 5, 6)
        $parent = [EoLogMaintenance.DirectoryObservation]::new('parent', 1, 2, 3, 4, 5, ([ulong]$script:chainCalls))
        return @($leaf, $parent)
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $root) $false
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value $originalChain
    # Actual same-name directory replacement within this owned synthetic root.
    $script:swapSource = [IO.Path]::GetFullPath((Join-Path $root 'swap'))
    $script:swapBackup = [IO.Path]::GetFullPath((Join-Path $root 'swap-preserved'))
    $script:swapOwner = [IO.Path]::GetFullPath($root)
    [IO.Directory]::CreateDirectory($script:swapSource) | Out-Null
    [IO.File]::WriteAllText((Join-Path $script:swapSource 'original.txt'), 'preserved')
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value {
        param($LiteralPath)
        # Verify both absolute move targets before moving a directory.
        $prefix = $script:swapOwner + [IO.Path]::DirectorySeparatorChar
        if ($LiteralPath -cne $script:swapSource -or
            -not $script:swapSource.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            -not $script:swapBackup.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            ([IO.File]::GetAttributes($LiteralPath) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'fixture_move_target_invalid'
        }
        [IO.Directory]::Move($script:swapSource, $script:swapBackup)
        [IO.Directory]::CreateDirectory($script:swapSource) | Out-Null
        return [ulong]1000000000
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $script:swapSource) $false
    if ([IO.File]::ReadAllText((Join-Path $script:swapBackup 'original.txt')) -cne 'preserved' -or
        [IO.File]::Exists((Join-Path $script:swapSource 'original.txt'))) { throw 'Replacement test lost original bytes.' }
    $checks++
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    # Retain the same leaf object while replacing its parent under the same name.
    $script:ancestorBase = [IO.Path]::GetFullPath((Join-Path $root 'ancestor'))
    $script:ancestorBackup = [IO.Path]::GetFullPath((Join-Path $root 'ancestor-preserved'))
    $script:ancestorLeaf = Join-Path $script:ancestorBase 'leaf'
    $script:preservedLeaf = Join-Path $script:ancestorBackup 'leaf'
    [IO.Directory]::CreateDirectory($script:ancestorLeaf) | Out-Null
    [IO.File]::WriteAllText((Join-Path $script:ancestorLeaf 'original.txt'), 'preserved-leaf')
    $leafBefore = Get-EoExistingDirectoryObservation $script:ancestorLeaf
    $parentBefore = Get-EoExistingDirectoryObservation $script:ancestorBase
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value {
        param($LiteralPath)
        $prefix = $script:swapOwner + [IO.Path]::DirectorySeparatorChar
        if ($LiteralPath -cne $script:ancestorLeaf) { throw 'fixture_move_target_invalid' }
        foreach ($movePath in @($script:ancestorBase, $script:ancestorBackup, $script:ancestorLeaf, $script:preservedLeaf)) {
            $absolute = [IO.Path]::GetFullPath($movePath)
            if (-not $absolute.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'fixture_move_target_invalid'
            }
        }
        if (([IO.File]::GetAttributes($script:ancestorBase) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'fixture_move_target_invalid'
        }
        [IO.Directory]::Move($script:ancestorBase, $script:ancestorBackup)
        [IO.Directory]::CreateDirectory($script:ancestorBase) | Out-Null
        [IO.Directory]::Move($script:preservedLeaf, $script:ancestorLeaf)
        return [ulong]1000000000
    }
    Assert-Observation (Get-EoStagingFreeSpaceObservation $script:ancestorLeaf) $false
    $leafAfter = Get-EoExistingDirectoryObservation $script:ancestorLeaf
    $parentAfter = Get-EoExistingDirectoryObservation $script:ancestorBase
    if ($leafBefore.VolumeId -ne $leafAfter.VolumeId -or $leafBefore.IdPart0 -ne $leafAfter.IdPart0 -or
        $leafBefore.IdPart1 -ne $leafAfter.IdPart1 -or
        ($parentBefore.VolumeId -eq $parentAfter.VolumeId -and $parentBefore.IdPart0 -eq $parentAfter.IdPart0 -and
         $parentBefore.IdPart1 -eq $parentAfter.IdPart1) -or
        [IO.File]::ReadAllText((Join-Path $script:ancestorLeaf 'original.txt')) -cne 'preserved-leaf') {
        throw 'Ancestor replacement fixture did not preserve the leaf.'
    }
    $checks++
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    $target = Join-Path $root 'target'
    [IO.Directory]::CreateDirectory($target) | Out-Null
    & $env:ComSpec /d /c mklink /J $junction $target 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Assert-Observation (Get-EoStagingFreeSpaceObservation $junction) $false
    }
    else { $skipped++ }
    if ([IO.File]::ReadAllText($marker) -cne 'synthetic-preserve') { throw 'Original bytes changed.' }
    $checks++
}
finally {
    Set-Item Function:Get-EoDirectoryAvailableBytes -Value $originalQuery
    Set-Item Function:Get-EoExistingDirectoryChainObservation -Value $originalChain
    $resolved = [IO.Path]::GetFullPath($root)
    if ([IO.Path]::GetDirectoryName($resolved).TrimEnd([IO.Path]::DirectorySeparatorChar) -cne $parent -or
        -not [IO.Path]::GetFileName($resolved).StartsWith('eo-free-space-') -or
        ([IO.File]::GetAttributes($resolved) -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        [IO.File]::ReadAllText($marker) -cne 'synthetic-preserve') { throw 'Unexpected cleanup root.' }
    if ([IO.Directory]::Exists($junction)) { [IO.Directory]::Delete($junction) }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Host "PASS: $checks free-space observations; $skipped unavailable junction checks skipped."
