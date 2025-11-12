#!/usr/bin/env python3
"""
Script de diagnóstico para verificar qué dispositivo está conectado
"""

import requests
import json

requests.packages.urllib3.disable_warnings()

def check_device(host):
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO DE DISPOSITIVO EN {host}")
    print('='*80)
    
    # 1. Verificar página principal
    print("\n[*] Verificando página principal...")
    try:
        response = requests.get(f"http://{host}", timeout=3, verify=False)
        print(f"    Status: {response.status_code}")
        print(f"    Server: {response.headers.get('Server', 'N/A')}")
        print(f"    Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        html_lower = response.text.lower()
        if 'grandstream' in html_lower:
            print("    [!] Detectado: GRANDSTREAM en HTML")
        if 'ht818' in html_lower:
            print("    [!] Detectado: HT818 en HTML")
        if 'fiberhome' in html_lower:
            print("    [!] Detectado: FIBERHOME en HTML")
        if 'huawei' in html_lower:
            print("    [!] Detectado: HUAWEI en HTML")
            
    except Exception as e:
        print(f"    Error: {e}")
    
    # 2. Verificar AJAX get_device_name
    print("\n[*] Verificando AJAX get_device_name...")
    try:
        response = requests.get(
            f"http://{host}/cgi-bin/ajax",
            params={'ajaxmethod': 'get_device_name'},
            auth=('root', 'admin'),
            timeout=3,
            verify=False
        )
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"    Respuesta: {json.dumps(data, indent=2)}")
            if 'ModelName' in data:
                print(f"    [!] ModelName detectado: {data['ModelName']}")
    except Exception as e:
        print(f"    Error: {e}")
    
    # 3. Verificar AJAX get_operator
    print("\n[*] Verificando AJAX get_operator...")
    try:
        response = requests.get(
            f"http://{host}/cgi-bin/ajax",
            params={'ajaxmethod': 'get_operator'},
            auth=('root', 'admin'),
            timeout=3,
            verify=False
        )
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"    Respuesta: {json.dumps(data, indent=2)}")
            if 'SerialNumber' in data:
                print(f"    [!] Serial detectado: {data['SerialNumber']}")
    except Exception as e:
        print(f"    Error: {e}")
    
    # 4. Conclusión
    print("\n" + "="*80)
    print("CONCLUSIÓN")
    print("="*80)
    print("\nSi ves 'ModelName: HG6145F1' → Es un ONT Fiberhome (MOD001)")
    print("Si ves 'grandstream' o 'ht818' en HTML → Es un Grandstream HT818 (MOD006)")
    print("Si el AJAX no funciona pero HTTP sí → Probablemente es HT818\n")

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.100.1"
    check_device(host)
