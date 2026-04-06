import paho.mqtt.client as mqtt
import ssl
import json
import time
import threading
from datetime import datetime
from .settings import *
import uuid
from .sua_acceso import ensure_certs_from_sua, get_url_certificados


TOPIC_UPDATES_ALL = "ontester/updates/all"
TOPIC_UPDATES_STATION = "ontester/updates/{station_id}"
TOPIC_UPDATES_ACK = "ontester/updates/ack/{station_id}"

class IoTClient:
    def __init__(self, station_id=None, event_q = None):
        self.station_id = station_id or STATION_ID
        self.client = None
        self.connected = False
        self.heartbeat_timer = None
        self.update_lock = threading.Lock()
        self.event_q = event_q

    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se establece conexión con AWS IoT"""
        print(f"[MQTT] on_connect rc={rc} flags={flags}")
        if rc == 0:
            self.connected = True
            print("[MQTT]  Conexión establecida con AWS IoT")
        else:
            print(f"[MQTT]  Conexión rechazada rc={rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback cuando se pierde la conexión"""
        print(f"[MQTT] DESCONECTADO rc={rc}")
        if rc == 0:
            print("[MQTT] Desconexión limpia")
        else:
            print(f"[MQTT]  Desconexión inesperada - AWS cerró la conexión")
        self.connected = False

    def _on_publish(self, client, userdata, mid):
        print(f"[MQTT] Mensaje confirmado mid={mid}")

    def connect(self):
        """Conecta a AWS IoT Core"""
        
        try:
            if self.connected and self.client is not None:
                print("[MQTT] Ya conectado, no se abre otra conexión")
                return True
            if self.client is not None and not self.connected:
                try:
                    self.client.loop_stop()
                except Exception:
                    pass
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
            # Asegurar certs
            if not (CERTIFICATE_PATH.exists() and PRIVATE_KEY_PATH.exists() and ROOT_CA_PATH.exists()):
                print("[BOOT] No hay certs locales. solicitando con SUA...")
                okis = get_url_certificados()
                if not okis:
                    print("[BOOT] No se pudieron obtener certificados desde SUA.")
                    return False
            self.client = mqtt.Client(client_id=self.station_id)

            #callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_message = self._on_message
            
            # Configurar TLS
            self.client.tls_set(
                ca_certs=str(ROOT_CA_PATH),
                certfile=str(CERTIFICATE_PATH),
                keyfile=str(PRIVATE_KEY_PATH),
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            
            # Configurar Last Will and Testament (LWT)
            lwt_topic = TOPIC_PRESENCE.format(station_id=self.station_id)
            self.client.will_set(
                lwt_topic,
                payload=json.dumps({"status": "offline", "timestamp": time.time()}),
                qos=1,
                retain=False
            )
            
            # Conectar
            self.client.connect(AWS_IOT_ENDPOINT, AWS_IOT_PORT, keepalive=300)
            self.client.loop_start()
            #Espera a que se establezca la conexión antes de marcar como conectado
            timeout = 5  # segundos
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            if not self.connected:
                print("Timeout esperando conexión MQTT")
                return False
            self._publish_presence("online")  # Publicar presencia online al conectar
            print(f"Conectado a AWS IoT como estación {self.station_id}")
            
            # Suscribirse a las actualizaciones
            
            self._subscribe_updates()
            
            return True
        except Exception as e:
            print(f"Error conectando a AWS IoT: {e}")
            return False
    
    
    def disconnect(self):
        """Desconecta de AWS IoT"""
        if self.connected:
            # Publicar presencia offline
            self._publish_presence("offline")
            
            # Detener heartbeat
            if self.heartbeat_timer:
                self.heartbeat_timer.cancel()
            
            # Desconectar
            if self.client:
                self.client.disconnect()
                self.client.loop_stop()
            
            self.connected = False
            print("Desconectado de AWS IoT")
    
    def _publish_presence(self, status):
        """Publica estado de presencia"""
        topic = TOPIC_PRESENCE.format(station_id=self.station_id)
        payload = {
            "station_id": self.station_id,
            "status": status,
            "env": ENVIRONMENT,
            "timestamp": datetime.now().isoformat()
        }
        self._publish(topic, payload, retain=False)
    
    def publish_event(self, event_type, data=None):
        """Publica un evento"""
        topic = TOPIC_EVENTS.format(station_id=self.station_id)
        payload = {
            "event": event_type,
            "station_id": self.station_id,
            "env": ENVIRONMENT,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        self._publish(topic, payload)
    
    def publish_test_result(self, test_type, result_data):
        """Publica resultado de prueba (testeo/retest/etiqueta)"""
        topic = TOPIC_TEST_RESULTS.format(station_id=self.station_id)
        payload = {
            "event": test_type or "NaN",  # ETIQUETA, TESTEO, RETEST
            "station_id": self.station_id,
            "env": ENVIRONMENT,
            "timestamp": datetime.now().isoformat(),
            "data": result_data or {}
        }
        self._publish(topic, payload)

    def publish_update_ack(self, status, version_target, details=None):
        topic = TOPIC_UPDATES_ACK.format(station_id=self.station_id)
        payload = {
            "station_id": self.station_id,
            "env": ENVIRONMENT,
            "status": status,
            "version_target": version_target,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self._publish(topic, payload, qos=1, retain=False)
    
    def _publish(self, topic, payload, qos=1, retain=False):
        # Agregar ID único para detectar duplicados en AWS
        payload["message_id"] = str(uuid.uuid4())  # <-- ID único
        payload["publish_time"] = time.time()

        
        """Publica mensaje MQTT"""
        if not self.connected:
            print(f"ERROR: No conectado, no se puede publicar en {topic}")
            return False
        
        try:
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=qos,
                retain=retain
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Publicado en {topic}: {payload}")
                return True
            else:
                print(f"Error publicando en {topic}: {result.rc}")
                return False
        except Exception as e:
            print(f"Excepción publicando en {topic}: {e}")
            return False
        
    def _subscribe_updates(self):
        topics = [
            (TOPIC_UPDATES_ALL, 1),
            (TOPIC_UPDATES_STATION.format(station_id=self.station_id), 1),
        ]
        for topic, qos in topics:
            result, mid = self.client.subscribe(topic, qos=qos)
            print(f"[MQTT] subscribe topic={topic} result={result} mid={mid}")

    # ACTUALIZACION DESDE SSUA
    def _handle_update_message(self, topic, payload):
        if not self.update_lock.acquire(blocking=False):
            print("[UPDATE] Ya hay una actualización en curso, se ignora este mensaje")
            return

        try:
            msg_type = payload.get("type")

            if msg_type != "update_available":
                return
            
            target_version = payload.get("version")
            installer_url = payload.get("installer_url")
            installer_name = payload.get("installer_name", "ONTTesterSetup.exe")

            # Error por parte del mensaje recibido, no de descarga
            if not target_version or not installer_url:
                self.publish_update_ack(
                    status="failed",
                    version_target=target_version or "unknown",
                    details={"error": "Payload incompleto: falta version o installer_url"}
                )
                return

            from src.backend.endpoints.conexion import cargar_version
            current_version = cargar_version()

            # Ya actualizado -> Succes
            if current_version == target_version:
                print(f"[UPDATE] Ya estoy en versión {current_version}")
                self.publish_update_ack(
                    status="installed",
                    version_target=target_version,
                    details={
                        "note": "already_on_target_version",
                        "current_version": current_version
                    }
                )
                return

            from src.backend.sua_client.update_state import set_pending_update_target_version

            # Barra de progreso al 0%, comenzar instalación
            if self.event_q is not None:
                self.event_q.put((
                    "barra",
                    {
                        "show": True,
                        "status": "Actualización disponible",
                        "progress": 5,
                    }
                ))
            set_pending_update_target_version(
                version=target_version,
                installer_name=installer_name
            )

            self.publish_update_ack(
                status="pending",
                version_target=target_version,
                details={"current_version": current_version}
            )

            from src.backend.sua_client.actualizador import (
                download_update_installer_from_url,
                kill_processes_by_name,
                launch_inno_setup
            )

            # Comenzando proceso de descarga -> Avance al 30% (?)
            ok, ruta = download_update_installer_from_url(
                version=target_version,
                url=installer_url,
                installer_name=installer_name,
                queue=self.event_q
            )

            # Falla en la descarga -> Fail por culpa del ONT
            if not ok:
                self.publish_update_ack(
                    status="failed",
                    version_target=target_version,
                    details={"stage": "download"}
                )
                return

            # Descarga exitosa -> Avance completo
            self.publish_update_ack(
                status="downloaded",
                version_target=target_version,
                details={
                    "path": ruta,
                    "installer_name": installer_name,
                    "current_version": current_version
                }
            )

            from src.backend.sua_client.dao import insertar_version
            insertar_version(target_version)  # Guardar versión actual antes de actualizar
            print(f"[UPDATE] Versión actual registrada en local DB: {target_version}")


            kill_processes_by_name({"chromedriver.exe", "cmd.exe"})
            launch_inno_setup(ruta)

        except Exception as e:
            print(f"[UPDATE] Error: {e}")
            self.publish_update_ack(
                status="failed",
                version_target=payload.get("version", "unknown"),
                details={"error": str(e)}
            )
        finally:
            self.update_lock.release()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            print(f"[MQTT] Mensaje recibido topic={msg.topic} payload={payload}")

            thread = threading.Thread(
                target=self._handle_update_message,
                args=(msg.topic, payload),
                daemon=True,
            )
            thread.start()

        except Exception as e:
            print(f"[MQTT] Error procesando mensaje entrante: {e}")

    

    def report_installed_version_if_needed(self, target_version: str | None = None):
        """
        Se utiliza al arrancar la app, después de conectar MQTT.
        Si la app ya está en la versión target, reporta installed.
        """
        try:
            from src.backend.endpoints.conexion import cargar_version
            from src.backend.sua_client.update_state import (
                get_pending_update_target_version,
                clear_pending_update_target_version,
                set_last_reported_installed_version,
            )

            current_version = cargar_version()

            

            if not target_version:
                print("[UPDATE] No hay target_version pendiente para confirmar instalación")
                return False

            if current_version == target_version:
                ok = self.publish_update_ack(
                    status="installed",
                    version_target=target_version,
                    details={
                        "current_version": current_version,
                        "note": "reported_on_startup"
                    }
                )

                if ok:
                    set_last_reported_installed_version(current_version)
                    clear_pending_update_target_version()

                return ok

            print(
                f"[UPDATE] La versión actual ({current_version}) aún no coincide con la target ({target_version})"
            )
            return False

        except Exception as e:
            print(f"[UPDATE] No se pudo reportar versión instalada al arranque: {e}")
            return False
    
    def _start_heartbeat(self):
        """Inicia el envío periódico de heartbeat"""
        def heartbeat():
            if self.connected:
                self.publish_event("heartbeat", {"interval": HEARTBEAT_INTERVAL})
                self.heartbeat_timer = threading.Timer(HEARTBEAT_INTERVAL, heartbeat)
                self.heartbeat_timer.start()
        
        heartbeat()

def llamada_verision_instalada():
    from src.backend.sua_client.update_state import get_pending_update_target_version
    from src.backend.sua_client import publisher

    target_version = get_pending_update_target_version()
    if not target_version:
        print("[UPDATE] No hay una versión pendiente de confirmar")
        return

    iot_client = publisher.get_client()
    if iot_client and iot_client.connected:
        print("Usando conexión MQTT existente. Publicando confirmación de nueva versión instalada...")
        iot_client.report_installed_version_if_needed(target_version=target_version)
    else:
        print("No se pudo obtener una conexión MQTT activa.")