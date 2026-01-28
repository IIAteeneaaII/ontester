import queue
import threading
import time

from src.backend.sua_client import publisher

class AwsBridge:
    def __init__(self, max_q=20000):
        self.q = queue.Queue(maxsize=max_q)
        self._stop = threading.Event()
        self._t = None
        self._start_lock = threading.Lock()

    def start(self):
        # idempotente: si ya está vivo, no crea otro thread
        with self._start_lock:
            if self._t and self._t.is_alive():
                return
            self._stop.clear()
            self._t = threading.Thread(target=self._loop, daemon=True)
            self._t.start()

    def stop(self, join_timeout=2.0):
        self._stop.set()
        t = self._t
        if t:
            t.join(timeout=join_timeout)
        # Cierra la conexión MQTT una vez al salir de la app
        try:
            publisher.disconnect()
        except Exception:
            pass

    def enqueue(self, kind, payload, ctx=None):
        evt = {"kind": kind, "payload": payload, "ctx": ctx or {}, "ts": time.time()}
        
        try:
            self.q.put_nowait(evt)  # nunca bloquea UI
            print("[AWS-ENQUEUE]", kind)
        except queue.Full:
            # política: drop o spool (por ahora drop)
            pass

    def _loop(self):
        while not self._stop.is_set():
            try:
                evt = self.q.get(timeout=0.3)
            except queue.Empty:
                continue

            kind = evt["kind"]
            payload = evt["payload"]
            
            try:
                # Mapea tus kinds a publish
                if kind == "resultados":
                    # payload ideal: {"test_type": "...", "data": {...}}
                    if isinstance(payload, dict) and "test_type" in payload and "data" in payload:
                        # formato viejo
                        ok = publisher.publish_test_result(payload["test_type"], payload["data"])
                    else:
                        # formato nuevo (tu JSON plano completo)
                        ok = publisher.publish_event("resultados", payload)
                elif kind == "resultados2":
                        ok = publisher.publish_test_result(payload["test_type"], payload["data"])
                else:
                     ok = publisher.publish_event(kind, payload)

                if ok:
                    print("[AWS-PUBLISH]", kind)
            except Exception:
                # Si algo falla (red), desconecta y espera un poco.
                # La siguiente iteración reconecta vía get_client()
                try:
                    publisher.disconnect()
                except Exception:
                    pass
                time.sleep(0.8)
