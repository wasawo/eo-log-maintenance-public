#requires -Version 7.6.7
[CmdletBinding()]
param([string]$PythonExecutable='python')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../Common/OwnedLogMoveSimulation.ps1')
$script:Passed=0
function Assert-True([bool]$Condition,[string]$Name) {
    if(-not $Condition){throw "ASSERTION FAILED: $Name"};$script:Passed++
}
function New-State($Location) {
    $state=@{Files=[Collections.Generic.List[object]]::new();Events=[Collections.Generic.List[object]]::new()}
    foreach($id in @('one','two')) {$state.Files.Add(@{Id=$id;Location=$Location;LogType='BattleLog';RelativePath="20240101_12345678@$id.txt";Bytes=[Text.Encoding]::UTF8.GetBytes('synthetic')})}
    return $state
}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('eolm-owner-loss-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture|Out-Null
try {
    $config=Get-Content (Join-Path $PSScriptRoot '../Config/PC-A.example.json') -Raw|ConvertFrom-Json -AsHashtable
    $config.allowArchive=$true
    foreach($operation in @('Sync','Archive')) {
        $location=if($operation -eq 'Sync'){'PC-A'}else{'Cloud'}
        foreach($phase in @('before_source','before_destination_write','before_prepared','before_delete','after_delete','before_outcome','before_summary','before_report')) {
            $base=Join-Path $fixture ([guid]::NewGuid().ToString('N'))
            foreach($part in @('journal','reports')){New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
            $state=New-State $location
            $control=@{Calls=0;Failed=$false;Phase=$phase}
            $check={param($Point,$SourceId) $control.Calls++; if($Point -ceq $control.Phase){$control.Failed=$true;return $false};return $true}
            $run=Invoke-EoLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId 'PC-A' -Operation $operation `
                -State $state -ReferenceDate ([datetime]'2026-10-28') -JournalRoot (Join-Path $base 'journal') -ReportRoot (Join-Path $base 'reports') `
                -PythonExecutable $PythonExecutable -OwnershipCheck $check
            Assert-True ($control.Failed -and $run.OwnershipStatus -ceq 'unconfirmed' -and $run.ReportSaveStatus -ceq 'unconfirmed') "$operation $phase suppresses final report after lost ownership"
            Assert-True (@(Get-ChildItem (Join-Path $base 'reports') -File).Count -eq 0) "$operation $phase creates no success report"
            $sources=@($state.Files|Where-Object {$_.Location -ceq $location})
            if($phase -in @('before_summary','before_report')) {
                Assert-True ($run.CompletedSourceCount -eq 2 -and $run.Status -ceq 'partial_failure') "$operation $phase preserves previously confirmed file completions"
            }
            elseif($phase -in @('after_delete','before_outcome')) {
                Assert-True ($sources.Count -eq 1 -and $run.CompletedSourceCount -eq 0 -and $run.Results[0].Outcome -ceq 'unknown') "$operation $phase does not invent source restoration or completion"
            }
            else {Assert-True ($sources.Count -eq 2 -and $run.CompletedSourceCount -eq 0) "$operation $phase retains both sources"}
            if($phase -notin @('before_summary','before_report')) {
                Assert-True (@($state.Files|Where-Object {$_.Location -cne $location -and $_.RelativePath -like '*two.txt'}).Count -eq 0) "$operation $phase stops later source copy"
            }
            if($phase -in @('before_delete','after_delete','before_outcome')) {
                $records=@(Get-ChildItem (Join-Path $base 'journal') -File|ForEach-Object {Get-Content $_.FullName -Raw|ConvertFrom-Json -AsHashtable})
                Assert-True ($records.Count -eq 1 -and $records[0].event_kind -ceq 'prepared') "$operation $phase leaves prepared pending without fabricated deletion result"
            }
            if($phase -eq 'before_source'){Assert-True ($control.Calls -eq 1) 'ownership failure is sticky even if callback would later return true'}
        }
        foreach($target in @('source','destination')) {
            $state=New-State $location
            $base=Join-Path $fixture ([guid]::NewGuid().ToString('N'))
            foreach($part in @('journal','reports')){New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
            $check={param($Point,$SourceId) if($Point -ceq 'before_delete' -and $SourceId -ceq 'one') {
                $file=if($target -ceq 'source'){@($state.Files|Where-Object {$_.Id -ceq 'one'})[0]}else{@($state.Files|Where-Object {$_.Location -cne $location})[0]}
                $file.Bytes=[byte[]]@(99)
            };return $true}
            $run=Invoke-EoLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId 'PC-A' -Operation $operation `
                -State $state -ReferenceDate ([datetime]'2026-10-28') -OwnershipCheck $check -JournalRoot (Join-Path $base 'journal') `
                -ReportRoot (Join-Path $base 'reports') -PythonExecutable $PythonExecutable
            Assert-True (@($state.Files|Where-Object {$_.Id -ceq 'one'}).Count -eq 1 -and $run.Results[0].Outcome -ceq 'retained') "$operation rechecks $target content after ownership acknowledgement"
            $prepared=@($state.Events|Where-Object {$_.Kind -ceq 'prepared' -and $_.SourceId -ceq 'one'})[0].JournalRecord.record_id
            $result=@(Get-ChildItem (Join-Path $base 'journal') -File|ForEach-Object {Get-Content $_.FullName -Raw|ConvertFrom-Json -AsHashtable}|Where-Object {
                $_.event_kind -ceq 'deletion_result' -and $_.prior_record_refs[0].record_id -ceq $prepared
            })[0]
            Assert-True ($result.event_data.request_outcome -ceq 'not_sent' -and $null -eq $result.event_data.destination_current) "$operation $target change never substitutes prepared content for unknown current verification"
        }
        $base=Join-Path $fixture ([guid]::NewGuid().ToString('N'))
        foreach($part in @('journal','reports')){New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
        $state=New-State $location;$state.Files.RemoveAt(1)
        $arguments=@{ConfigurationJson=($config|ConvertTo-Json -Compress);MachineId='PC-A';Operation=$operation;State=$state;
            ReferenceDate=[datetime]'2026-10-28';JournalRoot=(Join-Path $base 'journal');ReportRoot=(Join-Path $base 'reports');PythonExecutable=$PythonExecutable}
        [void](Invoke-EoLogMoveSimulation @arguments -Faults @{one='result_record_failed'})
        $count=@(Get-ChildItem $arguments.JournalRoot -File).Count
        $run=Invoke-EoLogMoveSimulation @arguments -OwnershipCheck {param($Point) $Point -cne 'before_reconcile'}
        Assert-True ($run.CompletedSourceCount -eq 0 -and $run.OwnershipStatus -ceq 'unconfirmed' -and
            @(Get-ChildItem $arguments.JournalRoot -File).Count -eq $count) "$operation lost ownership prevents historical reconciliation writes"
        $run=Invoke-EoLogMoveSimulation @arguments -OwnershipCheck {param($Point) $Point -cne 'before_outcome'}
        Assert-True ($run.Results[0].Reason -ceq 'ownership_unconfirmed_during_reconciliation' -and $run.CompletedSourceCount -eq 0 -and
            @(Get-ChildItem $arguments.JournalRoot -File).Count -eq $count) "$operation reconciliation recording failure is not labelled as this-run deletion"
    }
    # R-01: Q11 observations must follow the last waiting ownership callback.
    foreach($operation in @('Sync','Archive')) {
        $location=if($operation -ceq 'Sync'){'PC-A'}else{'Cloud'}
        foreach($withJournal in @($false,$true)) {
            $phases=if($withJournal){@('before_reconcile','before_outcome')}else{@('before_reconcile')}
            foreach($phase in $phases) {
                foreach($change in @('destination_content','destination_removed','source_recreated')) {
                    $state=New-State $location;$state.Files.RemoveAt(1)
                    $arguments=@{ConfigurationJson=($config|ConvertTo-Json -Compress);MachineId='PC-A';Operation=$operation;
                        State=$state;ReferenceDate=[datetime]'2026-10-28';PythonExecutable=$PythonExecutable}
                    if($withJournal) {
                        $base=Join-Path $fixture ([guid]::NewGuid().ToString('N'))
                        foreach($part in @('journal','reports')){New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
                        $arguments.JournalRoot=Join-Path $base 'journal';$arguments.ReportRoot=Join-Path $base 'reports'
                    }
                    [void](Invoke-EoLogMoveSimulation @arguments -Faults @{one='delete_unknown_absent'})
                    $historyBefore=$state.Events | ConvertTo-Json -Depth 20 -Compress
                    $count=if($withJournal){@(Get-ChildItem $arguments.JournalRoot -File).Count}else{0}
                    $control=@{Changed=$false}
                    $check={param($Point) if($Point -ceq $phase -and -not $control.Changed) {
                        $control.Changed=$true
                        switch($change) {
                            'destination_content' {$state.Files[0].Bytes=[byte[]]@(99)}
                            'destination_removed' {$state.Files.Clear()}
                            'source_recreated' {$state.Files.Add(@{Id='new-source';Location=$location;LogType='BattleLog';
                                RelativePath='20240101_12345678@one.txt';Bytes=[byte[]]@(99)})}
                        }
                    };return $true}
                    $run=Invoke-EoLogMoveSimulation @arguments -OwnershipCheck $check
                    Assert-True ($control.Changed -and $run.CompletedSourceCount -eq 0 -and $run.Status -ceq 'failure' -and
                        $run.Results[0].Reason -ceq 'reconciliation_unconfirmed') "$operation $withJournal $phase $change cannot reconcile stale observations"
                    Assert-True ($state.Events[-1].Kind -ceq 'reconciled' -and $state.Events[-1].Outcome -ceq 'unknown') 'no completed model event is added'
                    if($withJournal) {
                        Assert-True (@(Get-ChildItem $arguments.JournalRoot -File).Count -eq $count) 'unconfirmed reconciliation preserves old journal without a new deletion result'
                        Assert-True ($run.ReportSaveStatus -ceq 'confirmed' -and $run.RunReportSummary.unresolved_source_count -eq 1) 'unconfirmed reconciliation remains visible in final report'
                    }
                    $state.Events.RemoveAt($state.Events.Count-1)
                    Assert-True (($state.Events | ConvertTo-Json -Depth 20 -Compress) -ceq $historyBefore) 'previous history is unchanged'
                }
            }
        }
    }
    # Real owner IPC: alter the self-created token record immediately after
    # prepared publication, so the next checkpoint must refuse deletion.
    $script:originalSend=(Get-Command Send-EoSimulationRecord).ScriptBlock
    function Send-EoSimulationRecord {
        param([hashtable]$Record,[string]$JournalRoot,[string]$PythonExecutable)
        $ack=& $script:originalSend @PSBoundParameters
        if($Record.event_kind -ceq 'prepared') {
            $lock=@(Get-ChildItem -LiteralPath $script:lossLifecycle -Filter '*.lock')[0]
            [IO.File]::WriteAllText($lock.FullName,'changed synthetic ownership')
        }
        return $ack
    }
    foreach($operation in @('Sync','Archive')) {
        $base=Join-Path $fixture ([guid]::NewGuid().ToString('N'))
        foreach($part in @('journal','journal.lifecycle','reports')){New-Item -ItemType Directory -Path (Join-Path $base $part) -Force|Out-Null}
        $script:lossLifecycle=Join-Path $base 'journal.lifecycle'
        $location=if($operation -eq 'Sync'){'PC-A'}else{'Cloud'};$state=New-State $location
        $run=Invoke-EoOwnedLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId 'PC-A' -Operation $operation `
            -State $state -ReferenceDate ([datetime]'2026-10-28') -JournalRoot (Join-Path $base 'journal') -ReportRoot (Join-Path $base 'reports') `
            -LifecycleRoot $script:lossLifecycle -PythonExecutable $PythonExecutable
        Assert-True ($run.OwnershipStatus -ceq 'unconfirmed' -and $run.LifecycleStatus -ceq 'unconfirmed' -and $run.CompletedSourceCount -eq 0) "$operation real owner rejects changed record before source deletion"
        Assert-True (@($state.Files|Where-Object {$_.Location -ceq $location}).Count -eq 2) "$operation real owner failure preserves remaining sources"
        $ended=Get-Content (Join-Path $script:lossLifecycle ($run.RunId+'.ended.json')) -Raw|ConvertFrom-Json -AsHashtable
        Assert-True ($ended.disposition -ceq 'interrupted' -and @(Get-ChildItem $script:lossLifecycle -Filter '*.lock').Count -eq 1) "$operation changed ownership stays for explicit recovery"
    }
    $state=New-State 'PC-A'
    $run=Invoke-EoLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId 'PC-A' -Operation 'Sync' -State $state `
        -ReferenceDate ([datetime]'2026-10-28') -DryRun -OwnershipCheck {throw 'Dry Run must never call ordinary ownership'}
    Assert-True ($run.Status -ceq 'dry_run' -and $run.OwnershipStatus -ceq 'not_checked') 'Dry Run bypasses all ownership callbacks'
    foreach($invalid in @({return 'yes'},{throw 'synthetic private exception'})) {
        $state=New-State 'PC-A'
        $run=Invoke-EoLogMoveSimulation -ConfigurationJson ($config|ConvertTo-Json -Compress) -MachineId 'PC-A' -Operation 'Sync' -State $state `
            -ReferenceDate ([datetime]'2026-10-28') -OwnershipCheck $invalid
        Assert-True ($run.Status -ceq 'failure' -and $state.Files.Count -eq 2 -and $run.Results[0].Reason -ceq 'ownership_unconfirmed') 'nonboolean or exceptional ownership observation fails closed'
    }
    Write-Host "PASS: $script:Passed ownership loss assertions"
}
finally {
    $item=Get-Item -LiteralPath $fixture -Force;$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    if($item.Parent.FullName.TrimEnd('\') -cne $parent -or -not $item.Name.StartsWith('eolm-owner-loss-') -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'synthetic_cleanup_root_invalid'}
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
}
