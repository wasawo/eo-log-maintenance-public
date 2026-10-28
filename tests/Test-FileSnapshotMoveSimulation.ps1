#requires -Version 7.6.7
[CmdletBinding()]
param([string]$PythonExecutable='python')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../Common/OwnedLogMoveSimulation.ps1')
$script:Passed=0
function Assert-True([bool]$Condition,[string]$Name) {
    if (-not $Condition) {throw "ASSERTION FAILED: $Name"}; $script:Passed++
}
function New-State { @{Files=[Collections.Generic.List[object]]::new();Events=[Collections.Generic.List[object]]::new()} }
function Get-FileSnapshot($Roots) {
    $values=[ordered]@{}
    foreach($root in $Roots) { foreach($file in @(Get-ChildItem -LiteralPath $root.path -File -Recurse | Sort-Object FullName)) {$values[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash} }
    $values|ConvertTo-Json -Compress
}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('eolm-snapshot-model-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture|Out-Null
try {
    foreach($case in @(@{Machine='PC-A';Operation='Sync'},@{Machine='PC-B';Operation='Sync'},@{Machine='PC-A';Operation='Archive'})) {
        $base=Join-Path $fixture ($case.Machine+'-'+$case.Operation)
        foreach($part in @('journal','journal.lifecycle','reports')) {New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
        $roots=@(foreach($side in @('source','destination')) {foreach($kind in @('BattleLog','ErrorReport')) {
            $path=Join-Path $base ($side+'-'+$kind);New-Item -ItemType Directory -Path $path|Out-Null
            @{side=$side;log_type=$kind;path=$path}
        }})
        New-Item -ItemType Directory -Path (Join-Path $roots[0].path 'nested')|Out-Null
        [IO.File]::WriteAllText((Join-Path $roots[0].path 'nested/20240101_12345678@same.txt'),'same synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[2].path '20240101_12345678@same.txt'),'same synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[0].path '20240101_12345678@conflict.txt'),'source synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[2].path '20240101_12345678@conflict.txt'),'destination synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[0].path '20261001_12345678@current.txt'),'retain synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[1].path '20240101_12345678.txt'),'error synthetic')
        [IO.File]::WriteAllText((Join-Path $roots[1].path 'unclassifiable.txt'),'invalid synthetic')
        $config=Get-Content (Join-Path $PSScriptRoot "../Config/$($case.Machine).example.json") -Raw|ConvertFrom-Json -AsHashtable
        if($case.Machine -eq 'PC-A') {$config.allowArchive=$true}
        $state=New-State
        $arguments=@{ConfigurationJson=($config|ConvertTo-Json -Compress);MachineId=$case.Machine;Operation=$case.Operation;State=$state;
            ReferenceDate=[datetime]'2026-10-28';LifecycleRoot=(Join-Path $base 'journal.lifecycle');JournalRoot=(Join-Path $base 'journal');
            ReportRoot=(Join-Path $base 'reports');PythonExecutable=$PythonExecutable;SnapshotRoots=$roots}
        $before=Get-FileSnapshot $roots
        $dry=Invoke-EoOwnedLogMoveSimulation @arguments -DryRun
        Assert-True ($dry.Status -ceq 'failure' -and $dry.LifecycleStatus -ceq 'not_started' -and $state.Files.Count -eq 0) 'Dry Run reports invalid input but preserves caller model'
        Assert-True (@(Get-ChildItem $arguments.LifecycleRoot -Force).Count -eq 0 -and @(Get-ChildItem $arguments.JournalRoot -Force).Count -eq 0) 'Dry Run never creates lifecycle or journal'
        $run=Invoke-EoOwnedLogMoveSimulation @arguments
        Assert-True ($run.LifecycleStatus -ceq 'confirmed' -and $run.ReportSaveStatus -ceq 'confirmed') 'filesystem input reaches owned journal and final report'
        Assert-True ($run.Status -ceq 'partial_failure' -and $run.CompletedSourceCount -eq 2 -and $run.UnresolvedSourceCount -eq 2) 'both log types flow through route selection and independent failures'
        Assert-True ($run.RunReportSummary.inventory_source_count -eq 5) 'inventory includes invalid and retained-period source files'
        Assert-True ((Get-FileSnapshot $roots) -ceq $before) 'all physical sources and destinations remain byte-identical'
        $saved=Get-Content (Join-Path $arguments.ReportRoot ($run.RunId+'.json')) -Raw|ConvertFrom-Json -AsHashtable
        Assert-True (@($saved.results|Where-Object {$_.reason_code -ceq 'content_conflict'}).Count -eq 1 -and
            @($saved.results|Where-Object {$_.reason_code -ceq 'filename_invalid'}).Count -eq 1) 'early failures survive persistent report'
        $count=@(Get-ChildItem $arguments.LifecycleRoot -File).Count; $blocked=$false
        try {[void](Invoke-EoOwnedLogMoveSimulation @arguments)}catch{$blocked=$_.Exception.Message -ceq 'simulation_snapshot_state_not_empty'}
        Assert-True ($blocked -and @(Get-ChildItem $arguments.LifecycleRoot -File).Count -eq $count) 'nonempty model is never silently replaced'
        $arguments.State=New-State; $roots[0].path=Join-Path $base 'missing-source'
        $journalCount=@(Get-ChildItem $arguments.JournalRoot -File).Count; $runId=[guid]::NewGuid(); $blocked=$false
        try {[void](Invoke-EoOwnedLogMoveSimulation @arguments -RunId $runId)}catch{$blocked=$_.Exception.Message -ceq 'owned_simulation_interrupted'}
        $ended=Get-Content (Join-Path $arguments.LifecycleRoot ($runId.ToString('D')+'.ended.json')) -Raw|ConvertFrom-Json -AsHashtable
        Assert-True ($blocked -and $ended.disposition -ceq 'interrupted' -and $arguments.State.Files.Count -eq 0 -and
            @(Get-ChildItem $arguments.JournalRoot -File).Count -eq $journalCount) 'incomplete enumeration never enters model move or replaces caller state'
    }
    $base=Join-Path $fixture 'empty'
    foreach($part in @('journal','journal.lifecycle','reports')) {New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
    $roots=@(foreach($side in @('source','destination')) {foreach($kind in @('BattleLog','ErrorReport')) {
        $path=Join-Path $base ($side+'-'+$kind);New-Item -ItemType Directory -Path $path|Out-Null
        @{side=$side;log_type=$kind;path=$path}
    }})
    $arguments.State=New-State; $arguments.SnapshotRoots=$roots
    $arguments.LifecycleRoot=Join-Path $base 'journal.lifecycle';$arguments.JournalRoot=Join-Path $base 'journal';$arguments.ReportRoot=Join-Path $base 'reports'
    $run=Invoke-EoOwnedLogMoveSimulation @arguments
    Assert-True ($run.Status -ceq 'no_work' -and $run.LifecycleStatus -ceq 'confirmed' -and $run.RunReportSummary.inventory_source_count -eq 0) 'complete empty filesystem snapshot is distinct from enumeration failure'
    Write-Host "PASS: $script:Passed file snapshot integration assertions"
}
finally {
    $item=Get-Item -LiteralPath $fixture -Force
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    if($item.Parent.FullName.TrimEnd('\') -cne $parent -or -not $item.Name.StartsWith('eolm-snapshot-model-') -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'synthetic_cleanup_root_invalid'}
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
}
