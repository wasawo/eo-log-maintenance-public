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
    public static class DirectoryMetadata {
        [StructLayout(LayoutKind.Sequential)]
        private struct Information {
            public uint Attributes;
            public System.Runtime.InteropServices.ComTypes.FILETIME Creation;
            public System.Runtime.InteropServices.ComTypes.FILETIME Access;
            public System.Runtime.InteropServices.ComTypes.FILETIME Write;
            public uint VolumeSerial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
        }
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern SafeFileHandle CreateFileW(
            string name, uint access, uint share, IntPtr security,
            uint disposition, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetFileInformationByHandle(
            SafeFileHandle handle, out Information information);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern uint GetFinalPathNameByHandleW(
            SafeFileHandle handle, StringBuilder path, uint length, uint flags);
        public static string CanonicalDirectory(string path) {
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
                return buffer.ToString();
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
