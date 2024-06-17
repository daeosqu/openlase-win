@REM -*- coding: utf-8-dos -*-

@echo off

PUSHD %~dp0
SET script_dir=%CD%
POPD

python "%script_dir%\oldownload.py" %*

