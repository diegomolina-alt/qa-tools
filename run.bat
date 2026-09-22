@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" >nul 2>&1
if errorlevel 1 (
    echo No se pudo acceder a la carpeta de QA Tools.
    pause
    exit /b 1
)

set "PYTHON="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys, tkinter as tk; raise SystemExit(0 if sys.version_info >= (3, 11) and tk.TkVersion >= 8.6 else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON=py -3"
)
if defined PYTHON goto :run

for %%P in (python python3) do (
    if not defined PYTHON (
        %%P -c "import sys, tkinter as tk; raise SystemExit(0 if sys.version_info >= (3, 11) and tk.TkVersion >= 8.6 else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON=%%P"
    )
)

if not defined PYTHON (
    echo.
    echo No se encontro Python 3.11 o superior con soporte Tkinter.
    echo.
    echo Instala Python desde:
    echo https://www.python.org/downloads/windows/
    echo.
    echo Durante la instalacion habilita Python Launcher y Add Python to PATH cuando corresponda.
    echo Despues vuelve a ejecutar: run.bat
    echo.
    pause
    popd
    exit /b 1
)

:run
%PYTHON% "%PROJECT_DIR%bootstrap.py"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo QA Tools no pudo iniciarse. Revisa el mensaje anterior.
    pause
)
popd
exit /b %EXIT_CODE%
