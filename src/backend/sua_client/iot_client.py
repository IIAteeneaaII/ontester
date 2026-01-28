import paho.mqtt.client as mqtt
import ssl
import json
import time
import threading
from datetime import datetime
from .settings import *

class IoTClient:
    def __init__(self, station_id=None):
        self.station_id = station_id or STATION_ID
        self.client = None
        self.connected = False
        self.heartbeat_timer = None
        # Agregados para estabilidad
        self._connected_evt = threading.Event()
        self._pub_lock = threading.Lock()
        
    def connect(self):
        """Conecta a AWS IoT Core"""
        try:
            self.client = mqtt.Client(client_id=self.station_id)
            
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
                retain=True
            )
            
            # Conectar
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            # Despues de verificar
            self._connected_evt.clear()
            self.client.connect(AWS_IOT_ENDPOINT, AWS_IOT_PORT, keepalive=60)
            self.client.loop_start()
            # self.connected = True

            if not self._connected_evt.wait(timeout=10):
                print("Timeout esperando on_connect")
                self.connected = False
                return False

            if not self.connected:
                return False
            
            # Publicar presencia online
            self._publish_presence("online")
            
            # Iniciar heartbeat
            # self._start_heartbeat()
            
            print(f"Conectado a AWS IoT como estación {self.station_id}")
            return True
            
        except Exception as e:
            print(f"Error conectando a AWS IoT: {e}")
            self.connected = False
            self.disconnect()
            return False
    
    def disconnect(self):
        """Desconecta de AWS IoT"""
        if self.connected:
            # Publicar presencia offline
            self._publish_presence("offline")
            
            # Detener heartbeat
            if self.heartbeat_timer:
                self.heartbeat_timer.cancel()
                self.heartbeat_timer = None
            
            # Desconectar
            if self.client:
                try:
                 self.client.disconnect()
                except Exception:
                    pass
                try:
                    self.client.loop_stop()   # <-- CLAVE
                except Exception:
                    pass
            
            self.connected = False
            self.client = None
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
        self._publish(topic, payload, retain=True)
    
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
        
        # También publicar en el topic específico para tu política
        #test_topic = f"{TOPIC_BASE}/test/{event_type}"
        #self._publish(test_topic, payload)
    
    def publish_test_result(self, test_type, result_data):
        """Publica resultado de prueba (testeo/retest/etiqueta)"""
        topic = TOPIC_TEST_RESULTS.format(station_id=self.station_id)
        payload = {
            "test_type": test_type,  # ETIQUETA, TESTEO, RETEST
            "station_id": self.station_id,
            "env": ENVIRONMENT,
            "timestamp": datetime.now().isoformat(),
            "result": result_data
        }
        self._publish(topic, payload)
        
        # También para compatibilidad con tu política
        #test_topic = f"{TOPIC_BASE}/test/results"
        #self._publish(test_topic, payload)
    
    def _publish(self, topic, payload, qos=1, retain=False):
        """Publica mensaje MQTT"""
        if not self.client:
            return False

        # Validación real del socket
        if (not self.connected) or (not self.client.is_connected()):
            self.connected = False
            print(f"ERROR: No conectado, no se puede publicar en {topic}")
            return False

        try:
            with self._pub_lock:  # evita choques con heartbeat + worker
                result = self.client.publish(topic, json.dumps(payload), qos=qos, retain=retain)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Publicado en {topic}: {payload}")
                return True

            print(f"Error publicando en {topic}: {result.rc} ({mqtt.error_string(result.rc)})")
            return False

        except Exception as e:
            print(f"Excepción publicando en {topic}: {e}")
            return False
        # if not self.connected:
        #     print(f"ERROR: No conectado, no se puede publicar en {topic}")
        #     return False
        # print("rc:", result.rc, mqtt.error_string(result.rc))
        # try:
        #     result = self.client.publish(
        #         topic,
        #         json.dumps(payload),
        #         qos=qos,
        #         retain=retain
        #     )
        #     if result.rc == mqtt.MQTT_ERR_SUCCESS:
        #         print(f"Publicado en {topic}: {payload}")
        #         return True
        #     else:
        #         print(f"Error publicando en {topic}: {result.rc}")
        #         return False
        # except Exception as e:
        #     print(f"Excepción publicando en {topic}: {e}")
        #     return False
    
    def _start_heartbeat(self):
        """Inicia el envío periódico de heartbeat"""
        def heartbeat():
            if self.connected:
                self.publish_event("heartbeat", {"interval": HEARTBEAT_INTERVAL})
                self.heartbeat_timer = threading.Timer(HEARTBEAT_INTERVAL, heartbeat)
                self.heartbeat_timer.start()
        
        heartbeat()

    # Funciones helper para desconexion y conexion
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("MQTT conectado OK")
        else:
            self.connected = False
            print(f"MQTT connect rc={rc}")
        self._connected_evt.set()

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        print(f"MQTT desconectado rc={rc}")