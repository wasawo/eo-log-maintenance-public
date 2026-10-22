#requires -Version 7.6.7

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\Common\LogFunctions.ps1')

$script:Passed = 0
$script:Failed = 0

function Assert-Equal {
    param([string]$Name, [object]$Expected, [object]$Actual)
    if ([object]::Equals($Expected, $Actual)) {
        $script:Passed++
        Write-Host "PASS: $Name"
    }
    else {
        $script:Failed++
        $expectedType = if ($null -eq $Expected) { '<null>' } else { $Expected.GetType().FullName }
        $actualType = if ($null -eq $Actual) { '<null>' } else { $Actual.GetType().FullName }
        Write-Host "FAIL: $Name (expected type=$expectedType, actual type=$actualType)"
    }
}

Assert-SupportedPowerShellVersion

# Safe paths are preserved except for separator-direction canonicalization.
Assert-Equal 'safe relative path preserved' 'BattleLog/20260930_12345678@Example.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'BattleLog/20260930_12345678@Example.txt'
)
Assert-Equal 'backslashes canonicalized' 'BattleLog/20260930_12345678@Example.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'BattleLog\20260930_12345678@Example.txt'
)
Assert-Equal 'Unicode scalar text accepted' 'logs/日本語.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'logs/日本語.txt'
)

# Invalid or unsafe path values return null and are never echoed by this function.
Assert-Equal 'null input rejected' $null (ConvertTo-SafeDiagnosticRelativePath $null)
Assert-Equal 'non-string input rejected' $null (ConvertTo-SafeDiagnosticRelativePath ([int]42))
Assert-Equal 'empty path rejected' $null (ConvertTo-SafeDiagnosticRelativePath '')
Assert-Equal 'leading slash rejected' $null (ConvertTo-SafeDiagnosticRelativePath '/logs/file.txt')
Assert-Equal 'drive-qualified path rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'C:\logs\file.txt')
Assert-Equal 'UNC path rejected' $null (ConvertTo-SafeDiagnosticRelativePath '\\server\share\file.txt')
Assert-Equal 'device path rejected' $null (ConvertTo-SafeDiagnosticRelativePath '\\?\C:\logs\file.txt')
Assert-Equal 'colon rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'logs/file:stream.txt')
Assert-Equal 'repeated separator rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'logs//file.txt')
Assert-Equal 'trailing separator rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'logs/')
Assert-Equal 'dot segment rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'logs/./file.txt')
Assert-Equal 'traversal segment rejected' $null (ConvertTo-SafeDiagnosticRelativePath 'logs/../file.txt')
Assert-Equal 'NUL rejected' $null (ConvertTo-SafeDiagnosticRelativePath ("logs/$([char]0)file.txt"))
Assert-Equal 'control character rejected' $null (ConvertTo-SafeDiagnosticRelativePath ("logs/$([char]9)file.txt"))
$unpairedSurrogate = [string]::Concat('logs/', [char]0xD800, '.txt')
Assert-Equal 'unpaired surrogate rejected' $null (ConvertTo-SafeDiagnosticRelativePath $unpairedSurrogate)

# Fixed sensitive names are checked in every segment, case-insensitively.
foreach ($name in @('.env', '.npmrc', '.pypirc', '.netrc', '.dockerconfigjson', '.aws', '.ssh', '.gnupg', 'secrets', 'secret', 'credentials', 'credential')) {
    Assert-Equal "fixed sensitive segment rejected: $name" $null (
        ConvertTo-SafeDiagnosticRelativePath "logs/$name/config.json"
    )
}
Assert-Equal 'fixed sensitive name case-insensitive' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/.ENV/config.json'
)
Assert-Equal 'ordinary similar filename accepted' 'logs/envoy.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'logs/envoy.txt'
)

# Every approved sensitive token is checked with ASCII alphanumeric boundaries.
foreach ($tokenName in @('token', 'password', 'passwd', 'secret', 'credential', 'credentials', 'apikey', 'api-key', 'private-key', 'access-key', 'client-secret', 'authorization', 'bearer')) {
    Assert-Equal "sensitive token rejected: $tokenName" $null (
        ConvertTo-SafeDiagnosticRelativePath "logs/$tokenName/config.txt"
    )
}
Assert-Equal 'bounded token in compound name rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/api-token-prod.txt'
)
Assert-Equal 'tokenizer false positive avoided' 'logs/tokenizer.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'logs/tokenizer.txt'
)
Assert-Equal 'password token rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/password.txt'
)
Assert-Equal 'token in middle directory rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/client-secret/archive.txt'
)

# C-54 value-format rules that can occur in a syntactically relative path.
# URI user-info contains a colon and is rejected by C-53 before C-54 evaluation.
Assert-Equal 'URI user-info path rejected by C-53 syntax gate' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/https://user:pass@example.invalid/file.txt'
)
Assert-Equal 'Bearer credential rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/Bearer abc.def_123+/==.txt'
)
Assert-Equal 'GitHub classic token-like value rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/ghp_12345678901234567890.txt'
)
Assert-Equal 'GitHub fine-grained token-like value rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/github_pat_12345678901234567890.txt'
)
Assert-Equal 'AWS access-key-ID-like value rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/AKIA1234567890ABCDEF.txt'
)
Assert-Equal 'PEM private-key marker rejected' $null (
    ConvertTo-SafeDiagnosticRelativePath 'logs/-----BEGIN PRIVATE KEY-----.txt'
)
Assert-Equal 'ordinary bearer-like word accepted' 'logs/bearerly.txt' (
    ConvertTo-SafeDiagnosticRelativePath 'logs/bearerly.txt'
)

if ($script:Failed -gt 0) {
    throw "$($script:Failed) diagnostic path sanitization test(s) failed; $($script:Passed) passed."
}
Write-Host "Diagnostic path sanitization tests passed: $($script:Passed)"
