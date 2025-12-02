#!/usr/bin/env python3
"""
Script para localizar dispositivos Grandstream HT818 en la red.
Prueba IPs comunes y escanea la subred actual.
"""

import requests
from requests.auth import HTTPBasicAuth
import socket
import concurrent.futures
from typing import Dict, Optional, Tuple
import sys
import time

# Configuración
TIMEOUT = 3
MAX_WORKERS = 20

# IPs comunes de Grandstream
COMMON_IPS = [
    "192.168.2.1",      # Default factory
    "192.168.1.1",      # Común en muchos dispositivos
    "192.168.0.1",      # Alternativo
    "192.168.100.1",    # Actual (verificar si es realmente HT818)
]

# Endpoints característicos de Grandstream
GRANDSTREAM_ENDPOINTS = [
    "/cgi-bin/api.values.get",
    "/cgi-bin/api-sys_operation",
    "/status.html",
    "/index.html",
]

# Credenciales comunes
CREDENTIALS = [
    ("admin", "admin"),
    ("admin", ""),
    ("", "admin"),
]


class GrandstreamFinder:
    def __init__(self):
        self.found_devices = []
        
    def check_ip(self, ip: str) -> Optional[Dict]:
        """Verifica si hay un dispositivo Grandstream en la IP dada."""
        print(f"[*] Probando {ip}...", end=" ", flush=True)
        
        # 1. Verificar si el puerto 80 está abierto
        if not self._check_port(ip, 80):
            print("✗ Puerto 80 cerrado")
            return None
            
        # 2. Intentar obtener información del dispositivo
        device_info = self._probe_device(ip)
        
        if device_info:
            print(f"✓ {device_info.get('type', 'Dispositivo encontrado')}")
            return device_info
        else:
            print("✗ No es Grandstream")
            return None
    
    def _check_port(self, ip: str, port: int) -> bool:
        """Verifica si un puerto está abierto."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _probe_device(self, ip: str) -> Optional[Dict]:
        """Intenta identificar el dispositivo en la IP."""
        device_info = {
            "ip": ip,
            "type": "Unknown",
            "endpoints": [],
            "headers": {},
            "credentials": None,
        }
        
        # Probar diferentes endpoints con diferentes credenciales
        for user, pwd in CREDENTIALS:
            for endpoint in GRANDSTREAM_ENDPOINTS:
                url = f"http://{ip}{endpoint}"
                try:
                    auth = HTTPBasicAuth(user, pwd) if user or pwd else None
                    response = requests.get(url, auth=auth, timeout=TIMEOUT, verify=False)
                    
                    if response.status_code == 200:
                        device_info["endpoints"].append(endpoint)
                        device_info["headers"] = dict(response.headers)
                        device_info["credentials"] = (user, pwd)
                        
                        # Analizar contenido para identificar dispositivo
                        content = response.text.lower()
                        
                        # Buscar indicadores de Grandstream
                        if any(x in content for x in ["grandstream", "ht818", "ht801", "ht802"]):
                            device_info["type"] = "Grandstream ATA"
                            if "ht818" in content:
                                device_info["model"] = "HT818"
                            return device_info
                        
                        # Buscar indicadores de ONT
                        elif any(x in content for x in ["fiberhome", "hg6145", "ont", "pon", "ajaxmethod"]):
                            device_info["type"] = "ONT (Fiberhome/similar)"
                            return device_info
                            
                except requests.exceptions.RequestException:
                    continue
        
        # Si encontramos algún endpoint pero no identificamos el tipo
        if device_info["endpoints"]:
            return device_info
            
        return None
    
    def scan_subnet(self, base_ip: str, start: int = 1, end: int = 254) -> None:
        """Escanea una subred completa."""
        base = ".".join(base_ip.split(".")[:-1])
        ips_to_scan = [f"{base}.{i}" for i in range(start, end + 1)]
        
        print(f"\n{'='*70}")
        print(f"ESCANEANDO SUBRED: {base}.{start}-{end}")
        print(f"{'='*70}\n")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.check_ip, ip): ip for ip in ips_to_scan}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    self.found_devices.append(result)
    
    def check_common_ips(self) -> None:
        """Verifica las IPs comunes de Grandstream."""
        print(f"\n{'='*70}")
        print("VERIFICANDO IPs COMUNES DE GRANDSTREAM")
        print(f"{'='*70}\n")
        
        for ip in COMMON_IPS:
            result = self.check_ip(ip)
            if result:
                self.found_devices.append(result)
            time.sleep(0.2)  # Pequeña pausa entre intentos
    
    def get_local_subnet(self) -> str:
        """Obtiene la subred local."""
        try:
            # Conectar a un servidor externo para obtener nuestra IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "192.168.100.1"  # Default fallback
    
    def print_results(self) -> None:
        """Muestra los resultados del escaneo."""
        print(f"\n{'='*70}")
        print("RESULTADOS DEL ESCANEO")
        print(f"{'='*70}\n")
        
        if not self.found_devices:
            print("❌ No se encontraron dispositivos Grandstream")
            return
        
        print(f"✓ {len(self.found_devices)} dispositivo(s) encontrado(s):\n")
        
        for i, device in enumerate(self.found_devices, 1):
            print(f"\n[Dispositivo {i}]")
            print(f"  IP:          {device['ip']}")
            print(f"  Tipo:        {device['type']}")
            print(f"  Modelo:      {device.get('model', 'N/A')}")
            print(f"  Credenciales: {device.get('credentials', 'N/A')}")
            print(f"  Endpoints:   {', '.join(device['endpoints']) if device['endpoints'] else 'N/A'}")
            
            if device['headers']:
                print(f"  Server:      {device['headers'].get('Server', 'N/A')}")
            
            print()
    
    def save_results(self, filename: str = None) -> None:
        """Guarda los resultados en un archivo JSON."""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
            filename = f"grandstream_scan_{timestamp}.json"
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "scan_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "devices_found": len(self.found_devices),
                "devices": self.found_devices
            }, f, indent=2)
        
        print(f"[+] Resultados guardados en: {filename}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           GRANDSTREAM HT818 FINDER - Network Scanner             ║
║                   Localización de dispositivos ATA                ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    finder = GrandstreamFinder()
    
    # 1. Verificar IPs comunes
    finder.check_common_ips()
    
    # 2. Obtener subred local
    local_ip = finder.get_local_subnet()
    print(f"\n[i] IP local detectada: {local_ip}")
    
    # 3. Escanear subred local (rango reducido para ser más rápido)
    if "--full-scan" in sys.argv:
        finder.scan_subnet(local_ip, 1, 254)
    else:
        print("[i] Escaneando rango reducido (1-50). Use --full-scan para escaneo completo.")
        finder.scan_subnet(local_ip, 1, 50)
    
    # 4. Mostrar resultados
    finder.print_results()
    
    # 5. Guardar resultados
    if finder.found_devices:
        finder.save_results()
    
    print(f"\n{'='*70}")
    print("RECOMENDACIONES")
    print(f"{'='*70}")
    
    if not finder.found_devices:
        print("""
❌ No se encontró ningún dispositivo Grandstream HT818.

Posibles causas:
1. El HT818 está en una subred diferente
2. El dispositivo está apagado o desconectado
3. El firewall está bloqueando el acceso
4. Las credenciales han sido cambiadas

Acciones recomendadas:
→ Verificar conexión física del HT818
→ Revisar configuración de red del HT818 (puede estar en 192.168.2.x)
→ Conectar directamente al HT818 con cable ethernet
→ Hacer reset de fábrica al HT818 (mantener botón 10 seg)
        """)
    else:
        grandstream_found = any(d['type'] == "Grandstream ATA" for d in finder.found_devices)
        
        if grandstream_found:
            print("""
✓ Dispositivo(s) Grandstream encontrado(s).

Próximos pasos:
→ Usar la IP y credenciales encontradas para extraer información
→ Ejecutar: python discover_ht818.py --host <IP_ENCONTRADA>
→ Actualizar configuración en los scripts de testing
            """)
        else:
            print("""
⚠ Se encontraron dispositivos pero ninguno es Grandstream.

El dispositivo en 192.168.100.1 es un ONT, no el HT818.
El HT818 debe estar en otra dirección IP o subred.
            """)
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Escaneo interrumpido por el usuario")
        sys.exit(0)
