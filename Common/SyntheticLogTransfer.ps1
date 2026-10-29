#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'LogFunctions.ps1')

# Shared only by the explicitly isolated, non-deployable S1/S2 entry points.
function Invoke-EoSyntheticLogTransfer {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateSet('Sync', 'Archive')][string]$Route,
        [switch]$Synthetic,
        [string]$SyntheticRoot,
        [ValidateSet('PC-A', 'PC-B')][string]$MachineId = 'PC-B',
        [ValidateSet('Sync', 'Archive')][string]$Operation = 'Sync',
        [datetime]$ReferenceDate = (Get-Date).Date,
        [ValidateSet('none', 'copy_failed', 'hash_mismatch', 'enumeration_failed')]
        [string]$MockFault = 'none',
        [switch]$DryRun
    )

    $slice = if ($Route -eq 'Sync') { 'S1' } else { 'S2' }
    $fixturePrefix = if ($Route -eq 'Sync') { 'eolm-s1-sync-' } else { 'eolm-s2-archive-' }
    $fixtureMarker = if ($Route -eq 'Sync') { 'eolm-s1-synthetic-v1' } else { 'eolm-s2-synthetic-v1' }
    $sourceSide = if ($Route -eq 'Sync') { 'source' } else { 'mock-drive' }
    $destinationSide = if ($Route -eq 'Sync') { 'mock-drive' } else { 'archive' }
    $results = [Collections.Generic.List[object]]::new()
    $fixtureLease = $null
    try {
        # Reject unsupported routes before opening any supplied path.
        if ($Route -eq 'Sync') {
            if ($Operation -ne 'Sync') { throw 'archive_role_denied' }
            if ($MachineId -ne 'PC-B') { throw 's1_pc_b_only' }
        }
        else {
            if ($MachineId -ne 'PC-A') { throw 'archive_role_denied' }
            if ($Operation -ne 'Archive') { throw 's2_archive_only' }
        }
        if (-not $Synthetic -or [string]::IsNullOrWhiteSpace($SyntheticRoot)) { throw 'synthetic_fixture_required' }
        $root = [IO.Path]::GetFullPath($SyntheticRoot).TrimEnd([char[]]'\/')
        $temp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([char[]]'\/')
        if ([IO.Path]::GetDirectoryName($root) -ine $temp -or
            [IO.Path]::GetFileName($root) -cnotmatch ("^" + $fixturePrefix + "[a-f0-9]{32}$")) { throw 'synthetic_root_invalid' }
        $rootItem = Get-Item -LiteralPath $root -Force
        if (-not $rootItem.PSIsContainer -or ($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'synthetic_root_invalid'
        }
        $marker = Join-Path $root '.synthetic-fixture'
        $markerItem = Get-Item -LiteralPath $marker -Force
        if ($markerItem.PSIsContainer -or ($markerItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'synthetic_marker_invalid'
        }
        # The existing fixture marker doubles as a record-free exclusive lease.
        $fixtureLease = [IO.File]::Open($marker, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
        $markerBytes = [byte[]]::new(64)
        $markerLength = $fixtureLease.Read($markerBytes, 0, $markerBytes.Length)
        if ($fixtureLease.Length -ne $markerLength -or
            [Text.Encoding]::UTF8.GetString($markerBytes, 0, $markerLength) -cne $fixtureMarker) {
            throw 'synthetic_marker_invalid'
        }

        $sources = [Collections.Generic.List[object]]::new()
        $destinations = @{}
        foreach ($side in @($sourceSide, $destinationSide)) {
            $sideRoot = Join-Path $root $side
            $sideItem = Get-Item -LiteralPath $sideRoot -Force
            if (-not $sideItem.PSIsContainer -or ($sideItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'synthetic_layout_invalid'
            }
            foreach ($kind in @('BattleLog', 'ErrorReport')) {
                $kindRoot = Join-Path $sideRoot $kind
                $pending = [Collections.Generic.Stack[string]]::new()
                $pending.Push($kindRoot)
                while ($pending.Count -gt 0) {
                    $directory = $pending.Pop()
                    $item = Get-Item -LiteralPath $directory -Force
                    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                        throw 'synthetic_reparse_denied'
                    }
                    if ($MockFault -eq 'enumeration_failed' -and $side -eq $sourceSide) { throw 'enumeration_failed' }
                    foreach ($child in @(Get-ChildItem -LiteralPath $directory -Force)) {
                        if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'synthetic_reparse_denied' }
                        if ($child.PSIsContainer) {
                            if ($side -eq $destinationSide) { throw 'mock_drive_layout_invalid' }
                            $pending.Push($child.FullName)
                            continue
                        }
                        if ($side -eq $sourceSide) {
                            $sources.Add(@{ File=$child; LogType=$kind; RelativePath=[IO.Path]::GetRelativePath($kindRoot, $child.FullName) })
                        }
                    }
                }
                if ($side -eq $destinationSide) { $destinations[$kind] = $kindRoot }
            }
        }

        foreach ($source in @($sources | Sort-Object LogType, RelativePath)) {
            $file = $source.File
            $result = [ordered]@{
                SourceRelativePath=($source.LogType + '/' + $source.RelativePath.Replace('\', '/'))
                DestinationRelativePath=($source.LogType + '/' + $file.Name)
                Status='failure'; Reason='filename_invalid'; SourceSha256=$null; DestinationSha256=$null
                Reused=$false
            }
            try {
                $eligible = Test-LogFileEligible -LogType $source.LogType -FileName $file.Name -Operation $Operation -ReferenceDate $ReferenceDate
            }
            catch { $results.Add([pscustomobject]$result); continue }
            if (-not $eligible) {
                $result.Status='excluded'; $result.Reason='outside_period'
                $results.Add([pscustomobject]$result); continue
            }
            if ($DryRun) {
                $result.Status='planned'; $result.Reason='dry_run_no_write'
                $results.Add([pscustomobject]$result); continue
            }
            $inputStream = $null
            $outputStream = $null
            try {
                $result.Reason='copy_or_verification_failed'
                $inputStream = [IO.File]::Open($file.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
                $result.SourceSha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($inputStream)).ToLowerInvariant()
                $inputStream.Position = 0
                $destination = Join-Path $destinations[$source.LogType] $file.Name
                if (Test-Path -LiteralPath $destination) {
                    $result.DestinationSha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
                    if ($result.SourceSha256 -cne $result.DestinationSha256) {
                        $result.Status='held'; $result.Reason='content_conflict'
                    }
                    else {
                        $result.Status='success'; $result.Reason='existing_content_verified'; $result.Reused=$true
                    }
                }
                else {
                    if ($MockFault -eq 'copy_failed') { throw 'mock_copy_failed' }
                    $outputStream = [IO.File]::Open($destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                    $inputStream.CopyTo($outputStream)
                    # Faults affect only the explicitly opted-in synthetic destination.
                    if ($MockFault -eq 'hash_mismatch') { $outputStream.WriteByte(0x21) }
                    $outputStream.Flush($true)
                    $outputStream.Dispose(); $outputStream=$null
                    $result.DestinationSha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
                    if ($result.SourceSha256 -ceq $result.DestinationSha256) {
                        $result.Status='success'; $result.Reason='copied_content_verified'
                    }
                    else { $result.Reason='hash_mismatch' }
                }
            }
            catch { $result.Status='failure' }
            finally {
                if ($null -ne $outputStream) { $outputStream.Dispose() }
                if ($null -ne $inputStream) { $inputStream.Dispose() }
            }
            $results.Add([pscustomobject]$result)
        }
    }
    catch {
        # Do not expose supplied absolute paths or exception text in public output.
        $reason = if ($_.Exception.Message -cin @('archive_role_denied','s1_pc_b_only','synthetic_fixture_required',
            'synthetic_root_invalid','synthetic_marker_invalid','synthetic_layout_invalid','synthetic_reparse_denied',
            'mock_drive_layout_invalid','enumeration_failed','s2_archive_only')) { $_.Exception.Message } else { 'synthetic_run_failed' }
        $results.Add([pscustomobject]@{SourceRelativePath=$null;DestinationRelativePath=$null;Status='failure';Reason=$reason})
    }
    finally { if ($null -ne $fixtureLease) { $fixtureLease.Dispose() } }

    $failed = @($results | Where-Object Status -eq 'failure').Count
    $held = @($results | Where-Object Status -eq 'held').Count
    $success = @($results | Where-Object Status -eq 'success').Count
    $planned = @($results | Where-Object Status -eq 'planned').Count
    $status = if ($failed -gt 0) { 'failure' } elseif ($held -gt 0) { 'held' } elseif ($planned -gt 0) { 'planned' } elseif ($success -eq 0) { 'no_work' } else { 'success' }
    return [pscustomobject][ordered]@{
        Slice=$slice; SyntheticOnly=$true; MachineId=$MachineId; Operation=$Operation; Status=$status
        ProcessedCount=@($results | Where-Object { $null -ne $_.SourceRelativePath }).Count
        SuccessCount=$success; FailureCount=$failed; HeldCount=$held
        ExcludedCount=@($results | Where-Object Status -eq 'excluded').Count
        PlannedCount=$planned
        CompletedMoveCount=0; Results=@($results)
    }
}
