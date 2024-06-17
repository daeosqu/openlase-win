@echo off

setlocal

PUSHD %~dp0
SET script_dir=%CD%
POPD

SET "LOGFILE=%TMP%\openlase-register-startmenu.log"
REM SET "LOGFILE=NUL"

powershell.exe -NoProfile -NonInteractive -InputFormat None -ExecutionPolicy Bypass -File "%script_dir%\register-startmenu.ps1" %* > %LOGFILE% 2>&1

set "exit_code=%errorlevel%"

type %LOGFILE%

if %exit_code% equ 0 (
    echo OK
) else (
    echo register-startmenu.ps1 exited by nonzero: exit_code=%exit_code%
)

exit %exit_code%
