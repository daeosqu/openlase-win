@REM Run OpenLase terminal

@echo off

PUSHD %~dp0
SET script_dir=%CD%
POPD

REM check if pwsh exists
where pwsh > nul 2>&1
if %errorlevel% equ 0 (
    set "pwsh=pwsh"
) else (
    set "pwsh=powershell"
)

REM Start OpenLase terminal
wt.exe -- %pwsh% -NoExit -Command "cd %CD% \; . '%script_dir%\scripts\win\openlase_rc.ps1' %*"

GOTO END

:ERROR

exit /b 1

:END

