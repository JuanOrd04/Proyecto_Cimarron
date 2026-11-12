// Una sesión entrega una sola respuesta y descarta transcripciones al cancelarse.
// Escucha de forma continua y entrega la respuesta cuando el niño lleva un rato en silencio, para no cortarlo
// cuando hace pausas ("eeh... la... la del sol").
export function createSpeechSession(recognition, { onStart, onText, onAnswer, onFinish, onError },
  { silenceMs = 1800, setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  let active = false;
  let transcript = '';
  let ending = false;
  let pendingStart = false;
  let silenceTimer = null;

  const stopTimer = () => {
    if (silenceTimer !== null) clearTimer(silenceTimer);
    silenceTimer = null;
  };

  const start = () => {
    if (ending) { pendingStart = true; return; }
    if (active) return;
    active = true;
    transcript = '';
    try { recognition.start(); }
    catch {
      active = false;
      transcript = '';
      onFinish();
      onError('start-failed');
    }
  };

  const cancel = () => {
    pendingStart = false;
    stopTimer();
    if (!active) return;
    active = false;
    transcript = '';
    ending = true;
    onFinish();
    try { recognition.abort(); } catch { ending = false; }
  };

  const deliver = () => {
    stopTimer();
    if (!active) return;
    const answer = transcript;
    cancel();
    if (answer) onAnswer(answer);
  };

  recognition.onstart = () => { if (active) onStart(); };
  recognition.onresult = (event) => {
    if (!active) return;
    let final = '';
    let interim = '';
    for (const result of Array.from(event.results)) {
      if (result.isFinal) final += ` ${result[0].transcript}`;
      else interim += ` ${result[0].transcript}`;
    }
    transcript = `${final} ${interim}`.replace(/\s+/g, ' ').trim();
    onText(transcript);
    stopTimer();
    if (transcript) silenceTimer = setTimer(deliver, silenceMs);
  };
  recognition.onend = () => {
    stopTimer();
    if (!active) {
      ending = false;
      if (pendingStart) { pendingStart = false; start(); }
      return;
    }
    const answer = transcript;
    active = false;
    transcript = '';
    onFinish();
    if (answer) onAnswer(answer);
    else onError('no-speech');
  };
  recognition.onerror = (event) => {
    if (!active) return;
    if (event.error === 'no-speech' && transcript) { deliver(); return; }
    cancel();
    onError(event.error);
  };

  return {
    start,
    cancel,
    dispose() {
      cancel();
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
    },
  };
}

export function speechErrorMessage(error) {
  if (error === 'not-allowed' || error === 'service-not-allowed') return 'Necesito permiso para usar el micrófono. Pide ayuda a un adulto o toca una tarjeta.';
  if (error === 'no-speech') return 'No te escuché. Pulsa Hablar y dime tu respuesta, o toca una tarjeta.';
  if (error === 'network') return 'No te pude escuchar bien. Pulsa Hablar otra vez o toca una tarjeta.';
  if (error === 'unsupported') return 'Aquí no te puedo escuchar. Toca una tarjeta o escribe tu respuesta.';
  return 'No te pude escuchar. Pulsa Hablar otra vez o toca una tarjeta.';
}
