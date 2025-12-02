#!/usr/bin/env python3
"""
Script para obtener información PON del ONT HG6145F
Incluye manejo de escenarios sin fibra conectada y simulación
"""

import requests
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

requests.packages.urllib3.disable_warnings()


class ONTPONInfo:
    """Obtiene y analiza información PON del ONT"""
    
    def __init__(self, host: str, username: str = 'root', password: str = 'admin'):
        self.host = host
        self.username = username
        self.password = password
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.sessionid = None
        
    def get_session(self) -> bool:
        """Obtiene sessionid"""
        params = {
            'ajaxmethod': 'get_refresh_sessionid',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        try:
            response = requests.get(
                self.ajax_url,
                params=params,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.sessionid = data.get('sessionid')
                return True
        except:
            pass
        return False
    
    def _ajax_request(self, method: str) -> Dict[str, Any]:
        """Realiza petición AJAX"""
        params = {
            'ajaxmethod': method,
            'sessionid': self.sessionid,
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        try:
            response = requests.get(
                self.ajax_url,
                params=params,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_pon_info(self) -> Dict[str, Any]:
        """Obtiene información PON"""
        result = self._ajax_request('get_pon_info')
        
        if result['success']:
            data = result['data']
            
            # Verificar si hay sesión válida
            if data.get('session_valid') == 0:
                return {
                    "status": "no_auth",
                    "message": "Método requiere autenticación web completa",
                    "data": data
                }
            
            # Verificar si hay datos PON
            if len(data.keys()) <= 2:  # Solo sessionid y session_valid
                return {
                    "status": "no_data",
                    "message": "Sin datos PON (posiblemente sin fibra conectada)",
                    "data": data
                }
            
            # Hay datos PON
            return {
                "status": "success",
                "message": "Información PON obtenida",
                "data": data
            }
        
        return {
            "status": "error",
            "message": f"Error al consultar: {result.get('status', 'Unknown')}",
            "data": None
        }
    
    def check_fiber_status(self) -> Dict[str, Any]:
        """Verifica si hay fibra conectada consultando múltiples indicadores"""
        print("\n" + "="*80)
        print("VERIFICACIÓN DE ESTADO DE FIBRA")
        print("="*80)
        
        # Obtener información del dispositivo
        device_info = self._ajax_request('get_device_name')
        operator_info = self._ajax_request('get_operator')
        pon_info = self._ajax_request('get_pon_info')
        
        status = {
            "device_accessible": device_info.get('success', False),
            "has_pon_method": pon_info.get('success', False),
            "pon_auth_required": False,
            "fiber_likely_connected": False,
            "indicators": []
        }
        
        # Analizar respuestas
        if pon_info.get('success'):
            pon_data = pon_info['data']
            
            if pon_data.get('session_valid') == 0:
                status['pon_auth_required'] = True
                status['indicators'].append("⚠️  Método PON requiere autenticación web")
            
            # Buscar indicadores de fibra conectada
            fiber_indicators = [
                'tx_power', 'rx_power', 'TxPower', 'RxPower',
                'olt_id', 'olt_rx_power', 'pon_status', 'link_status'
            ]
            
            for indicator in fiber_indicators:
                if indicator in pon_data:
                    status['fiber_likely_connected'] = True
                    status['indicators'].append(f"✓ Encontrado indicador: {indicator}")
        
        # Si no hay indicadores de fibra
        if not status['fiber_likely_connected']:
            status['indicators'].append("❌ Sin indicadores de fibra conectada")
            status['indicators'].append("   → Probable: Fibra no conectada al puerto PON")
        
        return status
    
    def simulate_pon_data(self) -> Dict[str, Any]:
        """Genera ejemplo de datos PON que se obtendrían con fibra conectada"""
        return {
            "simulation": True,
            "note": "Datos de ejemplo - Lo que se obtendría CON fibra conectada",
            "timestamp": datetime.now().isoformat(),
            "pon_info": {
                "session_valid": 1,
                "sessionid": "example123",
                
                # Potencia óptica TX (Transmisión del ONT)
                "tx_power": "2.45",  # dBm
                "tx_power_unit": "dBm",
                "tx_power_description": "Potencia de transmisión del ONT hacia OLT",
                "tx_power_range_normal": "0 a +5 dBm",
                
                # Potencia óptica RX (Recepción del ONT)
                "rx_power": "-21.34",  # dBm
                "rx_power_unit": "dBm",
                "rx_power_description": "Potencia recibida por el ONT desde OLT",
                "rx_power_range_normal": "-28 a -8 dBm",
                
                # Potencia RX del OLT (lo que el OLT recibe del ONT)
                "olt_rx_power": "1.89",  # dBm
                "olt_rx_power_unit": "dBm",
                "olt_rx_power_description": "Potencia recibida por OLT desde ONT",
                
                # Información del transceptor
                "temperature": "45.2",  # °C
                "temperature_unit": "°C",
                "voltage": "3.28",  # V
                "voltage_unit": "V",
                "bias_current": "28.5",  # mA
                "bias_current_unit": "mA",
                
                # Estado del enlace PON
                "pon_status": "up",
                "link_status": "online",
                "olt_id": "HUAW12345678",
                "pon_mode": "GPON",
                
                # Velocidades
                "upstream_rate": "1.25 Gbps",
                "downstream_rate": "2.5 Gbps"
            },
            "interpretation": {
                "tx_rx_difference": "TX > RX significa transmisión normal",
                "tx_power_meaning": "Potencia que SALE del ONT (transmite)",
                "rx_power_meaning": "Potencia que LLEGA al ONT (recibe)",
                "olt_rx_power_meaning": "Potencia que LLEGA al OLT desde ONT",
                "healthy_indicators": [
                    "TX Power entre 0 y +5 dBm (óptimo: +2 a +4 dBm)",
                    "RX Power entre -28 y -8 dBm (óptimo: -25 a -15 dBm)",
                    "Temperatura < 70°C",
                    "Voltaje entre 3.0 y 3.5V",
                    "Link status: online/up"
                ],
                "problem_indicators": [
                    "RX Power < -28 dBm: Señal muy débil, posible problema de fibra",
                    "RX Power > -8 dBm: Señal muy fuerte, posible problema de OLT",
                    "TX Power fuera de rango: Problema con transceptor ONT",
                    "Temperatura > 70°C: Sobrecalentamiento"
                ]
            }
        }
    
    def run_analysis(self, show_simulation: bool = False):
        """Ejecuta análisis completo"""
        print("\n" + "="*80)
        print("ANÁLISIS DE INFORMACIÓN PON - ONT HG6145F")
        print("="*80)
        print(f"Host: {self.host}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener sesión
        print("\n[*] Obteniendo sessionid...")
        if self.get_session():
            print(f"[+] SessionID: {self.sessionid}")
        else:
            print("[-] No se pudo obtener sessionid")
            return
        
        # Verificar estado de fibra
        fiber_status = self.check_fiber_status()
        
        print("\nRESULTADOS:")
        print("-" * 80)
        for indicator in fiber_status['indicators']:
            print(f"  {indicator}")
        
        # Intentar obtener información PON
        print("\n" + "="*80)
        print("CONSULTANDO INFORMACIÓN PON")
        print("="*80)
        
        pon_result = self.get_pon_info()
        
        print(f"\nEstado: {pon_result['status']}")
        print(f"Mensaje: {pon_result['message']}")
        
        if pon_result['data']:
            print("\nDatos obtenidos:")
            print(json.dumps(pon_result['data'], indent=2, ensure_ascii=False))
        
        # Simulación (si se solicita o no hay fibra)
        simulated_data = None
        if show_simulation or pon_result['status'] in ['no_auth', 'no_data']:
            print("\n" + "="*80)
            print("DATOS DE EJEMPLO (CON FIBRA CONECTADA)")
            print("="*80)
            print("\n📘 Así se vería la respuesta SI tuvieras fibra conectada:\n")
            
            simulated_data = self.simulate_pon_data()
            
            # Mostrar estructura de datos simulados
            pon_info = simulated_data['pon_info']
            
            print("┌─ POTENCIA ÓPTICA ─────────────────────────────────────┐")
            print(f"│                                                        │")
            print(f"│  📤 TX Power (ONT → OLT)                              │")
            print(f"│     Valor: {pon_info['tx_power']} {pon_info['tx_power_unit']}                                  │")
            print(f"│     Rango normal: {pon_info['tx_power_range_normal']}                   │")
            print(f"│                                                        │")
            print(f"│  📥 RX Power (OLT → ONT)                              │")
            print(f"│     Valor: {pon_info['rx_power']} {pon_info['rx_power_unit']}                                │")
            print(f"│     Rango normal: {pon_info['rx_power_range_normal']}                  │")
            print(f"│                                                        │")
            print(f"│  📥 OLT RX Power (ONT → OLT recibido)                │")
            print(f"│     Valor: {pon_info['olt_rx_power']} {pon_info['olt_rx_power_unit']}                                  │")
            print(f"│                                                        │")
            print("└────────────────────────────────────────────────────────┘")
            
            print("\n┌─ TRANSCEPTOR ─────────────────────────────────────────┐")
            print(f"│  🌡️  Temperatura: {pon_info['temperature']} {pon_info['temperature_unit']}                             │")
            print(f"│  ⚡ Voltaje: {pon_info['voltage']} {pon_info['voltage_unit']}                                   │")
            print(f"│  🔌 Corriente: {pon_info['bias_current']} {pon_info['bias_current_unit']}                              │")
            print("└────────────────────────────────────────────────────────┘")
            
            print("\n┌─ ENLACE PON ──────────────────────────────────────────┐")
            print(f"│  Estado: {pon_info['pon_status']} / {pon_info['link_status']}                              │")
            print(f"│  Modo: {pon_info['pon_mode']}                                        │")
            print(f"│  OLT ID: {pon_info['olt_id']}                           │")
            print(f"│  Upload: {pon_info['upstream_rate']}                              │")
            print(f"│  Download: {pon_info['downstream_rate']}                            │")
            print("└────────────────────────────────────────────────────────┘")
            
            print("\n" + "="*80)
            print("INTERPRETACIÓN DE VALORES")
            print("="*80)
            
            interp = simulated_data['interpretation']
            
            print("\n🔍 Diferencia TX/RX:")
            print(f"   {interp['tx_rx_difference']}")
            print(f"\n   • TX Power: {interp['tx_power_meaning']}")
            print(f"   • RX Power: {interp['rx_power_meaning']}")
            print(f"   • OLT RX: {interp['olt_rx_power_meaning']}")
            
            print("\n✅ Indicadores de salud normal:")
            for indicator in interp['healthy_indicators']:
                print(f"   • {indicator}")
            
            print("\n⚠️  Indicadores de problemas:")
            for indicator in interp['problem_indicators']:
                print(f"   • {indicator}")
        
        # Guardar resultados
        output = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "fiber_status_check": fiber_status,
            "pon_query_result": pon_result,
            "simulated_data": simulated_data,
            "note": "Sin fibra conectada - Los métodos PON no devuelven datos reales"
        }
        
        filename = f"pon_analysis_{datetime.now().strftime('%d_%m_%y_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Análisis guardado en: {filename}")
        
        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN")
        print("="*80)
        
        if not fiber_status['fiber_likely_connected']:
            print("\n⚠️  ESTADO ACTUAL: Sin fibra conectada")
            print("\n📋 Pasos para obtener datos PON reales:")
            print("   1. Conectar cable de fibra óptica al puerto PON del ONT")
            print("   2. Esperar ~30 segundos para que sincronice con OLT")
            print("   3. Ejecutar este script nuevamente")
            print("   4. Los métodos PON deberían devolver datos reales")
        else:
            print("\n✓ Fibra conectada - Datos obtenidos exitosamente")


def main():
    parser = argparse.ArgumentParser(
        description='Análisis de información PON del ONT HG6145F'
    )
    parser.add_argument('--host', type=str, default='192.168.100.1',
                        help='Dirección IP del ONT')
    parser.add_argument('--username', type=str, default='root',
                        help='Usuario (default: root)')
    parser.add_argument('--password', type=str, default='admin',
                        help='Contraseña (default: admin)')
    parser.add_argument('--simulate', action='store_true',
                        help='Mostrar datos simulados de ejemplo')
    
    args = parser.parse_args()
    
    analyzer = ONTPONInfo(args.host, args.username, args.password)
    analyzer.run_analysis(show_simulation=args.simulate)


if __name__ == "__main__":
    main()
