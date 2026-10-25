#!/usr/bin/env bash
set -euo pipefail

CIMARRON_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CIMARRON_ROOT/backend"

if [ ! -x venv/bin/python ]; then
    echo "Falta el entorno backend/venv. Prepara las dependencias antes de iniciar."
    exit 1
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "El puerto 8000 ya está ocupado. Detén el backend anterior con Ctrl+C y vuelve a ejecutar este comando."
    exit 1
fi

if ! curl --fail --silent --max-time 5 http://127.0.0.1:11434/api/tags >/dev/null; then
    echo "Ollama no responde. Abre Ollama o ejecuta 'ollama serve' en otra terminal."
    exit 1
fi

CIMARRON_INTERFACE="$(route -n get default 2>/dev/null | awk '/interface:/ {print $2}' || true)"
CIMARRON_IP=""
if [ -n "$CIMARRON_INTERFACE" ]; then
    CIMARRON_IP="$(ipconfig getifaddr "$CIMARRON_INTERFACE" 2>/dev/null || true)"
fi

echo "Iniciando el backend de la Mac para recibir consultas de la red local."
if [ -n "$CIMARRON_IP" ]; then
    echo "Dirección para el cliente Windows: http://$CIMARRON_IP:8000"
else
    echo "Consulta la IP de la Mac en Ajustes del Sistema > Red. El puerto del servidor será 8000."
fi
echo "Mantén esta terminal abierta. Para detener el servidor, presiona Ctrl+C."
exec venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
