<#
OpenLase Utility.
#>

# Enable Visual Studio Development Environment
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

Export-ModuleMember -Function `
  Enable-VsDevEnv
