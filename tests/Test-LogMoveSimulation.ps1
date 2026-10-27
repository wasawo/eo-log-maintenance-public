#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/LogMoveSimulation.ps1')
$script:Passed = 0

function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function New-State {
    return @{ Files = [Collections.Generic.List[object]]::new(); Events = [Collections.Generic.List[object]]::new() }
}
function Add-File($State, $Id, $Location, $LogType, $RelativePath, $Text = 'synthetic log') {
    $State.Files.Add(@{
        Id = $Id; Location = $Location; LogType = $LogType
        RelativePath = $RelativePath; Bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    })
}
function Invoke-Scenario($State, $Machine = 'PC-A', $Operation = 'Sync', $Faults = @{}, [switch]$DryRun, $Date = [datetime]'2026-10-28') {
    $config = Get-Content (Join-Path $PSScriptRoot "../Config/$Machine.example.json") -Raw | ConvertFrom-Json -AsHashtable
    if ($Machine -eq 'PC-A') { $config.allowArchive = $true }
    return Invoke-EoLogMoveSimulation -ConfigurationJson ($config | ConvertTo-Json -Compress) `
        -MachineId $Machine -Operation $Operation -State $State -ReferenceDate $Date -Faults $Faults -DryRun:$DryRun
}

# AC-01/02/03/04: both machines, both routes, recursive names, late arrival.
$state = New-State
Add-File $state 'a-old' 'PC-A' 'BattleLog' 'nested/deeper/20241231_12345678@a.txt'
Add-File $state 'a-month' 'PC-A' 'BattleLog' '20261001_12345678@a.txt'
Add-File $state 'b-year' 'PC-B' 'ErrorReport' 'nested/20251231_12345678.txt'
Add-File $state 'b-now' 'PC-B' 'ErrorReport' '20260101_12345678.txt'
$syncA = Invoke-Scenario $state
Assert-True ($syncA.CompletedSourceCount -eq 1) 'A moves old log only'
Assert-True (@($state.Files | Where-Object { $_.Location -eq 'Archive' }).Count -eq 0) 'old A log goes through cloud'
$archive = Invoke-Scenario $state 'PC-A' 'Archive'
Assert-True ($archive.CompletedSourceCount -eq 1) 'archive works without B run'
Assert-True (@($state.Files | Where-Object { $_.Location -eq 'Archive' -and $_.RelativePath -eq '20241231_12345678@a.txt' }).Count -eq 1) 'archive flattened'
$syncB = Invoke-Scenario $state 'PC-B'
Assert-True ($syncB.CompletedSourceCount -eq 1) 'B keeps current year error log'
Add-File $state 'b-late' 'PC-B' 'BattleLog' 'late/20231231_12345678@b.txt'
[void](Invoke-Scenario $state 'PC-B')
$archive = Invoke-Scenario $state 'PC-A' 'Archive'
Assert-True ($archive.CompletedSourceCount -eq 1) 'late B log archives next run'
Assert-True (@($state.Files | Where-Object { $_.Location -eq 'Cloud' -and $_.LogType -eq 'ErrorReport' }).Count -eq 1) 'prior-year error remains in cloud'
$before = $state | ConvertTo-Json -Depth 12 -Compress
$rejected = $false
try { Invoke-Scenario $state 'PC-B' 'Archive' | Out-Null } catch { $rejected = $_.Exception.Message -ceq 'move_archive_role_denied' }
Assert-True $rejected 'B archive denied before effects'
Assert-True (($state | ConvertTo-Json -Depth 12 -Compress) -ceq $before) 'B rejection preserves state'

# AC-05/06/07: duplicate sources are counted individually, conflict is retained.
foreach ($operation in @('Sync', 'Archive')) {
    $state = New-State
    $location = if ($operation -eq 'Sync') { 'PC-A' } else { 'Cloud' }
    $target = if ($operation -eq 'Sync') { 'Cloud' } else { 'Archive' }
    foreach ($id in @('first', 'second', 'third')) {
        Add-File $state $id $location 'BattleLog' "$id/20240101_12345678@same.txt" $(if ($id -eq 'third') { 'different' } else { 'same' })
    }
    $result = Invoke-Scenario $state 'PC-A' $operation
    Assert-True ($result.CompletedSourceCount -eq 2 -and $result.UnresolvedSourceCount -eq 1) "$operation per-source completion"
    Assert-True ($result.Status -eq 'partial_failure') "$operation conflict visible"
    Assert-True (@($state.Files | Where-Object { $_.Location -eq $target }).Count -eq 1) "$operation reuses identical destination"
    Assert-True (@($state.Files | Where-Object { $_.Id -eq 'third' }).Count -eq 1) "$operation conflicting source retained"
    Assert-True ($result.Results[2].Reason -eq 'content_conflict') "$operation no suffix or overwrite"
    foreach ($fault in @('copy_failed', 'destination_changed', 'record_failed', 'source_changed', 'source_replaced', 'verification_unknown', 'delete_failed')) {
        $state = New-State
        Add-File $state 'bad' $location 'BattleLog' '20240101_12345678@bad.txt'
        Add-File $state 'good' $location 'BattleLog' '20240101_12345678@good.txt'
        $result = Invoke-Scenario $state 'PC-A' $operation @{ bad = $fault }
        Assert-True ($result.CompletedSourceCount -eq 1 -and $result.UnresolvedSourceCount -eq 1) "$operation $fault allows independent file"
        Assert-True (@($state.Files | Where-Object { $_.Location -eq $location }).Count -eq 1) "$operation $fault retains source"
        if ($fault -in @('delete_failed', 'record_failed')) {
            $count = @($state.Files | Where-Object { $_.Location -eq $target }).Count
            $rerun = Invoke-Scenario $state 'PC-A' $operation
            Assert-True ($rerun.CompletedSourceCount -eq 1) "$operation normal rerun completes remaining source"
            Assert-True (@($state.Files | Where-Object { $_.Location -eq $target }).Count -eq $count) "$operation rerun reuses target"
        }
    }
    # Ambiguous cloud names must not select an arbitrary object.
    $state = New-State
    Add-File $state 'source' $location 'BattleLog' 'sub/20240101_12345678@a.txt'
    Add-File $state 'dest-1' $target 'BattleLog' '20240101_12345678@a.txt'
    Add-File $state 'dest-2' $target 'BattleLog' '20240101_12345678@a.txt'
    $result = Invoke-Scenario $state 'PC-A' $operation
    Assert-True ($result.Results[0].Reason -eq 'destination_ambiguous') "$operation ambiguous destination retained"

    # AC-08/09: unknown response is not immediately a completion or no-work.
    foreach ($fault in @('delete_unknown_absent', 'delete_unknown_present')) {
        $state = New-State
        Add-File $state 'unknown' $location 'BattleLog' '20240101_12345678@unknown.txt'
        $first = Invoke-Scenario $state 'PC-A' $operation @{ unknown = $fault }
        Assert-True ($first.Status -eq 'failure' -and $first.Results[0].Outcome -eq 'unknown') "$operation records unknown response"
        $second = Invoke-Scenario $state 'PC-A' $operation
        Assert-True ($second.CompletedSourceCount -eq 1) "$operation resolves unknown on rerun"
        $expected = if ($fault -eq 'delete_unknown_absent') { 'reconciled_completion' } else { 'delete_confirmed' }
        Assert-True ($second.Results[0].Reason -eq $expected) "$operation distinguishes reconciliation from delete success"
        $third = Invoke-Scenario $state 'PC-A' $operation
        Assert-True ($third.Status -eq 'no_work' -and $third.CompletedSourceCount -eq 0) "$operation no double counting"
        Assert-True ($state.Events[1].Outcome -eq 'unknown') "$operation old unknown event unchanged"
    }
    foreach ($problem in @('destination_missing', 'destination_modified', 'record_missing', 'record_mismatch', 'presence_unknown', 'recreated')) {
        $state = New-State
        Add-File $state 'unknown' $location 'BattleLog' '20240101_12345678@unknown.txt'
        [void](Invoke-Scenario $state 'PC-A' $operation @{ unknown = 'delete_unknown_absent' })
        $faults = @{}
        switch ($problem) {
            'destination_missing' { $state.Files.Clear() }
            'destination_modified' { $state.Files[0].Bytes = [byte[]]@(9) }
            'record_missing' { $state.Events.RemoveAt(0) }
            'record_mismatch' { $state.Events[0].Sha256 = '0' * 64 }
            'presence_unknown' { $faults.unknown = 'presence_unknown' }
            'recreated' { Add-File $state 'replacement' $location 'BattleLog' '20240101_12345678@unknown.txt' 'new' }
        }
        if ($problem -eq 'recreated') { $faults.replacement = 'verification_unknown' }
        $result = Invoke-Scenario $state 'PC-A' $operation $faults
        Assert-True ($result.Status -eq 'failure' -and $result.CompletedSourceCount -eq 0) "$operation $problem cannot complete or report no-work"
    }
    $state = New-State
    Add-File $state 'unrecorded' $location 'BattleLog' '20240101_12345678@unknown.txt'
    $result = Invoke-Scenario $state 'PC-A' $operation @{ unrecorded = 'result_record_failed' }
    Assert-True ($result.Status -eq 'failure' -and $result.CompletedSourceCount -eq 0) "$operation removal with missing result is not completed"
    Assert-True ($state.Events.Count -eq 1 -and $state.Events[0].Kind -eq 'prepared') "$operation only pre-delete binding survives"
    $before = $state | ConvertTo-Json -Depth 12 -Compress
    $result = Invoke-Scenario $state 'PC-A' $operation -DryRun
    Assert-True ($result.Status -eq 'failure' -and $result.UnresolvedSourceCount -eq 1) "$operation dry run does not hide prior unresolved attempt"
    Assert-True (($state | ConvertTo-Json -Depth 12 -Compress) -ceq $before) "$operation dry run leaves pending record unchanged"
    $result = Invoke-Scenario $state 'PC-A' $operation
    Assert-True ($result.CompletedSourceCount -eq 1 -and $result.Results[0].Reason -eq 'reconciled_completion') "$operation missing result reconciles from valid binding"
}

# Fixed boundary dates and invalid filenames; LastWriteTime is never an input.
foreach ($case in @(
    @('Sync', 'BattleLog', '20260930_12345678@a.txt', '2026-10-01', 1),
    @('Sync', 'BattleLog', '20261001_12345678@a.txt', '2026-10-31', 0),
    @('Sync', 'ErrorReport', '20251231_12345678.txt', '2026-01-01', 1),
    @('Archive', 'BattleLog', '20251231_12345678@a.txt', '2026-01-01', 1),
    @('Archive', 'ErrorReport', '20241231_12345678.txt', '2026-01-01', 1),
    @('Archive', 'ErrorReport', '20250101_12345678.txt', '2026-01-01', 0),
    @('Sync', 'BattleLog', '20240229_12345678@a.txt', '2024-03-01', 1)
)) {
    $state = New-State
    $location = if ($case[0] -eq 'Sync') { 'PC-A' } else { 'Cloud' }
    Add-File $state 'boundary' $location $case[1] $case[2]
    $result = Invoke-Scenario $state 'PC-A' $case[0] @{} -Date ([datetime]$case[3])
    Assert-True ($result.CompletedSourceCount -eq $case[4]) "boundary $($case[2]) $($case[3])"
}
$state = New-State
Add-File $state 'invalid' 'PC-A' 'BattleLog' '20260230_12345678@a.txt'
Add-File $state 'upper' 'PC-A' 'ErrorReport' '20250101_12345678.TXT'
Add-File $state 'good' 'PC-A' 'BattleLog' '20250101_12345678@a.txt'
$before = $state | ConvertTo-Json -Depth 12 -Compress
$dry = Invoke-Scenario $state -DryRun
Assert-True (($state | ConvertTo-Json -Depth 12 -Compress) -ceq $before) 'Dry Run has zero model writes or events'
Assert-True ($dry.CompletedSourceCount -eq 0 -and $dry.UnresolvedSourceCount -eq 2) 'Dry Run does not hide invalid names'
$result = Invoke-Scenario $state
Assert-True ($result.Status -eq 'partial_failure' -and $result.CompletedSourceCount -eq 1) 'invalid dates and case remain visible'
Assert-True ($result.SimulationOnly) 'results explicitly identify simulation'
$empty = Invoke-Scenario (New-State)
Assert-True ($empty.Status -eq 'no_work') 'clean empty state is no-work'
$state = New-State
Add-File $state 'empty-content' 'PC-A' 'BattleLog' '20240101_12345678@empty.txt' ''
$result = Invoke-Scenario $state
Assert-True ($result.CompletedSourceCount -eq 1 -and $state.Files[0].Bytes.Length -eq 0) 'empty file is compared and moved'
$state = New-State
Add-File $state 'cross-route' 'PC-A' 'BattleLog' '20240101_12345678@old.txt'
[void](Invoke-Scenario $state -Faults @{ 'cross-route' = 'delete_unknown_absent' })
[void](Invoke-Scenario $state 'PC-A' 'Archive')
$result = Invoke-Scenario $state
Assert-True ($result.Status -eq 'failure' -and $result.Results[0].Outcome -eq 'unknown') 'next-route archive is not inferred as original sync completion'
$state = New-State
Add-File $state 'disabled' 'Cloud' 'BattleLog' '20240101_12345678@disabled.txt'
$before = $state | ConvertTo-Json -Depth 12 -Compress
$config = Get-Content (Join-Path $PSScriptRoot '../Config/PC-A.example.json') -Raw
$rejected = $false
try {
    Invoke-EoLogMoveSimulation -ConfigurationJson $config -MachineId 'PC-A' -Operation 'Archive' `
        -State $state -ReferenceDate ([datetime]'2026-10-28') | Out-Null
}
catch { $rejected = $_.Exception.Message -ceq 'move_archive_role_denied' }
Assert-True $rejected 'disabled archive configuration rejected'
Assert-True (($state | ConvertTo-Json -Depth 12 -Compress) -ceq $before) 'disabled archive has no model effects'
Write-Host "PASS: $script:Passed log-move simulation assertions"
