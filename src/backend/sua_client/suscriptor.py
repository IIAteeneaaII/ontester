from src.backend.sua_client.settings import TOPIC_UPDATES_ALL, TOPIC_UPDATES_STATION
import json

def _on_message(self, client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        print(f"[MQTT] Mensaje inválido en {msg.topic}")
        return

    # Solo procesa updates
    if msg.topic in (
        TOPIC_UPDATES_ALL,
        TOPIC_UPDATES_STATION.format(station_id=self.station_id),
    ):
        print(f"[MQTT] Update recibido: {payload}")

        if payload.get("type") == "update_available":
            version = payload.get("version")
            installer_key = payload.get("installer_key")
            if not version or not installer_key:
                print("[UPDATE] Payload incompleto (version/installer_key)")
                return

            # Aquí NO descargas directo del key:
            # le pides al SUA la presigned URL con tu station_token
            from .actualizador import download_update_installer, kill_processes_by_name, launch_inno_setup
            descarga, path = download_update_installer(version=version)

            if descarga:
                # TODO Avisar que hay descarga disponible
                # Matar los procesos del tester
                kill_processes_by_name({"ChromeDriver.exe", "Google Chrome for Testing.exe", "chrome.exe", "chromedriver.exe"})
                # Lanzar el instalador
                launch_inno_setup(path)


def _subscribe_updates(self):
    # estación (unicast)
    t1 = TOPIC_UPDATES_STATION.format(station_id=self.station_id)
    self.client.subscribe(t1, qos=1)

    # opcional: broadcast
    self.client.subscribe(TOPIC_UPDATES_ALL, qos=1)

    print(f"[MQTT] Suscrito a updates: {t1} y {TOPIC_UPDATES_ALL}")