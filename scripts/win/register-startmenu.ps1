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
$ErrorActionPreference = "Stop"

if ($allusers) {
    $data_dir = $env:ProgramData
} else {
    $data_dir = $env:APPDATA
}

$script_dir = Resolve-Path "$PSScriptRoot\..\.."
$work_dir = $script_dir

if (Test-Path "$script_dir\res\laser.ico") {
    $root_dir = Resolve-Path "$script_dir"
} else {
    $root_dir = Resolve-Path "$script_dir\.."
}

$ico = Resolve-Path "$root_dir\share\openlase\laser.ico"

$version = (Select-String -Path "$root_dir\share\openlase\VERSION" "(OpenLase)? *([a-zA-Z0-9._-]+)" | Select -First 1 | % { $_.matches.groups[2].value -split '\.' } | Select-Object -First 3) -join "."
$menu_dir = $data_dir + "\Microsoft\Windows\Start Menu\Programs"

if (Test-Path $script_dir\.git) {
    $name = "${name}-dev"
    $cmd = Resolve-Path "$script_dir\openlase.cmd"
} else {
    $cmd = Resolve-Path "$script_dir\openlase.cmd"
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

