import pytest

from src.backend.mixins.common_mixin import CommonMixin

def optical(tx, rx):
    return {"hw_optical": {"data": {"tx_optical_power": f"{tx:.2f} dBm", "rx_optical_power": f"{rx:.2f} dBm"}}}

def usb(connected=True):
    return {"hw_usb": {"data": {"connected": connected}}}

def factory_reset(status=True):
    return {"factory_reset": {"status": status}}

def sw_update(done=True):
    return {"software_update": {"details": {"update_completed": done}}}

def wifi_raw(p24, p5, ssid24="Totalplay-A2A2", ssid5="Totalplay-A2A2-5G"):
    return {"potencia_wifi": {"details": {
        "raw_24": [{"ssid": ssid24, "signal_percent": p24}],
        "raw_5": [{"ssid": ssid5, "signal_percent": p5}],
    }}}

# "name, modo, add_tests, expect",
# Casos estándar + valores dentro de los límites máximos
CASES_HUAWEI_BASE = [
    # ETIQUETA: solo ping => casi nada en tests
    pytest.param(
        "etiqueta_minimo", "ETIQUETA",
        {
            # "hw_mac": {"data": "AA:BB:CC:DD:EE:FF"},
            # "hw_device": {"data": {"software_version": "V1"}},
            # "hw_wifi24": {"data": {"ssid": "WIFI_24", "status": "Enabled"}},
            # "hw_wifi5": {"data": {"ssid": "WIFI_5", "status": "Enabled"}},
            # "hw_wifi24_pass": {"data": {"password": "12345678"}},
        },
        {
            # Con la lógica actual (05/02/2026) Si no se hace la prueba no se agrega la key
            # "reset": "SIN PRUEBA",
            # "usb": "SIN PRUEBA",
            # "tx": "SIN PRUEBA",
            # "rx": "SIN PRUEBA",
            # "w24": "SIN PRUEBA",
            # "w5": "SIN PRUEBA",
            # "sftU": "SIN PRUEBA",
        },
        id="ETIQUETA completa (todos los valores encontrados)",
    ),

    # TEST completo: existen las keys porque se ejecutó todo
    pytest.param(
        "test_completo_ok", "TEST",
        {**factory_reset(True), **usb(True), **optical(2.72, -14.69), **sw_update(True)},
        {"reset": "PASS", "usb": True, "tx": 2.72, "rx": -14.69, "sftU": True},
        id="TEST INICIAL completo (todos los valores encontrados)",
    ),

    pytest.param(
        "test_completo_limites S", "TEST",
        {**factory_reset(True), **usb(True), **optical(5.00, -13.00), **sw_update(True)},
        {"reset": "PASS", "usb": True, "tx": 5.0, "rx": -13.0, "sftU": True},
        id="TEST INICIAL limites de valores S",
    ),

    pytest.param(
        "test_completo_limites I", "TEST",
        {**factory_reset(True), **usb(True), **optical(1.00, -19.00), **sw_update(True)},
        {"reset": "PASS", "usb": True, "tx": 1.0, "rx": -19.0, "sftU": True},
        id="TEST INICIAL limites de valores I",
    ),

    # RETEST: opciones apagaron reset
    pytest.param(
        "retest_sin_reset", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True), **wifi_raw(80, 75)},
        {"sftU": True, "usb": True, "tx": 2.72, "rx": -14.69, "w24": True, "w5": True},
        id="RETEST completo (todos los valores encontrados)",
    ),

    pytest.param(
        "retest_limites_superiores", "RETEST",
        {**usb(True), **optical(5.00, -13.00), **sw_update(True), **wifi_raw(100, 100)},
        {"sftU": True, "usb": True, "tx": 5.0, "rx": -13.0, "w24": True, "w5": True},
        id="RETEST limites superiores",
    ),

    pytest.param(
        "retest_limites_inferiores", "RETEST",
        {**usb(True), **optical(1.00, -19.00), **sw_update(True), **wifi_raw(60, 60)},
        {"sftU": True, "usb": True, "tx": 1.0, "rx": -19.0, "w24": True, "w5": True},
        id="RETEST limites inferiores",
    ),
]

# Casos fuera de los límites
CASES_HUAWEI_LIMITES = [
    pytest.param(
        "retest_fuera_limites_inferiores", "RETEST",
        {**usb(True), **optical(0.99, -19.01), **sw_update(True), **wifi_raw(59, 59)},
        {"sftU": True, "usb": True, "tx": False, "rx": False, "w24": False, "w5": False},
        id="RETEST limites inferiores fuera de rango",
    ),

    pytest.param(
        "retest_limites_superiores_fuera", "RETEST",
        {**usb(True), **optical(5.01, -12.99), **sw_update(True), **wifi_raw(101, 101)},
        {"sftU": True, "usb": True, "tx": False, "rx": False, "w24": True, "w5": True},
        id="RETEST limites superiores fuera de rango",
    ),

    pytest.param(
        "test_completo__fuera_limites I", "TEST",
        {**factory_reset(True), **usb(True), **optical(0.99, -19.01), **sw_update(True)},
        {"reset": "PASS", "usb": True, "tx": False, "rx": False, "sftU": True},
        id="TEST INICIAL fuera de limites de valores I",
    ),

    pytest.param(
        "test_completo__fuera_limites S", "TEST",
        {**factory_reset(True), **usb(True), **optical(5.01, -12.99), **sw_update(True)},
        {"reset": "PASS", "usb": True, "tx": False, "rx": False, "sftU": True},
        id="TEST INICIAL fuera de limites de valores S",
    ),
]

CASES_HUAWEI = CASES_HUAWEI_BASE + CASES_HUAWEI_LIMITES
@pytest.mark.parametrize("name, modo, add_tests, expect", CASES_HUAWEI)
def test_resultados_huawei_por_modo(name, modo, add_tests, expect,
                                   huawei_base_payload, opts_por_modo, payload_builder, dummy_factory):
    payload = payload_builder(huawei_base_payload, add_tests=add_tests)
    opts = opts_por_modo[modo]

    # En caso de querer umbrales específicos (en la clase Tresholds ya hay definidos, esto solo contempla específicos)
    """
    from tests.helpers.thresholds import Thresholds

    thresholds = Thresholds(
        min_tx=0.5,
        max_tx=6,
        min_rx=-25,
        max_rx=-10,
    )

    dummy = dummy_factory(payload, opts, thresholds)

    Para cuando se hagan los de integracion con la BD
    thresholds = load_thresholds_from_db()

    dummy = dummy_factory(payload, opts, thresholds)
    """
    dummy = dummy_factory(payload, opts)
    out = CommonMixin._resultadosHuawei(dummy)

    for k, v in expect.items():
        assert out["tests"][k] == v, (name, k, out["tests"].get(k), v, out)