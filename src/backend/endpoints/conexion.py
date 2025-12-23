from pathlib import Path
import threading
import time

def load_users_txt(path: str | Path) -> dict[str, str]:
    users = {}
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            users[k.strip()] = v.strip()
    return users

def load_default_users() -> dict[str, str]:
    base_utils = Path(__file__).resolve().parents[1]   # -> backend
    txt_path = base_utils / "utils" / "empleados.txt"
    return load_users_txt(txt_path)

def iniciar_testerConexion(resetFabrica, usb, fibra, wifi, out_q = None, stop_event = None):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    # Mostrar cambio de modo detectado primero
    emit("log", "Cambio de modo detectado.")
    time.sleep(1) # Pequeña pausa para que sea perceptible

    print("[CONEXION] Fibra recibida: "+str(fibra))
    if any([resetFabrica, usb, fibra, wifi]):
        sftU = True
    else:
        sftU = False
    opcionesTest = {
        "info": {
            "sn": True,
            "mac": True,
            "ssid_24ghz": True,
            "ssid_5ghz": True,
            "software_version": True,
            "wifi_password": True,
            "model": True
        },
        "tests": {
            "ping": True, # Esta prueba no se deshabilita
            "factory_reset": resetFabrica,
            "software_update": sftU, # Esta prueba no se deshabilita, validar si almenos una prueba está encendida
            "usb_port": usb,
            "tx_power": fibra,
            "rx_power": fibra,
            "wifi_24ghz_signal": wifi,
            "wifi_5ghz_signal": wifi
        }
    }
    
    emit("log", "Iniciando pruebas...")
    # print("CONEXION: wifi: "+str(wifi))
    # Mandar a llamar a la función en ont_automatico
    from src.backend.ont_automatico import main_loop
    main_loop(opcionesTest, out_q, stop_event) 
    # Se hará desde dentro del main_loop
    # from src.backend.mixins.common_mixin import _resultados_finales
    # resultados = _resultados_finales()  # función de resultados finales
    # emit("resultados", resultados)

    # Solo emitir "Pruebas terminadas" si no fue cancelado
    if not(stop_event and stop_event.is_set()):
        emit("log", "Cambio de modo detectado.")

def iniciar_pruebaUnitariaConexion(resetFabrica, sftU, usb, fibra, wifi, model, out_q=None):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))
    
    opcionesTest = {
        "info": {
            "sn": True,
            "mac": True,
            "ssid_24ghz": True,
            "ssid_5ghz": True,
            "software_version": True,
            "wifi_password": True,
            "model": True
        },
        "tests": {
            "ping": True, # Esta prueba no se deshabilita
            "factory_reset": resetFabrica,
            "software_update": sftU, 
            "usb_port": usb,
            "tx_power": fibra,
            "rx_power": fibra,
            "wifi_24ghz_signal": wifi,
            "wifi_5ghz_signal": wifi
        }
    }
    # Poner log 
    emit("log", "Iniciando prueba unitaria...")
    model = model.removeprefix("Modelo: ") # Limpiar el modelo (viene como "Modelo: ___")
    # Mandar a llamar una prueba unitaria
    from src.backend.ont_automatico import pruebaUnitariaONT
    pruebaUnitariaONT(opcionesTest, out_q, model)
    # Actualizar botón unitario