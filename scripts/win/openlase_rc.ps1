[cmdletbinding()]
param()

# Import necessary modules
Import-Module "$PSScriptRoot\functions.psm1"

# Functions
function Enable-VsDevEnv {
    # Get the list of Visual Studio instances, sorted by version, and filtered for specific product types
    $vsInstances = Get-CimInstance -ClassName MSFT_VSInstance -Namespace root/cimv2/vs |
        Sort-Object -Property Version |
        Where-Object -Property ProductId -match '^Microsoft\.VisualStudio\.Product\.(Community|Professional|Enterprise)$'
    
    # If no Visual Studio instances are found, display a warning and return
    if (-not $vsInstances) {
        Write-Warning -Message "Error: Visual Studio is not installed."
        return
    }
    
    # Get the latest version of Visual Studio installed
    $vsLatestVersion = ($vsInstances | ForEach-Object { [System.Version]($_.Version) } | Sort-Object | Select-Object -Last 1).ToString()
    $vs = $vsInstances | Where-Object -Property Version -eq $vsLatestVersion
    
    # Import the Visual Studio development shell module and set up the environment
    Import-Module ($vs.InstallLocation + "\Common7\Tools\Microsoft.VisualStudio.DevShell.dll")
    $env:VSINSTALLDIR = ""
    Enter-VsDevShell -InstanceId $vs.IdentifyingNumber -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64"
}

function Get-PythonDirectory {
    # Check if pyenv command exists
    $pyenvExec = Get-Command -Name pyenv -ErrorAction SilentlyContinue
    if ($pyenvExec) {
        # If pyenv exists, use pyenv which python to get the Python path
        $pythonPath = pyenv which python
        if ($pythonPath) {
            return (Get-Item -Path $pythonPath).DirectoryName
        }
    }
    
    # If pyenv doesn't exist or fails, fallback to finding python normally
    $pyexec = Get-Command -Name python.exe -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" }
    if ($pyexec) {
        return (Get-Item -Path $pyexec.Path).DirectoryName
    }

    return $null
}

# Set OL_DIR if not defined, resolving its path based on the presence of openlase.cmd
if (-not $env:OL_DIR) {
    if (Test-Path -Path "$PSScriptRoot\..\..\VERSION") {
	$env:OL_DIR = (Resolve-Path -Path "$PSScriptRoot\..\..").Path
    } elseif (Test-Path -Path "$PSScriptRoot\..\..\..\share\openlase\VERSION") {
	$env:OL_DIR = (Resolve-Path -Path "$PSScriptRoot\..\..\..").Path
    } else {
        Write-Warning "Can not find VERSION file. OL_DIR environment variable could not be set."
    }
}

if (-not $env:OL_DIR) {
    $env:OL_DIR = "C:\Program Files\OpenLase"
    Write-Verbose -Message "OL_DIR is not set, default is $env:OL_DIR" -Verbose
} else {
    Write-Verbose -Message "OL_DIR is $env:OL_DIR" -Verbose
}

if ($env:OL_DEVEL -eq $null) {
    if (Test-Path -Path "$env:OL_DIR\.git") {
	$env:OL_DEVEL = 1
    } else {
	$env:OL_DEVEL = ""
    }
}

# Environment Variables Setup
# Set default build type if not defined
if (-not $env:OL_BUILD_TYPE) {
    $env:OL_BUILD_TYPE = "Release"
}

# Load OpenLase initialization script based on whether in development mode or not
$openlaserc = if (-not $env:OL_DEVEL) { "$HOME\.openlaserc.ps1" } else { "$env:OL_DIR\.openlaserc.ps1" }
if (Test-Path -Path $openlaserc) {
    Write-Verbose -Message "Loading $openlaserc" -Verbose
    . $openlaserc
} else {
    Write-Verbose -Message "NOTE: You can create an initialization script at $openlaserc" -Verbose
}

# Find AutoHotkey executable directory
# Set AHK_DIR if not defined, looking up in the registry and finding the appropriate version
if (-not $env:AHK_DIR) {
    $ahkDir = (Get-ItemProperty -Path "HKLM:\SOFTWARE\AutoHotkey").InstallDir
    $env:AHK_DIR = Get-ChildItem -Path $ahkDir -Directory | Where-Object -Property Name -match '^v1\..*' | Select-Object -First 1 | ForEach-Object { $_.FullName }
    if (-not $env:AHK_DIR) {
        $env:AHK_DIR = $ahkDir
    }
}

# Verify if AutoHotkey executable exists in AHK_DIR
if ($env:AHK_DIR) {
    if (-not (Test-Path -Path "$env:AHK_DIR\AutoHotkeyU64.exe")) {
        Write-Verbose -Message "Cannot find AutoHotKey v1" -Verbose
    }
} else {
    Write-Verbose -Message "Please set AHK_DIR" -Verbose
}

# Enable Visual Studio Development Environment if in development mode
if ($env:OL_DEVEL) {
    Enable-VsDevEnv
}

# Set OL_DATA_DIR if not defined, and create the directory if it doesn't exist
if (-not $env:OL_DATA_DIR) {
    $env:OL_DATA_DIR = "$HOME\.cache\openlase"
    Write-Verbose -Message "OL_DATA_DIR is not set, default is $env:OL_DATA_DIR" -Verbose
}
New-Item -Path "$env:OL_DATA_DIR" -ItemType Directory -ErrorAction SilentlyContinue

# Update PATH to include necessary directories
$env:PATH = "$env:AHK_DIR;$env:PATH"
$env:PATH = "C:\Program Files\JACK2;$env:PATH"
$env:PATH = "C:\Program Files\JACK2\qjackctl;$env:PATH"
$env:PATH = "C:\Program Files\JACK2\tools;$env:PATH"

if ($env:OL_DEVEL) {
    # If in development mode, update PATH to include various build directories
    if (-not $env:WIX) {
        Write-Verbose -Message "WIX is not set." -Verbose
    }
    $env:OL_BUILD_DIR = "$env:OL_DIR\build-$env:OL_BUILD_TYPE.Windows"
    $env:PATH = "$env:OL_BUILD_DIR\libol;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\tools;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\tools\qplayvid;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\output;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\examples;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\examples\lase_demo;$env:PATH"
    $env:PATH = "$env:OL_BUILD_DIR\jopa_install\usr\local\bin;$env:PATH"
    $env:PATH = "$env:OL_DIR;$env:PATH"
    $env:PATH = "$env:OL_DIR\scripts\win;$env:PATH"
    $env:PATH = "$env:OL_DIR\tools;$env:PATH"

    # Set Qt5_DIR if not already set, based on default Qt installation path
    if (-not $env:Qt5_DIR) {
        if (Test-Path -Path "C:/Qt/Qt5.14.2/5.14.2/msvc2017_64") {
            $env:Qt5_DIR = "C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"
            Write-Warning -Message "Qt5_DIR is not set, default is $env:Qt5_DIR."
        } else {
            Write-Warning -Message "Qt5_DIR is not set, please set Qt5_DIR."
        }
    }
    $env:PYTHONPATH = "$env:OL_BUILD_DIR\python"

    # Verify if vcpkg.cmake exists in VCPKG_ROOT
    if ($env:VCPKG_ROOT -and -not (Test-Path -Path "$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake")) {
        Write-Warning -Message "Cannot find vcpkg.cmake in $env:VCPKG_ROOT."
    } else {
        Write-Verbose -Message "Found vcpkg: $env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"
    }
} else {
    # If not in development mode, set build directory and update PATH accordingly
    $env:OL_BUILD_DIR = ""
    $env:PATH = "$env:OL_DIR\bin;$env:PATH"
    $env:PATH = "$env:OL_DIR;$env:PATH"
    $env:PATH = "$env:OL_DIR\bin\scripts\win;$env:PATH"
    $env:PATH = "$env:OL_DIR\tools;$env:PATH"
    $env:PYTHONPATH = "$env:OL_DIR\bin"
}

# Set OL_PYTHON_DIR if not defined, using Get-PythonDirectory function
if (-not $env:OL_PYTHON_DIR) {
    if ($env:OL_DEVEL) {
        # In development mode, change directory to OL_DIR before getting Python directory
        Push-Location -Path $env:OL_DIR
        $env:OL_PYTHON_DIR = Get-PythonDirectory
        Pop-Location
    } else {
        $env:OL_PYTHON_DIR = Get-PythonDirectory
    }
    
    # Log the Python directory information
    if ($env:OL_PYTHON_DIR) {
        Write-Verbose -Message "OL_PYTHON_DIR is not set, default is $env:OL_PYTHON_DIR" -Verbose
    } else {
        Write-Verbose -Message "OL_PYTHON_DIR is not set. Please set OL_PYTHON_DIR." -Verbose
    }
}

# Update PATH to include Python directories if OL_PYTHON_DIR is set
if ($env:OL_PYTHON_DIR -and (Test-Path -Path "$env:OL_PYTHON_DIR")) {
    $env:PATH = "$env:OL_PYTHON_DIR\Scripts;$env:PATH"
    $env:PATH = "$env:OL_PYTHON_DIR;$env:PATH"
}

# Set title for Windows Terminal
$title = "OpenLase"
$version = ""

$version_file = Join-Path -Path "$env:OL_DIR" -ChildPath 'VERSION'
if (-not (Test-Path -Path $version_file)) {
    $version_file = Join-Path -Path "$env:OL_DIR" -ChildPath 'share\openlase\VERSION'
}

if (Test-Path -Path $version_file) {
    $version = Get-Content -Path $version_file -Raw | Select-Object -First 1
}

if ($version -ne "") {
    $title = "$title $version"
}

# If in development mode, change directory to OL_DIR
if ($env:OL_DEVEL) {
    $Host.UI.RawUI.WindowTitle = "$title [DEV]"
    Write-Verbose -Message "Development mode (OL_DEVEL is true)"
    Set-Location -Path $env:OL_DIR
} else {
    $Host.UI.RawUI.WindowTitle = "$title"
}
