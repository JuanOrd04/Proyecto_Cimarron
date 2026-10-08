#!/usr/bin/env bash

# Directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "          INICIANDO ASISTENTE INTERACTIVO CIMARRÓN UABC"
echo "======================================================================"
echo ""

# Función para detener ambos procesos limpiamente al presionar Ctrl+C o cerrar
cleanup() {
    echo ""
    echo "======================================================================"
    echo "  Deteniendo servidores..."
    echo "======================================================================"
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    wait 2>/dev/null
    echo "  ¡Servidores detenidos correctamente!"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# [1/3] Backend
echo "[1/3] Iniciando Servidor Backend (FastAPI - http://127.0.0.1:8000)..."
"$PROJECT_ROOT/backend/start_backend.sh" &
BACKEND_PID=$!

# [2/3] Frontend
echo "[2/3] Iniciando Servidor Frontend (Vite - http://127.0.0.1:5173)..."
"$PROJECT_ROOT/frontend/start_frontend.sh" &
FRONTEND_PID=$!

# Esperar unos segundos a que los servidores levanten
sleep 3

# [3/3] Abrir navegador si xdg-open está disponible
echo "[3/3] Abriendo aplicación en el navegador..."
if command -v xdg-open > /dev/null; then
    xdg-open "http://127.0.0.1:5173" > /dev/null 2>&1 &
fi

echo ""
echo "======================================================================"
echo "  TODO LISTO! Backend y Frontend están corriendo."
echo "  Presiona Ctrl+C en esta terminal para detener ambos servicios."
echo "======================================================================"
echo ""

# Esperar a los procesos en segundo plano
wait
