from contextlib import contextmanager
import threading
import time


class InferenceQueue:
    def __init__(self):
        self.condicion = threading.Condition()
        self.ocupada = False
        self.esperas_interactivas = 0

    @contextmanager
    def acquire(self, priority, timeout):
        limite = time.monotonic() + timeout
        es_interactiva = priority != 'background'
        with self.condicion:
            self.esperas_interactivas += int(es_interactiva)
            try:
                while self.ocupada or (not es_interactiva and self.esperas_interactivas):
                    tiempo_restante = limite - time.monotonic()
                    if tiempo_restante <= 0:
                        raise TimeoutError('La inferencia sigue ocupada.')
                    self.condicion.wait(tiempo_restante)
                self.ocupada = True
            finally:
                self.esperas_interactivas -= int(es_interactiva)
        try:
            tiempo_restante = limite - time.monotonic()
            if tiempo_restante <= 0:
                raise TimeoutError('Se agotó el tiempo de inferencia.')
            yield tiempo_restante
        finally:
            with self.condicion:
                self.ocupada = False
                self.condicion.notify_all()
