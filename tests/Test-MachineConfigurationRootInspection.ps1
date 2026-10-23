#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/MachineConfigurationRootInspection.ps1')
$script:Passed = 0
$script:Skipped = 0
function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function Assert-Rejected([hashtable]$Configuration, [string]$Machine, [switch]$AllowLexical) {
    $json = $Configuration | ConvertTo-Json -Compress
    # All these fixtures must pass lexical validation before physical inspection.
    if (-not $AllowLexical) { ConvertFrom-EoMachineConfigurationJson -Json $json -ExpectedMachineId $Machine | Out-Null }
    $caught = $false
    try { Test-EoMachineConfigurationRoots -Json $json -ExpectedMachineId $Machine | Out-Null }
    catch {
        $caught = $true
        $reasons = @('configuration_root_inspection_failed')
        if ($AllowLexical) { $reasons += 'configuration_maintenance_local_overlap' }
        Assert-True ($_.Exception.Message -cin $reasons) 'Sanitized inspection reason'
    }
    Assert-True $caught 'Physical inspection rejects'
}
$testParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar)
$root = Join-Path $testParent ('eo-root-inspection-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root) | Out-Null
$junctions = [Collections.Generic.List[string]]::new()
try {
    Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
using System.Text;
public static class EoShortPathFixture {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern uint GetShortPathNameW(string path, StringBuilder result, uint size);
}
"@
    foreach ($machine in @('PC-A', 'PC-B')) {
        $configuration = Get-Content (Join-Path $PSScriptRoot "../Config/$machine.example.json") -Raw |
            ConvertFrom-Json -AsHashtable
        $fixture = Join-Path $root $machine
        $names = @($configuration.Keys | Where-Object { $_ -notin @('machineId','role','allowArchive') })
        foreach ($name in $names) {
            $directory = Join-Path $fixture ($name + '-long-directory-name')
            [IO.Directory]::CreateDirectory($directory) | Out-Null
            [IO.File]::WriteAllText((Join-Path $directory 'sentinel.txt'), 'synthetic-preserve')
            $configuration[$name] = $directory
        }
        $before = @([IO.Directory]::GetFileSystemEntries($fixture, '*', [IO.SearchOption]::AllDirectories) | Sort-Object)
        $result = Test-EoMachineConfigurationRoots -Json ($configuration | ConvertTo-Json) -ExpectedMachineId $machine
        Assert-True ($result.Status -ceq 'existing_roots_separated') "$machine existing roots accepted"
        Assert-True ($result.RootCount -eq $names.Count) 'All PC roots inspected'
        Assert-True (-not (($result | ConvertTo-Json).Contains($root))) 'No private metadata returned'
        $after = @([IO.Directory]::GetFileSystemEntries($fixture, '*', [IO.SearchOption]::AllDirectories) | Sort-Object)
        Assert-True (($before -join '|') -ceq ($after -join '|')) 'Inspection creates no entries'

        foreach ($name in $names) {
            $changed = $configuration.Clone()
            $missing = Join-Path $fixture ("missing-$name")
            $changed[$name] = $missing
            Assert-Rejected $changed $machine
            Assert-True (-not [IO.Directory]::Exists($missing)) 'Missing root never created'
            $changed[$name] = Join-Path $configuration[$name] 'sentinel.txt'
            Assert-Rejected $changed $machine
        }
        foreach ($name in @('maintenanceLocal', 'runtimeRoot')) {
            $alias = Join-Path $fixture ("junction-$name")
            New-Item -ItemType Junction -Path $alias -Target $configuration[$name] | Out-Null
            $junctions.Add($alias)
            $changed = $configuration.Clone()
            $changed[$name] = $alias
            Assert-Rejected $changed $machine
        }
        $container = Join-Path $fixture 'container'
        $nested = Join-Path $container 'nested'
        [IO.Directory]::CreateDirectory($nested) | Out-Null
        $alias = Join-Path $fixture 'junction-ancestor'
        New-Item -ItemType Junction -Path $alias -Target $container | Out-Null
        $junctions.Add($alias)
        $changed = $configuration.Clone()
        $changed.maintenanceLocal = Join-Path $alias 'nested'
        Assert-Rejected $changed $machine

        $buffer = [Text.StringBuilder]::new(32768)
        $length = [EoShortPathFixture]::GetShortPathNameW($configuration.maintenanceLocal, $buffer, $buffer.Capacity)
        $short = $buffer.ToString()
        if ($length -gt 0 -and $length -lt $buffer.Capacity -and
            -not $short.Equals($configuration.maintenanceLocal, [StringComparison]::OrdinalIgnoreCase)) {
            $changed = $configuration.Clone()
            $changed.runtimeRoot = $short
            $longCanonical = Get-EoExistingDirectoryCanonicalPath -LiteralPath $configuration.maintenanceLocal
            $shortCanonical = Get-EoExistingDirectoryCanonicalPath -LiteralPath $short
            Assert-True ($longCanonical.Equals($shortCanonical, [StringComparison]::OrdinalIgnoreCase)) 'Short and long aliases share canonical directory'
            Assert-Rejected $changed $machine -AllowLexical
            $changed.runtimeRoot = Join-Path $short 'nested'
            [IO.Directory]::CreateDirectory((Join-Path $configuration.maintenanceLocal 'nested')) | Out-Null
            Assert-Rejected $changed $machine -AllowLexical
        }
        else {
            $script:Skipped += 2
            Write-Host "$machine short-name overlap fixtures unavailable; 2 checks skipped"
        }
        # Inject alternate namespace observations after real metadata lookup.
        # These lexical names are disjoint; only canonical observations overlap.
        $script:OriginalInspector = ${function:Get-EoExistingDirectoryCanonicalPath}
        $script:AliasObservedPath = $configuration.runtimeRoot
        $localCanonical = Get-EoExistingDirectoryCanonicalPath -LiteralPath $configuration.maintenanceLocal
        try {
            function Get-EoExistingDirectoryCanonicalPath {
                param([Parameter(Mandatory)][string]$LiteralPath)
                if ($LiteralPath -ceq $script:AliasObservedPath) {
                    if ($script:AliasFault) { throw 'synthetic-private-error' }
                    return $script:AliasCanonical
                }
                return (& $script:OriginalInspector -LiteralPath $LiteralPath)
            }
            $script:AliasFault = $false
            foreach ($observed in @(
                $localCanonical,
                ($localCanonical + [IO.Path]::DirectorySeparatorChar + 'modeled-child'),
                $localCanonical.Substring(0, $localCanonical.LastIndexOf([IO.Path]::DirectorySeparatorChar))
            )) {
                $script:AliasCanonical = $observed
                Assert-Rejected $configuration $machine
            }
            $script:AliasFault = $true
            Assert-Rejected $configuration $machine
        }
        finally {
            Set-Item -LiteralPath Function:Get-EoExistingDirectoryCanonicalPath -Value $script:OriginalInspector
        }
        foreach ($name in $names) {
            Assert-True ([IO.File]::ReadAllText((Join-Path $configuration[$name] 'sentinel.txt')) -ceq 'synthetic-preserve') 'Original bytes preserved'
        }
    }
}
finally {
    $resolved = [IO.Path]::GetFullPath($root)
    if ([IO.Path]::GetDirectoryName($resolved).TrimEnd([IO.Path]::DirectorySeparatorChar) -cne $testParent -or
        -not [IO.Path]::GetFileName($resolved).StartsWith('eo-root-inspection-')) { throw 'Unexpected cleanup root' }
    foreach ($junction in $junctions) {
        $full = [IO.Path]::GetFullPath($junction)
        if (-not $full.StartsWith($resolved + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected junction cleanup' }
        [IO.Directory]::Delete($full) # Delete only the owned junction, never its target.
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Host "Root inspection tests passed: $script:Passed assertions; $script:Skipped unavailable short-name checks skipped"
