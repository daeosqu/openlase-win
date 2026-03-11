<#
OpenLase PATH helper module.

$env:OL_BUILD_DIR defined -> development mode

Development mode:
    A valid source directory must contain:
        CMakeLists.txt
        VERSION

    Candidates checked while walking upward:
        CurrentDir
        CurrentDir\openlase-win

Installed mode:
    The directory (or its parents) must contain:
        share\openlase\VERSION

Usage
-----

Development:

    $env:OL_BUILD_DIR = "D:\oldev4\openlase-win-dev\build"
    Get-OlPathAuto -BaseDir "D:\oldev4\openlase-win-dev"

Installed:

    Remove-Item Env:OL_BUILD_DIR -ErrorAction Ignore
    Get-OlPathAuto -BaseDir "C:\Program Files\openlase-0.0.4"
#>

function Find-AhkDir {
    [CmdletBinding()]
    param()

    $rootCandidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($env:AHK_DIR)) {
        $rootCandidates.Add($env:AHK_DIR)
    }

    try {
        $ahkRoot = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\AutoHotkey' -ErrorAction Stop).InstallDir
        if (-not [string]::IsNullOrWhiteSpace($ahkRoot)) {
            $rootCandidates.Add($ahkRoot)

            $v1dirs = Get-ChildItem -LiteralPath $ahkRoot -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^v1(\.|$)' } |
                Sort-Object -Property Name

            foreach ($dir in $v1dirs) {
                $rootCandidates.Add($dir.FullName)
            }
        }
    }
    catch {
    }

    $defaultDirs = @(
        'C:\Program Files\AutoHotkey',
        'C:\Program Files\AutoHotkey\v1',
        'C:\Program Files (x86)\AutoHotkey',
        'C:\Program Files (x86)\AutoHotkey\v1'
    )

    foreach ($dir in $defaultDirs) {
        $rootCandidates.Add($dir)
    }

    $roots = Normalize-UniquePathList -Paths $rootCandidates

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }

        $exeCandidates = @(
            (Join-Path $root 'AutoHotkeyU64.exe'),
            (Join-Path $root 'AutoHotkey.exe')
        )

        foreach ($exe in $exeCandidates) {
            if (Test-Path -LiteralPath $exe -PathType Leaf) {
                return $root
            }
        }
    }

    return $null
}

function Normalize-UniquePathList {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Paths
    )

    $seen = @{}
    $result = New-Object System.Collections.Generic.List[string]

    foreach ($p in $Paths) {
        if ([string]::IsNullOrWhiteSpace($p)) {
            continue
        }

        $trimmed = $p.Trim()

        try {
            $resolved = (Resolve-Path -LiteralPath $trimmed -ErrorAction Stop).Path
        }
        catch {
            $resolved = $trimmed
        }

        $key = $resolved.TrimEnd('\', '/').ToLowerInvariant()

        if ($seen.ContainsKey($key)) {
            continue
        }

        $seen[$key] = $true
        $result.Add($resolved)
    }

    return @($result)
}

function Resolve-OlSearchStartDir {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $null
    )

    if ([string]::IsNullOrWhiteSpace($BaseDir)) {
        return $PSScriptRoot
    }

    try {
        $item = Get-Item -LiteralPath $BaseDir -ErrorAction Stop
    }
    catch {
        return $null
    }

    if ($item.PSIsContainer) {
        return $item.FullName
    }

    if ($null -eq $item.Directory) {
        return $null
    }

    return $item.Directory.FullName
}

function Find-OlRootUpward {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $null,

        [Parameter(Mandatory = $true)]
        [ValidateSet('source', 'installed')]
        [string]$Kind
    )

    $startDir = Resolve-OlSearchStartDir -BaseDir $BaseDir
    if ($null -eq $startDir) {
        return $null
    }

    $rules = @{
        source = [pscustomobject]@{
            GetCandidates = {
                param([string]$dir)
                @(
                    $dir
                    (Join-Path $dir 'openlase-win')
                )
            }
            Test = {
                param([string]$dir)
                (Test-Path -LiteralPath $dir -PathType Container) -and
                (Test-Path -LiteralPath (Join-Path $dir 'CMakeLists.txt') -PathType Leaf) -and
                (Test-Path -LiteralPath (Join-Path $dir 'VERSION') -PathType Leaf)
            }
        }
        installed = [pscustomobject]@{
            GetCandidates = {
                param([string]$dir)
                @($dir)
            }
            Test = {
                param([string]$dir)
                (Test-Path -LiteralPath $dir -PathType Container) -and
                (Test-Path -LiteralPath (Join-Path $dir 'share\openlase\VERSION') -PathType Leaf)
            }
        }
    }

    $rule = $rules[$Kind]
    $seen = @{}
    $current = $startDir

    while ($null -ne $current) {
        $candidates = @(& $rule.GetCandidates $current)

        foreach ($candidate in $candidates) {
            if ([string]::IsNullOrWhiteSpace($candidate)) {
                continue
            }

            $key = $candidate.TrimEnd('\', '/').ToLowerInvariant()
            if ($seen.ContainsKey($key)) {
                continue
            }

            $seen[$key] = $true

            if (& $rule.Test $candidate) {
                return $candidate
            }
        }

        $parent = Split-Path -Path $current -Parent
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            break
        }

        $current = $parent
    }

    return $null
}

function Resolve-OlSourceDir {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $null
    )

    return Find-OlRootUpward -BaseDir $BaseDir -Kind source
}

function Resolve-OlInstalledDir {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $null
    )

    return Find-OlRootUpward -BaseDir $BaseDir -Kind installed
}

function Test-OlDevelopmentDir {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $PSScriptRoot
    )

    return $null -ne (Resolve-OlSourceDir -BaseDir $BaseDir)
}

function Get-OlExtraPathInstalled {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $null
    )

    $resolvedBaseDir = Resolve-OlInstalledDir -BaseDir $BaseDir
    if ($null -eq $resolvedBaseDir) {
        if ([string]::IsNullOrWhiteSpace($BaseDir)) {
            throw "Could not resolve OpenLase installed directory from module location."
        }

        throw "Could not resolve OpenLase installed directory from BaseDir: $BaseDir"
    }

    $ahkDir = Find-AhkDir
    $entries = New-Object System.Collections.Generic.List[string]

    if ($ahkDir) {
        $entries.Add($ahkDir)
    }

    $entries.Add('C:\Program Files\JACK2')
    $entries.Add('C:\Program Files\JACK2\qjackctl')
    $entries.Add('C:\Program Files\JACK2\tools')

    $entries.Add((Join-Path $resolvedBaseDir 'bin'))
    $entries.Add((Join-Path $resolvedBaseDir 'bin\scripts\win'))

    return Normalize-UniquePathList -Paths $entries
}

function Get-OlExtraPathDev {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$OlBuildDir,

        [string]$BaseDir = $null
    )

    $resolvedBaseDir = Resolve-OlSourceDir -BaseDir $BaseDir
    if ($null -eq $resolvedBaseDir) {
        if ([string]::IsNullOrWhiteSpace($BaseDir)) {
            throw "Could not resolve OpenLase source directory."
        }

        throw "Invalid OpenLase source directory: $BaseDir"
    }

    $resolvedBuildDir = [System.IO.Path]::GetFullPath($OlBuildDir)

    $ahkDir = Find-AhkDir
    $entries = New-Object System.Collections.Generic.List[string]

    if ($ahkDir) {
        $entries.Add($ahkDir)
    }

    $entries.Add('C:\Program Files\JACK2')
    $entries.Add('C:\Program Files\JACK2\qjackctl')
    $entries.Add('C:\Program Files\JACK2\tools')

    $entries.Add($resolvedBuildDir)
    $entries.Add((Join-Path $resolvedBuildDir 'libol'))
    $entries.Add((Join-Path $resolvedBuildDir 'tools'))
    $entries.Add((Join-Path $resolvedBuildDir 'tools\qplayvid'))
    $entries.Add((Join-Path $resolvedBuildDir 'output'))
    $entries.Add((Join-Path $resolvedBuildDir 'examples'))
    $entries.Add((Join-Path $resolvedBuildDir 'examples\lase_demo'))
    $entries.Add((Join-Path $resolvedBuildDir 'jopa_install\usr\local\bin'))

    $entries.Add((Join-Path $resolvedBaseDir 'scripts\win'))
    $entries.Add((Join-Path $resolvedBaseDir 'tools'))

    return Normalize-UniquePathList -Paths $entries
}

function Get-OlPathAuto {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $PSScriptRoot
    )

    $startDir = Resolve-OlSearchStartDir -BaseDir $BaseDir
    if ($null -eq $startDir) {
        throw "BaseDir not found: $BaseDir"
    }

    $sourceDir = Resolve-OlSourceDir -BaseDir $startDir
    if ($null -ne $sourceDir) {
        if ([string]::IsNullOrWhiteSpace($env:OL_BUILD_DIR)) {
            throw "Development directory detected, but OL_BUILD_DIR is not set."
        }

        $entries = Get-OlExtraPathDev `
            -OlBuildDir $env:OL_BUILD_DIR `
            -BaseDir $sourceDir

        return [pscustomobject]@{
            Mode         = 'devel'
            SourceDir    = $sourceDir
            InstalledDir = $null
            AddedEntries = @($entries)
        }
    }

    $installedDir = Resolve-OlInstalledDir -BaseDir $startDir
    if ($null -eq $installedDir) {
        throw "Could not resolve OpenLase directory from BaseDir: $BaseDir"
    }

    $entries = Get-OlExtraPathInstalled -BaseDir $installedDir

    return [pscustomobject]@{
        Mode         = 'installed'
        SourceDir    = $null
        InstalledDir = $installedDir
        AddedEntries = @($entries)
    }
}

function Set-OlPathAuto {
    [CmdletBinding()]
    param(
        [string]$BaseDir = $PSScriptRoot
    )

    $info = Get-OlPathAuto -BaseDir $BaseDir

    if ([string]::IsNullOrWhiteSpace($env:OL_PATH_SAVE)) {
        $env:OL_PATH_SAVE = $env:PATH
    }

    $basePaths = @()
    if (-not [string]::IsNullOrWhiteSpace($env:OL_PATH_SAVE)) {
        $basePaths = @($env:OL_PATH_SAVE -split ';')
    }

    $paths = @($info.AddedEntries) + $basePaths
    $merged = Normalize-UniquePathList -Paths $paths

    $env:PATH = [string]::Join(';', $merged)
}

Export-ModuleMember -Function `
  Find-AhkDir, `
  Resolve-OlSourceDir, `
  Resolve-OlInstalledDir, `
  Test-OlDevelopmentDir, `
  Get-OlExtraPathDev, `
  Get-OlExtraPathInstalled, `
  Get-OlPathAuto, `
  Set-OlPathAuto
