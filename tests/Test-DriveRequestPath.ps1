#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/DriveRequestPath.ps1')
$corpus = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fixtures/drive-request-path-l1.json') -Raw -Encoding utf8 |
    ConvertFrom-Json -AsHashtable
$script:Passed = 0
$script:EffectCalls = 0

function Assert-PathCase([AllowNull()] [AllowEmptyString()] [object] $Value, [bool] $Expected) {
    $original = $Value
    $results = @(Test-DriveRequestFilePath -Value $Value)
    if ($results.Count -ne 1 -or $results[0] -isnot [bool] -or $results[0] -ne $Expected) {
        throw 'request_path_verdict_mismatch'
    }
    if ($Value -is [string] -and -not [string]::Equals($original, $Value, [StringComparison]::Ordinal)) {
        throw 'request_path_input_changed'
    }
    $script:Passed++
}

foreach ($command in @('Get-Content', 'Set-Content', 'Test-Path', 'Resolve-Path', 'Get-Item',
                        'New-Item', 'Remove-Item', 'Start-Process', 'Invoke-WebRequest', 'Invoke-RestMethod')) {
    Set-Item -Path "Function:local:$command" -Value { $script:EffectCalls++; throw 'unexpected_effect' }
}
foreach ($value in $corpus.valid) { Assert-PathCase $value $true }
foreach ($value in $corpus.invalid) { Assert-PathCase $value $false }
foreach ($value in @($null, $true, $false, 0, 1, @{}, @('C:\synthetic.txt'))) {
    Assert-PathCase $value $false
}
Assert-PathCase ('C:\' + ('x' * 300)) $true
Assert-PathCase ('C:\' + ((@('component') * 100) -join '\')) $true
if ($script:EffectCalls -ne 0) { throw 'request_path_effect_detected' }
Write-Output "Drive request path: $script:Passed passed; no operational effects."
