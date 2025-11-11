#!/usr/bin/env python3
"""
Descubridor de Endpoints ONT
Identifica endpoints accesibles y sus requisitos de autenticacion
"""

import requests
import argparse
from typing import Dict, List, Tuple

class EndpointDiscoverer:
    def __init__(self, host: str):
        self.host = host
        self.base_url = f"http://{host}"
        self.session = requests.Session()
        
    def test_endpoint(self, path: str, with_auth: bool = False) -> Tuple[int, int]:
        """Prueba un endpoint y retorna (status_code, content_length)"""
        headers = {
            'Host': self.host,
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/json',
            'Connection': 'keep-alive'
        }
        
        try:
            if with_auth:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    headers=headers,
                    auth=('root', 'admin'),
                    timeout=3
                )
            else:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    headers=headers,
                    timeout=3
                )
            return (response.status_code, len(response.content))
        except:
            return (0, 0)
    
    def discover_endpoints(self) -> Dict[str, List[Dict]]:
        """Descubre todos los endpoints relevantes"""
        
        endpoints_to_test = {
            "PON_INFO": [
                "/pon_link_info_inter.html",
                "/html/status/pon_info.html",
                "/html/pon_status_inter.html",
                "/status/pon.html",
                "/pon_status.html",
                "/optical_info.html",
                "/html/status/optical.html"
            ],
            "WIFI_24": [
                "/wifi_info_inter.html",
                "/html/status/wifi_info.html",
                "/html/wlan_inter.html",
                "/wlan_24g.html",
                "/wireless_24g.html",
                "/html/status/wireless.html"
            ],
            "WIFI_5": [
                "/wifi_info_inter5g.html",
                "/html/status/wifi_info_5g.html",
                "/wlan_5g.html",
                "/wireless_5g.html"
            ],
            "DEVICE_INFO": [
                "/get_device_name",
                "/device_info.html",
                "/html/status/device_info.html",
                "/system_info.html",
                "/html/status/system.html",
                "/html/device_inter.html"
            ],
            "USB_INFO": [
                "/usb_storage.html",
                "/usb_info.html",
                "/html/status/usb.html",
                "/storage_info.html"
            ],
            "RESET": [
                "/reset.html",
                "/factory_reset.html",
                "/html/admin/reset.html",
                "/admin_management_inter.html",
                "/system_reset.html"
            ],
            "VERSION": [
                "/version.html",
                "/html/status/version.html",
                "/firmware_info.html",
                "/software_version.html"
            ],
            "STATUS": [
                "/status.html",
                "/html/status.html",
                "/html/main.html",
                "/index.html"
            ]
        }
        
        results = {}
        
        for category, paths in endpoints_to_test.items():
            print(f"\n[*] Probando {category}...")
            category_results = []
            
            for path in paths:
                # Probar sin autenticacion
                status_no_auth, size_no_auth = self.test_endpoint(path, False)
                
                # Probar con autenticacion
                status_with_auth, size_with_auth = self.test_endpoint(path, True)
                
                if status_no_auth == 200 or status_with_auth == 200:
                    accessible = "SIN_AUTH" if status_no_auth == 200 else "CON_AUTH"
                    print(f"  [OK] {path} - {accessible} (size: {size_with_auth if status_with_auth == 200 else size_no_auth})")
                    category_results.append({
                        "path": path,
                        "accessible": accessible,
                        "status_no_auth": status_no_auth,
                        "status_with_auth": status_with_auth,
                        "size": size_with_auth if status_with_auth == 200 else size_no_auth
                    })
                elif status_no_auth == 401 or status_with_auth == 401:
                    print(f"  [AUTH] {path} - Requiere autenticacion")
                    category_results.append({
                        "path": path,
                        "accessible": "REQUIERE_AUTH",
                        "status_no_auth": status_no_auth,
                        "status_with_auth": status_with_auth
                    })
            
            results[category] = category_results
        
        return results
    
    def print_summary(self, results: Dict):
        """Imprime resumen de endpoints encontrados"""
        print("\n" + "="*60)
        print("RESUMEN DE ENDPOINTS ENCONTRADOS")
        print("="*60)
        
        for category, endpoints in results.items():
            accessible = [e for e in endpoints if e.get('accessible') in ['SIN_AUTH', 'CON_AUTH']]
            if accessible:
                print(f"\n{category}:")
                for endpoint in accessible:
                    print(f"  -> {endpoint['path']} [{endpoint['accessible']}]")

def main():
    parser = argparse.ArgumentParser(description="Descubre endpoints ONT")
    parser.add_argument("--host", required=True, help="IP de la ONT")
    args = parser.parse_args()
    
    discoverer = EndpointDiscoverer(args.host)
    results = discoverer.discover_endpoints()
    discoverer.print_summary(results)
    
    # Guardar resultados
    import json
    with open("discovered_endpoints.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[+] Resultados guardados en: discovered_endpoints.json")

if __name__ == "__main__":
    main()
