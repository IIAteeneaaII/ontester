import pytest

from src.backend.mixins.common_mixin import CommonMixin

@pytest.mark.parametrize(
    "name, modo, add_tests, expect",
    [
        # ETIQUETA: solo ping => casi nada en tests
        ("etiqueta_minimo", "ETIQUETA",
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
         }),

        # TEST completo: existen las keys porque se ejecutó todo
        ("test_completo_ok", "TEST",
         {
            # "hw_mac": {"data": "AA:BB:CC:DD:EE:FF"},
            # "hw_device": {"data": {"software_version": "V1"}},
            # "hw_wifi24": {"data": {"ssid": "WIFI_24", "status": "Enabled"}},
            # "hw_wifi5": {"data": {"ssid": "WIFI_5", "status": "Enabled"}},
            # "hw_wifi24_pass": {"data": {"password": "12345678"}},
            "factory_reset": {"status": True},
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "2.72 dBm", "rx_optical_power": "-14.69 dBm"}},
            "software_update": {"details": {"update_completed": True}},
         },
         {
            "reset": "PASS",
            "usb": True,
            "tx": 2.72,
            "rx": -14.69,
            "sftU": True,
         }),
         ("test_completo_limites S", "TEST",
         {
            "factory_reset": {"status": True},
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "5.00 dBm", "rx_optical_power": "-13.00 dBm"}},
            "software_update": {"details": {"update_completed": True}},
         },
         {
            "reset": "PASS",
            "usb": True,
            "tx": 5.0,
            "rx": -13.0,
            "sftU": True,
         }),
         ("test_completo_limites I", "TEST",
         {
            "factory_reset": {"status": True},
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "1.00 dBm", "rx_optical_power": "-19.00 dBm"}},
            "software_update": {"details": {"update_completed": True}},
         },
         {
            "reset": "PASS",
            "usb": True,
            "tx": 1.0,
            "rx": -19.0,
            "sftU": True,
         }),

        # RETEST: opciones apagaron reset 
        ("retest_sin_reset", "RETEST",
         {
            # "hw_mac": {"data": "AA:BB:CC:DD:EE:FF"},
            # "hw_device": {"data": {"software_version": "V1"}},
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "2.72 dBm", "rx_optical_power": "-14.69 dBm"}},
            "software_update": {"status": True, "details": {"update_completed": True}},
            "potencia_wifi": {"details": {
                "raw_24": [{"ssid": "Totalplay-A2A2", "signal_percent": 80}],
                "raw_5": [{"ssid": "Totalplay-A2A2-5G", "signal_percent": 75}],
            }},
         },
         {
            "sftU": True,
            "usb": True,
            "tx": 2.72,
            "rx": -14.69,
            "w24": True,
            "w5": True,
         }),
         ("retest_limites_superiores", "RETEST",
         {
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "5.00 dBm", "rx_optical_power": "-13.00 dBm"}},
            "software_update": {"status": True, "details": {"update_completed": True}},
            "potencia_wifi": {"details": {
                "raw_24": [{"ssid": "Totalplay-A2A2", "signal_percent": 100}],
                "raw_5": [{"ssid": "Totalplay-A2A2-5G", "signal_percent": 100}],
            }},
         },
         {
            "sftU": True,
            "usb": True,
            "tx": 5.0,
            "rx": -13.0,
            "w24": True,
            "w5": True,
         }),
         ("retest_limites_inferiores", "RETEST",
         {
            "hw_usb": {"data": {"connected": True}},
            "hw_optical": {"data": {"tx_optical_power": "1.00 dBm", "rx_optical_power": "-19.00 dBm"}},
            "software_update": {"status": True, "details": {"update_completed": True}},
            "potencia_wifi": {"details": {
                "raw_24": [{"ssid": "Totalplay-A2A2", "signal_percent": 60}],
                "raw_5": [{"ssid": "Totalplay-A2A2-5G", "signal_percent": 60}],
            }},
         },
         {
            "sftU": True,
            "usb": True,
            "tx": 1.0,
            "rx": -19.0,
            "w24": True,
            "w5": True,
         }),
    ],
    # Ponerle ids para salida mas limpia
    ids=[
            "ETIQUETA completa (todos los valores encontrados)", 
            "TEST INICIAL completo (todos los valores encontrados)", 
            "TEST INICIAL limites de valores S", 
            "TEST INICIAL limites de valores I", 
            "RETEST completo (todos los valores encontrados)",
            "RETEST limites superiores",
            "RETEST limites inferiores",
        ]
)
def test_resultados_huawei_por_modo(name, modo, add_tests, expect,
                                   huawei_base_payload, opts_por_modo, payload_builder, dummy_factory):
    payload = payload_builder(huawei_base_payload, add_tests=add_tests)
    opts = opts_por_modo[modo]

    dummy = dummy_factory(payload, opts)
    out = CommonMixin._resultadosHuawei(dummy)

    for k, v in expect.items():
        assert out["tests"][k] == v, (name, k, out["tests"].get(k), v, out)