<#
 .SYNOPSIS
   This is a powershell script to register openlase.cmd to start menu.
 .PARAMETER name
   Specify short cut name
 .PARAMETER allusers
   Install for all users
 .PARAMETER uninstall
   Uninstall short cuts
 .NOTES
   Version:        1.0
   Author:         Daisuke Arai
 .EXAMPLE
   register-startmenu.ps1
 .EXAMPLE
   register-startmenu.ps1 -uninstall
 #>

param (
    [switch]$uninstall = $false,
    [switch]$allusers = $false,
    [string]$name = "OpenLase",
    [string]$ico = ""
)

Set-StrictMode -Version Latest

if ($allusers) {
    $data_dir = $env:ProgramData
} else {
    $data_dir = $env:APPDATA
}

$ol_dir = (Resolve-Path -Path "$PSScriptRoot\..\..").Path

if (Test-Path "$ol_dir\res\laser.ico") {
    # C:\repos\openlase-win\scripts\win\register-startmenu.ps1
    $cmd = Resolve-Path "$ol_dir\openlase.cmd"
    $ico = Resolve-Path "$ol_dir\res\laser.ico"
    $version_file = "$ol_dir\VERSION"
    $work_dir = $ol_dir
} else {
    # C:\Program Files\OpenLase\bin\scripts\win\register-startmenu.ps1
    $ol_dir = (Resolve-Path -Path "$PSScriptRoot\..\..\..").Path
    $cmd = Resolve-Path "$ol_dir\bin\openlase.cmd"
    $ico = Resolve-Path "$ol_dir\share\openlase\laser.ico"
    $version_file = "$ol_dir\share\openlase\VERSION"
    $work_dir = $ol_dir
}

echo "ol_dir: $ol_dir"
echo "cmd: $cmd"
echo "ico: $ico"
echo "version_file: $version_file"
echo "work_dir: $work_dir"
echo "data_dir: $data_dir"

$version = (Select-String -Path "$version_file" "(OpenLase)? *([a-zA-Z0-9._-]+)" | Select -First 1 | % { $_.matches.groups[2].value -split '\.' } | Select-Object -First 3) -join "."
$menu_dir = $data_dir + "\Microsoft\Windows\Start Menu\Programs"

if (Test-Path $ol_dir\.git) {
    $name = "${name}-dev"
    $work_dir = $ol_dir
} else {
    $work_dir = $env:USERPROFILE
}

if ($uninstall) {
    Remove-Item -Force "$menu_dir\${name}-${version}.lnk"
} else {
    &"$PSScriptRoot\create-shortcut.ps1" "${menu_dir}\${name}-${version}.lnk" "$cmd" "$ico" "$work_dir"
}

if ($allusers) {
    # Update start menu
    Restart-Service WSearch -Force
}
