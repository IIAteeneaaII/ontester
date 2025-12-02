#!/usr/bin/env python3
"""
Extraer información completa del ONT MOD001
"""

import requests
from bs4 import BeautifulSoup

host = "192.168.100.1"

# URLs a probar para Device Information
urls_to_try = [
    f"http://{host}/html/status/status_dev_info.html",
    f"http://{host}/html/main_inter.html",
    f"http://{host}/status/device_info.html",
    f"http://{host}/device_info.html",
    f"http://{host}/html/status/dev_info.html"
]

requests.packages.urllib3.disable_warnings()

print("\n[*] Buscando página Device Information...\n")

device_info = {}

for url in urls_to_try:
    try:
        print(f"Probando: {url}")
        r = requests.get(url, auth=('root', 'admin'), verify=False, timeout=5)
        
        if r.status_code == 200 and len(r.text) > 500:
            print(f"  ✓ Encontrada (Status: {r.status_code}, Size: {len(r.text)} bytes)")
            soup = BeautifulSoup(r.text, 'html.parser')
            """ PRUEBAS TODO """
            headers = {'Authorization': 'root admin'}
            r2 = requests.get(url, headers=headers, verify=False, timeout=10)
            print("\n", r.url)
            print("\n", soup)
            """ fin pruebas """
            tables = soup.find_all('table')
            
            if tables:
                print(f"  ✓ Tablas encontradas: {len(tables)}\n")
                
                print("="*60)
                print("DEVICE INFORMATION - MOD001")
                print("="*60)
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        if len(cols) >= 2 and cols[0] and cols[1] and cols[0] != cols[1]:
                            key = cols[0]
                            value = cols[1]
                            device_info[key] = value
                            print(f"{key:<25} : {value}")
                
                if device_info:
                    break
        else:
            print(f"  ✗ No encontrada (Status: {r.status_code})")
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:50]}")

if not device_info:
    print("\n[!] No se pudo acceder a Device Information via HTML")
    print("[*] Intentando via AJAX...\n")
    
    # Obtener info via AJAX
    ajax_methods = ['get_device_name', 'get_operator', 'get_heartbeat']
    
    print("="*60)
    print("INFORMACIÓN VIA AJAX")
    print("="*60)
    
    for method in ajax_methods:
        try:
            r = requests.get(
                f"http://{host}/cgi-bin/ajax",
                params={'ajaxmethod': method, '_': '123'},
                auth=('root', 'admin'),
                verify=False,
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\n{method}:")
                for key, value in data.items():
                    if key not in ['sessionid', 'session_valid']:
                        print(f"  {key:<23} : {value}")
                        device_info[key] = value
        except:
            pass

print("\n" + "="*60)
print("INFORMACIÓN NECESARIA PARA SN FÍSICO")
print("="*60)
print(f"\n1. Serial Number (Lógico): {device_info.get('SerialNumber', 'N/A')}")
print(f"2. OLT Vendor ID:          {device_info.get('OLT Vendor ID', 'N/A')}")
print(f"3. MAC Address:            {device_info.get('MAC Address', 'N/A')}")
print(f"4. Model Name:             {device_info.get('ModelName', 'N/A')}")

print("\n[!] IMPORTANTE: Necesitamos también:")
print("    - Serial Number FÍSICO de la etiqueta del dispositivo")
print("    - Formato: 16 caracteres hexadecimales (ej: 48575443E0B2A5AA)")
