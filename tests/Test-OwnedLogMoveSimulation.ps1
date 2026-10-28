#requires -Version 7.6.7
[CmdletBinding()]
param([string]$PythonExecutable='python')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../Common/OwnedLogMoveSimulation.ps1')
$script:Passed=0
function Assert-True([bool]$Condition,[string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('eolm-owned-model-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
try {
    foreach ($case in @(@{Machine='PC-A';Operation='Sync'},@{Machine='PC-A';Operation='Archive'},@{Machine='PC-B';Operation='Sync'})) {
        $operation=$case.Operation; $machine=$case.Machine
        $base=Join-Path $fixture ($machine+'-'+$operation)
        foreach ($part in @('journal.lifecycle','journal','reports')) { New-Item -ItemType Directory -Path (Join-Path $base $part) -Force | Out-Null }
        $state=@{Files=[Collections.Generic.List[object]]::new();Events=[Collections.Generic.List[object]]::new()}
        $location=if ($operation -eq 'Sync') {$machine}else{'Cloud'}
        $state.Files.Add(@{Id='synthetic';Location=$location;LogType='BattleLog';RelativePath='nested/20240101_12345678@a.txt';Bytes=[Text.Encoding]::UTF8.GetBytes('synthetic')})
        $config=Get-Content (Join-Path $PSScriptRoot "../Config/$machine.example.json") -Raw | ConvertFrom-Json -AsHashtable
        if ($machine -eq 'PC-A') { $config.allowArchive=$true }
        $arguments=@{ConfigurationJson=($config|ConvertTo-Json -Compress);MachineId=$machine;Operation=$operation;State=$state;
            ReferenceDate=[datetime]'2026-10-28';LifecycleRoot=(Join-Path $base 'journal.lifecycle');JournalRoot=(Join-Path $base 'journal');
            ReportRoot=(Join-Path $base 'reports');PythonExecutable=$PythonExecutable}
        $run=Invoke-EoOwnedLogMoveSimulation @arguments
        Assert-True ($run.LifecycleStatus -ceq 'confirmed' -and $run.CompletedSourceCount -eq 1 -and $run.ReportSaveStatus -ceq 'confirmed') "$operation ownership wraps real model/journal/report calls"
        $ended=Get-Content (Join-Path $arguments.LifecycleRoot ($run.RunId+'.ended.json')) -Raw | ConvertFrom-Json -AsHashtable
        Assert-True ($ended.disposition -ceq 'finished' -and $ended.operation_status -ceq 'success') "$operation terminal processing state recorded separately from per-file journal"
        Assert-True ($ended.report_sha256 -ceq (Get-FileHash (Join-Path $arguments.ReportRoot ($run.RunId+'.json')) -Algorithm SHA256).Hash.ToLowerInvariant()) "$operation ending binds exact final report bytes"
        Assert-True (@(Get-ChildItem $arguments.LifecycleRoot -Filter '*.lock').Count -eq 0) "$operation normal exit removes only owned lock"
        $before=$state|ConvertTo-Json -Depth 30 -Compress
        $denied=$false
        try { [void](Invoke-EoOwnedLogMoveSimulation @arguments -RunId ([guid]$run.RunId)) } catch {$denied=$_.Exception.Message -ceq 'owned_simulation_interrupted'}
        Assert-True ($denied -and ($state|ConvertTo-Json -Depth 30 -Compress) -ceq $before) "$operation reused run ID rejected before processing model"
        $count=@(Get-ChildItem $base -Recurse -File).Count
        $dry=Invoke-EoOwnedLogMoveSimulation @arguments -DryRun
        Assert-True ($dry.LifecycleStatus -ceq 'not_started' -and @(Get-ChildItem $base -Recurse -File).Count -eq $count) "$operation Dry Run bypasses all ordinary lifecycle writes"
        $state.Files='invalid'
        $runId=[guid]::NewGuid(); $denied=$false
        try { [void](Invoke-EoOwnedLogMoveSimulation @arguments -RunId $runId) } catch {$denied=$_.Exception.Message -ceq 'owned_simulation_interrupted'}
        $ended=Get-Content (Join-Path $arguments.LifecycleRoot ($runId.ToString('D')+'.ended.json')) -Raw | ConvertFrom-Json -AsHashtable
        Assert-True ($denied -and $ended.disposition -ceq 'interrupted' -and $null -eq $ended.operation_status) "$operation worker validation exception leaves an interrupted lifecycle"
    }
    Write-Host "PASS: $script:Passed owned model assertions"
}
finally {
    $item=Get-Item -LiteralPath $fixture -Force
    $expectedParent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    if ($item.Parent.FullName.TrimEnd('\') -cne $expectedParent -or -not $item.Name.StartsWith('eolm-owned-model-') -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'synthetic_cleanup_root_invalid' }
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
}
