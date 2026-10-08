#!/usr/bin/env bash

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cargar NVM si está instalado en el usuario
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
    source "$NVM_DIR/nvm.sh"
elif [ -d "$HOME/.nvm/versions/node" ]; then
    LATEST_NODE=$(find "$HOME/.nvm/versions/node" -maxdepth 2 -name bin | tail -n 1)
    if [ -n "$LATEST_NODE" ]; then
        export PATH="$LATEST_NODE:$PATH"
    fi
fi

if [ ! -d "node_modules" ]; then
    echo "Instalando dependencias de Node.js..."
    npm install
fi

echo "Servidor frontend iniciando en http://127.0.0.1:5173 ..."
npm run dev -- --host 127.0.0.1
