export function observarPreparacionQuiz({ apiBaseUrl, grade, subject, onUpdate, onError, fetchImpl = fetch, debounceMs = 250, pollMs = 900, requestTimeoutMs = 8000 }) {
  const controlador = new AbortController();
  let temporizador;
  let temporizadorSolicitud;

  const consultar = async (primeraConsulta) => {
    const solicitud = new AbortController();
    const cancelarSolicitud = () => solicitud.abort();
    controlador.signal.addEventListener('abort', cancelarSolicitud, { once: true });
    let tiempoAgotado = false;
    temporizadorSolicitud = setTimeout(() => { tiempoAgotado = true; solicitud.abort(); }, requestTimeoutMs);
    try {
      const url = primeraConsulta ? `${apiBaseUrl}/quiz/prepare` : `${apiBaseUrl}/quiz/prepare?grade=${grade}&subject=${subject}`;
      const respuesta = await fetchImpl(url, {
        method: primeraConsulta ? 'POST' : 'GET', signal: solicitud.signal,
        ...(primeraConsulta ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ grade, subject }) } : {}),
      });
      if (!respuesta.ok) throw new Error('No pude conectar para preparar el juego.');
      const datos = await respuesta.json();
      if (controlador.signal.aborted) return;
      if (!['ready', 'preparing', 'unavailable'].includes(datos.state)) throw new Error('No pude consultar el estado del juego.');
      onUpdate(datos);
      if (datos.state === 'unavailable') throw new Error('Todavía no pude preparar esta ronda. Puedes reintentar o elegir otra materia.');
      if (datos.state !== 'ready') temporizador = setTimeout(() => consultar(false), pollMs);
    } catch (error) {
      if (!controlador.signal.aborted) onError(tiempoAgotado ? 'La conexión está tardando. Revisa el servidor y reintenta.' : error.message);
    } finally {
      clearTimeout(temporizadorSolicitud);
      controlador.signal.removeEventListener('abort', cancelarSolicitud);
    }
  };

  temporizador = setTimeout(() => consultar(true), debounceMs);
  return () => { controlador.abort(); clearTimeout(temporizador); clearTimeout(temporizadorSolicitud); };
}
