#requires -Version 7.6.7
Set-StrictMode -Version Latest

function ConvertFrom-EoPrivateFileSecurityDescriptor {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [byte[]]$SecurityDescriptorBytes
    )
    # Internal sensitive observation only. Never a public diagnostic or a file
    # provider: no Get-Acl/Get-Item/token query, descriptor write or permission.
    try {
        if ($null -eq $SecurityDescriptorBytes -or $SecurityDescriptorBytes.Length -eq 0) {
            throw 'invalid'
        }
        $snapshot = [byte[]]$SecurityDescriptorBytes.Clone()
        $descriptor = [System.Security.AccessControl.RawSecurityDescriptor]::new($snapshot, 0)
        $control = [System.Security.AccessControl.ControlFlags]
        $allowedFlags = [int]$control::SelfRelative -bor [int]$control::DiscretionaryAclPresent -bor [int]$control::DiscretionaryAclProtected
        if (([int]$descriptor.ControlFlags -band (-bnot $allowedFlags)) -ne 0 -or
            ($descriptor.ControlFlags -band $control::SelfRelative) -eq 0 -or
            $null -eq $descriptor.Owner -or $null -ne $descriptor.SystemAcl -or
            $descriptor.BinaryLength -ne $snapshot.Length) {
            throw 'unsupported'
        }
        $roundtrip = [byte[]]::new($descriptor.BinaryLength)
        $descriptor.GetBinaryForm($roundtrip, 0)
        if ([Convert]::ToBase64String($roundtrip) -cne [Convert]::ToBase64String($snapshot)) {
            throw 'unsupported'
        }
        $entries = [System.Collections.Generic.List[object]]::new()
        if ($null -ne $descriptor.DiscretionaryAcl) {
            foreach ($ace in $descriptor.DiscretionaryAcl) {
                if ($ace -isnot [System.Security.AccessControl.CommonAce] -or $ace.IsCallback) {
                    throw 'unsupported'
                }
                $kind = switch ($ace.AceQualifier) {
                    ([System.Security.AccessControl.AceQualifier]::AccessAllowed) { 'allow' }
                    ([System.Security.AccessControl.AceQualifier]::AccessDenied) { 'deny' }
                    default { throw 'unsupported' }
                }
                $mask = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$ace.AccessMask), 0)
                $entries.Add([ordered]@{
                    sid = $ace.SecurityIdentifier.Value
                    type = $kind
                    flags = [int]$ace.AceFlags
                    mask = $mask
                })
            }
        }
        return [ordered]@{
            object_kind = 'file'
            owner_sid = $descriptor.Owner.Value
            dacl_present = [bool](($descriptor.ControlFlags -band $control::DiscretionaryAclPresent) -ne 0)
            dacl_null = [bool]($null -eq $descriptor.DiscretionaryAcl)
            dacl_protected = [bool](($descriptor.ControlFlags -band $control::DiscretionaryAclProtected) -ne 0)
            aces = [object[]]$entries.ToArray()
        }
    }
    catch {
        throw [System.InvalidOperationException]::new('private_acl_descriptor_invalid_or_unsupported')
    }
}
