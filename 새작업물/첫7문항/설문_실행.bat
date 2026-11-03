@echo off
setlocal
cd /d "%~dp0"
"%ComSpec%" /d /k call "%~dp0run_local.cmd" %*
exit /b
