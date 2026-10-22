#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MachineConfiguration.ps1')

function Initialize-EoMachineConfiguration {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ConfigDirectory,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$MachineId
    )

    # Explicit existing package directory only. Never invoked by dot-sourcing.
    # This is not a production installer or an approved-root runtime gate.
    $temporary = $null
    $temporaryOwned = $false
    $stream = $null
    try {
        $directory = [IO.DirectoryInfo]::new([IO.Path]::GetFullPath($ConfigDirectory))
        if (-not $directory.Exists) { throw 'configuration_bootstrap_failed' }
        $cursor = $directory
        while ($null -ne $cursor) {
            if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw 'configuration_bootstrap_failed'
            }
            $cursor = $cursor.Parent
        }
        $active = Join-Path $directory.FullName "$MachineId.json"
        # Any existing entry is preserved, including malformed configuration.
        # Reading/validating existing settings is the separate loader's job.
        if (Test-Path -LiteralPath $active) {
            return [pscustomobject]@{ Status = 'preserved'; MachineId = $MachineId }
        }
        $example = Join-Path $directory.FullName "$MachineId.example.json"
        $attributes = [IO.File]::GetAttributes($example)
        if (($attributes -band ([IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Directory)) -ne 0) {
            throw 'configuration_bootstrap_failed'
        }
        $bytes = [IO.File]::ReadAllBytes($example)
        $json = [Text.UTF8Encoding]::new($false, $true).GetString($bytes)
        if ($json.Length -gt 0 -and [int]$json[0] -eq 0xfeff) { $json = $json.Substring(1) }
        $configuration = ConvertFrom-EoMachineConfigurationJson -Json $json -ExpectedMachineId $MachineId
        if ($MachineId -ceq 'PC-A' -and $configuration.allowArchive) {
            throw 'configuration_bootstrap_failed'
        }
        $temporary = Join-Path $directory.FullName ('.configuration-' + [guid]::NewGuid().ToString('N') + '.tmp')
        $stream = [IO.FileStream]::new($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $temporaryOwned = $true
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        try {
            # Same-directory publication; the overload never overwrites a winner.
            [IO.File]::Move($temporary, $active, $false)
            $temporary = $null
        }
        catch [IO.IOException] {
            if (-not (Test-Path -LiteralPath $active)) { throw }
            return [pscustomobject]@{ Status = 'preserved'; MachineId = $MachineId }
        }
        return [pscustomobject]@{ Status = 'created'; MachineId = $MachineId }
    }
    catch { throw 'configuration_bootstrap_failed' }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        # Only our unique temporary path; never delete/replace an active config.
        if ($temporaryOwned -and $null -ne $temporary -and [IO.File]::Exists($temporary)) {
            try { [IO.File]::Delete($temporary) }
            catch { throw 'configuration_bootstrap_cleanup_failed' }
        }
    }
}
