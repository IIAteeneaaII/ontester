#!/usr/bin/env python3
"""
Busca información de MAC address en métodos AJAX del ONT
"""

import requests
import json

requests.packages.urllib3.disable_warnings()

host = "192.168.100.1"
ajax_url = f"http://{host}/cgi-bin/ajax"

# Métodos potenciales que pueden contener MAC
methods = [
    'get_device_name',
    'get_operator',
    'get_device_info',
    'get_system_info',
    'get_lan_info',
    'get_wan_info',
    'get_network_info',
    'get_network_status',
    'get_eth_info',
    'get_mac_address',
    'get_mac_info'
]

print("=" * 80)
print("BÚSQUEDA DE MAC ADDRESS EN MÉTODOS AJAX")
print("=" * 80)

for method in methods:
    print(f"\n[*] Probando: {method}")
    
    try:
        r = requests.get(
            ajax_url,
            params={'ajaxmethod': method, '_': '123'},
            auth=('root', 'admin'),
            verify=False,
            timeout=5
        )
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"    Status: 200 | Type: JSON")
                print(f"    Keys: {', '.join(data.keys())}")
                
                # Buscar cualquier key que contenga 'mac'
                mac_keys = [k for k in data.keys() if 'mac' in k.lower() or 'addr' in k.lower()]
                if mac_keys:
                    print(f"    >>> POSIBLE MAC: {mac_keys}")
                    for key in mac_keys:
                        print(f"        {key}: {data[key]}")
                
                # Buscar en valores también
                for key, value in data.items():
                    if isinstance(value, str) and ':' in value:
                        # Patrón típico de MAC: XX:XX:XX:XX:XX:XX
                        parts = value.split(':')
                        if len(parts) == 6 and all(len(p) == 2 for p in parts):
                            print(f"    >>> MAC ENCONTRADA: {key} = {value}")
            except:
                print(f"    Status: 200 | Type: TEXT")
                # Buscar patrón de MAC en texto
                import re
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                matches = re.findall(mac_pattern, r.text)
                if matches:
                    print(f"    >>> MAC en texto: {[''.join(m) for m in matches]}")
        else:
            print(f"    Status: {r.status_code}")
    except Exception as e:
        print(f"    Error: {e}")

print("\n" + "=" * 80)
