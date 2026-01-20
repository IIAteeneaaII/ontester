import json
import os
from pathlib import Path

# Configuración de AWS IoT
AWS_IOT_ENDPOINT = "a2fpmiyip6snsh-ats.iot.us-east-1.amazonaws.com"  
AWS_IOT_PORT = 8883

# Rutas de certificados y claves
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CERTS_DIR = BASE_DIR / "certs"
CERTIFICATE_PATH = CERTS_DIR / "certificate.pem.crt"
PRIVATE_KEY_PATH = CERTS_DIR / "private.pem.key"
ROOT_CA_PATH = CERTS_DIR / "AmazonRootCA1.pem"

# Temas MQTT 
TOPIC_PRESENCE = f"ontester/presence/{{station_id}}"
TOPIC_EVENTS = f"ontester/events/{{station_id}}"
TOPIC_TEST_RESULTS = f"ontester/test/results/{{station_id}}"

# Configuración local
STATION_ID = "001"  # Esto debe leerse de la base de datos o config
ENVIRONMENT = "dev"  # dev/prod

# Heartbeat
HEARTBEAT_INTERVAL = 30  # segundos