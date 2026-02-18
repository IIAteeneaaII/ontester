# Esto se usará para unicamente mostrar conectado  desconectado
import time
from src.backend.ont_automatico import _ping_once  

COMMON_IPS = ["192.168.100.1", "192.168.1.1"]

def iniciar_monitoreo(out_q=None, stop_event=None):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    emit("log", "[MON] Iniciando monitoreo...")
    last_state = None
    current_ip = None

    while True:
        if stop_event and stop_event.is_set():
            emit("log", "[MON] Monitoreo cancelado por cambio de modo")
            return

        # 1) detectar si hay equipo (ping a IPs)
        found_ip = None
        for ip in COMMON_IPS:
            if _ping_once(ip, timeout_ms=500):
                found_ip = ip
                break

        # 2) estado
        connected = found_ip is not None

        # 3) emitir solo si cambia el estado (anti-spam)
        if connected and (last_state != "connected" or current_ip != found_ip):
            current_ip = found_ip
            last_state = "connected"
            emit("con", "Dispositivo Conectado")
            # Marcar PING como PASS automáticamente al detectar conexión
            emit("test_individual", {"name": "ping", "status": "PASS"})
            emit("log", f"[MON] Conectado: {current_ip}")

        if (not connected) and last_state != "disconnected":
            current_ip = None
            last_state = "disconnected"
            emit("con", "DESCONECTADO")
            emit("log", "[MON] Desconectado")

        time.sleep(0.5)