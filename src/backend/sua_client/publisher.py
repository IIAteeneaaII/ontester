"""
Módulo simplificado para publicar eventos desde cualquier parte de la aplicación
"""
from .iot_client import IoTClient

_iot_client = None
_event_q = None


def configure_event_queue(event_q):
    global _event_q
    _event_q = event_q


def get_client():
    global _iot_client

    if _event_q is None:
        raise RuntimeError("publisher.py no ha sido configurado con event_q")

    if _iot_client is None:
        _iot_client = IoTClient(event_q=_event_q)
        _iot_client.connect()
        return _iot_client

    if not _iot_client.connected:
        _iot_client.connect()

    return _iot_client

def publish_event(event_type, data=None):
    """Publica un evento"""
    client = get_client()
    return client.publish_event(event_type, data)

def publish_presence(status):
    """Publica presencia (online/offline)"""
    client = get_client()
    return client._publish_presence(status)

def publish_test_result(test_type, result_data):
    """Publica resultado de prueba"""
    client = get_client()
    return client.publish_test_result(test_type, result_data)

def disconnect():
    """Desconecta el cliente"""
    global _iot_client
    if _iot_client:
        _iot_client.disconnect()
        _iot_client = None