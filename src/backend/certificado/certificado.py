from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
# from weasyprint import HTML, CSS

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR.parent / "reports"


def _get_weasyprint():
    """
    Carga WeasyPrint sólo cuando realmente se necesita.
    Envuelve los errores en un RuntimeError para que el llamador pueda decidir
    qué hacer (mostrar mensaje, etc.).
    """
    try:
        from weasyprint import HTML, CSS  # type: ignore
        return HTML, CSS
    except Exception as e:
        # Aquí caen tanto problemas de import como de DLL (libgobject-2.0-0, etc.)
        raise RuntimeError(
            "No se pudo inicializar WeasyPrint. En el ejecutable probablemente "
            "faltan las librerías nativas (GTK / libgobject / pango / cairo)."
        ) from e


def generarCertificado(resultado: dict):
    REPORTS_DIR.mkdir(exist_ok=True)

    info = resultado.get("info", {})
    tests = resultado.get("tests", {})
    valido = resultado.get("valido", False)

    sn = info.get("sn", "SIN_SN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_pdf = f"certificado_{sn}_{timestamp}.pdf"
    ruta_pdf = REPORTS_DIR / nombre_pdf

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html")

    fechaTest = info.get("fecha_test", "01/01/0001")
    try:
        dt = datetime.fromisoformat(fechaTest)
        fechaTest = dt.strftime("%d/%m/%Y")
    except ValueError:
        # Si el formato no es ISO, lo dejamos como venga
        pass

    fechaHoy = datetime.now().strftime("%d/%m/%Y")
    sft_v = info.get("sftVer", "")

    # Software update pass
    sftUStatus = "SKIP"
    if info.get("modelo") in ("HG6145F", "HG6145F1"):
        if "!" not in sft_v:
            sftUStatus = "PASS"
        else:
            sftUStatus = "FAIL"

    contexto = {
        # header
        "sn": info.get("sn", ""),
        "fecha_diagnostico": fechaTest,

        # info
        "model": info.get("modelo", ""),
        "mac": info.get("mac", ""),
        "sft_v": info.get("sftVer", ""),
        "w24ssid": info.get("wifi24", ""),
        "w5ssid": info.get("wifi5", ""),
        "wifi_pass": info.get("passWifi", ""),
        "estacion": 25,  # TODO: parametrizar

        # pruebas
        "fact_reset": tests.get("reset", ""),
        "ping": tests.get("ping", ""),
        "sft_u": sftUStatus,
        "usb": tests.get("usb", ""),
        "fibra_tx": tests.get("tx", ""),
        "fibra_rx": tests.get("rx", ""),
        "w24_test": tests.get("w24", ""),
        "w5_test": tests.get("w5", ""),

        # footer
        "fecha_certificado": fechaHoy,
    }

    html_renderizado = template.render(**contexto)
    tmp_html = TEMPLATES_DIR / "_tmp_render.html"
    tmp_html.write_text(html_renderizado, encoding="utf-8")

    # Intentar usar WeasyPrint
    try:
        HTML, CSS = _get_weasyprint()
    except RuntimeError as e:
        # En modo exe, caerás aquí si faltan las DLL. No rompemos la app,
        # sólo devolvemos None y dejamos que la UI avise al usuario.
        print(f"[CERTIFICADO] {e}")
        return None

    html_obj = HTML(
        string=html_renderizado,
        base_url=str(TEMPLATES_DIR),
    )
    css = CSS(filename=str(TEMPLATES_DIR / "estilos.css"))

    html_obj.write_pdf(
        target=str(ruta_pdf),
        stylesheets=[css],
    )

    return ruta_pdf
