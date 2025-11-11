# ONT Tester - Sistema Automatizado de Testing

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Pending-yellow)]()
[![Status](https://img.shields.io/badge/Status-Active-success)]()

Sistema automatizado para testing, diagnóstico y análisis de dispositivos ONT (Optical Network Terminal) de múltiples fabricantes.

---

## 🎯 Características Principales

- ✅ **12 Tests Automatizados**: Suite completa de validación
- ✅ **Auto-detección de Modelo**: Identifica automáticamente el dispositivo
- ✅ **3 Modos de Operación**: Test / Retest / Label
- ✅ **Cálculo de SN Físico**: Algoritmo automático para MOD001
- ✅ **Reportes Detallados**: JSON + TXT con toda la información
- ✅ **Etiquetas Imprimibles**: Generación de labels identificativos
- ✅ **Multi-fabricante**: Soporte para Fiberhome, Huawei, ZTE

---

## 📊 Estado del Proyecto

| Métrica | Valor |
|---------|-------|
| **Tests Implementados** | 12/12 (100%) |
| **Tests Passing** | 6/12 (50%) |
| **RF Completados** | 9/31 (29%) |
| **Modelos Soportados** | 5 |

**Resultado Actual**: `6 PASS | 5 FAIL | 1 SKIP`

---

## 🚀 Inicio Rápido

### Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd "ONT Tester"

# Instalar dependencias
pip install -r requirements.txt
```

### Uso Básico

```bash
# Test completo (auto-detecta modelo)
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode test

# Retest de pruebas fallidas
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode retest

# Generar etiqueta imprimible
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode label
```

### Ejemplo de Salida

```
============================================================
ONT AUTOMATED TEST SUITE
Host: 192.168.100.1
============================================================

[AUTH] Modelo detectado automaticamente: MOD001 (HG6145F1)
[AUTH] Serial Number (Logico): FHTT9E222B98
[AUTH] Serial Number (Fisico/PON): 464854549E222B98 (calculado)

[TEST] PWD PASS - Autenticacion
[TEST] CONNECTIVITY - Ping
[TEST] CONNECTIVITY - HTTP
...

RESUMEN: 6 PASS | 5 FAIL | 1 SKIP
============================================================
```

---

## 📋 Tests Implementados

| # | Test | Status | Descripción |
|---|------|--------|-------------|
| 1 | PWD_PASS | ✅ | Autenticación Basic Auth |
| 2 | FACTORY_RESET | ⏭️ | Skip (no destructivo) |
| 3 | PING_CONNECTIVITY | ✅ | Latencia ICMP |
| 4 | HTTP_CONNECTIVITY | ✅ | Tiempo respuesta HTTP |
| 5 | PORT_SCAN | ✅ | Escaneo de puertos |
| 6 | DNS_RESOLUTION | ✅ | Resolución DNS |
| 7 | USB_PORT | ❌ | Requiere login completo |
| 8 | SOFTWARE_PASS | ✅ | Versión de software |
| 9 | TX_POWER | ❌ | Requiere login completo |
| 10 | RX_POWER | ❌ | Requiere login completo |
| 11 | WIFI_24GHZ | ❌ | Requiere login completo |
| 12 | WIFI_5GHZ | ❌ | Requiere login completo |

---

## 🔧 Modelos Soportados

| Código | Modelo | Fabricante | SN Físico |
|--------|--------|------------|-----------|
| MOD001 | HG6145F / HG6145F1 | Fiberhome | ✅ Auto-calculable |
| MOD002 | F670L | ZTE | ⚠️ Manual |
| MOD003 | HG8145X6-10 | Huawei | ⚠️ Manual |
| MOD004 | HG8145V5 | Huawei | ⚠️ Manual |
| MOD005 | HG145V5 SMALL | Huawei | ⚠️ Manual |

---

## 📁 Estructura del Proyecto

```
ONT Tester/
├── scripts/                     # Scripts principales
│   ├── ont_automated_tester.py # ⭐ Suite principal
│   ├── ont_network_tester.py
│   ├── ont_http_detailed.py
│   ├── deprecated/              # Scripts obsoletos (evidencia)
│   ├── research/                # Scripts de investigación
│   └── standalone_tools/        # Herramientas útiles
│
├── data/                        # Datos de análisis
│   ├── html_snapshots/
│   ├── js_files/
│   └── analysis_results/
│
├── docs/                        # Documentación
│   └── DOCUMENTATION_COMPLETE.md # 📖 Documentación completa
│
├── reports/                     # Reportes generados
│   ├── automated_tests/
│   └── labels/
│
├── config/                      # Configuración
├── requirements.txt             # Dependencias
└── README.md                    # Este archivo
```

---

## 🎮 Modos de Operación

### Modo TEST
Ejecuta suite completo de 12 tests.
```bash
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode test
```

### Modo RETEST
Ejecuta solo tests fallidos del último reporte.
```bash
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode retest
```

### Modo LABEL
Genera etiqueta imprimible con información del dispositivo.
```bash
python scripts/ont_automated_tester.py --host 192.168.100.1 --mode label
```

---

## 📖 Documentación

La documentación completa está disponible en:
- **[docs/DOCUMENTATION_COMPLETE.md](docs/DOCUMENTATION_COMPLETE.md)** - Documentación técnica completa
- **[scripts/README_ORGANIZATION.md](scripts/README_ORGANIZATION.md)** - Organización de scripts

### Contenido de la Documentación

1. Resumen Ejecutivo
2. Arquitectura del Sistema
3. Métodos AJAX Descubiertos (43 probados, 7 accesibles)
4. Requisitos Funcionales (31 RF totales)
5. Tests Implementados (12 tests)
6. Modos de Operación
7. Patrón de Serial Numbers
8. Guía de Uso
9. Roadmap

---

## 🔒 Seguridad

### Credenciales Default
```
Usuario: root
Password: admin
```

⚠️ **Nota**: Cambiar credenciales default en dispositivos de producción.

### Puertos Detectados
- **80 (HTTP)**: Interface web
- **23 (Telnet)**: ⚠️ Recomendado deshabilitar

---

## 🐛 Problemas Conocidos

### 1. fhencrypt() - Login Completo Bloqueado
**Status**: 🔴 En investigación  
**Impacto**: 5/12 tests (USB, TX/RX Power, WiFi) requieren `do_login` con password encriptada  
**Workaround**: Tests funcionales usan Basic Auth

### 2. MAC Address No Disponible
**Status**: 🟡 Bloqueado por fhencrypt()  
**Workaround**: Usar Serial Number como identificador

### 3. Patrón SN Físico Incompleto
**Status**: 🟡 Solo MOD001 implementado  
**Requiere**: Más dispositivos para análisis de patrones

---

## 🗺️ Roadmap

### ✅ Fase 1: Tests Básicos (COMPLETADO)
- [x] Auto-detección de modelo
- [x] Tests de conectividad
- [x] 6/12 tests funcionales
- [x] Cálculo SN Físico MOD001

### 🔄 Fase 2: Login Completo (EN PROGRESO)
- [ ] Reverse-engineering fhencrypt()
- [ ] Implementar do_login completo
- [ ] Desbloquear 5 tests restantes

### ⏳ Fase 3: Completar RF (PENDIENTE)
- [ ] RF 010: MAC Address
- [ ] RF 016: Etiquetas PDF
- [ ] RF 027: Parser de errores
- [ ] 22 RF restantes

### 🚀 Fase 4: Avanzado (FUTURO)
- [ ] Web interface
- [ ] Tests en paralelo
- [ ] Dashboard en tiempo real

---

## 🤝 Contribución

Las contribuciones son bienvenidas! Áreas que necesitan ayuda:

- 🔍 Reverse-engineering de `fhencrypt()`
- 📐 Descubrir patrones SN Físico MOD002-005
- 🧪 Tests unitarios
- 📝 Documentación
- 🎨 UI/Web interface

### Cómo Contribuir
1. Fork el proyecto
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar funcionalidad'`)
4. Push a branch (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

---

## 📜 Licencia

**Pendiente de definir**

---

## 📞 Soporte

- **Documentación**: [docs/DOCUMENTATION_COMPLETE.md](docs/DOCUMENTATION_COMPLETE.md)
- **Issues**: Reportar en GitHub Issues
- **Email**: [Pendiente]

---

## 📊 Métricas

```
Tests:     ████████████░░░░░░░░  50%  (6/12 PASS)
RF:        ███░░░░░░░░░░░░░░░░░  29%  (9/31)
Modelos:   █████████████████████ 100%  (5/5)
```

---

## 🏆 Logros

- ✅ Descubrimiento de 43 métodos AJAX
- ✅ Reverse-engineering de patrón SN Físico MOD001
- ✅ Sistema de auto-detección de modelo
- ✅ 3 modos de operación implementados
- ✅ Suite completa de 12 tests

---

**Última Actualización**: 10/11/2025  
**Versión**: 1.0.0  
**Status**: ✅ Listo para Pull Request

1. Active el entorno virtual:
```bash
.\venv\Scripts\activate
```

2. Ejecute la aplicación:
```bash
python main.py
```

## Configuración

La configuración del sistema se puede personalizar a través de los archivos en el directorio `config/`:
- `settings.py`: Configuraciones generales del sistema
- `constants.py`: Definición de constantes globales

## Características Principales

- Diagnóstico automático de ONTs
- Pruebas de conectividad
- Medición de rendimiento
- Generación de reportes
- Soporte para múltiples modelos de ONT

## Contribución

1. Fork del repositorio
2. Cree una rama para su característica (`git checkout -b feature/AmazingFeature`)
3. Commit de sus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abra un Pull Request

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - vea el archivo `LICENSE` para más detalles.

## Soporte

Para soporte, por favor abra un issue en el repositorio o contacte al equipo de desarrollo.

---
Desarrollado con ❤️ por el equipo de ONT Tester
