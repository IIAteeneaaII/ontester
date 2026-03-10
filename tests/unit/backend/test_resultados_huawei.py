import pytest

from src.backend.mixins.common_mixin import CommonMixin
from tests.helpers.helpers_construccion import *

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
        [],
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
        [],
        {
            "present": 
                {"tests.reset": "PASS", "tests.usb": True, "tests.tx": 2.72, "tests.rx": -14.69, "tests.sftU": True}, 
            "missing": []
        },
        id="TEST INICIAL completo (todos los valores encontrados)",
    ),

    pytest.param(
        "test_completo_limites S", "TEST",
        {**factory_reset(True), **usb(True), **optical(5.00, -13.00), **sw_update(True)},
        [],
        {"present": {"tests.reset": "PASS", "tests.usb": True, "tests.tx": 5.0, "tests.rx": -13.0, "tests.sftU": True}},
        id="TEST INICIAL limites de valores S",
    ),

    pytest.param(
        "test_completo_limites I", "TEST",
        {**factory_reset(True), **usb(True), **optical(1.00, -19.00), **sw_update(True)},
        [],
        {"present": {"tests.reset": "PASS", "tests.usb": True, "tests.tx": 1.0, "tests.rx": -19.0, "tests.sftU": True}},
        id="TEST INICIAL limites de valores I",
    ),

    # RETEST: opciones apagaron reset
    pytest.param(
        "retest_sin_reset", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True), **wifi_raw(80, 75)},
        [],
        {"present": {"tests.sftU": True, "tests.usb": True, "tests.tx": 2.72, "tests.rx": -14.69, "tests.w24": True, "tests.w5": True}},
        id="RETEST completo (todos los valores encontrados)",
    ),

    pytest.param(
        "retest_limites_superiores", "RETEST",
        {**usb(True), **optical(5.00, -13.00), **sw_update(True), **wifi_raw(100, 100)},
        [],
        {"present": {"tests.sftU": True, "tests.usb": True, "tests.tx": 5.0, "tests.rx": -13.0, "tests.w24": True, "tests.w5": True}},
        id="RETEST limites superiores",
    ),

    pytest.param(
        "retest_limites_inferiores", "RETEST",
        {**usb(True), **optical(1.00, -19.00), **sw_update(True), **wifi_raw(60, 60)},
        [],
        {"present": {"tests.sftU": True, "tests.usb": True, "tests.tx": 1.0, "tests.rx": -19.0, "tests.w24": True, "tests.w5": True}},
        id="RETEST limites inferiores",
    ),
]

# Casos fuera de los límites
CASES_HUAWEI_LIMITES = [
    pytest.param(
        "retest_fuera_limites_inferiores", "RETEST",
        {**usb(True), **optical(0.99, -19.01), **sw_update(True), **wifi_raw(59, 59)},
        [],
        {"present":{"tests.sftU": True, "tests.usb": True, "tests.tx": False, "tests.rx": False, "tests.w24": False, "tests.w5": False}},
        id="RETEST limites inferiores fuera de rango",
    ),

    pytest.param(
        "retest_limites_superiores_fuera", "RETEST",
        {**usb(True), **optical(5.01, -12.99), **sw_update(True), **wifi_raw(101, 101)},
        [],
        {"present": {"tests.sftU": True, "tests.usb": True, "tests.tx": False, "tests.rx": False, "tests.w24": True, "tests.w5": True}},
        id="RETEST limites superiores fuera de rango",
    ),

    pytest.param(
        "test_completo__fuera_limites I", "TEST",
        {**factory_reset(True), **usb(True), **optical(0.99, -19.01), **sw_update(True)},
        [],
        {"present": {"tests.reset": "PASS", "tests.usb": True, "tests.tx": False, "tests.rx": False, "tests.sftU": True}},
        id="TEST INICIAL fuera de limites de valores I",
    ),

    pytest.param(
        "test_completo__fuera_limites S", "TEST",
        {**factory_reset(True), **usb(True), **optical(5.01, -12.99), **sw_update(True)},
        [],
        {"present": {"tests.reset": "PASS", "tests.usb": True, "tests.tx": False, "tests.rx": False, "tests.sftU": True}},
        id="TEST INICIAL fuera de limites de valores S",
    ),
]

CASES_HUAWEI_INCOMPLETOS = [
    # =========================
    # TEST: keys faltantes
    # =========================
    pytest.param(
        "test_sin_factory_reset", "TEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True)},
        ["factory_reset"],
        {
            "present": {
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
            },
            "missing": [
                "tests.reset",
            ],
        },
        id="HUAWEI_TEST_sin_factory_reset",
    ),

    pytest.param(
        "test_sin_hw_usb", "TEST",
        {**factory_reset(True), **optical(2.72, -14.69), **sw_update(True)},
        ["hw_usb"],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
            },
            "missing": [
                "tests.usb",
            ],
        },
        id="HUAWEI_TEST_sin_hw_usb",
    ),

    pytest.param(
        "test_sin_hw_optical", "TEST",
        {**factory_reset(True), **usb(True), **sw_update(True)},
        ["hw_optical"],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.sftU": True,
            },
            "missing": [
                "tests.tx",
                "tests.rx",
            ],
        },
        id="HUAWEI_TEST_sin_hw_optical",
    ),

    pytest.param(
        "test_sin_software_update", "TEST",
        {**factory_reset(True), **usb(True), **optical(2.72, -14.69)},
        ["software_update"],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
            },
            "missing": [
                "tests.sftU",
            ],
        },
        id="HUAWEI_TEST_sin_software_update",
    ),

    pytest.param(
        "retest_sin_potencia_wifi", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True)},
        ["potencia_wifi"],
        {
            "present": {
                #"tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
            },
            "missing": [
                "tests.w24",
                "tests.w5",
            ],
        },
        id="HUAWEI_RETEST_sin_potencia_wifi",
    ),

    # =========================
    # TEST: key existe pero data=None
    # =========================
    pytest.param(
        "test_hw_optical_data_none", "TEST",
        {**factory_reset(True), **usb(True), **optical_none(), **sw_update(True)},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": False,
                "tests.rx": False,
                "tests.sftU": True,
            },
            "missing": [],
        },
        id="HUAWEI_TEST_hw_optical_data_none",
    ),

    pytest.param(
        "test_hw_usb_data_none", "TEST",
        {**factory_reset(True), **usb_none(), **optical(2.72, -14.69), **sw_update(True)},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": False,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
            },
            "missing": [],
        },
        id="HUAWEI_TEST_hw_usb_data_none",
    ),

    pytest.param(
        "test_hw_usb_data_empty", "TEST",
        {**factory_reset(True), **usb_empty(), **optical(2.72, -14.69), **sw_update(True)},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": False,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
            },
            "missing": [],
        },
        id="HUAWEI_TEST_hw_usb_data_empty",
    ),

    pytest.param(
        "retest_hw_wifi24_data_none", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **wifi24_none(), **sw_update(True), **wifi_raw(80, 75)},
        [],
        {
            "present": {
                #"tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
                "tests.w24": False,
                "tests.w5": True,
            },
            "missing": [],
        },
        id="HUAWEI_RETEST_hw_wifi24_data_none",
    ),

    pytest.param(
        "retest_hw_wifi5_data_none", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **wifi5_none(), **sw_update(True), **wifi_raw(80, 75)},
        [],
        {
            "present": {
                #"tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
                "tests.w24": True,
                "tests.w5": False,
            },
            "missing": [],
        },
        id="HUAWEI_RETEST_hw_wifi5_data_none",
    ),

    pytest.param(
        "test_hw_wifi24_pass_data_none", "TEST",
        {**factory_reset(True), **usb(True), **optical(2.72, -14.69), **wifi24_pass_none(), **sw_update(True)},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
                "info.passWifi": "N/A",
            },
            "missing": [],
        },
        id="HUAWEI_TEST_hw_wifi24_pass_data_none",
    ),

    # =========================
    # TEST: subcampos faltantes / details rotos
    # =========================
    pytest.param(
        "test_software_update_sin_details", "TEST",
        {**factory_reset(True), **usb(True), **optical(2.72, -14.69), **sw_update_no_details()},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": None,
            },
            "missing": [],
        },
        id="HUAWEI_TEST_software_update_sin_details",
    ),

    pytest.param(
        "test_software_update_details_vacios", "TEST",
        {**factory_reset(True), **usb(True), **optical(2.72, -14.69), **sw_update_details_empty()},
        [],
        {
            "present": {
                "tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": None,
            },
            "missing": [],
        },
        id="HUAWEI_TEST_software_update_details_vacios",
    ),

    pytest.param(
        "retest_wifi_raw_solo_24", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True), **wifi_raw_only_24(80)},
        [],
        {
            "present": {
                #"tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
                "tests.w24": True,
                "tests.w5": False,
            },
            "missing": [],
        },
        id="HUAWEI_RETEST_wifi_raw_solo_24",
    ),

    pytest.param(
        "retest_wifi_raw_solo_5", "RETEST",
        {**usb(True), **optical(2.72, -14.69), **sw_update(True), **wifi_raw_only_5(75)},
        [],
        {
            "present": {
                #"tests.reset": "PASS",
                "tests.usb": True,
                "tests.tx": 2.72,
                "tests.rx": -14.69,
                "tests.sftU": True,
                "tests.w24": False,
                "tests.w5": True,
            },
            "missing": [],
        },
        id="HUAWEI_RETEST_wifi_raw_solo_5",
    ),
]

CASES_HUAWEI = CASES_HUAWEI_BASE + CASES_HUAWEI_LIMITES + CASES_HUAWEI_INCOMPLETOS
@pytest.mark.parametrize("name, modo, add_tests, remove_tests, expect", CASES_HUAWEI)
def test_resultados_huawei_por_modo(name, modo, add_tests, remove_tests, expect,
                                 huawei_base_payload, opts_por_modo, payload_builder, dummy_factory):
    payload = payload_builder(
        huawei_base_payload,
        add_tests=add_tests,
        remove_tests=remove_tests,
    )
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

    present = expect.get("present", {})
    missing = expect.get("missing", [])

    # print("CASE:", name)
    # print("EXPECT:", expect)
    for path, expected in present.items():
        got = get_path_strict(out, path)
        #print("KEY:", path, "GOT:", got, "EXPECTED:", expected, "EQUAL?:", got == expected)
        assert got == expected, (name, path, got, expected, out)

    for path in missing:
        exists = path_exists(out, path)
        #print("MISSING CHECK ->", path, "EXISTS?:", exists)
        assert not path_exists(out, path), (name, path, out)