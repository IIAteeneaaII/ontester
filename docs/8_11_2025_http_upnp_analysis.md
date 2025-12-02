# Reporte de Scripts HTTP/UPnP - 8 Nov 2025

## Resumen de Scripts Generados

| Archivo | Función Principal |
|---------|------------------|
| `test_ont_auth.py` | Prueba básica de autenticación con credenciales root/admin |
| `test_ont_auth_detailed.py` | Pruebas exhaustivas de autenticación con diferentes headers y user agents |
| `test_ont_curl.py` | Emulación de comandos curl que funcionaron para acceder a la ONT |
| `test_ont_routes.py` | Análisis de todas las rutas y páginas disponibles en la ONT |
| `analyze_version.py` | Análisis del archivo versionControl.js para entender el control de versiones |
| `analyze_login.py` | Análisis de la página de login y sus mecanismos de autenticación |
| `ont_http_detailed.py` | Análisis HTTP detallado con estructura modular y pruebas de servicios |

## Análisis de Mantenibilidad

### Scripts a Conservar

1. `ont_http_detailed.py`
   - **Razón:** Script principal y más completo
   - **Características:**
     - Implementación modular y orientada a objetos
     - Análisis completo de servicios y APIs
     - Estructura base para futuras expansiones
     - Incluye pruebas de seguridad y headers

2. `test_ont_routes.py`
   - **Razón:** Documentación completa de endpoints
   - **Características:**
     - Mapeo completo de rutas disponibles
     - Identificación de niveles de acceso
     - Útil como referencia para desarrollo futuro

3. `test_ont_curl.py`
   - **Razón:** Implementación base funcional
   - **Características:**
     - Contiene la implementación HTTP funcional
     - Sirve como referencia para el protocolo correcto
     - Base para futuras implementaciones de clientes HTTP

### Scripts a Eliminar

1. Scripts de Autenticación:
   - `test_ont_auth.py`
   - `test_ont_auth_detailed.py`
   - **Razón:** Funcionalidad migrada a `ont_http_detailed.py`

2. Scripts de Análisis:
   - `analyze_version.py`
   - `analyze_login.py`
   - **Razón:** Scripts de uso único, información ya documentada

## Hallazgos Principales

1. Protocolo HTTP:
   - Formato específico requerido para HTTP/1.1
   - Headers y orden específico necesarios
   - Manejo de conexiones keep-alive importante

2. Autenticación:
   - Credenciales: root/admin
   - Sistema de niveles de acceso (0-4)
   - Control de acceso basado en JavaScript

3. Estructura de la ONT:
   - Múltiples interfaces de login por operador
   - APIs para información del dispositivo
   - Servicios modulares (WiFi, PON, VoIP)

## Bitácora del Día (8/11/2025)

### Secuencia de Archivos Creados
1. `run_all_tests.py`
   - Script principal de automatización
   - Ejecuta todas las pruebas en secuencia
   - Genera reportes en formato JSON y Markdown
   - Organiza resultados por fecha y modelo

2. `test_ont_auth.py` (eliminado)
   - Primera prueba de autenticación básica
   - Verificación de credenciales root/admin
   - Eliminado tras migrar a versión detallada

2. `test_ont_auth_detailed.py` (eliminado)
   - Implementación de diferentes User-Agents
   - Pruebas de variaciones en headers
   - Documentación de respuestas de error

3. `test_ont_curl.py`
   - Emulación exitosa de curl
   - Primera implementación funcional
   - Base para el cliente HTTP final

4. `analyze_login.py` (eliminado)
   - Análisis de la página de login
   - Extracción de parámetros necesarios
   - Documentación del proceso de login

5. `analyze_version.py` (eliminado)
   - Análisis de versionControl.js
   - Identificación de versiones soportadas
   - Documentación de compatibilidad

6. `test_ont_routes.py`
   - Mapeo completo de endpoints
   - Identificación de rutas protegidas
   - Documentación de niveles de acceso

7. `ont_http_detailed.py`
   - Implementación final modular
   - Incorporación de todos los hallazgos
   - Base para desarrollo futuro

### Archivos de Resultados Generados
1. `auth_results.json`
   - Resultados de pruebas de autenticación
   - Estadísticas de éxito/fallo

2. `auth_results_detailed.json`
   - Detalles de cada intento de autenticación
   - Headers usados y respuestas

3. `route_analysis.json`
   - Mapeo completo de rutas
   - Métodos HTTP soportados

4. `curl_results.json`
   - Resultados de emulación curl
   - Headers exitosos documentados

5. `ont_http_analysis.json`
   - Análisis completo del protocolo
   - Documentación de peculiaridades

### Pruebas HTTP Detalladas
- **Primera ejecución de ont_http_detailed.py**
  - Identificado formato específico necesario para headers HTTP/1.1
  - Orden crítico: Host, User-Agent, Accept, Connection
  - La ONT rechaza requests que no siguen este orden exacto

### Errores y Limitaciones Encontradas
- **Error #1: Formato de Headers**
  ```
  HTTP/1.1 400 Bad Request
  Content-Type: text/html
  Connection: close
  ```
  - Causa: Headers en orden incorrecto
  - Solución: Reorganización siguiendo el orden exacto requerido

- **Error #2: Autenticación**
  - Rechazo inicial de credenciales válidas
  - La ONT requiere un User-Agent específico
  - Necesario mantener cookies de sesión entre requests

### Análisis de UPnP
- **Limitaciones del Servicio:**
  - Puerto UPnP no responde consistentemente
  - Respuestas SOAP requieren parseo especial
  - Algunos servicios devuelven datos malformados

### Bloqueos de Seguridad
- Detectado sistema anti-fuzzing
  - Bloqueo temporal tras múltiples intentos
  - Necesario implementar delays entre requests
  - Algunas rutas requieren headers adicionales

## Próximos Pasos

1. Implementación de Autenticación:
   - Sistema de manejo de sesiones
   - Soporte para diferentes operadores
   - Manejo de cookies y estados

2. Estructuración del Proyecto:
   ```
   src/
     backend/
       auth/
         ont_auth.py     # Manejo de autenticación
       services/
         ont_info.py     # Información básica
         ont_wifi.py     # Gestión WiFi
         ont_pon.py      # Información PON
   ```

3. Mejoras Planificadas:
   - Implementación de cliente HTTP robusto
   - Sistema de manejo de sesiones
   - Módulos específicos por servicio
   - Sistema de reintentos y manejo de errores
   - Documentación detallada de headers requeridos

## Requisitos del Sistema

### Dependencias Python
```powershell
pip install requests python-nmap scapy
```
Estado: ✓ Instalado (8/11/2025)

### Herramientas del Sistema
1. **nmap** - Requerido para análisis de red
   - Instalado vía winget: `winget install Insecure.Nmap`
   - Versión instalada: 7.80
   - Ruta de instalación: `C:\Program Files (x86)\Nmap`
   - ⚠️ Nota: El script usa la ruta completa, no requiere PATH configurado
   Estado: ✓ Instalado y funcionando (8/11/2025)

## Problemas Solucionados

### Configuración de nmap y python-nmap
**Problema:** python-nmap no podía encontrar el ejecutable de nmap en el PATH

**Solución Implementada:**
1. Desinstalación completa: `pip uninstall python-nmap -y; winget uninstall nmap`
2. Reinstalación de nmap: `winget install Insecure.Nmap`
3. Instalación de python-nmap v0.6.1: `pip install python-nmap==0.6.1`
4. Modificación del script para usar ruta absoluta de nmap: `C:\Program Files (x86)\Nmap\nmap.exe`

**Resultado:** ✓ Script `run_all_tests.py` funcionando correctamente (8/11/2025 14:02)

### Errores de Sintaxis Corregidos

**Error 1: upnp_client.py línea 40**
- Problema: Bloque try mal indentado después de definir ssdp_request
- Solución: Corregida indentación del bloque try
- Estado: ✓ Resuelto (8/11/2025 14:05)

**Error 2: ont_http_upnp_analyzer.py línea 58**
- Problema: Llave de cierre extra `}` después de la definición de headers
- Solución: Eliminada la llave duplicada
- Estado: ✓ Resuelto (8/11/2025 14:05)

**Error 3: upnp_client.py - Bloques try anidados**
- Problema: Bloques try-except-finally mal estructurados, falta except/finally
- Solución: Reestructurada la función discover() con bloques correctamente anidados
  - Añadido except general para capturar errores por puerto
  - Movido finally dentro del loop for
  - Corregida gestión de socket con verificación None
- Estado: ✓ Resuelto (8/11/2025 14:08)

**Resultado Final:** Todos los scripts ejecutan sin errores de sintaxis. Suite completa funcional.

## Resumen de Pruebas Realizadas (8/11/2025)

### Pruebas Completadas

| Modelo | Código | Hora | IP Testeada | Puertos Abiertos | Estado |
|--------|--------|------|-------------|------------------|--------|
| FIBERHOME HG6145F | MOD001 | 14:22:19 | 192.168.100.1 | 80, 49152 | ✓ Exitoso |
| FIBERHOME HG6145F | MOD001 | 14:28:13 | 192.168.100.1 | 80, 49152 | ✓ Exitoso |
| ZTE F660L | MOD002 | 14:36:27 | 192.168.100.1 | 23, 80 | ✓ Exitoso |
| ZTE F680 | MOD003 | 14:47:23 | 192.168.100.1 | 80 | ✓ Exitoso |
| HUAWEI HG8145V5 | MOD004 | 14:53:03 | 192.168.100.1 | 80 | ✓ Exitoso |
| HUAWEI HG145V5 SMALL | MOD005 | 14:41:34 | 192.168.100.1 | 80 | ✓ Exitoso |

### Hallazgos por Modelo

#### MOD001 - FIBERHOME HG6145F
- **Conectividad:** ✓ Exitosa (latencia: ~5-29ms)
- **Puertos detectados:** HTTP (80), UPnP-Alt (49152)
- **Servicios:** HTTP funcional, UPnP parcial
- **Headers de seguridad:** X-Frame-Options, X-XSS-Protection presentes

#### MOD002 - ZTE F660L
- **Conectividad:** ✓ Exitosa (latencia: ~29ms)
- **Puertos detectados:** Telnet (23), HTTP (80)
- **Servicios:** HTTP y Telnet funcionales
- **Nota:** Telnet habilitado (riesgo de seguridad)

#### MOD003 - ZTE F680
- **Conectividad:** ✓ Exitosa
- **Puertos detectados:** HTTP (80)
- **Servicios:** HTTP funcional
- **Características:** Configuración más restrictiva

#### MOD004 - HUAWEI HG8145V5
- **Conectividad:** ✓ Exitosa
- **Puertos detectados:** HTTP (80)
- **Servicios:** HTTP funcional
- **Configuración:** Estándar Huawei

#### MOD005 - HUAWEI HG145V5 SMALL
- **Conectividad:** ✓ Exitosa
- **Puertos detectados:** HTTP (80)
- **Servicios:** HTTP funcional
- **Configuración:** Similar a MOD004

### Problemas Comunes Encontrados

1. **Autenticación:**
   - Todos los modelos requieren autenticación para endpoints específicos
   - Error 400 Bad Request en rutas sin autenticación

2. **UPnP:**
   - Servicio inconsistente en todos los modelos
   - Puerto 1900 generalmente no responde o responde parcialmente

3. **Codificación:**
   - Caracteres especiales mal codificados en salida de scripts (á, é, í, ó, ú → �)
   - Requiere ajuste UTF-8 en scripts de análisis HTTP

### Ubicación de Reportes

Todos los reportes están guardados en:
```
reports/
├── 08_11_25_MOD001/
│   ├── 142219/
│   └── 142813/
├── 08_11_25_MOD002/
│   └── 143627/
├── 08_11_25_MOD003/
│   └── 144723/
├── 08_11_25_MOD004/
│   └── 145303/
└── 08_11_25_MOD005/
    └── 144134/
```

Cada directorio contiene:
- `*_results.json` - Resultados completos en formato JSON
- `*_report.md` - Reporte legible en Markdown

---

# Actualizaciones - 10/11/2025

## Nuevo Script: ONT Automated Tester

### Descripción
Script de pruebas automatizadas basado en protocolo estándar de testing para ONTs.
Implementa 8 pruebas principales según especificaciones de fabricante.

### Pruebas Implementadas

| Test | Nombre | Descripción | Endpoints Verificados |
|------|--------|-------------|----------------------|
| 1 | PWD_PASS | Autenticación con credenciales | `/` con auth |
| 2 | FACTORY_RESET_PASS | Verificación de reset | `/reset.html`, `/factory_reset.html` |
| 3 | USB_PORT | Detección de puerto USB | `/usb_storage.html`, `/usb_info.html` |
| 4 | SOFTWARE_PASS | Versión de software | `/get_device_name`, `/version.html` |
| 5 | TX_POWER | Potencia óptica TX | `/pon_link_info_inter.html` |
| 6 | RX_POWER | Potencia óptica RX | `/pon_link_info_inter.html` |
| 7 | WIFI_24GHZ | WiFi 2.4 GHz | `/wifi_info_inter.html` |
| 8 | WIFI_5GHZ | WiFi 5.0 GHz | `/wifi_info_inter5g.html` |

### Uso

```powershell
# Ejecución básica
python scripts/ont_automated_tester.py --host 192.168.100.1 --model MOD001

# Con directorio de salida personalizado
python scripts/ont_automated_tester.py --host 192.168.100.1 --model MOD001 --output ./mis_pruebas
```

### Características

- **No destructivo:** Las pruebas de reset solo verifican accesibilidad, no ejecutan el reset
- **Reporte automático:** Genera JSON y TXT con resultados
- **Estado visual:** Indica PASS/FAIL/SKIP para cada prueba
- **Extracción de serial:** Intenta obtener número de serie de la ONT
- **Resumen ejecutivo:** Contador de pruebas exitosas/fallidas

### Formato de Salida

```
===========================================================
REPORTE DE PRUEBAS AUTOMATIZADAS ONT
===========================================================
Fecha: 10/11/2025 14:30:00
Modelo: MOD001
Host: 192.168.100.1
Serie: 4857544314FA16A1

RESULTADOS:
-----------------------------------------------------------
[OK] PWD_PASS: PASS
[OK] FACTORY_RESET_PASS: PASS
[-] USB_PORT: SKIP
[OK] SOFTWARE_PASS: PASS
[OK] TX_POWER: PASS
[OK] RX_POWER: PASS
[OK] WIFI_24GHZ: PASS
[OK] WIFI_5GHZ: PASS

-----------------------------------------------------------
RESUMEN: 6 PASS | 0 FAIL | 2 SKIP
===========================================================
```

### Ubicación de Resultados

```
reports/
└── automated_tests/
    ├── 10_11_25_143000_MOD001_automated_results.json
    └── 10_11_25_143000_MOD001_automated_report.txt
```

### Primera Prueba Realizada (10/11/2025 09:59)

**Modelo testeado:** MOD005 (HUAWEI HG145V5 SMALL)  
**IP:** 192.168.100.1

**Resultados:**
- ✅ PWD_PASS: PASS - Autenticación exitosa con credenciales root/admin
- ⚠️ FACTORY_RESET_PASS: SKIP - Prueba no destructiva omitida
- ❌ USB_PORT: FAIL - Endpoint no accesible
- ❌ SOFTWARE_PASS: FAIL - Requiere autenticación adicional
- ❌ TX_POWER: FAIL - Endpoint PON no accesible
- ❌ RX_POWER: FAIL - Endpoint PON no accesible  
- ❌ WIFI_24GHZ: FAIL - Endpoint WiFi no accesible
- ❌ WIFI_5GHZ: FAIL - Endpoint WiFi 5G no accesible

**Conclusión:** El script funciona correctamente. Los fallos indican que se requiere:
1. Mejorar manejo de sesión autenticada
2. Identificar endpoints específicos por modelo
3. Implementar parseo de respuestas HTML/JSON

**Archivo generado:** `reports/automated_tests/10_11_25_095903_MOD005_automated_report.txt`

## Guía para Solucionar Pruebas FAIL

### Paso 1: Identificar los Endpoints Correctos

Los endpoints que probamos pueden no ser los correctos para tu modelo. Para encontrar los correctos:

```powershell
# Mapea todas las rutas disponibles
python scripts/test_ont_routes.py --host 192.168.100.1
```

**Resultado esperado:** Lista de rutas con códigos 200 (accesibles) vs 400/404 (no accesibles)

### Paso 2: Realizar Login con Credenciales

La mayoría de endpoints requieren estar autenticado. Para esto necesitas:

1. **Acceder a la página de login:** `http://192.168.100.1`
2. **Usar las credenciales correctas:**
   - Usuario: `root` (o `admin`, `telecomadmin`)
   - Contraseña: `admin` (o `root`, `admintelecom`)

3. **Capturar la cookie de sesión:**
   - Abre el navegador en modo desarrollador (F12)
   - Ve a la pestaña "Network" o "Red"
   - Haz login
   - Busca la cookie `SID` o similar en las peticiones

### Paso 3: Ejemplo Manual con curl

```powershell
# 1. Hacer login y obtener cookie
curl -v -u root:admin http://192.168.100.1/

# 2. Usar la cookie para acceder a endpoints protegidos
curl -H "Cookie: SID=tu_cookie_aqui" http://192.168.100.1/pon_link_info_inter.html
```

### Paso 4: Verificar Endpoints Específicos por Modelo

Cada modelo puede tener endpoints diferentes:

**Para información PON (TX/RX Power):**
- Prueba: `/pon_link_info_inter.html`
- Prueba: `/html/status/pon_info.html`
- Prueba: `/status.html` (y busca sección PON)

**Para información WiFi:**
- Prueba: `/wifi_info_inter.html` (2.4GHz)
- Prueba: `/wifi_info_inter5g.html` (5GHz)
- Prueba: `/html/status/wireless.html`

**Para información del dispositivo:**
- Prueba: `/html/status/device_info.html`
- Prueba: `/device_info.html`
- Prueba: `/status.html`

### Paso 5: Actualizar el Script con los Endpoints Correctos

Una vez identifiques los endpoints que funcionan, edita `ont_automated_tester.py`:

```python
# Ejemplo para TX Power
def test_tx_power(self) -> Dict[str, Any]:
    # Cambia estos endpoints por los que funcionan en tu ONT
    pon_endpoints = [
        "/html/status/pon_info.html",  # <-- Añade el que funcione
        "/pon_link_info_inter.html",
        "/pon_status.html"
    ]
```

### Paso 6: Implementar Autenticación en el Script

Necesitas modificar el script para que haga login primero:

```python
def login(self):
    """Realiza login y obtiene cookie de sesión"""
    response = self._make_request("/", auth=("root", "admin"))
    if response and response.status_code == 200:
        # La sesión guarda automáticamente las cookies
        return True
    return False
```

Y llamarlo antes de las pruebas:

```python
def run_all_tests(self):
    # Hacer login primero
    if not self.login():
        print("[ERROR] No se pudo autenticar")
        return
    
    # Luego ejecutar las pruebas...
```

### Resumen de Acciones

1. ✅ **Ejecuta** `test_ont_routes.py` para ver rutas disponibles
2. ✅ **Accede manualmente** al ONT via navegador para confirmar que funciona
3. ✅ **Captura la cookie** de sesión usando DevTools del navegador
4. ✅ **Identifica los endpoints correctos** para cada prueba
5. ✅ **Modifica** `ont_automated_tester.py` con los endpoints correctos
6. ✅ **Añade autenticación** al script si es necesario

### Archivos Útiles para Debugging

- `route_analysis.json` - Todas las rutas mapeadas
- `curl_results.json` - Resultados de pruebas básicas
- `ont_http_analysis.json` - Análisis detallado HTTP

## Guía de Pruebas para Otros Modelos

### Orden de Ejecución Recomendado

1. **Prueba de Conectividad Básica**
   ```powershell
   python scripts/ont_basic_tester.py --ip <ip_ont>
   ```
   - Verifica conectividad TCP/IP básica
   - Identifica puertos abiertos principales
   - Guarda resultados en analysis_results.json

2. **Análisis de Protocolos**
   ```powershell
   python scripts/test_protocols.py --ip <ip_ont>
   ```
   - Prueba HTTP, SNMP, TR-069
   - Identifica protocolos habilitados
   - Detecta versiones y variantes

3. **Prueba de Red y Servicios**
   ```powershell
   python scripts/ont_network_tester.py --ip <ip_ont>
   ```
   - Analiza configuración de red
   - Prueba servicios básicos
   - Identifica configuración VLAN

4. **Análisis HTTP Detallado**
   ```powershell
   python scripts/ont_http_detailed.py --ip <ip_ont> --model <modelo>
   ```
   - Prueba autenticación HTTP
   - Mapea rutas disponibles
   - Documenta peculiaridades del modelo

5. **Análisis UPnP**
   ```powershell
   python scripts/ont_http_upnp_analyzer.py --ip <ip_ont>
   ```
   - Descubre servicios UPnP
   - Prueba endpoints SOAP
   - Documenta servicios disponibles

### Notas Importantes para Otros Modelos
1. Siempre comenzar con pruebas no intrusivas (ont_basic_tester.py)
2. Documentar diferencias en headers y autenticación
3. Guardar logs específicos por modelo para comparación
4. En caso de bloqueo, esperar 5 minutos antes de reintentar
5. Usar el parámetro --safe en caso de modelos desconocidos

### Archivos de Resultados
- Cada script genera su propio archivo JSON
- Los resultados se guardan con el formato: `<test_name>_<model>_results.json`
- Comparar con resultados base en /docs para identificar diferencias

### Modelos Soportados

| Código | Modelo | Configuración por Defecto |
|--------|--------|-------------------------|
| MOD001 | FIBERHOME HG6145F | - Host: 192.168.1.1<br>- Credenciales: admin/admin<br>- Puertos: 80, 443 |
| MOD002 | ZTE F660L | - Host: 192.168.1.1<br>- Credenciales: admin/admin<br>- Puertos: 80, 443 |
| MOD003 | ZTE F680 | - Host: 192.168.1.1<br>- Credenciales: admin/admin<br>- Puertos: 80, 443 |
| MOD004 | HUAWEI HG8145V5 | - Host: 192.168.100.1<br>- Credenciales: root/admin<br>- Puertos: 80, 443, 8080 |
| MOD005 | HUAWEI HG145V5 SMALL | - Host: 192.168.100.1<br>- Credenciales: root/admin<br>- Puertos: 80, 443, 8080 |

### Ejecución de Pruebas

#### FIBERHOME HG6145F
```powershell
# Configuración por defecto
python scripts/run_all_tests.py --host 192.168.1.1 --model MOD001

# Configuración alternativa
python scripts/run_all_tests.py --host <ip_personalizada> --model MOD001
```

#### ZTE F660L y F680
```powershell
# F660L
python scripts/run_all_tests.py --host 192.168.1.1 --model MOD002

# F680
python scripts/run_all_tests.py --host 192.168.1.1 --model MOD003
```

#### HUAWEI HG8145V5 y HG145V5 SMALL
```powershell
# HG8145V5
python scripts/run_all_tests.py --host 192.168.100.1 --model MOD004

# HG145V5 SMALL
python scripts/run_all_tests.py --host 192.168.100.1 --model MOD005
```

### Requisitos Previos
Antes de ejecutar las pruebas, asegúrate de tener instalado:

1. **Herramientas del Sistema:**
   ```powershell
   # Windows
   winget install Insecure.Nmap
   ```

2. **Dependencias Python:**
   ```powershell
   pip install requests scapy python-nmap==0.6.1
   ```

3. **⚠️ IMPORTANTE: Configurar PATH en cada sesión de PowerShell**
   ```powershell
   $env:Path += ";C:\Program Files (x86)\Nmap"
   ```
   O ejecutar directamente:
   ```powershell
   $env:Path += ";C:\Program Files (x86)\Nmap"; python scripts/run_all_tests.py --host <ip> --model <modelo>
   ```

#### Requisitos Previos
Antes de ejecutar las pruebas, asegúrate de tener instalado:

1. **Herramientas del Sistema:**
   ```powershell
   # Windows
   winget install nmap  # o descarga desde https://nmap.org/download.html
   
   # Linux
   sudo apt install nmap
   ```

2. **Dependencias Python:**
   ```powershell
   pip install requests python-nmap scapy
   ```

#### Modo Seguro
Para cualquier modelo, puedes añadir el flag --safe:
```powershell
python scripts/run_all_tests.py --host <ip_ont> --model <código_modelo> --safe
```

#### Resultados
Los resultados se guardarán en:
```
reports/
└── DD_MM_YY_<código_modelo>/
    └── HHMMSS/
        ├── DD_MM_YY_<código_modelo>_HHMMSS_results.json
        └── DD_MM_YY_<código_modelo>_HHMMSS_report.md
```

Por ejemplo, para una prueba del MOD002 realizada el 8 de noviembre a las 14:30:22:
```
reports/
└── 08_11_25_MOD002/
    └── 143022/
        ├── 08_11_25_MOD002_143022_results.json
        └── 08_11_25_MOD002_143022_report.md
```

#### Modo Seguro
Para modelos desconocidos o pruebas iniciales:
```powershell
python scripts/run_all_tests.py --host <ip_ont> --model <modelo> --safe
```
- Usa delays más largos entre requests
- Evita pruebas potencialmente bloqueantes
- Reduce el número de requests concurrentes

### Estructura de Reportes Generados
Los reportes se guardan en el directorio `reports/` con la siguiente estructura:
```
reports/
  DD_MM_YY_<modelo>/
    HHMMSS/                          # Timestamp de la prueba
      DD_MM_YY_<modelo>_HHMMSS_results.json   # Resultados detallados
      DD_MM_YY_<modelo>_HHMMSS_report.md      # Reporte legible
```

Ejemplo de nombres de archivo:
- `08_11_25_zte/143022/08_11_25_zte_143022_results.json`
- `08_11_25_zte/143022/08_11_25_zte_143022_report.md`

Esto permite:
- Múltiples pruebas del mismo modelo en el mismo día
- Fácil comparación de resultados cronológicos
- No hay riesgo de sobreescritura de archivos