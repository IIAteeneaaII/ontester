#!/usr/bin/env python3
"""
Script para obtener información PON real con autenticación completa
"""

import requests
import json
import hashlib
from datetime import datetime

requests.packages.urllib3.disable_warnings()

def get_password_hash(password):
    """Genera el hash de la contraseña como lo hace el ONT"""
    return hashlib.md5(password.encode()).hexdigest()

def login_ont(host='192.168.100.1', username='root', password='admin'):
    """Realiza login en el ONT y obtiene sessionid válido"""
    print("[*] Intentando login en el ONT...")
    
    login_url = f"http://{host}/cgi-bin/login"
    
    # El ONT usa hash MD5 de la contraseña
    password_hash = get_password_hash(password)
    
    login_data = {
        'user': username,
        'password': password_hash,
        'login': 'Login'
    }
    
    try:
        session = requests.Session()
        
        # Hacer login
        response = session.post(
            login_url,
            data=login_data,
            timeout=5,
            verify=False,
            allow_redirects=False
        )
        
        print(f"Login Status: {response.status_code}")
        
        # Obtener sessionid de las cookies
        cookies = session.cookies.get_dict()
        print(f"Cookies: {cookies}")
        
        return session
        
    except Exception as e:
        print(f"[-] Error en login: {e}")
        return None

def get_pon_info_authenticated(host='192.168.100.1'):
    """Obtiene información PON con sesión autenticada"""
    
    # Intentar con autenticación HTTP básica primero
    print("\n" + "="*60)
    print("MÉTODO 1: HTTP Basic Auth + SessionID")
    print("="*60)
    
    ajax_url = f"http://{host}/cgi-bin/ajax"
    
    # Obtener sessionid
    params = {
        'ajaxmethod': 'get_refresh_sessionid',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    try:
        response = requests.get(
            ajax_url,
            params=params,
            auth=('root', 'admin'),
            timeout=5,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            sessionid = data.get('sessionid')
            print(f"[+] SessionID obtenido: {sessionid}")
            
            # Probar get_pon_info
            params = {
                'ajaxmethod': 'get_pon_info',
                'sessionid': sessionid,
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            response = requests.get(
                ajax_url,
                params=params,
                auth=('root', 'admin'),
                timeout=5,
                verify=False
            )
            
            print(f"\n[*] get_pon_info - Status: {response.status_code}")
            pon_data = response.json()
            print(json.dumps(pon_data, indent=2, ensure_ascii=False))
            
            if pon_data.get('session_valid') == 0:
                print("\n[!] Session no válida. Probando método alternativo...")
                
                # MÉTODO 2: Probar otros métodos que sí funcionan para comparar
                print("\n" + "="*60)
                print("MÉTODO 2: Comparando con otros métodos accesibles")
                print("="*60)
                
                test_methods = [
                    'get_device_name',
                    'get_operator',
                    'get_pon_info',
                    'get_wifi_status',
                    'get_usb_info'
                ]
                
                results = {}
                
                for method in test_methods:
                    params = {
                        'ajaxmethod': method,
                        'sessionid': sessionid,
                        '_': str(int(datetime.now().timestamp() * 1000))
                    }
                    
                    response = requests.get(
                        ajax_url,
                        params=params,
                        auth=('root', 'admin'),
                        timeout=5,
                        verify=False
                    )
                    
                    data = response.json()
                    results[method] = data
                    
                    print(f"\n[*] {method}:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Guardar resultados comparativos
                output = {
                    "timestamp": datetime.now().isoformat(),
                    "host": host,
                    "note": "Comparación de métodos AJAX con mismo sessionid",
                    "sessionid": sessionid,
                    "methods": results
                }
                
                filename = f"pon_info_comparison_{datetime.now().strftime('%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                
                print(f"\n[+] Resultados guardados en: {filename}")
                
                # Análisis
                print("\n" + "="*60)
                print("ANÁLISIS")
                print("="*60)
                
                for method, data in results.items():
                    session_valid = data.get('session_valid', 'N/A')
                    has_data = len(data.keys()) > 2  # Más que sessionid y session_valid
                    
                    print(f"\n{method}:")
                    print(f"  - session_valid: {session_valid}")
                    print(f"  - Tiene datos adicionales: {has_data}")
                    print(f"  - Campos: {list(data.keys())}")
                
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_pon_info_authenticated()
