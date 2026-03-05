# Suite de Pruebas (pytest)

Este directorio contiene la infraestructura y el conjunto de pruebas automatizadas del proyecto.
El objetivo es poder validar lógica, flujo de eventos (backend → UI) y operaciones con BD de manera
repetible, sin depender de hardware real (routers, fibra óptica) en la mayoría de los casos.

## Filosofía de pruebas (capas)

La suite se divide por niveles, para evitar pruebas frágiles y lentas:

- **Unit**: Pruebas rápidas, sin red, sin Selenium real, sin UI real, sin BD real.
  Se prueban funciones puras y pequeñas piezas de lógica. Se usan mocks/monkeypatch.
- **Integration**: Pruebas con componentes reales pero controlados (por ejemplo SQLite temporal,
  colas reales, dispatcher real sin abrir interfaz).
- **E2E (opcional)**: Pruebas completas (Selenium real / router real). Son pocas y se ejecutan
  sólo cuando es necesario (son lentas y más frágiles).

---

## Estructura del directorio `tests/`

### `tests/unit/`
Pruebas unitarias (rápidas). Reglas:
- No se permite red real, Selenium real, impresiones reales o hardware real.
- Todo I/O se simula con mocks.
- Deben ejecutarse en segundos.

**Contenido típico**:
- Normalización: `norm_result`, `norm_power`, conversiones, parsing seguro.
- Validaciones: “valido por modo”, umbrales TX/RX, umbrales WiFi.
- Parsers: extracción de datos desde HTML/XML (Huawei/ZTE/Fiberhome) usando strings guardados.
- Lógica de “update parcial”: payload de unitaria NO debe pisar campos no presentes.

Subcarpetas:
- `tests/unit/backend/`: lógica del backend.
- `tests/unit/frontend/`: funciones de render/parsing de eventos hacia UI (sin abrir ventanas).
- `tests/unit/shared/`: utilidades comunes (si aplica).

### `tests/integration/`
Pruebas de integración (moderadas). Validan interacción real entre componentes internos.
Reglas:
- Se permiten componentes reales *controlados* (SQLite temporal, colas reales, dispatcher).
- No se requiere hardware real.
- Deben ser pocas y enfocadas.

Subcarpetas:
- `tests/integration/db/`: valida operaciones reales con BD (inserts, updates, upserts, constraints).
  Normalmente usa SQLite temporal (archivo o in-memory) con schema del proyecto.
- `tests/integration/events/`: valida “contratos” de eventos backend → frontend:
  - que el backend emite eventos esperados
  - que la UI consume sin pisar campos no presentes
  - que no se pierden eventos al reiniciar/recargar vistas (cuando aplique)

### `tests/e2e/` (opcional)
Pruebas end-to-end. Se usan cuando es necesario validar un flujo completo real.
Ejemplos:
- Selenium real contra router real (ZTE/Huawei/Fiberhome).
- Pruebas de “login + navegación + extracción”.

**Importante**:
- Estas pruebas NO deben correr por defecto.
- Deben quedar aisladas y ejecutarse manualmente o bajo un flag.

### `tests/fixtures/`
Datos estáticos de prueba para alimentar unit/integration tests.

Subcarpetas:
- `tests/fixtures/payloads/`:
  - JSONs que simulan payloads reales emitidos por el backend.
  - Ejemplos: `payload_full_pass.json`, `payload_unit_usb.json`, `payload_fibra_fail.json`, etc.
- `tests/fixtures/html/`:
  - HTMLs reales guardados para detección de modelos o parseos.
  - Ejemplos: login pages Huawei/ZTE, respuestas AJAX XML, etc.

### `tests/conftest.py`
Archivo global de pytest donde se definen **fixtures reutilizables**.
Ejemplos:
- `out_q` (queue real) para simular el canal de eventos.
- `fake_config` / monkeypatch de `cargarConfig()`.
- `tmp_db` (SQLite temporal) para integration tests.
- utilidades para cargar fixtures JSON/HTML.

---

## Cómo correr las pruebas

### 1) Instalar dependencias de pruebas
En un entorno virtual recomendado:

```bash
pip install -r requirements-dev.txt
# o si no existe:
pip install pytest
```

### 2) Ejecutar todo
```bash
pytest
```

### 3) Ejecutar solo unitarias
```
pytest test/unit
```

### 4) Ejecutar solo integración
```
pytest test/integration
```

### 5) Ejecutar un archivo específico
```
pytest test/unit/backend/test_wifi_logic.py
py -m pytest tests/unit/test_sanity.py
```

### 6) Ejecutar una prueba específica (por nombre)
```
pytest -k "wifi"
```

## Nomenclatura de tests
Cada test debe tener una nomenclatura específica para ser reconocido de manera correcta por la herramienta *pytest*. 

### Clases
Todas las clases de pruebas deben iniciar con **Test...** sin poner __init__ ya que puede alterar el comportamiento de la prueba.

### Funciones
Las funciones deben incluir la palabra *test*, de preferencia que sean *test_algo*

### Ejemplo
```py
class TestLogin:
    def test_ok(self):
        assert True

    # Estrucura común: Arrange - Act - Assert
    def test_calcula_total_con_descuento(self):
        # Arrange (preparar)
        subtotal = 100
        descuento = 0.1

        # Act (ejecutar)
        total = subtotal * (1 - descuento)

        # Assert (verificar)
        assert total == 90
```

## Probando escenarios
Para probar escenarios sin tener que hacer copy, estos parametros son decoradores para la función inmediata, por lo que una función con los mismos nombres de parámetros pero declarada después de la función 1 no servirá. En caso de buscar reutilizar parámetros vea la siguiente sección.

```py
import pytest

@pytest.mark.parametrize(
    "subtotal, descuento, esperado",
    [
        (100, 0.10, 90),
        (200, 0.25, 150),
        (50, 0.00, 50),
    ],
)

def test_total_con_descuento(subtotal, descuento, esperado):
    total = subtotal *(1-descuento)
    assert total == esperado
```

## Reutilizables
Para utilizar elementos compartidos (payload, cliente, db, etc.), por convención dentro de *conftest.py*

```py
import pytest

@pytest.fixture
def payload_base():
    return {"modo": "TESTEO", "info": {}, "tests": {}}

def test_payload_tiene_modo(payload_base):
    assert payload_base["modo"] == "TESTEO"
```