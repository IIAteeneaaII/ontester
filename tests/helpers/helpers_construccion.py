# Helpers para construccion de pruebas
def get_path_strict(data, path):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict):
            raise KeyError(path)
        if part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def path_exists(data, path):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return False
        if part not in current:
            return False
        current = current[part]
    return True

# Helpers de construccion de casos HUAWEI
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

def optical_none():
    return {"hw_optical": {"data": None}}

def usb_none():
    return {"hw_usb": {"data": None}}

def usb_empty():
    return {"hw_usb": {"data": {}}}

def wifi24_none():
    return {"hw_wifi24": {"data": None}}

def wifi5_none():
    return {"hw_wifi5": {"data": None}}

def wifi24_pass_none():
    return {"hw_wifi24_pass": {"data": None}}

def sw_update_no_details():
    return {"software_update": {}}

def sw_update_details_empty():
    return {"software_update": {"details": {}}}

def wifi_raw_only_24(p24, ssid24="Totalplay-A2A2"):
    return {"potencia_wifi": {"details": {
        "raw_24": [{"ssid": ssid24, "signal_percent": p24}],
        "raw_5": [],
    }}}

def wifi_raw_only_5(p5, ssid5="Totalplay-A2A2-5G"):
    return {"potencia_wifi": {"details": {
        "raw_24": [],
        "raw_5": [{"ssid": ssid5, "signal_percent": p5}],
    }}}

# Helpers de construccion de casos ZTE
def zte_factory_reset(status=True):
    return {
        "factory_reset": {
            "name": "factory_reset",
            "status": status,
            "data": {"result": status}
        }
    }

def zte_usb(has_usb=True):
    details = {"USBDEV": {"dev": "usb1"}} if has_usb else {}
    return {
        "usb": {
            "name": "usb",
            "status": has_usb,
            "details": details
        }
    }

def zte_fibra(tx, rx):
    return {
        "fibra": {
            "name": "fibra",
            "status": True,
            "details": {
                "PON_OPTICALPARA": {
                    "TxPower": tx,
                    "RxPower": rx
                }
            }
        }
    }

def zte_fibra_none():
    return {
        "fibra": {
            "name": "fibra",
            "status": False,
            "details": {}
        }
    }

def zte_software_update(done=True):
    return {
        "software_update": {
            "name": "software_update",
            "status": done,
            "details": {
                "update_completed": done
            }
        }
    }

def zte_software_update_no_details():
    return {
        "software_update": {
            "name": "software_update",
            "status": True
        }
    }

def zte_potencia_wifi(raw_24=None, raw_5=None):
    return {
        "potencia_wifi": {
            "name": "potencia_wifi",
            "status": "PASS",
            "details": {
                "raw_24": raw_24 or [],
                "raw_5": raw_5 or [],
            }
        }
    }