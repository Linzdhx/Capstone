@echo off
setlocal
title CVW Inventory Monitor - YOLOv8 Live System
chcp 65001 >nul

:: Determinar directorio del script
set "SCRIPT_DIR=%~dp0"

:: Si estamos en la raiz del repositorio, ingresar a Capstone
if exist "%SCRIPT_DIR%Capstone\run.py" (
    cd /d "%SCRIPT_DIR%Capstone"
) else if exist "%SCRIPT_DIR%run.py" (
    cd /d "%SCRIPT_DIR%"
) else (
    echo [ERROR] No se encontro run.py ni el directorio Capstone.
    echo Ubicacion actual: %CD%
    pause
    exit /b 1
)

:: Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Verificar instalacion de Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta en el PATH del sistema.
    echo Instala Python o agregalo a las variables de entorno.
    pause
    exit /b 1
)

echo ============================================================
echo   Iniciando CVW Inventory Monitor...
echo   La aplicacion se abrira automaticamente en el navegador.
echo   URL: http://localhost:8000
echo ============================================================
echo.

:: Abrir navegador tras 2 segundos de espera
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Lanzar servidor backend
python run.py

if errorlevel 1 (
    echo.
    echo [AVISO] El proceso se cerro con codigo de error %errorlevel%.
    pause
)
