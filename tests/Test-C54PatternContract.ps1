#requires -Version 7.6.7

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Contract-level regex tests only; these do not exercise runtime path sanitization.
$patterns = [ordered]@{
    UriUserInfo = '(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^:/@\s][^/@\s]*:[^/@\s]+@'
    Bearer = '(?i)(?<![A-Za-z0-9_-])Bearer[ \t]+[A-Za-z0-9._~+/-]+=*(?![A-Za-z0-9._~+/-])'
    GitHubClassic = '(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{20,}(?![A-Za-z0-9])'
    GitHubFineGrained = '(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])'
    AwsAkia = '(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}(?![A-Za-z0-9])'
    PemPrivateKey = '-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'
}

$cases = @(
    @{ Name='URI user-info positive'; Pattern='UriUserInfo'; Value='https://demo-user:demo-pass@example.invalid/a.txt'; Expected=$true }
    @{ Name='URI without password negative'; Pattern='UriUserInfo'; Value='https://demo-user@example.invalid/a.txt'; Expected=$false }
    @{ Name='Bearer positive'; Pattern='Bearer'; Value='Bearer demoToken_123=='; Expected=$true }
    @{ Name='Bearer case-insensitive scheme'; Pattern='Bearer'; Value='bEaReR demoToken_123'; Expected=$true }
    @{ Name='Bearer empty token negative'; Pattern='Bearer'; Value='Bearer '; Expected=$false }
    @{ Name='Bearerish near miss'; Pattern='Bearer'; Value='Bearerish demoToken'; Expected=$false }
    @{ Name='GitHub classic positive'; Pattern='GitHubClassic'; Value='ghp_AbCdEf0123456789GhIjKlMn'; Expected=$true }
    @{ Name='GitHub classic short suffix negative'; Pattern='GitHubClassic'; Value='ghp_AbCdEf0123456789'; Expected=$false }
    @{ Name='GitHub classic case-sensitive'; Pattern='GitHubClassic'; Value='GHP_AbCdEf0123456789GhIjKlMn'; Expected=$false }
    @{ Name='GitHub classic left boundary'; Pattern='GitHubClassic'; Value='xghp_AbCdEf0123456789GhIjKlMn'; Expected=$false }
    @{ Name='GitHub fine-grained positive'; Pattern='GitHubFineGrained'; Value='github_pat_demo0123456789_AbCdEf0123456789'; Expected=$true }
    @{ Name='GitHub fine-grained short suffix negative'; Pattern='GitHubFineGrained'; Value='github_pat_123456789012345'; Expected=$false }
    @{ Name='GitHub fine-grained case-sensitive'; Pattern='GitHubFineGrained'; Value='GITHUB_PAT_demo0123456789_AbCdEf0123456789'; Expected=$false }
    @{ Name='GitHub fine-grained left boundary'; Pattern='GitHubFineGrained'; Value='xgithub_pat_demo0123456789_AbCdEf0123456789'; Expected=$false }
    @{ Name='AWS AKIA positive'; Pattern='AwsAkia'; Value='AKIAIOSFODNN7EXAMPLE'; Expected=$true }
    @{ Name='AWS AKIA short suffix negative'; Pattern='AwsAkia'; Value='AKIA123'; Expected=$false }
    @{ Name='AWS AKIA case-sensitive'; Pattern='AwsAkia'; Value='akiaIOSFODNN7EXAMPLE'; Expected=$false }
    @{ Name='AWS AKIA left boundary'; Pattern='AwsAkia'; Value='xAKIAIOSFODNN7EXAMPLE'; Expected=$false }
    @{ Name='PEM generic private key'; Pattern='PemPrivateKey'; Value='-----BEGIN PRIVATE KEY-----'; Expected=$true }
    @{ Name='PEM RSA private key'; Pattern='PemPrivateKey'; Value='-----BEGIN RSA PRIVATE KEY-----'; Expected=$true }
    @{ Name='PEM EC private key'; Pattern='PemPrivateKey'; Value='-----BEGIN EC PRIVATE KEY-----'; Expected=$true }
    @{ Name='PEM DSA private key'; Pattern='PemPrivateKey'; Value='-----BEGIN DSA PRIVATE KEY-----'; Expected=$true }
    @{ Name='PEM OpenSSH private key'; Pattern='PemPrivateKey'; Value='-----BEGIN OPENSSH PRIVATE KEY-----'; Expected=$true }
    @{ Name='PEM certificate excluded'; Pattern='PemPrivateKey'; Value='-----BEGIN CERTIFICATE-----'; Expected=$false }
    @{ Name='PEM case-sensitive'; Pattern='PemPrivateKey'; Value='-----begin private key-----'; Expected=$false }
)

$failed = 0
foreach ($case in $cases) {
    $matched = [regex]::IsMatch(
        [string]$case.Value,
        [string]$patterns[[string]$case.Pattern],
        [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    )
    if ($matched -ne [bool]$case.Expected) {
        $failed++
        Write-Error "FAIL: $($case.Name) expected=$($case.Expected) actual=$matched"
    }
    else {
        Write-Host "PASS: $($case.Name)"
    }
}

if ($failed -gt 0) {
    throw "$failed C-54 pattern-contract test(s) failed."
}
Write-Host "C-54 pattern-contract tests passed: $($cases.Count)"
