@echo off
title Lanzador de Proyecto Cimarron UABC
color 0A

echo ======================================================================
echo           INICIANDO ASISTENTE INTERACTIVO CIMARRON UABC
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Iniciando Servidor Backend (FastAPI - http://127.0.0.1:8000)...
start "Cimarron - Backend (FastAPI)" cmd /k "cd /d ""%~dp0backend"" && call venv\Scripts\activate.bat && python main.py"

echo [2/3] Iniciando Servidor Frontend (Vite - http://127.0.0.1:5173)...
start "Cimarron - Frontend (React)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Esperando a que los servidores esten listos...
timeout /t 3 /nobreak >nul

echo [3/3] Abriendo aplicacion en el navegador...
start http://127.0.0.1:5173

echo.
echo ======================================================================
echo  TODO LISTO! Tus servidores estan corriendo en ventanas independientes.
echo  Para detenerlos, simplemente cierra sus respectivas ventanas de consola.
echo ======================================================================
echo.
pause
