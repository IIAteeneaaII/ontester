from pathlib import Path
import threading
import time
from datetime import date
import json
from src.backend.ont_automatico import main_loop

_UNIT_RUNNING = threading.Event()
_UNIT_LOCK = threading.Lock()

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
    # base_utils = Path(__file__).resolve().parents[1]   # -> backend
    txt_path = Path(r"C:/ONT/empleados.txt") 
    return load_users_txt(txt_path)

def cargarConfig() -> dict:
    """Devuelve el diccionario de configuración, o {} si no existe / falla."""
    config_path = Path("C:/ONT/config.json")
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[CONFIG] Error leyendo config: {e}")
        return {}

def guardarConfig(configRecibida, tipo):
    # config es el diccionario de info recibida, tipo es de que grupo pertenece
    config_path = Path("C:/ONT/config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "wifi": {},   # wifi
            "fibra": {},   # fibra 
            "general": {}    # estación, etiqueta, etc.
        }

    if(tipo == "valores"):
          #configuracion de fibra y wifi
        seccion = config.setdefault("wifi", {})
        wifi = {
            "rssi24_min": configRecibida.get("rssi24_min"),
            "rssi5_min": configRecibida.get("rssi50_min"),
            "rssi24_max": configRecibida.get("rssi24_max"),
            "rssi5_max": configRecibida.get("rssi50_max"),
            "min24percent": configRecibida.get("busquedas"),
            "min5percent": configRecibida.get("busquedas")
        }
        seccion.update(wifi)
        seccion = config.setdefault("fibra", {})
        fibra = {
            "mintx": configRecibida.get("tx_min"),
            "maxtx": configRecibida.get("tx_max"),
            "minrx": configRecibida.get("rx_min"),
            "maxrx": configRecibida.get("rx_max")
        }
        seccion.update(fibra)
    else:
        # configuración de estación y modo etiqueta
        seccion = config.setdefault("general", {})
        seccion.update(configRecibida)
        pass
        
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_daily_report_path() -> Path:
        """
        Devuelve la ruta del CSV del día.
        Ejemplo: C:\\ONT\\Reportes diarios\\reportes_YYYY-MM-DD.csv
        """
        base_dir = Path(r"C:\ONT") 
        reports_dir = base_dir / "Reportes diarios"
        reports_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()
        filename = f"reportes_{today}.csv"
        return reports_dir / filename

def _get_report_path_for(d: date) -> Path:
        """
        Devuelve la ruta del CSV para la fecha d.
        Ejem: C:\\ONT\\Reportes diarios\\reportes_YYYY-MM-DD.csv
        """
        base_dir = Path(r"C:\ONT")
        reports_dir = base_dir / "Reportes diarios"
        reports_dir.mkdir(parents=True, exist_ok=True)

        filename = f"reportes_{d.isoformat()}.csv"
        return reports_dir / filename

def iniciar_testerConexion(resetFabrica, usb, fibra, wifi, out_q = None, stop_event = None, auto_test_on_detect = True):
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
    # Mandar a llamar al main loop de ont_automatico
    main_loop(opcionesTest, out_q, stop_event, auto_test_on_detect=auto_test_on_detect)
    # Se hará desde dentro del main_loop
    # from src.backend.mixins.common_mixin import _resultados_finales
    # resultados = _resultados_finales()  # función de resultados finales
    # emit("resultados", resultados)

    # Solo emitir "Pruebas terminadas" si no fue cancelado
    if not (stop_event and stop_event.is_set()):
        emit("log", "Pruebas terminadas.")

def iniciar_pruebaUnitariaConexion(resetFabrica, sftU, usb, fibra, wifi, model, out_q=None, stop_event=None):
    # 1) Definir emisor ANTES de usarlo
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    # 2) Check + set del flag SOLO dentro del lock (y salir del lock rápido)        
    with _UNIT_LOCK:
        if _UNIT_RUNNING.is_set():
            emit("log", "Ya hay una prueba unitaria en ejecución. Ignorando este click.")
            return
        _UNIT_RUNNING.set()
    
    # Determinar qué prueba unitaria se está ejecutando para mostrar mensaje claro
    prueba_nombre = "Prueba unitaria"
    if resetFabrica:
        prueba_nombre = "Factory Reset"
    elif sftU:
        prueba_nombre = "Software Update"
    elif usb:
        prueba_nombre = "USB Port"
    elif fibra:
        prueba_nombre = "TX/RX Power (Fibra)"
    elif wifi:
        prueba_nombre = "WiFi 2.4/5 GHz"
    
    try:
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
        
        # Emitir al panel inferior inmediatamente al iniciar
        emit("pruebas", f"Iniciando: {prueba_nombre}...")
        emit("log", f"Iniciando prueba unitaria: {prueba_nombre}")

        # Mandar a llamar una prueba unitaria
        from src.backend.ont_automatico import pruebaUnitariaONT
        pruebaUnitariaONT(opcionesTest=opcionesTest, out_q=out_q, modelo=model, stop_event=stop_event)
        
        # Emitir finalización (solo si no fue cancelado)
        if not (stop_event and stop_event.is_set()):
            emit("pruebas", f"Completado: {prueba_nombre}")
            emit("log", f"Prueba unitaria completada: {prueba_nombre}")
        else:
            emit("pruebas", f"Cancelado: {prueba_nombre}")
            emit("log", f"Prueba unitaria cancelada: {prueba_nombre}")

    finally:
        # 3) SIEMPRE liberar la bandera aunque falle/cancele
        with _UNIT_LOCK:
            _UNIT_RUNNING.clear()
    
    # Solo emitir "Prueba unitaria terminada" si no fue cancelado
    if not (stop_event and stop_event.is_set()):
        emit("log", "Prueba unitaria terminada.")
    
