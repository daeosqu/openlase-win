# Register batch file to start menu
# Usage: create-shortcut.ps1 LNK_NAME BAT_PATH ICON_PATH WORK_DIR
$objShell = New-Object -ComObject ("WScript.Shell")
$objShortCut = $objShell.CreateShortcut($env:APPDATA + "\Microsoft\Windows\Start Menu\Programs\" + $Args[0])
$objShortCut.TargetPath = "cmd.exe"
$objShortCut.Arguments = "/c $($Args[1])"
$objShortCut.IconLocation = $Args[2]
$objShortCut.WorkingDirectory = $Args[3]
$objShortCut.Save()
