#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import struct
import time
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree

class UPnPClient:
    """Cliente UPnP para descubrimiento y control de dispositivos"""
    
    MULTICAST_GROUP = '239.255.255.250'
    MULTICAST_PORT = 1900
    ALTERNATE_PORTS = [1900, 2869, 5000, 49152, 49153, 49154, 49155, 49156]
    
    def __init__(self, timeout: int = 3):
        self.timeout = timeout
        self._devices: List[Dict[str, Any]] = []
        self.vulnerabilities_found: List[Dict[str, Any]] = []

    def discover(self, test_vulnerabilities: bool = True) -> List[Dict[str, Any]]:
        """Descubre dispositivos UPnP en la red y prueba vulnerabilidades conocidas"""
        # Limpiar listas
        self._devices = []
        self.vulnerabilities_found = []
        
        # Probar puertos alternativos
        for port in self.ALTERNATE_PORTS:
            sock = None
            try:
                # Crear socket multicast
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.settimeout(self.timeout)
                
                print(f"Probando puerto UPnP: {port}")
        
                # Mensaje SSDP de descubrimiento
                ssdp_request = (
                    'M-SEARCH * HTTP/1.1\r\n'
                    f'HOST: {self.MULTICAST_GROUP}:{self.MULTICAST_PORT}\r\n'
                    'MAN: "ssdp:discover"\r\n'
                    'MX: 2\r\n'
                    'ST: upnp:rootdevice\r\n'
                    '\r\n'
                )
                
                # Enviar mensaje de descubrimiento
                sock.sendto(ssdp_request.encode(), (self.MULTICAST_GROUP, self.MULTICAST_PORT))
            
                # Esperar respuestas
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    try:
                        data, addr = sock.recvfrom(1024)
                        device = self._parse_ssdp_response(data.decode(), addr[0])
                        if device:
                            self._devices.append(device)
                    except socket.timeout:
                        break
                        
            except Exception as e:
                print(f"Error en puerto {port}: {str(e)}")
            finally:
                if sock:
                    sock.close()
            
        return self._devices

    def _parse_ssdp_response(self, response: str, ip: str) -> Optional[Dict[str, Any]]:
        """Parsea la respuesta SSDP"""
        lines = response.split('\r\n')
        if not lines:
            return None
            
        device = {
            'ip': ip,
            'headers': {},
            'type': 'unknown'
        }
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                device['headers'][key.lower().strip()] = value.strip()
                
        # Extraer información relevante
        location = device['headers'].get('location')
        if location:
            device['location'] = location
            try:
                device.update(self._fetch_device_description(location))
            except:
                pass
                
        server = device['headers'].get('server')
        if server:
            device['server'] = server
            
        return device

    def _fetch_device_description(self, url: str) -> Dict[str, Any]:
        """Obtiene la descripción detallada del dispositivo"""
        try:
            from urllib.parse import urlparse
            # Crear socket
            parsed_url = urlparse(url)
            port = parsed_url.port or 80
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((parsed_url.hostname, port))
            
            # Enviar solicitud HTTP
            request = (
                f"GET {parsed_url.path} HTTP/1.1\r\n"
                f"Host: {parsed_url.hostname}\r\n"
                "Connection: close\r\n\r\n"
            )
            sock.send(request.encode())
            
            # Recibir respuesta
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
            # Encontrar inicio del XML
            xml_start = response.find(b'<?xml')
            if xml_start == -1:
                return {}
                
            # Parsear XML
            xml_data = response[xml_start:]
            root = ElementTree.fromstring(xml_data)
            
            # Extraer información
            device_element = root.find('.//device')
            if device_element is not None:
                return {
                    'friendly_name': device_element.findtext('friendlyName', ''),
                    'manufacturer': device_element.findtext('manufacturer', ''),
                    'model_name': device_element.findtext('modelName', ''),
                    'model_number': device_element.findtext('modelNumber', ''),
                    'serial_number': device_element.findtext('serialNumber', ''),
                    'device_type': device_element.findtext('deviceType', '')
                }
                
        except Exception as e:
            return {'error': str(e)}
            
        return {}

    def get_device_info(self, device_url: str) -> Dict[str, Any]:
        """Obtiene información detallada de un dispositivo específico"""
        return self._fetch_device_description(device_url)

    def list_services(self, device_url: str) -> List[Dict[str, Any]]:
        """Lista los servicios disponibles en un dispositivo"""
        services = []
        try:
            device_info = self._fetch_device_description(device_url)
            root = ElementTree.fromstring(device_info.get('xml', ''))
            
            for service in root.findall('.//service'):
                services.append({
                    'service_type': service.findtext('serviceType', ''),
                    'service_id': service.findtext('serviceId', ''),
                    'control_url': service.findtext('controlURL', ''),
                    'event_sub_url': service.findtext('eventSubURL', ''),
                    'scpd_url': service.findtext('SCPDURL', '')
                })
                
        except Exception as e:
            return [{'error': str(e)}]
            
        return services
