# ping_service.py
import time
import threading
from src.backend.ont_automatico import _ping_once

class DisconnectMonitor:
    def __init__(self, ip_buscada, out_q=None, stop_event=None):
        self.ip_buscada = ip_buscada
        self.out_q = out_q
        self.stop_event = stop_event

        self.last_state = None
        self.current_ip = None
        self.consecutivosPass = 0
        self.consecutivosFail = 0

        self.expected_disconnect = False
        self.abort_main_run = threading.Event()

    def emit(self, kind, payload):
        if self.out_q:
            self.out_q.put((kind, payload))

    def recibir_eventos_desconexion(self, kind, payload):
        if kind != "prueba_monitor":
            return

        print(f"[MONITOREO_NEW] Recepción exitosa del paquete: {payload}")

        accion = payload.get("accion")

        if accion == "expected_disconnect_on":
            self.expected_disconnect = True

        elif accion == "expected_disconnect_off":
            self.expected_disconnect = False

    def loop(self):
        print(f"[MONITOREO_NEW] Llegando a monitoreo con ip {self.ip_buscada}")

        while True:
            if self.stop_event and self.stop_event.is_set():
                return

            found_ip = None
            if _ping_once(self.ip_buscada, timeout_ms=500):
                found_ip = self.ip_buscada

            connected = found_ip is not None

            if connected and (self.last_state != "connected" or self.current_ip != found_ip):
                self.consecutivosPass += 1
                if self.consecutivosFail != 0:
                    self.consecutivosFail = 0

                if self.consecutivosPass > 2:
                    self.current_ip = found_ip
                    self.last_state = "connected"
                    self.consecutivosPass = 0
                    print(f"[MONITOREO_NEW] Dispositivo encontrado: {self.current_ip}")
                    # emitir a UI
                    self.emit("con", "CONECTADO")

            if (not connected) and self.last_state != "disconnected":
                # Aumentar el numero de errores consecutivos
                self.consecutivosFail += 1
                # Si hay errores entonces limpiar los buenos
                if self.consecutivosPass != 0:
                    self.consecutivosPass = 0

                # Si da 3 errores consecutivos entonces es desconexion
                if self.consecutivosFail > 2:
                    self.current_ip = None
                    self.last_state = "disconnected"
                    self.consecutivosFail = 0

                    print("[MONITOREO_NEW] Dispositivo desconectado")

                    if not self.expected_disconnect:
                        print("[MONITOREO_NEW] Desconexión inesperada detectada")
                        self.abort_main_run.set()
                        self.emit("log", "Desconexión inesperada detectada por monitor")
                        # 1) para limpiar la UI:
                        self.emit("con", "DESCONECTADO")

                        # 2) marcar aborto lógico
                        self.abort_main_run.set()

                        # 3) cortar ejecución principal
                        if self.stop_event:
                            self.stop_event.set()

                        # emit para la UI y mostrar mensaje de error
                        self.emit("error_ont", "desconexion")
                    else:
                        print("[MONITOREO_NEW] Desconexión esperada, no se aborta")
                        # Mandar nuevo emit de desconexion pero sin limpiar lo demas
                        self.emit("con", "DESCONECTADO2")

            time.sleep(0.5)


def control_monitoreo(ip_buscada, dispatcher=None, out_q=None, stop_event=None):
    monitor = DisconnectMonitor(
        ip_buscada=ip_buscada,
        out_q=out_q,
        stop_event=stop_event,
    )

    if dispatcher is not None:
        dispatcher.set_monitor(monitor)

    t = threading.Thread(target=monitor.loop, daemon=True)
    t.start()
    return monitor, t