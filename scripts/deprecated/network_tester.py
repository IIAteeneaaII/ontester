#!/usr/bin/env python3
"""
Tests de conectividad de red para ONT
RF 002: Prueba Ethernet
RF 003: Prueba de conectividad
"""

import socket
import subprocess
import platform
import re
from typing import Dict, Any
import requests

class NetworkTester:
    def __init__(self, host: str):
        self.host = host
        self.is_windows = platform.system() == "Windows"
    
    def test_ping(self, target: str = None, count: int = 4) -> Dict[str, Any]:
        """Test de ping básico"""
        target = target or self.host
        
        result = {
            "target": target,
            "reachable": False,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_pct": 100.0,
            "avg_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None
        }
        
        try:
            # Comando ping según OS
            param = "-n" if self.is_windows else "-c"
            timeout_param = "-w" if self.is_windows else "-W"
            
            cmd = ["ping", param, str(count), timeout_param, "2000", target]
            
            output = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if output.returncode == 0:
                result["reachable"] = True
                
                # Parsear resultados (Windows)
                if self.is_windows:
                    # Packets: "Paquetes: enviados = 4, recibidos = 4, perdidos = 0"
                    packets_match = re.search(r'recibidos = (\d+)', output.stdout)
                    if packets_match:
                        result["packets_received"] = int(packets_match.group(1))
                        result["packet_loss_pct"] = ((count - result["packets_received"]) / count) * 100
                    
                    # Latency: "Mínimo = 1ms, Máximo = 2ms, Media = 1ms"
                    latency_match = re.search(r'M.nimo = (\d+)ms.*M.ximo = (\d+)ms.*Media = (\d+)ms', output.stdout)
                    if latency_match:
                        result["min_latency_ms"] = int(latency_match.group(1))
                        result["max_latency_ms"] = int(latency_match.group(2))
                        result["avg_latency_ms"] = int(latency_match.group(3))
                    
                    # Fallback: buscar "tiempo=" o "time="
                    if not latency_match:
                        times = re.findall(r'tiempo[=<](\d+)ms|time[=<](\d+)ms', output.stdout, re.IGNORECASE)
                        if times:
                            latencies = [int(t[0] or t[1]) for t in times]
                            result["min_latency_ms"] = min(latencies)
                            result["max_latency_ms"] = max(latencies)
                            result["avg_latency_ms"] = sum(latencies) // len(latencies)
                
        except subprocess.TimeoutExpired:
            result["error"] = "Timeout"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_http_connectivity(self) -> Dict[str, Any]:
        """Test de conectividad HTTP al ONT"""
        result = {
            "http_accessible": False,
            "https_accessible": False,
            "response_time_ms": None,
            "status_code": None
        }
        
        try:
            import time
            start = time.time()
            
            response = requests.get(
                f"http://{self.host}",
                timeout=5,
                verify=False,
                auth=('root', 'admin')
            )
            
            elapsed_ms = (time.time() - start) * 1000
            
            result["http_accessible"] = True
            result["response_time_ms"] = round(elapsed_ms, 2)
            result["status_code"] = response.status_code
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_gateway_connectivity(self) -> Dict[str, Any]:
        """Test de conectividad al gateway (asumiendo ONT es el gateway)"""
        # El ONT típicamente es el gateway en 192.168.x.1
        gateway = self.host
        
        result = {
            "gateway": gateway,
            "ping_result": self.test_ping(gateway, count=4)
        }
        
        return result
    
    def test_dns_resolution(self) -> Dict[str, Any]:
        """Test de resolución DNS"""
        result = {
            "dns_working": False,
            "resolved_hosts": []
        }
        
        test_domains = ["google.com", "cloudflare.com"]
        
        for domain in test_domains:
            try:
                ip = socket.gethostbyname(domain)
                result["resolved_hosts"].append({
                    "domain": domain,
                    "ip": ip,
                    "success": True
                })
                result["dns_working"] = True
            except socket.gaierror:
                result["resolved_hosts"].append({
                    "domain": domain,
                    "success": False
                })
        
        return result
    
    def test_port_connectivity(self, port: int) -> Dict[str, Any]:
        """Test de conectividad a un puerto específico"""
        result = {
            "host": self.host,
            "port": port,
            "open": False,
            "response_time_ms": None
        }
        
        try:
            import time
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            
            start = time.time()
            result_code = sock.connect_ex((self.host, port))
            elapsed_ms = (time.time() - start) * 1000
            
            sock.close()
            
            if result_code == 0:
                result["open"] = True
                result["response_time_ms"] = round(elapsed_ms, 2)
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def run_all_connectivity_tests(self) -> Dict[str, Any]:
        """Ejecuta todos los tests de conectividad"""
        print(f"\n[*] Ejecutando tests de conectividad para {self.host}\n")
        
        results = {
            "host": self.host,
            "tests": {}
        }
        
        # Test 1: Ping
        print("[TEST] RF 002 - Ping al ONT")
        results["tests"]["ping"] = self.test_ping()
        status = "PASS" if results["tests"]["ping"]["reachable"] else "FAIL"
        print(f"        [{status}] Latencia promedio: {results['tests']['ping'].get('avg_latency_ms', 'N/A')} ms\n")
        
        # Test 2: HTTP
        print("[TEST] RF 002 - Conectividad HTTP")
        results["tests"]["http"] = self.test_http_connectivity()
        status = "PASS" if results["tests"]["http"]["http_accessible"] else "FAIL"
        print(f"        [{status}] Tiempo de respuesta: {results['tests']['http'].get('response_time_ms', 'N/A')} ms\n")
        
        # Test 3: Gateway
        print("[TEST] RF 003 - Conectividad Gateway")
        results["tests"]["gateway"] = self.test_gateway_connectivity()
        status = "PASS" if results["tests"]["gateway"]["ping_result"]["reachable"] else "FAIL"
        print(f"        [{status}] Gateway accesible\n")
        
        # Test 4: DNS
        print("[TEST] RF 003 - Resolución DNS")
        results["tests"]["dns"] = self.test_dns_resolution()
        status = "PASS" if results["tests"]["dns"]["dns_working"] else "FAIL"
        hosts_ok = sum(1 for h in results["tests"]["dns"]["resolved_hosts"] if h["success"])
        print(f"        [{status}] Hosts resueltos: {hosts_ok}/{len(results['tests']['dns']['resolved_hosts'])}\n")
        
        # Test 5: Puertos comunes
        print("[TEST] RF 004 - Escaneo de puertos")
        common_ports = [80, 443, 22, 23, 8080]
        results["tests"]["ports"] = {}
        
        for port in common_ports:
            port_result = self.test_port_connectivity(port)
            results["tests"]["ports"][port] = port_result
            status = "OPEN" if port_result["open"] else "CLOSED"
            print(f"        Puerto {port}: [{status}]")
        
        print()
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Network Connectivity Tests")
    parser.add_argument("--host", required=True, help="IP del ONT")
    
    args = parser.parse_args()
    
    tester = NetworkTester(args.host)
    results = tester.run_all_connectivity_tests()
    
    # Guardar resultados
    import json
    with open("network_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("[+] Resultados guardados en: network_test_results.json")

if __name__ == "__main__":
    main()
