# Usar la Mac como servidor del Cimarrón

Esta configuración permite elegir entre ejecutar todo en la Mac o usar una PC Windows como cliente. La configuración predeterminada continúa siendo local.

## Cómo se distribuye el trabajo

```text
Windows: navegador, React, micrófono y bocinas
    -> Vite local recibe /api/chat
    -> HTTP por el router hacia la Mac:8000/chat
Mac: FastAPI, Chroma, Ollama y Supertonic
    -> devuelve texto y audio
Windows: muestra la respuesta y reproduce el audio
```

Vite funciona como intermediario para que el navegador use `localhost` en Windows. Esto conserva el contexto seguro requerido para capturar el micrófono y evita que el navegador deba acceder directamente a la IP de la Mac. La transcripción sigue usando la implementación del navegador; esta configuración no agrega un motor de STT.

## Modo local: los comandos actuales

Ollama debe estar abierto o ejecutar `ollama serve` en otra terminal.

Backend:

```bash
cd /Users/davesch/Desktop/AIAN/Proyecto_Cimarron/backend
./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Interfaz, en otra terminal:

```bash
cd /Users/davesch/Desktop/AIAN/Proyecto_Cimarron/frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abre [http://127.0.0.1:5173](http://127.0.0.1:5173/). Sin variables adicionales ni un `.env.local` de cliente, la interfaz continúa utilizando `http://127.0.0.1:8000`.

## Modo servidor: Mac

Conecta ambos equipos al mismo router. Mantén Ollama abierto y detén el backend local anterior con `Ctrl+C` para liberar el puerto 8000.

```bash
cd /Users/davesch/Desktop/AIAN/Proyecto_Cimarron
bash iniciar_servidor_mac.sh
```

El script muestra una dirección como `http://192.168.1.50:8000` y atiende en las interfaces de red de la Mac. Mantén su terminal abierta. Ollama sigue siendo consultado localmente por FastAPI; Windows solo necesita acceder al puerto 8000.

Si aparece una solicitud del firewall de macOS, permite conexiones entrantes para el backend en la red del router. No hace falta configurar reenvío de puertos hacia internet. La función de enseñar conocimiento sigue disponible; usa este modo en la red de confianza de la demostración.

## Modo cliente: Windows

Windows necesita Node.js 18 o posterior, npm y una copia de la carpeta `frontend` junto con `iniciar_cliente_windows.bat`, conservando su estructura. Puede usarse una copia completa del proyecto con estos cambios; Windows no necesita instalar el backend, los modelos de Ollama ni Chroma.

La primera instalación de dependencias de la interfaz requiere acceso al registro npm. Prepárala antes de la presentación. `node_modules` de la Mac no se debe copiar a Windows, porque incluye componentes específicos de macOS.

Abre CMD o PowerShell en la raíz de la copia del proyecto y ejecuta, sustituyendo la dirección por la mostrada en la Mac:

```powershell
.\iniciar_cliente_windows.bat http://192.168.1.50:8000
```

El script comprueba `/health`, configura el destino y arranca únicamente la interfaz. Cuando Vite esté listo, abre [http://127.0.0.1:5173](http://127.0.0.1:5173/) en el navegador de Windows.

## Configuración manual opcional

El script del cliente establece variables solo para ese proceso. No modifica archivos `.env` ni la configuración permanente de Windows.

También puedes crear `frontend/.env.local` con:

```dotenv
VITE_API_BASE_URL=/api
CIMARRON_BACKEND_URL=http://192.168.1.50:8000
```

Y ejecutar `npm run dev` dentro de `frontend`. Al modificar variables, reinicia Vite. Para volver al modo local en ese equipo, quita esas variables o cambia ambos valores a `http://127.0.0.1:8000`.

`VITE_API_BASE_URL` controla las rutas usadas por React tanto para conversar como para enseñar. `CIMARRON_BACKEND_URL` controla el destino del intermediario Vite y no se expone como variable de React. `npm run build` también admite `VITE_API_BASE_URL`; si se compila con `/api`, el servidor que publique esa compilación deberá ofrecer esas rutas.

## Comprobación de conexión

Una vez iniciado el servidor, abre `http://IP_DE_LA_MAC:8000/health` desde Windows. Si no responde, comprueba la IP, el firewall y que el router no tenga aislamiento de clientes o una red de invitados separada.

Después inicia el cliente y envía una pregunta. La terminal del backend de la Mac mostrará la solicitud; Windows mostrará el texto y reproducirá el audio.

## Versión y recuperación

Estos cambios se prepararon en la rama `feature/conexion-mac-windows`, partiendo de `90a1724`. El respaldo previo con código, Chroma y caché está en `/Users/davesch/Desktop/AIAN/Respaldos/Cimarron_2026-10-13_90a1724`.
