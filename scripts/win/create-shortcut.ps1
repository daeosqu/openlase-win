# Register batch file to start menu
# Usage: create-shortcut.ps1 LNK_PATH BATCHFILE ICON_PATH WORK_DIR

#Set-PSDebug -Trace 1

$batch_file = $Args[1] -replace '[/]', '\'
$icon_location = $Args[2] -replace '[/]', '\'
$working_directory = $Args[3] -replace '[/]', '\'

$objShell = New-Object -ComObject ("WScript.Shell")
$objShortCut = $objShell.CreateShortcut($Args[0])
$objShortCut.TargetPath = "cmd.exe"
$objShortCut.Arguments = "/c ""$batch_file"""
$objShortCut.IconLocation = $icon_location
$objShortCut.WorkingDirectory = $working_directory
$objShortCut.Save()

if ($?) {
    exit 0
} else {
    exit 1
}
