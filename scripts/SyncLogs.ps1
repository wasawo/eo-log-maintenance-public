#requires -Version 7.6.7
# EOLM-SYNTHETIC-ONLY: S1 does not provide a deployable runtime.
[CmdletBinding()]
param(
    [switch]$Synthetic,
    [string]$SyntheticRoot,
    [ValidateSet('PC-A', 'PC-B')][string]$MachineId = 'PC-B',
    [ValidateSet('Sync', 'Archive')][string]$Operation = 'Sync',
    [datetime]$ReferenceDate = (Get-Date).Date,
    [ValidateSet('none', 'copy_failed', 'hash_mismatch', 'enumeration_failed')]
    [string]$MockFault = 'none',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/SyntheticLogTransfer.ps1')
$report = Invoke-EoSyntheticLogTransfer -Route Sync -Synthetic:$Synthetic -SyntheticRoot $SyntheticRoot `
    -MachineId $MachineId -Operation $Operation -ReferenceDate $ReferenceDate -MockFault $MockFault -DryRun:$DryRun
$report | ConvertTo-Json -Depth 6
if ($report.FailureCount -gt 0 -or $report.HeldCount -gt 0) { exit 1 }
exit 0
