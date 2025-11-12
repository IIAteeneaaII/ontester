# Estructura de Reportes - ONT/ATA Testing Suite

## 📁 Organización de Archivos

A partir del **11 de noviembre de 2025**, todos los reportes y etiquetas se organizan automáticamente en subdirectorios por fecha.

### Estructura de Directorios

```
reports/
├── automated_tests/
│   ├── 10_11_25/          # Reportes del 10/11/2025
│   │   ├── *_MOD001_automated_results.json
│   │   ├── *_MOD001_automated_report.txt
│   │   ├── *_MOD005_automated_results.json
│   │   └── ...
│   ├── 11_11_25/          # Reportes del 11/11/2025
│   │   ├── *_MOD001_automated_results.json
│   │   ├── *_MOD006_automated_results.json
│   │   └── ...
│   └── dd_mm_yy/          # Futuros reportes por fecha
│
└── labels/
    ├── 10_11_25/          # Etiquetas del 10/11/2025
    │   ├── *_MOD001_*_label.txt
    │   └── ...
    └── 11_11_25/          # Etiquetas del 11/11/2025
        └── ...
```

## 🔧 Uso

### Ejecutar Tests Automáticos

```bash
# Test completo (detecta tipo automáticamente)
python ont_automated_tester.py --host <IP> --mode test

# Ejemplos:
python ont_automated_tester.py --host 192.168.100.1 --mode test  # ONT
python ont_automated_tester.py --host 192.168.2.1 --mode test     # HT818
```

**Resultado:** Archivos guardados en `reports/automated_tests/dd_mm_yy/`

### Generar Etiqueta de Identificación

```bash
python ont_automated_tester.py --host <IP> --mode label
```

**Resultado:** Etiqueta guardada en `reports/labels/dd_mm_yy/`

### Re-ejecutar Solo Tests Fallidos

```bash
python ont_automated_tester.py --host <IP> --mode retest
```

**Comportamiento:**
- Busca el último reporte en todos los subdirectorios de fecha
- Ejecuta solo los tests que fallaron
- Guarda resultados con prefijo `retest` en el subdirectorio de la fecha actual

### Visualizar Estructura de Reportes

```bash
# Ver estructura completa
python view_reports_structure.py

# Ver últimos N reportes
python view_reports_structure.py --latest 10
```

## 📊 Formato de Nombres de Archivo

### Reportes Automáticos

```
dd_mm_yy_HHMMSS_MODELO_automated_results.json
dd_mm_yy_HHMMSS_MODELO_automated_report.txt

Ejemplo:
11_11_25_180313_MOD006_automated_results.json
11_11_25_180313_MOD006_automated_report.txt
```

### Reportes de Retest

```
dd_mm_yy_HHMMSS_MODELO_retest_results.json
dd_mm_yy_HHMMSS_MODELO_retest_report.txt

Ejemplo:
11_11_25_122440_MOD001_retest_results.json
11_11_25_122440_MOD001_retest_report.txt
```

### Etiquetas

```
dd_mm_yy_HHMMSS_MODELO_SERIAL_label.txt

Ejemplo:
11_11_25_180320_MOD001_FHTTC1166D5C_label.txt
11_11_25_175738_MOD006_UNKNOWN_label.txt
```

## 🎯 Ventajas de la Organización por Fecha

1. **Búsqueda rápida:** Encontrar reportes de una fecha específica
2. **Gestión de espacio:** Fácil limpieza de reportes antiguos
3. **Historial claro:** Ver evolución de tests por día
4. **Sin saturación:** Directorios con menos archivos
5. **Organización automática:** Sin intervención manual

## 📈 Estadísticas

Para ver estadísticas y resumen de todos los reportes:

```bash
python view_reports_structure.py
```

Muestra:
- Total de reportes por fecha
- Modelos testeados
- Cantidad de tests y retests
- Etiquetas generadas
- Última actividad

## 🔄 Migración de Archivos Antiguos

Los archivos existentes antes de esta actualización fueron migrados automáticamente a subdirectorios según su fecha de creación:

```bash
# Migración automática ejecutada el 11/11/2025
reports/automated_tests/10_11_25/  # 24 archivos migrados
reports/automated_tests/11_11_25/  # Archivos nuevos + migrados
reports/labels/10_11_25/           # 4 etiquetas migradas
```

## 📝 Notas Técnicas

### Formato de Fecha

- **Subdirectorios:** `dd_mm_yy` (ejemplo: `11_11_25`)
- **Timestamps completos:** `dd_mm_yy_HHMMSS` (ejemplo: `11_11_25_180313`)

### Creación Automática

Los subdirectorios se crean automáticamente:
- Si el directorio de fecha ya existe, se agregan archivos nuevos
- Si no existe, se crea y se guardan los archivos

### Búsqueda de Reportes Previos (Retest)

El modo retest busca en TODOS los subdirectorios de fecha, ordenados de más reciente a más antiguo, para encontrar el último reporte generado.

## 🛠️ Mantenimiento

### Limpiar Reportes Antiguos

```bash
# Eliminar reportes de una fecha específica
Remove-Item reports/automated_tests/10_10_25 -Recurse -Force

# Listar tamaño de cada directorio de fecha
Get-ChildItem reports/automated_tests -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "$($_.Name): $([Math]::Round($size, 2)) MB"
}
```

### Archivar Reportes

```bash
# Comprimir reportes de un mes
Compress-Archive -Path "reports/automated_tests/10_11_25" -DestinationPath "archive/automated_tests_10_11_25.zip"
```

---

**Última actualización:** 11 de noviembre de 2025  
**Versión:** 2.0 (Organización por fecha)
