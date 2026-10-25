@echo off
setlocal

if "%~1"=="" (
    echo Uso: scripts\iniciar_cliente_windows.bat http://IP_DE_LA_MAC:8000
    echo Ejemplo: scripts\iniciar_cliente_windows.bat http://192.168.1.50:8000
    exit /b 1
)

set "CIMARRON_BACKEND_URL=%~1"
set "VITE_API_BASE_URL=/api"
cd /d "%~dp0..\frontend"

where node >nul 2>&1
if errorlevel 1 (
    echo Falta Node.js. Instala Node.js 18 o posterior antes de iniciar el cliente.
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo npm no esta disponible. Comprueba la instalacion de Node.js.
    exit /b 1
)

echo Comprobando el servidor de la Mac...
node -e "const url = new URL('/health', process.env.CIMARRON_BACKEND_URL); if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Usa una direccion HTTP o HTTPS'); fetch(url, {signal: AbortSignal.timeout(5000)}).then(async r => {if (!r.ok) throw new Error('HTTP ' + r.status); const h = await r.json(); if (h.ollama_status !== 'conectado') throw new Error('Ollama no esta conectado en la Mac'); console.log('Servidor conectado:', process.env.CIMARRON_BACKEND_URL);}).catch(e => {console.error('No se pudo conectar:', e.message); process.exitCode = 1;});"
if errorlevel 1 (
    echo Comprueba la IP, que ambos equipos esten en el mismo router y que el backend de la Mac este iniciado en modo servidor.
    exit /b 1
)

if not exist node_modules (
    echo Instalando dependencias de la interfaz...
    call npm ci --no-audit --no-fund
    if errorlevel 1 exit /b 1
)

echo Abre http://127.0.0.1:5173 en el navegador de Windows cuando Vite indique que esta listo.
echo El cliente usa la Mac para generar las respuestas y la voz.
call npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
exit /b %errorlevel%
