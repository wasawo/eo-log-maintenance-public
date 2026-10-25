#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MachineConfiguration.ps1')

function Initialize-EoDirectoryMetadataType {
    if (([Management.Automation.PSTypeName]'EoLogMaintenance.DirectoryMetadata').Type) { return }
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
namespace EoLogMaintenance {
    public sealed class DirectoryObservation {
        public readonly string CanonicalPath;
        public readonly uint VolumeSerial, IndexHigh, IndexLow;
        public readonly bool HasExtendedIdentity;
        public readonly ulong VolumeId, IdPart0, IdPart1;
        public DirectoryObservation(string canonicalPath, uint volumeSerial, uint indexHigh, uint indexLow) {
            CanonicalPath = canonicalPath;
            VolumeSerial = volumeSerial;
            IndexHigh = indexHigh;
            IndexLow = indexLow;
        }
        public DirectoryObservation(string canonicalPath, uint volumeSerial, uint indexHigh, uint indexLow,
                                    ulong volumeId, ulong idPart0, ulong idPart1)
            : this(canonicalPath, volumeSerial, indexHigh, indexLow) {
            HasExtendedIdentity = true;
            VolumeId = volumeId;
            IdPart0 = idPart0;
            IdPart1 = idPart1;
        }
    }
    public static class DirectoryMetadata {
        [StructLayout(LayoutKind.Sequential)]
        private struct Information {
            public uint Attributes;
            public System.Runtime.InteropServices.ComTypes.FILETIME Creation;
            public System.Runtime.InteropServices.ComTypes.FILETIME Access;
            public System.Runtime.InteropServices.ComTypes.FILETIME Write;
            public uint VolumeSerial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct FileIdentity {
            // FILE_ID_INFO: UInt64 volume serial followed by 16 opaque ID bytes.
            public ulong VolumeId, Part0, Part1;
        }
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern SafeFileHandle CreateFileW(
            string name, uint access, uint share, IntPtr security,
            uint disposition, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetFileInformationByHandle(
            SafeFileHandle handle, out Information information);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetFileInformationByHandleEx(
            SafeFileHandle handle, int informationClass, out FileIdentity identity, uint size);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern uint GetFinalPathNameByHandleW(
            SafeFileHandle handle, StringBuilder path, uint length, uint flags);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern bool GetDiskFreeSpaceExW(
            string path, out ulong availableToCaller, out ulong total, out ulong totalFree);
        public static ulong AvailableBytes(string path) {
            ulong available, total, totalFree;
            if (!GetDiskFreeSpaceExW(path, out available, out total, out totalFree))
                throw new InvalidOperationException("staging_free_space_unavailable");
            return available;
        }
        public static string CanonicalDirectory(string path) {
            return ObserveDirectory(path).CanonicalPath;
        }
        public static DirectoryObservation ObserveDirectory(string path) {
            return ReadDirectory(path, false);
        }
        public static DirectoryObservation ObserveDirectoryIdentity(string path) {
            return ReadDirectory(path, true);
        }
        private static DirectoryObservation ReadDirectory(string path, bool requireExtendedIdentity) {
            // Metadata only, OPEN_EXISTING, BACKUP_SEMANTICS | OPEN_REPARSE_POINT.
            // No write access, creation, content read or directory enumeration.
            using (var handle = CreateFileW(path, 0, 7, IntPtr.Zero, 3,
                                           0x02200000, IntPtr.Zero)) {
                if (handle.IsInvalid) throw new InvalidOperationException("root_metadata_unavailable");
                Information information;
                if (!GetFileInformationByHandle(handle, out information))
                    throw new InvalidOperationException("root_metadata_unavailable");
                if ((information.Attributes & 0x400) != 0 ||
                    (information.Attributes & 0x10) == 0)
                    throw new InvalidOperationException("root_metadata_invalid");
                var buffer = new StringBuilder(32768);
                // FILE_NAME_NORMALIZED | VOLUME_NAME_GUID. Unsupported providers fail.
                uint length = GetFinalPathNameByHandleW(handle, buffer, (uint)buffer.Capacity, 1);
                if (length == 0 || length >= buffer.Capacity)
                    throw new InvalidOperationException("root_metadata_unavailable");
                if (requireExtendedIdentity) {
                    FileIdentity identity;
                    // FileIdInfo = 0x12; no fallback to 64-bit identity on failure.
                    if (!GetFileInformationByHandleEx(handle, 0x12, out identity,
                                                     (uint)Marshal.SizeOf(typeof(FileIdentity))))
                        throw new InvalidOperationException("root_identity_unavailable");
                    return new DirectoryObservation(buffer.ToString(), information.VolumeSerial,
                        information.IndexHigh, information.IndexLow, identity.VolumeId, identity.Part0, identity.Part1);
                }
                return new DirectoryObservation(buffer.ToString(), information.VolumeSerial,
                                                information.IndexHigh, information.IndexLow);
            }
        }
    }
}
"@
}

function Assert-EoDirectoryComponents {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $cursor = [IO.DirectoryInfo]::new($LiteralPath)
    while ($null -ne $cursor) {
        $attributes = [IO.File]::GetAttributes($cursor.FullName)
        if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
            ($attributes -band [IO.FileAttributes]::Directory) -eq 0) {
            throw 'configuration_root_inspection_failed'
        }
        $cursor = $cursor.Parent
    }
}

function Get-EoExistingDirectoryCanonicalPath {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $full = [IO.Path]::GetFullPath($LiteralPath)
    Assert-EoDirectoryComponents -LiteralPath $full
    $canonical = [EoLogMaintenance.DirectoryMetadata]::CanonicalDirectory($full)
    Assert-EoDirectoryComponents -LiteralPath $full
    if (-not $canonical.StartsWith('\\?\Volume{', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'configuration_root_inspection_failed'
    }
    return $canonical.TrimEnd([char]'\')
}

function Get-EoDirectoryAvailableBytes {
    param([Parameter(Mandatory)][string]$LiteralPath)
    return [EoLogMaintenance.DirectoryMetadata]::AvailableBytes($LiteralPath)
}

function Get-EoExistingDirectoryObservation {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $full = [IO.Path]::GetFullPath($LiteralPath)
    Assert-EoDirectoryComponents -LiteralPath $full
    $observation = [EoLogMaintenance.DirectoryMetadata]::ObserveDirectoryIdentity($full)
    Assert-EoDirectoryComponents -LiteralPath $full
    if (-not $observation.CanonicalPath.StartsWith('\\?\Volume{', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'configuration_root_inspection_failed'
    }
    return $observation
}

function Get-EoExistingDirectoryChainObservation {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $full = [IO.Path]::GetFullPath($LiteralPath)
    Assert-EoDirectoryComponents -LiteralPath $full
    $observations = [Collections.Generic.List[EoLogMaintenance.DirectoryObservation]]::new()
    $cursor = [IO.DirectoryInfo]::new($full)
    while ($null -ne $cursor) {
        $observed = [EoLogMaintenance.DirectoryMetadata]::ObserveDirectoryIdentity($cursor.FullName)
        if (-not $observed.CanonicalPath.StartsWith('\\?\Volume{', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'configuration_root_inspection_failed'
        }
        $observations.Add($observed)
        $cursor = $cursor.Parent
    }
    Assert-EoDirectoryComponents -LiteralPath $full
    return $observations.ToArray()
}

function Get-EoStagingFreeSpaceObservation {
    <# Metadata observation only: no creation, reservation or root qualification. #>
    [CmdletBinding()]
    param([AllowNull()][object]$LiteralPath)
    $available = $null
    $reason = 'staging_free_space_unavailable'
    $status = 'held'
    try {
        if (-not [OperatingSystem]::IsWindows()) { throw 'unsupported' }
        if ($LiteralPath -isnot [string] -or $LiteralPath -notmatch '^[A-Za-z]:\\' -or
            $LiteralPath.Substring(2) -match '[<>:"|?*/\x00-\x1f]') { throw 'invalid' }
        $full = [IO.Path]::GetFullPath($LiteralPath)
        Initialize-EoDirectoryMetadataType
        $before = @(Get-EoExistingDirectoryChainObservation -LiteralPath $full)
        if ($before.Count -eq 0) { throw 'invalid' }
        foreach ($item in $before) {
            if ($item -isnot [EoLogMaintenance.DirectoryObservation] -or -not $item.HasExtendedIdentity) {
                throw 'invalid'
            }
        }
        $observed = Get-EoDirectoryAvailableBytes -LiteralPath $full
        $after = @(Get-EoExistingDirectoryChainObservation -LiteralPath $full)
        if ($observed -isnot [ulong] -or $before.Count -ne $after.Count) { throw 'invalid' }
        for ($index = 0; $index -lt $before.Count; $index++) {
            $old = $before[$index]; $new = $after[$index]
            if ($new -isnot [EoLogMaintenance.DirectoryObservation] -or -not $new.HasExtendedIdentity -or
                -not $old.CanonicalPath.Equals($new.CanonicalPath, [StringComparison]::OrdinalIgnoreCase) -or
                $old.VolumeSerial -ne $new.VolumeSerial -or $old.IndexHigh -ne $new.IndexHigh -or
                $old.IndexLow -ne $new.IndexLow -or $old.VolumeId -ne $new.VolumeId -or
                $old.IdPart0 -ne $new.IdPart0 -or $old.IdPart1 -ne $new.IdPart1) {
                throw 'invalid'
            }
        }
        $available = [bigint]$observed
        $status = 'requires_runtime_evidence'
        $reason = 'staging_free_space_metadata_observed'
    }
    catch {
        # Never return the supplied path, canonical volume name or raw exception.
        $available = $null
    }
    return [pscustomobject]@{
        Status = $status; ReasonCode = $reason; AvailableFreeBytes = $available
        FreeSpaceReliable = $false; MayCreateStaging = $false; MayUpload = $false
    }
}

function Test-EoMachineConfigurationRoots {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Json,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$ExpectedMachineId
    )
    # Structural validation remains first. Nothing runs by dot-sourcing.
    $configuration = ConvertFrom-EoMachineConfigurationJson -Json $Json -ExpectedMachineId $ExpectedMachineId
    if (-not [OperatingSystem]::IsWindows()) { throw 'configuration_root_inspection_unsupported' }
    try {
        Initialize-EoDirectoryMetadataType
        $roots = @{}
        foreach ($property in $configuration.PSObject.Properties) {
            if ($property.Name -notin @('machineId', 'role', 'allowArchive')) {
                $roots[$property.Name] = Get-EoExistingDirectoryCanonicalPath -LiteralPath $property.Value
            }
        }
        $local = $roots.maintenanceLocal
        $comparison = [StringComparison]::OrdinalIgnoreCase
        foreach ($name in @($roots.Keys | Where-Object { $_ -ne 'maintenanceLocal' })) {
            $other = $roots[$name]
            if ($local.Equals($other, $comparison) -or
                $local.StartsWith($other + [IO.Path]::DirectorySeparatorChar, $comparison) -or
                $other.StartsWith($local + [IO.Path]::DirectorySeparatorChar, $comparison)) {
                throw 'configuration_root_inspection_failed'
            }
        }
        # Metadata/canonical strings are intentionally not returned or logged.
        return [pscustomobject]@{
            Status = 'existing_roots_separated'
            MachineId = $ExpectedMachineId
            RootCount = $roots.Count
        }
    }
    catch { throw 'configuration_root_inspection_failed' }
}
