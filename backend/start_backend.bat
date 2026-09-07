@echo off
echo ========================================================
echo   Iniciando Backend del Asistente Cimarron UABC (FastAPI)
echo ========================================================

cd /d "%~dp0"

if not exist venv (
    echo Creando entorno virtual de Python...
    python -m venv venv
)

echo Activando entorno virtual e instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo Servidor iniciando en http://127.0.0.1:8000 ...
python main.py

pause
