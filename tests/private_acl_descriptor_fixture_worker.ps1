#requires -Version 7.6.7
# Test-only synthetic descriptors supplied on stdin; no runtime path/token I/O.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/PrivateFileSecurityDescriptor.ps1')
$fixtures = [Console]::In.ReadToEnd() | ConvertFrom-Json
$results = [System.Collections.Generic.List[object]]::new()
foreach ($fixture in $fixtures) {
    try {
        $descriptor = [System.Security.AccessControl.RawSecurityDescriptor]::new([string]$fixture.sddl)
        $bytes = [byte[]]::new($descriptor.BinaryLength)
        $descriptor.GetBinaryForm($bytes, 0)
        if ($fixture.mutation -eq 'callback') {
            $daclOffset = [BitConverter]::ToUInt32($bytes, 16)
            $bytes[$daclOffset + 8] = 9
        }
        if ($fixture.mutation -eq 'trailing') { $bytes = [byte[]]($bytes + 0) }
        if ($fixture.mutation -eq 'truncated') { $bytes = [byte[]]$bytes[0..5] }
        if ($fixture.mutation -eq 'empty') { $bytes = [byte[]]::new(0) }
        $before = [Convert]::ToBase64String($bytes)
        try {
            $observation = ConvertFrom-EoPrivateFileSecurityDescriptor -SecurityDescriptorBytes $bytes
            $results.Add(@{ ok = $true; observation = $observation; preserved = ($before -ceq [Convert]::ToBase64String($bytes)) })
        }
        catch {
            $results.Add(@{ ok = $false; reason = $_.Exception.Message; preserved = ($before -ceq [Convert]::ToBase64String($bytes)) })
        }
    }
    catch {
        $results.Add(@{ ok = $false; reason = 'synthetic_fixture_failed'; preserved = $false })
    }
}
ConvertTo-Json -InputObject ([object[]]$results.ToArray()) -Depth 10 -Compress
