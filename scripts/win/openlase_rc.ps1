[cmdletbinding()]
param()

$VerbosePreference="SilentlyContinue"

$ahkv1_dir=Get-ChildItem "C:\Program Files\AutohotKey" -Directory | Where-Object -Property Name -like v1.* | Select-Object -First 1 | % { $_.FullName }

if (-not (Get-Module pwsh-dotenv -ListAvailable)) {
    Install-Module pwsh-dotenv -Scope CurrentUser -Force
}

Import-Module $PSScriptRoot\functions.psm1
Import-Module pwsh-dotenv

$OldVerbosePreference=$VerbosePreference
$VerbosePreference="Continue"

$project_root="$PSScriptRoot\..\.." | Resolve-Path
$env="$project_root\.env"

if (Test-Path "$env") {
    Write-Verbose -Message "loading $env" -Verbose
    Import-Dotenv "$env"
}

if (-Not $env:OL_DEVEL) {
    if (Test-Path "$HOME/.openlase") {
	Write-Verbose -Message "loading $HOME/.openlase" -Verbose
	Import-Dotenv "$HOME/.openlase"
    }
}

if ($env:OL_DEVEL) {
    $env:OL_DIR=$project_root
} else {
    $env:OL_DIR="C:\Program Files\openlase"
}

if (-Not $env:OL_DATA_DIR) {
    $env:OL_DATA_DIR="$HOME/.cache/openlase"
}

if (-Not $env:OL_PYTHON_DIR) {
    $env:OL_PYTHON_DIR="C:\opt\python311"
}

md "$env:OL_DATA_DIR" -ea 0

$env:PATH="$ahkv1_dir;$env:PATH"
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
    $env:PYTHONPATH="$env:OL_DIR\build\python"
} else {
    $env:OL_BUILD_DIR=""
    $env:PATH="$env:OL_DIR\bin;$env:PATH"
    $env:PATH="$env:OL_DIR;$env:PATH"
    $env:PATH="$env:OL_DIR\bin\scripts\win;$env:PATH"
    $env:PATH="$env:OL_DIR\tools;$env:PATH"
    $env:PYTHONPATH="$env:OL_DIR\bin"
}
$env:PATH="C:\Qt\Qt5.14.2\5.14.2\msvc2017_64\bin;$env:PATH"
$env:PATH="$env:OL_PYTHON_DIR\Scripts;$env:PATH"
$env:PATH="$env:OL_PYTHON_DIR;$env:PATH"

if ($env:OL_DEVEL) {
    Write-Verbose -Message "Initialize environment for development"
    cd "$project_root"
}

$VerbosePreference=$OldVerbosePreference
