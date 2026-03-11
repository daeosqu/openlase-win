[cmdletbinding()]
param()

# Import necessary modules
Import-Module "$PSScriptRoot\functions.psm1"
Import-Module "$PSScriptRoot\ol_paths.psm1"
Import-Module "$PSScriptRoot\ol_utils.psm1"

$env:DISTUTILS_USE_SDK = "1"

# Detect project root or installed directory
$DevRoot = Resolve-OlSourceDir
$InstallRoot = Resolve-OlInstalledDir
$OlDir = if ($DevRoot) { $DevRoot } else { $InstallRoot }

# Check detected directories and set up environment variables accordingly
if ($DevRoot) {
    # Development mode
    Write-Verbose -Message "OpenLase directory [SOURCE]: $DevRoot" -Verbose
    $openlaserc = "$DevRoot\.openlaserc.ps1"
    if (-not $env:OL_BUILD_DIR) {
	$env:OL_BUILD_DIR = Join-Path $DevRoot "build"
	Write-Verbose -Message "OL_BUILD_DIR is not set, default is $env:OL_BUILD_DIR" -Verbose
    }
} elseif ($InstallRoot) {
    Write-Verbose -Message "OpenLase directory [INSTALLED]: $InstallRoot" -Verbose
    # Installed mode
    $openlaserc = "$HOME\.openlaserc.ps1"
} else {
    Write-Warning -Message "Error: Could not determine OpenLase directory. Please run openlase-dev.cmd in OpenLase source directory or openlase.cmd in OpenLase installation directory." -WarningAction Continue
}

# Load .openlaserc if it exists
if (Test-Path -Path $openlaserc) {
    Write-Verbose -Message "Loading $openlaserc" -Verbose
    . $openlaserc
} else {
    Write-Verbose -Message "NOTE: You can create an initialization script at $openlaserc" -Verbose
}

# Enable Visual Studio Development Environment if in development mode
if ($DevRoot) {
    Enable-VsDevEnv
}

# Initialize path
Set-OlPathAuto

# Set OL_DATA_DIR if not defined, and create the directory if it doesn't exist
if (-not $env:OL_DATA_DIR) {
    $env:OL_DATA_DIR = "$HOME\.cache\openlase"
    Write-Verbose -Message "OL_DATA_DIR is not set, default is $env:OL_DATA_DIR" -Verbose
}
New-Item -Path "$env:OL_DATA_DIR" -ItemType Directory -ErrorAction SilentlyContinue

# Title for Windows Terminal
$title = "OpenLase"

# Version
$version_file = Join-Path -Path "$OlDir" -ChildPath 'VERSION'
if (-not (Test-Path -Path $version_file)) {
    $version_file = Join-Path -Path "$OlDir" -ChildPath 'share\openlase\VERSION'
}
if (Test-Path -Path $version_file) {
    $version = Get-Content -Path $version_file -Raw | Select-Object -First 1
}
if ($version -ne "") {
    $title = "$title $version"
}

# Set title and CD
if ($DevRoot) {
    $Host.UI.RawUI.WindowTitle = "$title [DEV]"
    Write-Verbose -Message "Development mode (OL_DEVEL is true)"
    Set-Location -Path $OlDir
} else {
    $Host.UI.RawUI.WindowTitle = "$title"
}
