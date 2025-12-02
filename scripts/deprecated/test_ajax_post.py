#!/usr/bin/env python3
"""
Prueba métodos AJAX con POST y sessionid
"""

import requests
import json

requests.packages.urllib3.disable_warnings()

host = "192.168.100.1"
ajax_url = f"http://{host}/cgi-bin/ajax"

# Primero obtener sessionid
print("[*] Obteniendo sessionid...")
r = requests.get(ajax_url, params={'ajaxmethod': 'get_refresh_sessionid', '_': '123'}, 
                 auth=('root','admin'), verify=False)
session_data = r.json()
sessionid = session_data.get('sessionid')
print(f"[+] SessionID: {sessionid}\n")

# Métodos que requieren POST con sessionid
methods = [
    'get_pon_info',
    'get_wifi_status',
    'get_usb_info',
    'get_device_info',
    'get_system_info'
]

print("=" * 80)
print("RESULTADOS DE MÉTODOS AJAX (POST)")
print("=" * 80)

for method in methods:
    print(f"\n[*] Método: {method}")
    print("-" * 80)
    
    data = {
        'ajaxmethod': method,
        'sessionid': sessionid
    }
    
    try:
        r = requests.post(ajax_url, data=data, auth=('root','admin'), 
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         verify=False, timeout=5)
        
        if r.status_code == 200:
            try:
                result = r.json()
                print(json.dumps(result, indent=2))
            except:
                print(f"Text response: {r.text[:500]}")
        else:
            print(f"Status: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 80)
