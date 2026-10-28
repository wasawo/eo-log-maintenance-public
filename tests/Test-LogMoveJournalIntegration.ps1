#requires -Version 7.6.7
[CmdletBinding()]
param([string]$PythonExecutable='python')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../Common/LogMoveSimulation.ps1')
$script:Passed=0
function Assert-True([bool]$Condition,[string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function New-State {
    @{Files=[Collections.Generic.List[object]]::new();Events=[Collections.Generic.List[object]]::new()}
}
function Add-Source($State,$Id,$Location='PC-A',$Path='20240101_12345678@a.txt') {
    $State.Files.Add(@{Id=$Id;Location=$Location;LogType='BattleLog';RelativePath=$Path;Bytes=[Text.Encoding]::UTF8.GetBytes('synthetic')})
}
$script:Fixture=[IO.Path]::Combine([IO.Path]::GetTempPath(),'eolm-move-journal-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $script:Fixture | Out-Null
function New-Journal {
    $path=Join-Path $script:Fixture ([guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $path | Out-Null
    $path
}
function Invoke-Model($State,$Journal,$Machine='PC-A',$Operation='Sync',$Faults=@{},[switch]$DryRun) {
    $config=Get-Content (Join-Path $PSScriptRoot "../Config/$Machine.example.json") -Raw | ConvertFrom-Json -AsHashtable
    if ($Machine -eq 'PC-A') { $config.allowArchive=$true }
    Invoke-EoLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId $Machine -Operation $Operation `
        -State $State -ReferenceDate ([datetime]'2026-10-28') -Faults $Faults -DryRun:$DryRun -JournalRoot $Journal -PythonExecutable $PythonExecutable
}
function Read-Summary($Journal,$Run,$Machine='PC-A',$Operation='Sync') {
    & (Join-Path $PSScriptRoot '../scripts/Show-MoveRun.ps1') -JournalRoot $Journal -RunId $Run -MachineId $Machine `
        -Operation $Operation -PythonExecutable $PythonExecutable -AsJson | ConvertFrom-Json -AsHashtable
}
try {
    foreach ($operation in @('Sync','Archive')) {
        $state=New-State; $journal=New-Journal
        $location=if ($operation -eq 'Sync') {'PC-A'}else{'Cloud'}
        Add-Source $state 'source' $location 'sub/20240101_12345678@a.txt'
        $first=Invoke-Model $state $journal 'PC-A' $operation @{source='delete_failed'}
        Assert-True ($first.CompletedSourceCount -eq 0) "$operation failed deletion is not completion"
        $firstEvent=@($state.Events|Where-Object {$_.Kind -eq 'prepared'})[0]
        Assert-True ($firstEvent.JournalRecord.observed_at_utc -is [string]) "$operation UTC timestamp is not converted to DateTime"
        $one=Read-Summary $journal $first.RunId 'PC-A' $operation
        Assert-True ($one.unresolved_source_count -eq 1) "$operation failure is recorded"
        $second=Invoke-Model $state $journal 'PC-A' $operation
        Assert-True ($second.CompletedSourceCount -eq 1) "$operation normal rerun completes remaining source"
        $two=Read-Summary $journal $second.RunId 'PC-A' $operation
        Assert-True ($two.newly_completed_source_count -eq 1) "$operation first real completion counted once"
        Assert-True ($two.unresolved_source_count -eq 0) "$operation retry does not introduce duplicate move identity"
        $prepared=@(Get-ChildItem $journal -Filter '*.json' | ForEach-Object {
            Get-Content $_.FullName -Raw | ConvertFrom-Json -AsHashtable
        } | Where-Object {$_.event_kind -eq 'prepared'})
        Assert-True ($prepared.Count -eq 2 -and $prepared[0].move_id -ceq $prepared[1].move_id) "$operation stable move ID across retries"
        $third=Invoke-Model $state $journal 'PC-A' $operation
        $three=Read-Summary $journal $third.RunId 'PC-A' $operation
        Assert-True ($three.newly_completed_source_count -eq 0) "$operation completed source not recounted"
        Assert-True ($three.unresolved_source_count -eq 0) "$operation old failed attempt does not remain pending after successful retry"
    }
    foreach ($fault in @('delete_unknown_absent','result_record_failed')) {
        $state=New-State; $journal=New-Journal
        Add-Source $state 'unknown'
        $first=Invoke-Model $state $journal -Faults @{unknown=$fault}
        Assert-True ($first.CompletedSourceCount -eq 0) "$fault remains unknown"
        if ($fault -eq 'result_record_failed') {
            $saved=@(Get-ChildItem $journal -Filter '*.json' | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json -AsHashtable -DateKind String })
            Assert-True ($saved.Count -eq 1 -and $saved[0].event_kind -ceq 'prepared') 'lost result leaves only the persisted preparation'
        }
        $second=Invoke-Model $state $journal
        $report=Read-Summary $journal $second.RunId
        Assert-True ($report.reconciled_source_count -eq 1 -and $report.unresolved_source_count -eq 0) "$fault reconciliation reaches persisted summary"
    }
    $state=New-State; $journal=New-Journal
    Add-Source $state 'dry'
    $before=$state|ConvertTo-Json -Depth 20 -Compress
    [void](Invoke-Model $state $journal -DryRun)
    Assert-True (($state|ConvertTo-Json -Depth 20 -Compress) -ceq $before) 'Dry Run preserves model'
    Assert-True (@(Get-ChildItem $journal -Force).Count -eq 0) 'Dry Run writes no journal'
    $state=New-State; $journal=New-Journal
    Add-Source $state 'bad'; Add-Source $state 'good' 'PC-A' '20240101_12345678@good.txt'
    Set-Content (Join-Path $journal 'partial.tmp') 'partial'
    $result=Invoke-Model $state $journal
    Assert-True ($result.CompletedSourceCount -eq 0 -and @($state.Files|Where-Object {$_.Location -eq 'PC-A'}).Count -eq 2) 'broken journal retains every source'
    $state=New-State; $journal=New-Journal
    Add-Source $state 'early'
    $result=Invoke-Model $state $journal -Faults @{early='copy_failed'}
    Assert-True ($result.Status -eq 'failure' -and $result.Results[0].Reason -eq 'copy_failed') 'failure before prepared remains in file results'
    Assert-True (@(Get-ChildItem $journal -Force).Count -eq 0) 'copy failure does not fabricate verified preparation'
    $state=New-State; $journal=New-Journal
    Add-Source $state 'unloaded-history'
    [void](Invoke-Model $state $journal -Faults @{'unloaded-history'='result_record_failed'})
    $fresh=Invoke-Model (New-State) $journal
    Assert-True ($fresh.Status -eq 'failure' -and $fresh.JournalUnresolvedSourceCount -eq 1) 'fresh empty model does not hide persisted pending movement as no-work'
    $state=New-State; $journal=New-Journal
    Set-Content (Join-Path $journal 'broken.tmp') 'partial'
    $fresh=Invoke-Model $state $journal
    Assert-True ($fresh.Status -eq 'failure' -and $fresh.JournalReadStatus -eq 'unconfirmed') 'unreadable journal prevents no-work even with zero model sources'
    $state=New-State; $journal=New-Journal
    Add-Source $state 'b-source' 'PC-B'
    $first=Invoke-Model $state $journal 'PC-B' 'Sync' @{'b-source'='delete_failed'}
    $second=Invoke-Model $state $journal 'PC-B' 'Sync'
    $report=Read-Summary $journal $second.RunId 'PC-B' 'Sync'
    Assert-True ($report.newly_completed_source_count -eq 1) 'PC-B sync persists valid role-scoped records'
    $state=New-State; $journal=New-Journal
    Add-Source $state 'cloud' 'Cloud'
    $denied=$false
    try { [void](Invoke-Model $state $journal 'PC-B' 'Archive') } catch { $denied=$_.Exception.Message -ceq 'move_archive_role_denied' }
    Assert-True ($denied -and @(Get-ChildItem $journal -Force).Count -eq 0) 'PC-B archive rejected before journal writes'
    Write-Host "PASS: $script:Passed journal integration assertions"
}
finally {
    $fixture=Get-Item -LiteralPath $script:Fixture
    $expectedParent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([char[]]'\/')
    if ($fixture.Parent.FullName -ne $expectedParent -or -not $fixture.Name.StartsWith('eolm-move-journal-') -or
        ($fixture.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'fixture_root_changed' }
    Remove-Item -LiteralPath $fixture.FullName -Recurse -Force
}
