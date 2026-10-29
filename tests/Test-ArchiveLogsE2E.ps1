#requires -Version 7.6.7
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$script:Passed = 0
$fixtures = [Collections.Generic.List[string]]::new()
$pwsh = (Get-Process -Id $PID).Path
$entry = Join-Path $PSScriptRoot '../scripts/ArchiveLogs.ps1'

function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function New-ArchiveFixture {
    $path = Join-Path ([IO.Path]::GetTempPath()) ('eolm-s2-archive-' + [guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($path)
    $fixtures.Add($path)
    [IO.File]::WriteAllText((Join-Path $path '.synthetic-fixture'), 'eolm-s2-synthetic-v1')
    foreach ($side in @('mock-drive','archive')) {
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
function Invoke-ArchiveEntry([string]$Root, [string[]]$Extra = @(), [int]$ExpectedExit = 0, [string]$ReferenceDate = '2026-10-29') {
    $output = & $pwsh -NoProfile -File $entry -Synthetic -SyntheticRoot $Root -ReferenceDate $ReferenceDate @Extra
    $code = $LASTEXITCODE
    Assert-True ($code -eq $ExpectedExit) "entry process exit $ExpectedExit (actual $code)"
    return (($output -join "`n") | ConvertFrom-Json)
}

try {
    $root = New-ArchiveFixture
    Add-SyntheticFile $root 'mock-drive/BattleLog/nested/20251231_12345678@battle.txt' 'synthetic battle'
    Add-SyntheticFile $root 'mock-drive/ErrorReport/nested/20241231_12345678.txt' 'synthetic error'
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.Status -ceq 'success' -and $run.SuccessCount -eq 2 -and $run.CompletedMoveCount -eq 0) 'normal E2E verifies copies without claiming moves'
    foreach ($pair in @(
        @('mock-drive/BattleLog/nested/20251231_12345678@battle.txt','archive/BattleLog/20251231_12345678@battle.txt'),
        @('mock-drive/ErrorReport/nested/20241231_12345678.txt','archive/ErrorReport/20241231_12345678.txt')
    )) {
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $root $pair[0])).Hash -ceq
            (Get-FileHash -LiteralPath (Join-Path $root $pair[1])).Hash) 'physical source retained and flattened copy SHA-256 matches'
    }
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.SuccessCount -eq 2 -and @($run.Results | Where-Object Reused).Count -eq 2) 'rerun reuses verified destinations'

    $root = New-ArchiveFixture
    foreach ($name in @('20251231_12345678@last.txt','20260101_12345678@current.txt','20240101_12345678@old.txt',
        '20250230_12345678@invalid.txt','not-a-log.txt','20251231_12345678@upper.TXT')) {
        Add-SyntheticFile $root "mock-drive/BattleLog/$name" 'synthetic period fixture'
    }
    Add-SyntheticFile $root 'mock-drive/ErrorReport/20241231_12345678.txt' 'previous year'
    Add-SyntheticFile $root 'mock-drive/ErrorReport/20250101_12345678.txt' 'current year'
    $run = Invoke-ArchiveEntry $root -ExpectedExit 1
    Assert-True ($run.ProcessedCount -eq 8 -and $run.SuccessCount -eq 3 -and $run.ExcludedCount -eq 2 -and
        $run.FailureCount -eq 3 -and $run.HeldCount -eq 0) 'period boundaries, all older periods, invalid names, and exact counts'
    Assert-True (@($run.Results | Where-Object Reason -eq 'filename_invalid').Count -eq 3) 'invalid date, unexpected name and uppercase extension remain visible failures'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $root 'archive/BattleLog/20260101_12345678@current.txt')) -and
        -not (Test-Path -LiteralPath (Join-Path $root 'archive/ErrorReport/20250101_12345678.txt'))) 'current periods are not copied'
    Assert-True (@(Get-ChildItem -LiteralPath (Join-Path $root 'mock-drive') -Recurse -File).Count -eq 8) 'every source survives mixed success and failure'

    foreach ($boundary in @(
        @{Date='2027-01-01';Include='20261231';Exclude='20270101';ErrorInclude='20251231';ErrorExclude='20260101'},
        @{Date='2025-01-01';Include='20240229';Exclude='20250101';ErrorInclude='20231231';ErrorExclude='20240101'}
    )) {
        $root = New-ArchiveFixture
        Add-SyntheticFile $root ("mock-drive/BattleLog/"+$boundary.Include+'_12345678@eligible.txt') 'boundary eligible'
        Add-SyntheticFile $root ("mock-drive/BattleLog/"+$boundary.Exclude+'_12345678@retained.txt') 'boundary retained'
        Add-SyntheticFile $root ("mock-drive/ErrorReport/"+$boundary.ErrorInclude+'_12345678.txt') 'error boundary eligible'
        Add-SyntheticFile $root ("mock-drive/ErrorReport/"+$boundary.ErrorExclude+'_12345678.txt') 'error boundary retained'
        $run = Invoke-ArchiveEntry $root -ReferenceDate $boundary.Date
        Assert-True ($run.SuccessCount -eq 2 -and $run.ExcludedCount -eq 2) 'archive year boundaries for both kinds and valid historical leap day'
    }

    $root = New-ArchiveFixture
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.Status -ceq 'no_work' -and $run.ProcessedCount -eq 0 -and $run.FailureCount -eq 0) 'empty inventory is normal no-work'
    $run = Invoke-ArchiveEntry $root -Extra @('-MockFault','enumeration_failed') -ExpectedExit 1
    Assert-True ($run.Status -ceq 'failure' -and $run.Results[0].Reason -ceq 'enumeration_failed') 'enumeration failure is not no-work'

    $root = New-ArchiveFixture
    $name = '20240101_12345678@same.txt'
    Add-SyntheticFile $root "mock-drive/BattleLog/a/$name" 'same content'
    Add-SyntheticFile $root "mock-drive/BattleLog/b/$name" 'same content'
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.SuccessCount -eq 2 -and @($run.Results | Where-Object Reused).Count -eq 1 -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'archive/BattleLog') -File).Count -eq 1) 'same-name same-content sources share one destination'
    Assert-True ($run.Results[0].SourceRelativePath -cne $run.Results[1].SourceRelativePath) 'flattening preserves distinct source relative identities'

    $root = New-ArchiveFixture
    Add-SyntheticFile $root "mock-drive/BattleLog/$name" 'source content'
    Add-SyntheticFile $root "archive/BattleLog/$name" 'different existing destination'
    $before = (Get-FileHash -LiteralPath (Join-Path $root "archive/BattleLog/$name")).Hash
    $run = Invoke-ArchiveEntry $root -ExpectedExit 1
    Assert-True ($run.HeldCount -eq 1 -and $run.Results[0].Reason -ceq 'content_conflict') 'different content is held'
    Assert-True ((Get-FileHash -LiteralPath (Join-Path $root "archive/BattleLog/$name")).Hash -ceq $before -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'archive/BattleLog') -File).Count -eq 1) 'conflict neither overwrites nor renames'

    foreach ($fault in @('hash_mismatch','copy_failed')) {
        $root = New-ArchiveFixture
        Add-SyntheticFile $root "mock-drive/BattleLog/$name" 'unchanged source'
        $before = (Get-FileHash -LiteralPath (Join-Path $root "mock-drive/BattleLog/$name")).Hash
        $run = Invoke-ArchiveEntry $root -Extra @('-MockFault',$fault) -ExpectedExit 1
        Assert-True ($run.FailureCount -eq 1 -and $run.SuccessCount -eq 0 -and $run.CompletedMoveCount -eq 0) 'copy or hash failure never claims success or move completion'
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $root "mock-drive/BattleLog/$name")).Hash -ceq $before) 'verification/copy failure retains source bytes'
        if ($fault -eq 'hash_mismatch') {
            Assert-True ($run.Results[0].Reason -ceq 'hash_mismatch' -and
                $run.Results[0].SourceSha256 -cne $run.Results[0].DestinationSha256) 'real corrupted mock copy is detected by SHA-256'
            $rerun = Invoke-ArchiveEntry $root -ExpectedExit 1
            Assert-True ($rerun.HeldCount -eq 1) 'failed copy remains preserved as a conflict on rerun'
        }
    }

    $root = New-ArchiveFixture
    Add-SyntheticFile $root "mock-drive/BattleLog/$name" 'dry run source'
    $run = Invoke-ArchiveEntry $root -Extra @('-DryRun')
    Assert-True ($run.Status -ceq 'planned' -and $run.PlannedCount -eq 1 -and $run.SuccessCount -eq 0 -and
        @(Get-ChildItem -LiteralPath (Join-Path $root 'archive') -Recurse -File).Count -eq 0) 'Dry Run never copies or creates reports'
    $run = Invoke-ArchiveEntry $root -Extra @('-Operation','Sync') -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 's2_archive_only') 'Archive entry rejects Sync operation'
    $run = Invoke-ArchiveEntry $root -Extra @('-MachineId','PC-B') -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'archive_role_denied') 'PC-B cannot archive'
    $lease = [IO.File]::Open((Join-Path $root '.synthetic-fixture'), 'Open', 'Read', 'None')
    try {
        $run = Invoke-ArchiveEntry $root -ExpectedExit 1
        Assert-True ($run.Results[0].Reason -ceq 'synthetic_run_failed') 'second entry cannot acquire fixture lease'
    }
    finally { $lease.Dispose() }
    [IO.File]::WriteAllText((Join-Path $root '.synthetic-fixture'), 'wrong marker')
    $run = Invoke-ArchiveEntry $root -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'synthetic_marker_invalid') 'unmarked fixture denied before copying'
    $run = Invoke-ArchiveEntry ([IO.Path]::GetTempPath()) -ExpectedExit 1
    Assert-True ($run.Results[0].Reason -ceq 'synthetic_root_invalid') 'arbitrary root rejected'
    $root = New-ArchiveFixture
    Add-SyntheticFile $root 'mock-drive/BattleLog/20240101_12345678@initial.txt' 'existing cloud data'
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.SuccessCount -eq 1) 'archive proceeds with no PC-B completion state'
    Add-SyntheticFile $root 'mock-drive/BattleLog/20240101_12345678@late.txt' 'late cloud data'
    $run = Invoke-ArchiveEntry $root
    Assert-True ($run.SuccessCount -eq 2 -and @($run.Results | Where-Object Reused).Count -eq 1) 'next run copies late data and reuses prior archive'
    Assert-True (@(Get-ChildItem -LiteralPath (Join-Path $root 'mock-drive/BattleLog') -File).Count -eq 2) 'cloud sources are never removed'
    Write-Host "PASS: $script:Passed S2 entry E2E assertions"
}
finally {
    foreach ($root in $fixtures) {
        $item = Get-Item -LiteralPath $root -Force
        $temp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([char[]]'\/')
        if ($item.Parent.FullName.TrimEnd([char[]]'\/') -ine $temp -or
            $item.Name -cnotmatch '^eolm-s2-archive-[a-f0-9]{32}$' -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'synthetic_cleanup_root_invalid' }
        Remove-Item -LiteralPath $item.FullName -Recurse -Force
    }
}
# Expected failing child processes must not become the CI shell's final exit code.
exit 0
