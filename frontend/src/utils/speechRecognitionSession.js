// Una sesión entrega una sola respuesta y descarta transcripciones al cancelarse.
export function createSpeechSession(recognition, { onStart, onText, onAnswer, onFinish, onError }) {
  let active = false;
  let transcript = '';
  let ending = false;
  let pendingStart = false;

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
    if (!active) return;
    active = false;
    transcript = '';
    ending = true;
    onFinish();
    try { recognition.abort(); } catch { ending = false; }
  };

  recognition.onstart = () => { if (active) onStart(); };
  recognition.onresult = (event) => {
    if (!active) return;
    let final = '';
    let interim = '';
    for (const result of Array.from(event.results)) {
      if (result.isFinal) final += result[0].transcript;
      else interim += result[0].transcript;
    }
    transcript = (final || interim).trim();
    onText(transcript);
    if (final.trim()) {
      const answer = final.trim();
      cancel();
      onAnswer(answer);
    }
  };
  recognition.onend = () => {
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
  if (error === 'not-allowed' || error === 'service-not-allowed') return 'Permite el micrófono en el navegador y pulsa Reanudar voz. También puedes responder con los botones.';
  if (error === 'no-speech') return 'No escuché una respuesta. Pulsa Hablar para intentarlo otra vez o Reanudar voz.';
  if (error === 'network') return 'El navegador no pudo reconocer la voz. Revisa su conexión o responde con los botones.';
  if (error === 'unsupported') return 'Este navegador no admite reconocimiento de voz. Puedes responder con los botones o escribiendo.';
  return 'No pude activar el reconocimiento de voz. Pulsa Hablar para reintentar o responde con los botones.';
}
