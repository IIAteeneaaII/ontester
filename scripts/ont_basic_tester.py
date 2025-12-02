#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONT Network Tester - Herramienta de diagnóstico sin dependencia de SSH/Telnet
Utiliza sockets y protocolos de red básicos para obtener información
"""

import sys
import time
import json
import socket
import struct
import argparse
from typing import Dict, List, Any
import concurrent.futures

class ONTBasicTester:
    def __init__(self, target_ip: str):
        self.target_ip = target_ip
        self.results: Dict[str, Any] = {
            "target_ip": target_ip,
            "timestamp": int(time.time()),
            "tests": {}
        }

    def test_basic_connectivity(self) -> Dict[str, Any]:
        """Prueba conectividad básica"""
        results = {}
        
        # Prueba de ping básica usando socket
        try:
            start_time = time.time()
            socket.create_connection((self.target_ip, 80), timeout=2)
            end_time = time.time()
            results["connectivity"] = {
                "status": "success",
                "latency_ms": round((end_time - start_time) * 1000, 2)
            }
        except Exception as e:
            results["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }

        # Intenta obtener el hostname
        try:
            hostname = socket.gethostbyaddr(self.target_ip)[0]
            results["hostname"] = hostname
        except Exception:
            results["hostname"] = "unknown"

        return results

    def scan_port(self, port: int) -> Dict[str, Any]:
        """Escanea un puerto específico"""
        result = {
            "port": port,
            "state": "closed",
            "service": self.get_common_service_name(port),
            "latency_ms": None
        }
        
        try:
            start_time = time.time()
            with socket.create_connection((self.target_ip, port), timeout=1) as sock:
                end_time = time.time()
                result["state"] = "open"
                result["latency_ms"] = round((end_time - start_time) * 1000, 2)
                
                # Para puertos HTTP, intenta obtener el banner
                if port in [80, 443, 8080, 8443]:
                    try:
                        sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                        banner = sock.recv(1024).decode('utf-8', errors='ignore').split('\r\n')[0]
                        result["banner"] = banner
                    except:
                        pass
                
        except (socket.timeout, ConnectionRefusedError):
            pass
        except Exception as e:
            result["error"] = str(e)
            
        return result

    def scan_common_ports(self) -> Dict[str, List[Dict[str, Any]]]:
        """Escanea puertos comunes de manera segura y paralela"""
        common_ports = [
            21,    # FTP
            22,    # SSH
            23,    # Telnet
            53,    # DNS
            80,    # HTTP
            443,   # HTTPS
            8080,  # HTTP Alternate
            8443,  # HTTPS Alternate
            161,   # SNMP
            162,   # SNMP Trap
            1900,  # UPNP
            5000,  # UPnP
            49152  # UPnP
        ]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_port = {executor.submit(self.scan_port, port): port for port in common_ports}
            for future in concurrent.futures.as_completed(future_to_port):
                try:
                    result = future.result()
                    if result["state"] == "open" or "error" in result:
                        results.append(result)
                except Exception as e:
                    port = future_to_port[future]
                    results.append({
                        "port": port,
                        "state": "error",
                        "error": str(e)
                    })
        
        return {
            "scanned_ports": len(common_ports),
            "open_ports": len([r for r in results if r["state"] == "open"]),
            "results": sorted(results, key=lambda x: x["port"])
        }

    @staticmethod
    def get_common_service_name(port: int) -> str:
        """Retorna el nombre común del servicio para un puerto"""
        services = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            53: "DNS",
            80: "HTTP",
            443: "HTTPS",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
            161: "SNMP",
            162: "SNMP-Trap",
            1900: "UPnP",
            5000: "UPnP-Alt",
            49152: "UPnP-Alt"
        }
        return services.get(port, "Unknown")

    def test_http_info(self) -> Dict[str, Any]:
        """Intenta obtener información básica vía HTTP"""
        results = {}
        
        for port in [80, 443, 8080, 8443]:
            try:
                if port in [443, 8443]:
                    continue  # Skip HTTPS for now
                    
                sock = socket.create_connection((self.target_ip, port), timeout=2)
                sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                response = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()
                
                headers = response.split('\r\n')
                results[f"port_{port}"] = {
                    "status": "success",
                    "response": headers[0] if headers else "No response",
                    "server": next((h for h in headers if h.lower().startswith('server:')), "Unknown")
                }
                
            except Exception as e:
                results[f"port_{port}"] = {
                    "status": "failed",
                    "error": str(e)
                }
                
        return results

    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todas las pruebas disponibles"""
        self.results["tests"]["basic_connectivity"] = self.test_basic_connectivity()
        self.results["tests"]["ports"] = self.scan_common_ports()
        self.results["tests"]["http_info"] = self.test_http_info()
        
        return self.results

def main():
    parser = argparse.ArgumentParser(description='ONT Basic Network Tester')
    parser.add_argument('--host', required=True, help='IP del dispositivo objetivo')
    args = parser.parse_args()

    tester = ONTBasicTester(args.host)
    results = tester.run_all_tests()
    
    print(json.dumps(results, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())