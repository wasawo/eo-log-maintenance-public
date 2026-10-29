#requires -Version 7.6.7
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$script:Passed = 0
$fixtures = [Collections.Generic.List[string]]::new()
$pwsh = (Get-Process -Id $PID).Path
$entry = Join-Path $PSScriptRoot '../scripts/SyncLogs.ps1'

function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function New-SyncFixture {
    $path = Join-Path ([IO.Path]::GetTempPath()) ('eolm-s1-sync-' + [guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($path)
    $fixtures.Add($path)
    [IO.File]::WriteAllText((Join-Path $path '.synthetic-fixture'), 'eolm-s1-synthetic-v1')
    foreach ($side in @('source','mock-drive')) {
        foreach ($kind in @('BattleLog','ErrorReport')) {
            [void][IO.Directory]::CreateDirectory((Join-Path $path "$side/$kind"))
        }
    }
    return $path
}
function Add-SyntheticFile([string]$Root, [string]$RelativePath, [string]$Content) {
    $path = Join-Path $Root $RelativePath
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
    [IO.File]::WriteAllText($path, $Content)
}
function Invoke-SyncEntry([string]$Root, [string[]]$Extra = @(), [int]$ExpectedExit = 0, [string]$ReferenceDate = '2026-10-29') {
    $output = & $pwsh -NoProfile -File $entry -Synthetic -SyntheticRoot $Root -ReferenceDate $ReferenceDate @Extra
    $code = $LASTEXITCODE
    Assert-True ($code -eq $ExpectedExit) "entry process exit $ExpectedExit (actual $code)"
    return (($output -join "`n") | ConvertFrom-Json)
}

try {
    $root = New-SyncFixture
    Add-SyntheticFile $root 'source/BattleLog/nested/20260930_12345678@battle.txt' 'synthetic battle'
    Add-SyntheticFile $root 'source/ErrorReport/nested/20251231_12345678.txt' 'synthetic error'
    $run = Invoke-SyncEntry $root
    Assert-True ($run.Status -ceq 'success' -and $run.SuccessCount -eq 2 -and $run.CompletedMoveCount -eq 0) 'normal E2E verifies copies without claiming moves'
    foreach ($pair in @(
        @('source/BattleLog/nested/20260930_12345678@battle.txt','mock-drive/BattleLog/20260930_12345678@battle.txt'),
        @('source/ErrorReport/nested/20251231_12345678.txt','mock-drive/ErrorReport/20251231_12345678.txt')
    )) {
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $root $pair[0])).Hash -ceq
            (Get-FileHash -LiteralPath (Join-Path $root $pair[1])).Hash) 'physical source retained and flattened copy SHA-256 matches'
    }
    $run = Invoke-SyncEntry $root
    Assert-True ($run.SuccessCount -eq 2 -and @($run.Results | Where-Object Reused).Count -eq 2) 'rerun reuses verified destinations'

    $root = New-SyncFixture
    foreach ($name in @('20260930_12345678@last.txt','20261001_12345678@current.txt','20240101_12345678@old.txt',
        '20260230_12345678@invalid.txt','not-a-log.txt','20260930_12345678@upper.TXT')) {
        Add-SyntheticFile $root "source/BattleLog/$name" 'synthetic period fixture'
    }
    Add-SyntheticFile $root 'source/ErrorReport/20251231_12345678.txt' 'previous year'
    Add-SyntheticFile $root 'source/ErrorReport/20260101_12345678.txt' 'current year'
    $run = Invoke-SyncEntry $root -ExpectedExit 1
    Assert-True ($run.ProcessedCount -eq 8 -and $run.SuccessCount -eq 3 -and $run.ExcludedCount -eq 2 -and
        $run.FailureCount -eq 3 -and $run.HeldCount -eq 0) 'period boundaries, all older periods, invalid names, and exact counts'
    Assert-True (@($run.Results | Where-Object Reason -eq 'filename_invalid').Count -eq 3) 'invalid date, unexpected name and uppercase extension remain visible failures'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $root 'mock-drive/BattleLog/20261001_12345678@current.txt')) -and
        -not (Test-Path -LiteralPath (Join-Path $root 'mock-drive/ErrorReport/20260101_12345678.txt'))) 'current periods are not copied'
    Assert-True (@(Get-ChildItem -LiteralPath (Join-Path $root 'source') -Recurse -File).Count -eq 8) 'every source survives mixed success and failure'

    foreach ($boundary in @(
        @{Date='2027-01-01';Include='20261231';Exclude='20270101'},
        @{Date='2024-03-01';Include='20240229';Exclude='20240301'}
    )) {
        $root = New-SyncFixture
        Add-SyntheticFile $root ("source/BattleLog/"+$boundary.Include+'_12345678@eligible.txt') 'boundary eligible'
        Add-SyntheticFile $root ("source/BattleLog/"+$boundary.Exclude+'_12345678@retained.txt') 'boundary retained'
        $run = Invoke-SyncEntry $root -ReferenceDate $boundary.Date
        Assert-True ($run.SuccessCount -eq 1 -and $run.ExcludedCount -eq 1) 'January/year transition and leap-day month boundary'
    }

    $root = New-SyncFixture
    $run = Invoke-SyncEntry $root
    Assert-True ($run.Status -ceq 'no_work' -and $run.ProcessedCount -eq 0 -and $run.FailureCount -eq 0) 'empty inventory is normal no-work'
    $run = Invoke-SyncEntry $root -Extra @('-MockFault','enumeration_failed') -ExpectedExit 1
    Assert-True ($run.Status -ceq 'failure' -and $run.Results[0].Reason -ceq 'enumeration_failed') 'enumeration failure is not no-work'

    $root = New-SyncFixture
    $name = '20240101_12345678@same.txt'
    Add-SyntheticFile $root "source/BattleLog/a/$name" 'same content'
    Add-SyntheticFile $root "source/BattleLog/b/$name" 'same content'
    $run = Invoke-SyncEntry $root
    Assert-True ($run.SuccessCount -eq 2 -and @($run.Results | Where-Object Reused).Count -eq 1 -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'mock-drive/BattleLog') -File).Count -eq 1) 'same-name same-content sources share one destination'
    Assert-True ($run.Results[0].SourceRelativePath -cne $run.Results[1].SourceRelativePath) 'flattening preserves distinct source relative identities'

    $root = New-SyncFixture
    Add-SyntheticFile $root "source/BattleLog/$name" 'source content'
    Add-SyntheticFile $root "mock-drive/BattleLog/$name" 'different existing destination'
    $before = (Get-FileHash -LiteralPath (Join-Path $root "mock-drive/BattleLog/$name")).Hash
    $run = Invoke-SyncEntry $root -ExpectedExit 1
    Assert-True ($run.HeldCount -eq 1 -and $run.Results[0].Reason -ceq 'content_conflict') 'different content is held'
    Assert-True ((Get-FileHash -LiteralPath (Join-Path $root "mock-drive/BattleLog/$name")).Hash -ceq $before -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'mock-drive/BattleLog') -File).Count -eq 1) 'conflict neither overwrites nor renames'

    foreach ($fault in @('hash_mismatch','copy_failed')) {
        $root = New-SyncFixture
        Add-SyntheticFile $root "source/BattleLog/$name" 'unchanged source'
        $before = (Get-FileHash -LiteralPath (Join-Path $root "source/BattleLog/$name")).Hash
        $run = Invoke-SyncEntry $root -Extra @('-MockFault',$fault) -ExpectedExit 1
        Assert-True ($run.FailureCount -eq 1 -and $run.SuccessCount -eq 0 -and $run.CompletedMoveCount -eq 0) 'copy or hash failure never claims success or move completion'
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $root "source/BattleLog/$name")).Hash -ceq $before) 'verification/copy failure retains source bytes'
        if ($fault -eq 'hash_mismatch') {
            Assert-True ($run.Results[0].Reason -ceq 'hash_mismatch' -and
                $run.Results[0].SourceSha256 -cne $run.Results[0].DestinationSha256) 'real corrupted mock copy is detected by SHA-256'
            $rerun = Invoke-SyncEntry $root -ExpectedExit 1
            Assert-True ($rerun.HeldCount -eq 1) 'failed copy remains preserved as a conflict on rerun'
        }
    }

    $root = New-SyncFixture
    Add-SyntheticFile $root "source/BattleLog/$name" 'dry run source'
    $run = Invoke-SyncEntry $root -Extra @('-DryRun')
    Assert-True ($run.Status -ceq 'planned' -and $run.PlannedCount -eq 1 -and $run.SuccessCount -eq 0 -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'mock-drive') -Recurse -File).Count -eq 0) 'Dry Run never copies or creates reports'
    $run = Invoke-SyncEntry $root -Extra @('-Operation','Archive') -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'archive_role_denied') 'PC-B archive rejected by actual entry'
    $run = Invoke-SyncEntry $root -Extra @('-MachineId','PC-A') -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 's1_pc_b_only') 'S1 cannot be expanded to PC-A'
    $lease = [IO.File]::Open((Join-Path $root '.synthetic-fixture'), 'Open', 'Read', 'None')
    try {
        $run = Invoke-SyncEntry $root -ExpectedExit 1
        Assert-True ($run.Results[0].Reason -ceq 'synthetic_run_failed') 'second entry cannot acquire fixture lease'
    }
    finally { $lease.Dispose() }
    [IO.File]::WriteAllText((Join-Path $root '.synthetic-fixture'), 'wrong marker')
    $run = Invoke-SyncEntry $root -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'synthetic_marker_invalid') 'unmarked fixture denied before copying'
    $run = Invoke-SyncEntry ([IO.Path]::GetTempPath()) -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'synthetic_root_invalid') 'arbitrary root rejected'
    Write-Host "PASS: $script:Passed S1 entry E2E assertions"
}
finally {
    foreach ($root in $fixtures) {
        $item = Get-Item -LiteralPath $root -Force
        $temp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([char[]]'\/')
        if ($item.Parent.FullName.TrimEnd([char[]]'\/') -ine $temp -or
            $item.Name -cnotmatch '^eolm-s1-sync-[a-f0-9]{32}$' -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'synthetic_cleanup_root_invalid' }
        Remove-Item -LiteralPath $item.FullName -Recurse -Force
    }
}
