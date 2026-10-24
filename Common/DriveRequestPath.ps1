#requires -Version 7.6.7
Set-StrictMode -Version Latest

function Test-DriveRequestFilePath {
    <#
    .SYNOPSIS
    Checks only the C-01 P1/L1 request-file-path grammar without I/O.
    .DESCRIPTION
    No normalization, root authority, target validation or filesystem access.
    True never authorizes reading, writing, Drive access or operational use.
    #>
    [CmdletBinding()]
    param([AllowNull()] [AllowEmptyString()] [object] $Value)

    if ($Value -isnot [string] -or
        $Value -cnotmatch '\A[A-Za-z]:\\[^\\/:<>"|?*\x00-\x1f\x7f]+(?:\\[^\\/:<>"|?*\x00-\x1f\x7f]+)*\z') {
        return $false
    }
    foreach ($component in $Value.Substring(3).Split([char]'\')) {
        if ($component.EndsWith('.') -or $component.EndsWith(' ')) { return $false }
        $stem = $component.Split([char]'.')[0].TrimEnd([char]' ')
        # Explicit ASCII letter classes avoid Unicode/culture case folding.
        if ($stem -cmatch '\A(?:[Cc][Oo][Nn]|[Pp][Rr][Nn]|[Aa][Uu][Xx]|[Nn][Uu][Ll]|[Cc][Oo][Mm][1-9¹²³]|[Ll][Pp][Tt][1-9¹²³]|[Cc][Oo][Nn][Ii][Nn]\$|[Cc][Oo][Nn][Oo][Uu][Tt]\$)\z') {
            return $false
        }
    }
    return $true
}
