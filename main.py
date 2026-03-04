# main.py en la raíz de ontester
import traceback
from pathlib import Path
from datetime import datetime
from src.backend.sua_client.local_db import init_db

if __name__ == "__main__":
    try:
        # Iniciar la db
        init_db()
        # from src.backend.mixins.common_mixin import CommonMixin
        # cm = CommonMixin()
        # nets_all = cm.scan_wifi_windows(target_ssid=None, retries=3, delay=1.0, debug=True)
        # print("SSIDs vistos:", sorted({n["ssid"] for n in nets_all if n.get("ssid")}))
        # Correr interfaz
        from src.Frontend.ui.inicio_view import run_app
        run_app()        

    except Exception as e:
        log_path = Path("C:/ONT/ontester_exe_error.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n\n=== EXCEPCIÓN NO MANEJADA ===\n")
            f.write(f"Fecha/hora: {datetime.now().isoformat()}\n")
            f.write(f"Tipo: {type(e).__name__}\n")
            f.write(f"Mensaje: {e}\n\n")
            traceback.print_exc(file=f)