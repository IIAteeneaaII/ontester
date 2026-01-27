import queue

class EventDispatcher:
    def __init__(self, root, event_q, aws_bridge=None, interval_ms=20, max_per_tick=200):
        self.root = root
        self.event_q = event_q
        self.aws_bridge = aws_bridge
        self.interval_ms = interval_ms
        self.max_per_tick = max_per_tick

        self._polling = False
        self._target = None  # 1 vista activa (tu caso)

    def set_target(self, view):
        self._target = view

    def start(self):
        if self._polling:
            return
        self._polling = True
        self._poll()

    def stop(self):
        self._polling = False

    def _poll(self):
        if not self._polling:
            return

        processed = 0
        try:
            while processed < self.max_per_tick:
                kind, payload = self.event_q.get_nowait()
                processed += 1

                # 1) UI: entregar a la vista activa
                if self._target and hasattr(self._target, "on_event"):
                    self._target.on_event(kind, payload)

                # 2) AWS: solo encolar (NO publicar aquí)
                if self.aws_bridge and kind in {"con", "resultados", "logSuper", "pruebas"}:
                    self.aws_bridge.start()
                    self.aws_bridge.enqueue(kind, payload, ctx={
                        "pc_id": getattr(self.root, "pc_id", "UNKNOWN"),
                    })

        except queue.Empty:
            pass

        self.root.after(self.interval_ms, self._poll)