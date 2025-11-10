#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import ssl
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime

class TR069Client:
    """Cliente básico TR-069 para comunicación con ACS"""
    
    def __init__(self, host: str, port: int = 7547, timeout: int = 10, 
                 username: str = None, password: str = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.username = username
        self.password = password
        self.session_id = None
        self.last_inform_time = None

    def connect(self) -> Dict[str, Any]:
        """Inicia una conexión con el dispositivo"""
        try:
            # Crear socket
            sock = socket.create_connection((self.host, self.port), self.timeout)
            
            # Enviar mensaje Inform inicial
            inform_response = self._send_inform(sock)
            
            if inform_response.get('status') == 'success':
                self.session_id = inform_response.get('session_id')
                self.last_inform_time = datetime.now()
                
            return inform_response
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_parameter_values(self, parameters: list) -> Dict[str, Any]:
        """Obtiene valores de parámetros TR-069"""
        if not self.session_id:
            return {'error': 'No session established'}
            
        try:
            # Crear mensaje GetParameterValues
            message = self._create_get_parameter_values_message(parameters)
            
            # Enviar solicitud
            sock = socket.create_connection((self.host, self.port), self.timeout)
            response = self._send_soap_message(sock, message)
            
            return self._parse_parameter_values_response(response)
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_device_info(self) -> Dict[str, Any]:
        """Obtiene información básica del dispositivo"""
        common_parameters = [
            "Device.DeviceInfo.Manufacturer",
            "Device.DeviceInfo.ModelName",
            "Device.DeviceInfo.Description",
            "Device.DeviceInfo.SerialNumber",
            "Device.DeviceInfo.HardwareVersion",
            "Device.DeviceInfo.SoftwareVersion"
        ]
        
        return self.get_parameter_values(common_parameters)

    def _send_inform(self, sock: socket.socket) -> Dict[str, Any]:
        """Envía un mensaje Inform TR-069"""
        try:
            # Crear mensaje Inform
            inform_message = self._create_inform_message()
            
            # Enviar mensaje
            response = self._send_soap_message(sock, inform_message)
            
            # Parsear respuesta
            return self._parse_inform_response(response)
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _create_inform_message(self) -> str:
        """Crea un mensaje Inform TR-069"""
        current_time = datetime.utcnow().isoformat()
        
        message = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope 
    xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
    <SOAP-ENV:Header>
        <cwmp:ID SOAP-ENV:mustUnderstand="1">1</cwmp:ID>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
        <cwmp:Inform>
            <DeviceId>
                <Manufacturer>Unknown</Manufacturer>
                <OUI>000000</OUI>
                <ProductClass>ONT</ProductClass>
                <SerialNumber>UNKNOWN</SerialNumber>
            </DeviceId>
            <Event SOAP-ENV:arrayType="cwmp:EventStruct[1]">
                <EventStruct>
                    <EventCode>2 PERIODIC</EventCode>
                    <CommandKey></CommandKey>
                </EventStruct>
            </Event>
            <MaxEnvelopes>1</MaxEnvelopes>
            <CurrentTime>{current_time}</CurrentTime>
            <RetryCount>0</RetryCount>
        </cwmp:Inform>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""
        
        return message

    def _create_get_parameter_values_message(self, parameters: list) -> str:
        """Crea un mensaje GetParameterValues"""
        parameters_xml = "".join([f"<string>{param}</string>" for param in parameters])
        
        message = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope 
    xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
    <SOAP-ENV:Header>
        <cwmp:ID SOAP-ENV:mustUnderstand="1">{self.session_id}</cwmp:ID>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
        <cwmp:GetParameterValues>
            <ParameterNames SOAP-ENV:arrayType="xsd:string[{len(parameters)}]">
                {parameters_xml}
            </ParameterNames>
        </cwmp:GetParameterValues>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""
        
        return message

    def _send_soap_message(self, sock: socket.socket, message: str) -> str:
        """Envía un mensaje SOAP y recibe la respuesta"""
        try:
            # Construir solicitud HTTP
            http_request = (
                f"POST / HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Content-Type: text/xml; charset=utf-8\r\n"
                f"Content-Length: {len(message)}\r\n"
                f"Connection: keep-alive\r\n"
                f"\r\n"
                f"{message}"
            )
            
            # Enviar solicitud
            sock.send(http_request.encode())
            
            # Recibir respuesta
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
            # Extraer cuerpo SOAP
            response_str = response.decode('utf-8')
            body_start = response_str.find('\r\n\r\n')
            if body_start != -1:
                return response_str[body_start + 4:]
                
            return response_str
            
        finally:
            sock.close()

    def _parse_inform_response(self, response: str) -> Dict[str, Any]:
        """Parsea la respuesta a un mensaje Inform"""
        try:
            root = ET.fromstring(response)
            
            # Buscar el ID de sesión
            header = root.find(".//{urn:dslforum-org:cwmp-1-0}ID")
            if header is not None:
                session_id = header.text
                return {
                    'status': 'success',
                    'session_id': session_id
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
        return {
            'status': 'error',
            'error': 'Could not parse response'
        }

    def _parse_parameter_values_response(self, response: str) -> Dict[str, Any]:
        """Parsea la respuesta a un mensaje GetParameterValues"""
        try:
            root = ET.fromstring(response)
            
            # Buscar parámetros
            parameters = {}
            param_list = root.findall(".//ParameterValueStruct")
            
            for param in param_list:
                name = param.find("Name")
                value = param.find("Value")
                if name is not None and value is not None:
                    parameters[name.text] = value.text
                    
            return {
                'status': 'success',
                'parameters': parameters
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión TR-069 al dispositivo"""
        try:
            response = self.connect()
            if response.get('status') == 'success':
                return {
                    'status': 'success',
                    'session_id': self.session_id,
                    'last_inform': self.last_inform_time.isoformat() if self.last_inform_time else None
                }
            return response
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
