#!/usr/bin/env python3
"""
Buscar el Serial Number real (48575443E0B2A5AA) en todos los métodos AJAX
"""

import requests
import json
from requests.auth import HTTPBasicAuth

host = "192.168.100.1"
ajax_url = f"http://{host}/cgi-bin/ajax"

# Deshabilitar warnings SSL
requests.packages.urllib3.disable_warnings()

# Métodos a probar
methods = [
    'get_device_name',
    'get_operator',
    'get_device_info',
    'get_system_info',
    'get_pon_info',
    'get_ont_info',
    'get_gpon_info',
    'get_epon_info',
    'get_hardware_info',
    'get_device_sn',
    'get_sn',
    'get_serial',
    'get_serial_number',
    'get_mac_sn',
    'get_factory_info'
]

print(f"\n[*] Buscando Serial Number: 48575443E0B2A5AA\n")

for method in methods:
    try:
        params = {
            'ajaxmethod': method,
            '_': '1234567890'
        }
        
        response = requests.get(
            ajax_url,
            params=params,
            auth=HTTPBasicAuth('root', 'admin'),
            timeout=5,
            verify=False
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                json_str = json.dumps(data, indent=2)
                
                # Buscar el SN en el JSON
                if '48575443E0B2A5AA' in json_str or '48575443E0B2A5AA' in str(data).upper():
                    print(f"[!!!] ENCONTRADO en {method}:")
                    print(json_str)
                    print()
                elif 'session_valid' in data and data['session_valid'] == 1:
                    print(f"[+] {method}: 200 OK (session_valid=1)")
                    print(f"    Keys: {list(data.keys())}")
                    
                    # Buscar cualquier campo que contenga "serial" o "sn"
                    for key, value in data.items():
                        if 'serial' in key.lower() or 'sn' in key.lower() or key.lower() in ['gponserial', 'ponserial', 'mac']:
                            print(f"    -> {key}: {value}")
                    print()
                elif data.get('sessionid'):
                    print(f"[~] {method}: 200 OK (session_valid=0, necesita login)")
            except:
                # No es JSON, buscar en texto plano
                if '48575443E0B2A5AA' in response.text or '48575443e0b2a5aa' in response.text.lower():
                    print(f"[!!!] ENCONTRADO en {method} (texto plano):")
                    print(response.text[:500])
                    print()
        elif response.status_code == 403:
            pass  # Silenciar 403
        else:
            print(f"[-] {method}: {response.status_code}")
    except Exception as e:
        pass

print("\n[*] Búsqueda completada")
