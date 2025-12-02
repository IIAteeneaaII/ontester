#!/usr/bin/env python3
"""
Script de descubrimiento exhaustivo de endpoints HTTP en ONT
Prueba endpoints comunes de diferentes fabricantes (Huawei, ZTE, Fiberhome)
"""

import requests
import json
from typing import Dict, List
from datetime import datetime
import argparse
import sys

# Deshabilitar warnings SSL
requests.packages.urllib3.disable_warnings()

def make_request(base_url: str, endpoint: str, auth: tuple) -> Dict:
    """Realiza request HTTP con autenticacion"""
    url = f"{base_url}{endpoint}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(
            url,
            auth=auth,
            headers=headers,
            timeout=5,
            verify=False,
            allow_redirects=True
        )
        
        return {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "accessible": response.status_code == 200,
            "content_length": len(response.text),
            "has_html": "<html" in response.text.lower(),
            "has_json": response.headers.get('Content-Type', '').startswith('application/json'),
            "url": response.url
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status_code": 0,
            "accessible": False,
            "error": str(e)
        }

def discover_endpoints(host: str, username: str = "root", password: str = "admin") -> Dict:
    """Descubre endpoints accesibles en el ONT"""
    
    base_url = f"http://{host}"
    auth = (username, password)
    
    # Lista exhaustiva de endpoints comunes en ONTs
    endpoints = [
        # Páginas principales
        "/",
        "/index.html",
        "/main.html",
        "/home.html",
        "/login.html",
        
        # Status general
        "/html/status.html",
        "/status.html",
        "/html/status/status.html",
        
        # Información PON y óptica
        "/html/status/pon_info.html",
        "/pon_link_info_inter.html",
        "/html/pon_status_inter.html",
        "/status/pon.html",
        "/pon_status.html",
        "/optical_info.html",
        "/pon_info.html",
        "/gpon_status.html",
        "/epon_status.html",
        
        # WiFi / WLAN
        "/html/bbsp/wlan/wlan.html",
        "/html/wlan/wlan.html",
        "/html/wlan/wlan_5g.html",
        "/wifi_info_inter.html",
        "/wifi_info_inter5g.html",
        "/wlan_24g.html",
        "/wlan_5g.html",
        "/wireless_24g.html",
        "/wireless_5g.html",
        "/wireless_settings.html",
        "/network/wifi.html",
        "/network/wifi_5g.html",
        "/html/wlbasic.html",
        "/wlan.html",
        "/wlan/basic.html",
        
        # Información del dispositivo
        "/get_device_name",
        "/version.html",
        "/system_info.html",
        "/device_info.html",
        "/html/status/device_info.html",
        "/html/deviceinfo.html",
        "/info.html",
        
        # USB
        "/usb_inter.html",
        "/usb_status.html",
        "/html/usb/usb.html",
        "/storage.html",
        
        # Reset / Reboot
        "/html/main/reboot.html",
        "/system_reboot.html",
        "/reboot.html",
        "/html/syscmd.html",
        
        # Network
        "/html/status/lan_info.html",
        "/html/status/wan_info.html",
        "/network_status.html",
        "/lan.html",
        "/wan.html",
        
        # Management
        "/html/management.html",
        "/management.html",
        "/system.html",
        "/admin.html",
        
        # Advanced
        "/html/advanced.html",
        "/advanced.html",
        
        # API endpoints
        "/api/system/info",
        "/api/device/info",
        "/api/pon/status",
        "/api/wifi/status",
        
        # Huawei specific
        "/html/ssmp/wlanbasic/wlanbasic.html",
        "/html/ssmp/poninfo/poninfo.html",
        "/html/ssmp/deviceinfo/deviceinfo.html",
        
        # ZTE specific
        "/getpage.gch?pid=1002",
        "/getpage.gch?pid=1001",
        
        # Fiberhome specific
        "/ponstatusinfo.html",
        "/wlansetting.html"
    ]
    
    print(f"\n[*] Iniciando descubrimiento en {host}")
    print(f"[*] Autenticacion: {username}:{password}")
    print(f"[*] Total endpoints a probar: {len(endpoints)}\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "host": host,
        "total_tested": len(endpoints),
        "accessible": [],
        "not_accessible": [],
        "errors": []
    }
    
    # Probar cada endpoint
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\r[{i}/{len(endpoints)}] Probando endpoints...", end='', flush=True)
        
        result = make_request(base_url, endpoint, auth)
        
        if result["accessible"]:
            results["accessible"].append(result)
        elif "error" in result:
            results["errors"].append(result)
        else:
            results["not_accessible"].append(result)
    
    print("\n")
    return results

def print_results(results: Dict):
    """Imprime resultados del descubrimiento"""
    
    print("=" * 80)
    print("RESULTADOS DEL DESCUBRIMIENTO DE ENDPOINTS")
    print("=" * 80)
    print(f"Host: {results['host']}")
    print(f"Fecha: {results['timestamp']}")
    print(f"Total probados: {results['total_tested']}")
    print(f"\nACCESIBLES: {len(results['accessible'])}")
    print(f"NO ACCESIBLES: {len(results['not_accessible'])}")
    print(f"ERRORES: {len(results['errors'])}")
    
    if results['accessible']:
        print("\n" + "-" * 80)
        print("ENDPOINTS ACCESIBLES:")
        print("-" * 80)
        
        for item in sorted(results['accessible'], key=lambda x: x['endpoint']):
            content_type = "HTML" if item.get('has_html') else "JSON" if item.get('has_json') else "OTHER"
            print(f"[OK] {item['endpoint']}")
            print(f"     Status: {item['status_code']} | Size: {item['content_length']} bytes | Type: {content_type}")
            if item.get('url') != f"http://{results['host']}{item['endpoint']}":
                print(f"     Redirected to: {item.get('url')}")
            print()
    
    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Descubre endpoints accesibles en ONT')
    parser.add_argument('--host', required=True, help='IP del ONT')
    parser.add_argument('--user', default='root', help='Usuario (default: root)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    parser.add_argument('--output', help='Archivo de salida JSON')
    
    args = parser.parse_args()
    
    # Descubrir endpoints
    results = discover_endpoints(args.host, args.user, args.password)
    
    # Mostrar resultados
    print_results(results)
    
    # Guardar a archivo
    output_file = args.output or "discovered_endpoints_full.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[+] Resultados guardados en: {output_file}")
    
    return 0 if results['accessible'] else 1

if __name__ == "__main__":
    sys.exit(main())
