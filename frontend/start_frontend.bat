@echo off
echo ========================================================
echo   Iniciando Frontend del Asistente Cimarron UABC (Vite)
echo ========================================================

cd /d "%~dp0"

if not exist node_modules (
    echo Instalando dependencias de Node.js...
    cmd /c "npm install"
)

echo Servidor frontend iniciando en http://127.0.0.1:5173 ...
cmd /c "npm run dev -- --host 127.0.0.1"

pause
