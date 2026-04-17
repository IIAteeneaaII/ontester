# Archivo pensado para servir como monitoreo a una IP especifica en el backend
import time
import threading
from src.backend.ont_automatico import _ping_once  

def control_monitoreo(ip_buscada, out_q=None, stop_event=None):
    # arrancar desde hilo, no normal para no evitar la ejecución
    def worker():
        iniciar_monitoreo(ip_buscada, out_q)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t # regresar el hilo 

def iniciar_monitoreo(ip_buscada, out_q=None, stop_event=None):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    # emit("log", "[MON] Iniciando monitoreo...")
    print(f"[MONITOREO_NEW] Llegando a monitoreo con ip {ip_buscada}")
    last_state = None
    current_ip = None

    while True:
        if stop_event and stop_event.is_set():
            # emit("log", "[MON] Monitoreo cancelado por cambio de modo")
            return

        # 1) detectar si hay equipo (ping a IPs)
        found_ip = None
        if _ping_once(ip_buscada, timeout_ms=500):
            found_ip = ip_buscada

        # 2) estado
        connected = found_ip is not None

        # 3) emitir solo si cambia el estado (anti-spam)
        if connected and (last_state != "connected" or current_ip != found_ip):
            current_ip = found_ip
            last_state = "connected"
            print(f"[MONITOREO_NEW] Dispositivo encontrado: {current_ip}")
            #emit("con", "Dispositivo Conectado")
            # Marcar PING como PASS automáticamente al detectar conexión
            #emit("individual_show", {"name": "ping", "status": "PASS"})
            #emit("log", f"[MON] Conectado: {current_ip}")

        if (not connected) and last_state != "disconnected":
            current_ip = None
            last_state = "disconnected"
            #emit("con", "DESCONECTADO")
            #emit("log", "[MON] Desconectado")
            print("[MONITOREO_NEW] Dispositivo desconectado")

        time.sleep(0.5)