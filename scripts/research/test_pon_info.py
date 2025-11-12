#!/usr/bin/env python3
"""
Script rápido para probar el método get_pon_info
"""

import requests
import json
from datetime import datetime

requests.packages.urllib3.disable_warnings()

def test_pon_info(host='192.168.100.1'):
    ajax_url = f"http://{host}/cgi-bin/ajax"
    
    # Primero obtener sessionid
    print("[*] Obteniendo sessionid...")
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
            print(f"[+] SessionID: {sessionid}\n")
            
            # Ahora probar get_pon_info con sessionid
            print("[*] Consultando get_pon_info...")
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
            
            print(f"Status Code: {response.status_code}\n")
            
            if response.status_code == 200:
                pon_data = response.json()
                print("="*60)
                print("INFORMACIÓN PON")
                print("="*60)
                print(json.dumps(pon_data, indent=2, ensure_ascii=False))
                print("="*60)
                
                # Guardar resultado
                output = {
                    "timestamp": datetime.now().isoformat(),
                    "method": "get_pon_info",
                    "data": pon_data
                }
                
                with open('pon_info_result.json', 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                
                print("\n[+] Resultado guardado en: pon_info_result.json")
                
            else:
                print(f"[-] Error: {response.text}")
                
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    test_pon_info()
