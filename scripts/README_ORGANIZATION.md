# Organización de Scripts

## 📁 Estructura

### `/scripts/` (Raíz - Scripts Principales)
Scripts de producción que se usan activamente:

- **`ont_automated_tester.py`** - ⭐ Suite completa de 12 tests automatizados
- **`run_all_tests.py`** - Suite legacy de tests separados
- **`ont_http_detailed.py`** - Análisis HTTP por modelo
- **`ont_http_upnp_analyzer.py`** - Análisis UPnP
- **`ont_network_tester.py`** - Tests de red/conectividad
- **`ont_basic_tester.py`** - Tests básicos de conectividad
- **`test_protocols.py`** - Análisis de protocolos

---

### `/scripts/deprecated/` 
Scripts obsoletos pero conservados como evidencia:

**Reemplazados por `ont_automated_tester.py`:**
- `ont_auth_tester.py` - Reemplazado por RF 001-003 del automated tester
- `test_login_ajax.py` - Integrado en automated tester
- `test_ajax_post.py` - Integrado en automated tester
- `network_tester.py` - Funcionalidad movida a ont_network_tester.py

**Superseded por nuevos métodos:**
- `test_ont_curl.py` - Tests con curl (ahora usamos requests)
- `test_ont_routes.py` - Análisis de rutas (integrado en otros tests)

---

### `/scripts/research/`
Scripts de investigación/descubrimiento (NO borrar - evidencia importante):

**Descubrimiento de endpoints:**
- `discover_endpoints.py` - Primera versión de descubrimiento
- `discover_all_endpoints.py` - Versión mejorada
- `discover_ajax_methods.py` - Descubrimiento de métodos AJAX

**Investigación de Serial Numbers:**
- `analyze_serial_numbers.py` - 🔍 CLAVE: Descubrió patrones MOD001/MOD005
- `find_real_serial.py` - Búsqueda del SN físico
- `find_mac_address.py` - Investigación de MAC address
- `find_mac_post.py` - Variante con POST

**Análisis de páginas:**
- `inspect_ont_page.py` - Inspección de HTML
- `extract_device_info.py` - Extracción de info del dispositivo
- `extract_mod001_info.py` - Extracción específica MOD001

**Otros:**
- `download_js_files.py` - Descarga de JS para análisis
- `enable_ssh_any.py` - Intento de habilitar SSH

---

### `/scripts/standalone_tools/`
Herramientas independientes útiles:

- `calculate_physical_sn.py` - Calculadora de SN Físico (standalone)

---

## 🔄 Scripts Migrados a Automated Tester

El archivo `ont_automated_tester.py` consolidó funcionalidad de:

| Script Original | RF en Automated Tester |
|----------------|------------------------|
| `ont_auth_tester.py` | RF 001, 002, 003 |
| `test_login_ajax.py` | RF 001 |
| `test_ajax_post.py` | RF 004-012 |
| `analyze_serial_numbers.py` | `_calculate_physical_sn()` |

---

## ⚠️ Comandos para Reorganizar

```powershell
# DEPRECATED - Scripts obsoletos
Move-Item "scripts\ont_auth_tester.py" "scripts\deprecated\"
Move-Item "scripts\test_login_ajax.py" "scripts\deprecated\"
Move-Item "scripts\test_ajax_post.py" "scripts\deprecated\"
Move-Item "scripts\network_tester.py" "scripts\deprecated\"
Move-Item "scripts\test_ont_curl.py" "scripts\deprecated\"
Move-Item "scripts\test_ont_routes.py" "scripts\deprecated\"

# RESEARCH - Scripts de investigación
Move-Item "scripts\discover_endpoints.py" "scripts\research\"
Move-Item "scripts\discover_all_endpoints.py" "scripts\research\"
Move-Item "scripts\discover_ajax_methods.py" "scripts\research\"
Move-Item "scripts\analyze_serial_numbers.py" "scripts\research\"
Move-Item "scripts\find_real_serial.py" "scripts\research\"
Move-Item "scripts\find_mac_address.py" "scripts\research\"
Move-Item "scripts\find_mac_post.py" "scripts\research\"
Move-Item "scripts\inspect_ont_page.py" "scripts\research\"
Move-Item "scripts\extract_device_info.py" "scripts\research\"
Move-Item "scripts\extract_mod001_info.py" "scripts\research\"
Move-Item "scripts\download_js_files.py" "scripts\research\"
Move-Item "scripts\enable_ssh_any.py" "scripts\research\"

# STANDALONE TOOLS - Herramientas útiles
Move-Item "scripts\calculate_physical_sn.py" "scripts\standalone_tools\"
```

---

## ✅ Resultado Final en `/scripts/`

Después de reorganizar, la raíz de `/scripts/` quedará solo con:

```
scripts/
├── ont_automated_tester.py     ⭐ PRINCIPAL
├── run_all_tests.py            (legacy suite)
├── ont_http_detailed.py
├── ont_http_upnp_analyzer.py
├── ont_network_tester.py
├── ont_basic_tester.py
├── test_protocols.py
├── README_ORGANIZATION.md      (este archivo)
├── deprecated/                 (16 scripts)
├── research/                   (12 scripts)
└── standalone_tools/           (1 script)
```

---

## 📝 Notas

- **NO eliminar**: Todos los scripts tienen valor histórico
- **Deprecated**: Funcionan pero hay mejores alternativas
- **Research**: Evidencia del proceso de descubrimiento (IMPORTANTE)
- **Standalone Tools**: Útiles para tareas específicas
