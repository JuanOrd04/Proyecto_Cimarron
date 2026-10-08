#!/usr/bin/env bash

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  Iniciando Backend del Asistente Cimarrón UABC (FastAPI)"
echo "========================================================"

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual de Python..."
    python3 -m venv venv
    echo "Instalando dependencias..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

echo "Activando entorno virtual..."
source venv/bin/activate

echo "Servidor iniciando en http://127.0.0.1:8000 ..."
python main.py
