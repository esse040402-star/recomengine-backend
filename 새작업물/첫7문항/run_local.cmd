@echo off
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist "quick_survey\data\questions.json" goto missing
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -u "%~dp0run_local.py" %* 2>"%~dp0error.log"
goto result
:python
where python >nul 2>nul
if errorlevel 1 goto no_python
python -u "%~dp0run_local.py" %* 2>"%~dp0error.log"
:result
set "survey_exit=%errorlevel%"
if not "%survey_exit%"=="0" goto failed
if exist "%~dp0error.log" type "%~dp0error.log"
echo.
echo Completed. This window stays open. Type exit to close.
exit /b 0
:failed
echo.
echo Execution failed. Please share the error below or error.log.
type "%~dp0error.log"
echo.
echo This window stays open. Type exit to close.
exit /b %survey_exit%
:missing
echo Extract the ENTIRE ZIP first. The quick_survey folder is missing.
exit /b 1
:no_python
echo Python was not found. Install Python 3.10 or newer.
exit /b 1
