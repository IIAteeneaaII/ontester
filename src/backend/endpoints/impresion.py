from pathlib import Path
import win32print


# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(r"C:\ONT\zebra_templates")

# modelo -> nombre de plantilla en impresora
TEMPLATE_BY_MODEL = {
    "HG6145F": ["R:fiberFA.ZPL", "R:fiberFB.ZPL"],
    "HG6145F1": ["R:fiberF1A.ZPL", "R:fiberFB.ZPL"],
    "F670L": ["R:zte1.ZPL", "R:zte2.ZPL"], 
    "F6600": ["R:zte1.ZPL", "R:zte3.ZPL"], 
    "HG8145X6-10": "R:x6-10.ZPL",
    "HG8145X6": "R:x6.ZPL",
    "HG8145V5": "R:V5.ZPL",
    "DESCONOCIDO": "R:V5.ZPL",
}

# modelo -> archivo local que instala la plantilla
TEMPLATE_FILE_BY_MODEL = {
    "HG6145F": [BASE_DIR / "fiberFA.prn", BASE_DIR / "fiberFB.prn"],
    "HG6145F1": [BASE_DIR / "fiberF1A.prn", BASE_DIR / "fiberFB.prn"],
    "F670L": [BASE_DIR / "zte1.prn", BASE_DIR / "zte2.prn"],
    "F6600": [BASE_DIR / "zte1.prn", BASE_DIR / "zte3.prn"],
    "HG8145X6-10": BASE_DIR / "x6-10.prn",
    "HG8145X6": BASE_DIR / "x6.prn",
    "HG8145V5": BASE_DIR / "V5.prn",
    "DESCONOCIDO": BASE_DIR / "V5.prn",
}

# Control simple en memoria para no reinstalar en cada impresión
_TEMPLATES_INSTALLED = set()

def _ensure_list(value):
    if isinstance(value, list):
        return value
    return [value]

def escape_zpl(value: str) -> str:
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace("^", "\\^").replace("~", "\\~")


def send_raw_to_printer(printer_name: str, zpl: str) -> None:
    hprinter = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(hprinter, 1, ("Etiqueta Zebra", None, "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, zpl.encode("utf-8"))
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)

def obtener_template_path(modelo: str) -> str:
    modelo = (modelo or "DESCONOCIDO").upper()
    return TEMPLATE_BY_MODEL.get(modelo, TEMPLATE_BY_MODEL["DESCONOCIDO"])


def obtener_template_file(modelo: str) -> Path:
    modelo = (modelo or "DESCONOCIDO").upper()
    return TEMPLATE_FILE_BY_MODEL.get(modelo, TEMPLATE_FILE_BY_MODEL["DESCONOCIDO"])

def instalar_template(printer_name: str, template_file: Path) -> None:
    if not template_file.exists():
        raise FileNotFoundError(f"No existe la plantilla local: {template_file}")

    zpl = template_file.read_text(encoding="utf-8", errors="ignore")
    send_raw_to_printer(printer_name, zpl)


def asegurar_templates_instalados(printer_name: str, modelo: str) -> list[str]:
    template_paths = _ensure_list(obtener_template_path(modelo))
    template_files = _ensure_list(obtener_template_file(modelo))

    if len(template_paths) != len(template_files):
        raise ValueError(
            f"[ZEBRA] Desajuste entre rutas y archivos de plantilla para modelo {modelo}: "
            f"{len(template_paths)} paths vs {len(template_files)} files"
        )

    for template_path, template_file in zip(template_paths, template_files):
        cache_key = f"{printer_name}::{template_path}"

        if cache_key not in _TEMPLATES_INSTALLED:
            print(f"[ZEBRA] Instalando plantilla para modelo {modelo}: {template_file}")
            instalar_template(printer_name, template_file)
            _TEMPLATES_INSTALLED.add(cache_key)

    return template_paths

FIELD_MAP_BY_TEMPLATE = {
    "R:x6-10.ZPL": {
        "mac": 1,
        "sn": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:x6.ZPL": {
        "mac": 1,
        "sn": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:V5.ZPL": {
        "mac": 1,
        "sn": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:zte1.ZPL": {
        "sn": 1,
        "mac": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:zte2.ZPL": {
        "sn": 5,
        "mac": 4,
        "pass_wifi": 3,
        "wifi24": 1,
        "wifi5": 2,
    },
    "R:zte3.ZPL": {
        "sn": 5,
        "mac": 4,
        "pass_wifi": 3,
        "wifi24": 1,
        "wifi5": 2,
    },
    "R:fiberFA.ZPL": {
        "sn": 1,
        "mac": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:fiberF1A.ZPL": {
        "sn": 1,
        "mac": 2,
        "pass_wifi": 3,
        "wifi24": 4,
        "wifi5": 5,
    },
    "R:fiberFB.ZPL": {
        "sn": 5,
        "mac": 4,
        "pass_wifi": 2,
        "wifi24": 1,
        "wifi5": 3,
    },
}


def construir_recall_zpl(datos: dict, template_path: str) -> str:
    field_map = FIELD_MAP_BY_TEMPLATE[template_path]
    values = {
        "mac": escape_zpl(datos.get("mac", "")),
        "sn": escape_zpl(datos.get("sn", "")),
        "pass_wifi": escape_zpl(datos.get("pass_wifi", "")),
        "wifi24": escape_zpl(datos.get("wifi24", "")),
        "wifi5": escape_zpl(datos.get("wifi5", "")),
    }

    lines = ["^XA", f"^XF{template_path}^FS", "^CI27"]
    for key, fn in field_map.items():
        lines.append(f"^FN{fn}^FH\\^FD{values[key]}^FS")
    lines.append("^PQ1,0,1")
    lines.append("^XZ")
    return "\n".join(lines)

def imprimir_etiqueta_zebra(datos: dict, printer_name: str) -> None:
    modelo = datos.get("modelo", "DESCONOCIDO").upper()

    template_paths = asegurar_templates_instalados(
        printer_name=printer_name,
        modelo=modelo
    )

    for template_path in template_paths:
        zpl = construir_recall_zpl(
            datos=datos,
            template_path=template_path
        )

        print(f"[ZEBRA] Imprimiendo modelo {modelo} con plantilla {template_path}")
        send_raw_to_printer(printer_name, zpl)