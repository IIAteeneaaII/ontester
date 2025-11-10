#!/usr/bin/env python3
"""
Prueba login completo en ONT via AJAX do_login
"""

import requests
import json
import base64
import hashlib

requests.packages.urllib3.disable_warnings()

host = "192.168.100.1"
ajax_url = f"http://{host}/cgi-bin/ajax"

username = "root"
password = "admin"

print("[*] Iniciando proceso de login...")
print(f"[*] Usuario: {username}\n")

# Paso 1: Obtener sessionid
print("[1] Obteniendo sessionid...")
r = requests.get(ajax_url, params={'ajaxmethod': 'get_refresh_sessionid', '_': '123'}, 
                 auth=(username, password), verify=False)
session_data = r.json()
sessionid = session_data.get('sessionid')
print(f"[+] SessionID: {sessionid}\n")

# Paso 2: Intentar login con diferentes encriptaciones
encryption_methods = {
    "plaintext": password,
    "base64": base64.b64encode(password.encode()).decode(),
    "md5": hashlib.md5(password.encode()).hexdigest(),
    "sha256": hashlib.sha256(password.encode()).hexdigest(),
}

for method, encrypted_pwd in encryption_methods.items():
    print(f"[2] Intentando login con password {method}: {encrypted_pwd[:50]}...")
    
    data = {
        'ajaxmethod': 'do_login',
        'username': username,
        'loginpd': encrypted_pwd,
        'port': '0',
        'sessionid': sessionid
    }
    
    try:
        r = requests.post(ajax_url, data=data, auth=(username, password),
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         verify=False, timeout=5)
        
        if r.status_code == 200:
            result = r.json()
            print(f"    Status: {r.status_code}")
            print(f"    Response: {json.dumps(result, indent=6)}")
            
            if result.get('ret') == 0 or result.get('success') or result.get('login_result') == 'success':
                print(f"\n[+] ¡LOGIN EXITOSO con {method}!\n")
                break
        else:
            print(f"    Status: {r.status_code}\n")
    except Exception as e:
        print(f"    Error: {e}\n")

print("=" * 80)
