@echo off
REM Buffer Fin Resize - Windows one-click dependency installer.
REM
REM Usage:
REM     scripts\install.bat              -- check + install required deps
REM     scripts\install.bat --check      -- report only, no install
REM     scripts\install.bat --all        -- install required + optional
REM
REM Forces UTF-8 mode for Python so YAML / JSON I/O works regardless of
REM the host's ANSI code page (avoids "UnicodeDecodeError: gbk codec
REM can't decode" on zh-CN Windows).

setlocal
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM Find Python: try 'py' launcher first, then 'python', then 'python3'.
set PY_CMD=
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PY_CMD=python"
    ) else (
        where python3 >nul 2>nul
        if %ERRORLEVEL%==0 (
            set "PY_CMD=python3"
        )
    )
)
if "%PY_CMD%"=="" (
    echo [ERROR] No Python interpreter found on PATH.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         and re-run this script.
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "CHECKER=%SCRIPT_DIR%check_deps.py"

if "%~1"=="--check" (
    %PY_CMD% "%CHECKER%"
    exit /b %ERRORLEVEL%
)
if "%~1"=="--all" (
    %PY_CMD% "%CHECKER%" --with-optional
    exit /b %ERRORLEVEL%
)

REM Default: install required, report optional.
%PY_CMD% "%CHECKER%" --install
exit /b %ERRORLEVEL%
