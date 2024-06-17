@REM Run OpenLase terminal

@echo off

PUSHD %~dp0
SET script_dir=%CD%
POPD

IF EXIST "%script_dir%\.git" IF EXIST "%script_dir%\CMakeLists.txt" SET OL_DEVEL=1

IF "%OL_DEVEL%"=="" GOTO RUN_OPENLASE_TERMINAL

REM Set source directory

PUSHD %~dp0
SET script_dir=%CD%
POPD

REM Check VCINSTALLDIR

IF "%VCToolsVersion%"=="" (
  IF "%VCINSTALLDIR%"=="" (
    IF EXIST "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
      SET "VCINSTALLDIR=C:\Program Files\Microsoft Visual Studio\2022\Community\VC"
      SETLOCAL EnableDelayedExpansion
      ECHO VCINSTALLDIR is not set. default is !VCINSTALLDIR!
      ENDLOCAL
    )
  )
)

IF "%VCToolsVersion%"=="" IF EXIST "%VCINSTALLDIR%\Auxiliary\Build\vcvars64.bat" (
  CALL "%VCINSTALLDIR%\Auxiliary\Build\vcvars64.bat"
) ELSE (
  ECHO ERROR: %VCVARS_BAT% does not exists. Please set VCINSTALLDIR.
  GOTO ERROR
)

:RUN_OPENLASE_TERMINAL

REM check if pwsh exists
where pwsh > nul 2>&1
if %errorlevel% equ 0 (
    set "pwsh=pwsh"
) else (
    set "pwsh=powershell"
)

SET "title=OpenLase"

SET "version_file=%script_dir%\VERSION"
IF NOT EXIST "%version_file%" Set "version_file=%script_dir%\..\..\VERSION"

set "version="
FOR /F %%i IN (%version_file%) DO SET version=%%i

IF NOT "%version%"=="" SET "title=%title% %version%"
If NOT "%OL_DEVEL%"=="" SET "title=%title% [DEV]"

wt.exe --title "%title%" -- %pwsh% -NoExit -Command "&{ . '%script_dir%\scripts\win\openlase_rc.ps1' %* }"

GOTO END

:ERROR

exit /b 1

:END
