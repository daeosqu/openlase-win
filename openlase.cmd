@echo off
REM Run OpenLase-Win Terminal

PUSHD %~dp0
SET script_dir=%CD%
POPD

wt.exe --title "OpenLase" -- pwsh.exe -NoExit -Command "&{ . '%script_dir%\scripts\win\openlase_rc.ps1' -Verbose }"
