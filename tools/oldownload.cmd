@REM -*- coding: utf-8-dos -*-

@REM Development only

@echo off

PUSHD %~dp0
SET script_dir=%CD%
POPD

python "%script_dir%\..\python\pylase\oldownload.py" %*

