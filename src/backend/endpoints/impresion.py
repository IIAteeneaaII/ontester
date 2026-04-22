from pathlib import Path
import win32print


# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(r"C:\ONT\zebra_templates")

# modelo -> nombre de plantilla en impresora
TEMPLATE_BY_MODEL = {
    "HG6145F": "R:HG6145F.ZPL",
    "RP2811": "R:RP2811.ZPL",
    "F670": "R:F670.ZPL",
    "HG8145X6-10": "R:x6-10.ZPL",
    "HG8145V5": "R:V5.ZPL",
    "DESCONOCIDO": "R:x6-10.ZPL",
}

# modelo -> archivo local que instala la plantilla
TEMPLATE_FILE_BY_MODEL = {
    "HG6145F": BASE_DIR / "HG6145F_store.zpl",
    "RP2811": BASE_DIR / "RP2811_store.zpl",
    "F670": BASE_DIR / "F670_store.zpl",
    "HG8145X6-10": BASE_DIR / "x6-10.prn",
    "HG8145V5": BASE_DIR / "V5.prn",
    "DESCONOCIDO": BASE_DIR / "x6-10.prn",
}

# Control simple en memoria para no reinstalar en cada impresión
_TEMPLATES_INSTALLED = set()

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


def asegurar_template_instalado(printer_name: str, modelo: str) -> str:
    template_path = obtener_template_path(modelo)
    cache_key = f"{printer_name}::{template_path}"

    if cache_key not in _TEMPLATES_INSTALLED:
        template_file = obtener_template_file(modelo)
        print(f"[ZEBRA] Instalando plantilla para modelo {modelo}: {template_file}")
        instalar_template(printer_name, template_file)
        _TEMPLATES_INSTALLED.add(cache_key)

    return template_path

def construir_recall_zpl(datos: dict, template_path: str) -> str:
    mac = escape_zpl(datos.get("mac", ""))
    sn = escape_zpl(datos.get("sn", ""))
    password = escape_zpl(datos.get("pass_wifi", ""))
    wifi24 = escape_zpl(datos.get("wifi24", ""))
    wifi5 = escape_zpl(datos.get("wifi5", ""))

    return f"""^XA
^XF{template_path}^FS
^CI27^FN1^FH\\^FD{mac}^FS
^CI27^FN2^FH\\^FD{sn}^FS
^CI27^FN3^FH\\^FD{password}^FS
^CI27^FN4^FH\\^FD{wifi24}^FS
^CI27^FN5^FH\\^FD{wifi5}^FS
^PQ1,0,1
^XZ"""

def imprimir_etiqueta_zebra(datos: dict, printer_name: str) -> None:
    modelo = datos.get("modelo", "DESCONOCIDO").upper()

    template_path = asegurar_template_instalado(
        printer_name=printer_name,
        modelo=modelo
    )

    zpl = construir_recall_zpl(
        datos=datos,
        template_path=template_path
    )

    print(f"[ZEBRA] Imprimiendo modelo {modelo} con plantilla {template_path}")
    send_raw_to_printer(printer_name, zpl)