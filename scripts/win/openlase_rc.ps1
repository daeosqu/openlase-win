[cmdletbinding()]
param()

$OldVerbosePreference=$VerbosePreference
$VerbosePreference="SilentlyContinue"
Import-Module $PSScriptRoot\functions.psm1
$VerbosePreference=$OldVerbosePreference

if (-Not $env:AHK_DIR) {
    $env:AHK_DIR=Get-ChildItem "C:\Program Files\AutohotKey" -Directory | Where-Object -Property Name -like v1.* | Select-Object -First 1 | % { $_.FullName }
}
if (-Not $env:AHK_DIR) {
    Write-Verbose -Message "AutoHotKey is not installed." -Verbose
}

if (-Not $env:WIX_DIR) {
    $env:WIX_DIR=Get-ChildItem "C:\Program Files (x86)" -Directory | Where-Object -Property Name -like "WiX Toolset v3.*" | Select-Object -First 1 | % { $_.FullName }
}
if ($env:WIX_DIR) {
    Write-Verbose -Message "Wix v3 found $env:WIX_DIR"
    $env:PATH = "$env:PATH;$env:WIX_DIR\bin"
} else {
    Write-Verbose -Message "WIX_DIR is not set." -Verbose
}

if (-Not $env:OL_DIR) {
    $env:OL_DIR = "$PSScriptRoot\..\.." | Resolve-Path
}
Write-Verbose -Message "OL_DIR is $env:OL_DIR"

if ($env:OL_DEVEL) {
    Write-Verbose -Message "Development mode (OL_DEVEL is true)"
    cd $env:OL_DIR
}

if (-Not $env:OL_DEVEL) {
    $openlaserc="$HOME\.openlaserc.ps1"
} else {
    $openlaserc="$env:OL_DIR\.openlaserc.ps1"
}

if (Test-Path "$openlaserc") {
    Write-Verbose -Message "loading $openlaserc" -Verbose
    . "$openlaserc"
} else {
    Write-Verbose -Message "NOTE: You can make a initialization script to $openlaserc" -Verbose
}

if ($env:OL_DATA_DIR) {
    Write-Verbose -Message "OL_DATA_DIR is $env:OL_DATA_DIR"
} else {
    $env:OL_DATA_DIR="$HOME\.cache\openlase"
    Write-Verbose -Message "OL_DATA_DIR is not set, default is $env:OL_DATA_DIR" -Verbose
}

md "$env:OL_DATA_DIR" -ea 0

$env:PATH="$env:AHK_DIR;$env:PATH"
$env:PATH="C:\Program Files\JACK2;$env:PATH"
$env:PATH="C:\Program Files\JACK2\qjackctl;$env:PATH"
$env:PATH="C:\Program Files\JACK2\tools;$env:PATH"
if ($env:OL_DEVEL) {
    $env:OL_BUILD_DIR="$env:OL_DIR\build"
    $env:PATH="$env:OL_DIR\build\libol;$env:PATH"
    $env:PATH="$env:OL_DIR\build\tools;$env:PATH"
    $env:PATH="$env:OL_DIR\build\tools\qplayvid;$env:PATH"
    $env:PATH="$env:OL_DIR\build\output;$env:PATH"
    $env:PATH="$env:OL_DIR\build\examples;$env:PATH"
    $env:PATH="$env:OL_DIR\build\examples\lase_demo;$env:PATH"
    $env:PATH="$env:OL_DIR\build\jopa_install\usr\local\bin;$env:PATH"
    $env:PATH="$env:OL_DIR;$env:PATH"
    $env:PATH="$env:OL_DIR\scripts\win;$env:PATH"
    $env:PATH="$env:OL_DIR\tools;$env:PATH"

    if (-Not $env:Qt5_DIR) {
	If (Test-Path "C:/Qt/Qt5.14.2/5.14.2/msvc2017_64") {
	    $env:Qt5_DIR = "C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"
	    Write-Warning -Message "Qt5_DIR is not set, default is $env:Qt5_DIR."
	} else {
	    Write-Warning -Message "Qt5_DIR is not set, please set Qt5_DIR."
	}
    }
    $env:PYTHONPATH="$env:OL_DIR\build\python"

    if ( ! $env:VCPKG_ROOT) {
	if (Test-Path "$env:USERPROFILE\scoop\apps\vcpkg\current\scripts\buildsystems\vcpkg.cmake") {
	    $env:VCPKG_ROOT = "$env:USERPROFILE\scoop\apps\vcpkg\current";
	    Write-Verbose -Message "set VCPKG_ROOT=$env:VCPKG_ROOT" -Verbose
	} else {
	    Write-Warning -Message "Please set VCPKG_ROOT."
	}
    }

    if ($env:VCPKG_ROOT -and ! (Test-Path "$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake")) {
	Write-Warning -Message "Can not find vcpkg.cmake in $env:VCPKG_ROOT."
    } else {
	Write-Verbose -Message "Found vcpkg: $env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"
    }
} else {
    $env:OL_BUILD_DIR=""
    $env:PATH="$env:OL_DIR\bin;$env:PATH"
    $env:PATH="$env:OL_DIR;$env:PATH"
    $env:PATH="$env:OL_DIR\bin\scripts\win;$env:PATH"
    $env:PATH="$env:OL_DIR\tools;$env:PATH"
    $env:PYTHONPATH="$env:OL_DIR\bin"
}

if (-Not $env:OL_PYTHON_DIR) {
    if (Test-Path "C:\opt\python311") {
	$env:OL_PYTHON_DIR="C:\opt\python311"
    } Else {
	Write-Verbose -Message "OL_PYTHON_DIR is not set." -Verbose
    }
}

if (Test-Path "$env:OL_PYTHON_DIR") {
    $env:PATH="$env:OL_PYTHON_DIR\Scripts;$env:PATH"
    $env:PATH="$env:OL_PYTHON_DIR;$env:PATH"
}

$VerbosePreference=$OldVerbosePreference
