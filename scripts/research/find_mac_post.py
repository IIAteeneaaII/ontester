#!/usr/bin/env python3
"""
Busca MAC usando métodos POST con sessionid
"""

import requests
import json

requests.packages.urllib3.disable_warnings()

host = "192.168.100.1"
ajax_url = f"http://{host}/cgi-bin/ajax"

# Obtener sessionid
print("[*] Obteniendo sessionid...")
r = requests.get(ajax_url, params={'ajaxmethod': 'get_refresh_sessionid', '_': '123'}, 
                 auth=('root','admin'), verify=False)
sessionid = r.json().get('sessionid')
print(f"[+] SessionID: {sessionid}\n")

# Métodos POST que pueden tener MAC
methods = [
    'get_lan_info',
    'get_wan_info',
    'get_eth_info',
    'get_lan_status',
    'get_wan_status',
    'get_network_info',
    'get_device_info',
    'get_system_info',
    'get_mac_address',
    'get_lan_mac',
    'get_wan_mac',
    'get_eth_mac'
]

print("=" * 80)
print("BÚSQUEDA DE MAC CON POST + SESSIONID")
print("=" * 80)

for method in methods:
    print(f"\n[*] Probando POST: {method}")
    
    data = {
        'ajaxmethod': method,
        'sessionid': sessionid
    }
    
    try:
        r = requests.post(
            ajax_url,
            data=data,
            auth=('root', 'admin'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            verify=False,
            timeout=5
        )
        
        if r.status_code == 200:
            try:
                result = r.json()
                print(f"    Status: 200 | session_valid: {result.get('session_valid', 'N/A')}")
                
                if result.get('session_valid') == 1:
                    print(f"    Keys: {', '.join(result.keys())}")
                    
                    # Buscar MAC
                    mac_keys = [k for k in result.keys() if 'mac' in k.lower() or 'addr' in k.lower()]
                    if mac_keys:
                        print(f"    >>> POSIBLE MAC:")
                        for key in mac_keys:
                            print(f"        {key}: {result[key]}")
                    
                    # Buscar patrón de MAC en valores
                    import re
                    for key, value in result.items():
                        if isinstance(value, str):
                            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                            if re.match(mac_pattern, value):
                                print(f"    >>> MAC ENCONTRADA: {key} = {value}")
                elif result.get('session_valid') == 0:
                    print(f"    Requiere login completo")
            except:
                print(f"    Status: 200 | Type: TEXT ({len(r.text)} bytes)")
        else:
            print(f"    Status: {r.status_code}")
    except Exception as e:
        print(f"    Error: {e}")

print("\n" + "=" * 80)
