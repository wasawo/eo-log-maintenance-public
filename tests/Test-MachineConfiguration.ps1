#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Common\MachineConfiguration.ps1')
$script:Passed = 0

function Assert-True([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Name" }
    $script:Passed++
}

function Assert-Rejected([string]$Reason, [scriptblock]$Action) {
    $caught = $false
    try { & $Action | Out-Null }
    catch {
        $caught = $true
        Assert-True ($_.Exception.Message -ceq $Reason) "Expected sanitized reason $Reason"
    }
    Assert-True $caught "Expected rejection $Reason"
}

function New-Config([string]$Machine) {
    return Get-Content (Join-Path $PSScriptRoot "../Config/$Machine.example.json") -Raw |
        ConvertFrom-Json -AsHashtable
}

foreach ($machine in @('PC-A', 'PC-B')) {
    $baseline = New-Config $machine
    $json = $baseline | ConvertTo-Json -Compress
    $config = ConvertFrom-EoMachineConfigurationJson -Json $json -ExpectedMachineId $machine
    Assert-True ($config.machineId -ceq $machine) "$machine valid example loads"
    Assert-True ($config.maintenanceLocal -ceq $baseline.maintenanceLocal) "$machine root retained"

    foreach ($name in $baseline.Keys) {
        $changed = New-Config $machine
        $changed.Remove($name)
        $value = $changed | ConvertTo-Json -Compress
        Assert-Rejected 'configuration_missing_field' {
            ConvertFrom-EoMachineConfigurationJson -Json $value -ExpectedMachineId $machine
        }
    }
    foreach ($name in @('allowDelete', 'deleteSource', 'unknownField', 'Role')) {
        $changed = New-Config $machine
        $changed[$name] = $false
        $value = $changed | ConvertTo-Json -Compress
        Assert-Rejected 'configuration_unknown_field' {
            ConvertFrom-EoMachineConfigurationJson -Json $value -ExpectedMachineId $machine
        }
    }
    foreach ($pathName in @($baseline.Keys | Where-Object { $_ -notin @('machineId', 'role', 'allowArchive', 'maintenanceLocal') })) {
        foreach ($variant in @('same', 'child', 'parent', 'normalized', 'case')) {
            $changed = New-Config $machine
            $other = $changed[$pathName]
            $changed.maintenanceLocal = switch ($variant) {
                'same' { $other }
                'child' { $other + '\child' }
                'parent' { [IO.Path]::GetDirectoryName($other) }
                'normalized' { $other + '\child\..' }
                'case' { $other.ToUpperInvariant() + '\' }
            }
            $value = $changed | ConvertTo-Json -Compress
            Assert-Rejected 'configuration_maintenance_local_overlap' {
                ConvertFrom-EoMachineConfigurationJson -Json $value -ExpectedMachineId $machine
            }
        }
    }
    foreach ($value in @('relative\root', 'C:relative', '\\server\share', '\\?\C:\root', 'C:\root:stream', 'C:\bad*\root', 'C:\root.\child')) {
        $changed = New-Config $machine
        $changed.maintenanceLocal = $value
        $raw = $changed | ConvertTo-Json -Compress
        Assert-Rejected 'configuration_path_invalid' {
            ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId $machine
        }
    }
    foreach ($value in @($null, 123, $true, @('array'), @{ nested = 'value' })) {
        $changed = New-Config $machine
        $changed.maintenanceLocal = $value
        $raw = $changed | ConvertTo-Json -Compress -Depth 10
        Assert-Rejected 'configuration_field_type_invalid' {
            ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId $machine
        }
    }
    $changed = New-Config $machine
    $changed.role = 'wrong'
    $raw = $changed | ConvertTo-Json -Compress
    Assert-Rejected 'configuration_role_mismatch' {
        ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId $machine
    }
    $duplicate = $json.Replace('"machineId":', '"machineId":"' + $machine + '","machineId":')
    Assert-Rejected 'configuration_duplicate_field' {
        ConvertFrom-EoMachineConfigurationJson -Json $duplicate -ExpectedMachineId $machine
    }
    $changed = New-Config $machine
    $changed.maintenanceLocal = $changed.runtimeRoot + '-data'
    $raw = $changed | ConvertTo-Json -Compress
    $sibling = ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId $machine
    Assert-True ($sibling.maintenanceLocal.EndsWith('-data')) 'Sibling prefix accepted'
}

foreach ($raw in @('', '{bad-json', '{"private-path":"incomplete"')) {
    Assert-Rejected 'configuration_json_invalid' {
        ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId PC-A
    }
}
foreach ($raw in @('[]', 'null', '"scalar"')) {
    Assert-Rejected 'configuration_object_required' {
        ConvertFrom-EoMachineConfigurationJson -Json $raw -ExpectedMachineId PC-A
    }
}
$pcA = New-Config PC-A
$pcA.allowArchive = $true
$enabled = ConvertFrom-EoMachineConfigurationJson -Json ($pcA | ConvertTo-Json -Compress) -ExpectedMachineId PC-A
Assert-True ($enabled.allowArchive -eq $true) 'Explicit PC-A true accepted as data only'
$pcA.allowArchive = 'true'
Assert-Rejected 'configuration_field_type_invalid' {
    ConvertFrom-EoMachineConfigurationJson -Json ($pcA | ConvertTo-Json -Compress) -ExpectedMachineId PC-A
}
$pcB = New-Config PC-B
$pcB.allowArchive = $false
Assert-Rejected 'configuration_unknown_field' {
    ConvertFrom-EoMachineConfigurationJson -Json ($pcB | ConvertTo-Json -Compress) -ExpectedMachineId PC-B
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('eo-config-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    $configPath = Join-Path $tempRoot 'synthetic-config.json'
    $json = (New-Config PC-B) | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($configPath, $json)
    $before = [IO.File]::ReadAllBytes($configPath)
    $result = Read-EoMachineConfiguration -LiteralPath $configPath -ExpectedMachineId PC-B
    Assert-True ($result.role -ceq 'secondary') 'Read-only file loader returns validated role'
    Assert-True ([Convert]::ToBase64String($before) -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($configPath))) 'Config bytes unchanged'
    Assert-True (@(Get-ChildItem -LiteralPath $tempRoot).Count -eq 1) 'No directories or output artifacts created'
    $bomEncoding = [Text.UTF8Encoding]::new($true, $true)
    [IO.File]::WriteAllBytes($configPath, [byte[]]($bomEncoding.GetPreamble() + $bomEncoding.GetBytes($json)))
    $withBom = Read-EoMachineConfiguration -LiteralPath $configPath -ExpectedMachineId PC-B
    Assert-True ($withBom.machineId -ceq 'PC-B') 'UTF-8 BOM accepted'
    [IO.File]::WriteAllBytes($configPath, [byte[]]@(255))
    Assert-Rejected 'configuration_read_failed' {
        Read-EoMachineConfiguration -LiteralPath $configPath -ExpectedMachineId PC-B
    }

    Assert-Rejected 'configuration_read_failed' {
        Read-EoMachineConfiguration -LiteralPath (Join-Path $tempRoot 'missing.json') -ExpectedMachineId PC-B
    }
}
finally {
    if ((Split-Path $tempRoot) -ne ([IO.Path]::GetTempPath()).TrimEnd('\')) {
        throw 'Unexpected test cleanup root'
    }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
}
Write-Host "Machine configuration structure: $script:Passed assertions passed."
