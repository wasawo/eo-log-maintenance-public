#requires -Version 7.6.7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'LogFunctions.ps1')

function ConvertFrom-EoMachineConfigurationJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Json,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$ExpectedMachineId
    )

    # Structural/lexical validation only. Physical approved-root and reparse
    # identity checks remain mandatory before any operational side effect.
    $document = $null
    try {
        $document = [System.Text.Json.JsonDocument]::Parse($Json)
        $root = $document.RootElement
        if ($root.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
            throw 'configuration_object_required'
        }
        $common = @(
            'machineId', 'role', 'runtimeRoot', 'battleLogLocal', 'errorLogLocal',
            'battleLogDrive', 'errorLogDrive', 'maintenanceDrive', 'maintenanceLocal'
        )
        $required = if ($ExpectedMachineId -ceq 'PC-A') {
            @($common + @('battleLogArchive', 'errorLogArchive', 'allowArchive'))
        }
        else { $common }
        $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $result = [ordered]@{}
        foreach ($property in $root.EnumerateObject()) {
            if (-not $seen.Add($property.Name)) { throw 'configuration_duplicate_field' }
            if ($property.Name -cnotin $required) { throw 'configuration_unknown_field' }
            if ($property.Name -ceq 'allowArchive') {
                if ($property.Value.ValueKind -notin @(
                    [System.Text.Json.JsonValueKind]::True,
                    [System.Text.Json.JsonValueKind]::False
                )) { throw 'configuration_field_type_invalid' }
                $result[$property.Name] = $property.Value.GetBoolean()
            }
            else {
                if ($property.Value.ValueKind -ne [System.Text.Json.JsonValueKind]::String) {
                    throw 'configuration_field_type_invalid'
                }
                $result[$property.Name] = $property.Value.GetString()
            }
        }
        foreach ($name in $required) {
            if (-not $seen.Contains($name)) { throw 'configuration_missing_field' }
        }
        $expectedRole = if ($ExpectedMachineId -ceq 'PC-A') { 'primary' } else { 'secondary' }
        if ($result.machineId -cne $ExpectedMachineId -or $result.role -cne $expectedRole) {
            throw 'configuration_role_mismatch'
        }
        $paths = @{}
        foreach ($name in @($required | Where-Object { $_ -notin @('machineId', 'role', 'allowArchive') })) {
            $value = $result[$name]
            if ([string]::IsNullOrWhiteSpace($value) -or $value -notmatch '^[A-Za-z]:\\' -or
                $value.Substring(2) -match '[<>:"|?*\x00-\x1f]') {
                throw 'configuration_path_invalid'
            }
            foreach ($segment in $value.Substring(3).Split([char]'\')) {
                if ($segment -notin @('.', '..') -and
                    ($segment.EndsWith('.') -or $segment.EndsWith(' '))) {
                    throw 'configuration_path_invalid'
                }
            }

            try { $full = [IO.Path]::GetFullPath($value) }
            catch { throw 'configuration_path_invalid' }
            foreach ($segment in $full.Substring(3).Split([char]'\')) {
                if ($segment.EndsWith('.') -or $segment.EndsWith(' ')) {
                    throw 'configuration_path_invalid'
                }
            }
            $paths[$name] = $full.TrimEnd([char[]]'\/')
        }
        $comparison = [StringComparison]::OrdinalIgnoreCase
        $local = $paths.maintenanceLocal
        foreach ($name in @($paths.Keys | Where-Object { $_ -ne 'maintenanceLocal' })) {
            $other = $paths[$name]
            if ($local.Equals($other, $comparison) -or
                $local.StartsWith($other + '\', $comparison) -or
                $other.StartsWith($local + '\', $comparison)) {
                throw 'configuration_maintenance_local_overlap'
            }
        }
        # allowArchive:true is a valid PC-A configuration value, not permission
        # to archive: manifests, live cloud verification and other gates still apply.
        return [pscustomobject]$result
    }
    catch {
        $reason = $_.Exception.Message
        $allowed = @(
            'configuration_object_required', 'configuration_duplicate_field',
            'configuration_unknown_field', 'configuration_field_type_invalid',
            'configuration_missing_field', 'configuration_role_mismatch',
            'configuration_path_invalid', 'configuration_maintenance_local_overlap'
        )
        if ($reason -cnotin $allowed) { $reason = 'configuration_json_invalid' }
        throw $reason
    }
    finally {
        if ($null -ne $document) { $document.Dispose() }
    }
}

function Read-EoMachineConfiguration {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$LiteralPath,
        [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$ExpectedMachineId
    )
    try {
        $encoding = [Text.UTF8Encoding]::new($false, $true)
        $json = $encoding.GetString([IO.File]::ReadAllBytes($LiteralPath))
        if ($json.Length -gt 0 -and [int]$json[0] -eq 0xfeff) { $json = $json.Substring(1) }
    }
    catch { throw 'configuration_read_failed' }
    return ConvertFrom-EoMachineConfigurationJson -Json $json -ExpectedMachineId $ExpectedMachineId
}
