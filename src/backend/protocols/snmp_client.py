#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import struct
import time
from typing import Dict, List, Any, Optional, Union

class SNMPClient:
    """Cliente SNMP básico para consultar dispositivos"""
    
    def __init__(self, host: str, community: str = 'public', port: int = 161, timeout: int = 2):
        self.host = host
        self.community = community
        self.port = port
        self.timeout = timeout
        self._request_id = 0

    def get(self, oid: str) -> Dict[str, Any]:
        """Realiza una consulta SNMP GET"""
        # Incrementar ID de solicitud
        self._request_id += 1
        
        # Construir paquete SNMP
        packet = self._build_get_request(oid)
        
        try:
            # Crear socket UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            
            # Enviar solicitud
            sock.sendto(packet, (self.host, self.port))
            
            # Recibir respuesta
            response, _ = sock.recvfrom(4096)
            
            # Parsear respuesta
            return self._parse_response(response)
            
        except socket.timeout:
            return {'error': 'Timeout', 'status': 'error'}
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
        finally:
            sock.close()

    def get_bulk(self, oids: List[str]) -> Dict[str, Any]:
        """Realiza múltiples consultas SNMP GET"""
        results = {}
        for oid in oids:
            results[oid] = self.get(oid)
        return results

    def walk(self, base_oid: str) -> List[Dict[str, Any]]:
        """Realiza un SNMP WALK desde el OID base"""
        results = []
        current_oid = base_oid
        
        while True:
            response = self.get(current_oid)
            
            if 'error' in response:
                break
                
            if not self._is_in_subtree(base_oid, response.get('oid', '')):
                break
                
            results.append(response)
            current_oid = self._get_next_oid(response.get('oid', ''))
            
        return results

    def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión SNMP al dispositivo"""
        # System Description OID
        system_descr_oid = '1.3.6.1.2.1.1.1.0'
        
        result = self.get(system_descr_oid)
        if 'error' not in result:
            return {
                'status': 'success',
                'community': self.community,
                'system_description': result.get('value', 'Unknown')
            }
        return {
            'status': 'error',
            'error': result.get('error', 'Unknown error')
        }

    def get_device_info(self) -> Dict[str, Any]:
        """Obtiene información básica del dispositivo via SNMP"""
        # OIDs comunes para información del sistema
        system_oids = {
            'description': '1.3.6.1.2.1.1.1.0',
            'object_id': '1.3.6.1.2.1.1.2.0',
            'uptime': '1.3.6.1.2.1.1.3.0',
            'contact': '1.3.6.1.2.1.1.4.0',
            'name': '1.3.6.1.2.1.1.5.0',
            'location': '1.3.6.1.2.1.1.6.0',
            'services': '1.3.6.1.2.1.1.7.0'
        }
        
        return self.get_bulk(list(system_oids.values()))

    def _build_get_request(self, oid: str) -> bytes:
        """Construye un paquete SNMP GET Request"""
        # Versión SNMP v1
        version = 0
        
        # Community string
        community = self.community.encode()
        
        # Request ID
        request_id = self._request_id
        
        # Error status y index
        error_status = 0
        error_index = 0
        
        # Construir el paquete
        packet = (
            b'\x30' +  # Sequence
            self._length_byte(
                # Version
                b'\x02' + self._length_byte(bytes([version])) +
                # Community
                b'\x04' + self._length_byte(community) +
                # PDU type (GET)
                b'\xa0' + self._length_byte(
                    # Request ID
                    b'\x02' + self._length_byte(self._int_to_bytes(request_id)) +
                    # Error status
                    b'\x02' + self._length_byte(bytes([error_status])) +
                    # Error index
                    b'\x02' + self._length_byte(bytes([error_index])) +
                    # Variable bindings
                    b'\x30' + self._length_byte(
                        b'\x30' + self._length_byte(
                            # OID
                            b'\x06' + self._length_byte(self._encode_oid(oid)) +
                            # NULL
                            b'\x05\x00'
                        )
                    )
                )
            )
        )
        
        return packet

    @staticmethod
    def _length_byte(content: bytes) -> bytes:
        """Genera el byte de longitud para ASN.1"""
        length = len(content)
        if length <= 127:
            return bytes([length]) + content
        else:
            length_bytes = []
            while length > 0:
                length_bytes.insert(0, length & 0xFF)
                length >>= 8
            return bytes([0x80 | len(length_bytes)]) + bytes(length_bytes) + content

    @staticmethod
    def _int_to_bytes(value: int) -> bytes:
        """Convierte un entero a bytes"""
        if value == 0:
            return b'\x00'
        bytes_list = []
        while value:
            bytes_list.insert(0, value & 0xFF)
            value >>= 8
        return bytes(bytes_list)

    @staticmethod
    def _encode_oid(oid: str) -> bytes:
        """Codifica un OID en formato ASN.1"""
        # Separar el OID en sus componentes
        components = [int(x) for x in oid.split('.')]
        
        # El primer byte es especial (40 * first + second)
        result = bytes([40 * components[0] + components[1]])
        
        # Codificar el resto de los componentes
        for value in components[2:]:
            if value < 128:
                result += bytes([value])
            else:
                bytes_list = []
                while value:
                    bytes_list.insert(0, value & 0x7F)
                    value >>= 7
                # Establecer el bit más significativo en todos excepto el último
                for i in range(len(bytes_list) - 1):
                    bytes_list[i] |= 0x80
                result += bytes(bytes_list)
                
        return result

    @staticmethod
    def _parse_response(response: bytes) -> Dict[str, Any]:
        """Parsea una respuesta SNMP"""
        try:
            # Implementación básica del parser
            # En una implementación real, necesitaríamos un parser ASN.1 completo
            if len(response) < 10:
                return {'error': 'Response too short'}
                
            # Verificar que es una secuencia
            if response[0] != 0x30:
                return {'error': 'Invalid response format'}
                
            # Extraer valor (simplificado)
            value_start = response.find(b'\x04', 10)  # Buscar el primer OCTET STRING
            if value_start != -1:
                value_length = response[value_start + 1]
                value = response[value_start + 2:value_start + 2 + value_length]
                try:
                    return {
                        'value': value.decode('utf-8'),
                        'type': 'string'
                    }
                except:
                    return {
                        'value': value.hex(),
                        'type': 'hex'
                    }
                    
        except Exception as e:
            return {'error': str(e)}
            
        return {'error': 'Unable to parse response'}

    @staticmethod
    def _is_in_subtree(base_oid: str, current_oid: str) -> bool:
        """Verifica si un OID está en el sub-árbol de otro"""
        return current_oid.startswith(base_oid + '.')
