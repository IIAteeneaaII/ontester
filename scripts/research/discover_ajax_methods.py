#!/usr/bin/env python3
"""
Descubre todos los métodos AJAX disponibles en el ONT
"""

import requests
import json
import argparse
from datetime import datetime

requests.packages.urllib3.disable_warnings()

def test_ajax_method(host: str, method: str, params: dict = None) -> dict:
    """Prueba un método AJAX específico"""
    ajax_url = f"http://{host}/cgi-bin/ajax"
    
    params = params or {}
    params['ajaxmethod'] = method
    params['_'] = str(datetime.now().timestamp())
    
    try:
        response = requests.get(
            ajax_url,
            params=params,
            auth=('root', 'admin'),
            timeout=5,
            verify=False
        )
        
        result = {
            "method": method,
            "status": response.status_code,
            "accessible": response.status_code == 200
        }
        
        if response.status_code == 200:
            try:
                result["data"] = response.json()
                result["type"] = "json"
            except:
                result["data"] = response.text[:500]
                result["type"] = "text"
        else:
            result["error"] = response.text[:200]
        
        return result
    
    except Exception as e:
        return {
            "method": method,
            "status": 0,
            "accessible": False,
            "error": str(e)
        }

def test_common_methods(host: str):
    """Prueba métodos AJAX comunes"""
    
    print(f"\n[*] Probando métodos AJAX en {host}/cgi-bin/ajax\n")
    
    # Métodos encontrados en JS
    known_methods = [
        "get_device_name",
        "get_operator",
        "get_heartbeat",
        "get_refresh_sessionid",
    ]
    
    # Métodos comunes basados en patrones de ONTs Huawei
    common_methods = [
        # Información del sistema
        "get_system_info",
        "get_device_info",
        "get_device_status",
        "get_hardware_version",
        "get_software_version",
        "get_sysinfo",
        
        # PON/Óptica
        "get_pon_info",
        "get_pon_status",
        "get_optical_info",
        "get_optical_status",
        "get_pon_link_info",
        "get_poninfo",
        "get_optical_power",
        
        # WiFi
        "get_wlan_info",
        "get_wlan_status",
        "get_wlan_basic",
        "get_wifi_info",
        "get_wifi_status",
        "get_wlan_24g",
        "get_wlan_5g",
        "get_wireless_info",
        
        # Network
        "get_lan_info",
        "get_wan_info",
        "get_network_status",
        "get_dhcp_info",
        "get_ip_info",
        "get_net_info",
        
        # USB
        "get_usb_info",
        "get_usb_status",
        "get_storage_info",
        
        # Management
        "get_user_info",
        "get_login_info",
        "get_session_info",
        
        # Status general
        "get_status",
        "get_config",
        "get_statistics",
        "get_all_info",
        
        # Diagnóstico
        "get_diagnostic_info",
        "get_log_info"
    ]
    
    all_methods = known_methods + common_methods
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "host": host,
        "total_tested": len(all_methods),
        "accessible": [],
        "not_accessible": []
    }
    
    for i, method in enumerate(all_methods, 1):
        print(f"\r[{i}/{len(all_methods)}] Probando: {method:<40}", end='', flush=True)
        
        result = test_ajax_method(host, method)
        
        if result["accessible"]:
            results["accessible"].append(result)
        else:
            results["not_accessible"].append(result)
    
    print("\n")
    return results

def print_results(results: dict):
    """Imprime resultados"""
    
    print("=" * 80)
    print("MÉTODOS AJAX DESCUBIERTOS")
    print("=" * 80)
    print(f"Host: {results['host']}")
    print(f"Total probados: {results['total_tested']}")
    print(f"Accesibles: {len(results['accessible'])}")
    print(f"No accesibles: {len(results['not_accessible'])}")
    
    if results['accessible']:
        print("\n" + "-" * 80)
        print("MÉTODOS ACCESIBLES:")
        print("-" * 80)
        
        for item in results['accessible']:
            print(f"\n[OK] {item['method']}")
            print(f"     Status: {item['status']} | Type: {item.get('type', 'unknown')}")
            
            if item.get('data'):
                data = item['data']
                if isinstance(data, dict):
                    print(f"     Keys: {', '.join(data.keys())}")
                    # Mostrar algunos valores importantes
                    for key in ['ModelName', 'SerialNumber', 'HardwareVersion', 
                               'SoftwareVersion', 'operator_name', 'sessionid']:
                        if key in data:
                            value = str(data[key])
                            if len(value) > 50:
                                value = value[:50] + "..."
                            print(f"       - {key}: {value}")
                else:
                    print(f"     Data: {data[:100]}")
    
    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Descubre métodos AJAX del ONT')
    parser.add_argument('--host', required=True, help='IP del ONT')
    parser.add_argument('--output', help='Archivo de salida JSON')
    
    args = parser.parse_args()
    
    results = test_common_methods(args.host)
    print_results(results)
    
    # Guardar resultados
    output_file = args.output or "ajax_methods_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[+] Resultados guardados en: {output_file}\n")

if __name__ == "__main__":
    main()
