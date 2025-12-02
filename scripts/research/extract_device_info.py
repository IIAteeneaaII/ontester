#!/usr/bin/env python3
"""
Extraer Device Information de la interfaz web
"""

import requests
from bs4 import BeautifulSoup

host = "192.168.100.1"
url = f"http://{host}/html/main_inter.html"

requests.packages.urllib3.disable_warnings()

print("[*] Obteniendo Device Information...\n")

response = requests.get(url, auth=('root', 'admin'), verify=False, timeout=10)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("="*60)
    print("DEVICE INFORMATION")
    print("="*60 + "\n")
    
    device_info = {}
    
    # Buscar todas las tablas
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                
                if key and value and key != value:
                    device_info[key] = value
                    print(f"{key:<25} : {value}")
    
    # Analizar SN físico
    if 'OLT Vendor ID' in device_info and 'MAC Address' in device_info:
        print("\n" + "="*60)
        print("CONSTRUCCIÓN SN FÍSICO")
        print("="*60 + "\n")
        
        olt_vendor = device_info['OLT Vendor ID']
        mac = device_info['MAC Address']
        
        # Convertir OLT Vendor a HEX
        olt_hex = ''.join([format(ord(c), '02X') for c in olt_vendor])
        print(f"OLT Vendor: {olt_vendor} -> HEX: {olt_hex}")
        
        # MAC sin separadores
        mac_hex = mac.replace(':', '').upper()
        print(f"MAC Address: {mac} -> HEX: {mac_hex}")
        
        # Últimos 4 bytes (8 chars) de MAC
        mac_suffix = mac_hex[-8:]
        print(f"Últimos 4 bytes MAC: {mac_suffix}")
        
        # Construir SN físico
        sn_physical = f"{olt_hex}{mac_suffix}"
        print(f"\nSN Físico construido: {sn_physical}")
        print(f"SN Físico esperado:   48575443E0B2A5AA")
        
        if sn_physical == "48575443E0B2A5AA":
            print("\n✅ ¡FÓRMULA CORRECTA!")
            print("   SN_Físico = OLT_Vendor_ID(HEX) + Últimos_4_bytes_MAC")
        else:
            print(f"\n❌ No coincide")
            
else:
    print(f"[!] Error: {response.status_code}")
