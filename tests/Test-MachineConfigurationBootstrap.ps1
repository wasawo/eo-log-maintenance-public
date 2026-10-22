#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/MachineConfigurationBootstrap.ps1')
$script:Passed = 0
function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}
function Assert-Rejected([scriptblock]$Action) {
    $caught = $false
    try { & $Action | Out-Null }
    catch {
        $caught = $true
        Assert-True ($_.Exception.Message -ceq 'configuration_bootstrap_failed') 'Sanitized failure'
    }
    Assert-True $caught 'Rejected'
}
$root = Join-Path ([IO.Path]::GetTempPath()) ('eo-config-bootstrap-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root) | Out-Null
try {
    foreach ($machine in @('PC-A', 'PC-B')) {
        $directory = Join-Path $root $machine
        [IO.Directory]::CreateDirectory($directory) | Out-Null
        $example = Join-Path $directory "$machine.example.json"
        $active = Join-Path $directory "$machine.json"
        [IO.File]::Copy((Join-Path $PSScriptRoot "../Config/$machine.example.json"), $example)
        $expected = [Convert]::ToBase64String([IO.File]::ReadAllBytes($example))
        $result = Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId $machine
        Assert-True ($result.Status -ceq 'created') "$machine created"
        Assert-True ([Convert]::ToBase64String([IO.File]::ReadAllBytes($active)) -ceq $expected) 'Exact example bytes'
        Assert-True (@(Get-ChildItem -LiteralPath $directory -Force).Count -eq 2) 'No temporary remains'
        # Even invalid existing settings must survive an update byte-for-byte.
        [IO.File]::WriteAllBytes($active, [byte[]]@(255, 0, 7))
        [IO.File]::WriteAllText($example, 'invalid example')
        $result = Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId $machine
        Assert-True ($result.Status -ceq 'preserved') 'Existing preserved without template validation'
        Assert-True ([Convert]::ToBase64String([IO.File]::ReadAllBytes($active)) -ceq '/wAH') 'Existing bytes unchanged'
    }
    $directory = Join-Path $root 'invalid'
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $example = Join-Path $directory 'PC-A.example.json'
    Assert-Rejected { Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId PC-A }
    [IO.File]::WriteAllText($example, '{}')
    Assert-Rejected { Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId PC-A }
    $config = Get-Content (Join-Path $PSScriptRoot '../Config/PC-A.example.json') -Raw | ConvertFrom-Json
    $config.allowArchive = $true
    [IO.File]::WriteAllText($example, ($config | ConvertTo-Json))
    Assert-Rejected { Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId PC-A }
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $directory 'PC-A.json'))) 'Failure leaves no active config'
    Assert-True (@(Get-ChildItem -LiteralPath $directory -Force).Count -eq 1) 'Failure leaves only example'
    Assert-Rejected { Initialize-EoMachineConfiguration -ConfigDirectory (Join-Path $root 'absent') -MachineId PC-B }
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $root 'absent'))) 'Missing directory not created'
    [IO.Directory]::CreateDirectory((Join-Path $directory 'PC-A.json')) | Out-Null
    Assert-True ((Initialize-EoMachineConfiguration -ConfigDirectory $directory -MachineId PC-A).Status -ceq 'preserved') 'Existing directory never replaced'
}
finally {
    $resolved = [IO.Path]::GetFullPath($root)
    $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    if ([IO.Path]::GetDirectoryName($resolved).TrimEnd('\') -cne $parent) { throw 'Unexpected test cleanup root' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Host "Machine configuration bootstrap tests passed: $script:Passed assertions"
