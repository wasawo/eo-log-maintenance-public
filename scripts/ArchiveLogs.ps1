#requires -Version 7.6.7
# EOLM-SYNTHETIC-ONLY: S2 does not provide a deployable runtime.
[CmdletBinding()]
param(
    [switch]$Synthetic,
    [string]$SyntheticRoot,
    [ValidateSet('PC-A', 'PC-B')][string]$MachineId = 'PC-A',
    [ValidateSet('Sync', 'Archive')][string]$Operation = 'Archive',
    [datetime]$ReferenceDate = (Get-Date).Date,
    [ValidateSet('none', 'copy_failed', 'hash_mismatch', 'enumeration_failed')]
    [string]$MockFault = 'none',
    [switch]$DriveApiMock,
    [switch]$IsolatedDrive,
    [string]$ConnectionConfig,
    [string]$PythonExecutable = 'python',
    [ValidateSet('none','auth_denied','api_error','upload_unknown','content_changed','version_changed','duplicate_name')]
    [string]$ApiFault = 'none',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/SyntheticLogTransfer.ps1')
$report = Invoke-EoSyntheticLogTransfer -Route Archive -Synthetic:$Synthetic -SyntheticRoot $SyntheticRoot `
    -MachineId $MachineId -Operation $Operation -ReferenceDate $ReferenceDate -MockFault $MockFault -DryRun:$DryRun `
    -DriveApiMock:$DriveApiMock -IsolatedDrive:$IsolatedDrive -ConnectionConfig $ConnectionConfig -PythonExecutable $PythonExecutable -ApiFault $ApiFault
$report | ConvertTo-Json -Depth 6
if ($report.FailureCount -gt 0 -or $report.HeldCount -gt 0) { exit 1 }
exit 0
