#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONT Network Tester - Herramienta de diagnóstico sin dependencia de SSH/Telnet
Utiliza protocolos de red básicos para obtener información y realizar pruebas
"""

import sys
import time
import json
import socket
import struct
import argparse
from typing import Dict, List, Any
from scapy.all import ARP, Ether, srp
import nmap
import upnpy
from pysnmp.hlapi import *

class ONTNetworkTester:
    def __init__(self, target_ip: str):
        self.target_ip = target_ip
        self.results: Dict[str, Any] = {
            "target_ip": target_ip,
            "timestamp": int(time.time()),
            "tests": {}
        }

    def test_basic_connectivity(self) -> Dict[str, Any]:
        """Prueba conectividad básica y obtiene información ARP"""
        results = {}
        
        # Prueba de ping básica
        try:
            socket.create_connection((self.target_ip, 80), timeout=2)
            results["ping"] = True
        except Exception:
            results["ping"] = False

        # Escaneo ARP para obtener MAC
        try:
            arp = ARP(pdst=self.target_ip)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            result = srp(packet, timeout=2, verbose=0)[0]
            
            if result:
                results["mac_address"] = result[0][1].hwsrc
                results["vendor"] = self.get_vendor_from_mac(result[0][1].hwsrc)
            
        except Exception as e:
            results["arp_error"] = str(e)

        return results

    def scan_common_ports(self) -> Dict[str, List[int]]:
        """Escanea puertos comunes de manera segura"""
        nm = nmap.PortScanner()
        
        # Escaneo básico de puertos comunes
        common_ports = [21,22,23,53,80,443,8080,8443]
        ports_to_scan = ",".join(map(str, common_ports))
        
        try:
            nm.scan(self.target_ip, arguments=f'-n -sS -p{ports_to_scan}')
            
            open_ports = []
            closed_ports = []
            
            if self.target_ip in nm.all_hosts():
                for port in common_ports:
                    try:
                        state = nm[self.target_ip]['tcp'][port]['state']
                        if state == 'open':
                            open_ports.append(port)
                        elif state == 'closed':
                            closed_ports.append(port)
                    except:
                        continue
            
            return {
                "open": open_ports,
                "closed": closed_ports
            }
            
        except Exception as e:
            return {"error": str(e)}

    def discover_upnp(self) -> Dict[str, Any]:
        """Intenta descubrir servicios UPnP"""
        try:
            upnp = upnpy.UPnP()
            devices = upnp.discover(timeout=2)
            
            upnp_info = {
                "devices_found": len(devices),
                "devices": []
            }
            
            for device in devices:
                try:
                    device_info = {
                        "friendly_name": device.friendly_name,
                        "manufacturer": device.manufacturer,
                        "model_name": device.model_name,
                        "services": [service.service_type for service in device.services]
                    }
                    upnp_info["devices"].append(device_info)
                except:
                    continue
                    
            return upnp_info
            
        except Exception as e:
            return {"error": str(e)}

    def check_snmp(self) -> Dict[str, Any]:
        """Intenta obtener información básica via SNMP"""
        results = {}
        
        # Comunidades SNMP comunes
        communities = ['public', 'private', 'router']
        
        for community in communities:
            try:
                iterator = getNext(
                    SnmpEngine(),
                    CommunityData(community, mpModel=0),
                    UdpTransportTarget((self.target_ip, 161), timeout=2),
                    ContextData(),
                    ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                
                if errorIndication or errorStatus:
                    continue
                    
                for varBind in varBinds:
                    results[community] = {
                        "status": "accessible",
                        "system_description": str(varBind[1])
                    }
                    break
                    
            except Exception:
                continue
                
        return results

    @staticmethod
    def get_vendor_from_mac(mac: str) -> str:
        """Obtiene el fabricante basado en los primeros 6 dígitos de la MAC"""
        # Simplificado para el ejemplo - en producción usar una base de datos OUI
        mac_prefix = mac.replace(":", "")[:6].upper()
        vendors = {
            "FCFBFB": "HUAWEI",
            "00E0FC": "HUAWEI",
            "002E40": "ZTE",
            # Añadir más según necesidad
        }
        return vendors.get(mac_prefix, "Unknown")

    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todas las pruebas disponibles"""
        self.results["tests"]["connectivity"] = self.test_basic_connectivity()
        self.results["tests"]["ports"] = self.scan_common_ports()
        self.results["tests"]["upnp"] = self.discover_upnp()
        self.results["tests"]["snmp"] = self.check_snmp()
        
        return self.results

def main():
    parser = argparse.ArgumentParser(description='ONT Network Tester')
    parser.add_argument('--host', required=True, help='IP del dispositivo objetivo')
    args = parser.parse_args()

    tester = ONTNetworkTester(args.host)
    results = tester.run_all_tests()
    
    print(json.dumps(results, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())