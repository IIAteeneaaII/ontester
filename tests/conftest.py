# tests/conftest.py
import copy
from types import SimpleNamespace
import pytest
from tests.helpers.tresholds import Thresholds

@pytest.fixture
def huawei_base_payload():
    """
    Payload base para los huawei (compartida entre todos los casos ∴ payload de etiqueta)
    """
    return {
            "metadata": {
                "host": "192.168.100.1",
                "model": "HG8145V5",
                "timestamp": "2026-03-05T11:56:29.585849",
                "serial_number": "485754431BB9A2A2"
            },
            "tests": {
                "hw_device": {
                    "data": {
                        "software_version": "V5R022C00S292"
                    }
                },
                "hw_wifi24": {
                    "data": {
                        "ssid": "Totalplay-A2A2"
                    }
                },
                "hw_wifi5": {
                    "data": {
                        "ssid": "Totalplay-A2A2-5G"
                    }
                },
                "hw_mac": {
                    "data": "8C:E5:EF:FE:0A:75"
                },
                "hw_wifi24_pass": {
                    "data": {
                        "password": "A2A20A754P2HZyPR"
                    }
                }
            }
        }


@pytest.fixture
def opts_por_modo():
    """Todas las banderas de retest encendidas para que el método intente evaluarlas."""
    return {
        "RETEST": {
            "ping": True,
            "factory_reset": False,
            "usb_port": True,
            "tx_power": True,
            "rx_power": True,
            "wifi_24ghz_signal": True,
            "wifi_5ghz_signal": True,
            "software_update": True,
        },
        "ETIQUETA": {
            "ping": True,
            "factory_reset": False,
            "usb_port": False,
            "tx_power": False,
            "rx_power": False,
            "wifi_24ghz_signal": False,
            "wifi_5ghz_signal": False,
            "software_update": False,
        },
        "TEST": {
            "ping": True,
            "factory_reset": True,
            "usb_port": True,
            "tx_power": True,
            "rx_power": True,
            "wifi_24ghz_signal": False,
            "wifi_5ghz_signal": False,
            "software_update": True,
        }
    }

@pytest.fixture
def payload_builder():
    """
    Construye una payload a partir de la base+tests+remove_keys-
    tests: dict con entradas a insertar en la payload["tests"]
    remove_keys: lista de keys a eliminar de payload["tests"]
    """
    def _make(base: dict, add_tests=None, remove_keys=None):
        p = copy.deepcopy(base)
        add_tests = add_tests or {}
        remove_keys = remove_keys or []
        p.setdefault("tests", {})
        p["tests"].update(add_tests)
        for k in remove_keys:
            p["tests"].pop(k, None)
        return p
    return _make

@pytest.fixture
def dummy_factory():
    """
    Crea el self-dummy minimo para CommonMixin (resultados por ahora)
    """
    def _make(test_results, tests_opts, thresholds=None):

        if thresholds is None:
            thresholds = Thresholds()  # valores default para unit tests

        dummy = SimpleNamespace()

        dummy.test_results = test_results
        dummy.opcionesTest = {"tests": tests_opts}

        # inyectar umbrales
        dummy._getMinFibraTx = lambda: thresholds.min_tx
        dummy._getMaxFibraTx = lambda: thresholds.max_tx
        dummy._getMinFibraRx = lambda: thresholds.min_rx
        dummy._getMaxFibraRx = lambda: thresholds.max_rx

        dummy._getMinWifi24SignalPercent = lambda: thresholds.min_wifi24
        dummy._getMinWifi5SignalPercent = lambda: thresholds.min_wifi5

        return dummy
    return _make
