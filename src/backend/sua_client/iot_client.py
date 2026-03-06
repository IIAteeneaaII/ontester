import paho.mqtt.client as mqtt
import ssl
import json
import time
import threading
from datetime import datetime
from .settings import *
import uuid
from .sua_acceso import ensure_certs_from_sua, get_url_certificados

class IoTClient:
    def __init__(self, station_id=None):
        self.station_id = station_id or STATION_ID
        self.client = None
        self.connected = False
        self.heartbeat_timer = None

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
            # Asegurar certs
            if not (CERTIFICATE_PATH.exists() and PRIVATE_KEY_PATH.exists() and ROOT_CA_PATH.exists()):
                print("[BOOT] No hay certs locales. Bootstrapping con SUA...")
                if not get_url_certificados:
                    print("[BOOT] No se pudieron obtener certificados desde SUA.")
                    return False
            self.client = mqtt.Client(client_id=self.station_id)

            #callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            
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
            if self.connected:
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
    
    def _start_heartbeat(self):
        """Inicia el envío periódico de heartbeat"""
        def heartbeat():
            if self.connected:
                self.publish_event("heartbeat", {"interval": HEARTBEAT_INTERVAL})
                self.heartbeat_timer = threading.Timer(HEARTBEAT_INTERVAL, heartbeat)
                self.heartbeat_timer.start()
        
        heartbeat()