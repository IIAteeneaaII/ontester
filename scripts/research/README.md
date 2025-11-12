# Research Scripts - ONT Tester

Directorio de scripts de investigación y testing experimental.

## 📁 Estructura

```
research/
├── results/              # Resultados de pruebas (JSON/TXT)
├── discover_*.py         # Scripts de descubrimiento
├── test_*.py            # Scripts de testing específico
├── analyze_*.py         # Scripts de análisis
└── diagnose_*.py        # Herramientas de diagnóstico
```

## 🔧 Scripts Disponibles

### Descubrimiento

- **`discover_ajax_methods.py`** - Descubre métodos AJAX en ONTs
- **`discover_ht818.py`** - Descubrimiento específico para Grandstream HT818
- **`diagnose_device.py`** - Identifica tipo de dispositivo en una IP

### Testing Específico

- **`test_wifi.py`** - Prueba WiFi 2.4G y 5G (indicadores verde/rojo)
- **`test_usb_functionality.py`** - Prueba funcionalidad USB completa
- **`test_pon_*.py`** - Varios scripts de testing PON

### Análisis

- **`analyze_pon_info.py`** - Análisis completo de información PON con simulación

## 📊 Directorio Results

Contiene todos los archivos JSON y TXT generados por los scripts de investigación:

- `ajax_methods_analysis.json` - Mapeo completo de métodos AJAX
- `ht818_discovery_*.json` - Resultados de descubrimiento HT818
- `pon_analysis_*.json` - Análisis de información PON
- `wifi_test_*.json` - Resultados de pruebas WiFi
- `usb_test_*.json` - Resultados de pruebas USB

## 🚀 Uso Rápido

```powershell
# WiFi (modo rápido)
python test_wifi.py --host 192.168.100.1 --quick

# PON (con simulación)
python analyze_pon_info.py --host 192.168.100.1 --simulate

# Diagnóstico
python diagnose_device.py 192.168.100.1

# Descubrimiento HT818
python discover_ht818.py --host <IP_HT818>
```

## ⚠️ Notas

- Los scripts de ONT (test_wifi, analyze_pon, test_usb) son **solo compatibles con MOD001-MOD005**
- El HT818 (MOD006) requiere scripts específicos diferentes
- Usar `diagnose_device.py` primero para identificar el tipo de dispositivo
- Los archivos en `results/` se generan automáticamente con timestamp

## 📖 Documentación

Ver reportes completos en `docs/`:
- `11_11_2025_reporte_investigacion_completo.md` - Reporte consolidado
- `11_11_2025_soporte_ht818_mod006.md` - Detalles específicos HT818
